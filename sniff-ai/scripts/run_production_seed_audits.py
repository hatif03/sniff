"""Queue production audits requested for dashboard seeding."""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

POLL_SECONDS = 15
SITE_POLL_DEADLINE_SECONDS = 45 * 60
PAGE_POLL_DEADLINE_SECONDS = 25 * 60


def _env() -> tuple[str, str]:
    load_dotenv()
    load_dotenv(Path(__file__).resolve().parents[2] / "sniff-web" / ".env.local")
    base = os.environ.get("BACKEND_URL", "https://sniff-api-2wv6ilt7fa-uc.a.run.app").rstrip("/")
    token = os.environ.get("SNIFF_API_TOKEN")
    if not token:
        raise RuntimeError("SNIFF_API_TOKEN is required")
    return base, token


def _request(method: str, url: str, token: str, body: dict | None = None) -> dict:
    data = None
    headers = {"Authorization": f"Bearer {token}"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _poll_page_audit(base: str, token: str, audit_id: str) -> dict:
    deadline = time.time() + PAGE_POLL_DEADLINE_SECONDS
    while time.time() < deadline:
        time.sleep(POLL_SECONDS)
        try:
            status = _request("GET", f"{base}/audits/{audit_id}", token)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"  {audit_id} -> (404, retrying poll)")
                continue
            raise
        state = status.get("status")
        print(f"  {audit_id} -> {state}")
        if state in ("completed", "failed"):
            return status
    raise TimeoutError(f"Timed out waiting for audit {audit_id}")


def _poll_site_audit(base: str, token: str, site_audit_id: str) -> dict:
    deadline = time.time() + SITE_POLL_DEADLINE_SECONDS
    while time.time() < deadline:
        time.sleep(POLL_SECONDS)
        try:
            status = _request("GET", f"{base}/site-audits/{site_audit_id}", token)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"  {site_audit_id} -> (404, retrying poll)")
                continue
            raise
        state = status.get("status")
        audited = status.get("pages_audited", 0)
        discovered = status.get("pages_discovered", 0)
        print(f"  {site_audit_id} -> {state} ({audited}/{discovered} pages)")
        if state in ("completed", "failed"):
            return status
    raise TimeoutError(f"Timed out waiting for site audit {site_audit_id}")


def _verify_report_images(status: dict) -> None:
    report = status.get("report") or {}
    images = report.get("images") or {}
    for key, url in images.items():
        if not str(url).startswith("https://"):
            raise RuntimeError(f"Screenshot {key} is not a public URL: {url}")


def _verify_images_http(url: str) -> None:
    req = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status >= 400:
            raise RuntimeError(f"Screenshot URL not accessible: {url} ({resp.status})")


def main() -> int:
    base, token = _env()
    failures = 0

    # 1) Single-page audit — Flocus
    flocus = "https://getflocus.in/"
    created = _request("POST", f"{base}/audits", token, {"url": flocus})
    audit_id = created["audit_id"]
    print(f"queued page audit {audit_id} {flocus}")
    try:
        result = _poll_page_audit(base, token, audit_id)
        if result.get("status") != "completed":
            failures += 1
            print(f"  failed: {result.get('error')}", file=sys.stderr)
        else:
            _verify_report_images(result)
            for url in (result.get("report") or {}).get("images", {}).values():
                _verify_images_http(str(url))
            print(f"  OK score={result['report'].get('overall_score')} audit_id={audit_id}")
    except Exception as e:
        failures += 1
        print(f"  FAIL {e}", file=sys.stderr)

    # 2) Whole-site audit — Klesos / Deals Machine landing
    seed = "https://deals-machine.vercel.app/"
    site_created = _request(
        "POST",
        f"{base}/site-audits",
        token,
        {"seed_url": seed, "max_pages": 10},
    )
    site_audit_id = site_created["site_audit_id"]
    print(f"queued site audit {site_audit_id} {seed}")
    try:
        site_result = _poll_site_audit(base, token, site_audit_id)
        if site_result.get("status") != "completed":
            failures += 1
            print(f"  failed: {site_result.get('error')}", file=sys.stderr)
        else:
            pages = site_result.get("pages") or []
            print(f"  OK {len(pages)} page reports")
            for page in pages[:3]:
                page_status = _request("GET", f"{base}/audits/{page['audit_id']}", token)
                _verify_report_images(page_status)
    except Exception as e:
        failures += 1
        print(f"  FAIL {e}", file=sys.stderr)

    return failures


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.HTTPError as e:
        print(e.read().decode(), file=sys.stderr)
        raise SystemExit(1) from e
