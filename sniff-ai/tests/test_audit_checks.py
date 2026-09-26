"""Tests for src/evidence/audit_checks.py.

Covers:
- PlaywrightWorker.evaluate_page_checks() graceful per-check degradation,
  using a fake Page whose evaluate() throws for one sub-check.
- The pure parsing functions that turn the raw dict into AuditReport pieces.
- check_footer_links() HEAD-then-GET-fallback behavior against a fake httpx
  AsyncClient (no real network).
"""

import pytest

from src.evidence import audit_checks
from src.evidence.audit_checks import (
    build_browsing_evidence_base,
    build_navigation_findings,
    build_visual_teaser,
    check_footer_links,
    select_cta_candidates,
)
from src.executor.playwright_worker import PlaywrightWorker


class FakePage:
    """Stands in for a Playwright Page - evaluate() dispatches on script content."""

    async def evaluate(self, script: str):
        if "getComputedStyle" in script:
            return {
                "colors": [{"value": "rgb(37, 99, 235)", "count": 12}],
                "fonts": [{"value": "Inter", "count": 8}],
            }
        if "getBoundingClientRect" in script and "button" in script:
            # Simulate a hostile site's CSP blocking this inline script.
            raise RuntimeError("Content Security Policy blocked inline script")
        if 'meta[name="description"]' in script:
            return {
                "title": "Join the waitlist",
                "title_length": 18,
                "meta_description": "Sign up early",
                "meta_description_length": 13,
                "h1_count": 1,
                "img_count": 4,
                "img_alt_count": 3,
                "img_alt_pct": 75,
                "has_canonical": True,
                "has_viewport": True,
            }
        if "largest-contentful-paint" in script:
            return {"lcp": 1200.5, "fcp": 800.0, "cls": 0.02}
        if "footer a[href]" in script:
            return ["https://example.com/privacy", "https://example.com/terms"]
        raise AssertionError(f"Unexpected script passed to evaluate(): {script[:60]}")


@pytest.mark.asyncio
async def test_evaluate_page_checks_degrades_broken_subcheck(tmp_path):
    worker = PlaywrightWorker(run_id="test_audit", artifacts_dir=tmp_path)
    worker._page = FakePage()  # bypass initialize(); no real browser needed

    results = await worker.evaluate_page_checks()

    # Working sub-checks return real data.
    assert results["colors_fonts"]["colors"][0]["value"] == "rgb(37, 99, 235)"
    assert results["seo"]["title"] == "Join the waitlist"
    assert results["web_vitals"]["lcp"] == 1200.5
    assert results["footer_nav_links"] == ["https://example.com/privacy", "https://example.com/terms"]

    # The interactive-elements sub-check threw - it degrades to its default,
    # the whole audit doesn't blow up.
    assert results["interactive_elements"] == []


def test_build_visual_teaser():
    raw = {
        "colors_fonts": {
            "colors": [{"value": "rgb(0,0,0)", "count": 10}, {"value": "rgb(255,255,255)", "count": 5}],
            "fonts": [{"value": "Inter", "count": 7}],
        }
    }
    teaser = build_visual_teaser(raw)
    assert teaser["dominant_colors"] == [
        {"color": "rgb(0,0,0)", "uses": 10},
        {"color": "rgb(255,255,255)", "uses": 5},
    ]
    assert teaser["font_families"] == [{"family": "Inter", "uses": 7}]


def test_build_visual_teaser_handles_missing_data():
    assert build_visual_teaser({}) == {"dominant_colors": [], "font_families": []}


def test_select_cta_candidates_sorts_dedupes_and_caps():
    raw = {
        "interactive_elements": [
            {"index": 0, "text": "Learn more", "prominence": 100},
            {"index": 1, "text": "Join the waitlist", "prominence": 900},
            {"index": 2, "text": "join the waitlist", "prominence": 850},  # dupe (case-insensitive)
            {"index": 3, "text": "", "prominence": 500},  # no text, skipped
            {"index": 4, "text": "Contact us", "prominence": 400},
            {"index": 5, "text": "About", "prominence": 300},
        ]
    }
    candidates = select_cta_candidates(raw, top_n=3)
    assert [c["text"] for c in candidates] == ["Join the waitlist", "Contact us", "About"]


def test_build_browsing_evidence_base():
    raw = {"interactive_elements": [{"text": "a"}, {"text": "b"}, {"text": "c"}]}
    candidates = [{"text": "Join the waitlist"}, {"text": "Contact us"}]
    base = build_browsing_evidence_base(raw, candidates)
    assert base == {
        "total_interactive_elements": 3,
        "safe_cta_candidates": 2,
        "primary_label": "Join the waitlist",
    }


def test_build_browsing_evidence_base_empty():
    base = build_browsing_evidence_base({}, [])
    assert base == {"total_interactive_elements": 0, "safe_cta_candidates": 0, "primary_label": ""}


def test_build_navigation_findings_positive():
    findings = build_navigation_findings([{"url": "https://x/a", "status": 200, "ok": True}])
    assert "POSITIVE" in findings[0]
    assert "1 tested footer links" in findings[0]


def test_build_navigation_findings_negative():
    results = [
        {"url": "https://x/a", "status": 200, "ok": True},
        {"url": "https://x/broken", "status": 404, "ok": False},
    ]
    findings = build_navigation_findings(results)
    assert "NEGATIVE" in findings[0]
    assert "https://x/broken" in findings[0]


def test_build_navigation_findings_no_links():
    findings = build_navigation_findings([])
    assert "SKIPPED" in findings[0]


class _FakeResponse:
    def __init__(self, status_code: int):
        self.status_code = status_code


class _FakeAsyncClient:
    """Stands in for httpx.AsyncClient - HEAD returns 405 for one URL to
    exercise the GET fallback, and a plain 200 for the other."""

    def __init__(self, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def head(self, url):
        if "no-head" in url:
            return _FakeResponse(405)
        return _FakeResponse(200)

    async def get(self, url):
        return _FakeResponse(200)


@pytest.mark.asyncio
async def test_check_footer_links_head_then_get_fallback(monkeypatch):
    monkeypatch.setattr(audit_checks.httpx, "AsyncClient", _FakeAsyncClient)

    results = await check_footer_links(["https://x/ok", "https://x/no-head"])

    assert results[0] == {"url": "https://x/ok", "status": 200, "ok": True}
    assert results[1] == {"url": "https://x/no-head", "status": 200, "ok": True}


@pytest.mark.asyncio
async def test_check_footer_links_empty_list():
    assert await check_footer_links([]) == []
