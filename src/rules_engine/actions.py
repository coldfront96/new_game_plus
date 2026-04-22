"""
src/rules_engine/actions.py
---------------------------
3.5e SRD Action Economy: action types and per-turn action tracker.

In the 3.5e SRD, each 6-second combat round grants a character:
  * 1 Standard action (or 1 Full-Round action in lieu of Standard + Move)
  * 1 Move action
  * 1 Swift action
  * Any number of Free actions (typically not tracked as a resource)

A Full-Round action replaces both the Standard and Move actions for the
round.  Using a Full-Round action therefore exhausts both slots.

Usage::

    from src.rules_engine.actions import ActionType, ActionTracker

    tracker = ActionTracker()
    tracker.consume_action(ActionType.STANDARD)   # OK
    tracker.consume_action(ActionType.STANDARD)   # raises ValueError

    tracker.reset_turn()
    tracker.consume_action(ActionType.FULL_ROUND)
    print(tracker.standard_used)  # True
    print(tracker.move_used)      # True
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


# ---------------------------------------------------------------------------
# ActionType
# ---------------------------------------------------------------------------

class ActionType(Enum):
    """The five action categories defined by the D&D 3.5e SRD.

    Attributes:
        STANDARD:    One standard action per round (attack, cast a spell, etc.).
        MOVE:        One move action per round (move up to speed, draw weapon, etc.).
        SWIFT:       One swift action per round (very fast, nearly instantaneous).
        FREE:        Unlimited free actions per round (drop an item, speak briefly).
        FULL_ROUND:  A full-round action consumes both the Standard and Move slots.
    """

    STANDARD = auto()
    MOVE = auto()
    SWIFT = auto()
    FREE = auto()
    FULL_ROUND = auto()


# ---------------------------------------------------------------------------
# ActionTracker
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ActionTracker:
    """Tracks which actions a character has spent during their current turn.

    A fresh :class:`ActionTracker` (or one that has just had
    :meth:`reset_turn` called) begins with all resource slots available.

    Attributes:
        standard_used:   ``True`` once the Standard action has been spent.
        move_used:       ``True`` once the Move action has been spent.
        swift_used:      ``True`` once the Swift action has been spent.
    """

    standard_used: bool = False
    move_used: bool = False
    swift_used: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reset_turn(self) -> None:
        """Restore all action slots for a new turn.

        Grants: 1 Standard, 1 Move, 1 Swift action.
        Free actions are unlimited and are never tracked.
        """
        self.standard_used = False
        self.move_used = False
        self.swift_used = False

    def consume_action(self, action_type: ActionType) -> None:
        """Spend one action of *action_type*.

        Rules:
          - :attr:`~ActionType.STANDARD`: marks the standard slot as used.
          - :attr:`~ActionType.MOVE`:     marks the move slot as used.
          - :attr:`~ActionType.SWIFT`:    marks the swift slot as used.
          - :attr:`~ActionType.FREE`:     always allowed; no slot is consumed.
          - :attr:`~ActionType.FULL_ROUND`: marks **both** the standard and
            move slots as used (neither must already be spent).

        Raises:
            ValueError: If the requested action slot is already exhausted.
        """
        if action_type == ActionType.STANDARD:
            if self.standard_used:
                raise ValueError(
                    "Standard action already used this turn."
                )
            self.standard_used = True

        elif action_type == ActionType.MOVE:
            if self.move_used:
                raise ValueError(
                    "Move action already used this turn."
                )
            self.move_used = True

        elif action_type == ActionType.SWIFT:
            if self.swift_used:
                raise ValueError(
                    "Swift action already used this turn."
                )
            self.swift_used = True

        elif action_type == ActionType.FREE:
            # Free actions are never resource-limited.
            pass

        elif action_type == ActionType.FULL_ROUND:
            if self.standard_used:
                raise ValueError(
                    "Cannot take a Full-Round action: Standard action already used this turn."
                )
            if self.move_used:
                raise ValueError(
                    "Cannot take a Full-Round action: Move action already used this turn."
                )
            # A full-round action exhausts both Standard and Move slots.
            self.standard_used = True
            self.move_used = True

    # ------------------------------------------------------------------
    # Convenience queries
    # ------------------------------------------------------------------

    def has_action(self, action_type: ActionType) -> bool:
        """Return ``True`` if *action_type* is still available this turn.

        Free actions are always considered available.

        Args:
            action_type: The action type to query.

        Returns:
            ``True`` if the action can still be taken.
        """
        if action_type == ActionType.STANDARD:
            return not self.standard_used
        if action_type == ActionType.MOVE:
            return not self.move_used
        if action_type == ActionType.SWIFT:
            return not self.swift_used
        if action_type == ActionType.FREE:
            return True
        if action_type == ActionType.FULL_ROUND:
            return not self.standard_used and not self.move_used
        return False  # pragma: no cover
