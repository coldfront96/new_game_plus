"""
tests/rules_engine/test_penalties.py
--------------------------------------
Verification tests for Armor Physical Penalties.

Covers:
* Full Plate: Max Dex Bonus cap (+1) applied to armor_class.
* Full Plate: Speed reduction (30 ft → 20 ft / voxel_speed 6 → 4).
* Chain Shirt (light armor): No speed reduction.
* ACP subtracted from STR/DEX-based skill checks but not other skills.
* EquipmentManager.get_total_acp() and get_min_max_dex_bonus() helpers.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.core.event_bus import EventBus
from src.loot_math.item import Item, ItemType
from src.rules_engine.character_35e import Character35e
from src.rules_engine.equipment import EquipmentManager, EquipmentSlot
from src.rules_engine.skills import SkillSystem
from src.rules_engine.dice import RollResult


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def bus():
    return EventBus()


@pytest.fixture
def full_plate():
    """Full Plate (3.5e SRD): +8 AC, Max Dex +1, ACP -6, Speed 20 ft (heavy)."""
    return Item(
        name="Full Plate",
        item_type=ItemType.ARMOUR,
        base_armour=8,
        metadata={
            "armor_category": "heavy",
            "max_dex_bonus": 1,
            "armor_check_penalty": 6,
            "asf_chance": 35,
        },
    )


@pytest.fixture
def chain_shirt():
    """Chain Shirt (3.5e SRD): +4 AC, Max Dex +4, ACP -2, no speed penalty (light)."""
    return Item(
        name="Chain Shirt",
        item_type=ItemType.ARMOUR,
        base_armour=4,
        metadata={
            "armor_category": "light",
            "max_dex_bonus": 4,
            "armor_check_penalty": 2,
            "asf_chance": 20,
        },
    )


@pytest.fixture
def heavy_shield():
    """Heavy Steel Shield (3.5e SRD): +2 AC, ACP -2."""
    return Item(
        name="Heavy Steel Shield",
        item_type=ItemType.ARMOUR,
        base_armour=2,
        metadata={
            "armor_check_penalty": 2,
        },
    )


@pytest.fixture
def knight(bus, full_plate):
    """Fighter with DEX 16 (+3 mod) wearing Full Plate."""
    mgr = EquipmentManager(event_bus=bus)
    char = Character35e(
        name="Sir Aldric",
        char_class="Fighter",
        level=5,
        strength=16,
        dexterity=16,  # +3 mod — capped to +1 by Full Plate
        constitution=14,
        base_speed=30,
        equipment_manager=mgr,
    )
    mgr.equip_item(full_plate, EquipmentSlot.TORSO)
    return char


# ---------------------------------------------------------------------------
# Tests — Max Dex Bonus cap on armor_class
# ---------------------------------------------------------------------------

class TestMaxDexBonusCap:
    """Verify that armor_class respects the Max Dex Bonus from equipped armor."""

    def test_full_plate_caps_dex_bonus_to_1(self, knight):
        """With Full Plate (Max Dex +1) and DEX 16 (+3 mod), DEX contribution is +1."""
        # AC = 10 + capped_dex(+1) + size(0) + armor(+8) = 19
        assert knight.armor_class == 19

    def test_no_armor_uses_full_dex_bonus(self, bus):
        """Without armor, full DEX modifier applies to AC."""
        mgr = EquipmentManager(event_bus=bus)
        char = Character35e(name="Rogue", dexterity=16, equipment_manager=mgr)
        # AC = 10 + 3 (DEX) + 0 (size) = 13
        assert char.armor_class == 13

    def test_chain_shirt_caps_dex_at_4(self, bus, chain_shirt):
        """Chain Shirt (Max Dex +4) does not cap a +3 DEX modifier."""
        mgr = EquipmentManager(event_bus=bus)
        char = Character35e(name="Scout", dexterity=18, equipment_manager=mgr)
        # DEX +4, Max Dex +4 → capped at +4
        # AC = 10 + 4 + 0 + 4 = 18
        mgr.equip_item(chain_shirt, EquipmentSlot.TORSO)
        assert char.armor_class == 18

    def test_chain_shirt_does_not_cap_low_dex(self, bus, chain_shirt):
        """Chain Shirt (Max Dex +4) imposes no cap when DEX mod ≤ +4."""
        mgr = EquipmentManager(event_bus=bus)
        char = Character35e(name="Scout", dexterity=14, equipment_manager=mgr)
        # DEX +2, Max Dex +4 → no cap applied
        # AC = 10 + 2 + 0 + 4 = 16
        mgr.equip_item(chain_shirt, EquipmentSlot.TORSO)
        assert char.armor_class == 16

    def test_no_equipment_manager_no_cap(self):
        """Character without an EquipmentManager never has a DEX cap."""
        char = Character35e(name="Naked", dexterity=20)
        # AC = 10 + 5 (DEX) = 15
        assert char.armor_class == 15

    def test_get_min_max_dex_bonus_no_armor(self, bus):
        mgr = EquipmentManager(event_bus=bus)
        assert mgr.get_min_max_dex_bonus() is None

    def test_get_min_max_dex_bonus_full_plate(self, bus, full_plate):
        mgr = EquipmentManager(event_bus=bus)
        mgr.equip_item(full_plate, EquipmentSlot.TORSO)
        assert mgr.get_min_max_dex_bonus() == 1

    def test_get_min_max_dex_bonus_most_restrictive(self, bus, full_plate, chain_shirt):
        """When two pieces of armor impose caps, the lower cap wins."""
        mgr = EquipmentManager(event_bus=bus)
        mgr.equip_item(full_plate, EquipmentSlot.TORSO)
        mgr.equip_item(chain_shirt, EquipmentSlot.HEAD)
        # Full Plate: max_dex_bonus=1, Chain Shirt: max_dex_bonus=4 → min=1
        assert mgr.get_min_max_dex_bonus() == 1


# ---------------------------------------------------------------------------
# Tests — Speed reduction
# ---------------------------------------------------------------------------

class TestArmorSpeedReduction:
    """Verify voxel_speed applies the 3.5e armor speed table."""

    def test_full_plate_reduces_30ft_to_20ft(self, knight):
        """Full Plate (heavy): 30 ft base → 20 ft → 4 voxels."""
        assert knight.voxel_speed == 4  # 20 ft // 5

    def test_no_armor_30ft_gives_6_voxels(self, bus):
        """No armor: 30 ft base → 6 voxels."""
        mgr = EquipmentManager(event_bus=bus)
        char = Character35e(name="Unarmored", base_speed=30, equipment_manager=mgr)
        assert char.voxel_speed == 6

    def test_light_armor_no_speed_penalty(self, bus, chain_shirt):
        """Light armor (Chain Shirt) does not reduce movement speed."""
        mgr = EquipmentManager(event_bus=bus)
        char = Character35e(name="Scout", base_speed=30, equipment_manager=mgr)
        mgr.equip_item(chain_shirt, EquipmentSlot.TORSO)
        assert char.voxel_speed == 6  # still 30 ft → 6 voxels

    def test_heavy_armor_20ft_base_reduces_to_15ft(self, bus, full_plate):
        """Full Plate on a creature with 20 ft base speed → 15 ft → 3 voxels."""
        mgr = EquipmentManager(event_bus=bus)
        char = Character35e(name="Dwarf", base_speed=20, equipment_manager=mgr)
        mgr.equip_item(full_plate, EquipmentSlot.TORSO)
        assert char.voxel_speed == 3  # 15 ft // 5

    def test_no_equipment_manager_no_penalty(self):
        """Character without EquipmentManager is never penalised."""
        char = Character35e(name="NoGear", base_speed=30)
        assert char.voxel_speed == 6

    def test_unequip_armor_restores_speed(self, knight):
        """Removing Full Plate restores full speed."""
        knight.equipment_manager.unequip_slot(EquipmentSlot.TORSO)
        assert knight.voxel_speed == 6  # back to 30 ft // 5


# ---------------------------------------------------------------------------
# Tests — Armor Check Penalty helpers
# ---------------------------------------------------------------------------

class TestArmorCheckPenaltyHelpers:
    """Verify EquipmentManager ACP helper methods."""

    def test_no_armor_acp_is_zero(self, bus):
        mgr = EquipmentManager(event_bus=bus)
        assert mgr.get_total_acp() == 0

    def test_full_plate_acp_is_6(self, bus, full_plate):
        mgr = EquipmentManager(event_bus=bus)
        mgr.equip_item(full_plate, EquipmentSlot.TORSO)
        assert mgr.get_total_acp() == 6

    def test_full_plate_plus_shield_acp_stacks(self, bus, full_plate, heavy_shield):
        mgr = EquipmentManager(event_bus=bus)
        mgr.equip_item(full_plate, EquipmentSlot.TORSO)
        mgr.equip_item(heavy_shield, EquipmentSlot.OFF_HAND)
        # 6 (Full Plate) + 2 (Heavy Shield) = 8
        assert mgr.get_total_acp() == 8

    def test_unequip_removes_acp(self, bus, full_plate):
        mgr = EquipmentManager(event_bus=bus)
        mgr.equip_item(full_plate, EquipmentSlot.TORSO)
        mgr.unequip_slot(EquipmentSlot.TORSO)
        assert mgr.get_total_acp() == 0


# ---------------------------------------------------------------------------
# Tests — ACP applied to skill checks
# ---------------------------------------------------------------------------

class TestSkillArmorCheckPenalty:
    """Verify SkillSystem.check() subtracts ACP from STR/DEX skills only."""

    def test_acp_subtracts_from_climb_str_skill(self):
        """Climb (STR-based) check should be penalised by ACP."""
        ss = SkillSystem()
        ss.set_rank("Climb", 5)

        with patch("src.rules_engine.skills.roll_d20") as mock_d20:
            mock_d20.return_value = RollResult(raw=10, modifier=8, total=18)
            ss.check("Climb", ability_modifier=3, dc=10)
            no_acp_modifier = mock_d20.call_args[1]["modifier"]

        with patch("src.rules_engine.skills.roll_d20") as mock_d20:
            mock_d20.return_value = RollResult(raw=10, modifier=2, total=12)
            ss.check("Climb", ability_modifier=3, dc=10, armor_check_penalty=6)
            acp_modifier = mock_d20.call_args[1]["modifier"]

        # ACP of 6 should reduce the modifier by 6
        assert no_acp_modifier - acp_modifier == 6

    def test_acp_subtracts_from_hide_dex_skill(self):
        """Hide (DEX-based) check should be penalised by ACP."""
        ss = SkillSystem()
        ss.set_rank("Hide", 4)

        with patch("src.rules_engine.skills.roll_d20") as mock_d20:
            mock_d20.return_value = RollResult(raw=12, modifier=6, total=18)
            ss.check("Hide", ability_modifier=2, dc=15)
            no_acp_modifier = mock_d20.call_args[1]["modifier"]

        with patch("src.rules_engine.skills.roll_d20") as mock_d20:
            mock_d20.return_value = RollResult(raw=12, modifier=0, total=12)
            ss.check("Hide", ability_modifier=2, dc=15, armor_check_penalty=6)
            acp_modifier = mock_d20.call_args[1]["modifier"]

        assert no_acp_modifier - acp_modifier == 6

    def test_acp_does_not_affect_wis_skill(self):
        """Survival (WIS-based) check is NOT penalised by ACP."""
        ss = SkillSystem()
        ss.set_rank("Survival", 5)

        with patch("src.rules_engine.skills.roll_d20") as mock_d20:
            mock_d20.return_value = RollResult(raw=10, modifier=7, total=17)
            ss.check("Survival", ability_modifier=2, dc=10)
            no_acp_modifier = mock_d20.call_args[1]["modifier"]

        with patch("src.rules_engine.skills.roll_d20") as mock_d20:
            mock_d20.return_value = RollResult(raw=10, modifier=7, total=17)
            ss.check("Survival", ability_modifier=2, dc=10, armor_check_penalty=6)
            acp_modifier = mock_d20.call_args[1]["modifier"]

        # Same modifier — ACP is ignored for WIS-based skills
        assert no_acp_modifier == acp_modifier

    def test_acp_does_not_affect_int_skill(self):
        """Spellcraft (INT-based) check is NOT penalised by ACP."""
        ss = SkillSystem()
        ss.set_rank("Spellcraft", 8)

        with patch("src.rules_engine.skills.roll_d20") as mock_d20:
            mock_d20.return_value = RollResult(raw=15, modifier=11, total=26)
            ss.check("Spellcraft", ability_modifier=3, dc=20)
            no_acp_modifier = mock_d20.call_args[1]["modifier"]

        with patch("src.rules_engine.skills.roll_d20") as mock_d20:
            mock_d20.return_value = RollResult(raw=15, modifier=11, total=26)
            ss.check("Spellcraft", ability_modifier=3, dc=20, armor_check_penalty=6)
            acp_modifier = mock_d20.call_args[1]["modifier"]

        assert no_acp_modifier == acp_modifier

    def test_zero_acp_no_effect_on_str_skill(self):
        """Zero ACP (no armor) has no effect on any skill."""
        ss = SkillSystem()
        ss.set_rank("Climb", 5)

        with patch("src.rules_engine.skills.roll_d20") as mock_d20:
            mock_d20.return_value = RollResult(raw=10, modifier=8, total=18)
            ss.check("Climb", ability_modifier=3, dc=10, armor_check_penalty=0)
            modifier = mock_d20.call_args[1]["modifier"]

        # rank(5) + ability(3) + misc(0) - acp(0) = 8
        assert modifier == 8


# ---------------------------------------------------------------------------
# Tests — Full Plate integration (combined)
# ---------------------------------------------------------------------------

class TestFullPlateIntegration:
    """End-to-end verification of Full Plate physical penalties."""

    def test_full_plate_dex_cap_and_speed_combined(self, knight):
        """Full Plate simultaneously caps DEX bonus and reduces speed."""
        # DEX 16 (+3 mod) capped to +1 by Full Plate
        # AC = 10 + 1 (capped DEX) + 0 (size) + 8 (armor) = 19
        assert knight.armor_class == 19
        # Speed: 30 ft → 20 ft → 4 voxels
        assert knight.voxel_speed == 4

    def test_full_plate_acp_affects_swim_check(self, knight):
        """Full Plate ACP penalises Swim (STR-based) skill checks."""
        ss = SkillSystem()
        ss.set_rank("Swim", 3)
        acp = knight.equipment_manager.get_total_acp()
        assert acp == 6

        with patch("src.rules_engine.skills.roll_d20") as mock_d20:
            mock_d20.return_value = RollResult(raw=10, modifier=0, total=10)
            ss.check("Swim", ability_modifier=knight.strength_mod, dc=15, armor_check_penalty=acp)
            # modifier = rank(3) + str_mod(3) - acp(6) = 0
            modifier_used = mock_d20.call_args[1]["modifier"]

        assert modifier_used == 0  # rank(3) + str_mod(3) - acp(6) = 0
