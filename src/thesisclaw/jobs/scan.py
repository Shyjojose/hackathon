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


async def run_daily_scan(max_papers: int = 5, query: str = "ASR edge quantization") -> BriefingResult:
    """Run daily literature scan and compile findings."""
    orch = ThesisOrchestrator()
    paper_ids = await query_arxiv_rss_or_api(query, max_results=max_papers)

    # Filter out already processed papers
    to_evaluate = [pid for pid in paper_ids if not orch.is_paper_processed(pid)]

    logger.info("Discovered %d papers, %d new to process.", len(paper_ids), len(to_evaluate))
    briefing = await orch.run_batch_evaluation(to_evaluate)
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
