"""
tests/rules_engine/test_magic.py
---------------------------------
Unit tests for the D&D 3.5e spellcasting engine.

Verifies spell definitions, registry, slot management, spellbook,
and casting math (DC, caster level).
"""

import pytest

from src.rules_engine.magic import (
    MAGE_ARMOR,
    MAGIC_MISSILE,
    # Phase 1 – Level 0
    DETECT_MAGIC,
    RAY_OF_FROST,
    RESISTANCE,
    MAGE_HAND,
    READ_MAGIC,
    ACID_SPLASH,
    DAZE,
    LIGHT,
    # Phase 1 – Level 1
    CHARM_PERSON,
    COLOR_SPRAY,
    FEATHER_FALL,
    GREASE,
    RAY_OF_ENFEEBLEMENT,
    TRUE_STRIKE,
    CAUSE_FEAR,
    ENLARGE_PERSON,
    # Phase 1 – Level 2
    SCORCHING_RAY,
    INVISIBILITY,
    MIRROR_IMAGE,
    WEB,
    BULLS_STRENGTH,
    BLUR,
    RESIST_ENERGY,
    BEARS_ENDURANCE,
    # Phase 1 – Level 3
    FIREBALL,
    LIGHTNING_BOLT,
    DISPEL_MAGIC,
    HASTE,
    HOLD_PERSON,
    FLY,
    SLOW,
    VAMPIRIC_TOUCH,
    Spell,
    SpellComponent,
    SpellRegistry,
    SpellSchool,
    create_default_registry,
)
from src.rules_engine.spellcasting import (
    Spellbook,
    SpellResolver,
    SpellSlotManager,
    get_key_ability,
    is_caster_class,
    _bonus_spells_for_level,
)
from src.rules_engine.character_35e import Character35e


# ---------------------------------------------------------------------------
# Spell dataclass tests
# ---------------------------------------------------------------------------

class TestSpellDataclass:
    def test_magic_missile_attributes(self):
        assert MAGIC_MISSILE.name == "Magic Missile"
        assert MAGIC_MISSILE.level == 1
        assert MAGIC_MISSILE.school == SpellSchool.EVOCATION
        assert SpellComponent.VERBAL in MAGIC_MISSILE.components
        assert SpellComponent.SOMATIC in MAGIC_MISSILE.components
        assert "Force" in MAGIC_MISSILE.descriptor

    def test_mage_armor_attributes(self):
        assert MAGE_ARMOR.name == "Mage Armor"
        assert MAGE_ARMOR.level == 1
        assert MAGE_ARMOR.school == SpellSchool.CONJURATION
        assert MAGE_ARMOR.subschool == "Creation"
        assert SpellComponent.FOCUS in MAGE_ARMOR.components

    def test_spell_slots_true(self):
        """Verify Spell uses __slots__ for memory efficiency."""
        assert hasattr(Spell, "__slots__")

    def test_magic_missile_effect_callback(self):
        result = MAGIC_MISSILE.effect_callback(None, None, 1)
        assert result["damage_type"] == "Force"
        assert result["num_missiles"] == 1
        assert result["auto_hit"] is True

    def test_magic_missile_scales_with_caster_level(self):
        # CL 3 => 2 missiles, CL 5 => 3, CL 9 => 5 (max)
        result_cl3 = MAGIC_MISSILE.effect_callback(None, None, 3)
        assert result_cl3["num_missiles"] == 2

        result_cl5 = MAGIC_MISSILE.effect_callback(None, None, 5)
        assert result_cl5["num_missiles"] == 3

        result_cl9 = MAGIC_MISSILE.effect_callback(None, None, 9)
        assert result_cl9["num_missiles"] == 5

        # CL 11 still capped at 5
        result_cl11 = MAGIC_MISSILE.effect_callback(None, None, 11)
        assert result_cl11["num_missiles"] == 5

    def test_mage_armor_effect_callback(self):
        result = MAGE_ARMOR.effect_callback(None, None, 5)
        assert result["ac_bonus"] == 4
        assert result["bonus_type"] == "armor"
        assert result["duration_hours"] == 5
        assert result["force_effect"] is True


# ---------------------------------------------------------------------------
# SpellRegistry tests
# ---------------------------------------------------------------------------

class TestSpellRegistry:
    def test_register_and_get(self):
        registry = SpellRegistry()
        registry.register(MAGIC_MISSILE)
        assert registry.get("Magic Missile") is MAGIC_MISSILE

    def test_get_nonexistent_returns_none(self):
        registry = SpellRegistry()
        assert registry.get("Nonexistent Spell") is None

    def test_duplicate_registration_raises(self):
        registry = SpellRegistry()
        registry.register(MAGIC_MISSILE)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(MAGIC_MISSILE)

    def test_get_by_level(self):
        registry = create_default_registry()
        level_1 = registry.get_by_level(1)
        names = [s.name for s in level_1]
        assert "Magic Missile" in names
        assert "Mage Armor" in names

    def test_get_by_school(self):
        registry = create_default_registry()
        evocations = registry.get_by_school(SpellSchool.EVOCATION)
        assert any(s.name == "Magic Missile" for s in evocations)

        conjurations = registry.get_by_school(SpellSchool.CONJURATION)
        assert any(s.name == "Mage Armor" for s in conjurations)

    def test_count(self):
        registry = create_default_registry()
        assert registry.count == 43
        assert len(registry) == 43

    def test_contains(self):
        registry = create_default_registry()
        assert "Magic Missile" in registry
        assert "Wish" not in registry


# ---------------------------------------------------------------------------
# SpellSlotManager tests
# ---------------------------------------------------------------------------

class TestSpellSlotManager:
    def test_wizard_level_1_base_slots(self):
        """A Level 1 Wizard with INT 10 (mod 0) has 3 cantrips, 1 first-level."""
        slots = SpellSlotManager.for_wizard(level=1, int_mod=0)
        assert slots.max_slots[0] == 3  # 0-level (cantrips)
        assert slots.max_slots[1] == 1  # 1st-level
        assert slots.max_slots[2] == 0  # 2nd-level (not available)

    def test_wizard_level_1_with_high_int(self):
        """A Level 1 Wizard with INT 16 (mod +3) gets bonus 1st-level slots.

        Per 3.5e SRD: bonus spells for level 1 with mod 3 = 1 + (3-1)//4 = 1.
        So total 1st-level = 1 (base) + 1 (bonus) = 2.
        """
        slots = SpellSlotManager.for_wizard(level=1, int_mod=3)
        assert slots.max_slots[0] == 3  # Cantrips: no bonus
        assert slots.max_slots[1] == 2  # 1 base + 1 bonus

    def test_wizard_level_1_base_slots_srd_verification(self):
        """VERIFICATION TEST: Level 1 Wizard correctly has three 0-level
        and one 1st-level spell slots (base, before bonus spells from INT).

        Per 3.5e SRD Wizard table:
        - Level 1: 3 cantrips (0-level), 1 first-level slot (base).
        """
        # Using INT 10 (mod 0) to test pure base slots
        slots = SpellSlotManager.for_wizard(level=1, int_mod=0)
        assert slots.max_slots[0] == 3, "Level 1 Wizard should have 3 cantrip slots"
        assert slots.max_slots[1] == 1, "Level 1 Wizard should have 1 first-level slot"

    def test_expend_and_available(self):
        slots = SpellSlotManager.for_wizard(level=1, int_mod=0)
        assert slots.available(1) == 1
        assert slots.expend(1) is True
        assert slots.available(1) == 0
        assert slots.expend(1) is False  # No more slots

    def test_rest_restores_slots(self):
        slots = SpellSlotManager.for_wizard(level=1, int_mod=0)
        slots.expend(0)
        slots.expend(0)
        slots.expend(1)
        assert slots.available(0) == 1
        assert slots.available(1) == 0

        slots.rest()
        assert slots.available(0) == 3
        assert slots.available(1) == 1

    def test_sorcerer_level_1_slots(self):
        slots = SpellSlotManager.for_sorcerer(level=1, cha_mod=3)
        assert slots.max_slots[0] == 5  # Cantrips
        assert slots.max_slots[1] == 4  # 3 base + 1 bonus

    def test_invalid_class_raises(self):
        with pytest.raises(ValueError, match="not a recognised caster"):
            SpellSlotManager.for_class("Fighter", 1, 0)

    def test_total_max_and_available(self):
        slots = SpellSlotManager.for_wizard(level=1, int_mod=0)
        assert slots.total_max() == 4  # 3 + 1
        assert slots.total_available() == 4
        slots.expend(0)
        assert slots.total_available() == 3

    def test_slots_true_attribute(self):
        """Verify SpellSlotManager uses __slots__."""
        assert hasattr(SpellSlotManager, "__slots__")


# ---------------------------------------------------------------------------
# Spellbook tests
# ---------------------------------------------------------------------------

class TestSpellbook:
    def test_add_and_check_known(self):
        book = Spellbook()
        book.add_known("Magic Missile", spell_level=1)
        assert book.is_known("Magic Missile")
        assert not book.is_known("Fireball")

    def test_remove_known(self):
        book = Spellbook()
        book.add_known("Magic Missile", spell_level=1)
        book.remove_known("Magic Missile")
        assert not book.is_known("Magic Missile")

    def test_prepare_known_spell(self):
        book = Spellbook()
        book.add_known("Magic Missile", spell_level=1)
        assert book.prepare("Magic Missile", spell_level=1) is True
        assert "Magic Missile" in book.get_prepared(1)

    def test_prepare_unknown_spell_fails(self):
        book = Spellbook()
        assert book.prepare("Fireball", spell_level=3) is False

    def test_unprepare_all(self):
        book = Spellbook()
        book.add_known("Magic Missile", spell_level=1)
        book.prepare("Magic Missile", spell_level=1)
        book.unprepare_all()
        assert book.get_prepared(1) == []

    def test_slots_true_attribute(self):
        """Verify Spellbook uses __slots__."""
        assert hasattr(Spellbook, "__slots__")


# ---------------------------------------------------------------------------
# SpellResolver tests
# ---------------------------------------------------------------------------

class TestSpellResolver:
    def test_spell_save_dc_wizard(self):
        """DC = 10 + spell_level + INT mod.

        Wizard with INT 16 (+3 mod) casting a 1st-level spell: DC = 14.
        """
        resolver = SpellResolver(caster_level=1, key_ability_mod=3)
        assert resolver.spell_save_dc(spell_level=1) == 14

    def test_spell_save_dc_cantrip(self):
        """DC for a 0-level spell with +3 mod: 10 + 0 + 3 = 13."""
        resolver = SpellResolver(caster_level=1, key_ability_mod=3)
        assert resolver.spell_save_dc(spell_level=0) == 13

    def test_spell_save_dc_high_level(self):
        """DC for a 9th-level spell with +5 mod: 10 + 9 + 5 = 24."""
        resolver = SpellResolver(caster_level=17, key_ability_mod=5)
        assert resolver.spell_save_dc(spell_level=9) == 24

    def test_caster_level(self):
        resolver = SpellResolver(caster_level=5, key_ability_mod=3)
        assert resolver.get_caster_level() == 5

    def test_resolve_spell_magic_missile(self):
        registry = create_default_registry()
        resolver = SpellResolver(
            caster_level=5, key_ability_mod=3, spell_registry=registry,
        )
        result = resolver.resolve_spell("Magic Missile")
        assert result is not None
        assert result["num_missiles"] == 3
        assert result["damage_type"] == "Force"

    def test_resolve_spell_not_found(self):
        registry = create_default_registry()
        resolver = SpellResolver(
            caster_level=1, key_ability_mod=3, spell_registry=registry,
        )
        assert resolver.resolve_spell("Nonexistent") is None

    def test_resolve_spell_no_registry(self):
        resolver = SpellResolver(caster_level=1, key_ability_mod=3)
        assert resolver.resolve_spell("Magic Missile") is None

    def test_slots_true_attribute(self):
        """Verify SpellResolver uses __slots__."""
        assert hasattr(SpellResolver, "__slots__")


# ---------------------------------------------------------------------------
# Bonus spells helper tests
# ---------------------------------------------------------------------------

class TestBonusSpells:
    def test_no_bonus_for_cantrips(self):
        assert _bonus_spells_for_level(5, 0) == 0

    def test_no_bonus_if_mod_less_than_level(self):
        # Mod 2 cannot grant bonus for level 3+
        assert _bonus_spells_for_level(2, 3) == 0

    def test_mod_equals_level(self):
        # Mod 1, level 1: 1 + (1-1)//4 = 1
        assert _bonus_spells_for_level(1, 1) == 1

    def test_high_mod_multiple_bonus(self):
        # Mod 5, level 1: 1 + (5-1)//4 = 1 + 1 = 2
        assert _bonus_spells_for_level(5, 1) == 2


# ---------------------------------------------------------------------------
# Character35e spellcasting integration tests
# ---------------------------------------------------------------------------

class TestCharacter35eSpellcasting:
    def test_wizard_is_caster(self):
        wizard = Character35e(name="Gandalf", char_class="Wizard", level=1)
        assert wizard.is_caster is True

    def test_fighter_is_not_caster(self):
        fighter = Character35e(name="Conan", char_class="Fighter", level=5)
        assert fighter.is_caster is False

    def test_wizard_caster_level(self):
        wizard = Character35e(name="Gandalf", char_class="Wizard", level=5)
        assert wizard.caster_level == 5

    def test_fighter_caster_level_is_zero(self):
        fighter = Character35e(name="Conan", char_class="Fighter", level=5)
        assert fighter.caster_level == 0

    def test_initialize_spellcasting_wizard(self):
        wizard = Character35e(
            name="Elminster",
            char_class="Wizard",
            level=1,
            intelligence=16,  # +3 mod
        )
        wizard.initialize_spellcasting()

        assert wizard.spell_slot_manager is not None
        assert wizard.spellbook is not None
        # Base: 3 cantrips, 1+1(bonus from INT 16)=2 first-level
        assert wizard.spell_slot_manager.max_slots[0] == 3
        assert wizard.spell_slot_manager.max_slots[1] == 2

    def test_initialize_spellcasting_fighter_does_nothing(self):
        fighter = Character35e(name="Conan", char_class="Fighter", level=5)
        fighter.initialize_spellcasting()
        assert fighter.spell_slot_manager is None
        assert fighter.spellbook is None

    def test_wizard_level_1_base_slots_verification(self):
        """VERIFICATION: A Level 1 Wizard correctly has three 0-level
        and one 1st-level spell slots (base allocation per SRD table).
        """
        wizard = Character35e(
            name="TestWizard",
            char_class="Wizard",
            level=1,
            intelligence=10,  # +0 mod, no bonus spells
        )
        wizard.initialize_spellcasting()

        assert wizard.spell_slot_manager is not None
        assert wizard.spell_slot_manager.max_slots[0] == 3, (
            "Level 1 Wizard must have 3 zero-level slots"
        )
        assert wizard.spell_slot_manager.max_slots[1] == 1, (
            "Level 1 Wizard must have 1 first-level slot"
        )

    def test_sorcerer_initialize_spellcasting(self):
        sorc = Character35e(
            name="Hennet",
            char_class="Sorcerer",
            level=1,
            charisma=16,  # +3 mod
        )
        sorc.initialize_spellcasting()

        assert sorc.spell_slot_manager is not None
        assert sorc.spells_known is not None
        assert sorc.spontaneous_caster is not None
        assert sorc.spell_slot_manager.max_slots[0] == 5  # Sorcerer cantrips
        assert sorc.spell_slot_manager.max_slots[1] == 4  # 3 + 1 bonus


# ---------------------------------------------------------------------------
# Key ability helper tests
# ---------------------------------------------------------------------------

class TestKeyAbility:
    def test_wizard_key_ability_is_intelligence(self):
        assert get_key_ability("Wizard") == "intelligence"

    def test_sorcerer_key_ability_is_charisma(self):
        assert get_key_ability("Sorcerer") == "charisma"

    def test_cleric_key_ability_is_wisdom(self):
        assert get_key_ability("Cleric") == "wisdom"

    def test_invalid_class_raises(self):
        with pytest.raises(ValueError):
            get_key_ability("Fighter")

    def test_is_caster_class(self):
        assert is_caster_class("Wizard") is True
        assert is_caster_class("Sorcerer") is True
        assert is_caster_class("Cleric") is True
        assert is_caster_class("Druid") is True
        assert is_caster_class("Fighter") is False
        assert is_caster_class("Rogue") is False


# ---------------------------------------------------------------------------
# Phase 1 – Wizard/Sorcerer Arcane Spells (Levels 0–3)
# ---------------------------------------------------------------------------

class TestPhase1WizardSorcererSpells:

    # ------------------------------------------------------------------ #
    #  Registry membership                                                 #
    # ------------------------------------------------------------------ #

    def test_all_32_new_spells_in_registry(self):
        registry = create_default_registry()
        new_spells = [
            "Detect Magic", "Ray of Frost", "Resistance", "Mage Hand",
            "Read Magic", "Acid Splash", "Daze", "Light",
            "Charm Person", "Color Spray", "Feather Fall", "Grease",
            "Ray of Enfeeblement", "True Strike", "Cause Fear", "Enlarge Person",
            "Scorching Ray", "Invisibility", "Mirror Image", "Web",
            "Bull's Strength", "Blur", "Resist Energy", "Bear's Endurance",
            "Fireball", "Lightning Bolt", "Dispel Magic", "Haste",
            "Hold Person", "Fly", "Slow", "Vampiric Touch",
        ]
        for name in new_spells:
            assert name in registry, f"'{name}' missing from default registry"

    def test_level_0_spells_queryable_by_level(self):
        registry = create_default_registry()
        level_0_names = [s.name for s in registry.get_by_level(0)]
        for name in ("Ghost Sound", "Detect Magic", "Ray of Frost", "Resistance",
                     "Mage Hand", "Read Magic", "Acid Splash", "Daze", "Light"):
            assert name in level_0_names

    def test_level_3_spells_queryable_by_school(self):
        registry = create_default_registry()
        evocations = [s.name for s in registry.get_by_school(SpellSchool.EVOCATION)]
        assert "Fireball" in evocations
        assert "Lightning Bolt" in evocations

        transmutations = [s.name for s in registry.get_by_school(SpellSchool.TRANSMUTATION)]
        assert "Haste" in transmutations
        assert "Fly" in transmutations
        assert "Slow" in transmutations

    # ------------------------------------------------------------------ #
    #  Level 0 – attributes                                                #
    # ------------------------------------------------------------------ #

    def test_detect_magic_attributes(self):
        assert DETECT_MAGIC.level == 0
        assert DETECT_MAGIC.school == SpellSchool.DIVINATION
        assert SpellComponent.VERBAL in DETECT_MAGIC.components
        assert SpellComponent.SOMATIC in DETECT_MAGIC.components

    def test_ray_of_frost_attributes(self):
        assert RAY_OF_FROST.level == 0
        assert RAY_OF_FROST.school == SpellSchool.EVOCATION
        assert "Cold" in RAY_OF_FROST.descriptor

    def test_resistance_attributes(self):
        assert RESISTANCE.level == 0
        assert RESISTANCE.school == SpellSchool.ABJURATION
        assert SpellComponent.MATERIAL in RESISTANCE.components

    def test_mage_hand_attributes(self):
        assert MAGE_HAND.level == 0
        assert MAGE_HAND.school == SpellSchool.TRANSMUTATION

    def test_read_magic_attributes(self):
        assert READ_MAGIC.level == 0
        assert READ_MAGIC.school == SpellSchool.DIVINATION
        assert SpellComponent.FOCUS in READ_MAGIC.components

    def test_acid_splash_attributes(self):
        assert ACID_SPLASH.level == 0
        assert ACID_SPLASH.school == SpellSchool.CONJURATION
        assert ACID_SPLASH.subschool == "Creation"
        assert "Acid" in ACID_SPLASH.descriptor

    def test_daze_attributes(self):
        assert DAZE.level == 0
        assert DAZE.school == SpellSchool.ENCHANTMENT
        assert DAZE.subschool == "Compulsion"
        assert "Mind-Affecting" in DAZE.descriptor

    def test_light_attributes(self):
        assert LIGHT.level == 0
        assert LIGHT.school == SpellSchool.EVOCATION

    # ------------------------------------------------------------------ #
    #  Level 0 – effect callbacks                                          #
    # ------------------------------------------------------------------ #

    def test_detect_magic_effect(self):
        result = DETECT_MAGIC.effect_callback(None, None, 3)
        assert result["detects"] == "spell auras"
        assert "3 min." in result["duration"]

    def test_ray_of_frost_effect(self):
        result = RAY_OF_FROST.effect_callback(None, None, 1)
        assert result["damage"] == "1d3"
        assert result["damage_type"] == "Cold"
        assert result["attack"] == "ranged touch"

    def test_resistance_effect(self):
        result = RESISTANCE.effect_callback(None, None, 1)
        assert result["save_bonus"] == 1
        assert result["bonus_type"] == "resistance"
        assert result["duration_minutes"] == 1

    def test_mage_hand_effect(self):
        result = MAGE_HAND.effect_callback(None, None, 1)
        assert result["max_weight_lb"] == 5

    def test_read_magic_effect_scales(self):
        result = READ_MAGIC.effect_callback(None, None, 5)
        assert result["deciphers_magical_writing"] is True
        assert result["duration_minutes"] == 50

    def test_acid_splash_effect(self):
        result = ACID_SPLASH.effect_callback(None, None, 1)
        assert result["damage"] == "1d3"
        assert result["damage_type"] == "Acid"
        assert result["attack"] == "ranged touch"

    def test_daze_effect(self):
        result = DAZE.effect_callback(None, None, 1)
        assert result["condition"] == "dazed"
        assert result["max_hd"] == 4
        assert result["save"] == "Will negates"

    def test_light_effect_scales(self):
        result = LIGHT.effect_callback(None, None, 4)
        assert result["bright_light_radius_ft"] == 20
        assert result["duration_minutes"] == 40

    # ------------------------------------------------------------------ #
    #  Level 1 – attributes                                                #
    # ------------------------------------------------------------------ #

    def test_charm_person_attributes(self):
        assert CHARM_PERSON.level == 1
        assert CHARM_PERSON.school == SpellSchool.ENCHANTMENT
        assert "Mind-Affecting" in CHARM_PERSON.descriptor

    def test_color_spray_attributes(self):
        assert COLOR_SPRAY.level == 1
        assert COLOR_SPRAY.school == SpellSchool.ILLUSION
        assert COLOR_SPRAY.subschool == "Pattern"

    def test_feather_fall_attributes(self):
        assert FEATHER_FALL.level == 1
        assert FEATHER_FALL.school == SpellSchool.TRANSMUTATION
        assert FEATHER_FALL.components == [SpellComponent.VERBAL]

    def test_grease_attributes(self):
        assert GREASE.level == 1
        assert GREASE.school == SpellSchool.CONJURATION
        assert GREASE.subschool == "Creation"

    def test_ray_of_enfeeblement_attributes(self):
        assert RAY_OF_ENFEEBLEMENT.level == 1
        assert RAY_OF_ENFEEBLEMENT.school == SpellSchool.NECROMANCY

    def test_true_strike_attributes(self):
        assert TRUE_STRIKE.level == 1
        assert TRUE_STRIKE.school == SpellSchool.DIVINATION
        assert SpellComponent.FOCUS in TRUE_STRIKE.components

    def test_cause_fear_attributes(self):
        assert CAUSE_FEAR.level == 1
        assert CAUSE_FEAR.school == SpellSchool.NECROMANCY
        assert "Fear" in CAUSE_FEAR.descriptor
        assert "Mind-Affecting" in CAUSE_FEAR.descriptor

    def test_enlarge_person_attributes(self):
        assert ENLARGE_PERSON.level == 1
        assert ENLARGE_PERSON.school == SpellSchool.TRANSMUTATION

    # ------------------------------------------------------------------ #
    #  Level 1 – effect callbacks                                          #
    # ------------------------------------------------------------------ #

    def test_charm_person_effect(self):
        result = CHARM_PERSON.effect_callback(None, None, 3)
        assert result["condition"] == "charmed"
        assert result["duration_hours"] == 3
        assert result["save"] == "Will negates"

    def test_color_spray_effect(self):
        result = COLOR_SPRAY.effect_callback(None, None, 1)
        assert "2_hd_or_less" in result["effects"]
        assert result["save"] == "Will negates"

    def test_feather_fall_effect(self):
        result = FEATHER_FALL.effect_callback(None, None, 4)
        assert result["fall_rate_ft_per_round"] == 60
        assert result["damage_on_landing"] == 0
        assert result["duration_rounds"] == 4

    def test_grease_effect_scales(self):
        result = GREASE.effect_callback(None, None, 5)
        assert result["duration_rounds"] == 5

    def test_ray_of_enfeeblement_effect_cl1(self):
        result = RAY_OF_ENFEEBLEMENT.effect_callback(None, None, 1)
        assert result["str_penalty"] == "1d6+0"
        assert result["attack"] == "ranged touch"

    def test_ray_of_enfeeblement_effect_max_bonus(self):
        # CL 10 -> min(10//2, 5) = 5
        result = RAY_OF_ENFEEBLEMENT.effect_callback(None, None, 10)
        assert result["str_penalty"] == "1d6+5"
        # CL 20 should still cap at +5
        result2 = RAY_OF_ENFEEBLEMENT.effect_callback(None, None, 20)
        assert result2["str_penalty"] == "1d6+5"

    def test_true_strike_effect(self):
        result = TRUE_STRIKE.effect_callback(None, None, 1)
        assert result["attack_bonus"] == 20
        assert result["bonus_type"] == "insight"

    def test_cause_fear_effect(self):
        result = CAUSE_FEAR.effect_callback(None, None, 1)
        assert result["condition"] == "frightened"
        assert result["max_hd"] == 5
        assert result["save"] == "Will negates"

    def test_enlarge_person_effect(self):
        result = ENLARGE_PERSON.effect_callback(None, None, 3)
        assert result["str_bonus"] == 2
        assert result["dex_penalty"] == -2
        assert result["duration_minutes"] == 3

    # ------------------------------------------------------------------ #
    #  Level 2 – attributes                                                #
    # ------------------------------------------------------------------ #

    def test_scorching_ray_attributes(self):
        assert SCORCHING_RAY.level == 2
        assert SCORCHING_RAY.school == SpellSchool.EVOCATION
        assert "Fire" in SCORCHING_RAY.descriptor

    def test_invisibility_attributes(self):
        assert INVISIBILITY.level == 2
        assert INVISIBILITY.school == SpellSchool.ILLUSION
        assert INVISIBILITY.subschool == "Glamer"

    def test_mirror_image_attributes(self):
        assert MIRROR_IMAGE.level == 2
        assert MIRROR_IMAGE.school == SpellSchool.ILLUSION
        assert MIRROR_IMAGE.subschool == "Figment"

    def test_web_attributes(self):
        assert WEB.level == 2
        assert WEB.school == SpellSchool.CONJURATION
        assert WEB.subschool == "Creation"

    def test_bulls_strength_attributes(self):
        assert BULLS_STRENGTH.level == 2
        assert BULLS_STRENGTH.school == SpellSchool.TRANSMUTATION

    def test_blur_attributes(self):
        assert BLUR.level == 2
        assert BLUR.school == SpellSchool.ILLUSION
        assert BLUR.subschool == "Glamer"

    def test_resist_energy_attributes(self):
        assert RESIST_ENERGY.level == 2
        assert RESIST_ENERGY.school == SpellSchool.ABJURATION

    def test_bears_endurance_attributes(self):
        assert BEARS_ENDURANCE.level == 2
        assert BEARS_ENDURANCE.school == SpellSchool.TRANSMUTATION

    # ------------------------------------------------------------------ #
    #  Level 2 – effect callbacks                                          #
    # ------------------------------------------------------------------ #

    def test_scorching_ray_effect_cl5(self):
        # CL 5: rays = min(3, 1 + 5//4) = min(3, 2) = 2
        result = SCORCHING_RAY.effect_callback(None, None, 5)
        assert result["rays"] == 2
        assert result["damage_per_ray"] == "4d6"
        assert result["damage_type"] == "Fire"

    def test_scorching_ray_effect_max_rays(self):
        # CL 11+: rays = min(3, 1 + 11//4) = min(3, 3) = 3
        result = SCORCHING_RAY.effect_callback(None, None, 11)
        assert result["rays"] == 3
        # Even higher CL still capped at 3
        result2 = SCORCHING_RAY.effect_callback(None, None, 20)
        assert result2["rays"] == 3

    def test_scorching_ray_effect_cl1(self):
        result = SCORCHING_RAY.effect_callback(None, None, 1)
        assert result["rays"] == 1

    def test_invisibility_effect(self):
        result = INVISIBILITY.effect_callback(None, None, 5)
        assert result["condition"] == "invisible"
        assert result["duration_minutes"] == 5
        assert result["ends_on_attack_or_cast"] is True

    def test_mirror_image_effect_cl3(self):
        # CL 3: max_images = min(1 + 3//3, 8) = min(2, 8) = 2
        result = MIRROR_IMAGE.effect_callback(None, None, 3)
        assert result["images"] == "1d4+1"
        assert result["max_images"] == 2
        assert result["duration_minutes"] == 3

    def test_mirror_image_effect_max(self):
        # CL 21+: would exceed 8, capped at 8
        result = MIRROR_IMAGE.effect_callback(None, None, 21)
        assert result["max_images"] == 8

    def test_web_effect_scales(self):
        result = WEB.effect_callback(None, None, 5)
        assert result["str_check_dc"] == 20
        assert result["duration_minutes"] == 50

    def test_bulls_strength_effect(self):
        result = BULLS_STRENGTH.effect_callback(None, None, 4)
        assert result["str_bonus"] == 4
        assert result["bonus_type"] == "enhancement"
        assert result["duration_minutes"] == 4

    def test_blur_effect(self):
        result = BLUR.effect_callback(None, None, 3)
        assert result["miss_chance_percent"] == 20
        assert result["duration_minutes"] == 3

    def test_resist_energy_effect(self):
        result = RESIST_ENERGY.effect_callback(None, None, 3)
        assert result["absorption"] == 10
        assert "fire" in result["energy_types"]
        assert "cold" in result["energy_types"]
        assert "acid" in result["energy_types"]
        assert "electricity" in result["energy_types"]
        assert "sonic" in result["energy_types"]
        assert result["duration_minutes"] == 30

    def test_bears_endurance_effect(self):
        result = BEARS_ENDURANCE.effect_callback(None, None, 5)
        assert result["con_bonus"] == 4
        assert result["bonus_type"] == "enhancement"
        assert result["duration_minutes"] == 5

    # ------------------------------------------------------------------ #
    #  Level 3 – attributes                                                #
    # ------------------------------------------------------------------ #

    def test_fireball_attributes(self):
        assert FIREBALL.level == 3
        assert FIREBALL.school == SpellSchool.EVOCATION
        assert "Fire" in FIREBALL.descriptor

    def test_lightning_bolt_attributes(self):
        assert LIGHTNING_BOLT.level == 3
        assert LIGHTNING_BOLT.school == SpellSchool.EVOCATION
        assert "Electricity" in LIGHTNING_BOLT.descriptor

    def test_dispel_magic_attributes(self):
        assert DISPEL_MAGIC.level == 3
        assert DISPEL_MAGIC.school == SpellSchool.ABJURATION

    def test_haste_attributes(self):
        assert HASTE.level == 3
        assert HASTE.school == SpellSchool.TRANSMUTATION

    def test_hold_person_attributes(self):
        assert HOLD_PERSON.level == 3
        assert HOLD_PERSON.school == SpellSchool.ENCHANTMENT
        assert "Mind-Affecting" in HOLD_PERSON.descriptor

    def test_fly_attributes(self):
        assert FLY.level == 3
        assert FLY.school == SpellSchool.TRANSMUTATION
        assert SpellComponent.FOCUS in FLY.components

    def test_slow_attributes(self):
        assert SLOW.level == 3
        assert SLOW.school == SpellSchool.TRANSMUTATION

    def test_vampiric_touch_attributes(self):
        assert VAMPIRIC_TOUCH.level == 3
        assert VAMPIRIC_TOUCH.school == SpellSchool.NECROMANCY

    # ------------------------------------------------------------------ #
    #  Level 3 – effect callbacks                                          #
    # ------------------------------------------------------------------ #

    def test_fireball_effect_cl5(self):
        result = FIREBALL.effect_callback(None, None, 5)
        assert result["damage"] == "5d6"
        assert result["damage_type"] == "Fire"
        assert result["area"] == "20-ft radius burst"
        assert result["save"] == "Reflex half"

    def test_fireball_effect_max_dice(self):
        # CL 10+ capped at 10d6
        result = FIREBALL.effect_callback(None, None, 10)
        assert result["damage"] == "10d6"
        result2 = FIREBALL.effect_callback(None, None, 15)
        assert result2["damage"] == "10d6"

    def test_lightning_bolt_effect_cl5(self):
        result = LIGHTNING_BOLT.effect_callback(None, None, 5)
        assert result["damage"] == "5d6"
        assert result["damage_type"] == "Electricity"
        assert result["area"] == "5-ft wide, 120-ft line"

    def test_lightning_bolt_effect_max_dice(self):
        result = LIGHTNING_BOLT.effect_callback(None, None, 10)
        assert result["damage"] == "10d6"

    def test_dispel_magic_effect_cl5(self):
        result = DISPEL_MAGIC.effect_callback(None, None, 5)
        assert result["max_caster_level_check"] == 15
        assert result["targeted"] is True

    def test_dispel_magic_effect_max_check(self):
        # CL 10 -> max bonus capped: 10 + min(10, 10) = 20
        result = DISPEL_MAGIC.effect_callback(None, None, 10)
        assert result["max_caster_level_check"] == 20
        # CL 20 still capped at 20
        result2 = DISPEL_MAGIC.effect_callback(None, None, 20)
        assert result2["max_caster_level_check"] == 20

    def test_haste_effect(self):
        result = HASTE.effect_callback(None, None, 5)
        assert result["extra_attack"] is True
        assert result["speed_bonus_ft"] == 30
        assert result["dodge_ac_bonus"] == 1
        assert result["reflex_bonus"] == 1
        assert result["duration_rounds"] == 5

    def test_hold_person_effect(self):
        result = HOLD_PERSON.effect_callback(None, None, 4)
        assert result["condition"] == "paralyzed"
        assert result["target"] == "humanoid"
        assert result["duration_rounds"] == 4
        assert result["save"] == "Will negates"

    def test_fly_effect(self):
        result = FLY.effect_callback(None, None, 6)
        assert result["fly_speed_ft"] == 60
        assert result["fly_speed_encumbered_ft"] == 40
        assert result["duration_minutes"] == 6

    def test_slow_effect(self):
        result = SLOW.effect_callback(None, None, 5)
        assert result["attack_penalty"] == -1
        assert result["ac_penalty"] == -1
        assert result["reflex_penalty"] == -1
        assert result["speed_multiplier"] == 0.5
        assert result["save"] == "Will negates"
        assert result["duration_rounds"] == 5

    def test_vampiric_touch_effect_cl6(self):
        # CL 6: dice = min(6//2, 10) = 3
        result = VAMPIRIC_TOUCH.effect_callback(None, None, 6)
        assert result["damage"] == "3d6"
        assert result["heals_caster"] is True
        assert result["temp_hp_duration_hours"] == 1

    def test_vampiric_touch_effect_max_dice(self):
        # CL 20: min(20//2, 10) = 10
        result = VAMPIRIC_TOUCH.effect_callback(None, None, 20)
        assert result["damage"] == "10d6"
        # CL 22: still capped at 10d6
        result2 = VAMPIRIC_TOUCH.effect_callback(None, None, 22)
        assert result2["damage"] == "10d6"
