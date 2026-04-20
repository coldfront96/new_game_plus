"""
tests/rules_engine/test_sorcerer.py
------------------------------------
Unit tests for D&D 3.5e Sorcerer spontaneous spellcasting.

Verifies:
- Shield and Burning Hands spell definitions (instinctive Sorcerer spells).
- SpellsKnownManager creation and capacity enforcement.
- SpontaneousCasterManager: CHA-based bonus slots, casting from known list.
- Level 1 Sorcerer with 16 CHA can cast known 1st-level spells 4 times/day.
- Character35e integration with Sorcerer spellcasting.
"""

import pytest

from src.rules_engine.magic import (
    BURNING_HANDS,
    MAGIC_MISSILE,
    SHIELD,
    Spell,
    SpellComponent,
    SpellSchool,
    create_default_registry,
)
from src.rules_engine.spellcasting import (
    SpellSlotManager,
    SpellsKnownManager,
    SpontaneousCasterManager,
)
from src.rules_engine.character_35e import Character35e


# ---------------------------------------------------------------------------
# Instinctive spell definition tests
# ---------------------------------------------------------------------------

class TestSorcererSpellDefinitions:
    """Verify the canonical SRD attributes of Sorcerer instinctive spells."""

    def test_shield_attributes(self):
        assert SHIELD.name == "Shield"
        assert SHIELD.level == 1
        assert SHIELD.school == SpellSchool.ABJURATION
        assert SpellComponent.VERBAL in SHIELD.components
        assert SpellComponent.SOMATIC in SHIELD.components
        assert SHIELD.range == "Personal"
        assert SHIELD.duration == "1 min./level"
        assert "Force" in SHIELD.descriptor

    def test_shield_effect(self):
        result = SHIELD.effect_callback(None, None, 3)
        assert result["ac_bonus"] == 4
        assert result["bonus_type"] == "shield"
        assert result["blocks_magic_missile"] is True
        assert result["duration_minutes"] == 3
        assert result["force_effect"] is True

    def test_burning_hands_attributes(self):
        assert BURNING_HANDS.name == "Burning Hands"
        assert BURNING_HANDS.level == 1
        assert BURNING_HANDS.school == SpellSchool.EVOCATION
        assert SpellComponent.VERBAL in BURNING_HANDS.components
        assert SpellComponent.SOMATIC in BURNING_HANDS.components
        assert BURNING_HANDS.range == "15 ft."
        assert BURNING_HANDS.duration == "Instantaneous"
        assert "Fire" in BURNING_HANDS.descriptor

    def test_burning_hands_effect(self):
        result = BURNING_HANDS.effect_callback(None, None, 3)
        assert result["damage"] == "3d4"
        assert result["damage_type"] == "Fire"
        assert result["area"] == "15 ft. cone"
        assert result["save"] == "Reflex half"

    def test_burning_hands_caps_at_5d4(self):
        result = BURNING_HANDS.effect_callback(None, None, 10)
        assert result["damage"] == "5d4"
        assert result["max_dice"] == 5

    def test_sorcerer_spells_use_slots(self):
        """Verify all spell objects use __slots__ for memory efficiency."""
        assert hasattr(Spell, "__slots__")

    def test_sorcerer_spells_in_default_registry(self):
        registry = create_default_registry()
        assert registry.get("Shield") is SHIELD
        assert registry.get("Burning Hands") is BURNING_HANDS


# ---------------------------------------------------------------------------
# SpellsKnownManager tests
# ---------------------------------------------------------------------------

class TestSpellsKnownManager:
    """Tests for the SpellsKnownManager class."""

    def test_slots_true_attribute(self):
        """Verify SpellsKnownManager uses __slots__."""
        assert hasattr(SpellsKnownManager, "__slots__")

    def test_for_sorcerer_level_1(self):
        """Level 1 Sorcerer knows max 4 cantrips and 2 first-level spells."""
        mgr = SpellsKnownManager.for_sorcerer(level=1)
        assert mgr.max_known[0] == 4  # Cantrips
        assert mgr.max_known[1] == 2  # 1st level
        assert mgr.max_known[2] == 0  # 2nd level unavailable

    def test_learn_spell_success(self):
        mgr = SpellsKnownManager.for_sorcerer(level=1)
        assert mgr.learn_spell("Magic Missile", 1) is True
        assert mgr.is_known("Magic Missile", 1) is True

    def test_learn_spell_duplicate_rejected(self):
        mgr = SpellsKnownManager.for_sorcerer(level=1)
        mgr.learn_spell("Magic Missile", 1)
        assert mgr.learn_spell("Magic Missile", 1) is False

    def test_learn_spell_exceeds_cap(self):
        """Cannot learn more spells than the SRD table allows."""
        mgr = SpellsKnownManager.for_sorcerer(level=1)
        # Level 1 Sorcerer can only know 2 first-level spells
        mgr.learn_spell("Magic Missile", 1)
        mgr.learn_spell("Shield", 1)
        assert mgr.learn_spell("Burning Hands", 1) is False

    def test_can_learn_returns_false_at_cap(self):
        mgr = SpellsKnownManager.for_sorcerer(level=1)
        mgr.learn_spell("Magic Missile", 1)
        mgr.learn_spell("Shield", 1)
        assert mgr.can_learn(1) is False

    def test_can_learn_unavailable_level(self):
        mgr = SpellsKnownManager.for_sorcerer(level=1)
        assert mgr.can_learn(2) is False  # 2nd level not available at lvl 1

    def test_get_known(self):
        mgr = SpellsKnownManager.for_sorcerer(level=1)
        mgr.learn_spell("Magic Missile", 1)
        known = mgr.get_known(1)
        assert "Magic Missile" in known

    def test_total_known(self):
        mgr = SpellsKnownManager.for_sorcerer(level=1)
        mgr.learn_spell("Magic Missile", 1)
        mgr.learn_spell("Shield", 1)
        assert mgr.total_known() == 2


# ---------------------------------------------------------------------------
# SpontaneousCasterManager tests
# ---------------------------------------------------------------------------

class TestSpontaneousCasterManager:
    """Tests for the SpontaneousCasterManager class."""

    def test_slots_true_attribute(self):
        """Verify SpontaneousCasterManager uses __slots__."""
        assert hasattr(SpontaneousCasterManager, "__slots__")

    def test_for_sorcerer_creates_manager(self):
        mgr = SpontaneousCasterManager.for_sorcerer(level=1, cha_mod=3)
        assert mgr.slot_manager is not None
        assert mgr.spells_known is not None

    def test_charisma_bonus_slots(self):
        """Level 1 Sorcerer with CHA 16 (+3) gets bonus 1st-level slots.

        Base Sorcerer at level 1: 5 cantrips, 3 first-level.
        Bonus for level 1 with mod +3: 1 + (3-1)//4 = 1.
        Total first-level = 3 + 1 = 4.
        """
        mgr = SpontaneousCasterManager.for_sorcerer(level=1, cha_mod=3)
        assert mgr.slot_manager.max_slots[0] == 5  # Cantrips: no bonus
        assert mgr.slot_manager.max_slots[1] == 4  # 3 base + 1 CHA bonus

    def test_cast_known_spell(self):
        mgr = SpontaneousCasterManager.for_sorcerer(level=1, cha_mod=3)
        mgr.learn_spell("Magic Missile", 1)
        assert mgr.cast_spell("Magic Missile", 1) is True

    def test_cannot_cast_unknown_spell(self):
        """Sorcerer cannot cast a spell that is not in their known list."""
        mgr = SpontaneousCasterManager.for_sorcerer(level=1, cha_mod=3)
        assert mgr.cast_spell("Fireball", 3) is False

    def test_can_cast_checks_known_and_slots(self):
        mgr = SpontaneousCasterManager.for_sorcerer(level=1, cha_mod=3)
        mgr.learn_spell("Magic Missile", 1)
        assert mgr.can_cast("Magic Missile", 1) is True
        assert mgr.can_cast("Shield", 1) is False  # Not known

    def test_cast_any_known_spell_spontaneously(self):
        """Sorcerer can cast ANY known spell with available slots.

        Unlike Wizards who must prepare a specific spell into each slot,
        a Sorcerer can freely choose from their known list each time.
        """
        mgr = SpontaneousCasterManager.for_sorcerer(level=1, cha_mod=3)
        mgr.learn_spell("Magic Missile", 1)
        mgr.learn_spell("Shield", 1)

        # Can freely alternate between known spells
        assert mgr.cast_spell("Magic Missile", 1) is True
        assert mgr.cast_spell("Shield", 1) is True
        assert mgr.cast_spell("Magic Missile", 1) is True
        assert mgr.cast_spell("Shield", 1) is True

    def test_level_1_sorcerer_16cha_casts_4_times(self):
        """A Level 1 Sorcerer with 16 CHA can cast 1st-level spells 4x/day.

        3.5e SRD: Level 1 Sorcerer base = 3 first-level slots.
        CHA 16 gives +3 modifier. Bonus: 1 + (3-1)//4 = 1.
        Total = 3 + 1 = 4 casts per day at 1st level.
        """
        mgr = SpontaneousCasterManager.for_sorcerer(level=1, cha_mod=3)
        mgr.learn_spell("Magic Missile", 1)
        mgr.learn_spell("Shield", 1)

        # Cast 4 times - mixing known spells freely
        assert mgr.cast_spell("Magic Missile", 1) is True
        assert mgr.cast_spell("Shield", 1) is True
        assert mgr.cast_spell("Magic Missile", 1) is True
        assert mgr.cast_spell("Shield", 1) is True

        # 5th cast should fail - all slots expended
        assert mgr.cast_spell("Magic Missile", 1) is False
        assert mgr.available_slots(1) == 0

    def test_rest_restores_slots(self):
        mgr = SpontaneousCasterManager.for_sorcerer(level=1, cha_mod=3)
        mgr.learn_spell("Magic Missile", 1)
        # Expend all slots
        for _ in range(4):
            mgr.cast_spell("Magic Missile", 1)
        assert mgr.available_slots(1) == 0

        # Rest restores all
        mgr.rest()
        assert mgr.available_slots(1) == 4

    def test_available_slots(self):
        mgr = SpontaneousCasterManager.for_sorcerer(level=1, cha_mod=3)
        assert mgr.available_slots(1) == 4
        mgr.learn_spell("Magic Missile", 1)
        mgr.cast_spell("Magic Missile", 1)
        assert mgr.available_slots(1) == 3


# ---------------------------------------------------------------------------
# Character35e integration tests
# ---------------------------------------------------------------------------

class TestSorcererCharacterIntegration:
    """Tests for Character35e Sorcerer integration."""

    def test_sorcerer_is_caster(self):
        sorc = Character35e(name="Zara", char_class="Sorcerer", level=1, charisma=16)
        assert sorc.is_caster is True

    def test_sorcerer_char_id_unique(self):
        sorc1 = Character35e(name="Zara", char_class="Sorcerer", level=1)
        sorc2 = Character35e(name="Vex", char_class="Sorcerer", level=1)
        assert sorc1.char_id != sorc2.char_id

    def test_sorcerer_caster_level(self):
        sorc = Character35e(name="Zara", char_class="Sorcerer", level=5, charisma=16)
        assert sorc.caster_level == 5

    def test_sorcerer_initialize_spellcasting(self):
        """Sorcerer initialization creates spontaneous_caster and spells_known."""
        sorc = Character35e(
            name="Zara", char_class="Sorcerer", level=1, charisma=16,
        )
        sorc.initialize_spellcasting()
        assert sorc.spell_slot_manager is not None
        assert sorc.spells_known is not None
        assert sorc.spontaneous_caster is not None
        # Sorcerers do NOT use Spellbook (that's for Wizards)
        assert sorc.spellbook is None

    def test_sorcerer_16cha_level1_full_workflow(self):
        """Full workflow: Level 1 Sorcerer with 16 CHA casts known spells 4x.

        This is the primary verification scenario from the requirements.
        """
        sorc = Character35e(
            name="Zara",
            char_class="Sorcerer",
            level=1,
            charisma=16,
        )
        sorc.initialize_spellcasting()

        # Learn spells (Sorcerer knows 2 first-level spells at level 1)
        sorc.spontaneous_caster.learn_spell("Magic Missile", 1)
        sorc.spontaneous_caster.learn_spell("Shield", 1)

        # Verify: 4 slots available (3 base + 1 CHA bonus)
        assert sorc.spontaneous_caster.available_slots(1) == 4

        # Cast any known spell freely, 4 times total
        assert sorc.spontaneous_caster.cast_spell("Magic Missile", 1) is True
        assert sorc.spontaneous_caster.cast_spell("Shield", 1) is True
        assert sorc.spontaneous_caster.cast_spell("Magic Missile", 1) is True
        assert sorc.spontaneous_caster.cast_spell("Shield", 1) is True

        # 5th attempt fails - out of slots
        assert sorc.spontaneous_caster.cast_spell("Magic Missile", 1) is False

    def test_wizard_still_uses_spellbook(self):
        """Ensure Wizard initialization still creates a Spellbook, not
        a SpontaneousCasterManager."""
        wiz = Character35e(
            name="Gandalf", char_class="Wizard", level=1, intelligence=16,
        )
        wiz.initialize_spellcasting()
        assert wiz.spellbook is not None
        assert wiz.spells_known is None
        assert wiz.spontaneous_caster is None
