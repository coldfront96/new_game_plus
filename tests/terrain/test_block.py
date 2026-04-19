"""
tests/terrain/test_block.py
---------------------------
Unit tests for src.terrain.block (Block data class and Material enum).
"""

import json
import pytest

from src.terrain.block import Block, Material, MaterialProps, MATERIAL_PROPS


# ---------------------------------------------------------------------------
# Material / MATERIAL_PROPS
# ---------------------------------------------------------------------------

class TestMaterialProps:
    def test_all_materials_have_props(self):
        for material in Material:
            assert material in MATERIAL_PROPS, f"{material} missing from MATERIAL_PROPS"

    def test_air_is_not_solid_and_zero_durability(self):
        props = MATERIAL_PROPS[Material.AIR]
        assert not props.is_solid
        assert props.base_durability == 0

    def test_lava_emits_max_light(self):
        props = MATERIAL_PROPS[Material.LAVA]
        assert props.light_emission == 15

    def test_obsidian_has_highest_blast_resistance(self):
        resistances = [p.blast_resistance for p in MATERIAL_PROPS.values()]
        assert MATERIAL_PROPS[Material.OBSIDIAN].blast_resistance == max(resistances)

    def test_fluids_are_not_solid(self):
        for material, props in MATERIAL_PROPS.items():
            if props.is_fluid:
                assert not props.is_solid, f"{material} is fluid but marked solid"


# ---------------------------------------------------------------------------
# Block construction
# ---------------------------------------------------------------------------

class TestBlockConstruction:
    def test_default_durability_set_from_material(self):
        block = Block(block_id=1, material=Material.STONE)
        assert block.durability == MATERIAL_PROPS[Material.STONE].base_durability

    def test_explicit_durability_respected(self):
        block = Block(block_id=1, material=Material.STONE, durability=50)
        assert block.durability == 50

    def test_durability_clamped_to_zero(self):
        block = Block(block_id=1, material=Material.STONE, durability=-10)
        assert block.durability == 0

    def test_durability_clamped_to_max(self):
        max_dur = MATERIAL_PROPS[Material.STONE].base_durability
        block = Block(block_id=1, material=Material.STONE, durability=max_dur + 999)
        assert block.durability == max_dur

    def test_light_level_clamped_low(self):
        block = Block(block_id=1, material=Material.STONE, light_level=-5)
        assert block.light_level == 0

    def test_light_level_clamped_high(self):
        block = Block(block_id=1, material=Material.STONE, light_level=99)
        assert block.light_level == 15

    def test_metadata_defaults_empty(self):
        block = Block(block_id=1, material=Material.DIRT)
        assert block.metadata == {}

    def test_custom_metadata_stored(self):
        block = Block(block_id=1, material=Material.DIRT, metadata={"growth": 3})
        assert block.metadata["growth"] == 3


# ---------------------------------------------------------------------------
# Derived properties
# ---------------------------------------------------------------------------

class TestBlockDerivedProperties:
    def test_is_solid_stone(self):
        block = Block(block_id=1, material=Material.STONE)
        assert block.is_solid is True

    def test_is_not_solid_air(self):
        block = Block(block_id=0, material=Material.AIR)
        assert block.is_solid is False

    def test_is_fluid_water(self):
        block = Block(block_id=7, material=Material.WATER)
        assert block.is_fluid is True

    def test_is_not_fluid_stone(self):
        block = Block(block_id=2, material=Material.STONE)
        assert block.is_fluid is False

    def test_light_emission_lava(self):
        block = Block(block_id=8, material=Material.LAVA)
        assert block.light_emission == 15

    def test_light_emission_stone(self):
        block = Block(block_id=2, material=Material.STONE)
        assert block.light_emission == 0

    def test_blast_resistance_obsidian(self):
        block = Block(block_id=12, material=Material.OBSIDIAN)
        assert block.blast_resistance == 10.0


# ---------------------------------------------------------------------------
# mine() / repair() / is_destroyed()
# ---------------------------------------------------------------------------

class TestBlockMutation:
    def test_mine_reduces_durability(self):
        block = Block(block_id=1, material=Material.STONE)
        initial = block.durability
        remaining = block.mine(30)
        assert remaining == initial - 30
        assert block.durability == initial - 30

    def test_mine_with_tool_efficiency(self):
        block = Block(block_id=1, material=Material.STONE)
        initial = block.durability
        block.mine(damage=20, tool_efficiency=2.0)
        assert block.durability == initial - 40

    def test_mine_clamps_at_zero(self):
        block = Block(block_id=1, material=Material.STONE)
        block.mine(99999)
        assert block.durability == 0

    def test_mine_negative_damage_raises(self):
        block = Block(block_id=1, material=Material.STONE)
        with pytest.raises(ValueError):
            block.mine(-5)

    def test_is_destroyed_after_full_mine(self):
        block = Block(block_id=1, material=Material.STONE)
        block.mine(99999)
        assert block.is_destroyed() is True

    def test_is_not_destroyed_when_durability_positive(self):
        block = Block(block_id=1, material=Material.STONE, durability=1)
        assert block.is_destroyed() is False

    def test_repair_restores_durability(self):
        block = Block(block_id=1, material=Material.STONE, durability=50)
        block.repair(20)
        assert block.durability == 70

    def test_repair_capped_at_max(self):
        max_dur = MATERIAL_PROPS[Material.STONE].base_durability
        block = Block(block_id=1, material=Material.STONE, durability=max_dur - 5)
        block.repair(100)
        assert block.durability == max_dur

    def test_repair_negative_raises(self):
        block = Block(block_id=1, material=Material.STONE)
        with pytest.raises(ValueError):
            block.repair(-1)


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

class TestBlockSerialisation:
    def test_to_dict_round_trip(self):
        original = Block(
            block_id=42,
            material=Material.IRON_ORE,
            durability=80,
            light_level=3,
            metadata={"vein_id": 7},
        )
        restored = Block.from_dict(original.to_dict())
        assert restored.block_id == original.block_id
        assert restored.material == original.material
        assert restored.durability == original.durability
        assert restored.light_level == original.light_level
        assert restored.metadata == original.metadata

    def test_to_json_round_trip(self):
        original = Block(block_id=5, material=Material.GOLD_ORE)
        json_str = original.to_json()
        assert isinstance(json_str, str)
        restored = Block.from_json(json_str)
        assert restored == original

    def test_json_is_valid_json(self):
        block = Block(block_id=1, material=Material.DIRT)
        parsed = json.loads(block.to_json())
        assert parsed["material"] == "DIRT"


# ---------------------------------------------------------------------------
# Equality and hashing
# ---------------------------------------------------------------------------

class TestBlockEquality:
    def test_equal_blocks(self):
        a = Block(block_id=1, material=Material.STONE)
        b = Block(block_id=1, material=Material.STONE, durability=50)
        assert a == b  # equality based on id + material only

    def test_unequal_different_id(self):
        a = Block(block_id=1, material=Material.STONE)
        b = Block(block_id=2, material=Material.STONE)
        assert a != b

    def test_unequal_different_material(self):
        a = Block(block_id=1, material=Material.STONE)
        b = Block(block_id=1, material=Material.DIRT)
        assert a != b

    def test_hashable(self):
        block = Block(block_id=1, material=Material.STONE)
        block_set = {block}
        assert block in block_set

    def test_repr_contains_key_info(self):
        block = Block(block_id=3, material=Material.DIAMOND_ORE)
        r = repr(block)
        assert "DIAMOND_ORE" in r
        assert "3" in r
