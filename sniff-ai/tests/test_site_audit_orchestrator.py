"""Tests for src/core/site_audit_orchestrator.py.

Mocks PlaywrightWorker, GeminiClient, K2HorizonClient, and sitemap
discovery so no real browser/LLM/network call happens. Reuses
test_audit_orchestrator.py's GEMINI_RESULT/K2_RESULT/RAW_CHECKS fixtures
via import rather than duplicating them.
"""

import pytest

import src.core.audit_orchestrator as audit_orchestrator_module
import src.core.site_audit_orchestrator as site_audit_module
from src.core.config import SniffConfig
from src.core.models import Observation
from src.core.site_audit_orchestrator import SiteAuditOrchestrator
from tests.test_audit_orchestrator import (
    RAW_CHECKS,
    FakeAgentService,
    FakeK2Client,
)


class FakeSiteWorker:
    """Like test_audit_orchestrator's FakeWorker, plus get_page_links()/
    login() for the crawl-specific behavior. One shared instance per test
    (matching how SiteAuditOrchestrator uses exactly one worker for the
    whole crawl), so call-history assertions are straightforward."""

    instances: list["FakeSiteWorker"] = []

    # url -> links discovered on that page (simulates real site structure)
    LINKS_BY_PAGE = {
        "https://example.com": ["/pricing", "/about", "/logout"],
        "https://example.com/pricing": ["/", "/about"],
        "https://example.com/about": [],
    }

    def __init__(self, run_id, artifacts_dir, device_name=None, headless=True, slow_mo=0, storage_state=None):
        self.run_id = run_id
        self.artifacts_dir = artifacts_dir
        self.storage_state = storage_state
        self.navigate_calls: list[str] = []
        self.login_calls: list[tuple] = []
        self.artifacts_dirs_used: list = []
        FakeSiteWorker.instances.append(self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def login(self, login_url, username, password, timeout=15000):
        self.login_calls.append((login_url, username, password))
        return True

    async def navigate(self, url, timeout=30000):
        self.navigate_calls.append(url)
        self.artifacts_dirs_used.append(self.artifacts_dir)
        screenshot_path = self.artifacts_dir / "full_page.png"
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        screenshot_path.write_bytes(b"fake-png-bytes")
        return Observation(
            runId=self.run_id, step=1, url=url,
            screenshotPath=str(screenshot_path), visibleText=["hi"],
        )

    async def evaluate_page_checks(self):
        return RAW_CHECKS

    async def get_page_links(self):
        return self.LINKS_BY_PAGE.get(self.navigate_calls[-1], [])

    async def screenshot_viewport(self, name=None):
        return str(self.artifacts_dir / (name or "above_fold.png"))

    async def screenshot(self, name=None):
        return str(self.artifacts_dir / (name or "full_page.png"))

    async def screenshot_with_overlay(self, annotations, name=None):
        return str(self.artifacts_dir / (name or "annotated.png"))

    async def tap(self, target):
        return Observation(
            runId=self.run_id, step=2, url=self.navigate_calls[-1],
            screenshotPath=str(self.artifacts_dir / "full_page.png"), visibleText=["hi"],
        )

    async def detect_modal(self):
        return False


@pytest.fixture(autouse=True)
def reset_instances():
    FakeSiteWorker.instances = []
    yield
    FakeSiteWorker.instances = []


@pytest.fixture
def config(tmp_path) -> SniffConfig:
    cfg = SniffConfig()
    cfg.artifacts_path = str(tmp_path)
    cfg.guardrails.max_site_audit_pages = 10
    return cfg


@pytest.fixture(autouse=True)
def patch_dependencies(monkeypatch):
    monkeypatch.setattr(audit_orchestrator_module, "create_agent_service", lambda cfg: FakeAgentService())
    monkeypatch.setattr(audit_orchestrator_module, "create_k2horizon_client", lambda cfg: FakeK2Client())
    monkeypatch.setattr(site_audit_module, "create_agent_service", lambda cfg: FakeAgentService())
    monkeypatch.setattr(site_audit_module, "create_k2horizon_client", lambda cfg: FakeK2Client())
    monkeypatch.setattr(site_audit_module, "PlaywrightWorker", FakeSiteWorker)

    async def no_sitemap(origin, timeout=5.0):
        return []
    monkeypatch.setattr(site_audit_module, "discover_sitemap_urls", no_sitemap)


@pytest.mark.asyncio
async def test_crawls_and_audits_multiple_pages_via_link_following(config):
    orchestrator = SiteAuditOrchestrator(config)
    site_audit_id, manifest = await orchestrator.run_site_audit(seed_url="https://example.com")

    manifest_dict = manifest.as_dict()
    audited = {url for url, entry in manifest_dict.items() if entry["status"] == "audited"}
    assert audited == {"https://example.com", "https://example.com/pricing", "https://example.com/about"}


@pytest.mark.asyncio
async def test_never_follows_the_logout_link(config):
    orchestrator = SiteAuditOrchestrator(config)
    _, manifest = await orchestrator.run_site_audit(seed_url="https://example.com")

    worker = FakeSiteWorker.instances[0]
    assert not any("logout" in url for url in worker.navigate_calls)
    assert not any("logout" in url for url in manifest.as_dict())


@pytest.mark.asyncio
async def test_respects_max_pages_cap(config):
    config.guardrails.max_site_audit_pages = 1
    orchestrator = SiteAuditOrchestrator(config)
    _, manifest = await orchestrator.run_site_audit(seed_url="https://example.com", max_pages=1)

    audited = [url for url, entry in manifest.as_dict().items() if entry["status"] == "audited"]
    assert len(audited) == 1
    skipped_reasons = [entry["reason"] for entry in manifest.as_dict().values() if entry["status"] == "skipped"]
    assert any("max_pages" in r for r in skipped_reasons)


@pytest.mark.asyncio
async def test_reuses_one_worker_session_for_the_whole_crawl(config):
    """The whole point of a shared session (so a login survives across
    pages) - confirm only ONE PlaywrightWorker is ever constructed."""
    orchestrator = SiteAuditOrchestrator(config)
    await orchestrator.run_site_audit(seed_url="https://example.com")
    assert len(FakeSiteWorker.instances) == 1


@pytest.mark.asyncio
async def test_each_page_gets_its_own_screenshot_subdirectory(config):
    """Confirms the collision fix: capture_audit_screenshots always writes
    the same 3 fixed filenames, so each page must get a distinct
    artifacts_dir or later pages would overwrite earlier ones' screenshots."""
    orchestrator = SiteAuditOrchestrator(config)
    await orchestrator.run_site_audit(seed_url="https://example.com")

    worker = FakeSiteWorker.instances[0]
    assert len(set(worker.artifacts_dirs_used)) == len(worker.artifacts_dirs_used)


@pytest.mark.asyncio
async def test_login_is_called_once_with_the_given_credentials_and_password_never_leaks(config):
    orchestrator = SiteAuditOrchestrator(config)
    site_audit_id, manifest = await orchestrator.run_site_audit(
        seed_url="https://example.com",
        login={"url": "https://example.com/login", "username": "test@example.com", "password": "hunter2"},
    )

    worker = FakeSiteWorker.instances[0]
    assert worker.login_calls == [("https://example.com/login", "test@example.com", "hunter2")]

    # The password must never leak into the manifest or the returned id.
    assert "hunter2" not in str(manifest.as_dict())
    assert "hunter2" not in site_audit_id


@pytest.mark.asyncio
async def test_on_page_complete_callback_fires_incrementally(config):
    """The incremental-persistence hook the API layer uses to upload each
    page as soon as it's done, not just at the very end."""
    completed = []

    async def on_complete(url, page_audit_id, report):
        completed.append(url)

    orchestrator = SiteAuditOrchestrator(config)
    await orchestrator.run_site_audit(seed_url="https://example.com", on_page_complete=on_complete)

    assert set(completed) == {"https://example.com", "https://example.com/pricing", "https://example.com/about"}


@pytest.mark.asyncio
async def test_respects_domain_allowlist_on_the_seed_url(config):
    config.security.enforce_domain_allowlist = True
    config.security.allowed_domains = ["allowed.example.com"]

    orchestrator = SiteAuditOrchestrator(config)
    with pytest.raises(ValueError, match="not in the allowed domains"):
        await orchestrator.run_site_audit(seed_url="https://evil.example.org")

    assert FakeSiteWorker.instances == []
