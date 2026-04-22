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


# ---------------------------------------------------------------------------
# FeatPrerequisite & meets_prerequisites
# ---------------------------------------------------------------------------

class TestFeatPrerequisites:
    """Verify the prerequisite engine against SRD rules."""

    # ---- Power Attack (STR 13) -----------------------------------------------

    def test_power_attack_meets_prereqs_str_13(self):
        char = Character35e(name="Brute", strength=13, feats=[])
        assert FeatRegistry.meets_prerequisites(char, "Power Attack")

    def test_power_attack_fails_prereqs_str_12(self):
        char = Character35e(name="Weak", strength=12, feats=[])
        assert not FeatRegistry.meets_prerequisites(char, "Power Attack")

    # ---- Cleave (STR 13 + Power Attack) --------------------------------------

    def test_cleave_meets_prereqs(self):
        char = Character35e(name="Cleaver", strength=13, feats=["Power Attack"])
        assert FeatRegistry.meets_prerequisites(char, "Cleave")

    def test_cleave_fails_without_power_attack(self):
        char = Character35e(name="Cleaver", strength=13, feats=[])
        assert not FeatRegistry.meets_prerequisites(char, "Cleave")

    def test_cleave_fails_low_str(self):
        char = Character35e(name="Cleaver", strength=12, feats=["Power Attack"])
        assert not FeatRegistry.meets_prerequisites(char, "Cleave")

    # ---- Great Cleave (STR 13 + Cleave + BAB +4) -----------------------------

    def test_great_cleave_meets_prereqs(self):
        char = Character35e(
            name="GreatCleaver",
            char_class="Fighter",
            level=4,   # BAB 4
            strength=13,
            feats=["Power Attack", "Cleave"],
        )
        assert FeatRegistry.meets_prerequisites(char, "Great Cleave")

    def test_great_cleave_fails_low_bab(self):
        char = Character35e(
            name="GreatCleaver",
            char_class="Fighter",
            level=3,   # BAB 3
            strength=13,
            feats=["Power Attack", "Cleave"],
        )
        assert not FeatRegistry.meets_prerequisites(char, "Great Cleave")

    # ---- Dodge (DEX 13) -------------------------------------------------------

    def test_dodge_meets_prereqs(self):
        char = Character35e(name="Dodger", dexterity=13, feats=[])
        assert FeatRegistry.meets_prerequisites(char, "Dodge")

    def test_dodge_fails_low_dex(self):
        char = Character35e(name="Clumsy", dexterity=12, feats=[])
        assert not FeatRegistry.meets_prerequisites(char, "Dodge")

    # ---- Mobility (DEX 13 + Dodge) -------------------------------------------

    def test_mobility_meets_prereqs(self):
        char = Character35e(name="Mobile", dexterity=13, feats=["Dodge"])
        assert FeatRegistry.meets_prerequisites(char, "Mobility")

    def test_mobility_fails_without_dodge(self):
        char = Character35e(name="Mobile", dexterity=13, feats=[])
        assert not FeatRegistry.meets_prerequisites(char, "Mobility")

    # ---- Spring Attack (DEX 13 + Dodge + Mobility + BAB +4) ------------------

    def test_spring_attack_meets_prereqs(self):
        char = Character35e(
            name="SpringAttacker",
            char_class="Fighter",
            level=4,
            dexterity=13,
            feats=["Dodge", "Mobility"],
        )
        assert FeatRegistry.meets_prerequisites(char, "Spring Attack")

    def test_spring_attack_fails_low_bab(self):
        char = Character35e(
            name="SpringAttacker",
            char_class="Fighter",
            level=3,
            dexterity=13,
            feats=["Dodge", "Mobility"],
        )
        assert not FeatRegistry.meets_prerequisites(char, "Spring Attack")

    # ---- Weapon Focus (BAB +1) ------------------------------------------------

    def test_weapon_focus_meets_prereqs(self):
        char = Character35e(
            name="Swordsman",
            char_class="Fighter",
            level=1,  # BAB 1
            feats=[],
        )
        assert FeatRegistry.meets_prerequisites(char, "Weapon Focus")

    def test_weapon_focus_fails_bab_0(self):
        char = Character35e(
            name="Wizard",
            char_class="Wizard",
            level=1,  # BAB 0 for half-progression at level 1
            feats=[],
        )
        assert not FeatRegistry.meets_prerequisites(char, "Weapon Focus")

    # ---- Weapon Specialization (Weapon Focus + Fighter 4) --------------------

    def test_weapon_spec_meets_prereqs(self):
        char = Character35e(
            name="Specialist",
            char_class="Fighter",
            level=4,
            feats=["Weapon Focus"],
        )
        assert FeatRegistry.meets_prerequisites(char, "Weapon Specialization")

    def test_weapon_spec_fails_wrong_class(self):
        char = Character35e(
            name="Specialist",
            char_class="Ranger",
            level=4,
            feats=["Weapon Focus"],
        )
        assert not FeatRegistry.meets_prerequisites(char, "Weapon Specialization")

    def test_weapon_spec_fails_low_level(self):
        char = Character35e(
            name="Specialist",
            char_class="Fighter",
            level=3,
            feats=["Weapon Focus"],
        )
        assert not FeatRegistry.meets_prerequisites(char, "Weapon Specialization")

    def test_weapon_spec_fails_no_weapon_focus(self):
        char = Character35e(
            name="Specialist",
            char_class="Fighter",
            level=4,
            feats=[],
        )
        assert not FeatRegistry.meets_prerequisites(char, "Weapon Specialization")

    # ---- Improved Critical (BAB +8) ------------------------------------------

    def test_improved_critical_meets_prereqs(self):
        char = Character35e(
            name="Crit",
            char_class="Fighter",
            level=8,   # BAB 8
            feats=[],
        )
        assert FeatRegistry.meets_prerequisites(char, "Improved Critical")

    def test_improved_critical_fails_low_bab(self):
        char = Character35e(
            name="Crit",
            char_class="Fighter",
            level=7,   # BAB 7
            feats=[],
        )
        assert not FeatRegistry.meets_prerequisites(char, "Improved Critical")

    # ---- No-prerequisite feats always pass -----------------------------------

    def test_combat_reflexes_no_prereqs(self):
        char = Character35e(name="Alerter", feats=[])
        assert FeatRegistry.meets_prerequisites(char, "Combat Reflexes")

    def test_toughness_no_prereqs(self):
        char = Character35e(name="Hardy", feats=[])
        assert FeatRegistry.meets_prerequisites(char, "Toughness")

    def test_great_fortitude_no_prereqs(self):
        char = Character35e(name="Hardy", feats=[])
        assert FeatRegistry.meets_prerequisites(char, "Great Fortitude")

    def test_iron_will_no_prereqs(self):
        char = Character35e(name="Willful", feats=[])
        assert FeatRegistry.meets_prerequisites(char, "Iron Will")

    def test_lightning_reflexes_no_prereqs(self):
        char = Character35e(name="Quick", feats=[])
        assert FeatRegistry.meets_prerequisites(char, "Lightning Reflexes")

    def test_empower_spell_no_prereqs(self):
        char = Character35e(name="Mage", char_class="Wizard", feats=[])
        assert FeatRegistry.meets_prerequisites(char, "Empower Spell")

    def test_maximize_spell_no_prereqs(self):
        char = Character35e(name="Mage", char_class="Wizard", feats=[])
        assert FeatRegistry.meets_prerequisites(char, "Maximize Spell")

    # ---- Unknown feats (no entry → no prereqs) --------------------------------

    def test_unknown_feat_no_prereqs(self):
        char = Character35e(name="Anyone", feats=[])
        assert FeatRegistry.meets_prerequisites(char, "Some Future Feat")


# ---------------------------------------------------------------------------
# add_feat
# ---------------------------------------------------------------------------

class TestAddFeat:
    def test_add_feat_success(self):
        char = Character35e(name="Brute", strength=13, feats=[])
        result = FeatRegistry.add_feat(char, "Power Attack")
        assert result is True
        assert "Power Attack" in char.feats

    def test_add_feat_fails_prereqs(self):
        char = Character35e(name="Weakling", strength=10, feats=[])
        result = FeatRegistry.add_feat(char, "Power Attack")
        assert result is False
        assert "Power Attack" not in char.feats

    def test_add_feat_idempotent(self):
        char = Character35e(name="Brute", strength=13, feats=["Power Attack"])
        result = FeatRegistry.add_feat(char, "Power Attack")
        assert result is True
        assert char.feats.count("Power Attack") == 1

    def test_add_feat_chain(self):
        """Cleave can be added after Power Attack is added via add_feat."""
        char = Character35e(
            name="Cleaver",
            char_class="Fighter",
            level=1,
            strength=13,
            feats=[],
        )
        assert FeatRegistry.add_feat(char, "Power Attack") is True
        assert FeatRegistry.add_feat(char, "Cleave") is True
        assert "Cleave" in char.feats

    def test_add_feat_chain_fails_without_first(self):
        """Cleave cannot be added without Power Attack."""
        char = Character35e(name="Cleaver", strength=13, feats=[])
        assert FeatRegistry.add_feat(char, "Cleave") is False


# ---------------------------------------------------------------------------
# Toughness (HP bonus)
# ---------------------------------------------------------------------------

class TestToughness:
    def test_toughness_adds_3_hp(self):
        base_char = Character35e(name="Normal", char_class="Fighter", level=1)
        tough_char = Character35e(
            name="Hardy", char_class="Fighter", level=1, feats=["Toughness"]
        )
        assert tough_char.hit_points == base_char.hit_points + 3

    def test_toughness_hp_bonus_is_flat_not_per_level(self):
        char_l1 = Character35e(
            name="Hardy", char_class="Fighter", level=1, feats=["Toughness"]
        )
        char_l5 = Character35e(
            name="Hardy", char_class="Fighter", level=5, feats=["Toughness"]
        )
        base_l1 = Character35e(name="Normal", char_class="Fighter", level=1)
        base_l5 = Character35e(name="Normal", char_class="Fighter", level=5)
        # Bonus is always exactly +3, regardless of level
        assert char_l1.hit_points - base_l1.hit_points == 3
        assert char_l5.hit_points - base_l5.hit_points == 3

    def test_get_hp_bonus_returns_3(self):
        char = Character35e(name="Hardy", feats=["Toughness"])
        assert FeatRegistry.get_hp_bonus(char) == 3

    def test_get_hp_bonus_no_feat(self):
        char = Character35e(name="Normal", feats=[])
        assert FeatRegistry.get_hp_bonus(char) == 0


# ---------------------------------------------------------------------------
# Great Fortitude, Iron Will, Lightning Reflexes (save bonuses)
# ---------------------------------------------------------------------------

class TestSaveFeatBonuses:
    def test_great_fortitude_adds_2_to_fortitude(self):
        base = Character35e(name="Base", char_class="Fighter", level=1)
        feat = Character35e(
            name="GF", char_class="Fighter", level=1, feats=["Great Fortitude"]
        )
        assert feat.fortitude_save == base.fortitude_save + 2

    def test_iron_will_adds_2_to_will(self):
        base = Character35e(name="Base", char_class="Fighter", level=1)
        feat = Character35e(
            name="IW", char_class="Fighter", level=1, feats=["Iron Will"]
        )
        assert feat.will_save == base.will_save + 2

    def test_lightning_reflexes_adds_2_to_reflex(self):
        base = Character35e(name="Base", char_class="Fighter", level=1)
        feat = Character35e(
            name="LR", char_class="Fighter", level=1, feats=["Lightning Reflexes"]
        )
        assert feat.reflex_save == base.reflex_save + 2

    def test_great_fortitude_does_not_affect_other_saves(self):
        base = Character35e(name="Base", char_class="Fighter", level=1)
        feat = Character35e(
            name="GF", char_class="Fighter", level=1, feats=["Great Fortitude"]
        )
        assert feat.reflex_save == base.reflex_save
        assert feat.will_save == base.will_save

    def test_iron_will_does_not_affect_other_saves(self):
        base = Character35e(name="Base", char_class="Fighter", level=1)
        feat = Character35e(
            name="IW", char_class="Fighter", level=1, feats=["Iron Will"]
        )
        assert feat.fortitude_save == base.fortitude_save
        assert feat.reflex_save == base.reflex_save

    def test_lightning_reflexes_does_not_affect_other_saves(self):
        base = Character35e(name="Base", char_class="Fighter", level=1)
        feat = Character35e(
            name="LR", char_class="Fighter", level=1, feats=["Lightning Reflexes"]
        )
        assert feat.fortitude_save == base.fortitude_save
        assert feat.will_save == base.will_save

    def test_registry_get_fortitude_bonus(self):
        char = Character35e(name="GF", feats=["Great Fortitude"])
        assert FeatRegistry.get_fortitude_bonus(char) == 2

    def test_registry_get_reflex_bonus(self):
        char = Character35e(name="LR", feats=["Lightning Reflexes"])
        assert FeatRegistry.get_reflex_bonus(char) == 2

    def test_registry_get_will_bonus(self):
        char = Character35e(name="IW", feats=["Iron Will"])
        assert FeatRegistry.get_will_bonus(char) == 2

    def test_all_three_save_feats_stack(self):
        char = Character35e(
            name="Survivor",
            char_class="Fighter",
            level=1,
            feats=["Great Fortitude", "Iron Will", "Lightning Reflexes"],
        )
        base = Character35e(name="Base", char_class="Fighter", level=1)
        assert char.fortitude_save == base.fortitude_save + 2
        assert char.reflex_save == base.reflex_save + 2
        assert char.will_save == base.will_save + 2


# ---------------------------------------------------------------------------
# Dodge (AC bonus)
# ---------------------------------------------------------------------------

class TestDodge:
    def test_dodge_adds_1_to_ac(self):
        base = Character35e(name="Base", dexterity=13)
        dodge = Character35e(name="Dodger", dexterity=13, feats=["Dodge"])
        assert dodge.armor_class == base.armor_class + 1

    def test_get_ac_bonus_dodge(self):
        char = Character35e(name="Dodger", dexterity=13, feats=["Dodge"])
        assert FeatRegistry.get_ac_bonus(char) == 1

    def test_get_ac_bonus_no_dodge(self):
        char = Character35e(name="Normal", feats=[])
        assert FeatRegistry.get_ac_bonus(char) == 0


# ---------------------------------------------------------------------------
# Weapon Specialization (damage bonus)
# ---------------------------------------------------------------------------

class TestWeaponSpecialization:
    def test_get_damage_bonus_with_weapon_spec(self):
        char = Character35e(
            name="Specialist",
            char_class="Fighter",
            level=4,
            feats=["Weapon Focus", "Weapon Specialization"],
            metadata={"weapon_focus_type": "longsword"},
        )
        assert FeatRegistry.get_damage_bonus(char, weapon_type="longsword") == 2

    def test_get_damage_bonus_wrong_weapon(self):
        char = Character35e(
            name="Specialist",
            char_class="Fighter",
            level=4,
            feats=["Weapon Focus", "Weapon Specialization"],
            metadata={"weapon_focus_type": "longsword"},
        )
        assert FeatRegistry.get_damage_bonus(char, weapon_type="greatsword") == 0

    def test_get_damage_bonus_no_feat(self):
        char = Character35e(name="Normal", feats=[])
        assert FeatRegistry.get_damage_bonus(char) == 0

    def test_get_damage_bonus_no_weapon_type_arg(self):
        """Without a weapon_type arg, Weapon Specialization always applies."""
        char = Character35e(
            name="Specialist",
            feats=["Weapon Specialization"],
            metadata={"weapon_focus_type": "longsword"},
        )
        assert FeatRegistry.get_damage_bonus(char) == 2


# ---------------------------------------------------------------------------
# Improved Critical (threat range multiplier)
# ---------------------------------------------------------------------------

class TestImprovedCritical:
    def test_threat_range_multiplier_with_feat(self):
        char = Character35e(name="Critter", feats=["Improved Critical"])
        assert FeatRegistry.get_threat_range_multiplier(char) == 2

    def test_threat_range_multiplier_without_feat(self):
        char = Character35e(name="Normal", feats=[])
        assert FeatRegistry.get_threat_range_multiplier(char) == 1


# ---------------------------------------------------------------------------
# Combat Reflexes (AoO count)
# ---------------------------------------------------------------------------

class TestCombatReflexes:
    def test_aoo_count_without_combat_reflexes(self):
        char = Character35e(name="Normal", dexterity=14, feats=[])
        assert FeatRegistry.get_aoo_count(char) == 1

    def test_aoo_count_with_combat_reflexes_positive_dex(self):
        char = Character35e(name="Alert", dexterity=14, feats=["Combat Reflexes"])
        # 1 + DEX mod(2) = 3
        assert FeatRegistry.get_aoo_count(char) == 3

    def test_aoo_count_minimum_1(self):
        char = Character35e(name="Clumsy", dexterity=6, feats=["Combat Reflexes"])
        # DEX mod = -2; max(1, 1 + -2) = max(1, -1) = 1
        assert FeatRegistry.get_aoo_count(char) == 1


# ---------------------------------------------------------------------------
# FEAT_CATALOG completeness
# ---------------------------------------------------------------------------

class TestFeatCatalog:
    """Verify all required SRD feats are present in the catalog."""

    def test_catalog_imported(self):
        from src.rules_engine.feat_engine import FEAT_CATALOG
        assert isinstance(FEAT_CATALOG, dict)

    def test_required_combat_feats_present(self):
        from src.rules_engine.feat_engine import FEAT_CATALOG
        required = [
            "Power Attack",
            "Cleave",
            "Great Cleave",
            "Dodge",
            "Mobility",
            "Spring Attack",
            "Combat Reflexes",
            "Weapon Focus",
            "Weapon Specialization",
            "Improved Critical",
        ]
        for feat_name in required:
            assert feat_name in FEAT_CATALOG, f"Missing: {feat_name}"

    def test_required_general_feats_present(self):
        from src.rules_engine.feat_engine import FEAT_CATALOG
        required = ["Toughness", "Great Fortitude", "Iron Will", "Lightning Reflexes"]
        for feat_name in required:
            assert feat_name in FEAT_CATALOG, f"Missing: {feat_name}"

    def test_metamagic_feats_present(self):
        from src.rules_engine.feat_engine import FEAT_CATALOG
        required = ["Empower Spell", "Maximize Spell"]
        for feat_name in required:
            assert feat_name in FEAT_CATALOG, f"Missing: {feat_name}"

    def test_catalog_entries_are_feat_instances(self):
        from src.rules_engine.feat_engine import FEAT_CATALOG, Feat
        for name, feat in FEAT_CATALOG.items():
            assert isinstance(feat, Feat), f"{name} is not a Feat instance"

    def test_feat_prerequisite_slots(self):
        from src.rules_engine.feat_engine import FeatPrerequisite
        prereq = FeatPrerequisite(min_str=13)
        assert not hasattr(prereq, "__dict__")

    def test_feat_dataclass_slots(self):
        from src.rules_engine.feat_engine import Feat
        feat = Feat(name="Test Feat")
        assert not hasattr(feat, "__dict__")

