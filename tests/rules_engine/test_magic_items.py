"""
tests/rules_engine/test_magic_items.py
---------------------------------------
Unit tests for the D&D 3.5e Magic Item Engine (Phase 2 DMG).

Covers:
- MagicItemCategory and BonusType enums
- MagicBonus dataclass
- WondrousItem dataclass
- MagicItemEngine — add/remove, ability enhancement, AC bonuses, save bonuses,
  non-stacking rules
- make_magic_weapon() factory
- make_magic_armor() factory
- WONDROUS_ITEM_REGISTRY contents (29 items)
- RING_REGISTRY contents (5 rings)
- Character35e integration — ability mods, AC, saves with MagicItemEngine
- EquipmentManager — armor/shield enhancement bonuses
"""

import pytest

from src.loot_math.item import Item, ItemType
from src.rules_engine.character_35e import Character35e
from src.rules_engine.equipment import EquipmentManager, EquipmentSlot
from src.rules_engine.magic_items import (
    BonusType,
    MagicBonus,
    MagicItemCategory,
    MagicItemEngine,
    RING_REGISTRY,
    WondrousItem,
    WONDROUS_ITEM_REGISTRY,
    get_armor_enhancement_bonus,
    make_magic_armor,
    make_magic_weapon,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine():
    return MagicItemEngine()


@pytest.fixture
def belt_4():
    return WONDROUS_ITEM_REGISTRY["belt_of_giant_strength_4"]


@pytest.fixture
def cloak_resistance_2():
    return WONDROUS_ITEM_REGISTRY["cloak_of_resistance_2"]


@pytest.fixture
def ring_of_protection_3():
    return RING_REGISTRY["ring_of_protection_3"]


@pytest.fixture
def amulet_nat_armor_2():
    return WONDROUS_ITEM_REGISTRY["amulet_of_natural_armor_2"]


@pytest.fixture
def longsword():
    return Item(
        name="Longsword",
        item_type=ItemType.WEAPON,
        base_damage=4,
        metadata={"damage_dice_count": 1, "damage_dice_sides": 8},
    )


@pytest.fixture
def chain_shirt():
    return Item(
        name="Chain Shirt",
        item_type=ItemType.ARMOUR,
        base_armour=4,
    )


@pytest.fixture
def heavy_shield():
    return Item(
        name="Heavy Shield",
        item_type=ItemType.ARMOUR,
        base_armour=2,
    )


# ---------------------------------------------------------------------------
# MagicItemCategory enum
# ---------------------------------------------------------------------------

class TestMagicItemCategory:

    def test_all_categories_present(self):
        names = {c.name for c in MagicItemCategory}
        expected = {"WEAPON", "ARMOR", "SHIELD", "RING", "ROD", "STAFF",
                    "WAND", "POTION", "SCROLL", "WONDROUS"}
        assert expected.issubset(names)

    def test_wondrous_value(self):
        assert MagicItemCategory.WONDROUS.value == "wondrous"

    def test_ring_value(self):
        assert MagicItemCategory.RING.value == "ring"


# ---------------------------------------------------------------------------
# BonusType enum
# ---------------------------------------------------------------------------

class TestBonusType:

    def test_enhancement_present(self):
        assert BonusType.ENHANCEMENT.value == "enhancement"

    def test_deflection_present(self):
        assert BonusType.DEFLECTION.value == "deflection"

    def test_natural_armor_present(self):
        assert BonusType.NATURAL_ARMOR.value == "natural_armor"

    def test_resistance_present(self):
        assert BonusType.RESISTANCE.value == "resistance"


# ---------------------------------------------------------------------------
# MagicBonus dataclass
# ---------------------------------------------------------------------------

class TestMagicBonus:

    def test_slots_enabled(self):
        assert hasattr(MagicBonus, "__slots__")

    def test_fields(self):
        mb = MagicBonus(BonusType.ENHANCEMENT, "strength", 4)
        assert mb.bonus_type == BonusType.ENHANCEMENT
        assert mb.stat == "strength"
        assert mb.value == 4


# ---------------------------------------------------------------------------
# WondrousItem dataclass
# ---------------------------------------------------------------------------

class TestWondrousItem:

    def test_slots_enabled(self):
        assert hasattr(WondrousItem, "__slots__")

    def test_fields(self, belt_4):
        assert belt_4.name == "Belt of Giant Strength +4"
        assert belt_4.category == MagicItemCategory.WONDROUS
        assert belt_4.slot == "belt"
        assert belt_4.caster_level == 8
        assert belt_4.price_gp == 16_000
        assert len(belt_4.bonuses) == 1
        assert belt_4.bonuses[0].bonus_type == BonusType.ENHANCEMENT
        assert belt_4.bonuses[0].stat == "strength"
        assert belt_4.bonuses[0].value == 4


# ---------------------------------------------------------------------------
# MagicItemEngine — construction
# ---------------------------------------------------------------------------

class TestMagicItemEngineConstruction:

    def test_slots_enabled(self):
        assert hasattr(MagicItemEngine, "__slots__")

    def test_starts_empty(self, engine):
        assert engine.items == []

    def test_add_item(self, engine, belt_4):
        engine.add_item(belt_4)
        assert belt_4 in engine.items

    def test_remove_item(self, engine, belt_4):
        engine.add_item(belt_4)
        result = engine.remove_item(belt_4)
        assert result is True
        assert belt_4 not in engine.items

    def test_remove_item_not_present(self, engine, belt_4):
        result = engine.remove_item(belt_4)
        assert result is False

    def test_clear(self, engine, belt_4, cloak_resistance_2):
        engine.add_item(belt_4)
        engine.add_item(cloak_resistance_2)
        engine.clear()
        assert engine.items == []

    def test_items_returns_copy(self, engine, belt_4):
        engine.add_item(belt_4)
        lst = engine.items
        lst.append(belt_4)  # mutate the copy
        assert len(engine.items) == 1  # original unchanged


# ---------------------------------------------------------------------------
# MagicItemEngine — ability enhancement
# ---------------------------------------------------------------------------

class TestAbilityEnhancement:

    def test_strength_bonus_from_belt(self, engine, belt_4):
        engine.add_item(belt_4)
        assert engine.get_ability_enhancement("strength") == 4

    def test_strength_bonus_zero_when_empty(self, engine):
        assert engine.get_ability_enhancement("strength") == 0

    def test_dexterity_bonus(self, engine):
        engine.add_item(WONDROUS_ITEM_REGISTRY["gloves_of_dexterity_6"])
        assert engine.get_ability_enhancement("dexterity") == 6

    def test_intelligence_bonus(self, engine):
        engine.add_item(WONDROUS_ITEM_REGISTRY["headband_of_intellect_4"])
        assert engine.get_ability_enhancement("intelligence") == 4

    def test_wisdom_bonus(self, engine):
        engine.add_item(WONDROUS_ITEM_REGISTRY["periapt_of_wisdom_2"])
        assert engine.get_ability_enhancement("wisdom") == 2

    def test_charisma_bonus(self, engine):
        engine.add_item(WONDROUS_ITEM_REGISTRY["cloak_of_charisma_6"])
        assert engine.get_ability_enhancement("charisma") == 6

    def test_constitution_bonus(self, engine):
        engine.add_item(WONDROUS_ITEM_REGISTRY["amulet_of_health_4"])
        assert engine.get_ability_enhancement("constitution") == 4

    def test_non_stacking_enhancement(self, engine):
        """Two strength enhancement bonuses — only the highest applies."""
        engine.add_item(WONDROUS_ITEM_REGISTRY["belt_of_giant_strength_2"])
        engine.add_item(WONDROUS_ITEM_REGISTRY["gauntlets_of_ogre_power"])
        # Both grant +2 to STR — should return 2, not 4
        assert engine.get_ability_enhancement("strength") == 2

    def test_non_stacking_enhancement_higher_wins(self, engine):
        """Belt +4 and Gauntlets +2 — +4 wins."""
        engine.add_item(WONDROUS_ITEM_REGISTRY["belt_of_giant_strength_4"])
        engine.add_item(WONDROUS_ITEM_REGISTRY["gauntlets_of_ogre_power"])
        assert engine.get_ability_enhancement("strength") == 4

    def test_different_abilities_stack(self, engine):
        """Different ability bonuses stack (they are different stats)."""
        engine.add_item(WONDROUS_ITEM_REGISTRY["belt_of_giant_strength_4"])
        engine.add_item(WONDROUS_ITEM_REGISTRY["gloves_of_dexterity_2"])
        assert engine.get_ability_enhancement("strength") == 4
        assert engine.get_ability_enhancement("dexterity") == 2


# ---------------------------------------------------------------------------
# MagicItemEngine — AC bonuses
# ---------------------------------------------------------------------------

class TestACBonuses:

    def test_deflection_bonus_from_ring(self, engine, ring_of_protection_3):
        engine.add_item(ring_of_protection_3)
        assert engine.get_deflection_bonus() == 3

    def test_deflection_zero_when_empty(self, engine):
        assert engine.get_deflection_bonus() == 0

    def test_deflection_non_stacking(self, engine):
        """Two rings of protection — only the highest deflection applies."""
        engine.add_item(RING_REGISTRY["ring_of_protection_2"])
        engine.add_item(RING_REGISTRY["ring_of_protection_5"])
        assert engine.get_deflection_bonus() == 5

    def test_natural_armor_from_amulet(self, engine, amulet_nat_armor_2):
        engine.add_item(amulet_nat_armor_2)
        assert engine.get_natural_armor_bonus() == 2

    def test_natural_armor_zero_when_empty(self, engine):
        assert engine.get_natural_armor_bonus() == 0

    def test_natural_armor_non_stacking(self, engine):
        engine.add_item(WONDROUS_ITEM_REGISTRY["amulet_of_natural_armor_1"])
        engine.add_item(WONDROUS_ITEM_REGISTRY["amulet_of_natural_armor_5"])
        assert engine.get_natural_armor_bonus() == 5


# ---------------------------------------------------------------------------
# MagicItemEngine — saving throw bonuses
# ---------------------------------------------------------------------------

class TestSaveBonuses:

    def test_resistance_bonus_from_cloak(self, engine, cloak_resistance_2):
        engine.add_item(cloak_resistance_2)
        assert engine.get_resistance_bonus() == 2

    def test_resistance_bonus_zero_when_empty(self, engine):
        assert engine.get_resistance_bonus() == 0

    def test_resistance_non_stacking(self, engine):
        engine.add_item(WONDROUS_ITEM_REGISTRY["cloak_of_resistance_1"])
        engine.add_item(WONDROUS_ITEM_REGISTRY["cloak_of_resistance_5"])
        assert engine.get_resistance_bonus() == 5

    def test_get_save_bonus_fortitude(self, engine, cloak_resistance_2):
        engine.add_item(cloak_resistance_2)
        assert engine.get_save_bonus("fortitude") == 2

    def test_get_save_bonus_reflex(self, engine, cloak_resistance_2):
        engine.add_item(cloak_resistance_2)
        assert engine.get_save_bonus("reflex") == 2

    def test_get_save_bonus_will(self, engine, cloak_resistance_2):
        engine.add_item(cloak_resistance_2)
        assert engine.get_save_bonus("will") == 2

    def test_get_save_bonus_zero_when_empty(self, engine):
        assert engine.get_save_bonus("fortitude") == 0


# ---------------------------------------------------------------------------
# make_magic_weapon factory
# ---------------------------------------------------------------------------

class TestMakeMagicWeapon:

    def test_returns_new_item(self, longsword):
        magic = make_magic_weapon(longsword, enhancement=1)
        assert magic is not longsword

    def test_original_unchanged(self, longsword):
        make_magic_weapon(longsword, enhancement=1)
        assert "enhancement_bonus" not in longsword.metadata

    def test_enhancement_bonus_set(self, longsword):
        magic = make_magic_weapon(longsword, enhancement=3)
        assert magic.metadata["enhancement_bonus"] == 3

    def test_name_updated(self, longsword):
        magic = make_magic_weapon(longsword, enhancement=2)
        assert magic.name == "+2 Longsword"

    def test_market_price_1(self, longsword):
        magic = make_magic_weapon(longsword, enhancement=1)
        assert magic.metadata["market_price_gp"] == 2_000

    def test_market_price_2(self, longsword):
        magic = make_magic_weapon(longsword, enhancement=2)
        assert magic.metadata["market_price_gp"] == 8_000

    def test_market_price_3(self, longsword):
        magic = make_magic_weapon(longsword, enhancement=3)
        assert magic.metadata["market_price_gp"] == 18_000

    def test_market_price_4(self, longsword):
        magic = make_magic_weapon(longsword, enhancement=4)
        assert magic.metadata["market_price_gp"] == 32_000

    def test_market_price_5(self, longsword):
        magic = make_magic_weapon(longsword, enhancement=5)
        assert magic.metadata["market_price_gp"] == 50_000

    def test_price_stacks_on_base(self):
        base = Item(
            name="Masterwork Longsword",
            item_type=ItemType.WEAPON,
            base_damage=4,
            metadata={"market_price_gp": 315},
        )
        magic = make_magic_weapon(base, enhancement=1)
        assert magic.metadata["market_price_gp"] == 315 + 2_000

    def test_raises_for_non_weapon(self, chain_shirt):
        with pytest.raises(ValueError, match="WEAPON"):
            make_magic_weapon(chain_shirt, enhancement=1)

    def test_raises_for_invalid_enhancement(self, longsword):
        with pytest.raises(ValueError, match="1–5"):
            make_magic_weapon(longsword, enhancement=6)

    def test_raises_for_zero_enhancement(self, longsword):
        with pytest.raises(ValueError, match="1–5"):
            make_magic_weapon(longsword, enhancement=0)

    def test_preserves_damage_dice(self, longsword):
        magic = make_magic_weapon(longsword, enhancement=1)
        assert magic.metadata["damage_dice_count"] == 1
        assert magic.metadata["damage_dice_sides"] == 8

    def test_item_type_remains_weapon(self, longsword):
        magic = make_magic_weapon(longsword, enhancement=2)
        assert magic.item_type == ItemType.WEAPON


# ---------------------------------------------------------------------------
# make_magic_armor factory
# ---------------------------------------------------------------------------

class TestMakeMagicArmor:

    def test_returns_new_item(self, chain_shirt):
        magic = make_magic_armor(chain_shirt, enhancement=1)
        assert magic is not chain_shirt

    def test_original_unchanged(self, chain_shirt):
        make_magic_armor(chain_shirt, enhancement=1)
        assert "enhancement_bonus" not in chain_shirt.metadata

    def test_enhancement_bonus_set(self, chain_shirt):
        magic = make_magic_armor(chain_shirt, enhancement=2)
        assert magic.metadata["enhancement_bonus"] == 2

    def test_name_updated(self, chain_shirt):
        magic = make_magic_armor(chain_shirt, enhancement=1)
        assert magic.name == "+1 Chain Shirt"

    def test_market_price_1(self, chain_shirt):
        magic = make_magic_armor(chain_shirt, enhancement=1)
        assert magic.metadata["market_price_gp"] == 1_000

    def test_market_price_2(self, chain_shirt):
        magic = make_magic_armor(chain_shirt, enhancement=2)
        assert magic.metadata["market_price_gp"] == 4_000

    def test_market_price_3(self, chain_shirt):
        magic = make_magic_armor(chain_shirt, enhancement=3)
        assert magic.metadata["market_price_gp"] == 9_000

    def test_market_price_4(self, chain_shirt):
        magic = make_magic_armor(chain_shirt, enhancement=4)
        assert magic.metadata["market_price_gp"] == 16_000

    def test_market_price_5(self, chain_shirt):
        magic = make_magic_armor(chain_shirt, enhancement=5)
        assert magic.metadata["market_price_gp"] == 25_000

    def test_raises_for_non_armor(self, longsword):
        with pytest.raises(ValueError, match="ARMOUR"):
            make_magic_armor(longsword, enhancement=1)

    def test_raises_for_invalid_enhancement(self, chain_shirt):
        with pytest.raises(ValueError, match="1–5"):
            make_magic_armor(chain_shirt, enhancement=6)

    def test_base_armour_preserved(self, chain_shirt):
        magic = make_magic_armor(chain_shirt, enhancement=1)
        assert magic.base_armour == 4

    def test_item_type_remains_armor(self, chain_shirt):
        magic = make_magic_armor(chain_shirt, enhancement=1)
        assert magic.item_type == ItemType.ARMOUR


# ---------------------------------------------------------------------------
# EquipmentManager — armor enhancement bonus
# ---------------------------------------------------------------------------

class TestEquipmentManagerArmorEnhancement:

    def test_plain_armor_no_enhancement(self, chain_shirt):
        mgr = EquipmentManager()
        mgr.equip_item(chain_shirt, EquipmentSlot.TORSO)
        assert mgr.get_armor_bonus() == 4  # base_armour only

    def test_magic_armor_includes_enhancement(self, chain_shirt):
        mgr = EquipmentManager()
        magic = make_magic_armor(chain_shirt, enhancement=2)
        mgr.equip_item(magic, EquipmentSlot.TORSO)
        assert mgr.get_armor_bonus() == 6  # 4 base + 2 enhancement

    def test_plain_shield_no_enhancement(self, heavy_shield):
        mgr = EquipmentManager()
        mgr.equip_item(heavy_shield, EquipmentSlot.OFF_HAND)
        assert mgr.get_shield_bonus() == 2

    def test_magic_shield_includes_enhancement(self, heavy_shield):
        mgr = EquipmentManager()
        magic = make_magic_armor(heavy_shield, enhancement=1)
        mgr.equip_item(magic, EquipmentSlot.OFF_HAND)
        assert mgr.get_shield_bonus() == 3  # 2 base + 1 enhancement

    def test_get_armor_enhancement_bonus_helper(self, chain_shirt, heavy_shield):
        mgr = EquipmentManager()
        magic_armor = make_magic_armor(chain_shirt, enhancement=3)
        magic_shield = make_magic_armor(heavy_shield, enhancement=1)
        mgr.equip_item(magic_armor, EquipmentSlot.TORSO)
        mgr.equip_item(magic_shield, EquipmentSlot.OFF_HAND)
        total = get_armor_enhancement_bonus(mgr)
        assert total == 4  # 3 + 1


# ---------------------------------------------------------------------------
# WONDROUS_ITEM_REGISTRY contents
# ---------------------------------------------------------------------------

class TestWondrousItemRegistry:

    def test_registry_is_dict(self):
        assert isinstance(WONDROUS_ITEM_REGISTRY, dict)

    def test_has_expected_count(self):
        # 3 belts + gauntlets + 3 gloves + 3 headbands + 3 periapts +
        # 3 cloaks_cha + 3 health + 5 nat_armor + 5 resistance = 29
        assert len(WONDROUS_ITEM_REGISTRY) >= 29

    def test_belt_of_giant_strength_2_price(self):
        assert WONDROUS_ITEM_REGISTRY["belt_of_giant_strength_2"].price_gp == 4_000

    def test_belt_of_giant_strength_6_price(self):
        assert WONDROUS_ITEM_REGISTRY["belt_of_giant_strength_6"].price_gp == 36_000

    def test_gauntlets_of_ogre_power_slot(self):
        item = WONDROUS_ITEM_REGISTRY["gauntlets_of_ogre_power"]
        assert item.slot == "gloves"
        assert item.bonuses[0].value == 2

    def test_gloves_of_dexterity_4(self):
        item = WONDROUS_ITEM_REGISTRY["gloves_of_dexterity_4"]
        assert item.bonuses[0].stat == "dexterity"
        assert item.bonuses[0].value == 4

    def test_headband_of_intellect_6(self):
        item = WONDROUS_ITEM_REGISTRY["headband_of_intellect_6"]
        assert item.price_gp == 36_000
        assert item.aura == "strong transmutation"

    def test_periapt_of_wisdom_2(self):
        item = WONDROUS_ITEM_REGISTRY["periapt_of_wisdom_2"]
        assert item.slot == "neck"
        assert item.bonuses[0].stat == "wisdom"

    def test_cloak_of_charisma_4(self):
        item = WONDROUS_ITEM_REGISTRY["cloak_of_charisma_4"]
        assert item.slot == "cloak"
        assert item.bonuses[0].bonus_type == BonusType.ENHANCEMENT

    def test_amulet_of_health_6(self):
        item = WONDROUS_ITEM_REGISTRY["amulet_of_health_6"]
        assert item.bonuses[0].stat == "constitution"
        assert item.bonuses[0].value == 6

    def test_amulet_of_natural_armor_1_to_5(self):
        for bonus in range(1, 6):
            key = f"amulet_of_natural_armor_{bonus}"
            item = WONDROUS_ITEM_REGISTRY[key]
            assert item.bonuses[0].bonus_type == BonusType.NATURAL_ARMOR
            assert item.bonuses[0].value == bonus

    def test_cloak_of_resistance_1_to_5(self):
        prices = {1: 1_000, 2: 4_000, 3: 9_000, 4: 16_000, 5: 25_000}
        for bonus, price in prices.items():
            key = f"cloak_of_resistance_{bonus}"
            item = WONDROUS_ITEM_REGISTRY[key]
            assert item.price_gp == price
            assert item.bonuses[0].bonus_type == BonusType.RESISTANCE

    def test_all_wondrous_items_have_description(self):
        for key, item in WONDROUS_ITEM_REGISTRY.items():
            assert item.description, f"{key} has empty description"


# ---------------------------------------------------------------------------
# RING_REGISTRY contents
# ---------------------------------------------------------------------------

class TestRingRegistry:

    def test_ring_count(self):
        assert len(RING_REGISTRY) == 5

    def test_ring_of_protection_1(self):
        item = RING_REGISTRY["ring_of_protection_1"]
        assert item.price_gp == 2_000
        assert item.bonuses[0].bonus_type == BonusType.DEFLECTION
        assert item.bonuses[0].value == 1

    def test_ring_of_protection_5(self):
        item = RING_REGISTRY["ring_of_protection_5"]
        assert item.price_gp == 50_000
        assert item.bonuses[0].value == 5

    def test_all_rings_have_category_ring(self):
        for item in RING_REGISTRY.values():
            assert item.category == MagicItemCategory.RING

    def test_all_rings_deflection_ac(self):
        for item in RING_REGISTRY.values():
            assert item.bonuses[0].stat == "ac"


# ---------------------------------------------------------------------------
# Character35e integration — ability modifiers
# ---------------------------------------------------------------------------

class TestCharacterAbilityModIntegration:

    def test_no_engine_no_change(self):
        char = Character35e(name="Test", strength=10)
        assert char.strength_mod == 0

    def test_belt_increases_strength_mod(self):
        engine = MagicItemEngine()
        engine.add_item(WONDROUS_ITEM_REGISTRY["belt_of_giant_strength_4"])
        char = Character35e(name="Fighter", strength=16, magic_item_engine=engine)
        # STR 16 → +3; +4 enhancement → +2 delta; total = +5
        assert char.strength_mod == 5

    def test_gloves_increases_dex_mod(self):
        engine = MagicItemEngine()
        engine.add_item(WONDROUS_ITEM_REGISTRY["gloves_of_dexterity_2"])
        char = Character35e(name="Rogue", dexterity=14, magic_item_engine=engine)
        # DEX 14 → +2; +2 enhancement → +1 delta; total = +3
        assert char.dexterity_mod == 3

    def test_amulet_of_health_increases_con_mod(self):
        engine = MagicItemEngine()
        engine.add_item(WONDROUS_ITEM_REGISTRY["amulet_of_health_4"])
        char = Character35e(name="Tank", constitution=12, magic_item_engine=engine)
        # CON 12 → +1; +4 enhancement → +2 delta; total = +3
        assert char.constitution_mod == 3

    def test_headband_increases_int_mod(self):
        engine = MagicItemEngine()
        engine.add_item(WONDROUS_ITEM_REGISTRY["headband_of_intellect_6"])
        char = Character35e(name="Wizard", intelligence=18, magic_item_engine=engine)
        # INT 18 → +4; +6 enhancement → +3 delta; total = +7
        assert char.intelligence_mod == 7

    def test_periapt_increases_wis_mod(self):
        engine = MagicItemEngine()
        engine.add_item(WONDROUS_ITEM_REGISTRY["periapt_of_wisdom_2"])
        char = Character35e(name="Cleric", wisdom=14, magic_item_engine=engine)
        assert char.wisdom_mod == 3

    def test_cloak_of_charisma_increases_cha_mod(self):
        engine = MagicItemEngine()
        engine.add_item(WONDROUS_ITEM_REGISTRY["cloak_of_charisma_6"])
        char = Character35e(name="Bard", charisma=16, magic_item_engine=engine)
        # CHA 16 → +3; +6 enhancement → +3 delta; total = +6
        assert char.charisma_mod == 6

    def test_hit_points_increase_with_con_enhancement(self):
        engine = MagicItemEngine()
        engine.add_item(WONDROUS_ITEM_REGISTRY["amulet_of_health_4"])
        char_with = Character35e(
            name="With", char_class="Fighter", level=5,
            constitution=10, magic_item_engine=engine,
        )
        char_without = Character35e(
            name="Without", char_class="Fighter", level=5, constitution=10,
        )
        # +4 CON → +2 CON mod → +10 HP over 5 levels
        assert char_with.hit_points == char_without.hit_points + 10


# ---------------------------------------------------------------------------
# Character35e integration — AC
# ---------------------------------------------------------------------------

class TestCharacterACIntegration:

    def test_no_engine_no_ac_change(self):
        char = Character35e(name="Test", dexterity=10)
        assert char.armor_class == 10

    def test_ring_of_protection_increases_ac(self):
        engine = MagicItemEngine()
        engine.add_item(RING_REGISTRY["ring_of_protection_3"])
        char = Character35e(name="Fighter", dexterity=10, magic_item_engine=engine)
        assert char.armor_class == 13  # 10 + 3 deflection

    def test_amulet_of_natural_armor_increases_ac(self):
        engine = MagicItemEngine()
        engine.add_item(WONDROUS_ITEM_REGISTRY["amulet_of_natural_armor_2"])
        char = Character35e(name="Ranger", dexterity=10, magic_item_engine=engine)
        assert char.armor_class == 12  # 10 + 2 natural

    def test_deflection_and_natural_armor_stack(self):
        """Different bonus types (deflection + natural armor) stack."""
        engine = MagicItemEngine()
        engine.add_item(RING_REGISTRY["ring_of_protection_2"])
        engine.add_item(WONDROUS_ITEM_REGISTRY["amulet_of_natural_armor_3"])
        char = Character35e(name="Knight", dexterity=10, magic_item_engine=engine)
        assert char.armor_class == 15  # 10 + 2 deflection + 3 natural

    def test_deflection_from_engine_beats_metadata(self):
        """MagicItemEngine deflection takes precedence when higher than metadata."""
        engine = MagicItemEngine()
        engine.add_item(RING_REGISTRY["ring_of_protection_4"])
        char = Character35e(
            name="Paladin", dexterity=10,
            metadata={"deflection_bonus": 2},
            magic_item_engine=engine,
        )
        # ring gives +4, metadata gives +2 → best wins (non-stacking)
        assert char.armor_class == 14  # 10 + 4

    def test_metadata_deflection_beats_lower_engine(self):
        """Metadata deflection used when engine bonus is lower."""
        engine = MagicItemEngine()
        engine.add_item(RING_REGISTRY["ring_of_protection_1"])
        char = Character35e(
            name="Blessed", dexterity=10,
            metadata={"deflection_bonus": 3},
            magic_item_engine=engine,
        )
        # ring gives +1, metadata gives +3 → metadata wins
        assert char.armor_class == 13

    def test_touch_ac_includes_deflection(self):
        engine = MagicItemEngine()
        engine.add_item(RING_REGISTRY["ring_of_protection_2"])
        char = Character35e(name="Nimble", dexterity=14, magic_item_engine=engine)
        # 10 + 2 (DEX) + 2 (deflection) = 14
        assert char.touch_ac == 14

    def test_flat_footed_ac_includes_deflection_and_natural(self):
        engine = MagicItemEngine()
        engine.add_item(RING_REGISTRY["ring_of_protection_2"])
        engine.add_item(WONDROUS_ITEM_REGISTRY["amulet_of_natural_armor_1"])
        char = Character35e(name="Guard", dexterity=14, magic_item_engine=engine)
        # Flat-footed loses DEX but keeps deflection and natural armor
        assert char.flat_footed_ac == 13  # 10 + 2 deflection + 1 natural


# ---------------------------------------------------------------------------
# Character35e integration — saving throws
# ---------------------------------------------------------------------------

class TestCharacterSaveIntegration:

    def test_no_engine_no_save_change(self):
        char = Character35e(name="Test", char_class="Fighter", level=1, constitution=10)
        base_fort = char.fortitude_save
        assert base_fort == 2  # Good save at level 1

    def test_cloak_of_resistance_increases_fortitude(self):
        engine = MagicItemEngine()
        engine.add_item(WONDROUS_ITEM_REGISTRY["cloak_of_resistance_3"])
        char_with = Character35e(
            name="Cloaked", char_class="Fighter", level=1, constitution=10,
            magic_item_engine=engine,
        )
        char_without = Character35e(
            name="Plain", char_class="Fighter", level=1, constitution=10,
        )
        assert char_with.fortitude_save == char_without.fortitude_save + 3

    def test_cloak_of_resistance_increases_reflex(self):
        engine = MagicItemEngine()
        engine.add_item(WONDROUS_ITEM_REGISTRY["cloak_of_resistance_2"])
        char_with = Character35e(
            name="Cloaked", char_class="Fighter", level=5, dexterity=12,
            magic_item_engine=engine,
        )
        char_without = Character35e(
            name="Plain", char_class="Fighter", level=5, dexterity=12,
        )
        assert char_with.reflex_save == char_without.reflex_save + 2

    def test_cloak_of_resistance_increases_will(self):
        engine = MagicItemEngine()
        engine.add_item(WONDROUS_ITEM_REGISTRY["cloak_of_resistance_5"])
        char_with = Character35e(
            name="Resolute", char_class="Wizard", level=10, wisdom=12,
            magic_item_engine=engine,
        )
        char_without = Character35e(
            name="Fragile", char_class="Wizard", level=10, wisdom=12,
        )
        assert char_with.will_save == char_without.will_save + 5

    def test_resistance_non_stacking_across_items(self):
        """Two cloaks of resistance — only the higher bonus applies."""
        engine = MagicItemEngine()
        engine.add_item(WONDROUS_ITEM_REGISTRY["cloak_of_resistance_2"])
        engine.add_item(WONDROUS_ITEM_REGISTRY["cloak_of_resistance_4"])
        char_with = Character35e(
            name="Stacker", char_class="Rogue", level=3, constitution=10,
            dexterity=10, wisdom=10, magic_item_engine=engine,
        )
        char_without = Character35e(
            name="None", char_class="Rogue", level=3,
            constitution=10, dexterity=10, wisdom=10,
        )
        # Only +4 (not +6) should be added
        assert char_with.fortitude_save == char_without.fortitude_save + 4
