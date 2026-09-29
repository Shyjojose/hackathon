from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class VerdictEnum(str, Enum):
    SUPPORT = "support"
    EXTEND = "extend"
    THREATEN = "threaten"
    IRRELEVANT = "irrelevant"


class Claim(BaseModel):
    """A falsifiable technical claim extracted directly from an academic paper."""

    text: str = Field(description="Statement of the claim")
    quote: str = Field(description="Direct verbatim quote from the paper supporting the claim")
    section: str = Field(default="body", description="Paper section where the quote appears")


class PaperContent(BaseModel):
    """Full structured content of a parsed paper."""

    arxiv_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int = 2026
    abstract: str = ""
    sections: dict[str, str] = Field(default_factory=dict)
    claims: list[Claim] = Field(default_factory=list)
    source_url: str = ""


class PaperVerdict(BaseModel):
    """Evaluation verdict produced by thesis-matcher."""

    arxiv_id: str
    project_slug: str | None = None
    verdict: VerdictEnum
    confidence: str = Field(default="medium", description="high, medium, or low")
    reason: str = Field(description="2-3 sentences explaining the verdict")
    direct_quote: str = Field(default="", description="The most impactful quoted sentence")
    new_topic_detected: bool = False


class PathfinderResult(BaseModel):
    """Proposed experiment and citation generated for extend/threaten papers."""

    arxiv_id: str
    project_slug: str
    next_experiment: str = Field(description="Specific, falsifiable experiment runnable on target hardware")
    success_criterion: str = Field(description="Measurable success metric (e.g. RTF <= 0.5)")
    citable_paragraph: str = Field(description="APA format citable summary paragraph with direct quotes")
    propose_code_change: bool = False
    code_change_description: str | None = None


class CriticResult(BaseModel):
    """Verification result from critic subagent ensuring >=90% claims are backed by direct quotes."""

    arxiv_id: str
    backed_ratio: float = Field(ge=0.0, le=1.0)
    result: str = Field(description="'pass' if backed_ratio >= 0.90 else 'fail'")
    unverified_claims: list[str] = Field(default_factory=list)
    notes: str = ""

    @property
    def is_passed(self) -> bool:
        return self.result.lower() == "pass" and self.backed_ratio >= 0.90


class BriefingResult(BaseModel):
    """Synthesized morning briefing formatted for both voice companion and Telegram."""

    voice_briefing: str = Field(description="Strictly <= 600 plain text characters")
    telegram_briefing: str = Field(description="Full rich-text briefing for Telegram")
    papers_processed: int = 0
    verdict_counts: dict[str, int] = Field(default_factory=dict)
    timestamp: str = ""


class FlowchartStep(BaseModel):
    """A discrete pipeline stage in the paper's methodology."""

    step_number: int
    title: str
    description: str
    category: str = Field(default="Pipeline", description="e.g. Input, Feature, Innovation, Kernel, Metric")
    icon: str = Field(default="⚡", description="Visual representation icon")


class EducationalBreakdown(BaseModel):
    """Complete structured breakdown feeding the 3-tab index.html."""

    arxiv_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int = 2026

    # Tab 1: Similarity & Novel Ideas
    similarity_score: float = Field(default=0.5, ge=0.0, le=1.0)
    verdict: VerdictEnum = VerdictEnum.SUPPORT
    verdict_reason: str = ""
    novel_ideas: list[str] = Field(default_factory=list, description="New ideas and innovative techniques found in the paper")
    thesis_comparison: str = Field(default="", description="Direct comparison vs student's RPi5 Moonshine INT4 thesis")

    # Tab 2: Picturefy & Flowchart
    simplified_summary: str = Field(default="", description="ELI5 visual explanation of how the system works")
    flowchart_steps: list[FlowchartStep] = Field(default_factory=list, description="Ordered pipeline stages")

    # Tab 3: Key Takeaways & Experiment
    key_takeaways: list[str] = Field(default_factory=list, description="Core bulleted takeaways")
    verified_quote: str = ""
    next_experiment: str = ""
    success_criterion: str = ""
    citable_paragraph: str = ""
