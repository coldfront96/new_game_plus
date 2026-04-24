"""
tests/rules_engine/test_objects.py
------------------------------------
Pytest suite for src/rules_engine/objects.py.

Covers T-001 (material schema), T-012 (break DC), T-013 (damage / state).
"""

from __future__ import annotations

import pytest

from src.rules_engine.objects import (
    MATERIAL_STATS,
    DamageType,
    MaterialType,
    ObjectMaterial,
    ObjectState,
    SizeCategory,
    apply_damage_to_object,
    calculate_break_dc,
)


# ---------------------------------------------------------------------------
# T-001: MaterialType enum membership
# ---------------------------------------------------------------------------

class TestMaterialTypeEnum:
    def test_all_nine_members(self):
        members = {m.value for m in MaterialType}
        assert members == {
            "wood", "stone", "iron", "steel", "mithral",
            "adamantine", "crystal", "rope", "glass",
        }

    def test_each_member_accessible(self):
        for name in ("WOOD", "STONE", "IRON", "STEEL", "MITHRAL",
                     "ADAMANTINE", "CRYSTAL", "ROPE", "GLASS"):
            assert hasattr(MaterialType, name)


# ---------------------------------------------------------------------------
# T-001: MATERIAL_STATS completeness and values
# ---------------------------------------------------------------------------

class TestMaterialStats:
    def test_all_materials_present(self):
        assert set(MATERIAL_STATS.keys()) == set(MaterialType)

    def test_returns_object_material_instances(self):
        for mat, stats in MATERIAL_STATS.items():
            assert isinstance(stats, ObjectMaterial)
            assert stats.material_type is mat

    # Spot-check table values from DMG Table 3-3
    def test_wood_values(self):
        s = MATERIAL_STATS[MaterialType.WOOD]
        assert s.hardness == 5
        assert s.hp_per_inch == 10
        assert s.break_dc == 15

    def test_stone_values(self):
        s = MATERIAL_STATS[MaterialType.STONE]
        assert s.hardness == 8
        assert s.hp_per_inch == 15
        assert s.break_dc == 28

    def test_iron_values(self):
        s = MATERIAL_STATS[MaterialType.IRON]
        assert s.hardness == 10
        assert s.hp_per_inch == 30
        assert s.break_dc == 28

    def test_steel_values(self):
        s = MATERIAL_STATS[MaterialType.STEEL]
        assert s.hardness == 10
        assert s.hp_per_inch == 30
        assert s.break_dc == 30

    def test_mithral_values(self):
        s = MATERIAL_STATS[MaterialType.MITHRAL]
        assert s.hardness == 15
        assert s.hp_per_inch == 30
        assert s.break_dc == 28

    def test_adamantine_values(self):
        s = MATERIAL_STATS[MaterialType.ADAMANTINE]
        assert s.hardness == 20
        assert s.hp_per_inch == 40
        assert s.break_dc == 35

    def test_crystal_values(self):
        s = MATERIAL_STATS[MaterialType.CRYSTAL]
        assert s.hardness == 1
        assert s.hp_per_inch == 4
        assert s.break_dc == 12

    def test_rope_values(self):
        s = MATERIAL_STATS[MaterialType.ROPE]
        assert s.hardness == 0
        assert s.hp_per_inch == 2
        assert s.break_dc == 23

    def test_glass_values(self):
        s = MATERIAL_STATS[MaterialType.GLASS]
        assert s.hardness == 1
        assert s.hp_per_inch == 1
        assert s.break_dc == 10

    def test_slots_no_dict(self):
        """ObjectMaterial uses __slots__ — no __dict__."""
        s = MATERIAL_STATS[MaterialType.WOOD]
        assert not hasattr(s, "__dict__")


# ---------------------------------------------------------------------------
# T-012: calculate_break_dc
# ---------------------------------------------------------------------------

class TestCalculateBreakDC:
    def test_base_dc_1_inch_medium(self):
        # No thickness bonus, no size modifier
        assert calculate_break_dc(MaterialType.WOOD, 1, SizeCategory.MEDIUM) == 15

    def test_thickness_adds_5_per_extra_inch(self):
        # Wood base 15 + 5*(3-1) = 25
        assert calculate_break_dc(MaterialType.WOOD, 3, SizeCategory.MEDIUM) == 25

    def test_thickness_2_inches(self):
        # Steel base 30 + 5 = 35
        assert calculate_break_dc(MaterialType.STEEL, 2, SizeCategory.MEDIUM) == 35

    def test_size_large_adds_4(self):
        assert calculate_break_dc(MaterialType.WOOD, 1, SizeCategory.LARGE) == 19

    def test_size_small_subtracts_4(self):
        assert calculate_break_dc(MaterialType.WOOD, 1, SizeCategory.SMALL) == 11

    def test_size_fine(self):
        assert calculate_break_dc(MaterialType.WOOD, 1, SizeCategory.FINE) == 15 - 16

    def test_size_colossal(self):
        assert calculate_break_dc(MaterialType.WOOD, 1, SizeCategory.COLOSSAL) == 15 + 16

    def test_size_huge(self):
        assert calculate_break_dc(MaterialType.STONE, 1, SizeCategory.HUGE) == 28 + 8

    def test_all_size_categories_accepted(self):
        for sz in SizeCategory:
            result = calculate_break_dc(MaterialType.IRON, 1, sz)
            assert isinstance(result, int)

    def test_adamantine_large_2inch(self):
        # 35 + 5 + 4 = 44
        assert calculate_break_dc(MaterialType.ADAMANTINE, 2, SizeCategory.LARGE) == 44


# ---------------------------------------------------------------------------
# T-013: apply_damage_to_object — immunity and resistance rules
# ---------------------------------------------------------------------------

class TestApplyDamageFireImmunity:
    def test_fire_immune_stone(self):
        hp, state = apply_damage_to_object(MaterialType.STONE, 30, 20, DamageType.FIRE)
        assert hp == 30
        assert state == ObjectState.INTACT

    def test_fire_immune_iron(self):
        hp, _ = apply_damage_to_object(MaterialType.IRON, 30, 20, DamageType.FIRE)
        assert hp == 30

    def test_fire_immune_steel(self):
        hp, _ = apply_damage_to_object(MaterialType.STEEL, 30, 20, DamageType.FIRE)
        assert hp == 30

    def test_fire_immune_mithral(self):
        hp, _ = apply_damage_to_object(MaterialType.MITHRAL, 30, 20, DamageType.FIRE)
        assert hp == 30

    def test_fire_immune_adamantine(self):
        hp, _ = apply_damage_to_object(MaterialType.ADAMANTINE, 30, 20, DamageType.FIRE)
        assert hp == 30

    def test_fire_damages_wood(self):
        # Wood hardness 5; 20 fire → effective 15; 30-15=15 which equals hp//2 → BROKEN
        hp, state = apply_damage_to_object(MaterialType.WOOD, 30, 20, DamageType.FIRE)
        assert hp == 15
        assert state == ObjectState.BROKEN

    def test_fire_damages_rope(self):
        hp, _ = apply_damage_to_object(MaterialType.ROPE, 10, 6, DamageType.FIRE)
        # Rope hardness 0; 6 fire → effective 6; 10-6=4
        assert hp == 4

    def test_fire_damages_crystal(self):
        hp, _ = apply_damage_to_object(MaterialType.CRYSTAL, 8, 4, DamageType.FIRE)
        # Crystal hardness 1; 4-1=3; 8-3=5
        assert hp == 5

    def test_fire_damages_glass(self):
        hp, state = apply_damage_to_object(MaterialType.GLASS, 2, 10, DamageType.FIRE)
        assert hp == 0
        assert state == ObjectState.DESTROYED


class TestApplyDamageColdResistance:
    def test_cold_immune_wood(self):
        hp, state = apply_damage_to_object(MaterialType.WOOD, 20, 15, DamageType.COLD)
        assert hp == 20
        assert state == ObjectState.INTACT

    def test_cold_immune_iron(self):
        hp, _ = apply_damage_to_object(MaterialType.IRON, 30, 20, DamageType.COLD)
        assert hp == 30

    def test_cold_half_crystal(self):
        # Crystal hardness 1; 10 cold → 5 after half → 4 after hardness; 8-4=4
        hp, state = apply_damage_to_object(MaterialType.CRYSTAL, 8, 10, DamageType.COLD)
        assert hp == 4
        assert state == ObjectState.BROKEN

    def test_cold_half_glass(self):
        # Glass hardness 1; 8 cold → 4 after half → 3 after hardness; 6-3=3
        hp, _ = apply_damage_to_object(MaterialType.GLASS, 6, 8, DamageType.COLD)
        assert hp == 3


class TestApplyDamageElectricity:
    def test_electricity_immune_iron(self):
        hp, state = apply_damage_to_object(MaterialType.IRON, 30, 20, DamageType.ELECTRICITY)
        assert hp == 30
        assert state == ObjectState.INTACT

    def test_electricity_immune_steel(self):
        hp, _ = apply_damage_to_object(MaterialType.STEEL, 30, 20, DamageType.ELECTRICITY)
        assert hp == 30

    def test_electricity_damages_wood(self):
        # Wood hardness 5; 15 elec → 10; 20-10=10
        hp, _ = apply_damage_to_object(MaterialType.WOOD, 20, 15, DamageType.ELECTRICITY)
        assert hp == 10


class TestApplyDamageAcid:
    def test_acid_full_stone(self):
        # Stone hardness 8; 20 acid → 12; 30-12=18
        hp, _ = apply_damage_to_object(MaterialType.STONE, 30, 20, DamageType.ACID)
        assert hp == 18

    def test_acid_half_iron(self):
        # Iron hardness 10; 20 acid → 10 after half → 0 after hardness; 30-0=30
        hp, state = apply_damage_to_object(MaterialType.IRON, 30, 20, DamageType.ACID)
        assert hp == 30
        assert state == ObjectState.INTACT

    def test_acid_half_steel(self):
        # Steel hardness 10; 30 acid → 15 after half → 5 after hardness; 30-5=25
        hp, _ = apply_damage_to_object(MaterialType.STEEL, 30, 30, DamageType.ACID)
        assert hp == 25


class TestApplyDamageSonic:
    def test_sonic_full_crystal(self):
        # Crystal hardness 1; 10 sonic → 9; 20-9=11
        hp, _ = apply_damage_to_object(MaterialType.CRYSTAL, 20, 10, DamageType.SONIC)
        assert hp == 11

    def test_sonic_full_glass(self):
        # Glass hardness 1; 10 sonic → 9; 10-9=1
        hp, _ = apply_damage_to_object(MaterialType.GLASS, 10, 10, DamageType.SONIC)
        assert hp == 1

    def test_sonic_half_wood(self):
        # Wood hardness 5; 20 sonic → 10 after half → 5 after hardness; 30-5=25
        hp, _ = apply_damage_to_object(MaterialType.WOOD, 30, 20, DamageType.SONIC)
        assert hp == 25


class TestApplyDamageHardness:
    def test_hardness_absorbs_all_damage(self):
        # Iron hardness 10; 8 bludgeoning → 0 effective
        hp, state = apply_damage_to_object(MaterialType.IRON, 30, 8, DamageType.BLUDGEONING)
        assert hp == 30
        assert state == ObjectState.INTACT

    def test_physical_damage_reduced_by_hardness(self):
        # Wood hardness 5; 12 slashing → 7; 20-7=13
        hp, state = apply_damage_to_object(MaterialType.WOOD, 20, 12, DamageType.SLASHING)
        assert hp == 13
        assert state == ObjectState.DAMAGED


class TestObjectStateTransitions:
    def test_intact_when_no_damage_penetrates(self):
        _, state = apply_damage_to_object(MaterialType.IRON, 30, 5, DamageType.BLUDGEONING)
        assert state == ObjectState.INTACT

    def test_damaged_when_above_half_hp(self):
        # Wood hp=20, take 6 bludgeoning → effective 1; hp=19 > 10
        _, state = apply_damage_to_object(MaterialType.WOOD, 20, 6, DamageType.BLUDGEONING)
        assert state == ObjectState.DAMAGED

    def test_broken_when_at_or_below_half_hp(self):
        # Wood hp=20, hardness 5; 16 bludgeoning → 11; 20-11=9 ≤ 10
        _, state = apply_damage_to_object(MaterialType.WOOD, 20, 16, DamageType.BLUDGEONING)
        assert state == ObjectState.BROKEN

    def test_destroyed_when_hp_reaches_zero(self):
        hp, state = apply_damage_to_object(MaterialType.GLASS, 3, 50, DamageType.BLUDGEONING)
        assert hp == 0
        assert state == ObjectState.DESTROYED

    def test_hp_never_goes_negative(self):
        hp, _ = apply_damage_to_object(MaterialType.ROPE, 2, 100, DamageType.SLASHING)
        assert hp == 0
