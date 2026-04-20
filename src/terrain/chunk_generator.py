"""
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

from opensimplex import OpenSimplex

from src.terrain.block import Block, Material
from src.terrain.chunk import Chunk, CHUNK_WIDTH, CHUNK_DEPTH, CHUNK_HEIGHT


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


@dataclass(slots=True)
class ChunkGenerator:
    """Procedural terrain generator using Simplex noise.

    Attributes:
        seed: Integer seed for deterministic terrain generation.
    """

    seed: int

    def generate_chunk(self, cx: int, cz: int) -> Chunk:
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
            cx: Chunk X coordinate in chunk-space.
            cz: Chunk Z coordinate in chunk-space.

        Returns:
            A populated :class:`Chunk` ready for use.
        """
        noise = OpenSimplex(seed=self.seed)
        # Per-chunk deterministic RNG for ore placement
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

        # Freshly generated — not dirty
        chunk.dirty = False
        return chunk

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

        # Gold ore (rarer, deeper)
        if GOLD_ORE_MIN_Y <= y <= GOLD_ORE_MAX_Y:
            if roll < GOLD_ORE_CHANCE:
                return Material.GOLD_ORE

        # Iron ore (more common, wider range)
        if IRON_ORE_MIN_Y <= y <= IRON_ORE_MAX_Y:
            if roll < IRON_ORE_CHANCE:
                return Material.IRON_ORE

        return Material.STONE
