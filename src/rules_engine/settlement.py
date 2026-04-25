"""
src/rules_engine/settlement.py
-------------------------------
D&D 3.5e Settlement Demographics & Economics subsystem.

Implements:
    E-012 — Community Size Enum & Base Schema
    E-013 — GP Limit & NPC Demographics Row Schema
    E-028 — Community GP Limit Lookup
    E-029 — Highest-Level NPC Class Formula
    E-042 — Community Type Registry
    E-043 — Power Center Registry
    E-054 — Settlement Generator
    E-060 — Settlement Magic Item Availability Roster
    E-066 — Settlement-Aware Shopping Engine

DMG reference: Dungeon Master's Guide, Chapter 5 (Settlements).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

from src.rules_engine.npc_classes import (
    NPCClassName,
    NPCClassBase,
    NPC_CLASS_DISTRIBUTION_PCT,
    generate_npc,
    NPCStats,
)
from src.rules_engine.magic_items import WONDROUS_ITEM_REGISTRY, RING_REGISTRY

# Re-export for callers that import from this module
__all__ = [
    "CommunitySize",
    "CommunityBase",
    "DemographicsRow",
    "NPC_CLASS_DISTRIBUTION_PCT",
    "COMMUNITY_REGISTRY",
    "DEMOGRAPHICS_TABLE",
    "PowerCenterType",
    "AlignmentLean",
    "AuthorityFigure",
    "PowerCenterEntry",
    "POWER_CENTER_REGISTRY",
    "PowerCenter",
    "Settlement",
    "AvailableInventory",
    "ShopResult",
    "gp_limit_for",
    "community_total_assets",
    "highest_level_npc_class",
    "population_class_roster",
    "roll_power_center_type",
    "generate_settlement",
    "available_magic_items",
    "shop",
]


# ---------------------------------------------------------------------------
# E-012 — Community Size Enum & Base Schema
# ---------------------------------------------------------------------------

class CommunitySize(Enum):
    Thorp = auto()
    Hamlet = auto()
    Village = auto()
    SmallTown = auto()
    LargeTown = auto()
    SmallCity = auto()
    LargeCity = auto()
    Metropolis = auto()


@dataclass(slots=True)
class CommunityBase:
    size: CommunitySize
    population_range: tuple[int, int]
    gp_limit: int
    assets_modifier_pct: float      # fraction: total assets = gp_limit/2 * population/10
    power_center_count_range: tuple[int, int]
    mixed_alignment: bool


# ---------------------------------------------------------------------------
# E-013 — GP Limit & NPC Demographics Row Schema
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class DemographicsRow:
    community_size: CommunitySize
    gp_limit: int
    total_assets_factor: float          # = gp_limit / 2 / 10 (assets per person)
    highest_pc_class_level_max: int     # max level for PC-class NPCs
    highest_npc_class_level_max: int    # max level for NPC-class NPCs


# DMG p.139 PC/NPC level caps and GP limits by settlement size
DEMOGRAPHICS_TABLE: dict[CommunitySize, DemographicsRow] = {
    CommunitySize.Thorp: DemographicsRow(
        community_size=CommunitySize.Thorp,
        gp_limit=40,
        total_assets_factor=40 / 2 / 10,
        highest_pc_class_level_max=2,
        highest_npc_class_level_max=1,
    ),
    CommunitySize.Hamlet: DemographicsRow(
        community_size=CommunitySize.Hamlet,
        gp_limit=100,
        total_assets_factor=100 / 2 / 10,
        highest_pc_class_level_max=3,
        highest_npc_class_level_max=2,
    ),
    CommunitySize.Village: DemographicsRow(
        community_size=CommunitySize.Village,
        gp_limit=200,
        total_assets_factor=200 / 2 / 10,
        highest_pc_class_level_max=5,
        highest_npc_class_level_max=3,
    ),
    CommunitySize.SmallTown: DemographicsRow(
        community_size=CommunitySize.SmallTown,
        gp_limit=800,
        total_assets_factor=800 / 2 / 10,
        highest_pc_class_level_max=7,
        highest_npc_class_level_max=5,
    ),
    CommunitySize.LargeTown: DemographicsRow(
        community_size=CommunitySize.LargeTown,
        gp_limit=3000,
        total_assets_factor=3000 / 2 / 10,
        highest_pc_class_level_max=9,
        highest_npc_class_level_max=7,
    ),
    CommunitySize.SmallCity: DemographicsRow(
        community_size=CommunitySize.SmallCity,
        gp_limit=15000,
        total_assets_factor=15000 / 2 / 10,
        highest_pc_class_level_max=11,
        highest_npc_class_level_max=9,
    ),
    CommunitySize.LargeCity: DemographicsRow(
        community_size=CommunitySize.LargeCity,
        gp_limit=40000,
        total_assets_factor=40000 / 2 / 10,
        highest_pc_class_level_max=14,
        highest_npc_class_level_max=12,
    ),
    CommunitySize.Metropolis: DemographicsRow(
        community_size=CommunitySize.Metropolis,
        gp_limit=100000,
        total_assets_factor=100000 / 2 / 10,
        highest_pc_class_level_max=20,
        highest_npc_class_level_max=17,
    ),
}


# ---------------------------------------------------------------------------
# E-028 — Community GP Limit Lookup
# ---------------------------------------------------------------------------

_GP_LIMIT: dict[CommunitySize, int] = {
    CommunitySize.Thorp:      40,
    CommunitySize.Hamlet:     100,
    CommunitySize.Village:    200,
    CommunitySize.SmallTown:  800,
    CommunitySize.LargeTown:  3_000,
    CommunitySize.SmallCity:  15_000,
    CommunitySize.LargeCity:  40_000,
    CommunitySize.Metropolis: 100_000,
}


def gp_limit_for(size: CommunitySize) -> int:
    """DMG Table 5-2: return the GP limit for a community size."""
    return _GP_LIMIT[size]


def community_total_assets(size: CommunitySize, population: int) -> int:
    """DMG p.137: total_assets = gp_limit/2 * population/10."""
    return int(gp_limit_for(size) / 2 * population / 10)


# ---------------------------------------------------------------------------
# E-029 — Highest-Level NPC Class Formula
# ---------------------------------------------------------------------------

_SIZE_MODIFIER: dict[CommunitySize, int] = {
    CommunitySize.Thorp:      0,
    CommunitySize.Hamlet:     0,
    CommunitySize.Village:    1,
    CommunitySize.SmallTown:  2,
    CommunitySize.LargeTown:  3,
    CommunitySize.SmallCity:  4,
    CommunitySize.LargeCity:  5,
    CommunitySize.Metropolis: 6,
}


def highest_level_npc_class(size: CommunitySize, klass: NPCClassName, rng=None) -> int:
    """DMG p.139 algorithm.

    Base roll: d4 + size_modifier.
    Cap result at highest_npc_class_level_max for size.
    If rng is None, use deterministic (size_modifier + 2) capped.
    """
    cap = DEMOGRAPHICS_TABLE[size].highest_npc_class_level_max
    mod = _SIZE_MODIFIER[size]
    if rng is None:
        result = mod + 2
    else:
        result = rng.randint(1, 4) + mod
    return max(1, min(result, cap))


def population_class_roster(
    size: CommunitySize,
    population: int,
    rng=None,
) -> dict[NPCClassName, list[int]]:
    """Returns level distributions per NPC class.

    Uses NPC_CLASS_DISTRIBUTION_PCT to split population.
    For each class: highest level = highest_level_npc_class();
    lower levels have twice as many NPCs as the next level up
    (exponential distribution).
    Returns {NPCClassName: [list of levels for each individual NPC]}.
    """
    roster: dict[NPCClassName, list[int]] = {}

    for klass, pct in NPC_CLASS_DISTRIBUTION_PCT.items():
        count = max(0, int(population * pct))
        if count == 0:
            roster[klass] = []
            continue

        top_level = highest_level_npc_class(size, klass, rng)
        levels: list[int] = []
        remaining = count
        count_at_level = 1
        current_level = top_level

        while current_level > 1 and remaining > 0:
            to_place = min(count_at_level, remaining)
            levels.extend([current_level] * to_place)
            remaining -= to_place
            count_at_level *= 2
            current_level -= 1

        # All remaining NPCs accumulate at level 1
        if remaining > 0:
            levels.extend([1] * remaining)

        roster[klass] = levels

    return roster


# ---------------------------------------------------------------------------
# E-042 — Community Type Registry
# ---------------------------------------------------------------------------

COMMUNITY_REGISTRY: dict[CommunitySize, CommunityBase] = {
    CommunitySize.Thorp: CommunityBase(
        size=CommunitySize.Thorp,
        population_range=(20, 80),
        gp_limit=40,
        assets_modifier_pct=0.5,
        power_center_count_range=(1, 1),
        mixed_alignment=False,
    ),
    CommunitySize.Hamlet: CommunityBase(
        size=CommunitySize.Hamlet,
        population_range=(81, 400),
        gp_limit=100,
        assets_modifier_pct=0.5,
        power_center_count_range=(1, 1),
        mixed_alignment=False,
    ),
    CommunitySize.Village: CommunityBase(
        size=CommunitySize.Village,
        population_range=(401, 900),
        gp_limit=200,
        assets_modifier_pct=0.5,
        power_center_count_range=(1, 1),
        mixed_alignment=False,
    ),
    CommunitySize.SmallTown: CommunityBase(
        size=CommunitySize.SmallTown,
        population_range=(901, 2000),
        gp_limit=800,
        assets_modifier_pct=0.5,
        power_center_count_range=(1, 2),
        mixed_alignment=True,
    ),
    CommunitySize.LargeTown: CommunityBase(
        size=CommunitySize.LargeTown,
        population_range=(2001, 5000),
        gp_limit=3_000,
        assets_modifier_pct=0.5,
        power_center_count_range=(1, 2),
        mixed_alignment=True,
    ),
    CommunitySize.SmallCity: CommunityBase(
        size=CommunitySize.SmallCity,
        population_range=(5001, 12000),
        gp_limit=15_000,
        assets_modifier_pct=0.5,
        power_center_count_range=(2, 3),
        mixed_alignment=True,
    ),
    CommunitySize.LargeCity: CommunityBase(
        size=CommunitySize.LargeCity,
        population_range=(12001, 25000),
        gp_limit=40_000,
        assets_modifier_pct=0.5,
        power_center_count_range=(3, 5),
        mixed_alignment=True,
    ),
    CommunitySize.Metropolis: CommunityBase(
        size=CommunitySize.Metropolis,
        population_range=(25001, 100000),
        gp_limit=100_000,
        assets_modifier_pct=0.5,
        power_center_count_range=(4, 6),
        mixed_alignment=True,
    ),
}


# ---------------------------------------------------------------------------
# E-043 — Power Center Registry
# ---------------------------------------------------------------------------

class PowerCenterType(Enum):
    Conventional = auto()   # mayor, council
    Nonstandard  = auto()   # guild, thieves, merchants
    Magical      = auto()   # wizard, sorcerer, cleric


class AlignmentLean(Enum):
    """General alignment lean of a power center or authority figure."""
    Lawful  = auto()
    Neutral = auto()
    Chaotic = auto()
    Good    = auto()
    Evil    = auto()
    Any     = auto()


@dataclass(slots=True)
class AuthorityFigure:
    title: str
    npc_class: NPCClassName
    level: int
    alignment_lean: AlignmentLean


@dataclass(slots=True)
class PowerCenterEntry:
    power_type: PowerCenterType
    alignment_lean: AlignmentLean
    typical_authority: AuthorityFigure


# d100 weighted table: 01-60=Conventional, 61-90=Nonstandard, 91-100=Magical
POWER_CENTER_REGISTRY: dict[str, PowerCenterEntry] = {
    "Conventional": PowerCenterEntry(
        power_type=PowerCenterType.Conventional,
        alignment_lean=AlignmentLean.Lawful,
        typical_authority=AuthorityFigure(
            title="Mayor",
            npc_class=NPCClassName.Aristocrat,
            level=3,
            alignment_lean=AlignmentLean.Lawful,
        ),
    ),
    "Nonstandard": PowerCenterEntry(
        power_type=PowerCenterType.Nonstandard,
        alignment_lean=AlignmentLean.Neutral,
        typical_authority=AuthorityFigure(
            title="Guildmaster",
            npc_class=NPCClassName.Expert,
            level=5,
            alignment_lean=AlignmentLean.Neutral,
        ),
    ),
    "Magical": PowerCenterEntry(
        power_type=PowerCenterType.Magical,
        alignment_lean=AlignmentLean.Any,
        typical_authority=AuthorityFigure(
            title="Archmage",
            npc_class=NPCClassName.Adept,
            level=10,
            alignment_lean=AlignmentLean.Any,
        ),
    ),
}

_POWER_CENTER_THRESHOLDS = [
    (60,  "Conventional"),
    (90,  "Nonstandard"),
    (100, "Magical"),
]


def roll_power_center_type(rng=None) -> str:
    """Rolls d100: 1-60=Conventional, 61-90=Nonstandard, 91-100=Magical."""
    roll = (rng or random).randint(1, 100)
    for threshold, name in _POWER_CENTER_THRESHOLDS:
        if roll <= threshold:
            return name
    return "Magical"


# ---------------------------------------------------------------------------
# E-054 — Settlement Generator
# ---------------------------------------------------------------------------

_PC_CLASS_NAMES = [
    "Fighter", "Wizard", "Cleric", "Rogue", "Ranger",
    "Paladin", "Druid", "Bard", "Barbarian", "Sorcerer",
]

# How many major PC classes appear at each size tier
_PC_CLASSES_BY_SIZE: dict[CommunitySize, list[str]] = {
    CommunitySize.Thorp:      ["Fighter"],
    CommunitySize.Hamlet:     ["Fighter", "Cleric"],
    CommunitySize.Village:    ["Fighter", "Cleric", "Rogue"],
    CommunitySize.SmallTown:  ["Fighter", "Wizard", "Cleric", "Rogue"],
    CommunitySize.LargeTown:  ["Fighter", "Wizard", "Cleric", "Rogue", "Ranger"],
    CommunitySize.SmallCity:  ["Fighter", "Wizard", "Cleric", "Rogue", "Ranger", "Druid"],
    CommunitySize.LargeCity:  _PC_CLASS_NAMES[:8],
    CommunitySize.Metropolis: _PC_CLASS_NAMES,
}


@dataclass
class PowerCenter:
    entry: PowerCenterEntry
    authority: AuthorityFigure


@dataclass
class Settlement:
    size: CommunitySize
    population: int
    gp_limit: int
    total_assets: int
    power_centers: list[PowerCenter]
    npc_roster: dict[NPCClassName, list[int]]   # level distributions
    pc_class_roster: dict[str, list[int]]        # PC class level distributions
    ruler_authority: AuthorityFigure


def _generate_pc_roster(
    size: CommunitySize,
    rng=None,
) -> dict[str, list[int]]:
    """Build a simple PC class roster: 1-2 individuals per class at a
    level appropriate for the community size."""
    pc_level_cap = DEMOGRAPHICS_TABLE[size].highest_pc_class_level_max
    classes = _PC_CLASSES_BY_SIZE[size]
    roster: dict[str, list[int]] = {}
    _rng = rng or random
    for cls_name in classes:
        count = _rng.randint(1, 2)
        levels = [_rng.randint(1, pc_level_cap) for _ in range(count)]
        roster[cls_name] = sorted(levels, reverse=True)
    return roster


def generate_settlement(size: CommunitySize, rng=None) -> Settlement:
    """Generates a complete settlement.

    - population: random in CommunityBase.population_range (midpoint if rng=None).
    - power_centers: count from power_center_count_range, each rolled from POWER_CENTER_REGISTRY.
    - npc_roster: population_class_roster(size, population, rng).
    - pc_class_roster: simple table with 1-2 PC class individuals per major class.
    - ruler_authority: from the first power center's typical_authority.
    """
    base = COMMUNITY_REGISTRY[size]
    _rng = rng or random

    # Population
    lo, hi = base.population_range
    if rng is None:
        population = (lo + hi) // 2
    else:
        population = rng.randint(lo, hi)

    gp_lim = gp_limit_for(size)
    assets = community_total_assets(size, population)

    # Power centers
    pc_lo, pc_hi = base.power_center_count_range
    if rng is None:
        center_count = pc_lo
    else:
        center_count = rng.randint(pc_lo, pc_hi)

    power_centers: list[PowerCenter] = []
    for _ in range(center_count):
        key = roll_power_center_type(rng)
        entry = POWER_CENTER_REGISTRY[key]
        # Clone the authority figure (same level/class as template)
        authority = AuthorityFigure(
            title=entry.typical_authority.title,
            npc_class=entry.typical_authority.npc_class,
            level=entry.typical_authority.level,
            alignment_lean=entry.typical_authority.alignment_lean,
        )
        power_centers.append(PowerCenter(entry=entry, authority=authority))

    # Rosters
    npc_roster = population_class_roster(size, population, rng)
    pc_roster = _generate_pc_roster(size, rng)

    ruler = power_centers[0].authority if power_centers else AuthorityFigure(
        title="Elder",
        npc_class=NPCClassName.Commoner,
        level=1,
        alignment_lean=AlignmentLean.Neutral,
    )

    return Settlement(
        size=size,
        population=population,
        gp_limit=gp_lim,
        total_assets=assets,
        power_centers=power_centers,
        npc_roster=npc_roster,
        pc_class_roster=pc_roster,
        ruler_authority=ruler,
    )


# ---------------------------------------------------------------------------
# E-060 — Settlement Magic Item Availability Roster
# ---------------------------------------------------------------------------

# Price thresholds for minor/medium/major tiers (DMG p.135 Table 7-1)
_MINOR_MAX_GP  = 3_400
_MEDIUM_MAX_GP = 40_000
# Major = above _MEDIUM_MAX_GP

# Combine all magic item pools
_ALL_MAGIC_ITEMS: list[tuple[str, int]] = [
    (item.name, item.price_gp)
    for item in {**WONDROUS_ITEM_REGISTRY, **RING_REGISTRY}.values()
]


def _item_tier(price_gp: int) -> str:
    if price_gp <= _MINOR_MAX_GP:
        return "minor"
    if price_gp <= _MEDIUM_MAX_GP:
        return "medium"
    return "major"


@dataclass
class AvailableInventory:
    minor_items: list[str]
    medium_items: list[str]
    major_items: list[str]
    settlement_gp_limit: int


def available_magic_items(settlement: Settlement, rng=None) -> AvailableInventory:
    """DMG p.137 rules for magic item availability.

    Minor items: 75% chance if item price <= gp_limit.
    Medium items: (gp_limit / item_price * 100)% chance, capped at 75%.
    Major items: available only if gp_limit >= item_price (no chance roll).
    """
    _rng = rng or random
    gp_lim = settlement.gp_limit
    minor: list[str] = []
    medium: list[str] = []
    major: list[str] = []

    for name, price in _ALL_MAGIC_ITEMS:
        if price > gp_lim:
            continue
        tier = _item_tier(price)
        if tier == "minor":
            if _rng.random() < 0.75:
                minor.append(name)
        elif tier == "medium":
            chance = min((gp_lim / price), 0.75)
            if _rng.random() < chance:
                medium.append(name)
        else:  # major
            major.append(name)

    return AvailableInventory(
        minor_items=minor,
        medium_items=medium,
        major_items=major,
        settlement_gp_limit=gp_lim,
    )


# ---------------------------------------------------------------------------
# E-066 — Settlement-Aware Shopping Engine
# ---------------------------------------------------------------------------

@dataclass
class ShopResult:
    success: bool
    item_name: str
    price_gp: int
    reason: str
    assets_remaining: int


def shop(
    settlement: Settlement,
    item_name: str,
    item_price_gp: int,
    is_magic: bool = False,
    rng=None,
) -> ShopResult:
    """Settlement shopping pipeline.

    1. Check item_price_gp <= settlement.gp_limit.
    2. For mundane items: always available if price <= gp_limit.
    3. For magic items: check availability via available_magic_items().
    4. Deduct from settlement.total_assets on success.
    """
    if item_price_gp > settlement.gp_limit:
        return ShopResult(
            success=False,
            item_name=item_name,
            price_gp=item_price_gp,
            reason=(
                f"Item price {item_price_gp} gp exceeds settlement GP limit "
                f"{settlement.gp_limit} gp."
            ),
            assets_remaining=settlement.total_assets,
        )

    if not is_magic:
        if settlement.total_assets < item_price_gp:
            return ShopResult(
                success=False,
                item_name=item_name,
                price_gp=item_price_gp,
                reason="Settlement lacks sufficient assets.",
                assets_remaining=settlement.total_assets,
            )
        settlement.total_assets -= item_price_gp
        return ShopResult(
            success=True,
            item_name=item_name,
            price_gp=item_price_gp,
            reason="Item available (mundane).",
            assets_remaining=settlement.total_assets,
        )

    # Magic item path
    inventory = available_magic_items(settlement, rng)
    all_available = (
        inventory.minor_items + inventory.medium_items + inventory.major_items
    )

    if item_name not in all_available:
        return ShopResult(
            success=False,
            item_name=item_name,
            price_gp=item_price_gp,
            reason="Magic item not currently available in this settlement.",
            assets_remaining=settlement.total_assets,
        )

    if settlement.total_assets < item_price_gp:
        return ShopResult(
            success=False,
            item_name=item_name,
            price_gp=item_price_gp,
            reason="Settlement lacks sufficient assets.",
            assets_remaining=settlement.total_assets,
        )

    settlement.total_assets -= item_price_gp
    return ShopResult(
        success=True,
        item_name=item_name,
        price_gp=item_price_gp,
        reason="Magic item available and purchased.",
        assets_remaining=settlement.total_assets,
    )
