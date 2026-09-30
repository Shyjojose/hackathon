"""
ThesisClaw — Cloudflare Quick Tunnel launcher.

Spawns `cloudflared tunnel --url http://localhost:<port>` as a managed
background subprocess, captures the assigned *.trycloudflare.com URL from
its stdout, and hot-patches `settings.mcp_tunnel_domain` so that every
subsequent call to `get_base_page_url()` in the Telegram bot returns the
public HTTPS URL.

No Cloudflare account or authentication needed — Quick Tunnels are free,
have no bandwidth cap, and require only the `cloudflared` binary.

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


def start_quick_tunnel(port: int | None = None) -> str | None:
    """
    Start a Cloudflare Quick Tunnel in background and return the public URL.

    Blocks for up to 20 seconds while waiting for cloudflared to print its URL.
    Returns None with a warning log if cloudflared is not installed or the URL
    cannot be determined within the timeout (graceful degradation — server still
    works on LAN).
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
        stderr=subprocess.STDOUT,   # merge stderr so we catch the URL on either stream
        text=True,
        bufsize=1,
    )

    url_event = threading.Event()
    discovered: list[str] = []

    def _reader() -> None:
        assert _proc and _proc.stdout
        for raw_line in _proc.stdout:
            line = raw_line.rstrip()
            logger.debug("[cloudflared] %s", line)
            url = _parse_url_from_line(line)
            if url and not url_event.is_set():
                discovered.append(url)
                url_event.set()

    threading.Thread(target=_reader, daemon=True, name="cloudflared-reader").start()

    found = url_event.wait(timeout=20)
    if not found or not discovered:
        logger.error(
            "cloudflared did not report a tunnel URL within 20 s — "
            "Telegram links will use LAN IP as fallback."
        )
        return None

    public_url = discovered[0].rstrip("/")
    logger.info(
        "✅ Cloudflare Quick Tunnel active: %s → http://localhost:%d",
        public_url, port,
    )

    # Hot-patch settings so get_base_page_url() resolves immediately
    _settings.mcp_tunnel_domain = public_url

    # Persist the URL to .env so it survives uvicorn hot-reloads
    _update_env_file(public_url)

    return public_url


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
    If the key is not present, it is appended.  Idempotent.
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
