"""Core data models for sniff mystery shopper system.

Defines contracts between components:
- Observation: Worker → Agent
- AgentDecision: Agent → Orchestrator
- ActionResult: Worker → Orchestrator
- DiagnosisResult: Diagnosis → Orchestrator

Architecture boundaries:
- Agent returns decisions only (no direct execution)
- Worker executes tools only (no decision-making)
- Orchestrator owns control flow and state machine
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class ActionType(str, Enum):
    """Allowed action types for agent decisions."""
    TAP = "tap"
    TYPE = "type"
    SCROLL = "scroll"
    WAIT = "wait"
    BACK = "back"
    ABORT = "abort"


class ScrollDirection(str, Enum):
    """Allowed scroll directions."""
    UP = "up"
    DOWN = "down"


class ActionStatus(str, Enum):
    """Result status from action execution."""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    ELEMENT_NOT_FOUND = "element_not_found"
    INVALID_ACTION = "invalid_action"


class Observation(BaseModel):
    """Structured observation from Execution Worker to Agent Service.

    Captures full browser state after each action including:
    - Navigation context (URL)
    - Visual state (screenshot, visible text)
    - Performance metrics (timing)
    - Error signals (console, network)
    - Action results
    """
    runId: str = Field(..., description="Unique run identifier")
    step: int = Field(..., ge=0, description="Step number in current run")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    url: str = Field(..., description="Current page URL")
    screenshotPath: str = Field(..., description="Absolute path to screenshot artifact")
    visibleText: list[str] = Field(default_factory=list, description="Extracted visible text snippets")
    timing: dict[str, int] = Field(
        default_factory=dict,
        description="Performance metrics: ttfb, domReady in milliseconds"
    )
    consoleErrors: list[str] = Field(default_factory=list, description="Console error messages")
    networkEvents: list[dict[str, Any]] = Field(default_factory=list, description="Network events (errors, slow requests)")
    lastActionResult: dict[str, Any] = Field(
        default_factory=dict,
        description="Result of last action execution"
    )


class AgentDecision(BaseModel):
    """Decision returned by Agent Service to Orchestrator.

    Agent returns ONLY decisions, never executes actions directly.
    Orchestrator validates and passes to Execution Worker.

    Critical validation: When action == "type", inputText is REQUIRED.
    """
    action: Literal["tap", "type", "scroll", "wait", "back", "abort"] = Field(
        ...,
        description="Action to execute"
    )
    target: Optional[str] = Field(
        None,
        description="Target specification: coordinates/text/selector hint"
    )
    inputText: Optional[str] = Field(
        None,
        description="REQUIRED when action='type', text to input into target field"
    )
    scrollDirection: Optional[Literal["up", "down"]] = Field(
        None,
        description="Direction to scroll - REQUIRED when action is 'scroll'"
    )
    waitDurationMs: Optional[int] = Field(
        None,
        description="Wait duration in ms - REQUIRED when action is 'wait'"
    )
    reasoningSummary: str = Field(
        ...,
        description="Brief explanation of why this action was chosen"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score 0-1"
    )
    fallbackAction: Optional['AgentDecision'] = Field(
        None,
        description="Alternative action if primary fails"
    )
    abortReason: Optional[str] = Field(
        None,
        description="Reason for abort - REQUIRED when action is 'abort'"
    )

    @model_validator(mode='after')
    def validate_action_requirements(self) -> 'AgentDecision':
        """Validate action-specific required fields."""
        if self.action == "type" and not self.inputText:
            raise ValueError("inputText is REQUIRED when action='type'")

        if self.action == "scroll" and not self.scrollDirection:
            raise ValueError("scrollDirection is REQUIRED when action='scroll'")

        if self.action == "wait" and not self.waitDurationMs:
            raise ValueError("waitDurationMs is REQUIRED when action='wait'")

        if self.action == "abort" and not self.abortReason:
            raise ValueError("abortReason is REQUIRED when action='abort'")

        if self.action == "tap" and not self.target:
            raise ValueError("target is REQUIRED when action='tap'")

        return self


class DiagnosisResult(BaseModel):
    """Diagnosis output from Diagnosis Engine.

    Classifies failures with root cause, severity, and actionable next steps.
    """
    rootCause: Literal["Backend", "UX/Content", "Performance", "Integration"] = Field(
        ...,
        description="Root cause category"
    )
    severity: Literal["P0", "P1", "P2", "P3"] = Field(
        ...,
        description="Severity level: P0=blocking, P1=major friction, P2=workaround exists, P3=minor"
    )
    evidence: dict[str, Any] = Field(
        default_factory=dict,
        description="Supporting evidence (screenshots, logs, metrics)"
    )
    likelyOwner: str = Field(
        ...,
        description="Team/person likely responsible for fix"
    )
    reproSteps: list[str] = Field(
        default_factory=list,
        description="Ordered steps to reproduce the issue"
    )
    suggestedFix: str = Field(
        ...,
        description="Recommended resolution approach"
    )


class ActionResult(BaseModel):
    """Result of an action execution by the Execution Worker.

    Returned by Worker to Orchestrator after each action execution.
    """
    success: bool = Field(..., description="Whether action succeeded")
    action: str = Field(..., description="Action that was attempted")
    status: Literal["success", "failed", "timeout", "element_not_found", "invalid_action"] = Field(
        ...,
        description="Detailed status of action execution"
    )
    target: Optional[str] = Field(None, description="Target that was acted upon")
    error: Optional[str] = Field(None, description="Error message if failed")
    screenshotPath: Optional[str] = Field(None, description="Screenshot captured during action")
    durationMs: int = Field(..., description="Action execution time in ms")
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional execution details"
    )
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SanitizedDecision(BaseModel):
    """Result of decision sanitization process.

    Used by validation layer to return either a valid decision or fallback.
    """
    decision: AgentDecision
    wasSanitized: bool = Field(False, description="Whether decision was modified during sanitization")
    sanitizationReason: Optional[str] = Field(None, description="Reason for sanitization if applied")
    originalAction: Optional[str] = Field(None, description="Original action if sanitized")


# Update forward references for recursive types
AgentDecision.model_rebuild()
