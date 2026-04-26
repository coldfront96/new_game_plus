"""LW-005 · LW-021 · LW-022 · LW-023 · LW-024 — Migration vectors and chunk adjacency graph."""
from __future__ import annotations

import enum
import logging
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.world_sim.biome import Biome, SpeciesBiomeBinding
    from src.world_sim.population import PopulationLedger, WorldChunk

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LW-005 · Migration schemas
# ---------------------------------------------------------------------------

class MigrationCause(enum.Enum):
    PopulationPressure = "population_pressure"
    BiomeRestored      = "biome_restored"
    PredatorFlight     = "predator_flight"
    DroughtFamine      = "drought_famine"
    AnomalyFlight      = "anomaly_flight"


@dataclass(slots=True)
class MigrationVector:
    """Immutable once created — cancel by filtering, never mutating."""
    species_id: str
    source_chunk_id: str
    target_chunk_id: str
    migrating_count: int
    scheduled_tick: int
    cause: MigrationCause


# ---------------------------------------------------------------------------
# LW-021 · Chunk Adjacency Graph
# ---------------------------------------------------------------------------

class ChunkAdjacencyGraph:
    """BFS adjacency graph built from WorldChunk.adjacent_chunks at world-load time."""

    def __init__(self, world_chunks: list["WorldChunk"]) -> None:
        self._chunks: dict[str, "WorldChunk"] = {c.chunk_id: c for c in world_chunks}

    def get_neighbors(self, chunk_id: str) -> list["WorldChunk"]:
        chunk = self._chunks.get(chunk_id)
        if chunk is None:
            return []
        return [self._chunks[adj] for adj in chunk.adjacent_chunks if adj in self._chunks]

    def biome_reachable_in_steps(
        self,
        chunk_id: str,
        target_biome: "Biome",
        max_steps: int,
    ) -> list[str]:
        """BFS: return chunk_ids of the given biome reachable within max_steps hops."""
        visited: set[str] = {chunk_id}
        frontier: list[str] = [chunk_id]
        results: list[str] = []
        for _ in range(max_steps):
            next_frontier: list[str] = []
            for cid in frontier:
                for neighbor in self.get_neighbors(cid):
                    if neighbor.chunk_id not in visited:
                        visited.add(neighbor.chunk_id)
                        next_frontier.append(neighbor.chunk_id)
                        if neighbor.biome == target_biome:
                            results.append(neighbor.chunk_id)
            frontier = next_frontier
            if not frontier:
                break
        return results


# ---------------------------------------------------------------------------
# LW-022 · Migration Pressure Calculator
# ---------------------------------------------------------------------------

def calculate_migration_pressure(
    species_id: str,
    chunk: "WorldChunk",
    ledger: "PopulationLedger",
) -> float:
    """Return signed pressure float for a species in a chunk.

    > 0  → overpopulation (push outward migration).
    < 0  → underpopulation (pull inward migration).
    0    → at carrying capacity.
    """
    local_count = chunk.local_populations.get(species_id, 0)
    cap = chunk.carrying_capacity.get(species_id)
    if cap is None or cap == 0:
        return 0.0
    return (local_count / cap) - 1.0


# ---------------------------------------------------------------------------
# LW-023 · Migration Vector Generator
# ---------------------------------------------------------------------------

def generate_migration_vectors(
    species_id: str,
    world: list["WorldChunk"],
    ledger: "PopulationLedger",
    graph: ChunkAdjacencyGraph,
    bindings: dict[str, "SpeciesBiomeBinding"],
    current_tick: int,
    rng,
) -> list[MigrationVector]:
    """Generate outbound migration vectors for a single species this tick.

    Vectors are returned but NOT applied — call apply_migration_vectors separately.
    Skips extinct species.  Selects the lowest-pressure compatible adjacent chunk.
    """
    record = ledger.get(species_id)
    if record is None or record.is_extinct:
        return []

    binding = bindings.get(species_id)
    if binding is None:
        return []

    from src.world_sim.biome import Biome
    allowed_biomes = set(binding.primary_biomes) | set(binding.tolerated_biomes)
    vectors: list[MigrationVector] = []

    for chunk in world:
        pressure = calculate_migration_pressure(species_id, chunk, ledger)
        if pressure <= 0:
            continue

        neighbors = graph.get_neighbors(chunk.chunk_id)
        compatible = [
            n for n in neighbors
            if (Biome.Any in allowed_biomes or n.biome in allowed_biomes)
            and n.biome not in binding.forbidden_biomes
        ]
        if not compatible:
            continue

        target = min(
            compatible,
            key=lambda n: calculate_migration_pressure(species_id, n, ledger),
        )

        local_count = chunk.local_populations.get(species_id, 0)
        migrating_count = max(1, math.ceil(pressure * 0.1 * local_count))
        delay = rng.randint(1, 4)

        vectors.append(MigrationVector(
            species_id=species_id,
            source_chunk_id=chunk.chunk_id,
            target_chunk_id=target.chunk_id,
            migrating_count=migrating_count,
            scheduled_tick=current_tick + delay,
            cause=MigrationCause.PopulationPressure,
        ))

    return vectors


# ---------------------------------------------------------------------------
# LW-024 · Migration Vector Applier
# ---------------------------------------------------------------------------

def apply_migration_vectors(
    vectors: list[MigrationVector],
    ledger: "PopulationLedger",
    world_chunks: list["WorldChunk"],
    current_tick: int,
) -> "PopulationLedger":
    """Apply all due vectors (scheduled_tick <= current_tick) to the ledger.

    Silently skips any vector whose source chunk no longer has sufficient population.
    """
    from src.world_sim.population import apply_population_delta

    chunk_map = {c.chunk_id: c for c in world_chunks}

    for v in vectors:
        if v.scheduled_tick > current_tick:
            continue

        source_chunk = chunk_map.get(v.source_chunk_id)
        if source_chunk is None:
            continue

        actual_local = source_chunk.local_populations.get(v.species_id, 0)
        if actual_local < v.migrating_count:
            continue   # not enough in source — skip silently

        apply_population_delta(ledger, v.species_id, v.source_chunk_id, -v.migrating_count)
        apply_population_delta(ledger, v.species_id, v.target_chunk_id, +v.migrating_count)

        # Keep WorldChunk.local_populations in sync with ledger
        source_chunk.local_populations[v.species_id] = max(
            0, source_chunk.local_populations.get(v.species_id, 0) - v.migrating_count
        )
        target_chunk = chunk_map.get(v.target_chunk_id)
        if target_chunk is not None:
            target_chunk.local_populations[v.species_id] = (
                target_chunk.local_populations.get(v.species_id, 0) + v.migrating_count
            )

        _log.debug(
            "Migration tick=%d %s: %d %s → %s",
            current_tick, v.species_id, v.migrating_count,
            v.source_chunk_id, v.target_chunk_id,
        )

    return ledger
