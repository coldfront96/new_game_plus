"""PH5-007 — Night Vision Radius Attenuation.

src/rules_engine/vision.py
---------------------------
Provides vision radius computation that accounts for time-of-day (via
:class:`~src.world_sim.chronos.ChronosRecord`) and character capabilities
(darkvision, light sources).

Key types
~~~~~~~~~
* :class:`VisionState` — computed vision snapshot for a character.

Key functions
~~~~~~~~~~~~~
* :func:`calculate_vision_radius` — applies night attenuation rules.
* :func:`build_vision_state`      — constructs a full :class:`VisionState`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.world_sim.chronos import ChronosRecord


# ---------------------------------------------------------------------------
# PH5-007 · Constants
# ---------------------------------------------------------------------------

BASE_VISION_RADIUS: int = 8
"""Default vision radius in voxels during daytime or with a light source."""

NIGHT_VISION_RADIUS: int = 3
"""Vision radius in voxels at night without special senses or a light source."""


# ---------------------------------------------------------------------------
# PH5-007 · VisionState dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class VisionState:
    """Computed vision parameters for a character at a specific world instant.

    Attributes:
        radius:           Effective vision radius in voxels.
        has_light_source: Whether the character carries a light source.
        low_light_vision: Whether the character has low-light vision.
        darkvision_ft:    Darkvision range in feet (0 = none).
    """

    radius: int
    has_light_source: bool
    low_light_vision: bool
    darkvision_ft: int


# ---------------------------------------------------------------------------
# PH5-007 · Vision Radius Calculator
# ---------------------------------------------------------------------------

def calculate_vision_radius(
    chronos: "ChronosRecord",
    character_metadata: dict,
    *,
    base_radius: int = BASE_VISION_RADIUS,
) -> int:
    """Compute the effective vision radius for a character.

    Priority rules (first match wins):

    1. **Daytime** — return *base_radius* unchanged.
    2. **Darkvision** — if ``character_metadata["darkvision_ft"] > 0``,
       return *base_radius* unchanged (darkvision ignores night penalties).
    3. **Light source** — if ``character_metadata["has_light_source"]`` is
       truthy, return *base_radius* unchanged (torch radius equals base).
    4. **Night penalty** — return :data:`NIGHT_VISION_RADIUS`.

    Args:
        chronos:            Current :class:`~src.world_sim.chronos.ChronosRecord`.
        character_metadata: Character metadata dict (read-only within this function).
        base_radius:        Base radius override; defaults to :data:`BASE_VISION_RADIUS`.

    Returns:
        Effective vision radius in voxels.
    """
    r = base_radius

    # Rule 1 — daytime: no attenuation.
    if chronos.is_day:
        return r

    # Rule 2 — darkvision overrides night penalty.
    if character_metadata.get("darkvision_ft", 0) > 0:
        return r

    # Rule 3 — light source overrides night penalty.
    if character_metadata.get("has_light_source", False):
        return r

    # Rule 4 — night with no special senses.
    return NIGHT_VISION_RADIUS


def build_vision_state(
    chronos: "ChronosRecord",
    character_metadata: dict,
) -> VisionState:
    """Construct a :class:`VisionState` from *chronos* and *character_metadata*.

    Args:
        chronos:            Current :class:`~src.world_sim.chronos.ChronosRecord`.
        character_metadata: Character metadata dict.

    Returns:
        A new :class:`VisionState` with all fields populated.
    """
    radius = calculate_vision_radius(chronos, character_metadata)
    return VisionState(
        radius=radius,
        has_light_source=bool(character_metadata.get("has_light_source", False)),
        low_light_vision=bool(character_metadata.get("low_light_vision", False)),
        darkvision_ft=int(character_metadata.get("darkvision_ft", 0)),
    )
