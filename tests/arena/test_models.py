"""
Unit tests for arena/models.py — Pydantic models.
No network calls, no LLM calls, no file I/O.
"""
from __future__ import annotations

from thesisclaw.arena.models import (
    EloEntry,
    FightCard,
    Fighter,
    FighterKind,
    FightRecord,
    FightState,
    MemoryEntry,
    MergedVerdict,
    Stance,
    Verdict,
)

# ── Fighter ───────────────────────────────────────────────────────────────────


def test_fighter_ground():
    f = Fighter(kind=FighterKind.GROUND, doc_id="ground")
    assert f.kind == FighterKind.GROUND
    assert f.doc_id == "ground"


def test_fighter_paper():
    f = Fighter(kind=FighterKind.PAPER, doc_id="2301.12345")
    assert f.kind == FighterKind.PAPER


# ── FightCard ─────────────────────────────────────────────────────────────────


def test_fight_card_caps_questions():
    card = FightCard(
        fight_id="f1",
        topic="Test topic",
        focal_questions=["q1", "q2", "q3", "q4", "q5", "q6"],  # 6 — should cap at 5
    )
    assert len(card.focal_questions) == 5


def test_fight_card_empty_questions():
    card = FightCard(fight_id="f1", topic="Test")
    assert card.focal_questions == []


# ── MemoryEntry ───────────────────────────────────────────────────────────────


def test_memory_entry_canonical_key():
    e = MemoryEntry(
        fight_id="f1", round=1, author="fighter_a", entry_type="claim",
        text="INT4 reduces memory", quote="INT4 quantization halves peak RAM",
        doc_id="2301.12345",
    )
    key = e.canonical_key()
    assert "f1" in key
    assert "fighter_a" in key
    assert "INT4 reduces memory" in key


def test_memory_entry_defaults():
    e = MemoryEntry(
        fight_id="f1", round=0, author="moderator",
        entry_type="claim", text="Topic set", doc_id="moderator",
    )
    assert e.stance == Stance.NOT_COVERED
    assert e.verified is False
    assert e.near_exact is False
    assert e.char_position == -1


def test_memory_entry_all_stances():
    for stance in Stance:
        e = MemoryEntry(
            fight_id="f1", round=1, author="fighter_a", entry_type="claim",
            text="claim", doc_id="doc", stance=stance,
        )
        assert e.stance == stance


# ── Verdict ───────────────────────────────────────────────────────────────────


def test_verdict_structure():
    v = Verdict(
        fight_id="f1",
        winner="fighter_a",
        claim_verdicts={"abc123": "upheld", "def456": "struck"},
        scores={"fighter_a": 4.5, "fighter_b": 3.2},
        ranked_ideas=["idea001"],
        swap_run=1,
        judge_citations=["abc123"],
    )
    assert v.winner == "fighter_a"
    assert v.claim_verdicts["abc123"] == "upheld"
    assert v.scores["fighter_a"] == 4.5


def test_merged_verdict_fields():
    mv = MergedVerdict(
        fight_id="f1",
        winner="draw",
        swap_agreement=0.85,
        final_scores={"fighter_a": 3.5, "fighter_b": 3.7},
        ranked_ideas=["idea001", "idea002"],
        all_entries_verified_ratio=0.92,
        struck_count=2,
        upheld_count=5,
    )
    assert mv.swap_agreement == 0.85
    assert mv.all_entries_verified_ratio == 0.92


# ── Elo ───────────────────────────────────────────────────────────────────────


def test_elo_entry_defaults():
    e = EloEntry(doc_id="ground")
    assert e.rating == 1200.0
    assert e.wins == 0
    assert e.fights == 0


# ── FightRecord ───────────────────────────────────────────────────────────────


def test_fight_record_states():
    fa = Fighter(kind=FighterKind.GROUND, doc_id="ground")
    fb = Fighter(kind=FighterKind.PAPER, doc_id="2301.12345")
    record = FightRecord(fight_id="f1", fighter_a=fa, fighter_b=fb)
    assert record.state == FightState.QUEUED
    assert record.merged_verdict is None
