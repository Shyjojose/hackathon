from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Any

import pytest
import respx

from thesisclaw.agent.orchestrator import ThesisOrchestrator
from thesisclaw.agent.subagents import (
    critic_subagent,
    pathfinder_subagent,
    publisher_subagent,
    thesis_matcher_subagent,
)
from thesisclaw.models.paper import Claim, PaperContent, PaperVerdict, VerdictEnum


def test_thesis_matcher_support():
    paper = PaperContent(
        arxiv_id="2608.12345",
        title="Moonshine Tiny Speech Transcription with INT4 on Raspberry Pi 5",
        abstract="We profile INT4 quantization on ARM Cortex-A76 achieving RTF of 0.44 and 3.9% WER degradation.",
        claims=[
            Claim(
                text="INT4 achieves RTF <= 0.5",
                quote="Achieved RTF of 0.44 on Raspberry Pi 5",
                section="Results",
            )
        ],
    )
    thesis = "Real-Time Speech Transcription on Raspberry Pi 5 with INT4 (RTF <= 0.5, WER <= 6%)"
    verdict = thesis_matcher_subagent(paper, thesis)

    assert verdict.verdict == VerdictEnum.SUPPORT
    assert verdict.confidence in ("high", "medium")


def test_critic_subagent_pass():
    paper = PaperContent(
        arxiv_id="2608.12345",
        title="Moonshine Tiny Evaluation",
        abstract="Full abstract text containing verbatim quote.",
        sections={"body": "We observe an RTF of 0.44 during streaming inference."},
        claims=[
            Claim(
                text="RTF is 0.44",
                quote="We observe an RTF of 0.44 during streaming inference.",
                section="body",
            )
        ],
    )
    result = critic_subagent(paper, paper.claims)
    assert result.is_passed is True
    assert result.backed_ratio == 1.0


def test_pathfinder_subagent():
    paper = PaperContent(
        arxiv_id="2608.55555",
        title="Novel Speculative Decoding on Cortex-A76",
        abstract="A paper that extends edge ASR decoding.",
    )
    verdict = PaperVerdict(
        arxiv_id="2608.55555",
        project_slug="rpi5-moonshine-int4",
        verdict=VerdictEnum.EXTEND,
        reason="Introduces speculative decoding for edge ASR.",
        direct_quote="Improves throughput by 35%.",
    )
    path = pathfinder_subagent(paper, verdict)
    assert path.propose_code_change is True
    assert "Raspberry Pi 5" in path.next_experiment


def test_publisher_subagent():
    p1 = PaperContent(arxiv_id="1", title="Paper 1")
    v1 = PaperVerdict(arxiv_id="1", verdict=VerdictEnum.SUPPORT, reason="Good match", direct_quote="Quote 1")
    briefing = publisher_subagent([p1], [v1])

    assert len(briefing.voice_briefing) <= 600
    assert "1 support" in briefing.voice_briefing
    assert "ThesisClaw Daily Briefing" in briefing.telegram_briefing


@pytest.mark.asyncio
@respx.mock
async def test_orchestrator_pipeline(tmp_path):
    arxiv_id = "2608.77777"
    db_file = tmp_path / "test_checkpoints.sqlite3"

    mock_text = (
        "Title: Real-Time ASR on Raspberry Pi 5\n\n"
        "Abstract\n"
        "We evaluate quantized Small Language Models on ARM Cortex-A76.\n\n"
        "Results\n"
        "We achieve an RTF of 0.45 with INT4 quantization."
    )
    respx.get(f"https://arxiv-txt.org/abs/{arxiv_id}").respond(
        status_code=200,
        text=mock_text,
    )

    orch = ThesisOrchestrator(db_path=db_file)
    res = await orch.evaluate_single_paper(arxiv_id)

    assert res["paper"].arxiv_id == arxiv_id
    assert res["verdict"].verdict in (VerdictEnum.SUPPORT, VerdictEnum.EXTEND)
    assert orch.is_paper_processed(arxiv_id) is True


def test_visualizer_subagent():
    from thesisclaw.agent.subagents import visualizer_subagent

    paper = PaperContent(
        arxiv_id="2608.12345",
        title="Streaming INT4 Speech on ARM NEON",
        abstract="We demonstrate mixed-precision INT4 quantization with ARM NEON SIMD kernels.",
    )
    verdict = PaperVerdict(
        arxiv_id="2608.12345",
        verdict=VerdictEnum.SUPPORT,
        reason="Demonstrates RTF <= 0.5 with high throughput.",
        direct_quote="Achieved RTF 0.44 on Cortex-A76.",
    )
    breakdown = visualizer_subagent(paper, verdict)

    assert breakdown.arxiv_id == "2608.12345"
    assert len(breakdown.flowchart_steps) == 5
    assert len(breakdown.novel_ideas) >= 1
    assert "Acoustic Ingestion" in breakdown.flowchart_steps[0].title
    assert "Raspberry Pi 5" in breakdown.flowchart_steps[3].title
    assert len(breakdown.key_takeaways) >= 2
    assert "flowchart TD" in breakdown.mermaid_architecture
    assert "sequenceDiagram" in breakdown.mermaid_sequence
    assert "rtf" in breakdown.chart_data


@pytest.mark.asyncio
async def test_research_scout_subagent_deduplication(tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    import arxiv

    from thesisclaw.agent.subagents import research_scout_subagent

    db_file = tmp_path / "test_scout.sqlite3"
    with sqlite3.connect(db_file) as conn:
        conn.execute(
            """
            CREATE TABLE processed_papers (
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
        conn.execute("INSERT INTO processed_papers (arxiv_id, title) VALUES ('2404.00001', 'Old Paper 1')")
        conn.execute("INSERT INTO processed_papers (arxiv_id, title) VALUES ('2404.00002', 'Old Paper 2')")

    class MockAuthor:
        def __init__(self, name: str) -> None:
            self.name = name

    class MockCandidate:
        def __init__(self, aid: str, title: str, summary: str) -> None:
            self._aid = aid
            self.title = title
            self.summary = summary
            self.authors = [MockAuthor("Author X")]
            self.published = datetime(2026, 4, 1, tzinfo=UTC)
            self.entry_id = f"https://arxiv.org/abs/{aid}"

        def get_short_id(self) -> str:
            return self._aid

    candidates = [
        MockCandidate("2404.00001v1", "Old Paper 1", "Old abstract"),
        MockCandidate("2404.00002v1", "Old Paper 2", "Old abstract"),
        MockCandidate("2404.00003v1", "Novel Speech Quantization on ARM", "Speech transcription with INT4 on Raspberry Pi"),
        MockCandidate("2404.00004v1", "Ultra-low Latency ASR", "Low latency streaming ASR on edge devices"),
        MockCandidate("2404.00005v1", "Speculative Edge Decoding", "Accelerating edge models via speculative decoding"),
        MockCandidate("2404.00006v1", "Extra Paper", "Should not be processed because limit is 3"),
    ]

    class MockClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def results(self, search: Any) -> Any:
            return iter(candidates)

    monkeypatch.setattr(arxiv, "Client", MockClient)

    result = await research_scout_subagent(
        query="speech quantization",
        limit=3,
        db_path=db_file,
        base_url="http://192.168.178.46:8080",
    )

    assert result.new_papers_found == 3
    assert len(result.papers) == 3

    # Check that old papers were skipped and exactly 3 new papers were returned
    paper_ids = [p.arxiv_id for p in result.papers]
    assert paper_ids == ["2404.00003", "2404.00004", "2404.00005"]
    assert "2404.00001" not in paper_ids
    assert "2404.00002" not in paper_ids

    # Check similarity scores and links
    for p in result.papers:
        assert 0.0 <= p.similarity_score <= 1.0
        assert p.similarity_score > 0.2  # Semantic or keyword grounding provides realistic score
        assert p.arxiv_url == f"https://arxiv.org/abs/{p.arxiv_id}"
        assert p.dashboard_url == f"http://192.168.178.46:8080/papers/{p.arxiv_id}/"

    # Check SQLite DB was updated to include all 5 papers
    with sqlite3.connect(db_file) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM processed_papers")
        count = cur.fetchone()[0]
        assert count == 5

    # Run again with same mock candidates: should skip 1-5 and find the 6th paper
    result_second = await research_scout_subagent(
        query="speech quantization",
        limit=3,
        db_path=db_file,
    )
    assert result_second.new_papers_found == 1
    assert len(result_second.papers) == 1
    assert result_second.papers[0].arxiv_id == "2404.00006"

    # Run third time: all 6 papers are in DB, so exactly 0 new papers found
    result_third = await research_scout_subagent(
        query="speech quantization",
        limit=3,
        db_path=db_file,
    )
    assert result_third.new_papers_found == 0
    assert len(result_third.papers) == 0


@pytest.mark.asyncio
async def test_research_scout_subagent_default_db_path(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    import arxiv

    from thesisclaw.agent.subagents import research_scout_subagent

    # Test that default settings.checkpoints_dir (string) does not cause TypeError
    monkeypatch.setattr("thesisclaw.config.settings.settings.checkpoints_dir", str(tmp_path))

    class MockAuthor:
        def __init__(self, name: str) -> None:
            self.name = name

    class MockCandidate:
        def __init__(self, aid: str, title: str, summary: str) -> None:
            self._aid = aid
            self.title = title
            self.summary = summary
            self.authors = [MockAuthor("Author Y")]
            self.published = datetime(2026, 4, 1, tzinfo=UTC)
            self.entry_id = f"https://arxiv.org/abs/{aid}"

        def get_short_id(self) -> str:
            return self._aid

    candidates = [
        MockCandidate(
            "2405.00001v1",
            "Default Path Speech Quantization",
            "Speech model with INT4 on edge",
        ),
    ]

    class MockClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def results(self, search: Any) -> Any:
            return iter(candidates)

    monkeypatch.setattr(arxiv, "Client", MockClient)

    # db_path=None tests the default settings path resolution (settings.checkpoints_path)
    result = await research_scout_subagent(
        query="speech quantization",
        limit=1,
        db_path=None,
    )

    assert result.new_papers_found == 1
    assert len(result.papers) == 1
    assert result.papers[0].arxiv_id == "2405.00001"


