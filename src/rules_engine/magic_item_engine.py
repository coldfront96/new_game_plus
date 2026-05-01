"""
src/rules_engine/magic_item_engine.py
--------------------------------------
Magic item pipeline: random selection, UMD checks, save DCs, identification.
Implements T-049, T-050, T-051, T-058.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Union

from src.rules_engine.consumables import (
    POTION_REGISTRY, SCROLL_REGISTRY, WAND_REGISTRY, ROD_REGISTRY, STAFF_REGISTRY,
    PotionBase, ScrollBase, WandBase, RodBase, StaffBase,
)
from src.rules_engine.magic_items import WONDROUS_ITEM_REGISTRY, RING_REGISTRY


# ---------------------------------------------------------------------------
# T-049 Magic Item Random Type Selector
# ---------------------------------------------------------------------------

class MagicItemCategory(Enum):
    ARMOR = "armor"
    WEAPON = "weapon"
    POTION = "potion"
    RING = "ring"
    ROD = "rod"
    SCROLL = "scroll"
    STAFF = "staff"
    WAND = "wand"
    WONDROUS = "wondrous"


# DMG p.229 d% table
_CATEGORY_TABLE: list[tuple[int, int, MagicItemCategory]] = [
    (1, 4, MagicItemCategory.ARMOR),
    (5, 8, MagicItemCategory.WEAPON),
    (9, 36, MagicItemCategory.POTION),
    (37, 43, MagicItemCategory.RING),
    (44, 46, MagicItemCategory.ROD),
    (47, 70, MagicItemCategory.SCROLL),
    (71, 73, MagicItemCategory.STAFF),
    (74, 84, MagicItemCategory.WAND),
    (85, 100, MagicItemCategory.WONDROUS),
]


def roll_magic_item_type(rng: random.Random | None = None) -> MagicItemCategory:
    """Roll d100 to determine magic item category per DMG p.229."""
    if rng is None:
        rng = random.Random()
    roll = rng.randint(1, 100)
    for low, high, cat in _CATEGORY_TABLE:
        if low <= roll <= high:
            return cat
    return MagicItemCategory.WONDROUS


MagicItemInstance = Union[PotionBase, ScrollBase, WandBase, RodBase, StaffBase]


def roll_magic_item(
    category: MagicItemCategory,
    rng: random.Random | None = None,
) -> dict:
    """Roll a specific magic item from the appropriate registry.

    Returns a dict with 'category', 'name', and the item object.
    """
    if rng is None:
        rng = random.Random()

    registry_map = {
        MagicItemCategory.POTION: POTION_REGISTRY,
        MagicItemCategory.SCROLL: SCROLL_REGISTRY,
        MagicItemCategory.WAND: WAND_REGISTRY,
        MagicItemCategory.ROD: ROD_REGISTRY,
        MagicItemCategory.STAFF: STAFF_REGISTRY,
        MagicItemCategory.RING: RING_REGISTRY,
        MagicItemCategory.WONDROUS: WONDROUS_ITEM_REGISTRY,
    }

    registry = registry_map.get(category)
    if registry:
        name = rng.choice(list(registry.keys()))
        return {"category": category, "name": name, "item": registry[name]}

    # For armor/weapon, return a placeholder
    return {"category": category, "name": f"Magic {category.value.title()}", "item": None}


# ---------------------------------------------------------------------------
# T-050 Magic Item Caster Level Activation Check (UMD)
# ---------------------------------------------------------------------------

class UMDResult:
    def __init__(self, success: bool, roll: int, dc: int):
        self.success = success
        self.roll = roll
        self.dc = dc

    def __repr__(self):
        return f"UMDResult(success={self.success}, roll={self.roll}, dc={self.dc})"


def check_use_magic_device(
    item: MagicItemInstance,
    use_magic_device_modifier: int = 0,
    rng: random.Random | None = None,
) -> UMDResult:
    """Check Use Magic Device activation per DMG rules.

    DCs: Scrolls = 20 + spell_level; Wands = 20; Staffs = 20; Potions = auto-succeed
    """
    if rng is None:
        rng = random.Random()

    if isinstance(item, PotionBase):
        return UMDResult(success=True, roll=20, dc=0)

    if isinstance(item, ScrollBase):
        dc = 20 + item.spell_level
    elif isinstance(item, (WandBase, StaffBase, RodBase)):
        dc = 20
    else:
        dc = 20

    roll = rng.randint(1, 20) + use_magic_device_modifier
    return UMDResult(success=roll >= dc, roll=roll, dc=dc)


# ---------------------------------------------------------------------------
# T-051 Magic Item Saving Throw DC Calculator
# ---------------------------------------------------------------------------

def magic_item_save_dc(item: MagicItemInstance) -> int | None:
    """Calculate saving throw DC for a magic item effect.

    Formula: 10 + (caster_level // 2)
    Applies to Wands and Staffs with save-triggering effects.
    Returns None for items without saves (Potions, Scrolls, Rods).
    """
    if isinstance(item, PotionBase):
        return None
    if isinstance(item, ScrollBase):
        return None  # Scroll save DCs use the spell's own DC
    if isinstance(item, (WandBase, StaffBase)):
        caster_level = getattr(item, "caster_level", 1)
        return 10 + (caster_level // 2)
    if isinstance(item, RodBase):
        return None
    return None


# ---------------------------------------------------------------------------
# T-058 Magic Item Identification Engine
# ---------------------------------------------------------------------------

class IdentificationMethod(Enum):
    SPELLCRAFT = "spellcraft"
    DETECT_MAGIC = "detect_magic"
    IDENTIFY = "identify"
    ANALYZE_DWEOMER = "analyze_dweomer"


@dataclass
class IdentificationResult:
    identified: bool
    aura_school: str | None
    full_name: str | None


def identify_magic_item(
    item_name: str,
    item: MagicItemInstance,
    method: IdentificationMethod,
    spellcraft_modifier: int = 0,
    rng: random.Random | None = None,
) -> IdentificationResult:
    """Identify a magic item using the specified method.

    Spellcraft DC = 15 + caster_level
    Identify spell: automatic after 1 hour
    Detect Magic: reveals aura school only
    Analyze Dweomer: full identification
    """
    if rng is None:
        rng = random.Random()

    if isinstance(item, PotionBase):
        aura_school = "conjuration"
    elif isinstance(item, ScrollBase):
        aura_school = "universal"
    elif isinstance(item, WandBase):
        aura_school = "evocation"
    elif isinstance(item, StaffBase):
        aura_school = "transmutation"
    else:
        aura_school = "universal"

    if method == IdentificationMethod.ANALYZE_DWEOMER:
        return IdentificationResult(identified=True, aura_school=aura_school, full_name=item_name)

    if method == IdentificationMethod.IDENTIFY:
        return IdentificationResult(identified=True, aura_school=aura_school, full_name=item_name)

    if method == IdentificationMethod.DETECT_MAGIC:
        return IdentificationResult(identified=False, aura_school=aura_school, full_name=None)

    if method == IdentificationMethod.SPELLCRAFT:
        caster_level = getattr(item, "caster_level", 1)
        dc = 15 + caster_level
        roll = rng.randint(1, 20) + spellcraft_modifier
        if roll >= dc:
            return IdentificationResult(identified=True, aura_school=aura_school, full_name=item_name)
        else:
            return IdentificationResult(identified=False, aura_school=aura_school, full_name=None)


# ---------------------------------------------------------------------------
# PH7-005 · Expanded wondrous item merge
# ---------------------------------------------------------------------------

def merge_expanded_wondrous(expanded: dict) -> None:
    """Merge supplemental wondrous items from *expanded* into the live registry.

    Only processes entries keyed under ``"magic_item_compendium"``.
    Each item dict must contain at minimum a ``"name"`` field; all other
    fields fall back to safe defaults.

    Deduplicates by name — last writer wins when names collide, preserving
    the expanded book's version.  Safe to call multiple times; repeated
    calls do not accumulate duplicates.

    Args:
        expanded: Dict returned by :func:`~src.rules_engine.srd_loader.load_expanded_rules`.
    """
    from src.rules_engine.magic_items import WondrousItem, MagicBonus

    mic_entries = expanded.get("magic_item_compendium")
    if not mic_entries:
        return

    for item_dict in mic_entries:
        if not isinstance(item_dict, dict) or not item_dict.get("name"):
            continue
        name = str(item_dict["name"])
        slug = name.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("+", "plus")
        new_item = WondrousItem(
            name=name,
            category=MagicItemCategory.WONDROUS,
            slot=str(item_dict.get("slot", "none")),
            caster_level=int(item_dict.get("caster_level", 1)),
            price_gp=int(item_dict.get("price_gp", 0)),
            weight_lb=float(item_dict.get("weight_lb", 0.0)),
            bonuses=[],
            aura=str(item_dict.get("aura_school", "moderate transmutation")),
            description=str(item_dict.get("description", "")),
        )
        WONDROUS_ITEM_REGISTRY[slug] = new_item

    # Deduplicate by name — keep latest entry per name key.
    seen_names: dict[str, str] = {}
    for slug, wi in list(WONDROUS_ITEM_REGISTRY.items()):
        if wi.name in seen_names:
            del WONDROUS_ITEM_REGISTRY[seen_names[wi.name]]
        seen_names[wi.name] = slug

    return IdentificationResult(identified=False, aura_school=None, full_name=None)


# ---------------------------------------------------------------------------
# PH7-005 — Expanded wondrous item merge
# ---------------------------------------------------------------------------

def _slug_from_name(name: str) -> str:
    """Convert an item name to a registry-style slug key."""
    import re as _re
    return _re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def merge_expanded_wondrous(expanded: dict) -> None:
    """Merge Magic Item Compendium wondrous items into :data:`WONDROUS_ITEM_REGISTRY`.

    Reads every item dict stored at ``expanded["magic_item_compendium"]`` and
    constructs a :class:`~src.rules_engine.magic_items.WondrousItem` for each.
    The merged items are added to (or overwrite) ``WONDROUS_ITEM_REGISTRY``
    using a slug derived from the item name.  A final deduplication pass by
    name ensures that repeated calls do not accumulate duplicates.

    Args:
        expanded: Dict returned by :func:`~src.rules_engine.srd_loader.load_expanded_rules`.
    """
    from src.rules_engine.magic_items import (
        MagicItemCategory,
        MagicBonus,
        BonusType,
        WondrousItem,
        WONDROUS_ITEM_REGISTRY,
    )

    book_entries = expanded.get("magic_item_compendium")
    if not book_entries:
        return

    for item_dict in book_entries:
        if not isinstance(item_dict, dict):
            continue
        name = item_dict.get("name")
        if not name:
            continue

        # Build a minimal WondrousItem from the available fields.
        item = WondrousItem(
            name=name,
            category=MagicItemCategory.WONDROUS,
            slot=item_dict.get("slot", "none"),
            caster_level=int(item_dict.get("caster_level", 1)),
            price_gp=int(item_dict.get("price_gp", 0)),
            weight_lb=float(item_dict.get("weight", item_dict.get("weight_lb", 0.0))),
            bonuses=[],
            aura=item_dict.get("aura_school", item_dict.get("aura", "")),
            description=item_dict.get("description", ""),
        )
        slug = _slug_from_name(name)
        WONDROUS_ITEM_REGISTRY[slug] = item

    # Deduplicate by name (last writer wins) — collect unique items by name.
    seen_names: Dict[str, str] = {}
    for key, entry in list(WONDROUS_ITEM_REGISTRY.items()):
        seen_names[entry.name] = key

    # Remove any earlier slugs that were superseded by a later one with the same name.
    surviving_keys = set(seen_names.values())
    for key in list(WONDROUS_ITEM_REGISTRY.keys()):
        if key not in surviving_keys:
            del WONDROUS_ITEM_REGISTRY[key]

