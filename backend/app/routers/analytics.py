"""Management analytics — org-wide, per-department, and per-workflow KPIs,
computed dynamically from real WorkflowRun data (never hardcoded). Business
value (hours saved) combines each workflow's real measured automated
processing time against a documented manual-baseline assumption — the only
input that can't be derived from data, since there's no real AP clerk to
time in this demo.
"""

from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.access import visible_departments
from app.database import get_session
from app.deps import require_min_level
from app.models import Level, RunStatus, User, Workflow, WorkflowRun

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

_min_level_dep = require_min_level(Level.SENIOR_MANAGER)

# Documented assumption: typical manual processing time per workflow before
# automation, in minutes. Everything else (automated time, transaction
# volume, hours saved) is measured from real WorkflowRun data.
MANUAL_PROCESSING_MINUTES: dict[str, float] = {
    "PO_CREATE": 20, "INV_MATCH": 15, "VENDOR_ONBOARD": 45,
    "MAINT_WO": 25, "SPARE_REPLEN": 20, "SHIFT_HANDOVER": 30,
    "EXPENSE_PROC": 12, "FUEL_RECON": 20, "CONTRACT_EXPIRY": 15,
    "HSE_INCIDENT": 30, "COMPLIANCE_DOC": 25, "ENV_COMPLIANCE": 40,
    "PROD_REPORT": 25, "CRUDE_RECON": 35, "SALES_ORDER": 15,
}
DEFAULT_MANUAL_MINUTES = 20.0


def _finished(run: WorkflowRun) -> bool:
    return run.finished_at is not None and run.status in (RunStatus.COMPLETED, RunStatus.EXCEPTION)


def _workflow_kpis(workflow: Workflow, runs: list[WorkflowRun]) -> dict:
    finished_runs = [r for r in runs if _finished(r)]
    completed = [r for r in runs if r.status == RunStatus.COMPLETED]
    exceptions = [r for r in runs if r.status == RunStatus.EXCEPTION]

    if finished_runs:
        avg_seconds = sum((r.finished_at - r.started_at).total_seconds() for r in finished_runs) / len(finished_runs)
    else:
        avg_seconds = 0.0

    manual_minutes = MANUAL_PROCESSING_MINUTES.get(workflow.key, DEFAULT_MANUAL_MINUTES)
    automated_minutes = avg_seconds / 60.0
    transactions = len(finished_runs)
    hours_saved = max(0.0, (manual_minutes - automated_minutes) * transactions / 60.0)
    automation_rate = (len(completed) / len(runs) * 100) if runs else 0.0

    return {
        "workflow_id": workflow.id,
        "workflow_key": workflow.key,
        "workflow_name": workflow.name,
        "department": workflow.department.value,
        "total_runs": len(runs),
        "completed": len(completed),
        "exceptions": len(exceptions),
        "automation_rate_pct": round(automation_rate, 1),
        "avg_processing_seconds": round(avg_seconds, 1),
        "manual_processing_minutes": manual_minutes,
        "transactions": transactions,
        "estimated_hours_saved": round(hours_saved, 1),
    }


@router.get("/dashboard")
def analytics_dashboard(department: Optional[str] = None, session: Session = Depends(get_session), user: User = Depends(_min_level_dep)):
    visible = set(d.value for d in visible_departments(user))
    if department is not None:
        if department not in visible:
            visible = set()
        else:
            visible = {department}

    workflows = session.exec(select(Workflow).where(Workflow.active == True)).all()  # noqa: E712
    workflows = [w for w in workflows if w.department.value in visible]

    runs_by_workflow: dict[int, list[WorkflowRun]] = defaultdict(list)
    if workflows:
        workflow_ids = [w.id for w in workflows]
        all_runs = session.exec(select(WorkflowRun).where(WorkflowRun.workflow_id.in_(workflow_ids))).all()
        for run in all_runs:
            runs_by_workflow[run.workflow_id].append(run)

    workflow_kpis = [_workflow_kpis(w, runs_by_workflow.get(w.id, [])) for w in workflows]

    dept_kpis: dict[str, dict] = {}
    for wf_kpi in workflow_kpis:
        dept = wf_kpi["department"]
        bucket = dept_kpis.setdefault(
            dept, {"department": dept, "total_runs": 0, "completed": 0, "exceptions": 0, "estimated_hours_saved": 0.0}
        )
        bucket["total_runs"] += wf_kpi["total_runs"]
        bucket["completed"] += wf_kpi["completed"]
        bucket["exceptions"] += wf_kpi["exceptions"]
        bucket["estimated_hours_saved"] += wf_kpi["estimated_hours_saved"]

    for bucket in dept_kpis.values():
        bucket["automation_rate_pct"] = round(bucket["completed"] / bucket["total_runs"] * 100, 1) if bucket["total_runs"] else 0.0
        bucket["human_intervention_rate_pct"] = round(bucket["exceptions"] / bucket["total_runs"] * 100, 1) if bucket["total_runs"] else 0.0
        bucket["estimated_hours_saved"] = round(bucket["estimated_hours_saved"], 1)

    total_runs = sum(k["total_runs"] for k in workflow_kpis)
    total_completed = sum(k["completed"] for k in workflow_kpis)
    total_exceptions = sum(k["exceptions"] for k in workflow_kpis)
    total_hours_saved = sum(k["estimated_hours_saved"] for k in workflow_kpis)
    finished_total = total_completed + total_exceptions
    weighted_avg_seconds = (
        sum(k["avg_processing_seconds"] * (k["completed"] + k["exceptions"]) for k in workflow_kpis) / finished_total
        if finished_total else 0.0
    )

    org_kpis = {
        "total_runs": total_runs,
        "completed": total_completed,
        "exceptions": total_exceptions,
        "automation_rate_pct": round(total_completed / total_runs * 100, 1) if total_runs else 0.0,
        "human_intervention_rate_pct": round(total_exceptions / total_runs * 100, 1) if total_runs else 0.0,
        "avg_processing_seconds": round(weighted_avg_seconds, 1),
        "estimated_hours_saved": round(total_hours_saved, 1),
    }

    return {
        "org": org_kpis,
        "departments": sorted(dept_kpis.values(), key=lambda d: d["department"]),
        "workflows": sorted(workflow_kpis, key=lambda w: (w["department"], w["workflow_name"])),
    }
