"""
src/ai_sim/components.py
------------------------
Pure-data component structs for the New Game Plus ECS simulation layer.

Components carry **no behaviour** — they are data bags consumed by Systems.
Attach them to an :class:`~src.ai_sim.entity.Entity` via
``entity.add_component(Position(x=0, y=64, z=0))``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# VisionType
# ---------------------------------------------------------------------------

class VisionType(Enum):
    """Racial vision types from the D&D 3.5e SRD.

    Attributes:
        NORMAL:           Standard human-range vision; requires light.
        LOW_LIGHT_VISION: Doubles the effective radius of all light sources
                          (Elf, Gnome, Half-Elf, etc.).
        DARKVISION:       Sees in total darkness up to *range_ft* feet as
                          if it were dim light; ignores the 50 % miss chance
                          for darkness within that range (Dwarf, Orc, etc.).
    """

    NORMAL = auto()
    LOW_LIGHT_VISION = auto()
    DARKVISION = auto()


# ---------------------------------------------------------------------------
# Position
# ---------------------------------------------------------------------------

@dataclass
class Position:
    """World-space voxel coordinates of an entity."""

    x: float = 0.0
    y: float = 64.0
    z: float = 0.0

    def __repr__(self) -> str:
        return f"Position({self.x:.1f}, {self.y:.1f}, {self.z:.1f})"


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@dataclass
class Health:
    """Hit-point pool for any entity that can receive damage."""

    current: float
    maximum: float

    @property
    def is_alive(self) -> bool:
        return self.current > 0

    @property
    def percentage(self) -> float:
        return self.current / self.maximum if self.maximum > 0 else 0.0

    def apply_damage(self, amount: float) -> float:
        """Reduce current HP by *amount*. Returns new current HP."""
        self.current = max(0.0, self.current - amount)
        return self.current

    def heal(self, amount: float) -> float:
        """Restore current HP by *amount* (capped at maximum)."""
        self.current = min(self.maximum, self.current + amount)
        return self.current


# ---------------------------------------------------------------------------
# Needs
# ---------------------------------------------------------------------------

class NeedType(Enum):
    """Enumeration of agent/NPC basic needs."""

    HUNGER = auto()
    REST = auto()
    SAFETY = auto()
    SOCIAL = auto()
    PURPOSE = auto()


@dataclass
class Needs:
    """Agent/NPC needs represented as values between 0 (critical) and 100 (satisfied)."""

    hunger: float = 100.0
    rest: float = 100.0
    safety: float = 100.0
    social: float = 100.0
    purpose: float = 100.0

    def most_critical(self) -> NeedType:
        """Return the :class:`NeedType` with the lowest current satisfaction."""
        values = {
            NeedType.HUNGER:  self.hunger,
            NeedType.REST:    self.rest,
            NeedType.SAFETY:  self.safety,
            NeedType.SOCIAL:  self.social,
            NeedType.PURPOSE: self.purpose,
        }
        return min(values, key=lambda k: values[k])

    def tick(self, delta_time: float = 1.0) -> None:
        """Decay all needs by a fixed rate per simulation tick.

        Args:
            delta_time: Elapsed game-time seconds since last tick.
        """
        decay_rates = {
            "hunger":  2.0,
            "rest":    1.0,
            "safety":  0.5,
            "social":  0.8,
            "purpose": 0.3,
        }
        for attr, rate in decay_rates.items():
            current = getattr(self, attr)
            setattr(self, attr, max(0.0, current - rate * delta_time))


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

@dataclass
class Stats:
    """Combat and skill stats for a character, NPC, or creature."""

    strength: int = 10
    dexterity: int = 10
    intelligence: int = 10
    vitality: int = 10
    level: int = 1
    experience: int = 0
    experience_to_next_level: int = 100

    def gain_xp(self, amount: int) -> bool:
        """Add *amount* XP, levelling up if the threshold is crossed.

        Returns:
            ``True`` if a level-up occurred.
        """
        self.experience += amount
        if self.experience >= self.experience_to_next_level:
            self.experience -= self.experience_to_next_level
            self.level += 1
            self.experience_to_next_level = int(self.experience_to_next_level * 1.5)
            return True
        return False

    @property
    def max_health(self) -> int:
        """Derived max HP from vitality."""
        return self.vitality * 10

    @property
    def base_damage(self) -> int:
        """Derived unarmed base damage from strength."""
        return self.strength // 2


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

@dataclass
class Inventory:
    """Simple slot-based inventory component."""

    capacity: int = 20
    _slots: List[Optional[object]] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        if not self._slots:
            self._slots = [None] * self.capacity

    def add_item(self, item: object) -> bool:
        """Place *item* in the first empty slot.

        Returns:
            ``True`` if the item was added; ``False`` if inventory is full.
        """
        for i, slot in enumerate(self._slots):
            if slot is None:
                self._slots[i] = item
                return True
        return False

    def remove_item(self, item: object) -> bool:
        """Remove the first occurrence of *item*.

        Returns:
            ``True`` if found and removed; ``False`` otherwise.
        """
        for i, slot in enumerate(self._slots):
            if slot is item:
                self._slots[i] = None
                return True
        return False

    @property
    def items(self) -> List[object]:
        """Non-None items currently in the inventory."""
        return [s for s in self._slots if s is not None]

    @property
    def is_full(self) -> bool:
        return all(s is not None for s in self._slots)

    @property
    def used_slots(self) -> int:
        return sum(1 for s in self._slots if s is not None)


# ---------------------------------------------------------------------------
# Vision
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Vision:
    """Tracks an entity's current vision capability.

    Attributes:
        vision_type: The entity's racial vision type (Normal, Low-Light, Darkvision).
        range_ft:    Maximum vision range in feet.  Used as the Darkvision cap
                     (typically 60 ft) and the general sight distance limit.
    """

    vision_type: VisionType = VisionType.NORMAL
    range_ft: float = 60.0

    @property
    def has_darkvision(self) -> bool:
        """``True`` if this entity has Darkvision."""
        return self.vision_type == VisionType.DARKVISION

    @property
    def has_low_light_vision(self) -> bool:
        """``True`` if this entity has Low-Light Vision."""
        return self.vision_type == VisionType.LOW_LIGHT_VISION
