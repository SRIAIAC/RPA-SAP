import json
import random
import time
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlmodel import Session, select

from app.access import can_run_workflow, can_view_department_data, visible_departments
from app.database import engine, get_session
from app.deps import get_current_user
from app.models import ExceptionItem, RunStatus, User, Workflow, WorkflowRun
from app.schemas import RunOut

router = APIRouter(prefix="/api/runs", tags=["runs"])

STEP_DELAY_SECONDS = 1.1
EXCEPTION_PROBABILITY = 0.3


def _run_to_out(run: WorkflowRun, workflow_name: str, triggered_by_name: str, total_steps: int) -> RunOut:
    return RunOut(
        id=run.id,
        workflow_id=run.workflow_id,
        workflow_name=workflow_name,
        triggered_by_id=run.triggered_by_id,
        triggered_by_name=triggered_by_name,
        department=run.department,
        status=run.status,
        current_step=run.current_step,
        total_steps=total_steps,
        log=json.loads(run.log_json),
        started_at=run.started_at,
        finished_at=run.finished_at,
        result_summary=run.result_summary,
    )


def _simulate_run(run_id: int, steps: list[str], exception_reasons: list[str]) -> None:
    with Session(engine) as session:
        run = session.get(WorkflowRun, run_id)
        if run is None:
            return
        log = []
        for idx, step in enumerate(steps, start=1):
            time.sleep(STEP_DELAY_SECONDS)
            log.append({"step": step, "index": idx, "ts": datetime.utcnow().isoformat(), "status": "done"})
            run.current_step = idx
            run.log_json = json.dumps(log)
            session.add(run)
            session.commit()

        will_except = random.random() < EXCEPTION_PROBABILITY
        run.finished_at = datetime.utcnow()
        if will_except:
            reason = random.choice(exception_reasons) if exception_reasons else "Unclassified exception"
            run.status = RunStatus.EXCEPTION
            run.result_summary = f"Exception raised: {reason}"
            session.add(run)
            session.add(
                ExceptionItem(
                    run_id=run.id,
                    workflow_id=run.workflow_id,
                    department=run.department,
                    reason=reason,
                )
            )
        else:
            run.status = RunStatus.COMPLETED
            run.result_summary = f"Completed successfully — {len(steps)} steps processed, no exceptions."
            session.add(run)
        session.commit()


@router.post("", response_model=RunOut, status_code=status.HTTP_201_CREATED)
def trigger_run(
    workflow_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    workflow = session.get(Workflow, workflow_id)
    if workflow is None or not workflow.active:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if not can_run_workflow(session, user, workflow):
        raise HTTPException(status_code=403, detail="You do not have access to run this workflow")

    run = WorkflowRun(
        workflow_id=workflow.id,
        triggered_by_id=user.id,
        department=workflow.department,
        status=RunStatus.RUNNING,
        log_json="[]",
    )
    session.add(run)
    session.commit()
    session.refresh(run)

    steps = json.loads(workflow.steps_json)
    exceptions = json.loads(workflow.exception_reasons_json)
    background_tasks.add_task(_simulate_run, run.id, steps, exceptions)

    return _run_to_out(run, workflow.name, user.full_name, len(steps))


@router.get("", response_model=list[RunOut])
def list_runs(session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    depts = visible_departments(user)
    runs = session.exec(
        select(WorkflowRun).where(WorkflowRun.department.in_(depts)).order_by(WorkflowRun.started_at.desc()).limit(100)
    ).all()

    out = []
    for run in runs:
        if not can_view_department_data(user, run.department) and run.triggered_by_id != user.id:
            continue
        workflow = session.get(Workflow, run.workflow_id)
        triggered_by = session.get(User, run.triggered_by_id)
        out.append(
            _run_to_out(
                run,
                workflow.name if workflow else "Unknown",
                triggered_by.full_name if triggered_by else "Unknown",
                len(json.loads(workflow.steps_json)) if workflow else run.current_step,
            )
        )
    return out


@router.get("/{run_id}", response_model=RunOut)
def get_run(run_id: int, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    run = session.get(WorkflowRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.department not in visible_departments(user):
        raise HTTPException(status_code=403, detail="Not authorized to view this run")
    if not can_view_department_data(user, run.department) and run.triggered_by_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this run")
    workflow = session.get(Workflow, run.workflow_id)
    triggered_by = session.get(User, run.triggered_by_id)
    return _run_to_out(
        run,
        workflow.name if workflow else "Unknown",
        triggered_by.full_name if triggered_by else "Unknown",
        len(json.loads(workflow.steps_json)) if workflow else run.current_step,
    )
