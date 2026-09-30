"""
ThesisClaw Paper Arena — Opponent Selection.

Ranks papers by cosine similarity against a target document (Ground or a given paper).
Reuses thesisclaw.tools.embed.embed_text and cosine_similarity — no new dependencies.

τ (default 0.65) controls the auto-fight threshold:
    - Any new paper with score ≥ τ against Ground is eligible for an automatic Ground fight.
    - The scan.py job calls should_auto_fight() after each new paper is ingested.

Design note:
    Embeddings are computed lazily and cached in-memory per session (not persisted).
    For a hackathon run with a few hundred papers, in-memory is sufficient.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import NamedTuple

from thesisclaw.tools.embed import cosine_similarity, embed_text

TAU_DEFAULT: float = 0.65
SIMILARITY_MIN_GATE: float = 0.35

# In-memory embedding cache: {text_hash: embedding}
_embedding_cache: dict[int, list[float]] = {}


def _cached_embed(text: str) -> list[float]:
    """Embed text with a simple in-process cache to avoid redundant API calls."""
    key = hash(text)
    if key not in _embedding_cache:
        _embedding_cache[key] = embed_text(text)
    return _embedding_cache[key]


def compute_similarity(text_a: str, text_b: str) -> float:
    """Compute cosine similarity between two texts using cached embeddings."""
    if not text_a or not text_b:
        return 0.0
    vec_a = _cached_embed(text_a[:8000])
    vec_b = _cached_embed(text_b[:8000])
    return cosine_similarity(vec_a, vec_b)


def is_fight_eligible(
    text_a: str,
    text_b: str,
    threshold: float = SIMILARITY_MIN_GATE,
) -> tuple[bool, float]:
    """
    Check if two documents meet the minimum similarity threshold for a meaningful fight.
    Returns (is_eligible, similarity_score).
    """
    score = compute_similarity(text_a, text_b)
    return score >= threshold, score


class RankedOpponent(NamedTuple):
    doc_id: str
    score: float
    above_tau: bool


def rank_opponents(
    target_text: str,
    candidates: list[tuple[str, str]],  # [(doc_id, text), ...]
    tau: float = TAU_DEFAULT,
) -> list[RankedOpponent]:
    """
    Rank candidate documents by cosine similarity to the target text.

    Args:
        target_text:  The full text of the reference document (Ground or a paper).
        candidates:   List of (doc_id, text) pairs to rank against target.
        tau:          Threshold — candidates with score ≥ tau are auto-fight eligible.

    Returns:
        List of RankedOpponent, sorted by score descending.
    """
    if not candidates:
        return []

    target_emb = _cached_embed(target_text)
    ranked: list[RankedOpponent] = []

    for doc_id, text in candidates:
        if not text or not text.strip():
            continue
        try:
            cand_emb = _cached_embed(text)
            score = cosine_similarity(target_emb, cand_emb)
        except Exception:  # noqa: BLE001
            score = 0.0
        ranked.append(RankedOpponent(doc_id=doc_id, score=score, above_tau=score >= tau))

    ranked.sort(key=lambda r: r.score, reverse=True)
    return ranked


def top_opponent(
    target_text: str,
    candidates: list[tuple[str, str]],
    tau: float = TAU_DEFAULT,
) -> RankedOpponent | None:
    """Return the highest-scoring opponent above τ, or None."""
    ranked = rank_opponents(target_text, candidates, tau=tau)
    for r in ranked:
        if r.above_tau:
            return r
    return None


def should_auto_fight(
    paper_text: str,
    ground_text: str,
    tau: float = TAU_DEFAULT,
) -> bool:
    """
    Determine whether a newly ingested paper should trigger an automatic Ground fight.
    Returns True if cosine similarity(paper, ground) ≥ τ.
    """
    try:
        paper_emb = _cached_embed(paper_text)
        ground_emb = _cached_embed(ground_text)
        score = cosine_similarity(paper_emb, ground_emb)
        return score >= tau
    except Exception:  # noqa: BLE001
        return False


def get_candidates_from_db(
    db_path: str | Path,
    *,
    exclude_doc_ids: set[str] | None = None,
    limit: int = 200,
) -> list[tuple[str, str]]:
    """
    Load paper arxiv_ids and abstracts from the existing ThesisClaw SQLite checkpoint
    to use as opponent candidates.  Reuses the existing processed_papers table.

    Args:
        db_path:          Path to thesisclaw.sqlite3
        exclude_doc_ids:  doc_ids to skip (e.g., the target itself, already-fought papers)
        limit:            Max candidates to return

    Returns:
        List of (arxiv_id, title + reason text) suitable for embedding.
    """
    exclude = exclude_doc_ids or set()
    try:
        with sqlite3.connect(db_path) as conn:
            rows = conn.execute(
                "SELECT arxiv_id, title, reason FROM processed_papers ORDER BY processed_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    except Exception:  # noqa: BLE001
        return []

    candidates = []
    for arxiv_id, title, reason in rows:
        if arxiv_id in exclude:
            continue
        text = f"{title or ''} {reason or ''}".strip()
        if text:
            candidates.append((arxiv_id, text))
    return candidates
