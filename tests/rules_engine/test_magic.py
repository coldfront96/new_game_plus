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
    # Phase 2 – Level 4
    DIMENSION_DOOR,
    POLYMORPH,
    GREATER_INVISIBILITY,
    ICE_STORM,
    STONESKIN,
    CONFUSION,
    ARCANE_EYE,
    BLACK_TENTACLES,
    # Phase 2 – Level 5
    CONE_OF_COLD,
    TELEKINESIS,
    WALL_OF_FORCE,
    CLOUDKILL,
    DOMINATE_PERSON,
    FEEBLEMIND,
    PERMANENCY,
    SENDING,
    # Phase 2 – Level 6
    DISINTEGRATE,
    CHAIN_LIGHTNING,
    GLOBE_OF_INVULNERABILITY,
    TRUE_SEEING,
    CONTINGENCY,
    LEGEND_LORE,
    REPULSION,
    MISLEAD,
    # Phase 2 – Level 7
    FINGER_OF_DEATH,
    POWER_WORD_BLIND,
    SPELL_TURNING,
    LIMITED_WISH,
    PRISMATIC_SPRAY,
    REVERSE_GRAVITY,
    ETHEREAL_JAUNT,
    MORDENKAINENS_SWORD,
    # Phase 2 – Level 8
    POWER_WORD_STUN,
    MIND_BLANK,
    PRISMATIC_WALL,
    MAZE,
    CLONE,
    GREATER_PRYING_EYES,
    SUNBURST,
    POLAR_RAY,
    # Phase 2 – Level 9
    WISH,
    TIME_STOP,
    METEOR_SWARM,
    WAIL_OF_THE_BANSHEE,
    POWER_WORD_KILL,
    SHAPECHANGE,
    GATE,
    FORESIGHT,
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
        assert registry.count == 91
        assert len(registry) == 91

    def test_contains(self):
        registry = create_default_registry()
        assert "Magic Missile" in registry
        assert "Bigby's Hand" not in registry


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


# ---------------------------------------------------------------------------
# Phase 2 – Wizard/Sorcerer Arcane Spells (Levels 4–9)
# ---------------------------------------------------------------------------

class TestPhase2WizardSorcererSpells:

    # ------------------------------------------------------------------ #
    #  Registry membership – all 48 new spells                             #
    # ------------------------------------------------------------------ #

    def test_all_48_new_spells_in_registry(self):
        registry = create_default_registry()
        new_spells = [
            # Level 4
            "Dimension Door", "Polymorph", "Greater Invisibility", "Ice Storm",
            "Stoneskin", "Confusion", "Arcane Eye", "Black Tentacles",
            # Level 5
            "Cone of Cold", "Telekinesis", "Wall of Force", "Cloudkill",
            "Dominate Person", "Feeblemind", "Permanency", "Sending",
            # Level 6
            "Disintegrate", "Chain Lightning", "Globe of Invulnerability",
            "True Seeing", "Contingency", "Legend Lore", "Repulsion", "Mislead",
            # Level 7
            "Finger of Death", "Power Word Blind", "Spell Turning", "Limited Wish",
            "Prismatic Spray", "Reverse Gravity", "Ethereal Jaunt",
            "Mordenkainen's Sword",
            # Level 8
            "Power Word Stun", "Mind Blank", "Prismatic Wall", "Maze", "Clone",
            "Greater Prying Eyes", "Sunburst", "Polar Ray",
            # Level 9
            "Wish", "Time Stop", "Meteor Swarm", "Wail of the Banshee",
            "Power Word Kill", "Shapechange", "Gate", "Foresight",
        ]
        for name in new_spells:
            assert name in registry, f"'{name}' missing from default registry"

    # ------------------------------------------------------------------ #
    #  Level grouping tests                                                #
    # ------------------------------------------------------------------ #

    def test_level_4_spells_in_registry(self):
        registry = create_default_registry()
        names = [s.name for s in registry.get_by_level(4)]
        for name in ("Dimension Door", "Polymorph", "Greater Invisibility",
                     "Ice Storm", "Stoneskin", "Confusion", "Arcane Eye",
                     "Black Tentacles"):
            assert name in names

    def test_level_5_spells_in_registry(self):
        registry = create_default_registry()
        names = [s.name for s in registry.get_by_level(5)]
        for name in ("Cone of Cold", "Telekinesis", "Wall of Force", "Cloudkill",
                     "Dominate Person", "Feeblemind", "Permanency", "Sending"):
            assert name in names

    def test_level_6_spells_in_registry(self):
        registry = create_default_registry()
        names = [s.name for s in registry.get_by_level(6)]
        for name in ("Disintegrate", "Chain Lightning", "Globe of Invulnerability",
                     "True Seeing", "Contingency", "Legend Lore", "Repulsion",
                     "Mislead"):
            assert name in names

    def test_level_7_spells_in_registry(self):
        registry = create_default_registry()
        names = [s.name for s in registry.get_by_level(7)]
        for name in ("Finger of Death", "Power Word Blind", "Spell Turning",
                     "Limited Wish", "Prismatic Spray", "Reverse Gravity",
                     "Ethereal Jaunt", "Mordenkainen's Sword"):
            assert name in names

    def test_level_8_spells_in_registry(self):
        registry = create_default_registry()
        names = [s.name for s in registry.get_by_level(8)]
        for name in ("Power Word Stun", "Mind Blank", "Prismatic Wall", "Maze",
                     "Clone", "Greater Prying Eyes", "Sunburst", "Polar Ray"):
            assert name in names

    def test_level_9_spells_in_registry(self):
        registry = create_default_registry()
        names = [s.name for s in registry.get_by_level(9)]
        for name in ("Wish", "Time Stop", "Meteor Swarm", "Wail of the Banshee",
                     "Power Word Kill", "Shapechange", "Gate", "Foresight"):
            assert name in names

    # ------------------------------------------------------------------ #
    #  Attribute tests – Level 4                                           #
    # ------------------------------------------------------------------ #

    def test_dimension_door_attributes(self):
        assert DIMENSION_DOOR.level == 4
        assert DIMENSION_DOOR.school == SpellSchool.CONJURATION
        assert DIMENSION_DOOR.subschool == "Teleportation"
        assert SpellComponent.VERBAL in DIMENSION_DOOR.components

    def test_polymorph_attributes(self):
        assert POLYMORPH.level == 4
        assert POLYMORPH.school == SpellSchool.TRANSMUTATION

    def test_greater_invisibility_attributes(self):
        assert GREATER_INVISIBILITY.level == 4
        assert GREATER_INVISIBILITY.school == SpellSchool.ILLUSION
        assert GREATER_INVISIBILITY.subschool == "Glamer"

    def test_ice_storm_attributes(self):
        assert ICE_STORM.level == 4
        assert ICE_STORM.school == SpellSchool.EVOCATION
        assert "Cold" in ICE_STORM.descriptor

    def test_stoneskin_attributes(self):
        assert STONESKIN.level == 4
        assert STONESKIN.school == SpellSchool.ABJURATION

    def test_confusion_attributes(self):
        assert CONFUSION.level == 4
        assert CONFUSION.school == SpellSchool.ENCHANTMENT
        assert CONFUSION.subschool == "Compulsion"
        assert "Mind-Affecting" in CONFUSION.descriptor

    def test_arcane_eye_attributes(self):
        assert ARCANE_EYE.level == 4
        assert ARCANE_EYE.school == SpellSchool.DIVINATION
        assert ARCANE_EYE.subschool == "Scrying"

    def test_black_tentacles_attributes(self):
        assert BLACK_TENTACLES.level == 4
        assert BLACK_TENTACLES.school == SpellSchool.CONJURATION
        assert BLACK_TENTACLES.subschool == "Creation"

    # ------------------------------------------------------------------ #
    #  Attribute tests – Level 5                                           #
    # ------------------------------------------------------------------ #

    def test_cone_of_cold_attributes(self):
        assert CONE_OF_COLD.level == 5
        assert CONE_OF_COLD.school == SpellSchool.EVOCATION
        assert "Cold" in CONE_OF_COLD.descriptor

    def test_telekinesis_attributes(self):
        assert TELEKINESIS.level == 5
        assert TELEKINESIS.school == SpellSchool.TRANSMUTATION

    def test_wall_of_force_attributes(self):
        assert WALL_OF_FORCE.level == 5
        assert WALL_OF_FORCE.school == SpellSchool.EVOCATION
        assert "Force" in WALL_OF_FORCE.descriptor

    def test_cloudkill_attributes(self):
        assert CLOUDKILL.level == 5
        assert CLOUDKILL.school == SpellSchool.CONJURATION
        assert CLOUDKILL.subschool == "Creation"

    def test_dominate_person_attributes(self):
        assert DOMINATE_PERSON.level == 5
        assert DOMINATE_PERSON.school == SpellSchool.ENCHANTMENT
        assert "Mind-Affecting" in DOMINATE_PERSON.descriptor

    def test_feeblemind_attributes(self):
        assert FEEBLEMIND.level == 5
        assert FEEBLEMIND.school == SpellSchool.ENCHANTMENT
        assert "Mind-Affecting" in FEEBLEMIND.descriptor

    def test_permanency_attributes(self):
        assert PERMANENCY.level == 5
        assert PERMANENCY.school == SpellSchool.UNIVERSAL
        assert SpellComponent.XP in PERMANENCY.components

    def test_sending_attributes(self):
        assert SENDING.level == 5
        assert SENDING.school == SpellSchool.EVOCATION

    # ------------------------------------------------------------------ #
    #  Attribute tests – Level 6                                           #
    # ------------------------------------------------------------------ #

    def test_disintegrate_attributes(self):
        assert DISINTEGRATE.level == 6
        assert DISINTEGRATE.school == SpellSchool.TRANSMUTATION

    def test_chain_lightning_attributes(self):
        assert CHAIN_LIGHTNING.level == 6
        assert CHAIN_LIGHTNING.school == SpellSchool.EVOCATION
        assert "Electricity" in CHAIN_LIGHTNING.descriptor

    def test_globe_of_invulnerability_attributes(self):
        assert GLOBE_OF_INVULNERABILITY.level == 6
        assert GLOBE_OF_INVULNERABILITY.school == SpellSchool.ABJURATION

    def test_true_seeing_attributes(self):
        assert TRUE_SEEING.level == 6
        assert TRUE_SEEING.school == SpellSchool.DIVINATION

    def test_contingency_attributes(self):
        assert CONTINGENCY.level == 6
        assert CONTINGENCY.school == SpellSchool.EVOCATION

    def test_legend_lore_attributes(self):
        assert LEGEND_LORE.level == 6
        assert LEGEND_LORE.school == SpellSchool.DIVINATION

    def test_repulsion_attributes(self):
        assert REPULSION.level == 6
        assert REPULSION.school == SpellSchool.ABJURATION

    def test_mislead_attributes(self):
        assert MISLEAD.level == 6
        assert MISLEAD.school == SpellSchool.ILLUSION

    # ------------------------------------------------------------------ #
    #  Attribute tests – Level 7                                           #
    # ------------------------------------------------------------------ #

    def test_finger_of_death_attributes(self):
        assert FINGER_OF_DEATH.level == 7
        assert FINGER_OF_DEATH.school == SpellSchool.NECROMANCY
        assert "Death" in FINGER_OF_DEATH.descriptor

    def test_power_word_blind_attributes(self):
        assert POWER_WORD_BLIND.level == 7
        assert POWER_WORD_BLIND.school == SpellSchool.ENCHANTMENT
        assert "Mind-Affecting" in POWER_WORD_BLIND.descriptor

    def test_spell_turning_attributes(self):
        assert SPELL_TURNING.level == 7
        assert SPELL_TURNING.school == SpellSchool.ABJURATION

    def test_limited_wish_attributes(self):
        assert LIMITED_WISH.level == 7
        assert LIMITED_WISH.school == SpellSchool.UNIVERSAL
        assert SpellComponent.XP in LIMITED_WISH.components

    def test_prismatic_spray_attributes(self):
        assert PRISMATIC_SPRAY.level == 7
        assert PRISMATIC_SPRAY.school == SpellSchool.EVOCATION

    def test_reverse_gravity_attributes(self):
        assert REVERSE_GRAVITY.level == 7
        assert REVERSE_GRAVITY.school == SpellSchool.TRANSMUTATION

    def test_ethereal_jaunt_attributes(self):
        assert ETHEREAL_JAUNT.level == 7
        assert ETHEREAL_JAUNT.school == SpellSchool.TRANSMUTATION

    def test_mordenkainens_sword_attributes(self):
        assert MORDENKAINENS_SWORD.level == 7
        assert MORDENKAINENS_SWORD.school == SpellSchool.EVOCATION
        assert "Force" in MORDENKAINENS_SWORD.descriptor

    # ------------------------------------------------------------------ #
    #  Attribute tests – Level 8                                           #
    # ------------------------------------------------------------------ #

    def test_power_word_stun_attributes(self):
        assert POWER_WORD_STUN.level == 8
        assert POWER_WORD_STUN.school == SpellSchool.ENCHANTMENT
        assert "Mind-Affecting" in POWER_WORD_STUN.descriptor

    def test_mind_blank_attributes(self):
        assert MIND_BLANK.level == 8
        assert MIND_BLANK.school == SpellSchool.ABJURATION

    def test_prismatic_wall_attributes(self):
        assert PRISMATIC_WALL.level == 8
        assert PRISMATIC_WALL.school == SpellSchool.ABJURATION

    def test_maze_attributes(self):
        assert MAZE.level == 8
        assert MAZE.school == SpellSchool.CONJURATION
        assert MAZE.subschool == "Teleportation"

    def test_clone_attributes(self):
        assert CLONE.level == 8
        assert CLONE.school == SpellSchool.NECROMANCY

    def test_greater_prying_eyes_attributes(self):
        assert GREATER_PRYING_EYES.level == 8
        assert GREATER_PRYING_EYES.school == SpellSchool.DIVINATION
        assert GREATER_PRYING_EYES.subschool == "Scrying"

    def test_sunburst_attributes(self):
        assert SUNBURST.level == 8
        assert SUNBURST.school == SpellSchool.EVOCATION
        assert "Light" in SUNBURST.descriptor

    def test_polar_ray_attributes(self):
        assert POLAR_RAY.level == 8
        assert POLAR_RAY.school == SpellSchool.EVOCATION
        assert "Cold" in POLAR_RAY.descriptor

    # ------------------------------------------------------------------ #
    #  Attribute tests – Level 9                                           #
    # ------------------------------------------------------------------ #

    def test_wish_attributes(self):
        assert WISH.level == 9
        assert WISH.school == SpellSchool.UNIVERSAL
        assert SpellComponent.XP in WISH.components

    def test_time_stop_attributes(self):
        assert TIME_STOP.level == 9
        assert TIME_STOP.school == SpellSchool.TRANSMUTATION
        assert TIME_STOP.components == [SpellComponent.VERBAL]

    def test_meteor_swarm_attributes(self):
        assert METEOR_SWARM.level == 9
        assert METEOR_SWARM.school == SpellSchool.EVOCATION
        assert "Fire" in METEOR_SWARM.descriptor

    def test_wail_of_the_banshee_attributes(self):
        assert WAIL_OF_THE_BANSHEE.level == 9
        assert WAIL_OF_THE_BANSHEE.school == SpellSchool.NECROMANCY
        assert "Death" in WAIL_OF_THE_BANSHEE.descriptor
        assert "Sonic" in WAIL_OF_THE_BANSHEE.descriptor

    def test_power_word_kill_attributes(self):
        assert POWER_WORD_KILL.level == 9
        assert POWER_WORD_KILL.school == SpellSchool.ENCHANTMENT
        assert "Death" in POWER_WORD_KILL.descriptor

    def test_shapechange_attributes(self):
        assert SHAPECHANGE.level == 9
        assert SHAPECHANGE.school == SpellSchool.TRANSMUTATION

    def test_gate_attributes(self):
        assert GATE.level == 9
        assert GATE.school == SpellSchool.CONJURATION

    def test_foresight_attributes(self):
        assert FORESIGHT.level == 9
        assert FORESIGHT.school == SpellSchool.DIVINATION

    # ------------------------------------------------------------------ #
    #  Effect callback tests – mechanically interesting spells             #
    # ------------------------------------------------------------------ #

    def test_cone_of_cold_scaling_cl10(self):
        result = CONE_OF_COLD.effect_callback(None, None, 10)
        assert result["damage"] == "10d6"
        assert result["damage_type"] == "Cold"
        assert result["save"] == "Reflex half"

    def test_cone_of_cold_scaling_max_cl20(self):
        result = CONE_OF_COLD.effect_callback(None, None, 20)
        assert result["damage"] == "15d6"

    def test_cone_of_cold_scaling_cl15_exactly(self):
        result = CONE_OF_COLD.effect_callback(None, None, 15)
        assert result["damage"] == "15d6"

    def test_disintegrate_damage_scaling_cl10(self):
        result = DISINTEGRATE.effect_callback(None, None, 10)
        assert result["damage"] == "20d6"
        assert result["save_damage"] == "5d6"
        assert result["dust_on_death"] is True

    def test_disintegrate_damage_scaling_cl25_max(self):
        result = DISINTEGRATE.effect_callback(None, None, 25)
        assert result["damage"] == "40d6"

    def test_chain_lightning_secondary_cl10(self):
        result = CHAIN_LIGHTNING.effect_callback(None, None, 10)
        assert result["primary_damage"] == "10d6"
        assert result["max_secondary_targets"] == 10

    def test_chain_lightning_secondary_max_cl25(self):
        result = CHAIN_LIGHTNING.effect_callback(None, None, 25)
        assert result["primary_damage"] == "20d6"
        assert result["max_secondary_targets"] == 20

    def test_stoneskin_absorption_cl10(self):
        result = STONESKIN.effect_callback(None, None, 10)
        assert result["max_absorption"] == 100
        assert result["dr"] == "10/adamantine"

    def test_stoneskin_absorption_max_cl15(self):
        result = STONESKIN.effect_callback(None, None, 15)
        assert result["max_absorption"] == 150

    def test_stoneskin_absorption_cap_cl20(self):
        result = STONESKIN.effect_callback(None, None, 20)
        assert result["max_absorption"] == 150

    def test_finger_of_death_save_damage_uses_caster_level(self):
        result_cl10 = FINGER_OF_DEATH.effect_callback(None, None, 10)
        assert result_cl10["save_damage"] == "3d6+10"
        assert result_cl10["death_on_fail"] is True
        result_cl15 = FINGER_OF_DEATH.effect_callback(None, None, 15)
        assert result_cl15["save_damage"] == "3d6+15"

    def test_wail_of_the_banshee_max_targets_equals_caster_level(self):
        result = WAIL_OF_THE_BANSHEE.effect_callback(None, None, 12)
        assert result["max_targets"] == 12
        assert result["death_effect"] is True
        assert result["save"] == "Fortitude negates"

    def test_wail_of_the_banshee_max_targets_cl20(self):
        result = WAIL_OF_THE_BANSHEE.effect_callback(None, None, 20)
        assert result["max_targets"] == 20

    def test_polar_ray_damage_cap_cl25(self):
        result = POLAR_RAY.effect_callback(None, None, 25)
        assert result["damage"] == "25d6"
        assert result["dex_drain"] == "2d4"

    def test_polar_ray_damage_cap_cl30(self):
        result = POLAR_RAY.effect_callback(None, None, 30)
        assert result["damage"] == "25d6"

    def test_polar_ray_damage_cl10(self):
        result = POLAR_RAY.effect_callback(None, None, 10)
        assert result["damage"] == "10d6"
        assert result["attack"] == "ranged touch"

    def test_meteor_swarm_always_4_spheres(self):
        result = METEOR_SWARM.effect_callback(None, None, 17)
        assert result["spheres"] == 4
        assert result["direct_hit_bludgeoning"] == "2d6"
        assert result["direct_hit_fire"] == "6d6"
        assert result["area_fire"] == "6d6"

    def test_greater_invisibility_no_end_on_attack(self):
        result = GREATER_INVISIBILITY.effect_callback(None, None, 8)
        assert result["ends_on_attack"] is False
        assert result["duration_rounds"] == 8

    def test_dimension_door_effect(self):
        result = DIMENSION_DOOR.effect_callback(None, None, 10)
        assert result["can_bring_others"] is True
        assert result["teleport_type"] == "short"
        assert result["max_carry"] == "medium load"

    def test_confusion_duration_scales(self):
        result = CONFUSION.effect_callback(None, None, 7)
        assert result["duration_rounds"] == 7
        assert result["save"] == "Will negates"

    def test_black_tentacles_effect(self):
        result = BLACK_TENTACLES.effect_callback(None, None, 9)
        assert result["grapple_bonus"] == 7
        assert result["damage_per_round"] == "1d6+4"
        assert result["duration_rounds"] == 9

    def test_telekinesis_weight_cap(self):
        result = TELEKINESIS.effect_callback(None, None, 15)
        assert result["max_weight_lbs"] == 375
        result2 = TELEKINESIS.effect_callback(None, None, 20)
        assert result2["max_weight_lbs"] == 375

    def test_telekinesis_weight_cl10(self):
        result = TELEKINESIS.effect_callback(None, None, 10)
        assert result["max_weight_lbs"] == 250

    def test_contingency_max_spell_level(self):
        result = CONTINGENCY.effect_callback(None, None, 12)
        assert result["max_contingent_spell_level"] == 4
        assert result["duration_days"] == 12

    def test_repulsion_radius_scales(self):
        result = REPULSION.effect_callback(None, None, 10)
        assert result["radius_ft"] == 100
        assert result["save"] == "Will negates"

    def test_globe_of_invulnerability_blocks_low_levels(self):
        result = GLOBE_OF_INVULNERABILITY.effect_callback(None, None, 6)
        assert 0 in result["blocks_spell_levels"]
        assert 4 in result["blocks_spell_levels"]
        assert 5 not in result["blocks_spell_levels"]

    def test_true_seeing_effect(self):
        result = TRUE_SEEING.effect_callback(None, None, 10)
        assert result["see_invisible"] is True
        assert result["see_through_illusions"] is True
        assert result["see_ethereal"] is True
        assert result["range_ft"] == 120

    def test_power_word_blind_no_save(self):
        result = POWER_WORD_BLIND.effect_callback(None, None, 13)
        assert result["no_save"] is True
        assert result["threshold_permanent_hp"] == 50
        assert result["threshold_short_hp"] == 100

    def test_spell_turning_effect(self):
        result = SPELL_TURNING.effect_callback(None, None, 13)
        assert result["spell_levels_to_reflect"] == "1d4+6"
        assert result["affects_area_spells"] is False
        assert result["duration_minutes"] == 130

    def test_mind_blank_effect(self):
        result = MIND_BLANK.effect_callback(None, None, 15)
        assert result["immune_mind_affecting"] is True
        assert result["immune_divination"] is True
        assert result["duration_hours"] == 24

    def test_prismatic_wall_effect(self):
        result = PRISMATIC_WALL.effect_callback(None, None, 15)
        assert result["layers"] == 8
        assert result["blinds_on_gaze"] is True
        assert result["duration_minutes"] == 150

    def test_maze_effect(self):
        result = MAZE.effect_callback(None, None, 15)
        assert result["exit_dc"] == 20
        assert result["minotaur_escape"] is True

    def test_sunburst_undead_damage_scales(self):
        result = SUNBURST.effect_callback(None, None, 15)
        assert result["damage"] == "6d6"
        assert result["undead_damage"] == "15d6"
        result2 = SUNBURST.effect_callback(None, None, 30)
        assert result2["undead_damage"] == "25d6"

    def test_wish_effect(self):
        result = WISH.effect_callback(None, None, 20)
        assert result["xp_cost"] == 5000
        assert result["alters_reality"] is True
        assert result["duplicates_any_arcane"] is True

    def test_time_stop_effect(self):
        result = TIME_STOP.effect_callback(None, None, 17)
        assert result["duration_rounds"] == "1d4+1"
        assert result["only_caster_acts"] is True

    def test_shapechange_effect(self):
        result = SHAPECHANGE.effect_callback(None, None, 18)
        assert result["min_hd"] == 0.25
        assert result["max_hd"] == 25
        assert result["duration_minutes"] == 180
        assert result["free_changes"] is True

    def test_gate_effect(self):
        result = GATE.effect_callback(None, None, 20)
        assert result["portal"] is True
        assert result["calling"] is True
        assert result["duration_rounds"] == 20

    def test_foresight_effect(self):
        result = FORESIGHT.effect_callback(None, None, 18)
        assert result["never_surprised"] is True
        assert result["insight_ac_bonus"] == 2
        assert result["insight_reflex_bonus"] == 2
        assert result["duration_minutes"] == 180

    def test_clone_maturation_time(self):
        result = CLONE.effect_callback(None, None, 15)
        assert result["soul_transfer"] is True
        assert result["material_cost_gp"] == 1000
        assert result["time_to_mature_days"] == 2 * (20 - 15)

    def test_clone_maturation_time_at_or_above_20(self):
        result = CLONE.effect_callback(None, None, 20)
        assert result["time_to_mature_days"] == 0

    def test_power_word_stun_effect(self):
        result = POWER_WORD_STUN.effect_callback(None, None, 15)
        assert result["no_save"] is True
        assert result["threshold_4d4_hp"] == 50
        assert result["threshold_2d4_hp"] == 100

    def test_power_word_kill_effect(self):
        result = POWER_WORD_KILL.effect_callback(None, None, 17)
        assert result["no_save"] is True
        assert result["max_hp_threshold"] == 100

    def test_permanency_xp_cost_scales(self):
        result = PERMANENCY.effect_callback(None, None, 15)
        assert result["xp_cost"] == 500 + 15 * 100
        assert "Detect Magic" in result["eligible_spells"]

    def test_limited_wish_effect(self):
        result = LIMITED_WISH.effect_callback(None, None, 14)
        assert result["xp_cost"] == 300
        assert result["undo_misfortune"] is True

    def test_sending_effect(self):
        result = SENDING.effect_callback(None, None, 10)
        assert result["max_words"] == 25
        assert result["reply_words"] == 25
        assert result["range"] == "unlimited"

    def test_arcane_eye_effect(self):
        result = ARCANE_EYE.effect_callback(None, None, 8)
        assert result["move_speed_ft"] == 30
        assert result["concentration"] is True
        assert result["can_see_magic"] is False

    def test_polymorph_effect(self):
        result = POLYMORPH.effect_callback(None, None, 10)
        assert result["max_hd"] == 15
        assert result["gains_physical_stats"] is True
        assert result["retains_mental_stats"] is True
        assert result["duration_minutes"] == 10

    def test_cloudkill_effect(self):
        result = CLOUDKILL.effect_callback(None, None, 10)
        assert result["instant_death_hd"] == 3
        assert result["fort_save_hd_threshold"] == 6
        assert result["con_damage"] == "1d4"
        assert result["move_ft_per_round"] == 10

    def test_dominate_person_effect(self):
        result = DOMINATE_PERSON.effect_callback(None, None, 12)
        assert result["duration_days"] == 12
        assert result["allows_new_save"] is True

    def test_feeblemind_effect(self):
        result = FEEBLEMIND.effect_callback(None, None, 10)
        assert result["int_score"] == 1
        assert result["cha_score"] == 1
        assert result["harder_vs_arcane_casters"] is True

    def test_wall_of_force_effect(self):
        result = WALL_OF_FORCE.effect_callback(None, None, 10)
        assert result["blocks_all"] is True
        assert result["immune_to_dispel"] is True
        assert result["vulnerable_to_disintegrate"] is True
        assert result["duration_rounds"] == 10

    def test_ice_storm_effect(self):
        result = ICE_STORM.effect_callback(None, None, 8)
        assert result["bludgeoning_damage"] == "3d6"
        assert result["cold_damage"] == "2d6"
        assert result["hampers_movement"] is True

    def test_mislead_effect(self):
        result = MISLEAD.effect_callback(None, None, 11)
        assert result["caster_invisible"] is True
        assert result["double_created"] is True
        assert result["duration_rounds"] == 11

    def test_legend_lore_effect(self):
        result = LEGEND_LORE.effect_callback(None, None, 12)
        assert result["reveals_legend"] is True
        assert result["casting_time"] == "variable"

    def test_ethereal_jaunt_effect(self):
        result = ETHEREAL_JAUNT.effect_callback(None, None, 14)
        assert result["ethereal"] is True
        assert result["see_material_plane"] is True
        assert result["duration_rounds"] == 14

    def test_mordenkainens_sword_effect(self):
        result = MORDENKAINENS_SWORD.effect_callback(None, None, 14)
        assert result["attack_bonus"] == 3
        assert result["damage"] == "4d6+3"
        assert result["damage_type"] == "Force"
        assert result["bab"] == 14
        assert result["duration_rounds"] == 14

    def test_reverse_gravity_effect(self):
        result = REVERSE_GRAVITY.effect_callback(None, None, 13)
        assert result["area"] == "20-ft radius, 40-ft high cylinder"
        assert result["duration_rounds"] == 13

    def test_prismatic_spray_effect(self):
        result = PRISMATIC_SPRAY.effect_callback(None, None, 13)
        assert result["effects"] == 7
        assert result["area"] == "60-ft cone"
        assert result["save"] == "varies"

    def test_greater_prying_eyes_effect(self):
        result = GREATER_PRYING_EYES.effect_callback(None, None, 15)
        assert result["true_seeing"] is True
        assert result["max_eyes"] == 20
        assert result["speed_ft"] == 30

    # ------------------------------------------------------------------ #
    #  School grouping tests                                               #
    # ------------------------------------------------------------------ #

    def test_evocation_contains_new_spells(self):
        registry = create_default_registry()
        evocations = [s.name for s in registry.get_by_school(SpellSchool.EVOCATION)]
        assert "Cone of Cold" in evocations
        assert "Chain Lightning" in evocations
        assert "Wall of Force" in evocations
        assert "Meteor Swarm" in evocations

    def test_transmutation_contains_new_spells(self):
        registry = create_default_registry()
        transmutations = [s.name for s in registry.get_by_school(SpellSchool.TRANSMUTATION)]
        assert "Polymorph" in transmutations
        assert "Disintegrate" in transmutations
        assert "Reverse Gravity" in transmutations
        assert "Time Stop" in transmutations
        assert "Shapechange" in transmutations

    def test_conjuration_contains_new_spells(self):
        registry = create_default_registry()
        conjurations = [s.name for s in registry.get_by_school(SpellSchool.CONJURATION)]
        assert "Dimension Door" in conjurations
        assert "Black Tentacles" in conjurations
        assert "Cloudkill" in conjurations
        assert "Gate" in conjurations

    def test_abjuration_contains_new_spells(self):
        registry = create_default_registry()
        abjurations = [s.name for s in registry.get_by_school(SpellSchool.ABJURATION)]
        assert "Stoneskin" in abjurations
        assert "Globe of Invulnerability" in abjurations
        assert "Spell Turning" in abjurations
        assert "Mind Blank" in abjurations
        assert "Prismatic Wall" in abjurations

    def test_enchantment_contains_new_spells(self):
        registry = create_default_registry()
        enchantments = [s.name for s in registry.get_by_school(SpellSchool.ENCHANTMENT)]
        assert "Confusion" in enchantments
        assert "Dominate Person" in enchantments
        assert "Power Word Blind" in enchantments
        assert "Power Word Stun" in enchantments
        assert "Power Word Kill" in enchantments

    def test_necromancy_contains_new_spells(self):
        registry = create_default_registry()
        necromancies = [s.name for s in registry.get_by_school(SpellSchool.NECROMANCY)]
        assert "Finger of Death" in necromancies
        assert "Clone" in necromancies
        assert "Wail of the Banshee" in necromancies

    def test_divination_contains_new_spells(self):
        registry = create_default_registry()
        divinations = [s.name for s in registry.get_by_school(SpellSchool.DIVINATION)]
        assert "Arcane Eye" in divinations
        assert "True Seeing" in divinations
        assert "Greater Prying Eyes" in divinations
        assert "Foresight" in divinations

    def test_illusion_contains_new_spells(self):
        registry = create_default_registry()
        illusions = [s.name for s in registry.get_by_school(SpellSchool.ILLUSION)]
        assert "Greater Invisibility" in illusions
        assert "Mislead" in illusions

    def test_universal_contains_new_spells(self):
        registry = create_default_registry()
        universals = [s.name for s in registry.get_by_school(SpellSchool.UNIVERSAL)]
        assert "Permanency" in universals
        assert "Limited Wish" in universals
        assert "Wish" in universals
