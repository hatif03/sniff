"""POST /audits to the deployed Sniff API and poll until done."""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

POLL_SECONDS = 12


def _request(method: str, url: str, token: str, body: dict | None = None) -> dict:
    data = None
    headers = {"Authorization": f"Bearer {token}"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    load_dotenv()
    # Also pick up Vercel proxy env if the user only has sniff-web configured.
    load_dotenv(Path(__file__).resolve().parents[2] / "sniff-web" / ".env.local")
    base = os.environ.get("BACKEND_URL", "https://sniff-api-2wv6ilt7fa-uc.a.run.app").rstrip("/")
    token = os.environ.get("SNIFF_API_TOKEN")
    if not token:
        print("SNIFF_API_TOKEN is required", file=sys.stderr)
        return 2

    urls = sys.argv[1:] or [
        "https://getflocus.in/",
        "https://deals-machine.vercel.app/",
    ]

    failures = 0
    for url in urls:
        created = _request("POST", f"{base}/audits", token, {"url": url})
        audit_id = created["audit_id"]
        print(f"queued {audit_id} {url}")
        deadline = time.time() + 20 * 60
        while time.time() < deadline:
            time.sleep(POLL_SECONDS)
            try:
                status = _request("GET", f"{base}/audits/{audit_id}", token)
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    print(f"  {audit_id} -> (404 on another instance, retrying poll)")
                    continue
                raise
            state = status.get("status")
            print(f"  {audit_id} -> {state}")
            if state in ("completed", "failed"):
                if state == "failed":
                    failures += 1
                    print(f"  error: {status.get('error')}", file=sys.stderr)
                elif status.get("report"):
                    report = status["report"]
                    print(f"  score={report.get('overall_score')} label={report.get('label')}")
                break
        else:
            failures += 1
            print(f"  timed out waiting for {audit_id}", file=sys.stderr)
    return failures


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.HTTPError as e:
        print(e.read().decode(), file=sys.stderr)
        raise SystemExit(1) from e
