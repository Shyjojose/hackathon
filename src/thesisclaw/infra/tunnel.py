"""
ThesisClaw — Cloudflare Tunnel launcher.

Supports two operational modes:
1. Named Tunnel (Token-based): If `CLOUDFLARE_TUNNEL_TOKEN` is configured in `.env`,
   launches `cloudflared tunnel run --token <token>` in the background. This provides
   a permanent, fixed HTTPS URL that never changes across restarts.
2. Quick Tunnel (Zero-config): If no token is provided, launches
   `cloudflared tunnel --url http://localhost:<port> --no-autoupdate` as a managed
   subprocess, captures the assigned *.trycloudflare.com URL from stdout, and
   hot-patches `settings.mcp_tunnel_domain` for the session.

Install once with:  brew install cloudflared
"""
from __future__ import annotations

import logging
import re
import shutil
import subprocess
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

# Matches any *.trycloudflare.com URL printed by cloudflared to stdout/stderr
_TUNNEL_URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")

# Singleton subprocess handle
_proc: subprocess.Popen[str] | None = None


def _parse_url_from_line(line: str) -> str | None:
    """Return the first trycloudflare.com URL found in `line`, or None."""
    m = _TUNNEL_URL_RE.search(line)
    return m.group() if m else None


def should_start_tunnel(domain: str, token: str = "") -> bool:
    """
    Return True if we should spawn cloudflared on startup.

    - If a named tunnel token is provided, always start the named tunnel.
    - If domain is empty or contains trycloudflare.com, start a fresh quick tunnel
      (because quick tunnels are ephemeral per-session and die on process exit).
    - If a custom named domain is set WITHOUT a token, assume the user runs
      cloudflared as a system service or external container.
    """
    if token.strip():
        return True
    clean = domain.split("#")[0].strip()
    return bool(not clean or "trycloudflare.com" in clean)


def start_tunnel(port: int | None = None) -> str | None:
    """
    Start Cloudflare Tunnel in background and return reachable public URL.

    If settings.cloudflare_tunnel_token is set, runs a named tunnel.
    Otherwise runs a quick tunnel and auto-discovers the trycloudflare.com URL.
    """
    global _proc

    from thesisclaw.config.settings import settings as _settings

    port = port or _settings.mcp_port
    cloudflared_bin = shutil.which("cloudflared")
    if not cloudflared_bin:
        logger.warning(
            "cloudflared not found in PATH — Cloudflare Tunnel not started. "
            "Install with: brew install cloudflared"
        )
        return None

    token = _settings.cloudflare_tunnel_token.strip()

    if token:
        # ── Mode 1: Named Persistent Tunnel ───────────────────────────────────
        cmd = [
            cloudflared_bin,
            "tunnel",
            "run",
            "--token", token,
        ]
        logger.info("Starting Cloudflare Named Tunnel with token...")
        _proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        connected_event = threading.Event()

        def _named_reader() -> None:
            assert _proc and _proc.stdout
            for raw_line in _proc.stdout:
                line = raw_line.rstrip()
                logger.debug("[cloudflared-named] %s", line)
                if "Registered tunnel connection" in line or "Connection" in line:
                    connected_event.set()

        threading.Thread(target=_named_reader, daemon=True, name="cf-named-reader").start()
        connected_event.wait(timeout=10)

        configured_domain = _settings.mcp_tunnel_domain.split("#")[0].strip()
        if configured_domain and not configured_domain.startswith(("http://", "https://")):
            configured_domain = f"https://{configured_domain}"

        if configured_domain and "trycloudflare.com" not in configured_domain:
            logger.info("✅ Cloudflare Named Tunnel connected → %s", configured_domain)
            return configured_domain

        logger.info("✅ Cloudflare Named Tunnel connected to Cloudflare Edge.")
        return configured_domain or None

    # ── Mode 2: Quick Tunnel (ephemeral trycloudflare.com) ───────────────────
    cmd = [
        cloudflared_bin,
        "tunnel",
        "--url", f"http://localhost:{port}",
        "--no-autoupdate",
    ]
    logger.info("Starting Cloudflare Quick Tunnel: %s", " ".join(cmd))

    _proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    url_event = threading.Event()
    discovered: list[str] = []

    def _quick_reader() -> None:
        assert _proc and _proc.stdout
        for raw_line in _proc.stdout:
            line = raw_line.rstrip()
            logger.debug("[cloudflared] %s", line)
            url = _parse_url_from_line(line)
            if url and not url_event.is_set():
                discovered.append(url)
                url_event.set()

    threading.Thread(target=_quick_reader, daemon=True, name="cloudflared-reader").start()

    found = url_event.wait(timeout=20)
    if not found or not discovered:
        logger.error(
            "cloudflared did not report a tunnel URL within 20 s — "
            "Telegram links will use LAN IP as fallback."
        )
        return None

    public_url = discovered[0].rstrip("/")
    logger.info("✅ Cloudflare Quick Tunnel active: %s → http://localhost:%d", public_url, port)

    # Hot-patch settings so get_base_page_url() resolves immediately
    _settings.mcp_tunnel_domain = public_url

    # Persist the URL to .env for this session
    _update_env_file(public_url)

    return public_url


def start_quick_tunnel(port: int | None = None) -> str | None:
    """Backward-compatible alias for start_tunnel."""
    return start_tunnel(port=port)


def stop_tunnel() -> None:
    """Terminate the cloudflared subprocess gracefully on server shutdown."""
    global _proc
    if _proc and _proc.poll() is None:
        logger.info("Stopping Cloudflare Tunnel...")
        _proc.terminate()
        try:
            _proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _proc.kill()
        _proc = None
        logger.info("Cloudflare Tunnel stopped.")


def _update_env_file(url: str) -> None:
    """
    Write `MCP_TUNNEL_DOMAIN=<url>` into `.env` without touching other lines.
    If the key is not present, it is appended. Idempotent.
    """
    env_path = Path(".env")
    if not env_path.exists():
        logger.debug(".env not found — skipping MCP_TUNNEL_DOMAIN update")
        return

    lines = env_path.read_text(encoding="utf-8").splitlines()
    new_lines: list[str] = []
    found = False
    for line in lines:
        if line.startswith("MCP_TUNNEL_DOMAIN"):
            new_lines.append(f"MCP_TUNNEL_DOMAIN={url}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"MCP_TUNNEL_DOMAIN={url}")

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    logger.info(".env updated: MCP_TUNNEL_DOMAIN=%s", url)
