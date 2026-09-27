"""Run one-page landing audits for a list of URLs (local orchestrator path)."""

import asyncio
import sys

from dotenv import load_dotenv

from src.core.audit_orchestrator import AuditOrchestrator
from src.core.config import SniffConfig


async def _audit_url(config: SniffConfig, url: str) -> None:
    orchestrator = AuditOrchestrator(config)
    report = await orchestrator.run_audit(url=url)
    print(f"OK {url} score={report.overall_score} label={report.label}")


async def main(urls: list[str]) -> int:
    load_dotenv()
    config = SniffConfig.load()
    # CLI helper for ad-hoc URLs passed on the command line (dashboard/API
    # callers enforce allowlist separately via deployed config).
    config.security.enforce_domain_allowlist = False
    failures = 0
    for url in urls:
        try:
            await _audit_url(config, url)
        except Exception as e:
            failures += 1
            print(f"FAIL {url}: {e}", file=sys.stderr)
    return failures


if __name__ == "__main__":
    targets = sys.argv[1:] or [
        "https://getflocus.in/",
        "https://deals-machine.vercel.app/",
    ]
    raise SystemExit(asyncio.run(main(targets)))
