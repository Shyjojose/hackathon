# ThesisClaw Infrastructure

This folder contains infrastructure utilities that run on the local machine.

## Cloudflare Quick Tunnel (`tunnel.py`)

[`tunnel.py`](../src/thesisclaw/infra/tunnel.py) exposes the ThesisClaw server to the
public internet using a **free Cloudflare Quick Tunnel** — no account, no bandwidth cap.

### How it works

1. When the ThesisClaw server starts (`uv run python -m thesisclaw.mcp.main`), a FastAPI
   `startup` event spawns `cloudflared tunnel --url http://localhost:8080`.
2. The launcher reads cloudflared's stdout until it finds the `*.trycloudflare.com` URL.
3. It hot-patches `settings.mcp_tunnel_domain` so all Telegram links immediately use the
   public HTTPS URL.
4. The URL is written back to `.env` as `MCP_TUNNEL_DOMAIN=https://xxx.trycloudflare.com`.
5. On server shutdown, the subprocess is terminated cleanly.

### Prerequisites

```bash
brew install cloudflared   # one-time install
```

### Named tunnel (optional — same URL every restart)

For a stable persistent URL, create a named tunnel:

```bash
cloudflared login                            # opens browser, picks your zone
cloudflared tunnel create thesisclaw         # creates a named tunnel
cloudflared tunnel route dns thesisclaw thesisclaw.<yourdomain.com>
```

Then set in `.env`:
```
MCP_TUNNEL_DOMAIN=thesisclaw.<yourdomain.com>
```

When `MCP_TUNNEL_DOMAIN` is pre-set, the auto-tunnel is skipped.
