from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from thesisclaw.config.settings import settings
from thesisclaw.mcp.server import mcp_router, voice_mcp_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    FastAPI lifespan context manager.

    Startup: Auto-start Cloudflare Quick Tunnel unless MCP_TUNNEL_DOMAIN is
    already set in .env (e.g. a named persistent tunnel). Runs the blocking
    tunnel launcher in a thread-pool executor so the event loop is not blocked
    while cloudflared prints its assigned URL (≤ 20 s).

    Shutdown: Terminate the cloudflared subprocess cleanly.
    """
    # ── Startup ───────────────────────────────────────────────────────────────
    existing = settings.mcp_tunnel_domain.split("#")[0].strip()
    if existing:
        logger.info(
            "MCP_TUNNEL_DOMAIN already set to %s — skipping auto Quick Tunnel", existing
        )
    else:
        from thesisclaw.infra.tunnel import start_quick_tunnel

        loop = asyncio.get_running_loop()
        url = await loop.run_in_executor(None, start_quick_tunnel)
        if url:
            logger.info("🌐 Public ThesisClaw URL: %s", url)
        else:
            logger.warning(
                "No Cloudflare Tunnel URL — Telegram links will use LAN IP. "
                "Install cloudflared (brew install cloudflared) to enable mobile access."
            )

    yield  # ← server is running here

    # ── Shutdown ──────────────────────────────────────────────────────────────
    from thesisclaw.infra.tunnel import stop_tunnel

    stop_tunnel()


# Import the FastAPI app from web.app and attach the lifespan handler
from thesisclaw.web.app import app

app.router.lifespan_context = lifespan  # type: ignore[assignment]

# Mount both MCP surfaces to the main web app
app.include_router(mcp_router)
app.include_router(voice_mcp_router)


def run_server() -> None:
    """Run unified ThesisClaw web and MCP server on local port."""
    uvicorn.run(
        "thesisclaw.mcp.main:app",
        host=settings.mcp_host,
        port=settings.mcp_port,
        reload=False,
    )


if __name__ == "__main__":
    run_server()
