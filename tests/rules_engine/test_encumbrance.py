"""
tests/rules_engine/test_encumbrance.py
----------------------------------------
Unit tests for the D&D 3.5e Encumbrance subsystem.

Covers E-001:
  * ``LoadCategory`` enum values and ordering.
  * ``LiftCategory`` enum values.
  * ``Item.weight_lb`` field presence, default, and round-trip serialisation.
  * ``CarryingCapacityRow`` dataclass construction and slot enforcement.
"""

import pytest

from src.loot_math.item import Item, ItemType, Rarity
from src.rules_engine.encumbrance import CarryingCapacityRow, LiftCategory, LoadCategory


# ---------------------------------------------------------------------------
# LoadCategory tests
# ---------------------------------------------------------------------------

class TestLoadCategory:
    """E-001: LoadCategory enum must have exactly four members."""

    def test_members_exist(self):
        assert LoadCategory.Light is not None
        assert LoadCategory.Medium is not None
        assert LoadCategory.Heavy is not None
        assert LoadCategory.Overload is not None

    def test_exactly_four_members(self):
        assert len(LoadCategory) == 4

    def test_members_are_unique(self):
        values = [m.value for m in LoadCategory]
        assert len(values) == len(set(values))

    def test_ordering_by_value(self):
        """Light < Medium < Heavy < Overload by enum declaration order."""
        members = list(LoadCategory)
        assert members[0] == LoadCategory.Light
        assert members[1] == LoadCategory.Medium
        assert members[2] == LoadCategory.Heavy
        assert members[3] == LoadCategory.Overload

    def test_is_enum(self):
        from enum import Enum
        assert issubclass(LoadCategory, Enum)


# ---------------------------------------------------------------------------
# LiftCategory tests
# ---------------------------------------------------------------------------

class TestLiftCategory:
    """E-001: LiftCategory enum must have exactly three members."""

    def test_members_exist(self):
        assert LiftCategory.LiftOverHead is not None
        assert LiftCategory.LiftOffGround is not None
        assert LiftCategory.PushOrDrag is not None

    def test_exactly_three_members(self):
        assert len(LiftCategory) == 3

    def test_members_are_unique(self):
        values = [m.value for m in LiftCategory]
        assert len(values) == len(set(values))

    def test_is_enum(self):
        from enum import Enum
        assert issubclass(LiftCategory, Enum)


# ---------------------------------------------------------------------------
# Item.weight_lb field tests
# ---------------------------------------------------------------------------

class TestItemWeightField:
    """E-001: Item dataclass must expose weight_lb field."""

    def test_default_weight_is_zero(self):
        item = Item(name="Pebble", item_type=ItemType.MATERIAL)
        assert item.weight_lb == 0.0

    def test_custom_weight_stored(self):
        item = Item(name="Longsword", item_type=ItemType.WEAPON, weight_lb=4.0)
        assert item.weight_lb == 4.0

    def test_weight_accepts_fractional_pounds(self):
        item = Item(name="Dagger", item_type=ItemType.WEAPON, weight_lb=1.0)
        assert item.weight_lb == 1.0

    def test_weight_zero_point_five(self):
        item = Item(name="Dart", item_type=ItemType.WEAPON, weight_lb=0.5)
        assert item.weight_lb == 0.5

    def test_to_dict_includes_weight(self):
        item = Item(name="Greataxe", item_type=ItemType.WEAPON, weight_lb=12.0)
        d = item.to_dict()
        assert "weight_lb" in d
        assert d["weight_lb"] == 12.0

    def test_from_dict_restores_weight(self):
        item = Item(name="Greataxe", item_type=ItemType.WEAPON, weight_lb=12.0)
        restored = Item.from_dict(item.to_dict())
        assert restored.weight_lb == 12.0

    def test_from_dict_missing_weight_defaults_zero(self):
        """Backwards-compatible: old dicts without weight_lb → 0.0."""
        item = Item(name="Sword", item_type=ItemType.WEAPON)
        d = item.to_dict()
        del d["weight_lb"]
        restored = Item.from_dict(d)
        assert restored.weight_lb == 0.0

    def test_to_json_round_trip_preserves_weight(self):
        item = Item(name="Chain Mail", item_type=ItemType.ARMOUR,
                    base_armour=5, weight_lb=40.0)
        restored = Item.from_json(item.to_json())
        assert restored.weight_lb == 40.0

    def test_weight_is_float_type(self):
        item = Item(name="Shield", item_type=ItemType.ARMOUR, weight_lb=15.0)
        assert isinstance(item.weight_lb, float)


# ---------------------------------------------------------------------------
# CarryingCapacityRow tests
# ---------------------------------------------------------------------------

class TestCarryingCapacityRow:
    """E-002 (scaffolded here): CarryingCapacityRow dataclass structure."""

    def test_construction(self):
        row = CarryingCapacityRow(
            strength=10,
            light_max_lb=33.0,
            medium_max_lb=66.0,
            heavy_max_lb=100.0,
        )
        assert row.strength == 10
        assert row.light_max_lb == 33.0
        assert row.medium_max_lb == 66.0
        assert row.heavy_max_lb == 100.0

    def test_slots_prevents_new_attributes(self):
        row = CarryingCapacityRow(
            strength=8,
            light_max_lb=26.0,
            medium_max_lb=53.0,
            heavy_max_lb=80.0,
        )
        with pytest.raises(AttributeError):
            row.new_field = "forbidden"  # type: ignore[attr-defined]

    def test_str_18_values(self):
        """PHB Table 9-1: STR 18 → light 100, medium 200, heavy 300."""
        row = CarryingCapacityRow(
            strength=18,
            light_max_lb=100.0,
            medium_max_lb=200.0,
            heavy_max_lb=300.0,
        )
        assert row.light_max_lb == 100.0
        assert row.medium_max_lb == 200.0
        assert row.heavy_max_lb == 300.0

    def test_str_1_values(self):
        """PHB Table 9-1: STR 1 → light 3.33, medium 6.66, heavy 10."""
        row = CarryingCapacityRow(
            strength=1,
            light_max_lb=3.0,
            medium_max_lb=6.0,
            heavy_max_lb=10.0,
        )
        assert row.strength == 1


# ===========================================================================
# NEW TESTS — E-016 through E-047
# ===========================================================================

from typing import Optional

from src.rules_engine.character_35e import Character35e, Size
from src.rules_engine.equipment import EquipmentManager, EquipmentSlot
from src.rules_engine.encumbrance import (
    CARRYING_CAPACITY_TABLE,
    EQUIPMENT_WEIGHT_REGISTRY,
    EncumbranceState,
    LoadPenalties,
    apply_load_penalties,
    apply_load_to_voxel_speed,
    carrying_capacity,
    coin_weight,
    compute_encumbrance_state,
    resolve_load_category,
    total_carried_weight,
    voxel_speed_from_feet,
)


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _make_character(strength: int = 10, size: Size = Size.MEDIUM,
                    base_speed: int = 30) -> Character35e:
    return Character35e(
        name="Test", char_class="Fighter", level=1,
        strength=strength, size=size, base_speed=base_speed,
    )


def _make_weapon(weight: float, name: str = "Sword") -> Item:
    return Item(name=name, item_type=ItemType.WEAPON, weight_lb=weight)


def _make_armor(weight: float, name: str = "Armor",
                armor_category: str = "none",
                acp: int = 0,
                max_dex: Optional[int] = None) -> Item:
    meta = {"armor_category": armor_category,
            "armor_check_penalty": acp}
    if max_dex is not None:
        meta["max_dex_bonus"] = max_dex
    return Item(name=name, item_type=ItemType.ARMOUR,
                base_armour=5, weight_lb=weight, metadata=meta)


# ---------------------------------------------------------------------------
# TestItemWeightAggregator (E-016)
# ---------------------------------------------------------------------------

class TestItemWeightAggregator:
    """E-016: total_carried_weight and coin_weight."""

    def test_empty_character_zero_weight(self):
        char = _make_character()
        assert total_carried_weight(char) == 0.0

    def test_single_item(self):
        char = _make_character()
        mgr = EquipmentManager()
        mgr.equip_item(_make_weapon(4.0, "Longsword"), EquipmentSlot.MAIN_HAND)
        char.equipment_manager = mgr
        assert total_carried_weight(char) == 4.0

    def test_multiple_items_summed(self):
        char = _make_character()
        mgr = EquipmentManager()
        mgr.equip_item(_make_weapon(4.0, "Longsword"), EquipmentSlot.MAIN_HAND)
        mgr.equip_item(_make_armor(40.0, "Chain Mail", "medium"), EquipmentSlot.TORSO)
        char.equipment_manager = mgr
        assert total_carried_weight(char) == 44.0

    def test_coin_weight_50_gp_equals_1_lb(self):
        assert coin_weight({"gp": 50}) == 1.0

    def test_coin_weight_mixed(self):
        assert coin_weight({"gp": 25, "sp": 25}) == 1.0

    def test_coin_weight_zero(self):
        assert coin_weight({}) == 0.0

    def test_coin_weight_unknown_key_ignored(self):
        assert coin_weight({"gp": 50, "diamond": 1}) == 1.0

    def test_coins_included_in_total(self):
        char = _make_character()
        char.metadata["coins"] = {"gp": 100}
        assert total_carried_weight(char) == 2.0

    def test_items_plus_coins(self):
        char = _make_character()
        mgr = EquipmentManager()
        mgr.equip_item(_make_weapon(4.0, "Longsword"), EquipmentSlot.MAIN_HAND)
        char.equipment_manager = mgr
        char.metadata["coins"] = {"gp": 50}
        assert total_carried_weight(char) == 5.0

    def test_rounded_to_nearest_tenth(self):
        char = _make_character()
        char.metadata["coins"] = {"gp": 1}  # 1/50 = 0.02
        mgr = EquipmentManager()
        mgr.equip_item(_make_weapon(0.0, "Dart"), EquipmentSlot.MAIN_HAND)
        char.equipment_manager = mgr
        result = total_carried_weight(char)
        assert result == round(result, 1)


# ---------------------------------------------------------------------------
# TestCarryingCapacity (E-017)
# ---------------------------------------------------------------------------

class TestCarryingCapacity:
    """E-017: carrying_capacity lookup and computation."""

    def test_str10_medium_biped(self):
        row = carrying_capacity(10, Size.MEDIUM)
        assert row.light_max_lb == 33.0
        assert row.medium_max_lb == 66.0
        assert row.heavy_max_lb == 100.0

    def test_str18_medium_biped(self):
        row = carrying_capacity(18, Size.MEDIUM)
        assert row.light_max_lb == 100.0
        assert row.medium_max_lb == 200.0
        assert row.heavy_max_lb == 300.0

    def test_str1_medium_biped(self):
        row = carrying_capacity(1, Size.MEDIUM)
        assert row.light_max_lb == 3.0
        assert row.heavy_max_lb == 10.0

    def test_str29_medium_biped(self):
        row = carrying_capacity(29, Size.MEDIUM)
        assert row.light_max_lb == 466.0
        assert row.heavy_max_lb == 1400.0

    def test_str30_is_4x_str29(self):
        row29 = carrying_capacity(29, Size.MEDIUM)
        row30 = carrying_capacity(30, Size.MEDIUM)
        assert abs(row30.heavy_max_lb - row29.heavy_max_lb * 4) < 1.0

    def test_str40_is_16x_str29(self):
        row29 = carrying_capacity(29, Size.MEDIUM)
        row40 = carrying_capacity(40, Size.MEDIUM)
        assert abs(row40.heavy_max_lb - row29.heavy_max_lb * 16) < 1.0

    def test_large_size_doubles(self):
        med = carrying_capacity(10, Size.MEDIUM)
        lrg = carrying_capacity(10, Size.LARGE)
        assert abs(lrg.heavy_max_lb - med.heavy_max_lb * 2) < 0.1

    def test_small_size_three_quarters(self):
        med = carrying_capacity(10, Size.MEDIUM)
        sm  = carrying_capacity(10, Size.SMALL)
        assert abs(sm.heavy_max_lb - med.heavy_max_lb * 0.75) < 0.1

    def test_tiny_size_half(self):
        med = carrying_capacity(10, Size.MEDIUM)
        tiny = carrying_capacity(10, Size.TINY)
        assert abs(tiny.heavy_max_lb - med.heavy_max_lb * 0.5) < 0.1

    def test_huge_size_4x(self):
        med  = carrying_capacity(10, Size.MEDIUM)
        huge = carrying_capacity(10, Size.HUGE)
        assert abs(huge.heavy_max_lb - med.heavy_max_lb * 4) < 0.1

    def test_quadruped_1_5x(self):
        biped = carrying_capacity(10, Size.MEDIUM, quadruped=False)
        quad  = carrying_capacity(10, Size.MEDIUM, quadruped=True)
        assert abs(quad.heavy_max_lb - biped.heavy_max_lb * 1.5) < 0.1

    def test_returns_carrying_capacity_row(self):
        result = carrying_capacity(10, Size.MEDIUM)
        assert isinstance(result, CarryingCapacityRow)

    def test_all_str_1_through_29_present(self):
        for s in range(1, 30):
            row = carrying_capacity(s, Size.MEDIUM)
            assert row.strength == s


# ---------------------------------------------------------------------------
# TestLoadCategoryResolver (E-018)
# ---------------------------------------------------------------------------

class TestLoadCategoryResolver:
    """E-018: resolve_load_category boundary conditions."""

    def test_str10_zero_is_light(self):
        row = CARRYING_CAPACITY_TABLE[10]
        assert resolve_load_category(0.0, row) == LoadCategory.Light

    def test_str10_at_light_max_is_light(self):
        row = CARRYING_CAPACITY_TABLE[10]
        assert resolve_load_category(33.0, row) == LoadCategory.Light

    def test_str10_above_light_is_medium(self):
        row = CARRYING_CAPACITY_TABLE[10]
        assert resolve_load_category(33.1, row) == LoadCategory.Medium

    def test_str10_at_medium_max_is_medium(self):
        row = CARRYING_CAPACITY_TABLE[10]
        assert resolve_load_category(66.0, row) == LoadCategory.Medium

    def test_str10_above_medium_is_heavy(self):
        row = CARRYING_CAPACITY_TABLE[10]
        assert resolve_load_category(66.1, row) == LoadCategory.Heavy

    def test_str10_at_heavy_max_is_heavy(self):
        row = CARRYING_CAPACITY_TABLE[10]
        assert resolve_load_category(100.0, row) == LoadCategory.Heavy

    def test_str10_above_heavy_is_overload(self):
        row = CARRYING_CAPACITY_TABLE[10]
        assert resolve_load_category(100.1, row) == LoadCategory.Overload

    def test_str18_light_boundary(self):
        row = CARRYING_CAPACITY_TABLE[18]
        assert resolve_load_category(100.0, row) == LoadCategory.Light
        assert resolve_load_category(100.1, row) == LoadCategory.Medium


# ---------------------------------------------------------------------------
# TestLoadPenalties (E-019)
# ---------------------------------------------------------------------------

class TestLoadPenalties:
    """E-019: apply_load_penalties returns correct LoadPenalties."""

    def test_light_no_penalties(self):
        p = apply_load_penalties(LoadCategory.Light)
        assert p.max_dex_to_ac is None
        assert p.armor_check_penalty == 0
        assert p.speed_table == {}
        assert p.run_multiplier == 4

    def test_medium_penalties(self):
        p = apply_load_penalties(LoadCategory.Medium)
        assert p.max_dex_to_ac == 3
        assert p.armor_check_penalty == -3
        assert p.speed_table[30] == 20
        assert p.speed_table[20] == 15
        assert p.run_multiplier == 4

    def test_heavy_penalties(self):
        p = apply_load_penalties(LoadCategory.Heavy)
        assert p.max_dex_to_ac == 1
        assert p.armor_check_penalty == -6
        assert p.speed_table[30] == 20
        assert p.run_multiplier == 3

    def test_overload_penalties(self):
        p = apply_load_penalties(LoadCategory.Overload)
        assert p.max_dex_to_ac == 0
        assert p.armor_check_penalty == -6

    def test_returns_load_penalties_instance(self):
        assert isinstance(apply_load_penalties(LoadCategory.Light), LoadPenalties)

    def test_load_penalties_has_slots(self):
        p = apply_load_penalties(LoadCategory.Light)
        with pytest.raises(AttributeError):
            p.nonexistent_field = 99  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# TestVoxelSpeed (E-020)
# ---------------------------------------------------------------------------

class TestVoxelSpeed:
    """E-020: voxel_speed_from_feet and apply_load_to_voxel_speed."""

    def test_30ft_is_6_voxels(self):
        assert voxel_speed_from_feet(30) == 6

    def test_20ft_is_4_voxels(self):
        assert voxel_speed_from_feet(20) == 4

    def test_zero_ft_is_zero_voxels(self):
        assert voxel_speed_from_feet(0) == 0

    def test_custom_voxel_size(self):
        assert voxel_speed_from_feet(30, voxel_ft_per_unit=10) == 3

    def test_light_load_no_change(self):
        result = apply_load_to_voxel_speed(6, LoadCategory.Light)
        assert result == 6

    def test_medium_load_no_armor_reduces_speed(self):
        result = apply_load_to_voxel_speed(6, LoadCategory.Medium, "none")
        assert result == 4  # 30ft → 20ft → 4 voxels

    def test_heavy_load_no_armor_reduces_speed(self):
        result = apply_load_to_voxel_speed(6, LoadCategory.Heavy, "none")
        assert result == 4  # 30ft → 20ft → 4 voxels

    def test_overload_zero_speed(self):
        result = apply_load_to_voxel_speed(6, LoadCategory.Overload)
        assert result == 0

    def test_medium_load_with_medium_armor_no_double_penalty(self):
        result = apply_load_to_voxel_speed(6, LoadCategory.Medium, "medium")
        assert result == 6  # no extra reduction

    def test_heavy_load_with_heavy_armor_no_double_penalty(self):
        result = apply_load_to_voxel_speed(6, LoadCategory.Heavy, "heavy")
        assert result == 6

    def test_light_armor_still_applies_load_penalty(self):
        result = apply_load_to_voxel_speed(6, LoadCategory.Medium, "light")
        assert result == 4

    def test_invalid_voxel_size_raises(self):
        with pytest.raises(ValueError):
            voxel_speed_from_feet(30, voxel_ft_per_unit=0)


# ---------------------------------------------------------------------------
# TestEquipmentWeightRegistry (E-034)
# ---------------------------------------------------------------------------

class TestEquipmentWeightRegistry:
    """E-034: EQUIPMENT_WEIGHT_REGISTRY completeness and spot-checks."""

    def test_minimum_180_entries(self):
        assert len(EQUIPMENT_WEIGHT_REGISTRY) >= 180

    def test_longsword_weight(self):
        assert EQUIPMENT_WEIGHT_REGISTRY["Longsword"] == 4.0

    def test_greatsword_weight(self):
        assert EQUIPMENT_WEIGHT_REGISTRY["Greatsword"] == 8.0

    def test_dagger_weight(self):
        assert EQUIPMENT_WEIGHT_REGISTRY["Dagger"] == 1.0

    def test_shortbow_weight(self):
        assert EQUIPMENT_WEIGHT_REGISTRY["Shortbow"] == 2.0

    def test_longbow_weight(self):
        assert EQUIPMENT_WEIGHT_REGISTRY["Longbow"] == 3.0

    def test_handaxe_weight(self):
        assert EQUIPMENT_WEIGHT_REGISTRY["Handaxe"] == 3.0

    def test_greataxe_weight(self):
        assert EQUIPMENT_WEIGHT_REGISTRY["Greataxe"] == 12.0

    def test_quarterstaff_weight(self):
        assert EQUIPMENT_WEIGHT_REGISTRY["Quarterstaff"] == 4.0

    def test_rapier_weight(self):
        assert EQUIPMENT_WEIGHT_REGISTRY["Rapier"] == 2.0

    def test_leather_armor_weight(self):
        assert EQUIPMENT_WEIGHT_REGISTRY["Leather Armor"] == 15.0

    def test_chain_shirt_weight(self):
        assert EQUIPMENT_WEIGHT_REGISTRY["Chain Shirt"] == 25.0

    def test_full_plate_weight(self):
        assert EQUIPMENT_WEIGHT_REGISTRY["Full Plate"] == 50.0

    def test_buckler_weight(self):
        assert EQUIPMENT_WEIGHT_REGISTRY["Buckler"] == 5.0

    def test_backpack_weight(self):
        assert EQUIPMENT_WEIGHT_REGISTRY["Backpack"] == 2.0

    def test_rope_hemp_weight(self):
        assert EQUIPMENT_WEIGHT_REGISTRY["Rope Hemp 50ft"] == 10.0

    def test_rope_silk_weight(self):
        assert EQUIPMENT_WEIGHT_REGISTRY["Rope Silk 50ft"] == 5.0

    def test_torch_weight(self):
        assert EQUIPMENT_WEIGHT_REGISTRY["Torch"] == 1.0

    def test_lantern_bullseye_weight(self):
        assert EQUIPMENT_WEIGHT_REGISTRY["Lantern Bullseye"] == 3.0

    def test_rations_trail_weight(self):
        assert EQUIPMENT_WEIGHT_REGISTRY["Rations Trail"] == 1.0

    def test_waterskin_weight(self):
        assert EQUIPMENT_WEIGHT_REGISTRY["Waterskin"] == 4.0

    def test_bedroll_weight(self):
        assert EQUIPMENT_WEIGHT_REGISTRY["Bedroll"] == 5.0

    def test_tent_weight(self):
        assert EQUIPMENT_WEIGHT_REGISTRY["Tent"] == 20.0

    def test_all_values_non_negative(self):
        for k, v in EQUIPMENT_WEIGHT_REGISTRY.items():
            assert v >= 0.0, f"{k} has negative weight {v}"

    def test_all_values_are_floats(self):
        for k, v in EQUIPMENT_WEIGHT_REGISTRY.items():
            assert isinstance(v, (int, float)), f"{k} is not numeric"


# ---------------------------------------------------------------------------
# TestCarryingCapacityTable (E-035)
# ---------------------------------------------------------------------------

class TestCarryingCapacityTable:
    """E-035: CARRYING_CAPACITY_TABLE completeness and spot-checks."""

    def test_has_all_29_entries(self):
        assert len(CARRYING_CAPACITY_TABLE) == 29

    def test_keys_are_1_through_29(self):
        assert set(CARRYING_CAPACITY_TABLE.keys()) == set(range(1, 30))

    def test_str1_values(self):
        row = CARRYING_CAPACITY_TABLE[1]
        assert row.light_max_lb == 3.0
        assert row.medium_max_lb == 6.0
        assert row.heavy_max_lb == 10.0

    def test_str10_values(self):
        row = CARRYING_CAPACITY_TABLE[10]
        assert row.light_max_lb == 33.0
        assert row.medium_max_lb == 66.0
        assert row.heavy_max_lb == 100.0

    def test_str18_values(self):
        row = CARRYING_CAPACITY_TABLE[18]
        assert row.light_max_lb == 100.0
        assert row.medium_max_lb == 200.0
        assert row.heavy_max_lb == 300.0

    def test_str20_values(self):
        row = CARRYING_CAPACITY_TABLE[20]
        assert row.light_max_lb == 133.0
        assert row.medium_max_lb == 266.0
        assert row.heavy_max_lb == 400.0

    def test_str29_values(self):
        row = CARRYING_CAPACITY_TABLE[29]
        assert row.light_max_lb == 466.0
        assert row.medium_max_lb == 933.0
        assert row.heavy_max_lb == 1400.0

    def test_each_row_strength_matches_key(self):
        for k, v in CARRYING_CAPACITY_TABLE.items():
            assert v.strength == k

    def test_light_less_than_medium(self):
        for row in CARRYING_CAPACITY_TABLE.values():
            assert row.light_max_lb < row.medium_max_lb

    def test_medium_less_than_heavy(self):
        for row in CARRYING_CAPACITY_TABLE.values():
            assert row.medium_max_lb < row.heavy_max_lb

    def test_all_rows_are_carrying_capacity_row(self):
        for row in CARRYING_CAPACITY_TABLE.values():
            assert isinstance(row, CarryingCapacityRow)

    def test_str5_values(self):
        row = CARRYING_CAPACITY_TABLE[5]
        assert row.light_max_lb == 16.0
        assert row.medium_max_lb == 33.0
        assert row.heavy_max_lb == 50.0

    def test_str15_values(self):
        row = CARRYING_CAPACITY_TABLE[15]
        assert row.light_max_lb == 66.0
        assert row.medium_max_lb == 133.0
        assert row.heavy_max_lb == 200.0


# ---------------------------------------------------------------------------
# TestEncumbranceState (E-047)
# ---------------------------------------------------------------------------

class TestEncumbranceState:
    """E-047: compute_encumbrance_state integration tests."""

    def test_unencumbered_character_light_load(self):
        char = _make_character(strength=10, base_speed=30)
        state = compute_encumbrance_state(char)
        assert state.load == LoadCategory.Light
        assert state.total_weight_lb == 0.0

    def test_light_load_full_speed(self):
        char = _make_character(strength=10, base_speed=30)
        state = compute_encumbrance_state(char)
        assert state.effective_speed_ft == 30
        assert state.effective_speed_voxel == 6

    def test_medium_load_reduces_speed(self):
        char = _make_character(strength=10, base_speed=30)
        mgr = EquipmentManager()
        # STR 10 light=33, medium=66 — put 50 lb in main hand
        mgr.equip_item(_make_weapon(50.0, "HeavyThing"), EquipmentSlot.MAIN_HAND)
        char.equipment_manager = mgr
        state = compute_encumbrance_state(char)
        assert state.load == LoadCategory.Medium
        assert state.effective_speed_ft == 20
        assert state.effective_speed_voxel == 4

    def test_heavy_load_reduces_speed_and_run(self):
        char = _make_character(strength=10, base_speed=30)
        mgr = EquipmentManager()
        mgr.equip_item(_make_weapon(90.0, "HugeLoad"), EquipmentSlot.MAIN_HAND)
        char.equipment_manager = mgr
        state = compute_encumbrance_state(char)
        assert state.load == LoadCategory.Heavy
        assert state.effective_speed_ft == 20
        assert state.penalties.run_multiplier == 3

    def test_overload_zero_speed(self):
        char = _make_character(strength=10, base_speed=30)
        mgr = EquipmentManager()
        mgr.equip_item(_make_weapon(200.0, "ImpossibleLoad"), EquipmentSlot.MAIN_HAND)
        char.equipment_manager = mgr
        state = compute_encumbrance_state(char)
        assert state.load == LoadCategory.Overload
        assert state.effective_speed_ft == 0
        assert state.effective_speed_voxel == 0

    def test_acp_stacks_armor_and_load(self):
        char = _make_character(strength=10, base_speed=30)
        mgr = EquipmentManager()
        mgr.equip_item(
            _make_armor(40.0, "Chain Mail", "medium", acp=5),
            EquipmentSlot.TORSO,
        )
        mgr.equip_item(_make_weapon(60.0, "OverloadWeapon"), EquipmentSlot.MAIN_HAND)
        char.equipment_manager = mgr
        state = compute_encumbrance_state(char)
        # load is Medium (33 < 100 <= 66? no: 100 > 66, so Heavy)
        # armor_acp=5, load_acp=-6
        assert state.armor_check_penalty_total == 5 + state.penalties.armor_check_penalty

    def test_max_dex_most_restrictive(self):
        char = _make_character(strength=18, base_speed=30)
        mgr = EquipmentManager()
        mgr.equip_item(
            _make_armor(50.0, "Full Plate", "heavy", acp=8, max_dex=1),
            EquipmentSlot.TORSO,
        )
        char.equipment_manager = mgr
        state = compute_encumbrance_state(char)
        # Light load; armor max_dex=1 → combined cap = 1
        assert state.max_dex_to_ac_after_armor == 1

    def test_no_max_dex_cap_for_light_load_no_armor(self):
        char = _make_character(strength=18, base_speed=30)
        state = compute_encumbrance_state(char)
        assert state.max_dex_to_ac_after_armor is None

    def test_encumbrance_state_is_dataclass(self):
        char = _make_character()
        state = compute_encumbrance_state(char)
        assert isinstance(state, EncumbranceState)

    def test_medium_armor_no_double_speed_penalty(self):
        char = _make_character(strength=18, base_speed=30)
        mgr = EquipmentManager()
        mgr.equip_item(
            _make_armor(40.0, "Chain Mail", "medium", acp=5),
            EquipmentSlot.TORSO,
        )
        # Add medium load weight (STR 18: light=100, medium=200)
        mgr.equip_item(_make_weapon(150.0, "HeavyPack"), EquipmentSlot.MAIN_HAND)
        char.equipment_manager = mgr
        state = compute_encumbrance_state(char)
        # Load is Medium; armor is medium → no double speed penalty
        assert state.effective_speed_ft == 30

    def test_coins_included_in_weight(self):
        char = _make_character(strength=10, base_speed=30)
        char.metadata["coins"] = {"gp": 2000}  # 40 lb
        state = compute_encumbrance_state(char)
        assert state.total_weight_lb == 40.0

    def test_capacity_reflects_strength(self):
        char = _make_character(strength=20, base_speed=30)
        state = compute_encumbrance_state(char)
        assert state.capacity.strength == 20
        assert state.capacity.heavy_max_lb == 400.0


# ---------------------------------------------------------------------------
# TestApplyEncumbranceToCombatState (E-063)
# ---------------------------------------------------------------------------

from src.rules_engine.encumbrance import apply_encumbrance_to_combat_state


class _FakeCombatState:
    """Minimal stand-in for CombatState used in E-063 tests."""
    def __init__(self, tick: int = 0):
        self.tick = tick


class TestApplyEncumbranceToCombatState:
    """E-063: apply_encumbrance_to_combat_state writes encumbrance metadata."""

    def test_returns_combat_state_unchanged(self):
        char = _make_character(strength=18, base_speed=30)
        cs = _FakeCombatState(tick=5)
        result = apply_encumbrance_to_combat_state(char, cs)
        assert result is cs
        assert result.tick == 5

    def test_light_load_no_max_dex_cap(self):
        char = _make_character(strength=18, base_speed=30)
        apply_encumbrance_to_combat_state(char, _FakeCombatState())
        assert char.metadata["load_max_dex_cap"] is None

    def test_medium_load_max_dex_cap_three(self):
        char = _make_character(strength=10, base_speed=30)
        mgr = EquipmentManager()
        mgr.equip_item(_make_weapon(50.0, "HeavyThing"), EquipmentSlot.MAIN_HAND)
        char.equipment_manager = mgr
        apply_encumbrance_to_combat_state(char, _FakeCombatState())
        assert char.metadata["load_max_dex_cap"] == 3

    def test_heavy_load_max_dex_cap_one(self):
        char = _make_character(strength=10, base_speed=30)
        mgr = EquipmentManager()
        mgr.equip_item(_make_weapon(90.0, "HugeLoad"), EquipmentSlot.MAIN_HAND)
        char.equipment_manager = mgr
        apply_encumbrance_to_combat_state(char, _FakeCombatState())
        assert char.metadata["load_max_dex_cap"] == 1

    def test_voxel_speed_written_to_metadata(self):
        char = _make_character(strength=10, base_speed=30)
        apply_encumbrance_to_combat_state(char, _FakeCombatState())
        assert "enc_voxel_speed" in char.metadata
        assert char.metadata["enc_voxel_speed"] == 6  # 30 ft / 5

    def test_voxel_speed_reduced_for_medium_load(self):
        char = _make_character(strength=10, base_speed=30)
        mgr = EquipmentManager()
        mgr.equip_item(_make_weapon(50.0, "HeavyThing"), EquipmentSlot.MAIN_HAND)
        char.equipment_manager = mgr
        apply_encumbrance_to_combat_state(char, _FakeCombatState())
        assert char.metadata["enc_voxel_speed"] == 4  # 20 ft / 5

    def test_overload_stationary_flag(self):
        char = _make_character(strength=10, base_speed=30)
        mgr = EquipmentManager()
        mgr.equip_item(_make_weapon(200.0, "ImpossibleLoad"), EquipmentSlot.MAIN_HAND)
        char.equipment_manager = mgr
        apply_encumbrance_to_combat_state(char, _FakeCombatState())
        assert char.metadata["enc_stationary"] is True
        assert char.metadata["enc_voxel_speed"] == 0

    def test_light_load_not_stationary(self):
        char = _make_character(strength=18, base_speed=30)
        apply_encumbrance_to_combat_state(char, _FakeCombatState())
        assert char.metadata["enc_stationary"] is False

    def test_voxel_speed_property_uses_metadata(self):
        """After apply_..., character.voxel_speed returns enc_voxel_speed."""
        char = _make_character(strength=10, base_speed=30)
        mgr = EquipmentManager()
        mgr.equip_item(_make_weapon(50.0, "HeavyThing"), EquipmentSlot.MAIN_HAND)
        char.equipment_manager = mgr
        apply_encumbrance_to_combat_state(char, _FakeCombatState())
        assert char.voxel_speed == 4

    def test_armor_class_respects_load_max_dex(self):
        """Heavy load (max_dex +1) caps Dex bonus to AC."""
        char = _make_character(strength=10, base_speed=30)
        char.dexterity = 20  # +5 dex mod without any cap
        mgr = EquipmentManager()
        mgr.equip_item(_make_weapon(90.0, "HugeLoad"), EquipmentSlot.MAIN_HAND)
        char.equipment_manager = mgr
        apply_encumbrance_to_combat_state(char, _FakeCombatState())
        # AC should cap dex at +1, not +5
        assert char.armor_class == 10 + 1  # 10 + min(+5, +1)

    def test_load_acp_written_to_metadata(self):
        char = _make_character(strength=10, base_speed=30)
        mgr = EquipmentManager()
        mgr.equip_item(_make_weapon(50.0, "HeavyThing"), EquipmentSlot.MAIN_HAND)
        char.equipment_manager = mgr
        apply_encumbrance_to_combat_state(char, _FakeCombatState())
        assert char.metadata["load_acp"] == -3  # Medium load ACP
