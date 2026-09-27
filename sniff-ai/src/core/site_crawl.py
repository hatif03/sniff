"""Site-wide discovery helpers for the whole-site audit feature.

Pure, network/browser-agnostic functions plus one small async sitemap
fetcher - kept separate from SiteAuditOrchestrator so link-filtering/
dedup logic can be unit-tested without a real Playwright session.

Discovery is deliberately a hybrid, matching how real site crawlers
(Screaming Frog, Scrapy's broad-crawl guidance) do it: sitemap.xml catches
pages with no inbound links from the seed page, breadth-first link
following (driven by the orchestrator calling PlaywrightWorker.get_page_links()
per visited page) catches everything else.
"""

import logging
import re
from urllib.parse import urljoin, urlparse, urlunparse
from xml.etree import ElementTree

import httpx

logger = logging.getLogger(__name__)

# Href patterns that should never be followed even if same-origin: a logout
# link would kill the very session a whole-site audit depends on.
_LOGOUT_PATTERN = re.compile(r"log[\s_-]?out|sign[\s_-]?out", re.IGNORECASE)

# Common non-page asset extensions - following these wastes a crawl slot on
# something that was never going to produce a meaningful audit anyway.
_ASSET_EXTENSIONS = {
    ".pdf", ".zip", ".rar", ".7z", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico", ".bmp",
    ".css", ".js", ".json", ".xml", ".txt", ".csv",
    ".mp4", ".mp3", ".wav", ".avi", ".mov", ".woff", ".woff2", ".ttf", ".eot",
}


def normalize_and_filter_links(
    raw_hrefs: list[str],
    current_url: str,
    origin: str,
) -> list[str]:
    """Turn raw <a href> values from one page into absolute, same-origin,
    audit-worthy candidate URLs. Filters out: other origins, non-http(s)
    schemes (mailto:/tel:/javascript:), fragment-only links, asset files,
    and anything matching the logout pattern. Does not dedupe against a
    crawl-wide visited set - that's the caller's job (it has that state).
    """
    candidates: list[str] = []
    for href in raw_hrefs:
        if not href or href.startswith("#"):
            continue
        if _LOGOUT_PATTERN.search(href):
            continue

        absolute = urljoin(current_url, href)
        parsed = urlparse(absolute)

        if parsed.scheme not in ("http", "https"):
            continue
        origin_parsed = urlparse(origin)
        if parsed.hostname != origin_parsed.hostname:
            continue
        path_lower = parsed.path.lower()
        if any(path_lower.endswith(ext) for ext in _ASSET_EXTENSIONS):
            continue

        # A same-site link on a different scheme (a stray http:// anchor on
        # an https page, common on older sites) is the same page, not a new
        # one - canonicalizing here keeps it out of the visited/dedup set
        # under a second, wasted key.
        if parsed.scheme != origin_parsed.scheme:
            absolute = urlunparse(parsed._replace(scheme=origin_parsed.scheme))

        # Strip fragment (same page, different anchor) - not a new page.
        normalized = absolute.split("#", 1)[0].rstrip("/")
        if normalized:
            candidates.append(normalized)

    return candidates


async def discover_sitemap_urls(origin: str, timeout: float = 5.0) -> list[str]:
    """Best-effort fetch + parse of {origin}/sitemap.xml. Returns an empty
    list on any failure (missing sitemap, network error, malformed XML) -
    this is a bonus discovery source, never a hard requirement, since
    link-following from the seed page always runs regardless."""
    sitemap_url = urljoin(origin, "/sitemap.xml")
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(sitemap_url)
            if response.status_code != 200:
                return []
            root = ElementTree.fromstring(response.content)
    except Exception as e:
        logger.info(f"No usable sitemap at {sitemap_url}: {e}")
        return []

    # Namespace-agnostic: match any element whose local tag is "loc".
    urls = [el.text.strip() for el in root.iter() if el.tag.endswith("loc") and el.text]
    origin_parsed = urlparse(origin)
    same_origin = []
    for u in urls:
        parsed = urlparse(u)
        if parsed.hostname != origin_parsed.hostname:
            continue
        # A sitemap INDEX lists other sitemap files (nested <sitemap><loc>),
        # not pages - those entries look identical to a real <url><loc> page
        # entry once flattened by the namespace-agnostic scan above, so the
        # same asset-extension filter link-following already uses (.xml
        # among them) is what actually tells them apart here.
        if any(parsed.path.lower().endswith(ext) for ext in _ASSET_EXTENSIONS):
            continue
        # Same canonicalization as normalize_and_filter_links: a sitemap
        # entry on a different scheme than the seed is still the same page.
        if parsed.scheme != origin_parsed.scheme:
            u = urlunparse(parsed._replace(scheme=origin_parsed.scheme))
        same_origin.append(u)
    return same_origin


class CrawlManifest:
    """Tracks what happened to every URL a site audit considered - the
    literal "what we clicked and what not" record surfaced in the dashboard.
    Not persisted directly; SiteAuditOrchestrator writes this dict into the
    site_audits.manifest JSONB column."""

    def __init__(self) -> None:
        self.entries: dict[str, dict] = {}

    def mark_audited(self, url: str, audit_id: str) -> None:
        self.entries[url] = {"status": "audited", "audit_id": audit_id}

    def mark_skipped(self, url: str, reason: str) -> None:
        self.entries.setdefault(url, {"status": "skipped", "reason": reason})

    def mark_failed(self, url: str, error: str) -> None:
        self.entries[url] = {"status": "failed", "error": error}

    def as_dict(self) -> dict:
        return dict(self.entries)
