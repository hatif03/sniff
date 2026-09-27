"""Tests for site_crawl.py's link-filtering/manifest logic - pure functions,
no Playwright/network needed (matches CLAUDE.md's testing conventions for
audit-checks-style pure logic)."""

import pytest

from src.core.site_crawl import CrawlManifest, normalize_and_filter_links

ORIGIN = "https://example.com"


def test_filters_out_other_origins():
    links = normalize_and_filter_links(
        ["https://example.com/pricing", "https://evil.com/phish", "https://sub.other.com/x"],
        current_url="https://example.com/",
        origin=ORIGIN,
    )
    assert links == ["https://example.com/pricing"]


def test_filters_out_non_http_schemes():
    links = normalize_and_filter_links(
        ["mailto:hi@example.com", "tel:+15551234567", "javascript:void(0)", "/about"],
        current_url="https://example.com/",
        origin=ORIGIN,
    )
    assert links == ["https://example.com/about"]


def test_filters_out_fragment_only_links():
    links = normalize_and_filter_links(
        ["#pricing", "https://example.com/page#section"],
        current_url="https://example.com/",
        origin=ORIGIN,
    )
    # The fragment-only "#pricing" is dropped entirely; the same-page anchor
    # normalizes down to the page itself (still a real, distinct URL to visit).
    assert links == ["https://example.com/page"]


def test_filters_out_asset_extensions():
    links = normalize_and_filter_links(
        ["/brochure.pdf", "/logo.png", "/app.js", "/pricing"],
        current_url="https://example.com/",
        origin=ORIGIN,
    )
    assert links == ["https://example.com/pricing"]


@pytest.mark.parametrize("href", ["/logout", "/auth/signout", "/sign-out", "/user/LogOut"])
def test_filters_out_logout_links_case_insensitive(href):
    links = normalize_and_filter_links([href], current_url="https://example.com/", origin=ORIGIN)
    assert links == []


def test_canonicalizes_same_site_links_to_the_origins_scheme():
    """A stray http:// anchor on an https site is the same page, not a new
    one - discovered via a live crawl of a real site where this produced a
    literal duplicate audit and wasted a page-budget slot."""
    links = normalize_and_filter_links(
        ["http://example.com/", "http://example.com/pricing"],
        current_url="https://example.com/",
        origin=ORIGIN,
    )
    assert links == ["https://example.com", "https://example.com/pricing"]


def test_resolves_relative_links_against_current_page_not_origin():
    links = normalize_and_filter_links(
        ["details"],
        current_url="https://example.com/products/",
        origin=ORIGIN,
    )
    assert links == ["https://example.com/products/details"]


def test_strips_trailing_slash_for_consistent_dedup_keys():
    links = normalize_and_filter_links(["/pricing/"], current_url="https://example.com/", origin=ORIGIN)
    assert links == ["https://example.com/pricing"]


class TestCrawlManifest:
    def test_records_audited_pages(self):
        m = CrawlManifest()
        m.mark_audited("https://example.com/", "audit_1")
        assert m.as_dict() == {"https://example.com/": {"status": "audited", "audit_id": "audit_1"}}

    def test_records_skipped_and_failed_pages_with_reasons(self):
        m = CrawlManifest()
        m.mark_skipped("https://example.com/admin", "domain not allowed")
        m.mark_failed("https://example.com/broken", "timeout")
        assert m.as_dict() == {
            "https://example.com/admin": {"status": "skipped", "reason": "domain not allowed"},
            "https://example.com/broken": {"status": "failed", "error": "timeout"},
        }

    def test_mark_skipped_does_not_overwrite_an_existing_audited_entry(self):
        """A URL discovered twice (once real, once re-queued) that already
        succeeded must not be downgraded to "skipped" by a later duplicate
        pass through the frontier."""
        m = CrawlManifest()
        m.mark_audited("https://example.com/", "audit_1")
        m.mark_skipped("https://example.com/", "already visited")
        assert m.as_dict()["https://example.com/"]["status"] == "audited"
