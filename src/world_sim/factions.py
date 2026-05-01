"""EM-004 · EM-006 · EM-009 — Sociopolitical Entity Grouping (Factions subsystem)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src.rules_engine.character_35e import Alignment

if TYPE_CHECKING:
    from src.world_sim.population import PopulationLedger
    from src.ai_sim.llm_bridge import LLMClient


# ---------------------------------------------------------------------------
# EM-004 · FactionRecord dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class FactionRecord:
    """A named sociopolitical faction with alignment and enemy list.

    Attributes:
        name:       Human-readable faction name.
        alignment:  D&D 3.5e alignment of the faction as a whole.
        hostile_to: Names of other factions this faction is hostile toward.
    """
    name:       str
    alignment:  Alignment
    hostile_to: list[str] = field(default_factory=list)


# Default warband assignments for common monster factions.
DEFAULT_FACTIONS: list[FactionRecord] = [
    FactionRecord(
        name="Orc Warband",
        alignment=Alignment.CHAOTIC_EVIL,
        hostile_to=["Goblin Warband", "Human Settlement"],
    ),
    FactionRecord(
        name="Goblin Warband",
        alignment=Alignment.NEUTRAL_EVIL,
        hostile_to=["Orc Warband", "Human Settlement"],
    ),
    FactionRecord(
        name="Human Settlement",
        alignment=Alignment.LAWFUL_NEUTRAL,
        hostile_to=["Orc Warband", "Goblin Warband"],
    ),
]


# ---------------------------------------------------------------------------
# EM-004 · Hostility check
# ---------------------------------------------------------------------------

def are_hostile(faction_a: FactionRecord, faction_b: FactionRecord) -> bool:
    """Return True if either faction considers the other an enemy."""
    return (
        faction_b.name in faction_a.hostile_to
        or faction_a.name in faction_b.hostile_to
    )


# ---------------------------------------------------------------------------
# EM-006 · Migration War Trigger
# ---------------------------------------------------------------------------

def resolve_migration_conflict(
    chunk_populations: dict[str, str],
    factions: list[FactionRecord],
    ledger: "PopulationLedger",
    chunk_id: str,
) -> list[dict]:
    """Resolve armed conflicts between hostile factions sharing a chunk.

    Casualty model:
        - Smaller force loses 30 % of the larger force's count.
        - Larger force loses 20 % of the smaller force's count.

    Args:
        chunk_populations: Maps faction_name → species_id for factions present.
        factions:          All known FactionRecord objects.
        ledger:            Population ledger to apply deltas against.
        chunk_id:          The chunk in which conflicts are resolved.

    Returns:
        A list of conflict result dicts, one per hostile pair found.
    """
    from src.world_sim.population import apply_population_delta

    faction_map = {f.name: f for f in factions}
    present_names = list(chunk_populations.keys())
    results: list[dict] = []

    for i in range(len(present_names)):
        for j in range(i + 1, len(present_names)):
            name_a = present_names[i]
            name_b = present_names[j]
            fa = faction_map.get(name_a)
            fb = faction_map.get(name_b)
            if fa is None or fb is None:
                continue
            if not are_hostile(fa, fb):
                continue

            species_a = chunk_populations[name_a]
            species_b = chunk_populations[name_b]
            rec_a = ledger.get(species_a)
            rec_b = ledger.get(species_b)
            pop_a = rec_a.local_counts.get(chunk_id, 0) if rec_a else 0
            pop_b = rec_b.local_counts.get(chunk_id, 0) if rec_b else 0

            if pop_a >= pop_b:
                larger_name, larger_sid, larger_pop = name_a, species_a, pop_a
                smaller_name, smaller_sid, smaller_pop = name_b, species_b, pop_b
            else:
                larger_name, larger_sid, larger_pop = name_b, species_b, pop_b
                smaller_name, smaller_sid, smaller_pop = name_a, species_a, pop_a

            smaller_losses = -max(1, int(larger_pop * 0.30))
            larger_losses  = -max(1, int(smaller_pop * 0.20))

            apply_population_delta(ledger, smaller_sid, chunk_id, smaller_losses)
            apply_population_delta(ledger, larger_sid,  chunk_id, larger_losses)

            results.append({
                "chunk_id":       chunk_id,
                "faction_a":      larger_name,
                "faction_b":      smaller_name,
                "faction_a_loss": larger_losses,
                "faction_b_loss": smaller_losses,
            })

    return results


# ---------------------------------------------------------------------------
# EM-009 · Faction Lore Generator
# ---------------------------------------------------------------------------

async def generate_faction_lore(
    faction_record: FactionRecord,
    population_count: int,
    llm_client: "LLMClient",
    growth_threshold: int = 100,
) -> str | None:
    """Use the LLM to forge a name and history for a faction that has grown large.

    Returns None if *population_count* is below *growth_threshold*.
    Otherwise queries the LLM for a short lore entry and returns its text.
    """
    if population_count < growth_threshold:
        return None

    system_prompt = (
        "You are a lore-master for a D&D 3.5e world. "
        "Generate a short, evocative name and a 2-3 sentence history for the faction described."
    )
    user_prompt = (
        f"Faction: {faction_record.name}\n"
        f"Alignment: {faction_record.alignment.value}\n"
        f"Enemies: {', '.join(faction_record.hostile_to) or 'none'}\n"
        f"Current population: {population_count}\n\n"
        "Provide a unique tribal/clan name and a brief origin story."
    )

    return await llm_client.query_text(system_prompt, user_prompt)
