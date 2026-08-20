"""MockAIProvider / AIService — deterministic output + AIDecision persistence."""

from sqlmodel import Session, select

from app.ai.mock_provider import MockAIProvider
from app.ai.service import AIService
from app.models_platform import AIDecision
from tests.conftest import TEST_ENGINE


def test_extract_invoice_is_deterministic():
    provider = MockAIProvider()
    text = "INVOICE\nInvoice Number: INV-58231\nPO Number: PO-100482\nTOTAL DUE: INR 98648.00"
    result_a = provider.extract_invoice(text)
    result_b = provider.extract_invoice(text)
    assert result_a == result_b
    assert result_a["invoice_number"] == "INV-58231"
    assert result_a["po_number"] == "PO-100482"
    assert result_a["confidence"] > 0


def test_classify_hse_incident_severity_tiers():
    provider = MockAIProvider()
    assert provider.classify_hse_incident("A worker suffered a fatality after a fall.")["classification"] == "Critical"
    assert provider.classify_hse_incident("Minor injury reported, first aid administered.")["classification"] == "Medium"
    assert provider.classify_hse_incident("Routine safety walkthrough completed, no issues.")["classification"] == "Low"


def test_classify_maintenance_alarm_priority_from_ratio():
    provider = MockAIProvider()
    result = provider.classify_maintenance_alarm(
        {"equipment_id": "EQ-100", "value": 12.0, "threshold": 5.0}
    )
    assert result["classification"] == "Emergency"
    assert result["confidence"] > 0.9


def test_explain_production_anomaly_variance_calc():
    provider = MockAIProvider()
    result = provider.explain_production_anomaly(1000, 850, {"unit": "bbl"})
    assert result["variance_pct"] == 15.0
    assert result["classification"] == "Critical"


def test_ai_service_persists_ai_decision():
    with Session(TEST_ENGINE) as session:
        service = AIService(session, correlation_id="test-corr-1")
        result, decision = service.classify_hse_incident("Fire reported at Refinery 2 pump station.")
        assert decision.id is not None
        assert decision.use_case == "hse_classification"
        assert decision.correlation_id == "test-corr-1"
        assert decision.classification == result["classification"]

        stored = session.exec(select(AIDecision).where(AIDecision.id == decision.id)).first()
        assert stored is not None
        assert stored.confidence == result["confidence"]
