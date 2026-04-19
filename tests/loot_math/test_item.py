"""
tests/loot_math/test_item.py
----------------------------
Unit tests for src.loot_math.item (Item, Affix, Rarity, ItemType).
"""

import json
import pytest

from src.loot_math.item import Affix, Item, ItemType, Rarity


# ---------------------------------------------------------------------------
# Rarity
# ---------------------------------------------------------------------------

class TestRarity:
    def test_affix_budget_increases_with_rarity(self):
        budgets = [r.affix_budget for r in Rarity]
        assert budgets == sorted(budgets)

    def test_stat_multiplier_increases_with_rarity(self):
        multipliers = [r.stat_multiplier for r in Rarity]
        assert multipliers == sorted(multipliers)

    def test_legendary_has_max_budget(self):
        assert Rarity.LEGENDARY.affix_budget >= max(r.affix_budget for r in Rarity)

    def test_display_colour_is_hex_string(self):
        for rarity in Rarity:
            colour = rarity.display_colour
            assert colour.startswith("#")
            assert len(colour) == 7


# ---------------------------------------------------------------------------
# Affix
# ---------------------------------------------------------------------------

class TestAffix:
    def test_affix_creation(self):
        a = Affix(name="Flaming", stat="fire_damage", value=15, is_prefix=True)
        assert a.name == "Flaming"
        assert a.stat == "fire_damage"
        assert a.value == 15
        assert a.is_prefix is True

    def test_affix_default_is_prefix(self):
        a = Affix(name="Shiny", stat="magic_find", value=5)
        assert a.is_prefix is True

    def test_affix_to_dict_round_trip(self):
        a = Affix(name="of Haste", stat="attack_speed", value=0.1, is_prefix=False)
        restored = Affix.from_dict(a.to_dict())
        assert restored.name == a.name
        assert restored.stat == a.stat
        assert restored.value == a.value
        assert restored.is_prefix == a.is_prefix

    def test_affix_repr(self):
        a = Affix(name="Flaming", stat="fire_damage", value=10)
        assert "Prefix" in repr(a)
        assert "Flaming" in repr(a)


# ---------------------------------------------------------------------------
# Item construction
# ---------------------------------------------------------------------------

class TestItemConstruction:
    def test_name_stored(self):
        item = Item(name="Iron Sword")
        assert item.name == "Iron Sword"

    def test_default_rarity_common(self):
        item = Item(name="Stick")
        assert item.rarity == Rarity.COMMON

    def test_default_item_type_weapon(self):
        item = Item(name="Dagger")
        assert item.item_type == ItemType.WEAPON

    def test_item_id_auto_generated(self):
        item = Item(name="Bow")
        assert isinstance(item.item_id, str) and len(item.item_id) == 36

    def test_explicit_item_id(self):
        item = Item(name="Bow", item_id="fixed-id-456")
        assert item.item_id == "fixed-id-456"

    def test_too_many_affixes_raises(self):
        prefix = Affix(name="Flaming", stat="fire_damage", value=15)
        suffix = Affix(name="of Speed", stat="attack_speed", value=0.1, is_prefix=False)
        # COMMON has 0 affix budget
        with pytest.raises(ValueError):
            Item(
                name="Iron Sword",
                rarity=Rarity.COMMON,
                prefixes=[prefix],
            )

    def test_too_many_prefixes_raises(self):
        p1 = Affix(name="Flaming", stat="fire_damage", value=10)
        p2 = Affix(name="Icy", stat="ice_damage", value=10)
        p3 = Affix(name="Toxic", stat="poison_damage", value=10)
        with pytest.raises(ValueError):
            Item(
                name="Sword",
                rarity=Rarity.LEGENDARY,
                prefixes=[p1, p2, p3],
            )

    def test_durability_auto_set_from_max(self):
        item = Item(name="Pickaxe", item_type=ItemType.TOOL, max_durability=100)
        assert item.durability == 100

    def test_no_durability_by_default(self):
        item = Item(name="Potion", item_type=ItemType.CONSUMABLE)
        assert item.durability is None


# ---------------------------------------------------------------------------
# Derived properties
# ---------------------------------------------------------------------------

class TestItemDerivedProperties:
    def test_display_name_no_affixes(self):
        item = Item(name="Iron Sword")
        assert item.display_name == "Iron Sword"

    def test_display_name_with_prefix(self):
        prefix = Affix(name="Flaming", stat="fire_damage", value=10)
        item = Item(name="Iron Sword", rarity=Rarity.UNCOMMON, prefixes=[prefix])
        assert item.display_name == "Flaming Iron Sword"

    def test_display_name_with_suffix(self):
        suffix = Affix(name="of Haste", stat="attack_speed", value=0.1, is_prefix=False)
        item = Item(name="Iron Sword", rarity=Rarity.UNCOMMON, suffixes=[suffix])
        assert item.display_name == "Iron Sword of Haste"

    def test_display_name_with_both(self):
        prefix = Affix(name="Flaming", stat="fire_damage", value=10)
        suffix = Affix(name="of Haste", stat="attack_speed", value=0.1, is_prefix=False)
        item = Item(
            name="Iron Sword",
            rarity=Rarity.RARE,
            prefixes=[prefix],
            suffixes=[suffix],
        )
        assert item.display_name == "Flaming Iron Sword of Haste"

    def test_effective_damage_scales_with_rarity(self):
        common = Item(name="Sword", rarity=Rarity.COMMON, base_damage=10)
        legendary = Item(name="Sword", rarity=Rarity.LEGENDARY, base_damage=10)
        assert legendary.effective_damage > common.effective_damage

    def test_effective_armour_scales_with_rarity(self):
        common = Item(name="Shield", item_type=ItemType.ARMOUR, rarity=Rarity.COMMON, base_armour=20)
        rare = Item(name="Shield", item_type=ItemType.ARMOUR, rarity=Rarity.RARE, base_armour=20)
        assert rare.effective_armour > common.effective_armour

    def test_total_stat_aggregates_affixes(self):
        p = Affix(name="Flaming", stat="fire_damage", value=10)
        s = Affix(name="Scorching", stat="fire_damage", value=5, is_prefix=False)
        item = Item(name="Sword", rarity=Rarity.RARE, prefixes=[p], suffixes=[s])
        assert item.total_stat("fire_damage") == 15

    def test_total_stat_missing_returns_zero(self):
        item = Item(name="Sword")
        assert item.total_stat("ice_damage") == 0

    def test_has_stat_true(self):
        p = Affix(name="Flaming", stat="fire_damage", value=10)
        item = Item(name="Sword", rarity=Rarity.UNCOMMON, prefixes=[p])
        assert item.has_stat("fire_damage") is True

    def test_has_stat_false(self):
        item = Item(name="Sword")
        assert item.has_stat("fire_damage") is False

    def test_all_affixes_combined(self):
        p = Affix(name="Flaming", stat="fire_damage", value=10)
        s = Affix(name="of Speed", stat="attack_speed", value=0.1, is_prefix=False)
        item = Item(name="Sword", rarity=Rarity.RARE, prefixes=[p], suffixes=[s])
        assert len(item.all_affixes) == 2


# ---------------------------------------------------------------------------
# use() / repair() / is_broken()
# ---------------------------------------------------------------------------

class TestItemMutation:
    def test_use_reduces_durability(self):
        item = Item(name="Pick", item_type=ItemType.TOOL, max_durability=100)
        result = item.use(10)
        assert result == 90
        assert item.durability == 90

    def test_use_clamps_at_zero(self):
        item = Item(name="Pick", item_type=ItemType.TOOL, max_durability=100)
        item.use(9999)
        assert item.durability == 0
        assert item.is_broken() is True

    def test_use_negative_raises(self):
        item = Item(name="Pick", item_type=ItemType.TOOL, max_durability=100)
        with pytest.raises(ValueError):
            item.use(-1)

    def test_use_no_durability_returns_none(self):
        item = Item(name="Potion", item_type=ItemType.CONSUMABLE)
        assert item.use() is None

    def test_repair_restores_durability(self):
        item = Item(name="Sword", item_type=ItemType.WEAPON, max_durability=100)
        item.use(40)
        item.repair(20)
        assert item.durability == 80

    def test_repair_capped_at_max(self):
        item = Item(name="Sword", item_type=ItemType.WEAPON, max_durability=100)
        item.use(10)
        item.repair(9999)
        assert item.durability == 100

    def test_repair_negative_raises(self):
        item = Item(name="Sword", item_type=ItemType.WEAPON, max_durability=100)
        with pytest.raises(ValueError):
            item.repair(-5)

    def test_is_broken_false_when_durability_positive(self):
        item = Item(name="Sword", item_type=ItemType.WEAPON, max_durability=100)
        assert item.is_broken() is False

    def test_is_broken_false_when_no_durability(self):
        item = Item(name="Gem", item_type=ItemType.MATERIAL)
        assert item.is_broken() is False


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

class TestItemSerialisation:
    def test_to_dict_round_trip(self):
        prefix = Affix(name="Flaming", stat="fire_damage", value=10)
        original = Item(
            name="Iron Sword",
            item_type=ItemType.WEAPON,
            rarity=Rarity.UNCOMMON,
            base_damage=20,
            prefixes=[prefix],
        )
        restored = Item.from_dict(original.to_dict())
        assert restored.item_id == original.item_id
        assert restored.name == original.name
        assert restored.rarity == original.rarity
        assert len(restored.prefixes) == 1
        assert restored.prefixes[0].name == "Flaming"

    def test_to_json_round_trip(self):
        original = Item(name="Shield", item_type=ItemType.ARMOUR, rarity=Rarity.RARE, base_armour=30)
        json_str = original.to_json()
        assert isinstance(json_str, str)
        restored = Item.from_json(json_str)
        assert restored.item_id == original.item_id
        assert restored.base_armour == original.base_armour

    def test_json_is_valid_json(self):
        item = Item(name="Magic Ring", item_type=ItemType.TRINKET)
        parsed = json.loads(item.to_json())
        assert parsed["name"] == "Magic Ring"
        assert parsed["item_type"] == "TRINKET"


# ---------------------------------------------------------------------------
# Equality and hashing
# ---------------------------------------------------------------------------

class TestItemEquality:
    def test_same_id_equal(self):
        a = Item(name="Sword", item_id="same-id")
        b = Item(name="Dagger", item_id="same-id")
        assert a == b

    def test_different_id_not_equal(self):
        a = Item(name="Sword")
        b = Item(name="Sword")
        assert a != b

    def test_hashable_in_set(self):
        item = Item(name="Axe")
        item_set = {item}
        assert item in item_set

    def test_repr_contains_name(self):
        item = Item(name="Long Bow")
        assert "Long Bow" in repr(item)
