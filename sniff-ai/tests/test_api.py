"""Tests for the FastAPI backend (src/api/main.py).

Mocks RunOrchestrator/ExperimentOrchestrator and the Supabase uploader so no
real Playwright browser, Gemini/k2-horizon call, or Supabase upload happens.
"""

import pytest
from fastapi.testclient import TestClient

import src.api.main as api_main
from src.core.audit_models import AuditReport
from src.core.experiment_models import ExperimentConfig
from src.core.state_machine import RunOutcome


@pytest.fixture(autouse=True)
def api_token(monkeypatch):
    """Give every test a known shared-secret token and a clean run/audit store."""
    monkeypatch.setattr(api_main.config.api, "token", "test-token")
    api_main.RUN_STORE.clear()
    api_main.AUDIT_STORE.clear()
    yield
    api_main.RUN_STORE.clear()
    api_main.AUDIT_STORE.clear()


@pytest.fixture
def client():
    return TestClient(api_main.app)


def auth_headers(token: str = "test-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


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

    # TestClient runs BackgroundTasks synchronously as part of the request,
    # so by now the fake run has already completed.
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

    # Background task (run synchronously by TestClient) uploaded both personas.
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

    # TestClient runs BackgroundTasks synchronously, so the fake audit has
    # already completed by the time we poll.
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

    status_response = client.get(f"/audits/{audit_id}", headers=auth_headers())
    body = status_response.json()
    assert body["status"] == "failed"
    assert "audit boom" in body["error"]
    assert body["report"] is None


def test_get_unknown_audit_is_404(client):
    response = client.get("/audits/audit_never_existed", headers=auth_headers())
    assert response.status_code == 404


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
