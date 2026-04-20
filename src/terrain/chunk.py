"""
src/terrain/chunk.py
--------------------
Chunk data structure for the New Game Plus voxel terrain engine.

A Chunk represents a 16×16×256 column of blocks in the world. Each chunk
is identified by its chunk coordinates (cx, cz) and stores a flat array of
Block objects indexed by local (x, y, z) position.

Usage::

    from src.terrain.chunk import Chunk
    from src.terrain.block import Block, Material

    chunk = Chunk(cx=0, cz=0)
    chunk.set_block(5, 64, 5, Block(block_id=2, material=Material.STONE))
    block = chunk.get_block(5, 64, 5)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import List, Optional

from src.terrain.block import Block, Material


# Chunk dimensions
CHUNK_WIDTH: int = 16
CHUNK_DEPTH: int = 16
CHUNK_HEIGHT: int = 256


@dataclass(slots=True)
class Chunk:
    """A 16×16×256 column of blocks in the voxel world.

    Attributes:
        cx:     Chunk X coordinate in chunk-space.
        cz:     Chunk Z coordinate in chunk-space.
        dirty:  Whether this chunk has been modified since last save/mesh.
    """

    cx: int
    cz: int
    dirty: bool = False
    _blocks: List[Optional[Block]] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        if not self._blocks:
            self._blocks = [None] * (CHUNK_WIDTH * CHUNK_HEIGHT * CHUNK_DEPTH)

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    @staticmethod
    def _index(x: int, y: int, z: int) -> int:
        """Compute flat array index from local coordinates.

        Layout: x + z * CHUNK_WIDTH + y * CHUNK_WIDTH * CHUNK_DEPTH
        """
        if not (0 <= x < CHUNK_WIDTH):
            raise IndexError(f"x={x} out of range [0, {CHUNK_WIDTH})")
        if not (0 <= y < CHUNK_HEIGHT):
            raise IndexError(f"y={y} out of range [0, {CHUNK_HEIGHT})")
        if not (0 <= z < CHUNK_DEPTH):
            raise IndexError(f"z={z} out of range [0, {CHUNK_DEPTH})")
        return x + z * CHUNK_WIDTH + y * CHUNK_WIDTH * CHUNK_DEPTH

    # ------------------------------------------------------------------
    # Block access
    # ------------------------------------------------------------------

    def get_block(self, x: int, y: int, z: int) -> Optional[Block]:
        """Return the block at local position (x, y, z), or ``None`` for air.

        Args:
            x: Local X coordinate (0–15).
            y: Local Y coordinate (0–255).
            z: Local Z coordinate (0–15).

        Returns:
            The :class:`Block` at that position, or ``None`` if unset (air).
        """
        return self._blocks[self._index(x, y, z)]

    def set_block(self, x: int, y: int, z: int, block: Optional[Block]) -> None:
        """Place a block at local position (x, y, z).

        Setting a block marks the chunk as dirty.

        Args:
            x:     Local X coordinate (0–15).
            y:     Local Y coordinate (0–255).
            z:     Local Z coordinate (0–15).
            block: The :class:`Block` to place, or ``None`` to clear (air).
        """
        self._blocks[self._index(x, y, z)] = block
        self.dirty = True

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise the chunk to a JSON-compatible dictionary."""
        blocks_data = []
        for i, block in enumerate(self._blocks):
            if block is not None:
                blocks_data.append({"index": i, "block": block.to_dict()})
        return {
            "cx": self.cx,
            "cz": self.cz,
            "blocks": blocks_data,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Chunk":
        """Deserialise a chunk from a dictionary produced by :meth:`to_dict`."""
        chunk = cls(cx=data["cx"], cz=data["cz"])
        for entry in data["blocks"]:
            chunk._blocks[entry["index"]] = Block.from_dict(entry["block"])
        chunk.dirty = False
        return chunk

    def to_json(self) -> str:
        """Serialise to a JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "Chunk":
        """Deserialise from a JSON string."""
        return cls.from_dict(json.loads(json_str))
