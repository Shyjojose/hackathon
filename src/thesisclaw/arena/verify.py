"""
ThesisClaw Paper Arena — Quote Verifier.

Verifies that a fighter's quoted text appears verbatim in its source document,
after normalising unicode ligatures, soft-hyphens, and internal whitespace.

Rules (per agentwars.md):
- Exact match  → verified=True,  near_exact=False
- Near-exact   → verified=False, near_exact=True  (SequenceMatcher ratio ≥ 0.95)
- No match     → verified=False, near_exact=False

Unverified entries are excluded from judge scoring (caller is responsible for filtering).
"""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

# Unicode ligature map — covers the most common ones in academic PDFs
_LIGATURES: dict[str, str] = {
    "\ufb00": "ff",   # ﬀ
    "\ufb01": "fi",   # ﬁ
    "\ufb02": "fl",   # ﬂ
    "\ufb03": "ffi",  # ﬃ
    "\ufb04": "ffl",  # ﬄ
    "\ufb05": "st",   # ﬅ
    "\ufb06": "st",   # ﬆ
}

_NEAR_EXACT_THRESHOLD = 0.95
_SEARCH_WINDOW_MULTIPLIER = 3  # search window = len(quote) * this factor around best anchor


def _normalize(text: str) -> str:
    """
    Normalise text for comparison:
    1. NFKD unicode normalisation (decomposes accents, etc.)
    2. Replace ligatures (ﬁ → fi, etc.)
    3. Remove soft hyphens (U+00AD)
    4. Collapse any whitespace sequence to a single space
    5. Strip leading/trailing whitespace
    """
    text = unicodedata.normalize("NFKD", text)
    for lig, rep in _LIGATURES.items():
        text = text.replace(lig, rep)
    text = text.replace("\u00ad", "")  # soft hyphen
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _find_section(char_pos: int, sections: dict[str, str]) -> str:
    """Map a character position in the concatenated document to its section name."""
    cumulative = 0
    for name, body in sections.items():
        cumulative += len(body)
        if char_pos < cumulative:
            return name
    return "body"


def verify_quote(
    quote: str,
    document: str,
    sections: dict[str, str] | None = None,
) -> dict[str, object]:
    """
    Verify a quote against the source document.

    Args:
        quote:     The quoted string from a fighter's MemoryEntry.
        document:  The full normalised text of the fighter's source document.
        sections:  Optional {section_name: section_text} dict for position → section mapping.

    Returns:
        {
            "verified":    bool,
            "near_exact":  bool,
            "position":    int,   # char offset in normalised doc, -1 if not found
            "section":     str,
        }
    """
    if not quote or not quote.strip():
        return {"verified": False, "near_exact": False, "position": -1, "section": ""}

    nq = _normalize(quote)
    nd = _normalize(document)

    # 1. Exact match
    pos = nd.find(nq)
    if pos != -1:
        section = _find_section(pos, sections or {})
        return {"verified": True, "near_exact": False, "position": pos, "section": section}

    # 2. Near-exact: find the best-matching window in the document
    #    Anchor on the first 20 chars of the quote to limit search space.
    anchor = nq[:20]
    anchor_pos = nd.find(anchor)
    if anchor_pos == -1:
        anchor_pos = 0  # fallback: scan from start

    window_start = max(0, anchor_pos)
    window_end = min(len(nd), anchor_pos + len(nq) * _SEARCH_WINDOW_MULTIPLIER)
    window = nd[window_start:window_end]

    ratio = SequenceMatcher(None, nq, window, autojunk=False).ratio()
    if ratio >= _NEAR_EXACT_THRESHOLD:
        return {"verified": False, "near_exact": True, "position": anchor_pos, "section": _find_section(anchor_pos, sections or {})}

    return {"verified": False, "near_exact": False, "position": -1, "section": ""}


def verify_all_entries(
    entries: list,
    documents: dict[str, dict],
) -> list:
    """
    Verify all MemoryEntries that have a non-empty quote field.
    Mutates entries in-place (sets verified, near_exact, char_position, section).
    Entries without a quote are left as-is (verified=False is the default).

    Args:
        entries:   list[MemoryEntry]
        documents: {doc_id: {"text": str, "sections": dict[str, str]}}
    Returns:
        The same list, entries mutated.
    """
    for entry in entries:
        if not entry.quote:
            continue
        doc = documents.get(entry.doc_id)
        if doc is None:
            entry.verification_note = f"Document '{entry.doc_id}' not loaded"
            continue
        result = verify_quote(
            entry.quote,
            doc["text"],
            doc.get("sections"),
        )
        entry.verified = result["verified"]      # type: ignore[assignment]
        entry.near_exact = result["near_exact"]  # type: ignore[assignment]
        entry.char_position = result["position"] # type: ignore[assignment]
        entry.section = result["section"]        # type: ignore[assignment]
    return entries


def compute_verified_ratio(entries: list) -> float:
    """
    Return the fraction of entries with quotes that are verified.
    Entries without a quote are excluded from the denominator.
    """
    with_quotes = [e for e in entries if e.quote]
    if not with_quotes:
        return 1.0  # no quotes → nothing to fail
    verified = [e for e in with_quotes if e.verified]
    return len(verified) / len(with_quotes)
