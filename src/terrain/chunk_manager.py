"""
src/terrain/chunk_manager.py
----------------------------
LRU-cached chunk manager for the New Game Plus voxel terrain engine.

The ChunkManager maintains a bounded in-memory cache of active chunks.
When the cache exceeds its capacity, the least-recently-used chunk is
saved to disk and evicted.

Usage::

    from src.core.event_bus import EventBus
    from src.terrain.chunk_manager import ChunkManager

    bus = EventBus()
    manager = ChunkManager(event_bus=bus, cache_size=64)
    chunk = manager.load_chunk(0, 0)
"""

from __future__ import annotations

import json
import os
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from src.core.event_bus import EventBus
from src.core.math_utils import chunk_coords, local_coords
from src.terrain.block import Block, Material
from src.terrain.chunk import Chunk, CHUNK_HEIGHT, CHUNK_WIDTH, CHUNK_DEPTH


# Default save directory (relative to project root)
DEFAULT_SAVES_DIR: str = "saves"


@dataclass(slots=True)
class ChunkManager:
    """Manages loading, caching, and unloading of terrain chunks.

    Uses an LRU (Least Recently Used) eviction strategy to keep memory
    usage bounded.

    Attributes:
        event_bus:  EventBus for publishing chunk lifecycle events.
        cache_size: Maximum number of chunks to hold in memory.
        saves_dir:  Path to the directory where chunks are persisted.
    """

    event_bus: EventBus
    cache_size: int = 64
    saves_dir: str = DEFAULT_SAVES_DIR
    _cache: OrderedDict = field(default_factory=OrderedDict, repr=False)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_chunk(self, cx: int, cz: int) -> Chunk:
        """Load a chunk by chunk coordinates, using the cache if available.

        If the chunk is already in memory, it is moved to the most-recently-used
        position. Otherwise, the chunk is loaded from disk or generated fresh.

        If loading this chunk exceeds cache capacity, the LRU chunk is evicted.

        Args:
            cx: Chunk X coordinate.
            cz: Chunk Z coordinate.

        Returns:
            The loaded or generated :class:`Chunk`.
        """
        key = (cx, cz)

        # Cache hit — move to end (most recently used)
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]

        # Try loading from disk
        chunk = self._load_from_disk(cx, cz)

        if chunk is None:
            # Generate a new chunk with default terrain
            chunk = self._generate_chunk(cx, cz)

        # Evict LRU if over capacity
        while len(self._cache) >= self.cache_size:
            self._evict_lru()

        self._cache[key] = chunk
        self.event_bus.publish("chunk_loaded", {"cx": cx, "cz": cz})
        return chunk

    def unload_chunk(self, cx: int, cz: int) -> bool:
        """Save and remove a chunk from the cache.

        If the chunk is dirty, it is saved to disk before removal.

        Args:
            cx: Chunk X coordinate.
            cz: Chunk Z coordinate.

        Returns:
            ``True`` if the chunk was in the cache and was unloaded;
            ``False`` if the chunk was not loaded.
        """
        key = (cx, cz)
        if key not in self._cache:
            return False

        chunk = self._cache.pop(key)
        if chunk.dirty:
            self._save_to_disk(chunk)
        self.event_bus.publish("chunk_unloaded", {"cx": cx, "cz": cz})
        return True

    def get_block_world(self, world_x: int, world_y: int, world_z: int) -> Optional[Block]:
        """Get a block by world coordinates.

        Loads the containing chunk if not already in memory.

        Args:
            world_x: World X coordinate.
            world_y: World Y coordinate (0–255).
            world_z: World Z coordinate.

        Returns:
            The block at the given position, or ``None`` if air/unset.
        """
        cx, _, cz = chunk_coords(world_x, world_z)
        lx, ly, lz = local_coords(world_x, world_y, world_z)
        chunk = self.load_chunk(cx, cz)
        return chunk.get_block(lx, ly, lz)

    def set_block_world(
        self, world_x: int, world_y: int, world_z: int, block: Optional[Block]
    ) -> None:
        """Set a block by world coordinates.

        Loads the containing chunk if not already in memory. Publishes
        a ``"block_modified"`` event.

        Args:
            world_x: World X coordinate.
            world_y: World Y coordinate (0–255).
            world_z: World Z coordinate.
            block:   The block to place (or ``None`` for air).
        """
        cx, _, cz = chunk_coords(world_x, world_z)
        lx, ly, lz = local_coords(world_x, world_y, world_z)
        chunk = self.load_chunk(cx, cz)
        chunk.set_block(lx, ly, lz, block)
        self.event_bus.publish("block_modified", {
            "world_x": world_x,
            "world_y": world_y,
            "world_z": world_z,
            "block": block,
        })

    @property
    def loaded_count(self) -> int:
        """Number of chunks currently in the cache."""
        return len(self._cache)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _evict_lru(self) -> None:
        """Evict the least-recently-used chunk from the cache."""
        if not self._cache:
            return
        key, chunk = self._cache.popitem(last=False)
        if chunk.dirty:
            self._save_to_disk(chunk)
        self.event_bus.publish("chunk_unloaded", {"cx": key[0], "cz": key[1]})

    def _chunk_path(self, cx: int, cz: int) -> Path:
        """Return the file path for a given chunk's save file."""
        return Path(self.saves_dir) / f"chunk_{cx}_{cz}.json"

    def _save_to_disk(self, chunk: Chunk) -> None:
        """Persist a chunk to the saves directory."""
        path = self._chunk_path(chunk.cx, chunk.cz)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write(chunk.to_json())
        chunk.dirty = False

    def _load_from_disk(self, cx: int, cz: int) -> Optional[Chunk]:
        """Attempt to load a chunk from disk.

        Returns:
            The chunk if a save file exists; ``None`` otherwise.
        """
        path = self._chunk_path(cx, cz)
        if not path.exists():
            return None
        with open(path, "r") as f:
            return Chunk.from_json(f.read())

    @staticmethod
    def _generate_chunk(cx: int, cz: int) -> Chunk:
        """Generate a default chunk with basic terrain layers.

        Terrain layout:
            y=0       → Bedrock (OBSIDIAN)
            y=1–59    → STONE
            y=60–63   → DIRT
            y=64      → DIRT (surface)
            y=65–255  → AIR (None / unset)
        """
        chunk = Chunk(cx=cx, cz=cz)
        for x in range(CHUNK_WIDTH):
            for z in range(CHUNK_DEPTH):
                # Bedrock layer
                chunk.set_block(x, 0, z, Block(
                    block_id=Material.OBSIDIAN.value,
                    material=Material.OBSIDIAN,
                ))
                # Stone layers
                for y in range(1, 60):
                    chunk.set_block(x, y, z, Block(
                        block_id=Material.STONE.value,
                        material=Material.STONE,
                    ))
                # Dirt layers
                for y in range(60, 65):
                    chunk.set_block(x, y, z, Block(
                        block_id=Material.DIRT.value,
                        material=Material.DIRT,
                    ))
        # After generation, mark as not dirty (fresh generated state)
        chunk.dirty = False
        return chunk
