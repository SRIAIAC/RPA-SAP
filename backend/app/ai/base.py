"""AIProvider: the abstract contract for every "AI" use case in the platform.

Hard rule (enforced by convention, not by the type system): an AIProvider
call NEVER executes a SAP transaction and NEVER makes the final decision on
an exception. Its output is always a *recommendation* that flows into the
deterministic Business Rules Engine (app/rules/) before anything is
persisted or acted on. See app/ai/service.py for where AIDecision rows are
written and how workflow_engine recipes are expected to consume this.

Future real implementation (not built now): an OpenAIProvider/
AzureOpenAIProvider backed by settings.openai_api_key /
settings.azure_openai_endpoint, implementing this exact same interface.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class AIProvider(ABC):
    @abstractmethod
    def extract_invoice(self, raw_text: str) -> dict[str, Any]: ...

    @abstractmethod
    def classify_document(
        self,
        subject: str,
        body: str,
        sender: str,
        attachment_filename: Optional[str] = None,
        attachment_text: Optional[str] = None,
    ) -> dict[str, Any]: ...

    @abstractmethod
    def extract_vendor_docs(self, raw_text: str) -> dict[str, Any]: ...

    @abstractmethod
    def classify_hse_incident(self, description: str) -> dict[str, Any]: ...

    @abstractmethod
    def classify_maintenance_alarm(self, alarm: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def explain_production_anomaly(
        self, planned: float, actual: float, context: dict[str, Any]
    ) -> dict[str, Any]: ...

    @abstractmethod
    def extract_contract_clauses(self, raw_text: str) -> dict[str, Any]: ...

    @abstractmethod
    def explain_exception(self, context: dict[str, Any]) -> dict[str, Any]: ...
