"""
src/rules_engine/magic_items.py
---------------------------------
D&D 3.5e DMG Magic Item Engine — Enhancement Bonuses & Wondrous Items.

Implements:

- Enhancement bonuses on weapons and armour (DMG p.216–219, p.221–224):
  ``+1`` through ``+5`` on melee/ranged weapons and on armour/shields.

- Wondrous Items (DMG Chapter 7): ability-score enhancement items (belts,
  gloves, headbands, periapts, cloaks, amulets), protection items (ring of
  protection, amulet of natural armour), and resistance cloaks.

- :class:`MagicItemEngine` accumulates bonuses from all worn wondrous items,
  enforcing the 3.5e non-stacking rule for same-typed bonuses from the same
  bonus category.

Bonus stacking rules (3.5e SRD p.170):
  * Enhancement bonuses of the same kind do **not** stack — the highest applies.
  * Deflection bonuses do not stack.
  * Natural armour bonuses do not stack (from the same source type).
  * Resistance bonuses to saves do not stack.
  * Different *types* of bonus always stack.

Usage::

    from src.rules_engine.magic_items import (
        MagicItemEngine, WondrousItem,
        make_magic_weapon, make_magic_armor,
        WONDROUS_ITEM_REGISTRY, RING_REGISTRY,
    )
    from src.loot_math.item import Item, ItemType

    # Equip a Belt of Giant Strength +4 and a Cloak of Resistance +2
    engine = MagicItemEngine()
    belt = WONDROUS_ITEM_REGISTRY["belt_of_giant_strength_4"]
    cloak = WONDROUS_ITEM_REGISTRY["cloak_of_resistance_2"]
    engine.add_item(belt)
    engine.add_item(cloak)

    print(engine.get_ability_enhancement("strength"))   # 4
    print(engine.get_resistance_bonus())                # 2

    # Build a +3 longsword
    base = Item(name="Longsword", item_type=ItemType.WEAPON, base_damage=4,
                metadata={"damage_dice_count": 1, "damage_dice_sides": 8})
    magic = make_magic_weapon(base, enhancement=3)
    print(magic.metadata["enhancement_bonus"])          # 3
    print(magic.metadata["market_price_gp"])            # 18_000 + base cost
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional

from src.loot_math.item import Item, ItemType


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class MagicItemCategory(Enum):
    """Broad categories of magic items (3.5e DMG Chapter 7)."""

    WEAPON = "weapon"
    ARMOR = "armor"
    SHIELD = "shield"
    RING = "ring"
    ROD = "rod"
    STAFF = "staff"
    WAND = "wand"
    POTION = "potion"
    SCROLL = "scroll"
    WONDROUS = "wondrous"


class BonusType(Enum):
    """Bonus categories that govern stacking rules (SRD p.170)."""

    ENHANCEMENT = "enhancement"
    """Enhancement bonuses from magic — same type does not stack."""

    DEFLECTION = "deflection"
    """Deflection bonus to AC (e.g. Ring of Protection) — does not stack."""

    NATURAL_ARMOR = "natural_armor"
    """Natural armour bonus to AC (e.g. Amulet of Natural Armor) — does not
    stack with other natural armour bonuses of the same type."""

    RESISTANCE = "resistance"
    """Resistance bonus to saving throws (e.g. Cloak of Resistance) — does
    not stack."""

    LUCK = "luck"
    """Luck bonuses do not stack with each other."""

    MORALE = "morale"
    """Morale bonuses do not stack with each other."""

    COMPETENCE = "competence"
    """Competence bonuses to skills/attacks do not stack."""

    CIRCUMSTANCE = "circumstance"
    """Circumstance bonuses may stack from different sources."""

    INHERENT = "inherent"
    """Inherent bonuses (e.g. from wishes) do not stack."""


# ---------------------------------------------------------------------------
# MagicBonus dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class MagicBonus:
    """A single typed bonus granted by a magic item.

    Attributes:
        bonus_type: The bonus category (governs stacking).
        stat:       The affected stat key.
                    Ability names: ``"strength"``, ``"dexterity"``,
                    ``"constitution"``, ``"intelligence"``, ``"wisdom"``,
                    ``"charisma"``.
                    Other recognised keys: ``"ac"`` (natural armour or
                    deflection applied to AC), ``"all_saves"`` (resistance
                    to all three saves), ``"fortitude"``, ``"reflex"``,
                    ``"will"``.
        value:      Magnitude of the bonus (always positive).
    """

    bonus_type: BonusType
    stat: str
    value: int


# ---------------------------------------------------------------------------
# WondrousItem dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class WondrousItem:
    """A 3.5e DMG wondrous item or ring definition.

    Attributes:
        name:         Item name (e.g. ``"Belt of Giant Strength +4"``).
        category:     :class:`MagicItemCategory` (usually WONDROUS or RING).
        slot:         Body slot required to wear (e.g. ``"belt"``, ``"ring"``,
                      ``"cloak"``, ``"head"``, ``"neck"``, ``"gloves"``,
                      ``"feet"``, ``"none"``).
        caster_level: Minimum caster level required to create the item.
        price_gp:     Market price in gold pieces (SRD reference).
        weight_lb:    Weight in pounds.
        bonuses:      List of :class:`MagicBonus` objects granted while worn.
        aura:         Aura school and strength (e.g. ``"moderate transmutation"``).
        description:  Brief flavour / rules description.
    """

    name: str
    category: MagicItemCategory
    slot: str
    caster_level: int
    price_gp: int
    weight_lb: float
    bonuses: List[MagicBonus]
    aura: str
    description: str = ""


# ---------------------------------------------------------------------------
# MagicItemEngine
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class MagicItemEngine:
    """Aggregates bonuses from all currently worn magic/wondrous items.

    Enforces the 3.5e non-stacking rule: for any given :class:`BonusType`,
    only the **highest** value for each *stat* applies.

    Typical usage (attach to :class:`~src.rules_engine.character_35e.Character35e`)::

        engine = MagicItemEngine()
        engine.add_item(WONDROUS_ITEM_REGISTRY["belt_of_giant_strength_4"])
        engine.add_item(WONDROUS_ITEM_REGISTRY["cloak_of_resistance_2"])

        char.magic_item_engine = engine
        # strength_mod, armor_class, fortitude_save etc. pick up the bonuses.

    Attributes:
        _items: The currently worn :class:`WondrousItem` objects.
    """

    _items: List[WondrousItem] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_item(self, item: WondrousItem) -> None:
        """Equip a wondrous item or ring.

        Args:
            item: The :class:`WondrousItem` to add.
        """
        self._items.append(item)

    def remove_item(self, item: WondrousItem) -> bool:
        """Remove a previously equipped item.

        Args:
            item: The :class:`WondrousItem` to remove.

        Returns:
            ``True`` if the item was found and removed, ``False`` otherwise.
        """
        try:
            self._items.remove(item)
            return True
        except ValueError:
            return False

    def clear(self) -> None:
        """Remove all equipped items."""
        self._items.clear()

    @property
    def items(self) -> List[WondrousItem]:
        """Read-only view of currently worn items."""
        return list(self._items)

    # ------------------------------------------------------------------
    # Internal aggregation helper
    # ------------------------------------------------------------------

    def _best_bonus(self, bonus_type: BonusType, stat: str) -> int:
        """Return the highest bonus of *bonus_type* targeting *stat*.

        Implements the non-stacking rule: only the maximum value for the
        given *(bonus_type, stat)* pair contributes.
        """
        best = 0
        for item in self._items:
            for mb in item.bonuses:
                if mb.bonus_type == bonus_type and mb.stat == stat:
                    if mb.value > best:
                        best = mb.value
        return best

    # ------------------------------------------------------------------
    # Ability score enhancement bonuses
    # ------------------------------------------------------------------

    def get_ability_enhancement(self, ability: str) -> int:
        """Return the highest enhancement bonus to the named ability score.

        Per the 3.5e SRD, enhancement bonuses to the same ability score do
        not stack — only the highest applies.

        Args:
            ability: One of ``"strength"``, ``"dexterity"``, ``"constitution"``,
                     ``"intelligence"``, ``"wisdom"``, ``"charisma"``.

        Returns:
            Enhancement bonus magnitude (≥ 0).
        """
        return self._best_bonus(BonusType.ENHANCEMENT, ability)

    # ------------------------------------------------------------------
    # Armour class bonuses
    # ------------------------------------------------------------------

    def get_deflection_bonus(self) -> int:
        """Return the best deflection bonus to AC (e.g. Ring of Protection).

        Deflection bonuses from multiple sources do **not** stack.

        Returns:
            Best deflection bonus (≥ 0).
        """
        return self._best_bonus(BonusType.DEFLECTION, "ac")

    def get_natural_armor_bonus(self) -> int:
        """Return the best natural armour bonus to AC (e.g. Amulet of Natural Armor).

        Natural armour enhancement bonuses do not stack with each other.

        Returns:
            Best natural armour bonus (≥ 0).
        """
        return self._best_bonus(BonusType.NATURAL_ARMOR, "ac")

    # ------------------------------------------------------------------
    # Saving throw bonuses
    # ------------------------------------------------------------------

    def get_resistance_bonus(self) -> int:
        """Return the best resistance bonus to all saving throws.

        A *Cloak of Resistance* applies a resistance bonus to all three
        saves (Fortitude, Reflex, Will). Multiple resistance bonuses do
        **not** stack.

        Returns:
            Best all-saves resistance bonus (≥ 0).
        """
        return self._best_bonus(BonusType.RESISTANCE, "all_saves")

    def get_save_bonus(self, save: str) -> int:
        """Return the total bonus to a specific saving throw.

        Includes the best ``all_saves`` resistance bonus plus the best
        save-specific resistance bonus (e.g. a theoretical Cloak of
        Fortitude), taking the maximum across all resistance sources that
        cover the named save.

        Args:
            save: ``"fortitude"``, ``"reflex"``, or ``"will"``.

        Returns:
            Total resistance bonus for the named save (≥ 0).
        """
        all_saves_bonus = self._best_bonus(BonusType.RESISTANCE, "all_saves")
        specific_bonus = self._best_bonus(BonusType.RESISTANCE, save)
        return max(all_saves_bonus, specific_bonus)


# ---------------------------------------------------------------------------
# Factory functions — magic weapons & armour
# ---------------------------------------------------------------------------

# Market price bonus per enhancement level (weapon = base + 2000 × bonus²)
_WEAPON_ENHANCEMENT_BONUS_PRICE: Dict[int, int] = {
    1: 2_000,
    2: 8_000,
    3: 18_000,
    4: 32_000,
    5: 50_000,
}

# Market price bonus per enhancement level (armour = base + 1000 × bonus²)
_ARMOR_ENHANCEMENT_BONUS_PRICE: Dict[int, int] = {
    1: 1_000,
    2: 4_000,
    3: 9_000,
    4: 16_000,
    5: 25_000,
}


def make_magic_weapon(base_item: Item, enhancement: int) -> Item:
    """Return a copy of *base_item* with a weapon enhancement bonus applied.

    The enhancement bonus is stored in ``metadata["enhancement_bonus"]``, which
    the :class:`~src.rules_engine.equipment.EquipmentManager` already reads for
    attack and damage roll bonuses.  The computed market price (base item value +
    the SRD formula ``2 000 × bonus²`` gp) is stored in
    ``metadata["market_price_gp"]``.

    Args:
        base_item:   The mundane :class:`~src.loot_math.item.Item` to enchant.
                     Must be :class:`~src.loot_math.item.ItemType.WEAPON`.
        enhancement: Enhancement bonus (+1 through +5).

    Returns:
        A **new** :class:`~src.loot_math.item.Item` instance (the original is not
        mutated) with updated metadata.

    Raises:
        ValueError: If *base_item* is not a WEAPON or if *enhancement* is out of
                    range.
    """
    if base_item.item_type != ItemType.WEAPON:
        raise ValueError(
            f"make_magic_weapon requires a WEAPON item; got {base_item.item_type.name}"
        )
    if enhancement not in _WEAPON_ENHANCEMENT_BONUS_PRICE:
        raise ValueError(
            f"Enhancement bonus must be 1–5; got {enhancement}"
        )

    new_item = copy.deepcopy(base_item)
    bonus_price = _WEAPON_ENHANCEMENT_BONUS_PRICE[enhancement]
    base_price = int(new_item.metadata.get("market_price_gp", 0))

    new_item.metadata["enhancement_bonus"] = enhancement
    new_item.metadata["market_price_gp"] = base_price + bonus_price

    # Rename to reflect enhancement if not already named
    if not new_item.name.startswith("+"):
        new_item.name = f"+{enhancement} {new_item.name}"

    return new_item


def make_magic_armor(base_item: Item, enhancement: int) -> Item:
    """Return a copy of *base_item* with an armour or shield enhancement bonus.

    The enhancement bonus is stored in ``metadata["enhancement_bonus"]``.  For
    armour this adds to the AC bonus at resolution time (integrate with
    :class:`~src.rules_engine.equipment.EquipmentManager` by reading the metadata
    key).  The computed market price follows the SRD formula ``1 000 × bonus²`` gp
    and is stored in ``metadata["market_price_gp"]``.

    Args:
        base_item:   A mundane :class:`~src.loot_math.item.Item` of type ARMOUR.
        enhancement: Enhancement bonus (+1 through +5).

    Returns:
        A **new** :class:`~src.loot_math.item.Item` instance with updated metadata.

    Raises:
        ValueError: If *base_item* is not ARMOUR or if *enhancement* is out of
                    range.
    """
    if base_item.item_type != ItemType.ARMOUR:
        raise ValueError(
            f"make_magic_armor requires an ARMOUR item; got {base_item.item_type.name}"
        )
    if enhancement not in _ARMOR_ENHANCEMENT_BONUS_PRICE:
        raise ValueError(
            f"Enhancement bonus must be 1–5; got {enhancement}"
        )

    new_item = copy.deepcopy(base_item)
    bonus_price = _ARMOR_ENHANCEMENT_BONUS_PRICE[enhancement]
    base_price = int(new_item.metadata.get("market_price_gp", 0))

    new_item.metadata["enhancement_bonus"] = enhancement
    new_item.metadata["market_price_gp"] = base_price + bonus_price

    if not new_item.name.startswith("+"):
        new_item.name = f"+{enhancement} {new_item.name}"

    return new_item


# ---------------------------------------------------------------------------
# EquipmentManager integration — armour enhancement bonus helper
# ---------------------------------------------------------------------------

def get_armor_enhancement_bonus(equipment_manager: object) -> int:  # type: ignore[attr-defined]
    """Return the total enhancement bonus from the TORSO armour and OFF_HAND shield.

    Reads ``metadata["enhancement_bonus"]`` from each relevant slot.  The
    :class:`~src.rules_engine.equipment.EquipmentManager` stores weapon
    enhancement via :meth:`~src.rules_engine.equipment.EquipmentManager.get_weapon_enhancement_bonus`;
    this function provides the parallel helper for armour / shields.

    Args:
        equipment_manager: An :class:`~src.rules_engine.equipment.EquipmentManager`
                           instance (typed as ``object`` to avoid a circular import).

    Returns:
        Sum of enhancement bonuses from TORSO armour and OFF_HAND shield (≥ 0).
    """
    from src.rules_engine.equipment import EquipmentSlot

    total = 0
    for slot in (EquipmentSlot.TORSO, EquipmentSlot.OFF_HAND):
        item = equipment_manager.slots.get(slot)  # type: ignore[attr-defined]
        if item is not None:
            total += int(item.metadata.get("enhancement_bonus", 0))
    return total


# ---------------------------------------------------------------------------
# SRD Wondrous Item Registry
# ---------------------------------------------------------------------------

WONDROUS_ITEM_REGISTRY: Dict[str, WondrousItem] = {

    # -----------------------------------------------------------------------
    # Belt slot — Strength enhancement (DMG p.250)
    # -----------------------------------------------------------------------
    "belt_of_giant_strength_2": WondrousItem(
        name="Belt of Giant Strength +2",
        category=MagicItemCategory.WONDROUS,
        slot="belt",
        caster_level=8,
        price_gp=4_000,
        weight_lb=1.0,
        bonuses=[MagicBonus(BonusType.ENHANCEMENT, "strength", 2)],
        aura="moderate transmutation",
        description=(
            "This wide belt grants the wearer an enhancement bonus of +2 to "
            "Strength."
        ),
    ),
    "belt_of_giant_strength_4": WondrousItem(
        name="Belt of Giant Strength +4",
        category=MagicItemCategory.WONDROUS,
        slot="belt",
        caster_level=8,
        price_gp=16_000,
        weight_lb=1.0,
        bonuses=[MagicBonus(BonusType.ENHANCEMENT, "strength", 4)],
        aura="moderate transmutation",
        description=(
            "This wide belt grants the wearer an enhancement bonus of +4 to "
            "Strength."
        ),
    ),
    "belt_of_giant_strength_6": WondrousItem(
        name="Belt of Giant Strength +6",
        category=MagicItemCategory.WONDROUS,
        slot="belt",
        caster_level=8,
        price_gp=36_000,
        weight_lb=1.0,
        bonuses=[MagicBonus(BonusType.ENHANCEMENT, "strength", 6)],
        aura="strong transmutation",
        description=(
            "This wide belt grants the wearer an enhancement bonus of +6 to "
            "Strength."
        ),
    ),

    # -----------------------------------------------------------------------
    # Gauntlets slot — Strength enhancement (DMG p.258)
    # -----------------------------------------------------------------------
    "gauntlets_of_ogre_power": WondrousItem(
        name="Gauntlets of Ogre Power",
        category=MagicItemCategory.WONDROUS,
        slot="gloves",
        caster_level=6,
        price_gp=4_000,
        weight_lb=4.0,
        bonuses=[MagicBonus(BonusType.ENHANCEMENT, "strength", 2)],
        aura="moderate transmutation",
        description=(
            "These sturdy gauntlets grant an enhancement bonus of +2 to "
            "Strength."
        ),
    ),

    # -----------------------------------------------------------------------
    # Gloves slot — Dexterity enhancement (DMG p.258)
    # -----------------------------------------------------------------------
    "gloves_of_dexterity_2": WondrousItem(
        name="Gloves of Dexterity +2",
        category=MagicItemCategory.WONDROUS,
        slot="gloves",
        caster_level=6,
        price_gp=4_000,
        weight_lb=0.1,
        bonuses=[MagicBonus(BonusType.ENHANCEMENT, "dexterity", 2)],
        aura="moderate transmutation",
        description=(
            "These thin gloves grant an enhancement bonus of +2 to Dexterity."
        ),
    ),
    "gloves_of_dexterity_4": WondrousItem(
        name="Gloves of Dexterity +4",
        category=MagicItemCategory.WONDROUS,
        slot="gloves",
        caster_level=6,
        price_gp=16_000,
        weight_lb=0.1,
        bonuses=[MagicBonus(BonusType.ENHANCEMENT, "dexterity", 4)],
        aura="moderate transmutation",
        description=(
            "These thin gloves grant an enhancement bonus of +4 to Dexterity."
        ),
    ),
    "gloves_of_dexterity_6": WondrousItem(
        name="Gloves of Dexterity +6",
        category=MagicItemCategory.WONDROUS,
        slot="gloves",
        caster_level=6,
        price_gp=36_000,
        weight_lb=0.1,
        bonuses=[MagicBonus(BonusType.ENHANCEMENT, "dexterity", 6)],
        aura="strong transmutation",
        description=(
            "These thin gloves grant an enhancement bonus of +6 to Dexterity."
        ),
    ),

    # -----------------------------------------------------------------------
    # Head slot — Intelligence enhancement (DMG p.258)
    # -----------------------------------------------------------------------
    "headband_of_intellect_2": WondrousItem(
        name="Headband of Intellect +2",
        category=MagicItemCategory.WONDROUS,
        slot="head",
        caster_level=8,
        price_gp=4_000,
        weight_lb=0.1,
        bonuses=[MagicBonus(BonusType.ENHANCEMENT, "intelligence", 2)],
        aura="moderate transmutation",
        description=(
            "This device grants an enhancement bonus of +2 to Intelligence."
        ),
    ),
    "headband_of_intellect_4": WondrousItem(
        name="Headband of Intellect +4",
        category=MagicItemCategory.WONDROUS,
        slot="head",
        caster_level=8,
        price_gp=16_000,
        weight_lb=0.1,
        bonuses=[MagicBonus(BonusType.ENHANCEMENT, "intelligence", 4)],
        aura="moderate transmutation",
        description=(
            "This device grants an enhancement bonus of +4 to Intelligence."
        ),
    ),
    "headband_of_intellect_6": WondrousItem(
        name="Headband of Intellect +6",
        category=MagicItemCategory.WONDROUS,
        slot="head",
        caster_level=8,
        price_gp=36_000,
        weight_lb=0.1,
        bonuses=[MagicBonus(BonusType.ENHANCEMENT, "intelligence", 6)],
        aura="strong transmutation",
        description=(
            "This device grants an enhancement bonus of +6 to Intelligence."
        ),
    ),

    # -----------------------------------------------------------------------
    # Neck slot — Wisdom enhancement (DMG p.263)
    # -----------------------------------------------------------------------
    "periapt_of_wisdom_2": WondrousItem(
        name="Periapt of Wisdom +2",
        category=MagicItemCategory.WONDROUS,
        slot="neck",
        caster_level=8,
        price_gp=4_000,
        weight_lb=0.1,
        bonuses=[MagicBonus(BonusType.ENHANCEMENT, "wisdom", 2)],
        aura="moderate transmutation",
        description=(
            "This gemstone grants an enhancement bonus of +2 to Wisdom."
        ),
    ),
    "periapt_of_wisdom_4": WondrousItem(
        name="Periapt of Wisdom +4",
        category=MagicItemCategory.WONDROUS,
        slot="neck",
        caster_level=8,
        price_gp=16_000,
        weight_lb=0.1,
        bonuses=[MagicBonus(BonusType.ENHANCEMENT, "wisdom", 4)],
        aura="moderate transmutation",
        description=(
            "This gemstone grants an enhancement bonus of +4 to Wisdom."
        ),
    ),
    "periapt_of_wisdom_6": WondrousItem(
        name="Periapt of Wisdom +6",
        category=MagicItemCategory.WONDROUS,
        slot="neck",
        caster_level=8,
        price_gp=36_000,
        weight_lb=0.1,
        bonuses=[MagicBonus(BonusType.ENHANCEMENT, "wisdom", 6)],
        aura="strong transmutation",
        description=(
            "This gemstone grants an enhancement bonus of +6 to Wisdom."
        ),
    ),

    # -----------------------------------------------------------------------
    # Cloak slot — Charisma enhancement (DMG p.254)
    # -----------------------------------------------------------------------
    "cloak_of_charisma_2": WondrousItem(
        name="Cloak of Charisma +2",
        category=MagicItemCategory.WONDROUS,
        slot="cloak",
        caster_level=8,
        price_gp=4_000,
        weight_lb=1.0,
        bonuses=[MagicBonus(BonusType.ENHANCEMENT, "charisma", 2)],
        aura="moderate transmutation",
        description=(
            "This cloak grants an enhancement bonus of +2 to Charisma."
        ),
    ),
    "cloak_of_charisma_4": WondrousItem(
        name="Cloak of Charisma +4",
        category=MagicItemCategory.WONDROUS,
        slot="cloak",
        caster_level=8,
        price_gp=16_000,
        weight_lb=1.0,
        bonuses=[MagicBonus(BonusType.ENHANCEMENT, "charisma", 4)],
        aura="moderate transmutation",
        description=(
            "This cloak grants an enhancement bonus of +4 to Charisma."
        ),
    ),
    "cloak_of_charisma_6": WondrousItem(
        name="Cloak of Charisma +6",
        category=MagicItemCategory.WONDROUS,
        slot="cloak",
        caster_level=8,
        price_gp=36_000,
        weight_lb=1.0,
        bonuses=[MagicBonus(BonusType.ENHANCEMENT, "charisma", 6)],
        aura="strong transmutation",
        description=(
            "This cloak grants an enhancement bonus of +6 to Charisma."
        ),
    ),

    # -----------------------------------------------------------------------
    # Neck slot — Constitution enhancement (DMG p.247)
    # -----------------------------------------------------------------------
    "amulet_of_health_2": WondrousItem(
        name="Amulet of Health +2",
        category=MagicItemCategory.WONDROUS,
        slot="neck",
        caster_level=8,
        price_gp=4_000,
        weight_lb=0.1,
        bonuses=[MagicBonus(BonusType.ENHANCEMENT, "constitution", 2)],
        aura="moderate transmutation",
        description=(
            "This amulet grants an enhancement bonus of +2 to Constitution."
        ),
    ),
    "amulet_of_health_4": WondrousItem(
        name="Amulet of Health +4",
        category=MagicItemCategory.WONDROUS,
        slot="neck",
        caster_level=8,
        price_gp=16_000,
        weight_lb=0.1,
        bonuses=[MagicBonus(BonusType.ENHANCEMENT, "constitution", 4)],
        aura="moderate transmutation",
        description=(
            "This amulet grants an enhancement bonus of +4 to Constitution."
        ),
    ),
    "amulet_of_health_6": WondrousItem(
        name="Amulet of Health +6",
        category=MagicItemCategory.WONDROUS,
        slot="neck",
        caster_level=8,
        price_gp=36_000,
        weight_lb=0.1,
        bonuses=[MagicBonus(BonusType.ENHANCEMENT, "constitution", 6)],
        aura="strong transmutation",
        description=(
            "This amulet grants an enhancement bonus of +6 to Constitution."
        ),
    ),

    # -----------------------------------------------------------------------
    # Neck slot — Natural armour bonus (DMG p.248)
    # -----------------------------------------------------------------------
    "amulet_of_natural_armor_1": WondrousItem(
        name="Amulet of Natural Armor +1",
        category=MagicItemCategory.WONDROUS,
        slot="neck",
        caster_level=5,
        price_gp=2_000,
        weight_lb=0.1,
        bonuses=[MagicBonus(BonusType.NATURAL_ARMOR, "ac", 1)],
        aura="faint transmutation",
        description=(
            "This amulet toughens the wearer's body and skin, granting a +1 "
            "enhancement bonus to the wearer's existing natural armour bonus."
        ),
    ),
    "amulet_of_natural_armor_2": WondrousItem(
        name="Amulet of Natural Armor +2",
        category=MagicItemCategory.WONDROUS,
        slot="neck",
        caster_level=5,
        price_gp=8_000,
        weight_lb=0.1,
        bonuses=[MagicBonus(BonusType.NATURAL_ARMOR, "ac", 2)],
        aura="faint transmutation",
        description=(
            "This amulet toughens the wearer's body, granting a +2 "
            "enhancement bonus to natural armour."
        ),
    ),
    "amulet_of_natural_armor_3": WondrousItem(
        name="Amulet of Natural Armor +3",
        category=MagicItemCategory.WONDROUS,
        slot="neck",
        caster_level=5,
        price_gp=18_000,
        weight_lb=0.1,
        bonuses=[MagicBonus(BonusType.NATURAL_ARMOR, "ac", 3)],
        aura="moderate transmutation",
        description=(
            "This amulet grants a +3 enhancement bonus to natural armour."
        ),
    ),
    "amulet_of_natural_armor_4": WondrousItem(
        name="Amulet of Natural Armor +4",
        category=MagicItemCategory.WONDROUS,
        slot="neck",
        caster_level=5,
        price_gp=32_000,
        weight_lb=0.1,
        bonuses=[MagicBonus(BonusType.NATURAL_ARMOR, "ac", 4)],
        aura="moderate transmutation",
        description=(
            "This amulet grants a +4 enhancement bonus to natural armour."
        ),
    ),
    "amulet_of_natural_armor_5": WondrousItem(
        name="Amulet of Natural Armor +5",
        category=MagicItemCategory.WONDROUS,
        slot="neck",
        caster_level=5,
        price_gp=50_000,
        weight_lb=0.1,
        bonuses=[MagicBonus(BonusType.NATURAL_ARMOR, "ac", 5)],
        aura="strong transmutation",
        description=(
            "This amulet grants a +5 enhancement bonus to natural armour."
        ),
    ),

    # -----------------------------------------------------------------------
    # Cloak slot — Resistance to saves (DMG p.254)
    # -----------------------------------------------------------------------
    "cloak_of_resistance_1": WondrousItem(
        name="Cloak of Resistance +1",
        category=MagicItemCategory.WONDROUS,
        slot="cloak",
        caster_level=5,
        price_gp=1_000,
        weight_lb=1.0,
        bonuses=[MagicBonus(BonusType.RESISTANCE, "all_saves", 1)],
        aura="faint abjuration",
        description=(
            "This cloak of magical weave grants its wearer a +1 resistance "
            "bonus on all saving throws."
        ),
    ),
    "cloak_of_resistance_2": WondrousItem(
        name="Cloak of Resistance +2",
        category=MagicItemCategory.WONDROUS,
        slot="cloak",
        caster_level=5,
        price_gp=4_000,
        weight_lb=1.0,
        bonuses=[MagicBonus(BonusType.RESISTANCE, "all_saves", 2)],
        aura="faint abjuration",
        description=(
            "This cloak grants a +2 resistance bonus on all saving throws."
        ),
    ),
    "cloak_of_resistance_3": WondrousItem(
        name="Cloak of Resistance +3",
        category=MagicItemCategory.WONDROUS,
        slot="cloak",
        caster_level=5,
        price_gp=9_000,
        weight_lb=1.0,
        bonuses=[MagicBonus(BonusType.RESISTANCE, "all_saves", 3)],
        aura="moderate abjuration",
        description=(
            "This cloak grants a +3 resistance bonus on all saving throws."
        ),
    ),
    "cloak_of_resistance_4": WondrousItem(
        name="Cloak of Resistance +4",
        category=MagicItemCategory.WONDROUS,
        slot="cloak",
        caster_level=5,
        price_gp=16_000,
        weight_lb=1.0,
        bonuses=[MagicBonus(BonusType.RESISTANCE, "all_saves", 4)],
        aura="moderate abjuration",
        description=(
            "This cloak grants a +4 resistance bonus on all saving throws."
        ),
    ),
    "cloak_of_resistance_5": WondrousItem(
        name="Cloak of Resistance +5",
        category=MagicItemCategory.WONDROUS,
        slot="cloak",
        caster_level=5,
        price_gp=25_000,
        weight_lb=1.0,
        bonuses=[MagicBonus(BonusType.RESISTANCE, "all_saves", 5)],
        aura="strong abjuration",
        description=(
            "This cloak grants a +5 resistance bonus on all saving throws."
        ),
    ),
}


# ---------------------------------------------------------------------------
# SRD Ring Registry — Rings of Protection (DMG p.232)
# ---------------------------------------------------------------------------

RING_REGISTRY: Dict[str, WondrousItem] = {
    "ring_of_protection_1": WondrousItem(
        name="Ring of Protection +1",
        category=MagicItemCategory.RING,
        slot="ring",
        caster_level=5,
        price_gp=2_000,
        weight_lb=0.0,
        bonuses=[MagicBonus(BonusType.DEFLECTION, "ac", 1)],
        aura="faint abjuration",
        description=(
            "This ring offers continual magical protection in the form of a "
            "+1 deflection bonus to AC."
        ),
    ),
    "ring_of_protection_2": WondrousItem(
        name="Ring of Protection +2",
        category=MagicItemCategory.RING,
        slot="ring",
        caster_level=5,
        price_gp=8_000,
        weight_lb=0.0,
        bonuses=[MagicBonus(BonusType.DEFLECTION, "ac", 2)],
        aura="faint abjuration",
        description=(
            "This ring provides a +2 deflection bonus to AC."
        ),
    ),
    "ring_of_protection_3": WondrousItem(
        name="Ring of Protection +3",
        category=MagicItemCategory.RING,
        slot="ring",
        caster_level=5,
        price_gp=18_000,
        weight_lb=0.0,
        bonuses=[MagicBonus(BonusType.DEFLECTION, "ac", 3)],
        aura="moderate abjuration",
        description=(
            "This ring provides a +3 deflection bonus to AC."
        ),
    ),
    "ring_of_protection_4": WondrousItem(
        name="Ring of Protection +4",
        category=MagicItemCategory.RING,
        slot="ring",
        caster_level=5,
        price_gp=32_000,
        weight_lb=0.0,
        bonuses=[MagicBonus(BonusType.DEFLECTION, "ac", 4)],
        aura="moderate abjuration",
        description=(
            "This ring provides a +4 deflection bonus to AC."
        ),
    ),
    "ring_of_protection_5": WondrousItem(
        name="Ring of Protection +5",
        category=MagicItemCategory.RING,
        slot="ring",
        caster_level=5,
        price_gp=50_000,
        weight_lb=0.0,
        bonuses=[MagicBonus(BonusType.DEFLECTION, "ac", 5)],
        aura="strong abjuration",
        description=(
            "This ring provides a +5 deflection bonus to AC."
        ),
    ),
}
