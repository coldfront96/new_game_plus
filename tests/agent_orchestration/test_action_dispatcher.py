"""Tests for src.agent_orchestration.action_dispatcher."""

from __future__ import annotations

import json
import random
from typing import List
from unittest.mock import MagicMock

import pytest

from src.agent_orchestration import (
    ActionDecodeError,
    ActionDispatcher,
    AgentAction,
    AgentActionType,
    AgentTask,
    DispatchResult,
    LLMTaskRunner,
    PromptBuilder,
    ResultParser,
    Scheduler,
    TaskStatus,
    TaskType,
    decode_action,
)
from src.rules_engine.actions import ActionTracker, ActionType
from src.rules_engine.character_35e import Character35e
from src.rules_engine.spellcasting import SpellResolver, Spellbook, SpellSlotManager
from src.rules_engine.magic import Spell, SpellRegistry, SpellSchool


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

class _FixedRNG:
    """Deterministic RNG: always returns a fixed value from randint/random."""

    def __init__(self, fixed: int = 10):
        self._fixed = fixed

    def randint(self, a: int, b: int) -> int:
        return min(self._fixed, b)

    def random(self) -> float:
        return 0.5

    def uniform(self, a: float, b: float) -> float:
        return (a + b) / 2.0

    def choice(self, seq):
        return seq[0]


def _make_fighter(name: str = "Aldric") -> Character35e:
    return Character35e(
        name=name,
        char_class="Fighter",
        level=5,
        strength=16,
        dexterity=13,
        constitution=14,
        skills={"Climb": 8, "Intimidate": 6},
        equipment=["Longsword", "Potion of Healing"],
    )


def _make_goblin() -> Character35e:
    return Character35e(
        name="Goblin",
        char_class="Rogue",
        level=1,
        strength=8,
        dexterity=14,
    )


def _make_wizard() -> Character35e:
    spellbook = Spellbook()
    spellbook.add_known("Magic Missile", spell_level=1)
    char = Character35e(
        name="Zara",
        char_class="Wizard",
        level=3,
        intelligence=16,
        spellbook=spellbook,
    )
    return char


def _make_dispatcher(*characters: Character35e) -> ActionDispatcher:
    dispatcher = ActionDispatcher()
    dispatcher.register_many(list(characters))
    return dispatcher


# ---------------------------------------------------------------------------
# decode_action
# ---------------------------------------------------------------------------

class TestDecodeAction:
    def test_attack(self):
        action = decode_action({"action_type": "attack", "target_id": "abc"})
        assert action.action_type is AgentActionType.ATTACK
        assert action.target_id == "abc"
        assert action.use_ranged is False

    def test_full_attack_ranged(self):
        action = decode_action({"action_type": "full_attack", "use_ranged": True})
        assert action.action_type is AgentActionType.FULL_ATTACK
        assert action.use_ranged is True

    def test_cast_spell(self):
        action = decode_action({"action_type": "cast_spell", "spell_name": "Magic Missile", "target_id": "x"})
        assert action.action_type is AgentActionType.CAST_SPELL
        assert action.spell_name == "Magic Missile"

    def test_skill_check_defaults(self):
        action = decode_action({"action_type": "skill_check", "skill_name": "Spot"})
        assert action.skill_name == "Spot"
        assert action.dc == 10

    def test_skill_check_custom_dc(self):
        action = decode_action({"action_type": "skill_check", "skill_name": "Spot", "dc": 18})
        assert action.dc == 18

    def test_move_with_destination(self):
        action = decode_action({"action_type": "move", "destination": [3, 5, 1]})
        assert action.action_type is AgentActionType.MOVE
        assert action.destination == [3, 5, 1]

    def test_total_defense(self):
        action = decode_action({"action_type": "total_defense"})
        assert action.action_type is AgentActionType.TOTAL_DEFENSE

    def test_delay(self):
        action = decode_action({"action_type": "delay"})
        assert action.action_type is AgentActionType.DELAY

    def test_five_foot_step(self):
        action = decode_action({"action_type": "five_foot_step", "destination": [4, 4, 0]})
        assert action.action_type is AgentActionType.FIVE_FOOT_STEP
        assert action.destination == [4, 4, 0]

    def test_use_item(self):
        action = decode_action({"action_type": "use_item", "item_name": "Potion of Healing"})
        assert action.item_name == "Potion of Healing"

    def test_unknown_action_type_raises(self):
        with pytest.raises(ActionDecodeError, match="unknown action_type"):
            decode_action({"action_type": "summon_dragon"})

    def test_missing_action_type_raises(self):
        with pytest.raises(ActionDecodeError):
            decode_action({})

    def test_non_list_destination_is_ignored(self):
        action = decode_action({"action_type": "move", "destination": "north"})
        assert action.destination is None


# ---------------------------------------------------------------------------
# ActionDispatcher.dispatch — ATTACK
# ---------------------------------------------------------------------------

class TestDispatchAttack:
    def test_attack_hit_or_miss_returns_dispatch_result(self):
        fighter = _make_fighter()
        goblin = _make_goblin()
        dispatcher = _make_dispatcher(fighter, goblin)
        tracker = ActionTracker()
        action = AgentAction(
            action_type=AgentActionType.ATTACK,
            target_id=goblin.char_id,
        )
        result = dispatcher.dispatch(action, fighter, action_tracker=tracker)
        assert isinstance(result, DispatchResult)
        assert result.action_type is AgentActionType.ATTACK
        assert result.action_cost is ActionType.STANDARD
        assert len(result.combat_results) == 1
        assert tracker.standard_used is True

    def test_attack_consumes_standard_action(self):
        fighter = _make_fighter()
        goblin = _make_goblin()
        dispatcher = _make_dispatcher(fighter, goblin)
        tracker = ActionTracker()
        action = AgentAction(action_type=AgentActionType.ATTACK, target_id=goblin.char_id)
        dispatcher.dispatch(action, fighter, action_tracker=tracker)
        with pytest.raises(ValueError, match="Standard action already used"):
            dispatcher.dispatch(action, fighter, action_tracker=tracker)

    def test_attack_no_target_returns_error_result(self):
        fighter = _make_fighter()
        dispatcher = ActionDispatcher()
        dispatcher.register(fighter)
        tracker = ActionTracker()
        action = AgentAction(action_type=AgentActionType.ATTACK, target_id="ghost_id")
        result = dispatcher.dispatch(action, fighter, action_tracker=tracker)
        assert result.success is False
        assert result.error == "target not found"

    def test_attack_damage_dealt_is_nonnegative(self):
        fighter = _make_fighter()
        goblin = _make_goblin()
        dispatcher = _make_dispatcher(fighter, goblin)
        tracker = ActionTracker()
        action = AgentAction(action_type=AgentActionType.ATTACK, target_id=goblin.char_id)
        result = dispatcher.dispatch(action, fighter, action_tracker=tracker)
        assert result.damage_dealt >= 0

    def test_attack_narrative_contains_names(self):
        fighter = _make_fighter("Aldric")
        goblin = _make_goblin()
        dispatcher = _make_dispatcher(fighter, goblin)
        tracker = ActionTracker()
        action = AgentAction(action_type=AgentActionType.ATTACK, target_id=goblin.char_id)
        result = dispatcher.dispatch(action, fighter, action_tracker=tracker)
        assert "Aldric" in result.narrative
        assert "Goblin" in result.narrative


# ---------------------------------------------------------------------------
# ActionDispatcher.dispatch — FULL_ATTACK
# ---------------------------------------------------------------------------

class TestDispatchFullAttack:
    def test_full_attack_returns_multiple_results(self):
        fighter = _make_fighter()
        goblin = _make_goblin()
        dispatcher = _make_dispatcher(fighter, goblin)
        tracker = ActionTracker()
        action = AgentAction(action_type=AgentActionType.FULL_ATTACK, target_id=goblin.char_id)
        result = dispatcher.dispatch(action, fighter, action_tracker=tracker)
        assert result.action_cost is ActionType.FULL_ROUND
        assert len(result.combat_results) >= 1
        assert tracker.standard_used is True
        assert tracker.move_used is True

    def test_full_attack_total_damage_equals_sum(self):
        fighter = _make_fighter()
        goblin = _make_goblin()
        dispatcher = _make_dispatcher(fighter, goblin)
        tracker = ActionTracker()
        action = AgentAction(action_type=AgentActionType.FULL_ATTACK, target_id=goblin.char_id)
        result = dispatcher.dispatch(action, fighter, action_tracker=tracker)
        assert result.damage_dealt == sum(r.total_damage for r in result.combat_results)


# ---------------------------------------------------------------------------
# ActionDispatcher.dispatch — CAST_SPELL
# ---------------------------------------------------------------------------

class TestDispatchCastSpell:
    def _make_spell_resolver(self, wizard: Character35e) -> SpellResolver:
        registry = SpellRegistry()
        spell = Spell(
            name="Magic Missile",
            school=SpellSchool.EVOCATION,
            level=1,
            effect_callback=lambda caster, target, cl: {"damage": cl + 1},
        )
        registry.register(spell)
        return SpellResolver(
            caster_level=wizard.level,
            key_ability_mod=wizard.intelligence_mod,
            spell_registry=registry,
        )

    def test_cast_spell_success(self):
        wizard = _make_wizard()
        goblin = _make_goblin()
        dispatcher = _make_dispatcher(wizard, goblin)
        tracker = ActionTracker()
        resolver = self._make_spell_resolver(wizard)
        action = AgentAction(
            action_type=AgentActionType.CAST_SPELL,
            spell_name="Magic Missile",
            target_id=goblin.char_id,
        )
        result = dispatcher.dispatch(action, wizard, action_tracker=tracker, spell_resolver=resolver)
        assert result.success is True
        assert result.spell_result is not None
        assert "damage" in result.spell_result
        assert tracker.standard_used is True

    def test_cast_spell_no_resolver_returns_error(self):
        wizard = _make_wizard()
        dispatcher = _make_dispatcher(wizard)
        tracker = ActionTracker()
        action = AgentAction(action_type=AgentActionType.CAST_SPELL, spell_name="Magic Missile")
        result = dispatcher.dispatch(action, wizard, action_tracker=tracker, spell_resolver=None)
        assert result.success is False
        assert "no SpellResolver" in result.error

    def test_cast_spell_unknown_spell_fails(self):
        wizard = _make_wizard()
        dispatcher = _make_dispatcher(wizard)
        tracker = ActionTracker()
        resolver = self._make_spell_resolver(wizard)
        action = AgentAction(
            action_type=AgentActionType.CAST_SPELL,
            spell_name="Wish",
            target_id=None,
        )
        result = dispatcher.dispatch(action, wizard, action_tracker=tracker, spell_resolver=resolver)
        assert result.success is False
        assert "not in spellbook" in result.error

    def test_cast_spell_missing_spell_name_fails(self):
        wizard = _make_wizard()
        dispatcher = _make_dispatcher(wizard)
        tracker = ActionTracker()
        resolver = self._make_spell_resolver(wizard)
        action = AgentAction(action_type=AgentActionType.CAST_SPELL)
        result = dispatcher.dispatch(action, wizard, action_tracker=tracker, spell_resolver=resolver)
        assert result.success is False
        assert "spell_name missing" in result.error


# ---------------------------------------------------------------------------
# ActionDispatcher.dispatch — MOVE
# ---------------------------------------------------------------------------

class TestDispatchMove:
    def test_move_with_destination(self):
        fighter = _make_fighter()
        dispatcher = _make_dispatcher(fighter)
        tracker = ActionTracker()
        action = AgentAction(action_type=AgentActionType.MOVE, destination=[10, 5, 0])
        result = dispatcher.dispatch(action, fighter, action_tracker=tracker)
        assert result.success is True
        assert result.action_cost is ActionType.MOVE
        assert "10" in result.narrative
        assert tracker.move_used is True

    def test_move_without_destination(self):
        fighter = _make_fighter()
        dispatcher = _make_dispatcher(fighter)
        tracker = ActionTracker()
        action = AgentAction(action_type=AgentActionType.MOVE)
        result = dispatcher.dispatch(action, fighter, action_tracker=tracker)
        assert result.success is True
        assert "adjacent" in result.narrative


# ---------------------------------------------------------------------------
# ActionDispatcher.dispatch — SKILL_CHECK
# ---------------------------------------------------------------------------

class TestDispatchSkillCheck:
    def test_skill_check_uses_character_skills_dict(self):
        fighter = _make_fighter()
        # fighter.skills["Climb"] == 8; DC 5 should succeed almost always
        dispatcher = _make_dispatcher(fighter)
        tracker = ActionTracker()
        action = AgentAction(action_type=AgentActionType.SKILL_CHECK, skill_name="Climb", dc=5)
        result = dispatcher.dispatch(action, fighter, action_tracker=tracker)
        assert result.skill_result is not None
        assert result.skill_result.skill_name == "Climb"
        assert result.skill_result.dc == 5
        assert result.action_cost is ActionType.STANDARD

    def test_skill_check_unknown_skill_defaults_to_zero_bonus(self):
        fighter = _make_fighter()
        dispatcher = _make_dispatcher(fighter)
        tracker = ActionTracker()
        action = AgentAction(action_type=AgentActionType.SKILL_CHECK, skill_name="Acrobatics", dc=1)
        result = dispatcher.dispatch(action, fighter, action_tracker=tracker)
        assert result.skill_result is not None

    def test_skill_check_missing_name_returns_error(self):
        fighter = _make_fighter()
        dispatcher = _make_dispatcher(fighter)
        tracker = ActionTracker()
        action = AgentAction(action_type=AgentActionType.SKILL_CHECK)
        result = dispatcher.dispatch(action, fighter, action_tracker=tracker)
        assert result.success is False
        assert "skill_name missing" in result.error

    def test_skill_check_success_flag_matches_roll(self):
        fighter = _make_fighter()
        dispatcher = _make_dispatcher(fighter)
        tracker = ActionTracker()
        action = AgentAction(action_type=AgentActionType.SKILL_CHECK, skill_name="Climb", dc=5)
        result = dispatcher.dispatch(action, fighter, action_tracker=tracker)
        assert result.success == result.skill_result.success


# ---------------------------------------------------------------------------
# ActionDispatcher.dispatch — USE_ITEM
# ---------------------------------------------------------------------------

class TestDispatchUseItem:
    def test_use_item_in_equipment(self):
        fighter = _make_fighter()
        dispatcher = _make_dispatcher(fighter)
        tracker = ActionTracker()
        action = AgentAction(action_type=AgentActionType.USE_ITEM, item_name="Potion of Healing")
        result = dispatcher.dispatch(action, fighter, action_tracker=tracker)
        assert result.success is True
        assert "Potion of Healing" in result.narrative

    def test_use_item_not_in_equipment(self):
        fighter = _make_fighter()
        dispatcher = _make_dispatcher(fighter)
        tracker = ActionTracker()
        action = AgentAction(action_type=AgentActionType.USE_ITEM, item_name="Wand of Fireball")
        result = dispatcher.dispatch(action, fighter, action_tracker=tracker)
        assert result.success is False
        assert "not in equipment" in result.error


# ---------------------------------------------------------------------------
# ActionDispatcher.dispatch — TOTAL_DEFENSE, DELAY, FIVE_FOOT_STEP
# ---------------------------------------------------------------------------

class TestDispatchUtilityActions:
    def test_total_defense(self):
        fighter = _make_fighter()
        dispatcher = _make_dispatcher(fighter)
        tracker = ActionTracker()
        action = AgentAction(action_type=AgentActionType.TOTAL_DEFENSE)
        result = dispatcher.dispatch(action, fighter, action_tracker=tracker)
        assert result.success is True
        assert "+4" in result.narrative
        assert str(fighter.armor_class + 4) in result.narrative
        assert tracker.standard_used is True

    def test_delay_costs_no_action(self):
        fighter = _make_fighter()
        dispatcher = _make_dispatcher(fighter)
        tracker = ActionTracker()
        action = AgentAction(action_type=AgentActionType.DELAY)
        result = dispatcher.dispatch(action, fighter, action_tracker=tracker)
        assert result.success is True
        assert result.action_cost is ActionType.FREE
        assert tracker.standard_used is False

    def test_five_foot_step_with_destination(self):
        fighter = _make_fighter()
        dispatcher = _make_dispatcher(fighter)
        tracker = ActionTracker()
        action = AgentAction(action_type=AgentActionType.FIVE_FOOT_STEP, destination=[5, 3, 0])
        result = dispatcher.dispatch(action, fighter, action_tracker=tracker)
        assert result.success is True
        assert result.action_cost is ActionType.FREE
        assert "attacks of opportunity" in result.narrative
        assert tracker.standard_used is False

    def test_five_foot_step_without_destination(self):
        fighter = _make_fighter()
        dispatcher = _make_dispatcher(fighter)
        tracker = ActionTracker()
        action = AgentAction(action_type=AgentActionType.FIVE_FOOT_STEP)
        result = dispatcher.dispatch(action, fighter, action_tracker=tracker)
        assert "adjacent square" in result.narrative


# ---------------------------------------------------------------------------
# ActionDispatcher.dispatch_task
# ---------------------------------------------------------------------------

class TestDispatchTask:
    def test_dispatch_task_reads_actor_from_context(self):
        fighter = _make_fighter()
        goblin = _make_goblin()
        dispatcher = _make_dispatcher(fighter, goblin)
        tracker_map = {fighter.char_id: ActionTracker()}
        task = AgentTask(
            task_type=TaskType.AGENT_DECISION.value,
            prompt="What do you do?",
            context={"actor_id": fighter.char_id},
        )
        task.mark_in_progress()
        task.complete({"action_type": "attack", "target_id": goblin.char_id})
        result = dispatcher.dispatch_task(task, action_tracker_map=tracker_map)
        assert isinstance(result, DispatchResult)
        assert result.action_type is AgentActionType.ATTACK

    def test_dispatch_task_raises_if_no_result(self):
        fighter = _make_fighter()
        dispatcher = _make_dispatcher(fighter)
        task = AgentTask(
            task_type=TaskType.AGENT_DECISION.value,
            prompt="What do you do?",
            context={"actor_id": fighter.char_id},
        )
        with pytest.raises(ValueError, match="no result"):
            dispatcher.dispatch_task(task, action_tracker_map={fighter.char_id: ActionTracker()})

    def test_dispatch_task_raises_if_actor_not_in_registry(self):
        dispatcher = ActionDispatcher()
        task = AgentTask(
            task_type=TaskType.AGENT_DECISION.value,
            prompt="What do you do?",
            context={"actor_id": "missing_id"},
        )
        task.mark_in_progress()
        task.complete({"action_type": "delay"})
        with pytest.raises(KeyError):
            dispatcher.dispatch_task(task, action_tracker_map={"missing_id": ActionTracker()})


# ---------------------------------------------------------------------------
# LLMTaskRunner integration — AGENT_DECISION validation hook
# ---------------------------------------------------------------------------

class TestLLMTaskRunnerAgentDecision:
    def _make_runner(self, payload: str) -> tuple:
        sched = Scheduler()
        task = AgentTask(
            task_type=TaskType.AGENT_DECISION.value,
            prompt="Decide your action.",
            context={"actor_id": "fighter_1"},
            max_retries=0,
        )
        sched.submit(task)
        dispatcher = ActionDispatcher()
        runner = LLMTaskRunner(
            scheduler=sched,
            prompt_builder=PromptBuilder(),
            result_parser=ResultParser(),
            completion_fn=lambda msgs: payload,
            action_dispatcher=dispatcher,
        )
        return runner, task

    def test_valid_agent_decision_completes(self):
        payload = json.dumps({"action_type": "attack", "target_id": "goblin_1"})
        runner, task = self._make_runner(payload)
        runner.run_one_sync()
        assert task.status is TaskStatus.COMPLETED
        assert task.result["action_type"] == "attack"

    def test_invalid_action_type_fails_task(self):
        payload = json.dumps({"action_type": "breathe_fire"})
        runner, task = self._make_runner(payload)
        runner.run_one_sync()
        assert task.status is TaskStatus.FAILED
        assert task.error is not None
        assert "action_type" in task.error

    def test_missing_action_type_fails_task(self):
        payload = json.dumps({"target_id": "orc_3"})
        runner, task = self._make_runner(payload)
        runner.run_one_sync()
        assert task.status is TaskStatus.FAILED

    def test_no_dispatcher_skips_validation(self):
        payload = json.dumps({"action_type": "breathe_fire"})
        sched = Scheduler()
        task = AgentTask(
            task_type=TaskType.AGENT_DECISION.value,
            prompt="Decide.",
            max_retries=0,
        )
        sched.submit(task)
        runner = LLMTaskRunner(
            scheduler=sched,
            prompt_builder=PromptBuilder(),
            result_parser=ResultParser(),
            completion_fn=lambda msgs: payload,
            action_dispatcher=None,
        )
        runner.run_one_sync()
        # Without a dispatcher, no decode validation — task completes with raw data.
        assert task.status is TaskStatus.COMPLETED


# ---------------------------------------------------------------------------
# Registry helpers
# ---------------------------------------------------------------------------

class TestRegistry:
    def test_register_and_get(self):
        fighter = _make_fighter()
        dispatcher = ActionDispatcher()
        dispatcher.register(fighter)
        assert dispatcher.get_entity(fighter.char_id) is fighter

    def test_register_many(self):
        chars = [_make_fighter(), _make_goblin()]
        dispatcher = ActionDispatcher()
        dispatcher.register_many(chars)
        for c in chars:
            assert dispatcher.get_entity(c.char_id) is c

    def test_get_nonexistent_returns_none(self):
        dispatcher = ActionDispatcher()
        assert dispatcher.get_entity("nonexistent") is None
