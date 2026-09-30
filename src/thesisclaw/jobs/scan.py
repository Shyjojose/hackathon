from __future__ import annotations

import argparse
import asyncio
import logging
import urllib.parse
import xml.etree.ElementTree as ET

import httpx

from thesisclaw.agent.orchestrator import ThesisOrchestrator
from thesisclaw.models.paper import BriefingResult

logger = logging.getLogger(__name__)


async def query_arxiv_rss_or_api(query: str, max_results: int = 5) -> list[str]:
    """Query arXiv API for recent papers matching technical query."""
    base_url = "http://export.arxiv.org/api/query?"
    params = {
        "search_query": f"all:{query}",
        "start": "0",
        "max_results": str(max_results),
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    url = base_url + urllib.parse.urlencode(params)

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return []

            root = ET.fromstring(resp.text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            ids = []
            for entry in root.findall("atom:entry", ns):
                id_elem = entry.find("atom:id", ns)
                if id_elem is not None and id_elem.text:
                    ids.append(id_elem.text.strip())
            return ids
    except Exception as exc:  # noqa: BLE001
        logger.warning("arXiv query failed: %s", exc)
        return []


async def _queue_auto_fights(evaluated_arxiv_ids: list[str]) -> list[str]:
    """
    Arena auto-fight trigger (ADR-011).
    For each newly evaluated paper, check cosine similarity against Ground.
    If score ≥ τ (0.65), queue a Ground fight in the background.
    Returns list of fight_ids queued.
    """
    if not evaluated_arxiv_ids:
        return []

    try:
        import uuid

        from thesisclaw.arena.docs import load_fighter_doc
        from thesisclaw.arena.graph import run_fight
        from thesisclaw.arena.memory import upsert_fight
        from thesisclaw.arena.models import Fighter, FighterKind, FightRecord, FightState
        from thesisclaw.arena.select import should_auto_fight
        from thesisclaw.tools.fetch import fetch_paper_text
    except Exception as exc:  # noqa: BLE001
        logger.debug("Arena module not ready for auto-fight: %s", exc)
        return []

    ground_doc = await load_fighter_doc("ground", "ground")
    fight_ids: list[str] = []

    for arxiv_id in evaluated_arxiv_ids:
        try:
            paper = await fetch_paper_text(arxiv_id)
            paper_text = f"{paper.title} {paper.abstract}"
            if should_auto_fight(paper_text, ground_doc["text"]):
                fight_id = f"auto-{uuid.uuid4().hex[:8]}"
                fa = Fighter(kind=FighterKind.GROUND, doc_id="ground")
                fb = Fighter(kind=FighterKind.PAPER, doc_id=arxiv_id)
                record = FightRecord(fight_id=fight_id, fighter_a=fa, fighter_b=fb, state=FightState.QUEUED)
                upsert_fight(record)
                asyncio.create_task(run_fight(fa, fb, fight_id=fight_id))
                logger.info("Auto-fight queued: %s vs %s (fight_id=%s)", "ground", arxiv_id, fight_id)
                fight_ids.append(fight_id)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Auto-fight check failed for %s: %s", arxiv_id, exc)

    return fight_ids


async def run_daily_scan(max_papers: int = 5, query: str = "ASR edge quantization") -> BriefingResult:
    """Run daily literature scan, compile findings, and queue auto-fights for high-similarity papers."""
    orch = ThesisOrchestrator()
    paper_ids = await query_arxiv_rss_or_api(query, max_results=max_papers)

    # Filter out already processed papers
    to_evaluate = [pid for pid in paper_ids if not orch.is_paper_processed(pid)]

    logger.info("Discovered %d papers, %d new to process.", len(paper_ids), len(to_evaluate))
    briefing = await orch.run_batch_evaluation(to_evaluate)

    # Auto-fight trigger: queue Ground fights for high-similarity papers
    auto_fights = await _queue_auto_fights(to_evaluate)
    if auto_fights:
        logger.info("Auto-fights queued: %s", auto_fights)

    return briefing


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ThesisClaw literature scan")
    parser.add_argument("--max-papers", type=int, default=5, help="Max papers to evaluate")
    parser.add_argument("--query", type=str, default="edge ASR quantization", help="arXiv query")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    briefing = asyncio.run(run_daily_scan(max_papers=args.max_papers, query=args.query))
    print("\n" + briefing.telegram_briefing)


if __name__ == "__main__":
    main()
