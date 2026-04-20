"""
tests/rules_engine/test_conditions.py
--------------------------------------
Unit tests for the D&D 3.5e Condition Tracking System.

Verifies that conditions correctly modify character stats, particularly
that a Blinded character loses their Dexterity bonus to AC.
"""

from unittest.mock import patch

import pytest

from src.core.event_bus import EventBus
from src.rules_engine.character_35e import Character35e, Size
from src.rules_engine.conditions import (
    Condition,
    ConditionManager,
    create_blinded,
    create_prone,
    create_stunned,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def manager(event_bus):
    return ConditionManager(event_bus=event_bus)


@pytest.fixture
def fighter():
    """A fighter with high DEX (modifier +2) to verify Dex-to-AC loss."""
    return Character35e(
        name="Aldric",
        char_class="Fighter",
        level=5,
        strength=16,
        dexterity=14,  # +2 DEX mod
        constitution=14,
    )


@pytest.fixture
def rogue():
    """A rogue with high DEX for testing loss of Dex bonus."""
    return Character35e(
        name="Sneaky",
        char_class="Rogue",
        level=3,
        strength=10,
        dexterity=18,  # +4 DEX mod
        constitution=12,
    )


# ---------------------------------------------------------------------------
# Condition dataclass tests
# ---------------------------------------------------------------------------

class TestConditionDataclass:
    def test_slots_enabled(self):
        assert hasattr(Condition, "__slots__")

    def test_condition_fields(self):
        cond = Condition(
            name="Test",
            duration=5,
            stat_modifiers={"ac": -2},
            lose_dex_to_ac=True,
            cannot_act=False,
        )
        assert cond.name == "Test"
        assert cond.duration == 5
        assert cond.stat_modifiers == {"ac": -2}
        assert cond.lose_dex_to_ac is True
        assert cond.cannot_act is False

    def test_default_duration_is_permanent(self):
        cond = Condition(name="Permanent")
        assert cond.duration == -1


# ---------------------------------------------------------------------------
# Blinded condition tests
# ---------------------------------------------------------------------------

class TestBlindedCondition:
    def test_blinded_loses_dex_to_ac(self, manager, fighter):
        """Core verification: Blinded character loses Dexterity bonus to AC."""
        normal_ac = fighter.armor_class  # 10 + DEX(+2) + size(0) = 12
        blinded = create_blinded(duration=3)
        manager.apply_condition(fighter, blinded)

        effective_ac = manager.get_effective_ac(fighter)
        # Should be flat-footed (no DEX) + condition AC modifier (-2)
        # flat_footed = 10 + size(0) = 10
        # effective = 10 + (-2) = 8
        expected_ac = fighter.flat_footed_ac + (-2)
        assert effective_ac == expected_ac
        assert effective_ac < normal_ac

    def test_blinded_ac_lower_than_normal(self, manager, rogue):
        """Blinded rogue with high DEX loses significant AC."""
        normal_ac = rogue.armor_class  # 10 + DEX(+4) + size(0) = 14
        blinded = create_blinded(duration=5)
        manager.apply_condition(rogue, blinded)

        effective_ac = manager.get_effective_ac(rogue)
        # flat_footed = 10, with -2 from blinded = 8
        assert effective_ac == 8
        assert effective_ac < normal_ac

    def test_blinded_melee_attack_penalty(self, manager, fighter):
        """Blinded character takes -2 to melee attacks."""
        blinded = create_blinded(duration=3)
        manager.apply_condition(fighter, blinded)

        modifier = manager.get_melee_attack_modifier(fighter)
        assert modifier == -2

    def test_blinded_does_not_prevent_actions(self, manager, fighter):
        """Blinded does not prevent acting (unlike Stunned)."""
        blinded = create_blinded(duration=3)
        manager.apply_condition(fighter, blinded)
        assert manager.cannot_act(fighter) is False


# ---------------------------------------------------------------------------
# Stunned condition tests
# ---------------------------------------------------------------------------

class TestStunnedCondition:
    def test_stunned_loses_dex_to_ac(self, manager, fighter):
        """Stunned character loses Dex bonus to AC."""
        stunned = create_stunned(duration=1)
        manager.apply_condition(fighter, stunned)
        assert manager.loses_dex_to_ac(fighter) is True

    def test_stunned_ac_penalty(self, manager, fighter):
        """Stunned applies -2 AC penalty."""
        stunned = create_stunned(duration=1)
        manager.apply_condition(fighter, stunned)
        ac_mod = manager.get_ac_modifier(fighter)
        assert ac_mod == -2

    def test_stunned_prevents_actions(self, manager, fighter):
        """Stunned character cannot act."""
        stunned = create_stunned(duration=2)
        manager.apply_condition(fighter, stunned)
        assert manager.cannot_act(fighter) is True

    def test_stunned_effective_ac(self, manager, rogue):
        """Stunned rogue: flat-footed AC minus 2."""
        stunned = create_stunned(duration=1)
        manager.apply_condition(rogue, stunned)
        effective_ac = manager.get_effective_ac(rogue)
        # flat_footed = 10, with -2 = 8
        assert effective_ac == 8


# ---------------------------------------------------------------------------
# Prone condition tests
# ---------------------------------------------------------------------------

class TestProneCondition:
    def test_prone_melee_attack_penalty(self, manager, fighter):
        """Prone gives -4 to melee attack rolls."""
        prone = create_prone(duration=2)
        manager.apply_condition(fighter, prone)
        modifier = manager.get_melee_attack_modifier(fighter)
        assert modifier == -4

    def test_prone_does_not_lose_dex(self, manager, fighter):
        """Prone does NOT cause loss of Dex bonus to AC."""
        prone = create_prone(duration=2)
        manager.apply_condition(fighter, prone)
        assert manager.loses_dex_to_ac(fighter) is False

    def test_prone_ac_vs_melee_penalty(self, manager, fighter):
        """Prone gives -4 AC vs melee (stored as stat modifier)."""
        prone = create_prone(duration=2)
        manager.apply_condition(fighter, prone)
        conditions = manager.get_conditions(fighter)
        assert len(conditions) == 1
        assert conditions[0].stat_modifiers.get("ac_vs_melee") == -4

    def test_prone_ac_vs_ranged_bonus(self, manager, fighter):
        """Prone gives +4 AC vs ranged (stored as stat modifier)."""
        prone = create_prone(duration=2)
        manager.apply_condition(fighter, prone)
        conditions = manager.get_conditions(fighter)
        assert conditions[0].stat_modifiers.get("ac_vs_ranged") == 4


# ---------------------------------------------------------------------------
# ConditionManager lifecycle tests
# ---------------------------------------------------------------------------

class TestConditionManager:
    def test_apply_and_query(self, manager, fighter):
        """Can apply and query conditions."""
        blinded = create_blinded(duration=3)
        manager.apply_condition(fighter, blinded)
        assert manager.has_condition(fighter, "Blinded") is True
        assert manager.has_condition(fighter, "Stunned") is False

    def test_remove_condition(self, manager, fighter):
        """Can remove a condition by name."""
        blinded = create_blinded(duration=3)
        manager.apply_condition(fighter, blinded)
        assert manager.remove_condition(fighter, "Blinded") is True
        assert manager.has_condition(fighter, "Blinded") is False

    def test_remove_nonexistent_returns_false(self, manager, fighter):
        """Removing a condition that isn't active returns False."""
        assert manager.remove_condition(fighter, "Blinded") is False

    def test_conditions_do_not_stack(self, manager, fighter):
        """Applying the same condition replaces, not stacks."""
        blind1 = create_blinded(duration=3)
        blind2 = create_blinded(duration=5)
        manager.apply_condition(fighter, blind1)
        manager.apply_condition(fighter, blind2)
        conditions = manager.get_conditions(fighter)
        assert len(conditions) == 1
        assert conditions[0].duration == 5

    def test_tick_decrements_duration(self, manager, fighter):
        """Tick decrements condition duration."""
        blinded = create_blinded(duration=3)
        manager.apply_condition(fighter, blinded)
        manager.tick()
        conditions = manager.get_conditions(fighter)
        assert conditions[0].duration == 2

    def test_tick_expires_condition(self, manager, fighter):
        """Condition expires when duration reaches 0."""
        blinded = create_blinded(duration=1)
        manager.apply_condition(fighter, blinded)
        expired = manager.tick()
        assert len(expired) == 1
        assert expired[0]["condition"] == "Blinded"
        assert manager.has_condition(fighter, "Blinded") is False

    def test_permanent_condition_never_expires(self, manager, fighter):
        """Permanent conditions (duration=-1) don't expire on tick."""
        blinded = create_blinded(duration=-1)
        manager.apply_condition(fighter, blinded)
        for _ in range(100):
            manager.tick()
        assert manager.has_condition(fighter, "Blinded") is True

    def test_event_published_on_apply(self, event_bus, manager, fighter):
        """condition_applied event is published when condition is applied."""
        received = []
        event_bus.subscribe("condition_applied", lambda p: received.append(p))
        blinded = create_blinded(duration=3)
        manager.apply_condition(fighter, blinded)
        assert len(received) == 1
        assert received[0]["condition"] == "Blinded"

    def test_event_published_on_expire(self, event_bus, manager, fighter):
        """condition_expired event is published when condition expires."""
        received = []
        event_bus.subscribe("condition_expired", lambda p: received.append(p))
        blinded = create_blinded(duration=1)
        manager.apply_condition(fighter, blinded)
        manager.tick()
        assert len(received) == 1
        assert received[0]["condition"] == "Blinded"

    def test_multiple_conditions_on_same_character(self, manager, fighter):
        """Multiple different conditions can be active simultaneously."""
        blinded = create_blinded(duration=3)
        prone = create_prone(duration=2)
        manager.apply_condition(fighter, blinded)
        manager.apply_condition(fighter, prone)
        conditions = manager.get_conditions(fighter)
        assert len(conditions) == 2
        names = {c.name for c in conditions}
        assert names == {"Blinded", "Prone"}

    def test_stacked_ac_modifiers(self, manager, fighter):
        """Multiple conditions combine their AC modifiers."""
        blinded = create_blinded(duration=3)
        stunned = create_stunned(duration=2)
        manager.apply_condition(fighter, blinded)
        manager.apply_condition(fighter, stunned)
        # Both apply -2 AC → total -4
        assert manager.get_ac_modifier(fighter) == -4
