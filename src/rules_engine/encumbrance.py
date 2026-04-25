"""
src/rules_engine/encumbrance.py
--------------------------------
D&D 3.5e Encumbrance Physics subsystem.

Implements the carrying-capacity and load-penalty rules from PHB Chapter 9
(Carrying Capacity, Table 9-1 and Table 9-2).

Tier 0 — Base schemas & enums (no external dependencies beyond stdlib).

    * :class:`LoadCategory` — Light / Medium / Heavy / Overload
    * :class:`LiftCategory` — LiftOverHead / LiftOffGround / PushOrDrag
    * :class:`CarryingCapacityRow` — per-Strength lookup row
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


# ---------------------------------------------------------------------------
# Load Category
# ---------------------------------------------------------------------------

class LoadCategory(Enum):
    """Encumbrance load category derived from carried weight vs. capacity.

    PHB Ch 9, Table 9-2.

    * ``Light``    — weight ≤ light_max_lb; no speed/AC/skill penalty.
    * ``Medium``   — light_max < weight ≤ medium_max; max Dex +3, ACP −3,
                     speed penalty (30 ft → 20 ft; 20 ft → 15 ft).
    * ``Heavy``    — medium_max < weight ≤ heavy_max; max Dex +1, ACP −6,
                     speed penalty (30 ft → 20 ft; 20 ft → 15 ft),
                     run ×3 only (not ×4).
    * ``Overload`` — weight > heavy_max; character cannot move voluntarily.
    """

    Light = auto()
    Medium = auto()
    Heavy = auto()
    Overload = auto()


# ---------------------------------------------------------------------------
# Lift Category
# ---------------------------------------------------------------------------

class LiftCategory(Enum):
    """One-time lifting actions distinct from sustained carrying load.

    PHB Ch 9 — "Lifting and Dragging" sidebar.

    * ``LiftOverHead``  — maximum weight the character can hoist overhead
                          equals the heavy-load maximum (= carrying capacity
                          heavy_max_lb).
    * ``LiftOffGround`` — max weight lifted off the ground = 2 × heavy_max.
    * ``PushOrDrag``    — max weight pushed or dragged across floor = 5 × heavy_max.
    """

    LiftOverHead = auto()
    LiftOffGround = auto()
    PushOrDrag = auto()


# ---------------------------------------------------------------------------
# Carrying Capacity Row Schema (E-002)
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class CarryingCapacityRow:
    """One row of PHB Table 9-1 — carrying limits for a single Strength score.

    For Strength values 1–29 the table is looked up explicitly; for STR 30+
    the values are computed by applying a ×4 multiplier per additional +10
    Strength above 29 (documented in the PHB Ch 9 footnote).

    Attributes:
        strength:      The Strength score this row applies to (1–29 explicit;
                       30+ computed).
        light_max_lb:  Maximum load in pounds for a Light load category.
        medium_max_lb: Maximum load in pounds for a Medium load category.
        heavy_max_lb:  Maximum load in pounds for a Heavy load category
                       (also equals the maximum overhead lift weight).
    """

    strength: int
    light_max_lb: float
    medium_max_lb: float
    heavy_max_lb: float
