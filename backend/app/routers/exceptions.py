import json
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlmodel import Session, select

from app.access import can_view_department_data, visible_departments
from app.ai.service import AIService
from app.audit import log_action
from app.database import get_session
from app.deps import get_current_user
from app.models import AuditLog, ExceptionItem, ExceptionStatus, RunStatus, User, Workflow, WorkflowRun
from app.models_platform import AIDecision, ExceptionAction, IntegrationLog, WorkflowStep
from app.rpa.mock_provider import MockRPAProvider
from app.rules.authorization_rules import evaluate_exception_action_authorization
from app.schemas import ExceptionOut, ExceptionResolve
from app.schemas_platform import (
    AIDecisionOut,
    AuditEntryOut,
    ExceptionActionIn,
    ExceptionActionOut,
    ExceptionDetailOut,
    IntegrationCallOut,
    WorkflowStepOut,
)
from app.workflow_engine.simulated_engine import simulated_engine

router = APIRouter(prefix="/api/exceptions", tags=["exceptions"])

_TERMINAL_ACTIONS = {"approve", "reject"}
_NONTERMINAL_ACTIONS = {"retry", "escalate", "request_correction"}
_ALL_ACTIONS = _TERMINAL_ACTIONS | _NONTERMINAL_ACTIONS


def _to_out(item: ExceptionItem, session: Session) -> ExceptionOut:
    workflow = session.get(Workflow, item.workflow_id)
    resolver = session.get(User, item.resolved_by_id) if item.resolved_by_id else None
    return ExceptionOut(
        id=item.id,
        run_id=item.run_id,
        workflow_id=item.workflow_id,
        workflow_name=workflow.name if workflow else "Unknown",
        department=item.department,
        reason=item.reason,
        status=item.status,
        raised_at=item.raised_at,
        resolved_at=item.resolved_at,
        resolved_by_name=resolver.full_name if resolver else None,
        resolution_note=item.resolution_note,
    )


@router.get("", response_model=list[ExceptionOut])
def list_exceptions(session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    depts = visible_departments(user)
    items = session.exec(
        select(ExceptionItem).where(ExceptionItem.department.in_(depts)).order_by(ExceptionItem.raised_at.desc())
    ).all()

    out = []
    for item in items:
        if can_view_department_data(user, item.department):
            out.append(_to_out(item, session))
            continue
        run = session.get(WorkflowRun, item.run_id)
        if run and run.triggered_by_id == user.id:
            out.append(_to_out(item, session))
    return out


@router.post("/{exception_id}/resolve", response_model=ExceptionOut)
def resolve_exception(
    exception_id: int,
    payload: ExceptionResolve,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    item = session.get(ExceptionItem, exception_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Exception not found")
    if not can_view_department_data(user, item.department):
        raise HTTPException(status_code=403, detail="Only Senior Manager level and above can resolve exceptions")
    if item.status == ExceptionStatus.RESOLVED:
        raise HTTPException(status_code=400, detail="Exception already resolved")

    item.status = ExceptionStatus.RESOLVED
    item.resolved_at = datetime.utcnow()
    item.resolved_by_id = user.id
    item.resolution_note = payload.resolution_note
    session.add(item)
    session.commit()
    session.refresh(item)

    log_action(
        session, user, "exception.resolved", "ExceptionItem", item.id,
        {"reason": item.reason, "resolution_note": item.resolution_note, "run_id": item.run_id},
    )

    return _to_out(item, session)


def _can_access_exception(user: User, item: ExceptionItem, run: Optional[WorkflowRun]) -> bool:
    return can_view_department_data(user, item.department) or (run is not None and run.triggered_by_id == user.id)


@router.get("/{exception_id}", response_model=ExceptionDetailOut)
def get_exception_detail(
    exception_id: int, session: Session = Depends(get_session), user: User = Depends(get_current_user)
):
    item = session.get(ExceptionItem, exception_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Exception not found")
    run = session.get(WorkflowRun, item.run_id)
    if not _can_access_exception(user, item, run):
        raise HTTPException(status_code=403, detail="Not authorized to view this exception")

    workflow = session.get(Workflow, item.workflow_id)
    resolver = session.get(User, item.resolved_by_id) if item.resolved_by_id else None

    steps = session.exec(
        select(WorkflowStep).where(WorkflowStep.run_id == item.run_id).order_by(WorkflowStep.index)
    ).all()
    step_out = [
        WorkflowStepOut(
            index=s.index, name=s.name, status=s.status,
            detail=json.loads(s.detail_json) if s.detail_json else None, started_at=s.started_at,
        )
        for s in steps
    ]

    integration_logs = session.exec(
        select(IntegrationLog).where(IntegrationLog.workflow_run_id == item.run_id).order_by(IntegrationLog.created_at)
    ).all()
    sap_calls = [IntegrationCallOut(**log.model_dump()) for log in integration_logs if log.provider == "sap"]
    nonsap_calls = [IntegrationCallOut(**log.model_dump()) for log in integration_logs if log.provider == "nonsap"]

    ai_rows = session.exec(
        select(AIDecision).where(AIDecision.workflow_run_id == item.run_id).order_by(AIDecision.created_at)
    ).all()
    ai_decisions_out = [AIDecisionOut(**row.model_dump()) for row in ai_rows]

    # AI explanation: reuse an existing exception_explanation AIDecision from
    # this run's recipe if the recipe already produced one (e.g. INV_MATCH);
    # otherwise compute (and cache) one on demand so every exception type has
    # an explanation, not just the recipes that call it inline.
    ai_explanation = None
    existing_explanation = next((r for r in ai_rows if r.use_case == "exception_explanation"), None)
    if existing_explanation is not None:
        ai_explanation = {
            "classification": existing_explanation.classification,
            "confidence": existing_explanation.confidence,
            "recommendation": existing_explanation.recommendation,
        }
    else:
        ai_service = AIService(session, correlation_id=f"exc-detail-{exception_id}-{uuid.uuid4().hex[:6]}", workflow_run_id=item.run_id)
        result, _ = ai_service.explain_exception({"workflow_name": workflow.name if workflow else "Unknown", "reason": item.reason})
        ai_explanation = {"classification": result.get("classification"), "confidence": result.get("confidence"), "recommendation": result.get("recommendation")}

    audit_rows = session.exec(
        select(AuditLog)
        .where(
            ((AuditLog.target_type == "ExceptionItem") & (AuditLog.target_id == item.id))
            | ((AuditLog.target_type == "WorkflowRun") & (AuditLog.target_id == item.run_id))
        )
        .order_by(AuditLog.created_at)
    ).all()
    audit_out = []
    for entry in audit_rows:
        actor = session.get(User, entry.actor_user_id) if entry.actor_user_id else None
        audit_out.append(AuditEntryOut(action=entry.action, actor_name=actor.full_name if actor else "Unknown", detail=entry.detail, created_at=entry.created_at))

    action_rows = session.exec(
        select(ExceptionAction).where(ExceptionAction.exception_id == item.id).order_by(ExceptionAction.created_at)
    ).all()
    actions_out = []
    for row in action_rows:
        actor = session.get(User, row.actor_id)
        actions_out.append(ExceptionActionOut(id=row.id, action=row.action, actor_name=actor.full_name if actor else "Unknown", note=row.note, created_at=row.created_at))

    available_actions = [a for a in _ALL_ACTIONS if evaluate_exception_action_authorization(user.level, a).decision == "AUTHORIZED"]

    return ExceptionDetailOut(
        id=item.id, run_id=item.run_id, workflow_id=item.workflow_id,
        workflow_name=workflow.name if workflow else "Unknown", department=item.department.value,
        reason=item.reason, status=item.status.value, raised_at=item.raised_at,
        resolved_at=item.resolved_at, resolved_by_name=resolver.full_name if resolver else None,
        resolution_note=item.resolution_note, ai_explanation=ai_explanation, steps=step_out,
        sap_calls=sap_calls, nonsap_calls=nonsap_calls, ai_decisions=ai_decisions_out,
        audit_history=audit_out, actions=actions_out, available_actions=sorted(available_actions),
    )


@router.post("/{exception_id}/action", response_model=ExceptionDetailOut)
def take_exception_action(
    exception_id: int,
    payload: ExceptionActionIn,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    if payload.action not in _ALL_ACTIONS:
        raise HTTPException(status_code=400, detail=f"Unknown action '{payload.action}'")

    item = session.get(ExceptionItem, exception_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Exception not found")
    run = session.get(WorkflowRun, item.run_id)
    if not _can_access_exception(user, item, run):
        raise HTTPException(status_code=403, detail="Not authorized to act on this exception")

    auth_result = evaluate_exception_action_authorization(user.level, payload.action)
    if auth_result.decision != "AUTHORIZED":
        raise HTTPException(status_code=403, detail=auth_result.recommended_action)

    if item.status == ExceptionStatus.RESOLVED and payload.action in _TERMINAL_ACTIONS:
        raise HTTPException(status_code=400, detail="Exception already resolved")

    if payload.action == "approve":
        item.status = ExceptionStatus.RESOLVED
        item.resolved_at = datetime.utcnow()
        item.resolved_by_id = user.id
        item.resolution_note = payload.note or "Approved"
        session.add(item)
    elif payload.action == "reject":
        item.status = ExceptionStatus.RESOLVED
        item.resolved_at = datetime.utcnow()
        item.resolved_by_id = user.id
        item.resolution_note = payload.note or "Rejected"
        session.add(item)
    elif payload.action == "retry" and run is not None:
        workflow = session.get(Workflow, item.workflow_id)
        new_run = WorkflowRun(
            workflow_id=item.workflow_id, triggered_by_id=user.id, department=item.department,
            status=RunStatus.RUNNING, log_json="[]",
        )
        session.add(new_run)
        session.commit()
        session.refresh(new_run)
        background_tasks.add_task(simulated_engine.run, new_run.id, None)
    elif payload.action == "escalate":
        MockRPAProvider().send_email(
            to="department-head@petronova.example", subject=f"Exception #{item.id} escalated ({item.reason})",
            body=payload.note or "Escalated for review.",
        )
    # "request_correction" — no side effect beyond the recorded action/note below.

    action_row = ExceptionAction(exception_id=item.id, actor_id=user.id, action=payload.action, note=payload.note)
    session.add(action_row)
    session.commit()

    log_action(
        session, user, f"exception.{payload.action}", "ExceptionItem", item.id,
        {"reason": item.reason, "note": payload.note},
    )

    return get_exception_detail(exception_id, session, user)
