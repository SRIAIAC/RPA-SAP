"""RecipeContext: what every workflow recipe function receives. Bundles the
integration/AI/RPA services (each pre-wired with the run's correlation_id
and workflow_run_id so every call is traceable) and a record_step() helper
that keeps WorkflowRun.log_json (what the existing RunDetail.tsx renders)
and the new formal WorkflowStep table in sync on every step, exactly
mirroring the live-progress UX the original sleep-based engine had.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from sqlmodel import Session

from app.ai.service import AIService
from app.integrations.nonsap.service import NonSAPIntegrationService
from app.integrations.sap.service import SAPIntegrationService
from app.models import Workflow, WorkflowRun
from app.models_platform import WorkflowStep
from app.rpa.mock_provider import MockRPAProvider

logger = logging.getLogger("app.workflow_engine")

STEP_PACING_SECONDS = 0.5  # short, deliberate pause per step so live-progress polling stays visible


@dataclass
class RecipeOutcome:
    status: str  # "Completed" | "Exception"
    summary: str
    exception_reason: Optional[str] = None


@dataclass
class RecipeContext:
    session: Session
    run: WorkflowRun
    workflow: Workflow
    correlation_id: str
    scenario: Optional[str] = None
    # User-entered field values from the Dashboard "Enter manually" form,
    # keyed by field name (see frontend/src/manualEntryFields.ts). None (or
    # a missing key) means "use the golden-fixture default" — recipes stay
    # runnable with zero input exactly as before. Any code/number typed here
    # that doesn't exist in the mock SAP/non-SAP data correctly falls through
    # to the recipe's existing "not found" exception path.
    manual_input: Optional[dict[str, Any]] = None

    sap: SAPIntegrationService = field(init=False)
    nonsap: NonSAPIntegrationService = field(init=False)
    ai: AIService = field(init=False)
    rpa: MockRPAProvider = field(init=False)

    def __post_init__(self) -> None:
        self.sap = SAPIntegrationService(self.session, self.correlation_id, workflow_run_id=self.run.id)
        self.nonsap = NonSAPIntegrationService(self.session, self.correlation_id, workflow_run_id=self.run.id)
        self.ai = AIService(self.session, self.correlation_id, workflow_run_id=self.run.id)
        self.rpa = MockRPAProvider()
        self._log: list[dict[str, Any]] = json.loads(self.run.log_json or "[]")
        self._index: int = self.run.current_step

    def record_step(self, name: str, detail: Optional[dict[str, Any]] = None, status: str = "done") -> None:
        time.sleep(STEP_PACING_SECONDS)
        self._index += 1
        entry: dict[str, Any] = {"step": name, "index": self._index, "ts": datetime.utcnow().isoformat(), "status": status}
        if detail:
            entry["detail"] = detail
        self._log.append(entry)

        self.run.current_step = self._index
        self.run.log_json = json.dumps(self._log, default=str)
        self.session.add(self.run)
        self.session.add(
            WorkflowStep(
                run_id=self.run.id,
                index=self._index,
                name=name,
                status=status,
                detail_json=json.dumps(detail, default=str) if detail else None,
            )
        )
        self.session.commit()
