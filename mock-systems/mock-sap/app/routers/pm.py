from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.numbering import generate_number
from app.models import Equipment, MaintenanceNotification, MaintenanceOrder

router = APIRouter(prefix="/api/pm", tags=["SAP PM"])


@router.get("/equipment/{equipment_id}")
def get_equipment(equipment_id: str, session: Session = Depends(get_session)):
    equipment = session.exec(select(Equipment).where(Equipment.equipment_id == equipment_id)).first()
    if equipment is None:
        raise HTTPException(status_code=404, detail="Equipment not found")
    return equipment.model_dump(mode="json")


@router.post("/notifications")
def create_notification(payload: dict, session: Session = Depends(get_session)):
    equipment_code = payload.pop("equipment_id", None)
    equipment = session.exec(select(Equipment).where(Equipment.equipment_id == equipment_code)).first()
    if equipment is None:
        raise HTTPException(status_code=404, detail=f"Equipment '{equipment_code}' not found in Asset Master")
    payload.setdefault("notification_number", generate_number("NOTIF"))
    notification = MaintenanceNotification(equipment_id=equipment.id, **payload)
    session.add(notification)
    session.commit()
    session.refresh(notification)
    out = notification.model_dump(mode="json")
    out["equipment_id"] = equipment_code
    return out


@router.post("/work-orders")
def create_work_order(payload: dict, session: Session = Depends(get_session)):
    equipment_code = payload.pop("equipment_id", None)
    equipment = session.exec(select(Equipment).where(Equipment.equipment_id == equipment_code)).first()
    if equipment is None:
        raise HTTPException(status_code=404, detail=f"Equipment '{equipment_code}' not found in Asset Master")
    payload.setdefault("order_number", generate_number("WO"))
    order = MaintenanceOrder(equipment_id=equipment.id, **payload)
    session.add(order)
    session.commit()
    session.refresh(order)
    out = order.model_dump(mode="json")
    out["equipment_id"] = equipment_code
    return out
