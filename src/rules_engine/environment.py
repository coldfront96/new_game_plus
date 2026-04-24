"""
src/rules_engine/environment.py
--------------------------------
D&D 3.5e DMG environment mechanics.

Covers:
- T-002: Weather enums (Precipitation, WindStrength, Temperature)
- T-003: TerrainType enum
- T-014: WeatherPenalties dataclass and apply_weather_penalties
- T-015: terrain_movement_cost, terrain_hide_bonus, terrain_listen_penalty
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


# ---------------------------------------------------------------------------
# T-002: Weather enums
# ---------------------------------------------------------------------------

class Precipitation(Enum):
    NONE = "none"
    LIGHT = "light"           # Light rain/snow
    HEAVY = "heavy"           # Heavy rain/snow
    TORRENTIAL = "torrential" # Downpour/blizzard


class WindStrength(Enum):
    CALM = "calm"
    LIGHT = "light"
    MODERATE = "moderate"
    STRONG = "strong"
    SEVERE = "severe"
    WINDSTORM = "windstorm"
    HURRICANE = "hurricane"
    TORNADO = "tornado"


class Temperature(Enum):
    EXTREME_COLD = "extreme_cold"  # below -20°F
    COLD = "cold"                   # -20 to 40°F
    TEMPERATE = "temperate"         # 40-90°F
    HOT = "hot"                     # 90-110°F
    EXTREME_HEAT = "extreme_heat"   # 110°F+


# ---------------------------------------------------------------------------
# T-003: TerrainType enum
# ---------------------------------------------------------------------------

class TerrainType(Enum):
    DUNGEON = "dungeon"
    FOREST = "forest"
    PLAINS = "plains"
    DESERT = "desert"
    HILLS = "hills"
    MOUNTAINS = "mountains"
    MARSH = "marsh"
    ARCTIC = "arctic"
    AQUATIC = "aquatic"
    UNDERGROUND = "underground"
    URBAN = "urban"


# ---------------------------------------------------------------------------
# T-014: WeatherPenalties and apply_weather_penalties
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class WeatherPenalties:
    ranged_attack_penalty: int     # negative value; sum of precip + wind penalties
    visibility_ft: int             # max visibility distance in feet
    movement_penalty_pct: float    # fraction of normal movement (1.0 = no penalty)
    listen_penalty: int            # negative value applied to Listen checks
    spot_penalty: int              # negative value applied to Spot checks
    fort_dc_cold: int | None       # Fort save DC for cold damage (if applicable)
    fort_dc_heat: int | None       # Fort save DC for heat damage (if applicable)
    fort_dc_wind: int | None       # Fort save DC for wind effects (if applicable)


_PRECIP_RANGED: dict[Precipitation, int] = {
    Precipitation.NONE: 0,
    Precipitation.LIGHT: -2,
    Precipitation.HEAVY: -4,
    Precipitation.TORRENTIAL: -6,
}

_PRECIP_VISIBILITY: dict[Precipitation, int | None] = {
    Precipitation.NONE: None,
    Precipitation.LIGHT: 1000,
    Precipitation.HEAVY: 500,
    Precipitation.TORRENTIAL: 100,
}

_PRECIP_MOVE: dict[Precipitation, float] = {
    Precipitation.NONE: 1.0,
    Precipitation.LIGHT: 1.0,
    Precipitation.HEAVY: 1.0,
    Precipitation.TORRENTIAL: 0.5,
}

_PRECIP_LISTEN: dict[Precipitation, int] = {
    Precipitation.NONE: 0,
    Precipitation.LIGHT: -4,
    Precipitation.HEAVY: -8,
    Precipitation.TORRENTIAL: -12,
}

_PRECIP_SPOT: dict[Precipitation, int] = {
    Precipitation.NONE: 0,
    Precipitation.LIGHT: -4,
    Precipitation.HEAVY: -8,
    Precipitation.TORRENTIAL: -12,
}

_WIND_RANGED: dict[WindStrength, int] = {
    WindStrength.CALM: 0,
    WindStrength.LIGHT: 0,
    WindStrength.MODERATE: 0,
    WindStrength.STRONG: -2,
    WindStrength.SEVERE: -4,
    WindStrength.WINDSTORM: -999,
    WindStrength.HURRICANE: -999,
    WindStrength.TORNADO: -999,
}

_WIND_VISIBILITY: dict[WindStrength, int | None] = {
    WindStrength.CALM: None,
    WindStrength.LIGHT: None,
    WindStrength.MODERATE: None,
    WindStrength.STRONG: 2000,
    WindStrength.SEVERE: 1000,
    WindStrength.WINDSTORM: 500,
    WindStrength.HURRICANE: 300,
    WindStrength.TORNADO: 100,
}

_WIND_FORT_DC: dict[WindStrength, int | None] = {
    WindStrength.CALM: None,
    WindStrength.LIGHT: None,
    WindStrength.MODERATE: None,
    WindStrength.STRONG: None,
    WindStrength.SEVERE: 10,
    WindStrength.WINDSTORM: 15,
    WindStrength.HURRICANE: 20,
    WindStrength.TORNADO: 30,
}

_TEMP_FORT_COLD: dict[Temperature, int | None] = {
    Temperature.EXTREME_COLD: 15,
    Temperature.COLD: 15,
    Temperature.TEMPERATE: None,
    Temperature.HOT: None,
    Temperature.EXTREME_HEAT: None,
}

_TEMP_FORT_HEAT: dict[Temperature, int | None] = {
    Temperature.EXTREME_COLD: None,
    Temperature.COLD: None,
    Temperature.TEMPERATE: None,
    Temperature.HOT: 15,
    Temperature.EXTREME_HEAT: 20,
}

_NO_VISIBILITY = 999_999


def apply_weather_penalties(
    precip: Precipitation,
    wind: WindStrength,
    temp: Temperature,
) -> WeatherPenalties:
    """Compute combined DMG weather penalties for the given conditions."""
    ranged = _PRECIP_RANGED[precip] + _WIND_RANGED[wind]

    precip_vis = _PRECIP_VISIBILITY[precip]
    wind_vis = _WIND_VISIBILITY[wind]
    if precip_vis is not None and wind_vis is not None:
        visibility = min(precip_vis, wind_vis)
    elif precip_vis is not None:
        visibility = precip_vis
    elif wind_vis is not None:
        visibility = wind_vis
    else:
        visibility = _NO_VISIBILITY

    return WeatherPenalties(
        ranged_attack_penalty=ranged,
        visibility_ft=visibility,
        movement_penalty_pct=_PRECIP_MOVE[precip],
        listen_penalty=_PRECIP_LISTEN[precip],
        spot_penalty=_PRECIP_SPOT[precip],
        fort_dc_cold=_TEMP_FORT_COLD[temp],
        fort_dc_heat=_TEMP_FORT_HEAT[temp],
        fort_dc_wind=_WIND_FORT_DC[wind],
    )


# ---------------------------------------------------------------------------
# T-015: Terrain helpers
# ---------------------------------------------------------------------------

_TERRAIN_MOVE_UNMOUNTED: dict[TerrainType, float] = {
    TerrainType.DUNGEON: 1.0,
    TerrainType.FOREST: 1.0,
    TerrainType.PLAINS: 1.0,
    TerrainType.DESERT: 1.0,
    TerrainType.HILLS: 1.5,
    TerrainType.MOUNTAINS: 2.0,
    TerrainType.MARSH: 2.0,
    TerrainType.ARCTIC: 1.5,
    TerrainType.AQUATIC: 1.0,
    TerrainType.UNDERGROUND: 1.0,
    TerrainType.URBAN: 1.0,
}

_TERRAIN_MOVE_MOUNTED: dict[TerrainType, float] = {
    TerrainType.DUNGEON: 1.0,
    TerrainType.FOREST: 1.0,
    TerrainType.PLAINS: 1.0,
    TerrainType.DESERT: 1.0,
    TerrainType.HILLS: 1.5,
    TerrainType.MOUNTAINS: 2.0,
    TerrainType.MARSH: 2.0,
    TerrainType.ARCTIC: 1.5,
    TerrainType.AQUATIC: 1.0,
    TerrainType.UNDERGROUND: 1.0,
    TerrainType.URBAN: 1.0,
}

_TERRAIN_HIDE: dict[TerrainType, int] = {
    TerrainType.DUNGEON: 2,
    TerrainType.FOREST: 5,
    TerrainType.PLAINS: 0,
    TerrainType.DESERT: 2,
    TerrainType.HILLS: 3,
    TerrainType.MOUNTAINS: 3,
    TerrainType.MARSH: 4,
    TerrainType.ARCTIC: 2,
    TerrainType.AQUATIC: 0,
    TerrainType.UNDERGROUND: 2,
    TerrainType.URBAN: 2,
}

_TERRAIN_LISTEN: dict[TerrainType, int] = {
    TerrainType.DUNGEON: 0,
    TerrainType.FOREST: 4,
    TerrainType.PLAINS: 0,
    TerrainType.DESERT: 0,
    TerrainType.HILLS: 2,
    TerrainType.MOUNTAINS: 4,
    TerrainType.MARSH: 2,
    TerrainType.ARCTIC: 2,
    TerrainType.AQUATIC: 4,
    TerrainType.UNDERGROUND: 0,
    TerrainType.URBAN: 4,
}


def terrain_movement_cost(terrain: TerrainType, mount: bool = False) -> float:
    """Return movement multiplier (1.0 = normal speed)."""
    if mount:
        return _TERRAIN_MOVE_MOUNTED[terrain]
    return _TERRAIN_MOVE_UNMOUNTED[terrain]


def terrain_hide_bonus(terrain: TerrainType) -> int:
    """Return bonus to Hide checks."""
    return _TERRAIN_HIDE[terrain]


def terrain_listen_penalty(terrain: TerrainType) -> int:
    """Return penalty to Listen checks (positive = harder to hear)."""
    return _TERRAIN_LISTEN[terrain]


# ---------------------------------------------------------------------------
# T-036 Underwater Combat Modifier Engine
# ---------------------------------------------------------------------------

import random as _random


@dataclass(slots=True)
class UnderwaterModifiers:
    attack_penalty: int         # penalty to attack rolls
    ranged_range_ft: int | None # None = cannot use ranged weapons
    fire_damage_multiplier: float   # 0.0 = no effect
    electricity_multiplier: float   # 1.5 if both attacker and target underwater

class WeaponType(Enum):
    SLASHING = "slashing"
    BLUDGEONING = "bludgeoning"
    PIERCING = "piercing"
    CROSSBOW = "crossbow"
    THROWN = "thrown"
    NATURAL = "natural"


def apply_underwater_modifiers(weapon_type: WeaponType, both_underwater: bool = True) -> UnderwaterModifiers:
    """Returns underwater combat modifiers per DMG Chapter 3.
    
    Slashing/bludgeoning: -2 attack
    Piercing/natural: no penalty
    Crossbow: -4 attack, range capped
    Thrown: cannot be used underwater (attack_penalty=-999 marker, ranged_range_ft=0)
    Fire damage: no effect (multiplier 0.0)
    Electricity: +50% if both underwater
    """
    electricity_mult = 1.5 if both_underwater else 1.0

    if weapon_type == WeaponType.THROWN:
        return UnderwaterModifiers(
            attack_penalty=0,
            ranged_range_ft=0,  # cannot throw
            fire_damage_multiplier=0.0,
            electricity_multiplier=electricity_mult,
        )
    elif weapon_type == WeaponType.CROSSBOW:
        return UnderwaterModifiers(
            attack_penalty=-4,
            ranged_range_ft=30,  # range capped at 30 ft
            fire_damage_multiplier=0.0,
            electricity_multiplier=electricity_mult,
        )
    elif weapon_type in (WeaponType.SLASHING, WeaponType.BLUDGEONING):
        return UnderwaterModifiers(
            attack_penalty=-2,
            ranged_range_ft=None,
            fire_damage_multiplier=0.0,
            electricity_multiplier=electricity_mult,
        )
    else:  # PIERCING, NATURAL
        return UnderwaterModifiers(
            attack_penalty=0,
            ranged_range_ft=None,
            fire_damage_multiplier=0.0,
            electricity_multiplier=electricity_mult,
        )


# ---------------------------------------------------------------------------
# T-037 Aerial Combat Modifier Engine
# ---------------------------------------------------------------------------

class Maneuverability(Enum):
    CLUMSY = "clumsy"
    POOR = "poor"
    AVERAGE = "average"
    GOOD = "good"
    PERFECT = "perfect"


@dataclass(slots=True)
class AerialModifiers:
    attack_bonus: int                  # + or - to attack rolls
    can_charge: bool                   # whether charging while flying is allowed
    can_attack_after_direction_change: bool  # Clumsy: no
    min_forward_movement: bool         # must move forward each round (Clumsy/Poor)
    dive_attack_bonus: int             # bonus when diving (altitude_delta negative)


def apply_aerial_modifiers(
    maneuverability: Maneuverability,
    altitude_delta_ft: int = 0,
) -> AerialModifiers:
    """Returns aerial combat modifiers per DMG Chapter 3.

    altitude_delta_ft: negative = diving (attacker descends), positive = ascending
    """
    attack_bonus = 0
    if altitude_delta_ft < 0:  # diving
        attack_bonus += 1
    elif altitude_delta_ft > 0:  # ascending/upward attack
        attack_bonus -= 1

    can_charge = maneuverability in (Maneuverability.AVERAGE, Maneuverability.GOOD, Maneuverability.PERFECT)
    can_attack_after_dir = maneuverability != Maneuverability.CLUMSY
    min_forward = maneuverability in (Maneuverability.CLUMSY, Maneuverability.POOR)

    return AerialModifiers(
        attack_bonus=attack_bonus,
        can_charge=can_charge,
        can_attack_after_direction_change=can_attack_after_dir,
        min_forward_movement=min_forward,
        dive_attack_bonus=1 if altitude_delta_ft < 0 else 0,
    )


# ---------------------------------------------------------------------------
# T-038 Weather State Machine (Escalation)
# ---------------------------------------------------------------------------

@dataclass
class WeatherStateMachine:
    precipitation: Precipitation
    wind: WindStrength
    temperature: Temperature

    def advance(self, hours: int = 1, climate: TerrainType = TerrainType.PLAINS, rng: _random.Random | None = None) -> "WeatherStateMachine":
        """Advance weather state by given hours, applying escalation/de-escalation probabilities."""
        if rng is None:
            rng = _random.Random()

        precip = self.precipitation
        wind = self.wind
        temp = self.temperature

        storm_climate = climate in (TerrainType.MARSH, TerrainType.MOUNTAINS, TerrainType.ARCTIC)
        escalate_prob = 0.15 if storm_climate else 0.10
        deescalate_prob = 0.10 if storm_climate else 0.15

        precip_order = [Precipitation.NONE, Precipitation.LIGHT, Precipitation.HEAVY, Precipitation.TORRENTIAL]
        wind_order = [WindStrength.CALM, WindStrength.LIGHT, WindStrength.MODERATE, WindStrength.STRONG, WindStrength.SEVERE, WindStrength.WINDSTORM, WindStrength.HURRICANE, WindStrength.TORNADO]

        for _ in range(hours):
            pi = precip_order.index(precip)
            roll = rng.random()
            if roll < escalate_prob and pi < len(precip_order) - 1:
                precip = precip_order[pi + 1]
            elif roll > 1 - deescalate_prob and pi > 0:
                precip = precip_order[pi - 1]

            wi = wind_order.index(wind)
            roll = rng.random()
            if roll < escalate_prob and wi < len(wind_order) - 1:
                wind = wind_order[wi + 1]
            elif roll > 1 - deescalate_prob and wi > 0:
                wind = wind_order[wi - 1]

        return WeatherStateMachine(precipitation=precip, wind=wind, temperature=temp)

    def get_penalties(self) -> WeatherPenalties:
        """Get current weather penalties."""
        return apply_weather_penalties(self.precipitation, self.wind, self.temperature)


def generate_weather(
    climate: TerrainType,
    season: str = "temperate",
    rng: _random.Random | None = None,
) -> WeatherStateMachine:
    """Generate a starting weather state based on climate and season."""
    if rng is None:
        rng = _random.Random()

    if climate == TerrainType.ARCTIC:
        temp = Temperature.EXTREME_COLD if season in ("winter", "autumn") else Temperature.COLD
        precip_choices = [Precipitation.LIGHT, Precipitation.HEAVY, Precipitation.NONE]
        wind_choices = [WindStrength.MODERATE, WindStrength.STRONG, WindStrength.SEVERE]
    elif climate == TerrainType.DESERT:
        temp = Temperature.EXTREME_HEAT if season == "summer" else Temperature.HOT
        precip_choices = [Precipitation.NONE, Precipitation.NONE, Precipitation.LIGHT]
        wind_choices = [WindStrength.CALM, WindStrength.LIGHT, WindStrength.MODERATE]
    elif climate == TerrainType.MOUNTAINS:
        temp = Temperature.COLD if season in ("winter", "autumn") else Temperature.TEMPERATE
        precip_choices = [Precipitation.NONE, Precipitation.LIGHT, Precipitation.HEAVY]
        wind_choices = [WindStrength.MODERATE, WindStrength.STRONG, WindStrength.SEVERE]
    elif climate == TerrainType.MARSH:
        temp = Temperature.TEMPERATE
        precip_choices = [Precipitation.LIGHT, Precipitation.HEAVY, Precipitation.NONE]
        wind_choices = [WindStrength.CALM, WindStrength.LIGHT, WindStrength.MODERATE]
    else:
        temp = Temperature.TEMPERATE if season not in ("winter",) else Temperature.COLD
        precip_choices = [Precipitation.NONE, Precipitation.LIGHT, Precipitation.NONE]
        wind_choices = [WindStrength.CALM, WindStrength.LIGHT, WindStrength.MODERATE]

    return WeatherStateMachine(
        precipitation=rng.choice(precip_choices),
        wind=rng.choice(wind_choices),
        temperature=temp,
    )


# ---------------------------------------------------------------------------
# T-046 Dungeon Dressing Generator
# ---------------------------------------------------------------------------

class AirQuality(Enum):
    FRESH = "fresh"
    SMOKY = "smoky"
    MUSTY = "musty"
    DAMP = "damp"
    FOULED = "fouled"


@dataclass(slots=True)
class DungeonDressingResult:
    air_quality: AirQuality
    smells: str
    sounds: str
    general_features: str


_AIR_QUALITY_TABLE = [
    (1, 6, AirQuality.FRESH),
    (7, 10, AirQuality.DAMP),
    (11, 14, AirQuality.MUSTY),
    (15, 17, AirQuality.SMOKY),
    (18, 19, AirQuality.FOULED),
    (20, 20, AirQuality.FOULED),
]

_SMELL_TABLE = [
    "Earthy", "Musty", "Damp stone", "Rot and decay", "Sulfur",
    "Fresh air", "Smoke", "Incense", "Blood", "Mold",
    "Brine", "Charcoal", "Animal musk", "Burnt wood", "Herbs",
    "Wet metal", "Stale air", "Sewage", "Fungal spores", "Nothing notable",
]

_SOUND_TABLE = [
    "Silence", "Dripping water", "Distant footsteps", "Creaking", "Wind howling",
    "Rattling chains", "Scratching", "Faint moaning", "Distant roar", "Rushing water",
    "Crumbling stone", "Insect buzzing", "Faint chanting", "Metal on stone", "Splashing",
    "Distant screaming", "Echoing laughter", "Nothing", "Clicking", "Grinding stone",
]

_FEATURE_TABLE = [
    "Rubble on the floor", "Cobwebs in corners", "Old torch brackets", "Carved stone reliefs",
    "Cracked flagstones", "Damp walls with moss", "Scattered bones", "Dust-covered surfaces",
    "Ancient graffiti", "Empty iron rings in walls", "Mysterious stains", "Broken pottery shards",
    "Faded tapestry remnants", "Old campfire ashes", "Collapsed section of ceiling",
    "Puddles of stagnant water", "Crude wooden furniture remains", "Rusted iron door hinges",
    "Etched symbols on walls", "Fresh claw marks",
]


def generate_dungeon_dressing(rng: _random.Random | None = None) -> DungeonDressingResult:
    """Generate dungeon dressing from DMG Chapter 4 d20 sub-tables."""
    if rng is None:
        rng = _random.Random()

    roll = rng.randint(1, 20)
    air = AirQuality.FRESH
    for low, high, quality in _AIR_QUALITY_TABLE:
        if low <= roll <= high:
            air = quality
            break

    smell = rng.choice(_SMELL_TABLE)
    sound = rng.choice(_SOUND_TABLE)
    feature = rng.choice(_FEATURE_TABLE)

    return DungeonDressingResult(
        air_quality=air,
        smells=smell,
        sounds=sound,
        general_features=feature,
    )


# ---------------------------------------------------------------------------
# T-053 Compound Weather + Terrain Integration
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class EnvironmentResult:
    movement_multiplier: float
    ranged_attack_penalty: int
    visibility_ft: int
    passive_perception_penalty: int    # combined spot/listen penalty
    fort_dc_cold: int | None
    fort_dc_heat: int | None


def apply_environment(
    weather: WeatherStateMachine,
    terrain: TerrainType,
    mounted: bool = False,
) -> EnvironmentResult:
    """Combine weather and terrain into a single EnvironmentResult."""
    penalties = weather.get_penalties()
    move_mult = terrain_movement_cost(terrain, mount=mounted)

    weather_move = penalties.movement_penalty_pct
    combined_move = move_mult * weather_move

    perception_penalty = max(penalties.listen_penalty, penalties.spot_penalty)
    perception_penalty += terrain_listen_penalty(terrain)

    return EnvironmentResult(
        movement_multiplier=combined_move,
        ranged_attack_penalty=penalties.ranged_attack_penalty,
        visibility_ft=penalties.visibility_ft,
        passive_perception_penalty=perception_penalty,
        fort_dc_cold=penalties.fort_dc_cold,
        fort_dc_heat=penalties.fort_dc_heat,
    )
