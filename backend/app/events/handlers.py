"""EventBus subscriber(s) registered at app startup (see app/main.py).
Opens its own Session(engine) — same pattern as the workflow engine's
background task — since handlers fire outside the request's DI graph."""

import json
import logging

from sqlmodel import Session

from app.database import engine
from app.events.events import PlatformEvent
from app.models_platform import Event

logger = logging.getLogger("app.events")


def persist_event_handler(event: PlatformEvent) -> None:
    with Session(engine) as session:
        session.add(
            Event(
                event_type=event.event_type,
                payload_json=json.dumps(event.payload, default=str),
                correlation_id=event.correlation_id,
                published_at=event.published_at,
                handled=True,
                handled_by="persist_event_handler",
            )
        )
        session.commit()
    logger.info(f"persisted event {event.event_type} (id={event.event_id})")
