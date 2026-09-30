"""
Unit tests for arena/memory.py — shared fight memory store.
Uses a tmp_path fixture to isolate from real research/fights/.
No network, no LLM.
"""
from __future__ import annotations

import json

from thesisclaw.arena.models import (
    Fighter,
    FighterKind,
    FightRecord,
    FightState,
    MemoryEntry,
    Stance,
)

# ── Helpers / fixtures ────────────────────────────────────────────────────────


def _patch_fights_dir(monkeypatch, tmp_path):
    """Redirect memory storage to a temp directory."""
    import thesisclaw.arena.memory as mem_mod
    monkeypatch.setattr(mem_mod, "FIGHTS_DIR", tmp_path / "fights")
    monkeypatch.setattr(mem_mod, "ARENA_DB", tmp_path / "fights" / "arena.db")
    monkeypatch.setattr(mem_mod, "CLAIMS_LOG", tmp_path / "fights" / "claims.jsonl")
    return mem_mod


def _mk_entry(fight_id: str, round_: int, author: str, text: str, quote: str = "") -> MemoryEntry:
    return MemoryEntry(
        fight_id=fight_id, round=round_, author=author, entry_type="claim",
        text=text, quote=quote, doc_id="2301.00001", stance=Stance.SUPPORTS,
    )


# ── write_entry ───────────────────────────────────────────────────────────────


def test_write_entry_creates_file(monkeypatch, tmp_path):
    mem = _patch_fights_dir(monkeypatch, tmp_path)
    e = _mk_entry("f1", 1, "fighter_a", "INT4 reduces memory", "INT4 reduces peak RAM")
    saved = mem.write_entry(e)
    assert saved.entry_id
    path = tmp_path / "fights" / "f1" / "memory.jsonl"
    assert path.exists()
    lines = [json.loads(l) for l in path.read_text().splitlines() if l]
    assert len(lines) == 1
    assert lines[0]["entry_id"] == saved.entry_id


def test_write_entry_idempotent(monkeypatch, tmp_path):
    """Writing the same entry twice must not create duplicates."""
    mem = _patch_fights_dir(monkeypatch, tmp_path)
    e = _mk_entry("f1", 1, "fighter_a", "Same claim", "Same quote")
    mem.write_entry(e)
    mem.write_entry(e)  # second write — should be a no-op
    path = tmp_path / "fights" / "f1" / "memory.jsonl"
    lines = [l for l in path.read_text().splitlines() if l]
    assert len(lines) == 1


def test_write_entry_different_entries(monkeypatch, tmp_path):
    mem = _patch_fights_dir(monkeypatch, tmp_path)
    e1 = _mk_entry("f1", 1, "fighter_a", "Claim A", "Quote A")
    e2 = _mk_entry("f1", 1, "fighter_b", "Claim B", "Quote B")
    mem.write_entry(e1)
    mem.write_entry(e2)
    path = tmp_path / "fights" / "f1" / "memory.jsonl"
    lines = [l for l in path.read_text().splitlines() if l]
    assert len(lines) == 2


def test_write_entry_sets_entry_id(monkeypatch, tmp_path):
    mem = _patch_fights_dir(monkeypatch, tmp_path)
    e = _mk_entry("f1", 1, "fighter_a", "claim", "quote")
    assert e.entry_id == ""  # not yet set
    saved = mem.write_entry(e)
    assert saved.entry_id != ""
    assert len(saved.entry_id) == 16  # SHA-256[:16]


# ── read_entries ──────────────────────────────────────────────────────────────


def test_read_entries_empty(monkeypatch, tmp_path):
    mem = _patch_fights_dir(monkeypatch, tmp_path)
    result = mem.read_entries("nonexistent_fight")
    assert result == []


def test_read_entries_filtered_by_author(monkeypatch, tmp_path):
    mem = _patch_fights_dir(monkeypatch, tmp_path)
    mem.write_entry(_mk_entry("f1", 1, "fighter_a", "A claim"))
    mem.write_entry(_mk_entry("f1", 1, "fighter_b", "B claim"))
    mem.write_entry(_mk_entry("f1", 2, "fighter_a", "A claim 2"))

    a_entries = mem.read_entries("f1", author="fighter_a")
    assert len(a_entries) == 2
    assert all(e.author == "fighter_a" for e in a_entries)


def test_read_entries_filtered_by_round(monkeypatch, tmp_path):
    mem = _patch_fights_dir(monkeypatch, tmp_path)
    mem.write_entry(_mk_entry("f1", 1, "fighter_a", "R1 claim"))
    mem.write_entry(_mk_entry("f1", 2, "fighter_a", "R2 claim"))
    r1 = mem.read_entries("f1", round_=1)
    assert len(r1) == 1
    assert r1[0].round == 1


def test_read_entries_verified_only(monkeypatch, tmp_path):
    mem = _patch_fights_dir(monkeypatch, tmp_path)
    e1 = _mk_entry("f1", 1, "fighter_a", "verified", "q1")
    e1.verified = True
    e2 = _mk_entry("f1", 1, "fighter_b", "unverified", "q2")
    mem.write_entry(e1)
    mem.write_entry(e2)
    result = mem.read_entries("f1", verified_only=True)
    assert len(result) == 1
    assert result[0].verified is True


# ── Resume safety (deduplication after kill) ──────────────────────────────────


def test_resume_no_duplicates(monkeypatch, tmp_path):
    """
    Simulate a fight killed mid-write and resumed.
    Re-writing the same entries should produce no duplicates.
    """
    mem = _patch_fights_dir(monkeypatch, tmp_path)
    entries = [_mk_entry("f1", 1, "fighter_a", f"Claim {i}", f"Quote {i}") for i in range(5)]
    for e in entries:
        mem.write_entry(e)

    # "Kill" and "resume" — re-write all entries
    for e in entries:
        mem.write_entry(e)

    path = tmp_path / "fights" / "f1" / "memory.jsonl"
    lines = [l for l in path.read_text().splitlines() if l]
    assert len(lines) == 5


# ── Elo leaderboard ───────────────────────────────────────────────────────────


def test_elo_update_win(monkeypatch, tmp_path):
    mem = _patch_fights_dir(monkeypatch, tmp_path)
    new_r_a, new_r_b = mem.update_elo("ground", "2301.00001", "a")
    # Winner should gain rating, loser should lose
    assert new_r_a > 1200.0
    assert new_r_b < 1200.0


def test_elo_update_draw(monkeypatch, tmp_path):
    mem = _patch_fights_dir(monkeypatch, tmp_path)
    new_r_a, new_r_b = mem.update_elo("ground", "2301.00001", "draw")
    # Both close to 1200 (slight symmetric adjustment)
    assert abs(new_r_a - new_r_b) < 5.0


def test_elo_update_two_fights(monkeypatch, tmp_path):
    """Second fight should update from new starting rating, not 1200."""
    mem = _patch_fights_dir(monkeypatch, tmp_path)
    _r_a1, _r_b1 = mem.update_elo("ground", "paper_1", "a")  # ground wins fight 1
    r_a2, _r_b2 = mem.update_elo("ground", "paper_2", "b")  # ground loses fight 2
    # After winning then losing, ground should be close to 1200
    assert 1190 < r_a2 < 1230


def test_leaderboard_order(monkeypatch, tmp_path):
    mem = _patch_fights_dir(monkeypatch, tmp_path)
    mem.update_elo("ground", "paper_1", "a")   # ground wins
    mem.update_elo("ground", "paper_2", "a")   # ground wins again
    lb = mem.get_leaderboard()
    # ground should be at the top
    assert lb[0].doc_id == "ground"
    assert lb[0].rating > lb[1].rating


# ── FightRecord CRUD ──────────────────────────────────────────────────────────


def test_upsert_and_get_fight(monkeypatch, tmp_path):
    mem = _patch_fights_dir(monkeypatch, tmp_path)
    fa = Fighter(kind=FighterKind.GROUND, doc_id="ground")
    fb = Fighter(kind=FighterKind.PAPER, doc_id="2301.00001")
    record = FightRecord(fight_id="f1", fighter_a=fa, fighter_b=fb, state=FightState.QUEUED)
    mem.upsert_fight(record)
    retrieved = mem.get_fight("f1")
    assert retrieved is not None
    assert retrieved.fight_id == "f1"
    assert retrieved.state == FightState.QUEUED


def test_upsert_updates_state(monkeypatch, tmp_path):
    mem = _patch_fights_dir(monkeypatch, tmp_path)
    fa = Fighter(kind=FighterKind.GROUND, doc_id="ground")
    fb = Fighter(kind=FighterKind.PAPER, doc_id="2301.00001")
    record = FightRecord(fight_id="f1", fighter_a=fa, fighter_b=fb, state=FightState.QUEUED)
    mem.upsert_fight(record)
    record.state = FightState.DONE
    mem.upsert_fight(record)
    retrieved = mem.get_fight("f1")
    assert retrieved.state == FightState.DONE


def test_get_nonexistent_fight(monkeypatch, tmp_path):
    mem = _patch_fights_dir(monkeypatch, tmp_path)
    assert mem.get_fight("does_not_exist") is None
