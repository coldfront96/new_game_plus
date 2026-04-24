"""
src/core/event_bus.py
---------------------
Simple synchronous publish/subscribe event bus.

All engine systems may publish and subscribe to named events without
creating hard dependencies between modules.

Usage::

    from src.core.event_bus import EventBus

    bus = EventBus()

    def on_block_broken(payload):
        print(f"Block broken: {payload}")

    bus.subscribe("block_broken", on_block_broken)
    bus.publish("block_broken", {"position": (10, 64, 10), "material": "STONE"})
    # → Block broken: {'position': (10, 64, 10), 'material': 'STONE'}
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional

_logger = logging.getLogger(__name__)


class EventBus:
    """Synchronous publish/subscribe event dispatcher."""

    def __init__(self) -> None:
        self._handlers: Dict[str, List[Callable[[Any], None]]] = defaultdict(list)

    def subscribe(self, event: str, handler: Callable[[Any], None]) -> None:
        """Register *handler* to be called when *event* is published.

        Args:
            event:   String event name.
            handler: Callable that receives the event payload.
        """
        self._handlers[event].append(handler)

    def unsubscribe(self, event: str, handler: Callable[[Any], None]) -> bool:
        """Remove a previously registered *handler* for *event*.

        Returns:
            ``True`` if the handler was found and removed; ``False`` otherwise.
        """
        if handler in self._handlers[event]:
            self._handlers[event].remove(handler)
            return True
        return False

    def publish(self, event: str, payload: Any = None) -> int:
        """Dispatch *payload* to all handlers subscribed to *event*.

        A handler that raises is logged and skipped so that a single
        misbehaving subscriber cannot crash the engine tick or prevent
        other subscribers from running.

        Args:
            event:   String event name.
            payload: Arbitrary data forwarded to each handler.

        Returns:
            Number of handlers invoked (including those that raised).
        """
        handlers = list(self._handlers.get(event, []))
        for handler in handlers:
            try:
                handler(payload)
            except Exception:  # noqa: BLE001 — deliberately broad: isolate subscribers
                _logger.exception(
                    "EventBus handler %r raised while processing event %r",
                    handler, event,
                )
        return len(handlers)

    def clear(self, event: Optional[str] = None) -> None:
        """Remove all handlers for *event*, or all handlers if *event* is ``None``."""
        if event is None:
            self._handlers.clear()
        else:
            self._handlers.pop(event, None)


# Module-level default bus instance (optional convenience singleton).
default_bus: EventBus = EventBus()
