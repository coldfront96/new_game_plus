"""
tests/rules_engine/test_action_economy.py
------------------------------------------
Unit tests for the 3.5e action economy:
  * ActionType enum
  * ActionTracker (slots, reset_turn, consume_action, has_action)
  * TurnManagerSystem (initiative roll, queue order, turn advancement,
    aggro detection)
  * CombatSystem action-gate (STANDARD action consumed on attack; second
    attack in same turn is silently dropped)
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.ai_sim.components import Position
from src.ai_sim.entity import Entity
from src.ai_sim.systems import AttackIntent, CombatSystem, TurnManagerSystem
from src.core.event_bus import EventBus
from src.rules_engine.actions import ActionTracker, ActionType
from src.rules_engine.character_35e import Character35e


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fighter(name: str = "Fighter", dexterity: int = 10) -> Character35e:
    return Character35e(
        name=name,
        char_class="Fighter",
        level=3,
        strength=14,
        dexterity=dexterity,
        constitution=12,
    )


def _make_entity(name: str, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> Entity:
    e = Entity(name=name)
    e.add_component(Position(x=x, y=y, z=z))
    return e


# ---------------------------------------------------------------------------
# ActionType enum
# ---------------------------------------------------------------------------

class TestActionType:
    def test_all_members_present(self):
        names = {m.name for m in ActionType}
        assert names == {"STANDARD", "MOVE", "SWIFT", "FREE", "FULL_ROUND"}

    def test_enum_values_unique(self):
        values = [m.value for m in ActionType]
        assert len(values) == len(set(values))


# ---------------------------------------------------------------------------
# ActionTracker – dataclass slots
# ---------------------------------------------------------------------------

class TestActionTrackerSlots:
    def test_slots_enabled(self):
        assert hasattr(ActionTracker, "__slots__")

    def test_default_all_unused(self):
        tracker = ActionTracker()
        assert tracker.standard_used is False
        assert tracker.move_used is False
        assert tracker.swift_used is False


# ---------------------------------------------------------------------------
# ActionTracker – reset_turn
# ---------------------------------------------------------------------------

class TestActionTrackerResetTurn:
    def test_reset_clears_all_used_flags(self):
        tracker = ActionTracker(
            standard_used=True, move_used=True, swift_used=True
        )
        tracker.reset_turn()
        assert tracker.standard_used is False
        assert tracker.move_used is False
        assert tracker.swift_used is False

    def test_reset_on_fresh_tracker_is_idempotent(self):
        tracker = ActionTracker()
        tracker.reset_turn()
        assert not tracker.standard_used
        assert not tracker.move_used
        assert not tracker.swift_used


# ---------------------------------------------------------------------------
# ActionTracker – consume_action: STANDARD
# ---------------------------------------------------------------------------

class TestConsumeStandard:
    def test_first_standard_succeeds(self):
        tracker = ActionTracker()
        tracker.consume_action(ActionType.STANDARD)
        assert tracker.standard_used is True

    def test_second_standard_raises(self):
        tracker = ActionTracker()
        tracker.consume_action(ActionType.STANDARD)
        with pytest.raises(ValueError, match="Standard action already used"):
            tracker.consume_action(ActionType.STANDARD)

    def test_entity_cannot_take_two_standard_actions_per_turn(self):
        """Core rule: one Standard action per turn."""
        tracker = ActionTracker()
        tracker.consume_action(ActionType.STANDARD)
        with pytest.raises(ValueError):
            tracker.consume_action(ActionType.STANDARD)


# ---------------------------------------------------------------------------
# ActionTracker – consume_action: MOVE
# ---------------------------------------------------------------------------

class TestConsumeMove:
    def test_first_move_succeeds(self):
        tracker = ActionTracker()
        tracker.consume_action(ActionType.MOVE)
        assert tracker.move_used is True

    def test_second_move_raises(self):
        tracker = ActionTracker()
        tracker.consume_action(ActionType.MOVE)
        with pytest.raises(ValueError, match="Move action already used"):
            tracker.consume_action(ActionType.MOVE)


# ---------------------------------------------------------------------------
# ActionTracker – consume_action: SWIFT
# ---------------------------------------------------------------------------

class TestConsumeSwift:
    def test_first_swift_succeeds(self):
        tracker = ActionTracker()
        tracker.consume_action(ActionType.SWIFT)
        assert tracker.swift_used is True

    def test_second_swift_raises(self):
        tracker = ActionTracker()
        tracker.consume_action(ActionType.SWIFT)
        with pytest.raises(ValueError, match="Swift action already used"):
            tracker.consume_action(ActionType.SWIFT)


# ---------------------------------------------------------------------------
# ActionTracker – consume_action: FREE
# ---------------------------------------------------------------------------

class TestConsumeFree:
    def test_free_action_never_exhausted(self):
        tracker = ActionTracker()
        for _ in range(10):
            tracker.consume_action(ActionType.FREE)  # must not raise
        # No flags changed
        assert not tracker.standard_used
        assert not tracker.move_used
        assert not tracker.swift_used


# ---------------------------------------------------------------------------
# ActionTracker – consume_action: FULL_ROUND
# ---------------------------------------------------------------------------

class TestConsumeFullRound:
    def test_full_round_zeroes_standard_and_move(self):
        """Full-Round action must exhaust both Standard and Move trackers."""
        tracker = ActionTracker()
        tracker.consume_action(ActionType.FULL_ROUND)
        assert tracker.standard_used is True
        assert tracker.move_used is True

    def test_full_round_leaves_swift_intact(self):
        tracker = ActionTracker()
        tracker.consume_action(ActionType.FULL_ROUND)
        assert tracker.swift_used is False

    def test_full_round_after_standard_raises(self):
        tracker = ActionTracker()
        tracker.consume_action(ActionType.STANDARD)
        with pytest.raises(ValueError, match="Standard action already used"):
            tracker.consume_action(ActionType.FULL_ROUND)

    def test_full_round_after_move_raises(self):
        tracker = ActionTracker()
        tracker.consume_action(ActionType.MOVE)
        with pytest.raises(ValueError, match="Move action already used"):
            tracker.consume_action(ActionType.FULL_ROUND)


# ---------------------------------------------------------------------------
# ActionTracker – has_action
# ---------------------------------------------------------------------------

class TestHasAction:
    def test_fresh_tracker_has_all_actions(self):
        tracker = ActionTracker()
        assert tracker.has_action(ActionType.STANDARD) is True
        assert tracker.has_action(ActionType.MOVE) is True
        assert tracker.has_action(ActionType.SWIFT) is True
        assert tracker.has_action(ActionType.FREE) is True
        assert tracker.has_action(ActionType.FULL_ROUND) is True

    def test_after_standard_consumed(self):
        tracker = ActionTracker()
        tracker.consume_action(ActionType.STANDARD)
        assert tracker.has_action(ActionType.STANDARD) is False
        assert tracker.has_action(ActionType.FULL_ROUND) is False

    def test_after_move_consumed(self):
        tracker = ActionTracker()
        tracker.consume_action(ActionType.MOVE)
        assert tracker.has_action(ActionType.MOVE) is False
        assert tracker.has_action(ActionType.FULL_ROUND) is False

    def test_after_full_round(self):
        tracker = ActionTracker()
        tracker.consume_action(ActionType.FULL_ROUND)
        assert tracker.has_action(ActionType.STANDARD) is False
        assert tracker.has_action(ActionType.MOVE) is False
        assert tracker.has_action(ActionType.FULL_ROUND) is False

    def test_free_always_available(self):
        tracker = ActionTracker()
        tracker.consume_action(ActionType.FULL_ROUND)
        tracker.consume_action(ActionType.SWIFT)
        assert tracker.has_action(ActionType.FREE) is True


# ---------------------------------------------------------------------------
# ActionTracker – reset restores full_round availability
# ---------------------------------------------------------------------------

class TestResetRestoresFullRound:
    def test_full_round_available_after_reset(self):
        tracker = ActionTracker()
        tracker.consume_action(ActionType.FULL_ROUND)
        tracker.reset_turn()
        assert tracker.has_action(ActionType.FULL_ROUND) is True


# ---------------------------------------------------------------------------
# CombatSystem – action gate (STANDARD action consumed on attack)
# ---------------------------------------------------------------------------

class TestCombatSystemActionGate:
    def setup_method(self):
        self.bus = EventBus()
        self.system = CombatSystem(self.bus)
        self.results = []
        self.bus.subscribe("combat_result", self.results.append)

    def test_attack_without_tracker_always_resolves(self):
        """Backwards-compatible: no tracker → attack always fires."""
        attacker = _make_fighter("Attacker")
        defender = _make_fighter("Defender")
        intent = AttackIntent(attacker=attacker, defender=defender)
        self.bus.publish("attack_intent", intent)
        self.system.update()
        assert len(self.results) == 1

    def test_attack_with_fresh_tracker_resolves_and_consumes_standard(self):
        attacker = _make_fighter("Attacker")
        defender = _make_fighter("Defender")
        tracker = ActionTracker()
        intent = AttackIntent(
            attacker=attacker, defender=defender, action_tracker=tracker
        )
        self.bus.publish("attack_intent", intent)
        self.system.update()
        assert len(self.results) == 1
        assert tracker.standard_used is True

    def test_second_attack_with_exhausted_standard_is_dropped(self):
        """An entity cannot make a second Standard-action attack in the same turn."""
        attacker = _make_fighter("Attacker")
        defender = _make_fighter("Defender")
        tracker = ActionTracker()
        tracker.consume_action(ActionType.STANDARD)  # already used

        intent = AttackIntent(
            attacker=attacker, defender=defender, action_tracker=tracker
        )
        self.bus.publish("attack_intent", intent)
        self.system.update()
        # Intent must be silently dropped — no result published.
        assert len(self.results) == 0

    def test_only_first_of_two_concurrent_intents_resolves(self):
        """Two intents sharing the same tracker: first fires, second is dropped."""
        attacker = _make_fighter("Attacker")
        defender = _make_fighter("Defender")
        tracker = ActionTracker()

        intent1 = AttackIntent(
            attacker=attacker, defender=defender, action_tracker=tracker
        )
        intent2 = AttackIntent(
            attacker=attacker, defender=defender, action_tracker=tracker
        )
        self.bus.publish("attack_intent", intent1)
        self.bus.publish("attack_intent", intent2)
        self.system.update()
        assert len(self.results) == 1


# ---------------------------------------------------------------------------
# TurnManagerSystem – initiative and queue
# ---------------------------------------------------------------------------

class TestTurnManagerSystem:
    def setup_method(self):
        self.bus = EventBus()
        self.system = TurnManagerSystem(self.bus)
        self.events: list = []
        self.bus.subscribe("combat_started", self.events.append)
        self.bus.subscribe("turn_start", self.events.append)
        self.bus.subscribe("combat_ended", self.events.append)

    def _make_pair(self, ally_name="Ally", hostile_name="Goblin",
                   ally_pos=(0.0, 0.0, 0.0), hostile_pos=(0.0, 0.0, 0.0)):
        ally = _make_fighter(ally_name, dexterity=14)
        ally_entity = _make_entity(ally_name, *ally_pos)
        hostile = _make_fighter(hostile_name, dexterity=8)
        hostile_entity = _make_entity(hostile_name, *hostile_pos)
        self.system.register_ally(ally_entity, ally)
        self.system.register_hostile(hostile_entity, hostile)
        return ally_entity, ally, hostile_entity, hostile

    def test_not_in_combat_initially(self):
        assert self.system.in_combat is False

    def test_start_combat_builds_queue(self):
        self._make_pair()
        with patch.object(self.system, "_roll_initiative", side_effect=[15, 10]):
            self.system.start_combat()
        assert self.system.in_combat is True
        assert len(self.system.initiative_queue) == 2

    def test_queue_ordered_highest_initiative_first(self):
        ally_char = _make_fighter("Ally", dexterity=14)
        hostile_char = _make_fighter("Goblin", dexterity=8)
        ally_ent = _make_entity("Ally")
        hostile_ent = _make_entity("Goblin")
        self.system.register_ally(ally_ent, ally_char)
        self.system.register_hostile(hostile_ent, hostile_char)

        # Force deterministic roll: ally=5, hostile=20 (hostile goes first)
        with patch.object(self.system, "_roll_initiative", side_effect=[5, 20]):
            self.system.start_combat()

        queue = self.system.initiative_queue
        assert queue[0].initiative_score > queue[1].initiative_score
        assert queue[0].character.name == "Goblin"

    def test_start_combat_publishes_combat_started_event(self):
        self._make_pair()
        self.system.start_combat()
        combat_started = [e for e in self.events if "combatant_count" in e]
        assert len(combat_started) == 1
        assert combat_started[0]["combatant_count"] == 2

    def test_start_combat_publishes_turn_start_for_first_combatant(self):
        self._make_pair()
        with patch.object(self.system, "_roll_initiative", side_effect=[20, 5]):
            self.system.start_combat()
        turn_starts = [e for e in self.events if "initiative_score" in e]
        assert len(turn_starts) == 1

    def test_first_combatant_has_fresh_action_tracker(self):
        self._make_pair()
        self.system.start_combat()
        first = self.system.current_combatant
        assert first is not None
        assert first.action_tracker.standard_used is False
        assert first.action_tracker.move_used is False
        assert first.action_tracker.swift_used is False

    def test_advance_turn_cycles_through_queue(self):
        self._make_pair()
        self.system.start_combat()
        first = self.system.current_combatant
        second = self.system.advance_turn()
        assert second is not None
        assert second.character.name != first.character.name

    def test_advance_turn_resets_action_tracker(self):
        self._make_pair()
        self.system.start_combat()
        current = self.system.current_combatant
        # Exhaust current combatant's actions
        current.action_tracker.consume_action(ActionType.STANDARD)
        current.action_tracker.consume_action(ActionType.MOVE)
        # Advance to next — their tracker should be fresh
        next_combatant = self.system.advance_turn()
        assert next_combatant is not None
        assert next_combatant.action_tracker.standard_used is False
        assert next_combatant.action_tracker.move_used is False

    def test_advance_turn_wraps_around(self):
        self._make_pair()
        self.system.start_combat()
        n = len(self.system.initiative_queue)
        first_name = self.system.current_combatant.character.name
        for _ in range(n):
            self.system.advance_turn()
        # After n advances we are back to the first combatant
        assert self.system.current_combatant.character.name == first_name

    def test_end_combat_clears_state(self):
        self._make_pair()
        self.system.start_combat()
        self.system.end_combat()
        assert self.system.in_combat is False
        assert self.system.initiative_queue == []

    # Aggro detection

    def test_aggro_within_range_triggers_combat(self):
        """Hostiles within aggro range → combat starts automatically on update."""
        ally_char = _make_fighter("Hero")
        hostile_char = _make_fighter("Orc")
        ally_ent = _make_entity("Hero", x=0.0, y=0.0, z=0.0)
        hostile_ent = _make_entity("Orc", x=5.0, y=0.0, z=0.0)  # within 10 voxels
        self.system.register_ally(ally_ent, ally_char)
        self.system.register_hostile(hostile_ent, hostile_char)
        assert self.system.in_combat is False
        self.system.update()
        assert self.system.in_combat is True

    def test_no_aggro_outside_range_no_combat(self):
        """Hostiles beyond aggro range → combat does NOT start."""
        ally_char = _make_fighter("Hero")
        hostile_char = _make_fighter("Orc")
        ally_ent = _make_entity("Hero", x=0.0, y=0.0, z=0.0)
        hostile_ent = _make_entity("Orc", x=50.0, y=0.0, z=0.0)  # beyond 10 voxels
        self.system.register_ally(ally_ent, ally_char)
        self.system.register_hostile(hostile_ent, hostile_char)
        self.system.update()
        assert self.system.in_combat is False

    def test_update_does_not_restart_combat_when_already_in_combat(self):
        """Once in combat, update() should not call start_combat() again."""
        self._make_pair()
        self.system.start_combat()
        queue_snapshot = list(self.system.initiative_queue)
        self.system.update()  # should be a no-op while in_combat
        assert self.system.initiative_queue == queue_snapshot
