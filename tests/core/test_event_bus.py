"""
tests/core/test_event_bus.py
----------------------------
Unit tests for :class:`src.core.event_bus.EventBus`.

Covers:
- subscribe / publish / unsubscribe basics
- multiple handlers and handler invocation order
- publish return value (count of handlers invoked)
- clear (single event and all events)
- unhandled-exception isolation: a raising handler must not stop the
  dispatch loop and must not crash the caller (regression coverage for
  the "unhandled handler exceptions crash ticks" bug)
- module-level default_bus singleton
"""

import logging

import pytest

from src.core.event_bus import EventBus, default_bus


# ---------------------------------------------------------------------------
# Basic subscribe / publish
# ---------------------------------------------------------------------------

class TestEventBusBasics:
    def test_subscribe_and_publish_invokes_handler(self):
        bus = EventBus()
        seen = []

        bus.subscribe("tick", lambda p: seen.append(p))
        bus.publish("tick", 42)

        assert seen == [42]

    def test_publish_with_no_payload_passes_none(self):
        bus = EventBus()
        seen = []
        bus.subscribe("ping", lambda p: seen.append(p))

        bus.publish("ping")

        assert seen == [None]

    def test_publish_with_no_subscribers_returns_zero(self):
        bus = EventBus()
        assert bus.publish("nobody-listens", {}) == 0

    def test_publish_returns_handler_count(self):
        bus = EventBus()
        bus.subscribe("tick", lambda p: None)
        bus.subscribe("tick", lambda p: None)
        bus.subscribe("tick", lambda p: None)

        assert bus.publish("tick") == 3

    def test_multiple_handlers_all_invoked_in_order(self):
        bus = EventBus()
        order = []

        bus.subscribe("e", lambda p: order.append("a"))
        bus.subscribe("e", lambda p: order.append("b"))
        bus.subscribe("e", lambda p: order.append("c"))
        bus.publish("e", None)

        assert order == ["a", "b", "c"]

    def test_handlers_isolated_between_events(self):
        """A handler on event A must not fire when event B is published."""
        bus = EventBus()
        a_seen, b_seen = [], []
        bus.subscribe("a", lambda p: a_seen.append(p))
        bus.subscribe("b", lambda p: b_seen.append(p))

        bus.publish("a", 1)

        assert a_seen == [1]
        assert b_seen == []


# ---------------------------------------------------------------------------
# Unsubscribe
# ---------------------------------------------------------------------------

class TestEventBusUnsubscribe:
    def test_unsubscribe_removes_handler(self):
        bus = EventBus()
        seen = []

        def handler(p):
            seen.append(p)

        bus.subscribe("tick", handler)
        assert bus.unsubscribe("tick", handler) is True

        bus.publish("tick", 1)
        assert seen == []

    def test_unsubscribe_returns_false_when_not_subscribed(self):
        bus = EventBus()

        def handler(p):
            pass

        assert bus.unsubscribe("tick", handler) is False

    def test_unsubscribe_unknown_event_returns_false(self):
        bus = EventBus()
        assert bus.unsubscribe("no-such-event", lambda p: None) is False

    def test_unsubscribe_one_leaves_others(self):
        bus = EventBus()
        seen = []

        def keep(p):
            seen.append("keep")

        def drop(p):
            seen.append("drop")

        bus.subscribe("e", keep)
        bus.subscribe("e", drop)
        bus.unsubscribe("e", drop)
        bus.publish("e")

        assert seen == ["keep"]


# ---------------------------------------------------------------------------
# clear()
# ---------------------------------------------------------------------------

class TestEventBusClear:
    def test_clear_specific_event_removes_its_handlers(self):
        bus = EventBus()
        a_seen, b_seen = [], []
        bus.subscribe("a", lambda p: a_seen.append(p))
        bus.subscribe("b", lambda p: b_seen.append(p))

        bus.clear("a")

        bus.publish("a", 1)
        bus.publish("b", 2)

        assert a_seen == []
        assert b_seen == [2]

    def test_clear_all_events(self):
        bus = EventBus()
        seen = []
        bus.subscribe("a", lambda p: seen.append(p))
        bus.subscribe("b", lambda p: seen.append(p))

        bus.clear()

        bus.publish("a", 1)
        bus.publish("b", 2)

        assert seen == []

    def test_clear_unknown_event_is_noop(self):
        bus = EventBus()
        bus.clear("never-subscribed")
        # Just ensure no exception raised.


# ---------------------------------------------------------------------------
# Exception isolation (regression: unhandled handler exceptions crashed ticks)
# ---------------------------------------------------------------------------

class TestEventBusExceptionIsolation:
    def test_raising_handler_does_not_propagate(self):
        """A subscriber that raises must not propagate the exception to
        the publisher.  Previously this crashed the engine tick."""
        bus = EventBus()

        def bad_handler(payload):
            raise RuntimeError("boom")

        bus.subscribe("tick", bad_handler)

        # Must not raise
        bus.publish("tick", {"t": 1})

    def test_raising_handler_does_not_stop_subsequent_handlers(self):
        """Handlers registered after a raising handler must still be called."""
        bus = EventBus()
        seen = []

        def bad_handler(payload):
            raise ValueError("fail")

        bus.subscribe("tick", bad_handler)
        bus.subscribe("tick", lambda p: seen.append("after-bad"))

        bus.publish("tick", None)

        assert seen == ["after-bad"]

    def test_first_handler_raising_does_not_prevent_following(self):
        bus = EventBus()
        calls = []

        bus.subscribe("e", lambda p: calls.append("first"))
        bus.subscribe("e", lambda p: (_ for _ in ()).throw(RuntimeError("x")))
        bus.subscribe("e", lambda p: calls.append("third"))

        bus.publish("e")

        assert "first" in calls
        assert "third" in calls

    def test_raising_handler_logged_at_exception_level(self, caplog):
        bus = EventBus()

        def bad(_):
            raise RuntimeError("oops")

        bus.subscribe("tick", bad)

        with caplog.at_level(logging.ERROR, logger="src.core.event_bus"):
            bus.publish("tick", None)

        assert any(
            "EventBus handler" in record.message and "tick" in record.message
            for record in caplog.records
        )

    def test_publish_returns_handler_count_even_when_one_raises(self):
        bus = EventBus()

        def bad(_):
            raise RuntimeError("x")

        bus.subscribe("tick", bad)
        bus.subscribe("tick", lambda p: None)

        assert bus.publish("tick") == 2


# ---------------------------------------------------------------------------
# Snapshot semantics during dispatch
# ---------------------------------------------------------------------------

class TestEventBusDispatchSnapshot:
    def test_handler_that_subscribes_during_publish_is_not_invoked_this_round(self):
        """publish() iterates a snapshot, so a new subscriber registered
        *during* dispatch does not fire for the current publish call."""
        bus = EventBus()
        seen = []

        def late_subscriber(payload):
            seen.append("late")

        def initial(payload):
            bus.subscribe("tick", late_subscriber)
            seen.append("initial")

        bus.subscribe("tick", initial)
        bus.publish("tick")

        assert seen == ["initial"]

        # Subsequent publish does invoke the late subscriber.
        bus.publish("tick")
        assert seen.count("late") == 1


# ---------------------------------------------------------------------------
# Module-level default_bus
# ---------------------------------------------------------------------------

class TestDefaultBus:
    def test_default_bus_is_eventbus_instance(self):
        assert isinstance(default_bus, EventBus)

    def test_default_bus_works(self):
        seen = []
        handler = lambda p: seen.append(p)  # noqa: E731

        default_bus.subscribe("unit-test-event", handler)
        try:
            default_bus.publish("unit-test-event", 99)
            assert seen == [99]
        finally:
            default_bus.unsubscribe("unit-test-event", handler)
