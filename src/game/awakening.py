"""
src/game/awakening.py
---------------------
First Awakening — genesis transition from Character Forge into the active world.

Responsibilities
~~~~~~~~~~~~~~~~
* Detect ``data/player.json`` and load the Mortal Coil.
* Initialise a :class:`~src.world_sim.world_tick.WorldState` rooted in the
  **Ashen Crossroads** starting biome.
* Force the :class:`~src.terrain.chunk_manager.ChunkManager` to spawn the
  player at world coordinates (0, 0, 0) inside a Safe Zone room.
* Dynamically enhance the room description by weaving in the player's Mortal
  Coil traits (eye aspect, build, distinguishing marks).
* Fire a ``PLAYER_AWAKENED`` event so the Chronos Engine begins ticking from
  Hour 0, Day 1 (absolute tick 0).
"""

from __future__ import annotations

import json
import logging
import random
import sys
import textwrap
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent.parent
_PLAYER_JSON = _REPO_ROOT / "data" / "player.json"

# ---------------------------------------------------------------------------
# Safe Zone room — base lore templates
# The RoomDescriptionEngine will stitch these together and splice in
# player-specific Mortal Coil details.
# ---------------------------------------------------------------------------

_BASE_ROOM_LINES = [
    "Silence presses against you like a physical weight.",
    "Ash drifts in slow spirals through air that smells of cold iron and old stone.",
    "Crumbling columns ring the chamber, their carvings worn to suggestions.",
    "The floor beneath you is solid — flagstone worn smooth by ages of footfall.",
    "A sealed iron vault door dominates the far wall, its surface etched with "
    "runes you almost recognise.",
    "No light source is visible, yet you can see. The darkness here is not empty.",
]

_COIL_TEMPLATES: list[str] = [
    "The faint non-light catches the {eye_aspect} of your eyes as you take in the ruin.",
    "Your {build} frame casts a long shadow across the ashen floor.",
    "The {marks} on your skin aches in the cold — an old wound remembering itself.",
    "Somewhere behind you, nothing stirs. You are, for now, alone.",
]

_CLOSING_LINES = [
    "You have awakened at the Ashen Crossroads.",
    "Hour 0. Day 1. The world waits.",
]

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class SafeZoneRoom:
    """The player's starting room at coordinates (0, 0, 0).

    Attributes:
        chunk_x:     Chunk X coordinate (always 0).
        chunk_z:     Chunk Z coordinate (always 0).
        world_x:     World X of the player spawn point.
        world_y:     World Y of the player spawn point (surface level).
        world_z:     World Z of the player spawn point.
        description: Fully-rendered, Mortal-Coil-enhanced room description.
        features:    Biome features present in this room (from spawn-rate table).
    """
    chunk_x: int = 0
    chunk_z: int = 0
    world_x: int = 0
    world_y: int = 64  # surface level as defined by BASE_HEIGHT in chunk_generator
    world_z: int = 0
    description: str = ""
    features: list[str] = field(default_factory=list)


@dataclass
class AwakeningState:
    """Everything initialised during the First Awakening sequence.

    Passed back to the caller so the game loop can wire up tick scheduling.
    """
    player_data: Dict[str, Any]
    world_state: Any   # WorldState — typed as Any to avoid circular imports
    chunk_manager: Any  # ChunkManager
    origin_room: SafeZoneRoom
    absolute_tick: int = 0


# ---------------------------------------------------------------------------
# RoomDescriptionEngine
# Simulates MasterMinion AI narrative enhancement.
# Takes a base room template and weaves in player Mortal Coil context.
# ---------------------------------------------------------------------------


class RoomDescriptionEngine:
    """Narrative engine that personalises room descriptions with Mortal Coil data.

    Mirrors the role of the MasterMinion LLM bridge for atmospheric text
    generation — without requiring a live inference endpoint.  When a real
    LLM client becomes available, this class is the intended integration point.
    """

    def enhance(
        self,
        player_data: Dict[str, Any],
        base_lines: list[str],
        coil_templates: list[str],
        closing_lines: list[str],
        rng: Optional[random.Random] = None,
    ) -> str:
        """Weave player Mortal Coil traits into the room description.

        Args:
            player_data:    Full character dict from ``data/player.json``.
            base_lines:     Static atmospheric lines for the room.
            coil_templates: Format-string templates referencing Mortal Coil fields.
            closing_lines:  Closing beats appended after the Coil passages.
            rng:            Optional seeded RNG for shuffling base lines.

        Returns:
            A multi-paragraph room description string ready for display.
        """
        phys = player_data.get("physical_description", {})
        eye_aspect   = phys.get("eye_aspect",           "dark").lower()
        build        = phys.get("build",                 "lean").lower()
        marks        = phys.get("distinguishing_marks",  "old scars").lower()
        name         = player_data.get("name",           "Traveller")
        char_class   = player_data.get("char_class",     "wanderer").lower()
        race         = player_data.get("race",           "unknown origin")

        # Shuffle base lines for variety without predictability
        shuffled = list(base_lines)
        if rng is not None:
            rng.shuffle(shuffled)

        paragraphs: list[str] = []

        # Opening — character grounding
        paragraphs.append(
            f"{name} — {race} {char_class} — opens their eyes."
        )

        # Base atmospheric description
        paragraphs.append(" ".join(shuffled))

        # Mortal Coil passages — interpolate player traits
        coil_passages: list[str] = []
        for tmpl in coil_templates:
            try:
                coil_passages.append(
                    tmpl.format(eye_aspect=eye_aspect, build=build, marks=marks)
                )
            except KeyError:
                coil_passages.append(tmpl)
        paragraphs.append(" ".join(coil_passages))

        # Closing beats
        paragraphs.append("  ".join(closing_lines))

        return "\n\n".join(paragraphs)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_player(path: Path) -> Dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _roll_features(
    feature_spawn_rates: dict[str, float],
    rng: random.Random,
) -> list[str]:
    """Roll which biome features are present in the origin room."""
    return [tag for tag, prob in feature_spawn_rates.items() if rng.random() <= prob]


def _build_origin_room(
    player_data: Dict[str, Any],
    rng: random.Random,
) -> SafeZoneRoom:
    from src.world_sim.biome import ASHEN_CROSSROADS

    features = _roll_features(ASHEN_CROSSROADS.feature_spawn_rates, rng)

    engine = RoomDescriptionEngine()
    description = engine.enhance(
        player_data=player_data,
        base_lines=_BASE_ROOM_LINES,
        coil_templates=_COIL_TEMPLATES,
        closing_lines=_CLOSING_LINES,
        rng=rng,
    )

    return SafeZoneRoom(
        chunk_x=0,
        chunk_z=0,
        world_x=0,
        world_y=64,
        world_z=0,
        description=description,
        features=features,
    )


def _init_world_state(event_bus: Any) -> Any:
    """Bootstrap the minimal WorldState for the First Awakening."""
    from src.world_sim.biome import Biome
    from src.world_sim.world_tick import WorldState
    from src.world_sim.population import WorldChunk

    origin_chunk = WorldChunk(
        chunk_id="0,0",
        biome=Biome.Ashen_Crossroads,
        adjacent_chunks=(),
        local_populations={},
        carrying_capacity={},
    )

    return WorldState(
        world_chunks=[origin_chunk],
        ledger={},
        species_registry={},
        pending_vectors=[],
        food_web_entries=[],
        event_bus=event_bus,
        tick=0,
    )


def _init_chunk_manager(event_bus: Any) -> Any:
    """Create a ChunkManager wired to the shared event bus.

    Attempts to attach a noise-based :class:`ChunkGenerator` (requires the
    ``opensimplex`` package).  Falls back to the flat-terrain default if the
    package is unavailable — chunk_manager.py itself imports chunk_generator at
    module level, so the entire import is guarded.
    """
    try:
        from src.terrain.chunk_manager import ChunkManager
        from src.terrain.chunk_generator import ChunkGenerator
        generator: Any = ChunkGenerator(seed=0)
    except ImportError:
        _log.warning(
            "opensimplex not installed — ChunkManager unavailable; "
            "skipping terrain initialisation."
        )
        return None

    manager = ChunkManager(
        event_bus=event_bus,
        cache_size=64,
        saves_dir=str(_REPO_ROOT / "saves"),
        generator=generator,
    )
    # Pre-load origin chunk into cache
    manager.load_chunk(0, 0)
    return manager


def _print_awakening(room: SafeZoneRoom, stream=None) -> None:
    """Render the awakening sequence to *stream* (default: stdout)."""
    if stream is None:
        stream = sys.stdout

    width = 72
    border = "=" * width

    stream.write("\n")
    stream.write(border + "\n")
    stream.write("  ASHEN CROSSROADS  —  FIRST AWAKENING\n")
    stream.write(border + "\n\n")

    for paragraph in room.description.split("\n\n"):
        for line in textwrap.wrap(paragraph.strip(), width=width - 4):
            stream.write("  " + line + "\n")
        stream.write("\n")

    if room.features:
        stream.write("  [ Features present: " + ", ".join(room.features) + " ]\n\n")

    stream.write(border + "\n\n")
    stream.flush()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_first_awakening(
    player_json_path: Optional[Path] = None,
    stream=None,
    seed: Optional[int] = None,
) -> int:
    """Execute the First Awakening sequence.

    1. Load player data from ``data/player.json``.
    2. Initialise :class:`~src.world_sim.world_tick.WorldState` with the
       Ashen Crossroads biome as the sole world chunk.
    3. Initialise :class:`~src.terrain.chunk_manager.ChunkManager` and
       pre-load the origin chunk at (0, 0).
    4. Generate the Safe Zone room description, enhanced by Mortal Coil traits.
    5. Fire ``PLAYER_AWAKENED`` on the shared :class:`~src.core.event_bus.EventBus`,
       carrying the player data, position, and Chronos record at tick 0.
    6. Print the atmospheric awakening text to *stream*.

    Args:
        player_json_path: Override path to ``player.json`` (defaults to
                          ``data/player.json`` relative to the repo root).
        stream:           Output stream for the awakening text (default: stdout).
        seed:             RNG seed for deterministic room generation.

    Returns:
        Exit code — 0 on success, 1 on failure.
    """
    from src.core.event_bus import default_bus
    from src.world_sim.chronos import chronos_from_world_tick

    path = player_json_path or _PLAYER_JSON

    if not path.exists():
        _log.error("No player file at %s — run the Character Forge first.", path)
        print(
            f"[ERROR] No player file found at {path}.\n"
            "Run the Character Forge first to create your character.",
            file=sys.stderr,
        )
        return 1

    try:
        player_data = _load_player(path)
    except (json.JSONDecodeError, OSError) as exc:
        _log.exception("Failed to load player data: %r", exc)
        print(f"[ERROR] Could not read player file: {exc}", file=sys.stderr)
        return 1

    rng = random.Random(seed if seed is not None else int(time.time()))

    # Initialise engine subsystems
    world_state   = _init_world_state(default_bus)
    chunk_manager = _init_chunk_manager(default_bus)

    # Generate origin room
    origin_room = _build_origin_room(player_data, rng)

    # Build the Chronos record — Hour 0, Day 1 = absolute tick 0
    chronos = chronos_from_world_tick(0)

    # Fire PLAYER_AWAKENED event
    default_bus.publish(
        "PLAYER_AWAKENED",
        {
            "player":    player_data,
            "position":  {"x": origin_room.world_x, "y": origin_room.world_y, "z": origin_room.world_z},
            "biome":     "ashen_crossroads",
            "features":  origin_room.features,
            "tick":      chronos.tick,
            "hour":      chronos.hour,
            "is_day":    chronos.is_day,
            "world_state": world_state,
        },
    )

    _log.info(
        "PLAYER_AWAKENED fired — tick=%d hour=%d is_day=%s position=(0,64,0)",
        chronos.tick, chronos.hour, chronos.is_day,
    )

    # Render the atmospheric awakening text
    _print_awakening(origin_room, stream=stream)

    return 0
