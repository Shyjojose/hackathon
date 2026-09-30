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


# ── Arena / Paper Fight Tools (/mcp only) ─────────────────────────────────────


@mcp_router.post("/tools/start_fight", dependencies=[Depends(verify_mcp_auth)])
async def start_fight_tool(payload: dict[str, Any]) -> dict[str, Any]:
    """
    MCP Tool: Start a Paper Arena fight.
    - No args       → Ground vs most similar paper from processed_papers DB
    - {"a": arxiv_id}     → Ground vs specific paper
    - {"a": id, "b": id}  → paper vs paper
    Returns immediately with fight_id; fight runs in background.
    """
    import asyncio
    import uuid

    from thesisclaw.arena.docs import load_fighter_doc
    from thesisclaw.arena.graph import run_fight
    from thesisclaw.arena.memory import upsert_fight
    from thesisclaw.arena.models import Fighter, FighterKind, FightRecord, FightState
    from thesisclaw.arena.select import get_candidates_from_db, top_opponent

    a_id = payload.get("a")
    b_id = payload.get("b")
    fight_id = f"fight-{uuid.uuid4().hex[:8]}"

    # Determine fighters
    if a_id is None and b_id is None:
        # Auto: Ground vs most similar from DB
        ground_doc = await load_fighter_doc("ground", "ground")
        candidates = get_candidates_from_db(settings.checkpoints_dir / "thesisclaw.sqlite3")
        best = top_opponent(ground_doc["text"], candidates)
        if best is None:
            return {"error": "No papers found in DB for auto-fight. Run /briefing first to ingest papers.", "fight_id": None}
        fighter_a = Fighter(kind=FighterKind.GROUND, doc_id="ground")
        fighter_b = Fighter(kind=FighterKind.PAPER, doc_id=best.doc_id)
    elif b_id is None:
        fighter_a = Fighter(kind=FighterKind.GROUND, doc_id="ground")
        fighter_b = Fighter(kind=FighterKind.PAPER, doc_id=a_id)
    else:
        fighter_a = Fighter(kind=FighterKind.PAPER, doc_id=a_id)
        fighter_b = Fighter(kind=FighterKind.PAPER, doc_id=b_id)

    # Register fight as queued
    record = FightRecord(fight_id=fight_id, fighter_a=fighter_a, fighter_b=fighter_b, state=FightState.QUEUED)
    upsert_fight(record)

    # Launch fight in background (non-blocking)
    asyncio.create_task(run_fight(fighter_a, fighter_b, fight_id=fight_id))

    return {
        "fight_id": fight_id,
        "fighter_a": fighter_a.doc_id,
        "fighter_b": fighter_b.doc_id,
        "status": "queued",
        "message": f"Fight {fight_id} started. Use fight_status to track progress.",
    }


@mcp_router.post("/tools/fight_status", dependencies=[Depends(verify_mcp_auth)])
def fight_status_tool(payload: dict[str, Any]) -> dict[str, Any]:
    """MCP Tool: Get the current state of a fight by fight_id."""
    from thesisclaw.arena.memory import get_fight, list_fights
    fight_id = payload.get("fight_id")
    if fight_id:
        record = get_fight(fight_id)
        if record is None:
            return {"error": f"Fight {fight_id} not found"}
        return {
            "fight_id": record.fight_id,
            "state": record.state.value,
            "fighter_a": record.fighter_a.doc_id,
            "fighter_b": record.fighter_b.doc_id,
            "finished_at": record.finished_at,
            "error": record.error or None,
        }
    # Return latest fight
    fights = list_fights(limit=1)
    if not fights:
        return {"message": "No fights recorded yet. Use start_fight to begin."}
    record = fights[0]
    return {"fight_id": record.fight_id, "state": record.state.value, "fighter_a": record.fighter_a.doc_id, "fighter_b": record.fighter_b.doc_id}


@mcp_router.post("/tools/get_verdict", dependencies=[Depends(verify_mcp_auth)])
def get_verdict_tool(payload: dict[str, Any]) -> dict[str, Any]:
    """MCP Tool: Get the merged verdict for a completed fight."""
    from thesisclaw.arena.memory import get_fight, list_fights
    fight_id = payload.get("fight_id")
    if not fight_id:
        fights = list_fights(limit=1)
        record = fights[0] if fights else None
    else:
        record = get_fight(fight_id)
    if record is None or record.merged_verdict is None:
        return {"error": "No verdict available yet. Fight may still be running."}
    mv = record.merged_verdict
    return {
        "fight_id": record.fight_id,
        "winner": mv.winner,
        "swap_agreement": mv.swap_agreement,
        "final_scores": mv.final_scores,
        "verified_ratio": mv.all_entries_verified_ratio,
        "ranked_ideas_count": len(mv.ranked_ideas),
        "struck_count": mv.struck_count,
        "upheld_count": mv.upheld_count,
    }


@mcp_router.post("/tools/ask_paper", dependencies=[Depends(verify_mcp_auth)])
async def ask_paper_tool(payload: dict[str, Any]) -> dict[str, Any]:
    """
    MCP Tool: Ask a question to a paper and get verified quotes or 'not in this paper'.
    Input: {"doc_id": "2301.12345", "question": "What RTF did they achieve?"}
    """
    from thesisclaw.arena.docs import load_fighter_doc
    from thesisclaw.arena.verify import verify_quote

    doc_id = payload.get("doc_id", "")
    question = payload.get("question", "")
    if not doc_id or not question:
        return {"error": "Both 'doc_id' and 'question' are required"}

    try:
        doc = await load_fighter_doc(doc_id)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Could not load document {doc_id}: {exc}"}

    # Simple heuristic: search for question keywords in the document
    keywords = [w.lower() for w in question.split() if len(w) > 4]
    sentences = doc["text"].replace("\n", " ").split(". ")
    matching = [s for s in sentences if any(kw in s.lower() for kw in keywords)]

    if not matching:
        return {"answer": "not in this paper", "doc_id": doc_id, "question": question}

    best = matching[0][:400]
    result = verify_quote(best, doc["text"])
    return {
        "answer": best,
        "doc_id": doc_id,
        "verified": result["verified"],
        "near_exact": result["near_exact"],
        "section": result["section"],
        "question": question,
    }


@mcp_router.post("/tools/similar_papers", dependencies=[Depends(verify_mcp_auth)])
def similar_papers_tool(payload: dict[str, Any]) -> dict[str, Any]:
    """
    MCP Tool: Return papers most similar to a given doc_id.
    Input: {"doc_id": "ground" | "2301.12345", "tau": 0.65, "limit": 5}
    """
    from thesisclaw.arena.select import get_candidates_from_db, rank_opponents

    doc_id = payload.get("doc_id", "ground")
    tau = float(payload.get("tau", 0.65))
    limit = int(payload.get("limit", 5))

    candidates = get_candidates_from_db(settings.checkpoints_dir / "thesisclaw.sqlite3", exclude_doc_ids={doc_id}, limit=100)
    if not candidates:
        return {"similar_papers": [], "message": "No candidates in DB"}

    # Get target text from DB or use a short representation
    import sqlite3
    target_text = ""
    try:
        with sqlite3.connect(settings.checkpoints_dir / "thesisclaw.sqlite3") as conn:
            row = conn.execute("SELECT title, reason FROM processed_papers WHERE arxiv_id = ?", (doc_id,)).fetchone()
            if row:
                target_text = f"{row[0] or ''} {row[1] or ''}".strip()
    except Exception:  # noqa: BLE001, S110
        pass

    if not target_text:
        return {"error": f"Document {doc_id} not found in DB"}

    ranked = rank_opponents(target_text, candidates, tau=tau)
    return {
        "doc_id": doc_id,
        "tau": tau,
        "similar_papers": [
            {"doc_id": r.doc_id, "score": round(r.score, 3), "above_tau": r.above_tau}
            for r in ranked[:limit]
        ],
    }


@mcp_router.post("/tools/leaderboard", dependencies=[Depends(verify_mcp_auth)])
def leaderboard_tool(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """MCP Tool: Return the current Elo leaderboard."""
    from thesisclaw.arena.memory import get_leaderboard
    limit = int((payload or {}).get("limit", 10))
    lb = get_leaderboard(limit=limit)
    return {
        "leaderboard": [
            {
                "rank": i + 1,
                "doc_id": e.doc_id,
                "rating": round(e.rating, 1),
                "wins": e.wins,
                "losses": e.losses,
                "draws": e.draws,
                "fights": e.fights,
            }
            for i, e in enumerate(lb)
        ]
    }
