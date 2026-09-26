"""FastAPI app for triggering and monitoring Sniff runs from a web UI.

Endpoints:
- POST /runs - start a single-persona run in the background, returns run_id immediately
- GET /runs/{run_id} - poll run status/result
- POST /experiments - start a multi-persona experiment in the background
- POST/GET/PATCH/DELETE /schedules - recurring run/audit definitions (requires Supabase)
- POST /internal/scheduler/tick - ticked by an external Cloud Scheduler job, not the frontend
- GET /status - liveness check, no auth

Phase 1 scope (see docs/product/SAAS_ROADMAP.md):
- Auth is a single shared bearer token (SNIFF_API_TOKEN), not per-user auth.
- Runs execute as in-process FastAPI BackgroundTasks, not a real job queue.
- Run/experiment status lives in a module-level dict (RUN_STORE below) -
  this is lost on process restart. A persistent job store is Phase 2.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from ..core.audit_orchestrator import AuditOrchestrator
from ..core.config import SniffConfig, get_config
from ..core.experiment_models import ExperimentConfig
from ..core.experiment_orchestrator import ExperimentOrchestrator
from ..core.models import DiagnosisResult
from ..core.orchestrator import RunOrchestrator
from ..integrations.supabase_client import create_schedule_store, create_supabase_uploader
from .schemas import (
    AuditRequest,
    AuditResponse,
    AuditStatusResponse,
    DiagnosisSummary,
    ExperimentRequest,
    ExperimentResponse,
    HealthResponse,
    RunRequest,
    RunResponse,
    RunStatusResponse,
    ScheduleRequest,
    ScheduleResponse,
    ScheduleUpdateRequest,
    TickResponse,
)

logger = logging.getLogger(__name__)

config: SniffConfig = get_config()

# ponytail: module-level in-process dict keyed by run_id, tracking
# queued/running/completed/failed status + result summary. Lost on process
# restart, not shared across worker processes. A real persisted job store is
# Phase 2 (docs/product/SAAS_ROADMAP.md section 3) once there's an actual queue.
RUN_STORE: dict[str, dict[str, Any]] = {}

# Same pattern as RUN_STORE, for landing-page audits. No Supabase dependency -
# GET /audits/{audit_id} returns the full AuditReport straight out of this
# in-process dict once status == "completed".
AUDIT_STORE: dict[str, dict[str, Any]] = {}

app = FastAPI(title="Sniff API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.api.cors_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_auth(authorization: str | None = Header(default=None)) -> None:
    """Phase-1 shared-secret gate: Authorization: Bearer <SNIFF_API_TOKEN>.

    Real per-user auth is Phase 2 (docs/product/SAAS_ROADMAP.md section 1).
    """
    if not config.api.token:
        raise HTTPException(status_code=503, detail="SNIFF_API_TOKEN is not configured on the server")
    if authorization != f"Bearer {config.api.token}":
        raise HTTPException(status_code=401, detail="Missing or invalid bearer token")


@app.get("/status", response_model=HealthResponse)
def status_check() -> HealthResponse:
    """Liveness check for hosting platforms. No auth required.

    Deliberately NOT named /healthz or / - both are reserved on Cloud Run's
    default *.run.app domain (Google's own edge intercepts them and serves a
    generic error page before the request ever reaches this app - confirmed
    live: a random unregistered path correctly reached FastAPI's own 404,
    while /healthz and / never did, regardless of deployment/auth config).
    """
    return HealthResponse(status="ok")


def _diagnosis_summary(diagnosis: DiagnosisResult | None) -> DiagnosisSummary | None:
    if not diagnosis:
        return None
    return DiagnosisSummary(
        rootCause=diagnosis.rootCause,
        severity=diagnosis.severity,
        likelyOwner=diagnosis.likelyOwner,
        suggestedFix=diagnosis.suggestedFix,
    )


async def _execute_run(run_id: str, req: RunRequest) -> None:
    """Background task body for a single run. Updates RUN_STORE[run_id] in place."""
    RUN_STORE[run_id]["status"] = "running"
    try:
        from ..agent.decision_service import create_agent_service

        agent_service = None
        try:
            agent_service = create_agent_service(config)
        except Exception as e:
            logger.warning(f"Could not create agent service for run {run_id}: {e}")
            logger.warning("Run will proceed in fallback mode without AI agent")

        orchestrator = RunOrchestrator(config=config, agent_service=agent_service)
        report = await orchestrator.run(
            goal=req.goal,
            start_url=req.url,
            persona_name=req.persona,
            device_name=req.device,
            run_id=run_id,
        )

        supabase_url = None
        if orchestrator.supabase_upload_result and orchestrator.supabase_upload_result.get("success"):
            supabase_url = orchestrator.supabase_upload_result.get("public_url")

        RUN_STORE[run_id].update(
            status="completed",
            outcome=report.outcome.value,
            diagnosis=_diagnosis_summary(report.diagnosis),
            supabase_url=supabase_url,
        )

    except Exception as e:
        logger.error(f"Run {run_id} failed: {e}", exc_info=True)
        RUN_STORE[run_id].update(status="failed", error=str(e))


@app.post("/runs", response_model=RunResponse, dependencies=[Depends(require_auth)])
def create_run(req: RunRequest, background_tasks: BackgroundTasks) -> RunResponse:
    """Start a single-persona run in the background. Returns immediately."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    run_id = f"run_{timestamp}_{uuid4().hex[:8]}"

    RUN_STORE[run_id] = {
        "status": "queued",
        "outcome": None,
        "diagnosis": None,
        "supabase_url": None,
        "error": None,
    }
    background_tasks.add_task(_execute_run, run_id, req)

    return RunResponse(run_id=run_id, status="queued")


@app.get("/runs/{run_id}", response_model=RunStatusResponse, dependencies=[Depends(require_auth)])
def get_run(run_id: str) -> RunStatusResponse:
    """Poll status/result for a previously-started run."""
    entry = RUN_STORE.get(run_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Unknown run_id: {run_id}")
    return RunStatusResponse(run_id=run_id, **entry)


async def _execute_experiment(orchestrator: ExperimentOrchestrator, experiment: ExperimentConfig) -> None:
    """Background task body for an experiment.

    Runs every persona, then uploads each persona's full result to Supabase
    the same way RunOrchestrator does for a single run - experiment sub-runs
    have their own auto-upload disabled (see experiment_orchestrator.py) so
    this is the only place each persona's run gets uploaded, once.
    """
    try:
        result = await orchestrator.run_experiment(experiment)
    except Exception as e:
        logger.error(f"Experiment {experiment.experiment_id} failed: {e}", exc_info=True)
        return

    uploader = create_supabase_uploader(config)
    if not uploader:
        return

    for run in result.runs:
        persona_data = orchestrator.reports.get(run.persona)
        if not persona_data:
            continue

        report = persona_data["report"]
        try:
            upload_result = uploader.upload_run(
                run_id=report.run_id,
                artifacts_dir=Path(config.artifacts_path) / report.run_id,
                goal=report.goal,
                persona_name=report.persona_name,
                outcome=report.outcome.value,
                start_time=report.start_time,
                end_time=report.end_time,
                observations=report.observations,
                action_results=report.action_results,
                diagnosis=report.diagnosis,
                reasoning_timeline=persona_data.get("reasoning_timeline") or None,
                persona_review=persona_data.get("persona_review"),
            )
            if upload_result.get("success"):
                logger.info(
                    f"Uploaded experiment {experiment.experiment_id} persona {run.persona} "
                    f"to Supabase: {upload_result.get('public_url')}"
                )
            else:
                logger.warning(
                    f"Supabase upload failed for experiment {experiment.experiment_id} "
                    f"persona {run.persona}: {upload_result.get('error')}"
                )
        except Exception as e:
            logger.warning(
                f"Supabase upload raised for experiment {experiment.experiment_id} "
                f"persona {run.persona}: {e}"
            )


async def _execute_audit(audit_id: str, req: AuditRequest) -> None:
    """Background task body for a single audit. Updates AUDIT_STORE[audit_id] in place."""
    AUDIT_STORE[audit_id]["status"] = "running"
    try:
        orchestrator = AuditOrchestrator(config=config)
        report = await orchestrator.run_audit(
            url=req.url,
            persona=req.persona,
            audit_id=audit_id,
        )
        AUDIT_STORE[audit_id].update(status="completed", report=report, error=None)

        uploader = create_supabase_uploader(config)
        if uploader:
            upload_result = uploader.upload_audit(
                audit_id=audit_id,
                url=req.url,
                persona=req.persona,
                report=report,
            )
            if not upload_result.get("success"):
                logger.warning(f"Supabase upload failed for audit {audit_id}: {upload_result.get('error')}")

    except Exception as e:
        logger.error(f"Audit {audit_id} failed: {e}", exc_info=True)
        AUDIT_STORE[audit_id].update(status="failed", error=str(e))


@app.post("/audits", response_model=AuditResponse, dependencies=[Depends(require_auth)])
def create_audit(req: AuditRequest, background_tasks: BackgroundTasks) -> AuditResponse:
    """Start a landing-page audit in the background. Returns immediately."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    audit_id = f"audit_{timestamp}_{uuid4().hex[:8]}"

    AUDIT_STORE[audit_id] = {
        "status": "queued",
        "report": None,
        "error": None,
    }
    background_tasks.add_task(_execute_audit, audit_id, req)

    return AuditResponse(audit_id=audit_id, status="queued")


@app.get("/audits/{audit_id}", response_model=AuditStatusResponse, dependencies=[Depends(require_auth)])
def get_audit(audit_id: str) -> AuditStatusResponse:
    """Poll status/result for a previously-started audit."""
    entry = AUDIT_STORE.get(audit_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Unknown audit_id: {audit_id}")
    return AuditStatusResponse(audit_id=audit_id, **entry)


# The three exact filenames screenshot_annotator.capture_audit_screenshots()
# ever writes - a fixed allowlist so audit_id/filename can't be used for path
# traversal (audit_id must also be a real, known AUDIT_STORE key).
_AUDIT_IMAGE_FILENAMES = {"above_fold.png", "full_page.png", "annotated.png"}


@app.get("/audits/{audit_id}/images/{filename}", dependencies=[Depends(require_auth)])
def get_audit_image(audit_id: str, filename: str):
    """Serve one of an audit's screenshots. AuditReport.images.* are bare
    local filesystem paths (no cloud storage configured in this environment) -
    this is what the frontend's image-proxy route handler calls."""
    from fastapi.responses import FileResponse

    if audit_id not in AUDIT_STORE or filename not in _AUDIT_IMAGE_FILENAMES:
        raise HTTPException(status_code=404, detail="Image not found")

    image_path = Path(config.artifacts_path) / audit_id / filename
    if not image_path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(image_path, media_type="image/png")


@app.post("/experiments", response_model=ExperimentResponse, dependencies=[Depends(require_auth)])
def create_experiment(req: ExperimentRequest, background_tasks: BackgroundTasks) -> ExperimentResponse:
    """Start a multi-persona experiment in the background. Returns immediately."""
    orchestrator = ExperimentOrchestrator(config)
    experiment = orchestrator.create_experiment(
        name=f"api_{req.goal[:40]}",
        goal=req.goal,
        personas=req.personas,
        url=req.url,
        parallel=req.parallel,
    )
    background_tasks.add_task(_execute_experiment, orchestrator, experiment)

    return ExperimentResponse(experiment_id=experiment.experiment_id, status="queued")


# -- Schedules: recurring runs/audits -----------------------------------
#
# Persisted in Supabase (ScheduleStore), not an in-process scheduler - this
# service autoscales to multiple Cloud Run instances, and an in-process
# scheduler would independently fire the same job on every instance. An
# external Cloud Scheduler job ticks POST /internal/scheduler/tick on a
# fixed cadence instead; see ScheduleStore.claim_due_schedule for the
# atomic-claim logic that makes concurrent/overlapping ticks safe.


def _require_schedule_store() -> Any:
    store = create_schedule_store(config)
    if store is None:
        raise HTTPException(
            status_code=503,
            detail="Schedules require Supabase to be configured (SUPABASE_ENABLED=true) - there is no other persistent home for schedule definitions.",
        )
    return store


@app.post("/schedules", response_model=ScheduleResponse, dependencies=[Depends(require_auth)])
def create_schedule(req: ScheduleRequest) -> ScheduleResponse:
    """Create a recurring run/audit definition."""
    if req.mode not in ("run", "audit"):
        raise HTTPException(status_code=400, detail="mode must be 'run' or 'audit'")
    if req.mode == "run" and not req.goal:
        raise HTTPException(status_code=400, detail="goal is required when mode='run'")

    store = _require_schedule_store()
    schedule_id = f"sched_{uuid4().hex[:12]}"
    now = datetime.utcnow()
    row = store.create_schedule(
        schedule_id,
        name=req.name,
        mode=req.mode,
        url=req.url,
        goal=req.goal,
        persona=req.persona,
        device=req.device,
        network=req.network,
        interval_minutes=req.interval_minutes,
        enabled=True,
        next_run_at=now.isoformat(),
    )
    return ScheduleResponse(**row)


@app.get("/schedules", response_model=list[ScheduleResponse], dependencies=[Depends(require_auth)])
def list_schedules() -> list[ScheduleResponse]:
    store = _require_schedule_store()
    return [ScheduleResponse(**row) for row in store.list_schedules()]


@app.patch("/schedules/{schedule_id}", response_model=ScheduleResponse, dependencies=[Depends(require_auth)])
def update_schedule(schedule_id: str, req: ScheduleUpdateRequest) -> ScheduleResponse:
    store = _require_schedule_store()
    row = store.update_schedule(
        schedule_id,
        name=req.name,
        enabled=req.enabled,
        interval_minutes=req.interval_minutes,
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"Unknown schedule_id: {schedule_id}")
    return ScheduleResponse(**row)


@app.delete("/schedules/{schedule_id}", dependencies=[Depends(require_auth)])
def delete_schedule(schedule_id: str) -> dict:
    store = _require_schedule_store()
    if not store.delete_schedule(schedule_id):
        raise HTTPException(status_code=404, detail=f"Unknown schedule_id: {schedule_id}")
    return {"deleted": schedule_id}


def _schedule_still_busy(last_run_id: str | None, mode: str) -> bool:
    """True if this schedule's last run/audit is still queued/running -
    guards against a slow run piling up duplicate executions if it outlasts
    its own interval."""
    if not last_run_id:
        return False
    store = RUN_STORE if mode == "run" else AUDIT_STORE
    entry = store.get(last_run_id)
    return entry is not None and entry.get("status") in ("queued", "running")


@app.post("/internal/scheduler/tick", response_model=TickResponse, dependencies=[Depends(require_auth)])
def scheduler_tick(background_tasks: BackgroundTasks) -> TickResponse:
    """Hit by an external Cloud Scheduler job on a fixed cadence (not called
    by the frontend). Finds due schedules, atomically claims each one, and
    enqueues its run/audit via the same background-task path POST /runs and
    POST /audits already use."""
    store = _require_schedule_store()
    now = datetime.utcnow()

    triggered: list[str] = []
    skipped_busy: list[str] = []

    for schedule_id in store.get_due_schedule_ids(now):
        row = store.get_schedule(schedule_id)
        if row is None:
            continue
        if _schedule_still_busy(row.get("last_run_id"), row["mode"]):
            skipped_busy.append(schedule_id)
            continue
        if not store.claim_due_schedule(schedule_id, row["interval_minutes"], now):
            # Another tick claimed it first (overlapping tick calls) - skip.
            continue

        if row["mode"] == "run":
            timestamp = now.strftime("%Y%m%d_%H%M%S")
            run_id = f"run_{timestamp}_{uuid4().hex[:8]}"
            RUN_STORE[run_id] = {"status": "queued", "outcome": None, "diagnosis": None, "supabase_url": None, "error": None}
            req = RunRequest(goal=row["goal"], url=row["url"], persona=row["persona"] or "confused_first_time_user", device=row.get("device"), network=row.get("network"))
            background_tasks.add_task(_execute_run, run_id, req)
            store.record_last_run(schedule_id, run_id)
        else:
            timestamp = now.strftime("%Y%m%d_%H%M%S")
            audit_id = f"audit_{timestamp}_{uuid4().hex[:8]}"
            AUDIT_STORE[audit_id] = {"status": "queued", "report": None, "error": None}
            audit_req = AuditRequest(url=row["url"], persona=row.get("persona"))
            background_tasks.add_task(_execute_audit, audit_id, audit_req)
            store.record_last_run(schedule_id, audit_id)

        triggered.append(schedule_id)

    return TickResponse(ticked_at=now.isoformat(), triggered=triggered, skipped_busy=skipped_busy)
