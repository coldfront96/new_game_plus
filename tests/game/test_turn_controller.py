"""Tests for ``src.game.turn_controller`` (Task 4)."""

from __future__ import annotations

import random

import pytest

from src.core.event_bus import EventBus
from src.game.turn_controller import (
    TurnController,
    roll_initiative,
)
from src.rules_engine.actions import ActionTracker, ActionType
from src.rules_engine.character_35e import Character35e
from src.rules_engine.conditions import ConditionManager, create_stunned


def _make(name: str, dex: int = 12, level: int = 1) -> Character35e:
    return Character35e(
        name=name,
        char_class="Fighter",
        level=level,
        dexterity=dex,
        constitution=14,
    )


def test_roll_initiative_sorts_high_to_low():
    rng = random.Random(11)
    combatants = [_make("A", 10), _make("B", 18), _make("C", 14)]
    entries = roll_initiative(combatants, rng=rng)
    # Highest initiative first.
    totals = [e.initiative for e in entries]
    assert totals == sorted(totals, reverse=True)


def test_turn_controller_builds_trackers_for_every_combatant():
    combatants = [_make("A"), _make("B"), _make("C")]
    controller = TurnController.from_combatants(
        combatants, rng=random.Random(0),
    )
    for c in combatants:
        tracker = controller.tracker_for(c)
        assert isinstance(tracker, ActionTracker)
        assert not tracker.standard_used


def test_action_trackers_reset_each_turn():
    combatants = [_make("A"), _make("B")]
    controller = TurnController.from_combatants(
        combatants, rng=random.Random(1),
    )

    calls = {}

    def action(combatant, tracker):
        # Every turn should start fresh.
        assert not tracker.standard_used
        assert not tracker.move_used
        tracker.consume_action(ActionType.STANDARD)
        calls[combatant.name] = calls.get(combatant.name, 0) + 1
        return False

    controller.run_round(action)
    controller.run_round(action)
    for c in combatants:
        assert calls[c.name] == 2


def test_round_counter_increments_and_publishes_events():
    combatants = [_make("A")]
    bus = EventBus()
    received = []
    bus.subscribe("round_started", lambda p: received.append(p["round"]))
    bus.subscribe("round_ended", lambda p: received.append(f"end_{p['round']}"))

    controller = TurnController.from_combatants(
        combatants, rng=random.Random(0), event_bus=bus,
    )
    controller.run_round(lambda c, t: False)
    controller.run_round(lambda c, t: False)

    assert controller.round_counter == 2
    assert received == [1, "end_1", 2, "end_2"]


def test_cannot_act_skips_stunned_combatant():
    combatants = [_make("A"), _make("B")]
    cm = ConditionManager()
    cm.apply_condition(combatants[0], create_stunned(duration=5))
    controller = TurnController.from_combatants(
        combatants, rng=random.Random(2), condition_manager=cm,
    )
    callers = []

    def action(c, t):
        callers.append(c.name)
        return False

    controller.run_round(action)
    # Only B should have acted.
    assert "A" not in callers
    assert "B" in callers


def test_condition_duration_ticks_at_end_of_round():
    char = _make("A")
    cm = ConditionManager()
    cm.apply_condition(char, create_stunned(duration=2))
    controller = TurnController.from_combatants(
        [char], rng=random.Random(3), condition_manager=cm,
    )
    assert cm.has_condition(char, "Stunned")
    controller.run_round(lambda c, t: False)     # duration 2 → 1
    assert cm.has_condition(char, "Stunned")
    controller.run_round(lambda c, t: False)     # duration 1 → expires
    assert not cm.has_condition(char, "Stunned")


def test_full_round_action_exhausts_both_slots():
    char = _make("A")
    controller = TurnController.from_combatants(
        [char], rng=random.Random(4),
    )

    def action(c, t):
        t.consume_action(ActionType.FULL_ROUND)
        assert t.standard_used and t.move_used
        with pytest.raises(ValueError):
            t.consume_action(ActionType.STANDARD)
        return False

    controller.run_round(action)
