"""LW-006 · LW-016 · LW-025 — Anomaly placement records, roll resolution, and LLMBridge lore hook."""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.world_sim.biome import Biome, SpeciesBiomeBinding
    from src.world_sim.population import WorldChunk
    from src.ai_sim.llm_bridge import LLMClient

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LW-006 · AnomalyRecord
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class AnomalyRecord:
    """Persisted immediately on creation; lore_text is None until LLM resolves."""
    anomaly_id: str
    entity_id: str
    species_id: str
    chunk_id: str
    native_biome: "Biome"
    current_biome: "Biome"
    anomaly_roll: float
    world_tick: int
    lore_text: str | None


# ---------------------------------------------------------------------------
# LW-016 · Anomaly Roll Resolver
# ---------------------------------------------------------------------------

def resolve_anomaly_roll(
    rng,
    species_id: str,
    entity_id: str,
    binding: "SpeciesBiomeBinding",
    chunk: "WorldChunk",
    world_tick: int,
    threshold: float = 0.005,
) -> "AnomalyRecord | None":
    """Draw a float in [0,1); return an AnomalyRecord if roll < threshold AND
    the chunk is outside the species' native biome.

    The anomaly spawn bypasses can_spawn_in_chunk exactly once.
    threshold is configurable per world-generation settings.
    Returns None if the roll misses or the entity is already in its native biome.
    """
    roll = rng.random()
    if roll >= threshold:
        return None

    native_biomes = set(binding.primary_biomes)
    if chunk.biome in native_biomes:
        return None   # in native biome — not an anomaly

    record = AnomalyRecord(
        anomaly_id=str(uuid.uuid4()),
        entity_id=entity_id,
        species_id=species_id,
        chunk_id=chunk.chunk_id,
        native_biome=next(iter(native_biomes)),
        current_biome=chunk.biome,
        anomaly_roll=roll,
        world_tick=world_tick,
        lore_text=None,
    )
    _log.info(
        "ANOMALY species=%s entity=%s biome=%s roll=%.6f",
        species_id, entity_id, chunk.biome.value, roll,
    )
    return record


# ---------------------------------------------------------------------------
# LW-025 · LLMBridge Anomaly Lore Hook
# ---------------------------------------------------------------------------

async def request_anomaly_lore(
    anomaly: AnomalyRecord,
    llm_client: "LLMClient",
    species_notes: str | None,
) -> AnomalyRecord:
    """Asynchronously generate permanent canon backstory lore for an out-of-biome anomaly.

    Dispatched as asyncio.create_task from the world tick — fires-and-forgets.
    World tick and combat continue unblocked while lore generates.
    On completion, writes the LLM response to anomaly.lore_text and persists the record.
    """
    from src.ai_sim.llm_bridge import CognitiveState

    system_prompt = (
        "You are the Lore Historian of a persistent fantasy world. "
        "Generate a single paragraph (3–5 sentences) of in-world historical backstory "
        "explaining why this creature is found outside its native biome. "
        "Be specific, evocative, and permanent — this becomes canon world history."
    )
    user_prompt = (
        f"Species: {anomaly.species_id}\n"
        f"Native biome: {anomaly.native_biome.value}\n"
        f"Current biome: {anomaly.current_biome.value}\n"
        f"World tick: {anomaly.world_tick}\n"
    )
    if species_notes:
        user_prompt += f"Ecology notes: {species_notes}\n"

    cognitive_state = CognitiveState(
        character_name=anomaly.species_id,
        char_class="creature",
        level=1,
        current_hp=1,
        max_hp=1,
        conditions=[],
        known_spells=[],
        action_tracker={},
        visible_entities=[],
        memory_log=[],
    )

    try:
        lore_text = await llm_client.query_model(system_prompt, cognitive_state, user_prompt)
        anomaly.lore_text = lore_text
        _log.info("Lore generated for anomaly %s", anomaly.anomaly_id)
    except Exception as exc:
        _log.warning("Anomaly lore generation failed for %s: %s", anomaly.anomaly_id, exc)

    return anomaly
