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


# ---------------------------------------------------------------------------
# T-036: UnderwaterModifiers and apply_underwater_modifiers
# ---------------------------------------------------------------------------

from src.rules_engine.environment import (
    UnderwaterModifiers,
    WeaponType,
    apply_underwater_modifiers,
    Maneuverability,
    AerialModifiers,
    apply_aerial_modifiers,
    WeatherStateMachine,
    generate_weather,
    AirQuality,
    DungeonDressingResult,
    generate_dungeon_dressing,
    EnvironmentResult,
    apply_environment,
)
import random as _random


class TestWeaponTypeEnum:
    def test_slashing(self):
        assert WeaponType.SLASHING.value == "slashing"

    def test_bludgeoning(self):
        assert WeaponType.BLUDGEONING.value == "bludgeoning"

    def test_piercing(self):
        assert WeaponType.PIERCING.value == "piercing"

    def test_crossbow(self):
        assert WeaponType.CROSSBOW.value == "crossbow"

    def test_thrown(self):
        assert WeaponType.THROWN.value == "thrown"

    def test_natural(self):
        assert WeaponType.NATURAL.value == "natural"

    def test_all_members(self):
        assert len(WeaponType) == 6


class TestApplyUnderwaterModifiers:
    def test_slashing_attack_penalty(self):
        m = apply_underwater_modifiers(WeaponType.SLASHING)
        assert m.attack_penalty == -2

    def test_bludgeoning_attack_penalty(self):
        m = apply_underwater_modifiers(WeaponType.BLUDGEONING)
        assert m.attack_penalty == -2

    def test_piercing_no_penalty(self):
        m = apply_underwater_modifiers(WeaponType.PIERCING)
        assert m.attack_penalty == 0

    def test_natural_no_penalty(self):
        m = apply_underwater_modifiers(WeaponType.NATURAL)
        assert m.attack_penalty == 0

    def test_crossbow_penalty(self):
        m = apply_underwater_modifiers(WeaponType.CROSSBOW)
        assert m.attack_penalty == -4

    def test_crossbow_range_capped(self):
        m = apply_underwater_modifiers(WeaponType.CROSSBOW)
        assert m.ranged_range_ft == 30

    def test_thrown_range_zero(self):
        m = apply_underwater_modifiers(WeaponType.THROWN)
        assert m.ranged_range_ft == 0

    def test_fire_multiplier_zero_slashing(self):
        m = apply_underwater_modifiers(WeaponType.SLASHING)
        assert m.fire_damage_multiplier == 0.0

    def test_fire_multiplier_zero_piercing(self):
        m = apply_underwater_modifiers(WeaponType.PIERCING)
        assert m.fire_damage_multiplier == 0.0

    def test_fire_multiplier_zero_thrown(self):
        m = apply_underwater_modifiers(WeaponType.THROWN)
        assert m.fire_damage_multiplier == 0.0

    def test_electricity_both_underwater(self):
        m = apply_underwater_modifiers(WeaponType.PIERCING, both_underwater=True)
        assert m.electricity_multiplier == 1.5

    def test_electricity_not_both_underwater(self):
        m = apply_underwater_modifiers(WeaponType.PIERCING, both_underwater=False)
        assert m.electricity_multiplier == 1.0

    def test_electricity_crossbow_both(self):
        m = apply_underwater_modifiers(WeaponType.CROSSBOW, both_underwater=True)
        assert m.electricity_multiplier == 1.5

    def test_slashing_ranged_range_none(self):
        m = apply_underwater_modifiers(WeaponType.SLASHING)
        assert m.ranged_range_ft is None

    def test_natural_ranged_range_none(self):
        m = apply_underwater_modifiers(WeaponType.NATURAL)
        assert m.ranged_range_ft is None


# ---------------------------------------------------------------------------
# T-037: Maneuverability enum and apply_aerial_modifiers
# ---------------------------------------------------------------------------

class TestManeuverabilityEnum:
    def test_clumsy(self):
        assert Maneuverability.CLUMSY.value == "clumsy"

    def test_poor(self):
        assert Maneuverability.POOR.value == "poor"

    def test_average(self):
        assert Maneuverability.AVERAGE.value == "average"

    def test_good(self):
        assert Maneuverability.GOOD.value == "good"

    def test_perfect(self):
        assert Maneuverability.PERFECT.value == "perfect"

    def test_all_members(self):
        assert len(Maneuverability) == 5


class TestApplyAerialModifiers:
    def test_diving_attack_bonus(self):
        m = apply_aerial_modifiers(Maneuverability.AVERAGE, altitude_delta_ft=-20)
        assert m.attack_bonus == 1

    def test_ascending_attack_penalty(self):
        m = apply_aerial_modifiers(Maneuverability.AVERAGE, altitude_delta_ft=20)
        assert m.attack_bonus == -1

    def test_level_no_bonus(self):
        m = apply_aerial_modifiers(Maneuverability.AVERAGE, altitude_delta_ft=0)
        assert m.attack_bonus == 0

    def test_clumsy_cannot_attack_after_direction_change(self):
        m = apply_aerial_modifiers(Maneuverability.CLUMSY)
        assert m.can_attack_after_direction_change is False

    def test_poor_can_attack_after_direction_change(self):
        m = apply_aerial_modifiers(Maneuverability.POOR)
        assert m.can_attack_after_direction_change is True

    def test_perfect_can_attack_after_direction_change(self):
        m = apply_aerial_modifiers(Maneuverability.PERFECT)
        assert m.can_attack_after_direction_change is True

    def test_clumsy_cannot_charge(self):
        m = apply_aerial_modifiers(Maneuverability.CLUMSY)
        assert m.can_charge is False

    def test_poor_cannot_charge(self):
        m = apply_aerial_modifiers(Maneuverability.POOR)
        assert m.can_charge is False

    def test_average_can_charge(self):
        m = apply_aerial_modifiers(Maneuverability.AVERAGE)
        assert m.can_charge is True

    def test_good_can_charge(self):
        m = apply_aerial_modifiers(Maneuverability.GOOD)
        assert m.can_charge is True

    def test_perfect_can_charge(self):
        m = apply_aerial_modifiers(Maneuverability.PERFECT)
        assert m.can_charge is True

    def test_clumsy_min_forward_movement(self):
        m = apply_aerial_modifiers(Maneuverability.CLUMSY)
        assert m.min_forward_movement is True

    def test_poor_min_forward_movement(self):
        m = apply_aerial_modifiers(Maneuverability.POOR)
        assert m.min_forward_movement is True

    def test_average_no_min_forward(self):
        m = apply_aerial_modifiers(Maneuverability.AVERAGE)
        assert m.min_forward_movement is False

    def test_perfect_no_min_forward(self):
        m = apply_aerial_modifiers(Maneuverability.PERFECT)
        assert m.min_forward_movement is False

    def test_dive_attack_bonus_set_when_diving(self):
        m = apply_aerial_modifiers(Maneuverability.GOOD, altitude_delta_ft=-30)
        assert m.dive_attack_bonus == 1

    def test_dive_attack_bonus_zero_when_level(self):
        m = apply_aerial_modifiers(Maneuverability.GOOD, altitude_delta_ft=0)
        assert m.dive_attack_bonus == 0


# ---------------------------------------------------------------------------
# T-038: WeatherStateMachine and generate_weather
# ---------------------------------------------------------------------------

class TestWeatherStateMachine:
    def test_creation(self):
        wsm = WeatherStateMachine(
            precipitation=Precipitation.NONE,
            wind=WindStrength.CALM,
            temperature=Temperature.TEMPERATE,
        )
        assert wsm.precipitation == Precipitation.NONE
        assert wsm.wind == WindStrength.CALM
        assert wsm.temperature == Temperature.TEMPERATE

    def test_get_penalties_returns_weather_penalties(self):
        wsm = WeatherStateMachine(
            precipitation=Precipitation.LIGHT,
            wind=WindStrength.MODERATE,
            temperature=Temperature.COLD,
        )
        penalties = wsm.get_penalties()
        assert isinstance(penalties, WeatherPenalties)

    def test_advance_returns_new_state(self):
        rng = _random.Random(42)
        wsm = WeatherStateMachine(
            precipitation=Precipitation.NONE,
            wind=WindStrength.CALM,
            temperature=Temperature.TEMPERATE,
        )
        new_wsm = wsm.advance(hours=1, rng=rng)
        assert isinstance(new_wsm, WeatherStateMachine)

    def test_advance_multiple_hours(self):
        rng = _random.Random(99)
        wsm = WeatherStateMachine(
            precipitation=Precipitation.LIGHT,
            wind=WindStrength.MODERATE,
            temperature=Temperature.COLD,
        )
        new_wsm = wsm.advance(hours=6, rng=rng)
        assert isinstance(new_wsm, WeatherStateMachine)
        assert new_wsm.temperature == Temperature.COLD

    def test_advance_storm_climate(self):
        rng = _random.Random(7)
        wsm = WeatherStateMachine(
            precipitation=Precipitation.NONE,
            wind=WindStrength.CALM,
            temperature=Temperature.COLD,
        )
        new_wsm = wsm.advance(hours=3, climate=TerrainType.MOUNTAINS, rng=rng)
        assert isinstance(new_wsm, WeatherStateMachine)

    def test_advance_preserves_temperature(self):
        rng = _random.Random(0)
        wsm = WeatherStateMachine(
            precipitation=Precipitation.HEAVY,
            wind=WindStrength.STRONG,
            temperature=Temperature.EXTREME_HEAT,
        )
        new_wsm = wsm.advance(hours=1, rng=rng)
        assert new_wsm.temperature == Temperature.EXTREME_HEAT


class TestGenerateWeather:
    def test_arctic_winter(self):
        rng = _random.Random(1)
        wsm = generate_weather(TerrainType.ARCTIC, season="winter", rng=rng)
        assert wsm.temperature == Temperature.EXTREME_COLD
        assert isinstance(wsm, WeatherStateMachine)

    def test_arctic_summer(self):
        rng = _random.Random(2)
        wsm = generate_weather(TerrainType.ARCTIC, season="summer", rng=rng)
        assert wsm.temperature == Temperature.COLD

    def test_desert_summer(self):
        rng = _random.Random(3)
        wsm = generate_weather(TerrainType.DESERT, season="summer", rng=rng)
        assert wsm.temperature == Temperature.EXTREME_HEAT

    def test_desert_non_summer(self):
        rng = _random.Random(4)
        wsm = generate_weather(TerrainType.DESERT, season="spring", rng=rng)
        assert wsm.temperature == Temperature.HOT

    def test_mountains_winter(self):
        rng = _random.Random(5)
        wsm = generate_weather(TerrainType.MOUNTAINS, season="winter", rng=rng)
        assert wsm.temperature == Temperature.COLD

    def test_mountains_summer(self):
        rng = _random.Random(6)
        wsm = generate_weather(TerrainType.MOUNTAINS, season="summer", rng=rng)
        assert wsm.temperature == Temperature.TEMPERATE

    def test_marsh(self):
        rng = _random.Random(7)
        wsm = generate_weather(TerrainType.MARSH, rng=rng)
        assert wsm.temperature == Temperature.TEMPERATE

    def test_plains_winter(self):
        rng = _random.Random(8)
        wsm = generate_weather(TerrainType.PLAINS, season="winter", rng=rng)
        assert wsm.temperature == Temperature.COLD

    def test_plains_summer(self):
        rng = _random.Random(9)
        wsm = generate_weather(TerrainType.PLAINS, season="summer", rng=rng)
        assert wsm.temperature == Temperature.TEMPERATE

    def test_all_climates_produce_valid_states(self):
        rng = _random.Random(42)
        for climate in TerrainType:
            wsm = generate_weather(climate, rng=rng)
            assert isinstance(wsm, WeatherStateMachine)
            assert isinstance(wsm.precipitation, Precipitation)
            assert isinstance(wsm.wind, WindStrength)
            assert isinstance(wsm.temperature, Temperature)


# ---------------------------------------------------------------------------
# T-046: AirQuality enum and generate_dungeon_dressing
# ---------------------------------------------------------------------------

class TestAirQualityEnum:
    def test_fresh(self):
        assert AirQuality.FRESH.value == "fresh"

    def test_smoky(self):
        assert AirQuality.SMOKY.value == "smoky"

    def test_musty(self):
        assert AirQuality.MUSTY.value == "musty"

    def test_damp(self):
        assert AirQuality.DAMP.value == "damp"

    def test_fouled(self):
        assert AirQuality.FOULED.value == "fouled"

    def test_all_members(self):
        assert len(AirQuality) == 5


class TestGenerateDungeonDressing:
    def test_returns_dressing_result(self):
        rng = _random.Random(1)
        result = generate_dungeon_dressing(rng=rng)
        assert isinstance(result, DungeonDressingResult)

    def test_air_quality_is_valid_enum(self):
        rng = _random.Random(2)
        result = generate_dungeon_dressing(rng=rng)
        assert isinstance(result.air_quality, AirQuality)

    def test_smells_is_string(self):
        rng = _random.Random(3)
        result = generate_dungeon_dressing(rng=rng)
        assert isinstance(result.smells, str)
        assert len(result.smells) > 0

    def test_sounds_is_string(self):
        rng = _random.Random(4)
        result = generate_dungeon_dressing(rng=rng)
        assert isinstance(result.sounds, str)
        assert len(result.sounds) > 0

    def test_general_features_is_string(self):
        rng = _random.Random(5)
        result = generate_dungeon_dressing(rng=rng)
        assert isinstance(result.general_features, str)
        assert len(result.general_features) > 0

    def test_all_air_quality_values_reachable(self):
        # Run many iterations to ensure all AirQuality values appear
        seen = set()
        for seed in range(200):
            rng = _random.Random(seed)
            result = generate_dungeon_dressing(rng=rng)
            seen.add(result.air_quality)
        assert len(seen) == len(AirQuality)

    def test_no_rng_arg_still_works(self):
        result = generate_dungeon_dressing()
        assert isinstance(result, DungeonDressingResult)


# ---------------------------------------------------------------------------
# T-053: EnvironmentResult and apply_environment
# ---------------------------------------------------------------------------

class TestEnvironmentResult:
    def test_direct_construction(self):
        er = EnvironmentResult(
            movement_multiplier=1.5,
            ranged_attack_penalty=-2,
            visibility_ft=1000,
            passive_perception_penalty=4,
            fort_dc_cold=15,
            fort_dc_heat=None,
        )
        assert er.movement_multiplier == 1.5
        assert er.ranged_attack_penalty == -2
        assert er.visibility_ft == 1000
        assert er.passive_perception_penalty == 4
        assert er.fort_dc_cold == 15
        assert er.fort_dc_heat is None


class TestApplyEnvironment:
    def test_plains_no_weather_movement(self):
        wsm = WeatherStateMachine(Precipitation.NONE, WindStrength.CALM, Temperature.TEMPERATE)
        result = apply_environment(wsm, TerrainType.PLAINS)
        assert result.movement_multiplier == 1.0

    def test_mountains_no_weather_movement(self):
        wsm = WeatherStateMachine(Precipitation.NONE, WindStrength.CALM, Temperature.TEMPERATE)
        result = apply_environment(wsm, TerrainType.MOUNTAINS)
        assert result.movement_multiplier == 2.0

    def test_torrential_rain_halves_movement(self):
        wsm = WeatherStateMachine(Precipitation.TORRENTIAL, WindStrength.CALM, Temperature.TEMPERATE)
        result = apply_environment(wsm, TerrainType.PLAINS)
        assert result.movement_multiplier == 0.5

    def test_mountains_torrential_movement_combined(self):
        wsm = WeatherStateMachine(Precipitation.TORRENTIAL, WindStrength.CALM, Temperature.TEMPERATE)
        result = apply_environment(wsm, TerrainType.MOUNTAINS)
        assert result.movement_multiplier == pytest.approx(1.0)  # 2.0 * 0.5

    def test_ranged_penalty_forwarded(self):
        wsm = WeatherStateMachine(Precipitation.HEAVY, WindStrength.SEVERE, Temperature.TEMPERATE)
        result = apply_environment(wsm, TerrainType.PLAINS)
        assert result.ranged_attack_penalty == -8  # -4 + -4

    def test_visibility_forwarded(self):
        wsm = WeatherStateMachine(Precipitation.LIGHT, WindStrength.CALM, Temperature.TEMPERATE)
        result = apply_environment(wsm, TerrainType.PLAINS)
        assert result.visibility_ft == 1000

    def test_terrain_listen_penalty_added(self):
        # Forest adds 4 to listen penalty
        wsm = WeatherStateMachine(Precipitation.NONE, WindStrength.CALM, Temperature.TEMPERATE)
        plains_result = apply_environment(wsm, TerrainType.PLAINS)
        forest_result = apply_environment(wsm, TerrainType.FOREST)
        assert forest_result.passive_perception_penalty == plains_result.passive_perception_penalty + 4

    def test_fort_dc_cold_forwarded(self):
        wsm = WeatherStateMachine(Precipitation.NONE, WindStrength.CALM, Temperature.COLD)
        result = apply_environment(wsm, TerrainType.PLAINS)
        assert result.fort_dc_cold == 15

    def test_fort_dc_heat_forwarded(self):
        wsm = WeatherStateMachine(Precipitation.NONE, WindStrength.CALM, Temperature.HOT)
        result = apply_environment(wsm, TerrainType.PLAINS)
        assert result.fort_dc_heat == 15

    def test_mounted_movement(self):
        wsm = WeatherStateMachine(Precipitation.NONE, WindStrength.CALM, Temperature.TEMPERATE)
        result_unmounted = apply_environment(wsm, TerrainType.HILLS, mounted=False)
        result_mounted = apply_environment(wsm, TerrainType.HILLS, mounted=True)
        assert result_unmounted.movement_multiplier == result_mounted.movement_multiplier
