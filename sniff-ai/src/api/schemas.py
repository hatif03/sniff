"""Pydantic request/response models for the FastAPI backend (src/api/main.py)."""


from pydantic import BaseModel, Field

from ..core.audit_models import AuditReport


class RunRequest(BaseModel):
    """Body for POST /runs."""
    goal: str = Field(..., description="User-defined test goal")
    url: str = Field(..., description="Starting URL for navigation")
    persona: str = Field(..., description="Persona name to use")
    device: str | None = Field(default=None, description="Device profile (defaults from config)")
    network: str | None = Field(default=None, description="Network profile (4g|3g|slow3g)")


class RunResponse(BaseModel):
    """Response for POST /runs - the run is queued, not yet complete."""
    run_id: str
    status: str


class ExperimentRequest(BaseModel):
    """Body for POST /experiments."""
    goal: str = Field(..., description="User-defined test goal")
    url: str = Field(..., description="Starting URL for navigation")
    personas: list[str] = Field(..., description="Persona names to test")
    parallel: bool = Field(default=True, description="Run personas in parallel or sequentially")


class ExperimentResponse(BaseModel):
    """Response for POST /experiments - the experiment is queued, not yet complete."""
    experiment_id: str
    status: str


class DiagnosisSummary(BaseModel):
    """Diagnosis fields surfaced to API callers polling a run."""
    rootCause: str | None = None
    severity: str | None = None
    likelyOwner: str | None = None
    suggestedFix: str | None = None


class RunStatusResponse(BaseModel):
    """Response for GET /runs/{run_id}.

    `status` tracks the in-process lifecycle (queued/running/completed/
    failed); `outcome` is the orchestrator's own result (success/failure/
    timeout/aborted/error), only set once `status` is completed or failed.
    """
    run_id: str
    status: str
    outcome: str | None = None
    diagnosis: DiagnosisSummary | None = None
    supabase_url: str | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: str


class AuditRequest(BaseModel):
    """Body for POST /audits."""
    url: str = Field(..., description="Landing page URL to audit")
    persona: str | None = Field(default=None, description="Persona name (defaults to confused_first_time_user)")


class AuditResponse(BaseModel):
    """Response for POST /audits - the audit is queued, not yet complete."""
    audit_id: str
    status: str


class AuditStatusResponse(BaseModel):
    """Response for GET /audits/{audit_id}.

    `status` tracks the in-process lifecycle (queued/running/completed/
    failed); `report` is only set once `status == "completed"`.
    """
    audit_id: str
    status: str
    report: AuditReport | None = None
    error: str | None = None


class ScheduleRequest(BaseModel):
    """Body for POST /schedules."""
    name: str = Field(..., description="Human-readable label")
    mode: str = Field(..., description="'run' or 'audit'")
    url: str
    goal: str | None = Field(default=None, description="Required when mode='run', ignored for 'audit'")
    persona: str | None = None
    device: str | None = None
    network: str | None = None
    interval_minutes: int = Field(..., ge=5, description="Minimum 5 minutes - matches the tick cadence")


class ScheduleUpdateRequest(BaseModel):
    """Body for PATCH /schedules/{schedule_id} - every field optional, only provided ones change."""
    name: str | None = None
    enabled: bool | None = None
    interval_minutes: int | None = Field(default=None, ge=5)


class ScheduleResponse(BaseModel):
    schedule_id: str
    name: str
    mode: str
    url: str
    goal: str | None = None
    persona: str | None = None
    device: str | None = None
    network: str | None = None
    interval_minutes: int
    enabled: bool
    next_run_at: str
    last_run_id: str | None = None
    last_triggered_at: str | None = None


class TickResponse(BaseModel):
    """Response for POST /internal/scheduler/tick."""
    ticked_at: str
    triggered: list[str] = Field(default_factory=list, description="schedule_ids that fired this tick")
    skipped_busy: list[str] = Field(default_factory=list, description="schedule_ids skipped - previous run still in flight")


class SiteAuditLogin(BaseModel):
    """Optional username/password login, used exactly once to establish a
    session before the crawl starts - never stored or echoed back anywhere."""
    url: str = Field(..., description="Login page URL")
    username: str
    password: str = Field(..., description="Used once in-memory to log in, then discarded - never persisted or logged")


class SiteAuditRequest(BaseModel):
    """Body for POST /site-audits."""
    seed_url: str = Field(..., description="Starting page - the rest of the site is discovered from here")
    persona: str | None = None
    max_pages: int | None = Field(default=None, ge=1, le=30, description="Defaults to the server's configured cap")
    max_depth: int | None = Field(default=None, ge=1)
    login: SiteAuditLogin | None = Field(default=None, description="Alternative to storage_state - a one-time username/password login")
    storage_state: dict | None = Field(
        default=None, description="Alternative to login - a pre-authenticated Playwright storage_state export"
    )


class SiteAuditResponse(BaseModel):
    """Response for POST /site-audits - queued, not yet complete."""
    site_audit_id: str
    status: str


class SiteAuditPageSummary(BaseModel):
    audit_id: str
    url: str
    overall_score: float | None = None
    label: str | None = None


class SiteAuditStatusResponse(BaseModel):
    """Response for GET /site-audits/{site_audit_id}.

    `manifest` records every URL the crawl considered and what happened to
    it (audited/skipped/failed + why) - updated incrementally as pages
    complete, not only once the whole crawl finishes.
    """
    site_audit_id: str
    status: str
    seed_url: str
    max_pages: int
    pages_discovered: int = 0
    pages_audited: int = 0
    manifest: dict = Field(default_factory=dict)
    pages: list[SiteAuditPageSummary] = Field(default_factory=list)
    error: str | None = None
