"""Runtime event payloads published through the EventBus. Kept as plain
dataclasses (not SQLModel) — the persisted audit trail of published events
lives in app.models_platform.Event, written by whoever publishes (see
app/workflow_engine/recipes/maintenance.py for the EquipmentAlarmEvent
golden-scenario usage), not by the bus itself.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4


@dataclass
class PlatformEvent:
    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None
    published_at: datetime = field(default_factory=datetime.utcnow)
    event_id: str = field(default_factory=lambda: uuid4().hex[:12])


def equipment_alarm_event(
    equipment_id: str,
    parameter: str,
    value: float,
    threshold: float,
    correlation_id: Optional[str] = None,
) -> PlatformEvent:
    return PlatformEvent(
        event_type="equipment_alarm",
        payload={
            "equipment_id": equipment_id,
            "parameter": parameter,
            "value": value,
            "threshold": threshold,
        },
        correlation_id=correlation_id,
    )


def invoice_exception_event(
    invoice_number: str, reason: str, correlation_id: Optional[str] = None
) -> PlatformEvent:
    return PlatformEvent(
        event_type="invoice_exception",
        payload={"invoice_number": invoice_number, "reason": reason},
        correlation_id=correlation_id,
    )


def contract_expiring_event(
    contract_id: str, expiry_date: str, days_remaining: int, correlation_id: Optional[str] = None
) -> PlatformEvent:
    return PlatformEvent(
        event_type="contract_expiring",
        payload={"contract_id": contract_id, "expiry_date": expiry_date, "days_remaining": days_remaining},
        correlation_id=correlation_id,
    )
