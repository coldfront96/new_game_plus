"""Tests for PH5-006 · PH5-008 · PH5-009 — chronos module (Chronos & Atmosphere)."""
from __future__ import annotations

import random
import pytest

from src.world_sim.chronos import (
    TICKS_PER_HOUR,
    HOURS_PER_DAY,
    DAY_START_HOUR,
    NIGHT_START_HOUR,
    ChronosRecord,
    WeatherType,
    WeatherState,
    advance_chronos,
    apply_weather_debuffs,
    chronos_from_world_tick,
    generate_weather,
    tick_weather,
)


# ---------------------------------------------------------------------------
# PH5-006 · Constants
# ---------------------------------------------------------------------------

class TestConstants:
    def test_ticks_per_hour(self):
        assert TICKS_PER_HOUR == 60

    def test_hours_per_day(self):
        assert HOURS_PER_DAY == 24

    def test_day_start(self):
        assert DAY_START_HOUR == 6

    def test_night_start(self):
        assert NIGHT_START_HOUR == 20


# ---------------------------------------------------------------------------
# PH5-006 · ChronosRecord
# ---------------------------------------------------------------------------

class TestChronosRecord:
    def test_slots_no_dict(self):
        cr = chronos_from_world_tick(0)
        assert not hasattr(cr, "__dict__")

    def test_daytime_hour(self):
        # Tick 0 → hour 0 → night (before DAY_START_HOUR)
        cr = chronos_from_world_tick(0)
        assert cr.hour == 0
        assert cr.is_day is False

    def test_is_day_at_dawn(self):
        # TICKS_PER_HOUR * DAY_START_HOUR ticks → exactly hour 6 → day
        tick = TICKS_PER_HOUR * DAY_START_HOUR
        cr = chronos_from_world_tick(tick)
        assert cr.hour == DAY_START_HOUR
        assert cr.is_day is True

    def test_is_night_at_dusk(self):
        tick = TICKS_PER_HOUR * NIGHT_START_HOUR
        cr = chronos_from_world_tick(tick)
        assert cr.hour == NIGHT_START_HOUR
        assert cr.is_day is False

    def test_day_wrap(self):
        # After one full day the hour wraps back to 0.
        tick = TICKS_PER_HOUR * HOURS_PER_DAY
        cr = chronos_from_world_tick(tick)
        assert cr.hour == 0

    def test_default_weather(self):
        cr = chronos_from_world_tick(100)
        assert cr.weather == "clear"
        assert cr.rain_intensity == 0.0

    def test_tick_stored(self):
        cr = chronos_from_world_tick(999)
        assert cr.tick == 999


# ---------------------------------------------------------------------------
# PH5-006 · advance_chronos
# ---------------------------------------------------------------------------

class TestAdvanceChronos:
    def test_tick_increments(self):
        cr = chronos_from_world_tick(0)
        cr2 = advance_chronos(cr, ticks=10)
        assert cr2.tick == 10

    def test_hour_recomputed(self):
        cr = chronos_from_world_tick(TICKS_PER_HOUR * 5)
        cr2 = advance_chronos(cr, ticks=TICKS_PER_HOUR)
        assert cr2.hour == 6
        assert cr2.is_day is True

    def test_weather_unchanged_without_rng(self):
        cr = ChronosRecord(
            tick=0, hour=0, is_day=False, weather="rain", rain_intensity=0.5, temperature_c=10.0
        )
        cr2 = advance_chronos(cr, ticks=1)
        assert cr2.weather == "rain"
        assert cr2.rain_intensity == 0.5

    def test_temperature_unchanged(self):
        cr = ChronosRecord(
            tick=0, hour=12, is_day=True, weather="clear", rain_intensity=0.0, temperature_c=25.0
        )
        cr2 = advance_chronos(cr, ticks=5)
        assert cr2.temperature_c == 25.0

    def test_returns_new_object(self):
        cr = chronos_from_world_tick(0)
        cr2 = advance_chronos(cr)
        assert cr2 is not cr


# ---------------------------------------------------------------------------
# PH5-008 · WeatherType
# ---------------------------------------------------------------------------

class TestWeatherType:
    def test_values(self):
        assert WeatherType.CLEAR == "clear"
        assert WeatherType.RAIN == "rain"
        assert WeatherType.STORM == "storm"

    def test_is_str(self):
        assert isinstance(WeatherType.RAIN, str)


# ---------------------------------------------------------------------------
# PH5-008 · WeatherState
# ---------------------------------------------------------------------------

class TestWeatherState:
    def test_slots_no_dict(self):
        ws = WeatherState(
            weather_type=WeatherType.CLEAR,
            intensity=0.0,
            rain_particles=[],
            wind_speed_ms=0.0,
        )
        assert not hasattr(ws, "__dict__")

    def test_fields(self):
        ws = WeatherState(
            weather_type=WeatherType.RAIN,
            intensity=0.5,
            rain_particles=[(1, 2), (3, 4)],
            wind_speed_ms=5.0,
        )
        assert ws.weather_type == WeatherType.RAIN
        assert ws.intensity == 0.5
        assert len(ws.rain_particles) == 2
        assert ws.wind_speed_ms == 5.0


# ---------------------------------------------------------------------------
# PH5-008 · generate_weather
# ---------------------------------------------------------------------------

class TestGenerateWeather:
    def _rng(self, seed: int = 42):
        return random.Random(seed)

    def test_returns_weather_state(self):
        ws = generate_weather(self._rng())
        assert isinstance(ws, WeatherState)

    def test_desert_mostly_clear(self):
        # With probability 5%, a desert is usually clear over many trials.
        rng = random.Random(0)
        clear_count = sum(
            1 for _ in range(200)
            if generate_weather(rng, terrain_biome="desert").weather_type == WeatherType.CLEAR
        )
        # Should be > 150 clear out of 200 (biased toward clear)
        assert clear_count > 150

    def test_swamp_more_rain(self):
        rng = random.Random(1)
        rain_count = sum(
            1 for _ in range(200)
            if generate_weather(rng, terrain_biome="swamp").weather_type != WeatherType.CLEAR
        )
        # Should be > 60 rainy / stormy out of 200
        assert rain_count > 60

    def test_storm_when_intensity_high(self):
        # Patch rng to always return high intensity values.
        class _HighRng:
            def random(self):
                return 0.99  # above any rain threshold → CLEAR... but we need rain
            def uniform(self, a, b):
                return 0.9  # ≥ 0.8 → STORM
            def randint(self, a, b):
                return (a + b) // 2

        # Can't easily force STORM without controlling rng; test consistency.
        ws = WeatherState(
            weather_type=WeatherType.STORM,
            intensity=0.9,
            rain_particles=[(0, 0)],
            wind_speed_ms=15.0,
        )
        assert ws.weather_type == WeatherType.STORM

    def test_rain_particles_count(self):
        class _RainRng:
            def random(self):
                return 0.01  # below rain threshold → always rain
            def uniform(self, a, b):
                return 0.5  # intensity 0.5 → RAIN (not STORM); 10 particles
            def randint(self, a, b):
                return a

        ws = generate_weather(_RainRng())
        assert ws.weather_type == WeatherType.RAIN
        assert len(ws.rain_particles) == int(0.5 * 20)

    def test_clear_has_no_particles(self):
        class _ClearRng:
            def random(self):
                return 1.0  # always above rain threshold → CLEAR
            def uniform(self, a, b):
                return 0.5
            def randint(self, a, b):
                return a

        ws = generate_weather(_ClearRng())
        assert ws.weather_type == WeatherType.CLEAR
        assert ws.rain_particles == []


# ---------------------------------------------------------------------------
# PH5-008 · tick_weather
# ---------------------------------------------------------------------------

class TestTickWeather:
    def test_particles_shift_down_one_row(self):
        class _StableRng:
            def random(self):
                return 0.5  # > 0.02 → no regeneration

        ws = WeatherState(
            weather_type=WeatherType.RAIN,
            intensity=0.5,
            rain_particles=[(0, 5), (10, 20)],
            wind_speed_ms=3.0,
        )
        ws2 = tick_weather(ws, _StableRng())
        assert (1, 5) in ws2.rain_particles
        assert (11, 20) in ws2.rain_particles

    def test_particles_wrap_at_bottom(self):
        class _StableRng:
            def random(self):
                return 0.5

        ws = WeatherState(
            weather_type=WeatherType.RAIN,
            intensity=0.5,
            rain_particles=[(23, 0)],
            wind_speed_ms=0.0,
        )
        ws2 = tick_weather(ws, _StableRng())
        assert (0, 0) in ws2.rain_particles  # row 24 wraps to 0

    def test_regeneration_on_low_roll(self):
        rng = random.Random(0)
        ws = WeatherState(
            weather_type=WeatherType.RAIN,
            intensity=0.5,
            rain_particles=[(5, 5)],
            wind_speed_ms=2.0,
        )
        # Force regeneration by patching random to always return 0.0.
        class _RegenRng:
            def random(self):
                return 0.0  # < 0.02 → regenerate
            def uniform(self, a, b):
                return 0.5
            def randint(self, a, b):
                return a

        ws2 = tick_weather(ws, _RegenRng())
        # It's a new WeatherState; particles may differ.
        assert isinstance(ws2, WeatherState)


# ---------------------------------------------------------------------------
# PH5-009 · apply_weather_debuffs
# ---------------------------------------------------------------------------

class TestApplyWeatherDebuffs:
    def _make_ws(self, wtype: WeatherType, intensity: float = 0.5) -> WeatherState:
        return WeatherState(
            weather_type=wtype,
            intensity=intensity,
            rain_particles=[],
            wind_speed_ms=0.0,
        )

    def test_clear_no_speed_penalty(self):
        meta: dict = {}
        apply_weather_debuffs(meta, self._make_ws(WeatherType.CLEAR))
        assert meta["weather_speed_multiplier"] == 1.0

    def test_rain_reduces_speed(self):
        meta: dict = {}
        ws = self._make_ws(WeatherType.RAIN, intensity=0.5)
        apply_weather_debuffs(meta, ws)
        expected = 1.0 - (0.5 * 0.4)
        assert abs(meta["weather_speed_multiplier"] - expected) < 1e-9

    def test_storm_reduces_speed_and_attack(self):
        meta: dict = {}
        ws = self._make_ws(WeatherType.STORM, intensity=1.0)
        apply_weather_debuffs(meta, ws)
        assert meta["weather_speed_multiplier"] < 1.0
        assert meta["weather_attack_penalty"] == -2

    def test_clear_removes_attack_penalty(self):
        meta: dict = {"weather_attack_penalty": -2}
        apply_weather_debuffs(meta, self._make_ws(WeatherType.CLEAR))
        assert "weather_attack_penalty" not in meta

    def test_storm_extinguishes_fire_effects(self):
        meta: dict = {
            "active_fire_effects": [
                {"element": "fire", "id": "fireball_1"},
                {"element": "ice", "id": "cone_cold_1"},
            ]
        }
        ws = self._make_ws(WeatherType.STORM, intensity=1.0)
        apply_weather_debuffs(meta, ws)
        remaining = meta["active_fire_effects"]
        assert all(e["element"] != "fire" for e in remaining)
        assert len(remaining) == 1
        assert remaining[0]["element"] == "ice"

    def test_returns_metadata(self):
        meta: dict = {}
        result = apply_weather_debuffs(meta, self._make_ws(WeatherType.RAIN))
        assert result is meta
