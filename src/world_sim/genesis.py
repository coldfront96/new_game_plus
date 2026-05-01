"""
src/world_sim/genesis.py
-------------------------
PH6-003 — Genesis Protocol: headless world-history simulation engine.

``fast_forward_simulation`` creates a minimal ``WorldState``, seeds it with
several representative biome chunks and species registrations, then drives the
``run_world_tick`` loop for the requested number of simulated years at maximum
CPU speed — no asyncio sleep, no Textual screen, no AnimationRenderer.

The function is deliberately **headless-only**:

* No ``textual`` imports.
* No ``Static`` widget.
* No ``AnimationRenderer``.

Usage::

    from src.world_sim.genesis import fast_forward_simulation

    result = fast_forward_simulation(years=500, seed=42)
    print(result["years_simulated"])   # 500
    print(result["final_tick"])        # 182500
    print(len(result["chunks"]))       # number of world chunks
"""

from __future__ import annotations

import random
from typing import Any

# ---------------------------------------------------------------------------
# Seed biomes used when bootstrapping the world
# ---------------------------------------------------------------------------

_SEED_BIOMES = [
    "Temperate_Forest",
    "Temperate_Plain",
    "Cold_Mountain",
    "Warm_Desert",
    "Temperate_Aquatic",
    "Underground",
    "Warm_Forest",
    "Cold_Forest",
]

# Seed species mapped to their primary biome name
_SEED_SPECIES: list[tuple[str, str]] = [
    ("wolf",      "Temperate_Forest"),
    ("goblin",    "Temperate_Forest"),
    ("orc",       "Cold_Mountain"),
    ("dragon",    "Warm_Desert"),
    ("merfolk",   "Temperate_Aquatic"),
    ("myconid",   "Underground"),
    ("tiger",     "Warm_Forest"),
    ("polar_bear","Cold_Forest"),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fast_forward_simulation(years: int, seed: int) -> dict:
    """Headless world-history simulation.

    Drives the ``run_world_tick`` loop ``years × 365`` times using a
    deterministic ``random.Random`` seeded with *seed*.  No UI widgets,
    Textual imports, or asyncio throttling are used.

    Args:
        years: Number of in-world years to simulate (each year = 365 ticks).
        seed:  RNG seed that determines the world layout and all random events.

    Returns:
        Plain ``dict`` with keys:

        * ``"seed"``             — the *seed* argument.
        * ``"years_simulated"``  — the *years* argument.
        * ``"final_tick"``       — last tick executed (``years × 365``).
        * ``"chunks"``           — list of serialised
                                   :class:`~src.world_sim.population.WorldChunk`
                                   dicts.
        * ``"faction_records"``  — list of serialised
                                   :class:`~src.world_sim.factions.FactionRecord`
                                   dicts.
    """
    from src.world_sim.population import WorldChunk, SpeciesPopRecord
    from src.world_sim.biome import Biome, SpeciesBiomeBinding
    from src.world_sim.factions import DEFAULT_FACTIONS
    from src.world_sim.world_tick import WorldState, run_world_tick

    rng = random.Random(seed)

    # ------------------------------------------------------------------
    # Build initial WorldChunks
    # ------------------------------------------------------------------
    chunks: list[WorldChunk] = []
    biome_names = _SEED_BIOMES[:]
    rng.shuffle(biome_names)

    for i, biome_name in enumerate(biome_names):
        try:
            biome = Biome[biome_name]
        except KeyError:
            biome = Biome.Temperate_Forest

        # Simple adjacency: each chunk is adjacent to the next and previous
        adj_ids = tuple(
            filter(None, [
                f"chunk_{i - 1}" if i > 0 else None,
                f"chunk_{i + 1}" if i < len(biome_names) - 1 else None,
            ])
        )

        chunks.append(
            WorldChunk(
                chunk_id=f"chunk_{i}",
                biome=biome,
                adjacent_chunks=adj_ids,
                local_populations={},
                carrying_capacity={},
            )
        )

    # ------------------------------------------------------------------
    # Build species registry and initial ledger
    # ------------------------------------------------------------------
    species_registry: dict[str, SpeciesBiomeBinding] = {}
    ledger: dict[str, SpeciesPopRecord] = {}

    for species_id, primary_biome_name in _SEED_SPECIES:
        try:
            primary_biome = Biome[primary_biome_name]
        except KeyError:
            primary_biome = Biome.Temperate_Forest

        binding = SpeciesBiomeBinding(
            species_id=species_id,
            primary_biomes=(primary_biome,),
            tolerated_biomes=(Biome.Any,),
            forbidden_biomes=(),
            population_base=rng.randint(50, 200),
        )
        species_registry[species_id] = binding

        # Seed initial populations into matching chunks
        local_counts: dict[str, int] = {}
        for chunk in chunks:
            if chunk.biome == primary_biome:
                initial_pop = rng.randint(10, 50)
                chunk.local_populations[species_id] = initial_pop
                chunk.carrying_capacity[species_id] = rng.randint(100, 500)
                local_counts[chunk.chunk_id] = initial_pop

        ledger[species_id] = SpeciesPopRecord(
            species_id=species_id,
            global_count=sum(local_counts.values()),
            local_counts=local_counts,
        )

    # ------------------------------------------------------------------
    # Build WorldState and run tick loop
    # ------------------------------------------------------------------
    world_state = WorldState(
        world_chunks=chunks,
        ledger=ledger,
        species_registry=species_registry,
        pending_vectors=[],
        event_bus=None,
        tick=0,
    )

    total_ticks = years * 365

    for tick in range(total_ticks):
        world_state = run_world_tick(
            world_state=world_state,
            tick=tick,
            rng=rng,
            llm_client=None,   # headless — no LLM calls
        )

    # ------------------------------------------------------------------
    # Serialise result
    # ------------------------------------------------------------------
    serialised_chunks = [_serialise_chunk(c) for c in world_state.world_chunks]
    serialised_factions = [_serialise_faction(f) for f in DEFAULT_FACTIONS]

    return {
        "seed": seed,
        "years_simulated": years,
        "final_tick": total_ticks,
        "chunks": serialised_chunks,
        "faction_records": serialised_factions,
    }


# ---------------------------------------------------------------------------
# Internal serialisation helpers
# ---------------------------------------------------------------------------

def _serialise_chunk(chunk: Any) -> dict:
    """Convert a :class:`~src.world_sim.population.WorldChunk` to a plain dict."""
    return {
        "chunk_id": chunk.chunk_id,
        "biome": chunk.biome.value if hasattr(chunk.biome, "value") else str(chunk.biome),
        "adjacent_chunks": list(chunk.adjacent_chunks),
        "local_populations": dict(chunk.local_populations),
        "carrying_capacity": dict(chunk.carrying_capacity),
    }


def _serialise_faction(faction: Any) -> dict:
    """Convert a :class:`~src.world_sim.factions.FactionRecord` to a plain dict."""
    return {
        "name": faction.name,
        "alignment": faction.alignment.value if hasattr(faction.alignment, "value") else str(faction.alignment),
        "hostile_to": list(faction.hostile_to),
    }
