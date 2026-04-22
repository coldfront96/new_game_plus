"""
src/terrain/lighting.py
-----------------------
Environmental Lighting Engine for New Game Plus.

Implements D&D 3.5e SRD lighting rules:
- BRIGHT light: full visibility, no concealment penalties.
- DIM light:    shadowy illumination; creatures gain 20% miss chance (Concealment).
- DARKNESS:     no natural illumination; creatures gain 50% miss chance
                (Total Concealment) unless the attacker has Darkvision.

Light sources
~~~~~~~~~~~~~
* **Sunlight** — a top-down area light that illuminates the entire surface
  layer within a radius. Represented by a :class:`Sunlight` descriptor.
* **Point Lights** — localised light sources such as torches or lanterns.
  Represented by :class:`PointLight` descriptors attached to world positions.

Usage::

    from src.terrain.lighting import LightLevel, LightSystem, PointLight, Sunlight

    system = LightSystem()
    torch = PointLight(x=10, y=64, z=10, radius=20.0, bright_radius=10.0)
    system.add_point_light(torch)

    level = system.get_light_level(10, 64, 10)
    # LightLevel.BRIGHT  (standing at the torch)

    level = system.get_light_level(25, 64, 10)
    # LightLevel.DARKNESS  (beyond torch's radius, no sunlight)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# LightLevel enum
# ---------------------------------------------------------------------------

class LightLevel(Enum):
    """Illumination categories from the D&D 3.5e SRD.

    Attributes:
        BRIGHT:   Full illumination.  No concealment penalty.
        DIM:      Shadowy illumination.  20 % miss chance (Concealment).
        DARKNESS: No light.  50 % miss chance (Total Concealment) for
                  creatures without Darkvision.
    """

    BRIGHT = auto()
    DIM = auto()
    DARKNESS = auto()


# ---------------------------------------------------------------------------
# Light-source data classes
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Sunlight:
    """Top-down area light simulating natural sunlight or moonlight.

    Attributes:
        surface_y:    The Y-coordinate (height) of the illuminated surface.
                      Voxels at or above this level are considered surface.
        radius:       Horizontal radius of sunlight coverage in voxels.
                      ``-1`` means unlimited coverage.
        bright_radius: Radius of BRIGHT light.  Beyond this and up to
                      ``radius`` is DIM light.  ``-1`` means all is BRIGHT.
        origin_x:     Centre X of the sunlight column (default 0).
        origin_z:     Centre Z of the sunlight column (default 0).
    """

    surface_y: float = 64.0
    radius: float = -1.0          # -1 = unlimited
    bright_radius: float = -1.0   # -1 = unlimited BRIGHT
    origin_x: float = 0.0
    origin_z: float = 0.0


@dataclass(slots=True)
class PointLight:
    """A localised light source such as a torch, lantern, or magical light.

    Per the 3.5e SRD a torch illuminates a 20-ft bright radius and provides
    shadowy illumination out to 40 ft.  The system normalises these to voxel
    units (1 voxel ≈ 5 ft by default).

    Attributes:
        x:            World X position of the light source.
        y:            World Y position of the light source.
        z:            World Z position of the light source.
        bright_radius: Radius (in voxels) of BRIGHT illumination.
        radius:       Total radius (in voxels) of any illumination (DIM beyond
                      ``bright_radius`` up to this value).
    """

    x: float
    y: float
    z: float
    bright_radius: float = 4.0   # 20 ft / 5 ft per voxel
    radius: float = 8.0          # 40 ft / 5 ft per voxel


# ---------------------------------------------------------------------------
# LightState — snapshot result (slots=True per memory standard)
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class LightState:
    """Result of a lighting query at a specific voxel position.

    Attributes:
        level:        The resolved :class:`LightLevel` at the queried voxel.
        contributing_source: Human-readable label of the dominant light source
                      (e.g. ``"sunlight"``, ``"point_light"``), or ``None``
                      when the voxel is in total darkness.
    """

    level: LightLevel
    contributing_source: Optional[str] = None


# ---------------------------------------------------------------------------
# LightSystem
# ---------------------------------------------------------------------------

class LightSystem:
    """Calculates voxel light levels from Sunlight and Point Light sources.

    The system evaluates all registered light sources and returns the
    *highest* light level (BRIGHT > DIM > DARKNESS) at any queried position.

    Low-Light Vision races (Elf) effectively double a light source's
    radius when querying via :meth:`get_light_level_for_vision`.

    Args:
        sunlight: Optional :class:`Sunlight` descriptor.  If ``None``, no
                  sunlight is present (underground / night without moon).
    """

    def __init__(self, sunlight: Optional[Sunlight] = None) -> None:
        self._sunlight: Optional[Sunlight] = sunlight
        self._point_lights: List[PointLight] = []

    # ------------------------------------------------------------------
    # Light source management
    # ------------------------------------------------------------------

    def set_sunlight(self, sunlight: Optional[Sunlight]) -> None:
        """Replace the current sunlight descriptor.

        Pass ``None`` to disable sunlight entirely (e.g. underground zones).
        """
        self._sunlight = sunlight

    def add_point_light(self, light: PointLight) -> None:
        """Register a :class:`PointLight` with the system."""
        self._point_lights.append(light)

    def remove_point_light(self, light: PointLight) -> None:
        """Deregister a :class:`PointLight` (no-op if not present)."""
        try:
            self._point_lights.remove(light)
        except ValueError:
            pass

    def clear_point_lights(self) -> None:
        """Remove all registered point lights."""
        self._point_lights.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _distance(
        ax: float, ay: float, az: float,
        bx: float, by: float, bz: float,
    ) -> float:
        """3-D Euclidean distance between two points."""
        return math.sqrt((ax - bx) ** 2 + (ay - by) ** 2 + (az - bz) ** 2)

    def _sunlight_level(
        self,
        x: float, y: float, z: float,
        radius_multiplier: float = 1.0,
    ) -> LightLevel:
        """Return the light level contributed by the sunlight source."""
        if self._sunlight is None:
            return LightLevel.DARKNESS

        sun = self._sunlight

        # Below the surface threshold → no sunlight
        if y < sun.surface_y:
            return LightLevel.DARKNESS

        # Check horizontal distance from origin if bounded
        if sun.radius >= 0:
            horiz = math.sqrt((x - sun.origin_x) ** 2 + (z - sun.origin_z) ** 2)
            effective_radius = sun.radius * radius_multiplier

            if horiz > effective_radius:
                return LightLevel.DARKNESS

            if sun.bright_radius >= 0:
                effective_bright = sun.bright_radius * radius_multiplier
                if horiz <= effective_bright:
                    return LightLevel.BRIGHT
                return LightLevel.DIM

        # Unlimited sunlight coverage
        if sun.bright_radius < 0:
            return LightLevel.BRIGHT
        # Unlimited radius but finite bright threshold is odd; treat as BRIGHT
        return LightLevel.BRIGHT

    def _point_light_level(
        self,
        x: float, y: float, z: float,
        radius_multiplier: float = 1.0,
    ) -> LightLevel:
        """Return the best light level contributed by any point light."""
        best = LightLevel.DARKNESS

        for pl in self._point_lights:
            dist = self._distance(x, y, z, pl.x, pl.y, pl.z)

            effective_bright = pl.bright_radius * radius_multiplier
            effective_dim = pl.radius * radius_multiplier

            if dist <= effective_bright:
                return LightLevel.BRIGHT  # Can't do better; short-circuit
            elif dist <= effective_dim:
                best = LightLevel.DIM

        return best

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_light_level(self, x: float, y: float, z: float) -> LightLevel:
        """Return the :class:`LightLevel` at voxel ``(x, y, z)``.

        Evaluates sunlight and all point lights and returns the highest
        (brightest) level found.

        Args:
            x: Voxel X coordinate.
            y: Voxel Y coordinate.
            z: Voxel Z coordinate.

        Returns:
            The :class:`LightLevel` at the given position.
        """
        levels = [
            self._sunlight_level(x, y, z),
            self._point_light_level(x, y, z),
        ]
        # BRIGHT > DIM > DARKNESS; Enum values are 1, 2, 3 respectively —
        # we want the *lowest* numeric value (highest brightness).
        return min(levels, key=lambda lv: lv.value)

    def get_light_state(self, x: float, y: float, z: float) -> LightState:
        """Return a full :class:`LightState` snapshot at ``(x, y, z)``.

        Args:
            x: Voxel X coordinate.
            y: Voxel Y coordinate.
            z: Voxel Z coordinate.

        Returns:
            A :class:`LightState` with the resolved level and source label.
        """
        sun_level = self._sunlight_level(x, y, z)
        pl_level = self._point_light_level(x, y, z)

        if sun_level.value <= pl_level.value:
            best = sun_level
            source = "sunlight" if best != LightLevel.DARKNESS else None
        else:
            best = pl_level
            source = "point_light" if best != LightLevel.DARKNESS else None

        return LightState(level=best, contributing_source=source)

    def get_light_level_for_vision(
        self,
        x: float,
        y: float,
        z: float,
        vision_type: str,
    ) -> LightLevel:
        """Return the effective :class:`LightLevel` as perceived by a specific
        vision type.

        Vision type rules (3.5e SRD):
        - ``"Normal"``:         Standard light evaluation.
        - ``"Low-Light Vision"``: Doubles all light-source radii.
        - ``"Darkvision"``:     Treats DARKNESS as BRIGHT within 60 ft of the
                                viewer; normal light otherwise.  Callers should
                                use :meth:`get_light_level` and handle darkvision
                                distance checks in the combat resolver.

        Args:
            x:           Target voxel X.
            y:           Target voxel Y.
            z:           Target voxel Z.
            vision_type: One of ``"Normal"``, ``"Low-Light Vision"``,
                         ``"Darkvision"``.

        Returns:
            Effective :class:`LightLevel` as seen by the entity.
        """
        if vision_type == "Low-Light Vision":
            sun_level = self._sunlight_level(x, y, z, radius_multiplier=2.0)
            pl_level = self._point_light_level(x, y, z, radius_multiplier=2.0)
            return min(sun_level, pl_level, key=lambda lv: lv.value)

        # Normal and Darkvision use the raw level; darkvision darkness-ignoring
        # is handled in AttackResolver / VisionSystem.
        return self.get_light_level(x, y, z)
