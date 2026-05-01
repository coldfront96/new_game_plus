"""
src/rules_engine/encounter.py
------------------------------
D&D 3.5e DMG Encounter Calculator.

Implements:
- CR → XP table (DMG Table 2-1)
- Encounter Level (EL) calculation from a group of monsters
- Per-character XP distribution with APL adjustment (DMG Table 2-2)

Usage::

    from src.rules_engine.encounter import (
        CR_TO_XP, xp_for_cr, xp_per_character,
        calculate_el, distribute_xp,
    )

    el = calculate_el([3.0, 3.0, 3.0, 3.0])   # four CR 3 monsters → EL 7
    xp = distribute_xp(el, [5, 5, 5, 5])
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# ChallengeRating dataclass (T-010)
# ---------------------------------------------------------------------------

@dataclass(slots=True, frozen=True, order=True)
class ChallengeRating:
    """A typed wrapper around a CR numeric value.

    Supports equality and ordering so CR values can be compared directly
    (e.g. ``ChallengeRating(3.0) < ChallengeRating(7.0)``).

    Common fractional CRs use the nearest float:
    - CR 1/8  → 0.125
    - CR 1/6  → 0.167
    - CR 1/4  → 0.25
    - CR 1/3  → 0.33
    - CR 1/2  → 0.5
    """
    value: float

    @classmethod
    def from_fraction(cls, numerator: int, denominator: int) -> "ChallengeRating":
        return cls(value=round(numerator / denominator, 3))

    def xp(self) -> int:
        """Return the base XP award for this CR (DMG Table 2-1)."""
        return xp_for_cr(self.value)

    def __str__(self) -> str:
        if self.value == 0.125:
            return "CR 1/8"
        if self.value == 0.167:
            return "CR 1/6"
        if self.value == 0.25:
            return "CR 1/4"
        if self.value == 0.33:
            return "CR 1/3"
        if self.value == 0.5:
            return "CR 1/2"
        return f"CR {int(self.value)}" if self.value == int(self.value) else f"CR {self.value}"


# EncounterLevel is semantically equivalent: same numeric domain, same table.
EncounterLevel = ChallengeRating


# ---------------------------------------------------------------------------
# CR → XP Table (DMG Table 2-1)
# ---------------------------------------------------------------------------

CR_TO_XP: dict[float, int] = {
    0.125: 50,
    0.167: 65,
    0.25:  100,
    0.33:  135,
    0.5:   200,
    1:     300,
    2:     600,
    3:     800,
    4:     1_200,
    5:     1_600,
    6:     2_400,
    7:     3_200,
    8:     4_800,
    9:     6_400,
    10:    9_600,
    11:    12_800,
    12:    19_200,
    13:    25_600,
    14:    38_400,
    15:    51_200,
    16:    76_800,
    17:    102_400,
    18:    153_600,
    19:    204_800,
    20:    307_200,
    21:    409_600,
    22:    614_400,
    23:    819_200,
    24:    1_228_800,
    25:    1_638_400,
    26:    2_457_600,
    27:    3_276_800,
    28:    4_915_200,
    29:    6_553_600,
    30:    9_830_400,
}


def _nearest_cr(cr: float) -> float:
    """Return the key in CR_TO_XP nearest to *cr*."""
    return min(CR_TO_XP.keys(), key=lambda k: abs(k - cr))


def xp_for_cr(cr: float) -> int:
    """Return the raw XP value for a given CR from DMG Table 2-1.

    Uses nearest-key lookup so fractional CRs not in the table still work.
    """
    key = _nearest_cr(cr)
    return CR_TO_XP[key]


def xp_per_character(
    cr: float,
    apl: int,
    party_size: int = 4,
) -> int:
    """Return per-character XP for defeating a CR *cr* monster.

    Divides the base XP by *party_size*, then applies an APL-based
    multiplier reflecting how challenging the encounter is.

    Args:
        cr:         Challenge Rating of the monster.
        apl:        Average Party Level (typically mean of character levels).
        party_size: Number of characters (default 4).

    Returns:
        Per-character XP award (floored to int).
    """
    base_xp = xp_for_cr(cr)
    per_char = base_xp / party_size

    diff = apl - int(cr)  # positive = party higher level (easier)

    if diff >= 5:
        mult = 0.0
    elif diff == 4:
        mult = 0.125
    elif diff == 3:
        mult = 0.25
    elif diff == 2:
        mult = 0.5
    elif diff == 1:
        mult = 0.75
    elif diff == 0:
        mult = 1.0
    elif diff == -1:
        mult = 1.5
    elif diff == -2:
        mult = 2.0
    else:  # diff <= -3
        mult = 3.0

    return max(0, int(per_char * mult))


# ---------------------------------------------------------------------------
# Encounter Level (EL) Calculation
# ---------------------------------------------------------------------------

def calculate_el(monster_crs: list[float]) -> float:
    """Calculate the Encounter Level for a group of monsters.

    Algorithm (per DMG p.48):
    1. Sum the XP values of all monsters.
    2. Find the CR whose XP value is closest to that total.

    This correctly handles:
    - Single monster: EL == CR
    - Two same-CR: EL ≈ CR + 2 (XP doubles, next bracket)
    - Four same-CR: EL ≈ CR + 4 (XP quadruples)
    - Mixed groups

    Args:
        monster_crs: List of CR values for each monster in the encounter.

    Returns:
        The Encounter Level as a float (may be a CR key value).
    """
    if not monster_crs:
        return 0.0

    total_xp = sum(xp_for_cr(cr) for cr in monster_crs)

    # Find nearest CR whose XP matches total_xp
    best_cr = min(CR_TO_XP.keys(), key=lambda k: abs(CR_TO_XP[k] - total_xp))
    return float(best_cr)


# ---------------------------------------------------------------------------
# XP Distribution
# ---------------------------------------------------------------------------

def distribute_xp(
    encounter_el: float,
    party_levels: list[int],
) -> dict[int, int]:
    """Distribute XP from an encounter to each party member.

    Per-character base XP is CR_TO_XP[encounter_el] // len(party_levels).
    Characters significantly above or below the APL get adjusted awards:

    - Level ≥ APL + 3: × 0.5  (less challenging for them)
    - Level ≤ APL − 4: × 1.5  (more dangerous for them)
    - Otherwise:       × 1.0

    Args:
        encounter_el:  Encounter Level (EL) as a float.
        party_levels:  List of character levels (one per PC).

    Returns:
        Dict mapping character index → XP award.
    """
    if not party_levels:
        return {}

    apl = sum(party_levels) // len(party_levels)
    el_key = _nearest_cr(encounter_el)
    base_xp_total = CR_TO_XP[el_key]
    per_char_base = base_xp_total // len(party_levels)

    result: dict[int, int] = {}
    for idx, level in enumerate(party_levels):
        if level >= apl + 3:
            mult = 0.5
        elif level <= apl - 4:
            mult = 1.5
        else:
            mult = 1.0
        result[idx] = max(0, int(per_char_base * mult))

    return result
