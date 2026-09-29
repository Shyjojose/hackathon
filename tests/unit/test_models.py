from __future__ import annotations

from thesisclaw.models.job import JobStatus, ScanJob
from thesisclaw.models.paper import (
    BriefingResult,
    Claim,
    CriticResult,
    PaperContent,
    PaperVerdict,
    PathfinderResult,
    VerdictEnum,
)


def test_claim_and_paper_content_creation():
    claim = Claim(
        text="INT4 quantization achieves RTF <= 0.5 on ARM Cortex-A76",
        quote="We observe an RTF of 0.44 when running Moonshine Tiny with INT4 weights on Raspberry Pi 5.",
        section="Experiments",
    )
    paper = PaperContent(
        arxiv_id="2608.12345",
        title="Real-Time Speech Transcription on Edge ARM Devices",
        authors=["Alice Researcher", "Bob Engineer"],
        year=2026,
        abstract="This paper explores quantized ASR models on Raspberry Pi 5.",
        claims=[claim],
    )
    assert paper.arxiv_id == "2608.12345"
    assert len(paper.claims) == 1
    assert paper.claims[0].section == "Experiments"


def test_paper_verdict_enum():
    verdict = PaperVerdict(
        arxiv_id="2608.12345",
        project_slug="rpi5-moonshine-int4",
        verdict=VerdictEnum.SUPPORT,
        confidence="high",
        reason="Directly demonstrates RTF <= 0.5 on target hardware without excessive WER degradation.",
        direct_quote="Achieves RTF of 0.44 on Cortex-A76.",
    )
    assert verdict.verdict == VerdictEnum.SUPPORT
    assert verdict.verdict.value == "support"


def test_critic_result_properties():
    passing_critic = CriticResult(
        arxiv_id="2608.12345",
        backed_ratio=0.95,
        result="pass",
    )
    assert passing_critic.is_passed is True

    failing_critic = CriticResult(
        arxiv_id="2608.12345",
        backed_ratio=0.80,
        result="fail",
        unverified_claims=["Unbacked claim 1"],
    )
    assert failing_critic.is_passed is False


def test_pathfinder_result():
    path = PathfinderResult(
        arxiv_id="2608.99999",
        project_slug="rpi5-moonshine-int4",
        next_experiment="Profile INT4 matrix multiplication with NEON SIMD kernels on Core 3.",
        success_criterion="RTF <= 0.45",
        citable_paragraph="Doe et al. (2026) report that INT4 PTQ reduces decode loop overhead.",
        propose_code_change=True,
        code_change_description="Add NEON SIMD unrolled loop to quantization kernel.",
    )
    assert path.propose_code_change is True
    assert "RTF" in path.success_criterion


def test_briefing_result_voice_limit():
    voice_text = "5 papers scanned today. 2 support, 1 extend, 0 threaten your thesis."
    briefing = BriefingResult(
        voice_briefing=voice_text,
        telegram_briefing="### Daily Briefing\n5 papers scanned...",
        papers_processed=5,
        timestamp="2026-09-29T21:00:00Z",
    )
    assert len(briefing.voice_briefing) <= 600


def test_scan_job_lifecycle():
    job = ScanJob(
        job_id="job-abc-123",
        status=JobStatus.QUEUED,
        target_url="https://arxiv.org/abs/2608.12345",
        created_at="2026-09-29T21:00:00Z",
    )
    assert job.status == JobStatus.QUEUED
    job.status = JobStatus.COMPLETED
    job.completed_at = "2026-09-29T21:01:00Z"
    assert job.status == JobStatus.COMPLETED
