"""
ThesisClaw Paper Arena — Pydantic models.

All arena data flows through these models. Zero LLM calls here.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator

# ── Enums ────────────────────────────────────────────────────────────────────


class FighterKind(str, Enum):
    GROUND = "ground"  # research/agent.md + project brief + draft files
    PAPER = "paper"    # arXiv paper full text


class Stance(str, Enum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    DIFFERENT_CONDITIONS = "DIFFERENT_CONDITIONS"
    NOT_COVERED = "NOT_COVERED"


class FightState(str, Enum):
    QUEUED = "queued"
    SETUP = "setup"
    OPENINGS = "openings"
    CROSS_EXAM = "cross_exam"
    FOLLOWUPS = "followups"
    COMMON_GROUND = "common_ground"
    VERIFYING = "verifying"
    JUDGING = "judging"
    DONE = "done"
    FAILED = "failed"
    REJECTED = "rejected"


# ── Core models ───────────────────────────────────────────────────────────────


class Fighter(BaseModel):
    """One participant in a fight."""

    kind: FighterKind
    doc_id: str  # arxiv_id OR "ground"


class FightCard(BaseModel):
    """Moderator output: the structured topic + sharpest focal questions."""

    fight_id: str
    topic: str = Field(description="2-sentence framing of what is at stake")
    focal_questions: list[str] = Field(
        default_factory=list,
        description="3–5 sharp conflict questions the fighters must address",
    )

    @model_validator(mode="after")
    def _cap_questions(self) -> FightCard:
        self.focal_questions = self.focal_questions[:5]
        return self


class MemoryEntry(BaseModel):
    """
    One unit of fight memory.
    Written by fighters, moderator, or judge.
    Indexed by content hash so resume is safe (no duplicates).
    """

    entry_id: str = ""             # SHA-256[:16] of canonical fields — set by memory.write_entry
    fight_id: str
    round: int
    author: str                    # "fighter_a" | "fighter_b" | "moderator" | "judge"
    entry_type: str                # "claim" | "concession" | "idea" | "verdict" | "followup"
    text: str
    quote: str = ""                # verbatim quote from the fighter's own document
    doc_id: str
    section: str = ""
    char_position: int = -1
    conditions: str = ""           # e.g. "only for >100M param models"
    stance: Stance = Stance.NOT_COVERED
    refs: list[str] = Field(default_factory=list)  # entry_ids cited
    verified: bool = False
    near_exact: bool = False       # True when quote passes 0.95 fuzzy threshold but not exact
    verification_note: str = ""

    def canonical_key(self) -> str:
        """Deterministic string for deduplication hashing."""
        return f"{self.fight_id}|{self.round}|{self.author}|{self.text}|{self.quote}"


class FighterTurn(BaseModel):
    """One fighter's output for a single round."""

    fight_id: str
    round: int
    fighter: str                   # "fighter_a" | "fighter_b"
    entries: list[MemoryEntry] = Field(default_factory=list)


class Verdict(BaseModel):
    """Judge output (produced twice with sides swapped, then merged)."""

    fight_id: str
    winner: str | None = None      # "fighter_a" | "fighter_b" | "draw"
    claim_verdicts: dict[str, str] = Field(
        default_factory=dict,
        description="entry_id → 'upheld' | 'struck' | 'incomparable'",
    )
    scores: dict[str, float] = Field(
        default_factory=dict,
        description="fighter → composite 1–5 score",
    )
    ranked_ideas: list[str] = Field(
        default_factory=list,
        description="entry_ids (idea type) ordered by novelty descending",
    )
    swap_run: int = 1              # 1 = sides as-is, 2 = sides swapped
    judge_citations: list[str] = Field(default_factory=list)
    dimension_scores: dict[str, dict[str, float]] = Field(
        default_factory=dict,
        description="dimension → {fighter: score} for evidence/relevance/novelty/conditions",
    )


class MergedVerdict(BaseModel):
    """Combined output after both judge runs (swap_run=1 and swap_run=2)."""

    fight_id: str
    winner: str | None = None
    swap_agreement: float = 0.0    # fraction of claim_verdicts that agree across both runs
    final_scores: dict[str, float] = Field(default_factory=dict)
    ranked_ideas: list[str] = Field(default_factory=list)
    all_entries_verified_ratio: float = 0.0
    struck_count: int = 0
    upheld_count: int = 0


class FightRecord(BaseModel):
    """Top-level fight metadata stored in the SQLite fight index."""

    fight_id: str
    fighter_a: Fighter
    fighter_b: Fighter
    state: FightState = FightState.QUEUED
    merged_verdict: MergedVerdict | None = None
    elo_delta_a: float = 0.0       # Elo change for fighter_a after this fight
    elo_delta_b: float = 0.0
    started_at: str = ""
    finished_at: str = ""
    error: str = ""


class EloEntry(BaseModel):
    """Elo leaderboard entry for a paper or Ground."""

    doc_id: str
    rating: float = 1200.0         # standard starting Elo
    wins: int = 0
    losses: int = 0
    draws: int = 0
    fights: int = 0
