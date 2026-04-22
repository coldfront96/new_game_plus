"""
tests/ai_sim/test_tactics.py
-----------------------------
Verification tests for src.ai_sim.tactics (TacticalEvaluator).

Key scenario tested:
    An AI armed with a standard melee weapon (reach 5 ft) faces a fighter
    at 15 ft distance.  The evaluator must:
    1. Recommend a MOVE action to close the 15 ft gap.
    2. After the move action is consumed and the AI steps to within 5 ft,
       recommend a STANDARD (attack) action.
"""

from __future__ import annotations

import math

import pytest

from src.ai_sim.components import Position
from src.ai_sim.entity import Entity
from src.ai_sim.tactics import (
    DEFAULT_REACH_FT,
    VOXELS_TO_FEET,
    TacticalDecision,
    TacticalEvaluator,
)
from src.loot_math.item import Item, ItemType, Rarity
from src.rules_engine.actions import ActionTracker, ActionType
from src.rules_engine.character_35e import Character35e


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def melee_weapon():
    """A standard longsword (default 5 ft reach — no metadata override)."""
    return Item(
        name="Longsword",
        item_type=ItemType.WEAPON,
        rarity=Rarity.COMMON,
        base_damage=8,
    )


@pytest.fixture
def reach_weapon():
    """A halberd (reach weapon, 10 ft reach per 3.5e SRD)."""
    return Item(
        name="Halberd",
        item_type=ItemType.WEAPON,
        rarity=Rarity.COMMON,
        base_damage=10,
        metadata={"reach_ft": 10.0},
    )


@pytest.fixture
def orc_entity():
    """AI-controlled orc warrior at the origin."""
    e = Entity(name="Orc Warrior")
    e.add_component(Position(x=0.0, y=64.0, z=0.0))
    return e


@pytest.fixture
def orc_char():
    return Character35e(name="Orc Warrior", char_class="Fighter", level=1, strength=14)


@pytest.fixture
def fighter_entity():
    """Player fighter at 3 voxels (15 ft) away on the X axis."""
    e = Entity(name="Fighter")
    e.add_component(Position(x=3.0, y=64.0, z=0.0))
    return e


@pytest.fixture
def fighter_char():
    return Character35e(name="Fighter", char_class="Fighter", level=3)


# ---------------------------------------------------------------------------
# TacticalDecision dataclass
# ---------------------------------------------------------------------------

class TestTacticalDecision:
    def test_slots_enabled(self, orc_entity, orc_char, fighter_entity, fighter_char):
        decision = TacticalDecision(
            primary_target_entity=fighter_entity,
            primary_target_character=fighter_char,
            recommended_action=ActionType.MOVE,
            distance_ft=15.0,
            reach_ft=5.0,
        )
        assert hasattr(TacticalDecision, "__slots__")

    def test_fields(self, orc_entity, orc_char, fighter_entity, fighter_char):
        decision = TacticalDecision(
            primary_target_entity=fighter_entity,
            primary_target_character=fighter_char,
            recommended_action=ActionType.STANDARD,
            distance_ft=5.0,
            reach_ft=5.0,
        )
        assert decision.primary_target_entity is fighter_entity
        assert decision.primary_target_character is fighter_char
        assert decision.recommended_action == ActionType.STANDARD
        assert decision.distance_ft == 5.0
        assert decision.reach_ft == 5.0


# ---------------------------------------------------------------------------
# TacticalEvaluator — unit tests
# ---------------------------------------------------------------------------

class TestTacticalEvaluatorBasics:
    def test_no_hostiles_returns_none(self, orc_entity, orc_char):
        evaluator = TacticalEvaluator(
            actor_entity=orc_entity,
            actor_character=orc_char,
            visible_hostiles=[],
        )
        assert evaluator.evaluate() is None

    def test_actor_without_position_returns_none(self, orc_char, fighter_entity, fighter_char):
        actor = Entity(name="NoPos")  # no Position component
        evaluator = TacticalEvaluator(
            actor_entity=actor,
            actor_character=orc_char,
            visible_hostiles=[(fighter_entity, fighter_char)],
        )
        assert evaluator.evaluate() is None

    def test_hostile_without_position_is_skipped(self, orc_entity, orc_char, fighter_char):
        no_pos_entity = Entity(name="Ghost")  # no Position component
        evaluator = TacticalEvaluator(
            actor_entity=orc_entity,
            actor_character=orc_char,
            visible_hostiles=[(no_pos_entity, fighter_char)],
        )
        assert evaluator.evaluate() is None

    def test_inactive_hostile_is_skipped(self, orc_entity, orc_char, fighter_char):
        dead = Entity(name="Dead Fighter")
        dead.add_component(Position(x=3.0, y=64.0, z=0.0))
        dead.is_active = False
        evaluator = TacticalEvaluator(
            actor_entity=orc_entity,
            actor_character=orc_char,
            visible_hostiles=[(dead, fighter_char)],
        )
        assert evaluator.evaluate() is None


# ---------------------------------------------------------------------------
# TacticalEvaluator — reach and action selection
# ---------------------------------------------------------------------------

class TestWeaponReach:
    def test_no_weapon_defaults_to_five_feet(self):
        assert TacticalEvaluator._weapon_reach_ft(None) == DEFAULT_REACH_FT
        assert TacticalEvaluator._weapon_reach_ft(None) == 5.0

    def test_weapon_without_metadata_defaults_to_five_feet(self, melee_weapon):
        assert TacticalEvaluator._weapon_reach_ft(melee_weapon) == 5.0

    def test_reach_weapon_metadata_respected(self, reach_weapon):
        assert TacticalEvaluator._weapon_reach_ft(reach_weapon) == 10.0

    def test_reach_ft_coerced_to_float(self):
        item = Item(
            name="Pike",
            item_type=ItemType.WEAPON,
            rarity=Rarity.COMMON,
            metadata={"reach_ft": 10},  # int, not float
        )
        result = TacticalEvaluator._weapon_reach_ft(item)
        assert isinstance(result, float)
        assert result == 10.0


class TestDistanceCalculation:
    def test_coaxial_distance(self):
        pos_a = Position(x=0.0, y=64.0, z=0.0)
        pos_b = Position(x=3.0, y=64.0, z=0.0)  # 3 voxels = 15 ft
        assert TacticalEvaluator._distance_ft(pos_a, pos_b) == pytest.approx(15.0)

    def test_same_position_is_zero(self):
        pos = Position(x=5.0, y=64.0, z=5.0)
        assert TacticalEvaluator._distance_ft(pos, pos) == pytest.approx(0.0)

    def test_diagonal_distance(self):
        pos_a = Position(x=0.0, y=64.0, z=0.0)
        pos_b = Position(x=1.0, y=64.0, z=1.0)  # sqrt(2) voxels
        expected_ft = math.sqrt(2) * VOXELS_TO_FEET
        assert TacticalEvaluator._distance_ft(pos_a, pos_b) == pytest.approx(expected_ft)


# ---------------------------------------------------------------------------
# Core scenario: 15 ft gap → MOVE, then within reach → STANDARD
# ---------------------------------------------------------------------------

class TestMeleeGapScenario:
    """
    Scenario: Orc warrior (AI) is 15 ft (3 voxels) from a fighter.
    Melee weapon reach = 5 ft.

    Turn 1: distance (15 ft) > reach (5 ft) → MOVE action recommended.
    Turn 2: After moving to within 5 ft → STANDARD action recommended.
    """

    def test_fifteen_foot_gap_recommends_move(
        self, orc_entity, orc_char, fighter_entity, fighter_char, melee_weapon
    ):
        """Gap > reach → MOVE action should be selected."""
        evaluator = TacticalEvaluator(
            actor_entity=orc_entity,
            actor_character=orc_char,
            visible_hostiles=[(fighter_entity, fighter_char)],
            weapon=melee_weapon,
        )
        decision = evaluator.evaluate()

        assert decision is not None
        assert decision.distance_ft == pytest.approx(15.0)
        assert decision.reach_ft == pytest.approx(5.0)
        assert decision.recommended_action == ActionType.MOVE
        assert decision.primary_target_entity is fighter_entity
        assert decision.primary_target_character is fighter_char

    def test_move_action_is_consumed_from_tracker(
        self, orc_entity, orc_char, fighter_entity, fighter_char, melee_weapon
    ):
        """Consuming the MOVE decision should mark move_used on the tracker."""
        evaluator = TacticalEvaluator(
            actor_entity=orc_entity,
            actor_character=orc_char,
            visible_hostiles=[(fighter_entity, fighter_char)],
            weapon=melee_weapon,
        )
        decision = evaluator.evaluate()
        assert decision.recommended_action == ActionType.MOVE

        tracker = ActionTracker()
        tracker.consume_action(decision.recommended_action)

        assert tracker.move_used is True
        assert tracker.standard_used is False

    def test_within_reach_recommends_standard(
        self, orc_entity, orc_char, fighter_entity, fighter_char, melee_weapon
    ):
        """After closing to 5 ft (within reach), STANDARD action is recommended."""
        # Simulate the orc moving to 1 voxel (5 ft) from the fighter at x=3
        orc_pos = orc_entity.get_component(Position)
        orc_pos.x = 2.0  # 1 voxel away from fighter at x=3.0

        evaluator = TacticalEvaluator(
            actor_entity=orc_entity,
            actor_character=orc_char,
            visible_hostiles=[(fighter_entity, fighter_char)],
            weapon=melee_weapon,
        )
        decision = evaluator.evaluate()

        assert decision is not None
        assert decision.distance_ft == pytest.approx(5.0)
        assert decision.recommended_action == ActionType.STANDARD

    def test_standard_action_is_consumed_from_tracker(
        self, orc_entity, orc_char, fighter_entity, fighter_char, melee_weapon
    ):
        """After moving to reach, consuming STANDARD marks standard_used."""
        orc_pos = orc_entity.get_component(Position)
        orc_pos.x = 2.0  # within reach

        evaluator = TacticalEvaluator(
            actor_entity=orc_entity,
            actor_character=orc_char,
            visible_hostiles=[(fighter_entity, fighter_char)],
            weapon=melee_weapon,
        )
        decision = evaluator.evaluate()
        assert decision.recommended_action == ActionType.STANDARD

        tracker = ActionTracker()
        tracker.consume_action(decision.recommended_action)

        assert tracker.standard_used is True
        assert tracker.move_used is False

    def test_full_turn_sequence_move_then_attack(
        self, orc_entity, orc_char, fighter_entity, fighter_char, melee_weapon
    ):
        """Full two-phase turn: MOVE to close gap, then STANDARD to attack.

        Verifies that:
        - Phase 1 (distance 15 ft): evaluator recommends MOVE.
        - Tracker records MOVE as used.
        - Phase 2 (distance 5 ft after move): evaluator recommends STANDARD.
        - Tracker records STANDARD as used.
        - Both action slots are exhausted by end of turn.
        """
        tracker = ActionTracker()

        # --- Phase 1: gap = 15 ft, should MOVE ---
        evaluator1 = TacticalEvaluator(
            actor_entity=orc_entity,
            actor_character=orc_char,
            visible_hostiles=[(fighter_entity, fighter_char)],
            weapon=melee_weapon,
        )
        decision1 = evaluator1.evaluate()
        assert decision1.recommended_action == ActionType.MOVE
        tracker.consume_action(decision1.recommended_action)
        assert tracker.move_used

        # Simulate movement: orc advances to 1 voxel (5 ft) from the fighter
        orc_pos = orc_entity.get_component(Position)
        orc_pos.x = 2.0  # fighter is at x=3.0

        # --- Phase 2: gap = 5 ft, should ATTACK ---
        evaluator2 = TacticalEvaluator(
            actor_entity=orc_entity,
            actor_character=orc_char,
            visible_hostiles=[(fighter_entity, fighter_char)],
            weapon=melee_weapon,
        )
        decision2 = evaluator2.evaluate()
        assert decision2.recommended_action == ActionType.STANDARD
        assert decision2.distance_ft == pytest.approx(5.0)
        tracker.consume_action(decision2.recommended_action)
        assert tracker.standard_used

        # Both action slots consumed by end of turn
        assert tracker.move_used
        assert tracker.standard_used


# ---------------------------------------------------------------------------
# Reach weapon scenario
# ---------------------------------------------------------------------------

class TestReachWeaponScenario:
    def test_reach_weapon_attacks_at_ten_feet(
        self, orc_entity, orc_char, fighter_entity, fighter_char, reach_weapon
    ):
        """With a reach weapon (10 ft), 10 ft distance → STANDARD action."""
        # Place fighter at 2 voxels (10 ft) away
        fighter_entity.get_component(Position).x = 2.0

        evaluator = TacticalEvaluator(
            actor_entity=orc_entity,
            actor_character=orc_char,
            visible_hostiles=[(fighter_entity, fighter_char)],
            weapon=reach_weapon,
        )
        decision = evaluator.evaluate()

        assert decision is not None
        assert decision.distance_ft == pytest.approx(10.0)
        assert decision.reach_ft == pytest.approx(10.0)
        assert decision.recommended_action == ActionType.STANDARD

    def test_reach_weapon_moves_beyond_ten_feet(
        self, orc_entity, orc_char, fighter_entity, fighter_char, reach_weapon
    ):
        """With a reach weapon (10 ft), 15 ft distance → MOVE action."""
        # fighter_entity is at x=3.0 (15 ft) from fixture — already outside reach
        evaluator = TacticalEvaluator(
            actor_entity=orc_entity,
            actor_character=orc_char,
            visible_hostiles=[(fighter_entity, fighter_char)],
            weapon=reach_weapon,
        )
        decision = evaluator.evaluate()

        assert decision is not None
        assert decision.recommended_action == ActionType.MOVE


# ---------------------------------------------------------------------------
# Primary target selection (closest hostile)
# ---------------------------------------------------------------------------

class TestPrimaryTargetSelection:
    def test_closest_hostile_is_selected(self, orc_entity, orc_char, fighter_char):
        """TacticalEvaluator must select the closest visible hostile."""
        near_entity = Entity(name="Near Enemy")
        near_entity.add_component(Position(x=1.0, y=64.0, z=0.0))  # 5 ft

        far_entity = Entity(name="Far Enemy")
        far_entity.add_component(Position(x=4.0, y=64.0, z=0.0))  # 20 ft

        near_char = Character35e(name="Near Enemy", char_class="Fighter", level=1)
        far_char = Character35e(name="Far Enemy", char_class="Fighter", level=1)

        evaluator = TacticalEvaluator(
            actor_entity=orc_entity,
            actor_character=orc_char,
            visible_hostiles=[(far_entity, far_char), (near_entity, near_char)],
        )
        decision = evaluator.evaluate()

        assert decision is not None
        assert decision.primary_target_entity is near_entity
        assert decision.distance_ft == pytest.approx(5.0)

    def test_single_hostile_is_always_primary(
        self, orc_entity, orc_char, fighter_entity, fighter_char
    ):
        """With one hostile, that hostile is always the primary target."""
        evaluator = TacticalEvaluator(
            actor_entity=orc_entity,
            actor_character=orc_char,
            visible_hostiles=[(fighter_entity, fighter_char)],
        )
        decision = evaluator.evaluate()

        assert decision is not None
        assert decision.primary_target_entity is fighter_entity


# ---------------------------------------------------------------------------
# TurnManagerSystem integration — AI turn auto-execution
# ---------------------------------------------------------------------------

class TestTurnManagerAiIntegration:
    """Verify that TurnManagerSystem auto-executes hostile AI turns via update()."""

    def _make_entity_at(self, name: str, x: float) -> Entity:
        e = Entity(name=name)
        e.add_component(Position(x=x, y=64.0, z=0.0))
        return e

    def test_hostile_turn_consumes_move_when_far(self):
        """Hostile at 15 ft: update() should auto-consume MOVE action."""
        from src.ai_sim.systems import TurnManagerSystem
        from src.core.event_bus import EventBus

        bus = EventBus()
        tm = TurnManagerSystem(bus)

        ally_entity = self._make_entity_at("Ally", x=3.0)   # 3 voxels = 15 ft
        ally_char = Character35e(name="Ally", char_class="Fighter", level=3)

        orc_entity = self._make_entity_at("Orc", x=0.0)
        orc_char = Character35e(name="Orc", char_class="Fighter", level=1)

        tm.register_ally(ally_entity, ally_char)
        tm.register_hostile(orc_entity, orc_char)

        ai_events: list = []
        bus.subscribe("ai_action", lambda p: ai_events.append(p))

        import unittest.mock as mock
        # Orc goes first (initiative 25), ally second (initiative 1)
        with mock.patch.object(tm, "_roll_initiative", side_effect=[1, 25]):
            tm.start_combat()

        # Orc is current combatant; call update() to execute their AI turn
        tm.update()

        assert len(ai_events) == 1
        assert ai_events[0]["action"] == "MOVE"
        assert ai_events[0]["character_name"] == "Orc"

        # The orc's action tracker should have move_used=True
        orc_entry = tm.current_combatant
        assert orc_entry is not None
        assert orc_entry.action_tracker.move_used is True

    def test_hostile_turn_consumes_standard_when_adjacent(self):
        """Hostile at 5 ft: update() should auto-consume STANDARD action."""
        from src.ai_sim.systems import TurnManagerSystem
        from src.core.event_bus import EventBus

        bus = EventBus()
        tm = TurnManagerSystem(bus)

        ally_entity = self._make_entity_at("Ally", x=1.0)   # 1 voxel = 5 ft
        ally_char = Character35e(name="Ally", char_class="Fighter", level=3)

        orc_entity = self._make_entity_at("Orc", x=0.0)
        orc_char = Character35e(name="Orc", char_class="Fighter", level=1)

        tm.register_ally(ally_entity, ally_char)
        tm.register_hostile(orc_entity, orc_char)

        ai_events: list = []
        bus.subscribe("ai_action", lambda p: ai_events.append(p))

        import unittest.mock as mock
        with mock.patch.object(tm, "_roll_initiative", side_effect=[1, 25]):
            tm.start_combat()

        tm.update()

        assert len(ai_events) == 1
        assert ai_events[0]["action"] == "STANDARD"

        orc_entry = tm.current_combatant
        assert orc_entry.action_tracker.standard_used is True

    def test_advance_turn_then_update_executes_hostile_ai(self):
        """advance_turn() to orc's turn, then update() should execute AI."""
        from src.ai_sim.systems import TurnManagerSystem
        from src.core.event_bus import EventBus

        bus = EventBus()
        tm = TurnManagerSystem(bus)

        ally_entity = self._make_entity_at("Ally", x=3.0)
        ally_char = Character35e(name="Ally", char_class="Fighter", level=3)

        orc_entity = self._make_entity_at("Orc", x=0.0)
        orc_char = Character35e(name="Orc", char_class="Fighter", level=1)

        tm.register_ally(ally_entity, ally_char)
        tm.register_hostile(orc_entity, orc_char)

        ai_events: list = []
        bus.subscribe("ai_action", lambda p: ai_events.append(p))

        import unittest.mock as mock
        # Ally goes first (initiative 25), orc second (initiative 1)
        with mock.patch.object(tm, "_roll_initiative", side_effect=[25, 1]):
            tm.start_combat()

        # Ally's turn first; update() should not fire AI for ally
        tm.update()
        assert len(ai_events) == 0

        # Advance to orc's turn, then update() → AI executes
        tm.advance_turn()
        tm.update()
        assert len(ai_events) == 1
        assert ai_events[0]["action"] == "MOVE"

    def test_update_called_twice_only_fires_ai_once(self):
        """Multiple update() calls on the same turn should not re-fire AI."""
        from src.ai_sim.systems import TurnManagerSystem
        from src.core.event_bus import EventBus

        bus = EventBus()
        tm = TurnManagerSystem(bus)

        ally_entity = self._make_entity_at("Ally", x=3.0)
        ally_char = Character35e(name="Ally", char_class="Fighter", level=3)

        orc_entity = self._make_entity_at("Orc", x=0.0)
        orc_char = Character35e(name="Orc", char_class="Fighter", level=1)

        tm.register_ally(ally_entity, ally_char)
        tm.register_hostile(orc_entity, orc_char)

        ai_events: list = []
        bus.subscribe("ai_action", lambda p: ai_events.append(p))

        import unittest.mock as mock
        with mock.patch.object(tm, "_roll_initiative", side_effect=[1, 25]):
            tm.start_combat()

        tm.update()  # First call: AI executes MOVE
        tm.update()  # Second call: action already consumed, no new event
        assert len(ai_events) == 1
