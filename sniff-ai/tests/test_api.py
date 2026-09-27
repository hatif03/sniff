"""Tests for the FastAPI backend (src/api/main.py).

Mocks RunOrchestrator/ExperimentOrchestrator and the Supabase uploader so no
real Playwright browser, Gemini/k2-horizon call, or Supabase upload happens.
"""

import asyncio
import copy

import pytest
from fastapi.testclient import TestClient

import src.api.main as api_main
from src.core.audit_models import AuditReport
from src.core.experiment_models import ExperimentConfig
from src.core.state_machine import RunOutcome


def _clear_job_queue() -> None:
    while not api_main.JOB_QUEUE.empty():
        api_main.JOB_QUEUE.get_nowait()


@pytest.fixture(autouse=True)
def api_token(monkeypatch):
    """Give every test a known shared-secret token and a clean run/audit store."""
    monkeypatch.setattr(api_main.config.api, "token", "test-token")
    api_main.RUN_STORE.clear()
    api_main.AUDIT_STORE.clear()
    api_main.SITE_AUDIT_STORE.clear()
    _clear_job_queue()
    yield
    api_main.RUN_STORE.clear()
    api_main.AUDIT_STORE.clear()
    api_main.SITE_AUDIT_STORE.clear()
    _clear_job_queue()


@pytest.fixture
def client():
    return TestClient(api_main.app)


def auth_headers(token: str = "test-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def run_queued_jobs() -> None:
    """Synchronously drain and execute every job currently sitting in
    JOB_QUEUE. In production, _job_worker() processes the queue in the
    background, decoupled from the request/response cycle by design - that
    decoupling is the entire point (it's what lets jobs run strictly one at
    a time instead of racing each other). A plain sync TestClient request
    can't wait on that background task, so tests call this right after a
    POST to deterministically say "run whatever was just queued, now"."""
    async def _drain():
        while not api_main.JOB_QUEUE.empty():
            job = api_main.JOB_QUEUE.get_nowait()
            await job()
            api_main.JOB_QUEUE.task_done()

    asyncio.run(_drain())


class FakeReport:
    """Stand-in for evidence.report_builder.RunReport."""

    def __init__(self, run_id: str, persona_name: str, goal: str, outcome=RunOutcome.SUCCESS, diagnosis=None):
        self.run_id = run_id
        self.persona_name = persona_name
        self.goal = goal
        self.outcome = outcome
        self.diagnosis = diagnosis
        self.start_time = None
        self.end_time = None
        self.observations = []
        self.action_results = []


class FakeRunOrchestrator:
    """Stand-in for core.orchestrator.RunOrchestrator - no browser, no LLM."""

    def __init__(self, config, agent_service=None, progress_callback=None):
        self.config = config
        self.supabase_upload_result = None

    async def run(self, goal, start_url, persona_name, device_name=None, run_id=None):
        return FakeReport(run_id=run_id, persona_name=persona_name, goal=goal)


class FailingRunOrchestrator(FakeRunOrchestrator):
    async def run(self, goal, start_url, persona_name, device_name=None, run_id=None):
        raise RuntimeError("boom")


# ---------------------------------------------------------------------------
# /status
# ---------------------------------------------------------------------------


def test_status_needs_no_auth(client):
    response = client.get("/status")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Auth enforcement
# ---------------------------------------------------------------------------


def test_runs_requires_auth(client):
    response = client.post("/runs", json={"goal": "g", "url": "https://x", "persona": "p"})
    assert response.status_code == 401


def test_runs_rejects_wrong_token(client):
    response = client.post(
        "/runs",
        json={"goal": "g", "url": "https://x", "persona": "p"},
        headers=auth_headers("wrong-token"),
    )
    assert response.status_code == 401


def test_get_run_requires_auth(client):
    response = client.get("/runs/run_does_not_exist")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /runs + GET /runs/{run_id}
# ---------------------------------------------------------------------------


def test_create_run_queues_and_completes(client, monkeypatch):
    monkeypatch.setattr(api_main, "RunOrchestrator", FakeRunOrchestrator)

    response = client.post(
        "/runs",
        json={"goal": "sign up", "url": "https://staging.example.com", "persona": "confused_first_time_user"},
        headers=auth_headers(),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "queued"
    run_id = body["run_id"]
    assert run_id.startswith("run_")

    run_queued_jobs()
    status_response = client.get(f"/runs/{run_id}", headers=auth_headers())
    assert status_response.status_code == 200
    status_body = status_response.json()
    assert status_body["status"] == "completed"
    assert status_body["outcome"] == "success"


def test_create_run_failure_reflected_in_status(client, monkeypatch):
    monkeypatch.setattr(api_main, "RunOrchestrator", FailingRunOrchestrator)

    response = client.post(
        "/runs",
        json={"goal": "sign up", "url": "https://staging.example.com", "persona": "p"},
        headers=auth_headers(),
    )
    run_id = response.json()["run_id"]

    run_queued_jobs()
    status_response = client.get(f"/runs/{run_id}", headers=auth_headers())
    body = status_response.json()
    assert body["status"] == "failed"
    assert "boom" in body["error"]


def test_get_unknown_run_is_404(client):
    response = client.get("/runs/run_never_existed", headers=auth_headers())
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /experiments - Supabase upload-per-persona
# ---------------------------------------------------------------------------


class FakeExperimentOrchestrator:
    """Stand-in for core.experiment_orchestrator.ExperimentOrchestrator."""

    def __init__(self, config):
        self.config = config
        self.reports = {}

    def create_experiment(self, name, goal, personas, url=None, parallel=True):
        return ExperimentConfig(
            experiment_id="exp_test_00000000",
            name=name,
            goal=goal,
            url=url,
            personas=personas,
            parallel=parallel,
        )

    async def run_experiment(self, experiment: ExperimentConfig):
        runs = []
        for persona in experiment.personas:
            report = FakeReport(run_id=f"run_{persona}", persona_name=persona, goal=experiment.goal)
            self.reports[persona] = {
                "report": report,
                "reasoning_timeline": [],
                "persona_review": None,
            }
            runs.append(type("FakeExperimentRun", (), {"persona": persona, "status": "completed"})())
        return type("FakeExperimentResult", (), {"runs": runs})()


def test_create_experiment_uploads_each_persona_to_supabase(client, monkeypatch):
    monkeypatch.setattr(api_main, "ExperimentOrchestrator", FakeExperimentOrchestrator)

    uploaded = []

    class FakeUploader:
        def upload_run(self, **kwargs):
            uploaded.append(kwargs["persona_name"])
            return {"success": True, "public_url": f"https://supabase.example/{kwargs['run_id']}"}

    monkeypatch.setattr(api_main, "create_supabase_uploader", lambda cfg: FakeUploader())

    response = client.post(
        "/experiments",
        json={
            "goal": "complete onboarding",
            "url": "https://staging.example.com",
            "personas": ["confused_first_time_user", "power_user"],
            "parallel": True,
        },
        headers=auth_headers(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "queued"
    assert body["experiment_id"] == "exp_test_00000000"

    run_queued_jobs()
    assert sorted(uploaded) == ["confused_first_time_user", "power_user"]


def test_create_experiment_requires_auth(client):
    response = client.post(
        "/experiments",
        json={"goal": "g", "url": "https://x", "personas": ["p"]},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /audits + GET /audits/{audit_id}
# ---------------------------------------------------------------------------


def _sample_audit_report() -> AuditReport:
    return AuditReport(
        overall_score=6.0,
        label="Strong concept, pre-launch friction",
        verdict="Clear concept, weak CTA.",
        verdict_summary="A one-paragraph summary.",
        honest_verdict="A blunter paragraph.",
        context={
            "page_type": "Pre-launch waitlist landing page",
            "primary_goal": "Capture emails",
            "likely_audience": "Early adopters",
            "audience_awareness": "Problem-aware",
            "visitor_motivation": "Curiosity",
            "assumptions_to_respect": [],
        },
        story=[],
        scores=[
            {"dimension": "Message & Clarity", "score": 7.0, "rationale": "r"},
            {"dimension": "Audience Fit", "score": 6.0, "rationale": "r"},
            {"dimension": "Action Path", "score": 5.0, "rationale": "r"},
            {"dimension": "Trust & Credibility", "score": 6.0, "rationale": "r"},
            {"dimension": "Content Depth", "score": 5.0, "rationale": "r"},
        ],
        growth={
            "seo": {"score": 5.0, "findings": []},
            "visual_design": {"score": 6.0, "findings": []},
            "navigation": {"score": 8.0, "findings": []},
            "strategic_options": [],
        },
        visual_teaser={"dominant_colors": [], "font_families": []},
        strengths=[],
        decision_gaps=[],
        jargon_terms=[],
        browsing_evidence={
            "total_interactive_elements": 2,
            "safe_cta_candidates": 2,
            "tested_count": 2,
            "primary_label": "Join the waitlist",
            "annotations": [],
            "tests": [],
        },
        primary_fix={"issue": "i", "why": "w", "action": "a"},
        next_fixes=[],
        rewrites=[],
        images={"above_fold": "/tmp/a.png", "full_page": "/tmp/f.png", "annotated": "/tmp/n.png"},
        visitor_persona="A curious early adopter.",
    )


class FakeAuditOrchestrator:
    """Stand-in for core.audit_orchestrator.AuditOrchestrator - no browser, no LLM."""

    def __init__(self, config):
        self.config = config

    async def run_audit(self, url, persona=None, audit_id=None):
        return _sample_audit_report()


class FailingAuditOrchestrator(FakeAuditOrchestrator):
    async def run_audit(self, url, persona=None, audit_id=None):
        raise RuntimeError("audit boom")


def test_create_audit_queues_and_completes(client, monkeypatch):
    monkeypatch.setattr(api_main, "AuditOrchestrator", FakeAuditOrchestrator)

    response = client.post(
        "/audits",
        json={"url": "https://staging.example.com"},
        headers=auth_headers(),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "queued"
    audit_id = body["audit_id"]
    assert audit_id.startswith("audit_")

    run_queued_jobs()
    status_response = client.get(f"/audits/{audit_id}", headers=auth_headers())
    assert status_response.status_code == 200
    status_body = status_response.json()
    assert status_body["status"] == "completed"
    assert status_body["report"]["overall_score"] == 6.0
    assert status_body["report"]["label"] == "Strong concept, pre-launch friction"
    assert len(status_body["report"]["scores"]) == 5


def test_create_audit_failure_reflected_in_status(client, monkeypatch):
    monkeypatch.setattr(api_main, "AuditOrchestrator", FailingAuditOrchestrator)

    response = client.post(
        "/audits",
        json={"url": "https://staging.example.com"},
        headers=auth_headers(),
    )
    audit_id = response.json()["audit_id"]

    run_queued_jobs()
    status_response = client.get(f"/audits/{audit_id}", headers=auth_headers())
    body = status_response.json()
    assert body["status"] == "failed"
    assert "audit boom" in body["error"]
    assert body["report"] is None


def test_get_unknown_audit_is_404(client):
    response = client.get("/audits/audit_never_existed", headers=auth_headers())
    assert response.status_code == 404


def test_get_audit_falls_back_to_supabase_when_audit_store_has_lost_it(client, monkeypatch):
    """Regression test for a real production gap: a completed audit became
    permanently unviewable once its AUDIT_STORE entry was lost to a routine
    backend redeploy, even though its full report was safely in Supabase."""
    report = _sample_audit_report()

    class FakeUploaderWithRow:
        def get_audit(self, audit_id):
            if audit_id == "audit_lost_from_memory":
                return {"report_json": report.model_dump(mode="json")}
            return None

    monkeypatch.setattr(api_main, "create_supabase_uploader", lambda cfg: FakeUploaderWithRow())

    # Deliberately not in AUDIT_STORE - simulates the entry having been lost.
    response = client.get("/audits/audit_lost_from_memory", headers=auth_headers())

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["report"]["overall_score"] == report.overall_score


def test_queued_jobs_run_strictly_one_at_a_time(client, monkeypatch):
    """The actual production incident this guards against: firing several
    audits at once used to spin up independent BackgroundTasks that ran
    concurrently, which (on Cloud Run) triggered a scale-up followed by a
    scale-down that silently killed whichever jobs landed on the reclaimed
    instance. JOB_QUEUE + the single _job_worker consumer must guarantee
    only one job's orchestrator.run_audit() is ever actually executing at
    once, no matter how many requests arrive first."""
    active_count = {"current": 0, "max_seen": 0}

    class TrackingAuditOrchestrator(FakeAuditOrchestrator):
        async def run_audit(self, url, persona=None, audit_id=None):
            active_count["current"] += 1
            active_count["max_seen"] = max(active_count["max_seen"], active_count["current"])
            await asyncio.sleep(0.05)
            active_count["current"] -= 1
            return _sample_audit_report()

    monkeypatch.setattr(api_main, "AuditOrchestrator", TrackingAuditOrchestrator)

    audit_ids = [
        client.post("/audits", json={"url": "https://staging.example.com"}, headers=auth_headers()).json()["audit_id"]
        for _ in range(3)
    ]

    # Nothing has drained the queue yet - all three requests must have
    # returned immediately without waiting for each other or for execution.
    assert api_main.JOB_QUEUE.qsize() == 3
    for audit_id in audit_ids:
        assert api_main.AUDIT_STORE[audit_id]["status"] == "queued"

    run_queued_jobs()

    assert active_count["max_seen"] == 1
    for audit_id in audit_ids:
        assert api_main.AUDIT_STORE[audit_id]["status"] == "completed"


def test_create_audit_requires_auth(client):
    response = client.post("/audits", json={"url": "https://x"})
    assert response.status_code == 401


def test_get_audit_requires_auth(client):
    response = client.get("/audits/audit_does_not_exist")
    assert response.status_code == 401


def test_get_audit_image_serves_known_file(client, tmp_path, monkeypatch):
    monkeypatch.setattr(api_main.config, "artifacts_path", str(tmp_path))
    audit_id = "audit_20260101_000000_test1234"
    api_main.AUDIT_STORE[audit_id] = {"status": "completed", "report": None, "error": None}
    image_dir = tmp_path / audit_id
    image_dir.mkdir(parents=True)
    (image_dir / "annotated.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")

    response = client.get(f"/audits/{audit_id}/images/annotated.png", headers=auth_headers())

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == b"\x89PNG\r\n\x1a\nfake"


def test_get_audit_image_rejects_unknown_filename(client):
    audit_id = "audit_20260101_000000_test1234"
    api_main.AUDIT_STORE[audit_id] = {"status": "completed", "report": None, "error": None}

    response = client.get(f"/audits/{audit_id}/images/../../etc/passwd", headers=auth_headers())

    assert response.status_code == 404


def test_get_audit_image_rejects_unknown_audit(client):
    response = client.get("/audits/audit_never_existed/images/annotated.png", headers=auth_headers())
    assert response.status_code == 404


def test_get_audit_image_requires_auth(client):
    response = client.get("/audits/audit_never_existed/images/annotated.png")
    assert response.status_code == 401


class FakeScheduleStore:
    """In-memory stand-in for ScheduleStore, mirroring its public interface
    (including claim_due_schedule's atomic-or-not semantics) so /schedules
    and /internal/scheduler/tick can be exercised without a real Supabase
    project. The atomic-claim guarantee itself is unit-tested against a
    mocked postgrest client in test_schedule_store.py."""

    def __init__(self):
        self.rows: dict[str, dict] = {}

    def list_schedules(self):
        return list(self.rows.values())

    def get_schedule(self, schedule_id):
        return self.rows.get(schedule_id)

    def create_schedule(self, schedule_id, **fields):
        row = {"schedule_id": schedule_id, "last_run_id": None, "last_triggered_at": None, **fields}
        self.rows[schedule_id] = row
        return row

    def update_schedule(self, schedule_id, **fields):
        row = self.rows.get(schedule_id)
        if row is None:
            return None
        row.update({k: v for k, v in fields.items() if v is not None})
        return row

    def delete_schedule(self, schedule_id):
        return self.rows.pop(schedule_id, None) is not None

    def get_due_schedule_ids(self, now):
        from datetime import datetime as _dt

        return [
            sid
            for sid, row in self.rows.items()
            if row["enabled"] and _dt.fromisoformat(row["next_run_at"]) <= now
        ]

    def claim_due_schedule(self, schedule_id, interval_minutes, now):
        from datetime import timedelta as _td

        row = self.rows.get(schedule_id)
        if row is None or not row["enabled"]:
            return False
        from datetime import datetime as _dt

        if _dt.fromisoformat(row["next_run_at"]) > now:
            return False  # already claimed by a prior call in this same test
        row["next_run_at"] = (now + _td(minutes=interval_minutes)).isoformat()
        row["last_triggered_at"] = now.isoformat()
        return True

    def record_last_run(self, schedule_id, run_or_audit_id):
        if schedule_id in self.rows:
            self.rows[schedule_id]["last_run_id"] = run_or_audit_id


def test_create_schedule_requires_auth(client):
    response = client.post("/schedules", json={"name": "x", "mode": "run", "url": "https://x", "goal": "g", "interval_minutes": 30})
    assert response.status_code == 401


def test_create_schedule_without_supabase_returns_503(client, monkeypatch):
    monkeypatch.setattr(api_main, "create_schedule_store", lambda cfg: None)
    response = client.post(
        "/schedules",
        json={"name": "x", "mode": "run", "url": "https://x", "goal": "g", "interval_minutes": 30},
        headers=auth_headers(),
    )
    assert response.status_code == 503


def test_create_schedule_rejects_run_mode_without_goal(client, monkeypatch):
    monkeypatch.setattr(api_main, "create_schedule_store", lambda cfg: FakeScheduleStore())
    response = client.post(
        "/schedules",
        json={"name": "x", "mode": "run", "url": "https://x", "interval_minutes": 30},
        headers=auth_headers(),
    )
    assert response.status_code == 400


def test_create_list_update_delete_schedule(client, monkeypatch):
    store = FakeScheduleStore()
    monkeypatch.setattr(api_main, "create_schedule_store", lambda cfg: store)

    created = client.post(
        "/schedules",
        json={"name": "Daily signup check", "mode": "run", "url": "https://x", "goal": "sign up", "interval_minutes": 30},
        headers=auth_headers(),
    )
    assert created.status_code == 200
    schedule_id = created.json()["schedule_id"]

    listed = client.get("/schedules", headers=auth_headers())
    assert listed.status_code == 200
    assert [s["schedule_id"] for s in listed.json()] == [schedule_id]

    updated = client.patch(f"/schedules/{schedule_id}", json={"enabled": False}, headers=auth_headers())
    assert updated.status_code == 200
    assert updated.json()["enabled"] is False

    deleted = client.delete(f"/schedules/{schedule_id}", headers=auth_headers())
    assert deleted.status_code == 200
    assert client.get("/schedules", headers=auth_headers()).json() == []


def test_scheduler_tick_triggers_due_schedule_and_skips_busy_one(client, monkeypatch):
    store = FakeScheduleStore()
    monkeypatch.setattr(api_main, "create_schedule_store", lambda cfg: store)
    monkeypatch.setattr(api_main, "RunOrchestrator", FakeRunOrchestrator)

    past = "2020-01-01T00:00:00"
    store.create_schedule(
        "sched_due", name="due", mode="run", url="https://x", goal="g", persona=None, device=None,
        network=None, interval_minutes=30, enabled=True, next_run_at=past,
    )
    store.create_schedule(
        "sched_busy", name="busy", mode="run", url="https://x", goal="g", persona=None, device=None,
        network=None, interval_minutes=30, enabled=True, next_run_at=past,
    )
    api_main.RUN_STORE["run_already_running"] = {"status": "running", "outcome": None, "diagnosis": None, "supabase_url": None, "error": None}
    store.rows["sched_busy"]["last_run_id"] = "run_already_running"

    response = client.post("/internal/scheduler/tick", headers=auth_headers())

    assert response.status_code == 200
    body = response.json()
    assert body["triggered"] == ["sched_due"]
    assert body["skipped_busy"] == ["sched_busy"]
    # The due schedule's next_run_at must have advanced, not stayed in the past.
    assert store.rows["sched_due"]["next_run_at"] > past


def test_scheduler_tick_requires_auth(client):
    response = client.post("/internal/scheduler/tick")
    assert response.status_code == 401


class FakeSiteAuditOrchestrator:
    """Stand-in for core.site_audit_orchestrator.SiteAuditOrchestrator - no
    browser, no LLM, no real crawl."""

    def __init__(self, config):
        self.config = config

    async def run_site_audit(
        self, seed_url, persona=None, max_pages=None, max_depth=None,
        login=None, storage_state=None, site_audit_id=None, on_page_complete=None,
    ):
        from src.core.site_crawl import CrawlManifest

        manifest = CrawlManifest()
        page_audit_id = f"{site_audit_id}_p0"
        manifest.mark_audited(seed_url, page_audit_id)
        if on_page_complete:
            result = on_page_complete(seed_url, page_audit_id, _sample_audit_report())
            if hasattr(result, "__await__"):
                await result
        return site_audit_id, manifest


class FailingSiteAuditOrchestrator(FakeSiteAuditOrchestrator):
    async def run_site_audit(self, *args, **kwargs):
        raise RuntimeError("crawl boom")


def test_create_site_audit_requires_auth(client):
    response = client.post("/site-audits", json={"seed_url": "https://staging.example.com"})
    assert response.status_code == 401


def test_create_site_audit_queues_and_completes(client, monkeypatch):
    monkeypatch.setattr(api_main, "SiteAuditOrchestrator", FakeSiteAuditOrchestrator)

    created = client.post(
        "/site-audits", json={"seed_url": "https://staging.example.com", "max_pages": 5}, headers=auth_headers()
    )
    assert created.status_code == 200
    site_audit_id = created.json()["site_audit_id"]
    assert created.json()["status"] == "queued"

    run_queued_jobs()
    status = client.get(f"/site-audits/{site_audit_id}", headers=auth_headers())
    assert status.status_code == 200
    body = status.json()
    assert body["status"] == "completed"
    assert body["pages_audited"] == 1
    assert len(body["pages"]) == 1
    assert body["pages"][0]["url"] == "https://staging.example.com"

    # The individual page is a real, independently-fetchable audit via the
    # existing GET /audits/{audit_id} - no new per-page endpoint needed.
    page_audit_id = body["pages"][0]["audit_id"]
    page_response = client.get(f"/audits/{page_audit_id}", headers=auth_headers())
    assert page_response.status_code == 200
    assert page_response.json()["status"] == "completed"


def test_create_site_audit_failure_reflected_in_status(client, monkeypatch):
    monkeypatch.setattr(api_main, "SiteAuditOrchestrator", FailingSiteAuditOrchestrator)

    created = client.post("/site-audits", json={"seed_url": "https://staging.example.com"}, headers=auth_headers())
    site_audit_id = created.json()["site_audit_id"]

    run_queued_jobs()
    status = client.get(f"/site-audits/{site_audit_id}", headers=auth_headers())
    assert status.json()["status"] == "failed"
    assert "crawl boom" in status.json()["error"]


def test_create_site_audit_password_never_appears_in_any_response(client, monkeypatch):
    """The literal security guarantee from the plan: a login password must
    never be echoed back by the API, in the create response or the status
    poll."""
    monkeypatch.setattr(api_main, "SiteAuditOrchestrator", FakeSiteAuditOrchestrator)

    created = client.post(
        "/site-audits",
        json={
            "seed_url": "https://staging.example.com",
            "login": {"url": "https://staging.example.com/login", "username": "test@example.com", "password": "hunter2"},
        },
        headers=auth_headers(),
    )
    site_audit_id = created.json()["site_audit_id"]
    assert "hunter2" not in created.text

    status = client.get(f"/site-audits/{site_audit_id}", headers=auth_headers())
    assert "hunter2" not in status.text


async def test_site_audit_status_reflects_progress_before_the_crawl_finishes(monkeypatch):
    """Regression test: SITE_AUDIT_STORE used to only get its manifest/
    pages_audited written once, after run_site_audit() fully returned - so a
    poll mid-crawl always saw manifest={}/pages_audited=0 regardless of real
    progress, discovered via a live end-to-end run. _on_page_complete must
    update the store as each page finishes, not just at the very end."""
    from src.api.schemas import SiteAuditRequest

    site_audit_id = "site_audit_progress_test"
    api_main.SITE_AUDIT_STORE[site_audit_id] = {
        "status": "queued", "seed_url": "https://staging.example.com", "max_pages": 5,
        "pages_discovered": 0, "pages_audited": 0, "manifest": {}, "error": None,
    }

    seen_mid_crawl: dict = {}

    class PausingOrchestrator(FakeSiteAuditOrchestrator):
        async def run_site_audit(self, *args, site_audit_id=None, on_page_complete=None, **kwargs):
            await on_page_complete("https://staging.example.com/page1", f"{site_audit_id}_p0", _sample_audit_report())
            # Snapshot (deep copy - the store's manifest dict is mutated in
            # place by later pages) the live store before the crawl finishes -
            # this is what a real client's poll would see mid-crawl.
            seen_mid_crawl.update(copy.deepcopy(api_main.SITE_AUDIT_STORE[site_audit_id]))
            await on_page_complete("https://staging.example.com/page2", f"{site_audit_id}_p1", _sample_audit_report())
            from src.core.site_crawl import CrawlManifest
            manifest = CrawlManifest()
            manifest.mark_audited("https://staging.example.com/page1", f"{site_audit_id}_p0")
            manifest.mark_audited("https://staging.example.com/page2", f"{site_audit_id}_p1")
            return site_audit_id, manifest

    monkeypatch.setattr(api_main, "SiteAuditOrchestrator", PausingOrchestrator)

    await api_main._execute_site_audit(site_audit_id, SiteAuditRequest(seed_url="https://staging.example.com"))

    assert seen_mid_crawl["pages_audited"] == 1
    assert seen_mid_crawl["manifest"] == {
        "https://staging.example.com/page1": {"status": "audited", "audit_id": f"{site_audit_id}_p0"}
    }


def test_get_unknown_site_audit_is_404(client):
    response = client.get("/site-audits/site_audit_never_existed", headers=auth_headers())
    assert response.status_code == 404


def test_get_site_audit_requires_auth(client):
    response = client.get("/site-audits/site_audit_never_existed")
    assert response.status_code == 401
