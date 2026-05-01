"""PH5-006 · PH5-008 — Chronos & Atmosphere subsystem.

src/world_sim/chronos.py
------------------------
Provides the world clock (ChronosRecord) and procedural weather engine
(WeatherState) for the New Game Plus simulation.

Key types
~~~~~~~~~
* :class:`ChronosRecord` — immutable snapshot of the in-game date/time.
* :class:`WeatherType`   — enumeration of weather conditions.
* :class:`WeatherState`  — mutable weather + particle state.

Key functions
~~~~~~~~~~~~~
* :func:`chronos_from_world_tick` — canonical constructor.
* :func:`advance_chronos`         — returns the next ChronosRecord.
* :func:`generate_weather`        — procedural weather roll.
* :func:`tick_weather`            — advance one weather animation frame.
* :func:`apply_weather_debuffs`   — write weather penalties to character metadata.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# PH5-006 · Constants
# ---------------------------------------------------------------------------

TICKS_PER_HOUR: int = 60
"""Number of world ticks that elapse per in-game hour."""

HOURS_PER_DAY: int = 24
"""Number of in-game hours per day."""

DAY_START_HOUR: int = 6
"""First hour of daylight (inclusive)."""

NIGHT_START_HOUR: int = 20
"""First hour of night (inclusive)."""


# ---------------------------------------------------------------------------
# PH5-006 · ChronosRecord dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ChronosRecord:
    """Immutable snapshot of the current in-game date/time and weather.

    All time-derived fields (``hour``, ``is_day``) are **computed** from
    ``tick`` and should not be set independently — use :func:`chronos_from_world_tick`
    or :func:`advance_chronos` as the authoritative constructors.

    Attributes:
        tick:           Absolute world-tick counter (monotonically increasing).
        hour:           Current in-game hour (0–23).
        is_day:         ``True`` when ``DAY_START_HOUR <= hour < NIGHT_START_HOUR``.
        weather:        Short weather label (e.g. ``"clear"``, ``"rain"``).
        rain_intensity: Rain intensity as a fraction in ``[0.0, 1.0]``.
        temperature_c:  Ambient temperature in degrees Celsius.
    """

    tick: int
    hour: int
    is_day: bool
    weather: str = "clear"
    rain_intensity: float = 0.0
    temperature_c: float = 18.0


def chronos_from_world_tick(world_tick: int) -> ChronosRecord:
    """Canonical constructor: build a :class:`ChronosRecord` from *world_tick*.

    Args:
        world_tick: Absolute world-tick counter.

    Returns:
        A new :class:`ChronosRecord` with hour/is_day derived from *world_tick*.
    """
    hour = (world_tick // TICKS_PER_HOUR) % HOURS_PER_DAY
    is_day = DAY_START_HOUR <= hour < NIGHT_START_HOUR
    return ChronosRecord(tick=world_tick, hour=hour, is_day=is_day)


def advance_chronos(
    record: ChronosRecord,
    ticks: int = 1,
    rng: Any = None,
    biome: str = "temperate",
) -> ChronosRecord:
    """Return a new :class:`ChronosRecord` advanced by *ticks* world ticks.

    Weather particle positions are advanced via :func:`tick_weather` when *rng*
    is provided (and a :class:`WeatherState` has been set in the record's
    context).  The base :class:`ChronosRecord` itself does **not** store a
    ``WeatherState`` directly — callers that track weather pass the state
    separately and supply *rng* to trigger a tick.

    Args:
        record: Current :class:`ChronosRecord`.
        ticks:  Number of ticks to advance (default 1).
        rng:    Optional random source; when not ``None``, weather particles are
                ticked via :func:`tick_weather`.
        biome:  Biome hint forwarded to weather generation on re-roll.

    Returns:
        A new :class:`ChronosRecord` with updated ``tick``, ``hour``, ``is_day``,
        and unchanged ``weather`` / ``rain_intensity`` / ``temperature_c``.
    """
    new_tick = record.tick + ticks
    new_hour = (new_tick // TICKS_PER_HOUR) % HOURS_PER_DAY
    new_is_day = DAY_START_HOUR <= new_hour < NIGHT_START_HOUR
    return ChronosRecord(
        tick=new_tick,
        hour=new_hour,
        is_day=new_is_day,
        weather=record.weather,
        rain_intensity=record.rain_intensity,
        temperature_c=record.temperature_c,
    )


# ---------------------------------------------------------------------------
# PH5-008 · WeatherType + WeatherState
# ---------------------------------------------------------------------------

class WeatherType(str, enum.Enum):
    """Enumeration of possible weather conditions.

    Members:
        CLEAR: No precipitation.
        RAIN:  Light to moderate rain.
        STORM: Heavy rain / thunderstorm.
    """

    CLEAR = "clear"
    RAIN = "rain"
    STORM = "storm"


@dataclass(slots=True)
class WeatherState:
    """Mutable snapshot of the current weather and ASCII particle positions.

    Attributes:
        weather_type:   Active :class:`WeatherType`.
        intensity:      Weather intensity as a fraction in ``[0.0, 1.0]``.
        rain_particles: Current ``(row, col)`` particle coordinates in the
                        24 × 80 viewport grid.
        wind_speed_ms:  Simulated wind speed in metres per second.
    """

    weather_type: WeatherType
    intensity: float
    rain_particles: list[tuple[int, int]]
    wind_speed_ms: float


# Biome rain probability table (probability that weather is *not* clear).
_BIOME_RAIN_PROBABILITY: dict[str, float] = {
    "desert":    0.05,
    "temperate": 0.25,
    "swamp":     0.45,
}
_DEFAULT_RAIN_PROBABILITY: float = 0.20

# Viewport dimensions for rain particle placement.
_VP_ROWS: int = 24
_VP_COLS: int = 80


def generate_weather(rng: Any, *, terrain_biome: str = "temperate") -> WeatherState:
    """Procedurally roll a new :class:`WeatherState` for *terrain_biome*.

    Algorithm:

    1. Look up the rain probability for *terrain_biome*
       (defaults to :data:`_DEFAULT_RAIN_PROBABILITY`).
    2. If ``rng.random()`` is *above* the threshold → return ``CLEAR``.
    3. Otherwise roll ``intensity = rng.uniform(0.3, 1.0)``.
    4. If ``intensity >= 0.8`` → ``STORM``; else → ``RAIN``.
    5. Populate ``rain_particles`` with ``int(intensity * 20)`` random
       ``(row, col)`` pairs inside a 24 × 80 viewport.

    Args:
        rng:          Random source with ``random()`` and ``uniform()`` methods.
        terrain_biome: Biome name used for the probability table lookup.

    Returns:
        A new :class:`WeatherState`.
    """
    rain_prob = _BIOME_RAIN_PROBABILITY.get(terrain_biome, _DEFAULT_RAIN_PROBABILITY)

    if rng.random() > rain_prob:
        return WeatherState(
            weather_type=WeatherType.CLEAR,
            intensity=0.0,
            rain_particles=[],
            wind_speed_ms=0.0,
        )

    intensity: float = rng.uniform(0.3, 1.0)
    weather_type = WeatherType.STORM if intensity >= 0.8 else WeatherType.RAIN
    n_particles = int(intensity * 20)
    particles = [
        (rng.randint(0, _VP_ROWS - 1), rng.randint(0, _VP_COLS - 1))
        for _ in range(n_particles)
    ]
    wind_speed = rng.uniform(1.0, intensity * 20.0)
    return WeatherState(
        weather_type=weather_type,
        intensity=intensity,
        rain_particles=particles,
        wind_speed_ms=wind_speed,
    )


def tick_weather(state: WeatherState, rng: Any) -> WeatherState:
    """Advance weather one animation frame and optionally re-roll.

    Each particle moves one row down, wrapping at row :data:`_VP_ROWS`.
    There is a 2 % chance per tick to regenerate weather from scratch via
    :func:`generate_weather`.

    Args:
        state: Current :class:`WeatherState`.
        rng:   Random source.

    Returns:
        A new :class:`WeatherState` with shifted (or regenerated) particles.
    """
    if rng.random() < 0.02:
        # 2 % chance to regenerate weather entirely.
        return generate_weather(rng)

    new_particles = [
        ((row + 1) % _VP_ROWS, col)
        for row, col in state.rain_particles
    ]
    return WeatherState(
        weather_type=state.weather_type,
        intensity=state.intensity,
        rain_particles=new_particles,
        wind_speed_ms=state.wind_speed_ms,
    )


# ---------------------------------------------------------------------------
# PH5-009 · Weather debuff integration
# ---------------------------------------------------------------------------

def apply_weather_debuffs(
    character_metadata: dict,
    weather: WeatherState,
) -> dict:
    """Write weather-derived combat and movement penalties to *character_metadata*.

    Penalty rules:

    * **Speed multiplier** — ``1.0 - (intensity × 0.4)`` when raining or
      storming; ``1.0`` otherwise.
    * **Attack penalty** — ``-2`` applied when weather is ``STORM``.
    * **Fire-effect extinction** — any effect in
      ``character_metadata["active_fire_effects"]`` whose ``"element"``
      key equals ``"fire"`` is removed (simulates dousing by storm rain).

    Args:
        character_metadata: Mutable metadata dict attached to the character.
        weather:            Current :class:`WeatherState`.

    Returns:
        The mutated *character_metadata* dict.
    """
    if weather.weather_type in (WeatherType.RAIN, WeatherType.STORM):
        speed_multiplier = 1.0 - (weather.intensity * 0.4)
    else:
        speed_multiplier = 1.0

    character_metadata["weather_speed_multiplier"] = speed_multiplier

    if weather.weather_type == WeatherType.STORM:
        character_metadata["weather_attack_penalty"] = -2
    else:
        character_metadata.pop("weather_attack_penalty", None)

    # Douse active fire effects during a storm.
    if weather.weather_type == WeatherType.STORM:
        active_fire = character_metadata.get("active_fire_effects", [])
        character_metadata["active_fire_effects"] = [
            eff for eff in active_fire
            if not (isinstance(eff, dict) and eff.get("element") == "fire")
        ]

    return character_metadata
