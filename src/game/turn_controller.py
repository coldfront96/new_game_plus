"""
src/game/turn_controller.py
---------------------------
Initiative + action-economy controller (Task 4).

Given a list of combatants, the :class:`TurnController`:

1. Rolls initiative for everyone (``d20 + DEX mod + Improved Initiative``).
2. Builds a round order (highest initiative first; ties broken by a
   secondary d20 or by DEX).
3. Loops over the order granting each combatant an
   :class:`~src.rules_engine.actions.ActionTracker` that is reset at the
   start of their turn.
4. Ticks the :class:`~src.rules_engine.conditions.ConditionManager` at
   end-of-round so duration-bound conditions decrement.

The class is deliberately agnostic of how actions are *chosen* — it only
manages the ordering and the per-turn tracker.  Higher-level loops (see
:mod:`src.game.session`) plug in decisions via the ``action_callback``.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional

from src.core.event_bus import EventBus
from src.rules_engine.actions import ActionTracker
from src.rules_engine.character_35e import Character35e
from src.rules_engine.conditions import ConditionManager


# ---------------------------------------------------------------------------
# InitiativeEntry
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class InitiativeEntry:
    """Single row in the turn order.

    Attributes:
        combatant:   The :class:`Character35e` taking the turn.
        initiative:  Final initiative value (d20 + DEX + feats).
        tiebreak:    Secondary sort key (raw d20) used when initiatives tie.
    """

    combatant: Character35e
    initiative: int
    tiebreak: int


def roll_initiative(
    combatants: Iterable[Character35e],
    rng: Optional[random.Random] = None,
) -> List[InitiativeEntry]:
    """Roll initiative for every combatant, highest first.

    A secondary d20 is rolled to break ties so the order is deterministic
    under a seeded RNG.

    Args:
        combatants: Iterable of characters entering combat.
        rng:        RNG source (defaults to a fresh :class:`random.Random`).

    Returns:
        List of :class:`InitiativeEntry`, already sorted in turn order.
    """
    rng = rng or random.Random()
    entries: List[InitiativeEntry] = []
    for combatant in combatants:
        roll = rng.randint(1, 20)
        total = roll + combatant.initiative
        tiebreak = rng.randint(1, 20)
        entries.append(
            InitiativeEntry(
                combatant=combatant,
                initiative=total,
                tiebreak=tiebreak,
            )
        )
    entries.sort(
        key=lambda e: (e.initiative, e.tiebreak, e.combatant.dexterity_mod),
        reverse=True,
    )
    return entries


# ---------------------------------------------------------------------------
# TurnController
# ---------------------------------------------------------------------------

# An ``action_callback`` receives the active combatant and its tracker,
# and returns ``True`` if the combatant wishes to end its turn early.
ActionCallback = Callable[[Character35e, ActionTracker], bool]


@dataclass
class TurnController:
    """Drive the initiative + action-economy loop.

    Attributes:
        order:               Initiative-sorted list of combatants.
        action_trackers:     One :class:`ActionTracker` per combatant
                             (keyed by ``char_id``).
        condition_manager:   Shared :class:`ConditionManager` ticked at end of
                             round.
        event_bus:           Optional :class:`EventBus` for round/turn events.
        round_counter:       Current round (1-indexed).
        is_alive:            Callable returning whether a combatant is still
                             able to act (defaults to: HP > 0).
    """

    order: List[InitiativeEntry]
    condition_manager: ConditionManager = field(default_factory=ConditionManager)
    event_bus: Optional[EventBus] = None
    round_counter: int = 0
    is_alive: Callable[[Character35e], bool] = field(
        default=lambda c: c.metadata.get("current_hp", c.hit_points) > 0
    )
    action_trackers: Dict[str, ActionTracker] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for entry in self.order:
            self.action_trackers.setdefault(
                entry.combatant.char_id, ActionTracker()
            )

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------

    @classmethod
    def from_combatants(
        cls,
        combatants: Iterable[Character35e],
        *,
        rng: Optional[random.Random] = None,
        condition_manager: Optional[ConditionManager] = None,
        event_bus: Optional[EventBus] = None,
    ) -> "TurnController":
        order = roll_initiative(combatants, rng)
        return cls(
            order=order,
            condition_manager=condition_manager or ConditionManager(),
            event_bus=event_bus,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def tracker_for(self, combatant: Character35e) -> ActionTracker:
        """Return the :class:`ActionTracker` for *combatant*."""
        return self.action_trackers.setdefault(
            combatant.char_id, ActionTracker()
        )

    def start_round(self) -> int:
        """Advance to the next round.  Returns the new round number."""
        self.round_counter += 1
        if self.event_bus is not None:
            self.event_bus.publish("round_started", {
                "round": self.round_counter,
            })
        return self.round_counter

    def end_round(self) -> List[Dict[str, object]]:
        """Tick conditions at end of round; return expired event dicts."""
        expired = self.condition_manager.tick()
        if self.event_bus is not None:
            self.event_bus.publish("round_ended", {
                "round": self.round_counter,
                "expired": expired,
            })
        return expired

    def run_round(self, action_callback: ActionCallback) -> None:
        """Run a single round, calling *action_callback* for each combatant.

        Combatants who fail :attr:`is_alive` or who have the
        ``cannot_act`` condition are skipped.
        """
        self.start_round()
        for entry in self.order:
            combatant = entry.combatant
            if not self.is_alive(combatant):
                continue
            if self.condition_manager.cannot_act(combatant):
                continue
            tracker = self.tracker_for(combatant)
            tracker.reset_turn()
            if self.event_bus is not None:
                self.event_bus.publish("turn_started", {
                    "round": self.round_counter,
                    "char_id": combatant.char_id,
                    "name": combatant.name,
                    "initiative": entry.initiative,
                })
            end_early = action_callback(combatant, tracker)
            if self.event_bus is not None:
                self.event_bus.publish("turn_ended", {
                    "round": self.round_counter,
                    "char_id": combatant.char_id,
                    "name": combatant.name,
                })
            if end_early is True:
                # ``action_callback`` returning True indicates the caller
                # wants to abort the round (e.g. combat just ended).
                break
        self.end_round()
