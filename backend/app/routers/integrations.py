"""Integration Monitor — per-mock-system health, request counts, latency,
and last success/error, aggregated from IntegrationLog (written by
SAPIntegrationService/NonSAPIntegrationService on every call) plus a live
health-check ping to each mock service."""

from collections import defaultdict
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.config import settings
from app.database import get_session
from app.deps import require_min_level
from app.models import Level, User
from app.models_platform import IntegrationLog

router = APIRouter(prefix="/api/integrations", tags=["integrations"])

_min_level_dep = require_min_level(Level.SENIOR_MANAGER)


def _check_health(base_url: str) -> dict[str, Any]:
    try:
        resp = httpx.get(f"{base_url}/api/health", timeout=2.0)
        if resp.status_code == 200:
            return {"status": "HEALTHY", "detail": resp.json()}
        return {"status": "DEGRADED", "detail": f"HTTP {resp.status_code}"}
    except httpx.HTTPError as exc:
        return {"status": "DOWN", "detail": str(exc)}


@router.get("/status")
def integration_status(session: Session = Depends(get_session), user: User = Depends(_min_level_dep)):
    services = {
        "Mock SAP": {**_check_health(settings.mock_sap_base_url), "base_url": settings.mock_sap_base_url},
        "Mock Non-SAP": {**_check_health(settings.mock_non_sap_base_url), "base_url": settings.mock_non_sap_base_url},
    }

    logs = session.exec(select(IntegrationLog).order_by(IntegrationLog.created_at)).all()
    grouped: dict[tuple[str, str], list[IntegrationLog]] = defaultdict(list)
    for log in logs:
        grouped[(log.provider, log.system)].append(log)

    integrations = []
    for (provider, system), entries in sorted(grouped.items(), key=lambda kv: kv[0]):
        successes = [e for e in entries if e.success]
        failures = [e for e in entries if not e.success]
        last_success = max(successes, key=lambda e: e.created_at, default=None)
        last_error = max(failures, key=lambda e: e.created_at, default=None)
        integrations.append(
            {
                "provider": provider,
                "system": system,
                "requests": len(entries),
                "successes": len(successes),
                "failures": len(failures),
                "success_rate_pct": round(len(successes) / len(entries) * 100, 1) if entries else 0.0,
                "avg_latency_ms": round(sum(e.latency_ms for e in entries) / len(entries), 1) if entries else 0.0,
                "last_success_at": last_success.created_at if last_success else None,
                "last_error": last_error.error if last_error else None,
                "last_error_at": last_error.created_at if last_error else None,
            }
        )

    return {"services": services, "integrations": integrations}


@router.get("/logs")
def integration_logs(
    provider: Optional[str] = None,
    system: Optional[str] = None,
    success: Optional[bool] = None,
    limit: int = 100,
    session: Session = Depends(get_session),
    user: User = Depends(_min_level_dep),
):
    stmt = select(IntegrationLog)
    if provider is not None:
        stmt = stmt.where(IntegrationLog.provider == provider)
    if system is not None:
        stmt = stmt.where(IntegrationLog.system == system)
    if success is not None:
        stmt = stmt.where(IntegrationLog.success == success)
    rows = session.exec(stmt.order_by(IntegrationLog.created_at.desc()).limit(limit)).all()
    return [row.model_dump(mode="json") for row in rows]
