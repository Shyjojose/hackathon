from __future__ import annotations

import httpx
import pytest
import respx

from thesisclaw.tools.embed import (
    cosine_similarity,
    embed_text,
    generate_deterministic_mock_embedding,
)
from thesisclaw.tools.fetch import (
    extract_arxiv_id,
    extract_key_claims,
    fetch_paper_text,
    split_sections,
)


def test_extract_arxiv_id():
    assert extract_arxiv_id("https://arxiv.org/abs/2404.12345") == "2404.12345"
    assert extract_arxiv_id("https://arxiv.org/html/2404.12345v2") == "2404.12345"
    assert extract_arxiv_id("arxiv:2404.12345") == "2404.12345"
    assert extract_arxiv_id("2404.12345") == "2404.12345"


def test_split_sections():
    raw_text = """
Introduction
Speech recognition on edge devices has received significant attention.

Methodology
We compress weights using symmetric INT4 quantization.

Results
The RTF achieved is 0.45 with a 4.2% WER degradation.

Conclusion
Our approach is privacy-preserving and runs offline.
"""
    sections = split_sections(raw_text)
    assert "introduction" in sections
    assert "methodology" in sections
    assert "results" in sections
    assert "INT4" in sections["methodology"]


def test_extract_key_claims():
    text = (
        "We achieve a real-time factor of 0.44 on Cortex-A76 processors. "
        "Furthermore, INT4 quantization reduces memory consumption by 52% without degradation."
    )
    claims = extract_key_claims(text)
    assert len(claims) >= 1
    assert any("0.44" in c.quote for c in claims)


def test_cosine_similarity():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]

    assert pytest.approx(cosine_similarity(v1, v2)) == 1.0
    assert pytest.approx(cosine_similarity(v1, v3)) == 0.0
    assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_deterministic_embedding():
    emb1 = generate_deterministic_mock_embedding("Edge AI Speech")
    emb2 = generate_deterministic_mock_embedding("Edge AI Speech")
    emb3 = generate_deterministic_mock_embedding("Unrelated Topic")

    assert len(emb1) == 1024
    assert emb1 == emb2
    assert emb1 != emb3
    assert pytest.approx(cosine_similarity(emb1, emb2)) == 1.0


def test_embed_text_fallback():
    vec = embed_text("Raspberry Pi 5 INT4 Quantization")
    assert isinstance(vec, list)
    assert len(vec) == 1024


@pytest.mark.asyncio
@respx.mock
async def test_fetch_paper_text_mocked():
    arxiv_id = "2608.12345"
    mock_txt_content = (
        "Title: Real-Time ASR on Edge Hardware\n\n"
        "Abstract\n"
        "We evaluate quantized Small Language Models on ARM Cortex-A76.\n\n"
        "Methodology\n"
        "We apply symmetric INT4 quantization.\n\n"
        "Results\n"
        "We achieve an RTF of 0.42 and WER degradation of 3.8%."
    )

    respx.get(f"https://arxiv-txt.org/abs/{arxiv_id}").respond(
        status_code=200,
        text=mock_txt_content,
    )

    async with httpx.AsyncClient() as client:
        # Patch rate limit wait for fast unit tests
        from thesisclaw.tools import fetch

        fetch._LAST_REQUEST_TIMESTAMP = 0.0
        paper = await fetch_paper_text(arxiv_id, client=client)

    assert paper.arxiv_id == arxiv_id
    assert "Methodology" in paper.sections or "methodology" in paper.sections
    assert len(paper.claims) >= 1
