"""
Unit tests for src/thesisclaw/infra/tunnel.py

All tests are fully offline — no cloudflared process is spawned.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

# ── _parse_url_from_line ──────────────────────────────────────────────────────


def test_parse_url_found():
    from thesisclaw.infra.tunnel import _parse_url_from_line

    line = "2026-09-30 INFO Your quick Tunnel has been created! Visit it at https://abc-def-123.trycloudflare.com"
    assert _parse_url_from_line(line) == "https://abc-def-123.trycloudflare.com"


def test_parse_url_not_found():
    from thesisclaw.infra.tunnel import _parse_url_from_line

    assert _parse_url_from_line("Connecting to backend, please wait...") is None
    assert _parse_url_from_line("") is None


def test_parse_url_ignores_non_tunnel_https():
    from thesisclaw.infra.tunnel import _parse_url_from_line

    # Regular https URL should not match
    assert _parse_url_from_line("See https://example.com for details") is None


# ── start_quick_tunnel — graceful degradation ─────────────────────────────────


def test_start_quick_tunnel_no_cloudflared(monkeypatch):
    """When cloudflared is not in PATH, return None gracefully without raising."""
    monkeypatch.setattr("shutil.which", lambda _name: None)
    # Reload to clear any cached module state
    import thesisclaw.infra.tunnel as tunnel_mod
    result = tunnel_mod.start_quick_tunnel(port=8080)
    assert result is None


# ── _update_env_file ──────────────────────────────────────────────────────────


def test_update_env_file_replaces_existing(tmp_path: Path, monkeypatch):
    """When MCP_TUNNEL_DOMAIN already exists in .env, it is replaced in-place."""
    env = tmp_path / ".env"
    env.write_text(textwrap.dedent("""\
        NVIDIA_API_KEY=abc
        MCP_TUNNEL_DOMAIN=https://old-url.trycloudflare.com
        OTHER_KEY=value
    """))
    monkeypatch.chdir(tmp_path)

    from thesisclaw.infra.tunnel import _update_env_file

    _update_env_file("https://new-url.trycloudflare.com")
    content = env.read_text()

    assert "MCP_TUNNEL_DOMAIN=https://new-url.trycloudflare.com" in content
    assert "old-url" not in content
    assert "NVIDIA_API_KEY=abc" in content
    assert "OTHER_KEY=value" in content


def test_update_env_file_appends_if_missing(tmp_path: Path, monkeypatch):
    """When MCP_TUNNEL_DOMAIN is absent from .env, it is appended."""
    env = tmp_path / ".env"
    env.write_text("TELEGRAM_BOT_TOKEN=tok\n")
    monkeypatch.chdir(tmp_path)

    from thesisclaw.infra.tunnel import _update_env_file

    _update_env_file("https://brand-new.trycloudflare.com")
    content = env.read_text()

    assert "MCP_TUNNEL_DOMAIN=https://brand-new.trycloudflare.com" in content
    assert "TELEGRAM_BOT_TOKEN=tok" in content


def test_update_env_file_skips_when_no_dotenv(tmp_path: Path, monkeypatch):
    """When .env does not exist, _update_env_file does nothing and does not raise."""
    monkeypatch.chdir(tmp_path)  # empty dir — no .env
    from thesisclaw.infra.tunnel import _update_env_file

    _update_env_file("https://example.trycloudflare.com")  # should not raise


# ── stop_tunnel ───────────────────────────────────────────────────────────────


def test_stop_tunnel_no_proc():
    """stop_tunnel is a no-op when no tunnel process was started."""
    import thesisclaw.infra.tunnel as tunnel_mod
    tunnel_mod._proc = None  # ensure clean state
    tunnel_mod.stop_tunnel()  # must not raise


def test_stop_tunnel_terminates_proc(monkeypatch):
    """stop_tunnel calls terminate() on the running subprocess."""
    from unittest.mock import MagicMock

    import thesisclaw.infra.tunnel as tunnel_mod

    mock_proc = MagicMock()
    mock_proc.poll.return_value = None  # process is running
    tunnel_mod._proc = mock_proc

    tunnel_mod.stop_tunnel()

    mock_proc.terminate.assert_called_once()
    mock_proc.wait.assert_called_once()
    assert tunnel_mod._proc is None
