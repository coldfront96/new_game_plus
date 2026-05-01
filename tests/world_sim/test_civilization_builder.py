"""Tests for PH2-001 · PH2-002 · PH2-003 · PH2-004 · PH2-005 — civilization_builder module."""
from __future__ import annotations

import pytest

from src.world_sim.biome import Biome
from src.world_sim.civilization_builder import (
    ItemCategory,
    InventoryItem,
    MerchantInventoryRecord,
    TownRecord,
    TownRegistry,
    MerchantRegistry,
    SPECIES_TO_LOOT,
    calculate_merchant_inventory,
    generate_towns,
    is_safe_biome,
)
from src.world_sim.factions import FactionRecord, DEFAULT_FACTIONS
from src.world_sim.population import SpeciesPopRecord, WorldChunk


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_chunk(chunk_id: str, biome: Biome) -> WorldChunk:
    return WorldChunk(
        chunk_id=chunk_id,
        biome=biome,
        adjacent_chunks=(),
        local_populations={},
        carrying_capacity={},
    )


def _make_faction_registry() -> dict[str, FactionRecord]:
    return {f.name: f for f in DEFAULT_FACTIONS}


def _make_ledger(entries: dict[str, dict[str, int]]) -> dict[str, SpeciesPopRecord]:
    return {
        sid: SpeciesPopRecord(
            species_id=sid,
            global_count=sum(local.values()),
            local_counts=dict(local),
        )
        for sid, local in entries.items()
    }


# ---------------------------------------------------------------------------
# PH2-001 · TownRecord
# ---------------------------------------------------------------------------

class TestTownRecord:
    def test_creation(self):
        t = TownRecord(
            town_id="abc123",
            name="Ashfield",
            chunk_id="chunk_A",
            biome=Biome.Temperate_Plain,
            faction_name="Human Settlement",
            population_count=500,
        )
        assert t.town_id == "abc123"
        assert t.biome == Biome.Temperate_Plain
        assert t.faction_name == "Human Settlement"
        assert t.merchant_ids == []

    def test_slots_no_dict(self):
        t = TownRecord("x", "Y", "c", Biome.Any_Urban, None, 100)
        assert not hasattr(t, "__dict__")

    def test_merchant_ids_default_empty(self):
        t = TownRecord("id", "Name", "c", Biome.Warm_Plain, None, 0)
        assert isinstance(t.merchant_ids, list)
        assert len(t.merchant_ids) == 0


# ---------------------------------------------------------------------------
# PH2-002 · is_safe_biome
# ---------------------------------------------------------------------------

class TestIsSafeBiome:
    @pytest.mark.parametrize("biome", [
        Biome.Temperate_Plain,
        Biome.Temperate_Forest,
        Biome.Temperate_Hill,
        Biome.Warm_Plain,
        Biome.Warm_Forest,
        Biome.Any_Urban,
    ])
    def test_safe_biomes(self, biome):
        assert is_safe_biome(biome) is True

    @pytest.mark.parametrize("biome", [
        Biome.Underdark,
        Biome.Arctic,
        Biome.Elemental_Fire,
        Biome.Elemental_Earth,
        Biome.Elemental_Air,
        Biome.Elemental_Water,
        Biome.Outer_Plane,
        Biome.Negative_Energy,
        Biome.Positive_Energy,
        Biome.Cold_Plain,
        Biome.Cold_Forest,
        Biome.Temperate_Swamp,
        Biome.Warm_Desert,
        Biome.Aquatic,
    ])
    def test_unsafe_biomes(self, biome):
        assert is_safe_biome(biome) is False


# ---------------------------------------------------------------------------
# PH2-003 · generate_towns
# ---------------------------------------------------------------------------

class TestGenerateTowns:
    def _chunks(self) -> list[WorldChunk]:
        return [
            _make_chunk("chunk_plain_1", Biome.Temperate_Plain),
            _make_chunk("chunk_plain_2", Biome.Temperate_Plain),
            _make_chunk("chunk_urban",   Biome.Any_Urban),
            _make_chunk("chunk_forest",  Biome.Temperate_Forest),
            _make_chunk("chunk_desert",  Biome.Warm_Desert),   # not safe
            _make_chunk("chunk_underd",  Biome.Underdark),      # not safe
        ]

    def test_returns_town_registry(self):
        registry = generate_towns(self._chunks(), _make_faction_registry(), seed=42)
        assert isinstance(registry, dict)

    def test_all_towns_in_safe_biomes(self):
        registry = generate_towns(self._chunks(), _make_faction_registry(), seed=42)
        for town in registry.values():
            assert is_safe_biome(town.biome), f"Town in unsafe biome: {town.biome}"

    def test_one_town_per_chunk(self):
        chunks = self._chunks()
        registry = generate_towns(chunks, _make_faction_registry(), seed=42)
        chunk_ids = [t.chunk_id for t in registry.values()]
        assert len(chunk_ids) == len(set(chunk_ids))

    def test_max_towns_per_biome_respected(self):
        # Many plain chunks, cap = 1.
        chunks = [_make_chunk(f"plain_{i}", Biome.Temperate_Plain) for i in range(20)]
        registry = generate_towns(chunks, _make_faction_registry(), seed=1, max_towns_per_biome=1)
        biome_counts: dict[str, int] = {}
        for t in registry.values():
            biome_counts[t.biome.value] = biome_counts.get(t.biome.value, 0) + 1
        for count in biome_counts.values():
            assert count <= 1

    def test_deterministic_with_same_seed(self):
        chunks = self._chunks()
        r1 = generate_towns(chunks, _make_faction_registry(), seed=999)
        r2 = generate_towns(chunks, _make_faction_registry(), seed=999)
        assert set(r1.keys()) == set(r2.keys())

    def test_different_seeds_may_differ(self):
        chunks = [_make_chunk(f"p_{i}", Biome.Warm_Plain) for i in range(30)]
        r1 = generate_towns(chunks, _make_faction_registry(), seed=1)
        r2 = generate_towns(chunks, _make_faction_registry(), seed=2)
        # Not guaranteed to differ but their IDs will typically differ.
        # Just assert both are valid dicts.
        assert isinstance(r1, dict)
        assert isinstance(r2, dict)

    def test_town_has_merchant_id(self):
        registry = generate_towns(self._chunks(), _make_faction_registry(), seed=42)
        for town in registry.values():
            assert len(town.merchant_ids) >= 1

    def test_empty_world_produces_no_towns(self):
        registry = generate_towns([], _make_faction_registry(), seed=42)
        assert len(registry) == 0

    def test_only_unsafe_chunks_produce_no_towns(self):
        chunks = [
            _make_chunk("a", Biome.Underdark),
            _make_chunk("b", Biome.Arctic),
            _make_chunk("c", Biome.Outer_Plane),
        ]
        registry = generate_towns(chunks, _make_faction_registry(), seed=42)
        assert len(registry) == 0


# ---------------------------------------------------------------------------
# PH2-004 · MerchantInventoryRecord / InventoryItem / ItemCategory
# ---------------------------------------------------------------------------

class TestMerchantSchemas:
    def test_item_category_values(self):
        expected = {"raw_material", "weapon", "armour", "provision", "alchemical", "misc"}
        actual = {c.value for c in ItemCategory}
        assert expected == actual

    def test_inventory_item_creation(self):
        item = InventoryItem("Iron Sword", 15, ItemCategory.Weapon)
        assert item.item_name == "Iron Sword"
        assert item.base_price_gp == 15
        assert item.category == ItemCategory.Weapon

    def test_inventory_item_slots(self):
        item = InventoryItem("x", 1, ItemCategory.Misc)
        assert not hasattr(item, "__dict__")

    def test_merchant_inventory_creation(self):
        rec = MerchantInventoryRecord(
            merchant_id="m_001",
            town_id="t_001",
            stock={"Leather": 10},
        )
        assert rec.merchant_id == "m_001"
        assert rec.stock["Leather"] == 10

    def test_merchant_inventory_slots(self):
        rec = MerchantInventoryRecord("m", "t")
        assert not hasattr(rec, "__dict__")

    def test_merchant_inventory_default_stock_empty(self):
        rec = MerchantInventoryRecord("m", "t")
        assert rec.stock == {}


# ---------------------------------------------------------------------------
# PH2-005 · calculate_merchant_inventory
# ---------------------------------------------------------------------------

class TestCalculateMerchantInventory:
    def _town(self) -> TownRecord:
        return TownRecord(
            town_id="town_001",
            name="Oakton",
            chunk_id="chunk_A",
            biome=Biome.Temperate_Plain,
            faction_name="Human Settlement",
            population_count=300,
            merchant_ids=["merchant_town_001"],
        )

    def test_basic_stock_from_deer(self):
        town = self._town()
        ledger = _make_ledger({"deer": {"chunk_A": 100}})
        rec = calculate_merchant_inventory(town, ledger, {}, {})
        assert "Leather" in rec.stock
        assert "Raw Meat" in rec.stock
        # floor(100 * 0.10) = 10 Leather
        assert rec.stock["Leather"] == 10
        # floor(100 * 0.15) = 15 Raw Meat
        assert rec.stock["Raw Meat"] == 15

    def test_stock_clamped_to_99(self):
        town = self._town()
        # 1000 deer → floor(1000 * 0.10) = 100 Leather → clamped to 99.
        ledger = _make_ledger({"deer": {"chunk_A": 1000}})
        rec = calculate_merchant_inventory(town, ledger, {}, {})
        assert rec.stock.get("Leather", 0) <= 99

    def test_zero_population_produces_no_stock(self):
        town = self._town()
        ledger = _make_ledger({"deer": {"chunk_A": 0}})
        rec = calculate_merchant_inventory(town, ledger, {}, {})
        assert "Leather" not in rec.stock

    def test_different_chunk_not_counted(self):
        town = self._town()
        ledger = _make_ledger({"deer": {"chunk_B": 500}})
        rec = calculate_merchant_inventory(town, ledger, {}, {})
        assert rec.stock.get("Leather", 0) == 0

    def test_unknown_species_ignored(self):
        town = self._town()
        ledger = _make_ledger({"dragon": {"chunk_A": 5}})
        rec = calculate_merchant_inventory(town, ledger, {}, {})
        assert rec.stock == {}

    def test_multiple_species_accumulate(self):
        town = self._town()
        ledger = _make_ledger({
            "deer": {"chunk_A": 100},
            "wolf": {"chunk_A": 50},
        })
        rec = calculate_merchant_inventory(town, ledger, {}, {})
        # Wolf adds Bone; deer adds Leather + Raw Meat.
        assert "Leather" in rec.stock
        assert "Wolf Pelt" in rec.stock
        assert "Bone" in rec.stock

    def test_merchant_id_taken_from_town(self):
        town = self._town()
        ledger = _make_ledger({"rabbit": {"chunk_A": 20}})
        rec = calculate_merchant_inventory(town, ledger, {}, {})
        assert rec.merchant_id == "merchant_town_001"
        assert rec.town_id == "town_001"

    def test_species_to_loot_populated(self):
        assert "deer" in SPECIES_TO_LOOT
        assert "wolf" in SPECIES_TO_LOOT
        assert len(SPECIES_TO_LOOT) >= 5
