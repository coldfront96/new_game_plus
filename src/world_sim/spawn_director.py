"""LW-043 — SpawnDirector: single authoritative spawn/death gateway for the living world."""
from __future__ import annotations

import enum
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.world_sim.biome import SpeciesBiomeBinding
    from src.world_sim.population import PopulationLedger, WorldChunk
    from src.world_sim.anomaly import AnomalyRecord
    from src.ai_sim.llm_bridge import LLMClient

_log = logging.getLogger(__name__)


class SpawnResult(enum.Enum):
    Spawned        = "spawned"
    Blocked_Biome  = "blocked_biome"
    Extinct        = "extinct"
    CapacityFull   = "capacity_full"
    AnomalySpawned = "anomaly_spawned"


@dataclass
class SpawnDirector:
    """Consults the PopulationLedger on every spawn and death event.

    This is the single authoritative gateway — no other code may create or
    destroy entities without going through request_spawn / notify_death.
    """
    ledger: "PopulationLedger"
    bindings: dict[str, "SpeciesBiomeBinding"]
    world_chunks: list["WorldChunk"]

    def request_spawn(
        self,
        species_id: str,
        chunk_id: str,
        entity_id: str,
        rng,
        llm_client: "LLMClient | None" = None,
        anomaly_threshold: float = 0.005,
    ) -> tuple[SpawnResult, "AnomalyRecord | None"]:
        """Attempt to spawn one entity of species_id in chunk_id.

        Sequence:
        1. can_spawn_in_chunk gate — return Blocked_Biome or Extinct on failure.
        2. Gate passed → apply_population_delta(ledger, species_id, chunk_id, -1).
        3. resolve_anomaly_roll — if anomaly, fire lore hook async and return AnomalySpawned.
        4. Return (Spawned, None) on a normal spawn.

        Returns (result, anomaly_record_or_None).
        """
        from src.world_sim.biome import can_spawn_in_chunk
        from src.world_sim.population import apply_population_delta, SpeciesExtinctError
        from src.world_sim.anomaly import resolve_anomaly_roll, request_anomaly_lore
        import asyncio

        chunk = self._chunk(chunk_id)
        if chunk is None:
            _log.warning("SpawnDirector: unknown chunk_id '%s'", chunk_id)
            return SpawnResult.Blocked_Biome, None

        record = self.ledger.get(species_id)
        if record is not None and record.is_extinct:
            return SpawnResult.Extinct, None

        if not can_spawn_in_chunk(species_id, chunk, self.ledger, self.bindings):
            # Distinguish capacity-full from biome mismatch
            binding = self.bindings.get(species_id)
            cap = chunk.carrying_capacity.get(species_id)
            local = chunk.local_populations.get(species_id, 0)
            if cap is not None and local >= cap:
                return SpawnResult.CapacityFull, None
            return SpawnResult.Blocked_Biome, None

        # Decrement world population
        try:
            apply_population_delta(self.ledger, species_id, chunk_id, -1)
        except SpeciesExtinctError:
            return SpawnResult.Extinct, None

        # Keep chunk.local_populations in sync
        chunk.local_populations[species_id] = max(
            0, chunk.local_populations.get(species_id, 0) - 1
        )

        # Anomaly roll
        binding = self.bindings.get(species_id)
        anomaly: AnomalyRecord | None = None
        if binding is not None:
            anomaly = resolve_anomaly_roll(
                rng, species_id, entity_id, binding, chunk,
                world_tick=0, threshold=anomaly_threshold,
            )
            if anomaly is not None and llm_client is not None:
                notes = getattr(binding, "ecology_notes", None)
                try:
                    loop = asyncio.get_event_loop()
                    loop.create_task(request_anomaly_lore(anomaly, llm_client, notes))
                except RuntimeError:
                    pass
                return SpawnResult.AnomalySpawned, anomaly

        return SpawnResult.Spawned, anomaly

    def notify_death(
        self,
        species_id: str,
        chunk_id: str,
        permanent: bool = True,
    ) -> None:
        """Notify the ledger that an entity has died.

        permanent=True  → decrement global population (entity is gone forever).
        permanent=False → entity will respawn elsewhere; no population change.
        """
        from src.world_sim.population import apply_population_delta, SpeciesExtinctError

        if not permanent:
            return

        chunk = self._chunk(chunk_id)
        if chunk is None:
            return

        try:
            apply_population_delta(self.ledger, species_id, chunk_id, -1)
            chunk.local_populations[species_id] = max(
                0, chunk.local_populations.get(species_id, 0) - 1
            )
            _log.debug("Death: species=%s chunk=%s", species_id, chunk_id)
        except SpeciesExtinctError:
            pass  # already extinct — nothing to decrement

    def _chunk(self, chunk_id: str) -> "WorldChunk | None":
        for c in self.world_chunks:
            if c.chunk_id == chunk_id:
                return c
        return None
