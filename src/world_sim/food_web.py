"""EM-001 · EM-002 · EM-007 — Trophic Level & Caloric Engine (Food Web subsystem)."""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.world_sim.population import PopulationLedger

# ---------------------------------------------------------------------------
# EM-001 · TrophicLevel enum and FoodWebEntry dataclass
# ---------------------------------------------------------------------------

class TrophicLevel(enum.Enum):
    """Ecological trophic level for a species."""
    Apex     = "Apex"
    Predator = "Predator"
    Prey     = "Prey"
    Producer = "Producer"


@dataclass(slots=True)
class FoodWebEntry:
    """Links a species to its trophic role and dietary tags.

    Attributes:
        species_id:    Matches SpeciesPopRecord.species_id.
        trophic_level: The ecological role of this species.
        diet_tags:     Free-form tags describing diet (e.g. ["herbivore", "grazer"]).
    """
    species_id:    str
    trophic_level: TrophicLevel
    diet_tags:     list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# EM-002 · Caloric Demand Formula
# ---------------------------------------------------------------------------

PREDATOR_PREY_RATIO_CONSTANT: float = 3.0


def calculate_chunk_starvation(
    ledger: "PopulationLedger",
    chunk_id: str,
    food_web_entries: list[FoodWebEntry],
    predator_ratio: float = PREDATOR_PREY_RATIO_CONSTANT,
) -> dict[str, int]:
    """Apply starvation deltas when predator population exceeds sustainable prey ratio.

    If the total Predator population in *chunk_id* exceeds
    (total Prey population / predator_ratio), each Predator species loses
    population proportionally to its share of total predators.

    Returns a dict mapping species_id → delta applied (always ≤ 0).
    An empty dict means no starvation occurred.
    """
    from src.world_sim.population import apply_population_delta

    predator_entries = [e for e in food_web_entries if e.trophic_level == TrophicLevel.Predator]
    prey_entries     = [e for e in food_web_entries if e.trophic_level == TrophicLevel.Prey]

    predator_pop = {
        e.species_id: ledger[e.species_id].local_counts.get(chunk_id, 0)
        for e in predator_entries
        if e.species_id in ledger and not ledger[e.species_id].is_extinct
    }
    prey_pop = {
        e.species_id: ledger[e.species_id].local_counts.get(chunk_id, 0)
        for e in prey_entries
        if e.species_id in ledger and not ledger[e.species_id].is_extinct
    }

    total_predators = sum(predator_pop.values())
    total_prey      = sum(prey_pop.values())

    deltas: dict[str, int] = {}

    if predator_ratio <= 0 or total_predators == 0:
        return deltas

    sustainable = total_prey / predator_ratio
    if total_predators <= sustainable:
        return deltas

    # Over-carrying-capacity — reduce predators proportionally
    excess = total_predators - sustainable
    for species_id, pop in predator_pop.items():
        if pop == 0:
            continue
        share   = pop / total_predators
        penalty = -max(1, int(excess * share))
        apply_population_delta(ledger, species_id, chunk_id, penalty)
        deltas[species_id] = penalty

    return deltas


# ---------------------------------------------------------------------------
# EM-007 · Resource Depletion
# ---------------------------------------------------------------------------

def degrade_biome_quality(
    chunk_id: str,
    food_web_entries: list[FoodWebEntry],
    ledger: "PopulationLedger",
    prey_overpopulation_threshold: int = 500,
) -> dict:
    """Compute biome quality degradation caused by Prey overpopulation.

    Returns a dict with keys:
        "chunk_id"      — the chunk evaluated.
        "prey_count"    — total Prey population in the chunk.
        "quality_delta" — negative int representing degradation (0 if none).
    """
    prey_entries = [e for e in food_web_entries if e.trophic_level == TrophicLevel.Prey]
    prey_count = sum(
        ledger[e.species_id].local_counts.get(chunk_id, 0)
        for e in prey_entries
        if e.species_id in ledger and not ledger[e.species_id].is_extinct
    )

    quality_delta = 0
    if prey_count > prey_overpopulation_threshold:
        quality_delta = -(prey_count // prey_overpopulation_threshold)

    return {
        "chunk_id":      chunk_id,
        "prey_count":    prey_count,
        "quality_delta": quality_delta,
    }
