from typing import Optional

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models import SCADAAlarm, SCADATelemetry

router = APIRouter(prefix="/api/scada", tags=["SCADA"])


@router.get("/equipment/{equipment_id}/telemetry")
def get_equipment_telemetry(equipment_id: str, limit: int = 200, session: Session = Depends(get_session)):
    rows = session.exec(
        select(SCADATelemetry)
        .where(SCADATelemetry.equipment_id == equipment_id)
        .order_by(SCADATelemetry.recorded_at.desc())
        .limit(limit)
    ).all()
    return [r.model_dump(mode="json") for r in rows]


@router.get("/alarms")
def list_alarms(
    equipment_id: Optional[str] = None,
    severity: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    session: Session = Depends(get_session),
):
    stmt = select(SCADAAlarm)
    if equipment_id is not None:
        stmt = stmt.where(SCADAAlarm.equipment_id == equipment_id)
    if severity is not None:
        stmt = stmt.where(SCADAAlarm.severity == severity)
    if acknowledged is not None:
        stmt = stmt.where(SCADAAlarm.acknowledged == acknowledged)
    rows = session.exec(stmt.order_by(SCADAAlarm.raised_at.desc()).limit(500)).all()
    return [r.model_dump(mode="json") for r in rows]
