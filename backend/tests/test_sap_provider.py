"""MockSAPProvider / SAPIntegrationService.

No mock-sap service is running during the unit test suite (that live-wiring
is exercised by the Phase 6 integration test instead), so these tests cover
what's true regardless: the provider genuinely attempts a real HTTP call
(proving it isn't secretly returning hardcoded data), and the integration
service logs failures via IntegrationLog rather than swallowing them.
"""

import httpx
import pytest
from sqlmodel import Session, select

from app.integrations.sap.mock_provider import MockSAPProvider
from app.integrations.sap.service import SAPIntegrationService
from app.models_platform import IntegrationLog
from tests.conftest import TEST_ENGINE

UNREACHABLE_BASE_URL = "http://127.0.0.1:8199"  # nothing listens here in tests


def test_mock_sap_provider_attempts_real_http_call():
    provider = MockSAPProvider(base_url=UNREACHABLE_BASE_URL, timeout=1.0)
    with pytest.raises(httpx.HTTPError):
        provider.get_vendor("V-1001")


def test_sap_integration_service_logs_failure_and_reraises():
    with Session(TEST_ENGINE) as session:
        service = SAPIntegrationService(
            session,
            correlation_id="test-corr-sap-1",
            provider=MockSAPProvider(base_url=UNREACHABLE_BASE_URL, timeout=1.0),
        )
        with pytest.raises(httpx.HTTPError):
            service.get_vendor("V-1001")

        logs = session.exec(
            select(IntegrationLog).where(IntegrationLog.correlation_id == "test-corr-sap-1")
        ).all()
        assert len(logs) == 1
        assert logs[0].success is False
        assert logs[0].provider == "sap"
        assert logs[0].system == "SAP MM"
        assert logs[0].error is not None
