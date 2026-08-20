"""InMemoryEventBus — subscribe/publish dispatch and handler-failure isolation."""

from app.events.events import equipment_alarm_event
from app.events.inmemory_bus import InMemoryEventBus


def test_publish_dispatches_to_subscribed_handler():
    bus = InMemoryEventBus()
    received = []
    bus.subscribe("equipment_alarm", received.append)

    event = equipment_alarm_event("EQ-200", "vibration", 8.2, 5.0, correlation_id="corr-x")
    bus.publish(event)

    assert len(received) == 1
    assert received[0].payload["equipment_id"] == "EQ-200"
    assert received[0].correlation_id == "corr-x"


def test_publish_with_no_subscribers_is_a_noop():
    bus = InMemoryEventBus()
    bus.publish(equipment_alarm_event("EQ-1", "temp", 1, 1))  # must not raise


def test_failing_handler_does_not_break_other_handlers_or_publisher():
    bus = InMemoryEventBus()
    calls = []

    def bad_handler(_event):
        raise RuntimeError("boom")

    def good_handler(event):
        calls.append(event.event_id)

    bus.subscribe("equipment_alarm", bad_handler)
    bus.subscribe("equipment_alarm", good_handler)

    bus.publish(equipment_alarm_event("EQ-1", "temp", 1, 1))  # must not raise
    assert len(calls) == 1


def test_multiple_event_types_are_isolated():
    bus = InMemoryEventBus()
    alarm_calls = []
    bus.subscribe("equipment_alarm", alarm_calls.append)
    bus.subscribe("invoice_exception", lambda e: (_ for _ in ()).throw(AssertionError("wrong handler fired")))

    bus.publish(equipment_alarm_event("EQ-1", "temp", 1, 1))
    assert len(alarm_calls) == 1
