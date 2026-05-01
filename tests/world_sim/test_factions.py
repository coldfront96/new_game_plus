"""Tests for EM-004 · EM-006 · EM-009 — factions module."""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.rules_engine.character_35e import Alignment
from src.world_sim.factions import (
    FactionRecord,
    DEFAULT_FACTIONS,
    are_hostile,
    resolve_migration_conflict,
    generate_faction_lore,
)
from src.world_sim.population import SpeciesPopRecord, PopulationLedger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ledger(entries: dict[str, dict[str, int]]) -> PopulationLedger:
    ledger: PopulationLedger = {}
    for sid, local in entries.items():
        ledger[sid] = SpeciesPopRecord(
            species_id=sid,
            global_count=sum(local.values()),
            local_counts=dict(local),
        )
    return ledger


CHUNK = "chunk_A"


# ---------------------------------------------------------------------------
# EM-004 · FactionRecord
# ---------------------------------------------------------------------------

class TestFactionRecord:
    def test_creation(self):
        f = FactionRecord(
            name="Orc Warband",
            alignment=Alignment.CHAOTIC_EVIL,
            hostile_to=["Goblin Warband"],
        )
        assert f.name == "Orc Warband"
        assert f.alignment == Alignment.CHAOTIC_EVIL
        assert "Goblin Warband" in f.hostile_to

    def test_default_hostile_to_empty(self):
        f = FactionRecord(name="Peaceful Guild", alignment=Alignment.LAWFUL_GOOD)
        assert f.hostile_to == []

    def test_slots_no_dict(self):
        f = FactionRecord("Test", Alignment.TRUE_NEUTRAL)
        assert not hasattr(f, "__dict__")

    def test_default_factions_populated(self):
        assert len(DEFAULT_FACTIONS) >= 2
        names = {f.name for f in DEFAULT_FACTIONS}
        assert "Orc Warband"    in names
        assert "Goblin Warband" in names


# ---------------------------------------------------------------------------
# EM-004 · are_hostile
# ---------------------------------------------------------------------------

class TestAreHostile:
    def _orc(self):
        return FactionRecord("Orc Warband", Alignment.CHAOTIC_EVIL, ["Goblin Warband"])

    def _goblin(self):
        return FactionRecord("Goblin Warband", Alignment.NEUTRAL_EVIL, ["Orc Warband"])

    def _neutral(self):
        return FactionRecord("Druid Circle", Alignment.TRUE_NEUTRAL, [])

    def test_mutually_hostile(self):
        assert are_hostile(self._orc(), self._goblin()) is True

    def test_one_sided_hostility(self):
        orc = FactionRecord("Orc Warband", Alignment.CHAOTIC_EVIL, ["Human Settlement"])
        human = FactionRecord("Human Settlement", Alignment.LAWFUL_NEUTRAL, [])
        # Orc hates humans, but humans don't list orcs — still hostile
        assert are_hostile(orc, human) is True

    def test_not_hostile(self):
        assert are_hostile(self._neutral(), self._orc()) is False

    def test_same_faction_not_hostile_by_default(self):
        orc = self._orc()
        assert are_hostile(orc, orc) is False


# ---------------------------------------------------------------------------
# EM-006 · resolve_migration_conflict
# ---------------------------------------------------------------------------

class TestResolveMigrationConflict:
    def _factions(self):
        return [
            FactionRecord("Orc Warband",    Alignment.CHAOTIC_EVIL, ["Goblin Warband"]),
            FactionRecord("Goblin Warband", Alignment.NEUTRAL_EVIL, ["Orc Warband"]),
        ]

    def test_conflict_produces_casualties(self):
        chunk_populations = {
            "Orc Warband":    "orc_species",
            "Goblin Warband": "goblin_species",
        }
        ledger = _make_ledger({
            "orc_species":    {CHUNK: 100},
            "goblin_species": {CHUNK: 60},
        })
        results = resolve_migration_conflict(chunk_populations, self._factions(), ledger, CHUNK)
        assert len(results) == 1
        r = results[0]
        # Larger (orcs 100) loses 20% of 60 = 12; smaller (goblins 60) loses 30% of 100 = 30
        assert r["faction_a_loss"] < 0
        assert r["faction_b_loss"] < 0

    def test_ledger_updated_after_conflict(self):
        chunk_populations = {
            "Orc Warband":    "orc_species",
            "Goblin Warband": "goblin_species",
        }
        ledger = _make_ledger({
            "orc_species":    {CHUNK: 100},
            "goblin_species": {CHUNK: 60},
        })
        orc_before = ledger["orc_species"].local_counts[CHUNK]
        gob_before = ledger["goblin_species"].local_counts[CHUNK]
        resolve_migration_conflict(chunk_populations, self._factions(), ledger, CHUNK)
        assert ledger["orc_species"].local_counts[CHUNK] < orc_before
        assert ledger["goblin_species"].local_counts[CHUNK] < gob_before

    def test_no_conflict_when_not_hostile(self):
        factions = [
            FactionRecord("Merchant Guild", Alignment.NEUTRAL_GOOD, []),
            FactionRecord("Druid Circle",   Alignment.TRUE_NEUTRAL, []),
        ]
        chunk_populations = {
            "Merchant Guild": "merchant_species",
            "Druid Circle":   "druid_species",
        }
        ledger = _make_ledger({
            "merchant_species": {CHUNK: 100},
            "druid_species":    {CHUNK: 100},
        })
        results = resolve_migration_conflict(chunk_populations, factions, ledger, CHUNK)
        assert results == []

    def test_single_faction_no_conflict(self):
        chunk_populations = {"Orc Warband": "orc_species"}
        ledger = _make_ledger({"orc_species": {CHUNK: 100}})
        results = resolve_migration_conflict(chunk_populations, self._factions(), ledger, CHUNK)
        assert results == []


# ---------------------------------------------------------------------------
# EM-009 · generate_faction_lore
# ---------------------------------------------------------------------------

class TestGenerateFactionLore:
    def _faction(self):
        return FactionRecord("Orc Warband", Alignment.CHAOTIC_EVIL, ["Human Settlement"])

    def test_below_threshold_returns_none(self):
        mock_client = MagicMock()
        result = asyncio.run(
            generate_faction_lore(self._faction(), population_count=50, llm_client=mock_client, growth_threshold=100)
        )
        assert result is None
        mock_client.query_text.assert_not_called()

    def test_above_threshold_calls_llm(self):
        mock_client = MagicMock()
        mock_client.query_text = AsyncMock(return_value="The Blood-Axe Tribe rose from the ashes...")
        result = asyncio.run(
            generate_faction_lore(self._faction(), population_count=200, llm_client=mock_client, growth_threshold=100)
        )
        assert result == "The Blood-Axe Tribe rose from the ashes..."
        mock_client.query_text.assert_called_once()

    def test_exactly_at_threshold_calls_llm(self):
        mock_client = MagicMock()
        mock_client.query_text = AsyncMock(return_value="Lore text")
        result = asyncio.run(
            generate_faction_lore(self._faction(), population_count=100, llm_client=mock_client, growth_threshold=100)
        )
        assert result == "Lore text"
