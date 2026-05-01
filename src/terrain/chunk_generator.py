"""EM-005 — Voxel Carving API (Lair Carver subsystem).

src/terrain/chunk_generator.py
------------------------------
Procedural terrain generation for the New Game Plus voxel engine.

Uses 2D Simplex noise (via opensimplex) to produce realistic heightmaps
with stratified geology and ore distribution for a 3.5e-inspired world.

Usage::

    from src.terrain.chunk_generator import ChunkGenerator

    gen = ChunkGenerator(seed=42)
    chunk = gen.generate_chunk(cx=0, cz=0)
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

from opensimplex import OpenSimplex

from src.terrain.block import Block, Material
from src.terrain.chunk import Chunk, CHUNK_WIDTH, CHUNK_DEPTH, CHUNK_HEIGHT

if TYPE_CHECKING:
    from src.world_sim.lairs import LairRecord
    from src.world_sim.anomaly import AnomalyRecord
    from src.terrain.dungeon_carver import DungeonFloor, DungeonSpawnManifest


# ---------------------------------------------------------------------------
# Generation constants
# ---------------------------------------------------------------------------

# Base surface height (sea level) and noise amplitude
BASE_HEIGHT: int = 64
HEIGHT_AMPLITUDE: int = 16
NOISE_SCALE: float = 0.02

# Ore generation depth ranges (Y values, measured from 0 upward)
IRON_ORE_MIN_Y: int = 5
IRON_ORE_MAX_Y: int = 54
IRON_ORE_CHANCE: float = 0.012

GOLD_ORE_MIN_Y: int = 5
GOLD_ORE_MAX_Y: int = 32
GOLD_ORE_CHANCE: float = 0.005

# Number of top stone layers replaced by dirt
DIRT_LAYER_DEPTH: int = 3


# Biomes that qualify a chunk for dungeon generation (PH3-004).
# Imported lazily to avoid circular imports.
def _get_ruin_biomes() -> "frozenset":
    from src.world_sim.biome import Biome
    return frozenset({Biome.Any_Ruin, Biome.Underdark})


@dataclass(slots=True)
class ChunkGenerator:
    """Procedural terrain generator using Simplex noise.

    Attributes:
        seed: Integer seed for deterministic terrain generation.
    """

    seed: int

    def generate_chunk(
        self,
        cx: int,
        cz: int,
        dungeon_floors: "list[DungeonFloor] | None" = None,
    ) -> Chunk:
        """Generate a fully populated Chunk at the given chunk coordinates.

        Terrain layout per column (x, z):
            y = 0:              Bedrock (OBSIDIAN)
            y = 1 to surface-3: STONE (with ore replacement)
            y = surface-2 to surface-1: DIRT
            y = surface:        DIRT with grass metadata
            y > surface:        AIR (None)

        Ore distribution:
            IRON_ORE replaces STONE between Y=5 and Y=54 at ~1.2% chance.
            GOLD_ORE replaces STONE between Y=5 and Y=32 at ~0.5% chance.

        Args:
            cx:            Chunk X coordinate in chunk-space.
            cz:            Chunk Z coordinate in chunk-space.
            dungeon_floors: Optional list of :class:`DungeonFloor` objects to
                            apply after surface generation.  When provided,
                            :meth:`_apply_dungeon_floors` is called to zero out
                            the underground voxels for each floor's rooms and
                            hallways.

        Returns:
            A populated :class:`Chunk` ready for use.
        """
        noise = OpenSimplex(seed=self.seed)
        # Per-chunk deterministic RNG for ore placement.
        # Large primes for spatial hashing ensure unique RNG sequences per chunk.
        ore_rng = random.Random(self.seed ^ (cx * 73856093) ^ (cz * 19349663))

        chunk = Chunk(cx=cx, cz=cz)

        for x in range(CHUNK_WIDTH):
            for z in range(CHUNK_DEPTH):
                # World-space coordinates for noise sampling
                world_x = cx * CHUNK_WIDTH + x
                world_z = cz * CHUNK_DEPTH + z

                # 2D Simplex noise → surface height
                noise_val = noise.noise2(
                    world_x * NOISE_SCALE, world_z * NOISE_SCALE
                )
                surface = int(BASE_HEIGHT + noise_val * HEIGHT_AMPLITUDE)
                # Clamp to valid range
                surface = max(1, min(surface, CHUNK_HEIGHT - 1))

                # Bedrock at y=0
                chunk.set_block(x, 0, z, Block(
                    block_id=Material.OBSIDIAN.value,
                    material=Material.OBSIDIAN,
                ))

                # Fill column from y=1 to surface
                for y in range(1, surface + 1):
                    # Determine layer type
                    depth_from_surface = surface - y

                    if depth_from_surface < DIRT_LAYER_DEPTH:
                        # Top layers are dirt/grass
                        if depth_from_surface == 0:
                            # Very top layer: grass (DIRT with metadata)
                            chunk.set_block(x, y, z, Block(
                                block_id=Material.DIRT.value,
                                material=Material.DIRT,
                                metadata={"grass": True},
                            ))
                        else:
                            # Sub-surface dirt
                            chunk.set_block(x, y, z, Block(
                                block_id=Material.DIRT.value,
                                material=Material.DIRT,
                            ))
                    else:
                        # Stone layer — check for ore replacement
                        material = self._pick_stone_or_ore(y, ore_rng)
                        chunk.set_block(x, y, z, Block(
                            block_id=material.value,
                            material=material,
                        ))

        # Apply dungeon floors if provided (PH3-004)
        if dungeon_floors:
            _apply_dungeon_floors(chunk, dungeon_floors)

        # Freshly generated — not dirty
        chunk.dirty = False
        return chunk

    def generate_chunk_with_lair(self, cx: int, cz: int, lair_record: "LairRecord") -> Chunk:
        """Generate a terrain chunk and carve a lair cavity into it.

        Args:
            cx:          Chunk X coordinate.
            cz:          Chunk Z coordinate.
            lair_record: Describes the cavity dimensions and type to carve.

        Returns:
            A :class:`Chunk` with the lair cavity carved out.
        """
        chunk = self.generate_chunk(cx, cz)
        return carve_lair(chunk, lair_record)

    def generate_chunk_with_dungeon(
        self,
        cx: int,
        cz: int,
        num_floors: int,
        anomaly: "AnomalyRecord | None",
        rng: random.Random,
    ) -> "tuple[Chunk, list[DungeonFloor], list[DungeonSpawnManifest]]":
        """Generate a surface chunk with a full multi-floor dungeon carved beneath it.

        This is the single public API surface the :class:`~src.terrain.chunk_manager.ChunkManager`
        calls when loading a chunk that qualifies for dungeon generation.

        Qualifier: ``anomaly is not None and anomaly.current_biome in RUIN_BIOMES``
        where ``RUIN_BIOMES = {Biome.Any_Ruin, Biome.Underdark}``.

        Pipeline:
            1. Generate surface terrain via :meth:`generate_chunk`.
            2. Carve dungeon floors via :func:`~src.terrain.dungeon_carver.carve_dungeon`.
            3. Populate each floor via :func:`~src.terrain.dungeon_carver.populate_dungeon_floor`.
            4. Apply the carved floors back into the chunk voxel grid.

        Args:
            cx:         Chunk X coordinate in chunk-space.
            cz:         Chunk Z coordinate in chunk-space.
            num_floors: Number of dungeon levels to generate.
            anomaly:    Optional anomaly record (biases room placement when present).
            rng:        Seeded RNG for reproducible generation.

        Returns:
            A 3-tuple of ``(Chunk, list[DungeonFloor], list[DungeonSpawnManifest])``.
        """
        from src.terrain.dungeon_carver import carve_dungeon, populate_dungeon_floor

        anchor_chunk_id = f"{cx},{cz}"

        # (1) Surface terrain
        chunk = self.generate_chunk(cx, cz)

        # (2) Carve dungeon floors
        floors = carve_dungeon(
            chunk=chunk,
            num_floors=num_floors,
            anchor_chunk_id=anchor_chunk_id,
            anomaly=anomaly,
            rng=rng,
        )

        # (3) Populate each floor
        manifests: list[DungeonSpawnManifest] = []
        party_level = 1  # default; caller may override via separate call
        for floor in floors:
            manifest = populate_dungeon_floor(floor, party_level=party_level, rng=rng)
            manifests.append(manifest)

        return chunk, floors, manifests

    @staticmethod
    def _pick_stone_or_ore(y: int, rng: random.Random) -> Material:
        """Determine whether a stone block should be replaced with ore.

        Args:
            y:   The Y coordinate of the block.
            rng: Seeded RNG for deterministic ore placement.

        Returns:
            The material to place (STONE, IRON_ORE, or GOLD_ORE).
        """
        roll = rng.random()

        # Gold ore (rarer, deeper) — checked first with exclusive range
        if GOLD_ORE_MIN_Y <= y <= GOLD_ORE_MAX_Y and roll < GOLD_ORE_CHANCE:
            return Material.GOLD_ORE

        # Iron ore (more common, wider range) — uses separate probability band
        if IRON_ORE_MIN_Y <= y <= IRON_ORE_MAX_Y:
            if GOLD_ORE_CHANCE <= roll < GOLD_ORE_CHANCE + IRON_ORE_CHANCE:
                return Material.IRON_ORE

        return Material.STONE


# ---------------------------------------------------------------------------
# PH3-004 · _apply_dungeon_floors helper
# ---------------------------------------------------------------------------

def _apply_dungeon_floors(chunk: Chunk, floors: "list[DungeonFloor]") -> None:
    """Zero-out voxels in *chunk* for every room and hallway in *floors*.

    Iterates each :class:`~src.terrain.dungeon_carver.DungeonFloor`,
    :class:`~src.terrain.dungeon_carver.DungeonRoom`, and
    :class:`~src.terrain.dungeon_carver.DungeonHallway` within it, setting
    the corresponding voxels to ``None`` (air) at the correct negative-Y offset.

    This is a secondary application pass — :func:`~src.terrain.dungeon_carver.carve_dungeon`
    already writes to the chunk directly during generation.  This helper is
    called by :meth:`ChunkGenerator.generate_chunk` when ``dungeon_floors`` is
    provided, ensuring that pre-built floor descriptors are always reflected in
    the chunk's voxel grid.

    Args:
        chunk:  The :class:`Chunk` to modify in-place.
        floors: Dungeon floor descriptors to apply.
    """
    _SURFACE_Y = BASE_HEIGHT

    def _safe_clear(x: int, y: int, z: int) -> None:
        if 0 <= x < CHUNK_WIDTH and 0 < y < CHUNK_HEIGHT and 0 <= z < CHUNK_DEPTH:
            chunk.set_block(x, y, z, None)

    for floor in floors:
        for room in floor.rooms:
            rx, ry_neg, rz = room.origin
            y_top = _SURFACE_Y + ry_neg
            y_bot = max(1, y_top - room.height + 1)
            for x in range(rx, rx + room.width):
                for z in range(rz, rz + room.depth):
                    for y in range(y_bot, y_top + 1):
                        _safe_clear(x, y, z)

        for hall in floor.hallways:
            sx, sy_neg, sz = hall.start_voxel
            ex, _, ez = hall.end_voxel
            y_mid = _SURFACE_Y + sy_neg
            y_floor = max(1, y_mid - hall.width + 1)
            w = hall.width
            x_lo, x_hi = min(sx, ex), max(sx, ex)
            for x in range(x_lo, x_hi + w):
                for dz in range(w):
                    for y in range(y_floor, y_mid + 1):
                        _safe_clear(x, y, sz + dz)
            z_lo, z_hi = min(sz, ez), max(sz, ez)
            for z in range(z_lo, z_hi + w):
                for dx in range(w):
                    for y in range(y_floor, y_mid + 1):
                        _safe_clear(ex + dx, y, z)


# ---------------------------------------------------------------------------
# EM-005 · Voxel Carving API
# ---------------------------------------------------------------------------

def carve_lair(chunk: Chunk, lair_record: "LairRecord") -> Chunk:
    """Carve a rectangular air cavity into *chunk* based on *lair_record* dimensions.

    The cavity is centred horizontally in the chunk and starts just below the
    surface (y = BASE_HEIGHT - 1 downward).  All coordinates are clamped to
    valid chunk bounds so oversized lairs never raise IndexError.

    Args:
        chunk:       The :class:`Chunk` to modify in-place.
        lair_record: Dimensions and metadata for the cavity.

    Returns:
        The same *chunk* with the carved region set to air (``None``).
    """
    half_w = lair_record.width  // 2
    half_d = lair_record.depth  // 2

    center_x = CHUNK_WIDTH // 2
    center_z  = CHUNK_DEPTH  // 2

    x_start = max(0, center_x - half_w)
    x_end   = min(CHUNK_WIDTH,  center_x + lair_record.width  - half_w)
    z_start = max(0, center_z  - half_d)
    z_end   = min(CHUNK_DEPTH,   center_z  + lair_record.depth  - half_d)

    y_top   = min(BASE_HEIGHT - 1, CHUNK_HEIGHT - 1)
    y_bot   = max(1, y_top - lair_record.height + 1)

    for y in range(y_bot, y_top + 1):
        for x in range(x_start, x_end):
            for z in range(z_start, z_end):
                chunk.set_block(x, y, z, None)

    return chunk
