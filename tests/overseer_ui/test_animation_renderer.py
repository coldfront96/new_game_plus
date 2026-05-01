"""Tests for PH5-010 · PH5-011 · PH5-012 · PH5-013 — AnimationRenderer module."""
from __future__ import annotations

import asyncio
import pytest

from src.overseer_ui.animation_renderer import AnimationRenderer, VFXEvent


# ---------------------------------------------------------------------------
# PH5-010 · VFXEvent
# ---------------------------------------------------------------------------

class TestVFXEvent:
    def test_slots_no_dict(self):
        e = VFXEvent(
            event_type="test",
            origin=(0, 0),
            target=None,
            duration_ms=100,
            payload={},
        )
        assert not hasattr(e, "__dict__")

    def test_fields(self):
        e = VFXEvent(
            event_type="lightning_bolt",
            origin=(5, 10),
            target=(10, 20),
            duration_ms=400,
            payload={"key": "val"},
        )
        assert e.event_type == "lightning_bolt"
        assert e.origin == (5, 10)
        assert e.target == (10, 20)
        assert e.duration_ms == 400
        assert e.payload == {"key": "val"}

    def test_target_can_be_none(self):
        e = VFXEvent("damage_flash", (1, 2), None, 200, {"hp_delta": -5})
        assert e.target is None


# ---------------------------------------------------------------------------
# Stub widget for testing
# ---------------------------------------------------------------------------

class _StubWidget:
    """Minimal stub of a Textual Static widget."""

    def __init__(self):
        self.last_update = None
        self.refresh_called = False

    def update(self, content):
        self.last_update = content

    def refresh(self):
        self.refresh_called = True


# ---------------------------------------------------------------------------
# PH5-010 · AnimationRenderer — queue management
# ---------------------------------------------------------------------------

class TestAnimationRendererQueue:
    def _renderer(self) -> AnimationRenderer:
        return AnimationRenderer(_StubWidget())

    def test_enqueue_single_event(self):
        r = self._renderer()
        e = VFXEvent("damage_flash", (0, 0), None, 200, {})
        r.enqueue(e)
        assert r._queue.qsize() == 1

    def test_enqueue_drops_oldest_when_full(self):
        r = self._renderer()
        # Fill the queue to maxsize.
        for i in range(128):
            r.enqueue(VFXEvent("test", (i, 0), None, 10, {}))
        assert r._queue.qsize() == 128
        # Adding one more should drop the oldest and add the new one.
        new_evt = VFXEvent("rain_particle", (99, 99), None, 10, {})
        r.enqueue(new_evt)
        # Queue size remains at 128.
        assert r._queue.qsize() == 128

    def test_running_initially_false(self):
        r = self._renderer()
        assert r.running is False

    @pytest.mark.asyncio
    async def test_stop_drains_queue(self):
        r = self._renderer()
        for _ in range(5):
            r.enqueue(VFXEvent("test", (0, 0), None, 10, {}))
        await r.stop()
        assert r._queue.empty()
        assert r.running is False


# ---------------------------------------------------------------------------
# PH5-011 · enqueue_lightning_bolt helper
# ---------------------------------------------------------------------------

class TestEnqueueLightningBolt:
    def test_creates_lightning_bolt_event(self):
        r = AnimationRenderer(_StubWidget())
        r.enqueue_lightning_bolt((0, 0), (5, 10), duration_ms=300)
        assert r._queue.qsize() == 1
        evt = r._queue.get_nowait()
        assert evt.event_type == "lightning_bolt"
        assert evt.origin == (0, 0)
        assert evt.target == (5, 10)
        assert evt.duration_ms == 300

    def test_default_duration(self):
        r = AnimationRenderer(_StubWidget())
        r.enqueue_lightning_bolt((0, 0), (1, 1))
        evt = r._queue.get_nowait()
        assert evt.duration_ms == 400


# ---------------------------------------------------------------------------
# PH5-012 · enqueue_damage_flash helper
# ---------------------------------------------------------------------------

class TestEnqueueDamageFlash:
    def test_creates_damage_flash_event(self):
        r = AnimationRenderer(_StubWidget())
        r.enqueue_damage_flash((3, 4), hp_delta=-7, duration_ms=150)
        evt = r._queue.get_nowait()
        assert evt.event_type == "damage_flash"
        assert evt.origin == (3, 4)
        assert evt.payload["hp_delta"] == -7
        assert evt.duration_ms == 150

    def test_default_duration(self):
        r = AnimationRenderer(_StubWidget())
        r.enqueue_damage_flash((0, 0), hp_delta=-3)
        evt = r._queue.get_nowait()
        assert evt.duration_ms == 200


# ---------------------------------------------------------------------------
# PH5-013 · enqueue_rain_update helper
# ---------------------------------------------------------------------------

class TestEnqueueRainUpdate:
    def test_creates_rain_particle_event(self):
        r = AnimationRenderer(_StubWidget())
        particles = [(0, 5), (10, 20)]
        next_p = [(1, 5), (11, 20)]
        r.enqueue_rain_update(particles, next_p)
        evt = r._queue.get_nowait()
        assert evt.event_type == "rain_particle"
        assert evt.payload["particles"] == particles
        assert evt.payload["next_particles"] == next_p

    def test_origin_is_zero(self):
        r = AnimationRenderer(_StubWidget())
        r.enqueue_rain_update([], [])
        evt = r._queue.get_nowait()
        assert evt.origin == (0, 0)


# ---------------------------------------------------------------------------
# Async render coroutine smoke tests
# ---------------------------------------------------------------------------

class TestRenderCoroutines:
    """Smoke-test the async render methods without a real Textual app."""

    @pytest.mark.asyncio
    async def test_render_damage_flash_updates_widget(self):
        widget = _StubWidget()
        r = AnimationRenderer(widget)
        evt = VFXEvent("damage_flash", (0, 0), None, 10, {"hp_delta": -5})
        await r._render_damage_flash(evt)
        # After the flash, refresh should have been called.
        assert widget.refresh_called

    @pytest.mark.asyncio
    async def test_render_rain_particles_updates_grid(self):
        widget = _StubWidget()
        r = AnimationRenderer(widget)
        evt = VFXEvent(
            "rain_particle",
            (0, 0),
            None,
            100,
            {"particles": [(0, 5), (1, 10)], "next_particles": [(1, 5), (2, 10)]},
        )
        await r._render_rain_particles(evt)
        # Widget should have been updated with grid text.
        assert widget.last_update is not None

    @pytest.mark.asyncio
    async def test_render_lightning_bolt_calls_refresh(self):
        widget = _StubWidget()
        r = AnimationRenderer(widget)
        evt = VFXEvent("lightning_bolt", (0, 0), (2, 4), 50, {})
        await r._render_lightning_bolt(evt)
        assert widget.refresh_called
