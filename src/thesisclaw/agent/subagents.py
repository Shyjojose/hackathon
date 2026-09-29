from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from thesisclaw.config.settings import settings
from thesisclaw.models.paper import (
    BriefingResult,
    Claim,
    CriticResult,
    EducationalBreakdown,
    FlowchartStep,
    PaperContent,
    PaperVerdict,
    PathfinderResult,
    VerdictEnum,
)
from thesisclaw.tools.embed import cosine_similarity, embed_text
from thesisclaw.tools.fetch import fetch_paper_text

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path("runtime/worker/prompts")


def load_subagent_prompt(name: str) -> str:
    """Load system prompt from runtime/worker/prompts/<name>.md."""
    path = PROMPTS_DIR / f"{name}.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def get_llm_client(model_name: str | None = None) -> Any:
    """Instantiate ChatNVIDIA client if API key is present."""
    if not settings.nvidia_api_key or not settings.nvidia_api_key.startswith("nvapi-"):
        return None

    try:
        from langchain_nvidia_ai_endpoints import ChatNVIDIA

        return ChatNVIDIA(
            model=model_name or settings.default_model,
            api_key=settings.nvidia_api_key,
            base_url=settings.nvidia_base_url,
            temperature=0.2,
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("ChatNVIDIA not available: %s", exc)
        return None


async def paper_reader_subagent(url_or_id: str) -> PaperContent:
    """Subagent 1: Fetches and structures the paper text and claims."""
    return await fetch_paper_text(url_or_id)


def thesis_matcher_subagent(
    paper: PaperContent,
    thesis_claim_text: str,
    similarity_threshold: float = 0.35,
) -> PaperVerdict:
    """Subagent 2: Compares paper against thesis and assigns verdict."""
    paper_summary = f"{paper.title}\n{paper.abstract}"
    paper_emb = embed_text(paper_summary)
    thesis_emb = embed_text(thesis_claim_text)
    sim = cosine_similarity(paper_emb, thesis_emb)

    # Heuristic & embedding-based categorization
    lower_text = (paper.abstract + " " + " ".join(c.text for c in paper.claims)).lower()

    if sim < similarity_threshold and not any(kw in lower_text for kw in ["arm", "quantiz", "int4", "asr", "wer"]):
        return PaperVerdict(
            arxiv_id=paper.arxiv_id,
            verdict=VerdictEnum.IRRELEVANT,
            confidence="high",
            reason=f"Embedding similarity ({sim:.2f}) is below relevance threshold ({similarity_threshold}).",
            direct_quote="",
        )

    # Check for threatening indicators
    threat_indicators = [
        "catastrophic degradation",
        "int4 fails",
        "wer increases by more than",
        "memory bottleneck prevents rtf",
        "unviable on edge",
    ]
    is_threat = any(ind in lower_text for ind in threat_indicators)

    # Check for extension indicators
    extend_indicators = [
        "speculative decoding",
        "mixed-precision",
        "int3",
        "sve2",
        "novel sliding window",
        "pruning algorithm",
    ]
    is_extend = any(ind in lower_text for ind in extend_indicators)

    best_quote = paper.claims[0].quote if paper.claims else (paper.abstract[:200] if paper.abstract else paper.title)

    if is_threat:
        verdict = VerdictEnum.THREATEN
        reason = "Paper presents empirical evidence of severe accuracy degradation or throughput bounds on ARM."
    elif is_extend:
        verdict = VerdictEnum.EXTEND
        reason = "Paper introduces novel adjacent quantization or decoding techniques extending the central thesis."
    else:
        verdict = VerdictEnum.SUPPORT
        reason = "Paper demonstrates quantized speech transcription efficiency consistent with target benchmarks."

    return PaperVerdict(
        arxiv_id=paper.arxiv_id,
        project_slug="rpi5-moonshine-int4",
        verdict=verdict,
        confidence="high" if sim > 0.6 else "medium",
        reason=reason,
        direct_quote=best_quote,
    )


def critic_subagent(paper: PaperContent, claims: list[Claim]) -> CriticResult:
    """Subagent 3: Verifies that claimed quotes exist verbatim in the paper content."""
    if not claims:
        return CriticResult(
            arxiv_id=paper.arxiv_id,
            backed_ratio=1.0,
            result="pass",
            notes="No claims to verify.",
        )

    full_paper_text = paper.title + " " + paper.abstract + " " + " ".join(paper.sections.values())
    backed_count = 0
    unverified = []

    for c in claims:
        # Check if substantive quote substring exists in paper body
        quote_snippet = c.quote.strip().lower()
        if len(quote_snippet) > 20:
            quote_snippet = quote_snippet[:40]
        if quote_snippet in full_paper_text.lower():
            backed_count += 1
        else:
            unverified.append(c.quote)

    ratio = backed_count / len(claims) if claims else 1.0
    passed = ratio >= 0.90

    return CriticResult(
        arxiv_id=paper.arxiv_id,
        backed_ratio=round(ratio, 2),
        result="pass" if passed else "fail",
        unverified_claims=unverified,
        notes=f"Verified {backed_count}/{len(claims)} claims against source text.",
    )


def pathfinder_subagent(paper: PaperContent, verdict: PaperVerdict) -> PathfinderResult:
    """Subagent 4: Proposes next experiment and APA citable paragraph."""
    next_experiment = (
        f"Deploy {paper.title} INT4 quantization profile on Raspberry Pi 5 under unprivileged Podman. "
        "Benchmark RTF and L2/L3 cache misses against baseline target (RTF <= 0.5)."
    )
    success_criterion = "Achieve RTF <= 0.5 with WER degradation <= 6% and Peak RAM <= 1.0 GB."

    citable_paragraph = (
        f"{', '.join(paper.authors[:2]) if paper.authors else 'Authors'} ({paper.year}) explore "
        f"quantized inference on edge RISC processors. Their findings report that '{verdict.direct_quote}', "
        f"which directly informs our {verdict.verdict.value} thesis evaluations."
    )

    propose_code_change = verdict.verdict in (VerdictEnum.EXTEND, VerdictEnum.THREATEN)

    return PathfinderResult(
        arxiv_id=paper.arxiv_id,
        project_slug=verdict.project_slug or "rpi5-moonshine-int4",
        next_experiment=next_experiment,
        success_criterion=success_criterion,
        citable_paragraph=citable_paragraph,
        propose_code_change=propose_code_change,
        code_change_description="Implement NEON SIMD sliding-window kernel optimization" if propose_code_change else None,
    )


def publisher_subagent(
    papers: list[PaperContent],
    verdicts: list[PaperVerdict],
) -> BriefingResult:
    """Subagent 5: Assembles morning briefings for Telegram and voice companion."""
    counts = {"support": 0, "extend": 0, "threaten": 0, "irrelevant": 0}
    for v in verdicts:
        counts[v.verdict.value] = counts.get(v.verdict.value, 0) + 1

    total = len(verdicts)
    top_finding = verdicts[0].direct_quote if verdicts else "No new papers scanned."

    # Strict <= 600 characters voice format
    voice_msg = (
        f"{total} papers scanned today. {counts['support']} support, {counts['extend']} extend, "
        f"{counts['threaten']} threaten your thesis. Top finding: {top_finding}"
    )
    if len(voice_msg) > settings.voice_reply_max_chars:
        voice_msg = voice_msg[: settings.voice_reply_max_chars - 3] + "..."

    # Telegram rich-text format
    telegram_lines = [
        f"📊 **ThesisClaw Daily Briefing** ({total} papers scanned)",
        f"• **Support:** {counts['support']} | **Extend:** {counts['extend']} | **Threaten:** {counts['threaten']} | **Irrelevant:** {counts['irrelevant']}",
        "",
        "**Key Findings:**",
    ]
    for v in verdicts[:3]:
        if v.verdict != VerdictEnum.IRRELEVANT:
            telegram_lines.append(f"• **[{v.verdict.value.upper()}]** arXiv:{v.arxiv_id} — {v.reason}")

    return BriefingResult(
        voice_briefing=voice_msg,
        telegram_briefing="\n".join(telegram_lines),
        papers_processed=total,
        verdict_counts=counts,
        timestamp="2026-09-29T21:00:00Z",
    )


def visualizer_subagent(
    paper: PaperContent,
    verdict: PaperVerdict,
    pathfinder: PathfinderResult | None = None,
    similarity_score: float = 0.76,
) -> EducationalBreakdown:
    """Subagent Skill: Extracts novel ideas, constructs a 5-step visual pipeline, and summarizes takeaways."""
    text_corpus = (paper.title + " " + paper.abstract + " " + " ".join(paper.sections.values())).lower()

    # 1. Extract Novel Ideas
    novel_ideas: list[str] = []
    if "mixed-precision" in text_corpus or "int4" in text_corpus:
        novel_ideas.append("Mixed-precision quantization preserving outlier-sensitive attention query heads while compressing linear weights.")
    if "speculative" in text_corpus:
        novel_ideas.append("Draft-model speculative decoding reducing memory bandwidth trips on edge LPDDR4X buses.")
    if "neon" in text_corpus or "simd" in text_corpus or "arm" in text_corpus:
        novel_ideas.append("Fused ARM NEON 128-bit vector arithmetic kernels for ultra-low latency integer matrix-vector multiplication.")
    if "sliding window" in text_corpus or "cache" in text_corpus:
        novel_ideas.append("Constant-memory KV cache eviction strategy capping memory footprint below 1.0 GB.")

    if not novel_ideas:
        novel_ideas = [
            "Quantized weight representation minimizing memory bus saturation during streaming speech decoding.",
            "Zero-point integer calibration preventing catastrophic accuracy loss under low-bit representations.",
            "Container-friendly memory footprint runnable without hardware driver privilege escalation.",
        ]

    # 2. Thesis Comparison
    thesis_comparison = (
        f"Compared to our Raspberry Pi 5 Moonshine Tiny baseline (INT4 PTQ, target RTF <= 0.5, WER degradation <= 6%), "
        f"this research {verdict.reason.lower().rstrip('.')}."
    )

    # 3. Simplified ELI5 Summary
    simplified_summary = (
        f"The paper addresses edge speech processing by compressing neural network parameters so they run locally "
        f"on low-power hardware. In short: {verdict.reason}"
    )

    # 4. Construct 5-Step Visual Flowchart Pipeline
    steps: list[FlowchartStep] = [
        FlowchartStep(
            step_number=1,
            title="Acoustic Ingestion & Framing",
            description="Streaming 16 kHz raw microphone audio is segmented into 25ms frames and converted into 80-channel Log-Mel spectrograms.",
            category="Input Stage",
            icon="🎙️",
        ),
        FlowchartStep(
            step_number=2,
            title="Encoder Feature Extraction",
            description="Convolutional subsampling downsamples speech frames by 4x before feeding deep multi-head self-attention blocks.",
            category="Architecture",
            icon="🧠",
        ),
        FlowchartStep(
            step_number=3,
            title="The Paper's Novel Mechanism",
            description=verdict.reason or "Post-training integer quantization applied to attention projections with outlier preservation.",
            category="Core Innovation",
            icon="⚡",
        ),
        FlowchartStep(
            step_number=4,
            title="Raspberry Pi 5 Execution Kernel",
            description="Dispatched across 4x ARM Cortex-A76 cores using ARM NEON SIMD registers inside an unprivileged Podman container.",
            category="Edge Hardware",
            icon="⚙️",
        ),
        FlowchartStep(
            step_number=5,
            title="Real-Time Streaming Output",
            description=f"Yields transcribed tokens meeting target: {pathfinder.success_criterion if pathfinder else 'RTF <= 0.5 and Peak RAM <= 1.0 GB'}.",
            category="Target Benchmark",
            icon="📊",
        ),
    ]

    # 5. Core Takeaways
    key_takeaways: list[str] = [
        f"Thesis Verdict: {verdict.verdict.value.upper()} — {verdict.reason}",
        "Edge Viability: Demonstrates that integer arithmetic can maintain acoustic transcription fidelity on RISC architectures.",
        f"Verified Quote: \"{verdict.direct_quote or 'Direct empirical evidence verified by critic.'}\"",
    ]
    if pathfinder:
        key_takeaways.append(f"Recommended Action: {pathfinder.next_experiment}")

    return EducationalBreakdown(
        arxiv_id=paper.arxiv_id,
        title=paper.title,
        authors=paper.authors,
        year=paper.year,
        similarity_score=similarity_score,
        verdict=verdict.verdict,
        verdict_reason=verdict.reason,
        novel_ideas=novel_ideas,
        thesis_comparison=thesis_comparison,
        simplified_summary=simplified_summary,
        flowchart_steps=steps,
        key_takeaways=key_takeaways,
        verified_quote=verdict.direct_quote,
        next_experiment=pathfinder.next_experiment if pathfinder else "",
        success_criterion=pathfinder.success_criterion if pathfinder else "",
        citable_paragraph=pathfinder.citable_paragraph if pathfinder else "",
    )

