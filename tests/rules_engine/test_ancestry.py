"""
tests/rules_engine/test_ancestry.py
------------------------------------
Verification tests for the Racial Trait Engine, advanced critical-hit logic,
and Damage Reduction integration.

Covers:
* RaceRegistry data correctness for all five core races.
* Racial stat modifiers automatically applied to Character35e ability modifiers.
* Weapon-specific threat ranges (19-20) and damage multipliers (x3, x4).
* Confirm-critical roll logic in AttackResolver.
* Damage Reduction subtraction from final damage.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.rules_engine.character_35e import Character35e, Size
from src.rules_engine.combat import AttackResolver, CombatResult
from src.rules_engine.dice import RollResult
from src.rules_engine.race import Race, RaceRegistry


# ===========================================================================
# RaceRegistry — data integrity
# ===========================================================================

class TestRaceRegistry:
    def test_get_returns_race_instance(self):
        race = RaceRegistry.get("Human")
        assert isinstance(race, Race)

    def test_unknown_race_defaults_to_human(self):
        race = RaceRegistry.get("Klingon")
        assert race.name == "Human"

    def test_all_names_sorted(self):
        names = RaceRegistry.all_names()
        assert names == sorted(names)
        assert "Elf" in names
        assert "Dwarf" in names

    def test_race_dataclass_uses_slots(self):
        assert hasattr(Race, "__slots__")


# ===========================================================================
# Racial stat modifiers — per-race correctness
# ===========================================================================

class TestRaceStatModifiers:
    def test_human_no_fixed_modifiers(self):
        race = RaceRegistry.get("Human")
        assert race.stat_modifiers == {}

    def test_elf_dex_bonus_and_con_penalty(self):
        race = RaceRegistry.get("Elf")
        assert race.stat_modifiers.get("dexterity") == 2
        assert race.stat_modifiers.get("constitution") == -2

    def test_dwarf_con_bonus_and_cha_penalty(self):
        race = RaceRegistry.get("Dwarf")
        assert race.stat_modifiers.get("constitution") == 2
        assert race.stat_modifiers.get("charisma") == -2

    def test_halfling_dex_bonus_and_str_penalty(self):
        race = RaceRegistry.get("Halfling")
        assert race.stat_modifiers.get("dexterity") == 2
        assert race.stat_modifiers.get("strength") == -2

    def test_orc_str_bonus_and_int_wis_cha_penalties(self):
        race = RaceRegistry.get("Orc")
        assert race.stat_modifiers.get("strength") == 4
        assert race.stat_modifiers.get("intelligence") == -2
        assert race.stat_modifiers.get("wisdom") == -2
        assert race.stat_modifiers.get("charisma") == -2


# ===========================================================================
# Racial special abilities
# ===========================================================================

class TestRaceSpecialAbilities:
    def test_elf_has_low_light_vision(self):
        assert "Low-Light Vision" in RaceRegistry.get("Elf").special_abilities

    def test_dwarf_has_darkvision(self):
        assert "Darkvision" in RaceRegistry.get("Dwarf").special_abilities

    def test_orc_has_ferocity(self):
        assert "Ferocity" in RaceRegistry.get("Orc").special_abilities

    def test_orc_has_darkvision(self):
        assert "Darkvision" in RaceRegistry.get("Orc").special_abilities

    def test_human_has_bonus_feat(self):
        assert "Bonus Feat" in RaceRegistry.get("Human").special_abilities


# ===========================================================================
# Character35e — racial modifiers applied to ability scores
# ===========================================================================

class TestCharacterRacialModifiers:
    def test_elf_dex_modifier_includes_racial_bonus(self):
        """An Elf with base DEX 10 should have dexterity_mod == +2 (0 + racial +2)."""
        elf = Character35e(name="Aelindra", race="Elf", dexterity=10)
        assert elf.dexterity_mod == 2  # (10-10)//2 + 2 = 0 + 2 = +2

    def test_elf_con_modifier_includes_racial_penalty(self):
        """An Elf with base CON 12 should have constitution_mod == -1 (1 + -2)."""
        elf = Character35e(name="Aelindra", race="Elf", constitution=12)
        assert elf.constitution_mod == -1  # (12-10)//2=1, racial=-2 → -1

    def test_human_modifier_unchanged(self):
        """A Human with STR 14 should have strength_mod == +2 (no racial modifier)."""
        human = Character35e(name="Aldric", race="Human", strength=14)
        assert human.strength_mod == 2

    def test_dwarf_con_modifier(self):
        """A Dwarf with CON 10 should have constitution_mod == +2."""
        dwarf = Character35e(name="Throdin", race="Dwarf", constitution=10)
        assert dwarf.constitution_mod == 2

    def test_dwarf_cha_modifier(self):
        """A Dwarf with CHA 10 should have charisma_mod == -2."""
        dwarf = Character35e(name="Throdin", race="Dwarf", charisma=10)
        assert dwarf.charisma_mod == -2

    def test_halfling_str_modifier(self):
        """A Halfling with STR 10 should have strength_mod == -2."""
        halfling = Character35e(name="Pip", race="Halfling", strength=10)
        assert halfling.strength_mod == -2

    def test_halfling_dex_modifier(self):
        """A Halfling with DEX 10 should have dexterity_mod == +2."""
        halfling = Character35e(name="Pip", race="Halfling", dexterity=10)
        assert halfling.dexterity_mod == 2

    def test_orc_str_modifier(self):
        """An Orc with STR 10 should have strength_mod == +4."""
        orc = Character35e(name="Gruk", race="Orc", strength=10)
        assert orc.strength_mod == 4

    def test_orc_int_modifier(self):
        """An Orc with INT 10 should have intelligence_mod == -2."""
        orc = Character35e(name="Gruk", race="Orc", intelligence=10)
        assert orc.intelligence_mod == -2

    def test_elf_default_race_applied_on_creation(self):
        """When race='Elf', dexterity_mod always reflects the +2 racial bonus."""
        elf = Character35e(name="Test", race="Elf", dexterity=14)
        # (14-10)//2 + 2 = 2 + 2 = 4
        assert elf.dexterity_mod == 4


# ===========================================================================
# Character35e — damage_reduction field
# ===========================================================================

class TestCharacterDamageReduction:
    def test_default_dr_is_empty(self):
        char = Character35e(name="Test")
        assert char.damage_reduction == ""

    def test_dr_can_be_set(self):
        char = Character35e(name="Ironclad", damage_reduction="5/Magic")
        assert char.damage_reduction == "5/Magic"

    def test_dr_three_slash_dash(self):
        char = Character35e(name="Stone", damage_reduction="3/-")
        assert char.damage_reduction == "3/-"


# ===========================================================================
# AttackResolver — critical threat ranges and multipliers
# ===========================================================================

class TestCriticalThreatRange:
    """Verify weapon-specific threat ranges and confirm-crit logic."""

    @pytest.fixture
    def fighter(self):
        return Character35e(name="Aldric", char_class="Fighter", level=5,
                            strength=16, dexterity=13, constitution=14)

    @pytest.fixture
    def goblin(self):
        return Character35e(name="Goblin", char_class="Rogue", level=1,
                            strength=8, dexterity=14, size=Size.SMALL)

    def test_nat20_is_always_crit_confirmed(self, fighter, goblin):
        """Natural 20 confirms a critical (both threat and confirm hit)."""
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            mock_d20.return_value = RollResult(
                raw=20, modifier=fighter.melee_attack,
                total=20 + fighter.melee_attack,
            )
            mock_dmg.return_value = RollResult(raw=5, modifier=3, total=8)

            result = AttackResolver.resolve_attack(fighter, goblin)
            assert result.hit is True
            assert result.critical is True
            assert result.total_damage == 16  # 8 × 2 (default multiplier)

    def test_threat_on_19_with_19_20_weapon(self, fighter, goblin):
        """A roll of 19 with threat_range=19 generates a critical threat."""
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            # First call = attack roll (19, hits); second = confirm (also 19)
            confirm_total = 19 + fighter.melee_attack
            mock_d20.return_value = RollResult(
                raw=19, modifier=fighter.melee_attack,
                total=confirm_total,
            )
            mock_dmg.return_value = RollResult(raw=4, modifier=3, total=7)

            result = AttackResolver.resolve_attack(
                fighter, goblin, threat_range=19,
            )
            # confirm_total must meet goblin.armor_class for crit to confirm
            if confirm_total >= goblin.armor_class:
                assert result.critical is True
            else:
                assert result.critical is False

    def test_no_threat_below_range(self, fighter, goblin):
        """A roll below threat_range never triggers a critical."""
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            mock_d20.return_value = RollResult(
                raw=18, modifier=fighter.melee_attack,
                total=18 + fighter.melee_attack,
            )
            mock_dmg.return_value = RollResult(raw=4, modifier=3, total=7)

            result = AttackResolver.resolve_attack(
                fighter, goblin, threat_range=19,
            )
            assert result.critical is False

    def test_failed_confirm_is_not_critical(self, fighter, goblin):
        """If the confirm roll misses, no critical is awarded."""
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            # First roll: raw=20 (threat), second roll: raw=2 (fails confirm)
            mock_d20.side_effect = [
                RollResult(raw=20, modifier=fighter.melee_attack,
                           total=20 + fighter.melee_attack),
                RollResult(raw=2, modifier=fighter.melee_attack,
                           total=2 + fighter.melee_attack),
            ]
            mock_dmg.return_value = RollResult(raw=5, modifier=3, total=8)

            result = AttackResolver.resolve_attack(fighter, goblin)
            assert result.hit is True
            assert result.critical is False
            # Damage is not multiplied
            assert result.total_damage == 8


# ===========================================================================
# AttackResolver — Greataxe x3 multiplier
# ===========================================================================

class TestGreataxeCritical:
    """Greataxe uses a x3 crit multiplier and threat range of 20."""

    @pytest.fixture
    def barbarian(self):
        return Character35e(
            name="Ragnar", char_class="Barbarian", level=5,
            strength=18, dexterity=10, constitution=16,
        )

    @pytest.fixture
    def target(self):
        return Character35e(name="Skeleton", char_class="Fighter", level=1)

    def test_greataxe_confirmed_crit_x3(self, barbarian, target):
        """A confirmed crit with a Greataxe (x3) triples the damage."""
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            # Both attack and confirm rolls are natural 20 → always confirm
            mock_d20.return_value = RollResult(
                raw=20, modifier=barbarian.melee_attack,
                total=20 + barbarian.melee_attack,
            )
            # 1d12 Greataxe: raw=8, STR mod applied via damage_bonus
            mock_dmg.return_value = RollResult(raw=8, modifier=4, total=12)

            result = AttackResolver.resolve_attack(
                barbarian, target,
                damage_dice_count=1,
                damage_dice_sides=12,
                damage_bonus=0,
                threat_range=20,
                damage_multiplier=3,       # Greataxe x3
            )
            assert result.hit is True
            assert result.critical is True
            assert result.total_damage == 36  # 12 × 3

    def test_greataxe_miss_no_crit(self, barbarian, target):
        """A miss with a Greataxe does 0 damage regardless of multiplier."""
        with patch("src.rules_engine.combat.roll_d20") as mock_d20:
            mock_d20.return_value = RollResult(raw=1, modifier=0, total=1)

            result = AttackResolver.resolve_attack(
                barbarian, target,
                damage_dice_count=1,
                damage_dice_sides=12,
                threat_range=20,
                damage_multiplier=3,
            )
            assert result.hit is False
            assert result.total_damage == 0
            assert result.critical is False

    def test_greataxe_x4_multiplier(self, barbarian, target):
        """x4 multiplier (e.g. scythe) quadruples damage on a confirmed crit."""
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            mock_d20.return_value = RollResult(
                raw=20, modifier=barbarian.melee_attack,
                total=20 + barbarian.melee_attack,
            )
            mock_dmg.return_value = RollResult(raw=5, modifier=4, total=9)

            result = AttackResolver.resolve_attack(
                barbarian, target,
                damage_dice_count=2,
                damage_dice_sides=4,
                damage_bonus=0,
                threat_range=20,
                damage_multiplier=4,
            )
            assert result.critical is True
            assert result.total_damage == 36  # 9 × 4


# ===========================================================================
# AttackResolver — Damage Reduction
# ===========================================================================

class TestDamageReduction:
    @pytest.fixture
    def fighter(self):
        return Character35e(name="Aldric", char_class="Fighter", level=5,
                            strength=16, dexterity=13, constitution=14)

    @pytest.fixture
    def stone_golem(self):
        return Character35e(
            name="Stone Golem", char_class="Fighter", level=1,
            damage_reduction="10/-",
        )

    def test_dr_subtracted_from_damage(self, fighter, stone_golem):
        """DR/- reduces raw damage by the listed amount."""
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            mock_d20.return_value = RollResult(
                raw=15, modifier=fighter.melee_attack,
                total=15 + fighter.melee_attack,
            )
            mock_dmg.return_value = RollResult(raw=6, modifier=3, total=15)

            result = AttackResolver.resolve_attack(fighter, stone_golem)
            assert result.hit is True
            assert result.damage_reduction_applied == 10
            assert result.total_damage == 5  # 15 − 10

    def test_dr_cannot_reduce_damage_below_zero(self, fighter, stone_golem):
        """DR cannot drive damage negative; floor is 0."""
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            mock_d20.return_value = RollResult(
                raw=15, modifier=fighter.melee_attack,
                total=15 + fighter.melee_attack,
            )
            # Damage 5 vs DR 10 → 0 (floor)
            mock_dmg.return_value = RollResult(raw=4, modifier=1, total=5)

            result = AttackResolver.resolve_attack(fighter, stone_golem)
            assert result.total_damage == 0
            assert result.damage_reduction_applied == 10

    def test_no_dr_no_reduction(self, fighter):
        """Characters without DR have damage_reduction_applied == 0."""
        defender = Character35e(name="Unarmored")
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            mock_d20.return_value = RollResult(
                raw=15, modifier=fighter.melee_attack,
                total=15 + fighter.melee_attack,
            )
            mock_dmg.return_value = RollResult(raw=6, modifier=3, total=9)

            result = AttackResolver.resolve_attack(fighter, defender)
            assert result.damage_reduction_applied == 0
            assert result.total_damage == 9

    def test_dr_magic_parsed_correctly(self, fighter):
        """DR '5/Magic' correctly subtracts 5."""
        defender = Character35e(name="Lycanthrope", damage_reduction="5/Magic")
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            mock_d20.return_value = RollResult(
                raw=15, modifier=fighter.melee_attack,
                total=15 + fighter.melee_attack,
            )
            mock_dmg.return_value = RollResult(raw=8, modifier=3, total=11)

            result = AttackResolver.resolve_attack(fighter, defender)
            assert result.damage_reduction_applied == 5
            assert result.total_damage == 6  # 11 - 5
