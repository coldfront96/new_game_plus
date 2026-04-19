"""
src/core/math_utils.py
----------------------
Shared mathematical helpers for the New Game Plus engine.

Covers common operations needed by the terrain, AI, and loot subsystems:
3D vector arithmetic, clamping, lerp, and integer coordinate hashing.
"""

from __future__ import annotations

import math
from typing import Tuple

Vec3 = Tuple[float, float, float]
IVec3 = Tuple[int, int, int]


def clamp(value: float, low: float, high: float) -> float:
    """Clamp *value* to the closed interval [*low*, *high*]."""
    return max(low, min(high, value))


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between *a* and *b* at parameter *t* ∈ [0, 1]."""
    return a + (b - a) * clamp(t, 0.0, 1.0)


def vec3_add(a: Vec3, b: Vec3) -> Vec3:
    """Element-wise addition of two 3-vectors."""
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def vec3_sub(a: Vec3, b: Vec3) -> Vec3:
    """Element-wise subtraction *a* − *b*."""
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vec3_scale(v: Vec3, s: float) -> Vec3:
    """Multiply a 3-vector by scalar *s*."""
    return (v[0] * s, v[1] * s, v[2] * s)


def vec3_length(v: Vec3) -> float:
    """Euclidean length of a 3-vector."""
    return math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)


def vec3_distance(a: Vec3, b: Vec3) -> float:
    """Euclidean distance between two points in 3D space."""
    return vec3_length(vec3_sub(a, b))


def vec3_normalize(v: Vec3) -> Vec3:
    """Return the unit vector of *v*.

    Raises:
        ZeroDivisionError: If *v* is the zero vector.
    """
    length = vec3_length(v)
    if length == 0.0:
        raise ZeroDivisionError("Cannot normalize the zero vector.")
    return (v[0] / length, v[1] / length, v[2] / length)


def chunk_coords(world_x: int, world_z: int, chunk_size: int = 16) -> IVec3:
    """Convert world-space XZ coordinates to chunk coordinates.

    Args:
        world_x:    World-space X block coordinate.
        world_z:    World-space Z block coordinate.
        chunk_size: Width/depth of each chunk in blocks (default 16).

    Returns:
        ``(chunk_x, 0, chunk_z)`` tuple.
    """
    return (world_x // chunk_size, 0, world_z // chunk_size)


def local_coords(world_x: int, world_y: int, world_z: int, chunk_size: int = 16) -> IVec3:
    """Return block coordinates local to their chunk."""
    return (world_x % chunk_size, world_y, world_z % chunk_size)


def manhattan_distance_3d(a: IVec3, b: IVec3) -> int:
    """Manhattan distance between two integer 3D points — used by A* heuristic."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])
