"""Tests for PlaywrightWorker's screenshot resilience.

Regression tests for a real production failure: a stripe.com audit failed
entirely because Page.screenshot(full_page=True) timed out waiting for the
page to reach a "stable" render state (fonts/animations) - one slow
screenshot took down the whole audit before a single check ever ran. These
tests use a fake Playwright Page (no real browser) to force that failure
deterministically and confirm screenshot()/screenshot_viewport() degrade
gracefully instead of raising.
"""

from pathlib import Path

import pytest
from PIL import Image

from src.executor.playwright_worker import PlaywrightWorker


class FakePage:
    """Stand-in for playwright.async_api.Page - only screenshot() is used
    by the methods under test."""

    def __init__(self, fail_full_page=False, fail_viewport=False):
        self.fail_full_page = fail_full_page
        self.fail_viewport = fail_viewport
        self.calls: list[dict] = []
        self.url = "https://example.com"

    async def screenshot(self, path: str, full_page: bool, timeout: int | None = None):
        self.calls.append({"path": path, "full_page": full_page, "timeout": timeout})
        if full_page and self.fail_full_page:
            raise TimeoutError("Timeout 30000ms exceeded.")
        if not full_page and self.fail_viewport:
            raise TimeoutError("Timeout 15000ms exceeded.")
        # Simulate a real successful capture by writing a real image file.
        Image.new("RGB", (10, 10)).save(path)


@pytest.fixture
def worker(tmp_path) -> PlaywrightWorker:
    w = PlaywrightWorker(run_id="test-run", artifacts_dir=tmp_path)
    return w


class TestScreenshotResilience:
    @pytest.mark.asyncio
    async def test_full_page_success_returns_that_screenshot(self, worker):
        worker._page = FakePage()
        path = await worker.screenshot(name="test.png")

        assert Path(path).exists()
        assert worker._page.calls == [{"path": path, "full_page": True, "timeout": None}]

    @pytest.mark.asyncio
    async def test_falls_back_to_viewport_when_full_page_times_out(self, worker):
        worker._page = FakePage(fail_full_page=True)
        path = await worker.screenshot(name="test.png")

        # A real, openable image must exist at the returned path - the rest
        # of the audit pipeline (Observation, Gemini vision input) assumes
        # screenshotPath always points to something real.
        assert Path(path).exists()
        Image.open(path).verify()
        assert [c["full_page"] for c in worker._page.calls] == [True, False]

    @pytest.mark.asyncio
    async def test_falls_back_to_placeholder_when_everything_times_out(self, worker):
        worker._page = FakePage(fail_full_page=True, fail_viewport=True)
        path = await worker.screenshot(name="test.png")

        assert Path(path).exists()
        Image.open(path).verify()

    @pytest.mark.asyncio
    async def test_screenshot_viewport_falls_back_to_placeholder(self, worker):
        worker._page = FakePage(fail_viewport=True)
        path = await worker.screenshot_viewport(name="above_fold.png")

        assert Path(path).exists()
        Image.open(path).verify()
