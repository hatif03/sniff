"""Playwright Execution Worker for mobile browser automation.

Responsibilities:
- Initialize and manage Playwright browser session with mobile emulation
- Execute tool actions: tap, type, scroll, wait, back, screenshot
- Capture structured observations after each action
- Return Observation objects to orchestrator

Architecture boundary: Worker executes tools ONLY, never makes decisions.
"""

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from playwright.async_api import Browser, BrowserContext, Page, async_playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from ..core.models import ActionResult, Observation

logger = logging.getLogger(__name__)


class PlaywrightWorker:
    """Execution Worker for browser automation with mobile emulation.

    Manages Playwright session lifecycle and exposes deterministic tool interface
    for orchestrator to invoke.
    """

    def __init__(
        self,
        run_id: str,
        artifacts_dir: Path,
        device_name: str = "iPhone 13",
        headless: bool = False,
        slow_mo: int = 0,
        storage_state: dict | str | None = None,
    ):
        """Initialize Playwright worker.

        Args:
            run_id: Unique identifier for this run
            artifacts_dir: Directory to store screenshots and traces
            device_name: Playwright device to emulate (default: iPhone 13)
            headless: Whether to run in headless mode
            slow_mo: Milliseconds to slow down operations (useful for demos)
            storage_state: Optional pre-authenticated Playwright storage_state
                (cookies/localStorage) to start the browser context already
                logged in - the "paste an existing session" auth path for a
                site audit, as an alternative to login(). Never persisted by
                this class; the caller owns its lifecycle.
        """
        self.run_id = run_id
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        self.device_name = device_name
        self.headless = headless
        self.slow_mo = slow_mo
        self.storage_state = storage_state

        # Playwright objects
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

        # State tracking
        self.step_count = 0
        self.last_action_result: ActionResult | None = None

        # Performance tracking
        self._navigation_start_time: float | None = None
        self._ttfb: int | None = None
        self._dom_ready: int | None = None

    async def initialize(self) -> None:
        """Bootstrap Playwright session with mobile emulation.

        Sets up browser context with:
        - Mobile device emulation
        - Network event monitoring
        - Console error capture
        - Performance timing collection
        """
        logger.info(f"Initializing Playwright worker for run {self.run_id}")

        self._playwright = await async_playwright().start()

        # Launch browser with mobile device emulation
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            slow_mo=self.slow_mo,
        )

        # Get device configuration
        device = self._playwright.devices.get(self.device_name)
        if not device:
            raise ValueError(f"Unknown device: {self.device_name}")

        # Create context with device emulation
        self._context = await self._browser.new_context(
            **device,
            locale="en-US",
            timezone_id="America/New_York",
            record_video_dir=str(self.artifacts_dir / "videos") if not self.headless else None,
            **({"storage_state": self.storage_state} if self.storage_state else {}),
        )

        # Enable tracing for debugging
        await self._context.tracing.start(screenshots=True, snapshots=True)

        # Create page
        self._page = await self._context.new_page()

        # Setup event listeners for observation capture
        self._setup_event_listeners()

        logger.info(f"Playwright session initialized with device: {self.device_name}")

    def _setup_event_listeners(self) -> None:
        """Configure event listeners for observation capture."""
        if not self._page:
            return

        # Console error capture
        self._page.on("console", self._handle_console)
        self._page.on("pageerror", self._handle_page_error)

        # Network monitoring
        self._page.on("response", self._handle_response)
        self._page.on("requestfailed", self._handle_request_failed)

    def _handle_console(self, msg) -> None:
        """Capture console messages for error detection."""
        if msg.type in ("error", "warning"):
            logger.debug(f"Console {msg.type}: {msg.text}")

    def _handle_page_error(self, error) -> None:
        """Capture page errors."""
        logger.error(f"Page error: {error}")

    def _handle_response(self, response) -> None:
        """Monitor response timing for performance metrics."""
        # Track TTFB on first response after navigation
        if self._navigation_start_time and not self._ttfb:
            asyncio.create_task(response.request.timing())

    def _handle_request_failed(self, request) -> None:
        """Capture failed network requests."""
        logger.warning(f"Request failed: {request.url} - {request.failure}")

    async def navigate(self, url: str, timeout: int = 30000) -> Observation:
        """Navigate to URL and capture observation.

        Args:
            url: Target URL
            timeout: Navigation timeout in milliseconds

        Returns:
            Observation with post-navigation state
        """
        if not self._page:
            raise RuntimeError("Worker not initialized. Call initialize() first.")

        logger.info(f"Navigating to {url}")
        start_time = time.time()

        try:
            await self._page.goto(url, timeout=timeout, wait_until="domcontentloaded")

            # Capture timing
            performance_timing = await self._page.evaluate("""
                () => {
                    const timing = performance.timing;
                    return {
                        ttfb: timing.responseStart - timing.requestStart,
                        domReady: timing.domContentLoadedEventEnd - timing.navigationStart
                    };
                }
            """)
            self._ttfb = performance_timing.get("ttfb", 0)
            self._dom_ready = performance_timing.get("domReady", 0)

            duration_ms = int((time.time() - start_time) * 1000)

            # Record successful navigation
            self.last_action_result = ActionResult(
                success=True,
                action="navigate",
                status="success",
                target=url,
                durationMs=duration_ms,
                details={"timing": performance_timing}
            )

        except PlaywrightTimeoutError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Navigation timeout: {e}")
            self.last_action_result = ActionResult(
                success=False,
                action="navigate",
                status="timeout",
                target=url,
                error=f"Navigation timeout after {timeout}ms",
                durationMs=duration_ms
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Navigation failed: {e}")
            self.last_action_result = ActionResult(
                success=False,
                action="navigate",
                status="failed",
                target=url,
                error=str(e),
                durationMs=duration_ms
            )

        return await self.capture_observation()

    async def tap(self, target: str, timeout: int = 5000) -> Observation:
        """Tap/click on target element.

        Args:
            target: Element identifier (text content, selector, or coordinates)
            timeout: Action timeout in milliseconds

        Returns:
            Observation after tap execution
        """
        if not self._page:
            raise RuntimeError("Worker not initialized. Call initialize() first.")

        logger.info(f"Tapping target: {target}")
        start_time = time.time()

        try:
            # Try multiple resolution strategies
            element = await self._resolve_target(target, timeout)

            if element:
                await element.click()
                duration_ms = int((time.time() - start_time) * 1000)
                self.last_action_result = ActionResult(
                    success=True,
                    action="tap",
                    status="success",
                    target=target,
                    durationMs=duration_ms,
                    details={"resolved": True}
                )
            else:
                duration_ms = int((time.time() - start_time) * 1000)
                self.last_action_result = ActionResult(
                    success=False,
                    action="tap",
                    status="element_not_found",
                    target=target,
                    error=f"Could not resolve target: {target}",
                    durationMs=duration_ms
                )

        except PlaywrightTimeoutError:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Tap timeout on target: {target}")
            self.last_action_result = ActionResult(
                success=False,
                action="tap",
                status="timeout",
                target=target,
                error=f"Element not found within {timeout}ms",
                durationMs=duration_ms
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Tap failed: {e}")
            self.last_action_result = ActionResult(
                success=False,
                action="tap",
                status="failed",
                target=target,
                error=str(e),
                durationMs=duration_ms
            )

        # Wait briefly for UI updates
        await asyncio.sleep(0.5)
        return await self.capture_observation()

    async def type(self, target: str, input_text: str, timeout: int = 5000) -> Observation:
        """Type text into target input field.

        Args:
            target: Input field identifier
            input_text: Text to type (REQUIRED)
            timeout: Action timeout in milliseconds

        Returns:
            Observation after typing
        """
        if not self._page:
            raise RuntimeError("Worker not initialized. Call initialize() first.")

        if not input_text:
            raise ValueError("input_text is REQUIRED for type action")

        logger.info(f"Typing into target: {target}")
        start_time = time.time()

        try:
            element = await self._resolve_target(target, timeout)

            if element:
                # Check if element is fillable before attempting to type
                is_fillable = await self._is_element_fillable(element)

                if not is_fillable:
                    # Element is not fillable (likely a dropdown/select/combobox)
                    duration_ms = int((time.time() - start_time) * 1000)
                    element_type = await self._get_element_type(element)

                    error_msg = f"Cannot type into {element_type}. "
                    if element_type in ["select", "combobox", "listbox"]:
                        error_msg += "This is a dropdown/select element - use TAP action to click and open it, then TAP the desired option."
                    else:
                        error_msg += "Element is not a text input field."

                    logger.warning(error_msg)
                    self.last_action_result = ActionResult(
                        success=False,
                        action="type",
                        status="invalid_element_type",
                        target=target,
                        error=error_msg,
                        durationMs=duration_ms,
                        details={"element_type": element_type, "suggestion": "use_tap_instead"}
                    )
                else:
                    # Element is fillable, proceed
                    await element.fill("")
                    # Type new content
                    await element.type(input_text, delay=50)  # 50ms delay per char for realism

                    duration_ms = int((time.time() - start_time) * 1000)
                    self.last_action_result = ActionResult(
                        success=True,
                        action="type",
                        status="success",
                        target=target,
                        durationMs=duration_ms,
                        details={"text_length": len(input_text), "resolved": True}
                    )
            else:
                duration_ms = int((time.time() - start_time) * 1000)
                self.last_action_result = ActionResult(
                    success=False,
                    action="type",
                    status="element_not_found",
                    target=target,
                    error=f"Could not resolve target: {target}",
                    durationMs=duration_ms
                )

        except PlaywrightTimeoutError:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Type timeout on target: {target}")
            self.last_action_result = ActionResult(
                success=False,
                action="type",
                status="timeout",
                target=target,
                error=f"Element not found within {timeout}ms",
                durationMs=duration_ms
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Type failed: {e}")
            self.last_action_result = ActionResult(
                success=False,
                action="type",
                status="failed",
                target=target,
                error=str(e),
                durationMs=duration_ms
            )

        await asyncio.sleep(0.5)
        return await self.capture_observation()

    async def scroll(self, direction: Literal["up", "down"] = "down", amount: int = 300) -> Observation:
        """Scroll viewport in specified direction.

        Args:
            direction: Scroll direction (up or down)
            amount: Scroll distance in pixels

        Returns:
            Observation after scroll
        """
        if not self._page:
            raise RuntimeError("Worker not initialized. Call initialize() first.")

        logger.info(f"Scrolling {direction} by {amount}px")
        start_time = time.time()

        try:
            scroll_delta = amount if direction == "down" else -amount
            await self._page.evaluate(f"window.scrollBy(0, {scroll_delta})")

            duration_ms = int((time.time() - start_time) * 1000)
            self.last_action_result = ActionResult(
                success=True,
                action="scroll",
                status="success",
                target=direction,
                durationMs=duration_ms,
                details={"amount": amount}
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Scroll failed: {e}")
            self.last_action_result = ActionResult(
                success=False,
                action="scroll",
                status="failed",
                target=direction,
                error=str(e),
                durationMs=duration_ms
            )

        await asyncio.sleep(0.3)
        return await self.capture_observation()

    async def wait(self, duration: int = 1000) -> Observation:
        """Explicit wait for specified duration.

        Args:
            duration: Wait time in milliseconds

        Returns:
            Observation after wait
        """
        logger.info(f"Waiting {duration}ms")
        start_time = time.time()

        try:
            await asyncio.sleep(duration / 1000)
            duration_ms = int((time.time() - start_time) * 1000)
            self.last_action_result = ActionResult(
                success=True,
                action="wait",
                status="success",
                target=f"{duration}ms",
                durationMs=duration_ms,
                details={"requested_duration_ms": duration}
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Wait failed: {e}")
            self.last_action_result = ActionResult(
                success=False,
                action="wait",
                status="failed",
                target=f"{duration}ms",
                error=str(e),
                durationMs=duration_ms
            )

        return await self.capture_observation()

    async def back(self) -> Observation:
        """Navigate back using browser history.

        Returns:
            Observation after navigation
        """
        if not self._page:
            raise RuntimeError("Worker not initialized. Call initialize() first.")

        logger.info("Navigating back")
        start_time = time.time()

        try:
            await self._page.go_back()
            duration_ms = int((time.time() - start_time) * 1000)
            self.last_action_result = ActionResult(
                success=True,
                action="back",
                status="success",
                target="browser_history",
                durationMs=duration_ms
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Back navigation failed: {e}")
            self.last_action_result = ActionResult(
                success=False,
                action="back",
                status="failed",
                target="browser_history",
                error=str(e),
                durationMs=duration_ms
            )

        await asyncio.sleep(0.5)
        return await self.capture_observation()

    async def screenshot(self, name: str | None = None) -> str:
        """Capture screenshot of current page state.

        A full-page capture can hang waiting for the page to reach a
        "stable" render state (fonts/animations settling) on a heavy site -
        confirmed live: stripe.com timed out here and failed an entire
        audit that never got to run a single check as a result. Falls back
        to a cheaper viewport-only capture, then to a placeholder image, so
        a slow/stuck screenshot degrades the result instead of losing it.

        Args:
            name: Optional custom screenshot name

        Returns:
            Absolute path to saved screenshot
        """
        if not self._page:
            raise RuntimeError("Worker not initialized. Call initialize() first.")

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        filename = name or f"step_{self.step_count}_{timestamp}.png"
        screenshot_path = self.artifacts_dir / filename

        try:
            await self._page.screenshot(path=str(screenshot_path), full_page=True)
        except Exception as e:
            logger.warning(f"Full-page screenshot failed ({e}), retrying viewport-only")
            try:
                await self._page.screenshot(path=str(screenshot_path), full_page=False, timeout=15000)
            except Exception as e2:
                logger.warning(f"Viewport screenshot also failed ({e2}), using a placeholder image")
                self._write_placeholder_screenshot(screenshot_path)

        logger.debug(f"Screenshot saved: {screenshot_path}")
        return str(screenshot_path.absolute())

    def _write_placeholder_screenshot(self, path: Path) -> None:
        """A minimal blank image so a fully-failed capture still leaves a
        valid file at the expected path - callers (Observation,
        the Gemini vision call, the dashboard's screenshot viewer) all
        assume screenshotPath points to a real, openable image."""
        from PIL import Image

        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (1280, 720), color=(240, 240, 240)).save(path)

    async def evaluate_page_checks(self) -> dict[str, Any]:
        """Run deterministic landing-page audit checks (colors/fonts sampling,
        interactive-element enumeration, SEO/meta DOM queries, Core Web Vitals,
        footer/nav link collection).

        Each sub-check is independently guarded: if one throws (e.g. a hostile
        site's CSP blocks inline scripts), that section degrades to an empty
        default instead of failing the whole audit.

        Returns:
            Raw dict with keys: colors, fonts, interactive_elements, seo,
            web_vitals, footer_nav_links. See src/evidence/audit_checks.py
            for the JS source and the pure functions that turn this into
            AuditReport sections.
        """
        if not self._page:
            raise RuntimeError("Worker not initialized. Call initialize() first.")

        from ..evidence.audit_checks import (
            COLOR_FONT_SAMPLING_JS,
            FOOTER_NAV_LINKS_JS,
            INTERACTIVE_ELEMENTS_JS,
            SEO_META_JS,
            WEB_VITALS_JS,
        )

        checks: list[tuple[str, str, Any]] = [
            ("colors_fonts", COLOR_FONT_SAMPLING_JS, {"colors": [], "fonts": []}),
            ("interactive_elements", INTERACTIVE_ELEMENTS_JS, []),
            ("seo", SEO_META_JS, {}),
            ("web_vitals", WEB_VITALS_JS, {"lcp": None, "fcp": None, "cls": None}),
            ("footer_nav_links", FOOTER_NAV_LINKS_JS, []),
        ]

        results: dict[str, Any] = {}
        for key, script, default in checks:
            try:
                results[key] = await self._page.evaluate(script)
            except Exception as e:
                logger.warning(f"Audit check '{key}' failed, using default: {e}")
                results[key] = default
        return results

    async def get_page_links(self) -> list[str]:
        """Raw href values of every <a href> on the current page - the
        site-audit crawler's link-discovery source (site_crawl.py filters/
        normalizes these into same-origin candidate URLs)."""
        if not self._page:
            raise RuntimeError("Worker not initialized. Call initialize() first.")
        try:
            return await self._page.evaluate(
                "Array.from(document.querySelectorAll('a[href]')).map(a => a.getAttribute('href'))"
            )
        except Exception as e:
            logger.warning(f"Link discovery failed on {self._page.url}: {e}")
            return []

    async def login(self, login_url: str, username: str, password: str, timeout: int = 15000) -> bool:
        """Log in once via a real form submission, then leave the resulting
        session on this worker's browser context - every subsequent
        navigate() call on this same worker reuses it automatically (no
        storage_state export/import needed for this path; that mechanism is
        only for the separate "paste an existing session" auth mode handled
        at context-creation time via the constructor's storage_state param).

        The password is used exactly once, right here, and is never written
        to a log line, a return value, or any persisted state - only whether
        login looked successful (a bool) is reported back.

        Best-effort heuristic (no site-specific config): finds the first
        password field on the login page, the nearest text/email field
        before it, fills both, and submits. Good enough for a standard
        single-step username+password form; anything more exotic (multi-step
        SSO, CAPTCHA, 2FA) is out of scope - report the login as failed
        rather than guess further.
        """
        if not self._page:
            raise RuntimeError("Worker not initialized. Call initialize() first.")

        try:
            await self._page.goto(login_url, timeout=timeout, wait_until="domcontentloaded")

            password_field = self._page.locator("input[type='password']").first
            await password_field.wait_for(state="visible", timeout=timeout)

            identifier_field = self._page.locator(
                "input[type='email'], input[type='text'], input[name*='user' i], input[name*='email' i]"
            ).first
            await identifier_field.fill(username, timeout=timeout)
            await password_field.fill(password, timeout=timeout)

            submit_button = self._page.locator("button[type='submit'], input[type='submit']").first
            if await submit_button.count() > 0:
                await submit_button.click(timeout=timeout)
            else:
                await password_field.press("Enter")

            await self._page.wait_for_load_state("domcontentloaded", timeout=timeout)
            still_on_login = self._page.url.rstrip("/") == login_url.rstrip("/")
            still_has_password_field = await self._page.locator("input[type='password']").count() > 0
            return not (still_on_login and still_has_password_field)
        except Exception as e:
            logger.warning(f"Login at {login_url} failed: {e}")
            return False

    async def detect_modal(self) -> bool:
        """Cheap heuristic check for a dialog/modal overlay having appeared.

        Used by CTA click-testing to distinguish "opened a modal" from
        "no observable effect" when the URL didn't change.
        """
        if not self._page:
            raise RuntimeError("Worker not initialized. Call initialize() first.")
        try:
            return bool(
                await self._page.evaluate(
                    "() => !!document.querySelector('[role=\"dialog\"], dialog[open], [aria-modal=\"true\"]')"
                )
            )
        except Exception as e:
            logger.debug(f"Modal detection failed: {e}")
            return False

    async def screenshot_viewport(self, name: str | None = None) -> str:
        """Capture a viewport-only (non-full-page) screenshot.

        Args:
            name: Optional custom screenshot name

        Returns:
            Absolute path to saved screenshot
        """
        if not self._page:
            raise RuntimeError("Worker not initialized. Call initialize() first.")

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        filename = name or f"viewport_{timestamp}.png"
        screenshot_path = self.artifacts_dir / filename

        try:
            await self._page.screenshot(path=str(screenshot_path), full_page=False)
        except Exception as e:
            logger.warning(f"Viewport screenshot failed ({e}), using a placeholder image")
            self._write_placeholder_screenshot(screenshot_path)

        logger.debug(f"Viewport screenshot saved: {screenshot_path}")
        return str(screenshot_path.absolute())

    async def screenshot_with_overlay(
        self, annotations: list[dict[str, Any]], name: str | None = None
    ) -> str:
        """Inject a colored annotation overlay for the given candidates, capture
        a viewport screenshot, then remove the overlay so subsequent
        interactions (CTA click-testing) aren't affected by injected nodes.

        Args:
            annotations: list of {rect: {x,y,width,height}, color, label} dicts
            name: Optional custom screenshot name

        Returns:
            Absolute path to saved screenshot
        """
        if not self._page:
            raise RuntimeError("Worker not initialized. Call initialize() first.")

        from ..evidence.screenshot_annotator import build_overlay_script

        try:
            await self._page.evaluate(build_overlay_script(annotations))
        except Exception as e:
            logger.warning(f"Overlay injection failed, capturing plain screenshot: {e}")

        path = await self.screenshot_viewport(name=name)

        try:
            await self._page.evaluate(
                "() => document.querySelectorAll('[data-sniff-audit-overlay]').forEach(el => el.remove())"
            )
        except Exception as e:
            logger.debug(f"Overlay cleanup failed (non-fatal): {e}")

        return path

    async def capture_observation(self) -> Observation:
        """Capture complete observation of current browser state.

        Returns:
            Structured Observation with URL, screenshot, text, timing, errors
        """
        if not self._page:
            raise RuntimeError("Worker not initialized. Call initialize() first.")

        self.step_count += 1

        # Capture screenshot
        screenshot_path = await self.screenshot()

        # Extract visible text
        visible_text = await self._extract_visible_text()

        # Gather console errors
        console_errors = await self._get_console_errors()

        # Gather network events
        network_events = await self._get_network_events()

        # Build observation
        observation = Observation(
            runId=self.run_id,
            step=self.step_count,
            url=self._page.url,
            screenshotPath=screenshot_path,
            visibleText=visible_text,
            timing={
                "ttfb": self._ttfb or 0,
                "domReady": self._dom_ready or 0,
            },
            consoleErrors=console_errors,
            networkEvents=network_events,
            lastActionResult=self.last_action_result.model_dump() if self.last_action_result else {}
        )

        logger.debug(f"Captured observation for step {self.step_count}")
        return observation

    async def _is_element_fillable(self, element: Any) -> bool:
        """Check if element can accept text input (fill/type).

        Args:
            element: Playwright locator or element handle

        Returns:
            True if element is input/textarea/contenteditable, False otherwise
        """
        try:
            # Check if element is editable
            is_editable = await element.is_editable()
            return is_editable
        except Exception as e:
            logger.debug(f"Could not check if element is fillable: {e}")
            return False

    async def _get_element_type(self, element: Any) -> str:
        """Get descriptive type of element for error messages.

        Args:
            element: Playwright locator or element handle

        Returns:
            Element type description (e.g., "combobox", "select", "div")
        """
        try:
            # Try to get role attribute first (most descriptive)
            role = await element.get_attribute("role")
            if role:
                return role

            # Fall back to tag name
            tag_name = await element.evaluate("el => el.tagName")
            return tag_name.lower() if tag_name else "unknown"
        except Exception as e:
            logger.debug(f"Could not determine element type: {e}")
            return "unknown"

    async def _resolve_target(self, target: str, timeout: int) -> Any:
        """Resolve target specification to Playwright element locator.

        Follows Playwright best practices hierarchy:
        FOR INPUT FIELDS:
          1. Data attributes (data-testid, data-cy) - most stable
          2. getByLabel - finds associated input via label
          3. getByPlaceholder - backup for inputs
          4. getByRole('textbox') - semantic/accessible
          5. Semantic selectors (input[name=...])

        FOR BUTTONS/LINKS:
          1. Data attributes
          2. getByRole('button'/'link')
          3. getByText - button/link text content

        See: https://github.com/lackeyjb/playwright-skill/blob/main/skills/playwright-skill/API_REFERENCE.md

        Args:
            target: Target specification
            timeout: Resolution timeout

        Returns:
            Playwright ElementHandle or None
        """
        if not self._page:
            return None

        # Strategy 1: Direct CSS selector (data attributes or IDs)
        if target.startswith("#") or target.startswith(".") or target.startswith("["):
            try:
                element = await self._page.wait_for_selector(target, timeout=timeout)
                if element:
                    return element
            except PlaywrightTimeoutError:
                pass

        # Strategy 2: getByLabel - PREFERRED for input fields (finds associated input)
        try:
            locator = self._page.get_by_label(target, exact=False).first
            await locator.wait_for(state="visible", timeout=min(timeout, 3000))
            if await locator.count() > 0:
                logger.info(f"Found input via label: '{target}'")
                return locator
        except Exception as e:
            logger.debug(f"getByLabel failed for '{target}': {e}")

        # Strategy 3: getByPlaceholder - GOOD for input fields
        try:
            locator = self._page.get_by_placeholder(target, exact=False).first
            await locator.wait_for(state="visible", timeout=min(timeout, 3000))
            if await locator.count() > 0:
                logger.info(f"Found input with placeholder: '{target}'")
                return locator
        except Exception as e:
            logger.debug(f"getByPlaceholder failed for '{target}': {e}")

        # Strategy 4: getByRole - GOOD for semantic selection (buttons, textboxes, links)
        roles_to_try = [
            ("textbox", "textbox"),  # Try textbox first for inputs
            ("button", "button"),
            ("link", "link"),
        ]
        for role_name, role_desc in roles_to_try:
            try:
                locator = self._page.get_by_role(role_name, name=target, exact=False).first
                await locator.wait_for(state="visible", timeout=min(timeout, 2000))
                if await locator.count() > 0:
                    logger.info(f"Found {role_desc} with name: '{target}'")
                    return locator
            except PlaywrightTimeoutError:
                continue
            except Exception as e:
                logger.debug(f"Role {role_desc} match failed: {e}")
                continue

        # Strategy 5: Text content (GOOD for buttons/links, NOT for inputs)
        text_variations = [target, target.lower(), target.upper(), target.title()]
        for text_var in text_variations:
            try:
                locator = self._page.get_by_text(text_var, exact=False).first
                await locator.wait_for(state="visible", timeout=min(timeout, 2000))
                if await locator.count() > 0:
                    logger.info(f"Found element with text: '{text_var}'")
                    return locator
            except PlaywrightTimeoutError:
                continue
            except Exception as e:
                logger.debug(f"Text match failed for '{text_var}': {e}")
                continue

        # Strategy 6: Semantic HTML selectors - OK for inputs
        if any(keyword in target.lower() for keyword in ['email', 'password', 'name', 'phone', 'address', 'input', 'field']):
            keywords = [w for w in target.lower().split() if len(w) > 2 and w not in ['input', 'field', 'the', 'your', 'enter']]
            if keywords:
                key_word = keywords[0]
                semantic_selectors = [
                    f"input[name*='{key_word}' i]",
                    f"input[id*='{key_word}' i]",
                    f"textarea[name*='{key_word}' i]",
                    "input[type='email']" if 'email' in target.lower() else None,
                    "input[type='password']" if 'password' in target.lower() else None,
                    "input[type='tel']" if 'phone' in target.lower() else None,
                ]
                for selector in semantic_selectors:
                    if selector:
                        try:
                            locator = self._page.locator(selector).first
                            await locator.wait_for(state="visible", timeout=min(timeout, 2000))
                            if await locator.count() > 0:
                                logger.info(f"Found input via semantic selector: {selector}")
                                return locator
                        except Exception:
                            continue

        # Strategy 7: ARIA label
        try:
            locator = self._page.locator(f"[aria-label*='{target}' i]").first
            await locator.wait_for(state="visible", timeout=min(timeout, 2000))
            if await locator.count() > 0:
                logger.info(f"Found element via aria-label: '{target}'")
                return locator
        except Exception:
            pass

        # Strategy 8: XPath with contains (very flexible)
        try:
            xpath = f"//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{target.lower()}') and (self::button or self::a or self::span[@role='button'] or self::div[@role='button'])]"
            element = await self._page.locator(f"xpath={xpath}").first
            if await element.count() > 0:
                logger.info("Found element via XPath text match")
                return element
        except Exception:
            pass

        # Strategy 9: Data attributes (data-testid, data-action, etc.)
        try:
            locator = self._page.locator(f"[data-testid*='{target}' i], [data-action*='{target}' i], [data-cy*='{target}' i]").first
            await locator.wait_for(state="visible", timeout=min(timeout, 2000))
            if await locator.count() > 0:
                logger.info("Found element via data attribute")
                return locator
        except Exception:
            pass

        # Strategy 10: Partial word matching - split target and match any word
        try:
            # Extract meaningful words (>2 chars) from target
            words = [w.strip() for w in target.lower().split() if len(w.strip()) > 2]
            if words:
                for word in words:
                    # Try to find any button/link containing this word
                    xpath = f"//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{word}') and (self::button or self::a or self::span[@role='button'] or self::div[@role='button'])]"
                    element = await self._page.locator(f"xpath={xpath}").first
                    if await element.count() > 0:
                        logger.info(f"Partial word match: '{word}' found in element")
                        return element
        except Exception as e:
            logger.debug(f"Partial word matching failed: {e}")

        # Strategy 11: Common semantic synonyms for signup/account actions
        semantic_synonyms = {
            'sign': ['join', 'register', 'create', 'open', 'start', 'begin'],
            'signup': ['register', 'join', 'create account', 'open account', 'get started'],
            'register': ['sign up', 'join', 'create account', 'open account'],
            'account': ['profile', 'user', 'member'],
            'create': ['open', 'start', 'begin', 'new'],
        }

        try:
            target_lower = target.lower()
            for key_word, synonyms in semantic_synonyms.items():
                if key_word in target_lower:
                    for synonym in synonyms:
                        # Try each synonym
                        xpath = f"//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{synonym}') and (self::button or self::a or self::span[@role='button'] or self::div[@role='button'])]"
                        element = await self._page.locator(f"xpath={xpath}").first
                        if await element.count() > 0:
                            logger.info(f"Semantic synonym match: '{synonym}' found for target '{target}'")
                            return element
        except Exception as e:
            logger.debug(f"Semantic synonym matching failed: {e}")

        logger.warning(f"Could not resolve target: {target} (tried 11 Playwright best-practice strategies)")
        return None

    async def _extract_visible_text(self, max_snippets: int = 50) -> list[str]:
        """Extract visible text snippets from page.

        Args:
            max_snippets: Maximum number of text snippets to return

        Returns:
            List of visible text strings
        """
        if not self._page:
            return []

        try:
            # Extract text from interactive and content elements
            text_snippets = await self._page.evaluate("""
                () => {
                    const elements = document.querySelectorAll(
                        'button, a, label, input, textarea, h1, h2, h3, p, span, div[role="button"]'
                    );
                    const texts = [];
                    elements.forEach(el => {
                        const text = (el.innerText || el.textContent || '').trim();
                        if (text && text.length > 0 && text.length < 200) {
                            texts.push(text);
                        }
                        // Also capture placeholder text
                        if (el.placeholder) {
                            texts.push(el.placeholder);
                        }
                    });
                    // Remove duplicates and limit
                    return [...new Set(texts)];
                }
            """)
            return text_snippets[:max_snippets]
        except Exception as e:
            logger.error(f"Failed to extract visible text: {e}")
            return []

    async def _get_console_errors(self) -> list[str]:
        """Get console errors captured during page lifecycle.

        Returns:
            List of console error messages
        """
        # This is a simplified implementation
        # In production, maintain a buffer of console messages
        return []

    async def _get_network_events(self) -> list[dict[str, Any]]:
        """Get network events (failures, slow requests).

        Returns:
            List of network event dictionaries
        """
        # This is a simplified implementation
        # In production, maintain a buffer of network events
        return []

    async def cleanup(self) -> None:
        """Clean up Playwright resources.

        Stops tracing, closes browser, and saves artifacts.
        """
        logger.info(f"Cleaning up Playwright worker for run {self.run_id}")

        if self._context:
            # Save trace
            trace_path = self.artifacts_dir / "trace.zip"
            await self._context.tracing.stop(path=str(trace_path))
            logger.info(f"Trace saved to {trace_path}")

        if self._browser:
            await self._browser.close()

        if self._playwright:
            await self._playwright.stop()

        logger.info("Playwright worker cleanup complete")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()
