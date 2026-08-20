"""System Health — a lightweight, role-agnostic view (any authenticated
user, unlike Integration Monitor's Senior-Manager+ gate) combining backend/
DB status with mock-service reachability. Deliberately separate from
GET /api/health (unauthenticated, used for container healthchecks) so a
transient mock-service blip never affects orchestrator health probes.
"""

import httpx
from fastapi import APIRouter, Depends
from sqlmodel import Session, text

from app.config import settings
from app.database import engine, get_session
from app.deps import get_current_user
from app.models import User

router = APIRouter(prefix="/api/system", tags=["system"])


def _ping(base_url: str) -> str:
    try:
        resp = httpx.get(f"{base_url}/api/health", timeout=2.0)
        return "HEALTHY" if resp.status_code == 200 else "DEGRADED"
    except httpx.HTTPError:
        return "DOWN"


@router.get("/health")
def system_health(session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    db_status = "ok"
    try:
        session.exec(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        db_status = f"error: {exc}"

    return {
        "app_mode": settings.app_mode,
        "backend": {"status": "HEALTHY" if db_status == "ok" else "DEGRADED", "db": db_status},
        "mock_sap": {"status": _ping(settings.mock_sap_base_url), "base_url": settings.mock_sap_base_url},
        "mock_non_sap": {"status": _ping(settings.mock_non_sap_base_url), "base_url": settings.mock_non_sap_base_url},
        "providers": {
            "sap": settings.sap_provider,
            "ai": settings.ai_provider,
            "rpa": settings.rpa_provider,
            "event_bus": settings.event_bus,
        },
    }
