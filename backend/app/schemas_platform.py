"""Pydantic response/request schemas for the new platform routers
(exceptions detail/actions now; integrations/ai/analytics/demo in later
phases)."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class WorkflowStepOut(BaseModel):
    index: int
    name: str
    status: str
    detail: Optional[dict[str, Any]] = None
    started_at: datetime


class IntegrationCallOut(BaseModel):
    provider: str
    system: str
    endpoint: str
    method: str
    success: bool
    latency_ms: float
    request_summary: Optional[str] = None
    response_summary: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime


class AIDecisionOut(BaseModel):
    use_case: str
    classification: Optional[str] = None
    confidence: Optional[float] = None
    recommendation: Optional[str] = None
    created_at: datetime


class AuditEntryOut(BaseModel):
    action: str
    actor_name: str
    detail: Optional[str] = None
    created_at: datetime


class ExceptionActionOut(BaseModel):
    id: int
    action: str
    actor_name: str
    note: Optional[str] = None
    created_at: datetime


class ExceptionDetailOut(BaseModel):
    id: int
    run_id: int
    workflow_id: int
    workflow_name: str
    department: str
    reason: str
    status: str
    raised_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by_name: Optional[str] = None
    resolution_note: Optional[str] = None

    ai_explanation: Optional[dict[str, Any]] = None
    steps: list[WorkflowStepOut] = []
    sap_calls: list[IntegrationCallOut] = []
    nonsap_calls: list[IntegrationCallOut] = []
    ai_decisions: list[AIDecisionOut] = []
    audit_history: list[AuditEntryOut] = []
    actions: list[ExceptionActionOut] = []
    available_actions: list[str] = []


class ExceptionActionIn(BaseModel):
    action: str  # "approve" | "reject" | "retry" | "escalate" | "request_correction"
    note: Optional[str] = None
