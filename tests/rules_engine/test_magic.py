"""
tests/rules_engine/test_magic.py
---------------------------------
Unit tests for the Wizardry Engine: magic.py and spellcasting.py.

Verifies:
- Spell dataclass creation and validation.
- SpellRegistry lookups.
- Spellbook learning and querying.
- SpellSlotManager slot calculations (base + bonus from Intelligence).
- SpellResolver save DC calculations.
- Character35e integration with spellcasting components.
"""

import pytest

from src.rules_engine.magic import (
    Spell,
    SpellRegistry,
    DEFAULT_SPELL_REGISTRY,
    SPELL_SCHOOLS,
)
from src.rules_engine.spellcasting import (
    Spellbook,
    SpellSlotManager,
    SpellResolver,
    _bonus_spells_for_level,
)
from src.rules_engine.character_35e import Character35e


# ---------------------------------------------------------------------------
# Spell Dataclass Tests
# ---------------------------------------------------------------------------

class TestSpell:
    def test_create_spell(self):
        spell = Spell(name="Test Spell", level=1, school="Evocation")
        assert spell.name == "Test Spell"
        assert spell.level == 1
        assert spell.school == "Evocation"

    def test_invalid_school_raises(self):
        with pytest.raises(ValueError, match="Invalid spell school"):
            Spell(name="Bad Spell", level=1, school="Pyromancy")

    def test_invalid_level_raises(self):
        with pytest.raises(ValueError, match="Spell level must be 0–9"):
            Spell(name="Bad Spell", level=10, school="Evocation")

    def test_negative_level_raises(self):
        with pytest.raises(ValueError, match="Spell level must be 0–9"):
            Spell(name="Bad Spell", level=-1, school="Evocation")

    def test_default_components_empty(self):
        spell = Spell(name="Simple", level=0, school="Universal")
        assert spell.components == []

    def test_effect_callback_default_none(self):
        spell = Spell(name="Simple", level=0, school="Universal")
        assert spell.effect_callback is None


# ---------------------------------------------------------------------------
# SpellRegistry Tests
# ---------------------------------------------------------------------------

class TestSpellRegistry:
    def test_register_and_get(self):
        registry = SpellRegistry()
        spell = Spell(name="Fireball", level=3, school="Evocation")
        registry.register(spell)
        assert registry.get("Fireball") is spell

    def test_get_nonexistent_returns_none(self):
        registry = SpellRegistry()
        assert registry.get("Nonexistent") is None

    def test_duplicate_registration_raises(self):
        registry = SpellRegistry()
        spell = Spell(name="Fireball", level=3, school="Evocation")
        registry.register(spell)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(spell)

    def test_get_by_level(self):
        registry = SpellRegistry()
        s1 = Spell(name="Spell A", level=1, school="Evocation")
        s2 = Spell(name="Spell B", level=1, school="Abjuration")
        s3 = Spell(name="Spell C", level=2, school="Conjuration")
        registry.register(s1)
        registry.register(s2)
        registry.register(s3)
        level_1 = registry.get_by_level(1)
        assert len(level_1) == 2
        assert s1 in level_1
        assert s2 in level_1

    def test_contains(self):
        registry = SpellRegistry()
        spell = Spell(name="Shield", level=1, school="Abjuration")
        registry.register(spell)
        assert "Shield" in registry
        assert "Nonexistent" not in registry

    def test_len(self):
        registry = SpellRegistry()
        assert len(registry) == 0
        registry.register(Spell(name="A", level=0, school="Universal"))
        assert len(registry) == 1


class TestDefaultSpellRegistry:
    def test_magic_missile_exists(self):
        mm = DEFAULT_SPELL_REGISTRY.get("Magic Missile")
        assert mm is not None
        assert mm.level == 1
        assert mm.school == "Evocation"
        assert "V" in mm.components
        assert "S" in mm.components

    def test_mage_armor_exists(self):
        ma = DEFAULT_SPELL_REGISTRY.get("Mage Armor")
        assert ma is not None
        assert ma.level == 1
        assert ma.school == "Conjuration"
        assert "V" in ma.components
        assert "S" in ma.components
        assert "F" in ma.components


# ---------------------------------------------------------------------------
# Spellbook Tests
# ---------------------------------------------------------------------------

class TestSpellbook:
    def test_learn_spell(self):
        book = Spellbook()
        spell = Spell(name="Sleep", level=1, school="Enchantment")
        assert book.learn_spell(spell) is True
        assert book.knows_spell(spell) is True

    def test_learn_duplicate_returns_false(self):
        book = Spellbook()
        spell = Spell(name="Sleep", level=1, school="Enchantment")
        book.learn_spell(spell)
        assert book.learn_spell(spell) is False

    def test_get_spells_by_level(self):
        book = Spellbook()
        s1 = Spell(name="Spell A", level=1, school="Evocation")
        s2 = Spell(name="Spell B", level=2, school="Evocation")
        book.learn_spell(s1)
        book.learn_spell(s2)
        assert len(book.get_spells_by_level(1)) == 1
        assert len(book.get_spells_by_level(2)) == 1
        assert len(book.get_spells_by_level(3)) == 0

    def test_all_known(self):
        book = Spellbook()
        s1 = Spell(name="A", level=0, school="Universal")
        s2 = Spell(name="B", level=1, school="Evocation")
        book.learn_spell(s1)
        book.learn_spell(s2)
        assert len(book.all_known()) == 2

    def test_serialization_roundtrip(self):
        book = Spellbook()
        mm = DEFAULT_SPELL_REGISTRY.get("Magic Missile")
        book.learn_spell(mm)
        data = book.to_dict()
        restored = Spellbook.from_dict(data, DEFAULT_SPELL_REGISTRY)
        assert restored.knows_spell(mm)


# ---------------------------------------------------------------------------
# Bonus Spells Calculation Tests
# ---------------------------------------------------------------------------

class TestBonusSpells:
    def test_no_bonus_for_cantrips(self):
        assert _bonus_spells_for_level(20, 0) == 0

    def test_int_16_level_1_bonus(self):
        # INT 16 → mod +3 → bonus for level 1 = (3 - 1) // 4 + 1 = 1
        assert _bonus_spells_for_level(16, 1) == 1

    def test_int_16_level_2_bonus(self):
        # INT 16 → mod +3 → bonus for level 2 = (3 - 2) // 4 + 1 = 1
        assert _bonus_spells_for_level(16, 2) == 1

    def test_int_16_level_3_bonus(self):
        # INT 16 → mod +3 → bonus for level 3 = (3 - 3) // 4 + 1 = 1
        assert _bonus_spells_for_level(16, 3) == 1

    def test_int_16_level_4_no_bonus(self):
        # INT 16 → mod +3 → mod < spell_level, no bonus
        assert _bonus_spells_for_level(16, 4) == 0

    def test_int_10_no_bonus(self):
        # INT 10 → mod +0 → no bonus for any level
        assert _bonus_spells_for_level(10, 1) == 0

    def test_int_insufficient_for_spell_level(self):
        # Need INT >= 10 + spell_level to cast. INT 11 < 12 (10+2)
        assert _bonus_spells_for_level(11, 2) == 0

    def test_int_20_level_1_bonus(self):
        # INT 20 → mod +5 → bonus for level 1 = (5 - 1) // 4 + 1 = 2
        assert _bonus_spells_for_level(20, 1) == 2


# ---------------------------------------------------------------------------
# SpellSlotManager Tests
# ---------------------------------------------------------------------------

class TestSpellSlotManager:
    def test_level_1_wizard_int_16_cantrips(self):
        """A Level 1 Wizard with 16 INT has 3 cantrip slots (no bonus for 0-level)."""
        mgr = SpellSlotManager(caster_level=1, intelligence=16)
        assert mgr.get_total_slots(0) == 3

    def test_level_1_wizard_int_16_first_level(self):
        """A Level 1 Wizard with 16 INT has 2 first-level slots (1 base + 1 bonus)."""
        mgr = SpellSlotManager(caster_level=1, intelligence=16)
        assert mgr.get_total_slots(1) == 2

    def test_level_1_wizard_int_10(self):
        """A Level 1 Wizard with 10 INT has 1 first-level slot (no bonus)."""
        mgr = SpellSlotManager(caster_level=1, intelligence=10)
        assert mgr.get_total_slots(0) == 3
        assert mgr.get_total_slots(1) == 1

    def test_no_second_level_at_caster_level_1(self):
        """A Level 1 Wizard cannot cast 2nd-level spells."""
        mgr = SpellSlotManager(caster_level=1, intelligence=16)
        assert mgr.get_total_slots(2) == 0

    def test_expend_slot(self):
        mgr = SpellSlotManager(caster_level=1, intelligence=16)
        assert mgr.get_remaining_slots(1) == 2
        assert mgr.expend_slot(1) is True
        assert mgr.get_remaining_slots(1) == 1
        assert mgr.expend_slot(1) is True
        assert mgr.get_remaining_slots(1) == 0
        assert mgr.expend_slot(1) is False

    def test_expend_slot_invalid_level(self):
        mgr = SpellSlotManager(caster_level=1, intelligence=16)
        assert mgr.expend_slot(9) is False

    def test_prepare_spell(self):
        mgr = SpellSlotManager(caster_level=1, intelligence=16)
        mm = DEFAULT_SPELL_REGISTRY.get("Magic Missile")
        assert mgr.prepare_spell(mm, 1) is True
        assert mgr.prepare_spell(mm, 1) is True  # Can prepare same spell twice
        assert mgr.prepare_spell(mm, 1) is False  # No more slots

    def test_prepare_spell_invalid_level(self):
        mgr = SpellSlotManager(caster_level=1, intelligence=16)
        mm = DEFAULT_SPELL_REGISTRY.get("Magic Missile")
        assert mgr.prepare_spell(mm, 5) is False

    def test_rest_resets_slots(self):
        mgr = SpellSlotManager(caster_level=1, intelligence=16)
        mgr.expend_slot(1)
        mgr.expend_slot(1)
        assert mgr.get_remaining_slots(1) == 0
        mgr.rest()
        assert mgr.get_remaining_slots(1) == 2

    def test_level_5_wizard_int_18(self):
        """Level 5 Wizard with 18 INT: verify multiple levels of slots."""
        mgr = SpellSlotManager(caster_level=5, intelligence=18)
        # Level 0: 4 base + 0 bonus = 4
        assert mgr.get_total_slots(0) == 4
        # Level 1: 3 base + 1 bonus (mod 4, (4-1)//4+1=1) = 4
        assert mgr.get_total_slots(1) == 4
        # Level 2: 2 base + 1 bonus (mod 4, (4-2)//4+1=1) = 3
        assert mgr.get_total_slots(2) == 3
        # Level 3: 1 base + 1 bonus (mod 4, (4-3)//4+1=1) = 2
        assert mgr.get_total_slots(3) == 2

    def test_serialization_roundtrip(self):
        mgr = SpellSlotManager(caster_level=1, intelligence=16)
        mgr.expend_slot(1)
        data = mgr.to_dict()
        restored = SpellSlotManager.from_dict(data)
        assert restored.caster_level == 1
        assert restored.intelligence == 16
        assert restored.get_remaining_slots(1) == 1


# ---------------------------------------------------------------------------
# SpellResolver Tests
# ---------------------------------------------------------------------------

class TestSpellResolver:
    def test_save_dc_level_1_int_16(self):
        """DC = 10 + 1 + 3 = 14 for a 1st-level spell with INT 16."""
        resolver = SpellResolver(intelligence=16)
        assert resolver.spell_save_dc(1) == 14

    def test_save_dc_level_0_int_16(self):
        """DC = 10 + 0 + 3 = 13 for a cantrip with INT 16."""
        resolver = SpellResolver(intelligence=16)
        assert resolver.spell_save_dc(0) == 13

    def test_save_dc_level_9_int_20(self):
        """DC = 10 + 9 + 5 = 24 for a 9th-level spell with INT 20."""
        resolver = SpellResolver(intelligence=20)
        assert resolver.spell_save_dc(9) == 24

    def test_caster_level_check_success(self):
        resolver = SpellResolver(intelligence=16, caster_level=5)
        # d20 roll of 10 + caster level 5 = 15 >= DC 15
        assert resolver.caster_level_check(dc=15, roll=10) is True

    def test_caster_level_check_failure(self):
        resolver = SpellResolver(intelligence=16, caster_level=5)
        # d20 roll of 9 + caster level 5 = 14 < DC 15
        assert resolver.caster_level_check(dc=15, roll=9) is False


# ---------------------------------------------------------------------------
# Character35e Integration Tests
# ---------------------------------------------------------------------------

class TestCharacterSpellcasting:
    def test_wizard_with_spellbook(self):
        """Verify Character35e can hold a Spellbook."""
        book = Spellbook()
        mm = DEFAULT_SPELL_REGISTRY.get("Magic Missile")
        book.learn_spell(mm)

        wizard = Character35e(
            name="Gandalf",
            char_class="Wizard",
            level=1,
            intelligence=16,
            spellbook=book,
        )
        assert wizard.spellbook is not None
        assert wizard.spellbook.knows_spell(mm)

    def test_wizard_with_slot_manager(self):
        """Verify Character35e can hold a SpellSlotManager."""
        slots = SpellSlotManager(caster_level=1, intelligence=16)
        wizard = Character35e(
            name="Gandalf",
            char_class="Wizard",
            level=1,
            intelligence=16,
            spell_slot_manager=slots,
        )
        assert wizard.spell_slot_manager is not None
        assert wizard.spell_slot_manager.get_total_slots(1) == 2

    def test_wizard_serialization_roundtrip(self):
        """Verify to_dict/from_dict preserves spellcasting components."""
        book = Spellbook()
        mm = DEFAULT_SPELL_REGISTRY.get("Magic Missile")
        book.learn_spell(mm)
        slots = SpellSlotManager(caster_level=1, intelligence=16)

        wizard = Character35e(
            name="Gandalf",
            char_class="Wizard",
            level=1,
            intelligence=16,
            spellbook=book,
            spell_slot_manager=slots,
        )

        data = wizard.to_dict()
        assert "spellbook" in data
        assert "spell_slot_manager" in data

        restored = Character35e.from_dict(data)
        assert restored.spellbook is not None
        assert restored.spellbook.knows_spell(mm)
        assert restored.spell_slot_manager is not None
        assert restored.spell_slot_manager.get_total_slots(1) == 2

    def test_non_caster_has_no_spellbook(self):
        """Non-caster characters have no spellbook or slots by default."""
        fighter = Character35e(name="Conan", char_class="Fighter", level=5)
        assert fighter.spellbook is None
        assert fighter.spell_slot_manager is None
        data = fighter.to_dict()
        assert "spellbook" not in data
        assert "spell_slot_manager" not in data
