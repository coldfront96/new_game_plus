"""
src/rules_engine/traps.py
--------------------------
D&D 3.5e DMG Chapter 3 — Trap Schema, Search, and Disable mechanics.

Covers:
- T-004: TrapBase dataclass and supporting enums
- T-016: resolve_trap_search / find_trap_active
- T-017: resolve_trap_disable
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


# ---------------------------------------------------------------------------
# T-004: Enums
# ---------------------------------------------------------------------------

class TrapType(Enum):
    """Whether a trap is mundane or magical in origin."""

    MECHANICAL = "mechanical"
    MAGIC = "magic"


class TriggerType(Enum):
    """How a trap is set off."""

    LOCATION = "location"
    PROXIMITY = "proximity"
    TOUCH = "touch"
    SOUND = "sound"
    VISUAL = "visual"
    TIMED = "timed"


class ResetType(Enum):
    """How (or whether) a trap resets after firing."""

    NO_RESET = "no_reset"
    REPAIR = "repair"
    AUTOMATIC = "automatic"
    MANUAL = "manual"


class DisableResult(Enum):
    """Outcome of a Disable Device attempt."""

    DISABLED = "disabled"
    FAILED = "failed"
    TRIGGERED = "triggered"


# ---------------------------------------------------------------------------
# T-004: TrapBase dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class TrapBase:
    """Core trap definition following DMG trap stat-block conventions.

    Attributes:
        name:       Descriptive name of the trap.
        cr:         Challenge Rating (may be fractional, e.g. ``0.5``).
        trap_type:  :class:`TrapType` — mechanical or magical.
        trigger:    :class:`TriggerType` — how the trap fires.
        reset:      :class:`ResetType` — how (if at all) the trap resets.
        search_dc:  DC to *find* the trap with a Search check.
        disable_dc: DC to *disable* the trap with a Disable Device check.
    """

    name: str
    cr: float
    trap_type: TrapType
    trigger: TriggerType
    reset: ResetType
    search_dc: int
    disable_dc: int


# ---------------------------------------------------------------------------
# T-016: Trap search resolvers
# ---------------------------------------------------------------------------

def resolve_trap_search(trap: TrapBase, searcher_spot_total: int) -> bool:
    """Passive detection check (10 + Search modifier vs. search_dc).

    Args:
        trap:                 The trap being searched for.
        searcher_spot_total:  Total Search modifier (Spot used as proxy).

    Returns:
        ``True`` if the passive check meets or exceeds the trap's search DC.
    """
    passive = 10 + searcher_spot_total
    return passive >= trap.search_dc


def find_trap_active(trap: TrapBase, active_roll: int) -> bool:
    """Active Search check (d20 already rolled and added to modifier).

    Args:
        trap:         The trap being searched for.
        active_roll:  Full d20 + Search modifier result.

    Returns:
        ``True`` if the active roll meets or exceeds the trap's search DC.
    """
    return active_roll >= trap.search_dc


# ---------------------------------------------------------------------------
# T-017: Trap disable resolver
# ---------------------------------------------------------------------------

def resolve_trap_disable(trap: TrapBase, disable_roll: int) -> DisableResult:
    """Disable Device check against the trap's disable DC.

    Per DMG rules, failing by 5 or more accidentally triggers the trap.

    Args:
        trap:          The trap being disabled.
        disable_roll:  Full d20 + Disable Device modifier result.

    Returns:
        :class:`DisableResult` — DISABLED, FAILED, or TRIGGERED.
    """
    if disable_roll >= trap.disable_dc:
        return DisableResult.DISABLED
    elif disable_roll <= trap.disable_dc - 5:
        return DisableResult.TRIGGERED
    else:
        return DisableResult.FAILED
