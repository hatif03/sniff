"""FastAPI backend for triggering and monitoring Sniff runs from a web UI.

Phase 1 of docs/product/SAAS_ROADMAP.md: a shared-secret bearer token and an
in-process background task, not real multi-tenant auth or a job queue (both
are Phase 2+, see that doc for what's deliberately out of scope here).
"""
