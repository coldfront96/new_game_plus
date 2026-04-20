"""
tests/ai_sim/test_behavior.py
-------------------------------
Unit and integration tests for the D&D 3.5e Skill System and AI Behavior FSM.

Includes a simulation test where a hungry entity finds and moves toward a
"Food" source using the Survival skill.
"""

from unittest.mock import patch

import pytest

from src.ai_sim.behavior import BehaviorFSM, BehaviorState, EntityTask, TaskType
from src.ai_sim.components import Needs, Position
from src.ai_sim.entity import Entity
from src.ai_sim.systems import BehaviorSystem, EntityBehaviorEntry, MoveIntent, MovementSystem
from src.core.event_bus import EventBus
from src.rules_engine.character_35e import Character35e
from src.rules_engine.dice import RollResult
from src.rules_engine.skills import (
    SKILL_DEFINITIONS,
    SkillAbility,
    SkillCheckResult,
    SkillSystem,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def bus():
    return EventBus()


@pytest.fixture
def ranger():
    """A ranger with good Wisdom for Survival checks."""
    return Character35e(
        name="Elara",
        char_class="Ranger",
        level=3,
        strength=14,
        dexterity=16,
        constitution=12,
        intelligence=10,
        wisdom=16,  # +3 modifier
        charisma=8,
    )


@pytest.fixture
def skill_system():
    ss = SkillSystem()
    ss.set_rank("Survival", 6)
    ss.set_rank("Search", 4)
    return ss


# ---------------------------------------------------------------------------
# Tests — SkillSystem
# ---------------------------------------------------------------------------

class TestSkillSystem:
    """Unit tests for src.rules_engine.skills.SkillSystem."""

    def test_slots_enabled(self):
        assert hasattr(SkillSystem, "__slots__")

    def test_initial_ranks_empty(self):
        ss = SkillSystem()
        assert ss.get_rank("Survival") == 0
        assert ss.trained_skills == {}

    def test_set_rank(self):
        ss = SkillSystem()
        ss.set_rank("Survival", 5)
        assert ss.get_rank("Survival") == 5

    def test_set_rank_zero(self):
        ss = SkillSystem()
        ss.set_rank("Search", 3)
        ss.set_rank("Search", 0)
        assert ss.get_rank("Search") == 0

    def test_set_rank_negative_raises(self):
        ss = SkillSystem()
        with pytest.raises(ValueError, match="negative"):
            ss.set_rank("Hide", -1)

    def test_set_rank_exceeds_cap_raises(self):
        ss = SkillSystem()
        with pytest.raises(ValueError, match="exceeds maximum"):
            ss.set_rank("Hide", 30)

    def test_add_ranks(self):
        ss = SkillSystem()
        ss.set_rank("Craft", 3)
        new_rank = ss.add_ranks("Craft", 2)
        assert new_rank == 5
        assert ss.get_rank("Craft") == 5

    def test_add_ranks_exceeds_cap_raises(self):
        ss = SkillSystem(max_rank_cap=10)
        ss.set_rank("Swim", 8)
        with pytest.raises(ValueError, match="exceed cap"):
            ss.add_ranks("Swim", 5)

    def test_add_ranks_negative_raises(self):
        ss = SkillSystem()
        with pytest.raises(ValueError, match="non-negative"):
            ss.add_ranks("Hide", -1)

    def test_trained_skills(self):
        ss = SkillSystem()
        ss.set_rank("Survival", 5)
        ss.set_rank("Search", 3)
        ss.set_rank("Hide", 0)
        assert ss.trained_skills == {"Survival": 5, "Search": 3}

    def test_get_key_ability(self):
        ss = SkillSystem()
        assert ss.get_key_ability("Survival") == SkillAbility.WIS
        assert ss.get_key_ability("Search") == SkillAbility.INT
        assert ss.get_key_ability("Climb") == SkillAbility.STR
        assert ss.get_key_ability("NotASkill") is None

    def test_custom_max_rank_cap(self):
        ss = SkillSystem(max_rank_cap=10)
        ss.set_rank("Spot", 10)
        assert ss.get_rank("Spot") == 10
        with pytest.raises(ValueError):
            ss.set_rank("Spot", 11)


class TestSkillCheck:
    """Tests for the SkillSystem.check() method."""

    def test_check_result_slots(self):
        assert hasattr(SkillCheckResult, "__slots__")

    def test_check_success(self):
        ss = SkillSystem()
        ss.set_rank("Survival", 5)
        # Force a known roll (roll=15, total=15+5+3=23 vs DC 15 → success)
        with patch("src.rules_engine.skills.roll_d20") as mock_roll:
            mock_roll.return_value = RollResult(raw=15, modifier=8, total=23)
            result = ss.check("Survival", ability_modifier=3, dc=15)

        assert result.success is True
        assert result.total == 23
        assert result.dc == 15
        assert result.margin == 8
        assert result.skill_name == "Survival"

    def test_check_failure(self):
        ss = SkillSystem()
        ss.set_rank("Search", 2)
        # Force low roll (roll=3, total=3+2+0=5 vs DC 15 → fail)
        with patch("src.rules_engine.skills.roll_d20") as mock_roll:
            mock_roll.return_value = RollResult(raw=3, modifier=2, total=5)
            result = ss.check("Search", ability_modifier=0, dc=15)

        assert result.success is False
        assert result.total == 5
        assert result.margin == -10

    def test_check_with_misc_modifier(self):
        ss = SkillSystem()
        ss.set_rank("Spot", 4)
        with patch("src.rules_engine.skills.roll_d20") as mock_roll:
            # total_modifier = 4 + 2 + 3 = 9, roll raw=10
            mock_roll.return_value = RollResult(raw=10, modifier=9, total=19)
            result = ss.check("Spot", ability_modifier=2, dc=18, misc_modifier=3)

        assert result.success is True
        assert result.total == 19

    def test_check_untrained_skill(self):
        ss = SkillSystem()
        # 0 ranks + 0 ability mod, need high roll
        with patch("src.rules_engine.skills.roll_d20") as mock_roll:
            mock_roll.return_value = RollResult(raw=20, modifier=0, total=20)
            result = ss.check("Craft", ability_modifier=0, dc=15)

        assert result.success is True
        assert result.total == 20


# ---------------------------------------------------------------------------
# Tests — BehaviorFSM
# ---------------------------------------------------------------------------

class TestBehaviorFSM:
    """Unit tests for the Finite State Machine."""

    def test_slots_enabled(self):
        assert hasattr(BehaviorFSM, "__slots__")

    def test_initial_state_is_idle(self):
        fsm = BehaviorFSM()
        assert fsm.state == BehaviorState.IDLE
        assert fsm.is_idle is True

    def test_valid_transition_idle_to_search(self):
        fsm = BehaviorFSM()
        assert fsm.transition(BehaviorState.SEARCH_FOR_TASK) is True
        assert fsm.state == BehaviorState.SEARCH_FOR_TASK

    def test_valid_transition_search_to_move(self):
        fsm = BehaviorFSM()
        fsm.transition(BehaviorState.SEARCH_FOR_TASK)
        assert fsm.transition(BehaviorState.MOVE_TO_TARGET) is True
        assert fsm.state == BehaviorState.MOVE_TO_TARGET

    def test_valid_transition_move_to_action(self):
        fsm = BehaviorFSM()
        fsm.transition(BehaviorState.SEARCH_FOR_TASK)
        fsm.transition(BehaviorState.MOVE_TO_TARGET)
        assert fsm.transition(BehaviorState.PERFORM_ACTION) is True
        assert fsm.state == BehaviorState.PERFORM_ACTION

    def test_valid_transition_action_to_idle(self):
        fsm = BehaviorFSM()
        fsm.transition(BehaviorState.SEARCH_FOR_TASK)
        fsm.transition(BehaviorState.MOVE_TO_TARGET)
        fsm.transition(BehaviorState.PERFORM_ACTION)
        assert fsm.transition(BehaviorState.IDLE) is True
        assert fsm.is_idle is True

    def test_invalid_transition_returns_false(self):
        fsm = BehaviorFSM()
        # Cannot jump directly from IDLE to MOVE_TO_TARGET
        assert fsm.transition(BehaviorState.MOVE_TO_TARGET) is False
        assert fsm.state == BehaviorState.IDLE

    def test_invalid_transition_idle_to_action(self):
        fsm = BehaviorFSM()
        assert fsm.transition(BehaviorState.PERFORM_ACTION) is False

    def test_assign_task_transitions_from_idle(self):
        fsm = BehaviorFSM()
        task = EntityTask(task_type=TaskType.FORAGE, skill_name="Survival", dc=15)
        fsm.assign_task(task)
        assert fsm.state == BehaviorState.SEARCH_FOR_TASK
        assert fsm.current_task is task

    def test_complete_task(self):
        fsm = BehaviorFSM()
        task = EntityTask(task_type=TaskType.FORAGE, skill_name="Survival", dc=15)
        fsm.assign_task(task)
        fsm.transition(BehaviorState.MOVE_TO_TARGET)
        fsm.transition(BehaviorState.PERFORM_ACTION)
        fsm.complete_task()
        assert fsm.is_idle is True
        assert fsm.current_task.completed is True

    def test_tick_increments_counter(self):
        fsm = BehaviorFSM()
        fsm.tick()
        fsm.tick()
        assert fsm.ticks_in_state == 2

    def test_transition_resets_tick_counter(self):
        fsm = BehaviorFSM()
        fsm.tick()
        fsm.tick()
        fsm.transition(BehaviorState.SEARCH_FOR_TASK)
        assert fsm.ticks_in_state == 0

    def test_reset(self):
        fsm = BehaviorFSM()
        fsm.assign_task(EntityTask(task_type=TaskType.FORAGE))
        fsm.reset()
        assert fsm.is_idle is True
        assert fsm.current_task.task_type == TaskType.NONE
        assert fsm.has_task is False

    def test_has_task(self):
        fsm = BehaviorFSM()
        assert fsm.has_task is False
        fsm.assign_task(EntityTask(task_type=TaskType.FORAGE))
        assert fsm.has_task is True


class TestEntityTask:
    """Unit tests for the EntityTask dataclass."""

    def test_slots_enabled(self):
        assert hasattr(EntityTask, "__slots__")

    def test_defaults(self):
        task = EntityTask()
        assert task.task_type == TaskType.NONE
        assert task.target_position is None
        assert task.skill_name is None
        assert task.dc == 10
        assert task.completed is False

    def test_forage_task(self):
        task = EntityTask(
            task_type=TaskType.FORAGE,
            target_position=(10, 65, 10),
            skill_name="Survival",
            dc=15,
        )
        assert task.task_type == TaskType.FORAGE
        assert task.target_position == (10, 65, 10)
        assert task.skill_name == "Survival"


# ---------------------------------------------------------------------------
# Tests — BehaviorSystem
# ---------------------------------------------------------------------------

class TestBehaviorSystem:
    """Unit tests for the BehaviorSystem."""

    def test_register_entity(self, bus, ranger, skill_system):
        system = BehaviorSystem(event_bus=bus)
        entity = Entity(name="Elara")
        fsm = BehaviorFSM()
        system.register_entity(entity, fsm, skill_system, ranger)
        assert system.entity_count == 1

    def test_idle_entity_with_low_hunger_starts_forage(self, bus, ranger, skill_system):
        system = BehaviorSystem(event_bus=bus)
        entity = Entity(name="Elara")
        entity.add_component(Position(x=0, y=65, z=0))
        entity.add_component(Needs(hunger=20.0))  # Below threshold
        fsm = BehaviorFSM()
        system.register_entity(entity, fsm, skill_system, ranger)

        system.update()

        assert fsm.state == BehaviorState.SEARCH_FOR_TASK
        assert fsm.current_task.task_type == TaskType.FORAGE

    def test_idle_entity_with_full_hunger_stays_idle(self, bus, ranger, skill_system):
        system = BehaviorSystem(event_bus=bus)
        entity = Entity(name="Elara")
        entity.add_component(Needs(hunger=100.0))
        fsm = BehaviorFSM()
        system.register_entity(entity, fsm, skill_system, ranger)

        system.update()

        assert fsm.is_idle is True

    def test_search_with_food_source_transitions_to_move(self, bus, ranger, skill_system):
        system = BehaviorSystem(event_bus=bus)
        system.add_food_source((10, 65, 10))

        entity = Entity(name="Elara")
        entity.add_component(Position(x=0, y=65, z=0))
        entity.add_component(Needs(hunger=20.0))
        fsm = BehaviorFSM()
        system.register_entity(entity, fsm, skill_system, ranger)

        # First tick: IDLE → SEARCH_FOR_TASK
        system.update()
        # Second tick: SEARCH_FOR_TASK → MOVE_TO_TARGET
        system.update()

        assert fsm.state == BehaviorState.MOVE_TO_TARGET
        assert fsm.current_task.target_position == (10, 65, 10)

    def test_search_without_food_returns_to_idle(self, bus, ranger, skill_system):
        system = BehaviorSystem(event_bus=bus)
        # No food sources registered

        entity = Entity(name="Elara")
        entity.add_component(Position(x=0, y=65, z=0))
        entity.add_component(Needs(hunger=20.0))
        fsm = BehaviorFSM()
        system.register_entity(entity, fsm, skill_system, ranger)

        # First tick: IDLE → SEARCH_FOR_TASK
        system.update()
        # Second tick: SEARCH_FOR_TASK → IDLE (no food)
        system.update()

        assert fsm.is_idle is True

    def test_move_complete_transitions_to_perform_action(self, bus, ranger, skill_system):
        system = BehaviorSystem(event_bus=bus)
        system.add_food_source((5, 65, 5))

        entity = Entity(name="Elara")
        entity.add_component(Position(x=0, y=65, z=0))
        entity.add_component(Needs(hunger=20.0))
        fsm = BehaviorFSM()
        system.register_entity(entity, fsm, skill_system, ranger)

        # IDLE → SEARCH → MOVE
        system.update()
        system.update()
        assert fsm.state == BehaviorState.MOVE_TO_TARGET

        # Simulate move_complete event
        bus.publish("move_complete", {
            "entity_id": entity.entity_id,
            "position": (5.0, 65.0, 5.0),
        })
        assert fsm.state == BehaviorState.PERFORM_ACTION

    def test_perform_action_does_skill_check(self, bus, ranger, skill_system):
        system = BehaviorSystem(event_bus=bus)
        system.add_food_source((5, 65, 5))

        entity = Entity(name="Elara")
        entity.add_component(Position(x=0, y=65, z=0))
        entity.add_component(Needs(hunger=20.0))
        fsm = BehaviorFSM()
        system.register_entity(entity, fsm, skill_system, ranger)

        skill_results = []
        bus.subscribe("skill_check_result", lambda r: skill_results.append(r))

        # Drive through states: IDLE → SEARCH → MOVE
        system.update()
        system.update()
        # Simulate arrival
        bus.publish("move_complete", {
            "entity_id": entity.entity_id,
            "position": (5.0, 65.0, 5.0),
        })
        # PERFORM_ACTION tick
        system.update()

        assert len(skill_results) == 1
        assert skill_results[0]["skill"] == "Survival"
        assert skill_results[0]["dc"] == 15
        assert fsm.is_idle is True

    def test_successful_forage_restores_hunger(self, bus, ranger, skill_system):
        system = BehaviorSystem(event_bus=bus)
        system.add_food_source((5, 65, 5))

        entity = Entity(name="Elara")
        entity.add_component(Position(x=0, y=65, z=0))
        needs = Needs(hunger=20.0)
        entity.add_component(needs)
        fsm = BehaviorFSM()
        system.register_entity(entity, fsm, skill_system, ranger)

        # Drive to PERFORM_ACTION
        system.update()
        system.update()
        bus.publish("move_complete", {"entity_id": entity.entity_id, "position": (5.0, 65.0, 5.0)})

        # Force a successful roll
        with patch("src.rules_engine.skills.roll_d20") as mock_roll:
            # rank=6 + wisdom_mod=3 = 9 total modifier
            mock_roll.return_value = RollResult(raw=15, modifier=9, total=24)
            system.update()

        assert needs.hunger == 50.0  # 20 + 30 restored
        assert fsm.is_idle is True


# ---------------------------------------------------------------------------
# Tests — Integration / Simulation
# ---------------------------------------------------------------------------

class TestHungryEntitySimulation:
    """Integration test: a hungry entity finds and moves toward food."""

    def test_full_behavior_cycle_hungry_entity_forages(self, bus, ranger, skill_system):
        """Simulation: hungry entity → searches → moves → forages successfully."""
        # Setup
        system = BehaviorSystem(event_bus=bus)
        food_pos = (5, 65, 5)
        system.add_food_source(food_pos)

        entity = Entity(name="Elara")
        entity.add_component(Position(x=0, y=65, z=0))
        needs = Needs(hunger=15.0)  # Very hungry
        entity.add_component(needs)
        fsm = BehaviorFSM()
        system.register_entity(entity, fsm, skill_system, ranger)

        # Track events
        move_requests = []
        skill_results = []
        bus.subscribe("behavior_move_request", lambda r: move_requests.append(r))
        bus.subscribe("skill_check_result", lambda r: skill_results.append(r))

        # --- Tick 1: IDLE → SEARCH_FOR_TASK (hunger triggers forage) ---
        system.update()
        assert fsm.state == BehaviorState.SEARCH_FOR_TASK
        assert fsm.current_task.task_type == TaskType.FORAGE
        assert fsm.current_task.skill_name == "Survival"

        # --- Tick 2: SEARCH_FOR_TASK → MOVE_TO_TARGET ---
        system.update()
        assert fsm.state == BehaviorState.MOVE_TO_TARGET
        assert fsm.current_task.target_position == food_pos
        assert len(move_requests) == 1
        assert move_requests[0]["target"] == food_pos

        # --- Simulate entity arriving at food (external movement system) ---
        pos = entity.get_component(Position)
        pos.x, pos.y, pos.z = 5.0, 65.0, 5.0
        bus.publish("move_complete", {
            "entity_id": entity.entity_id,
            "position": (5.0, 65.0, 5.0),
        })
        assert fsm.state == BehaviorState.PERFORM_ACTION

        # --- Tick 3: PERFORM_ACTION — Survival check ---
        with patch("src.rules_engine.skills.roll_d20") as mock_roll:
            # rank=6, wisdom_mod=3, total_modifier=9
            mock_roll.return_value = RollResult(raw=12, modifier=9, total=21)
            system.update()

        # Verify outcome
        assert fsm.is_idle is True
        assert fsm.current_task.completed is True
        assert len(skill_results) == 1
        assert skill_results[0]["success"] is True
        assert skill_results[0]["total"] == 21
        # Hunger restored: 15 + 30 = 45
        assert needs.hunger == 45.0

    def test_hungry_entity_fails_forage_no_hunger_restored(self, bus, ranger, skill_system):
        """If the Survival check fails, hunger is not restored."""
        system = BehaviorSystem(event_bus=bus)
        system.add_food_source((5, 65, 5))

        entity = Entity(name="Elara")
        entity.add_component(Position(x=0, y=65, z=0))
        needs = Needs(hunger=20.0)
        entity.add_component(needs)
        fsm = BehaviorFSM()
        system.register_entity(entity, fsm, skill_system, ranger)

        # Drive through states
        system.update()  # IDLE → SEARCH
        system.update()  # SEARCH → MOVE
        bus.publish("move_complete", {"entity_id": entity.entity_id, "position": (5.0, 65.0, 5.0)})

        # Force a failed roll (rank=6 + wis=3 = 9, but roll is 1)
        with patch("src.rules_engine.skills.roll_d20") as mock_roll:
            mock_roll.return_value = RollResult(raw=1, modifier=9, total=10)
            system.update()

        assert fsm.is_idle is True
        assert needs.hunger == 20.0  # Not restored

    def test_inactive_entity_is_skipped(self, bus, ranger, skill_system):
        """Inactive entities should be skipped by the BehaviorSystem."""
        system = BehaviorSystem(event_bus=bus)
        entity = Entity(name="Dead")
        entity.add_component(Needs(hunger=5.0))
        entity.destroy()  # Mark inactive
        fsm = BehaviorFSM()
        system.register_entity(entity, fsm, skill_system, ranger)

        system.update()
        assert fsm.is_idle is True  # Never triggered


# ---------------------------------------------------------------------------
# Tests — Skill definitions
# ---------------------------------------------------------------------------

class TestSkillDefinitions:
    """Verify the standard 3.5e skill list."""

    def test_survival_is_wisdom(self):
        assert SKILL_DEFINITIONS["Survival"] == SkillAbility.WIS

    def test_search_is_intelligence(self):
        assert SKILL_DEFINITIONS["Search"] == SkillAbility.INT

    def test_craft_is_intelligence(self):
        assert SKILL_DEFINITIONS["Craft"] == SkillAbility.INT

    def test_hide_is_dexterity(self):
        assert SKILL_DEFINITIONS["Hide"] == SkillAbility.DEX

    def test_climb_is_strength(self):
        assert SKILL_DEFINITIONS["Climb"] == SkillAbility.STR

    def test_standard_skills_count(self):
        # 3.5e SRD has ~35 standard skills
        assert len(SKILL_DEFINITIONS) >= 30
