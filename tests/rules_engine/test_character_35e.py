"""
tests/rules_engine/test_character_35e.py
----------------------------------------
Unit tests for src.rules_engine.character_35e (Character35e).
"""

import json
import pytest

from src.rules_engine.character_35e import (
    Character35e,
    Alignment,
    Size,
    _ability_modifier,
    _bab_for_level,
    _save_bonus,
)


# ---------------------------------------------------------------------------
# Ability modifier helper
# ---------------------------------------------------------------------------

class TestAbilityModifier:
    def test_score_10_gives_0(self):
        assert _ability_modifier(10) == 0

    def test_score_16_gives_3(self):
        assert _ability_modifier(16) == 3

    def test_score_8_gives_minus_1(self):
        assert _ability_modifier(8) == -1

    def test_score_1_gives_minus_5(self):
        assert _ability_modifier(1) == -5

    def test_score_20_gives_5(self):
        assert _ability_modifier(20) == 5

    def test_odd_score_11_gives_0(self):
        assert _ability_modifier(11) == 0

    def test_odd_score_15_gives_2(self):
        assert _ability_modifier(15) == 2


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

class TestCharacter35eConstruction:
    def test_name_stored(self):
        c = Character35e(name="Aldric")
        assert c.name == "Aldric"

    def test_char_id_auto_generated(self):
        c = Character35e(name="Aldric")
        assert isinstance(c.char_id, str) and len(c.char_id) == 36

    def test_explicit_char_id(self):
        c = Character35e(name="Aldric", char_id="fixed-id")
        assert c.char_id == "fixed-id"

    def test_default_class_fighter(self):
        c = Character35e(name="Aldric")
        assert c.char_class == "Fighter"

    def test_default_level_1(self):
        c = Character35e(name="Aldric")
        assert c.level == 1

    def test_default_race_human(self):
        c = Character35e(name="Aldric")
        assert c.race == "Human"

    def test_default_alignment(self):
        c = Character35e(name="Aldric")
        assert c.alignment is Alignment.TRUE_NEUTRAL

    def test_default_size_medium(self):
        c = Character35e(name="Aldric")
        assert c.size is Size.MEDIUM

    def test_default_ability_scores_are_10(self):
        c = Character35e(name="Aldric")
        for attr in ("strength", "dexterity", "constitution",
                      "intelligence", "wisdom", "charisma"):
            assert getattr(c, attr) == 10

    def test_default_equipment_empty(self):
        c = Character35e(name="Aldric")
        assert c.equipment == []

    def test_default_feats_empty(self):
        c = Character35e(name="Aldric")
        assert c.feats == []

    def test_default_skills_empty(self):
        c = Character35e(name="Aldric")
        assert c.skills == {}

    def test_slots_enabled(self):
        """Verify that slots=True prevents __dict__ creation."""
        c = Character35e(name="Aldric")
        assert not hasattr(c, "__dict__")


# ---------------------------------------------------------------------------
# Ability modifiers (property accessors)
# ---------------------------------------------------------------------------

class TestCharacterAbilityModifiers:
    def test_strength_mod(self):
        c = Character35e(name="Aldric", strength=16)
        assert c.strength_mod == 3

    def test_dexterity_mod(self):
        c = Character35e(name="Aldric", dexterity=14)
        assert c.dexterity_mod == 2

    def test_constitution_mod(self):
        c = Character35e(name="Aldric", constitution=12)
        assert c.constitution_mod == 1

    def test_intelligence_mod(self):
        c = Character35e(name="Aldric", intelligence=8)
        assert c.intelligence_mod == -1

    def test_wisdom_mod(self):
        c = Character35e(name="Aldric", wisdom=18)
        assert c.wisdom_mod == 4

    def test_charisma_mod(self):
        c = Character35e(name="Aldric", charisma=7)
        assert c.charisma_mod == -2


# ---------------------------------------------------------------------------
# Hit die & hit points
# ---------------------------------------------------------------------------

class TestCharacterHitPoints:
    def test_fighter_hit_die(self):
        c = Character35e(name="Aldric", char_class="Fighter")
        assert c.hit_die == 10

    def test_wizard_hit_die(self):
        c = Character35e(name="Merlin", char_class="Wizard")
        assert c.hit_die == 4

    def test_barbarian_hit_die(self):
        c = Character35e(name="Conan", char_class="Barbarian")
        assert c.hit_die == 12

    def test_unknown_class_hit_die_default(self):
        c = Character35e(name="X", char_class="Unknown")
        assert c.hit_die == 8

    def test_fighter_level1_hp(self):
        # Fighter: HD=10, avg_roll=6, CON=10 → mod=0 → HP = 6 × 1 = 6
        c = Character35e(name="Aldric", char_class="Fighter", level=1,
                         constitution=10)
        assert c.hit_points == 6

    def test_fighter_level5_con14_hp(self):
        # Fighter: HD=10, avg=6, CON=14 → mod=+2 → HP = (6+2) × 5 = 40
        c = Character35e(name="Aldric", char_class="Fighter", level=5,
                         constitution=14)
        assert c.hit_points == 40

    def test_wizard_level1_con8_hp(self):
        # Wizard: HD=4, avg=3, CON=8 → mod=-1 → per_level=max(1, 3-1)=2 → HP=2
        c = Character35e(name="Merlin", char_class="Wizard", level=1,
                         constitution=8)
        assert c.hit_points == 2

    def test_minimum_1_hp_per_level(self):
        # With very low CON, ensure at least 1 HP/level
        c = Character35e(name="Weakling", char_class="Wizard", level=3,
                         constitution=1)
        # HD=4, avg=3, CON=1 → mod=-5 → per_level=max(1, 3-5)=1 → HP=3
        assert c.hit_points == 3


# ---------------------------------------------------------------------------
# Base attack bonus
# ---------------------------------------------------------------------------

class TestCharacterBAB:
    def test_fighter_bab_level5(self):
        # Full progression: BAB = level
        c = Character35e(name="Aldric", char_class="Fighter", level=5)
        assert c.base_attack_bonus == 5

    def test_cleric_bab_level4(self):
        # 3/4 progression: BAB = 4 * 3 // 4 = 3
        c = Character35e(name="Priest", char_class="Cleric", level=4)
        assert c.base_attack_bonus == 3

    def test_wizard_bab_level6(self):
        # Half progression: BAB = 6 // 2 = 3
        c = Character35e(name="Merlin", char_class="Wizard", level=6)
        assert c.base_attack_bonus == 3

    def test_bab_helper_full(self):
        assert _bab_for_level("full", 10) == 10

    def test_bab_helper_three_quarter(self):
        assert _bab_for_level("three_quarter", 8) == 6

    def test_bab_helper_half(self):
        assert _bab_for_level("half", 10) == 5


# ---------------------------------------------------------------------------
# Saving throws
# ---------------------------------------------------------------------------

class TestCharacterSaves:
    def test_fighter_fortitude_good(self):
        # Fighter: fortitude is good → base = 2 + 4//2 = 4, CON=14→mod=+2 → 6
        c = Character35e(name="Aldric", char_class="Fighter", level=4,
                         constitution=14)
        assert c.fortitude_save == 6

    def test_fighter_reflex_poor(self):
        # Fighter: reflex is poor → base = 4//3 = 1, DEX=10→mod=0 → 1
        c = Character35e(name="Aldric", char_class="Fighter", level=4,
                         dexterity=10)
        assert c.reflex_save == 1

    def test_rogue_reflex_good(self):
        # Rogue: reflex is good → base = 2 + 4//2 = 4, DEX=16→mod=+3 → 7
        c = Character35e(name="Thief", char_class="Rogue", level=4,
                         dexterity=16)
        assert c.reflex_save == 7

    def test_wizard_will_good(self):
        # Wizard: will is good → base = 2 + 6//2 = 5, WIS=12→mod=+1 → 6
        c = Character35e(name="Merlin", char_class="Wizard", level=6,
                         wisdom=12)
        assert c.will_save == 6

    def test_save_bonus_good(self):
        assert _save_bonus(4, True) == 4   # 2 + 4//2

    def test_save_bonus_poor(self):
        assert _save_bonus(6, False) == 2  # 6//3


# ---------------------------------------------------------------------------
# Armour class
# ---------------------------------------------------------------------------

class TestCharacterAC:
    def test_base_ac_medium(self):
        c = Character35e(name="Aldric", dexterity=10, size=Size.MEDIUM)
        assert c.armor_class == 10

    def test_ac_with_dex(self):
        c = Character35e(name="Aldric", dexterity=16)
        assert c.armor_class == 13  # 10 + 3

    def test_ac_small_size(self):
        c = Character35e(name="Halfling", dexterity=14, size=Size.SMALL)
        assert c.armor_class == 13  # 10 + 2 + 1

    def test_ac_large_size(self):
        c = Character35e(name="Ogre", dexterity=8, size=Size.LARGE)
        assert c.armor_class == 8  # 10 + (-1) + (-1)

    def test_touch_ac(self):
        c = Character35e(name="Aldric", dexterity=14)
        assert c.touch_ac == 12  # 10 + 2

    def test_flat_footed_ac(self):
        c = Character35e(name="Aldric", dexterity=18, size=Size.MEDIUM)
        assert c.flat_footed_ac == 10  # 10 + 0 (no DEX)


# ---------------------------------------------------------------------------
# Combat
# ---------------------------------------------------------------------------

class TestCharacterCombat:
    def test_initiative(self):
        c = Character35e(name="Aldric", dexterity=14)
        assert c.initiative == 2

    def test_melee_attack(self):
        # BAB=5 + STR_mod=3 + size=0 = 8
        c = Character35e(name="Aldric", char_class="Fighter", level=5,
                         strength=16)
        assert c.melee_attack == 8

    def test_ranged_attack(self):
        # BAB=5 + DEX_mod=2 + size=0 = 7
        c = Character35e(name="Aldric", char_class="Fighter", level=5,
                         dexterity=14)
        assert c.ranged_attack == 7

    def test_grapple(self):
        # BAB=5 + STR_mod=3 + (-size)=0 = 8
        c = Character35e(name="Aldric", char_class="Fighter", level=5,
                         strength=16, size=Size.MEDIUM)
        assert c.grapple == 8

    def test_grapple_large(self):
        # BAB=5 + STR_mod=3 + (-(-1))=+1 = 9
        c = Character35e(name="Ogre", char_class="Fighter", level=5,
                         strength=16, size=Size.LARGE)
        assert c.grapple == 9


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

class TestCharacter35eSerialisation:
    def test_to_dict_contains_required_keys(self):
        c = Character35e(name="Aldric")
        d = c.to_dict()
        for key in ("char_id", "name", "char_class", "level", "strength",
                     "hit_points", "armor_class", "base_attack_bonus"):
            assert key in d

    def test_from_dict_round_trip(self):
        original = Character35e(
            name="Bridget",
            char_class="Cleric",
            level=3,
            strength=14,
            wisdom=16,
            alignment=Alignment.NEUTRAL_GOOD,
        )
        restored = Character35e.from_dict(original.to_dict())
        assert restored.char_id == original.char_id
        assert restored.name == original.name
        assert restored.char_class == original.char_class
        assert restored.level == original.level
        assert restored.strength == original.strength
        assert restored.wisdom == original.wisdom
        assert restored.alignment == original.alignment

    def test_to_json_round_trip(self):
        original = Character35e(name="Corvin", char_class="Rogue", level=4)
        json_str = original.to_json()
        restored = Character35e.from_json(json_str)
        assert restored.char_id == original.char_id
        assert restored.char_class == "Rogue"

    def test_json_is_valid_json(self):
        c = Character35e(name="Doris")
        parsed = json.loads(c.to_json())
        assert parsed["name"] == "Doris"

    def test_derived_fields_in_dict(self):
        c = Character35e(name="Aldric", char_class="Fighter", level=5,
                         strength=16, constitution=14)
        d = c.to_dict()
        assert d["hit_points"] == c.hit_points
        assert d["base_attack_bonus"] == c.base_attack_bonus
        assert d["armor_class"] == c.armor_class


# ---------------------------------------------------------------------------
# Equality and hashing
# ---------------------------------------------------------------------------

class TestCharacter35eEquality:
    def test_same_id_equal(self):
        c1 = Character35e(name="A", char_id="same-id")
        c2 = Character35e(name="B", char_id="same-id")
        assert c1 == c2

    def test_different_id_not_equal(self):
        c1 = Character35e(name="A")
        c2 = Character35e(name="A")
        assert c1 != c2

    def test_hashable_usable_in_set(self):
        c = Character35e(name="A", char_id="hash-test")
        assert c in {c}

    def test_repr_contains_name(self):
        c = Character35e(name="Aldric")
        assert "Aldric" in repr(c)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class TestEnums:
    def test_alignment_values(self):
        assert Alignment.LAWFUL_GOOD.value == "LG"
        assert Alignment.CHAOTIC_EVIL.value == "CE"

    def test_size_modifier_medium(self):
        assert Size.MEDIUM.value == 0

    def test_size_modifier_small(self):
        assert Size.SMALL.value == 1

    def test_size_modifier_large(self):
        assert Size.LARGE.value == -1
