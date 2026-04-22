"""
src/rules_engine/equipment.py
------------------------------
D&D 3.5e Equipment Manager for the New Game Plus engine.

Manages equipment slots and item equipping/unequipping logic following
3.5e SRD rules. Armor provides an "Armor Bonus" to AC, and weapons
provide specific damage dice and hit bonuses.

The system is decoupled from other modules via the :class:`EventBus`,
publishing ``"item_equipped"`` and ``"item_unequipped"`` events when
gear changes occur.

Usage::

    from src.core.event_bus import EventBus
    from src.loot_math.item import Item, ItemType
    from src.rules_engine.equipment import EquipmentManager, EquipmentSlot

    bus = EventBus()
    mgr = EquipmentManager(event_bus=bus)

    plate = Item(name="Full Plate", item_type=ItemType.ARMOUR, base_armour=8)
    mgr.equip_item(plate, EquipmentSlot.TORSO)
    print(mgr.get_armor_bonus())  # 8
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, Optional

from src.core.event_bus import EventBus
from src.loot_math.item import Item, ItemType


# ---------------------------------------------------------------------------
# Equipment Slot Enum
# ---------------------------------------------------------------------------

class EquipmentSlot(Enum):
    """Body slots where equipment can be worn or held (3.5e SRD)."""

    HEAD = auto()
    TORSO = auto()
    MAIN_HAND = auto()
    OFF_HAND = auto()
    LEGS = auto()
    FEET = auto()
    ACCESSORY = auto()


# ---------------------------------------------------------------------------
# Slot-to-ItemType validation mapping
# ---------------------------------------------------------------------------

# Which ItemTypes are valid for each slot
_VALID_SLOT_TYPES: Dict[EquipmentSlot, frozenset] = {
    EquipmentSlot.HEAD: frozenset({ItemType.ARMOUR, ItemType.TRINKET}),
    EquipmentSlot.TORSO: frozenset({ItemType.ARMOUR}),
    EquipmentSlot.MAIN_HAND: frozenset({ItemType.WEAPON, ItemType.TOOL}),
    EquipmentSlot.OFF_HAND: frozenset({ItemType.WEAPON, ItemType.ARMOUR}),
    EquipmentSlot.LEGS: frozenset({ItemType.ARMOUR}),
    EquipmentSlot.FEET: frozenset({ItemType.ARMOUR}),
    EquipmentSlot.ACCESSORY: frozenset({ItemType.TRINKET}),
}


# ---------------------------------------------------------------------------
# EquipmentManager
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class EquipmentManager:
    """Manages equipped items across body slots for a single character.

    Enforces 3.5e slot-type validation: weapons go in hand slots, armour
    goes in body slots, trinkets go in accessory/head slots.

    Publishes ``"item_equipped"`` and ``"item_unequipped"`` events on the
    :class:`EventBus` when gear changes occur.

    Attributes:
        event_bus: The event bus for publishing equipment change events.
        slots:     Mapping of :class:`EquipmentSlot` to the equipped
                   :class:`Item`, or ``None`` if the slot is empty.
    """

    event_bus: Optional[EventBus] = None
    slots: Dict[EquipmentSlot, Optional[Item]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize all slots to empty if not already set."""
        for slot in EquipmentSlot:
            if slot not in self.slots:
                self.slots[slot] = None

    def equip_item(self, item: Item, slot: EquipmentSlot) -> Optional[Item]:
        """Equip an item into the specified slot.

        Validates that the item's type is allowed in the target slot.
        If a different item is already in the slot, it is unequipped first
        and returned.

        Args:
            item: The :class:`Item` to equip.
            slot: The :class:`EquipmentSlot` to place it in.

        Returns:
            The previously equipped item if one was displaced, or ``None``.

        Raises:
            ValueError: If the item's type is not valid for the target slot.
        """
        valid_types = _VALID_SLOT_TYPES.get(slot, frozenset())
        if item.item_type not in valid_types:
            raise ValueError(
                f"Cannot equip {item.item_type.name} item '{item.name}' "
                f"into {slot.name} slot. Valid types: "
                f"{[t.name for t in valid_types]}"
            )

        # Unequip existing item if present
        previous = self.slots.get(slot)
        if previous is not None and previous != item:
            self._publish_unequipped(previous, slot)
        elif previous is not None and previous == item:
            # Same item re-equipped — no change needed
            return None

        self.slots[slot] = item
        self._publish_equipped(item, slot)

        return previous if previous != item else None

    def unequip_slot(self, slot: EquipmentSlot) -> Optional[Item]:
        """Remove and return the item from the specified slot.

        Args:
            slot: The :class:`EquipmentSlot` to clear.

        Returns:
            The item that was removed, or ``None`` if the slot was empty.
        """
        item = self.slots.get(slot)
        if item is not None:
            self.slots[slot] = None
            self._publish_unequipped(item, slot)
        return item

    def get_item(self, slot: EquipmentSlot) -> Optional[Item]:
        """Return the item currently equipped in the given slot.

        Args:
            slot: The :class:`EquipmentSlot` to query.

        Returns:
            The equipped :class:`Item`, or ``None`` if empty.
        """
        return self.slots.get(slot)

    def get_armor_bonus(self) -> int:
        """Calculate total armor bonus from the TORSO slot item.

        In 3.5e, the armor bonus to AC comes from body armor (TORSO).

        Returns:
            Integer armor bonus (``base_armour`` of the TORSO item), or 0.
        """
        torso_item = self.slots.get(EquipmentSlot.TORSO)
        if torso_item is not None and torso_item.item_type == ItemType.ARMOUR:
            return torso_item.base_armour
        return 0

    def get_shield_bonus(self) -> int:
        """Calculate shield bonus from the OFF_HAND slot.

        In 3.5e, a shield equipped in the off-hand provides a shield
        bonus to AC (stored as ``base_armour`` on ARMOUR-type items).

        Returns:
            Integer shield bonus, or 0.
        """
        off_hand = self.slots.get(EquipmentSlot.OFF_HAND)
        if off_hand is not None and off_hand.item_type == ItemType.ARMOUR:
            return off_hand.base_armour
        return 0

    def get_weapon(self) -> Optional[Item]:
        """Return the weapon in the MAIN_HAND slot, if any.

        Returns:
            The main-hand weapon :class:`Item`, or ``None``.
        """
        item = self.slots.get(EquipmentSlot.MAIN_HAND)
        if item is not None and item.item_type == ItemType.WEAPON:
            return item
        return None

    def get_weapon_enhancement_bonus(self) -> int:
        """Return the enhancement bonus from the MAIN_HAND weapon.

        In 3.5e, magical weapons have an enhancement bonus that applies
        to both attack and damage rolls. Stored in the item's
        ``enhancement_bonus`` metadata field.

        Returns:
            Integer enhancement bonus, or 0 if no weapon or non-magical.
        """
        weapon = self.get_weapon()
        if weapon is not None:
            return int(weapon.metadata.get("enhancement_bonus", 0))
        return 0

    def get_weapon_damage_dice(self) -> tuple:
        """Return the weapon's damage dice (count, sides) from metadata.

        3.5e weapons define their damage as NdM (e.g., longsword = 1d8).
        Stored in metadata as ``damage_dice_count`` and ``damage_dice_sides``.

        Returns:
            Tuple of (dice_count, dice_sides), or (0, 0) if no weapon.
        """
        weapon = self.get_weapon()
        if weapon is not None:
            count = int(weapon.metadata.get("damage_dice_count", 0))
            sides = int(weapon.metadata.get("damage_dice_sides", 0))
            return (count, sides)
        return (0, 0)

    def is_slot_empty(self, slot: EquipmentSlot) -> bool:
        """Return ``True`` if the specified slot has no item equipped."""
        return self.slots.get(slot) is None

    def get_total_asf(self) -> int:
        """Calculate the total Arcane Spell Failure chance from all equipped armor.

        In 3.5e SRD, each armor and shield contributes an ASF percentage that
        applies when an arcane caster attempts a spell with a somatic component.
        The chances from multiple pieces of armor stack additively.

        The ASF percentage for each item is stored in the item's ``metadata``
        dict under the key ``"asf_chance"`` as an integer (e.g., ``35`` for
        Full Plate's 35% ASF).

        Returns:
            Total ASF percentage (0–100+) from all equipped armor items.
        """
        total = 0
        for slot in (EquipmentSlot.TORSO, EquipmentSlot.HEAD,
                     EquipmentSlot.OFF_HAND, EquipmentSlot.LEGS,
                     EquipmentSlot.FEET):
            item = self.slots.get(slot)
            if item is not None and item.item_type == ItemType.ARMOUR:
                total += int(item.metadata.get("asf_chance", 0))
        return total

    def _publish_equipped(self, item: Item, slot: EquipmentSlot) -> None:
        """Publish an item_equipped event."""
        if self.event_bus is not None:
            self.event_bus.publish("item_equipped", {
                "item_id": item.item_id,
                "item_name": item.name,
                "item_type": item.item_type.name,
                "slot": slot.name,
            })

    def _publish_unequipped(self, item: Item, slot: EquipmentSlot) -> None:
        """Publish an item_unequipped event."""
        if self.event_bus is not None:
            self.event_bus.publish("item_unequipped", {
                "item_id": item.item_id,
                "item_name": item.name,
                "item_type": item.item_type.name,
                "slot": slot.name,
            })
