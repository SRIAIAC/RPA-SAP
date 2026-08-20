"""Cross-cutting platform tables added for the AI/integration/audit upgrade.

These are additive to app/models.py (never edited) and follow the same
conventions: no SQLModel Relationship() objects, manual FK lookups via
session.get(Model, id) in routers/services, str enums stored as plain str
columns where a fixed vocabulary exists but doesn't need a DB-level enum.
"""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class IntegrationLog(SQLModel, table=True):
    """One row per outbound call from SAPIntegrationService / NonSAPIntegrationService
    to a mock (or, later, real) provider. Powers the Integration Monitor page."""

    id: Optional[int] = Field(default=None, primary_key=True)
    provider: str = Field(index=True)  # "sap" | "nonsap"
    system: str = Field(index=True)  # e.g. "SAP MM", "SCADA", "CRM"
    endpoint: str
    method: str = Field(default="GET")
    success: bool = Field(default=True)
    status_code: Optional[int] = None
    latency_ms: float = Field(default=0.0)
    correlation_id: str = Field(index=True)
    workflow_run_id: Optional[int] = Field(default=None, foreign_key="workflowrun.id", index=True)
    request_summary: Optional[str] = None
    response_summary: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class AIDecision(SQLModel, table=True):
    """One row per MockAIProvider call, capturing the full AI -> Recommendation ->
    Rules -> Final Decision chain for a workflow step. Powers the AI Decisions page
    and the run-detail decision trace."""

    id: Optional[int] = Field(default=None, primary_key=True)
    workflow_run_id: Optional[int] = Field(default=None, foreign_key="workflowrun.id", index=True)
    use_case: str = Field(index=True)  # e.g. "invoice_extraction", "hse_classification"
    correlation_id: str = Field(index=True)
    input_summary: str
    classification: Optional[str] = None
    confidence: Optional[float] = None
    recommendation: Optional[str] = None
    rules_result: Optional[str] = None
    final_decision: Optional[str] = None
    human_decision: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class Event(SQLModel, table=True):
    """Rows published through the EventBus (e.g. EquipmentAlarmEvent). Additive
    audit trail of event-driven activity, independent of the in-memory bus itself."""

    id: Optional[int] = Field(default=None, primary_key=True)
    event_type: str = Field(index=True)
    payload_json: str = Field(default="{}")
    correlation_id: Optional[str] = Field(default=None, index=True)
    published_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    handled: bool = Field(default=False)
    handled_by: Optional[str] = None
    handled_at: Optional[datetime] = None


class WorkflowStep(SQLModel, table=True):
    """Formal per-step row for a WorkflowRun, additive alongside the existing
    WorkflowRun.log_json blob (which the current RunDetail.tsx already renders
    and must keep working). Gives structured per-step detail (mock SAP call
    results, rule outcomes) for the AI decision trace / step drill-down UI."""

    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="workflowrun.id", index=True)
    index: int
    name: str
    status: str = Field(default="done")  # "done" | "exception" | "running"
    detail_json: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None


class ExceptionAction(SQLModel, table=True):
    """Human-in-the-loop actions taken against an ExceptionItem (Approve/Reject/
    Retry/Escalate/Request correction), in addition to the existing single
    resolve/resolution_note fields on ExceptionItem."""

    id: Optional[int] = Field(default=None, primary_key=True)
    exception_id: int = Field(foreign_key="exceptionitem.id", index=True)
    actor_id: int = Field(foreign_key="user.id")
    action: str  # "approve" | "reject" | "retry" | "escalate" | "request_correction"
    note: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
