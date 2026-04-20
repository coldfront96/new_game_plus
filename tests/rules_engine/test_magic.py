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
        assert registry.count == 2
        assert len(registry) == 2

    def test_contains(self):
        registry = create_default_registry()
        assert "Magic Missile" in registry
        assert "Fireball" not in registry


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

    def test_wizard_level_1_int_mod_3_verification(self):
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
        assert sorc.spellbook is not None
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
