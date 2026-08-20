"""Demo Scenarios — a curated catalog of deterministic scenario variants
across every golden-scenario workflow. Triggering one goes through the
exact same WorkflowRun + SimulatedWorkflowEngine path as a normal Dashboard
"Run now" click (see app/routers/runs.py's trigger_run) — no separate demo
engine, per the platform's "workflows must actually run through the real
engine" requirement. Gated at Senior Manager+ so it can't be used to route
around a Manager's WorkflowAccess grants (Senior Manager+ already bypasses
that grant check in app.access.can_run_workflow, so this router doesn't
need its own special-cased authorization logic).
"""

import json
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlmodel import Session, select

from app.access import can_run_workflow
from app.database import get_session
from app.deps import require_min_level
from app.models import Level, RunStatus, User, Workflow, WorkflowRun
from app.routers.runs import _run_to_out
from app.schemas import RunOut
from app.workflow_engine.simulated_engine import simulated_engine

router = APIRouter(prefix="/api/demo", tags=["demo"])

_min_level_dep = require_min_level(Level.SENIOR_MANAGER)

DEMO_SCENARIOS: list[dict] = [
    {"id": "invoice_success", "category": "Invoice", "label": "Auto-approve (clean 3-way match)", "variant": "Successful", "workflow_key": "INV_MATCH", "scenario": "success"},
    {"id": "invoice_qty_mismatch", "category": "Invoice", "label": "Quantity mismatch", "variant": "Exception", "workflow_key": "INV_MATCH", "scenario": "quantity_mismatch"},
    {"id": "invoice_price_mismatch", "category": "Invoice", "label": "Price mismatch", "variant": "Exception", "workflow_key": "INV_MATCH", "scenario": "price_mismatch"},
    {"id": "invoice_duplicate", "category": "Invoice", "label": "Duplicate invoice", "variant": "Exception", "workflow_key": "INV_MATCH", "scenario": "duplicate_invoice"},
    {"id": "invoice_missing_grn", "category": "Invoice", "label": "Missing goods receipt", "variant": "Exception", "workflow_key": "INV_MATCH", "scenario": "missing_grn"},
    {"id": "maintenance_vibration", "category": "Maintenance", "label": "Pump vibration alarm (SCADA -> AI -> SAP PM)", "variant": "Critical", "workflow_key": "MAINT_WO", "scenario": None},
    {"id": "vendor_success", "category": "Vendor", "label": "Onboarding — compliant vendor", "variant": "Successful", "workflow_key": "VENDOR_ONBOARD", "scenario": "success"},
    {"id": "vendor_expired_insurance", "category": "Vendor", "label": "Expired insurance certificate", "variant": "Exception", "workflow_key": "VENDOR_ONBOARD", "scenario": "expired_insurance"},
    {"id": "crude_reconciliation", "category": "Crude", "label": "Terminal/SAP quantity mismatch", "variant": "Exception", "workflow_key": "CRUDE_RECON", "scenario": None},
    {"id": "hse_critical", "category": "HSE", "label": "Fire incident — AI critical classification", "variant": "Critical", "workflow_key": "HSE_INCIDENT", "scenario": "critical"},
    {"id": "hse_routine", "category": "HSE", "label": "Routine safety walkthrough", "variant": "Successful", "workflow_key": "HSE_INCIDENT", "scenario": "low"},
    {"id": "production_anomaly", "category": "Production", "label": "Production shortfall — critical anomaly", "variant": "Critical", "workflow_key": "PROD_REPORT", "scenario": None},
    {"id": "contract_expiry", "category": "Contract", "label": "Contract expiring within 30 days", "variant": "Exception", "workflow_key": "CONTRACT_EXPIRY", "scenario": None},
    {"id": "sales_order_success", "category": "Sales", "label": "Sales order — credit OK", "variant": "Successful", "workflow_key": "SALES_ORDER", "scenario": None},
]
_BY_ID = {s["id"]: s for s in DEMO_SCENARIOS}


@router.get("/scenarios")
def list_scenarios(user: User = Depends(_min_level_dep)):
    return DEMO_SCENARIOS


@router.post("/scenarios/{scenario_id}/run", response_model=RunOut, status_code=201)
def run_scenario(
    scenario_id: str,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    user: User = Depends(_min_level_dep),
):
    spec = _BY_ID.get(scenario_id)
    if spec is None:
        raise HTTPException(status_code=404, detail="Unknown demo scenario")

    workflow = session.exec(select(Workflow).where(Workflow.key == spec["workflow_key"])).first()
    if workflow is None or not workflow.active:
        raise HTTPException(status_code=404, detail=f"Workflow '{spec['workflow_key']}' not found")
    if not can_run_workflow(session, user, workflow):
        raise HTTPException(status_code=403, detail="Not authorized to run this workflow's department")

    run = WorkflowRun(
        workflow_id=workflow.id, triggered_by_id=user.id, department=workflow.department,
        status=RunStatus.RUNNING, log_json="[]",
    )
    session.add(run)
    session.commit()
    session.refresh(run)

    scenario: Optional[str] = spec.get("scenario")
    background_tasks.add_task(simulated_engine.run, run.id, scenario)

    return _run_to_out(run, workflow.name, user.full_name, len(json.loads(workflow.steps_json)))
