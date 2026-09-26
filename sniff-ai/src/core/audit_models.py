"""Data models for the landing-page audit feature.

Schema was reverse-engineered from a real competitor product (ColdVisit)'s
server-streamed JSON payload - field names are adapted to snake_case/pydantic
conventions, but the concepts/structure are meant to match precisely. Every
field is always fully populated (no paywall/locked-placeholder concept).

Field ownership (who fills each section) is documented on AuditOrchestrator,
not here - this module only defines the shape.
"""

from typing import Literal

from pydantic import BaseModel, Field


class AuditContext(BaseModel):
    """What kind of page this is and who it's for - grounds the rest of the audit."""
    page_type: str = Field(..., description="e.g. 'Pre-launch waitlist landing page for an AI tutoring app'")
    primary_goal: str = Field(..., description="e.g. 'Capture email addresses before the product goes live'")
    likely_audience: str = Field(..., description="Who this page is written for")
    audience_awareness: str = Field(..., description="How aware/informed the audience is assumed to be")
    visitor_motivation: str = Field(..., description="Why a visitor would land here in the first place")
    assumptions_to_respect: list[str] = Field(
        default_factory=list, description="Assumptions the audit should not second-guess"
    )


class StoryStep(BaseModel):
    """One step in the first-time-visitor narrative walkthrough."""
    step: str = Field(..., description="What the agent did/observed, in-character as a first-time visitor")
    title: str = Field(..., description="The specific detail noticed")
    text: str = Field(..., description="The analytical takeaway")
    sentiment: Literal["positive", "neutral", "negative"] = Field(...)


class DimensionScore(BaseModel):
    """One of the 5 fixed scoring dimensions."""
    dimension: str = Field(..., description="One of: Message & Clarity, Audience Fit, Action Path, Trust & Credibility, Content Depth")
    score: float = Field(..., ge=0.0, le=10.0)
    rationale: str = Field(...)


class FindingsBlock(BaseModel):
    """A scored findings list, reused for seo/visual_design/navigation."""
    score: float = Field(..., ge=0.0, le=10.0)
    findings: list[str] = Field(default_factory=list)


class StrategicOption(BaseModel):
    path: str = Field(..., description="A strategic direction the site owner could take")
    risk: str = Field(..., description="What could go wrong / the tradeoff")
    experiment: str = Field(..., description="A concrete, testable experiment for this path")


class GrowthSection(BaseModel):
    seo: FindingsBlock
    visual_design: FindingsBlock
    navigation: FindingsBlock
    strategic_options: list[StrategicOption] = Field(default_factory=list)


class ColorUse(BaseModel):
    color: str = Field(..., description="Computed-style color value, e.g. 'rgb(37, 99, 235)'")
    uses: int = Field(..., ge=0)


class FontUse(BaseModel):
    family: str
    uses: int = Field(..., ge=0)


class VisualTeaser(BaseModel):
    dominant_colors: list[ColorUse] = Field(default_factory=list)
    font_families: list[FontUse] = Field(default_factory=list)


class Annotation(BaseModel):
    """One semantic role assigned (by the vision LLM) to a detected interactive element,
    used to render the annotated screenshot overlay."""
    role: Literal["headline", "support", "primary-cta", "cta"]
    text: str
    color: str = Field(..., description="Hex color for the overlay border/badge")
    label: str = Field(..., description="Short badge label, e.g. 'Primary CTA'")


class CTATest(BaseModel):
    """Result of actually clicking a candidate CTA during the audit."""
    label: str
    target_text: str
    result: str = Field(..., description="What happened: navigated to X / no observable effect / opened a modal / error")


class BrowsingEvidence(BaseModel):
    total_interactive_elements: int = Field(..., ge=0)
    safe_cta_candidates: int = Field(..., ge=0)
    tested_count: int = Field(..., ge=0)
    primary_label: str = Field(..., description="Detected main CTA text, e.g. 'Join the waitlist'")
    annotations: list[Annotation] = Field(default_factory=list)
    tests: list[CTATest] = Field(default_factory=list)


class FixItem(BaseModel):
    issue: str
    why: str
    action: str


class RewriteItem(BaseModel):
    original: str
    replacement: str


class ImagePaths(BaseModel):
    above_fold: str = Field(..., description="Local file path to the viewport-only screenshot")
    full_page: str = Field(..., description="Local file path to the full-page screenshot")
    annotated: str = Field(..., description="Local file path to the viewport screenshot with the CTA overlay")


class AuditReport(BaseModel):
    """Full landing-page audit result. Every field is always populated."""
    overall_score: float = Field(..., ge=0.0, le=10.0)
    label: str = Field(..., description="Short verdict tag, e.g. 'Strong concept, pre-launch friction'")
    verdict: str = Field(..., description="One sentence")
    verdict_summary: str = Field(..., description="One paragraph")
    honest_verdict: str = Field(..., description="A blunter, more direct variant of verdict_summary")

    context: AuditContext
    story: list[StoryStep] = Field(default_factory=list)
    scores: list[DimensionScore] = Field(
        ..., description="Exactly 5 entries, in order: Message & Clarity, Audience Fit, Action Path, Trust & Credibility, Content Depth"
    )
    growth: GrowthSection
    visual_teaser: VisualTeaser
    strengths: list[str] = Field(default_factory=list)
    decision_gaps: list[str] = Field(default_factory=list, description="Things a visitor can't tell/decide from the page as-is")
    jargon_terms: list[str] = Field(default_factory=list, description="Confusing terminology found on the page")
    browsing_evidence: BrowsingEvidence
    primary_fix: FixItem
    next_fixes: list[FixItem] = Field(default_factory=list)
    rewrites: list[RewriteItem] = Field(default_factory=list)
    images: ImagePaths
    visitor_persona: str = Field(..., description="One synthesized persona description framing the whole audit")
