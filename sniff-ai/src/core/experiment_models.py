"""Data models for experiments - running multiple personas against the same flow."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ExperimentConfig(BaseModel):
    """Configuration for an experiment run."""

    experiment_id: str
    name: str
    description: Optional[str] = None
    goal: str
    url: Optional[str] = None
    device: Optional[str] = None
    network: Optional[str] = None
    personas: List[str]  # List of persona names to test
    max_steps: Optional[int] = None
    headless: bool = True
    parallel: bool = False  # Run personas in parallel or sequentially
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ExperimentRun(BaseModel):
    """Individual run within an experiment."""

    experiment_id: str
    run_id: str
    persona: str
    status: str  # pending, running, completed, failed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    outcome: Optional[str] = None  # success, failure, stuck, timeout
    steps_executed: Optional[int] = None
    error: Optional[str] = None


class ExperimentResult(BaseModel):
    """Aggregated results from an experiment."""

    experiment_id: str
    name: str
    goal: str
    total_runs: int
    successful_runs: int
    failed_runs: int
    total_duration_seconds: float
    average_duration_seconds: float
    runs: List[ExperimentRun]
    insights: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    completed_at: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_runs == 0:
            return 0.0
        return (self.successful_runs / self.total_runs) * 100


class PersonaComparison(BaseModel):
    """Comparison between different persona results."""

    persona: str
    outcome: str
    duration_seconds: float
    steps_executed: int
    successful_actions: int
    failed_actions: int
    experience_rating: Optional[int] = None  # 1-10
    abandonment_risk: Optional[str] = None  # low, medium, high
    key_friction_points: List[str] = Field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate action success rate."""
        total = self.successful_actions + self.failed_actions
        if total == 0:
            return 0.0
        return (self.successful_actions / total) * 100


class ExperimentInsights(BaseModel):
    """Insights derived from experiment results."""

    experiment_id: str
    fastest_persona: Optional[str] = None
    slowest_persona: Optional[str] = None
    most_successful_persona: Optional[str] = None
    highest_abandonment_risk: Optional[str] = None
    common_friction_points: List[str] = Field(default_factory=list)
    persona_comparisons: List[PersonaComparison] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
