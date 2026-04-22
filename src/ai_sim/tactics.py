"""
src/ai_sim/tactics.py
---------------------
Tactical Combat AI evaluation for D&D 3.5e combat in New Game Plus.

The :class:`TacticalEvaluator` analyses physical constraints *first* —
Line-of-Sight (visually confirmed hostiles) and absolute distance via the
:class:`~src.ai_sim.components.Position` component — before choosing an
action.  Weapon reach and creature movement limits follow strict 3.5e SRD
rules.

Decision logic::

    distance > reach  →  MOVE action (close the gap)
    distance ≤ reach  →  STANDARD action (melee attack)

Usage::

    from src.ai_sim.tactics import TacticalEvaluator, TacticalDecision

    evaluator = TacticalEvaluator(
        actor_entity=orc_entity,
        actor_character=orc_char,
        visible_hostiles=[(fighter_entity, fighter_char)],
        weapon=sword,
    )
    decision = evaluator.evaluate()
    if decision:
        tracker.consume_action(decision.recommended_action)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

from src.ai_sim.components import Position
from src.ai_sim.entity import Entity
from src.loot_math.item import Item
from src.rules_engine.actions import ActionType
from src.rules_engine.character_35e import Character35e


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Scale factor: 1 voxel = 5 feet (standard 3.5e grid)
VOXELS_TO_FEET: float = 5.0

# 3.5e SRD: default natural melee reach for a Medium creature
DEFAULT_REACH_FT: float = 5.0


# ---------------------------------------------------------------------------
# TacticalDecision
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class TacticalDecision:
    """Output of a single :class:`TacticalEvaluator` analysis.

    Attributes:
        primary_target_entity:    The entity selected as the primary target.
        primary_target_character: The target's 3.5e stat block.
        recommended_action:       :class:`~src.rules_engine.actions.ActionType`
                                  the actor should spend this turn —
                                  :attr:`~ActionType.MOVE` to close the gap or
                                  :attr:`~ActionType.STANDARD` to attack.
        distance_ft:              Absolute distance to the primary target in feet.
        reach_ft:                 The actor's effective melee reach in feet.
    """

    primary_target_entity: Entity
    primary_target_character: Character35e
    recommended_action: ActionType
    distance_ft: float
    reach_ft: float


# ---------------------------------------------------------------------------
# TacticalEvaluator
# ---------------------------------------------------------------------------

class TacticalEvaluator:
    """Evaluates the tactical situation for an entity in combat.

    Physical barriers are prioritised in the analysis:

    1. **Line of Sight** — only *visually confirmed* hostiles (passed in by
       the caller, typically from :class:`~src.ai_sim.systems.VisionSystem`)
       are considered.
    2. **Distance** — Euclidean distance in feet between the actor and each
       visible hostile, derived from their
       :class:`~src.ai_sim.components.Position` components.

    The closest hostile is selected as the primary target.  The recommended
    action then follows strict 3.5e SRD reach rules:

    * ``distance > reach`` → :attr:`~ActionType.MOVE`
    * ``distance ≤ reach`` → :attr:`~ActionType.STANDARD` (attack)

    Args:
        actor_entity:      The ECS entity performing the evaluation.
        actor_character:   The actor's 3.5e stat block.
        visible_hostiles:  List of ``(Entity, Character35e)`` pairs that the
                           actor can currently see.  This list should be
                           pre-filtered by a :class:`VisionSystem` check.
        weapon:            The actor's equipped weapon, used to determine reach.
                           Reads ``weapon.metadata["reach_ft"]`` when present;
                           defaults to :data:`DEFAULT_REACH_FT` (5 ft).
    """

    def __init__(
        self,
        actor_entity: Entity,
        actor_character: Character35e,
        visible_hostiles: List[Tuple[Entity, Character35e]],
        weapon: Optional[Item] = None,
    ) -> None:
        self._actor_entity = actor_entity
        self._actor_character = actor_character
        self._visible_hostiles = visible_hostiles
        self._weapon = weapon

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _distance_ft(pos_a: Position, pos_b: Position) -> float:
        """Euclidean distance between two positions in feet (1 voxel = 5 ft).

        Args:
            pos_a: Observer position.
            pos_b: Target position.

        Returns:
            Distance in feet.
        """
        dx = pos_a.x - pos_b.x
        dy = pos_a.y - pos_b.y
        dz = pos_a.z - pos_b.z
        return math.sqrt(dx * dx + dy * dy + dz * dz) * VOXELS_TO_FEET

    @staticmethod
    def _weapon_reach_ft(weapon: Optional[Item]) -> float:
        """Return the weapon's reach in feet from its metadata, or 5 ft.

        Reads ``weapon.metadata["reach_ft"]`` when present.  Per the 3.5e SRD,
        standard melee weapons threaten a 5 ft radius; reach weapons threaten
        10 ft for Medium creatures.

        Args:
            weapon: The actor's equipped weapon, or ``None`` for unarmed.

        Returns:
            Reach in feet.
        """
        if weapon is None:
            return DEFAULT_REACH_FT
        return float(weapon.metadata.get("reach_ft", DEFAULT_REACH_FT))

    # ------------------------------------------------------------------
    # Core evaluation
    # ------------------------------------------------------------------

    def evaluate(self) -> Optional[TacticalDecision]:
        """Evaluate the current combat situation and return a decision.

        The evaluation proceeds in two physical-constraint passes:

        1. Distance to each visible hostile is measured (absolute Euclidean
           distance, not path distance).
        2. The closest hostile is selected; their distance is compared against
           the actor's weapon reach.

        Returns:
            A :class:`TacticalDecision`, or ``None`` if there are no visible
            hostiles or the actor lacks a :class:`Position` component.
        """
        if not self._visible_hostiles:
            return None

        actor_pos: Optional[Position] = self._actor_entity.get_component(Position)
        if actor_pos is None:
            return None

        # --- Select primary target: closest absolute distance ----------------
        best_pair: Optional[Tuple[Entity, Character35e]] = None
        best_dist: float = float("inf")

        for hostile_entity, hostile_char in self._visible_hostiles:
            if not hostile_entity.is_active:
                continue
            target_pos: Optional[Position] = hostile_entity.get_component(Position)
            if target_pos is None:
                continue
            dist = self._distance_ft(actor_pos, target_pos)
            if dist < best_dist:
                best_dist = dist
                best_pair = (hostile_entity, hostile_char)

        if best_pair is None:
            return None

        reach = self._weapon_reach_ft(self._weapon)

        # --- Action decision: physical distance vs. weapon reach -------------
        if best_dist > reach:
            action = ActionType.MOVE
        else:
            action = ActionType.STANDARD

        return TacticalDecision(
            primary_target_entity=best_pair[0],
            primary_target_character=best_pair[1],
            recommended_action=action,
            distance_ft=best_dist,
            reach_ft=reach,
        )
