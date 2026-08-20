"""InMemoryEventBus: synchronous, in-process pub/sub. A handler raising
never breaks the publisher or other handlers — it's logged and swallowed,
matching how a real message bus's consumer failure wouldn't take down the
producer.
"""

import logging
from collections import defaultdict

from app.events.bus import EventBus, Handler
from app.events.events import PlatformEvent

logger = logging.getLogger("app.events")


class InMemoryEventBus(EventBus):
    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Handler) -> None:
        # Idempotent: registering the same handler twice (e.g. a test
        # harness re-entering app startup via multiple TestClient(app)
        # instances in one process) must not duplicate its side effects.
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)

    def publish(self, event: PlatformEvent) -> None:
        logger.info(
            f"event published: type={event.event_type} id={event.event_id} "
            f"correlation_id={event.correlation_id}"
        )
        for handler in self._handlers.get(event.event_type, []):
            try:
                handler(event)
            except Exception:  # noqa: BLE001 — a subscriber failing must not break the publisher
                logger.exception(f"event handler failed for {event.event_type} (id={event.event_id})")


# Process-wide singleton. Subscribers register once at app startup (see
# app/main.py); anything in the app (workflow recipes, demo scenario
# triggers) can import this and call .publish(...).
event_bus = InMemoryEventBus()
