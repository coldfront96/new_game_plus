"""
tests/rules_engine/test_feats.py
--------------------------------
Unit tests for the 3.5e Feat Engine and Class Abilities.

Verifies that feats and abilities correctly modify character stats
according to SRD rules.
"""

import pytest

from src.rules_engine.character_35e import Character35e, Size
from src.rules_engine.feat_engine import (
    BonusType,
    Feat,
    FeatRegistry,
    PowerAttackIntent,
)
from src.rules_engine.abilities import (
    AbilityRegistry,
    Evasion,
    ImprovedEvasion,
    UncannyDodge,
)


# ---------------------------------------------------------------------------
# Feat data class
# ---------------------------------------------------------------------------

class TestFeatDataClass:
    def test_feat_creation(self):
        feat = Feat(name="Improved Initiative", description="+4 to initiative")
        assert feat.name == "Improved Initiative"
        assert feat.bonus_type == BonusType.UNTYPED

    def test_feat_slots(self):
        """Verify @dataclass(slots=True) is used."""
        feat = Feat(name="Test")
        assert not hasattr(feat, "__dict__")


# ---------------------------------------------------------------------------
# Improved Initiative
# ---------------------------------------------------------------------------

class TestImprovedInitiative:
    def test_initiative_bonus_with_feat(self):
        """Character with Improved Initiative has +4 higher initiative."""
        char_with = Character35e(
            name="Fighter A",
            dexterity=14,
            feats=["Improved Initiative"],
        )
        char_without = Character35e(
            name="Fighter B",
            dexterity=14,
            feats=[],
        )
        assert char_with.initiative == char_without.initiative + 4

    def test_initiative_bonus_value(self):
        """Initiative = DEX mod + 4 with Improved Initiative."""
        char = Character35e(
            name="Quick",
            dexterity=16,  # +3 DEX mod
            feats=["Improved Initiative"],
        )
        assert char.initiative == 7  # 3 (DEX) + 4 (feat)

    def test_initiative_without_feat(self):
        """Without the feat, initiative is just DEX mod."""
        char = Character35e(name="Normal", dexterity=14)
        assert char.initiative == 2  # DEX mod only

    def test_registry_returns_bonus(self):
        """FeatRegistry.get_initiative_bonus returns correct value."""
        char = Character35e(
            name="Test",
            feats=["Improved Initiative"],
        )
        assert FeatRegistry.get_initiative_bonus(char) == 4

    def test_registry_no_bonus_without_feat(self):
        """FeatRegistry returns 0 for characters without initiative feats."""
        char = Character35e(name="Test", feats=[])
        assert FeatRegistry.get_initiative_bonus(char) == 0


# ---------------------------------------------------------------------------
# Weapon Focus
# ---------------------------------------------------------------------------

class TestWeaponFocus:
    def test_attack_bonus_with_weapon_focus(self):
        """Weapon Focus grants +1 to attack rolls."""
        char = Character35e(
            name="Swordsman",
            char_class="Fighter",
            level=1,
            strength=14,
            feats=["Weapon Focus"],
            metadata={"weapon_focus_type": "longsword"},
        )
        # BAB=1, STR mod=2, size=0, Weapon Focus=+1 → 4
        assert char.melee_attack == 4

    def test_attack_bonus_without_weapon_focus(self):
        """Without Weapon Focus, no extra attack bonus."""
        char = Character35e(
            name="Swordsman",
            char_class="Fighter",
            level=1,
            strength=14,
            feats=[],
        )
        # BAB=1, STR mod=2, size=0 → 3
        assert char.melee_attack == 3

    def test_weapon_focus_specific_weapon_match(self):
        """Weapon Focus bonus applies when weapon type matches."""
        char = Character35e(
            name="Bowman",
            feats=["Weapon Focus"],
            metadata={"weapon_focus_type": "longbow"},
        )
        bonus = FeatRegistry.get_attack_bonus(char, weapon_type="longbow")
        assert bonus == 1

    def test_weapon_focus_specific_weapon_mismatch(self):
        """Weapon Focus bonus does not apply when weapon type doesn't match."""
        char = Character35e(
            name="Bowman",
            feats=["Weapon Focus"],
            metadata={"weapon_focus_type": "longbow"},
        )
        bonus = FeatRegistry.get_attack_bonus(char, weapon_type="longsword")
        assert bonus == 0


# ---------------------------------------------------------------------------
# Power Attack
# ---------------------------------------------------------------------------

class TestPowerAttack:
    def test_has_power_attack(self):
        """Characters with Power Attack feat are detected."""
        char = Character35e(
            name="Brute",
            strength=16,
            feats=["Power Attack"],
        )
        assert FeatRegistry.has_power_attack(char)

    def test_no_power_attack(self):
        """Characters without Power Attack feat are not detected."""
        char = Character35e(name="Normal", feats=[])
        assert not FeatRegistry.has_power_attack(char)

    def test_valid_power_attack_intent(self):
        """Valid Power Attack intent passes validation."""
        char = Character35e(
            name="Fighter",
            char_class="Fighter",
            level=5,
            strength=16,
            feats=["Power Attack"],
        )
        intent = PowerAttackIntent(penalty=3)
        assert FeatRegistry.validate_power_attack(char, intent)

    def test_power_attack_penalty_exceeds_bab(self):
        """Power Attack penalty cannot exceed BAB."""
        char = Character35e(
            name="Fighter",
            char_class="Fighter",
            level=1,  # BAB = 1
            strength=16,
            feats=["Power Attack"],
        )
        intent = PowerAttackIntent(penalty=2)  # exceeds BAB of 1
        assert not FeatRegistry.validate_power_attack(char, intent)

    def test_power_attack_requires_str_13(self):
        """Power Attack requires STR 13+."""
        char = Character35e(
            name="Weak",
            char_class="Fighter",
            level=5,
            strength=12,  # below 13
            feats=["Power Attack"],
        )
        intent = PowerAttackIntent(penalty=1)
        assert not FeatRegistry.validate_power_attack(char, intent)

    def test_power_attack_one_handed_damage(self):
        """One-handed Power Attack: damage bonus == penalty."""
        char = Character35e(
            name="Fighter",
            char_class="Fighter",
            level=5,
            strength=16,
            feats=["Power Attack"],
        )
        intent = PowerAttackIntent(penalty=3, two_handed=False)
        attack_mod, damage_mod = FeatRegistry.apply_power_attack(char, intent)
        assert attack_mod == -3
        assert damage_mod == 3

    def test_power_attack_two_handed_damage(self):
        """Two-handed Power Attack: damage bonus == 2× penalty."""
        char = Character35e(
            name="Fighter",
            char_class="Fighter",
            level=5,
            strength=16,
            feats=["Power Attack"],
        )
        intent = PowerAttackIntent(penalty=3, two_handed=True)
        attack_mod, damage_mod = FeatRegistry.apply_power_attack(char, intent)
        assert attack_mod == -3
        assert damage_mod == 6

    def test_power_attack_invalid_returns_zero(self):
        """Invalid Power Attack intent returns (0, 0)."""
        char = Character35e(
            name="Fighter",
            char_class="Fighter",
            level=1,
            strength=16,
            feats=["Power Attack"],
        )
        intent = PowerAttackIntent(penalty=5)  # exceeds BAB
        attack_mod, damage_mod = FeatRegistry.apply_power_attack(char, intent)
        assert attack_mod == 0
        assert damage_mod == 0

    def test_power_attack_intent_slots(self):
        """Verify PowerAttackIntent uses slots."""
        intent = PowerAttackIntent(penalty=2)
        assert not hasattr(intent, "__dict__")


# ---------------------------------------------------------------------------
# Evasion
# ---------------------------------------------------------------------------

class TestEvasion:
    def test_rogue_level_2_has_evasion(self):
        """Rogue at level 2 gains Evasion."""
        rogue = Character35e(name="Shadow", char_class="Rogue", level=2)
        assert AbilityRegistry.has_evasion(rogue)

    def test_rogue_level_1_no_evasion(self):
        """Rogue at level 1 does not have Evasion."""
        rogue = Character35e(name="Shadow", char_class="Rogue", level=1)
        assert not AbilityRegistry.has_evasion(rogue)

    def test_monk_level_2_has_evasion(self):
        """Monk at level 2 gains Evasion."""
        monk = Character35e(name="Zen", char_class="Monk", level=2)
        assert AbilityRegistry.has_evasion(monk)

    def test_fighter_no_evasion(self):
        """Fighter never gets Evasion."""
        fighter = Character35e(name="Tank", char_class="Fighter", level=20)
        assert not AbilityRegistry.has_evasion(fighter)

    def test_evasion_zero_damage_on_save(self):
        """Evasion: successful save → zero damage."""
        damage = Evasion.resolve_damage(save_succeeded=True, base_damage=30)
        assert damage == 0

    def test_evasion_full_damage_on_fail(self):
        """Evasion: failed save → full damage."""
        damage = Evasion.resolve_damage(save_succeeded=False, base_damage=30)
        assert damage == 30

    def test_improved_evasion_zero_on_save(self):
        """Improved Evasion: successful save → zero damage."""
        damage = ImprovedEvasion.resolve_damage(save_succeeded=True, base_damage=30)
        assert damage == 0

    def test_improved_evasion_half_on_fail(self):
        """Improved Evasion: failed save → half damage."""
        damage = ImprovedEvasion.resolve_damage(save_succeeded=False, base_damage=30)
        assert damage == 15


# ---------------------------------------------------------------------------
# Uncanny Dodge
# ---------------------------------------------------------------------------

class TestUncannyDodge:
    def test_rogue_level_4_has_uncanny_dodge(self):
        """Rogue at level 4 gains Uncanny Dodge."""
        rogue = Character35e(name="Shadow", char_class="Rogue", level=4)
        assert AbilityRegistry.has_uncanny_dodge(rogue)

    def test_rogue_level_3_no_uncanny_dodge(self):
        """Rogue at level 3 does not have Uncanny Dodge."""
        rogue = Character35e(name="Shadow", char_class="Rogue", level=3)
        assert not AbilityRegistry.has_uncanny_dodge(rogue)

    def test_barbarian_level_2_has_uncanny_dodge(self):
        """Barbarian at level 2 gains Uncanny Dodge."""
        barb = Character35e(name="Rage", char_class="Barbarian", level=2)
        assert AbilityRegistry.has_uncanny_dodge(barb)

    def test_uncanny_dodge_retains_dex(self):
        """Uncanny Dodge: flat-footed AC includes DEX bonus."""
        rogue = Character35e(
            name="Shadow",
            char_class="Rogue",
            level=4,
            dexterity=16,  # +3 DEX mod
        )
        ff_ac = UncannyDodge.get_flat_footed_ac(rogue)
        # 10 + size(0) + DEX(3) = 13
        assert ff_ac == 13

    def test_normal_flat_footed_no_dex(self):
        """Normal flat-footed AC does not include DEX bonus."""
        fighter = Character35e(
            name="Tank",
            char_class="Fighter",
            level=1,
            dexterity=16,  # +3 DEX mod
        )
        # Normal flat-footed: 10 + size(0) = 10
        assert fighter.flat_footed_ac == 10

    def test_registry_resolve_flat_footed_with_uncanny(self):
        """AbilityRegistry correctly resolves flat-footed AC with Uncanny Dodge."""
        rogue = Character35e(
            name="Shadow",
            char_class="Rogue",
            level=4,
            dexterity=16,
        )
        ff_ac = AbilityRegistry.resolve_flat_footed_ac(rogue)
        assert ff_ac == 13  # retains DEX bonus

    def test_registry_resolve_flat_footed_without_uncanny(self):
        """AbilityRegistry uses normal flat-footed AC without Uncanny Dodge."""
        fighter = Character35e(
            name="Tank",
            char_class="Fighter",
            level=1,
            dexterity=16,
        )
        ff_ac = AbilityRegistry.resolve_flat_footed_ac(fighter)
        assert ff_ac == 10  # no DEX bonus


# ---------------------------------------------------------------------------
# Integration: Character properties with feats
# ---------------------------------------------------------------------------

class TestCharacterFeatIntegration:
    def test_initiative_property_includes_feat(self):
        """Character.initiative integrates Improved Initiative bonus."""
        char = Character35e(
            name="Quick",
            dexterity=12,  # +1 DEX mod
            feats=["Improved Initiative"],
        )
        assert char.initiative == 5  # 1 + 4

    def test_melee_attack_includes_weapon_focus(self):
        """Character.melee_attack integrates Weapon Focus bonus."""
        char = Character35e(
            name="Swordsman",
            char_class="Fighter",
            level=1,
            strength=14,  # +2 STR mod
            feats=["Weapon Focus"],
            metadata={"weapon_focus_type": "longsword"},
        )
        # BAB(1) + STR(2) + size(0) + feat(1) = 4
        assert char.melee_attack == 4

    def test_ranged_attack_includes_weapon_focus(self):
        """Character.ranged_attack integrates Weapon Focus bonus."""
        char = Character35e(
            name="Archer",
            char_class="Fighter",
            level=1,
            dexterity=14,  # +2 DEX mod
            feats=["Weapon Focus"],
            metadata={"weapon_focus_type": "longbow"},
        )
        # BAB(1) + DEX(2) + size(0) + feat(1) = 4
        assert char.ranged_attack == 4

    def test_multiple_feats(self):
        """Character with multiple feats gets all bonuses applied."""
        char = Character35e(
            name="Elite Fighter",
            char_class="Fighter",
            level=5,
            strength=16,
            dexterity=14,
            feats=["Improved Initiative", "Weapon Focus", "Power Attack"],
            metadata={"weapon_focus_type": "greatsword"},
        )
        # Initiative: DEX(2) + feat(4) = 6
        assert char.initiative == 6
        # Melee: BAB(5) + STR(3) + size(0) + WF(1) = 9
        assert char.melee_attack == 9
