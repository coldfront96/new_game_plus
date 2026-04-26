"""LW-001 · LW-004 · LW-012 · LW-014 · LW-035 — Population ledger and world chunk schemas."""
from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.world_sim.biome import Biome, SpeciesBiomeBinding
    from src.core.event_bus import EventBus

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class SpeciesExtinctError(Exception):
    """Raised when a population delta is applied to an already-extinct species."""


class AlreadyExtinctError(Exception):
    """Raised when a second extinction broadcast is attempted for the same species."""


# ---------------------------------------------------------------------------
# LW-001 · SpeciesPopRecord
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class SpeciesPopRecord:
    species_id: str
    global_count: int
    local_counts: dict[str, int]   # chunk_id → count
    is_extinct: bool = False


# ---------------------------------------------------------------------------
# LW-004 · WorldChunk · WorldGenerationSeed
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class WorldChunk:
    chunk_id: str
    biome: "Biome"
    adjacent_chunks: tuple[str, ...]
    local_populations: dict[str, int]   # species_id → count
    carrying_capacity: dict[str, int]   # species_id → max sustainable


@dataclass(slots=True)
class WorldGenerationSeed:
    seed: int
    biome_distribution: dict[str, float]   # Biome.name → fraction; must sum to 1.0


# Type alias used throughout the world-sim subsystem.
PopulationLedger = dict[str, SpeciesPopRecord]


# ---------------------------------------------------------------------------
# LW-012 · Global Population Initializer
# ---------------------------------------------------------------------------

def initialize_world_populations(
    world_chunks: list[WorldChunk],
    species_registry: dict[str, "SpeciesBiomeBinding"],
    seed: WorldGenerationSeed,
) -> PopulationLedger:
    """Distribute each species' population across biome-matching chunks.

    Species whose primary biomes are absent from the world receive
    global_count=0 and is_extinct=True immediately — permanent, no undo.
    Writes result to the returned PopulationLedger.
    """
    from src.world_sim.biome import apply_biome_strictness

    ledger: PopulationLedger = {}
    world_biomes = {chunk.biome for chunk in world_chunks}
    zeroed: list[str] = []

    for species_id, binding in species_registry.items():
        if not apply_biome_strictness(binding, world_biomes):
            ledger[species_id] = SpeciesPopRecord(
                species_id=species_id,
                global_count=0,
                local_counts={},
                is_extinct=True,
            )
            zeroed.append(species_id)
            continue

        matching = [c for c in world_chunks if c.biome in binding.primary_biomes]
        pop_base: int = getattr(binding, "population_base", 100)

        if not matching:
            ledger[species_id] = SpeciesPopRecord(
                species_id=species_id, global_count=0, local_counts={}, is_extinct=True
            )
            zeroed.append(species_id)
            continue

        per_chunk, remainder = divmod(pop_base, len(matching))
        local_counts: dict[str, int] = {}
        for i, chunk in enumerate(matching):
            local_counts[chunk.chunk_id] = per_chunk + (1 if i < remainder else 0)

        ledger[species_id] = SpeciesPopRecord(
            species_id=species_id,
            global_count=sum(local_counts.values()),
            local_counts=local_counts,
        )

    if zeroed:
        _log.warning(
            "World-gen: %d species zeroed (no primary biome): %s", len(zeroed), zeroed
        )
    return ledger


# ---------------------------------------------------------------------------
# LW-014 · Population Delta
# ---------------------------------------------------------------------------

def apply_population_delta(
    ledger: PopulationLedger,
    species_id: str,
    chunk_id: str,
    delta: int,
) -> SpeciesPopRecord:
    """Apply delta (positive=birth/in, negative=kill/out) to a chunk population.

    Clamps local count to ≥ 0.  If global_count reaches 0, sets is_extinct=True
    permanently — one-way gate with no undo path.
    Raises SpeciesExtinctError if called on an already-extinct species.
    """
    record = ledger.get(species_id)
    if record is None:
        count = max(0, delta)
        record = SpeciesPopRecord(
            species_id=species_id,
            global_count=count,
            local_counts={chunk_id: count},
        )
        ledger[species_id] = record
        return record

    if record.is_extinct:
        raise SpeciesExtinctError(
            f"Species '{species_id}' is extinct — cannot modify population."
        )

    current = record.local_counts.get(chunk_id, 0)
    record.local_counts[chunk_id] = max(0, current + delta)
    record.global_count = sum(record.local_counts.values())

    if record.global_count == 0:
        record.is_extinct = True   # one-way gate

    return record


# ---------------------------------------------------------------------------
# LW-035 · Extinction Broadcaster
# ---------------------------------------------------------------------------

class ExtinctionCause(enum.Enum):
    PlayerKills       = "player_kills"
    MigrationCollapse = "migration_collapse"
    BiomeLoss         = "biome_loss"
    StarvationCycle   = "starvation_cycle"
    WorldGenZeroed    = "world_gen_zeroed"


@dataclass(slots=True)
class ExtinctionEvent:
    species_id: str
    last_known_chunk: str
    world_tick: int
    cause: ExtinctionCause


# Module-level idempotency lock — never resets within a world instance.
_EXTINCT_BROADCAST: set[str] = set()


def broadcast_extinction(
    species_id: str,
    ledger: PopulationLedger,
    event_bus: "EventBus",
    tick: int,
    cause: ExtinctionCause = ExtinctionCause.MigrationCollapse,
) -> ExtinctionEvent:
    """Fire a permanent, idempotent extinction event via EventBus.

    Raises AlreadyExtinctError on a second broadcast for the same species_id.
    Once fired, the species_id is locked out of apply_population_delta via is_extinct flag.
    """
    if species_id in _EXTINCT_BROADCAST:
        raise AlreadyExtinctError(
            f"Extinction already broadcast for species '{species_id}'."
        )

    record = ledger.get(species_id)
    last_chunk = (
        next(iter(record.local_counts), "unknown") if record else "unknown"
    )

    event = ExtinctionEvent(
        species_id=species_id,
        last_known_chunk=last_chunk,
        world_tick=tick,
        cause=cause,
    )
    _EXTINCT_BROADCAST.add(species_id)
    event_bus.publish("species_extinction", event)
    _log.info(
        "EXTINCTION tick=%d species=%s cause=%s last_chunk=%s",
        tick, species_id, cause.value, last_chunk,
    )
    return event
