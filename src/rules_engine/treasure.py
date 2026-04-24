"""
src/rules_engine/treasure.py
-----------------------------
D&D 3.5e DMG Treasure Hoard Generation Engine.

Implements DMG Table 7-1 (Treasure Types A–Z), Table 7-4 (Gems),
Table 7-6 (Art Objects), and the hoard-generation algorithm.

Usage::

    from src.rules_engine.treasure import generate_treasure_hoard
    import random

    rng = random.Random(42)
    hoard = generate_treasure_hoard(cr=5, rng=rng)
    print(hoard.coins)          # {'gp': 1200, ...}
    print(hoard.total_value_gp) # float
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class GemGrade(Enum):
    ORNAMENTAL = "ornamental"
    SEMIPRECIOUS = "semiprecious"
    FANCY = "fancy"
    PRECIOUS = "precious"
    GEMSTONE = "gemstone"
    JEWEL = "jewel"


class ArtObjectCategory(Enum):
    MUNDANE = "mundane"
    DECORATED = "decorated"
    MASTERWORK = "masterwork"
    EXOTIC = "exotic"


# GP conversion rates for each coin type.
COIN_TO_GP: dict[str, float] = {"cp": 0.01, "sp": 0.1, "gp": 1.0, "pp": 10.0}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class GemEntry:
    name: str
    grade: GemGrade
    base_value_gp: int
    value_range_gp: tuple[int, int]


@dataclass(slots=True)
class ArtObjectEntry:
    name: str
    category: ArtObjectCategory
    value_gp: int


@dataclass(slots=True)
class CoinRoll:
    """Represents 'count d-die × multiplier' coins."""
    count: int
    die: int
    multiplier: int


@dataclass(slots=True)
class TreasureTypeEntry:
    coin_rolls: list[tuple[str, int, CoinRoll]]   # (coin_type, chance_pct, roll)
    gem_chance_pct: int
    gem_count_dice: str    # e.g. "2d6"
    art_chance_pct: int
    art_count_dice: str
    magic_item_chance_pct: int
    magic_item_count_dice: str


@dataclass(slots=True)
class TreasureHoard:
    coins: dict[str, int]
    gems: list[GemEntry]
    art_objects: list[ArtObjectEntry]
    magic_item_count: int
    total_value_gp: float


# ---------------------------------------------------------------------------
# Gem Table (DMG Table 7-4, 30+ entries across 6 grades)
# ---------------------------------------------------------------------------

GEM_TABLE: list[GemEntry] = [
    # Ornamental — base 10 gp, range 4–16 gp
    GemEntry("Azurite",         GemGrade.ORNAMENTAL,  10, (4,  16)),
    GemEntry("Banded Agate",    GemGrade.ORNAMENTAL,  10, (4,  16)),
    GemEntry("Blue Quartz",     GemGrade.ORNAMENTAL,  10, (4,  16)),
    GemEntry("Eye Agate",       GemGrade.ORNAMENTAL,  10, (4,  16)),
    GemEntry("Malachite",       GemGrade.ORNAMENTAL,  10, (4,  16)),
    GemEntry("Moss Agate",      GemGrade.ORNAMENTAL,  10, (4,  16)),
    GemEntry("Obsidian",        GemGrade.ORNAMENTAL,  10, (4,  16)),
    GemEntry("Rhodonite",       GemGrade.ORNAMENTAL,  10, (4,  16)),
    GemEntry("Tiger Eye",       GemGrade.ORNAMENTAL,  10, (4,  16)),
    GemEntry("Turquoise",       GemGrade.ORNAMENTAL,  10, (4,  16)),

    # Semiprecious — base 50 gp, range 20–80 gp
    GemEntry("Bloodstone",      GemGrade.SEMIPRECIOUS, 50, (20, 80)),
    GemEntry("Carnelian",       GemGrade.SEMIPRECIOUS, 50, (20, 80)),
    GemEntry("Chalcedony",      GemGrade.SEMIPRECIOUS, 50, (20, 80)),
    GemEntry("Chrysoprase",     GemGrade.SEMIPRECIOUS, 50, (20, 80)),
    GemEntry("Citrine",         GemGrade.SEMIPRECIOUS, 50, (20, 80)),
    GemEntry("Iolite",          GemGrade.SEMIPRECIOUS, 50, (20, 80)),
    GemEntry("Jasper",          GemGrade.SEMIPRECIOUS, 50, (20, 80)),
    GemEntry("Moonstone",       GemGrade.SEMIPRECIOUS, 50, (20, 80)),
    GemEntry("Onyx",            GemGrade.SEMIPRECIOUS, 50, (20, 80)),
    GemEntry("Rock Crystal",    GemGrade.SEMIPRECIOUS, 50, (20, 80)),
    GemEntry("Sardonyx",        GemGrade.SEMIPRECIOUS, 50, (20, 80)),
    GemEntry("Rose Quartz",     GemGrade.SEMIPRECIOUS, 50, (20, 80)),
    GemEntry("Smoky Quartz",    GemGrade.SEMIPRECIOUS, 50, (20, 80)),
    GemEntry("Star Quartz",     GemGrade.SEMIPRECIOUS, 50, (20, 80)),
    GemEntry("Zircon",          GemGrade.SEMIPRECIOUS, 50, (20, 80)),

    # Fancy — base 100 gp, range 40–160 gp
    GemEntry("Amber",           GemGrade.FANCY,       100, (40,  160)),
    GemEntry("Amethyst",        GemGrade.FANCY,       100, (40,  160)),
    GemEntry("Chrysoberyl",     GemGrade.FANCY,       100, (40,  160)),
    GemEntry("Coral",           GemGrade.FANCY,       100, (40,  160)),
    GemEntry("Red Garnet",      GemGrade.FANCY,       100, (40,  160)),
    GemEntry("Jade",            GemGrade.FANCY,       100, (40,  160)),
    GemEntry("Jet",             GemGrade.FANCY,       100, (40,  160)),
    GemEntry("White Pearl",     GemGrade.FANCY,       100, (40,  160)),
    GemEntry("Red Spinel",      GemGrade.FANCY,       100, (40,  160)),
    GemEntry("Tourmaline",      GemGrade.FANCY,       100, (40,  160)),

    # Precious — base 500 gp, range 200–800 gp
    GemEntry("Alexandrite",         GemGrade.PRECIOUS,  500, (200, 800)),
    GemEntry("Aquamarine",          GemGrade.PRECIOUS,  500, (200, 800)),
    GemEntry("Violet Garnet",       GemGrade.PRECIOUS,  500, (200, 800)),
    GemEntry("Black Pearl",         GemGrade.PRECIOUS,  500, (200, 800)),
    GemEntry("Deep Blue Spinel",    GemGrade.PRECIOUS,  500, (200, 800)),
    GemEntry("Golden Yellow Topaz", GemGrade.PRECIOUS,  500, (200, 800)),

    # Gemstone — base 1000 gp, range 500–2000 gp
    GemEntry("Emerald",              GemGrade.GEMSTONE, 1000, (500, 2000)),
    GemEntry("White Opal",           GemGrade.GEMSTONE, 1000, (500, 2000)),
    GemEntry("Black Opal",           GemGrade.GEMSTONE, 1000, (500, 2000)),
    GemEntry("Fire Opal",            GemGrade.GEMSTONE, 1000, (500, 2000)),
    GemEntry("Blue Sapphire",        GemGrade.GEMSTONE, 1000, (500, 2000)),
    GemEntry("Fiery Yellow Corundum",GemGrade.GEMSTONE, 1000, (500, 2000)),

    # Jewel — base 5000 gp, range 1000–8000 gp
    GemEntry("Bright Green Emerald", GemGrade.JEWEL, 5000, (1000, 8000)),
    GemEntry("Blue-White Diamond",   GemGrade.JEWEL, 5000, (1000, 8000)),
    GemEntry("Canary Diamond",       GemGrade.JEWEL, 5000, (1000, 8000)),
    GemEntry("Pink Diamond",         GemGrade.JEWEL, 5000, (1000, 8000)),
    GemEntry("Blue Diamond",         GemGrade.JEWEL, 5000, (1000, 8000)),
    GemEntry("Jacinth",              GemGrade.JEWEL, 5000, (1000, 8000)),
]


# ---------------------------------------------------------------------------
# Art Object Table (DMG Table 7-6, 50+ entries across value bands)
# ---------------------------------------------------------------------------

ART_OBJECT_TABLE: list[ArtObjectEntry] = [
    # 10 gp — Mundane
    ArtObjectEntry("Fur Pelt",                  ArtObjectCategory.MUNDANE,    10),
    ArtObjectEntry("Carved Bone Statuette",     ArtObjectCategory.MUNDANE,    10),
    ArtObjectEntry("Small Bronze Mirror",       ArtObjectCategory.MUNDANE,    10),
    ArtObjectEntry("Painted Cloth",             ArtObjectCategory.MUNDANE,    10),
    ArtObjectEntry("Woven Basket",              ArtObjectCategory.MUNDANE,    10),

    # 25 gp — Mundane/Decorated
    ArtObjectEntry("Carved Ivory Statuette",    ArtObjectCategory.DECORATED,  25),
    ArtObjectEntry("Silver Ewer",               ArtObjectCategory.DECORATED,  25),
    ArtObjectEntry("Cloth-of-Gold Vestments",   ArtObjectCategory.DECORATED,  25),
    ArtObjectEntry("Black Velvet Mask",         ArtObjectCategory.DECORATED,  25),
    ArtObjectEntry("Copper Chalice",            ArtObjectCategory.DECORATED,  25),

    # 50 gp — Decorated
    ArtObjectEntry("Silver Comb with Moonstones",       ArtObjectCategory.DECORATED,  50),
    ArtObjectEntry("Silver-Plated Steel Longsword",     ArtObjectCategory.DECORATED,  50),
    ArtObjectEntry("Carved Harp",                       ArtObjectCategory.DECORATED,  50),
    ArtObjectEntry("Gold Idol",                         ArtObjectCategory.DECORATED,  50),
    ArtObjectEntry("Painted Portrait",                  ArtObjectCategory.DECORATED,  50),

    # 100 gp — Decorated/Masterwork
    ArtObjectEntry("Gold Ring with Bloodstone",         ArtObjectCategory.MASTERWORK, 100),
    ArtObjectEntry("Carved Ivory Charm",                ArtObjectCategory.MASTERWORK, 100),
    ArtObjectEntry("Obsidian Statuette",                ArtObjectCategory.MASTERWORK, 100),
    ArtObjectEntry("Painted Gold Idol",                 ArtObjectCategory.MASTERWORK, 100),
    ArtObjectEntry("Stitched Silk Tapestry",            ArtObjectCategory.MASTERWORK, 100),

    # 250 gp — Masterwork
    ArtObjectEntry("Golden Yellow Topaz Bracelet",      ArtObjectCategory.MASTERWORK, 250),
    ArtObjectEntry("Embroidered Silk Satin Cloak",      ArtObjectCategory.MASTERWORK, 250),
    ArtObjectEntry("Silver Necklace with Fire Opal",    ArtObjectCategory.MASTERWORK, 250),
    ArtObjectEntry("Carved Jade Figurine",              ArtObjectCategory.MASTERWORK, 250),
    ArtObjectEntry("Gold and Silver Brooch",            ArtObjectCategory.MASTERWORK, 250),

    # 500 gp — Masterwork
    ArtObjectEntry("Ivory and Gold Bracelet with Aquamarine",   ArtObjectCategory.MASTERWORK, 500),
    ArtObjectEntry("Silver and Gold Brooch",                    ArtObjectCategory.MASTERWORK, 500),
    ArtObjectEntry("Onyx Goblet with Gold Filigree",            ArtObjectCategory.MASTERWORK, 500),
    ArtObjectEntry("Enameled Gold Locket",                      ArtObjectCategory.MASTERWORK, 500),
    ArtObjectEntry("Amber and Gold Ring",                       ArtObjectCategory.MASTERWORK, 500),

    # 750 gp — Masterwork
    ArtObjectEntry("Jeweled Silver Goblet",                     ArtObjectCategory.MASTERWORK, 750),
    ArtObjectEntry("Platinum Comb with Sapphires",              ArtObjectCategory.MASTERWORK, 750),

    # 1000 gp — Exotic
    ArtObjectEntry("Jeweled Gold Crown",                        ArtObjectCategory.EXOTIC,   1000),
    ArtObjectEntry("Jeweled Electrum Ring",                     ArtObjectCategory.EXOTIC,   1000),
    ArtObjectEntry("Gold Music Box",                            ArtObjectCategory.EXOTIC,   1000),
    ArtObjectEntry("Painted Silver Dragon Statuette",           ArtObjectCategory.EXOTIC,   1000),
    ArtObjectEntry("Sapphire Pendant on Gold Chain",            ArtObjectCategory.EXOTIC,   1000),

    # 1500 gp — Exotic
    ArtObjectEntry("Ruby-Inlaid Gold Chalice",                  ArtObjectCategory.EXOTIC,   1500),
    ArtObjectEntry("Emerald-Set Platinum Brooch",               ArtObjectCategory.EXOTIC,   1500),

    # 2500 gp — Exotic
    ArtObjectEntry("Fine Gold Chain with Fire Opal",            ArtObjectCategory.EXOTIC,   2500),
    ArtObjectEntry("Ornate Gold Ring with Diamond",             ArtObjectCategory.EXOTIC,   2500),
    ArtObjectEntry("Jeweled Platinum Necklace",                 ArtObjectCategory.EXOTIC,   2500),
    ArtObjectEntry("Diamond-Studded Gold Tiara",                ArtObjectCategory.EXOTIC,   2500),
    ArtObjectEntry("Ruby and Sapphire Medallion",               ArtObjectCategory.EXOTIC,   2500),

    # 3500 gp — Exotic
    ArtObjectEntry("Platinum and Diamond Bracelet",             ArtObjectCategory.EXOTIC,   3500),
    ArtObjectEntry("Gold Dragon Idol with Gem Eyes",            ArtObjectCategory.EXOTIC,   3500),

    # 5000 gp — Exotic
    ArtObjectEntry("Jeweled Platinum Crown",                    ArtObjectCategory.EXOTIC,   5000),
    ArtObjectEntry("Marble Idol with Ruby Eyes",                ArtObjectCategory.EXOTIC,   5000),
    ArtObjectEntry("Ornate Platinum and Diamond Tiara",         ArtObjectCategory.EXOTIC,   5000),

    # 7500 gp — Exotic
    ArtObjectEntry("Jeweled Gold and Platinum Crown",           ArtObjectCategory.EXOTIC,   7500),
    ArtObjectEntry("Platinum Idol with Diamond and Sapphire Inlay", ArtObjectCategory.EXOTIC, 7500),
]


# ---------------------------------------------------------------------------
# Treasure Type Tables (DMG Table 7-1, all 26 types A–Z)
# ---------------------------------------------------------------------------

def _cr(count: int, die: int, mult: int = 1) -> CoinRoll:
    return CoinRoll(count=count, die=die, multiplier=mult)


TREASURE_TYPE_TABLES: dict[str, TreasureTypeEntry] = {
    "A": TreasureTypeEntry(
        coin_rolls=[
            ("cp", 25, _cr(1, 6, 1000)),
            ("sp", 30, _cr(1, 6, 100)),
            ("gp", 35, _cr(2, 6, 10)),
            ("pp", 25, _cr(1, 6, 5)),
        ],
        gem_chance_pct=20, gem_count_dice="2d6",
        art_chance_pct=10, art_count_dice="1d3",
        magic_item_chance_pct=30, magic_item_count_dice="3d1",
    ),
    "B": TreasureTypeEntry(
        coin_rolls=[
            ("cp", 50, _cr(1, 8, 1000)),
            ("sp", 25, _cr(1, 6, 1000)),
            ("gp", 25, _cr(1, 3, 1000)),
        ],
        gem_chance_pct=25, gem_count_dice="1d6",
        art_chance_pct=15, art_count_dice="1d3",
        magic_item_chance_pct=10, magic_item_count_dice="1d1",
    ),
    "C": TreasureTypeEntry(
        coin_rolls=[
            ("cp", 20, _cr(1, 12, 100)),
            ("sp", 30, _cr(1, 4, 100)),
        ],
        gem_chance_pct=25, gem_count_dice="1d6",
        art_chance_pct=20, art_count_dice="1d3",
        magic_item_chance_pct=10, magic_item_count_dice="2d1",
    ),
    "D": TreasureTypeEntry(
        coin_rolls=[
            ("cp", 10, _cr(1, 6, 1000)),
            ("sp", 15, _cr(1, 6, 1000)),
            ("gp", 50, _cr(1, 6, 1000)),
        ],
        gem_chance_pct=30, gem_count_dice="1d6",
        art_chance_pct=25, art_count_dice="1d3",
        magic_item_chance_pct=15, magic_item_count_dice="2d1",
    ),
    "E": TreasureTypeEntry(
        coin_rolls=[
            ("cp", 5,  _cr(1, 4, 100)),
            ("sp", 30, _cr(1, 6, 1000)),
            ("gp", 25, _cr(1, 4, 1000)),
            ("pp", 5,  _cr(1, 6, 100)),
        ],
        gem_chance_pct=15, gem_count_dice="1d6",
        art_chance_pct=10, art_count_dice="1d4",
        magic_item_chance_pct=25, magic_item_count_dice="3d1",
    ),
    "F": TreasureTypeEntry(
        coin_rolls=[
            ("sp", 10, _cr(2, 10, 100)),
            ("gp", 45, _cr(2, 10, 100)),
            ("pp", 30, _cr(1, 8, 100)),
        ],
        gem_chance_pct=20, gem_count_dice="2d6",
        art_chance_pct=10, art_count_dice="1d4",
        magic_item_chance_pct=30, magic_item_count_dice="3d1",
    ),
    "G": TreasureTypeEntry(
        coin_rolls=[
            ("gp", 50, _cr(1, 4, 10000)),
            ("pp", 50, _cr(1, 6, 1000)),
        ],
        gem_chance_pct=25, gem_count_dice="3d6",
        art_chance_pct=15, art_count_dice="1d4",
        magic_item_chance_pct=35, magic_item_count_dice="4d1",
    ),
    "H": TreasureTypeEntry(
        coin_rolls=[
            ("cp", 25, _cr(3, 8, 1000)),
            ("sp", 40, _cr(1, 10, 1000)),
            ("gp", 55, _cr(1, 8, 1000)),
            ("pp", 25, _cr(1, 4, 1000)),
        ],
        gem_chance_pct=50, gem_count_dice="1d100",
        art_chance_pct=30, art_count_dice="1d4",
        magic_item_chance_pct=15, magic_item_count_dice="1d4",
    ),
    "I": TreasureTypeEntry(
        coin_rolls=[
            ("pp", 30, _cr(2, 6, 100)),
        ],
        gem_chance_pct=55, gem_count_dice="2d6",
        art_chance_pct=40, art_count_dice="1d4",
        magic_item_chance_pct=15, magic_item_count_dice="1d1",
    ),
    "J": TreasureTypeEntry(
        coin_rolls=[
            ("cp", 45, _cr(3, 6, 1000)),
            ("sp", 45, _cr(1, 8, 1000)),
        ],
        gem_chance_pct=0, gem_count_dice="1d1",
        art_chance_pct=0, art_count_dice="1d1",
        magic_item_chance_pct=0, magic_item_count_dice="1d1",
    ),
    "K": TreasureTypeEntry(
        coin_rolls=[
            ("cp", 90, _cr(2, 10, 100)),
            ("sp", 35, _cr(1, 8, 100)),
        ],
        gem_chance_pct=0, gem_count_dice="1d1",
        art_chance_pct=0, art_count_dice="1d1",
        magic_item_chance_pct=0, magic_item_count_dice="1d1",
    ),
    "L": TreasureTypeEntry(
        coin_rolls=[
            ("sp", 50, _cr(3, 6, 10)),
        ],
        gem_chance_pct=0, gem_count_dice="1d1",
        art_chance_pct=0, art_count_dice="1d1",
        magic_item_chance_pct=0, magic_item_count_dice="1d1",
    ),
    "M": TreasureTypeEntry(
        coin_rolls=[
            ("gp", 55, _cr(2, 4, 100)),
            ("pp", 45, _cr(2, 6, 10)),
        ],
        gem_chance_pct=0, gem_count_dice="1d1",
        art_chance_pct=0, art_count_dice="1d1",
        magic_item_chance_pct=0, magic_item_count_dice="1d1",
    ),
    "N": TreasureTypeEntry(
        coin_rolls=[],
        gem_chance_pct=0, gem_count_dice="1d1",
        art_chance_pct=0, art_count_dice="1d1",
        magic_item_chance_pct=40, magic_item_count_dice="2d4",
    ),
    "O": TreasureTypeEntry(
        coin_rolls=[
            ("cp", 25, _cr(1, 4, 100)),
            ("sp", 50, _cr(1, 6, 100)),
        ],
        gem_chance_pct=0, gem_count_dice="1d1",
        art_chance_pct=0, art_count_dice="1d1",
        magic_item_chance_pct=0, magic_item_count_dice="1d1",
    ),
    "P": TreasureTypeEntry(
        coin_rolls=[
            ("cp", 100, _cr(3, 8, 1)),
        ],
        gem_chance_pct=0, gem_count_dice="1d1",
        art_chance_pct=0, art_count_dice="1d1",
        magic_item_chance_pct=0, magic_item_count_dice="1d1",
    ),
    "Q": TreasureTypeEntry(
        coin_rolls=[
            ("sp", 100, _cr(3, 6, 1)),
        ],
        gem_chance_pct=0, gem_count_dice="1d1",
        art_chance_pct=0, art_count_dice="1d1",
        magic_item_chance_pct=0, magic_item_count_dice="1d1",
    ),
    "R": TreasureTypeEntry(
        coin_rolls=[
            ("gp", 100, _cr(2, 6, 1)),
            ("pp", 75, _cr(2, 4, 1)),
        ],
        gem_chance_pct=0, gem_count_dice="1d1",
        art_chance_pct=0, art_count_dice="1d1",
        magic_item_chance_pct=0, magic_item_count_dice="1d1",
    ),
    "S": TreasureTypeEntry(
        coin_rolls=[],
        gem_chance_pct=0, gem_count_dice="1d1",
        art_chance_pct=0, art_count_dice="1d1",
        magic_item_chance_pct=100, magic_item_count_dice="2d4",
    ),
    "T": TreasureTypeEntry(
        coin_rolls=[],
        gem_chance_pct=0, gem_count_dice="1d1",
        art_chance_pct=0, art_count_dice="1d1",
        magic_item_chance_pct=100, magic_item_count_dice="1d4",
    ),
    "U": TreasureTypeEntry(
        coin_rolls=[
            ("cp", 10, _cr(1, 4, 10)),
            ("sp", 10, _cr(1, 4, 10)),
            ("gp", 5,  _cr(1, 4, 10)),
        ],
        gem_chance_pct=5, gem_count_dice="1d4",
        art_chance_pct=5, art_count_dice="1d4",
        magic_item_chance_pct=2, magic_item_count_dice="1d1",
    ),
    "V": TreasureTypeEntry(
        coin_rolls=[
            ("sp", 10, _cr(1, 4, 100)),
            ("gp", 10, _cr(1, 4, 100)),
            ("pp", 5,  _cr(1, 4, 100)),
        ],
        gem_chance_pct=10, gem_count_dice="1d4",
        art_chance_pct=10, art_count_dice="1d4",
        magic_item_chance_pct=15, magic_item_count_dice="1d4",
    ),
    "W": TreasureTypeEntry(
        coin_rolls=[
            ("sp", 30, _cr(1, 8, 100)),
            ("gp", 40, _cr(1, 6, 100)),
            ("pp", 10, _cr(1, 4, 100)),
        ],
        gem_chance_pct=15, gem_count_dice="1d6",
        art_chance_pct=10, art_count_dice="1d4",
        magic_item_chance_pct=30, magic_item_count_dice="1d4",
    ),
    "X": TreasureTypeEntry(
        coin_rolls=[
            ("gp", 20, _cr(1, 4, 100)),
            ("pp", 5,  _cr(1, 6, 100)),
        ],
        gem_chance_pct=10, gem_count_dice="1d6",
        art_chance_pct=0,  art_count_dice="1d1",
        magic_item_chance_pct=40, magic_item_count_dice="1d4",
    ),
    "Y": TreasureTypeEntry(
        coin_rolls=[
            ("gp", 70, _cr(2, 6, 100)),
            ("pp", 50, _cr(2, 4, 100)),
        ],
        gem_chance_pct=0,  gem_count_dice="1d1",
        art_chance_pct=0,  art_count_dice="1d1",
        magic_item_chance_pct=70, magic_item_count_dice="1d4",
    ),
    "Z": TreasureTypeEntry(
        coin_rolls=[
            ("cp", 20, _cr(1, 4, 100)),
            ("sp", 35, _cr(1, 6, 100)),
            ("gp", 50, _cr(1, 8, 100)),
            ("pp", 25, _cr(1, 6, 100)),
        ],
        gem_chance_pct=30, gem_count_dice="1d4",
        art_chance_pct=40, art_count_dice="1d6",
        magic_item_chance_pct=60, magic_item_count_dice="2d4",
    ),
}


# ---------------------------------------------------------------------------
# CR → Treasure Type mapping (DMG Table 7-2)
# ---------------------------------------------------------------------------

CR_TO_TREASURE_TYPE: dict[str, str] = {
    "1":   "A",
    "2":   "B",
    "3":   "C",
    "4":   "D",
    "5":   "E",
    "6":   "F",
    "7":   "G",
    "8":   "G",
    "9":   "H",
    "10":  "H",
    "11":  "I",
    "12":  "I",
    "13":  "J",
    "14":  "J",
    "15":  "K",
    "16":  "K",
    "17":  "L",
    "18":  "L",
    "19":  "M",
    "20":  "M",
    "21+": "N",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _roll_dice_str(dice_str: str, rng: random.Random) -> int:
    """Roll a dice expression like '2d6' or '1d3'."""
    count_s, sides_s = dice_str.split("d")
    count = int(count_s)
    sides = int(sides_s)
    return sum(rng.randint(1, sides) for _ in range(count))


def _cr_to_treasure_letter(cr: float) -> str:
    cr_int = int(cr)
    if cr_int >= 21:
        return CR_TO_TREASURE_TYPE["21+"]
    key = str(max(1, cr_int))
    return CR_TO_TREASURE_TYPE.get(key, "A")


# ---------------------------------------------------------------------------
# Tier 1 Mechanics
# ---------------------------------------------------------------------------

def roll_gem_value(gem: GemEntry, rng: random.Random) -> int:
    """Roll gem value within its range.

    On d% 1–10: multiply result by 10 (exceptional quality).
    On d% 91–100: multiply result by 100 (extraordinary quality).
    Otherwise: return rolled value clamped to value_range_gp.
    """
    base_roll = rng.randint(gem.value_range_gp[0], gem.value_range_gp[1])
    d_pct = rng.randint(1, 100)
    if d_pct <= 10:
        return base_roll * 10
    if d_pct >= 91:
        return base_roll * 100
    return base_roll


def roll_art_object(rng: random.Random) -> ArtObjectEntry:
    """Roll a random art object from ART_OBJECT_TABLE."""
    return rng.choice(ART_OBJECT_TABLE)


# ---------------------------------------------------------------------------
# Hoard Generation
# ---------------------------------------------------------------------------

def generate_treasure_hoard(
    cr: float,
    rng: Optional[random.Random] = None,
) -> TreasureHoard:
    """Generate a treasure hoard for an encounter of the given CR.

    Args:
        cr:  Challenge Rating of the encounter (1–30+).
        rng: Seeded :class:`random.Random` instance; defaults to a fresh one.

    Returns:
        A :class:`TreasureHoard` with coins, gems, art objects, and a count
        of magic items (not yet generated).
    """
    if rng is None:
        rng = random.Random()

    treasure_letter = _cr_to_treasure_letter(cr)
    entry = TREASURE_TYPE_TABLES[treasure_letter]

    # --- Coins ---
    coins: dict[str, int] = {}
    for coin_type, chance_pct, coin_roll in entry.coin_rolls:
        if rng.randint(1, 100) <= chance_pct:
            rolled = sum(rng.randint(1, coin_roll.die) for _ in range(coin_roll.count))
            coins[coin_type] = rolled * coin_roll.multiplier

    # --- Gems ---
    gems: list[GemEntry] = []
    if entry.gem_chance_pct > 0 and rng.randint(1, 100) <= entry.gem_chance_pct:
        count = _roll_dice_str(entry.gem_count_dice, rng)
        for _ in range(count):
            gems.append(rng.choice(GEM_TABLE))

    # --- Art Objects ---
    art_objects: list[ArtObjectEntry] = []
    if entry.art_chance_pct > 0 and rng.randint(1, 100) <= entry.art_chance_pct:
        count = _roll_dice_str(entry.art_count_dice, rng)
        for _ in range(count):
            art_objects.append(roll_art_object(rng))

    # --- Magic Items ---
    magic_item_count = 0
    if entry.magic_item_chance_pct > 0 and rng.randint(1, 100) <= entry.magic_item_chance_pct:
        magic_item_count = _roll_dice_str(entry.magic_item_count_dice, rng)

    # --- Total value ---
    gp_per_coin = COIN_TO_GP
    total_value = sum(amt * gp_per_coin.get(coin, 1.0) for coin, amt in coins.items())
    for gem in gems:
        total_value += gem.base_value_gp
    for art in art_objects:
        total_value += art.value_gp

    return TreasureHoard(
        coins=coins,
        gems=gems,
        art_objects=art_objects,
        magic_item_count=magic_item_count,
        total_value_gp=total_value,
    )
