"""Tests for PH5-007 — vision_radius module (Night Vision Radius Attenuation)."""
from __future__ import annotations

import pytest

from src.rules_engine.vision import (
    BASE_VISION_RADIUS,
    NIGHT_VISION_RADIUS,
    VisionState,
    build_vision_state,
    calculate_vision_radius,
)
from src.world_sim.chronos import ChronosRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _day_record() -> ChronosRecord:
    return ChronosRecord(tick=360, hour=6, is_day=True)


def _night_record() -> ChronosRecord:
    return ChronosRecord(tick=1200, hour=20, is_day=False)


# ---------------------------------------------------------------------------
# PH5-007 · Constants
# ---------------------------------------------------------------------------

class TestConstants:
    def test_base_vision_radius(self):
        assert BASE_VISION_RADIUS == 8

    def test_night_vision_radius(self):
        assert NIGHT_VISION_RADIUS == 3


# ---------------------------------------------------------------------------
# PH5-007 · VisionState
# ---------------------------------------------------------------------------

class TestVisionState:
    def test_slots_no_dict(self):
        vs = VisionState(radius=8, has_light_source=False, low_light_vision=False, darkvision_ft=0)
        assert not hasattr(vs, "__dict__")

    def test_fields(self):
        vs = VisionState(radius=5, has_light_source=True, low_light_vision=True, darkvision_ft=60)
        assert vs.radius == 5
        assert vs.has_light_source is True
        assert vs.low_light_vision is True
        assert vs.darkvision_ft == 60


# ---------------------------------------------------------------------------
# PH5-007 · calculate_vision_radius
# ---------------------------------------------------------------------------

class TestCalculateVisionRadius:
    def test_daytime_returns_base(self):
        r = calculate_vision_radius(_day_record(), {})
        assert r == BASE_VISION_RADIUS

    def test_night_no_senses_returns_night_radius(self):
        r = calculate_vision_radius(_night_record(), {})
        assert r == NIGHT_VISION_RADIUS

    def test_night_darkvision_returns_base(self):
        meta = {"darkvision_ft": 60}
        r = calculate_vision_radius(_night_record(), meta)
        assert r == BASE_VISION_RADIUS

    def test_night_light_source_returns_base(self):
        meta = {"has_light_source": True}
        r = calculate_vision_radius(_night_record(), meta)
        assert r == BASE_VISION_RADIUS

    def test_night_low_light_no_override(self):
        # low_light_vision alone does NOT override night penalty in the spec.
        meta = {"low_light_vision": True}
        r = calculate_vision_radius(_night_record(), meta)
        assert r == NIGHT_VISION_RADIUS

    def test_custom_base_radius_daytime(self):
        r = calculate_vision_radius(_day_record(), {}, base_radius=12)
        assert r == 12

    def test_custom_base_radius_night_no_senses(self):
        r = calculate_vision_radius(_night_record(), {}, base_radius=12)
        assert r == NIGHT_VISION_RADIUS  # night penalty still applies

    def test_darkvision_zero_treated_as_absent(self):
        meta = {"darkvision_ft": 0}
        r = calculate_vision_radius(_night_record(), meta)
        assert r == NIGHT_VISION_RADIUS

    def test_has_light_source_false_no_override(self):
        meta = {"has_light_source": False}
        r = calculate_vision_radius(_night_record(), meta)
        assert r == NIGHT_VISION_RADIUS


# ---------------------------------------------------------------------------
# PH5-007 · build_vision_state
# ---------------------------------------------------------------------------

class TestBuildVisionState:
    def test_daytime_state(self):
        vs = build_vision_state(_day_record(), {})
        assert vs.radius == BASE_VISION_RADIUS
        assert vs.has_light_source is False
        assert vs.darkvision_ft == 0

    def test_night_state(self):
        vs = build_vision_state(_night_record(), {})
        assert vs.radius == NIGHT_VISION_RADIUS

    def test_darkvision_carried_through(self):
        meta = {"darkvision_ft": 60}
        vs = build_vision_state(_night_record(), meta)
        assert vs.darkvision_ft == 60
        assert vs.radius == BASE_VISION_RADIUS

    def test_light_source_carried_through(self):
        meta = {"has_light_source": True}
        vs = build_vision_state(_night_record(), meta)
        assert vs.has_light_source is True
        assert vs.radius == BASE_VISION_RADIUS

    def test_low_light_vision_carried_through(self):
        meta = {"low_light_vision": True}
        vs = build_vision_state(_day_record(), meta)
        assert vs.low_light_vision is True
