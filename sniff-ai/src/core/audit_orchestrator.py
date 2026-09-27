"""Landing-page audit orchestrator.

Runs a second "mode" alongside RunOrchestrator's goal-pursuit loop: instead of
chasing a goal step by step, it audits a landing page the way a PM/CRO
consultant would - deterministic browser-side checks, real CTA click-testing,
then two LLM synthesis calls to turn all of that into an AuditReport.

Field ownership (who fills what - see docstrings on the two _run_*_synthesis
methods for the exact JSON contracts):
- Gemini (vision): context, story, the 5 scores, growth.visual_design,
  strengths, decision_gaps, visitor_persona, overall_score/label/verdict*,
  and CTA semantic-role assignment (for the annotation overlay).
- k2-horizon (text): jargon_terms, primary_fix/next_fixes, rewrites,
  growth.seo, growth.navigation, growth.strategic_options.
- Deterministic checks (no LLM): visual_teaser, browsing_evidence's
  total/safe-candidate counts, the three screenshots, footer-link liveness.

Reuses PlaywrightWorker's async context-manager lifecycle (see
executor/playwright_worker.py __aenter__/__aexit__) exactly like
RunOrchestrator does, and respects the same domain-allowlist/hard-timeout
guardrails a normal run does (core/config.py SecurityConfig/GuardrailsConfig).
"""

import asyncio
import base64
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ..agent.decision_service import create_agent_service
from ..agent.k2horizon_client import create_k2horizon_client
from ..evidence.audit_checks import (
    build_browsing_evidence_base,
    build_navigation_findings,
    build_visual_teaser,
    check_footer_links,
    select_cta_candidates,
)
from ..evidence.screenshot_annotator import capture_audit_screenshots, merge_role_assignments
from ..executor.playwright_worker import PlaywrightWorker
from .audit_models import AuditReport
from .config import SniffConfig
from .persona import CONFUSED_FIRST_TIME_USER, PersonaProfile

logger = logging.getLogger(__name__)


class AuditOrchestrator:
    """Orchestrates a single landing-page audit run."""

    def __init__(self, config: SniffConfig):
        self.config = config

    async def run_audit(
        self, url: str, persona: str | None = None, audit_id: str | None = None
    ) -> AuditReport:
        """Run a full landing-page audit and return the populated AuditReport.

        Args:
            url: Landing page URL to audit
            persona: Optional persona name (defaults to confused_first_time_user)
            audit_id: Pre-assigned audit ID (e.g. already handed back to an API
                caller to poll). Generated the usual way if omitted.
        """
        self._check_domain_allowlist(url)

        audit_id = audit_id or self._generate_audit_id()
        persona_profile = self._load_persona(persona)

        return await asyncio.wait_for(
            self._run_audit_body(url, audit_id, persona_profile),
            timeout=self.config.guardrails.hard_timeout,
        )

    async def _run_audit_body(
        self, url: str, audit_id: str, persona_profile: PersonaProfile
    ) -> AuditReport:
        """Single-page entry point: create a worker, navigate once, hand off
        to run_audit_on_page. Kept as a thin wrapper so this method's own
        behavior is unchanged - the reusable per-page logic now lives in
        run_audit_on_page, which SiteAuditOrchestrator also calls directly
        (once per crawled page, on one shared worker session) without going
        through this per-call worker creation."""
        artifacts_dir = Path(self.config.artifacts_path) / audit_id
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        gemini_client = create_agent_service(self.config).client
        k2_client = create_k2horizon_client(self.config)

        async with PlaywrightWorker(
            run_id=audit_id,
            artifacts_dir=artifacts_dir,
            device_name=self.config.defaults.device,
            headless=self.config.playwright.headless,
            slow_mo=self.config.playwright.slow_mo,
        ) as worker:
            observation = await worker.navigate(url, timeout=self.config.playwright.navigation_timeout)
            return await self.run_audit_on_page(
                worker, url, observation, persona_profile, gemini_client, k2_client
            )

    async def run_audit_on_page(
        self,
        worker: PlaywrightWorker,
        url: str,
        observation: Any,
        persona_profile: PersonaProfile,
        gemini_client: Any,
        k2_client: Any,
    ) -> AuditReport:
        """Per-page audit body: checks -> CTA testing -> screenshots -> both
        LLM syntheses -> AuditReport. Takes an already-initialized worker
        that has already navigated to `url` (its resulting `observation`) -
        this is the reusable unit a multi-page crawl calls once per page on
        one shared (optionally already-authenticated) worker session,
        instead of creating a brand new session - and losing any login -
        for every page."""
        raw_checks = await worker.evaluate_page_checks()
        candidates = select_cta_candidates(raw_checks)
        visual_teaser = build_visual_teaser(raw_checks)
        evidence_base = build_browsing_evidence_base(raw_checks, candidates)

        gemini_result = await self._run_vision_synthesis(
            gemini_client, url, observation, raw_checks, candidates, persona_profile
        )
        role_assignments = gemini_result.get("cta_role_assignments") or []

        overlay_annotations = merge_role_assignments(candidates, role_assignments)
        images = await capture_audit_screenshots(worker, overlay_annotations)

        tests = await self._run_cta_click_tests(worker, url, candidates, role_assignments)

        link_results = await check_footer_links(raw_checks.get("footer_nav_links") or [])
        navigation_findings = build_navigation_findings(link_results)

        k2_result = await self._run_text_synthesis(
            k2_client, url, observation, raw_checks, tests, navigation_findings, gemini_result, persona_profile
        )

        growth_navigation = dict(k2_result.get("growth_navigation") or {"score": 5.0, "findings": []})
        growth_navigation["findings"] = navigation_findings + list(growth_navigation.get("findings") or [])

        return AuditReport(
            overall_score=gemini_result["overall_score"],
            label=gemini_result["label"],
            verdict=gemini_result["verdict"],
            verdict_summary=gemini_result["verdict_summary"],
            honest_verdict=gemini_result["honest_verdict"],
            context=gemini_result["context"],
            story=gemini_result.get("story") or [],
            scores=gemini_result["scores"],
            growth={
                "seo": k2_result["growth_seo"],
                "visual_design": gemini_result["growth_visual_design"],
                "navigation": growth_navigation,
                "strategic_options": k2_result.get("growth_strategic_options") or [],
            },
            visual_teaser=visual_teaser,
            strengths=gemini_result.get("strengths") or [],
            decision_gaps=gemini_result.get("decision_gaps") or [],
            jargon_terms=k2_result.get("jargon_terms") or [],
            browsing_evidence={
                "total_interactive_elements": evidence_base["total_interactive_elements"],
                "safe_cta_candidates": evidence_base["safe_cta_candidates"],
                "tested_count": len(tests),
                "primary_label": evidence_base["primary_label"],
                "annotations": [
                    {
                        "role": a.get("role", "cta"),
                        "text": a.get("text", ""),
                        "color": a.get("color", "#ff00ff"),
                        "label": a.get("label", ""),
                    }
                    for a in overlay_annotations
                ],
                "tests": tests,
            },
            primary_fix=k2_result["primary_fix"],
            next_fixes=k2_result.get("next_fixes") or [],
            rewrites=k2_result.get("rewrites") or [],
            images=images,
            visitor_persona=gemini_result["visitor_persona"],
            core_web_vitals=raw_checks.get("web_vitals") or None,
            seo_checks=raw_checks.get("seo") or None,
        )

    # -- LLM synthesis -----------------------------------------------------

    async def _run_vision_synthesis(
        self,
        gemini_client: Any,
        url: str,
        observation: Any,
        raw_checks: dict,
        candidates: list[dict],
        persona_profile: PersonaProfile,
    ) -> dict:
        """Gemini (vision) call - owns everything that needs to reference what
        the page *looks like*: context, story, the 5 scores,
        growth.visual_design, strengths, decision_gaps, visitor_persona,
        overall_score/label/verdict*, and CTA semantic-role assignment."""
        image_b64 = self._encode_screenshot(observation.screenshotPath)
        candidate_payload = [
            {"index": c["index"], "text": c["text"], "tag": c.get("tag"), "above_fold": c.get("above_fold")}
            for c in candidates
        ]
        user_payload = {
            "url": url,
            "visible_text": observation.visibleText,
            "seo": raw_checks.get("seo") or {},
            "candidate_interactive_elements": candidate_payload,
            "persona": persona_profile.to_prompt_context(),
        }

        import json as _json

        user_message = [
            {
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": image_b64},
            },
            {"type": "text", "text": _json.dumps(user_payload)},
        ]

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: gemini_client.invoke_with_json_response(
                system_prompt=_GEMINI_AUDIT_SYSTEM_PROMPT,
                user_message=user_message,
                # Vision audit JSON is large; 4096 was truncating mid-object in prod.
                max_tokens=8192,
                temperature=0.5,
            ),
        )

    async def _run_text_synthesis(
        self,
        k2_client: Any,
        url: str,
        observation: Any,
        raw_checks: dict,
        tests: list[dict],
        navigation_findings: list[str],
        gemini_result: dict,
        persona_profile: PersonaProfile,
    ) -> dict:
        """k2-horizon (text-only) call - owns copy/text-only analysis:
        jargon_terms, primary_fix/next_fixes, rewrites, growth.seo,
        growth.navigation, growth.strategic_options."""
        import json as _json

        user_payload = {
            "url": url,
            "visible_text": observation.visibleText,
            "seo": raw_checks.get("seo") or {},
            "web_vitals": raw_checks.get("web_vitals") or {},
            "cta_click_tests": tests,
            "footer_link_check_findings": navigation_findings,
            "persona": persona_profile.to_prompt_context(),
            "page_context": gemini_result.get("context"),
            "page_verdict_summary": gemini_result.get("verdict_summary"),
        }

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: k2_client.invoke_with_json_response(
                system_prompt=_K2_AUDIT_SYSTEM_PROMPT,
                user_message=_json.dumps(user_payload),
                # k2-horizon is a reasoning model: response_format=json_object
                # guarantees syntax but not that reasoning stays out of the
                # budget - discovered live against real sites, where 4096
                # was sometimes exhausted by chain-of-thought before any
                # JSON was emitted at all, failing the whole page audit.
                max_tokens=8192,
                temperature=0.5,
            ),
        )

    # -- CTA click-testing ---------------------------------------------------

    async def _run_cta_click_tests(
        self,
        worker: PlaywrightWorker,
        url: str,
        candidates: list[dict],
        role_assignments: list[dict],
    ) -> list[dict]:
        """Actually click the top candidate CTAs (prioritizing whatever Gemini
        flagged as primary-cta/cta) and record what happened, restoring the
        starting page before testing the next one."""
        role_by_index = {a.get("index"): a for a in role_assignments}

        def sort_key(c: dict) -> int:
            role = role_by_index.get(c.get("index"), {}).get("role")
            return {"primary-cta": 0, "cta": 1}.get(role, 2)

        prioritized = sorted(candidates, key=sort_key)[:5]

        tests: list[dict] = []
        for candidate in prioritized:
            text = candidate.get("text", "")
            if not text:
                continue
            role_info = role_by_index.get(candidate.get("index"), {})
            label = role_info.get("label") or role_info.get("role") or "cta"

            navigated_away = False
            try:
                result_obs = await worker.tap(text)
                modal_open = await worker.detect_modal()
                if result_obs.url != url:
                    navigated_away = True
                    outcome = f"Navigated to {result_obs.url}"
                elif result_obs.consoleErrors:
                    outcome = f"Triggered a console error: {result_obs.consoleErrors[0]}"
                elif modal_open:
                    outcome = "Opened a modal/dialog overlay"
                else:
                    outcome = "No observable effect (click registered, page unchanged)"
            except Exception as e:
                modal_open = False
                outcome = f"Could not test this element: {e}"

            tests.append({"label": label, "target_text": text, "result": outcome})

            if navigated_away or modal_open:
                try:
                    await worker.navigate(url)
                except Exception as e:
                    logger.warning(f"Failed to restore starting page after CTA test: {e}")

        return tests

    # -- helpers -------------------------------------------------------------

    def _check_domain_allowlist(self, url: str) -> None:
        """Same guardrail a normal run's config enforces (core/config.py
        SecurityConfig) - an audit must not bypass it."""
        if not self.config.security.enforce_domain_allowlist:
            return
        allowed = self.config.security.allowed_domains
        if not allowed:
            return
        host = urlparse(url).hostname or ""
        if not any(host == domain or host.endswith(f".{domain}") for domain in allowed):
            raise ValueError(f"URL host '{host}' is not in the allowed domains list: {allowed}")

    def _load_persona(self, persona: str | None) -> PersonaProfile:
        if not persona:
            return CONFUSED_FIRST_TIME_USER
        return PersonaProfile.load(persona, Path(self.config.personas_path))

    @staticmethod
    def _generate_audit_id() -> str:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        return f"audit_{timestamp}_{short_uuid}"

    @staticmethod
    def _encode_screenshot(path: str) -> str:
        # ponytail: raw base64 of the PNG, no resize/compress like
        # DecisionService does for per-step vision calls - an audit makes one
        # vision call total (not one per step), so the extra Pillow work isn't
        # worth it here. Revisit if huge full-page screenshots start hitting
        # Gemini's request size limits.
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")


_GEMINI_AUDIT_SYSTEM_PROMPT = """You are a senior CRO (conversion rate optimization) consultant auditing a \
landing page for a paying client, producing a real audit report. You are given a full-page screenshot of the \
page, its visible text, deterministic SEO/meta checks, and a list of candidate interactive elements (their \
visible text and position) already detected on the page.

Ground every finding in what was ACTUALLY observed in the screenshot, the visible text, and the provided \
checks - never invent facts, competitors, or statistics not visible in the material given.

Respond with a single JSON object with EXACTLY these keys and nothing else:
{
  "overall_score": <float 0-10>,
  "label": "<short verdict tag, e.g. 'Strong concept, pre-launch friction'>",
  "verdict": "<one sentence verdict>",
  "verdict_summary": "<one paragraph verdict summary>",
  "honest_verdict": "<a blunter, more direct paragraph than verdict_summary - don't soften real problems>",
  "context": {
    "page_type": "<what kind of page this is>",
    "primary_goal": "<the page's primary conversion goal>",
    "likely_audience": "<who this page is written for>",
    "audience_awareness": "<how aware/informed that audience is assumed to be>",
    "visitor_motivation": "<why a visitor would land here>",
    "assumptions_to_respect": ["<assumption the audit should not second-guess>"]
  },
  "story": [
    {"step": "<what a first-time visitor did/noticed>", "title": "<the specific detail>", "text": "<the analytical takeaway>", "sentiment": "positive|neutral|negative"}
  ],
  "scores": [
    {"dimension": "Message & Clarity", "score": <0-10>, "rationale": "<grounded rationale>"},
    {"dimension": "Audience Fit", "score": <0-10>, "rationale": "<grounded rationale>"},
    {"dimension": "Action Path", "score": <0-10>, "rationale": "<grounded rationale>"},
    {"dimension": "Trust & Credibility", "score": <0-10>, "rationale": "<grounded rationale>"},
    {"dimension": "Content Depth", "score": <0-10>, "rationale": "<grounded rationale>"}
  ],
  "growth_visual_design": {"score": <0-10>, "findings": ["<specific visual design finding>"]},
  "strengths": ["<genuine strength, grounded in what's visible>"],
  "decision_gaps": ["<something a visitor can't tell/decide from the page as-is>"],
  "visitor_persona": "<one paragraph synthesizing a persona that frames the whole audit>",
  "cta_role_assignments": [
    {"index": <candidate index given to you>, "role": "headline|support|primary-cta|cta", "color": "<hex color, distinct per role>", "label": "<short badge label>"}
  ]
}

"scores" MUST contain exactly these 5 dimensions, in this exact order: Message & Clarity, Audience Fit, \
Action Path, Trust & Credibility, Content Depth.

"cta_role_assignments" must ONLY reference candidate indices you were given - never invent new elements. \
Assign exactly one element the role "primary-cta" (the single most important call to action on the page)."""


_K2_AUDIT_SYSTEM_PROMPT = """You are a senior copywriter and growth strategist doing the text-analysis half \
of a landing-page audit. You are given the page's visible text, deterministic SEO/meta checks, Core Web \
Vitals, the results of actually clicking the page's top candidate calls-to-action, footer-link liveness \
findings, and another consultant's context/verdict on the page (for continuity - don't contradict it \
without reason).

Ground every finding in the material given - never invent facts or numbers not present in the input.

Respond with a single JSON object with EXACTLY these keys and nothing else:
{
  "jargon_terms": ["<confusing terminology actually found in the visible text>"],
  "primary_fix": {"issue": "<the single highest-impact issue>", "why": "<why it matters>", "action": "<concrete action>"},
  "next_fixes": [{"issue": "...", "why": "...", "action": "..."}],
  "rewrites": [{"original": "<verbatim copy from visible_text>", "replacement": "<improved rewrite>"}],
  "growth_seo": {"score": <0-10>, "findings": ["<finding grounded in the seo checks given>"]},
  "growth_navigation": {"score": <0-10>, "findings": ["<finding grounded in the cta click tests / footer link findings given>"]},
  "growth_strategic_options": [{"path": "<a strategic direction>", "risk": "<the tradeoff>", "experiment": "<a concrete testable experiment>"}]
}

"rewrites" must quote real text from visible_text as "original" - never rewrite text that isn't there."""
