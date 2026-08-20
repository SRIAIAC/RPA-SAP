"""EventBus: the abstract pub/sub contract. Handlers are registered once at
app startup (see app/main.py) and events published anywhere in the app
reach them synchronously. Future real implementation (not built now):
KafkaEventBus, backed by a real broker, implementing this same interface —
publishers and subscribers would not need to change.
"""

from abc import ABC, abstractmethod
from typing import Callable

from app.events.events import PlatformEvent

Handler = Callable[[PlatformEvent], None]


class EventBus(ABC):
    @abstractmethod
    def publish(self, event: PlatformEvent) -> None: ...

    @abstractmethod
    def subscribe(self, event_type: str, handler: Handler) -> None: ...
