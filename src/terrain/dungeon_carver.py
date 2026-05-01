"""PH3-001 · PH3-002 · PH3-003 — Subterranean Architecture (Dungeon-Carver subsystem).

src/terrain/dungeon_carver.py
------------------------------
Procedural dungeon generation for the New Game Plus voxel engine.

Implements multi-floor dungeon carving beneath surface chunks, with room and
hallway placement, trap and treasure spawning, and negative-Y voxel integration.

Key types
~~~~~~~~~
* :class:`DungeonRoom`          — a single rectangular chamber.
* :class:`DungeonHallway`       — a rectilinear connecting corridor.
* :class:`DungeonFloor`         — one floor of the dungeon (rooms + hallways).
* :class:`DungeonSpawnManifest` — trap and treasure placement for one floor.

Usage::

    import random
    from src.terrain.chunk import Chunk
    from src.terrain.dungeon_carver import carve_dungeon, populate_dungeon_floor

    chunk = Chunk(cx=0, cz=0)
    rng = random.Random(42)
    floors = carve_dungeon(chunk, num_floors=3, anchor_chunk_id="0,0", anomaly=None, rng=rng)
    for floor in floors:
        manifest = populate_dungeon_floor(floor, party_level=5, rng=rng)
        print(manifest.trap_voxels, manifest.treasure_voxels)
"""

from __future__ import annotations

import hashlib
import uuid
import random as _random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src.terrain.block import Block, Material
from src.terrain.chunk import Chunk, CHUNK_WIDTH, CHUNK_DEPTH, CHUNK_HEIGHT
from src.rules_engine.traps import (
    TrapBase,
    generate_mechanical_trap,
    generate_magical_trap,
)
from src.rules_engine.treasure import TreasureHoard, generate_treasure_hoard

if TYPE_CHECKING:
    from src.world_sim.anomaly import AnomalyRecord

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

FLOOR_DEPTH_VOXELS: int = 16
"""Height in voxels of each underground floor slab."""

MAX_DUNGEON_FLOORS: int = 5
"""Maximum number of dungeon floors that can be generated for a single chunk."""

# Surface Y that the carver measures down from (matches ChunkGenerator.BASE_HEIGHT).
_SURFACE_Y: int = 64

# Room sizing bounds (in voxels)
_ROOM_MIN_W: int = 3
_ROOM_MAX_W: int = 8
_ROOM_MIN_D: int = 3
_ROOM_MAX_D: int = 8
_ROOM_DEFAULT_H: int = 4   # ceiling clearance

# Hallway width (in voxels)
_HALL_WIDTH: int = 2


# ---------------------------------------------------------------------------
# PH3-001 — DungeonRoom schema
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class DungeonRoom:
    """A single rectangular chamber within a dungeon floor.

    Attributes:
        room_id: Deterministic UUID derived from the anchor chunk, floor index,
                 and room index.
        origin:  Voxel XYZ origin of the room (south-west-bottom corner).
                 The Z component is negative (below the surface).
        width:   Room extent along the X axis in voxels.
        depth:   Room extent along the chunk-Z axis in voxels.
        height:  Ceiling clearance in voxels (default 4).
    """

    room_id: str
    origin: tuple[int, int, int]
    width: int
    depth: int
    height: int = _ROOM_DEFAULT_H


# ---------------------------------------------------------------------------
# PH3-001 — DungeonHallway schema
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class DungeonHallway:
    """A rectilinear L-shaped corridor connecting two dungeon rooms.

    Attributes:
        hall_id:     Deterministic UUID.
        start_voxel: Start coordinate (XYZ).
        end_voxel:   End coordinate (XYZ).
        width:       Corridor width in voxels (default 2).
    """

    hall_id: str
    start_voxel: tuple[int, int, int]
    end_voxel: tuple[int, int, int]
    width: int = _HALL_WIDTH


# ---------------------------------------------------------------------------
# PH3-001 — DungeonFloor schema
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class DungeonFloor:
    """One floor of an underground dungeon.

    Attributes:
        floor_index:     0 = first basement level, 1 = second, …
        z_offset:        Negative Y offset in voxel space.
                         Computed as ``-(floor_index + 1) * FLOOR_DEPTH_VOXELS``.
        rooms:           All :class:`DungeonRoom` objects on this floor.
        hallways:        All :class:`DungeonHallway` connectors on this floor.
        anchor_chunk_id: Chunk that owns this floor.
    """

    floor_index: int
    z_offset: int
    rooms: list[DungeonRoom]
    hallways: list[DungeonHallway]
    anchor_chunk_id: str


# ---------------------------------------------------------------------------
# PH3-003 — DungeonSpawnManifest schema
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class DungeonSpawnManifest:
    """Maps voxel coordinates to spawned traps and treasure for one floor.

    The manifest is the sole lookup table used by the game loop to resolve
    trap triggers and loot interactions — no runtime scanning of the voxel
    grid is required.

    Attributes:
        floor_index:     The floor this manifest covers.
        room_id:         The room that was populated.
        trap_voxels:     Mapping of voxel coordinate → trap object.
        treasure_voxels: Mapping of voxel coordinate → treasure hoard.
    """

    floor_index: int
    room_id: str
    trap_voxels: dict[tuple[int, int, int], TrapBase]
    treasure_voxels: dict[tuple[int, int, int], TreasureHoard]


# ---------------------------------------------------------------------------
# Internal UUID helper
# ---------------------------------------------------------------------------

def _det_uuid(seed_string: str) -> str:
    """Return a deterministic UUID derived from *seed_string* via SHA-1."""
    h = hashlib.sha1(seed_string.encode()).hexdigest()
    # UUID v5 namespace-independent format from SHA-1 hex
    return str(uuid.UUID(h[:32]))


# ---------------------------------------------------------------------------
# PH3-002 — AABB overlap check
# ---------------------------------------------------------------------------

def _rooms_overlap(a: DungeonRoom, b: DungeonRoom) -> bool:
    """Return True if two rooms' AABB bounding boxes overlap (XZ plane)."""
    ax1, _, az1 = a.origin
    ax2 = ax1 + a.width
    az2 = az1 + a.depth
    bx1, _, bz1 = b.origin
    bx2 = bx1 + b.width
    bz2 = bz1 + b.depth
    return ax1 < bx2 and ax2 > bx1 and az1 < bz2 and az2 > bz1


# ---------------------------------------------------------------------------
# PH3-002 — Voxel writing helpers
# ---------------------------------------------------------------------------

def _safe_set(chunk: Chunk, x: int, y: int, z: int, block: Block | None) -> None:
    """Set a voxel only when (x, y, z) are within chunk bounds."""
    if 0 <= x < CHUNK_WIDTH and 0 < y < CHUNK_HEIGHT and 0 <= z < CHUNK_DEPTH:
        chunk.set_block(x, y, z, block)


def _air() -> None:
    return None


def _stone_block() -> Block:
    return Block(block_id=Material.STONE.value, material=Material.STONE)


def _obsidian_block() -> Block:
    return Block(block_id=Material.OBSIDIAN.value, material=Material.OBSIDIAN)


def _carve_room(chunk: Chunk, room: DungeonRoom) -> None:
    """Carve a room into chunk voxels: AIR interior, STONE walls/ceiling, OBSIDIAN floor."""
    rx, ry_neg, rz = room.origin
    # Convert negative Z offset to actual chunk Y
    y_top = _SURFACE_Y + ry_neg            # ceiling row (inclusive)
    y_bot = max(1, y_top - room.height + 1)  # floor row (inclusive)

    for x in range(rx, rx + room.width):
        for z in range(rz, rz + room.depth):
            for y in range(y_bot, y_top + 1):
                if y == y_bot:
                    # Floor: obsidian
                    _safe_set(chunk, x, y, z, _obsidian_block())
                elif y == y_top:
                    # Ceiling: stone
                    _safe_set(chunk, x, y, z, _stone_block())
                else:
                    # Interior: air
                    _safe_set(chunk, x, y, z, _air())

    # Surround walls (±1 in x and z, but only if outside room bounds)
    # Line north/south walls
    for x in range(max(0, rx - 1), min(CHUNK_WIDTH, rx + room.width + 1)):
        for y in range(y_bot, y_top + 1):
            if x == rx - 1 or x == rx + room.width:
                for z in range(rz, rz + room.depth):
                    _safe_set(chunk, x, y, z, _stone_block())
    # Line east/west walls
    for z in range(max(0, rz - 1), min(CHUNK_DEPTH, rz + room.depth + 1)):
        for y in range(y_bot, y_top + 1):
            if z == rz - 1 or z == rz + room.depth:
                for x in range(rx, rx + room.width):
                    _safe_set(chunk, x, y, z, _stone_block())


def _carve_hallway(chunk: Chunk, hall: DungeonHallway) -> None:
    """Carve an L-shaped hallway: horizontal segment first, then vertical."""
    sx, sy_neg, sz = hall.start_voxel
    ex, _, ez = hall.end_voxel
    y_mid = _SURFACE_Y + sy_neg
    y_floor = max(1, y_mid - _HALL_WIDTH + 1)
    w = hall.width

    # Horizontal segment (along X, at start Z)
    x_lo, x_hi = min(sx, ex), max(sx, ex)
    for x in range(x_lo, x_hi + w):
        for dz in range(w):
            for y in range(y_floor, y_mid + 1):
                _safe_set(chunk, x, y, sz + dz, _air())

    # Vertical segment (along Z, at end X)
    z_lo, z_hi = min(sz, ez), max(sz, ez)
    for z in range(z_lo, z_hi + w):
        for dx in range(w):
            for y in range(y_floor, y_mid + 1):
                _safe_set(chunk, ex + dx, y, z, _air())


# ---------------------------------------------------------------------------
# PH3-002 — carve_dungeon
# ---------------------------------------------------------------------------

def carve_dungeon(
    chunk: Chunk,
    num_floors: int,
    anchor_chunk_id: str,
    anomaly: "AnomalyRecord | None",
    rng: _random.Random,
) -> list[DungeonFloor]:
    """Carve a multi-floor dungeon into *chunk* and return the floor descriptors.

    For each floor ``f`` in ``range(num_floors)``:

    * Computes ``z_base = -(f + 1) * FLOOR_DEPTH_VOXELS`` (negative Y offset).
    * Places 2–6 non-overlapping :class:`DungeonRoom` objects within the chunk footprint.
    * Connects rooms with rectilinear :class:`DungeonHallway` segments.
    * Writes ``Material.AIR`` to room/hallway interiors.
    * Lines room walls/ceilings with ``Material.STONE``; floors with ``Material.OBSIDIAN``.
    * When *anomaly* is provided and ``anomaly.chunk_id == anchor_chunk_id``,
      biases room placement ±4 voxels beneath the anomaly's surface XZ coords.

    Args:
        chunk:           The :class:`Chunk` to modify in-place.
        num_floors:      Number of dungeon levels to generate (≤ MAX_DUNGEON_FLOORS).
        anchor_chunk_id: Chunk identifier (used for deterministic UUIDs).
        anomaly:         Optional anomaly record; biases room placement when present.
        rng:             Seeded RNG for reproducible layouts.

    Returns:
        A list of :class:`DungeonFloor` descriptors for the carved layout.
    """
    num_floors = min(num_floors, MAX_DUNGEON_FLOORS)
    floors: list[DungeonFloor] = []

    # Anomaly anchor in chunk-local XZ (if applicable)
    anomaly_cx: int | None = None
    anomaly_cz: int | None = None
    if anomaly is not None and anomaly.chunk_id == anchor_chunk_id:
        # Place rooms biased ±4 voxels around chunk centre (anomaly doesn't
        # carry exact XZ, so we bias around the chunk midpoint)
        anomaly_cx = CHUNK_WIDTH // 2
        anomaly_cz = CHUNK_DEPTH // 2

    for f in range(num_floors):
        z_base = -(f + 1) * FLOOR_DEPTH_VOXELS   # negative Y offset
        y_top = _SURFACE_Y + z_base               # ceiling Y of this floor slab

        # --- Place 2–6 non-overlapping rooms ---
        num_rooms = rng.randint(2, 6)
        rooms: list[DungeonRoom] = []
        attempts = 0

        while len(rooms) < num_rooms and attempts < 100:
            attempts += 1
            rw = rng.randint(_ROOM_MIN_W, _ROOM_MAX_W)
            rd = rng.randint(_ROOM_MIN_D, _ROOM_MAX_D)

            if anomaly_cx is not None:
                # Bias: sample near anomaly XZ ±4 voxels
                bias_x = max(0, anomaly_cx + rng.randint(-4, 4))
                bias_z = max(0, anomaly_cz + rng.randint(-4, 4))
                rx = max(0, min(CHUNK_WIDTH - rw, bias_x))
                rz = max(0, min(CHUNK_DEPTH - rd, bias_z))
            else:
                rx = rng.randint(0, max(0, CHUNK_WIDTH - rw))
                rz = rng.randint(0, max(0, CHUNK_DEPTH - rd))

            # Room origin: (x, z_base, chunk_z) — z_base is negative Y offset
            room_id = _det_uuid(f"{anchor_chunk_id}:{f}:{len(rooms)}")
            candidate = DungeonRoom(
                room_id=room_id,
                origin=(rx, z_base, rz),
                width=rw,
                depth=rd,
                height=_ROOM_DEFAULT_H,
            )

            # AABB collision check against placed rooms
            if any(_rooms_overlap(candidate, existing) for existing in rooms):
                continue

            # Clamp to chunk bounds
            if rx + rw > CHUNK_WIDTH or rz + rd > CHUNK_DEPTH:
                continue
            if y_top - _ROOM_DEFAULT_H < 1:
                # Too deep — not enough vertical space
                continue

            rooms.append(candidate)
            _carve_room(chunk, candidate)

        # --- Connect rooms with L-shaped hallways ---
        hallways: list[DungeonHallway] = []
        for i in range(1, len(rooms)):
            a = rooms[i - 1]
            b = rooms[i]
            # Start at centre of room a, end at centre of room b
            ax, az = a.origin[0] + a.width // 2, a.origin[2] + a.depth // 2
            bx, bz = b.origin[0] + b.width // 2, b.origin[2] + b.depth // 2

            hall_id = _det_uuid(f"{anchor_chunk_id}:{f}:hall:{i}")
            hall = DungeonHallway(
                hall_id=hall_id,
                start_voxel=(ax, z_base, az),
                end_voxel=(bx, z_base, bz),
                width=_HALL_WIDTH,
            )
            hallways.append(hall)
            _carve_hallway(chunk, hall)

        floors.append(DungeonFloor(
            floor_index=f,
            z_offset=z_base,
            rooms=rooms,
            hallways=hallways,
            anchor_chunk_id=anchor_chunk_id,
        ))

    return floors


# ---------------------------------------------------------------------------
# PH3-003 — populate_dungeon_floor
# ---------------------------------------------------------------------------

def populate_dungeon_floor(
    floor: DungeonFloor,
    party_level: int,
    rng: _random.Random,
) -> DungeonSpawnManifest:
    """Populate a dungeon floor with traps and treasure hoards.

    For each room on *floor*:

    * **Trap** (1-in-3 chance): rolls either a :class:`MechanicalTrap` (70 %)
      or a :class:`MagicalTrap` (30 %), placed at a random non-doorway floor voxel.
    * **Treasure** (1-in-2 chance): generates a :class:`TreasureHoard` scaled to
      *party_level*, placed at a room corner voxel.

    The returned :class:`DungeonSpawnManifest` maps each spawned object to its
    exact voxel coordinate so the game loop can resolve interactions without
    scanning the voxel grid.

    Args:
        floor:       The :class:`DungeonFloor` to populate.
        party_level: Average party level — used to scale trap CR and treasure.
        rng:         Seeded RNG.

    Returns:
        A :class:`DungeonSpawnManifest` for *floor*.
    """
    trap_voxels: dict[tuple[int, int, int], TrapBase] = {}
    treasure_voxels: dict[tuple[int, int, int], TreasureHoard] = {}

    for room in floor.rooms:
        rx, ry_neg, rz = room.origin
        y_floor = _SURFACE_Y + ry_neg - room.height + 1   # floor voxel Y

        # --- Trap presence: 1-in-3 chance ---
        if rng.randint(1, 3) == 1:
            # Trap goes on a random interior floor voxel (avoid first column = doorway)
            trap_x = rx + rng.randint(1, max(1, room.width - 2))
            trap_z = rz + rng.randint(1, max(1, room.depth - 2))
            coord = (trap_x, y_floor, trap_z)

            if rng.random() < 0.70:
                trap = generate_mechanical_trap(cr=float(party_level), rng=rng)
            else:
                trap = generate_magical_trap(cr=float(party_level), rng=rng)

            trap_voxels[coord] = trap

        # --- Treasure presence: 1-in-2 chance ---
        if rng.randint(1, 2) == 1:
            # Corner voxels: 4 choices
            corners = [
                (rx, y_floor, rz),
                (rx + room.width - 1, y_floor, rz),
                (rx, y_floor, rz + room.depth - 1),
                (rx + room.width - 1, y_floor, rz + room.depth - 1),
            ]
            # Choose a corner not already occupied by a trap
            available = [c for c in corners if c not in trap_voxels]
            if available:
                corner = rng.choice(available)
                hoard = generate_treasure_hoard(cr=party_level, rng=rng)
                treasure_voxels[corner] = hoard

    # room_id is the first room's id if present, else empty string
    room_id = floor.rooms[0].room_id if floor.rooms else ""
    return DungeonSpawnManifest(
        floor_index=floor.floor_index,
        room_id=room_id,
        trap_voxels=trap_voxels,
        treasure_voxels=treasure_voxels,
    )
