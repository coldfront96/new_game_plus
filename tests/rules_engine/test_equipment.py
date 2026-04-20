"""
tests/rules_engine/test_equipment.py
--------------------------------------
Unit tests for the D&D 3.5e Equipment Manager.

Verifies slot validation, equip/unequip logic, EventBus integration,
and the downstream effects on Character35e stats (AC, attack bonus).
"""

from unittest.mock import patch

import pytest

from src.core.event_bus import EventBus
from src.loot_math.item import Item, ItemType, Rarity
from src.rules_engine.character_35e import Character35e, Size
from src.rules_engine.equipment import (
    EquipmentManager,
    EquipmentSlot,
    _VALID_SLOT_TYPES,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def bus():
    return EventBus()


@pytest.fixture
def manager(bus):
    return EquipmentManager(event_bus=bus)


@pytest.fixture
def full_plate():
    """Full Plate: +8 armor bonus to AC (3.5e SRD)."""
    return Item(
        name="Full Plate",
        item_type=ItemType.ARMOUR,
        base_armour=8,
    )


@pytest.fixture
def chain_shirt():
    """Chain Shirt: +4 armor bonus to AC (3.5e SRD)."""
    return Item(
        name="Chain Shirt",
        item_type=ItemType.ARMOUR,
        base_armour=4,
    )


@pytest.fixture
def heavy_shield():
    """Heavy Steel Shield: +2 shield bonus to AC (3.5e SRD)."""
    return Item(
        name="Heavy Steel Shield",
        item_type=ItemType.ARMOUR,
        base_armour=2,
    )


@pytest.fixture
def longsword():
    """Longsword: 1d8 damage (3.5e SRD)."""
    return Item(
        name="Longsword",
        item_type=ItemType.WEAPON,
        base_damage=4,
        metadata={"damage_dice_count": 1, "damage_dice_sides": 8},
    )


@pytest.fixture
def magic_longsword():
    """+2 Longsword: 1d8+2 damage, +2 enhancement to hit (3.5e SRD)."""
    return Item(
        name="+2 Longsword",
        item_type=ItemType.WEAPON,
        base_damage=4,
        metadata={
            "damage_dice_count": 1,
            "damage_dice_sides": 8,
            "enhancement_bonus": 2,
        },
    )


@pytest.fixture
def ring():
    """Ring of Protection."""
    return Item(
        name="Ring of Protection",
        item_type=ItemType.TRINKET,
    )


@pytest.fixture
def fighter(bus):
    """Level 5 Fighter with STR 16, DEX 13."""
    mgr = EquipmentManager(event_bus=bus)
    return Character35e(
        name="Aldric",
        char_class="Fighter",
        level=5,
        strength=16,
        dexterity=13,
        constitution=14,
        equipment_manager=mgr,
    )


# ---------------------------------------------------------------------------
# Tests — EquipmentSlot Enum
# ---------------------------------------------------------------------------

class TestEquipmentSlot:
    """Verify EquipmentSlot enum members."""

    def test_all_slots_defined(self):
        expected = {"HEAD", "TORSO", "MAIN_HAND", "OFF_HAND", "LEGS", "FEET", "ACCESSORY"}
        actual = {s.name for s in EquipmentSlot}
        assert actual == expected

    def test_slot_count(self):
        assert len(EquipmentSlot) == 7


# ---------------------------------------------------------------------------
# Tests — EquipmentManager construction
# ---------------------------------------------------------------------------

class TestEquipmentManagerConstruction:
    """Verify EquipmentManager initialization."""

    def test_slots_enabled(self):
        assert hasattr(EquipmentManager, "__slots__")

    def test_all_slots_initialized_empty(self, manager):
        for slot in EquipmentSlot:
            assert manager.is_slot_empty(slot) is True

    def test_no_event_bus_is_allowed(self):
        mgr = EquipmentManager()
        assert mgr.event_bus is None
        # Should still function without events
        sword = Item(name="Dagger", item_type=ItemType.WEAPON, base_damage=2,
                     metadata={"damage_dice_count": 1, "damage_dice_sides": 4})
        mgr.equip_item(sword, EquipmentSlot.MAIN_HAND)
        assert mgr.get_item(EquipmentSlot.MAIN_HAND) is sword


# ---------------------------------------------------------------------------
# Tests — equip_item validation
# ---------------------------------------------------------------------------

class TestEquipItemValidation:
    """Verify that equip_item rejects invalid slot/type combinations."""

    def test_weapon_in_torso_raises(self, manager, longsword):
        with pytest.raises(ValueError, match="Cannot equip WEAPON"):
            manager.equip_item(longsword, EquipmentSlot.TORSO)

    def test_weapon_in_legs_raises(self, manager, longsword):
        with pytest.raises(ValueError, match="Cannot equip WEAPON"):
            manager.equip_item(longsword, EquipmentSlot.LEGS)

    def test_weapon_in_feet_raises(self, manager, longsword):
        with pytest.raises(ValueError, match="Cannot equip WEAPON"):
            manager.equip_item(longsword, EquipmentSlot.FEET)

    def test_weapon_in_accessory_raises(self, manager, longsword):
        with pytest.raises(ValueError, match="Cannot equip WEAPON"):
            manager.equip_item(longsword, EquipmentSlot.ACCESSORY)

    def test_armour_in_main_hand_raises(self, manager, full_plate):
        with pytest.raises(ValueError, match="Cannot equip ARMOUR"):
            manager.equip_item(full_plate, EquipmentSlot.MAIN_HAND)

    def test_armour_in_accessory_raises(self, manager, full_plate):
        with pytest.raises(ValueError, match="Cannot equip ARMOUR"):
            manager.equip_item(full_plate, EquipmentSlot.ACCESSORY)

    def test_trinket_in_torso_raises(self, manager, ring):
        with pytest.raises(ValueError, match="Cannot equip TRINKET"):
            manager.equip_item(ring, EquipmentSlot.TORSO)

    def test_trinket_in_main_hand_raises(self, manager, ring):
        with pytest.raises(ValueError, match="Cannot equip TRINKET"):
            manager.equip_item(ring, EquipmentSlot.MAIN_HAND)

    def test_weapon_in_main_hand_valid(self, manager, longsword):
        manager.equip_item(longsword, EquipmentSlot.MAIN_HAND)
        assert manager.get_item(EquipmentSlot.MAIN_HAND) is longsword

    def test_weapon_in_off_hand_valid(self, manager, longsword):
        manager.equip_item(longsword, EquipmentSlot.OFF_HAND)
        assert manager.get_item(EquipmentSlot.OFF_HAND) is longsword

    def test_armour_in_torso_valid(self, manager, full_plate):
        manager.equip_item(full_plate, EquipmentSlot.TORSO)
        assert manager.get_item(EquipmentSlot.TORSO) is full_plate

    def test_armour_in_off_hand_valid_as_shield(self, manager, heavy_shield):
        manager.equip_item(heavy_shield, EquipmentSlot.OFF_HAND)
        assert manager.get_item(EquipmentSlot.OFF_HAND) is heavy_shield

    def test_trinket_in_accessory_valid(self, manager, ring):
        manager.equip_item(ring, EquipmentSlot.ACCESSORY)
        assert manager.get_item(EquipmentSlot.ACCESSORY) is ring

    def test_trinket_in_head_valid(self, manager, ring):
        manager.equip_item(ring, EquipmentSlot.HEAD)
        assert manager.get_item(EquipmentSlot.HEAD) is ring


# ---------------------------------------------------------------------------
# Tests — equip/unequip behaviour
# ---------------------------------------------------------------------------

class TestEquipUnequipBehavior:
    """Verify equip/unequip logic and item displacement."""

    def test_equip_returns_none_if_slot_empty(self, manager, longsword):
        result = manager.equip_item(longsword, EquipmentSlot.MAIN_HAND)
        assert result is None

    def test_equip_returns_previous_item(self, manager, longsword, magic_longsword):
        manager.equip_item(longsword, EquipmentSlot.MAIN_HAND)
        result = manager.equip_item(magic_longsword, EquipmentSlot.MAIN_HAND)
        assert result is longsword
        assert manager.get_item(EquipmentSlot.MAIN_HAND) is magic_longsword

    def test_unequip_returns_item(self, manager, full_plate):
        manager.equip_item(full_plate, EquipmentSlot.TORSO)
        result = manager.unequip_slot(EquipmentSlot.TORSO)
        assert result is full_plate
        assert manager.is_slot_empty(EquipmentSlot.TORSO) is True

    def test_unequip_empty_slot_returns_none(self, manager):
        result = manager.unequip_slot(EquipmentSlot.TORSO)
        assert result is None

    def test_equip_same_item_again(self, manager, longsword):
        manager.equip_item(longsword, EquipmentSlot.MAIN_HAND)
        result = manager.equip_item(longsword, EquipmentSlot.MAIN_HAND)
        # Same item re-equipped, no displacement
        assert result is None
        assert manager.get_item(EquipmentSlot.MAIN_HAND) is longsword


# ---------------------------------------------------------------------------
# Tests — EventBus integration
# ---------------------------------------------------------------------------

class TestEquipmentEvents:
    """Verify that equip/unequip publishes events."""

    def test_equip_publishes_item_equipped(self, bus, manager, longsword):
        events = []
        bus.subscribe("item_equipped", lambda p: events.append(p))

        manager.equip_item(longsword, EquipmentSlot.MAIN_HAND)

        assert len(events) == 1
        assert events[0]["item_name"] == "Longsword"
        assert events[0]["slot"] == "MAIN_HAND"
        assert events[0]["item_type"] == "WEAPON"

    def test_unequip_publishes_item_unequipped(self, bus, manager, full_plate):
        events = []
        bus.subscribe("item_unequipped", lambda p: events.append(p))

        manager.equip_item(full_plate, EquipmentSlot.TORSO)
        manager.unequip_slot(EquipmentSlot.TORSO)

        assert len(events) == 1
        assert events[0]["item_name"] == "Full Plate"
        assert events[0]["slot"] == "TORSO"

    def test_displacement_publishes_both_events(self, bus, manager, longsword, magic_longsword):
        equipped_events = []
        unequipped_events = []
        bus.subscribe("item_equipped", lambda p: equipped_events.append(p))
        bus.subscribe("item_unequipped", lambda p: unequipped_events.append(p))

        manager.equip_item(longsword, EquipmentSlot.MAIN_HAND)
        manager.equip_item(magic_longsword, EquipmentSlot.MAIN_HAND)

        # First equip + displacement unequip + second equip
        assert len(equipped_events) == 2
        assert len(unequipped_events) == 1
        assert unequipped_events[0]["item_name"] == "Longsword"


# ---------------------------------------------------------------------------
# Tests — Armor bonus calculation
# ---------------------------------------------------------------------------

class TestArmorBonus:
    """Verify armor bonus retrieval from TORSO slot."""

    def test_no_armor_returns_zero(self, manager):
        assert manager.get_armor_bonus() == 0

    def test_full_plate_gives_8(self, manager, full_plate):
        manager.equip_item(full_plate, EquipmentSlot.TORSO)
        assert manager.get_armor_bonus() == 8

    def test_chain_shirt_gives_4(self, manager, chain_shirt):
        manager.equip_item(chain_shirt, EquipmentSlot.TORSO)
        assert manager.get_armor_bonus() == 4

    def test_unequip_removes_armor_bonus(self, manager, full_plate):
        manager.equip_item(full_plate, EquipmentSlot.TORSO)
        manager.unequip_slot(EquipmentSlot.TORSO)
        assert manager.get_armor_bonus() == 0


# ---------------------------------------------------------------------------
# Tests — Shield bonus calculation
# ---------------------------------------------------------------------------

class TestShieldBonus:
    """Verify shield bonus retrieval from OFF_HAND slot."""

    def test_no_shield_returns_zero(self, manager):
        assert manager.get_shield_bonus() == 0

    def test_heavy_shield_gives_2(self, manager, heavy_shield):
        manager.equip_item(heavy_shield, EquipmentSlot.OFF_HAND)
        assert manager.get_shield_bonus() == 2

    def test_weapon_in_off_hand_gives_no_shield(self, manager, longsword):
        manager.equip_item(longsword, EquipmentSlot.OFF_HAND)
        assert manager.get_shield_bonus() == 0


# ---------------------------------------------------------------------------
# Tests — Weapon methods
# ---------------------------------------------------------------------------

class TestWeaponMethods:
    """Verify weapon retrieval and damage dice."""

    def test_get_weapon_when_empty(self, manager):
        assert manager.get_weapon() is None

    def test_get_weapon_returns_main_hand(self, manager, longsword):
        manager.equip_item(longsword, EquipmentSlot.MAIN_HAND)
        assert manager.get_weapon() is longsword

    def test_get_weapon_damage_dice(self, manager, longsword):
        manager.equip_item(longsword, EquipmentSlot.MAIN_HAND)
        count, sides = manager.get_weapon_damage_dice()
        assert count == 1
        assert sides == 8

    def test_get_weapon_damage_dice_no_weapon(self, manager):
        assert manager.get_weapon_damage_dice() == (0, 0)

    def test_get_enhancement_bonus_no_weapon(self, manager):
        assert manager.get_weapon_enhancement_bonus() == 0

    def test_get_enhancement_bonus_normal_weapon(self, manager, longsword):
        manager.equip_item(longsword, EquipmentSlot.MAIN_HAND)
        assert manager.get_weapon_enhancement_bonus() == 0

    def test_get_enhancement_bonus_magic_weapon(self, manager, magic_longsword):
        manager.equip_item(magic_longsword, EquipmentSlot.MAIN_HAND)
        assert manager.get_weapon_enhancement_bonus() == 2


# ---------------------------------------------------------------------------
# Tests — Character35e integration
# ---------------------------------------------------------------------------

class TestCharacterEquipmentIntegration:
    """Verify that equipping items affects Character35e derived stats."""

    def test_full_plate_increases_ac_by_8(self, fighter, full_plate):
        """Primary verification: equipping Full Plate increases AC by +8."""
        base_ac = fighter.armor_class
        fighter.equipment_manager.equip_item(full_plate, EquipmentSlot.TORSO)
        assert fighter.armor_class == base_ac + 8

    def test_chain_shirt_increases_ac_by_4(self, bus, chain_shirt):
        mgr = EquipmentManager(event_bus=bus)
        char = Character35e(name="Test", dexterity=12, equipment_manager=mgr)
        base_ac = char.armor_class
        mgr.equip_item(chain_shirt, EquipmentSlot.TORSO)
        assert char.armor_class == base_ac + 4

    def test_shield_adds_to_ac(self, fighter, heavy_shield):
        base_ac = fighter.armor_class
        fighter.equipment_manager.equip_item(heavy_shield, EquipmentSlot.OFF_HAND)
        assert fighter.armor_class == base_ac + 2

    def test_full_plate_plus_shield(self, fighter, full_plate, heavy_shield):
        base_ac = fighter.armor_class
        fighter.equipment_manager.equip_item(full_plate, EquipmentSlot.TORSO)
        fighter.equipment_manager.equip_item(heavy_shield, EquipmentSlot.OFF_HAND)
        assert fighter.armor_class == base_ac + 10  # +8 armor + +2 shield

    def test_unequip_armor_removes_bonus(self, fighter, full_plate):
        base_ac = fighter.armor_class
        fighter.equipment_manager.equip_item(full_plate, EquipmentSlot.TORSO)
        assert fighter.armor_class == base_ac + 8
        fighter.equipment_manager.unequip_slot(EquipmentSlot.TORSO)
        assert fighter.armor_class == base_ac

    def test_magic_weapon_adds_enhancement_to_melee(self, fighter, magic_longsword):
        base_melee = fighter.melee_attack
        fighter.equipment_manager.equip_item(magic_longsword, EquipmentSlot.MAIN_HAND)
        assert fighter.melee_attack == base_melee + 2

    def test_magic_weapon_adds_enhancement_to_ranged(self, fighter, magic_longsword):
        base_ranged = fighter.ranged_attack
        fighter.equipment_manager.equip_item(magic_longsword, EquipmentSlot.MAIN_HAND)
        assert fighter.ranged_attack == base_ranged + 2

    def test_no_equipment_manager_no_bonus(self):
        """Character without EquipmentManager behaves as before."""
        char = Character35e(name="NoGear", dexterity=14)
        # AC = 10 + 2 (DEX) + 0 (size) = 12
        assert char.armor_class == 12
        assert char.equipment_manager is None

    def test_character_ac_formula_full(self, bus, full_plate):
        """Full AC formula: 10 + DEX + size + armor + shield."""
        mgr = EquipmentManager(event_bus=bus)
        char = Character35e(
            name="Knight",
            dexterity=12,  # +1 DEX mod
            size=Size.MEDIUM,
            equipment_manager=mgr,
        )
        # Base: 10 + 1 + 0 = 11
        assert char.armor_class == 11
        mgr.equip_item(full_plate, EquipmentSlot.TORSO)
        # 11 + 8 = 19
        assert char.armor_class == 19


# ---------------------------------------------------------------------------
# Tests — CombatSystem auto-pulls weapon from EquipmentManager
# ---------------------------------------------------------------------------

class TestCombatSystemEquipmentIntegration:
    """Verify CombatSystem uses EquipmentManager weapon data."""

    def test_combat_system_uses_equipped_weapon(self, bus):
        from src.ai_sim.systems import AttackIntent, CombatSystem
        from src.rules_engine.dice import RollResult

        # Setup attacker with equipment manager and equipped weapon
        attacker_mgr = EquipmentManager(event_bus=bus)
        attacker = Character35e(
            name="Fighter",
            char_class="Fighter",
            level=5,
            strength=16,
            equipment_manager=attacker_mgr,
        )
        longsword = Item(
            name="Longsword",
            item_type=ItemType.WEAPON,
            base_damage=4,
            metadata={"damage_dice_count": 1, "damage_dice_sides": 8},
        )
        attacker_mgr.equip_item(longsword, EquipmentSlot.MAIN_HAND)

        defender = Character35e(name="Goblin", dexterity=14, size=Size.SMALL)

        system = CombatSystem(bus)
        results = []
        bus.subscribe("combat_result", lambda r: results.append(r))

        # Publish intent WITHOUT explicit weapon — system should pull from equipment
        intent = AttackIntent(attacker=attacker, defender=defender)
        bus.publish("attack_intent", intent)

        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            mock_d20.return_value = RollResult(raw=15, modifier=8, total=23)
            mock_dmg.return_value = RollResult(raw=6, modifier=3, total=9)
            system.update()

        assert len(results) == 1
        # The system resolved the attack using the equipped weapon

    def test_combat_system_explicit_weapon_overrides(self, bus):
        from src.ai_sim.systems import AttackIntent, CombatSystem
        from src.rules_engine.dice import RollResult

        attacker_mgr = EquipmentManager(event_bus=bus)
        attacker = Character35e(
            name="Fighter",
            char_class="Fighter",
            level=5,
            strength=16,
            equipment_manager=attacker_mgr,
        )
        # Equip a longsword
        longsword = Item(
            name="Longsword",
            item_type=ItemType.WEAPON,
            base_damage=4,
            metadata={"damage_dice_count": 1, "damage_dice_sides": 8},
        )
        attacker_mgr.equip_item(longsword, EquipmentSlot.MAIN_HAND)

        # But pass a different weapon explicitly
        greatsword = Item(
            name="Greatsword",
            item_type=ItemType.WEAPON,
            base_damage=7,
            metadata={"damage_dice_count": 2, "damage_dice_sides": 6},
        )

        defender = Character35e(name="Orc", strength=14)

        system = CombatSystem(bus)
        results = []
        bus.subscribe("combat_result", lambda r: results.append(r))

        intent = AttackIntent(attacker=attacker, defender=defender, weapon=greatsword)
        bus.publish("attack_intent", intent)

        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            mock_d20.return_value = RollResult(raw=18, modifier=8, total=26)
            mock_dmg.return_value = RollResult(raw=9, modifier=3, total=12)
            system.update()

        assert len(results) == 1
