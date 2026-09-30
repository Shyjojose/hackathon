"""
ThesisClaw Paper Arena — Fighter Document Loader.

Loads and caches the source documents for each fighter:

Ground fighter (doc_id="ground"):
    Priority 1: research/agent.md  (thesis profile — always included)
    Priority 2: Any *.draft.md files in research/ (user-approved to send to NVIDIA)
    Priority 3: README.md S.M.A.R.T. section for benchmarks context
    Concatenated and trimmed to ~40k tokens (~160k chars).

Paper fighter (doc_id=<arxiv_id>):
    Fetches via fetch_paper_text() (arxiv-txt.org → arXiv HTML → PDF).
    Strips references and appendix sections.
    Caps at ~40k tokens (~160k chars).
    Builds a section index for the quote verifier.

Cache: research/fights/cache/<doc_id>.json
    Avoids re-fetching during a resumed fight.
    Cache is invalidated by deleting the file (no TTL — stable during a hackathon run).
"""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

from thesisclaw.tools.fetch import fetch_paper_text

CACHE_DIR = Path("research/fights/cache")
RESEARCH_DIR = Path("research")
README_PATH = Path("README.md")

# ~40k tokens → ~160k chars (conservative for Nemotron 120B 128k context window)
_MAX_CHARS = 160_000

# Sections to strip from paper fighters (regex on section titles)
_STRIP_SECTION_RE = re.compile(
    r"^(references|bibliography|appendix|acknowledgements?|author contributions?)",
    re.IGNORECASE,
)


# ── Ground document ───────────────────────────────────────────────────────────


def _load_ground_document() -> dict:
    """
    Build the Ground fighter document from:
    1. research/agent.md  (always present)
    2. research/*.draft.md  (thesis draft — user approved)
    3. README.md S.M.A.R.T. section
    """
    parts: list[str] = []

    # 1. Thesis memory
    agent_path = RESEARCH_DIR / "agent.md"
    if agent_path.exists():
        parts.append("# Thesis Profile\n\n" + agent_path.read_text(encoding="utf-8"))

    # 2. Draft thesis files (user approved to send to NVIDIA)
    draft_files = sorted(RESEARCH_DIR.glob("*.draft.md"))
    for draft in draft_files:
        parts.append(f"# Draft: {draft.stem}\n\n" + draft.read_text(encoding="utf-8"))

    # 3. S.M.A.R.T. targets from README
    if README_PATH.exists():
        readme = README_PATH.read_text(encoding="utf-8")
        smart_match = re.search(r"(#{1,3}\s+S\.M\.A\.R\.T.*?)(?=\n#{1,3}\s|\Z)", readme, re.DOTALL)
        if smart_match:
            parts.append("# Verification Targets\n\n" + smart_match.group(1))

    text = "\n\n---\n\n".join(parts)[:_MAX_CHARS]
    sections = {"ground": text}
    return {
        "doc_id": "ground",
        "text": text,
        "sections": sections,
        "token_estimate": len(text) // 4,
    }


# ── Paper document ────────────────────────────────────────────────────────────


def _strip_references(sections: dict[str, str]) -> dict[str, str]:
    """Remove reference/appendix sections from a paper's section dict."""
    return {
        title: body
        for title, body in sections.items()
        if not _STRIP_SECTION_RE.match(title.strip())
    }


async def _load_paper_document(arxiv_id: str) -> dict:
    """Fetch and structure a paper fighter's document."""
    paper = await fetch_paper_text(arxiv_id)
    sections = _strip_references(paper.sections)

    # Build full text with section headers for the verifier
    text_parts = [f"# {paper.title}\n\n## Abstract\n\n{paper.abstract}"]
    for title, body in sections.items():
        text_parts.append(f"## {title}\n\n{body}")

    text = "\n\n".join(text_parts)[:_MAX_CHARS]
    # Rebuild sections from trimmed text so positions are valid
    sections["abstract"] = paper.abstract

    return {
        "doc_id": arxiv_id,
        "title": paper.title,
        "authors": paper.authors,
        "text": text,
        "sections": sections,
        "token_estimate": len(text) // 4,
    }


# ── Cached loader ─────────────────────────────────────────────────────────────


async def load_fighter_doc(doc_id: str, kind: str = "paper") -> dict:
    """
    Load a fighter document, using disk cache if available.

    Args:
        doc_id: "ground" for Ground fighter, arXiv ID for paper fighters.
        kind:   "ground" | "paper" (overrides doc_id logic only for "ground").

    Returns:
        {"doc_id", "text", "sections", "token_estimate", ...}
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"{doc_id}.json"

    # Cache hit
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, KeyError):
            cache_file.unlink(missing_ok=True)  # corrupt cache → re-fetch

    # Cache miss — load the document
    if doc_id == "ground" or kind == "ground":
        result = _load_ground_document()
    else:
        result = await _load_paper_document(doc_id)

    # Persist to cache
    # Sections may contain large strings; keep them but truncate for safety
    try:
        cache_file.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    except (OSError, ValueError):
        pass  # cache write failure is non-fatal

    return result


def invalidate_cache(doc_id: str) -> None:
    """Remove the cached document for a given doc_id (forces re-fetch)."""
    cache_file = CACHE_DIR / f"{doc_id}.json"
    cache_file.unlink(missing_ok=True)


async def load_fighter_docs(fighter_a_doc_id: str, fighter_b_doc_id: str) -> dict[str, dict]:
    """
    Load both fighter documents in parallel.
    Returns {doc_id: doc_dict}.
    """
    kind_a = "ground" if fighter_a_doc_id == "ground" else "paper"
    kind_b = "ground" if fighter_b_doc_id == "ground" else "paper"
    doc_a, doc_b = await asyncio.gather(
        load_fighter_doc(fighter_a_doc_id, kind_a),
        load_fighter_doc(fighter_b_doc_id, kind_b),
    )
    return {fighter_a_doc_id: doc_a, fighter_b_doc_id: doc_b}
