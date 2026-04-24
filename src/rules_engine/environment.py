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
    ranged_attack_penalty: int     # negative = penalty to attack rolls
    visibility_ft: int             # max visibility distance in feet
    movement_penalty_pct: float    # fraction of normal movement (1.0 = no penalty)
    listen_penalty: int            # penalty to Listen checks
    spot_penalty: int              # penalty to Spot checks
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
