"""
tests/rules_engine/test_item_specials.py
-----------------------------------------
Tests for item_specials.py — D&D 3.5e DMG magic item special abilities and artifacts.
"""

from __future__ import annotations

import pytest

from src.rules_engine.item_specials import (
    ArmorAbilityType,
    ArmorSpecialAbility,
    ArtifactEntry,
    ArtifactType,
    MagicItemError,
    WeaponAbilityType,
    WeaponSpecialAbility,
    ARMOR_SPECIAL_ABILITY_REGISTRY,
    WEAPON_SPECIAL_ABILITY_REGISTRY,
    ARTIFACT_REGISTRY,
    generate_magic_armor,
    generate_magic_weapon,
    validate_armor_ability_stack,
    validate_weapon_ability_stack,
)


# ---------------------------------------------------------------------------
# T-006: ArmorSpecialAbility creation
# ---------------------------------------------------------------------------

class TestArmorSpecialAbility:
    def test_create_basic_fields(self):
        a = ArmorSpecialAbility(
            name="Glamered",
            bonus_equivalent=1,
            aura="faint illusion",
            cl=5,
            prerequisites=["disguise self"],
            market_price_gp=None,
        )
        assert a.name == "Glamered"
        assert a.bonus_equivalent == 1
        assert a.aura == "faint illusion"
        assert a.cl == 5
        assert a.prerequisites == ["disguise self"]
        assert a.market_price_gp is None

    def test_default_ability_type_is_special(self):
        a = ArmorSpecialAbility(
            name="Test", bonus_equivalent=1, aura="faint", cl=1, prerequisites=[], market_price_gp=None
        )
        assert a.ability_type == ArmorAbilityType.SPECIAL

    def test_ability_type_can_be_enhancement(self):
        a = ArmorSpecialAbility(
            name="Test", bonus_equivalent=1, aura="faint", cl=1, prerequisites=[],
            market_price_gp=None, ability_type=ArmorAbilityType.ENHANCEMENT
        )
        assert a.ability_type == ArmorAbilityType.ENHANCEMENT

    def test_multiple_prerequisites(self):
        a = ArmorSpecialAbility(
            name="Undead Controlling", bonus_equivalent=9, aura="strong necromancy",
            cl=13, prerequisites=["control undead", "create undead"], market_price_gp=None
        )
        assert len(a.prerequisites) == 2
        assert "control undead" in a.prerequisites
        assert "create undead" in a.prerequisites

    def test_market_price_gp_none_by_default_convention(self):
        a = ARMOR_SPECIAL_ABILITY_REGISTRY["Glamered"]
        assert a.market_price_gp is None

    def test_bonus_equivalent_integer(self):
        a = ArmorSpecialAbility(
            name="X", bonus_equivalent=5, aura="strong", cl=14, prerequisites=[], market_price_gp=None
        )
        assert isinstance(a.bonus_equivalent, int)

    def test_cl_integer(self):
        a = ArmorSpecialAbility(
            name="X", bonus_equivalent=1, aura="faint", cl=13, prerequisites=[], market_price_gp=None
        )
        assert isinstance(a.cl, int)

    def test_armor_ability_type_enum_values(self):
        assert ArmorAbilityType.ENHANCEMENT.value == "enhancement"
        assert ArmorAbilityType.SPECIAL.value == "special"


# ---------------------------------------------------------------------------
# T-007: WeaponSpecialAbility creation, melee_only/ranged_only
# ---------------------------------------------------------------------------

class TestWeaponSpecialAbility:
    def test_create_basic(self):
        w = WeaponSpecialAbility(
            name="Flaming", bonus_equivalent=1, aura="faint evocation", cl=10,
            prerequisites=["flame blade, flame strike, or fireball"], market_price_gp=None
        )
        assert w.name == "Flaming"
        assert w.bonus_equivalent == 1
        assert w.aura == "faint evocation"
        assert w.cl == 10
        assert w.market_price_gp is None

    def test_default_not_melee_only(self):
        w = WeaponSpecialAbility(
            name="Bane", bonus_equivalent=1, aura="faint conjuration", cl=8,
            prerequisites=["summon monster I"], market_price_gp=None
        )
        assert w.melee_only is False

    def test_default_not_ranged_only(self):
        w = WeaponSpecialAbility(
            name="Bane", bonus_equivalent=1, aura="faint conjuration", cl=8,
            prerequisites=["summon monster I"], market_price_gp=None
        )
        assert w.ranged_only is False

    def test_melee_only_flag(self):
        w = WeaponSpecialAbility(
            name="Keen", bonus_equivalent=1, aura="faint transmutation", cl=10,
            prerequisites=["keen edge"], market_price_gp=None, melee_only=True
        )
        assert w.melee_only is True
        assert w.ranged_only is False

    def test_ranged_only_flag(self):
        w = WeaponSpecialAbility(
            name="Distance", bonus_equivalent=1, aura="faint divination", cl=6,
            prerequisites=["clairaudience/clairvoyance"], market_price_gp=None, ranged_only=True
        )
        assert w.ranged_only is True
        assert w.melee_only is False

    def test_default_ability_type_is_special(self):
        w = WeaponSpecialAbility(
            name="X", bonus_equivalent=1, aura="faint", cl=1, prerequisites=[], market_price_gp=None
        )
        assert w.ability_type == WeaponAbilityType.SPECIAL

    def test_weapon_ability_type_enum_values(self):
        assert WeaponAbilityType.ENHANCEMENT.value == "enhancement"
        assert WeaponAbilityType.SPECIAL.value == "special"

    def test_market_price_gp_is_none(self):
        w = WEAPON_SPECIAL_ABILITY_REGISTRY["Vorpal"]
        assert w.market_price_gp is None


# ---------------------------------------------------------------------------
# T-011: ArtifactEntry creation
# ---------------------------------------------------------------------------

class TestArtifactEntry:
    def test_create_minor_artifact(self):
        a = ArtifactEntry(
            name="Test Minor",
            artifact_type=ArtifactType.MINOR,
            powers=["power 1"],
            drawbacks=["drawback 1"],
            lore="Some lore.",
        )
        assert a.name == "Test Minor"
        assert a.artifact_type == ArtifactType.MINOR
        assert a.powers == ["power 1"]
        assert a.drawbacks == ["drawback 1"]
        assert a.lore == "Some lore."

    def test_market_price_gp_always_none(self):
        a = ArtifactEntry(
            name="Priceless", artifact_type=ArtifactType.MAJOR,
            powers=[], drawbacks=[], lore=""
        )
        assert a.market_price_gp is None

    def test_create_major_artifact(self):
        a = ArtifactEntry(
            name="Test Major", artifact_type=ArtifactType.MAJOR,
            powers=["omnipotence"], drawbacks=["destroys world"], lore="Legendary."
        )
        assert a.artifact_type == ArtifactType.MAJOR

    def test_artifact_type_enum_values(self):
        assert ArtifactType.MINOR.value == "minor"
        assert ArtifactType.MAJOR.value == "major"

    def test_powers_is_list(self):
        a = ARTIFACT_REGISTRY["Deck of Many Things"]
        assert isinstance(a.powers, list)
        assert len(a.powers) >= 1

    def test_drawbacks_is_list(self):
        a = ARTIFACT_REGISTRY["Deck of Many Things"]
        assert isinstance(a.drawbacks, list)
        assert len(a.drawbacks) >= 1


# ---------------------------------------------------------------------------
# T-025: validate_armor_ability_stack
# ---------------------------------------------------------------------------

class TestValidateArmorAbilityStack:
    def _make_ability(self, bonus: int) -> ArmorSpecialAbility:
        return ArmorSpecialAbility(
            name="Test", bonus_equivalent=bonus, aura="faint", cl=1,
            prerequisites=[], market_price_gp=None
        )

    def test_passes_exactly_ten(self):
        abilities = [self._make_ability(3), self._make_ability(3)]
        assert validate_armor_ability_stack(4, abilities) is True

    def test_passes_below_ten(self):
        abilities = [self._make_ability(2)]
        assert validate_armor_ability_stack(3, abilities) is True

    def test_raises_at_eleven(self):
        abilities = [self._make_ability(5), self._make_ability(5)]
        with pytest.raises(MagicItemError, match="exceeds \\+10 cap"):
            validate_armor_ability_stack(1, abilities)

    def test_raises_just_over_ten(self):
        abilities = [self._make_ability(5)]
        with pytest.raises(MagicItemError):
            validate_armor_ability_stack(6, abilities)

    def test_passes_with_no_abilities(self):
        assert validate_armor_ability_stack(5, []) is True

    def test_error_message_contains_total(self):
        abilities = [self._make_ability(9)]
        with pytest.raises(MagicItemError, match="11"):
            validate_armor_ability_stack(2, abilities)


# ---------------------------------------------------------------------------
# T-026: validate_weapon_ability_stack
# ---------------------------------------------------------------------------

class TestValidateWeaponAbilityStack:
    def _make_weapon_ability(self, bonus: int, melee_only: bool = False, ranged_only: bool = False) -> WeaponSpecialAbility:
        return WeaponSpecialAbility(
            name="Test", bonus_equivalent=bonus, aura="faint", cl=1,
            prerequisites=[], market_price_gp=None,
            melee_only=melee_only, ranged_only=ranged_only,
        )

    def test_passes_exactly_ten(self):
        abilities = [self._make_weapon_ability(4), self._make_weapon_ability(3)]
        assert validate_weapon_ability_stack(3, abilities) is True

    def test_passes_below_ten(self):
        abilities = [self._make_weapon_ability(2)]
        assert validate_weapon_ability_stack(2, abilities) is True

    def test_raises_at_eleven(self):
        abilities = [self._make_weapon_ability(5), self._make_weapon_ability(5)]
        with pytest.raises(MagicItemError, match="exceeds \\+10 cap"):
            validate_weapon_ability_stack(1, abilities)

    def test_ranged_excludes_melee_only(self):
        abilities = [self._make_weapon_ability(5, melee_only=True), self._make_weapon_ability(4)]
        # base 1 + 5 (excluded for ranged) + 4 = 5 total; should pass
        assert validate_weapon_ability_stack(1, abilities, ranged=True) is True

    def test_ranged_raises_without_melee_only_exclusion(self):
        abilities = [self._make_weapon_ability(5, melee_only=True), self._make_weapon_ability(4)]
        # melee: 1 + 5 + 4 = 10, exactly at cap
        assert validate_weapon_ability_stack(1, abilities, ranged=False) is True

    def test_ranged_true_excludes_all_melee_only(self):
        # Only melee-only abilities; ranged weapon should count 0 bonus_equivalent
        abilities = [self._make_weapon_ability(9, melee_only=True)]
        assert validate_weapon_ability_stack(5, abilities, ranged=True) is True

    def test_passes_with_no_abilities(self):
        assert validate_weapon_ability_stack(5, []) is True

    def test_error_message_contains_total(self):
        abilities = [self._make_weapon_ability(9)]
        with pytest.raises(MagicItemError, match="12"):
            validate_weapon_ability_stack(3, abilities)


# ---------------------------------------------------------------------------
# T-032: ARMOR_SPECIAL_ABILITY_REGISTRY
# ---------------------------------------------------------------------------

class TestArmorRegistry:
    def test_has_16_entries(self):
        assert len(ARMOR_SPECIAL_ABILITY_REGISTRY) == 16

    def test_glamered_bonus_1(self):
        assert ARMOR_SPECIAL_ABILITY_REGISTRY["Glamered"].bonus_equivalent == 1

    def test_fortification_light_bonus_1(self):
        assert ARMOR_SPECIAL_ABILITY_REGISTRY["Fortification, Light"].bonus_equivalent == 1

    def test_fortification_moderate_bonus_3(self):
        assert ARMOR_SPECIAL_ABILITY_REGISTRY["Fortification, Moderate"].bonus_equivalent == 3

    def test_fortification_heavy_bonus_5(self):
        assert ARMOR_SPECIAL_ABILITY_REGISTRY["Fortification, Heavy"].bonus_equivalent == 5

    def test_invulnerability_bonus_3(self):
        assert ARMOR_SPECIAL_ABILITY_REGISTRY["Invulnerability"].bonus_equivalent == 3

    def test_reflecting_bonus_5(self):
        assert ARMOR_SPECIAL_ABILITY_REGISTRY["Reflecting"].bonus_equivalent == 5

    def test_etherealness_bonus_6(self):
        assert ARMOR_SPECIAL_ABILITY_REGISTRY["Etherealness"].bonus_equivalent == 6

    def test_undead_controlling_bonus_9(self):
        assert ARMOR_SPECIAL_ABILITY_REGISTRY["Undead Controlling"].bonus_equivalent == 9

    def test_spell_resistance_entries_exist(self):
        for key in ["Spell Resistance 13", "Spell Resistance 15", "Spell Resistance 17", "Spell Resistance 19"]:
            assert key in ARMOR_SPECIAL_ABILITY_REGISTRY

    def test_spell_resistance_bonus_equivalents(self):
        assert ARMOR_SPECIAL_ABILITY_REGISTRY["Spell Resistance 13"].bonus_equivalent == 2
        assert ARMOR_SPECIAL_ABILITY_REGISTRY["Spell Resistance 15"].bonus_equivalent == 3
        assert ARMOR_SPECIAL_ABILITY_REGISTRY["Spell Resistance 17"].bonus_equivalent == 4
        assert ARMOR_SPECIAL_ABILITY_REGISTRY["Spell Resistance 19"].bonus_equivalent == 5

    def test_wild_bonus_3(self):
        assert ARMOR_SPECIAL_ABILITY_REGISTRY["Wild"].bonus_equivalent == 3

    def test_all_market_price_none(self):
        for ability in ARMOR_SPECIAL_ABILITY_REGISTRY.values():
            assert ability.market_price_gp is None

    def test_all_have_aura(self):
        for ability in ARMOR_SPECIAL_ABILITY_REGISTRY.values():
            assert ability.aura != ""

    def test_all_have_cl(self):
        for ability in ARMOR_SPECIAL_ABILITY_REGISTRY.values():
            assert isinstance(ability.cl, int) and ability.cl > 0

    def test_all_have_prerequisites(self):
        for ability in ARMOR_SPECIAL_ABILITY_REGISTRY.values():
            assert isinstance(ability.prerequisites, list)


# ---------------------------------------------------------------------------
# T-033: WEAPON_SPECIAL_ABILITY_REGISTRY
# ---------------------------------------------------------------------------

class TestWeaponRegistry:
    def test_has_at_least_27_entries(self):
        assert len(WEAPON_SPECIAL_ABILITY_REGISTRY) >= 27

    def test_has_exactly_28_entries(self):
        assert len(WEAPON_SPECIAL_ABILITY_REGISTRY) == 28

    def test_vorpal_bonus_5(self):
        assert WEAPON_SPECIAL_ABILITY_REGISTRY["Vorpal"].bonus_equivalent == 5

    def test_keen_is_melee_only(self):
        assert WEAPON_SPECIAL_ABILITY_REGISTRY["Keen"].melee_only is True

    def test_disruption_is_melee_only(self):
        assert WEAPON_SPECIAL_ABILITY_REGISTRY["Disruption"].melee_only is True

    def test_distance_is_ranged_only(self):
        assert WEAPON_SPECIAL_ABILITY_REGISTRY["Distance"].ranged_only is True

    def test_seeking_is_ranged_only(self):
        assert WEAPON_SPECIAL_ABILITY_REGISTRY["Seeking"].ranged_only is True

    def test_vorpal_is_melee_only(self):
        assert WEAPON_SPECIAL_ABILITY_REGISTRY["Vorpal"].melee_only is True

    def test_speed_bonus_3(self):
        assert WEAPON_SPECIAL_ABILITY_REGISTRY["Speed"].bonus_equivalent == 3

    def test_holy_bonus_2(self):
        assert WEAPON_SPECIAL_ABILITY_REGISTRY["Holy"].bonus_equivalent == 2

    def test_flaming_bonus_1(self):
        assert WEAPON_SPECIAL_ABILITY_REGISTRY["Flaming"].bonus_equivalent == 1

    def test_all_market_price_none(self):
        for ability in WEAPON_SPECIAL_ABILITY_REGISTRY.values():
            assert ability.market_price_gp is None

    def test_anarchic_bonus_2(self):
        assert WEAPON_SPECIAL_ABILITY_REGISTRY["Anarchic"].bonus_equivalent == 2

    def test_axiomatic_bonus_2(self):
        assert WEAPON_SPECIAL_ABILITY_REGISTRY["Axiomatic"].bonus_equivalent == 2

    def test_ki_focus_melee_only(self):
        assert WEAPON_SPECIAL_ABILITY_REGISTRY["Ki Focus"].melee_only is True

    def test_mighty_cleaving_melee_only(self):
        assert WEAPON_SPECIAL_ABILITY_REGISTRY["Mighty Cleaving"].melee_only is True

    def test_throwing_melee_only(self):
        assert WEAPON_SPECIAL_ABILITY_REGISTRY["Throwing"].melee_only is True

    def test_flaming_not_melee_only(self):
        assert WEAPON_SPECIAL_ABILITY_REGISTRY["Flaming"].melee_only is False

    def test_all_have_aura(self):
        for ability in WEAPON_SPECIAL_ABILITY_REGISTRY.values():
            assert ability.aura != ""


# ---------------------------------------------------------------------------
# T-044: ARTIFACT_REGISTRY
# ---------------------------------------------------------------------------

class TestArtifactRegistry:
    def test_has_at_least_26_entries(self):
        assert len(ARTIFACT_REGISTRY) >= 26

    def test_minor_artifacts_count(self):
        minor = [a for a in ARTIFACT_REGISTRY.values() if a.artifact_type == ArtifactType.MINOR]
        assert len(minor) >= 13

    def test_major_artifacts_count(self):
        major = [a for a in ARTIFACT_REGISTRY.values() if a.artifact_type == ArtifactType.MAJOR]
        assert len(major) >= 12

    def test_all_market_price_none(self):
        for artifact in ARTIFACT_REGISTRY.values():
            assert artifact.market_price_gp is None

    def test_deck_of_many_things_is_minor(self):
        assert ARTIFACT_REGISTRY["Deck of Many Things"].artifact_type == ArtifactType.MINOR

    def test_staff_of_magi_is_major(self):
        assert ARTIFACT_REGISTRY["Staff of the Magi"].artifact_type == ArtifactType.MAJOR

    def test_sphere_of_annihilation_is_major(self):
        assert ARTIFACT_REGISTRY["Sphere of Annihilation"].artifact_type == ArtifactType.MAJOR

    def test_eye_of_vecna_is_major(self):
        assert ARTIFACT_REGISTRY["Eye of Vecna"].artifact_type == ArtifactType.MAJOR

    def test_hand_of_vecna_is_major(self):
        assert ARTIFACT_REGISTRY["Hand of Vecna"].artifact_type == ArtifactType.MAJOR

    def test_sword_of_kas_is_major(self):
        assert ARTIFACT_REGISTRY["Sword of Kas"].artifact_type == ArtifactType.MAJOR

    def test_bag_of_tricks_is_minor(self):
        assert ARTIFACT_REGISTRY["Bag of Tricks (Rust)"].artifact_type == ArtifactType.MINOR

    def test_crystal_ball_is_minor(self):
        assert ARTIFACT_REGISTRY["Crystal Ball"].artifact_type == ArtifactType.MINOR

    def test_iron_flask_is_minor(self):
        assert ARTIFACT_REGISTRY["Iron Flask"].artifact_type == ArtifactType.MINOR

    def test_portable_hole_is_minor(self):
        assert ARTIFACT_REGISTRY["Portable Hole"].artifact_type == ArtifactType.MINOR

    def test_all_have_lore(self):
        for artifact in ARTIFACT_REGISTRY.values():
            assert artifact.lore != ""

    def test_all_have_powers(self):
        for artifact in ARTIFACT_REGISTRY.values():
            assert len(artifact.powers) >= 1

    def test_all_have_drawbacks(self):
        for artifact in ARTIFACT_REGISTRY.values():
            assert len(artifact.drawbacks) >= 1

    def test_orbs_of_dragonkind_is_major(self):
        assert ARTIFACT_REGISTRY["Orbs of Dragonkind"].artifact_type == ArtifactType.MAJOR

    def test_philosophers_stone_is_major(self):
        assert ARTIFACT_REGISTRY["Philosopher's Stone"].artifact_type == ArtifactType.MAJOR


# ---------------------------------------------------------------------------
# T-042: generate_magic_armor
# ---------------------------------------------------------------------------

class TestGenerateMagicArmor:
    def test_basic_price_formula_no_specials(self):
        result = generate_magic_armor("Chain Mail", 150, 2, [])
        # 150 + (2^2)*1000 = 150 + 4000 = 4150
        assert result["market_price_gp"] == 4150

    def test_price_with_one_special(self):
        result = generate_magic_armor("Chain Mail", 150, 1, ["Glamered"])
        # 150 + (1^2)*1000 + (1^2)*1000 = 2150
        assert result["market_price_gp"] == 2150

    def test_price_with_fortification_moderate(self):
        result = generate_magic_armor("Full Plate", 1500, 1, ["Fortification, Moderate"])
        # 1500 + (1^2)*1000 + (3^2)*1000 = 1500 + 1000 + 9000 = 11500
        assert result["market_price_gp"] == 11500

    def test_name_includes_enhancement(self):
        result = generate_magic_armor("Leather Armor", 10, 3, [])
        assert "+3" in result["name"]
        assert "Leather Armor" in result["name"]

    def test_name_includes_special_abilities(self):
        result = generate_magic_armor("Scale Mail", 50, 1, ["Shadow"])
        assert "Shadow" in result["name"]

    def test_name_no_specials_no_of(self):
        result = generate_magic_armor("Breastplate", 200, 2, [])
        assert " of " not in result["name"]

    def test_enhancement_in_result(self):
        result = generate_magic_armor("Plate", 1500, 3, [])
        assert result["enhancement"] == 3

    def test_special_abilities_in_result(self):
        result = generate_magic_armor("Chain Mail", 150, 1, ["Silent Moves"])
        assert "Silent Moves" in result["special_abilities"]

    def test_base_armor_in_result(self):
        result = generate_magic_armor("Splint Mail", 200, 1, [])
        assert result["base_armor"] == "Splint Mail"

    def test_raises_on_stack_overflow(self):
        # base 1 + Undead Controlling 9 + Reflecting 5 = 15 > 10
        with pytest.raises(MagicItemError):
            generate_magic_armor("Plate", 1500, 1, ["Undead Controlling", "Reflecting"])

    def test_passes_at_ten_exactly(self):
        # base 1 + Fortification, Heavy 5 + Reflecting 5 = 11 -> raises
        # base 1 + Fortification, Heavy 5 + Invulnerability 3 + Shadow 1 = 10 -> passes
        result = generate_magic_armor("Plate", 1500, 1, ["Fortification, Heavy", "Invulnerability", "Shadow"])
        assert result["enhancement"] == 1


# ---------------------------------------------------------------------------
# T-043: generate_magic_weapon
# ---------------------------------------------------------------------------

class TestGenerateMagicWeapon:
    def test_basic_price_formula_no_specials(self):
        result = generate_magic_weapon("Longsword", 15, 2, [])
        # 15 + (2^2)*2000 = 15 + 8000 = 8015
        assert result["market_price_gp"] == 8015

    def test_price_with_flaming(self):
        result = generate_magic_weapon("Longsword", 15, 1, ["Flaming"])
        # 15 + (1^2)*2000 + (1^2)*2000 = 4015
        assert result["market_price_gp"] == 4015

    def test_price_with_vorpal(self):
        result = generate_magic_weapon("Longsword", 15, 1, ["Vorpal"])
        # 15 + (1^2)*2000 + (5^2)*2000 = 15 + 2000 + 50000 = 52015
        assert result["market_price_gp"] == 52015

    def test_name_includes_enhancement(self):
        result = generate_magic_weapon("Greataxe", 20, 3, [])
        assert "+3" in result["name"]
        assert "Greataxe" in result["name"]

    def test_name_includes_special_abilities(self):
        result = generate_magic_weapon("Dagger", 2, 1, ["Flaming"])
        assert "Flaming" in result["name"]

    def test_enhancement_in_result(self):
        result = generate_magic_weapon("Sword", 15, 4, [])
        assert result["enhancement"] == 4

    def test_ranged_flag_stored(self):
        result = generate_magic_weapon("Longbow", 75, 1, [], ranged=True)
        assert result["ranged"] is True

    def test_melee_flag_stored(self):
        result = generate_magic_weapon("Longsword", 15, 1, [], ranged=False)
        assert result["ranged"] is False

    def test_raises_on_stack_overflow(self):
        # base 1 + Vorpal 5 + Speed 3 + Holy 2 = 11 -> raises
        with pytest.raises(MagicItemError):
            generate_magic_weapon("Longsword", 15, 1, ["Vorpal", "Speed", "Holy"])

    def test_ranged_excludes_melee_only_from_cap_not_price(self):
        # Keen is melee_only; for ranged weapon it is excluded from the +10 cap check
        # but still appears in the ability list and contributes to price.
        # base 1 + Keen(1, excluded) = 1 total against cap -> passes validation
        result_ranged = generate_magic_weapon("Composite Longbow", 100, 1, ["Keen"], ranged=True)
        # price = 100 + (1^2)*2000 + (1^2)*2000 = 4100 (Keen still priced in)
        assert result_ranged["market_price_gp"] == 4100
        assert "Keen" in result_ranged["special_abilities"]

    def test_melee_only_ability_raises_if_stacks_for_melee(self):
        # For melee, Keen IS counted; Vorpal(5) + Keen(1) + base(5) = 11 -> raises
        with pytest.raises(MagicItemError):
            generate_magic_weapon("Longsword", 15, 5, ["Vorpal", "Keen"])

    def test_base_weapon_in_result(self):
        result = generate_magic_weapon("Morningstar", 8, 1, [])
        assert result["base_weapon"] == "Morningstar"
