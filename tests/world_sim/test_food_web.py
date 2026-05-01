"""Tests for EM-001 · EM-002 · EM-007 — food_web module."""
from __future__ import annotations

import pytest

from src.world_sim.food_web import (
    TrophicLevel,
    FoodWebEntry,
    PREDATOR_PREY_RATIO_CONSTANT,
    calculate_chunk_starvation,
    degrade_biome_quality,
)
from src.world_sim.population import SpeciesPopRecord, PopulationLedger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ledger(entries: dict[str, dict[str, int]]) -> PopulationLedger:
    """Build a minimal PopulationLedger from {species_id: {chunk_id: count}}."""
    ledger: PopulationLedger = {}
    for sid, local in entries.items():
        ledger[sid] = SpeciesPopRecord(
            species_id=sid,
            global_count=sum(local.values()),
            local_counts=dict(local),
        )
    return ledger


# ---------------------------------------------------------------------------
# EM-001 · TrophicLevel enum
# ---------------------------------------------------------------------------

class TestTrophicLevel:
    def test_enum_members_exist(self):
        assert TrophicLevel.Apex.value     == "Apex"
        assert TrophicLevel.Predator.value == "Predator"
        assert TrophicLevel.Prey.value     == "Prey"
        assert TrophicLevel.Producer.value == "Producer"

    def test_four_members(self):
        assert len(TrophicLevel) == 4


# ---------------------------------------------------------------------------
# EM-001 · FoodWebEntry dataclass
# ---------------------------------------------------------------------------

class TestFoodWebEntry:
    def test_creation_defaults(self):
        entry = FoodWebEntry(species_id="wolf", trophic_level=TrophicLevel.Predator)
        assert entry.species_id == "wolf"
        assert entry.trophic_level == TrophicLevel.Predator
        assert entry.diet_tags == []

    def test_creation_with_tags(self):
        entry = FoodWebEntry(
            species_id="deer",
            trophic_level=TrophicLevel.Prey,
            diet_tags=["herbivore", "grazer"],
        )
        assert "herbivore" in entry.diet_tags
        assert "grazer" in entry.diet_tags

    def test_slots_no_dict(self):
        entry = FoodWebEntry("rabbit", TrophicLevel.Prey)
        assert not hasattr(entry, "__dict__")


# ---------------------------------------------------------------------------
# EM-002 · calculate_chunk_starvation
# ---------------------------------------------------------------------------

CHUNK = "chunk_1"


class TestCalculateChunkStarvation:
    def _entries(self):
        return [
            FoodWebEntry("wolf",  TrophicLevel.Predator),
            FoodWebEntry("deer",  TrophicLevel.Prey),
            FoodWebEntry("rabbit", TrophicLevel.Prey),
        ]

    def test_no_starvation_when_prey_sufficient(self):
        """Predators well within ratio — no penalty."""
        ledger = _make_ledger({
            "wolf":   {CHUNK: 10},
            "deer":   {CHUNK: 100},
            "rabbit": {CHUNK: 100},
        })
        deltas = calculate_chunk_starvation(ledger, CHUNK, self._entries())
        assert deltas == {}

    def test_starvation_when_predators_exceed_ratio(self):
        """Predators far exceed prey/ratio — negative delta applied."""
        ledger = _make_ledger({
            "wolf":   {CHUNK: 900},   # 900 predators
            "deer":   {CHUNK: 100},   # only 100 prey → sustainable = 33
            "rabbit": {CHUNK: 0},
        })
        deltas = calculate_chunk_starvation(ledger, CHUNK, self._entries())
        assert "wolf" in deltas
        assert deltas["wolf"] < 0

    def test_starvation_reduces_ledger_count(self):
        """apply_population_delta is called — ledger count decreases."""
        ledger = _make_ledger({
            "wolf":   {CHUNK: 500},
            "deer":   {CHUNK: 50},
        })
        entries = [
            FoodWebEntry("wolf", TrophicLevel.Predator),
            FoodWebEntry("deer", TrophicLevel.Prey),
        ]
        before = ledger["wolf"].local_counts[CHUNK]
        calculate_chunk_starvation(ledger, CHUNK, entries)
        after = ledger["wolf"].local_counts.get(CHUNK, 0)
        assert after < before

    def test_no_predators_returns_empty(self):
        """No predator entries → no starvation."""
        ledger = _make_ledger({"deer": {CHUNK: 1000}})
        entries = [FoodWebEntry("deer", TrophicLevel.Prey)]
        assert calculate_chunk_starvation(ledger, CHUNK, entries) == {}

    def test_custom_ratio(self):
        """Custom predator_ratio changes threshold."""
        ledger = _make_ledger({
            "lion": {CHUNK: 6},
            "gnu":  {CHUNK: 10},
        })
        entries = [
            FoodWebEntry("lion", TrophicLevel.Predator),
            FoodWebEntry("gnu",  TrophicLevel.Prey),
        ]
        # With ratio=1.0 → sustainable = 10 predators; 6 < 10 → no starvation
        assert calculate_chunk_starvation(ledger, CHUNK, entries, predator_ratio=1.0) == {}
        # With ratio=0.5 → sustainable = 20; 6 < 20 → no starvation
        assert calculate_chunk_starvation(ledger, CHUNK, entries, predator_ratio=0.5) == {}
        # With ratio=5.0 → sustainable = 2; 6 > 2 → starvation
        deltas = calculate_chunk_starvation(ledger, CHUNK, entries, predator_ratio=5.0)
        assert "lion" in deltas


# ---------------------------------------------------------------------------
# EM-007 · degrade_biome_quality
# ---------------------------------------------------------------------------

class TestDegradeBiomeQuality:
    def test_below_threshold_no_degradation(self):
        ledger = _make_ledger({"deer": {CHUNK: 100}})
        entries = [FoodWebEntry("deer", TrophicLevel.Prey)]
        result = degrade_biome_quality(CHUNK, entries, ledger, prey_overpopulation_threshold=500)
        assert result["quality_delta"] == 0

    def test_above_threshold_negative_delta(self):
        ledger = _make_ledger({"deer": {CHUNK: 1500}})
        entries = [FoodWebEntry("deer", TrophicLevel.Prey)]
        result = degrade_biome_quality(CHUNK, entries, ledger, prey_overpopulation_threshold=500)
        assert result["quality_delta"] < 0
        assert result["quality_delta"] == -3   # 1500 // 500

    def test_result_contains_expected_keys(self):
        ledger = _make_ledger({"deer": {CHUNK: 200}})
        entries = [FoodWebEntry("deer", TrophicLevel.Prey)]
        result = degrade_biome_quality(CHUNK, entries, ledger)
        assert "chunk_id"      in result
        assert "prey_count"    in result
        assert "quality_delta" in result

    def test_prey_count_is_accurate(self):
        ledger = _make_ledger({
            "deer":   {CHUNK: 300},
            "rabbit": {CHUNK: 250},
        })
        entries = [
            FoodWebEntry("deer",   TrophicLevel.Prey),
            FoodWebEntry("rabbit", TrophicLevel.Prey),
        ]
        result = degrade_biome_quality(CHUNK, entries, ledger, prey_overpopulation_threshold=500)
        assert result["prey_count"] == 550
        assert result["quality_delta"] == -1   # 550 // 500
