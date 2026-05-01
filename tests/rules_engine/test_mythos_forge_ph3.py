"""Tests for Phase 3: Mythos Forge (PH3-010 · PH3-011 · PH3-012) and
Artifact Quest Injector (PH3-013)."""
from __future__ import annotations

import asyncio
import random
from pathlib import Path
from typing import Any

import pytest

from src.rules_engine.mythos_forge import (
    FACTION_GROWTH_THRESHOLD,
    CHUNK_DANGER_THRESHOLD,
    MythosThresholdRecord,
    evaluate_mythos_threshold,
    trigger_forge_on_threshold,
    ProceduralArtifactGenerator,
)
from src.game.quest import QuestJournal, QuestStatus, inject_artifact_quest
from src.world_sim.factions import FactionRecord
from src.rules_engine.character_35e import Alignment


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_faction(name: str, alignment: Alignment, hostile_to: list[str]) -> FactionRecord:
    return FactionRecord(name=name, alignment=alignment, hostile_to=hostile_to)


def _make_pop_record(global_count: int):
    from src.world_sim.population import SpeciesPopRecord
    return SpeciesPopRecord(
        species_id="stub",
        global_count=global_count,
        local_counts={},
    )


# ---------------------------------------------------------------------------
# PH3-010 — Constants
# ---------------------------------------------------------------------------

class TestMythosConstants:
    def test_faction_growth_threshold(self):
        assert FACTION_GROWTH_THRESHOLD == 2.5

    def test_chunk_danger_threshold(self):
        assert CHUNK_DANGER_THRESHOLD == 8.0


# ---------------------------------------------------------------------------
# PH3-010 — MythosThresholdRecord schema
# ---------------------------------------------------------------------------

class TestMythosThresholdRecord:
    def test_fields(self):
        rec = MythosThresholdRecord(
            record_id="r1",
            faction_name="Orc Warband",
            chunk_id=None,
            trigger_value=3.0,
            threshold_cutoff=2.5,
            triggered_at_tick=42,
        )
        assert rec.record_id == "r1"
        assert rec.faction_name == "Orc Warband"
        assert rec.chunk_id is None
        assert rec.trigger_value == 3.0
        assert rec.threshold_cutoff == 2.5
        assert rec.triggered_at_tick == 42
        assert rec.artifact_id is None

    def test_artifact_id_default_none(self):
        rec = MythosThresholdRecord(
            record_id="r2",
            faction_name=None,
            chunk_id="3,7",
            trigger_value=9.5,
            threshold_cutoff=8.0,
            triggered_at_tick=1,
        )
        assert rec.artifact_id is None


# ---------------------------------------------------------------------------
# PH3-011 — evaluate_mythos_threshold
# ---------------------------------------------------------------------------

class TestEvaluateMythosThreshold:
    def _ledger_from(self, factions_and_pops: dict[str, int]):
        from src.world_sim.population import SpeciesPopRecord
        return {
            name: SpeciesPopRecord(
                species_id=name,
                global_count=count,
                local_counts={},
            )
            for name, count in factions_and_pops.items()
        }

    def test_no_breach_below_threshold(self):
        orcs = _make_faction("Orc Warband", Alignment.CHAOTIC_EVIL, ["Human Settlement"])
        humans = _make_faction("Human Settlement", Alignment.LAWFUL_NEUTRAL, [])
        registry = {"Orc Warband": orcs, "Human Settlement": humans}
        ledger = self._ledger_from({"Orc Warband": 10, "Human Settlement": 20})

        triggered = evaluate_mythos_threshold(
            faction_registry=registry,
            population_ledger=ledger,
            chunk_danger_map={},
            current_tick=1,
        )
        assert triggered == []

    def test_faction_breach_above_threshold(self):
        orcs = _make_faction("Orc Warband", Alignment.CHAOTIC_EVIL, ["Human Settlement"])
        humans = _make_faction("Human Settlement", Alignment.LAWFUL_NEUTRAL, [])
        registry = {"Orc Warband": orcs, "Human Settlement": humans}
        # orcs:humans = 300:10 = 30.0 > 2.5
        ledger = self._ledger_from({"Orc Warband": 300, "Human Settlement": 10})

        triggered = evaluate_mythos_threshold(
            faction_registry=registry,
            population_ledger=ledger,
            chunk_danger_map={},
            current_tick=5,
        )
        assert len(triggered) >= 1
        breach = triggered[0]
        assert breach.faction_name == "Orc Warband"
        assert breach.triggered_at_tick == 5

    def test_chunk_danger_breach(self):
        triggered = evaluate_mythos_threshold(
            faction_registry={},
            population_ledger={},
            chunk_danger_map={"chunk-3": 12.0},
            current_tick=7,
        )
        assert len(triggered) == 1
        assert triggered[0].chunk_id == "chunk-3"
        assert triggered[0].trigger_value == 12.0
        assert triggered[0].triggered_at_tick == 7

    def test_chunk_danger_no_breach_below_threshold(self):
        triggered = evaluate_mythos_threshold(
            faction_registry={},
            population_ledger={},
            chunk_danger_map={"chunk-1": 5.0},
            current_tick=1,
        )
        assert triggered == []

    def test_multiple_breaches(self):
        triggered = evaluate_mythos_threshold(
            faction_registry={},
            population_ledger={},
            chunk_danger_map={"c1": 10.0, "c2": 15.0, "c3": 3.0},
            current_tick=1,
        )
        # Only c1 and c2 exceed threshold of 8.0
        chunk_ids = {t.chunk_id for t in triggered}
        assert "c1" in chunk_ids
        assert "c2" in chunk_ids
        assert "c3" not in chunk_ids

    def test_breach_record_has_unique_ids(self):
        triggered = evaluate_mythos_threshold(
            faction_registry={},
            population_ledger={},
            chunk_danger_map={"c1": 10.0, "c2": 15.0},
            current_tick=1,
        )
        ids = [t.record_id for t in triggered]
        assert len(ids) == len(set(ids))

    def test_opposing_pop_zero_no_div_error(self):
        """Zero-population factions should not cause ZeroDivisionError."""
        orcs = _make_faction("Orc Warband", Alignment.CHAOTIC_EVIL, ["Ghost Faction"])
        ghosts = _make_faction("Ghost Faction", Alignment.TRUE_NEUTRAL, [])
        registry = {"Orc Warband": orcs, "Ghost Faction": ghosts}
        ledger = self._ledger_from({"Orc Warband": 100})  # Ghost Faction not in ledger

        # Should not raise
        triggered = evaluate_mythos_threshold(
            faction_registry=registry,
            population_ledger=ledger,
            chunk_danger_map={},
            current_tick=1,
        )
        # Ghost has 0 pop → ratio check skipped → no breach
        assert triggered == []


# ---------------------------------------------------------------------------
# PH3-012 — trigger_forge_on_threshold
# ---------------------------------------------------------------------------

class TestTriggerForgeOnThreshold:
    def _make_forge(self, tmp_path: Path) -> ProceduralArtifactGenerator:
        return ProceduralArtifactGenerator(
            store_path=tmp_path / "test_registry.json",
            rng=random.Random(42),
        )

    def test_returns_artifact(self, tmp_path: Path):
        forge = self._make_forge(tmp_path)
        threshold = MythosThresholdRecord(
            record_id="t1",
            faction_name="Orc Warband",
            chunk_id=None,
            trigger_value=3.0,
            threshold_cutoff=2.5,
            triggered_at_tick=1,
        )
        rng = random.Random(42)
        artifact = asyncio.run(
            trigger_forge_on_threshold(threshold, forge, campaign=None, rng=rng)
        )
        assert artifact is not None
        assert artifact.artifact_id != ""

    def test_writes_artifact_id_to_threshold(self, tmp_path: Path):
        forge = self._make_forge(tmp_path)
        threshold = MythosThresholdRecord(
            record_id="t2",
            faction_name=None,
            chunk_id="chunk-99",
            trigger_value=12.0,
            threshold_cutoff=8.0,
            triggered_at_tick=2,
        )
        rng = random.Random(99)
        artifact = asyncio.run(
            trigger_forge_on_threshold(threshold, forge, campaign=None, rng=rng)
        )
        assert threshold.artifact_id == artifact.artifact_id

    def test_minor_tier_below_2x(self, tmp_path: Path):
        from src.rules_engine.item_specials import ArtifactType
        forge = self._make_forge(tmp_path)
        threshold = MythosThresholdRecord(
            record_id="t3",
            faction_name="Some Faction",
            chunk_id=None,
            trigger_value=3.0,   # ratio = 3.0 / 2.5 = 1.2 < 2.0
            threshold_cutoff=2.5,
            triggered_at_tick=1,
        )
        artifact = asyncio.run(
            trigger_forge_on_threshold(threshold, forge, campaign=None, rng=random.Random(1))
        )
        assert artifact.artifact_type == ArtifactType.MINOR

    def test_major_tier_at_2x(self, tmp_path: Path):
        from src.rules_engine.item_specials import ArtifactType
        forge = self._make_forge(tmp_path)
        threshold = MythosThresholdRecord(
            record_id="t4",
            faction_name=None,
            chunk_id="c1",
            trigger_value=20.0,  # ratio = 20.0 / 8.0 = 2.5 >= 2.0
            threshold_cutoff=8.0,
            triggered_at_tick=1,
        )
        artifact = asyncio.run(
            trigger_forge_on_threshold(threshold, forge, campaign=None, rng=random.Random(2))
        )
        assert artifact.artifact_type == ArtifactType.MAJOR


# ---------------------------------------------------------------------------
# PH3-013 — inject_artifact_quest
# ---------------------------------------------------------------------------

class TestInjectArtifactQuest:
    def _make_artifact(self):
        """Build a minimal duck-typed artifact for testing."""
        from types import SimpleNamespace
        props = SimpleNamespace(
            artifact_id="art-001",
            calculated_price_gp=10_000,
        )
        return SimpleNamespace(
            artifact_id="art-001",
            lore_name="The Eternal Blade",
            lore_history="Forged in the Chaos Wars, this blade has never dulled.",
            properties=props,
        )

    def _make_threshold(self, faction=True):
        from types import SimpleNamespace
        if faction:
            return SimpleNamespace(faction_name="Orc Warband", chunk_id=None)
        return SimpleNamespace(faction_name=None, chunk_id="chunk-99")

    def test_returns_quest(self):
        artifact = self._make_artifact()
        threshold = self._make_threshold()
        journal = QuestJournal()
        quest = inject_artifact_quest(artifact, threshold, journal, world_seed=42)
        assert quest is not None

    def test_quest_title_contains_artifact_name(self):
        artifact = self._make_artifact()
        threshold = self._make_threshold()
        journal = QuestJournal()
        quest = inject_artifact_quest(artifact, threshold, journal, world_seed=42)
        assert "The Eternal Blade" in quest.title

    def test_quest_added_to_journal(self):
        artifact = self._make_artifact()
        threshold = self._make_threshold()
        journal = QuestJournal()
        quest = inject_artifact_quest(artifact, threshold, journal, world_seed=42)
        assert journal.get(quest.quest_id) is quest

    def test_quest_status_active(self):
        artifact = self._make_artifact()
        threshold = self._make_threshold()
        journal = QuestJournal()
        quest = inject_artifact_quest(artifact, threshold, journal, world_seed=42)
        assert quest.status == QuestStatus.ACTIVE

    def test_deterministic_quest_id(self):
        artifact = self._make_artifact()
        threshold = self._make_threshold()
        j1 = QuestJournal()
        j2 = QuestJournal()
        q1 = inject_artifact_quest(artifact, threshold, j1, world_seed=42)
        q2 = inject_artifact_quest(artifact, threshold, j2, world_seed=42)
        assert q1.quest_id == q2.quest_id

    def test_reward_is_10pct_of_price(self):
        artifact = self._make_artifact()
        threshold = self._make_threshold()
        journal = QuestJournal()
        quest = inject_artifact_quest(artifact, threshold, journal, world_seed=1)
        assert quest.reward_gp == 1_000   # 10% of 10,000

    def test_description_contains_lore_excerpt(self):
        artifact = self._make_artifact()
        threshold = self._make_threshold()
        journal = QuestJournal()
        quest = inject_artifact_quest(artifact, threshold, journal, world_seed=1)
        assert "Chaos Wars" in quest.description

    def test_faction_context_in_description(self):
        artifact = self._make_artifact()
        threshold = self._make_threshold(faction=True)
        journal = QuestJournal()
        quest = inject_artifact_quest(artifact, threshold, journal, world_seed=1)
        assert "Orc Warband" in quest.description

    def test_chunk_context_in_description(self):
        artifact = self._make_artifact()
        threshold = self._make_threshold(faction=False)
        journal = QuestJournal()
        quest = inject_artifact_quest(artifact, threshold, journal, world_seed=1)
        assert "chunk-99" in quest.description

    def test_objective_note_added(self):
        artifact = self._make_artifact()
        threshold = self._make_threshold()
        journal = QuestJournal()
        quest = inject_artifact_quest(artifact, threshold, journal, world_seed=1)
        assert any("art-001" in note for note in quest.notes)

    def test_campaign_journal_also_receives_quest(self):
        from types import SimpleNamespace
        artifact = self._make_artifact()
        threshold = self._make_threshold()
        journal = QuestJournal()
        camp_journal = QuestJournal()
        campaign = SimpleNamespace(journal=camp_journal)
        quest = inject_artifact_quest(artifact, threshold, journal, world_seed=1, campaign=campaign)
        assert camp_journal.get(quest.quest_id) is quest
