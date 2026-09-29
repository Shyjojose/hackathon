from __future__ import annotations

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

