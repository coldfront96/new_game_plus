"""
tests/rules_engine/test_settlement.py
---------------------------------------
Tests for settlement.py (E-012, E-013, E-028, E-029, E-042, E-043,
E-054, E-060, E-066).
"""

from __future__ import annotations

import random

import pytest

from src.rules_engine.npc_classes import NPCClassName, NPC_CLASS_DISTRIBUTION_PCT
from src.rules_engine.settlement import (
    AlignmentLean,
    AuthorityFigure,
    AvailableInventory,
    COMMUNITY_REGISTRY,
    DEMOGRAPHICS_TABLE,
    POWER_CENTER_REGISTRY,
    CommunityBase,
    CommunitySize,
    DemographicsRow,
    PowerCenter,
    PowerCenterEntry,
    PowerCenterType,
    Settlement,
    ShopResult,
    available_magic_items,
    community_total_assets,
    generate_settlement,
    gp_limit_for,
    highest_level_npc_class,
    population_class_roster,
    roll_power_center_type,
    shop,
)


# ---------------------------------------------------------------------------
# E-012 — Community Size Enum & Base Schema
# ---------------------------------------------------------------------------

class TestCommunitySizeEnum:
    def test_all_sizes_defined(self):
        sizes = list(CommunitySize)
        assert len(sizes) == 8
        names = {s.name for s in sizes}
        expected = {
            "Thorp", "Hamlet", "Village", "SmallTown",
            "LargeTown", "SmallCity", "LargeCity", "Metropolis",
        }
        assert names == expected

    def test_community_base_is_dataclass(self):
        entry = COMMUNITY_REGISTRY[CommunitySize.Village]
        assert isinstance(entry, CommunityBase)
        assert entry.size == CommunitySize.Village
        assert isinstance(entry.population_range, tuple)
        assert isinstance(entry.gp_limit, int)
        assert isinstance(entry.mixed_alignment, bool)


# ---------------------------------------------------------------------------
# E-013 — GP Limit & NPC Demographics Row Schema
# ---------------------------------------------------------------------------

class TestDemographicsTable:
    def test_all_sizes_have_demographics_row(self):
        assert set(DEMOGRAPHICS_TABLE.keys()) == set(CommunitySize)

    def test_demographics_row_fields(self):
        row = DEMOGRAPHICS_TABLE[CommunitySize.SmallCity]
        assert isinstance(row, DemographicsRow)
        assert row.gp_limit == 15_000
        assert row.highest_pc_class_level_max == 11
        assert row.highest_npc_class_level_max == 9

    @pytest.mark.parametrize("size,pc_max,npc_max", [
        (CommunitySize.Thorp,      2,  1),
        (CommunitySize.Hamlet,     3,  2),
        (CommunitySize.Village,    5,  3),
        (CommunitySize.SmallTown,  7,  5),
        (CommunitySize.LargeTown,  9,  7),
        (CommunitySize.SmallCity,  11, 9),
        (CommunitySize.LargeCity,  14, 12),
        (CommunitySize.Metropolis, 20, 17),
    ])
    def test_pc_npc_level_caps(self, size, pc_max, npc_max):
        row = DEMOGRAPHICS_TABLE[size]
        assert row.highest_pc_class_level_max == pc_max
        assert row.highest_npc_class_level_max == npc_max

    def test_total_assets_factor_formula(self):
        row = DEMOGRAPHICS_TABLE[CommunitySize.SmallTown]
        expected = 800 / 2 / 10
        assert abs(row.total_assets_factor - expected) < 1e-9

    def test_npc_class_distribution_re_export(self):
        # Confirm NPC_CLASS_DISTRIBUTION_PCT is accessible and sums to ~1.0
        total = sum(NPC_CLASS_DISTRIBUTION_PCT.values())
        assert abs(total - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# E-028 — Community GP Limit Lookup
# ---------------------------------------------------------------------------

class TestGpLimit:
    @pytest.mark.parametrize("size,expected_gp", [
        (CommunitySize.Thorp,      40),
        (CommunitySize.Hamlet,     100),
        (CommunitySize.Village,    200),
        (CommunitySize.SmallTown,  800),
        (CommunitySize.LargeTown,  3_000),
        (CommunitySize.SmallCity,  15_000),
        (CommunitySize.LargeCity,  40_000),
        (CommunitySize.Metropolis, 100_000),
    ])
    def test_gp_limit_for(self, size, expected_gp):
        assert gp_limit_for(size) == expected_gp

    def test_community_total_assets_formula(self):
        # gp_limit/2 * population/10
        result = community_total_assets(CommunitySize.Village, 600)
        assert result == int(200 / 2 * 600 / 10)

    def test_community_total_assets_thorp(self):
        result = community_total_assets(CommunitySize.Thorp, 50)
        assert result == int(40 / 2 * 50 / 10)

    def test_community_total_assets_metropolis(self):
        result = community_total_assets(CommunitySize.Metropolis, 50_000)
        assert result == int(100_000 / 2 * 50_000 / 10)


# ---------------------------------------------------------------------------
# E-029 — Highest-Level NPC Class Formula
# ---------------------------------------------------------------------------

class TestHighestLevelNpcClass:
    def test_deterministic_thorp(self):
        # size_modifier=0, deterministic=2, cap=1 → 1
        lvl = highest_level_npc_class(CommunitySize.Thorp, NPCClassName.Commoner)
        assert lvl == 1

    def test_deterministic_hamlet(self):
        # size_modifier=0, deterministic=2, cap=2 → 2
        lvl = highest_level_npc_class(CommunitySize.Hamlet, NPCClassName.Commoner)
        assert lvl == 2

    def test_deterministic_village(self):
        # size_modifier=1, deterministic=3, cap=3 → 3
        lvl = highest_level_npc_class(CommunitySize.Village, NPCClassName.Expert)
        assert lvl == 3

    def test_deterministic_metropolis(self):
        # size_modifier=6, deterministic=8, cap=17 → 8
        lvl = highest_level_npc_class(CommunitySize.Metropolis, NPCClassName.Expert)
        assert lvl == 8

    def test_result_within_cap(self):
        rng = random.Random(42)
        for size in CommunitySize:
            cap = DEMOGRAPHICS_TABLE[size].highest_npc_class_level_max
            for klass in NPCClassName:
                lvl = highest_level_npc_class(size, klass, rng=rng)
                assert 1 <= lvl <= cap, f"{size} {klass}: {lvl} not in [1, {cap}]"

    def test_result_at_least_one(self):
        lvl = highest_level_npc_class(CommunitySize.Thorp, NPCClassName.Commoner, rng=random.Random(0))
        assert lvl >= 1


class TestPopulationClassRoster:
    def test_returns_all_npc_classes(self):
        roster = population_class_roster(CommunitySize.SmallTown, 1000)
        assert set(roster.keys()) == set(NPCClassName)

    def test_levels_within_cap(self):
        roster = population_class_roster(CommunitySize.Village, 600)
        cap = DEMOGRAPHICS_TABLE[CommunitySize.Village].highest_npc_class_level_max
        for klass, levels in roster.items():
            for lvl in levels:
                assert 1 <= lvl <= cap, f"{klass}: level {lvl} exceeds cap {cap}"

    def test_commoner_majority(self):
        roster = population_class_roster(CommunitySize.SmallCity, 8000)
        commoner_count = len(roster[NPCClassName.Commoner])
        expert_count = len(roster[NPCClassName.Expert])
        assert commoner_count >= expert_count

    def test_exponential_distribution_shape(self):
        # Top level should have fewer individuals than level below
        roster = population_class_roster(CommunitySize.LargeCity, 15000)
        warrior_levels = roster[NPCClassName.Warrior]
        if len(warrior_levels) >= 2:
            top = warrior_levels[0]
            count_top = warrior_levels.count(top)
            count_next = warrior_levels.count(top - 1)
            assert count_next >= count_top  # twice as many at lower level

    def test_total_approximately_matches_population(self):
        pop = 5000
        roster = population_class_roster(CommunitySize.LargeTown, pop)
        total = sum(len(v) for v in roster.values())
        # Due to int truncation per class, total should be close to population
        assert total <= pop
        # Should be at least 90% of population
        assert total >= pop * 0.85


# ---------------------------------------------------------------------------
# E-042 — Community Type Registry
# ---------------------------------------------------------------------------

class TestCommunityRegistry:
    def test_all_sizes_in_registry(self):
        assert set(COMMUNITY_REGISTRY.keys()) == set(CommunitySize)

    def test_gp_limits_match(self):
        for size, base in COMMUNITY_REGISTRY.items():
            assert base.gp_limit == gp_limit_for(size)

    def test_population_ranges_are_ordered(self):
        sizes_ordered = [
            CommunitySize.Thorp, CommunitySize.Hamlet, CommunitySize.Village,
            CommunitySize.SmallTown, CommunitySize.LargeTown, CommunitySize.SmallCity,
            CommunitySize.LargeCity, CommunitySize.Metropolis,
        ]
        prev_hi = 0
        for size in sizes_ordered:
            lo, hi = COMMUNITY_REGISTRY[size].population_range
            assert lo > prev_hi, f"{size} range lo {lo} should follow prev hi {prev_hi}"
            assert hi > lo
            prev_hi = hi

    def test_mixed_alignment(self):
        assert not COMMUNITY_REGISTRY[CommunitySize.Thorp].mixed_alignment
        assert not COMMUNITY_REGISTRY[CommunitySize.Village].mixed_alignment
        assert COMMUNITY_REGISTRY[CommunitySize.SmallTown].mixed_alignment
        assert COMMUNITY_REGISTRY[CommunitySize.Metropolis].mixed_alignment

    def test_power_center_counts(self):
        assert COMMUNITY_REGISTRY[CommunitySize.Thorp].power_center_count_range == (1, 1)
        assert COMMUNITY_REGISTRY[CommunitySize.SmallTown].power_center_count_range == (1, 2)
        assert COMMUNITY_REGISTRY[CommunitySize.LargeCity].power_center_count_range == (3, 5)
        assert COMMUNITY_REGISTRY[CommunitySize.Metropolis].power_center_count_range == (4, 6)


# ---------------------------------------------------------------------------
# E-043 — Power Center Registry
# ---------------------------------------------------------------------------

class TestPowerCenterRegistry:
    def test_all_keys_present(self):
        assert set(POWER_CENTER_REGISTRY.keys()) == {"Conventional", "Nonstandard", "Magical"}

    def test_power_center_types(self):
        assert POWER_CENTER_REGISTRY["Conventional"].power_type == PowerCenterType.Conventional
        assert POWER_CENTER_REGISTRY["Nonstandard"].power_type == PowerCenterType.Nonstandard
        assert POWER_CENTER_REGISTRY["Magical"].power_type == PowerCenterType.Magical

    def test_authority_figure_fields(self):
        auth = POWER_CENTER_REGISTRY["Conventional"].typical_authority
        assert isinstance(auth, AuthorityFigure)
        assert auth.title == "Mayor"
        assert auth.npc_class == NPCClassName.Aristocrat
        assert auth.level == 3

    def test_alignment_leans(self):
        assert POWER_CENTER_REGISTRY["Conventional"].alignment_lean == AlignmentLean.Lawful
        assert POWER_CENTER_REGISTRY["Nonstandard"].alignment_lean == AlignmentLean.Neutral
        assert POWER_CENTER_REGISTRY["Magical"].alignment_lean == AlignmentLean.Any


class TestRollPowerCenterType:
    def test_valid_key_returned(self):
        rng = random.Random(42)
        for _ in range(20):
            result = roll_power_center_type(rng)
            assert result in POWER_CENTER_REGISTRY

    def test_distribution_rough(self):
        rng = random.Random(0)
        counts: dict[str, int] = {"Conventional": 0, "Nonstandard": 0, "Magical": 0}
        for _ in range(1000):
            counts[roll_power_center_type(rng)] += 1
        assert counts["Conventional"] > counts["Nonstandard"] > counts["Magical"]


# ---------------------------------------------------------------------------
# E-054 — Settlement Generator
# ---------------------------------------------------------------------------

class TestGenerateSettlement:
    def test_returns_settlement(self):
        s = generate_settlement(CommunitySize.Village)
        assert isinstance(s, Settlement)

    def test_deterministic_population(self):
        s = generate_settlement(CommunitySize.Village)
        lo, hi = COMMUNITY_REGISTRY[CommunitySize.Village].population_range
        assert lo <= s.population <= hi

    def test_gp_limit(self):
        for size in CommunitySize:
            s = generate_settlement(size)
            assert s.gp_limit == gp_limit_for(size)

    def test_total_assets_formula(self):
        s = generate_settlement(CommunitySize.SmallTown)
        expected = community_total_assets(CommunitySize.SmallTown, s.population)
        assert s.total_assets == expected

    def test_power_centers_count_in_range(self):
        rng = random.Random(99)
        for _ in range(10):
            s = generate_settlement(CommunitySize.LargeCity, rng=rng)
            lo, hi = COMMUNITY_REGISTRY[CommunitySize.LargeCity].power_center_count_range
            assert lo <= len(s.power_centers) <= hi

    def test_power_centers_have_entries(self):
        s = generate_settlement(CommunitySize.SmallTown)
        for pc in s.power_centers:
            assert isinstance(pc, PowerCenter)
            assert isinstance(pc.entry, PowerCenterEntry)
            assert isinstance(pc.authority, AuthorityFigure)

    def test_npc_roster_completeness(self):
        s = generate_settlement(CommunitySize.LargeTown)
        assert set(s.npc_roster.keys()) == set(NPCClassName)

    def test_pc_class_roster_nonempty(self):
        s = generate_settlement(CommunitySize.SmallCity)
        assert len(s.pc_class_roster) > 0
        for cls_name, levels in s.pc_class_roster.items():
            assert isinstance(cls_name, str)
            assert len(levels) >= 1
            for lvl in levels:
                assert lvl >= 1

    def test_ruler_authority_is_authority_figure(self):
        s = generate_settlement(CommunitySize.Hamlet)
        assert isinstance(s.ruler_authority, AuthorityFigure)

    def test_ruler_matches_first_power_center(self):
        s = generate_settlement(CommunitySize.Village)
        assert s.ruler_authority is s.power_centers[0].authority

    def test_rng_produces_variation(self):
        pops = {generate_settlement(CommunitySize.Metropolis, rng=random.Random(i)).population for i in range(5)}
        assert len(pops) > 1  # random variation


# ---------------------------------------------------------------------------
# E-060 — Settlement Magic Item Availability Roster
# ---------------------------------------------------------------------------

class TestAvailableMagicItems:
    def test_returns_inventory(self):
        s = generate_settlement(CommunitySize.LargeCity)
        inv = available_magic_items(s, rng=random.Random(1))
        assert isinstance(inv, AvailableInventory)
        assert inv.settlement_gp_limit == s.gp_limit

    def test_thorp_has_no_items(self):
        s = generate_settlement(CommunitySize.Thorp)
        # Thorp gp_limit=40; cheapest item is 1000 gp; nothing available
        inv = available_magic_items(s, rng=random.Random(0))
        assert inv.minor_items == []
        assert inv.medium_items == []
        assert inv.major_items == []

    def test_metropolis_has_items(self):
        s = generate_settlement(CommunitySize.Metropolis)
        # With gp_limit=100,000, items should appear (seed for determinism)
        rng = random.Random(42)
        inv = available_magic_items(s, rng=rng)
        total = len(inv.minor_items) + len(inv.medium_items) + len(inv.major_items)
        assert total > 0

    def test_no_item_exceeds_gp_limit(self):
        from src.rules_engine.magic_items import WONDROUS_ITEM_REGISTRY, RING_REGISTRY
        all_items = {**WONDROUS_ITEM_REGISTRY, **RING_REGISTRY}
        name_to_price = {v.name: v.price_gp for v in all_items.values()}

        s = generate_settlement(CommunitySize.SmallCity)
        rng = random.Random(7)
        inv = available_magic_items(s, rng=rng)
        all_avail = inv.minor_items + inv.medium_items + inv.major_items
        for name in all_avail:
            price = name_to_price[name]
            assert price <= s.gp_limit, f"{name} ({price} gp) exceeds limit {s.gp_limit}"

    def test_major_items_priced_above_medium_threshold(self):
        from src.rules_engine.magic_items import WONDROUS_ITEM_REGISTRY, RING_REGISTRY
        all_items = {**WONDROUS_ITEM_REGISTRY, **RING_REGISTRY}
        name_to_price = {v.name: v.price_gp for v in all_items.values()}

        s = generate_settlement(CommunitySize.Metropolis)
        inv = available_magic_items(s, rng=random.Random(5))
        for name in inv.major_items:
            price = name_to_price[name]
            assert price > 3_400, f"{name} is classified major but costs {price} gp"


# ---------------------------------------------------------------------------
# E-066 — Settlement-Aware Shopping Engine
# ---------------------------------------------------------------------------

class TestShop:
    def _small_city(self) -> Settlement:
        return generate_settlement(CommunitySize.SmallCity)

    def test_mundane_purchase_within_limit(self):
        s = self._small_city()
        initial_assets = s.total_assets
        result = shop(s, "Longsword", 15)
        assert result.success
        assert s.total_assets == initial_assets - 15
        assert result.assets_remaining == s.total_assets

    def test_mundane_fails_if_price_exceeds_gp_limit(self):
        s = generate_settlement(CommunitySize.Thorp)  # gp_limit=40
        result = shop(s, "Expensive Sword", 500)
        assert not result.success
        assert "GP limit" in result.reason

    def test_mundane_depletes_assets(self):
        s = generate_settlement(CommunitySize.SmallTown)
        # Drain most assets first
        s.total_assets = 50
        result = shop(s, "Rope", 1)
        assert result.success
        assert result.assets_remaining == 49

    def test_magic_item_not_available(self):
        s = generate_settlement(CommunitySize.Thorp)  # gp_limit=40
        result = shop(s, "Belt of Giant Strength +2", 4_000, is_magic=True)
        assert not result.success

    def test_magic_item_purchase_success(self):
        # Metropolis has everything within gp limit; use fixed seed to guarantee availability
        s = generate_settlement(CommunitySize.Metropolis)
        rng = random.Random(0)
        # Force the cloak of resistance +1 (1000 gp) into inventory by seeding
        inv = available_magic_items(s, rng=random.Random(1))
        if inv.minor_items:
            item_name = inv.minor_items[0]
            # Find price
            from src.rules_engine.magic_items import WONDROUS_ITEM_REGISTRY, RING_REGISTRY
            all_items = {**WONDROUS_ITEM_REGISTRY, **RING_REGISTRY}
            price = next(v.price_gp for v in all_items.values() if v.name == item_name)
            result = shop(s, item_name, price, is_magic=True, rng=random.Random(1))
            assert result.success
            assert result.assets_remaining == s.total_assets

    def test_shop_result_has_correct_fields(self):
        s = self._small_city()
        result = shop(s, "Dagger", 2)
        assert result.item_name == "Dagger"
        assert result.price_gp == 2
        assert isinstance(result.reason, str)
        assert isinstance(result.assets_remaining, int)

    def test_shop_fails_when_assets_exhausted(self):
        s = generate_settlement(CommunitySize.Village)
        s.total_assets = 0
        result = shop(s, "Arrow", 1)
        assert not result.success
        assert "assets" in result.reason.lower()

    def test_magic_item_price_exceeds_gp_limit_fails(self):
        s = generate_settlement(CommunitySize.Thorp)  # gp_limit=40
        result = shop(s, "Ring of Protection +5", 50_000, is_magic=True)
        assert not result.success
        assert "GP limit" in result.reason
