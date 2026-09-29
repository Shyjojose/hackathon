#!/usr/bin/env python3
"""
ThesisClaw Evaluation Runner

Usage:
    uv run python evals/run_eval.py [--model MODEL] [--full]

Flags:
    --full    Run full analysis on all 30 papers (expensive). Default: quick
              relevance check on all 30, full analysis on 5.
    --model   Override the default model for this eval run.

Outputs:
    - precision@10: fraction of top-10 papers correctly labelled by the agent
    - confusion matrix: verdicts vs. golden labels
    - per-paper breakdown: arxiv_id, golden, predicted, correct
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

GOLDEN_PATH = Path(__file__).parent / "golden" / "papers.jsonl"


def load_golden() -> list[dict]:
    papers = []
    with GOLDEN_PATH.open() as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                papers.append(json.loads(line))
    return papers


def run_quick_check(papers: list[dict], model: str | None) -> dict:
    """Quick relevance check: is the paper relevant (non-irrelevant) or not?"""
    # TODO: call thesis-matcher subagent for each paper
    raise NotImplementedError("Quick check not yet implemented — build worker first.")


def run_full_analysis(papers: list[dict], model: str | None) -> dict:
    """Full analysis: support / extend / threaten / irrelevant verdict."""
    # TODO: run the full orchestrator pipeline for each paper
    raise NotImplementedError("Full analysis not yet implemented — build worker first.")


def precision_at_k(results: list[dict], k: int = 10) -> float:
    """Fraction of top-k results where predicted == golden."""
    top_k = results[:k]
    if not top_k:
        return 0.0
    correct = sum(1 for r in top_k if r["predicted"] == r["golden"])
    return correct / len(top_k)


def main() -> None:
    parser = argparse.ArgumentParser(description="ThesisClaw evaluation runner")
    parser.add_argument("--full", action="store_true", help="Run full analysis on all papers")
    parser.add_argument("--model", type=str, default=None, help="Override model name")
    args = parser.parse_args()

    papers = load_golden()
    if not papers:
        print("No papers in golden set. Add entries to evals/golden/papers.jsonl first.")
        sys.exit(1)

    print(f"Loaded {len(papers)} golden papers.")

    if args.full:
        results = run_full_analysis(papers, args.model)
    else:
        results = run_quick_check(papers, args.model)

    p10 = precision_at_k(results.get("per_paper", []))
    print(f"precision@10: {p10:.2%}")


if __name__ == "__main__":
    main()
