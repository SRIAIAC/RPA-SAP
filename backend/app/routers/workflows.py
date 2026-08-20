import json
from datetime import datetime, time

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.access import can_run_workflow, can_view_department_data, visible_departments
from app.database import get_session
from app.deps import get_current_user
from app.models import ExceptionItem, ExceptionStatus, RunStatus, User, Workflow, WorkflowRun
from app.schemas import DashboardStats, WorkflowOut

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


@router.get("", response_model=list[WorkflowOut])
def list_workflows(session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    depts = visible_departments(user)
    workflows = session.exec(
        select(Workflow).where(Workflow.department.in_(depts), Workflow.active == True)  # noqa: E712
    ).all()
    out = []
    for wf in workflows:
        out.append(
            WorkflowOut(
                id=wf.id,
                key=wf.key,
                name=wf.name,
                department=wf.department,
                description=wf.description,
                sap_systems=wf.sap_systems,
                non_sap_systems=wf.non_sap_systems,
                steps=json.loads(wf.steps_json),
                can_run=can_run_workflow(session, user, wf),
            )
        )
    return out


@router.get("/dashboard", response_model=list[DashboardStats])
def dashboard(session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    depts = visible_departments(user)
    today_start = datetime.combine(datetime.utcnow().date(), time.min)
    stats = []
    for dept in depts:
        workflows = session.exec(select(Workflow).where(Workflow.department == dept, Workflow.active == True)).all()  # noqa: E712
        available = [wf for wf in workflows if can_run_workflow(session, user, wf)]

        if can_view_department_data(user, dept):
            runs_q = select(WorkflowRun).where(WorkflowRun.department == dept, WorkflowRun.started_at >= today_start)
            exceptions_q = select(ExceptionItem).where(
                ExceptionItem.department == dept, ExceptionItem.status == ExceptionStatus.OPEN
            )
        else:
            runs_q = select(WorkflowRun).where(
                WorkflowRun.department == dept,
                WorkflowRun.triggered_by_id == user.id,
                WorkflowRun.started_at >= today_start,
            )
            exceptions_q = (
                select(ExceptionItem)
                .join(WorkflowRun, WorkflowRun.id == ExceptionItem.run_id)
                .where(
                    ExceptionItem.department == dept,
                    ExceptionItem.status == ExceptionStatus.OPEN,
                    WorkflowRun.triggered_by_id == user.id,
                )
            )
        runs_today = session.exec(runs_q).all()
        open_exceptions = session.exec(exceptions_q).all()
        stats.append(
            DashboardStats(
                department=dept,
                workflows_available=len(available),
                runs_today=len(runs_today),
                completed_today=len([r for r in runs_today if r.status.value == "Completed"]),
                open_exceptions=len(open_exceptions),
            )
        )
    return stats


@router.get("/{workflow_id}")
def get_workflow(workflow_id: int, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    workflow = session.get(Workflow, workflow_id)
    if workflow is None or workflow.department not in visible_departments(user):
        raise HTTPException(status_code=404, detail="Workflow not found")

    from app.routers.runs import _run_to_out  # local import avoids a module-load-order cycle

    recent = session.exec(
        select(WorkflowRun).where(WorkflowRun.workflow_id == workflow.id).order_by(WorkflowRun.started_at.desc()).limit(20)
    ).all()
    steps = json.loads(workflow.steps_json)
    recent_out = []
    for run in recent:
        if not can_view_department_data(user, run.department) and run.triggered_by_id != user.id:
            continue
        triggered_by = session.get(User, run.triggered_by_id)
        recent_out.append(_run_to_out(run, workflow.name, triggered_by.full_name if triggered_by else "Unknown", len(steps)))

    all_runs = session.exec(select(WorkflowRun).where(WorkflowRun.workflow_id == workflow.id)).all()
    completed = len([r for r in all_runs if r.status == RunStatus.COMPLETED])
    exceptions = len([r for r in all_runs if r.status == RunStatus.EXCEPTION])

    return {
        "id": workflow.id,
        "key": workflow.key,
        "name": workflow.name,
        "department": workflow.department,
        "description": workflow.description,
        "sap_systems": workflow.sap_systems,
        "non_sap_systems": workflow.non_sap_systems,
        "steps": steps,
        "exception_reasons": json.loads(workflow.exception_reasons_json),
        "can_run": can_run_workflow(session, user, workflow),
        "total_runs": len(all_runs),
        "completed": completed,
        "exceptions": exceptions,
        "recent_runs": recent_out,
    }
