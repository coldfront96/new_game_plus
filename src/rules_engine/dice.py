"""
src/rules_engine/dice.py
------------------------
Dice-rolling utilities for the D&D 3.5e rules engine.

Provides functions for rolling standard polyhedral dice and parsing
damage expressions like ``"2d6+3"``.  All rolls return a
:class:`RollResult` dataclass that tracks the raw roll, applied
modifiers, and the final total — useful for combat logs and debugging.

Usage::

    from src.rules_engine.dice import roll_d20, roll_damage, RollResult

    attack = roll_d20(modifier=7)
    print(attack)        # RollResult(raw=14, modifier=7, total=21)
    print(attack.total)  # 21

    dmg = roll_damage("2d6+3")
    print(dmg.total)     # e.g. 11
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# RollResult
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class RollResult:
    """Immutable record of a single dice roll.

    Attributes:
        raw:      The sum of the dice before any modifier is applied.
        modifier: Flat integer added (or subtracted) after the roll.
        total:    ``raw + modifier`` (floored at 0 for damage-style rolls
                  where a negative total makes no sense — callers may
                  choose to allow negatives for attack rolls).
    """

    raw: int
    modifier: int
    total: int


# ---------------------------------------------------------------------------
# Core rolling helpers
# ---------------------------------------------------------------------------

_DAMAGE_RE = re.compile(
    r"^(?P<count>\d+)[dD](?P<sides>\d+)"
    r"(?:\s*(?P<sign>[+-])\s*(?P<bonus>\d+))?$"
)


def roll_dice(count: int, sides: int, modifier: int = 0) -> RollResult:
    """Roll *count* dice with *sides* faces and add *modifier*.

    Args:
        count:    Number of dice to roll (≥ 1).
        sides:    Number of faces per die (≥ 1).
        modifier: Flat integer added to the sum of all dice.

    Returns:
        A :class:`RollResult` with the raw sum, modifier, and total.

    Raises:
        ValueError: If *count* or *sides* is less than 1.
    """
    if count < 1:
        raise ValueError(f"count must be ≥ 1, got {count}")
    if sides < 1:
        raise ValueError(f"sides must be ≥ 1, got {sides}")
    raw = sum(random.randint(1, sides) for _ in range(count))
    return RollResult(raw=raw, modifier=modifier, total=raw + modifier)


def roll_d20(modifier: int = 0) -> RollResult:
    """Roll a single d20 and add *modifier*.

    This is the most common roll in D&D 3.5e — attack rolls, ability
    checks, saving throws, etc.

    Args:
        modifier: Flat bonus (or penalty) added to the d20 result.

    Returns:
        A :class:`RollResult`.
    """
    return roll_dice(1, 20, modifier)


def roll_damage(expression: str) -> RollResult:
    """Parse and roll a damage expression such as ``"2d6+3"``.

    Supported formats::

        "NdS"       →  roll N dice with S sides, no modifier
        "NdS+M"     →  roll N dice with S sides, add M
        "NdS-M"     →  roll N dice with S sides, subtract M

    The total is **not** clamped — callers may enforce a minimum of 1
    damage themselves when appropriate.

    Args:
        expression: Dice expression string.

    Returns:
        A :class:`RollResult`.

    Raises:
        ValueError: If *expression* cannot be parsed.
    """
    match = _DAMAGE_RE.match(expression.strip())
    if not match:
        raise ValueError(f"Invalid dice expression: {expression!r}")

    count = int(match.group("count"))
    sides = int(match.group("sides"))
    sign = match.group("sign")
    bonus = int(match.group("bonus")) if match.group("bonus") else 0
    if sign == "-":
        bonus = -bonus

    return roll_dice(count, sides, bonus)
