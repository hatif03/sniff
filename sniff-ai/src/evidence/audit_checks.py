"""Deterministic landing-page audit checks.

Two halves:
- JS source strings injected via `page.evaluate()` by
  `PlaywrightWorker.evaluate_page_checks()` (browser-side DOM/CSSOM/Performance
  sampling - no network calls from inside the page).
- Pure Python functions that turn the raw dict that produces into
  AuditReport-shaped pieces (visual_teaser, browsing_evidence base fields,
  navigation findings). Kept pure/synchronous so they're trivially unit
  testable without a real Playwright Page.

Footer/nav link liveness ("all N footer links return working pages") is
checked from the Python side over HTTP (httpx), not from inside the page's
JS context, to avoid CORS entirely.
"""

import httpx

# ponytail: Core Web Vitals via performance.getEntriesByType() rather than a
# live PerformanceObserver callback - Chromium buffers 'paint',
# 'largest-contentful-paint' and 'layout-shift' entries by default, so a
# direct query returns the same data with far less code. Upgrade to a live
# Observer only if an audit needs to catch entries that fire mid-evaluate().
COLOR_FONT_SAMPLING_JS = """
() => {
    const colorCounts = {};
    const fontCounts = {};
    const els = document.querySelectorAll('body, body *');
    let sampled = 0;
    const sampleLimit = 3000;
    for (const el of els) {
        if (sampled++ > sampleLimit) break;
        const style = getComputedStyle(el);
        const color = style.color;
        const bg = style.backgroundColor;
        const font = (style.fontFamily || '').split(',')[0].trim().replace(/["']/g, '');
        if (color && color !== 'rgba(0, 0, 0, 0)') colorCounts[color] = (colorCounts[color] || 0) + 1;
        if (bg && bg !== 'rgba(0, 0, 0, 0)') colorCounts[bg] = (colorCounts[bg] || 0) + 1;
        if (font) fontCounts[font] = (fontCounts[font] || 0) + 1;
    }
    const topColors = Object.entries(colorCounts)
        .sort((a, b) => b[1] - a[1]).slice(0, 6)
        .map(([color, count]) => ({ value: color, count }));
    const topFonts = Object.entries(fontCounts)
        .sort((a, b) => b[1] - a[1]).slice(0, 6)
        .map(([family, count]) => ({ value: family, count }));
    return { colors: topColors, fonts: topFonts };
}
"""

# ponytail: prominence = area * above-fold bonus. Not a real contrast/vividness
# proxy - a simple, cheap heuristic is enough since an LLM re-verifies semantic
# roles afterward. Upgrade path: sample computed border/background color
# saturation if this misranks CTAs in practice.
INTERACTIVE_ELEMENTS_JS = """
() => {
    const els = document.querySelectorAll(
        'button, a, [role="button"], input[type="submit"], input[type="button"]'
    );
    const viewportHeight = window.innerHeight || 800;
    const results = [];
    els.forEach((el, i) => {
        const rect = el.getBoundingClientRect();
        if (rect.width <= 0 || rect.height <= 0) return;
        const text = (el.innerText || el.value || el.getAttribute('aria-label') || '').trim().slice(0, 120);
        if (!text) return;
        const area = rect.width * rect.height;
        const aboveFold = rect.top < viewportHeight;
        const prominence = area * (aboveFold ? 1.5 : 1.0);
        results.push({
            index: i,
            text,
            tag: el.tagName.toLowerCase(),
            rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height, top: rect.top },
            above_fold: aboveFold,
            prominence,
        });
    });
    return results;
}
"""

SEO_META_JS = """
() => {
    const title = document.title || '';
    const metaDesc = document.querySelector('meta[name="description"]');
    const descContent = metaDesc ? (metaDesc.getAttribute('content') || '') : '';
    const imgs = document.querySelectorAll('img');
    let withAlt = 0;
    imgs.forEach(img => { if ((img.getAttribute('alt') || '').trim()) withAlt++; });
    return {
        title,
        title_length: title.length,
        meta_description: metaDesc ? descContent : null,
        meta_description_length: descContent.length,
        h1_count: document.querySelectorAll('h1').length,
        img_count: imgs.length,
        img_alt_count: withAlt,
        img_alt_pct: imgs.length ? Math.round((withAlt / imgs.length) * 100) : 100,
        has_canonical: !!document.querySelector('link[rel="canonical"]'),
        has_viewport: !!document.querySelector('meta[name="viewport"]'),
    };
}
"""

WEB_VITALS_JS = """
() => {
    const lcpEntries = performance.getEntriesByType('largest-contentful-paint');
    const lcp = lcpEntries.length ? lcpEntries[lcpEntries.length - 1].startTime : null;
    const paintEntries = performance.getEntriesByType('paint');
    const fcpEntry = paintEntries.find(e => e.name === 'first-contentful-paint');
    const fcp = fcpEntry ? fcpEntry.startTime : null;
    let cls = 0;
    performance.getEntriesByType('layout-shift').forEach(e => {
        if (!e.hadRecentInput) cls += e.value;
    });
    return { lcp, fcp, cls };
}
"""

FOOTER_NAV_LINKS_JS = """
() => {
    const hrefs = new Set();
    document.querySelectorAll('footer a[href], nav a[href]').forEach(a => {
        const href = a.href;
        if (href && href.startsWith('http') && !href.startsWith('javascript:')) hrefs.add(href);
    });
    return Array.from(hrefs).slice(0, 10);
}
"""


def build_visual_teaser(raw: dict) -> dict:
    """Turn the colors_fonts sub-check into AuditReport.visual_teaser shape."""
    colors_fonts = raw.get("colors_fonts") or {}
    colors = colors_fonts.get("colors") or []
    fonts = colors_fonts.get("fonts") or []
    return {
        "dominant_colors": [{"color": c.get("value", ""), "uses": c.get("count", 0)} for c in colors],
        "font_families": [{"family": f.get("value", ""), "uses": f.get("count", 0)} for f in fonts],
    }


def select_cta_candidates(raw: dict, top_n: int = 5) -> list[dict]:
    """Sort detected interactive elements by prominence, dedupe by text, return top_n.

    These are the "safe CTA candidates" handed to the vision LLM for semantic
    role assignment, and then to CTA click-testing.
    """
    elements = raw.get("interactive_elements") or []
    seen_text: set[str] = set()
    deduped = []
    for el in sorted(elements, key=lambda e: e.get("prominence", 0), reverse=True):
        text = el.get("text", "").strip()
        if not text or text.lower() in seen_text:
            continue
        seen_text.add(text.lower())
        deduped.append(el)
    return deduped[:top_n]


def build_browsing_evidence_base(raw: dict, candidates: list[dict]) -> dict:
    """Fields of BrowsingEvidence derivable without clicking anything yet
    (total_interactive_elements, safe_cta_candidates, primary_label)."""
    total = len(raw.get("interactive_elements") or [])
    primary_label = candidates[0]["text"] if candidates else ""
    return {
        "total_interactive_elements": total,
        "safe_cta_candidates": len(candidates),
        "primary_label": primary_label,
    }


async def check_footer_links(urls: list[str], timeout_seconds: float = 5.0) -> list[dict]:
    """HEAD (falling back to GET) each footer/nav link from the Python side,
    to avoid CORS restrictions that would break a same-origin JS fetch.

    Returns list of {"url": str, "status": int | None, "ok": bool}.
    """
    if not urls:
        return []

    results: list[dict] = []
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout_seconds) as client:
        for url in urls:
            status: int | None = None
            try:
                resp = await client.head(url)
                status = resp.status_code
                if status in (405, 501):
                    resp = await client.get(url)
                    status = resp.status_code
            except httpx.HTTPError:
                status = None
            results.append({"url": url, "status": status, "ok": status is not None and status < 400})
    return results


def build_navigation_findings(link_results: list[dict]) -> list[str]:
    """Turn footer/nav link check results into the growth.navigation findings
    prose format used by the real report this schema was reverse-engineered
    from, e.g.:
    'Footer links check: POSITIVE - all N tested footer links return working
    pages with no broken destinations.'
    """
    if not link_results:
        return ["Footer links check: SKIPPED - no footer/nav links were found to test."]

    broken = [r for r in link_results if not r["ok"]]
    n = len(link_results)
    if not broken:
        return [
            f"Footer links check: POSITIVE - all {n} tested footer links return working "
            "pages with no broken destinations."
        ]
    broken_desc = ", ".join(f"{r['url']} ({r['status'] or 'no response'})" for r in broken)
    return [
        f"Footer links check: NEGATIVE - {len(broken)} of {n} tested footer links are broken: {broken_desc}."
    ]
