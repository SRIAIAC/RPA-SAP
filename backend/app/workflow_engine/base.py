"""WorkflowEngine: the abstract contract for actually executing a
WorkflowRun. SimulatedWorkflowEngine (the only implementation today) walks
the workflow's real business steps against the mock SAP/non-SAP services,
AI provider, and business rules engine. A future ProductionWorkflowEngine
could implement this same interface against a real BPM/orchestration
system without changing the router that triggers runs.
"""

from abc import ABC, abstractmethod
from typing import Optional


class WorkflowEngine(ABC):
    @abstractmethod
    def run(self, run_id: int, scenario: Optional[str] = None) -> None:
        """Execute a WorkflowRun to completion (Completed or Exception).

        Takes only the run's id (plus an optional scenario override used by
        Demo Scenarios) because this typically runs as a FastAPI
        BackgroundTasks callable outside the request's DI graph — the
        engine loads the WorkflowRun/Workflow rows itself via its own
        Session, exactly like the original inline `_simulate_run` did.
        """
        ...
