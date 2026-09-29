from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any

from thesisclaw.agent.subagents import (
    critic_subagent,
    paper_reader_subagent,
    pathfinder_subagent,
    publisher_subagent,
    thesis_matcher_subagent,
)
from thesisclaw.config.settings import settings
from thesisclaw.models.paper import (
    BriefingResult,
    CriticResult,
    PaperContent,
    PaperVerdict,
    PathfinderResult,
    VerdictEnum,
)

logger = logging.getLogger(__name__)


class ThesisOrchestrator:
    """Coordinates Deep Agents subagents for literature monitoring and checkpointing."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path or f"{settings.checkpoints_dir}/thesisclaw.sqlite3")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite database for checkpoints and paper evaluation logs."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_papers (
                    arxiv_id TEXT PRIMARY KEY,
                    title TEXT,
                    verdict TEXT,
                    confidence TEXT,
                    reason TEXT,
                    backed_ratio REAL,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pending_approvals (
                    job_id TEXT PRIMARY KEY,
                    arxiv_id TEXT,
                    experiment TEXT,
                    code_change_desc TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def load_thesis_claim(self) -> str:
        """Read central thesis claim from research/agent.md or fallback default."""
        mem_path = settings.resolve_memory_path()
        if mem_path.exists():
            return mem_path.read_text(encoding="utf-8")
        return (
            "Real-Time Privacy-Preserving Speech Transcription on Raspberry Pi 5 using "
            "Moonshine Tiny with INT4/INT8 quantization under Podman isolation (RTF <= 0.5, WER <= 6%)."
        )

    def is_paper_processed(self, arxiv_id: str) -> bool:
        """Check if paper has already been evaluated."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM processed_papers WHERE arxiv_id = ?", (arxiv_id,))
            return cur.fetchone() is not None

    def record_processed_paper(
        self,
        paper: PaperContent,
        verdict: PaperVerdict,
        critic: CriticResult,
    ) -> None:
        """Persist paper evaluation checkpoint to SQLite."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO processed_papers 
                (arxiv_id, title, verdict, confidence, reason, backed_ratio)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    paper.arxiv_id,
                    paper.title,
                    verdict.verdict.value,
                    verdict.confidence,
                    verdict.reason,
                    critic.backed_ratio,
                ),
            )

    async def evaluate_single_paper(self, url_or_id: str) -> dict[str, Any]:
        """Run full evaluation pipeline for a single paper."""
        # Step 1: Read paper
        paper = await paper_reader_subagent(url_or_id)

        # Step 2: Match thesis
        thesis_claim = self.load_thesis_claim()
        verdict = thesis_matcher_subagent(paper, thesis_claim)

        # Step 3: Critic verification
        critic = critic_subagent(paper, paper.claims)

        # Step 4: Pathfinder experiment proposal (if relevant and passed critic)
        pathfinder: PathfinderResult | None = None
        if critic.is_passed and verdict.verdict in (VerdictEnum.SUPPORT, VerdictEnum.EXTEND, VerdictEnum.THREATEN):
            pathfinder = pathfinder_subagent(paper, verdict)
            # Record approval requirement if code change is suggested
            if pathfinder.propose_code_change:
                self._record_pending_approval(paper.arxiv_id, pathfinder)

        # Step 5: Checkpoint to SQLite
        self.record_processed_paper(paper, verdict, critic)

        return {
            "paper": paper,
            "verdict": verdict,
            "critic": critic,
            "pathfinder": pathfinder,
        }

    def _record_pending_approval(self, arxiv_id: str, pathfinder: PathfinderResult) -> None:
        """Record an experiment that requires human approval via web UI."""
        import uuid

        job_id = f"appr-{uuid.uuid4().hex[:8]}"
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO pending_approvals (job_id, arxiv_id, experiment, code_change_desc, status)
                VALUES (?, ?, ?, ?, 'pending')
                """,
                (
                    job_id,
                    arxiv_id,
                    pathfinder.next_experiment,
                    pathfinder.code_change_description or "",
                ),
            )

    async def run_batch_evaluation(self, urls: list[str]) -> BriefingResult:
        """Run batch scan across multiple papers and compile a briefing."""
        papers = []
        verdicts = []

        for url in urls:
            try:
                res = await self.evaluate_single_paper(url)
                papers.append(res["paper"])
                verdicts.append(res["verdict"])
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to evaluate %s: %s", url, exc)

        return publisher_subagent(papers, verdicts)
