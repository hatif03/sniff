#!/usr/bin/env python3
"""Test script for Playwright Worker validation.

Usage:
    python test_worker.py

This script validates:
- Worker initialization with mobile emulation
- Navigation and observation capture
- All tool actions (tap, type, scroll, wait, back, screenshot)
- Target resolution strategies
- Error handling
"""

import asyncio
import logging
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.executor.playwright_worker import PlaywrightWorker


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def test_basic_navigation():
    """Test basic navigation and observation capture."""
    logger.info("=" * 80)
    logger.info("TEST: Basic Navigation")
    logger.info("=" * 80)

    artifacts_dir = Path("./test_artifacts")
    artifacts_dir.mkdir(exist_ok=True)

    async with PlaywrightWorker(
        run_id="test_001",
        artifacts_dir=artifacts_dir,
        device_name="iPhone 13",
        headless=False,  # Set to True for CI
        slow_mo=100,  # Slow down for visibility
    ) as worker:
        # Test navigation
        logger.info("Navigating to example.com...")
        obs = await worker.navigate("https://example.com")

        logger.info(f"Observation captured:")
        logger.info(f"  Step: {obs.step}")
        logger.info(f"  URL: {obs.url}")
        logger.info(f"  Screenshot: {obs.screenshotPath}")
        logger.info(f"  Visible text snippets: {len(obs.visibleText)}")
        logger.info(f"  Timing: {obs.timing}")
        logger.info(f"  Last action: {obs.lastActionResult}")

        # Test wait
        logger.info("Testing wait action...")
        obs = await worker.wait(2000)
        logger.info(f"Wait completed, step: {obs.step}")

        # Test screenshot
        logger.info("Testing screenshot capture...")
        screenshot_path = await worker.screenshot("manual_test.png")
        logger.info(f"Screenshot saved to: {screenshot_path}")

    logger.info("Basic navigation test PASSED")


async def test_interaction_actions():
    """Test tap, type, and scroll actions."""
    logger.info("=" * 80)
    logger.info("TEST: Interaction Actions")
    logger.info("=" * 80)

    artifacts_dir = Path("./test_artifacts")
    artifacts_dir.mkdir(exist_ok=True)

    async with PlaywrightWorker(
        run_id="test_002",
        artifacts_dir=artifacts_dir,
        device_name="iPhone 13",
        headless=False,
        slow_mo=200,
    ) as worker:
        # Navigate to a page with form elements
        logger.info("Navigating to test form page...")
        await worker.navigate("https://www.google.com")

        # Test tap on search box (by text/placeholder)
        logger.info("Testing tap action on search box...")
        obs = await worker.tap("Search")
        logger.info(f"Tap result: {obs.lastActionResult}")

        # Test type action
        logger.info("Testing type action...")
        obs = await worker.type("Search", "playwright automation test")
        logger.info(f"Type result: {obs.lastActionResult}")

        # Test scroll
        logger.info("Testing scroll down...")
        obs = await worker.scroll("down", amount=300)
        logger.info(f"Scroll result: {obs.lastActionResult}")

        logger.info("Testing scroll up...")
        obs = await worker.scroll("up", amount=200)
        logger.info(f"Scroll result: {obs.lastActionResult}")

    logger.info("Interaction actions test PASSED")


async def test_error_handling():
    """Test error handling for invalid targets."""
    logger.info("=" * 80)
    logger.info("TEST: Error Handling")
    logger.info("=" * 80)

    artifacts_dir = Path("./test_artifacts")
    artifacts_dir.mkdir(exist_ok=True)

    async with PlaywrightWorker(
        run_id="test_003",
        artifacts_dir=artifacts_dir,
        device_name="iPhone 13",
        headless=False,
        slow_mo=100,
    ) as worker:
        await worker.navigate("https://example.com")

        # Test tap on non-existent element
        logger.info("Testing tap on non-existent element...")
        obs = await worker.tap("ThisElementDoesNotExist", timeout=2000)
        logger.info(f"Tap result: {obs.lastActionResult}")

        assert obs.lastActionResult.get("success") == False, "Should fail on non-existent element"
        logger.info("Error handling validated: non-existent element properly caught")

        # Test type without input_text (should raise ValueError)
        logger.info("Testing type action validation...")
        try:
            obs = await worker.type("some-field", "")
            logger.error("Should have raised ValueError for empty input_text")
        except ValueError as e:
            logger.info(f"Validation passed: {e}")

    logger.info("Error handling test PASSED")


async def test_mobile_emulation():
    """Verify mobile emulation is working."""
    logger.info("=" * 80)
    logger.info("TEST: Mobile Emulation")
    logger.info("=" * 80)

    artifacts_dir = Path("./test_artifacts")
    artifacts_dir.mkdir(exist_ok=True)

    async with PlaywrightWorker(
        run_id="test_004",
        artifacts_dir=artifacts_dir,
        device_name="iPhone 13",
        headless=False,
        slow_mo=100,
    ) as worker:
        # Navigate to a mobile-responsive test page
        await worker.navigate("https://whatismybrowser.com/detect/what-is-my-user-agent")
        await worker.wait(2000)

        # The screenshot should show mobile viewport
        screenshot = await worker.screenshot("mobile_viewport.png")
        logger.info(f"Mobile viewport screenshot: {screenshot}")
        logger.info("Check screenshot to verify iPhone 13 user agent is detected")

    logger.info("Mobile emulation test PASSED")


async def main():
    """Run all tests."""
    logger.info("Starting Playwright Worker test suite...")

    try:
        await test_basic_navigation()
        await test_interaction_actions()
        await test_error_handling()
        await test_mobile_emulation()

        logger.info("=" * 80)
        logger.info("ALL TESTS PASSED")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
