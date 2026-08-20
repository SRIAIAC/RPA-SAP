"""AIService: the only thing workflow recipes should call for AI-assisted
steps. Wraps whichever AIProvider is configured (today: always
MockAIProvider) and persists an AIDecision row per call, capturing the
input/classification/confidence/recommendation chain used by the AI
Decision Trace UI. Setting `final_decision`/`human_decision` is the
Business Rules Engine's and the exception-resolution flow's job
respectively — AIService only ever fills in the AI half of the row.
"""

import json
from typing import Any, Optional

from sqlmodel import Session

from app.ai.base import AIProvider
from app.ai.mock_provider import MockAIProvider
from app.models_platform import AIDecision


def _summarize(value: Any, limit: int = 500) -> str:
    try:
        text = json.dumps(value, default=str)
    except TypeError:
        text = str(value)
    return text if len(text) <= limit else text[: limit - 3] + "..."


class AIService:
    def __init__(
        self,
        session: Session,
        correlation_id: str,
        workflow_run_id: Optional[int] = None,
        provider: Optional[AIProvider] = None,
    ) -> None:
        self.session = session
        self.correlation_id = correlation_id
        self.workflow_run_id = workflow_run_id
        self.provider = provider or MockAIProvider()

    def _record(self, use_case: str, input_value: Any, result: dict[str, Any]) -> AIDecision:
        decision = AIDecision(
            workflow_run_id=self.workflow_run_id,
            use_case=use_case,
            correlation_id=self.correlation_id,
            input_summary=_summarize(input_value),
            classification=str(result.get("classification")) if result.get("classification") is not None else None,
            confidence=result.get("confidence"),
            recommendation=result.get("recommendation"),
        )
        self.session.add(decision)
        self.session.commit()
        self.session.refresh(decision)
        return decision

    def extract_invoice(self, raw_text: str) -> tuple[dict[str, Any], AIDecision]:
        result = self.provider.extract_invoice(raw_text)
        return result, self._record("invoice_extraction", raw_text, result)

    def classify_document(
        self,
        subject: str,
        body: str,
        sender: str,
        attachment_filename: Optional[str] = None,
        attachment_text: Optional[str] = None,
    ) -> tuple[dict[str, Any], AIDecision]:
        result = self.provider.classify_document(subject, body, sender, attachment_filename, attachment_text)
        return result, self._record(
            "document_classification", {"subject": subject, "sender": sender}, result
        )

    def extract_vendor_docs(self, raw_text: str) -> tuple[dict[str, Any], AIDecision]:
        result = self.provider.extract_vendor_docs(raw_text)
        return result, self._record("vendor_doc_extraction", raw_text, result)

    def classify_hse_incident(self, description: str) -> tuple[dict[str, Any], AIDecision]:
        result = self.provider.classify_hse_incident(description)
        return result, self._record("hse_classification", description, result)

    def classify_maintenance_alarm(self, alarm: dict[str, Any]) -> tuple[dict[str, Any], AIDecision]:
        result = self.provider.classify_maintenance_alarm(alarm)
        return result, self._record("maintenance_alarm_classification", alarm, result)

    def explain_production_anomaly(
        self, planned: float, actual: float, context: dict[str, Any]
    ) -> tuple[dict[str, Any], AIDecision]:
        result = self.provider.explain_production_anomaly(planned, actual, context)
        return result, self._record(
            "production_anomaly_explanation", {"planned": planned, "actual": actual, **context}, result
        )

    def extract_contract_clauses(self, raw_text: str) -> tuple[dict[str, Any], AIDecision]:
        result = self.provider.extract_contract_clauses(raw_text)
        return result, self._record("contract_clause_extraction", raw_text, result)

    def explain_exception(self, context: dict[str, Any]) -> tuple[dict[str, Any], AIDecision]:
        result = self.provider.explain_exception(context)
        return result, self._record("exception_explanation", context, result)
