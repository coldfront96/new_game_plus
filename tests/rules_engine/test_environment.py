"""
tests/rules_engine/test_environment.py
---------------------------------------
Tests for T-002, T-003, T-014, T-015 — D&D 3.5e environment mechanics.
"""

from __future__ import annotations

import pytest

from src.rules_engine.environment import (
    Precipitation,
    WindStrength,
    Temperature,
    TerrainType,
    WeatherPenalties,
    apply_weather_penalties,
    terrain_movement_cost,
    terrain_hide_bonus,
    terrain_listen_penalty,
)


# ---------------------------------------------------------------------------
# T-002: Enum membership
# ---------------------------------------------------------------------------

class TestPrecipitationEnum:
    def test_none(self):
        assert Precipitation.NONE.value == "none"

    def test_light(self):
        assert Precipitation.LIGHT.value == "light"

    def test_heavy(self):
        assert Precipitation.HEAVY.value == "heavy"

    def test_torrential(self):
        assert Precipitation.TORRENTIAL.value == "torrential"

    def test_all_members(self):
        assert len(Precipitation) == 4


class TestWindStrengthEnum:
    def test_calm(self):
        assert WindStrength.CALM.value == "calm"

    def test_light(self):
        assert WindStrength.LIGHT.value == "light"

    def test_moderate(self):
        assert WindStrength.MODERATE.value == "moderate"

    def test_strong(self):
        assert WindStrength.STRONG.value == "strong"

    def test_severe(self):
        assert WindStrength.SEVERE.value == "severe"

    def test_windstorm(self):
        assert WindStrength.WINDSTORM.value == "windstorm"

    def test_hurricane(self):
        assert WindStrength.HURRICANE.value == "hurricane"

    def test_tornado(self):
        assert WindStrength.TORNADO.value == "tornado"

    def test_all_members(self):
        assert len(WindStrength) == 8


class TestTemperatureEnum:
    def test_extreme_cold(self):
        assert Temperature.EXTREME_COLD.value == "extreme_cold"

    def test_cold(self):
        assert Temperature.COLD.value == "cold"

    def test_temperate(self):
        assert Temperature.TEMPERATE.value == "temperate"

    def test_hot(self):
        assert Temperature.HOT.value == "hot"

    def test_extreme_heat(self):
        assert Temperature.EXTREME_HEAT.value == "extreme_heat"

    def test_all_members(self):
        assert len(Temperature) == 5


# ---------------------------------------------------------------------------
# T-003: TerrainType enum membership
# ---------------------------------------------------------------------------

class TestTerrainTypeEnum:
    def test_all_members(self):
        expected = {
            "dungeon", "forest", "plains", "desert", "hills",
            "mountains", "marsh", "arctic", "aquatic", "underground", "urban",
        }
        assert {t.value for t in TerrainType} == expected

    def test_count(self):
        assert len(TerrainType) == 11


# ---------------------------------------------------------------------------
# T-014: WeatherPenalties dataclass
# ---------------------------------------------------------------------------

class TestWeatherPenaltiesDataclass:
    def test_direct_construction(self):
        wp = WeatherPenalties(
            ranged_attack_penalty=-2,
            visibility_ft=1000,
            movement_penalty_pct=1.0,
            listen_penalty=-4,
            spot_penalty=-4,
            fort_dc_cold=None,
            fort_dc_heat=None,
            fort_dc_wind=None,
        )
        assert wp.ranged_attack_penalty == -2
        assert wp.visibility_ft == 1000
        assert wp.movement_penalty_pct == 1.0
        assert wp.listen_penalty == -4
        assert wp.spot_penalty == -4
        assert wp.fort_dc_cold is None
        assert wp.fort_dc_heat is None
        assert wp.fort_dc_wind is None


# ---------------------------------------------------------------------------
# T-014: apply_weather_penalties combinations
# ---------------------------------------------------------------------------

class TestApplyWeatherPenaltiesBaseline:
    """NONE / CALM / TEMPERATE — no modifiers."""

    def setup_method(self):
        self.wp = apply_weather_penalties(
            Precipitation.NONE, WindStrength.CALM, Temperature.TEMPERATE
        )

    def test_ranged_zero(self):
        assert self.wp.ranged_attack_penalty == 0

    def test_visibility_large(self):
        assert self.wp.visibility_ft >= 999_999

    def test_movement_full(self):
        assert self.wp.movement_penalty_pct == 1.0

    def test_listen_zero(self):
        assert self.wp.listen_penalty == 0

    def test_spot_zero(self):
        assert self.wp.spot_penalty == 0

    def test_no_cold_dc(self):
        assert self.wp.fort_dc_cold is None

    def test_no_heat_dc(self):
        assert self.wp.fort_dc_heat is None

    def test_no_wind_dc(self):
        assert self.wp.fort_dc_wind is None


class TestApplyWeatherPenaltiesLight:
    """LIGHT rain / MODERATE wind / COLD."""

    def setup_method(self):
        self.wp = apply_weather_penalties(
            Precipitation.LIGHT, WindStrength.MODERATE, Temperature.COLD
        )

    def test_ranged_penalty(self):
        assert self.wp.ranged_attack_penalty == -2

    def test_visibility(self):
        assert self.wp.visibility_ft == 1000

    def test_listen(self):
        assert self.wp.listen_penalty == -4

    def test_spot(self):
        assert self.wp.spot_penalty == -4

    def test_cold_dc(self):
        assert self.wp.fort_dc_cold == 15

    def test_no_heat_dc(self):
        assert self.wp.fort_dc_heat is None

    def test_no_wind_dc(self):
        assert self.wp.fort_dc_wind is None


class TestApplyWeatherPenaltiesHeavySevere:
    """HEAVY rain / SEVERE wind / COLD."""

    def setup_method(self):
        self.wp = apply_weather_penalties(
            Precipitation.HEAVY, WindStrength.SEVERE, Temperature.COLD
        )

    def test_ranged_cumulative(self):
        # -4 (heavy) + -4 (severe) = -8
        assert self.wp.ranged_attack_penalty == -8

    def test_visibility_min_of_both(self):
        # precip=500, wind=1000 → min=500
        assert self.wp.visibility_ft == 500

    def test_movement(self):
        assert self.wp.movement_penalty_pct == 1.0

    def test_listen(self):
        assert self.wp.listen_penalty == -8

    def test_fort_dc_wind(self):
        assert self.wp.fort_dc_wind == 10

    def test_cold_dc(self):
        assert self.wp.fort_dc_cold == 15


class TestApplyWeatherPenaltiesTorrentialWindstorm:
    """TORRENTIAL / WINDSTORM / EXTREME_COLD."""

    def setup_method(self):
        self.wp = apply_weather_penalties(
            Precipitation.TORRENTIAL, WindStrength.WINDSTORM, Temperature.EXTREME_COLD
        )

    def test_ranged_impossible(self):
        # -6 + -999 → effectively impossible
        assert self.wp.ranged_attack_penalty <= -999

    def test_visibility_min(self):
        # precip=100, wind=500 → min=100
        assert self.wp.visibility_ft == 100

    def test_movement_halved(self):
        assert self.wp.movement_penalty_pct == 0.5

    def test_listen_severe(self):
        assert self.wp.listen_penalty == -12

    def test_spot_severe(self):
        assert self.wp.spot_penalty == -12

    def test_fort_dc_wind(self):
        assert self.wp.fort_dc_wind == 15

    def test_fort_dc_cold(self):
        assert self.wp.fort_dc_cold == 15


class TestApplyWeatherPenaltiesHurricane:
    """NONE / HURRICANE / HOT."""

    def setup_method(self):
        self.wp = apply_weather_penalties(
            Precipitation.NONE, WindStrength.HURRICANE, Temperature.HOT
        )

    def test_ranged_impossible(self):
        assert self.wp.ranged_attack_penalty <= -999

    def test_visibility_wind_only(self):
        assert self.wp.visibility_ft == 300

    def test_fort_dc_wind(self):
        assert self.wp.fort_dc_wind == 20

    def test_fort_dc_heat(self):
        assert self.wp.fort_dc_heat == 15

    def test_no_cold_dc(self):
        assert self.wp.fort_dc_cold is None


class TestApplyWeatherPenaltiesTornado:
    """NONE / TORNADO / EXTREME_HEAT."""

    def setup_method(self):
        self.wp = apply_weather_penalties(
            Precipitation.NONE, WindStrength.TORNADO, Temperature.EXTREME_HEAT
        )

    def test_visibility(self):
        assert self.wp.visibility_ft == 100

    def test_fort_dc_wind(self):
        assert self.wp.fort_dc_wind == 30

    def test_fort_dc_heat(self):
        assert self.wp.fort_dc_heat == 20


class TestApplyWeatherPenaltiesStrong:
    """NONE / STRONG / TEMPERATE — wind visibility kicks in."""

    def setup_method(self):
        self.wp = apply_weather_penalties(
            Precipitation.NONE, WindStrength.STRONG, Temperature.TEMPERATE
        )

    def test_ranged(self):
        assert self.wp.ranged_attack_penalty == -2

    def test_visibility(self):
        assert self.wp.visibility_ft == 2000

    def test_no_wind_dc(self):
        assert self.wp.fort_dc_wind is None


# ---------------------------------------------------------------------------
# T-015: terrain_movement_cost
# ---------------------------------------------------------------------------

class TestTerrainMovementCost:
    @pytest.mark.parametrize("terrain,mount,expected", [
        (TerrainType.DUNGEON, False, 1.0),
        (TerrainType.DUNGEON, True, 1.0),
        (TerrainType.FOREST, False, 1.0),
        (TerrainType.FOREST, True, 1.0),
        (TerrainType.PLAINS, False, 1.0),
        (TerrainType.PLAINS, True, 1.0),
        (TerrainType.DESERT, False, 1.0),
        (TerrainType.DESERT, True, 1.0),
        (TerrainType.HILLS, False, 1.5),
        (TerrainType.HILLS, True, 1.5),
        (TerrainType.MOUNTAINS, False, 2.0),
        (TerrainType.MOUNTAINS, True, 2.0),
        (TerrainType.MARSH, False, 2.0),
        (TerrainType.MARSH, True, 2.0),
        (TerrainType.ARCTIC, False, 1.5),
        (TerrainType.ARCTIC, True, 1.5),
        (TerrainType.AQUATIC, False, 1.0),
        (TerrainType.AQUATIC, True, 1.0),
        (TerrainType.UNDERGROUND, False, 1.0),
        (TerrainType.UNDERGROUND, True, 1.0),
        (TerrainType.URBAN, False, 1.0),
        (TerrainType.URBAN, True, 1.0),
    ])
    def test_cost(self, terrain, mount, expected):
        assert terrain_movement_cost(terrain, mount) == expected


# ---------------------------------------------------------------------------
# T-015: terrain_hide_bonus
# ---------------------------------------------------------------------------

class TestTerrainHideBonus:
    @pytest.mark.parametrize("terrain,expected", [
        (TerrainType.DUNGEON, 2),
        (TerrainType.FOREST, 5),
        (TerrainType.PLAINS, 0),
        (TerrainType.DESERT, 2),
        (TerrainType.HILLS, 3),
        (TerrainType.MOUNTAINS, 3),
        (TerrainType.MARSH, 4),
        (TerrainType.ARCTIC, 2),
        (TerrainType.AQUATIC, 0),
        (TerrainType.UNDERGROUND, 2),
        (TerrainType.URBAN, 2),
    ])
    def test_hide_bonus(self, terrain, expected):
        assert terrain_hide_bonus(terrain) == expected


# ---------------------------------------------------------------------------
# T-015: terrain_listen_penalty
# ---------------------------------------------------------------------------

class TestTerrainListenPenalty:
    @pytest.mark.parametrize("terrain,expected", [
        (TerrainType.DUNGEON, 0),
        (TerrainType.FOREST, 4),
        (TerrainType.PLAINS, 0),
        (TerrainType.DESERT, 0),
        (TerrainType.HILLS, 2),
        (TerrainType.MOUNTAINS, 4),
        (TerrainType.MARSH, 2),
        (TerrainType.ARCTIC, 2),
        (TerrainType.AQUATIC, 4),
        (TerrainType.UNDERGROUND, 0),
        (TerrainType.URBAN, 4),
    ])
    def test_listen_penalty(self, terrain, expected):
        assert terrain_listen_penalty(terrain) == expected
