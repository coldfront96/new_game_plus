"""
src/loot_math/item.py
---------------------
Foundational Item base class for the New Game Plus loot & progression system.

Items are the primary reward vector in New Game Plus. Each item has a type,
rarity, and a set of affixes (prefix/suffix modifiers) that scale its base
stats. Items are generated procedurally by the :mod:`src.loot_math.item_factory`
module; this file defines only the core data structures.

Usage::

    from src.loot_math.item import Item, ItemType, Rarity, Affix

    # Build an item manually
    fire_prefix = Affix(name="Flaming", stat="fire_damage", value=15)
    quick_suffix = Affix(name="of Haste", stat="attack_speed", value=0.1)

    sword = Item(
        name="Iron Sword",
        item_type=ItemType.WEAPON,
        rarity=Rarity.RARE,
        base_damage=20,
        prefixes=[fire_prefix],
        suffixes=[quick_suffix],
    )
    print(sword)
    print(sword.total_stat("fire_damage"))  # 15
    print(sword.display_name)              # "Flaming Iron Sword of Haste"
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class ItemType(Enum):
    """Broad category of an item, used to filter valid affixes and equipment slots."""

    WEAPON = auto()
    """Melee or ranged weapon — contributes to damage calculations."""

    ARMOUR = auto()
    """Wearable defensive item — contributes to protection calculations."""

    TRINKET = auto()
    """Ring, amulet, or charm — passive stat modifiers only."""

    CONSUMABLE = auto()
    """Single-use item (potions, scrolls, food)."""

    MATERIAL = auto()
    """Raw crafting ingredient — no combat stats."""

    TOOL = auto()
    """Mining / woodcutting / farming tool — has durability."""


class Rarity(Enum):
    """Item rarity tier.  Higher rarity → more affixes + higher stat multipliers."""

    COMMON = 1
    UNCOMMON = 2
    RARE = 3
    EPIC = 4
    LEGENDARY = 5

    @property
    def affix_budget(self) -> int:
        """Maximum total number of affixes (prefix + suffix) for this rarity."""
        return {
            Rarity.COMMON:    0,
            Rarity.UNCOMMON:  1,
            Rarity.RARE:      2,
            Rarity.EPIC:      3,
            Rarity.LEGENDARY: 4,
        }[self]

    @property
    def stat_multiplier(self) -> float:
        """Global multiplier applied to all base stats for this rarity tier."""
        return {
            Rarity.COMMON:    1.00,
            Rarity.UNCOMMON:  1.15,
            Rarity.RARE:      1.35,
            Rarity.EPIC:      1.60,
            Rarity.LEGENDARY: 2.00,
        }[self]

    @property
    def display_colour(self) -> str:
        """Canonical hex colour code for UI rendering of this rarity."""
        return {
            Rarity.COMMON:    "#FFFFFF",
            Rarity.UNCOMMON:  "#1EFF00",
            Rarity.RARE:      "#0070DD",
            Rarity.EPIC:      "#A335EE",
            Rarity.LEGENDARY: "#FF8000",
        }[self]


# ---------------------------------------------------------------------------
# Affix
# ---------------------------------------------------------------------------

@dataclass
class Affix:
    """A single modifier attached to an :class:`Item`.

    Affixes come in two flavours:
    * **Prefix** — prepended to the item name (e.g. *"Flaming"* Sword).
    * **Suffix** — appended to the item name (e.g. Sword *"of Haste"*).

    Attributes:
        name:  Human-readable label shown in the item tooltip.
        stat:  The stat key this affix modifies (e.g. ``"fire_damage"``,
               ``"attack_speed"``, ``"max_health"``).
        value: Numeric bonus applied to *stat*.  For multiplicative affixes
               this is a float (e.g. ``0.1`` = +10 %); for additive affixes
               it is an integer (e.g. ``15`` = +15 flat).
        is_prefix: ``True`` if this is a prefix affix, ``False`` for suffix.
    """

    name: str
    stat: str
    value: float
    is_prefix: bool = True

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "stat": self.stat,
            "value": self.value,
            "is_prefix": self.is_prefix,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Affix":
        return cls(
            name=data["name"],
            stat=data["stat"],
            value=data["value"],
            is_prefix=data.get("is_prefix", True),
        )

    def __repr__(self) -> str:
        kind = "Prefix" if self.is_prefix else "Suffix"
        return f"Affix({kind}: {self.name!r} | {self.stat}+{self.value})"


# ---------------------------------------------------------------------------
# Item
# ---------------------------------------------------------------------------

@dataclass
class Item:
    """Base item data class for the New Game Plus loot system.

    This class holds the complete state of a single item instance.  It is
    intentionally engine-agnostic and can be serialised to JSON for storage
    or network transmission.

    Attributes:
        name:         Base name of the item (e.g. ``"Iron Sword"``).
        item_type:    Broad :class:`ItemType` category.
        rarity:       :class:`Rarity` tier — drives affix budget & stat scaling.
        item_id:      Globally unique identifier (UUID4). Auto-generated.
        base_damage:  Flat damage value (weapons only; 0 for non-weapons).
        base_armour:  Flat armour value (armour only; 0 for non-armour).
        base_speed:   Attack or movement speed modifier (weapon/trinket).
        durability:   Current durability (0 = broken). ``None`` for items
                      that do not degrade (consumables, materials).
        max_durability: Maximum durability at full repair. ``None`` if N/A.
        level_requirement: Minimum colonist level required to equip.
        prefixes:     List of prefix :class:`Affix` modifiers (≤ 2).
        suffixes:     List of suffix :class:`Affix` modifiers (≤ 2).
        metadata:     Free-form dict for game-specific extra data.
    """

    name: str
    item_type: ItemType = ItemType.WEAPON
    rarity: Rarity = Rarity.COMMON
    item_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    base_damage: int = 0
    base_armour: int = 0
    base_speed: float = 1.0
    durability: Optional[int] = None
    max_durability: Optional[int] = None
    level_requirement: int = 1
    prefixes: List[Affix] = field(default_factory=list)
    suffixes: List[Affix] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Validate affix budget
        total_affixes = len(self.prefixes) + len(self.suffixes)
        budget = self.rarity.affix_budget
        if total_affixes > budget:
            raise ValueError(
                f"Item '{self.name}' has {total_affixes} affixes but "
                f"{self.rarity.name} rarity only allows {budget}."
            )
        # Validate prefix / suffix counts individually (max 2 each)
        if len(self.prefixes) > 2:
            raise ValueError(f"Items may have at most 2 prefixes (got {len(self.prefixes)}).")
        if len(self.suffixes) > 2:
            raise ValueError(f"Items may have at most 2 suffixes (got {len(self.suffixes)}).")
        # Sync durability
        if self.max_durability is not None and self.durability is None:
            self.durability = self.max_durability

    # ------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------

    @property
    def display_name(self) -> str:
        """Full display name assembled from prefix + base name + suffix.

        Example::

            "Flaming Iron Sword of Haste"
        """
        parts = []
        for prefix in self.prefixes:
            parts.append(prefix.name)
        parts.append(self.name)
        for suffix in self.suffixes:
            parts.append(suffix.name)
        return " ".join(parts)

    @property
    def effective_damage(self) -> float:
        """Base damage scaled by rarity multiplier."""
        return self.base_damage * self.rarity.stat_multiplier

    @property
    def effective_armour(self) -> float:
        """Base armour scaled by rarity multiplier."""
        return self.base_armour * self.rarity.stat_multiplier

    @property
    def all_affixes(self) -> List[Affix]:
        """Combined list of all prefix and suffix affixes."""
        return list(self.prefixes) + list(self.suffixes)

    def total_stat(self, stat: str) -> float:
        """Sum all affix bonuses for a given stat key.

        Args:
            stat: The stat key to look up (e.g. ``"fire_damage"``).

        Returns:
            Total additive bonus from all matching affixes.
        """
        return sum(a.value for a in self.all_affixes if a.stat == stat)

    def has_stat(self, stat: str) -> bool:
        """Return ``True`` if any affix modifies *stat*."""
        return any(a.stat == stat for a in self.all_affixes)

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def use(self, amount: int = 1) -> Optional[int]:
        """Reduce durability by *amount* (for tools/armour/weapons).

        Args:
            amount: Durability to subtract (must be non-negative).

        Returns:
            Remaining durability, or ``None`` if this item has no durability.

        Raises:
            ValueError: If *amount* is negative.
        """
        if amount < 0:
            raise ValueError(f"amount must be non-negative, got {amount}")
        if self.durability is None:
            return None
        self.durability = max(0, self.durability - amount)
        return self.durability

    def repair(self, amount: int) -> Optional[int]:
        """Restore durability up to ``max_durability``.

        Args:
            amount: Durability to restore (must be non-negative).

        Returns:
            New durability value, or ``None`` if this item has no durability.
        """
        if amount < 0:
            raise ValueError(f"amount must be non-negative, got {amount}")
        if self.durability is None or self.max_durability is None:
            return None
        self.durability = min(self.max_durability, self.durability + amount)
        return self.durability

    def is_broken(self) -> bool:
        """Return ``True`` if durability has reached zero."""
        return self.durability is not None and self.durability <= 0

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise to a plain dictionary (JSON-compatible)."""
        return {
            "item_id": self.item_id,
            "name": self.name,
            "item_type": self.item_type.name,
            "rarity": self.rarity.name,
            "base_damage": self.base_damage,
            "base_armour": self.base_armour,
            "base_speed": self.base_speed,
            "durability": self.durability,
            "max_durability": self.max_durability,
            "level_requirement": self.level_requirement,
            "prefixes": [p.to_dict() for p in self.prefixes],
            "suffixes": [s.to_dict() for s in self.suffixes],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Item":
        """Deserialise from a plain dictionary produced by :meth:`to_dict`.

        Args:
            data: Dictionary with keys matching the fields of :class:`Item`.

        Returns:
            A new :class:`Item` instance.
        """
        return cls(
            item_id=data["item_id"],
            name=data["name"],
            item_type=ItemType[data["item_type"]],
            rarity=Rarity[data["rarity"]],
            base_damage=data.get("base_damage", 0),
            base_armour=data.get("base_armour", 0),
            base_speed=data.get("base_speed", 1.0),
            durability=data.get("durability"),
            max_durability=data.get("max_durability"),
            level_requirement=data.get("level_requirement", 1),
            prefixes=[Affix.from_dict(p) for p in data.get("prefixes", [])],
            suffixes=[Affix.from_dict(s) for s in data.get("suffixes", [])],
            metadata=data.get("metadata", {}),
        )

    def to_json(self) -> str:
        """Serialise to a JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "Item":
        """Deserialise from a JSON string."""
        return cls.from_dict(json.loads(json_str))

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"Item(id={self.item_id[:8]}…, name={self.display_name!r}, "
            f"type={self.item_type.name}, rarity={self.rarity.name}, "
            f"dmg={self.effective_damage:.1f}, armour={self.effective_armour:.1f})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Item):
            return NotImplemented
        return self.item_id == other.item_id

    def __hash__(self) -> int:
        return hash(self.item_id)
