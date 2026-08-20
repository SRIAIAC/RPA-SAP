from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.numbering import generate_number
from app.models import Equipment, HSEIncident

router = APIRouter(prefix="/api/ehs", tags=["SAP EHS"])


@router.post("/incidents")
def create_incident(payload: dict, session: Session = Depends(get_session)):
    equipment_code = payload.pop("equipment_id", None)
    equipment_pk = None
    if equipment_code:
        equipment = session.exec(select(Equipment).where(Equipment.equipment_id == equipment_code)).first()
        # HSE KB #10: safety reporting is never blocked on missing equipment
        # data quality — record is created regardless, flagged separately.
        equipment_pk = equipment.id if equipment else None
    payload.setdefault("incident_number", generate_number("HSE"))
    incident = HSEIncident(equipment_id=equipment_pk, **payload)
    session.add(incident)
    session.commit()
    session.refresh(incident)
    out = incident.model_dump(mode="json")
    out["equipment_id"] = equipment_code
    out["equipment_found_in_asset_master"] = equipment_pk is not None
    return out
