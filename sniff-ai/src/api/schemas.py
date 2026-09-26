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
