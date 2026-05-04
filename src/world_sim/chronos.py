"""PH5-006 · PH5-008 — Chronos & Atmosphere subsystem.

src/world_sim/chronos.py
------------------------
Provides the world clock (ChronosRecord) and procedural weather engine
(WeatherState) for the New Game Plus simulation.

Also implements the D&D 3.5e Chronos Engine: a full time-management system
(GameTime + ChronosEngine) that translates combat rounds into world-scale
hours and days and integrates with the EventBus.

Key types
~~~~~~~~~
* :class:`ChronosRecord` — immutable snapshot of the in-game date/time.
* :class:`WeatherType`   — enumeration of weather conditions.
* :class:`WeatherState`  — mutable weather + particle state.
* :class:`GameTime`      — D&D 3.5e world clock (seconds since Genesis).
* :class:`ChronosEngine` — event-bus-integrated time manager.

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
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.event_bus import EventBus

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


# ---------------------------------------------------------------------------
# D&D 3.5e Time Engine · Constants
# ---------------------------------------------------------------------------

#: Seconds per combat round (D&D 3.5e SRD).
SECONDS_PER_ROUND: int = 6

#: Rounds per in-game minute.
ROUNDS_PER_MINUTE: int = 10

#: Minutes per in-game hour.
MINUTES_PER_HOUR: int = 60

#: Hours per in-game day.
HOURS_PER_GAME_DAY: int = 24

#: Seconds per in-game minute.
SECONDS_PER_MINUTE: int = SECONDS_PER_ROUND * ROUNDS_PER_MINUTE  # 60

#: Seconds per in-game hour.
SECONDS_PER_HOUR: int = SECONDS_PER_MINUTE * MINUTES_PER_HOUR  # 3600

#: Seconds per in-game day.
SECONDS_PER_DAY: int = SECONDS_PER_HOUR * HOURS_PER_GAME_DAY  # 86400

#: EventBus event name fired by the combat engine after each round.
EVENT_COMBAT_ROUND_END: str = "COMBAT_ROUND_END"

#: EventBus event name fired by ChronosEngine when an hour or day crosses.
EVENT_TIME_TICK: str = "TIME_TICK"


# ---------------------------------------------------------------------------
# D&D 3.5e Time Engine · Calendar
# ---------------------------------------------------------------------------

#: The 12-month fantasy calendar.  Each entry is ``(month_name, days_in_month)``.
#: The year totals 365 days.
CALENDAR_MONTHS: List[tuple[str, int]] = [
    ("Frostborn",    31),  # 1  — deep winter; the year awakens in ice
    ("Thaw's Wake",  28),  # 2  — winter retreats; rivers begin to move
    ("Verdant Rise", 31),  # 3  — first sprouts; adventuring season begins
    ("Bloom's Tide", 30),  # 4  — wildflower bloom; festival of colours
    ("Suncrest",     31),  # 5  — longest light; high-altitude passes open
    ("Highsun",      30),  # 6  — peak summer; caravans fill the roads
    ("Goldmere",     31),  # 7  — harvest preparations; markets overflow
    ("Harvest's Eve",31),  # 8  — main harvest; grain stored against winter
    ("Ashfall",      30),  # 9  — leaves turn; first ash-grey skies
    ("Mourning Moon",31),  # 10 — dark festivals; ancestors remembered
    ("Deepchill",    30),  # 11 — early frost; gates close at dusk
    ("Nighthold",    31),  # 12 — solstice; the long dark before Frostborn
]

#: Total days in one game year, derived from the calendar.
DAYS_PER_YEAR: int = sum(days for _, days in CALENDAR_MONTHS)  # 365

#: Cumulative day-of-year at the *start* of each month (0-indexed, month 0 = "Frostborn").
_MONTH_START_DAY: List[int] = []
_acc = 0
for _name, _days in CALENDAR_MONTHS:
    _MONTH_START_DAY.append(_acc)
    _acc += _days
del _name, _days, _acc


# ---------------------------------------------------------------------------
# D&D 3.5e Time Engine · GameTime
# ---------------------------------------------------------------------------

@dataclass
class GameTime:
    """In-universe clock for the New Game Plus world.

    Tracks time as an *absolute tick* (total seconds elapsed since the
    world's Genesis moment).  All calendar fields — second, minute, hour,
    day, month, year — are derived from :attr:`absolute_tick` on demand.

    Attributes:
        absolute_tick: Total seconds since Genesis (monotonically increasing).
    """

    absolute_tick: int = 0

    # ------------------------------------------------------------------
    # Derived time fields
    # ------------------------------------------------------------------

    @property
    def second(self) -> int:
        """Current second within the current minute (0–59)."""
        return self.absolute_tick % SECONDS_PER_MINUTE

    @property
    def minute(self) -> int:
        """Current minute within the current hour (0–59)."""
        return (self.absolute_tick // SECONDS_PER_MINUTE) % MINUTES_PER_HOUR

    @property
    def hour(self) -> int:
        """Current hour within the current day (0–23)."""
        return (self.absolute_tick // SECONDS_PER_HOUR) % HOURS_PER_GAME_DAY

    @property
    def total_days(self) -> int:
        """Total complete days elapsed since Genesis."""
        return self.absolute_tick // SECONDS_PER_DAY

    @property
    def year(self) -> int:
        """Current game year (0-indexed from Genesis)."""
        return self.total_days // DAYS_PER_YEAR

    @property
    def day_of_year(self) -> int:
        """Current day within the current year (0-indexed, 0 = first day of year)."""
        return self.total_days % DAYS_PER_YEAR

    @property
    def month_index(self) -> int:
        """Current month index (0-indexed; 0 = Frostborn, 11 = Nighthold)."""
        doy = self.day_of_year
        for i in range(len(CALENDAR_MONTHS) - 1, -1, -1):
            if doy >= _MONTH_START_DAY[i]:
                return i
        return 0  # pragma: no cover

    @property
    def month_name(self) -> str:
        """Human-readable name of the current month."""
        return CALENDAR_MONTHS[self.month_index][0]

    @property
    def day_of_month(self) -> int:
        """Current day within the current month (1-indexed)."""
        return self.day_of_year - _MONTH_START_DAY[self.month_index] + 1

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialise the clock to a plain :class:`dict` (JSON-safe).

        Returns:
            A dict containing ``absolute_tick`` and a human-readable
            ``formatted_date`` string, suitable for embedding in
            ``data/world_state.json``.
        """
        return {
            "absolute_tick": self.absolute_tick,
            "formatted_date": (
                f"Year {self.year}, {self.month_name} {self.day_of_month}, "
                f"{self.hour:02d}:{self.minute:02d}:{self.second:02d}"
            ),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GameTime":
        """Restore a :class:`GameTime` from a serialised dict.

        Args:
            data: Dict previously produced by :meth:`to_dict`.

        Returns:
            A new :class:`GameTime` with :attr:`absolute_tick` restored.
        """
        return cls(absolute_tick=int(data["absolute_tick"]))

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"GameTime(tick={self.absolute_tick}, "
            f"Year {self.year} {self.month_name} {self.day_of_month}, "
            f"{self.hour:02d}:{self.minute:02d}:{self.second:02d})"
        )


# ---------------------------------------------------------------------------
# D&D 3.5e Time Engine · ChronosEngine
# ---------------------------------------------------------------------------

class ChronosEngine:
    """Observable D&D 3.5e time manager that integrates with :class:`EventBus`.

    The engine subscribes to :data:`EVENT_COMBAT_ROUND_END` on an
    :class:`~src.core.event_bus.EventBus`.  Each time that event fires the
    clock advances by :data:`SECONDS_PER_ROUND` (6 s).  When a new **hour**
    or **day** boundary is crossed, a :data:`EVENT_TIME_TICK` event is
    published so that Biome and Faction systems can respond.

    The current :class:`GameTime` is serialisable via :meth:`to_dict` /
    :meth:`from_dict` for persistence in ``data/world_state.json``.

    Example::

        from src.core.event_bus import EventBus
        from src.world_sim.chronos import ChronosEngine

        bus = EventBus()
        engine = ChronosEngine()
        engine.attach(bus)

        # Fire 14400 combat rounds — clock should advance by exactly 24 hours.
        for _ in range(14_400):
            bus.publish("COMBAT_ROUND_END", {})

        assert engine.game_time.hour == 0  # wrapped back to midnight
        assert engine.game_time.total_days == 1

    Attributes:
        game_time:    The current in-universe :class:`GameTime`.
        real_started: Wall-clock :class:`~datetime.datetime` at which this
                      engine was created (UTC, for logging / analytics).
    """

    def __init__(self, initial_tick: int = 0) -> None:
        self.game_time: GameTime = GameTime(absolute_tick=initial_tick)
        self.real_started: datetime = datetime.now(tz=timezone.utc)
        self._bus: Optional["EventBus"] = None

    # ------------------------------------------------------------------
    # EventBus integration
    # ------------------------------------------------------------------

    def attach(self, bus: "EventBus") -> None:
        """Subscribe this engine to *bus* and remember it for publishing.

        Calling :meth:`attach` a second time on a different bus first
        detaches from the previous bus.

        Args:
            bus: The :class:`~src.core.event_bus.EventBus` to integrate with.
        """
        if self._bus is not None:
            self._bus.unsubscribe(EVENT_COMBAT_ROUND_END, self._on_combat_round_end)
        self._bus = bus
        bus.subscribe(EVENT_COMBAT_ROUND_END, self._on_combat_round_end)

    def detach(self) -> None:
        """Unsubscribe from the currently attached bus (no-op if not attached)."""
        if self._bus is not None:
            self._bus.unsubscribe(EVENT_COMBAT_ROUND_END, self._on_combat_round_end)
            self._bus = None

    def _on_combat_round_end(self, _payload: Any) -> None:
        """Handler called on every :data:`EVENT_COMBAT_ROUND_END` event."""
        self.advance_seconds(SECONDS_PER_ROUND)

    # ------------------------------------------------------------------
    # Core tick logic
    # ------------------------------------------------------------------

    def advance_seconds(self, seconds: int) -> None:
        """Advance the world clock by *seconds* and fire boundary events.

        Fires :data:`EVENT_TIME_TICK` with ``{"type": "hour", ...}`` for
        every new hour crossed, and with ``{"type": "day", ...}`` for every
        new day crossed.  Events are published in strict chronological order
        (by the tick at which each boundary was crossed).

        Args:
            seconds: Number of real seconds (in-universe) to advance.
        """
        old_tick = self.game_time.absolute_tick
        new_tick = old_tick + seconds

        old_hour_abs = old_tick // SECONDS_PER_HOUR
        new_hour_abs = new_tick // SECONDS_PER_HOUR
        hours_crossed = new_hour_abs - old_hour_abs

        old_day = old_tick // SECONDS_PER_DAY
        new_day = new_tick // SECONDS_PER_DAY
        days_crossed = new_day - old_day

        self.game_time = GameTime(absolute_tick=new_tick)

        if self._bus is None or hours_crossed == 0:
            return

        # Build all boundary events sorted by the tick at which they occur.
        boundary_events: list[tuple[int, dict]] = []

        for h in range(hours_crossed):
            boundary_tick = (old_hour_abs + h + 1) * SECONDS_PER_HOUR
            boundary_time = GameTime(absolute_tick=boundary_tick)
            boundary_events.append((
                boundary_tick,
                {
                    "type": "hour",
                    "absolute_tick": boundary_tick,
                    "hour": boundary_time.hour,
                    "game_time": boundary_time.to_dict(),
                },
            ))

        for d in range(days_crossed):
            boundary_tick = (old_day + d + 1) * SECONDS_PER_DAY
            boundary_time = GameTime(absolute_tick=boundary_tick)
            boundary_events.append((
                boundary_tick,
                {
                    "type": "day",
                    "absolute_tick": boundary_tick,
                    "total_days": old_day + d + 1,
                    "game_time": boundary_time.to_dict(),
                },
            ))

        # Publish in chronological order.
        for _, payload in sorted(boundary_events, key=lambda x: x[0]):
            self._bus.publish(EVENT_TIME_TICK, payload)

    def advance_rounds(self, rounds: int) -> None:
        """Advance the world clock by *rounds* combat rounds (6 s each).

        Args:
            rounds: Number of D&D 3.5e combat rounds to simulate.
        """
        self.advance_seconds(rounds * SECONDS_PER_ROUND)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialise engine state for ``data/world_state.json``.

        Returns:
            A JSON-safe dict containing :attr:`game_time` and
            :attr:`real_started` metadata.
        """
        return {
            "game_time": self.game_time.to_dict(),
            "real_started": self.real_started.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChronosEngine":
        """Restore a :class:`ChronosEngine` from a previously saved dict.

        Args:
            data: Dict previously produced by :meth:`to_dict`.

        Returns:
            A new :class:`ChronosEngine` with the saved tick restored.
        """
        engine = cls(initial_tick=int(data["game_time"]["absolute_tick"]))
        try:
            engine.real_started = datetime.fromisoformat(data["real_started"])
        except (KeyError, ValueError):
            pass
        return engine
