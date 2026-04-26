"""LW-046 — Living World regression test suite.

Six integration scenarios covering ecology, MM physics, and their interaction:
  1. Biome-zeroed at init     — species with no matching biome starts extinct.
  2. Extinction via kills     — single-entity population → AlreadyExtinctError on second broadcast.
  3. Migration repopulation   — overpopulated chunk generates vector; target count grows.
  4. Anomaly lore async       — mock LLMClient; AnomalyRecord.lore_text populated after await.
  5. DR + SR combat           — non-magical arrow reduced by DR; Magic Missile blocked by SR.
  6. Troll Regen suppression  — fire damage suppresses Regen; Fast Heal absent → 0 HP restored.
"""
from __future__ import annotations

import asyncio
import random
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from src.world_sim.biome import Biome, SpeciesBiomeBinding, apply_biome_strictness, can_spawn_in_chunk
from src.world_sim.population import (
    SpeciesPopRecord,
    WorldChunk,
    WorldGenerationSeed,
    PopulationLedger,
    initialize_world_populations,
    apply_population_delta,
    broadcast_extinction,
    SpeciesExtinctError,
    AlreadyExtinctError,
    ExtinctionCause,
    _EXTINCT_BROADCAST,
)
from src.world_sim.migration import (
    MigrationCause,
    MigrationVector,
    ChunkAdjacencyGraph,
    calculate_migration_pressure,
    generate_migration_vectors,
    apply_migration_vectors,
)
from src.world_sim.anomaly import AnomalyRecord, resolve_anomaly_roll, request_anomaly_lore
from src.rules_engine.mm_immortal import (
    RegenerationRecord,
    DamageEvent,
    apply_regeneration_weakness_check,
    resolve_healing_precedence,
    HealingSource,
)
from src.rules_engine.mm_metaphysical import (
    DRConjunction,
    DRRecord,
    SRRecord,
    apply_damage_reduction,
    check_spell_resistance,
)
from src.core.event_bus import EventBus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_chunk(
    chunk_id: str,
    biome: Biome,
    adjacent: tuple[str, ...] = (),
    populations: dict | None = None,
    capacity: dict | None = None,
) -> WorldChunk:
    return WorldChunk(
        chunk_id=chunk_id,
        biome=biome,
        adjacent_chunks=adjacent,
        local_populations=dict(populations or {}),
        carrying_capacity=dict(capacity or {}),
    )


def _make_binding(
    species_id: str,
    primary: tuple[Biome, ...],
    tolerated: tuple[Biome, ...] = (),
    forbidden: tuple[Biome, ...] = (),
    pop_base: int = 100,
) -> SpeciesBiomeBinding:
    return SpeciesBiomeBinding(
        species_id=species_id,
        primary_biomes=primary,
        tolerated_biomes=tolerated,
        forbidden_biomes=forbidden,
        population_base=pop_base,
    )


def _make_character(name: str = "Test", level: int = 5, **kwargs):
    """Build a minimal Character35e for physics tests."""
    from src.rules_engine.character_35e import Character35e
    defaults = dict(
        name=name,
        char_class="Fighter",
        level=level,
        strength=10,
        dexterity=10,
        constitution=10,
        intelligence=10,
        wisdom=10,
        charisma=10,
    )
    defaults.update(kwargs)
    return Character35e(**defaults)


# ---------------------------------------------------------------------------
# Scenario 1 — Biome-zeroed at init
# ---------------------------------------------------------------------------

class TestBiomeZeroedAtInit(unittest.TestCase):
    """World generated with no Underdark chunk → Drow global_count=0, is_extinct=True."""

    def setUp(self):
        _EXTINCT_BROADCAST.clear()

    def test_drow_zeroed_when_no_underdark(self):
        drow_binding = _make_binding(
            "drow", primary=(Biome.Underdark,), pop_base=5000
        )
        # World has Temperate_Forest and Cold_Hill — no Underdark
        chunks = [
            _make_chunk("c1", Biome.Temperate_Forest, capacity={"drow": 1000}),
            _make_chunk("c2", Biome.Cold_Hill, capacity={"drow": 1000}),
        ]
        seed = WorldGenerationSeed(seed=42, biome_distribution={})

        ledger = initialize_world_populations(chunks, {"drow": drow_binding}, seed)

        record = ledger["drow"]
        self.assertEqual(record.global_count, 0)
        self.assertTrue(record.is_extinct)

    def test_drow_spawns_when_underdark_present(self):
        drow_binding = _make_binding(
            "drow", primary=(Biome.Underdark,), pop_base=5000
        )
        chunks = [
            _make_chunk("u1", Biome.Underdark, capacity={"drow": 5000}),
            _make_chunk("c1", Biome.Temperate_Forest, capacity={"drow": 0}),
        ]
        seed = WorldGenerationSeed(seed=42, biome_distribution={})

        ledger = initialize_world_populations(chunks, {"drow": drow_binding}, seed)

        record = ledger["drow"]
        self.assertEqual(record.global_count, 5000)
        self.assertFalse(record.is_extinct)

    def test_biome_gate_blocks_non_native_chunk(self):
        drow_binding = _make_binding("drow", primary=(Biome.Underdark,), pop_base=100)
        ledger: PopulationLedger = {
            "drow": SpeciesPopRecord("drow", global_count=100, local_counts={"u1": 100})
        }
        forest_chunk = _make_chunk("f1", Biome.Temperate_Forest, capacity={"drow": 500})

        result = can_spawn_in_chunk("drow", forest_chunk, ledger, {"drow": drow_binding})
        self.assertFalse(result)


# ---------------------------------------------------------------------------
# Scenario 2 — Extinction via kills
# ---------------------------------------------------------------------------

class TestExtinctionViaKills(unittest.TestCase):
    """Single Troll killed → broadcast fires once; second call raises AlreadyExtinctError."""

    def setUp(self):
        _EXTINCT_BROADCAST.clear()

    def test_extinction_flow(self):
        ledger: PopulationLedger = {
            "troll": SpeciesPopRecord("troll", global_count=1, local_counts={"cold_hill_1": 1})
        }
        bus = EventBus()
        fired_events = []
        bus.subscribe("species_extinction", fired_events.append)

        # Kill the last Troll
        apply_population_delta(ledger, "troll", "cold_hill_1", -1)
        self.assertEqual(ledger["troll"].global_count, 0)
        self.assertTrue(ledger["troll"].is_extinct)

        # Broadcast extinction
        evt = broadcast_extinction("troll", ledger, bus, tick=10, cause=ExtinctionCause.PlayerKills)
        self.assertEqual(len(fired_events), 1)
        self.assertEqual(fired_events[0].species_id, "troll")
        self.assertEqual(fired_events[0].cause, ExtinctionCause.PlayerKills)

        # Second broadcast must raise
        with self.assertRaises(AlreadyExtinctError):
            broadcast_extinction("troll", ledger, bus, tick=11)

        # apply_population_delta must raise on extinct species
        with self.assertRaises(SpeciesExtinctError):
            apply_population_delta(ledger, "troll", "cold_hill_1", +1)


# ---------------------------------------------------------------------------
# Scenario 3 — Migration repopulation
# ---------------------------------------------------------------------------

class TestMigrationRepopulation(unittest.TestCase):
    """Overpopulated Cold_Hill chunk generates a vector; adjacent Cold_Mountain gains population."""

    def setUp(self):
        _EXTINCT_BROADCAST.clear()

    def test_migration_vector_generated_and_applied(self):
        rng = random.Random(0)

        troll_binding = _make_binding(
            "troll",
            primary=(Biome.Cold_Hill, Biome.Cold_Mountain),
            pop_base=300,
        )
        # Source chunk: overpopulated (200 trolls, capacity 100 → pressure 1.0)
        source = _make_chunk(
            "cold_hill_1", Biome.Cold_Hill,
            adjacent=("cold_mountain_1",),
            populations={"troll": 200},
            capacity={"troll": 100},
        )
        # Target chunk: empty, same biome group
        target = _make_chunk(
            "cold_mountain_1", Biome.Cold_Mountain,
            adjacent=("cold_hill_1",),
            populations={"troll": 0},
            capacity={"troll": 200},
        )
        world = [source, target]

        ledger: PopulationLedger = {
            "troll": SpeciesPopRecord("troll", global_count=200, local_counts={"cold_hill_1": 200})
        }

        graph = ChunkAdjacencyGraph(world)
        vectors = generate_migration_vectors(
            "troll", world, ledger, graph, {"troll": troll_binding},
            current_tick=1, rng=rng,
        )

        self.assertGreater(len(vectors), 0, "Expected at least one migration vector")
        v = vectors[0]
        self.assertEqual(v.species_id, "troll")
        self.assertEqual(v.source_chunk_id, "cold_hill_1")
        self.assertEqual(v.target_chunk_id, "cold_mountain_1")

        # Apply the vector at its scheduled tick
        apply_migration_vectors(vectors, ledger, world, current_tick=v.scheduled_tick)

        self.assertGreater(
            target.local_populations.get("troll", 0), 0,
            "Target chunk should have gained Trolls after migration",
        )


# ---------------------------------------------------------------------------
# Scenario 4 — Anomaly lore async
# ---------------------------------------------------------------------------

class TestAnomalyLoreAsync(unittest.TestCase):
    """Mock LLMClient; Tarrasque anomaly in Temperate_Forest → lore_text populated after await."""

    def setUp(self):
        _EXTINCT_BROADCAST.clear()

    def test_anomaly_record_created_and_lore_populated(self):
        rng_mock = MagicMock()
        rng_mock.random.return_value = 0.001   # well below threshold of 0.005

        tarrasque_binding = _make_binding(
            "tarrasque",
            primary=(Biome.Any,),
            pop_base=1,
        )
        # Override primary to a specific biome so the chunk biome differs
        tarrasque_binding = SpeciesBiomeBinding(
            species_id="tarrasque",
            primary_biomes=(Biome.Warm_Plain,),
            tolerated_biomes=(),
            forbidden_biomes=(),
            population_base=1,
        )

        forest_chunk = _make_chunk("forest_1", Biome.Temperate_Forest)

        anomaly = resolve_anomaly_roll(
            rng_mock, "tarrasque", "tarrasque_1",
            tarrasque_binding, forest_chunk, world_tick=42,
        )

        self.assertIsNotNone(anomaly, "Anomaly should be created")
        self.assertIsNone(anomaly.lore_text, "lore_text should be None before LLM call")
        self.assertEqual(anomaly.species_id, "tarrasque")
        self.assertEqual(anomaly.current_biome, Biome.Temperate_Forest)

        # Mock the LLM client with an async response
        mock_llm = MagicMock()
        mock_llm.query_model = AsyncMock(
            return_value="Centuries ago, a wizard's botched banishment ritual tore a rift..."
        )

        async def _run():
            return await request_anomaly_lore(anomaly, mock_llm, species_notes=None)

        result = asyncio.get_event_loop().run_until_complete(_run())
        self.assertIsNotNone(result.lore_text)
        self.assertIn("wizard", result.lore_text)

    def test_anomaly_not_created_in_native_biome(self):
        rng_mock = MagicMock()
        rng_mock.random.return_value = 0.001

        binding = _make_binding("drow", primary=(Biome.Underdark,))
        underdark_chunk = _make_chunk("ud1", Biome.Underdark)

        anomaly = resolve_anomaly_roll(
            rng_mock, "drow", "drow_1", binding, underdark_chunk, world_tick=1
        )
        self.assertIsNone(anomaly, "No anomaly when entity is in its native biome")


# ---------------------------------------------------------------------------
# Scenario 5 — DR + SR combat
# ---------------------------------------------------------------------------

class TestDRAndSRCombat(unittest.TestCase):
    """Beholder DR 10/Magic + SR 27.
    Non-magical arrow: reduced by 10.
    Magic Missile blocked by SR: spell damage = 0.
    """

    def test_non_magical_arrow_reduced_by_dr(self):
        beholder_dr = DRRecord(
            entity_id="beholder_1",
            dr_amount=10,
            bypass_conjunction=DRConjunction.Or,
            bypass_materials=("Magic",),
        )
        raw = 15
        # Non-magical arrow: no weapon properties
        result = apply_damage_reduction(raw, weapon_properties=(), dr_record=beholder_dr)
        self.assertEqual(result, 5)   # 15 - 10 = 5

    def test_magical_weapon_bypasses_dr(self):
        beholder_dr = DRRecord(
            entity_id="beholder_1",
            dr_amount=10,
            bypass_conjunction=DRConjunction.Or,
            bypass_materials=("Magic",),
        )
        result = apply_damage_reduction(15, weapon_properties=("Magic", "+1"), dr_record=beholder_dr)
        self.assertEqual(result, 15)   # bypassed

    def test_energy_damage_bypasses_dr(self):
        beholder_dr = DRRecord(
            entity_id="beholder_1",
            dr_amount=10,
            bypass_conjunction=DRConjunction.Or,
            bypass_materials=("Magic",),
        )
        result = apply_damage_reduction(20, weapon_properties=("Fire",), dr_record=beholder_dr)
        self.assertEqual(result, 20)   # energy bypasses DR

    def test_sr_blocks_magic_missile(self):
        beholder_sr = SRRecord(
            entity_id="beholder_1",
            sr_value=27,
            voluntarily_suppressed=False,
        )
        caster = _make_character("Wizard", level=5, char_class="Wizard")
        target = _make_character("Beholder", level=11, char_class="Fighter")
        # Patch roll_d20 to return a low roll (5 + caster_level fails vs SR 27)
        with patch("src.rules_engine.dice.roll_d20") as mock_roll:
            mock_result = MagicMock()
            mock_result.raw = 5
            mock_result.total = 5 + caster.caster_level   # well below 27
            mock_roll.return_value = mock_result

            sr_result = check_spell_resistance(caster, target, beholder_sr)

        self.assertFalse(sr_result.penetrated)

    def test_sr_penetrated_on_high_roll(self):
        beholder_sr = SRRecord(
            entity_id="beholder_1",
            sr_value=27,
            voluntarily_suppressed=False,
        )
        caster = _make_character("Archmage", level=20, char_class="Wizard")
        target = _make_character("Beholder", level=11, char_class="Fighter")
        with patch("src.rules_engine.dice.roll_d20") as mock_roll:
            mock_result = MagicMock()
            mock_result.raw = 20
            mock_result.total = 20 + caster.caster_level   # 40, beats SR 27
            mock_roll.return_value = mock_result

            sr_result = check_spell_resistance(caster, target, beholder_sr)

        self.assertTrue(sr_result.penetrated)

    def test_and_conjunction_dr_requires_both_materials(self):
        # e.g. 10/Cold Iron and Magic
        dr = DRRecord(
            entity_id="demon_1",
            dr_amount=10,
            bypass_conjunction=DRConjunction.And,
            bypass_materials=("Cold Iron", "Magic"),
        )
        # Only Magic — not enough
        self.assertEqual(apply_damage_reduction(15, ("Magic",), dr), 5)
        # Both Cold Iron and Magic — bypassed
        self.assertEqual(apply_damage_reduction(15, ("Cold Iron", "Magic"), dr), 15)


# ---------------------------------------------------------------------------
# Scenario 6 — Troll Regeneration suppression
# ---------------------------------------------------------------------------

class TestTrollRegenSuppression(unittest.TestCase):
    """Troll receives fire damage on tick N → Regen suppressed; no Fast Heal → 0 HP restored."""

    def _troll_record(self, suppressed_until: int = 0) -> RegenerationRecord:
        return RegenerationRecord(
            entity_id="troll_1",
            regen_hp_per_round=5,
            fast_heal_hp_per_round=0,   # Trolls have Regen only, no Fast Heal
            elemental_weaknesses=("Fire", "Acid"),
            alignment_weaknesses=(),
            suppressed_until_tick=suppressed_until,
        )

    def test_fire_suppresses_regen(self):
        record = self._troll_record()
        fire_event = DamageEvent(damage_type="Fire", amount=12, tick=5)
        apply_regeneration_weakness_check(record, fire_event, tick=5)
        self.assertEqual(record.suppressed_until_tick, 6)

    def test_no_healing_this_tick_when_suppressed(self):
        troll = _make_character(
            "Troll", level=6,
            strength=23, dexterity=14, constitution=23,
            char_class="Fighter",
        )
        record = self._troll_record()

        # Apply fire damage — sets suppressed_until_tick = 6
        fire_event = DamageEvent(damage_type="Fire", amount=12, tick=5)
        apply_regeneration_weakness_check(record, fire_event, tick=5)

        # Now resolve healing for tick 5
        result = resolve_healing_precedence(troll, record, tick=5)

        self.assertEqual(result.hp_restored, 0)
        self.assertTrue(result.regen_was_suppressed)
        self.assertEqual(result.source, HealingSource.FastHealing)   # attempted source when regen down

    def test_regen_resumes_next_tick(self):
        troll = _make_character(
            "Troll", level=6,
            strength=23, dexterity=14, constitution=23,
            char_class="Fighter",
        )
        # suppressed_until_tick=5 means suppressed on tick 5, clear on tick 6
        record = self._troll_record(suppressed_until=5)

        result = resolve_healing_precedence(troll, record, tick=6)

        self.assertFalse(result.regen_was_suppressed)
        self.assertEqual(result.source, HealingSource.Regeneration)

    def test_acid_also_suppresses_regen(self):
        record = self._troll_record()
        acid_event = DamageEvent(damage_type="Acid", amount=8, tick=10)
        apply_regeneration_weakness_check(record, acid_event, tick=10)
        self.assertEqual(record.suppressed_until_tick, 11)

    def test_slashing_damage_does_not_suppress_regen(self):
        record = self._troll_record()
        slash_event = DamageEvent(damage_type="Slashing", amount=10, tick=3)
        apply_regeneration_weakness_check(record, slash_event, tick=3)
        self.assertEqual(record.suppressed_until_tick, 0)   # unchanged


if __name__ == "__main__":
    unittest.main()
