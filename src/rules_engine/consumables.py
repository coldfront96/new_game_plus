"""
src/rules_engine/consumables.py
---------------------------------
D&D 3.5e DMG Consumable Magic Items — Potions, Scrolls, Wands, Rods, Staves.

Implements price formulae from DMG p.285-286 and registries of SRD items.

Price formulae:
  * :func:`potion_market_price`  — DMG p.285: spell_level × caster_level × 50 gp
  * :func:`scroll_market_price`  — DMG p.285: spell_level × caster_level × 25 gp
  * :func:`wand_market_price`    — DMG p.285: spell_level × caster_level × 750 gp
  * :func:`rod_market_price`     — returns stored market_price_gp from :class:`RodBase`
  * :func:`staff_market_price`   — primary spell at 900 gp/spell-level/caster-level + secondaries

Registries:
  * :data:`POTION_REGISTRY`  — 31 SRD potions
  * :data:`SCROLL_REGISTRY`  — 41 SRD scrolls (arcane + divine)
  * :data:`WAND_REGISTRY`    — 25 SRD wands
  * :data:`ROD_REGISTRY`     — 20 SRD rods
  * :data:`STAFF_REGISTRY`   — 20 SRD staves

Usage::

    from src.rules_engine.consumables import (
        POTION_REGISTRY, SCROLL_REGISTRY, WAND_REGISTRY,
        ROD_REGISTRY, STAFF_REGISTRY,
        potion_market_price, scroll_market_price, wand_market_price,
    )

    print(potion_market_price(1, 1))   # 50
    print(scroll_market_price(3, 5))   # 375
    print(wand_market_price(1, 1))     # 750

    clw = POTION_REGISTRY["Cure Light Wounds"]
    print(clw.market_price_gp)         # 50
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# T-005: Base dataclasses
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class PotionBase:
    name: str
    spell_name: str
    caster_level: int
    spell_level: int
    market_price_gp: int


@dataclass(slots=True)
class ScrollBase:
    name: str
    spell_name: str
    caster_level: int
    spell_level: int
    arcane: bool      # True=arcane, False=divine
    market_price_gp: int


@dataclass(slots=True)
class WandBase:
    name: str
    spell_name: str
    caster_level: int
    spell_level: int
    charges_max: int   # always 50
    market_price_gp: int


@dataclass(slots=True)
class RodBase:
    name: str
    charges_max: int    # 0 if no charges
    market_price_gp: int


@dataclass(slots=True)
class StaffBase:
    name: str
    charges_max: int    # always 50
    market_price_gp: int


# ---------------------------------------------------------------------------
# T-018: Potion price formula
# ---------------------------------------------------------------------------

def potion_market_price(spell_level: int, caster_level: int) -> int:
    """DMG p.285: spell_level × caster_level × 50 gp. Level 0 = × 25."""
    if spell_level == 0:
        return caster_level * 25
    return spell_level * caster_level * 50


# ---------------------------------------------------------------------------
# T-019: Scroll price formula
# ---------------------------------------------------------------------------

def scroll_market_price(spell_level: int, caster_level: int, arcane: bool = True) -> int:
    """DMG p.285: spell_level × caster_level × 25 gp. Level 0 = 12.5, rounded up."""
    if spell_level == 0:
        return math.ceil(caster_level * 12.5)
    return spell_level * caster_level * 25


# ---------------------------------------------------------------------------
# T-020: Wand price formula
# ---------------------------------------------------------------------------

def wand_market_price(spell_level: int, caster_level: int) -> int:
    """DMG p.285: spell_level × caster_level × 750 gp. Level 0 wand = minimum 375."""
    if spell_level == 0:
        return max(375, caster_level * 375)
    return spell_level * caster_level * 750


# ---------------------------------------------------------------------------
# T-021: Rod/Staff price formulas
# ---------------------------------------------------------------------------

def rod_market_price(rod: RodBase) -> int:
    """Returns the rod's stored market_price_gp."""
    return rod.market_price_gp


def staff_market_price(
    primary_spell_level: int,
    primary_caster_level: int,
    secondary_costs: list[int],
) -> int:
    """DMG p.285-286 staff pricing formula.

    Primary spell uses 2 charges per activation:
        base = primary_spell_level × primary_caster_level × 900 gp

    Secondary spells (1 charge each) pass their precomputed costs in
    ``secondary_costs``.  The total market price is the sum of all components.
    """
    base = primary_spell_level * primary_caster_level * 900
    return base + sum(secondary_costs)


# ---------------------------------------------------------------------------
# T-027: POTION_REGISTRY — 31 SRD potions
# ---------------------------------------------------------------------------

def _make_potion(name: str, spell_name: str, spell_level: int, caster_level: int) -> PotionBase:
    return PotionBase(
        name=name,
        spell_name=spell_name,
        caster_level=caster_level,
        spell_level=spell_level,
        market_price_gp=potion_market_price(spell_level, caster_level),
    )


POTION_REGISTRY: dict[str, PotionBase] = {p.name: p for p in [
    _make_potion("Cure Light Wounds",           "Cure Light Wounds",           1, 1),
    _make_potion("Cure Moderate Wounds",        "Cure Moderate Wounds",        2, 3),
    _make_potion("Cure Serious Wounds",         "Cure Serious Wounds",         3, 5),
    _make_potion("Bull's Strength",             "Bull's Strength",             2, 3),
    _make_potion("Cat's Grace",                 "Cat's Grace",                 2, 3),
    _make_potion("Bear's Endurance",            "Bear's Endurance",            2, 3),
    _make_potion("Eagle's Splendor",            "Eagle's Splendor",            2, 3),
    _make_potion("Fox's Cunning",               "Fox's Cunning",               2, 3),
    _make_potion("Owl's Wisdom",                "Owl's Wisdom",                2, 3),
    _make_potion("Barkskin",                    "Barkskin",                    2, 3),
    _make_potion("Darkvision",                  "Darkvision",                  2, 3),
    _make_potion("Hide from Undead",            "Hide from Undead",            1, 1),
    _make_potion("Jump",                        "Jump",                        1, 1),
    _make_potion("Neutralize Poison",           "Neutralize Poison",           4, 7),
    _make_potion("Remove Blindness/Deafness",   "Remove Blindness/Deafness",   3, 5),
    _make_potion("Remove Curse",                "Remove Curse",                3, 5),
    _make_potion("Remove Disease",              "Remove Disease",              3, 5),
    _make_potion("Remove Fear",                 "Remove Fear",                 1, 1),
    _make_potion("Resist Energy",               "Resist Energy",               2, 3),
    _make_potion("Spider Climb",                "Spider Climb",                2, 3),
    _make_potion("Water Breathing",             "Water Breathing",             3, 5),
    _make_potion("Blur",                        "Blur",                        2, 3),
    _make_potion("Endure Elements",             "Endure Elements",             1, 1),
    _make_potion("Gaseous Form",                "Gaseous Form",                3, 5),
    _make_potion("Invisibility",                "Invisibility",                2, 3),
    _make_potion("Levitate",                    "Levitate",                    2, 3),
    _make_potion("Mage Armor",                  "Mage Armor",                  1, 1),
    _make_potion("Magic Fang",                  "Magic Fang",                  1, 1),
    _make_potion("Nondetection",                "Nondetection",                3, 5),
    _make_potion("Protection from Arrows",      "Protection from Arrows",      2, 3),
    _make_potion("Shield of Faith",             "Shield of Faith",             1, 1),
]}


# ---------------------------------------------------------------------------
# T-028: SCROLL_REGISTRY — 41 SRD scrolls (arcane + divine)
# ---------------------------------------------------------------------------

def _make_scroll(
    spell_name: str,
    spell_level: int,
    caster_level: int,
    arcane: bool,
) -> ScrollBase:
    label = "Arcane" if arcane else "Divine"
    name = f"Scroll of {spell_name} ({label})"
    return ScrollBase(
        name=name,
        spell_name=spell_name,
        caster_level=caster_level,
        spell_level=spell_level,
        arcane=arcane,
        market_price_gp=scroll_market_price(spell_level, caster_level, arcane),
    )


SCROLL_REGISTRY: dict[str, ScrollBase] = {s.name: s for s in [
    # Arcane scrolls
    _make_scroll("Detect Magic",        0, 1,  True),
    _make_scroll("Read Magic",          0, 1,  True),
    _make_scroll("Mage Armor",          1, 1,  True),
    _make_scroll("Magic Missile",       1, 1,  True),
    _make_scroll("Sleep",               1, 1,  True),
    _make_scroll("Charm Person",        1, 1,  True),
    _make_scroll("Shield",              1, 1,  True),
    _make_scroll("Identify",            1, 1,  True),
    _make_scroll("Feather Fall",        1, 1,  True),
    _make_scroll("Invisibility",        2, 3,  True),
    _make_scroll("Web",                 2, 3,  True),
    _make_scroll("Mirror Image",        2, 3,  True),
    _make_scroll("Scorching Ray",       2, 3,  True),
    _make_scroll("Levitate",            2, 3,  True),
    _make_scroll("Knock",               2, 3,  True),
    _make_scroll("Blur",                2, 3,  True),
    _make_scroll("Fireball",            3, 5,  True),
    _make_scroll("Lightning Bolt",      3, 5,  True),
    _make_scroll("Fly",                 3, 5,  True),
    _make_scroll("Haste",               3, 5,  True),
    _make_scroll("Dispel Magic",        3, 5,  True),
    _make_scroll("Stoneskin",           4, 7,  True),
    _make_scroll("Ice Storm",           4, 7,  True),
    _make_scroll("Wall of Fire",        4, 7,  True),
    _make_scroll("Dimension Door",      4, 7,  True),
    # Divine scrolls
    _make_scroll("Cure Light Wounds",       1, 1,  False),
    _make_scroll("Cure Moderate Wounds",    2, 3,  False),
    _make_scroll("Cure Serious Wounds",     3, 5,  False),
    _make_scroll("Cure Critical Wounds",    4, 7,  False),
    _make_scroll("Heal",                    6, 11, False),
    _make_scroll("Remove Curse",            3, 5,  False),
    _make_scroll("Remove Disease",          3, 5,  False),
    _make_scroll("Remove Blindness/Deafness", 3, 5, False),
    _make_scroll("Neutralize Poison",       4, 7,  False),
    _make_scroll("Raise Dead",              5, 9,  False),
    _make_scroll("Restoration",             4, 7,  False),
    _make_scroll("Bless",                   1, 1,  False),
    _make_scroll("Prayer",                  3, 5,  False),
    _make_scroll("Holy Smite",              4, 7,  False),
    _make_scroll("Flame Strike",            5, 9,  False),
    _make_scroll("Blade Barrier",           6, 11, False),
]}


# ---------------------------------------------------------------------------
# T-029: WAND_REGISTRY — 25 SRD wands
# ---------------------------------------------------------------------------

def _make_wand(name: str, spell_name: str, spell_level: int, caster_level: int) -> WandBase:
    return WandBase(
        name=name,
        spell_name=spell_name,
        caster_level=caster_level,
        spell_level=spell_level,
        charges_max=50,
        market_price_gp=wand_market_price(spell_level, caster_level),
    )


WAND_REGISTRY: dict[str, WandBase] = {w.name: w for w in [
    _make_wand("Wand of Cure Light Wounds",     "Cure Light Wounds",     1, 1),
    _make_wand("Wand of Fireball",              "Fireball",              3, 5),
    _make_wand("Wand of Lightning Bolt",        "Lightning Bolt",        3, 5),
    _make_wand("Wand of Magic Missile",         "Magic Missile",         1, 1),
    _make_wand("Wand of Charm Person",          "Charm Person",          1, 1),
    _make_wand("Wand of Hold Person",           "Hold Person",           2, 3),
    _make_wand("Wand of Invisibility",          "Invisibility",          2, 3),
    _make_wand("Wand of Knock",                 "Knock",                 2, 3),
    _make_wand("Wand of Web",                   "Web",                   2, 3),
    _make_wand("Wand of Dispel Magic",          "Dispel Magic",          3, 5),
    _make_wand("Wand of Bear's Endurance",      "Bear's Endurance",      2, 3),
    _make_wand("Wand of Bull's Strength",       "Bull's Strength",       2, 3),
    _make_wand("Wand of Cat's Grace",           "Cat's Grace",           2, 3),
    _make_wand("Wand of Eagle's Splendor",      "Eagle's Splendor",      2, 3),
    _make_wand("Wand of Enervation",            "Enervation",            4, 7),
    _make_wand("Wand of Fear",                  "Fear",                  4, 7),
    _make_wand("Wand of Fly",                   "Fly",                   3, 5),
    _make_wand("Wand of Haste",                 "Haste",                 3, 5),
    _make_wand("Wand of Ice Storm",             "Ice Storm",             4, 7),
    _make_wand("Wand of Inflict Light Wounds",  "Inflict Light Wounds",  1, 1),
    _make_wand("Wand of Melf's Acid Arrow",     "Melf's Acid Arrow",     2, 3),
    _make_wand("Wand of Neutralize Poison",     "Neutralize Poison",     4, 7),
    _make_wand("Wand of Slow",                  "Slow",                  3, 5),
    _make_wand("Wand of Suggestion",            "Suggestion",            3, 5),
    _make_wand("Wand of Summon Monster III",    "Summon Monster III",    3, 5),
]}


# ---------------------------------------------------------------------------
# T-030: ROD_REGISTRY — 20 SRD rods
# ---------------------------------------------------------------------------

def _make_rod(name: str, market_price_gp: int, charges_max: int = 0) -> RodBase:
    return RodBase(name=name, charges_max=charges_max, market_price_gp=market_price_gp)


ROD_REGISTRY: dict[str, RodBase] = {r.name: r for r in [
    _make_rod("Rod of Absorption",                  50_000),
    _make_rod("Rod of Alertness",                   85_000),
    _make_rod("Rod of Cancellation",                11_000),
    _make_rod("Rod of Enemy Detection",             23_500),
    _make_rod("Rod of Flailing",                     2_000),
    _make_rod("Rod of Flame Extinguishing",         15_000),
    _make_rod("Rod of Lordly Might",                70_000),
    _make_rod("Rod of Metal and Mineral Detection", 10_500),
    _make_rod("Rod of Negation",                    37_000),
    _make_rod("Rod of Python",                      13_000),
    _make_rod("Rod of Rulership",                   60_000),
    _make_rod("Rod of Security",                    61_000),
    _make_rod("Rod of Smiting",                      4_000),
    _make_rod("Rod of Splendor",                    25_000),
    _make_rod("Rod of Thunder and Lightning",       33_000),
    _make_rod("Rod of the Viper",                   19_000),
    _make_rod("Rod of Viscid Globs",                60_000),
    _make_rod("Rod of Withering",                   25_000),
    _make_rod("Rod of Wonder",                      12_000),
    _make_rod("Immovable Rod",                       5_000),
]}


# ---------------------------------------------------------------------------
# T-031: STAFF_REGISTRY — 20 SRD staves
# ---------------------------------------------------------------------------

def _make_staff(name: str, market_price_gp: int) -> StaffBase:
    return StaffBase(name=name, charges_max=50, market_price_gp=market_price_gp)


STAFF_REGISTRY: dict[str, StaffBase] = {s.name: s for s in [
    _make_staff("Staff of Abjuration",          65_000),
    _make_staff("Staff of Charming",            16_500),
    _make_staff("Staff of Conjuration",         65_000),
    _make_staff("Staff of Defense",             58_250),
    _make_staff("Staff of Divination",          65_000),
    _make_staff("Staff of Earth and Stone",     80_500),
    _make_staff("Staff of Evocation",           65_000),
    _make_staff("Staff of Fire",                17_750),
    _make_staff("Staff of Frost",               41_400),
    _make_staff("Staff of Healing",             27_750),
    _make_staff("Staff of Illumination",        48_250),
    _make_staff("Staff of Illusion",            65_000),
    _make_staff("Staff of Life",               109_400),
    _make_staff("Staff of Necromancy",          65_000),
    _make_staff("Staff of Passage",            206_900),
    _make_staff("Staff of Power",              211_000),
    _make_staff("Staff of Size Alteration",     29_000),
    _make_staff("Staff of Swarming Insects",    24_750),
    _make_staff("Staff of Transmutation",       65_000),
    _make_staff("Staff of Woodlands",          101_250),
]}
