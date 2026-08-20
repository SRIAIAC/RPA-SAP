"""SimulatedWorkflowEngine: replaces the original inline `_simulate_run`.
Opens its own Session(engine) — module-level `engine`, imported here from
app.database — because it runs as a FastAPI BackgroundTasks callable
outside the request's DI graph, exactly like the original. This is the
critical compatibility seam: tests/conftest.py patches
`app.workflow_engine.simulated_engine.engine` (not app.database.engine)
so the background task hits the test database.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlmodel import Session

from app.audit import log_action
from app.database import engine
from app.models import ExceptionItem, RunStatus, User, Workflow, WorkflowRun
from app.workflow_engine.base import WorkflowEngine
from app.workflow_engine.recipe_context import RecipeContext, RecipeOutcome
from app.workflow_engine.recipes import RECIPES
from app.workflow_engine.recipes.generic_fallback import run as generic_fallback_run

logger = logging.getLogger("app.workflow_engine")


class SimulatedWorkflowEngine(WorkflowEngine):
    def run(self, run_id: int, scenario: Optional[str] = None, manual_input: Optional[dict[str, Any]] = None) -> None:
        with Session(engine) as session:
            run = session.get(WorkflowRun, run_id)
            if run is None:
                return
            workflow = session.get(Workflow, run.workflow_id)
            if workflow is None:
                run.status = RunStatus.EXCEPTION
                run.result_summary = "Exception raised: workflow definition not found"
                run.finished_at = datetime.utcnow()
                session.add(run)
                session.commit()
                return

            triggered_by = session.get(User, run.triggered_by_id)

            correlation_id = f"run-{run_id}-{uuid.uuid4().hex[:8]}"
            if triggered_by is not None:
                log_action(session, triggered_by, "workflow.execution_started", "WorkflowRun", run.id, {"workflow_key": workflow.key, "correlation_id": correlation_id})

            ctx = RecipeContext(
                session=session, run=run, workflow=workflow, correlation_id=correlation_id,
                scenario=scenario, manual_input=manual_input,
            )
            recipe_fn = RECIPES.get(workflow.key, generic_fallback_run)

            try:
                outcome = recipe_fn(ctx)
            except Exception as exc:  # noqa: BLE001 — a recipe bug must still finalize the run, not hang it in "Running" forever
                logger.exception(f"recipe for workflow {workflow.key} (run {run_id}) raised unexpectedly")
                outcome = RecipeOutcome(
                    status="Exception",
                    summary=f"Exception raised: unexpected error in workflow engine ({exc})",
                    exception_reason="Unclassified exception",
                )

            run.finished_at = datetime.utcnow()
            if outcome.status == "Exception":
                run.status = RunStatus.EXCEPTION
                run.result_summary = outcome.summary
                session.add(run)
                exception_item = ExceptionItem(
                    run_id=run.id,
                    workflow_id=run.workflow_id,
                    department=run.department,
                    reason=outcome.exception_reason or "Unclassified exception",
                )
                session.add(exception_item)
                session.commit()
                session.refresh(exception_item)
                if triggered_by is not None:
                    log_action(session, triggered_by, "workflow.execution_failed", "WorkflowRun", run.id, {"reason": exception_item.reason})
                    log_action(session, triggered_by, "exception.created", "ExceptionItem", exception_item.id, {"workflow_key": workflow.key, "reason": exception_item.reason})
            else:
                run.status = RunStatus.COMPLETED
                run.result_summary = outcome.summary
                session.add(run)
                session.commit()
                if triggered_by is not None:
                    log_action(session, triggered_by, "workflow.execution_completed", "WorkflowRun", run.id, {"summary": outcome.summary})


simulated_engine = SimulatedWorkflowEngine()
