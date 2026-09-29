from __future__ import annotations

import argparse
import asyncio
import logging

from thesisclaw.agent.orchestrator import ThesisOrchestrator
from thesisclaw.models.paper import BriefingResult

logger = logging.getLogger(__name__)

# Default curated list of notable edge ASR & quantization papers for hackathon demo
DEMO_PAPER_IDS = [
    "2404.12345",  # Simulated/sample ASR benchmark
    "2401.12345",  # Quantization on ARM Cortex
    "2312.12345",  # Sliding window attention
]


async def run_backfill(paper_ids: list[str] | None = None) -> BriefingResult:
    """Run historical backfill over targeted paper IDs to populate demo memory."""
    orch = ThesisOrchestrator()
    targets = paper_ids or DEMO_PAPER_IDS
    logger.info("Starting backfill for %d papers...", len(targets))
    briefing = await orch.run_batch_evaluation(targets)
    return briefing


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ThesisClaw historical backfill")
    parser.add_argument("ids", nargs="*", help="Optional specific arXiv IDs to backfill")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    briefing = asyncio.run(run_backfill(args.ids if args.ids else None))
    print("\n=== Backfill Completed ===")
    print(briefing.telegram_briefing)


if __name__ == "__main__":
    main()
