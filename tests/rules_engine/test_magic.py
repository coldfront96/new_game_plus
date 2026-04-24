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
    # Phase 3 – Cleric Level 0
    GUIDANCE,
    VIRTUE,
    INFLICT_MINOR_WOUNDS,
    DETECT_UNDEAD,
    CREATE_WATER,
    PURIFY_FOOD_AND_DRINK,
    # Phase 3 – Cleric Level 1
    COMMAND,
    SANCTUARY,
    DIVINE_FAVOR,
    DOOM,
    ENTROPIC_SHIELD,
    # Phase 3 – Cleric Level 2
    CURE_MODERATE_WOUNDS,
    SILENCE,
    SPIRITUAL_WEAPON,
    CONSECRATE,
    AID,
    DESECRATE,
    BLINDNESS_DEAFNESS,
    # Phase 3 – Cleric Level 3
    CURE_SERIOUS_WOUNDS,
    PRAYER,
    SEARING_LIGHT,
    SPEAK_WITH_DEAD,
    INFLICT_SERIOUS_WOUNDS,
    # Phase 3 – Cleric Level 4
    CURE_CRITICAL_WOUNDS,
    DIVINE_POWER,
    FREEDOM_OF_MOVEMENT,
    NEUTRALIZE_POISON,
    RESTORATION,
    # Phase 3 – Cleric Level 5
    FLAME_STRIKE,
    INSECT_PLAGUE,
    RIGHTEOUS_MIGHT,
    BREAK_ENCHANTMENT,
    # Phase 3 – Cleric Level 6
    BLADE_BARRIER,
    WORD_OF_RECALL,
    # Phase 3 – Cleric Level 7
    RESURRECTION,
    # Phase 3 – Cleric Level 9
    MASS_HEAL,
    # Phase 3 – Paladin Level 1
    DETECT_EVIL,
    PROTECTION_FROM_EVIL,
    BLESS_WEAPON,
    # Phase 3 – Paladin Level 2
    DELAY_POISON,
    SHIELD_OTHER,
    OWLS_WISDOM,
    # Phase 3 – Paladin Level 3
    DAYLIGHT,
    REMOVE_BLINDNESS_DEAFNESS,
    # Phase 3 – Paladin Level 4
    HOLY_SWORD,
    MARK_OF_JUSTICE,
    DISPEL_EVIL,
    HOLY_AURA,
    # Phase 4 – Druid Level 0
    FLARE,
    KNOW_DIRECTION,
    CURE_MINOR_WOUNDS,
    DETECT_ANIMALS_OR_PLANTS,
    SHILLELAGH,
    MENDING,
    # Phase 4 – Druid Level 1
    ENTANGLE,
    FAERIE_FIRE,
    LONGSTRIDER,
    SPEAK_WITH_ANIMALS,
    ANIMAL_FRIENDSHIP,
    PRODUCE_FLAME,
    # Phase 4 – Druid Level 2
    BARKSKIN,
    CALL_LIGHTNING,
    CHARM_ANIMAL,
    WARP_WOOD,
    FLAME_BLADE,
    TREE_SHAPE,
    # Phase 4 – Druid Level 3
    CONTAGION,
    WATER_BREATHING,
    POISON,
    SPIKE_GROWTH,
    QUENCH,
    # Phase 4 – Druid Level 4
    RUSTING_GRASP,
    COMMAND_PLANTS,
    REINCARNATE,
    REPEL_VERMIN,
    # Phase 4 – Druid Level 5
    ANIMAL_GROWTH,
    AWAKEN,
    WALL_OF_FIRE,
    CALL_LIGHTNING_STORM,
    # Phase 4 – Druid Level 6
    ANTILIFE_SHELL,
    LIVEOAK,
    # Phase 4 – Druid Level 7
    CONTROL_WEATHER,
    # Phase 4 – Druid Level 8
    EARTHQUAKE,
    # Phase 4 – Druid Level 9
    ELEMENTAL_SWARM,
    STORM_OF_VENGEANCE,
    # Phase 4 – Ranger Level 1
    ALARM,
    ANIMAL_MESSENGER,
    JUMP,
    # Phase 4 – Ranger Level 2
    SNARE,
    PASS_WITHOUT_TRACE,
    WIND_WALL,
    # Phase 4 – Ranger Level 3
    HEAL_ANIMAL_COMPANION,
    REMOVE_DISEASE,
    # Phase 4 – Ranger Level 4
    COMMUNE_WITH_NATURE,
    TREE_STRIDE,
    FIND_THE_PATH,
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
        assert registry.count == 187
        assert len(registry) == 187

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


# ---------------------------------------------------------------------------
# Phase 3 – Cleric / Paladin Divine Spells
# ---------------------------------------------------------------------------

class TestPhase3ClericPaladinSpells:

    # ------------------------------------------------------------------ #
    #  Registry membership                                                 #
    # ------------------------------------------------------------------ #

    def test_all_48_phase3_spells_in_registry(self):
        registry = create_default_registry()
        phase3_spells = [
            # Cleric Level 0
            "Guidance", "Virtue", "Inflict Minor Wounds", "Detect Undead",
            "Create Water", "Purify Food and Drink",
            # Cleric Level 1
            "Command", "Sanctuary", "Divine Favor", "Doom", "Entropic Shield",
            # Cleric Level 2
            "Cure Moderate Wounds", "Silence", "Spiritual Weapon",
            "Consecrate", "Aid", "Desecrate", "Blindness/Deafness",
            # Cleric Level 3
            "Cure Serious Wounds", "Prayer", "Searing Light",
            "Speak with Dead", "Inflict Serious Wounds",
            # Cleric Level 4
            "Cure Critical Wounds", "Divine Power", "Freedom of Movement",
            "Neutralize Poison", "Restoration",
            # Cleric Level 5
            "Flame Strike", "Insect Plague", "Righteous Might",
            "Break Enchantment",
            # Cleric Level 6
            "Blade Barrier", "Word of Recall",
            # Cleric Level 7
            "Resurrection",
            # Cleric Level 9
            "Mass Heal",
            # Paladin Level 1
            "Detect Evil", "Protection from Evil", "Bless Weapon",
            # Paladin Level 2
            "Delay Poison", "Shield Other", "Owl's Wisdom",
            # Paladin Level 3
            "Daylight", "Remove Blindness/Deafness",
            # Paladin Level 4
            "Holy Sword", "Mark of Justice", "Dispel Evil", "Holy Aura",
        ]
        for name in phase3_spells:
            assert name in registry, f"'{name}' missing from default registry"

    # ------------------------------------------------------------------ #
    #  Level grouping tests                                                #
    # ------------------------------------------------------------------ #

    def test_cleric_level_0_spells(self):
        registry = create_default_registry()
        level_0 = [s.name for s in registry.get_by_level(0)]
        for name in ("Guidance", "Virtue", "Inflict Minor Wounds",
                     "Detect Undead", "Create Water", "Purify Food and Drink"):
            assert name in level_0, f"'{name}' not in level 0"

    def test_cleric_level_1_spells(self):
        registry = create_default_registry()
        level_1 = [s.name for s in registry.get_by_level(1)]
        for name in ("Command", "Sanctuary", "Divine Favor", "Doom",
                     "Entropic Shield", "Detect Evil", "Protection from Evil",
                     "Bless Weapon"):
            assert name in level_1, f"'{name}' not in level 1"

    def test_cleric_level_2_spells(self):
        registry = create_default_registry()
        level_2 = [s.name for s in registry.get_by_level(2)]
        for name in ("Cure Moderate Wounds", "Silence", "Spiritual Weapon",
                     "Consecrate", "Aid", "Desecrate", "Blindness/Deafness",
                     "Delay Poison", "Shield Other", "Owl's Wisdom"):
            assert name in level_2, f"'{name}' not in level 2"

    def test_cleric_level_3_spells(self):
        registry = create_default_registry()
        level_3 = [s.name for s in registry.get_by_level(3)]
        for name in ("Cure Serious Wounds", "Prayer", "Searing Light",
                     "Speak with Dead", "Inflict Serious Wounds",
                     "Daylight", "Remove Blindness/Deafness"):
            assert name in level_3, f"'{name}' not in level 3"

    def test_cleric_level_4_spells(self):
        registry = create_default_registry()
        level_4 = [s.name for s in registry.get_by_level(4)]
        for name in ("Cure Critical Wounds", "Divine Power",
                     "Freedom of Movement", "Neutralize Poison", "Restoration",
                     "Holy Sword", "Mark of Justice", "Dispel Evil", "Holy Aura"):
            assert name in level_4, f"'{name}' not in level 4"

    def test_cleric_level_5_spells(self):
        registry = create_default_registry()
        level_5 = [s.name for s in registry.get_by_level(5)]
        for name in ("Flame Strike", "Insect Plague", "Righteous Might",
                     "Break Enchantment"):
            assert name in level_5, f"'{name}' not in level 5"

    def test_cleric_level_6_spells(self):
        registry = create_default_registry()
        level_6 = [s.name for s in registry.get_by_level(6)]
        assert "Blade Barrier" in level_6
        assert "Word of Recall" in level_6

    def test_cleric_level_7_spells(self):
        registry = create_default_registry()
        level_7 = [s.name for s in registry.get_by_level(7)]
        assert "Resurrection" in level_7

    def test_cleric_level_9_spells(self):
        registry = create_default_registry()
        level_9 = [s.name for s in registry.get_by_level(9)]
        assert "Mass Heal" in level_9

    # ------------------------------------------------------------------ #
    #  Attribute tests                                                     #
    # ------------------------------------------------------------------ #

    def test_guidance_attributes(self):
        assert GUIDANCE.level == 0
        assert GUIDANCE.school == SpellSchool.DIVINATION
        assert SpellComponent.VERBAL in GUIDANCE.components
        assert SpellComponent.SOMATIC in GUIDANCE.components

    def test_virtue_attributes(self):
        assert VIRTUE.level == 0
        assert VIRTUE.school == SpellSchool.TRANSMUTATION
        assert SpellComponent.DIVINE_FOCUS in VIRTUE.components

    def test_inflict_minor_wounds_attributes(self):
        assert INFLICT_MINOR_WOUNDS.level == 0
        assert INFLICT_MINOR_WOUNDS.school == SpellSchool.NECROMANCY

    def test_command_attributes(self):
        assert COMMAND.level == 1
        assert COMMAND.school == SpellSchool.ENCHANTMENT
        assert COMMAND.subschool == "Compulsion"
        assert "Mind-Affecting" in COMMAND.descriptor

    def test_sanctuary_attributes(self):
        assert SANCTUARY.level == 1
        assert SANCTUARY.school == SpellSchool.ABJURATION
        assert SpellComponent.DIVINE_FOCUS in SANCTUARY.components

    def test_divine_favor_attributes(self):
        assert DIVINE_FAVOR.level == 1
        assert DIVINE_FAVOR.school == SpellSchool.EVOCATION
        assert SpellComponent.DIVINE_FOCUS in DIVINE_FAVOR.components

    def test_doom_attributes(self):
        assert DOOM.level == 1
        assert DOOM.school == SpellSchool.NECROMANCY
        assert "Fear" in DOOM.descriptor
        assert "Mind-Affecting" in DOOM.descriptor

    def test_cure_moderate_wounds_attributes(self):
        assert CURE_MODERATE_WOUNDS.level == 2
        assert CURE_MODERATE_WOUNDS.school == SpellSchool.CONJURATION
        assert CURE_MODERATE_WOUNDS.subschool == "Healing"

    def test_spiritual_weapon_attributes(self):
        assert SPIRITUAL_WEAPON.level == 2
        assert SPIRITUAL_WEAPON.school == SpellSchool.EVOCATION
        assert "Force" in SPIRITUAL_WEAPON.descriptor
        assert SpellComponent.DIVINE_FOCUS in SPIRITUAL_WEAPON.components

    def test_consecrate_attributes(self):
        assert CONSECRATE.level == 2
        assert CONSECRATE.school == SpellSchool.EVOCATION
        assert "Good" in CONSECRATE.descriptor

    def test_desecrate_attributes(self):
        assert DESECRATE.level == 2
        assert DESECRATE.school == SpellSchool.EVOCATION
        assert "Evil" in DESECRATE.descriptor

    def test_blindness_deafness_attributes(self):
        assert BLINDNESS_DEAFNESS.level == 2
        assert BLINDNESS_DEAFNESS.school == SpellSchool.NECROMANCY

    def test_cure_serious_wounds_attributes(self):
        assert CURE_SERIOUS_WOUNDS.level == 3
        assert CURE_SERIOUS_WOUNDS.school == SpellSchool.CONJURATION
        assert CURE_SERIOUS_WOUNDS.subschool == "Healing"

    def test_flame_strike_attributes(self):
        assert FLAME_STRIKE.level == 5
        assert FLAME_STRIKE.school == SpellSchool.EVOCATION
        assert "Fire" in FLAME_STRIKE.descriptor
        assert SpellComponent.DIVINE_FOCUS in FLAME_STRIKE.components

    def test_blade_barrier_attributes(self):
        assert BLADE_BARRIER.level == 6
        assert BLADE_BARRIER.school == SpellSchool.EVOCATION
        assert "Force" in BLADE_BARRIER.descriptor

    def test_mass_heal_attributes(self):
        assert MASS_HEAL.level == 9
        assert MASS_HEAL.school == SpellSchool.CONJURATION
        assert MASS_HEAL.subschool == "Healing"

    def test_detect_evil_attributes(self):
        assert DETECT_EVIL.level == 1
        assert DETECT_EVIL.school == SpellSchool.DIVINATION
        assert SpellComponent.DIVINE_FOCUS in DETECT_EVIL.components

    def test_protection_from_evil_attributes(self):
        assert PROTECTION_FROM_EVIL.level == 1
        assert PROTECTION_FROM_EVIL.school == SpellSchool.ABJURATION
        assert "Good" in PROTECTION_FROM_EVIL.descriptor

    def test_bless_weapon_attributes(self):
        assert BLESS_WEAPON.level == 1
        assert BLESS_WEAPON.school == SpellSchool.TRANSMUTATION
        assert "Good" in BLESS_WEAPON.descriptor

    def test_holy_sword_attributes(self):
        assert HOLY_SWORD.level == 4
        assert HOLY_SWORD.school == SpellSchool.EVOCATION
        assert "Good" in HOLY_SWORD.descriptor

    def test_mark_of_justice_attributes(self):
        assert MARK_OF_JUSTICE.level == 4
        assert MARK_OF_JUSTICE.school == SpellSchool.NECROMANCY
        assert SpellComponent.DIVINE_FOCUS in MARK_OF_JUSTICE.components

    def test_dispel_evil_attributes(self):
        assert DISPEL_EVIL.level == 4
        assert DISPEL_EVIL.school == SpellSchool.ABJURATION
        assert "Good" in DISPEL_EVIL.descriptor

    def test_holy_aura_attributes(self):
        assert HOLY_AURA.level == 4
        assert HOLY_AURA.school == SpellSchool.ABJURATION
        assert "Good" in HOLY_AURA.descriptor

    # ------------------------------------------------------------------ #
    #  Effect callback scaling tests                                       #
    # ------------------------------------------------------------------ #

    def test_cure_moderate_wounds_scaling(self):
        result_cl5 = CURE_MODERATE_WOUNDS.effect_callback(None, None, 5)
        assert result_cl5["healing"] == "2d8+5"
        result_cl15 = CURE_MODERATE_WOUNDS.effect_callback(None, None, 15)
        assert result_cl15["healing"] == "2d8+10"
        result_cl20 = CURE_MODERATE_WOUNDS.effect_callback(None, None, 20)
        assert result_cl20["healing"] == "2d8+10"

    def test_cure_serious_wounds_scaling(self):
        result_cl5 = CURE_SERIOUS_WOUNDS.effect_callback(None, None, 5)
        assert result_cl5["healing"] == "3d8+5"
        result_cl15 = CURE_SERIOUS_WOUNDS.effect_callback(None, None, 15)
        assert result_cl15["healing"] == "3d8+15"
        result_cl20 = CURE_SERIOUS_WOUNDS.effect_callback(None, None, 20)
        assert result_cl20["healing"] == "3d8+15"

    def test_cure_critical_wounds_scaling(self):
        result_cl5 = CURE_CRITICAL_WOUNDS.effect_callback(None, None, 5)
        assert result_cl5["healing"] == "4d8+5"
        result_cl20 = CURE_CRITICAL_WOUNDS.effect_callback(None, None, 20)
        assert result_cl20["healing"] == "4d8+20"
        result_cl25 = CURE_CRITICAL_WOUNDS.effect_callback(None, None, 25)
        assert result_cl25["healing"] == "4d8+20"

    def test_searing_light_scaling(self):
        result_cl4 = SEARING_LIGHT.effect_callback(None, None, 4)
        assert result_cl4["damage"] == "2d8"
        result_cl10 = SEARING_LIGHT.effect_callback(None, None, 10)
        assert result_cl10["damage"] == "5d8"
        result_cl20 = SEARING_LIGHT.effect_callback(None, None, 20)
        assert result_cl20["damage"] == "5d8"

    def test_searing_light_undead_damage(self):
        result_cl4 = SEARING_LIGHT.effect_callback(None, None, 4)
        assert result_cl4["undead_damage"] == "4d8"
        result_cl10 = SEARING_LIGHT.effect_callback(None, None, 10)
        assert result_cl10["undead_damage"] == "10d8"
        result_cl12 = SEARING_LIGHT.effect_callback(None, None, 12)
        assert result_cl12["undead_damage"] == "10d8"

    def test_flame_strike_scaling(self):
        result_cl5 = FLAME_STRIKE.effect_callback(None, None, 5)
        assert result_cl5["damage"] == "5d6"
        result_cl15 = FLAME_STRIKE.effect_callback(None, None, 15)
        assert result_cl15["damage"] == "15d6"
        result_cl20 = FLAME_STRIKE.effect_callback(None, None, 20)
        assert result_cl20["damage"] == "15d6"

    def test_flame_strike_damage_types(self):
        result = FLAME_STRIKE.effect_callback(None, None, 10)
        assert result["fire_half"] is True
        assert result["divine_half"] is True
        assert result["save"] == "Reflex half"

    def test_blade_barrier_scaling(self):
        result_cl10 = BLADE_BARRIER.effect_callback(None, None, 10)
        assert result_cl10["damage"] == "10d6"
        result_cl20 = BLADE_BARRIER.effect_callback(None, None, 20)
        assert result_cl20["damage"] == "20d6"
        result_cl25 = BLADE_BARRIER.effect_callback(None, None, 25)
        assert result_cl25["damage"] == "20d6"

    def test_divine_favor_scaling(self):
        result_cl1 = DIVINE_FAVOR.effect_callback(None, None, 1)
        assert result_cl1["attack_bonus"] == 1
        result_cl6 = DIVINE_FAVOR.effect_callback(None, None, 6)
        assert result_cl6["attack_bonus"] == 2
        result_cl9 = DIVINE_FAVOR.effect_callback(None, None, 9)
        assert result_cl9["attack_bonus"] == 3
        result_cl20 = DIVINE_FAVOR.effect_callback(None, None, 20)
        assert result_cl20["attack_bonus"] == 3

    def test_mass_heal_scaling(self):
        result_cl10 = MASS_HEAL.effect_callback(None, None, 10)
        assert result_cl10["healing"] == 100
        result_cl25 = MASS_HEAL.effect_callback(None, None, 25)
        assert result_cl25["healing"] == 250
        result_cl30 = MASS_HEAL.effect_callback(None, None, 30)
        assert result_cl30["healing"] == 250

    def test_sanctuary_scaling(self):
        result_cl5 = SANCTUARY.effect_callback(None, None, 5)
        assert result_cl5["duration_rounds"] == 5

    def test_doom_duration_scaling(self):
        result_cl7 = DOOM.effect_callback(None, None, 7)
        assert result_cl7["duration_minutes"] == 7
        assert result_cl7["condition"] == "shaken"
        assert result_cl7["penalty"] == -2

    def test_create_water_scaling(self):
        result_cl5 = CREATE_WATER.effect_callback(None, None, 5)
        assert result_cl5["gallons"] == 10
        result_cl10 = CREATE_WATER.effect_callback(None, None, 10)
        assert result_cl10["gallons"] == 20

    def test_guidance_effect(self):
        result = GUIDANCE.effect_callback(None, None, 1)
        assert result["bonus"] == 1
        assert result["bonus_type"] == "competence"

    def test_virtue_effect(self):
        result = VIRTUE.effect_callback(None, None, 5)
        assert result["temp_hp"] == 1

    def test_inflict_minor_wounds_effect(self):
        result = INFLICT_MINOR_WOUNDS.effect_callback(None, None, 3)
        assert result["damage"] == 1
        assert result["heals_undead"] is True

    def test_detect_undead_effect(self):
        result = DETECT_UNDEAD.effect_callback(None, None, 5)
        assert result["detects_undead"] is True
        assert result["range_ft"] == 60

    def test_spiritual_weapon_scaling(self):
        result_cl3 = SPIRITUAL_WEAPON.effect_callback(None, None, 3)
        assert result_cl3["enhancement"] == 2
        result_cl15 = SPIRITUAL_WEAPON.effect_callback(None, None, 15)
        assert result_cl15["enhancement"] == 5

    def test_freedom_of_movement_effect(self):
        result = FREEDOM_OF_MOVEMENT.effect_callback(None, None, 8)
        assert result["ignore_grapple"] is True
        assert result["ignore_entangle"] is True
        assert result["move_underwater"] is True
        assert result["duration_minutes"] == 80

    def test_restoration_effect(self):
        result = RESTORATION.effect_callback(None, None, 10)
        assert result["removes_ability_damage"] is True
        assert result["removes_negative_levels"] is True
        assert result["material_cost_gp"] == 100

    def test_resurrection_scaling(self):
        result_cl10 = RESURRECTION.effect_callback(None, None, 10)
        assert result_cl10["max_years_dead"] == 100
        assert result_cl10["material_cost_gp"] == 10000

    def test_holy_sword_effect(self):
        result = HOLY_SWORD.effect_callback(None, None, 10)
        assert result["enhancement_bonus"] == 5
        assert result["holy_damage"] == "2d6"
        assert result["vs_evil_only"] is True
        assert result["duration_rounds"] == 10

    def test_dispel_evil_effect(self):
        result = DISPEL_EVIL.effect_callback(None, None, 8)
        assert result["ac_bonus_vs_evil"] == 4
        assert result["dispel_evil_spell"] is True
        assert result["banish_evil_extraplanar"] is True
        assert result["duration_rounds"] == 8

    def test_holy_aura_effect(self):
        result = HOLY_AURA.effect_callback(None, None, 12)
        assert result["deflection_bonus"] == 4
        assert result["resistance_bonus"] == 4
        assert result["spell_resistance"] == 25
        assert result["blinds_evil_attackers"] is True
        assert result["duration_rounds"] == 12

    def test_protection_from_evil_effect(self):
        result = PROTECTION_FROM_EVIL.effect_callback(None, None, 5)
        assert result["ac_bonus"] == 2
        assert result["save_bonus"] == 2
        assert result["blocks_possession"] is True
        assert result["duration_minutes"] == 5

    def test_bless_weapon_effect(self):
        result = BLESS_WEAPON.effect_callback(None, None, 7)
        assert result["enhancement_bonus"] == 1
        assert result["bypasses_dr_vs_evil_outsiders"] is True

    def test_owls_wisdom_effect(self):
        result = OWLS_WISDOM.effect_callback(None, None, 6)
        assert result["wis_bonus"] == 4
        assert result["bonus_type"] == "enhancement"
        assert result["duration_minutes"] == 6

    def test_daylight_effect(self):
        result = DAYLIGHT.effect_callback(None, None, 5)
        assert result["bright_radius_ft"] == 60
        assert result["shadowy_radius_ft"] == 60
        assert result["dispels_darkness_level"] == 3
        assert result["duration_minutes"] == 50

    def test_remove_blindness_deafness_effect(self):
        result = REMOVE_BLINDNESS_DEAFNESS.effect_callback(None, None, 7)
        assert result["removes_blindness"] is True
        assert result["removes_deafness"] is True

    def test_delay_poison_effect(self):
        result = DELAY_POISON.effect_callback(None, None, 6)
        assert result["suspends_poison"] is True
        assert result["duration_hours"] == 6

    def test_shield_other_effect(self):
        result = SHIELD_OTHER.effect_callback(None, None, 5)
        assert result["damage_split"] is True
        assert result["save_bonus"] == 1
        assert result["ac_bonus"] == 1

    def test_mark_of_justice_effect(self):
        result = MARK_OF_JUSTICE.effect_callback(None, None, 10)
        assert result["permanent"] is True
        assert result["triggered_curse"] is True

    # ------------------------------------------------------------------ #
    #  Divine Focus component tests                                        #
    # ------------------------------------------------------------------ #

    def test_divine_spells_use_divine_focus(self):
        """Key Cleric spells should use the Divine Focus (DF) component."""
        for spell in (VIRTUE, DOOM, DIVINE_FAVOR, SPIRITUAL_WEAPON,
                      CONSECRATE, DESECRATE, PRAYER, SPEAK_WITH_DEAD,
                      DIVINE_POWER, FREEDOM_OF_MOVEMENT, NEUTRALIZE_POISON,
                      FLAME_STRIKE, INSECT_PLAGUE, RIGHTEOUS_MIGHT,
                      RESURRECTION, DETECT_EVIL, MARK_OF_JUSTICE,
                      DISPEL_EVIL):
            assert SpellComponent.DIVINE_FOCUS in spell.components, (
                f"Expected {spell.name} to have DIVINE_FOCUS component"
            )

    # ------------------------------------------------------------------ #
    #  School grouping tests                                               #
    # ------------------------------------------------------------------ #

    def test_conjuration_contains_divine_spells(self):
        registry = create_default_registry()
        conjurations = [s.name for s in registry.get_by_school(SpellSchool.CONJURATION)]
        assert "Cure Moderate Wounds" in conjurations
        assert "Cure Serious Wounds" in conjurations
        assert "Cure Critical Wounds" in conjurations
        assert "Mass Heal" in conjurations
        assert "Neutralize Poison" in conjurations
        assert "Restoration" in conjurations
        assert "Resurrection" in conjurations
        assert "Create Water" in conjurations
        assert "Word of Recall" in conjurations

    def test_evocation_contains_divine_spells(self):
        registry = create_default_registry()
        evocations = [s.name for s in registry.get_by_school(SpellSchool.EVOCATION)]
        assert "Divine Favor" in evocations
        assert "Spiritual Weapon" in evocations
        assert "Flame Strike" in evocations
        assert "Blade Barrier" in evocations
        assert "Holy Sword" in evocations

    def test_abjuration_contains_divine_spells(self):
        registry = create_default_registry()
        abjurations = [s.name for s in registry.get_by_school(SpellSchool.ABJURATION)]
        assert "Sanctuary" in abjurations
        assert "Entropic Shield" in abjurations
        assert "Freedom of Movement" in abjurations
        assert "Protection from Evil" in abjurations
        assert "Dispel Evil" in abjurations
        assert "Holy Aura" in abjurations

    def test_necromancy_contains_divine_spells(self):
        registry = create_default_registry()
        necromancies = [s.name for s in registry.get_by_school(SpellSchool.NECROMANCY)]
        assert "Inflict Minor Wounds" in necromancies
        assert "Doom" in necromancies
        assert "Inflict Serious Wounds" in necromancies
        assert "Blindness/Deafness" in necromancies
        assert "Speak with Dead" in necromancies
        assert "Mark of Justice" in necromancies

    def test_transmutation_contains_divine_spells(self):
        registry = create_default_registry()
        transmutations = [s.name for s in registry.get_by_school(SpellSchool.TRANSMUTATION)]
        assert "Virtue" in transmutations
        assert "Purify Food and Drink" in transmutations
        assert "Righteous Might" in transmutations
        assert "Bless Weapon" in transmutations
        assert "Owl's Wisdom" in transmutations

    def test_divination_contains_divine_spells(self):
        registry = create_default_registry()
        divinations = [s.name for s in registry.get_by_school(SpellSchool.DIVINATION)]
        assert "Guidance" in divinations
        assert "Detect Undead" in divinations
        assert "Detect Evil" in divinations

    def test_enchantment_contains_divine_spells(self):
        registry = create_default_registry()
        enchantments = [s.name for s in registry.get_by_school(SpellSchool.ENCHANTMENT)]
        assert "Command" in enchantments
        assert "Aid" in enchantments
        assert "Prayer" in enchantments


# ---------------------------------------------------------------------------
# Phase 4 – Druid & Ranger Nature Spells
# ---------------------------------------------------------------------------

class TestPhase4DruidRangerSpells:

    # ------------------------------------------------------------------ #
    #  Registry membership                                                 #
    # ------------------------------------------------------------------ #

    def test_all_druid_orison_spells_in_registry(self):
        registry = create_default_registry()
        for name in (
            "Flare", "Know Direction", "Cure Minor Wounds",
            "Detect Animals or Plants", "Shillelagh", "Mending",
        ):
            assert name in registry, f"'{name}' missing from default registry"

    def test_all_druid_level1_spells_in_registry(self):
        registry = create_default_registry()
        for name in (
            "Entangle", "Faerie Fire", "Longstrider",
            "Speak with Animals", "Animal Friendship", "Produce Flame",
        ):
            assert name in registry, f"'{name}' missing from default registry"

    def test_all_druid_level2_spells_in_registry(self):
        registry = create_default_registry()
        for name in (
            "Barkskin", "Call Lightning", "Charm Animal",
            "Warp Wood", "Flame Blade", "Tree Shape",
        ):
            assert name in registry, f"'{name}' missing from default registry"

    def test_all_druid_level3_spells_in_registry(self):
        registry = create_default_registry()
        for name in ("Contagion", "Water Breathing", "Poison", "Spike Growth", "Quench"):
            assert name in registry, f"'{name}' missing from default registry"

    def test_all_druid_level4_spells_in_registry(self):
        registry = create_default_registry()
        for name in ("Rusting Grasp", "Command Plants", "Reincarnate", "Repel Vermin"):
            assert name in registry, f"'{name}' missing from default registry"

    def test_all_druid_level5_spells_in_registry(self):
        registry = create_default_registry()
        for name in ("Animal Growth", "Awaken", "Wall of Fire", "Call Lightning Storm"):
            assert name in registry, f"'{name}' missing from default registry"

    def test_all_druid_high_level_spells_in_registry(self):
        registry = create_default_registry()
        for name in (
            "Antilife Shell", "Liveoak",
            "Control Weather",
            "Earthquake",
            "Elemental Swarm", "Storm of Vengeance",
        ):
            assert name in registry, f"'{name}' missing from default registry"

    def test_all_ranger_spells_in_registry(self):
        registry = create_default_registry()
        for name in (
            "Alarm", "Animal Messenger", "Jump",
            "Snare", "Pass without Trace", "Wind Wall",
            "Heal Animal Companion", "Remove Disease",
            "Commune with Nature", "Tree Stride", "Find the Path",
        ):
            assert name in registry, f"'{name}' missing from default registry"

    # ------------------------------------------------------------------ #
    #  Druid orison level tests                                            #
    # ------------------------------------------------------------------ #

    def test_druid_orisons_are_level_0(self):
        for spell in (
            FLARE, KNOW_DIRECTION, CURE_MINOR_WOUNDS,
            DETECT_ANIMALS_OR_PLANTS, SHILLELAGH, MENDING,
        ):
            assert spell.level == 0, f"{spell.name} should be level 0"

    def test_druid_orisons_schools(self):
        assert FLARE.school == SpellSchool.EVOCATION
        assert KNOW_DIRECTION.school == SpellSchool.DIVINATION
        assert CURE_MINOR_WOUNDS.school == SpellSchool.CONJURATION
        assert DETECT_ANIMALS_OR_PLANTS.school == SpellSchool.DIVINATION
        assert SHILLELAGH.school == SpellSchool.TRANSMUTATION
        assert MENDING.school == SpellSchool.TRANSMUTATION

    def test_shillelagh_uses_divine_focus(self):
        assert SpellComponent.DIVINE_FOCUS in SHILLELAGH.components

    # ------------------------------------------------------------------ #
    #  Druid Level 1 attribute tests                                       #
    # ------------------------------------------------------------------ #

    def test_druid_level1_spells_have_correct_level(self):
        for spell in (
            ENTANGLE, FAERIE_FIRE, LONGSTRIDER,
            SPEAK_WITH_ANIMALS, ANIMAL_FRIENDSHIP, PRODUCE_FLAME,
        ):
            assert spell.level == 1, f"{spell.name} should be level 1"

    def test_entangle_uses_divine_focus(self):
        assert SpellComponent.DIVINE_FOCUS in ENTANGLE.components

    def test_faerie_fire_uses_divine_focus(self):
        assert SpellComponent.DIVINE_FOCUS in FAERIE_FIRE.components

    def test_produce_flame_descriptor(self):
        assert "Fire" in PRODUCE_FLAME.descriptor

    def test_animal_friendship_descriptor(self):
        assert "Mind-Affecting" in ANIMAL_FRIENDSHIP.descriptor
        assert "Animal" in ANIMAL_FRIENDSHIP.descriptor

    # ------------------------------------------------------------------ #
    #  Druid Level 2 attribute tests                                       #
    # ------------------------------------------------------------------ #

    def test_barkskin_uses_divine_focus(self):
        assert SpellComponent.DIVINE_FOCUS in BARKSKIN.components

    def test_flame_blade_uses_divine_focus(self):
        assert SpellComponent.DIVINE_FOCUS in FLAME_BLADE.components

    def test_charm_animal_school(self):
        assert CHARM_ANIMAL.school == SpellSchool.ENCHANTMENT

    def test_call_lightning_school(self):
        assert CALL_LIGHTNING.school == SpellSchool.CONJURATION
        assert "Electricity" in CALL_LIGHTNING.descriptor

    # ------------------------------------------------------------------ #
    #  Druid Level 3-4 attribute tests                                     #
    # ------------------------------------------------------------------ #

    def test_poison_uses_divine_focus(self):
        assert SpellComponent.DIVINE_FOCUS in POISON.components

    def test_spike_growth_uses_divine_focus(self):
        assert SpellComponent.DIVINE_FOCUS in SPIKE_GROWTH.components

    def test_quench_uses_divine_focus(self):
        assert SpellComponent.DIVINE_FOCUS in QUENCH.components

    def test_rusting_grasp_uses_divine_focus(self):
        assert SpellComponent.DIVINE_FOCUS in RUSTING_GRASP.components

    def test_reincarnate_uses_divine_focus(self):
        assert SpellComponent.DIVINE_FOCUS in REINCARNATE.components

    def test_repel_vermin_uses_divine_focus(self):
        assert SpellComponent.DIVINE_FOCUS in REPEL_VERMIN.components

    def test_contagion_school(self):
        assert CONTAGION.school == SpellSchool.NECROMANCY

    # ------------------------------------------------------------------ #
    #  Druid Level 5+ attribute tests                                      #
    # ------------------------------------------------------------------ #

    def test_wall_of_fire_uses_divine_focus(self):
        assert SpellComponent.DIVINE_FOCUS in WALL_OF_FIRE.components

    def test_wall_of_fire_descriptor(self):
        assert "Fire" in WALL_OF_FIRE.descriptor

    def test_call_lightning_storm_school(self):
        assert CALL_LIGHTNING_STORM.school == SpellSchool.CONJURATION
        assert "Electricity" in CALL_LIGHTNING_STORM.descriptor

    def test_antilife_shell_uses_divine_focus(self):
        assert SpellComponent.DIVINE_FOCUS in ANTILIFE_SHELL.components

    def test_earthquake_uses_divine_focus(self):
        assert SpellComponent.DIVINE_FOCUS in EARTHQUAKE.components

    def test_earthquake_level(self):
        assert EARTHQUAKE.level == 8

    def test_elemental_swarm_level(self):
        assert ELEMENTAL_SWARM.level == 9

    def test_storm_of_vengeance_level(self):
        assert STORM_OF_VENGEANCE.level == 9

    def test_control_weather_level(self):
        assert CONTROL_WEATHER.level == 7

    # ------------------------------------------------------------------ #
    #  Ranger spell levels                                                 #
    # ------------------------------------------------------------------ #

    def test_ranger_level1_spells(self):
        for spell in (ALARM, ANIMAL_MESSENGER, JUMP):
            assert spell.level == 1, f"{spell.name} should be level 1"

    def test_ranger_level2_spells(self):
        for spell in (SNARE, PASS_WITHOUT_TRACE, WIND_WALL):
            assert spell.level == 2, f"{spell.name} should be level 2"

    def test_ranger_level3_spells(self):
        for spell in (HEAL_ANIMAL_COMPANION, REMOVE_DISEASE):
            assert spell.level == 3, f"{spell.name} should be level 3"

    def test_ranger_level4_spells(self):
        for spell in (COMMUNE_WITH_NATURE, TREE_STRIDE, FIND_THE_PATH):
            assert spell.level == 4, f"{spell.name} should be level 4"

    def test_snare_uses_divine_focus(self):
        assert SpellComponent.DIVINE_FOCUS in SNARE.components

    def test_pass_without_trace_uses_divine_focus(self):
        assert SpellComponent.DIVINE_FOCUS in PASS_WITHOUT_TRACE.components

    def test_wind_wall_uses_divine_focus(self):
        assert SpellComponent.DIVINE_FOCUS in WIND_WALL.components

    def test_tree_stride_uses_divine_focus(self):
        assert SpellComponent.DIVINE_FOCUS in TREE_STRIDE.components

    def test_wind_wall_descriptor(self):
        assert "Air" in WIND_WALL.descriptor

    def test_alarm_school(self):
        assert ALARM.school == SpellSchool.ABJURATION

    def test_tree_stride_school(self):
        assert TREE_STRIDE.school == SpellSchool.CONJURATION
        assert TREE_STRIDE.subschool == "Teleportation"

    # ------------------------------------------------------------------ #
    #  Effect callback tests – Barkskin scaling                           #
    # ------------------------------------------------------------------ #

    def test_barkskin_cl3_gives_plus2(self):
        result = BARKSKIN.effect_callback(None, None, 3)
        assert result["natural_armor_bonus"] == 2
        assert result["bonus_type"] == "natural armor"

    def test_barkskin_cl6_gives_plus3(self):
        result = BARKSKIN.effect_callback(None, None, 6)
        assert result["natural_armor_bonus"] == 3

    def test_barkskin_cl9_gives_plus4(self):
        result = BARKSKIN.effect_callback(None, None, 9)
        assert result["natural_armor_bonus"] == 4

    def test_barkskin_cl15_capped_at_plus5(self):
        result = BARKSKIN.effect_callback(None, None, 15)
        assert result["natural_armor_bonus"] == 5

    def test_barkskin_cl20_still_capped_at_plus5(self):
        result = BARKSKIN.effect_callback(None, None, 20)
        assert result["natural_armor_bonus"] == 5

    def test_barkskin_duration_scales(self):
        result = BARKSKIN.effect_callback(None, None, 7)
        assert result["duration_minutes"] == 70

    # ------------------------------------------------------------------ #
    #  Effect callback tests – Produce Flame scaling                      #
    # ------------------------------------------------------------------ #

    def test_produce_flame_cl1_bonus_is_1(self):
        result = PRODUCE_FLAME.effect_callback(None, None, 1)
        assert result["melee_bonus"] == 1
        assert result["damage"] == "1d6+1"

    def test_produce_flame_cl3_bonus_is_3(self):
        result = PRODUCE_FLAME.effect_callback(None, None, 3)
        assert result["melee_bonus"] == 3
        assert result["damage"] == "1d6+3"

    def test_produce_flame_cl5_bonus_is_5(self):
        result = PRODUCE_FLAME.effect_callback(None, None, 5)
        assert result["melee_bonus"] == 5
        assert result["damage"] == "1d6+5"

    def test_produce_flame_cl10_capped_at_5(self):
        result = PRODUCE_FLAME.effect_callback(None, None, 10)
        assert result["melee_bonus"] == 5
        assert result["damage"] == "1d6+5"
        assert result["damage_type"] == "Fire"

    # ------------------------------------------------------------------ #
    #  Effect callback tests – Quench scaling                             #
    # ------------------------------------------------------------------ #

    def test_quench_cl5_deals_5d6(self):
        result = QUENCH.effect_callback(None, None, 5)
        assert result["fire_creature_damage"] == "5d6"
        assert result["extinguishes_fires"] is True

    def test_quench_cl10_deals_10d6(self):
        result = QUENCH.effect_callback(None, None, 10)
        assert result["fire_creature_damage"] == "10d6"

    def test_quench_cl15_capped_at_10d6(self):
        result = QUENCH.effect_callback(None, None, 15)
        assert result["fire_creature_damage"] == "10d6"

    def test_quench_area(self):
        result = QUENCH.effect_callback(None, None, 7)
        assert result["area"] == "20-ft radius"

    # ------------------------------------------------------------------ #
    #  Effect callback tests – Call Lightning Storm                       #
    # ------------------------------------------------------------------ #

    def test_call_lightning_storm_damage_is_5d6(self):
        result = CALL_LIGHTNING_STORM.effect_callback(None, None, 9)
        assert result["damage_per_bolt"] == "5d6"
        assert result["save"] == "Reflex half"

    def test_call_lightning_storm_bolts_scale(self):
        result = CALL_LIGHTNING_STORM.effect_callback(None, None, 10)
        assert result["bolts_available"] == 10

    def test_call_lightning_storm_duration_scales(self):
        result = CALL_LIGHTNING_STORM.effect_callback(None, None, 9)
        assert result["duration_minutes"] == 90

    # ------------------------------------------------------------------ #
    #  Effect callback tests – Storm of Vengeance phases                  #
    # ------------------------------------------------------------------ #

    def test_storm_of_vengeance_has_four_effect_phases(self):
        result = STORM_OF_VENGEANCE.effect_callback(None, None, 18)
        effects = result["effects"]
        assert len(effects) == 4
        assert "acid rain" in effects
        assert "lightning" in effects
        assert "hail" in effects
        assert "divine fire" in effects

    def test_storm_of_vengeance_area(self):
        result = STORM_OF_VENGEANCE.effect_callback(None, None, 18)
        assert result["area"] == "360-ft radius"
        assert result["max_rounds"] == 10

    # ------------------------------------------------------------------ #
    #  Effect callback tests – miscellaneous                              #
    # ------------------------------------------------------------------ #

    def test_entangle_effect(self):
        result = ENTANGLE.effect_callback(None, None, 5)
        assert result["area"] == "40-ft radius"
        assert result["save"] == "Reflex negates"
        assert result["duration_minutes"] == 5

    def test_flare_effect(self):
        result = FLARE.effect_callback(None, None, 1)
        assert result["penalty"] == -1
        assert result["duration_minutes"] == 1
        assert result["save"] == "Fortitude negates"

    def test_know_direction_effect(self):
        result = KNOW_DIRECTION.effect_callback(None, None, 1)
        assert result["reveals"] == "north direction"

    def test_cure_minor_wounds_effect(self):
        result = CURE_MINOR_WOUNDS.effect_callback(None, None, 5)
        assert result["healing"] == 1

    def test_shillelagh_duration_scales(self):
        result = SHILLELAGH.effect_callback(None, None, 7)
        assert result["enhancement_bonus"] == 1
        assert result["damage_die"] == "2d6"
        assert result["duration_minutes"] == 7

    def test_longstrider_effect(self):
        result = LONGSTRIDER.effect_callback(None, None, 6)
        assert result["speed_bonus_ft"] == 10
        assert result["bonus_type"] == "enhancement"
        assert result["duration_hours"] == 6

    def test_call_lightning_effect(self):
        result = CALL_LIGHTNING.effect_callback(None, None, 8)
        assert result["damage_indoor"] == "3d6"
        assert result["damage_outdoor"] == "3d10"
        assert result["bolts_available"] == 8

    def test_charm_animal_effect(self):
        result = CHARM_ANIMAL.effect_callback(None, None, 5)
        assert result["animal_only"] is True
        assert result["duration_hours"] == 5
        assert result["save"] == "Will negates"

    def test_warp_wood_scales(self):
        result = WARP_WOOD.effect_callback(None, None, 7)
        assert result["cubic_feet"] == 7
        assert result["destroys_wooden_weapons"] is True

    def test_flame_blade_effect(self):
        result = FLAME_BLADE.effect_callback(None, None, 4)
        assert result["damage"] == "1d8+2"
        assert result["damage_type"] == "Fire"

    def test_flame_blade_capped_at_10(self):
        result = FLAME_BLADE.effect_callback(None, None, 20)
        assert result["damage"] == "1d8+10"

    def test_water_breathing_duration_scales(self):
        result = WATER_BREATHING.effect_callback(None, None, 8)
        assert result["duration_hours"] == 16
        assert result["targets"] == "1 creature/level"

    def test_poison_effect(self):
        result = POISON.effect_callback(None, None, 10)
        assert result["initial_damage"] == "1d10 Con"
        assert result["secondary_damage"] == "1d10 Con"
        assert result["save"] == "Fortitude half"
        assert result["attack"] == "touch"

    def test_contagion_effect(self):
        result = CONTAGION.effect_callback(None, None, 9)
        assert result["save"] == "Fortitude negates"
        assert result["disease"] == "one of 6 diseases"

    def test_spike_growth_effect(self):
        result = SPIKE_GROWTH.effect_callback(None, None, 6)
        assert result["damage_per_5ft"] == "1d4"
        assert result["speed_reduced"] is True
        assert result["duration_hours"] == 6

    def test_rusting_grasp_effect(self):
        result = RUSTING_GRASP.effect_callback(None, None, 10)
        assert result["destroys_metal"] is True
        assert result["damage_to_creature"] == "3d6"
        assert result["attack"] == "touch"

    def test_command_plants_duration_scales(self):
        result = COMMAND_PLANTS.effect_callback(None, None, 12)
        assert result["duration_days"] == 12
        assert result["save"] == "Will negates"

    def test_reincarnate_effect(self):
        result = REINCARNATE.effect_callback(None, None, 9)
        assert result["new_body"] == "random race"
        assert result["soul_restored"] is True
        assert result["material_cost_gp"] == 1000

    def test_repel_vermin_duration_scales(self):
        result = REPEL_VERMIN.effect_callback(None, None, 8)
        assert result["radius_ft"] == 10
        assert result["duration_minutes"] == 80

    def test_animal_growth_effect(self):
        result = ANIMAL_GROWTH.effect_callback(None, None, 10)
        assert result["str_bonus"] == 8
        assert result["con_bonus"] == 4
        assert result["natural_armor"] == 2
        assert result["targets"] == "1 animal per 2 levels"

    def test_awaken_effect(self):
        result = AWAKEN.effect_callback(None, None, 11)
        assert result["grants_intelligence"] is True
        assert result["xp_cost"] == 1250
        assert result["target"] == "animal or tree"

    def test_wall_of_fire_effect(self):
        result = WALL_OF_FIRE.effect_callback(None, None, 10)
        assert result["proximity_10ft_damage"] == "2d4"
        assert result["proximity_20ft_damage"] == "1d4"
        assert result["pass_through_damage"] == "2d6+10"
        assert result["damage_type"] == "Fire"

    def test_wall_of_fire_capped_at_20(self):
        result = WALL_OF_FIRE.effect_callback(None, None, 25)
        assert result["pass_through_damage"] == "2d6+20"

    def test_antilife_shell_effect(self):
        result = ANTILIFE_SHELL.effect_callback(None, None, 12)
        assert result["radius_ft"] == 10
        assert result["excludes"] == "living creatures"
        assert result["duration_minutes"] == 120

    def test_liveoak_duration_scales(self):
        result = LIVEOAK.effect_callback(None, None, 14)
        assert result["animates_oak"] is True
        assert result["sentry"] is True
        assert result["duration_days"] == 14

    def test_control_weather_effect(self):
        result = CONTROL_WEATHER.effect_callback(None, None, 15)
        assert result["radius_miles"] == 2
        assert result["duration_hours"] == "4d12"
        assert "hurricane" in result["weather_types"]

    def test_earthquake_effect(self):
        result = EARTHQUAKE.effect_callback(None, None, 15)
        assert result["area"] == "80-ft radius"
        assert result["collapses_structures"] is True
        assert result["fissures"] is True

    def test_elemental_swarm_effect(self):
        result = ELEMENTAL_SWARM.effect_callback(None, None, 17)
        assert result["phase_1"] == "2d4 Large elementals"
        assert result["phase_2"] == "1d4 Huge elementals"
        assert result["phase_3"] == "1 Elder elemental"
        assert result["duration_minutes"] == 170

    def test_alarm_effect(self):
        result = ALARM.effect_callback(None, None, 5)
        assert result["radius_ft"] == 20
        assert result["mental_or_audible"] is True
        assert result["duration_hours"] == 8

    def test_animal_messenger_duration_scales(self):
        result = ANIMAL_MESSENGER.effect_callback(None, None, 6)
        assert result["animal_size"] == "Tiny"
        assert result["duration_days"] == 6

    def test_jump_effect_scaling(self):
        # CL 1-3 → +10, CL 4-6 → +20, CL 7+ → +30
        result_cl1 = JUMP.effect_callback(None, None, 1)
        assert result_cl1["jump_bonus"] == 10

        result_cl4 = JUMP.effect_callback(None, None, 4)
        assert result_cl4["jump_bonus"] == 20

        result_cl7 = JUMP.effect_callback(None, None, 7)
        assert result_cl7["jump_bonus"] == 30

        result_cl20 = JUMP.effect_callback(None, None, 20)
        assert result_cl20["jump_bonus"] == 30

    def test_snare_effect(self):
        result = SNARE.effect_callback(None, None, 7)
        assert result["reflex_dc"] == 23
        assert result["holds_creature"] is True

    def test_pass_without_trace_effect(self):
        result = PASS_WITHOUT_TRACE.effect_callback(None, None, 8)
        assert result["leaves_no_tracks"] is True
        assert result["leaves_no_scent"] is True
        assert result["duration_hours"] == 8

    def test_wind_wall_duration_scales(self):
        result = WIND_WALL.effect_callback(None, None, 9)
        assert result["deflects_arrows"] is True
        assert result["deflects_gases"] is True
        assert result["deflects_tiny"] is True
        assert result["duration_rounds"] == 9

    def test_heal_animal_companion_scales(self):
        result_cl5 = HEAL_ANIMAL_COMPANION.effect_callback(None, None, 5)
        assert result_cl5["healing"] == 50
        assert result_cl5["animal_companion_only"] is True

        result_cl10 = HEAL_ANIMAL_COMPANION.effect_callback(None, None, 10)
        assert result_cl10["healing"] == 100

        result_cl20 = HEAL_ANIMAL_COMPANION.effect_callback(None, None, 20)
        assert result_cl20["healing"] == 150  # max 150

    def test_remove_disease_effect(self):
        result = REMOVE_DISEASE.effect_callback(None, None, 7)
        assert result["removes_disease"] is True
        assert result["magical_diseases"] is True

    def test_commune_with_nature_scales(self):
        result = COMMUNE_WITH_NATURE.effect_callback(None, None, 10)
        assert result["range_miles"] == 10
        assert "terrain" in result["reveals"]
        assert "animals" in result["reveals"]

    def test_tree_stride_effect(self):
        result = TREE_STRIDE.effect_callback(None, None, 8)
        assert result["range_miles"] == 3
        assert result["teleport_between_trees"] is True
        assert result["duration_hours"] == 8

    def test_find_the_path_duration_scales(self):
        result = FIND_THE_PATH.effect_callback(None, None, 12)
        assert result["shows_path"] is True
        assert result["avoids_obstacles"] is True
        assert result["duration_minutes"] == 120

    # ------------------------------------------------------------------ #
    #  School grouping tests                                               #
    # ------------------------------------------------------------------ #

    def test_transmutation_contains_nature_spells(self):
        registry = create_default_registry()
        transmutations = [s.name for s in registry.get_by_school(SpellSchool.TRANSMUTATION)]
        for name in (
            "Entangle", "Longstrider", "Barkskin", "Warp Wood", "Tree Shape",
            "Water Breathing", "Spike Growth", "Quench",
            "Rusting Grasp", "Command Plants", "Reincarnate",
            "Animal Growth", "Awaken", "Liveoak", "Control Weather",
            "Shillelagh", "Mending", "Snare", "Pass without Trace",
        ):
            assert name in transmutations, f"Expected {name!r} in Transmutation"

    def test_evocation_contains_nature_spells(self):
        registry = create_default_registry()
        evocations = [s.name for s in registry.get_by_school(SpellSchool.EVOCATION)]
        for name in ("Flare", "Faerie Fire", "Produce Flame", "Flame Blade",
                     "Wall of Fire", "Earthquake", "Wind Wall"):
            assert name in evocations, f"Expected {name!r} in Evocation"

    def test_conjuration_contains_nature_spells(self):
        registry = create_default_registry()
        conjurations = [s.name for s in registry.get_by_school(SpellSchool.CONJURATION)]
        for name in (
            "Cure Minor Wounds", "Call Lightning",
            "Call Lightning Storm", "Elemental Swarm", "Storm of Vengeance",
            "Heal Animal Companion", "Remove Disease", "Tree Stride",
        ):
            assert name in conjurations, f"Expected {name!r} in Conjuration"

    def test_divination_contains_nature_spells(self):
        registry = create_default_registry()
        divinations = [s.name for s in registry.get_by_school(SpellSchool.DIVINATION)]
        for name in (
            "Know Direction", "Detect Animals or Plants",
            "Speak with Animals", "Commune with Nature", "Find the Path",
        ):
            assert name in divinations, f"Expected {name!r} in Divination"

    def test_abjuration_contains_nature_spells(self):
        registry = create_default_registry()
        abjurations = [s.name for s in registry.get_by_school(SpellSchool.ABJURATION)]
        for name in ("Antilife Shell", "Repel Vermin", "Alarm"):
            assert name in abjurations, f"Expected {name!r} in Abjuration"

    def test_necromancy_contains_nature_spells(self):
        registry = create_default_registry()
        necromancies = [s.name for s in registry.get_by_school(SpellSchool.NECROMANCY)]
        for name in ("Contagion", "Poison"):
            assert name in necromancies, f"Expected {name!r} in Necromancy"

    def test_enchantment_contains_nature_spells(self):
        registry = create_default_registry()
        enchantments = [s.name for s in registry.get_by_school(SpellSchool.ENCHANTMENT)]
        for name in ("Animal Friendship", "Charm Animal", "Animal Messenger"):
            assert name in enchantments, f"Expected {name!r} in Enchantment"
