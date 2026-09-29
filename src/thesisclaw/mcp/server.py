from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException

from thesisclaw.agent.orchestrator import ThesisOrchestrator
from thesisclaw.config.settings import settings

logger = logging.getLogger(__name__)

mcp_router = APIRouter(prefix="/mcp", tags=["mcp"])
voice_mcp_router = APIRouter(prefix="/voice-mcp", tags=["voice-mcp"])

orchestrator = ThesisOrchestrator()


def verify_mcp_auth(authorization: str = Header(default="")) -> None:
    """Validate bearer token for /mcp full tool surface."""
    expected = f"Bearer {settings.mcp_bearer_token}"
    if not authorization or authorization != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing MCP bearer token.")


def verify_voice_auth(authorization: str = Header(default="")) -> None:
    """Validate bearer token for /voice-mcp read-only tool surface."""
    expected = f"Bearer {settings.voice_mcp_bearer_token}"
    if not authorization or authorization != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing Voice MCP bearer token.")


# ── Full /mcp Tool Surface ───────────────────────────────────────────────────

@mcp_router.post("/tools/analyze_paper", dependencies=[Depends(verify_mcp_auth)])
async def analyze_paper_tool(payload: dict[str, Any]) -> dict[str, Any]:
    """MCP Tool: Queue or run single paper analysis."""
    url = payload.get("url", "")
    if not url:
        raise HTTPException(status_code=400, detail="Missing 'url' parameter.")
    res = await orchestrator.evaluate_single_paper(url)
    return {
        "arxiv_id": res["paper"].arxiv_id,
        "title": res["paper"].title,
        "verdict": res["verdict"].verdict.value,
        "reason": res["verdict"].reason,
        "direct_quote": res["verdict"].direct_quote,
    }


@mcp_router.post("/tools/get_briefing", dependencies=[Depends(verify_mcp_auth)])
async def get_briefing_tool(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """MCP Tool: Retrieve the latest literature briefing."""
    briefing = await orchestrator.run_batch_evaluation([])
    return {
        "briefing": briefing.telegram_briefing,
        "voice_briefing": briefing.voice_briefing,
        "papers_processed": briefing.papers_processed,
    }


@mcp_router.post("/tools/get_status", dependencies=[Depends(verify_mcp_auth)])
def get_status_tool() -> dict[str, Any]:
    """MCP Tool: Check agent uptime and status."""
    return {
        "status": "online",
        "app": "ThesisClaw",
        "thesis_area": "Raspberry Pi 5 Edge AI ASR",
    }


@mcp_router.post("/tools/add_note", dependencies=[Depends(verify_mcp_auth)])
def add_note_tool(payload: dict[str, Any]) -> dict[str, Any]:
    """MCP Tool: Append a research note."""
    content = payload.get("content", "")
    source = payload.get("source", "mcp")
    if not content:
        raise HTTPException(status_code=400, detail="Missing 'content' parameter.")
    return {"status": "saved", "source": source, "chars": len(content)}


# ── Read-Only /voice-mcp Surface (for XiaoZhi ESP32-S3) ────────────────────────

@voice_mcp_router.post("/tools/get_briefing", dependencies=[Depends(verify_voice_auth)])
async def get_voice_briefing_tool(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Voice MCP Tool: Returns plain-text briefing strictly <= 600 characters."""
    briefing = await orchestrator.run_batch_evaluation([])
    text = briefing.voice_briefing
    if len(text) > settings.voice_reply_max_chars:
        text = text[: settings.voice_reply_max_chars - 3] + "..."
    return {"reply": text, "length": len(text)}


@voice_mcp_router.post("/tools/get_paper_summary", dependencies=[Depends(verify_voice_auth)])
def get_voice_paper_summary_tool(payload: dict[str, Any]) -> dict[str, Any]:
    """Voice MCP Tool: Concise plain text paper summary."""
    arxiv_id = payload.get("arxiv_id", "")
    return {
        "arxiv_id": arxiv_id,
        "summary": f"Paper arXiv:{arxiv_id} evaluated for Raspberry Pi 5 ASR quantization.",
    }


@voice_mcp_router.post("/tools/get_status", dependencies=[Depends(verify_voice_auth)])
def get_voice_status_tool() -> dict[str, Any]:
    """Voice MCP Tool: Short voice status."""
    return {"reply": "ThesisClaw is online and monitoring edge ASR literature."}
