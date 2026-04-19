"""
src/terrain/block.py
--------------------
Foundational voxel Block data class for the New Game Plus terrain engine.

Each Block represents a single unit of the voxel grid. Blocks are stored
in 16×16×256 Chunks and are the atomic building unit of the destructible world.

Usage::

    from src.terrain.block import Block, Material

    stone = Block(block_id=2, material=Material.STONE, durability=100)
    print(stone)
    # Block(id=2, material=STONE, durability=100/100, light=0, solid=True)

    stone.mine(damage=30)
    print(stone.durability)  # 70
    print(stone.is_destroyed())  # False
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


class Material(Enum):
    """All valid voxel materials.

    Values correspond to a stable numeric ID used for serialisation.
    Never reorder or remove entries — only append new materials at the end
    so that saved chunk data remains compatible across versions.
    """

    AIR = 0
    DIRT = auto()
    STONE = auto()
    SAND = auto()
    GRAVEL = auto()
    WOOD = auto()
    LEAVES = auto()
    WATER = auto()
    LAVA = auto()
    IRON_ORE = auto()
    GOLD_ORE = auto()
    DIAMOND_ORE = auto()
    OBSIDIAN = auto()
    GLASS = auto()
    CRAFTED_WOOD = auto()
    CRAFTED_STONE = auto()


# ---------------------------------------------------------------------------
# Material property look-up table
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MaterialProps:
    """Immutable physical properties for a given material."""

    base_durability: int
    """Maximum / starting durability when the block is first placed."""

    is_solid: bool
    """Whether the block occupies its full voxel (blocks movement/light)."""

    light_emission: int
    """0–15 light level emitted. 0 means the block emits no light."""

    is_fluid: bool = False
    """Whether the block flows like a fluid (water/lava)."""

    blast_resistance: float = 1.0
    """Multiplier applied to explosive damage received (< 1 = resistant)."""


MATERIAL_PROPS: dict[Material, MaterialProps] = {
    Material.AIR:           MaterialProps(base_durability=0,   is_solid=False, light_emission=0,  is_fluid=False),
    Material.DIRT:          MaterialProps(base_durability=30,  is_solid=True,  light_emission=0),
    Material.STONE:         MaterialProps(base_durability=100, is_solid=True,  light_emission=0,  blast_resistance=1.5),
    Material.SAND:          MaterialProps(base_durability=25,  is_solid=True,  light_emission=0),
    Material.GRAVEL:        MaterialProps(base_durability=30,  is_solid=True,  light_emission=0),
    Material.WOOD:          MaterialProps(base_durability=50,  is_solid=True,  light_emission=0),
    Material.LEAVES:        MaterialProps(base_durability=5,   is_solid=False, light_emission=0),
    Material.WATER:         MaterialProps(base_durability=0,   is_solid=False, light_emission=0,  is_fluid=True),
    Material.LAVA:          MaterialProps(base_durability=0,   is_solid=False, light_emission=15, is_fluid=True),
    Material.IRON_ORE:      MaterialProps(base_durability=150, is_solid=True,  light_emission=0,  blast_resistance=2.0),
    Material.GOLD_ORE:      MaterialProps(base_durability=130, is_solid=True,  light_emission=0,  blast_resistance=1.8),
    Material.DIAMOND_ORE:   MaterialProps(base_durability=200, is_solid=True,  light_emission=0,  blast_resistance=3.0),
    Material.OBSIDIAN:      MaterialProps(base_durability=500, is_solid=True,  light_emission=0,  blast_resistance=10.0),
    Material.GLASS:         MaterialProps(base_durability=10,  is_solid=True,  light_emission=0),
    Material.CRAFTED_WOOD:  MaterialProps(base_durability=60,  is_solid=True,  light_emission=0),
    Material.CRAFTED_STONE: MaterialProps(base_durability=120, is_solid=True,  light_emission=0),
}


# ---------------------------------------------------------------------------
# Block
# ---------------------------------------------------------------------------

@dataclass
class Block:
    """A single voxel block within the New Game Plus world.

    Attributes:
        block_id:     Unique numeric identifier for serialisation.
        material:     The :class:`Material` that defines this block's properties.
        durability:   Remaining hit-points before the block is destroyed.
                      Defaults to the material's ``base_durability``.
        light_level:  Ambient light level at this block position (0–15).
                      Derived from neighbours during light propagation; may
                      also be overridden by the block's own ``light_emission``.
        metadata:     Optional free-form dictionary for block-specific state
                      (e.g. crop growth stage, furnace fuel remaining).
    """

    block_id: int
    material: Material
    durability: int = field(default=-1)  # -1 sentinel → filled in __post_init__
    light_level: int = 0
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.durability == -1:
            self.durability = MATERIAL_PROPS[self.material].base_durability

        props = MATERIAL_PROPS[self.material]
        # Clamp durability to valid range
        self.durability = max(0, min(self.durability, props.base_durability))
        # Clamp light_level to 0-15
        self.light_level = max(0, min(15, self.light_level))

    # ------------------------------------------------------------------
    # Derived properties (delegated to MaterialProps)
    # ------------------------------------------------------------------

    @property
    def props(self) -> MaterialProps:
        """Return the immutable :class:`MaterialProps` for this block's material."""
        return MATERIAL_PROPS[self.material]

    @property
    def is_solid(self) -> bool:
        """``True`` if this block fully occupies its voxel."""
        return self.props.is_solid

    @property
    def is_fluid(self) -> bool:
        """``True`` if this block behaves as a fluid."""
        return self.props.is_fluid

    @property
    def light_emission(self) -> int:
        """Light level emitted by this block type (0–15)."""
        return self.props.light_emission

    @property
    def blast_resistance(self) -> float:
        """Multiplier applied to explosive damage received."""
        return self.props.blast_resistance

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def mine(self, damage: int, tool_efficiency: float = 1.0) -> int:
        """Apply mining damage to this block.

        Args:
            damage:          Raw damage value dealt by the tool.
            tool_efficiency: Multiplier for the tool's effectiveness against
                             this material (default 1.0 = no bonus/penalty).

        Returns:
            Remaining durability after the hit (≥ 0).
        """
        if damage < 0:
            raise ValueError(f"damage must be non-negative, got {damage}")
        effective_damage = int(damage * tool_efficiency)
        self.durability = max(0, self.durability - effective_damage)
        return self.durability

    def repair(self, amount: int) -> int:
        """Restore durability up to the material's ``base_durability``.

        Args:
            amount: Hit-points to restore.

        Returns:
            New durability value.
        """
        if amount < 0:
            raise ValueError(f"amount must be non-negative, got {amount}")
        max_dur = self.props.base_durability
        self.durability = min(max_dur, self.durability + amount)
        return self.durability

    def is_destroyed(self) -> bool:
        """Return ``True`` when durability has reached zero."""
        return self.durability <= 0

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise to a plain dictionary (JSON-compatible)."""
        return {
            "block_id": self.block_id,
            "material": self.material.name,
            "durability": self.durability,
            "light_level": self.light_level,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Block":
        """Deserialise from a plain dictionary produced by :meth:`to_dict`.

        Args:
            data: Dictionary with keys matching the fields of :class:`Block`.

        Returns:
            A new :class:`Block` instance.
        """
        return cls(
            block_id=data["block_id"],
            material=Material[data["material"]],
            durability=data["durability"],
            light_level=data.get("light_level", 0),
            metadata=data.get("metadata", {}),
        )

    def to_json(self) -> str:
        """Serialise to a JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "Block":
        """Deserialise from a JSON string."""
        return cls.from_dict(json.loads(json_str))

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        max_dur = self.props.base_durability
        return (
            f"Block(id={self.block_id}, material={self.material.name}, "
            f"durability={self.durability}/{max_dur}, "
            f"light={self.light_level}, solid={self.is_solid})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Block):
            return NotImplemented
        return self.block_id == other.block_id and self.material == other.material

    def __hash__(self) -> int:
        return hash((self.block_id, self.material))
