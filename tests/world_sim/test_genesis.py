"""
tests/world_sim/test_genesis.py
--------------------------------
Unit tests for PH6-003 — fast_forward_simulation() headless tick engine.
"""
from __future__ import annotations

import pytest

from src.world_sim.genesis import (
    fast_forward_simulation,
    _serialise_chunk,
    _serialise_faction,
)


# ---------------------------------------------------------------------------
# fast_forward_simulation — output structure
# ---------------------------------------------------------------------------

class TestFastForwardSimulation:
    """Light smoke-tests that run a tiny simulation to keep the suite fast."""

    @pytest.fixture(scope="class")
    def result(self):
        # 1 year = 365 ticks — deterministic seed 1
        return fast_forward_simulation(years=1, seed=1)

    def test_returns_dict(self, result):
        assert isinstance(result, dict)

    def test_seed_key(self, result):
        assert result["seed"] == 1

    def test_years_simulated_key(self, result):
        assert result["years_simulated"] == 1

    def test_final_tick_is_365(self, result):
        assert result["final_tick"] == 365

    def test_chunks_is_list(self, result):
        assert isinstance(result["chunks"], list)

    def test_chunks_not_empty(self, result):
        assert len(result["chunks"]) > 0

    def test_chunk_has_required_keys(self, result):
        chunk = result["chunks"][0]
        for key in ("chunk_id", "biome", "adjacent_chunks", "local_populations", "carrying_capacity"):
            assert key in chunk, f"missing key {key!r} in chunk"

    def test_faction_records_is_list(self, result):
        assert isinstance(result["faction_records"], list)

    def test_faction_records_not_empty(self, result):
        assert len(result["faction_records"]) > 0

    def test_faction_has_required_keys(self, result):
        faction = result["faction_records"][0]
        for key in ("name", "alignment", "hostile_to"):
            assert key in faction, f"missing key {key!r} in faction"

    def test_deterministic_with_same_seed(self):
        r1 = fast_forward_simulation(years=1, seed=77)
        r2 = fast_forward_simulation(years=1, seed=77)
        # Same seed → same final tick, same chunk count
        assert r1["final_tick"] == r2["final_tick"]
        assert len(r1["chunks"]) == len(r2["chunks"])

    def test_different_seeds_may_differ(self):
        r1 = fast_forward_simulation(years=1, seed=1)
        r2 = fast_forward_simulation(years=1, seed=999)
        # Both valid; just confirm they complete without error
        assert r1["seed"] == 1
        assert r2["seed"] == 999

    def test_zero_years(self):
        result = fast_forward_simulation(years=0, seed=42)
        assert result["final_tick"] == 0
        assert result["years_simulated"] == 0


# ---------------------------------------------------------------------------
# _serialise_chunk helper
# ---------------------------------------------------------------------------

class TestSerialiseChunk:
    def test_returns_dict_with_keys(self):
        from src.world_sim.population import WorldChunk
        from src.world_sim.biome import Biome

        chunk = WorldChunk(
            chunk_id="c0",
            biome=Biome.Temperate_Forest,
            adjacent_chunks=("c1",),
            local_populations={"wolf": 10},
            carrying_capacity={"wolf": 100},
        )
        d = _serialise_chunk(chunk)
        assert d["chunk_id"] == "c0"
        assert "biome" in d
        assert d["adjacent_chunks"] == ["c1"]
        assert d["local_populations"] == {"wolf": 10}
        assert d["carrying_capacity"] == {"wolf": 100}


# ---------------------------------------------------------------------------
# _serialise_faction helper
# ---------------------------------------------------------------------------

class TestSerialiseFaction:
    def test_returns_dict_with_keys(self):
        from src.world_sim.factions import FactionRecord
        from src.rules_engine.character_35e import Alignment

        faction = FactionRecord(
            name="Test Guild",
            alignment=Alignment.LAWFUL_GOOD,
            hostile_to=["Bandits"],
        )
        d = _serialise_faction(faction)
        assert d["name"] == "Test Guild"
        assert "alignment" in d
        assert d["hostile_to"] == ["Bandits"]
