"""LW-036 — World tick orchestrator: canonical simulation loop."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.world_sim.biome import SpeciesBiomeBinding
    from src.world_sim.population import PopulationLedger, WorldChunk
    from src.world_sim.migration import MigrationVector
    from src.ai_sim.llm_bridge import LLMClient
    from src.core.event_bus import EventBus

_log = logging.getLogger(__name__)


@dataclass
class WorldState:
    """Mutable snapshot of the living world threaded through every tick."""
    world_chunks: list["WorldChunk"]
    ledger: "PopulationLedger"
    species_registry: dict[str, "SpeciesBiomeBinding"]
    pending_vectors: list["MigrationVector"] = field(default_factory=list)
    event_bus: "EventBus | None" = None
    tick: int = 0


def run_world_tick(
    world_state: WorldState,
    tick: int,
    rng,
    llm_client: "LLMClient",
) -> WorldState:
    """Execute one world tick — steps 1–4 are synchronous; step 5 fires async lore tasks.

    1. Process births via biome-capacity birth-rate formula for each non-extinct species.
    2. Generate migration vectors for all species.
    3. Apply all due migration vectors.
    4. Check all species for global_count == 0 → broadcast_extinction.
    5. For each spawn this tick, resolve anomaly roll; fire lore hook async on hit.

    Returns the updated WorldState.
    """
    from src.world_sim.population import (
        apply_population_delta,
        broadcast_extinction,
        ExtinctionCause,
        AlreadyExtinctError,
    )
    from src.world_sim.migration import (
        ChunkAdjacencyGraph,
        generate_migration_vectors,
        apply_migration_vectors,
    )
    from src.world_sim.anomaly import resolve_anomaly_roll, request_anomaly_lore

    world_state.tick = tick

    # Step 1 — Births
    _process_births(world_state, rng)

    # Step 2 — Generate migration vectors for every species
    graph = ChunkAdjacencyGraph(world_state.world_chunks)
    for species_id in list(world_state.species_registry):
        new_vecs = generate_migration_vectors(
            species_id,
            world_state.world_chunks,
            world_state.ledger,
            graph,
            world_state.species_registry,
            tick,
            rng,
        )
        world_state.pending_vectors.extend(new_vecs)

    # Step 3 — Apply due vectors; prune spent ones
    apply_migration_vectors(
        world_state.pending_vectors,
        world_state.ledger,
        world_state.world_chunks,
        tick,
    )
    world_state.pending_vectors = [
        v for v in world_state.pending_vectors if v.scheduled_tick > tick
    ]

    # Step 4 — Extinction check (synchronous, idempotent)
    if world_state.event_bus is not None:
        for species_id, record in list(world_state.ledger.items()):
            if record.global_count == 0 and not record.is_extinct:
                try:
                    broadcast_extinction(
                        species_id,
                        world_state.ledger,
                        world_state.event_bus,
                        tick,
                        cause=ExtinctionCause.MigrationCollapse,
                    )
                except AlreadyExtinctError:
                    pass

    # Step 5 — Anomaly lore (fire-and-forget; does not block tick return)
    _trigger_anomaly_lore_tasks(world_state, tick, llm_client, rng)

    # Step 6 — PH5-009: Apply weather debuffs to each chunk's entity metadata.
    _apply_weather_debuffs(world_state)

    return world_state


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _process_births(world_state: WorldState, rng) -> None:
    """Apply a simple 1 % per-tick birth rate per chunk, capped at carrying capacity."""
    from src.world_sim.population import apply_population_delta, SpeciesExtinctError

    for chunk in world_state.world_chunks:
        for species_id in list(chunk.local_populations):
            record = world_state.ledger.get(species_id)
            if record is None or record.is_extinct:
                continue

            local_count = chunk.local_populations.get(species_id, 0)
            if local_count == 0:
                continue

            cap = chunk.carrying_capacity.get(species_id, 0)
            if cap == 0 or local_count >= cap:
                continue

            binding = world_state.species_registry.get(species_id)
            birth_rate = 0.01
            if binding and chunk.biome in binding.tolerated_biomes and chunk.biome not in binding.primary_biomes:
                birth_rate = 0.005   # tolerated biome → halved birth rate

            births = int(local_count * birth_rate)
            if births < 1 and rng.random() < birth_rate:
                births = 1

            if births > 0:
                try:
                    apply_population_delta(world_state.ledger, species_id, chunk.chunk_id, births)
                    chunk.local_populations[species_id] = (
                        chunk.local_populations.get(species_id, 0) + births
                    )
                except SpeciesExtinctError:
                    pass


def _trigger_anomaly_lore_tasks(
    world_state: WorldState,
    tick: int,
    llm_client: "LLMClient",
    rng,
) -> None:
    """Resolve anomaly rolls for all populated chunks this tick; schedule lore async."""
    from src.world_sim.anomaly import resolve_anomaly_roll, request_anomaly_lore

    for chunk in world_state.world_chunks:
        for species_id in list(chunk.local_populations):
            binding = world_state.species_registry.get(species_id)
            if binding is None:
                continue

            entity_id = f"{species_id}_{chunk.chunk_id}_{tick}"
            anomaly = resolve_anomaly_roll(rng, species_id, entity_id, binding, chunk, tick)
            if anomaly is not None:
                notes: str | None = None
                try:
                    loop = asyncio.get_event_loop()
                    loop.create_task(request_anomaly_lore(anomaly, llm_client, notes))
                except RuntimeError:
                    pass   # no running event loop in sync context — lore skipped


def _apply_weather_debuffs(world_state: WorldState) -> None:
    """PH5-009: Apply weather debuffs to each chunk's entity_metadata dict.

    Iterates every :class:`~src.world_sim.population.WorldChunk` that carries
    a ``weather_state`` attribute (a :class:`~src.world_sim.chronos.WeatherState`).
    For each such chunk, calls
    :func:`~src.world_sim.chronos.apply_weather_debuffs` on the chunk's
    ``entity_metadata`` dict.

    Args:
        world_state: The current :class:`WorldState`.
    """
    try:
        from src.world_sim.chronos import apply_weather_debuffs
    except ImportError:
        return

    for chunk in world_state.world_chunks:
        weather = getattr(chunk, "weather_state", None)
        if weather is None:
            continue
        entity_metadata = getattr(chunk, "entity_metadata", None)
        if entity_metadata is None:
            continue
        try:
            apply_weather_debuffs(entity_metadata, weather)
        except Exception:  # noqa: BLE001
            pass
