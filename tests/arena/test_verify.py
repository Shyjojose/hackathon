"""
Unit tests for arena/verify.py — quote verifier.
No network, no LLM, no file I/O.
"""
from __future__ import annotations

from thesisclaw.arena.models import MemoryEntry, Stance
from thesisclaw.arena.verify import (
    _normalize,
    compute_verified_ratio,
    verify_all_entries,
    verify_quote,
)

# ── _normalize ────────────────────────────────────────────────────────────────


def test_normalize_whitespace():
    assert _normalize("hello   world") == "hello world"
    assert _normalize("  strip  ") == "strip"


def test_normalize_ligatures():
    assert _normalize("\ufb01ne") == "fine"   # ﬁ → fi
    assert _normalize("\ufb02ow") == "flow"   # ﬂ → fl
    assert _normalize("\ufb00ort") == "ffort" # ﬀ → ff


def test_normalize_soft_hyphen():
    assert _normalize("re\u00adsearch") == "research"  # removes soft hyphen


def test_normalize_nfkd():
    # é composed vs decomposed should both normalise to 'e' + combining accent
    assert _normalize("caf\u00e9") == _normalize("cafe\u0301")


# ── verify_quote ──────────────────────────────────────────────────────────────


def test_exact_match():
    doc = "The RTF was measured at 0.43 under INT4 quantization on Raspberry Pi 5."
    result = verify_quote("RTF was measured at 0.43", doc)
    assert result["verified"] is True
    assert result["near_exact"] is False
    assert result["position"] >= 0


def test_exact_match_with_ligature_in_doc():
    doc = "The ef\ufb01ciency gain was 2x compared to baseline."  # ﬁ
    result = verify_quote("efficiency gain was 2x", doc)
    assert result["verified"] is True


def test_soft_hyphen_in_doc():
    """
    Soft hyphens in the doc are removed during normalisation.
    "Real\u00adtime" → "Realtime" (no hyphen).
    "Real-time" (query) → "Real-time" (hyphen kept — it's a regular hyphen, not soft).
    These are different strings, so we do NOT expect a match.
    If the user wants a match, they must quote the text exactly as it appears after normalisation.
    """
    doc = "Real\u00adtime factor below 0.5 was achieved."
    # Exact quote with soft hyphen removed (as it appears after normalisation)
    result_exact = verify_quote("Realtime factor below 0.5", doc)
    assert result_exact["verified"] is True

    # Regular hyphen quote should NOT match after soft-hyphen removal
    result_miss = verify_quote("Real-time factor below 0.5", doc)
    assert result_miss["verified"] is False


def test_no_match():
    doc = "This document is about image segmentation."
    result = verify_quote("INT4 quantization reduces WER", doc)
    assert result["verified"] is False
    assert result["near_exact"] is False
    assert result["position"] == -1


def test_empty_quote():
    result = verify_quote("", "some document text")
    assert result["verified"] is False
    assert result["position"] == -1


def test_near_exact_match():
    doc = "The WER degradation was 5.8% compared to the FP16 baseline model."
    # Slightly different: "5.9%" instead of "5.8%"
    result = verify_quote("The WER degradation was 5.9% compared to the FP16 baseline model.", doc)
    # Should not be exactly verified, but could be near_exact
    assert result["verified"] is False  # 5.9 vs 5.8 is not exact


def test_section_mapping():
    sections = {
        "introduction": "This is the introduction. It talks about ASR.",
        "results": "The RTF was measured at 0.43 under INT4 quantization.",
    }
    # quote is in results section
    full_text = sections["introduction"] + " " + sections["results"]
    result = verify_quote("RTF was measured at 0.43", full_text, sections)
    assert result["verified"] is True


# ── verify_all_entries ────────────────────────────────────────────────────────


def test_verify_all_entries_exact():
    doc_text = "Symmetric INT4 quantization reduces peak RAM by 55% on Cortex-A76."
    documents = {"2301.00001": {"text": doc_text, "sections": {}}}

    entries = [
        MemoryEntry(
            fight_id="f1", round=1, author="fighter_a", entry_type="claim",
            text="INT4 reduces RAM",
            quote="INT4 quantization reduces peak RAM by 55%",
            doc_id="2301.00001", stance=Stance.SUPPORTS,
        ),
        MemoryEntry(
            fight_id="f1", round=1, author="fighter_a", entry_type="claim",
            text="Claim with no quote", quote="", doc_id="2301.00001", stance=Stance.NOT_COVERED,
        ),
    ]
    result = verify_all_entries(entries, documents)
    assert result[0].verified is True
    assert result[1].verified is False   # no quote → not verified (default)


def test_verify_all_entries_missing_doc():
    entries = [
        MemoryEntry(
            fight_id="f1", round=1, author="fighter_a", entry_type="claim",
            text="claim", quote="some quote", doc_id="missing_doc", stance=Stance.SUPPORTS,
        )
    ]
    result = verify_all_entries(entries, {})
    assert result[0].verified is False
    assert "not loaded" in result[0].verification_note


# ── compute_verified_ratio ────────────────────────────────────────────────────


def test_verified_ratio_all_verified():
    entries = [
        MemoryEntry(
            fight_id="f1", round=1, author="fighter_a", entry_type="claim",
            text="c", quote="q", doc_id="doc", verified=True,
        ),
        MemoryEntry(
            fight_id="f1", round=1, author="fighter_b", entry_type="claim",
            text="c2", quote="q2", doc_id="doc", verified=True,
        ),
    ]
    assert compute_verified_ratio(entries) == 1.0


def test_verified_ratio_none_verified():
    entries = [
        MemoryEntry(
            fight_id="f1", round=1, author="fighter_a", entry_type="claim",
            text="c", quote="q", doc_id="doc", verified=False,
        ),
    ]
    assert compute_verified_ratio(entries) == 0.0


def test_verified_ratio_no_quotes():
    # Entries with no quotes → ratio = 1.0 (nothing to fail)
    entries = [
        MemoryEntry(
            fight_id="f1", round=0, author="moderator", entry_type="claim",
            text="topic", doc_id="moderator",
        ),
    ]
    assert compute_verified_ratio(entries) == 1.0


def test_verified_ratio_mixed():
    entries = [
        MemoryEntry(fight_id="f1", round=1, author="a", entry_type="claim",
                    text="c1", quote="q1", doc_id="d", verified=True),
        MemoryEntry(fight_id="f1", round=1, author="a", entry_type="claim",
                    text="c2", quote="q2", doc_id="d", verified=True),
        MemoryEntry(fight_id="f1", round=1, author="b", entry_type="claim",
                    text="c3", quote="q3", doc_id="d", verified=False),
        MemoryEntry(fight_id="f1", round=1, author="b", entry_type="claim",
                    text="c4", quote="", doc_id="d", verified=False),  # no quote → excluded
    ]
    ratio = compute_verified_ratio(entries)
    # 2 verified out of 3 with quotes = 0.666...
    assert abs(ratio - 2 / 3) < 0.001
