"""Whole-site audit orchestrator: crawl + audit every reachable page of a
site in one browser session, optionally logging in first so auth-gated
pages are reachable too.

Reuses AuditOrchestrator's per-page pipeline (run_audit_on_page) unchanged -
this module only adds the crawl layer around it: discovery (sitemap +
breadth-first link-following via site_crawl.py), a shared PlaywrightWorker
session (so an authenticated cookie jar survives across every page, unlike
creating a fresh worker per page), and incremental persistence so a
long-running crawl that hits its time budget still leaves real, usable
per-page results instead of losing everything.
"""

import asyncio
import logging
import uuid
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ..agent.decision_service import create_agent_service
from ..agent.k2horizon_client import create_k2horizon_client
from ..executor.playwright_worker import PlaywrightWorker
from .audit_models import AuditReport
from .audit_orchestrator import AuditOrchestrator
from .config import SniffConfig
from .site_crawl import CrawlManifest, discover_sitemap_urls, normalize_and_filter_links

logger = logging.getLogger(__name__)


class SiteAuditOrchestrator:
    """Orchestrates a whole-site audit: discover pages, optionally log in,
    audit up to max_pages of them on one shared (optionally authenticated)
    worker session."""

    def __init__(self, config: SniffConfig):
        self.config = config
        # Delegate to a plain AuditOrchestrator for the pieces that are
        # already correct and shouldn't be reimplemented: domain-allowlist
        # enforcement, persona loading, and the per-page audit pipeline
        # itself (run_audit_on_page).
        self._audit = AuditOrchestrator(config)

    async def run_site_audit(
        self,
        seed_url: str,
        persona: str | None = None,
        max_pages: int | None = None,
        max_depth: int | None = None,
        login: dict | None = None,
        storage_state: dict | None = None,
        site_audit_id: str | None = None,
        on_page_complete: Callable[[str, str, AuditReport], Any] | None = None,
    ) -> tuple[str, CrawlManifest]:
        """Crawl and audit a whole site.

        Args:
            seed_url: Starting page.
            persona: Optional persona name (defaults same as single-page audit).
            max_pages: Cap on pages actually audited (default from config,
                hard ceiling enforced by GuardrailsConfig itself).
            max_depth: Cap on link-following depth from the seed page.
            login: Optional {"url": ..., "username": ..., "password": ...} -
                used exactly once to establish a session; the password is
                never returned, logged, or included in any persisted state.
            storage_state: Optional pre-authenticated Playwright storage_state
                (cookies/localStorage) - alternative to `login` for a user
                who'd rather not hand over a password at all.
            site_audit_id: Pre-assigned ID (already handed back to an API
                caller to poll). Generated if omitted.
            on_page_complete: Optional callback invoked with (url,
                page_audit_id, AuditReport) as each page finishes - the
                incremental-persistence hook the API layer uses to upload
                each page's result to Supabase as soon as it's ready, not
                just at the very end. page_audit_id is the exact ID this
                orchestrator generated and used for that page's own
                artifacts_dir/manifest entry - passed through rather than
                left for the caller to independently re-derive.

        Returns:
            (site_audit_id, manifest) - the manifest records every URL
            considered and what happened to it (audited/skipped/failed).
        """
        self._audit._check_domain_allowlist(seed_url)

        site_audit_id = site_audit_id or self._generate_site_audit_id()
        persona_profile = self._audit._load_persona(persona)
        max_pages = min(max_pages or self.config.guardrails.max_site_audit_pages, self.config.guardrails.max_site_audit_pages)
        max_depth = max_depth or self.config.guardrails.max_site_audit_depth

        return await asyncio.wait_for(
            self._run_crawl(
                seed_url, site_audit_id, persona_profile, max_pages, max_depth,
                login, storage_state, on_page_complete,
            ),
            timeout=self.config.guardrails.site_audit_hard_timeout,
        )

    async def _run_crawl(
        self,
        seed_url: str,
        site_audit_id: str,
        persona_profile: Any,
        max_pages: int,
        max_depth: int,
        login: dict | None,
        storage_state: dict | None,
        on_page_complete: Callable[[str, str, AuditReport], Any] | None,
    ) -> tuple[str, CrawlManifest]:
        origin = f"{urlparse(seed_url).scheme}://{urlparse(seed_url).netloc}"
        artifacts_dir = Path(self.config.artifacts_path) / site_audit_id
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        manifest = CrawlManifest()
        gemini_client = create_agent_service(self.config).client
        k2_client = create_k2horizon_client(self.config)

        async with PlaywrightWorker(
            run_id=site_audit_id,
            artifacts_dir=artifacts_dir,
            device_name=self.config.defaults.device,
            headless=self.config.playwright.headless,
            slow_mo=self.config.playwright.slow_mo,
            storage_state=storage_state,
        ) as worker:
            if login:
                logged_in = await worker.login(login["url"], login["username"], password=login["password"])
                if not logged_in:
                    logger.warning(f"Site audit {site_audit_id}: login at {login['url']} did not appear to succeed")

            # Sitemap discovery runs once, up front - a bonus source, not a
            # requirement (see discover_sitemap_urls's own docstring).
            queue: list[tuple[str, int]] = [(seed_url, 0)]
            for sitemap_url in await discover_sitemap_urls(origin):
                queue.append((sitemap_url, 0))

            visited: set[str] = set()
            audited_count = 0

            # Not `and audited_count < max_pages` - once the cap is hit we
            # still want to drain the rest of the queue (via the max_pages
            # check below) so every already-discovered URL gets a manifest
            # entry ("skipped: max_pages limit reached"), not silently
            # dropped. No new links get queued once skipping starts (that
            # only happens after a successful audit, below), so this drain
            # is cheap - no further navigation happens.
            while queue:
                url, depth = queue.pop(0)
                normalized = url.rstrip("/")
                if normalized in visited:
                    continue
                visited.add(normalized)

                try:
                    self._audit._check_domain_allowlist(url)
                except ValueError as e:
                    manifest.mark_skipped(url, f"domain not allowed: {e}")
                    continue

                if audited_count >= max_pages:
                    manifest.mark_skipped(url, "max_pages limit reached")
                    continue

                # capture_audit_screenshots() always writes the same three
                # fixed filenames (above_fold.png/full_page.png/annotated.png)
                # under worker.artifacts_dir - redirecting it to a fresh
                # per-page subdirectory before each page is what stops every
                # page's screenshots from overwriting the last one's, since
                # this whole crawl deliberately shares one worker/session.
                page_audit_id = f"{site_audit_id}_p{audited_count}"
                worker.artifacts_dir = artifacts_dir / page_audit_id
                worker.artifacts_dir.mkdir(parents=True, exist_ok=True)

                try:
                    observation = await worker.navigate(url, timeout=self.config.playwright.navigation_timeout)
                    report = await self._audit.run_audit_on_page(
                        worker, url, observation, persona_profile, gemini_client, k2_client
                    )
                except Exception as e:
                    logger.error(f"Site audit {site_audit_id}: page {url} failed: {e}", exc_info=True)
                    manifest.mark_failed(url, str(e))
                    continue

                manifest.mark_audited(url, page_audit_id)
                audited_count += 1

                if on_page_complete:
                    result = on_page_complete(url, page_audit_id, report)
                    if asyncio.iscoroutine(result):
                        await result

                if depth < max_depth:
                    try:
                        raw_links = await worker.get_page_links()
                        for link in normalize_and_filter_links(raw_links, url, origin):
                            if link.rstrip("/") not in visited:
                                queue.append((link, depth + 1))
                    except Exception as e:
                        logger.warning(f"Link discovery failed on {url}: {e}")

        return site_audit_id, manifest

    @staticmethod
    def _generate_site_audit_id() -> str:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        return f"site_audit_{timestamp}_{short_uuid}"
