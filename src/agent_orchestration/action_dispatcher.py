"""
src/agent_orchestration/action_dispatcher.py
--------------------------------------------
Last-mile resolver: translates a validated LLM AgentDecision payload into
actual D&D 3.5e rules-engine calls and returns a structured DispatchResult.

This closes the autonomous-AI-agency loop:

    CognitiveState → LLMClient → ResultParser → ActionDispatcher
                                                       │
                                          AttackResolver / SpellResolver
                                          SkillSystem / ActionTracker
                                                       │
                                                 DispatchResult
                                                       │
                                              OverseerQueue (on failure)

Decision JSON schema (task_type = "agent_decision")
----------------------------------------------------
Required:
    action_type   str   One of the AgentActionType string values.

Optional (presence depends on action_type):
    target_id     str   Entity ID of the primary target.
    spell_name    str   Spell name for CAST_SPELL actions.
    use_ranged    bool  True to resolve a ranged attack instead of melee.
    skill_name    str   Skill name for SKILL_CHECK actions.
    dc            int   Difficulty Class for SKILL_CHECK actions (default 10).
    destination   list  [x, y, z] voxel coordinates for MOVE actions.
    item_name     str   Item name for USE_ITEM actions.

Example agent decision payloads
--------------------------------
Attack:
    {"action_type": "attack", "target_id": "orc_001"}

Full attack:
    {"action_type": "full_attack", "target_id": "orc_001", "use_ranged": false}

Cast spell:
    {"action_type": "cast_spell", "spell_name": "Magic Missile", "target_id": "orc_001"}

Skill check:
    {"action_type": "skill_check", "skill_name": "Spot", "dc": 15}

Move:
    {"action_type": "move", "destination": [10, 5, 3]}

Total defense:
    {"action_type": "total_defense"}

Delay:
    {"action_type": "delay"}

Five-foot step:
    {"action_type": "five_foot_step", "destination": [11, 5, 3]}

Use item:
    {"action_type": "use_item", "item_name": "Potion of Healing"}
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from src.agent_orchestration.agent_task import AgentTask
from src.rules_engine.actions import ActionTracker, ActionType
from src.rules_engine.character_35e import Character35e
from src.rules_engine.combat import AttackResolver, CombatResult
from src.rules_engine.dice import roll_d20, roll_damage
from src.rules_engine.skills import SkillCheckResult
from src.rules_engine.spellcasting import SpellResolver


# Metadata keys — must match session.py HP_KEY / DEAD_KEY constants.
_HP_KEY = "current_hp"
_DEAD_KEY = "dead"


def _apply_hp_damage(target: Character35e, amount: int) -> None:
    """Reduce *target*'s current HP by *amount* and mark dead if it hits zero."""
    from src.game.session import apply_damage
    apply_damage(target, amount)


# ---------------------------------------------------------------------------
# AgentActionType
# ---------------------------------------------------------------------------

class AgentActionType(str, Enum):
    """All in-game actions an autonomous agent may declare on its turn."""

    ATTACK = "attack"
    FULL_ATTACK = "full_attack"
    CAST_SPELL = "cast_spell"
    MOVE = "move"
    SKILL_CHECK = "skill_check"
    USE_ITEM = "use_item"
    TOTAL_DEFENSE = "total_defense"
    DELAY = "delay"
    FIVE_FOOT_STEP = "five_foot_step"


# ---------------------------------------------------------------------------
# AgentAction
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class AgentAction:
    """A decoded, validated in-game action ready for mechanical dispatch.

    Attributes:
        action_type:  Category of action being taken.
        target_id:    Entity ID of the primary target (attacks, spells).
        spell_name:   Spell name for CAST_SPELL actions.
        use_ranged:   If True, resolve as a ranged attack.
        skill_name:   Skill name for SKILL_CHECK actions.
        dc:           Difficulty Class for SKILL_CHECK actions.
        destination:  Voxel [x, y, z] coordinates for MOVE / FIVE_FOOT_STEP.
        item_name:    Item name for USE_ITEM actions.
    """

    action_type: AgentActionType
    target_id: Optional[str] = None
    spell_name: Optional[str] = None
    use_ranged: bool = False
    skill_name: Optional[str] = None
    dc: int = 10
    destination: Optional[List[int]] = None
    item_name: Optional[str] = None


# ---------------------------------------------------------------------------
# DispatchResult
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class DispatchResult:
    """Mechanical outcome of a dispatched agent action.

    Attributes:
        action_type:    The action that was resolved.
        success:        Whether the action succeeded (hit, check passed, etc.).
        narrative:      Human-readable description of the outcome.
        combat_results: CombatResult objects for ATTACK / FULL_ATTACK actions.
        spell_result:   Effect dict returned by SpellResolver for CAST_SPELL.
        skill_result:   SkillCheckResult for SKILL_CHECK actions.
        action_cost:    The 3.5e ActionType that was consumed this turn.
        damage_dealt:   Total damage dealt across all attacks (0 on miss).
        error:          Non-empty string when the action could not be executed.
    """

    action_type: AgentActionType
    success: bool
    narrative: str
    combat_results: List[CombatResult] = field(default_factory=list)
    spell_result: Optional[Dict[str, Any]] = None
    skill_result: Optional[SkillCheckResult] = None
    action_cost: ActionType = ActionType.STANDARD
    damage_dealt: int = 0
    error: str = ""


# ---------------------------------------------------------------------------
# Decode helpers
# ---------------------------------------------------------------------------

class ActionDecodeError(ValueError):
    """Raised when an LLM response cannot be decoded into a valid AgentAction."""


def decode_action(data: Dict[str, Any]) -> AgentAction:
    """Translate a validated ParseResult.data dict into an AgentAction.

    Args:
        data: The dict produced by ResultParser for an AGENT_DECISION task.

    Returns:
        A fully populated AgentAction.

    Raises:
        ActionDecodeError: If action_type is missing or unrecognised.
    """
    raw_type = data.get("action_type", "")
    try:
        action_type = AgentActionType(raw_type)
    except ValueError:
        known = ", ".join(t.value for t in AgentActionType)
        raise ActionDecodeError(
            f"unknown action_type {raw_type!r}; valid values: {known}"
        )

    destination = data.get("destination")
    if destination is not None and not isinstance(destination, list):
        destination = None

    return AgentAction(
        action_type=action_type,
        target_id=data.get("target_id"),
        spell_name=data.get("spell_name"),
        use_ranged=bool(data.get("use_ranged", False)),
        skill_name=data.get("skill_name"),
        dc=int(data.get("dc", 10)),
        destination=destination,
        item_name=data.get("item_name"),
    )


# ---------------------------------------------------------------------------
# ActionDispatcher
# ---------------------------------------------------------------------------

@dataclass
class ActionDispatcher:
    """Resolves AgentAction objects against the 3.5e rules engine.

    The dispatcher is the single integration point between LLM-generated
    decisions and the physics layer.  It is intentionally stateless with
    respect to mutable game world data — it never stores per-entity HP or
    positions; callers provide all context at dispatch time.

    Attributes:
        entity_registry: Maps entity IDs (char_id) to Character35e instances.
                         Used to look up actors and targets by string ID.
        rng:             Random source injected at construction.  Override
                         in tests for deterministic outcomes.
    """

    entity_registry: Dict[str, Character35e] = field(default_factory=dict)
    rng: Any = field(default_factory=lambda: random)

    # ------------------------------------------------------------------
    # Registry helpers
    # ------------------------------------------------------------------

    def register(self, character: Character35e) -> None:
        """Add *character* to the entity registry keyed by its char_id."""
        self.entity_registry[character.char_id] = character

    def register_many(self, characters: List[Character35e]) -> None:
        """Register multiple characters at once."""
        for character in characters:
            self.register(character)

    def get_entity(self, entity_id: str) -> Optional[Character35e]:
        """Return the character with *entity_id*, or None if not registered."""
        return self.entity_registry.get(entity_id)

    # ------------------------------------------------------------------
    # Primary dispatch entry point
    # ------------------------------------------------------------------

    def dispatch(
        self,
        action: AgentAction,
        actor: Character35e,
        *,
        action_tracker: ActionTracker,
        spell_resolver: Optional[SpellResolver] = None,
    ) -> DispatchResult:
        """Execute *action* on behalf of *actor* against the rules engine.

        Validates the action economy (raises ValueError if the required slot
        is already spent), then delegates to the appropriate resolver.

        Args:
            action:          The decoded action to resolve.
            actor:           The character taking the action.
            action_tracker:  Per-turn action economy tracker; mutated in place.
            spell_resolver:  Required for CAST_SPELL actions.

        Returns:
            A DispatchResult with the full mechanical outcome.

        Raises:
            ValueError: If the required action slot is already exhausted.
        """
        _dispatch_map = {
            AgentActionType.ATTACK:         self._resolve_attack,
            AgentActionType.FULL_ATTACK:    self._resolve_full_attack,
            AgentActionType.CAST_SPELL:     self._resolve_cast_spell,
            AgentActionType.MOVE:           self._resolve_move,
            AgentActionType.SKILL_CHECK:    self._resolve_skill_check,
            AgentActionType.USE_ITEM:       self._resolve_use_item,
            AgentActionType.TOTAL_DEFENSE:  self._resolve_total_defense,
            AgentActionType.DELAY:          self._resolve_delay,
            AgentActionType.FIVE_FOOT_STEP: self._resolve_five_foot_step,
        }
        return _dispatch_map[action.action_type](
            action, actor, action_tracker, spell_resolver
        )

    def dispatch_task(
        self,
        task: AgentTask,
        *,
        action_tracker_map: Dict[str, ActionTracker],
        spell_resolver_map: Optional[Dict[str, SpellResolver]] = None,
    ) -> DispatchResult:
        """Convenience wrapper that reads context from a completed AgentTask.

        Expects ``task.context["actor_id"]`` to identify the acting entity
        and ``task.result`` to be a validated AGENT_DECISION payload.

        Args:
            task:               A COMPLETED AgentTask of type agent_decision.
            action_tracker_map: Maps entity IDs to their ActionTracker.
            spell_resolver_map: Maps entity IDs to their SpellResolver.

        Returns:
            A DispatchResult with the full mechanical outcome.

        Raises:
            KeyError:            If actor_id is missing from task.context or
                                 the entity is not in the registry.
            ValueError:          If task.result is None.
            ActionDecodeError:   If the result payload has an invalid
                                 action_type.
        """
        if task.result is None:
            raise ValueError(
                f"Task {task.task_id[:8]}… has no result to dispatch."
            )
        context = task.context or {}
        actor_id: str = context["actor_id"]
        actor = self.entity_registry[actor_id]
        action = decode_action(task.result)
        tracker = action_tracker_map[actor_id]
        resolver = (spell_resolver_map or {}).get(actor_id)
        return self.dispatch(action, actor, action_tracker=tracker, spell_resolver=resolver)

    # ------------------------------------------------------------------
    # Private resolvers
    # ------------------------------------------------------------------

    def _lookup_target(self, target_id: Optional[str]) -> Optional[Character35e]:
        if not target_id:
            return None
        return self.entity_registry.get(target_id)

    def _resolve_attack(
        self,
        action: AgentAction,
        actor: Character35e,
        tracker: ActionTracker,
        spell_resolver: Optional[SpellResolver],
    ) -> DispatchResult:
        tracker.consume_action(ActionType.STANDARD)
        target = self._lookup_target(action.target_id)
        if target is None:
            return DispatchResult(
                action_type=action.action_type,
                success=False,
                narrative=f"{actor.name} attacks but finds no valid target in range.",
                action_cost=ActionType.STANDARD,
                error="target not found",
            )
        result = AttackResolver.resolve_attack(actor, target, use_ranged=action.use_ranged)
        if result.hit:
            _apply_hp_damage(target, result.total_damage)
        return DispatchResult(
            action_type=action.action_type,
            success=result.hit,
            narrative=_narrate_attack(actor.name, target.name, result),
            combat_results=[result],
            action_cost=ActionType.STANDARD,
            damage_dealt=result.total_damage,
        )

    def _resolve_full_attack(
        self,
        action: AgentAction,
        actor: Character35e,
        tracker: ActionTracker,
        spell_resolver: Optional[SpellResolver],
    ) -> DispatchResult:
        tracker.consume_action(ActionType.FULL_ROUND)
        target = self._lookup_target(action.target_id)
        if target is None:
            return DispatchResult(
                action_type=action.action_type,
                success=False,
                narrative=f"{actor.name} attempts a full attack but no valid target is in range.",
                action_cost=ActionType.FULL_ROUND,
                error="target not found",
            )
        results = AttackResolver.resolve_full_attack(actor, target, use_ranged=action.use_ranged)
        total_damage = sum(r.total_damage for r in results if r.hit)
        if total_damage:
            _apply_hp_damage(target, total_damage)
        return DispatchResult(
            action_type=action.action_type,
            success=any(r.hit for r in results),
            narrative=_narrate_full_attack(actor.name, target.name, results),
            combat_results=results,
            action_cost=ActionType.FULL_ROUND,
            damage_dealt=total_damage,
        )

    def _resolve_cast_spell(
        self,
        action: AgentAction,
        actor: Character35e,
        tracker: ActionTracker,
        spell_resolver: Optional[SpellResolver],
    ) -> DispatchResult:
        tracker.consume_action(ActionType.STANDARD)
        if spell_resolver is None:
            return DispatchResult(
                action_type=action.action_type,
                success=False,
                narrative=f"{actor.name} reaches for magic but no spell resolver is active.",
                action_cost=ActionType.STANDARD,
                error="no SpellResolver provided",
            )
        if not action.spell_name:
            return DispatchResult(
                action_type=action.action_type,
                success=False,
                narrative=f"{actor.name} attempts to cast but named no spell.",
                action_cost=ActionType.STANDARD,
                error="spell_name missing",
            )
        spellbook = actor.spellbook
        if spellbook is not None and not spellbook.is_known(action.spell_name):
            return DispatchResult(
                action_type=action.action_type,
                success=False,
                narrative=f"{actor.name} does not know {action.spell_name!r}.",
                action_cost=ActionType.STANDARD,
                error=f"spell {action.spell_name!r} not in spellbook",
            )
        target = self._lookup_target(action.target_id)
        spell_result = spell_resolver.resolve_spell(
            action.spell_name, target=target, caster=actor
        )
        if spell_result is None:
            return DispatchResult(
                action_type=action.action_type,
                success=False,
                narrative=(
                    f"{actor.name} casts {action.spell_name} but the effect produces no outcome."
                ),
                action_cost=ActionType.STANDARD,
                error=f"spell {action.spell_name!r} has no effect callback",
            )
        target_label = target.name if target else "the area"
        spell_damage = 0
        if target is not None and isinstance(spell_result, dict):
            raw_dmg = spell_result.get("damage")
            if raw_dmg and isinstance(raw_dmg, str):
                try:
                    spell_damage = roll_damage(raw_dmg).total
                    _apply_hp_damage(target, spell_damage)
                except ValueError:
                    pass
        return DispatchResult(
            action_type=action.action_type,
            success=True,
            narrative=f"{actor.name} casts {action.spell_name} at {target_label}. Effect: {spell_result}",
            spell_result=spell_result,
            action_cost=ActionType.STANDARD,
            damage_dealt=spell_damage,
        )

    def _resolve_move(
        self,
        action: AgentAction,
        actor: Character35e,
        tracker: ActionTracker,
        spell_resolver: Optional[SpellResolver],
    ) -> DispatchResult:
        tracker.consume_action(ActionType.MOVE)
        dest = action.destination
        if dest and len(dest) >= 2:
            actor.metadata["position"] = list(dest)
            coord = ", ".join(str(c) for c in dest)
            narrative = f"{actor.name} moves to [{coord}]."
        else:
            narrative = f"{actor.name} moves to an adjacent position."
        return DispatchResult(
            action_type=action.action_type,
            success=True,
            narrative=narrative,
            action_cost=ActionType.MOVE,
        )

    def _resolve_skill_check(
        self,
        action: AgentAction,
        actor: Character35e,
        tracker: ActionTracker,
        spell_resolver: Optional[SpellResolver],
    ) -> DispatchResult:
        tracker.consume_action(ActionType.STANDARD)
        if not action.skill_name:
            return DispatchResult(
                action_type=action.action_type,
                success=False,
                narrative=f"{actor.name} attempts a skill check but specified no skill.",
                action_cost=ActionType.STANDARD,
                error="skill_name missing",
            )
        # actor.skills holds precomputed total bonuses (rank + ability mod + misc).
        skill_bonus = actor.skills.get(action.skill_name, 0)
        roll = roll_d20(modifier=skill_bonus)
        success = roll.total >= action.dc
        margin = roll.total - action.dc
        skill_result = SkillCheckResult(
            skill_name=action.skill_name,
            roll=roll,
            total=roll.total,
            dc=action.dc,
            success=success,
            margin=margin,
        )
        outcome = "succeeds" if success else "fails"
        sign = "+" if margin >= 0 else ""
        narrative = (
            f"{actor.name} makes a {action.skill_name} check (DC {action.dc}): "
            f"rolled {roll.total} — {outcome} ({sign}{margin})."
        )
        return DispatchResult(
            action_type=action.action_type,
            success=success,
            narrative=narrative,
            skill_result=skill_result,
            action_cost=ActionType.STANDARD,
        )

    def _resolve_use_item(
        self,
        action: AgentAction,
        actor: Character35e,
        tracker: ActionTracker,
        spell_resolver: Optional[SpellResolver],
    ) -> DispatchResult:
        tracker.consume_action(ActionType.STANDARD)
        item_name = action.item_name or "unknown item"
        if item_name not in actor.equipment:
            return DispatchResult(
                action_type=action.action_type,
                success=False,
                narrative=f"{actor.name} reaches for {item_name!r} but doesn't have it.",
                action_cost=ActionType.STANDARD,
                error=f"{item_name!r} not in equipment",
            )
        actor.equipment.remove(item_name)
        return DispatchResult(
            action_type=action.action_type,
            success=True,
            narrative=f"{actor.name} uses {item_name}.",
            action_cost=ActionType.STANDARD,
        )

    def _resolve_total_defense(
        self,
        action: AgentAction,
        actor: Character35e,
        tracker: ActionTracker,
        spell_resolver: Optional[SpellResolver],
    ) -> DispatchResult:
        tracker.consume_action(ActionType.STANDARD)
        return DispatchResult(
            action_type=action.action_type,
            success=True,
            narrative=(
                f"{actor.name} takes Total Defense: +4 dodge bonus to AC "
                f"(effective AC {actor.armor_class + 4}) until their next turn."
            ),
            action_cost=ActionType.STANDARD,
        )

    def _resolve_delay(
        self,
        action: AgentAction,
        actor: Character35e,
        tracker: ActionTracker,
        spell_resolver: Optional[SpellResolver],
    ) -> DispatchResult:
        return DispatchResult(
            action_type=action.action_type,
            success=True,
            narrative=f"{actor.name} delays, waiting for a more opportune moment.",
            action_cost=ActionType.FREE,
        )

    def _resolve_five_foot_step(
        self,
        action: AgentAction,
        actor: Character35e,
        tracker: ActionTracker,
        spell_resolver: Optional[SpellResolver],
    ) -> DispatchResult:
        dest = action.destination
        if dest and len(dest) >= 2:
            coord = ", ".join(str(c) for c in dest)
            narrative = (
                f"{actor.name} takes a 5-foot step to [{coord}], "
                "not provoking attacks of opportunity."
            )
        else:
            narrative = (
                f"{actor.name} takes a 5-foot step to an adjacent square, "
                "not provoking attacks of opportunity."
            )
        return DispatchResult(
            action_type=action.action_type,
            success=True,
            narrative=narrative,
            action_cost=ActionType.FREE,
        )


# ---------------------------------------------------------------------------
# Narrative helpers (pure functions, no side effects)
# ---------------------------------------------------------------------------

def _narrate_attack(attacker: str, defender: str, result: CombatResult) -> str:
    if result.miss_chance_triggered:
        return (
            f"{attacker} swings at {defender} (roll {result.roll.total} vs AC {result.target_ac})"
            " — the blow would have landed but concealment intervenes."
        )
    if not result.hit:
        return (
            f"{attacker} attacks {defender}: rolled {result.roll.total} "
            f"vs AC {result.target_ac} — miss."
        )
    crit_str = " CRITICAL HIT!" if result.critical else ""
    dr_str = (
        f" ({result.damage_reduction_applied} blocked by DR)"
        if result.damage_reduction_applied
        else ""
    )
    return (
        f"{attacker} hits {defender} for {result.total_damage} damage"
        f"{crit_str}{dr_str} "
        f"(roll {result.roll.total} vs AC {result.target_ac})."
    )


def _narrate_full_attack(
    attacker: str, defender: str, results: List[CombatResult]
) -> str:
    lines = [f"{attacker} unleashes a full attack on {defender}:"]
    total = 0
    for i, r in enumerate(results, start=1):
        if r.hit:
            crit = " (CRIT)" if r.critical else ""
            lines.append(f"  Attack {i}: HIT — {r.total_damage} damage{crit}.")
            total += r.total_damage
        else:
            lines.append(
                f"  Attack {i}: Miss (rolled {r.roll.total} vs AC {r.target_ac})."
            )
    if total:
        lines.append(f"  Total damage dealt: {total}.")
    return "\n".join(lines)
