"""Queue one whole-site audit and poll until done."""

import sys

from run_production_seed_audits import (
    _env,
    _poll_site_audit,
    _request,
    _verify_images_http,
    _verify_report_images,
)


def main() -> int:
    seed = sys.argv[1] if len(sys.argv) > 1 else "https://deals-machine.vercel.app/"
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    base, token = _env()
    created = _request("POST", f"{base}/site-audits", token, {"seed_url": seed, "max_pages": max_pages})
    site_audit_id = created["site_audit_id"]
    print(f"queued site audit {site_audit_id} {seed}")
    result = _poll_site_audit(base, token, site_audit_id)
    print(f"status={result.get('status')} pages={len(result.get('pages') or [])}")
    if result.get("status") != "completed":
        print(result.get("error") or result.get("manifest"), file=sys.stderr)
        return 1
    for page in result.get("pages") or []:
        st = _request("GET", f"{base}/audits/{page['audit_id']}", token)
        _verify_report_images(st)
        for url in (st.get("report") or {}).get("images", {}).values():
            _verify_images_http(str(url))
        print(f"  OK {page['audit_id']} score={page.get('overall_score')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
