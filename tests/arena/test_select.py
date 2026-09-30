"""
Unit tests for arena/select.py — opponent selection and ranking.
Uses mock embeddings to test ranking and threshold logic deterministically.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from thesisclaw.arena.select import (
    get_candidates_from_db,
    rank_opponents,
    should_auto_fight,
    top_opponent,
)


def _mock_semantic_embed(monkeypatch):
    """
    Mock _cached_embed in select.py so that texts containing 'ASR' or 'quantization'
    produce vectors close to the target, and unrelated texts produce orthogonal vectors.
    """
    def fake_embed(text: str) -> list[float]:
        t = text.lower()
        if "speech" in t or "asr" in t or "quantiz" in t:
            return [1.0, 0.2]
        return [0.0, 1.0]

    monkeypatch.setattr("thesisclaw.arena.select._cached_embed", fake_embed)


def test_rank_opponents_empty():
    assert rank_opponents("target text", []) == []


def test_rank_opponents_sorting(monkeypatch):
    _mock_semantic_embed(monkeypatch)
    target = "Speech recognition on ARM Cortex CPUs with low latency"
    candidates = [
        ("cand_unrelated", "Quantum computing algorithms for cryptography"),
        ("cand_relevant", "Low-latency speech recognition on ARM Cortex-A76"),
    ]
    ranked = rank_opponents(target, candidates, tau=0.3)
    assert len(ranked) == 2
    # The relevant paper should have higher cosine similarity
    assert ranked[0].doc_id == "cand_relevant"
    assert ranked[0].score > ranked[1].score


def test_top_opponent_found(monkeypatch):
    _mock_semantic_embed(monkeypatch)
    target = "Symmetric INT4 quantization for Moonshine ASR"
    candidates = [
        ("cand_1", "Symmetric INT4 quantization for Moonshine ASR model"),
        ("cand_2", "Plant biology and photosynthesis efficiency"),
    ]
    top = top_opponent(target, candidates, tau=0.5)
    assert top is not None
    assert top.doc_id == "cand_1"
    assert top.above_tau is True


def test_top_opponent_none_when_below_tau(monkeypatch):
    _mock_semantic_embed(monkeypatch)
    target = "Speech recognition on Edge AI embedded hardware"
    candidates = [
        ("cand_remote", "Galactic rotation curves in deep space astrophysics"),
    ]
    top = top_opponent(target, candidates, tau=0.99)
    assert top is None


def test_should_auto_fight(monkeypatch):
    _mock_semantic_embed(monkeypatch)
    paper = "Real-time edge speech recognition INT4 quantization on ARM"
    ground = "Real-time edge speech recognition INT4 quantization on ARM Cortex"
    assert should_auto_fight(paper, ground, tau=0.5) is True
    assert should_auto_fight("Completely unrelated deep sea biology", ground, tau=0.5) is False


def test_get_candidates_from_db(tmp_path: Path):
    db_file = tmp_path / "thesisclaw.sqlite3"
    with sqlite3.connect(db_file) as conn:
        conn.execute(
            """
            CREATE TABLE processed_papers (
                arxiv_id TEXT PRIMARY KEY,
                title TEXT,
                reason TEXT,
                processed_at TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO processed_papers VALUES (?, ?, ?, ?)",
            ("2608.001", "Edge ASR", "quantization study", "2026-09-30T10:00:00Z"),
        )
        conn.execute(
            "INSERT INTO processed_papers VALUES (?, ?, ?, ?)",
            ("2608.002", "Vision Transformer", "image classification", "2026-09-30T10:05:00Z"),
        )
        conn.commit()

    candidates = get_candidates_from_db(db_file, exclude_doc_ids={"2608.001"})
    assert len(candidates) == 1
    assert candidates[0][0] == "2608.002"
    assert "Vision Transformer" in candidates[0][1]


def test_get_candidates_from_nonexistent_db(tmp_path: Path):
    candidates = get_candidates_from_db(tmp_path / "missing.db")
    assert candidates == []


def test_compute_similarity_empty():
    from thesisclaw.arena.select import compute_similarity
    assert compute_similarity("", "some text") == 0.0
    assert compute_similarity("some text", "") == 0.0


def test_compute_similarity_and_eligibility(monkeypatch):
    _mock_semantic_embed(monkeypatch)
    from thesisclaw.arena.select import SIMILARITY_MIN_GATE, compute_similarity, is_fight_eligible

    text_asr = "Speech recognition on ARM Cortex with INT4 quantization"
    text_relevant = "Low latency ASR inference on embedded edge"
    text_unrelated = "Galactic rotation in astrophysics cosmology"

    # Similar topics should have high similarity
    sim_high = compute_similarity(text_asr, text_relevant)
    assert sim_high > 0.9

    # Unrelated topics should have low similarity
    sim_low = compute_similarity(text_asr, text_unrelated)
    assert sim_low < SIMILARITY_MIN_GATE

    # Test is_fight_eligible gate
    eligible_high, score_high = is_fight_eligible(text_asr, text_relevant)
    assert eligible_high is True
    assert score_high >= SIMILARITY_MIN_GATE

    eligible_low, score_low = is_fight_eligible(text_asr, text_unrelated)
    assert eligible_low is False
    assert score_low < SIMILARITY_MIN_GATE
