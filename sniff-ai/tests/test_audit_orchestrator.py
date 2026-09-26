"""Tests for src/core/audit_orchestrator.py.

Mocks PlaywrightWorker, GeminiClient (via create_agent_service) and
K2HorizonClient (via create_k2horizon_client) so no real browser or LLM call
happens. Verifies AuditReport assembly, domain-allowlist guardrail
enforcement, and that a sparse/degraded raw-checks result still produces a
fully valid AuditReport.
"""

import pytest

import src.core.audit_orchestrator as audit_orchestrator_module
from src.core.audit_orchestrator import AuditOrchestrator
from src.core.config import SniffConfig
from src.core.models import Observation

GEMINI_RESULT = {
    "overall_score": 6.0,
    "label": "Strong concept, pre-launch friction",
    "verdict": "The waitlist concept is clear but the CTA lacks urgency.",
    "verdict_summary": "A one-paragraph verdict summary.",
    "honest_verdict": "A blunter paragraph naming the real friction.",
    "context": {
        "page_type": "Pre-launch waitlist landing page",
        "primary_goal": "Capture email addresses before launch",
        "likely_audience": "Early adopters interested in AI tutoring",
        "audience_awareness": "Problem-aware, solution-unaware",
        "visitor_motivation": "Curiosity about a new AI tutoring product",
        "assumptions_to_respect": ["Pre-launch, no live product yet"],
    },
    "story": [
        {"step": "Landed on the hero", "title": "Bold headline", "text": "Clear value prop", "sentiment": "positive"},
    ],
    "scores": [
        {"dimension": "Message & Clarity", "score": 7.0, "rationale": "Headline is clear"},
        {"dimension": "Audience Fit", "score": 6.0, "rationale": "Speaks to early adopters"},
        {"dimension": "Action Path", "score": 5.0, "rationale": "CTA buried below fold"},
        {"dimension": "Trust & Credibility", "score": 6.0, "rationale": "No social proof yet"},
        {"dimension": "Content Depth", "score": 5.0, "rationale": "Thin on details"},
    ],
    "growth_visual_design": {"score": 6.5, "findings": ["Consistent color palette"]},
    "strengths": ["Clear headline"],
    "decision_gaps": ["Pricing isn't mentioned anywhere"],
    "visitor_persona": "A curious early adopter skimming for a reason to trust this pre-launch product.",
    "cta_role_assignments": [
        {"index": 0, "role": "primary-cta", "color": "#ff0055", "label": "Primary CTA"},
    ],
}

K2_RESULT = {
    "jargon_terms": ["synergistic"],
    "primary_fix": {"issue": "CTA lacks urgency", "why": "Visitors don't feel compelled to act now", "action": "Add a launch date"},
    "next_fixes": [{"issue": "No social proof", "why": "Reduces trust", "action": "Add testimonials"}],
    "rewrites": [{"original": "Join the waitlist", "replacement": "Reserve your early-access spot"}],
    "growth_seo": {"score": 5.0, "findings": ["Meta description is present but short"]},
    "growth_navigation": {"score": 8.0, "findings": ["Primary CTA responded correctly when clicked"]},
    "growth_strategic_options": [{"path": "Add urgency messaging", "risk": "Could feel gimmicky", "experiment": "A/B test a countdown"}],
}

RAW_CHECKS = {
    "colors_fonts": {
        "colors": [{"value": "rgb(37, 99, 235)", "count": 10}],
        "fonts": [{"value": "Inter", "count": 6}],
    },
    "interactive_elements": [
        {
            "index": 0,
            "text": "Join the waitlist",
            "tag": "button",
            "rect": {"x": 10, "y": 20, "width": 200, "height": 48},
            "above_fold": True,
            "prominence": 900,
        },
        {
            "index": 1,
            "text": "Learn more",
            "tag": "a",
            "rect": {"x": 10, "y": 400, "width": 80, "height": 24},
            "above_fold": False,
            "prominence": 200,
        },
    ],
    "seo": {
        "title": "Join the waitlist",
        "title_length": 18,
        "meta_description": "Sign up early",
        "meta_description_length": 13,
        "h1_count": 1,
        "img_count": 2,
        "img_alt_count": 2,
        "img_alt_pct": 100,
        "has_canonical": True,
        "has_viewport": True,
    },
    "web_vitals": {"lcp": 1200.0, "fcp": 800.0, "cls": 0.01},
    "footer_nav_links": [],
}


class FakeGeminiClient:
    def invoke_with_json_response(self, system_prompt, user_message, max_tokens=4096, temperature=0.5):
        return GEMINI_RESULT


class FakeAgentService:
    """Stand-in for DecisionService - AuditOrchestrator only reads .client off it."""

    def __init__(self):
        self.client = FakeGeminiClient()


class FakeK2Client:
    def invoke_with_json_response(self, system_prompt, user_message, max_tokens=4096, temperature=0.5):
        return K2_RESULT


class FakeWorker:
    """Stand-in for PlaywrightWorker - no real browser."""

    instances: list["FakeWorker"] = []

    def __init__(self, run_id, artifacts_dir, device_name=None, headless=True, slow_mo=0):
        self.run_id = run_id
        self.artifacts_dir = artifacts_dir
        self.tap_calls: list[str] = []
        self.navigate_calls: list[str] = []
        FakeWorker.instances.append(self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def navigate(self, url, timeout=30000):
        self.navigate_calls.append(url)
        screenshot_path = self.artifacts_dir / "full_page.png"
        if not screenshot_path.exists():
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            screenshot_path.write_bytes(b"fake-png-bytes")
        return Observation(
            runId=self.run_id,
            step=1,
            url=url,
            screenshotPath=str(screenshot_path),
            visibleText=["Join the waitlist", "Learn more"],
        )

    async def evaluate_page_checks(self):
        return RAW_CHECKS

    async def screenshot_viewport(self, name=None):
        return str(self.artifacts_dir / (name or "above_fold.png"))

    async def screenshot(self, name=None):
        return str(self.artifacts_dir / (name or "full_page.png"))

    async def screenshot_with_overlay(self, annotations, name=None):
        return str(self.artifacts_dir / (name or "annotated.png"))

    async def tap(self, target):
        self.tap_calls.append(target)
        # Same URL, no console errors -> "no observable effect" branch.
        return Observation(
            runId=self.run_id,
            step=2,
            url=self.navigate_calls[-1],
            screenshotPath=str(self.artifacts_dir / "full_page.png"),
            visibleText=["Join the waitlist", "Learn more"],
        )

    async def detect_modal(self):
        return False


@pytest.fixture(autouse=True)
def reset_fake_worker_instances():
    FakeWorker.instances = []
    yield
    FakeWorker.instances = []


@pytest.fixture
def config(tmp_path) -> SniffConfig:
    cfg = SniffConfig()
    cfg.artifacts_path = str(tmp_path)
    return cfg


@pytest.fixture(autouse=True)
def patch_clients(monkeypatch):
    monkeypatch.setattr(audit_orchestrator_module, "create_agent_service", lambda cfg: FakeAgentService())
    monkeypatch.setattr(audit_orchestrator_module, "create_k2horizon_client", lambda cfg: FakeK2Client())
    monkeypatch.setattr(audit_orchestrator_module, "PlaywrightWorker", FakeWorker)


@pytest.mark.asyncio
async def test_run_audit_assembles_full_report(config):
    orchestrator = AuditOrchestrator(config)
    report = await orchestrator.run_audit(url="https://staging.example.com", audit_id="audit_test_001")

    assert report.overall_score == 6.0
    assert report.label == GEMINI_RESULT["label"]
    assert [s.dimension for s in report.scores] == [
        "Message & Clarity", "Audience Fit", "Action Path", "Trust & Credibility", "Content Depth",
    ]
    assert report.growth.seo.findings == K2_RESULT["growth_seo"]["findings"]
    assert report.growth.visual_design.findings == GEMINI_RESULT["growth_visual_design"]["findings"]
    # Navigation findings = deterministic footer-link check + k2's own findings.
    assert "SKIPPED" in report.growth.navigation.findings[0]
    assert report.growth.navigation.findings[1:] == K2_RESULT["growth_navigation"]["findings"]

    assert report.visual_teaser.dominant_colors[0].color == "rgb(37, 99, 235)"
    assert report.browsing_evidence.total_interactive_elements == 2
    assert report.browsing_evidence.safe_cta_candidates == 2
    assert report.browsing_evidence.tested_count == 2
    assert report.browsing_evidence.primary_label == "Join the waitlist"
    # Only index 0 got a role assignment from Gemini - the overlay/annotations
    # only cover matched candidates.
    assert len(report.browsing_evidence.annotations) == 1
    assert report.browsing_evidence.annotations[0].role == "primary-cta"

    assert report.images.above_fold.endswith("above_fold.png")
    assert report.images.full_page.endswith("full_page.png")
    assert report.images.annotated.endswith("annotated.png")

    assert report.primary_fix.issue == K2_RESULT["primary_fix"]["issue"]
    assert report.rewrites[0].original == "Join the waitlist"

    # CTA click-testing actually happened against the mock worker.
    worker = FakeWorker.instances[0]
    assert worker.tap_calls == ["Join the waitlist", "Learn more"]


@pytest.mark.asyncio
async def test_run_audit_respects_domain_allowlist(config):
    config.security.enforce_domain_allowlist = True
    config.security.allowed_domains = ["allowed.example.com"]

    orchestrator = AuditOrchestrator(config)
    with pytest.raises(ValueError, match="not in the allowed domains"):
        await orchestrator.run_audit(url="https://evil.example.org")

    # Never even got as far as constructing a worker.
    assert FakeWorker.instances == []


@pytest.mark.asyncio
async def test_run_audit_allows_url_within_allowlist(config):
    config.security.enforce_domain_allowlist = True
    config.security.allowed_domains = ["staging.example.com"]

    orchestrator = AuditOrchestrator(config)
    report = await orchestrator.run_audit(url="https://staging.example.com/landing")

    assert report.overall_score == 6.0


@pytest.mark.asyncio
async def test_run_audit_degrades_gracefully_with_no_candidates(config, monkeypatch):
    """Sparse raw checks (e.g. every sub-check degraded) must still produce a
    fully valid AuditReport - no candidates to test/annotate."""

    class EmptyWorker(FakeWorker):
        async def evaluate_page_checks(self):
            return {
                "colors_fonts": {"colors": [], "fonts": []},
                "interactive_elements": [],
                "seo": {},
                "web_vitals": {"lcp": None, "fcp": None, "cls": None},
                "footer_nav_links": [],
            }

    monkeypatch.setattr(audit_orchestrator_module, "PlaywrightWorker", EmptyWorker)

    orchestrator = AuditOrchestrator(config)
    report = await orchestrator.run_audit(url="https://staging.example.com")

    assert report.browsing_evidence.total_interactive_elements == 0
    assert report.browsing_evidence.safe_cta_candidates == 0
    assert report.browsing_evidence.tested_count == 0
    assert report.browsing_evidence.primary_label == ""
    assert report.browsing_evidence.annotations == []
    assert report.visual_teaser.dominant_colors == []
