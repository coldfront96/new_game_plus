"""
tests/rules_engine/test_asf.py
-------------------------------
Unit tests for Arcane Spell Failure (ASF) mechanics (3.5e SRD).

Verifies:
- EquipmentManager.get_total_asf() sums ASF from equipped armor correctly.
- MagicSystem applies a d100 ASF check for arcane spells with somatic
  components.
- A Wizard wearing Full Plate (35% ASF) fails Magic Missile on a roll ≤ 35
  and succeeds on a roll > 35.
- Divine casters are not subject to ASF.
- Spells without a somatic component are never subject to ASF.
"""

from __future__ import annotations

import random
from unittest.mock import patch

import pytest

from src.ai_sim.systems import MagicSystem, SpellIntent
from src.core.event_bus import EventBus
from src.loot_math.item import Item, ItemType, Rarity
from src.rules_engine.character_35e import Character35e
from src.rules_engine.equipment import EquipmentManager, EquipmentSlot
from src.rules_engine.magic import (
    MAGIC_MISSILE,
    SpellComponent,
    SpellSchool,
    Spell,
    create_default_registry,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_full_plate() -> Item:
    """Create a Full Plate armor item with 35% ASF per 3.5e SRD."""
    return Item(
        name="Full Plate",
        item_type=ItemType.ARMOUR,
        rarity=Rarity.COMMON,
        base_armour=8,
        metadata={"asf_chance": 35},
    )


def _make_wizard(with_full_plate: bool = False) -> Character35e:
    """Build a level-1 Wizard, optionally wearing Full Plate."""
    wizard = Character35e(
        name="Gandalf",
        char_class="Wizard",
        level=1,
        intelligence=16,
    )
    wizard.initialize_spellcasting()

    if with_full_plate:
        em = EquipmentManager()
        em.equip_item(_make_full_plate(), EquipmentSlot.TORSO)
        wizard.equipment_manager = em

    return wizard


# ---------------------------------------------------------------------------
# EquipmentManager ASF tests
# ---------------------------------------------------------------------------

class TestGetTotalAsf:
    """Tests for EquipmentManager.get_total_asf()."""

    def test_no_armor_returns_zero(self):
        em = EquipmentManager()
        assert em.get_total_asf() == 0

    def test_full_plate_returns_35(self):
        em = EquipmentManager()
        em.equip_item(_make_full_plate(), EquipmentSlot.TORSO)
        assert em.get_total_asf() == 35

    def test_armor_without_asf_returns_zero(self):
        """Armor with no asf_chance metadata contributes 0."""
        em = EquipmentManager()
        leather = Item(
            name="Leather Armor",
            item_type=ItemType.ARMOUR,
            rarity=Rarity.COMMON,
            base_armour=2,
        )
        em.equip_item(leather, EquipmentSlot.TORSO)
        assert em.get_total_asf() == 0

    def test_armor_plus_shield_asf_stacks(self):
        """ASF from body armor and shield stack additively."""
        em = EquipmentManager()
        breastplate = Item(
            name="Breastplate",
            item_type=ItemType.ARMOUR,
            rarity=Rarity.COMMON,
            base_armour=5,
            metadata={"asf_chance": 25},
        )
        shield = Item(
            name="Heavy Steel Shield",
            item_type=ItemType.ARMOUR,
            rarity=Rarity.COMMON,
            base_armour=2,
            metadata={"asf_chance": 15},
        )
        em.equip_item(breastplate, EquipmentSlot.TORSO)
        em.equip_item(shield, EquipmentSlot.OFF_HAND)
        assert em.get_total_asf() == 40


# ---------------------------------------------------------------------------
# MagicSystem ASF integration tests
# ---------------------------------------------------------------------------

class TestMagicSystemAsf:
    """Tests for MagicSystem arcane spell failure logic."""

    def setup_method(self):
        self.bus = EventBus()
        self.registry = create_default_registry()
        self.system = MagicSystem(self.bus, self.registry)
        self.failures = []
        self.successes = []
        self.bus.subscribe("spell_failed", self.failures.append)
        self.bus.subscribe("spell_cast", self.successes.append)

    def test_wizard_no_armor_always_succeeds(self):
        """A Wizard in no armor has 0% ASF and always succeeds."""
        wizard = _make_wizard(with_full_plate=False)
        intent = SpellIntent(caster=wizard, spell_name="Magic Missile", spell_level=1)
        for _ in range(20):
            result = self.system.resolve(intent)
            assert result["success"] is True
            assert result["asf_roll"] is None

    def test_wizard_full_plate_fails_on_low_roll(self):
        """A Wizard in Full Plate (35% ASF) fails on a d100 roll ≤ 35."""
        wizard = _make_wizard(with_full_plate=True)
        intent = SpellIntent(caster=wizard, spell_name="Magic Missile", spell_level=1)

        with patch("src.ai_sim.systems.MagicSystem._roll_d100", return_value=35):
            result = self.system.resolve(intent)

        assert result["success"] is False
        assert result["asf_roll"] == 35
        assert result["asf_chance"] == 35
        assert result["effect"] is None

    def test_wizard_full_plate_succeeds_on_high_roll(self):
        """A Wizard in Full Plate (35% ASF) succeeds on a d100 roll > 35."""
        wizard = _make_wizard(with_full_plate=True)
        intent = SpellIntent(caster=wizard, spell_name="Magic Missile", spell_level=1)

        with patch("src.ai_sim.systems.MagicSystem._roll_d100", return_value=36):
            result = self.system.resolve(intent)

        assert result["success"] is True
        assert result["asf_roll"] == 36
        assert result["asf_chance"] == 35
        assert result["effect"] is not None

    def test_wizard_full_plate_35_percent_statistical(self):
        """Statistical test: ~35% of casts fail for a Wizard in Full Plate."""
        wizard = _make_wizard(with_full_plate=True)
        intent = SpellIntent(caster=wizard, spell_name="Magic Missile", spell_level=1)

        random.seed(42)
        n = 10_000
        failures = sum(
            1 for _ in range(n)
            if not self.system.resolve(intent)["success"]
        )
        failure_rate = failures / n
        # Expect close to 35% ± 2% tolerance
        assert 0.33 <= failure_rate <= 0.37, (
            f"Expected ~35% failure rate, got {failure_rate:.2%}"
        )

    def test_cleric_in_full_plate_no_asf(self):
        """Clerics are divine casters and are never subject to ASF."""
        cleric = Character35e(
            name="Brother Doom",
            char_class="Cleric",
            level=1,
            wisdom=14,
        )
        cleric.initialize_spellcasting()
        em = EquipmentManager()
        em.equip_item(_make_full_plate(), EquipmentSlot.TORSO)
        cleric.equipment_manager = em

        intent = SpellIntent(
            caster=cleric, spell_name="Cure Light Wounds", spell_level=1
        )
        for _ in range(20):
            result = self.system.resolve(intent)
            assert result["success"] is True
            assert result["asf_roll"] is None

    def test_spell_without_somatic_no_asf(self):
        """Spells without a somatic component are not subject to ASF."""
        verbal_only = Spell(
            name="Test Verbal Only",
            level=1,
            school=SpellSchool.EVOCATION,
            components=[SpellComponent.VERBAL],
        )
        self.registry.register(verbal_only)

        wizard = _make_wizard(with_full_plate=True)
        intent = SpellIntent(
            caster=wizard, spell_name="Test Verbal Only", spell_level=1
        )
        with patch("src.ai_sim.systems.MagicSystem._roll_d100", return_value=1):
            result = self.system.resolve(intent)

        assert result["success"] is True
        assert result["asf_roll"] is None

    def test_spell_failed_event_published_on_asf_failure(self):
        """A 'spell_failed' event is published when ASF causes failure."""
        wizard = _make_wizard(with_full_plate=True)
        intent = SpellIntent(caster=wizard, spell_name="Magic Missile", spell_level=1)

        with patch("src.ai_sim.systems.MagicSystem._roll_d100", return_value=1):
            self.system.resolve(intent)

        assert len(self.failures) == 1
        assert self.failures[0]["spell_name"] == "Magic Missile"

    def test_spell_cast_event_published_on_success(self):
        """A 'spell_cast' event is published when the spell succeeds."""
        wizard = _make_wizard(with_full_plate=False)
        intent = SpellIntent(caster=wizard, spell_name="Magic Missile", spell_level=1)
        self.system.resolve(intent)
        assert len(self.successes) == 1
        assert self.successes[0]["spell_name"] == "Magic Missile"

    def test_update_drains_pending_queue(self):
        """update() processes all queued SpellIntents."""
        wizard = _make_wizard(with_full_plate=False)
        for _ in range(3):
            self.bus.publish(
                "spell_intent",
                SpellIntent(caster=wizard, spell_name="Magic Missile", spell_level=1),
            )
        assert self.system.pending_count == 3
        self.system.update()
        assert self.system.pending_count == 0
