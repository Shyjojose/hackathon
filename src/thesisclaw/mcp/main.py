from __future__ import annotations

import uvicorn

from thesisclaw.config.settings import settings
from thesisclaw.mcp.server import mcp_router, voice_mcp_router
from thesisclaw.web.app import app

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
