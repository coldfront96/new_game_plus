"""
tests/rules_engine/test_cleric.py
----------------------------------
Unit tests for D&D 3.5e Cleric divine spellcasting and spontaneous casting.

Verifies:
- Divine spell definitions (Cure Light Wounds, Bless, Bane).
- DivineCasterManager creation and Wisdom-based bonus slots.
- Spontaneous Cure conversion (swap prepared non-domain spell for Cure).
- Alignment restrictions on spontaneous casting.
- Character35e integration with divine spellcasting.
"""

import pytest

from src.rules_engine.magic import (
    BANE,
    BLESS,
    CURE_LIGHT_WOUNDS,
    CURE_SPELLS,
    SUMMON_NATURES_ALLY_SPELLS,
    Spell,
    SpellComponent,
    SpellSchool,
    create_default_registry,
)
from src.rules_engine.spellcasting import (
    DivineCasterManager,
    SpellSlotManager,
    Spellbook,
)
from src.rules_engine.character_35e import Character35e


# ---------------------------------------------------------------------------
# Divine spell definition tests
# ---------------------------------------------------------------------------

class TestDivineSpellDefinitions:
    """Verify the canonical SRD attributes of divine spells."""

    def test_cure_light_wounds_attributes(self):
        assert CURE_LIGHT_WOUNDS.name == "Cure Light Wounds"
        assert CURE_LIGHT_WOUNDS.level == 1
        assert CURE_LIGHT_WOUNDS.school == SpellSchool.CONJURATION
        assert CURE_LIGHT_WOUNDS.subschool == "Healing"
        assert SpellComponent.VERBAL in CURE_LIGHT_WOUNDS.components
        assert SpellComponent.SOMATIC in CURE_LIGHT_WOUNDS.components
        assert CURE_LIGHT_WOUNDS.range == "Touch"
        assert CURE_LIGHT_WOUNDS.duration == "Instantaneous"

    def test_cure_light_wounds_effect(self):
        result = CURE_LIGHT_WOUNDS.effect_callback(None, None, 3)
        assert result["healing"] == "1d8+3"
        assert result["max_bonus"] == 3
        assert result["harms_undead"] is True
        assert result["energy_type"] == "positive"

    def test_cure_light_wounds_caps_at_5(self):
        result = CURE_LIGHT_WOUNDS.effect_callback(None, None, 10)
        assert result["max_bonus"] == 5
        assert result["healing"] == "1d8+5"

    def test_bless_attributes(self):
        assert BLESS.name == "Bless"
        assert BLESS.level == 1
        assert BLESS.school == SpellSchool.ENCHANTMENT
        assert BLESS.subschool == "Compulsion"
        assert "Mind-Affecting" in BLESS.descriptor
        assert SpellComponent.DIVINE_FOCUS in BLESS.components

    def test_bless_effect(self):
        result = BLESS.effect_callback(None, None, 5)
        assert result["attack_bonus"] == 1
        assert result["bonus_type"] == "morale"
        assert result["duration_minutes"] == 5

    def test_bane_attributes(self):
        assert BANE.name == "Bane"
        assert BANE.level == 1
        assert BANE.school == SpellSchool.ENCHANTMENT
        assert BANE.subschool == "Compulsion"
        assert "Fear" in BANE.descriptor
        assert "Mind-Affecting" in BANE.descriptor
        assert SpellComponent.DIVINE_FOCUS in BANE.components

    def test_bane_effect(self):
        result = BANE.effect_callback(None, None, 3)
        assert result["attack_penalty"] == -1
        assert result["penalty_type"] == "morale"
        assert result["duration_minutes"] == 3

    def test_divine_spells_use_slots(self):
        """Verify all divine spells use __slots__ for memory efficiency."""
        assert hasattr(Spell, "__slots__")

    def test_divine_spells_in_default_registry(self):
        registry = create_default_registry()
        assert registry.get("Cure Light Wounds") is CURE_LIGHT_WOUNDS
        assert registry.get("Bless") is BLESS
        assert registry.get("Bane") is BANE


# ---------------------------------------------------------------------------
# DivineCasterManager tests
# ---------------------------------------------------------------------------

class TestDivineCasterManager:
    """Tests for the DivineCasterManager class."""

    def test_slots_true_attribute(self):
        """Verify DivineCasterManager uses __slots__."""
        assert hasattr(DivineCasterManager, "__slots__")

    def test_for_cleric_creates_manager(self):
        mgr = DivineCasterManager.for_cleric(level=1, wis_mod=2)
        assert mgr.slot_manager is not None
        assert mgr.spellbook is not None
        assert mgr.alignment == "good"

    def test_for_cleric_wisdom_bonus_slots(self):
        """Level 1 Cleric with WIS 14 (+2) gets bonus 1st-level slots.

        Base Cleric at level 1: 3 cantrips, 1 first-level.
        Bonus for level 1 with mod +2: 1 + (2-1)//4 = 1.
        Total first-level = 1 + 1 = 2.
        """
        mgr = DivineCasterManager.for_cleric(level=1, wis_mod=2)
        assert mgr.slot_manager.max_slots[0] == 3  # Cantrips: no bonus
        assert mgr.slot_manager.max_slots[1] == 2  # 1 base + 1 bonus

    def test_for_cleric_high_wisdom(self):
        """Level 1 Cleric with WIS 18 (+4) gets more bonus slots.

        Bonus for level 1 with mod +4: 1 + (4-1)//4 = 1.
        Total = 1 + 1 = 2.
        """
        mgr = DivineCasterManager.for_cleric(level=1, wis_mod=4)
        assert mgr.slot_manager.max_slots[1] == 2  # 1 base + 1 bonus

    def test_for_druid_creates_manager(self):
        mgr = DivineCasterManager.for_druid(level=1, wis_mod=3)
        assert mgr.alignment == "neutral"
        assert mgr.slot_manager is not None

    def test_can_spontaneous_cure_good(self):
        mgr = DivineCasterManager.for_cleric(level=1, wis_mod=2, alignment="good")
        assert mgr.can_spontaneous_cure() is True

    def test_can_spontaneous_cure_neutral(self):
        mgr = DivineCasterManager.for_cleric(level=1, wis_mod=2, alignment="neutral")
        assert mgr.can_spontaneous_cure() is True

    def test_cannot_spontaneous_cure_evil(self):
        mgr = DivineCasterManager.for_cleric(level=1, wis_mod=2, alignment="evil")
        assert mgr.can_spontaneous_cure() is False

    def test_prepare_spell(self):
        mgr = DivineCasterManager.for_cleric(level=1, wis_mod=2)
        assert mgr.prepare_spell("Bane", 1) is True
        assert "Bane" in mgr.spellbook.get_prepared(1)

    def test_cast_spell(self):
        mgr = DivineCasterManager.for_cleric(level=1, wis_mod=2)
        mgr.prepare_spell("Bless", 1)
        assert mgr.cast_spell("Bless", 1) is True
        assert "Bless" not in mgr.spellbook.get_prepared(1)

    def test_cast_spell_fails_if_not_prepared(self):
        mgr = DivineCasterManager.for_cleric(level=1, wis_mod=2)
        assert mgr.cast_spell("Bless", 1) is False

    def test_rest_restores_slots(self):
        mgr = DivineCasterManager.for_cleric(level=1, wis_mod=2)
        mgr.prepare_spell("Bane", 1)
        mgr.cast_spell("Bane", 1)
        mgr.rest()
        assert mgr.slot_manager.available(1) == 2  # fully restored
        assert mgr.spellbook.get_prepared(1) == []  # cleared


# ---------------------------------------------------------------------------
# Spontaneous Casting (convert_to_cure) tests
# ---------------------------------------------------------------------------

class TestSpontaneousCasting:
    """Core test: Level 1 Cleric spontaneously converts Bane → Cure Light Wounds."""

    def test_convert_bane_to_cure_light_wounds(self):
        """A Level 1 Good Cleric prepares Bane and swaps it for Cure Light Wounds.

        This is the primary verification required by the problem statement.
        """
        mgr = DivineCasterManager.for_cleric(level=1, wis_mod=2, alignment="good")
        mgr.prepare_spell("Bane", 1)

        cure_name = mgr.convert_to_cure("Bane")

        assert cure_name == "Cure Light Wounds"
        # Bane should no longer be prepared
        assert "Bane" not in mgr.spellbook.get_prepared(1)
        # A slot should have been consumed
        assert mgr.slot_manager.available(1) == 1  # Was 2, now 1

    def test_convert_bless_to_cure_light_wounds(self):
        """Any non-domain spell can be converted."""
        mgr = DivineCasterManager.for_cleric(level=1, wis_mod=2, alignment="good")
        mgr.prepare_spell("Bless", 1)

        cure_name = mgr.convert_to_cure("Bless")
        assert cure_name == "Cure Light Wounds"

    def test_convert_fails_for_evil_cleric(self):
        """Evil Clerics cannot spontaneously cast Cure spells."""
        mgr = DivineCasterManager.for_cleric(level=1, wis_mod=2, alignment="evil")
        mgr.prepare_spell("Bane", 1)

        result = mgr.convert_to_cure("Bane")
        assert result is None
        # Bane should still be prepared (not consumed)
        assert "Bane" in mgr.spellbook.get_prepared(1)

    def test_convert_fails_for_domain_spell(self):
        """Domain spells cannot be spontaneously converted."""
        mgr = DivineCasterManager.for_cleric(level=1, wis_mod=2, alignment="good")
        mgr.domain_spells.add("Bane")
        mgr.prepare_spell("Bane", 1)

        result = mgr.convert_to_cure("Bane")
        assert result is None

    def test_convert_fails_if_not_prepared(self):
        """Cannot convert a spell that is not prepared."""
        mgr = DivineCasterManager.for_cleric(level=1, wis_mod=2, alignment="good")

        result = mgr.convert_to_cure("Bane")
        assert result is None

    def test_convert_fails_if_no_slots_available(self):
        """Cannot convert if all slots are already expended."""
        mgr = DivineCasterManager.for_cleric(level=1, wis_mod=2, alignment="good")
        mgr.prepare_spell("Bane", 1)
        mgr.prepare_spell("Bless", 1)

        # Expend all 1st-level slots
        for _ in range(mgr.slot_manager.max_slots[1]):
            mgr.slot_manager.expend(1)

        result = mgr.convert_to_cure("Bane")
        assert result is None

    def test_convert_cantrip_fails(self):
        """Cantrips (level 0) cannot be spontaneously converted."""
        mgr = DivineCasterManager.for_cleric(level=1, wis_mod=2, alignment="good")
        # Prepare a cantrip
        mgr.prepare_spell("Create Water", 0)

        result = mgr.convert_to_cure("Create Water")
        assert result is None

    def test_cure_spells_table_completeness(self):
        """Verify CURE_SPELLS has entries for levels 1–9."""
        for level in range(1, 10):
            assert level in CURE_SPELLS
            assert isinstance(CURE_SPELLS[level], str)


# ---------------------------------------------------------------------------
# Druid spontaneous Summon Nature's Ally conversion (spellcasting.py 747–774)
# ---------------------------------------------------------------------------

class TestDruidSpontaneousSummonConversion:
    """Druids can spontaneously sacrifice a prepared non-domain spell to cast
    a Summon Nature's Ally spell of the same level (3.5e SRD p.35)."""

    def test_can_spontaneous_summon_is_true_for_druid(self):
        mgr = DivineCasterManager.for_druid(level=5, wis_mod=3)
        assert mgr.can_spontaneous_summon() is True

    def test_can_spontaneous_summon_is_false_for_cleric(self):
        mgr = DivineCasterManager.for_cleric(level=5, wis_mod=3, alignment="good")
        assert mgr.can_spontaneous_summon() is False

    def test_druid_converts_prepared_spell_to_summon_i(self):
        """A Level 1 Druid sacrificing a prepared 1st-level non-domain spell
        receives Summon Nature's Ally I and consumes a slot."""
        mgr = DivineCasterManager.for_druid(level=1, wis_mod=2)
        mgr.prepare_spell("Entangle", 1)

        initial_slots = mgr.slot_manager.available(1)
        summon_name = mgr.convert_to_summon_natures_ally("Entangle")

        assert summon_name == "Summon Nature's Ally I"
        assert "Entangle" not in mgr.spellbook.get_prepared(1)
        assert mgr.slot_manager.available(1) == initial_slots - 1

    def test_druid_converts_level_3_spell_to_summon_iii(self):
        """A higher-level Druid sacrificing a 3rd-level spell gets
        Summon Nature's Ally III."""
        mgr = DivineCasterManager.for_druid(level=5, wis_mod=3)
        mgr.prepare_spell("Call Lightning", 3)

        summon_name = mgr.convert_to_summon_natures_ally("Call Lightning")

        assert summon_name == "Summon Nature's Ally III"
        assert "Call Lightning" not in mgr.spellbook.get_prepared(3)

    def test_cleric_cannot_spontaneously_summon(self):
        """A Cleric (not a Druid) cannot convert to Summon Nature's Ally."""
        mgr = DivineCasterManager.for_cleric(level=5, wis_mod=3, alignment="good")
        mgr.prepare_spell("Bane", 1)

        result = mgr.convert_to_summon_natures_ally("Bane")
        assert result is None
        # Spell remains prepared — nothing was consumed.
        assert "Bane" in mgr.spellbook.get_prepared(1)

    def test_druid_cannot_convert_domain_spell(self):
        """Domain spells are excluded from spontaneous conversion."""
        mgr = DivineCasterManager.for_druid(level=3, wis_mod=2)
        mgr.domain_spells.add("Flame Strike")
        mgr.prepare_spell("Flame Strike", 5)

        result = mgr.convert_to_summon_natures_ally("Flame Strike")

        assert result is None
        assert "Flame Strike" in mgr.spellbook.get_prepared(5)

    def test_druid_cannot_convert_spell_not_prepared(self):
        """If the named spell isn't prepared at any level, conversion fails."""
        mgr = DivineCasterManager.for_druid(level=3, wis_mod=2)

        result = mgr.convert_to_summon_natures_ally("Entangle")
        assert result is None

    def test_druid_cannot_convert_when_no_slot_available(self):
        """If the slot of that spell's level is fully expended, conversion fails."""
        mgr = DivineCasterManager.for_druid(level=1, wis_mod=2)
        mgr.prepare_spell("Entangle", 1)

        # Expend every 1st-level slot
        for _ in range(mgr.slot_manager.max_slots[1]):
            mgr.slot_manager.expend(1)

        result = mgr.convert_to_summon_natures_ally("Entangle")
        assert result is None
        # Spell remains prepared — nothing was consumed.
        assert "Entangle" in mgr.spellbook.get_prepared(1)

    def test_druid_cannot_convert_cantrip(self):
        """Cantrips (level 0) cannot be spontaneously converted: level 0
        is not in range(1, 10), so the search finds no matching level."""
        mgr = DivineCasterManager.for_druid(level=1, wis_mod=2)
        mgr.prepare_spell("Create Water", 0)

        result = mgr.convert_to_summon_natures_ally("Create Water")
        assert result is None

    def test_summon_natures_ally_spells_table_completeness(self):
        """Table must contain entries for spell levels 1–9."""
        for level in range(1, 10):
            assert level in SUMMON_NATURES_ALLY_SPELLS
            assert SUMMON_NATURES_ALLY_SPELLS[level].startswith("Summon Nature's Ally")

    def test_multiple_conversions_consume_distinct_slots(self):
        """Each conversion consumes one slot at that level."""
        mgr = DivineCasterManager.for_druid(level=3, wis_mod=4)  # more slots
        mgr.prepare_spell("Entangle", 1)
        mgr.prepare_spell("Faerie Fire", 1)

        start = mgr.slot_manager.available(1)
        mgr.convert_to_summon_natures_ally("Entangle")
        mgr.convert_to_summon_natures_ally("Faerie Fire")

        assert mgr.slot_manager.available(1) == start - 2
        assert mgr.spellbook.get_prepared(1) == []


# ---------------------------------------------------------------------------
# Character35e divine caster integration tests
# ---------------------------------------------------------------------------

class TestCharacter35eClericIntegration:
    """Integration tests for Cleric character creation and spellcasting."""

    def test_cleric_is_caster(self):
        cleric = Character35e(name="Jozan", char_class="Cleric", level=1)
        assert cleric.is_caster is True

    def test_cleric_caster_level(self):
        cleric = Character35e(name="Jozan", char_class="Cleric", level=5)
        assert cleric.caster_level == 5

    def test_cleric_initialize_spellcasting_uses_wisdom(self):
        """Cleric spell slots should be based on Wisdom."""
        cleric = Character35e(
            name="Jozan",
            char_class="Cleric",
            level=1,
            wisdom=16,  # +3 mod
        )
        cleric.initialize_spellcasting()

        assert cleric.spell_slot_manager is not None
        # Base: 3 cantrips, 1 first-level
        # Bonus for level 1 with WIS mod +3: 1 + (3-1)//4 = 1
        # Total first-level = 1 + 1 = 2
        assert cleric.spell_slot_manager.max_slots[0] == 3
        assert cleric.spell_slot_manager.max_slots[1] == 2

    def test_cleric_armor_class_with_deflection_bonus(self):
        """AC should include deflection bonus from divine spells (e.g. Shield of Faith)."""
        cleric = Character35e(
            name="Jozan",
            char_class="Cleric",
            level=1,
            dexterity=10,
        )
        # Base AC = 10 + 0 (DEX) + 0 (size) = 10
        assert cleric.armor_class == 10

        # Apply Shield of Faith (+2 deflection)
        cleric.metadata["deflection_bonus"] = 2
        assert cleric.armor_class == 12

    def test_full_cleric_spontaneous_casting_workflow(self):
        """End-to-end: Create a Level 1 Good Cleric, prepare Bane, convert to CLW.

        This test validates the full workflow described in the problem statement.
        """
        # Create a Level 1 Cleric with WIS 14 (+2 mod)
        cleric = Character35e(
            name="Jozan",
            char_class="Cleric",
            level=1,
            wisdom=14,
        )
        cleric.initialize_spellcasting()

        # Set up divine caster manager
        wis_mod = cleric.wisdom_mod  # +2
        mgr = DivineCasterManager.for_cleric(
            level=cleric.level,
            wis_mod=wis_mod,
            alignment="good",
        )

        # Prepare Bane (a 1st-level Enchantment spell)
        mgr.prepare_spell("Bane", 1)
        assert "Bane" in mgr.spellbook.get_prepared(1)

        # Spontaneously convert Bane → Cure Light Wounds
        cure_name = mgr.convert_to_cure("Bane")

        assert cure_name == "Cure Light Wounds"
        assert "Bane" not in mgr.spellbook.get_prepared(1)
