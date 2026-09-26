"""Builds the JS overlay used to produce the "annotated" audit screenshot.

Kept as a pure function (string in, string out) so it's testable without a
real Playwright Page. `PlaywrightWorker.screenshot_with_overlay()` is what
actually injects this via `page.evaluate()` and takes the screenshot - see
executor/playwright_worker.py.
"""

import json
from typing import Any


def build_overlay_script(annotations: list[dict[str, Any]]) -> str:
    """Build a JS snippet that draws an absolutely-positioned, colored,
    labeled overlay div for each annotation over its bounding box.

    Each annotation dict is expected to have: rect ({x,y,width,height}),
    color (CSS color string), label (short badge text).
    """
    payload = json.dumps(annotations)
    return f"""
(() => {{
    const annotations = {payload};
    annotations.forEach((a) => {{
        const rect = a.rect || {{}};
        const box = document.createElement('div');
        box.setAttribute('data-sniff-audit-overlay', 'true');
        box.style.position = 'fixed';
        box.style.left = (rect.x || 0) + 'px';
        box.style.top = (rect.y || 0) + 'px';
        box.style.width = (rect.width || 0) + 'px';
        box.style.height = (rect.height || 0) + 'px';
        box.style.border = '2px solid ' + (a.color || '#ff00ff');
        box.style.borderRadius = '4px';
        box.style.zIndex = '2147483647';
        box.style.pointerEvents = 'none';
        box.style.boxSizing = 'border-box';

        const badge = document.createElement('div');
        badge.setAttribute('data-sniff-audit-overlay', 'true');
        badge.textContent = a.label || '';
        badge.style.position = 'fixed';
        badge.style.left = (rect.x || 0) + 'px';
        badge.style.top = Math.max((rect.y || 0) - 18, 0) + 'px';
        badge.style.background = a.color || '#ff00ff';
        badge.style.color = '#ffffff';
        badge.style.font = '11px sans-serif';
        badge.style.padding = '1px 5px';
        badge.style.borderRadius = '3px';
        badge.style.zIndex = '2147483647';
        badge.style.pointerEvents = 'none';

        document.body.appendChild(box);
        document.body.appendChild(badge);
    }});
}})();
"""


def merge_role_assignments(candidates: list[dict], role_assignments: list[dict]) -> list[dict]:
    """Match Gemini's {index, role, color, label} assignments back to the real
    candidate elements (by index, falling back to text match), producing the
    overlay-ready annotation list (each with rect + color + label + role/text).
    """
    by_index = {c.get("index"): c for c in candidates}
    by_text = {c.get("text", "").lower(): c for c in candidates}

    merged = []
    for assignment in role_assignments:
        candidate = by_index.get(assignment.get("index"))
        if candidate is None:
            candidate = by_text.get(str(assignment.get("text", "")).lower())
        if candidate is None:
            continue
        merged.append(
            {
                "rect": candidate.get("rect", {}),
                "text": candidate.get("text", ""),
                "role": assignment.get("role", "cta"),
                "color": assignment.get("color", "#ff00ff"),
                "label": assignment.get("label", assignment.get("role", "cta")),
            }
        )
    return merged


async def capture_audit_screenshots(worker, annotations: list[dict]) -> dict[str, str]:
    """Produce the three audit screenshots (above_fold, full_page, annotated)
    using the existing PlaywrightWorker screenshot methods. Screenshots land
    under the worker's own artifacts_dir (one per run/audit), same convention
    as every other PlaywrightWorker screenshot.

    Args:
        worker: an initialized PlaywrightWorker (already navigated to the
            target page)
        annotations: overlay-ready annotations, see merge_role_assignments()

    Returns:
        {"above_fold": path, "full_page": path, "annotated": path}
    """
    above_fold = await worker.screenshot_viewport(name="above_fold.png")
    full_page = await worker.screenshot(name="full_page.png")
    annotated = await worker.screenshot_with_overlay(annotations, name="annotated.png")
    return {"above_fold": above_fold, "full_page": full_page, "annotated": annotated}
