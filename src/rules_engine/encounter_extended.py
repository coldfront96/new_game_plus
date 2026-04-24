"""
src/rules_engine/encounter_extended.py
---------------------------------------
Extended encounter mechanics: terrain encounter tables, encounter builder, full encounter generator.
Implements T-045, T-052, T-056.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from src.rules_engine.encounter import (
    calculate_el, distribute_xp, xp_for_cr, CR_TO_XP,
)

try:
    from src.rules_engine.environment import TerrainType
except ImportError:
    class TerrainType(Enum):
        DUNGEON = "dungeon"
        FOREST = "forest"
        PLAINS = "plains"
        DESERT = "desert"
        HILLS = "hills"
        MOUNTAINS = "mountains"
        MARSH = "marsh"
        ARCTIC = "arctic"
        AQUATIC = "aquatic"
        UNDERGROUND = "underground"
        URBAN = "urban"


# ---------------------------------------------------------------------------
# T-045 Terrain-Specific Random Encounter Tables
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class EncounterEntry:
    d100_low: int
    d100_high: int
    monster_name: str
    number_appearing: str   # dice expression like "1d4" or "2d6"
    cr: float


ENCOUNTER_TABLES: dict[str, list[EncounterEntry]] = {
    "dungeon": [
        EncounterEntry(1, 10, "Dire Rat", "2d4", 0.33),
        EncounterEntry(11, 20, "Skeleton", "1d6+1", 0.33),
        EncounterEntry(21, 30, "Zombie", "1d4", 0.5),
        EncounterEntry(31, 40, "Goblin", "2d4", 0.33),
        EncounterEntry(41, 50, "Orc", "2d4", 0.5),
        EncounterEntry(51, 60, "Gnoll", "1d4", 1.0),
        EncounterEntry(61, 68, "Hobgoblin", "1d6", 0.5),
        EncounterEntry(69, 76, "Ghoul", "1d4", 1.0),
        EncounterEntry(77, 84, "Wight", "1d3", 3.0),
        EncounterEntry(85, 92, "Troll", "1", 5.0),
        EncounterEntry(93, 100, "Wraith", "1d2", 5.0),
    ],
    "forest": [
        EncounterEntry(1, 10, "Wolf", "2d4", 1.0),
        EncounterEntry(11, 20, "Dire Wolf", "1d4", 3.0),
        EncounterEntry(21, 30, "Bear, Black", "1", 2.0),
        EncounterEntry(31, 40, "Goblin", "2d4", 0.33),
        EncounterEntry(41, 50, "Orc", "2d4", 0.5),
        EncounterEntry(51, 58, "Centaur", "1d4", 3.0),
        EncounterEntry(59, 66, "Treant", "1", 8.0),
        EncounterEntry(67, 74, "Owlbear", "1", 4.0),
        EncounterEntry(75, 82, "Dryad", "1d2", 3.0),
        EncounterEntry(83, 90, "Giant Spider", "1d3", 1.0),
        EncounterEntry(91, 100, "Green Dragon, Young", "1", 9.0),
    ],
    "plains": [
        EncounterEntry(1, 10, "Orc", "2d6", 0.5),
        EncounterEntry(11, 20, "Gnoll", "1d6", 1.0),
        EncounterEntry(21, 30, "Centaur", "1d4", 3.0),
        EncounterEntry(31, 40, "Lion", "1d2", 5.0),
        EncounterEntry(41, 50, "Dire Lion", "1", 5.0),
        EncounterEntry(51, 60, "Griffon", "1d3", 4.0),
        EncounterEntry(61, 68, "Wyvern", "1", 7.0),
        EncounterEntry(69, 76, "Manticore", "1", 5.0),
        EncounterEntry(77, 84, "Hobgoblin", "2d4", 0.5),
        EncounterEntry(85, 92, "Chimera", "1", 7.0),
        EncounterEntry(93, 100, "Roc", "1", 9.0),
    ],
    "desert": [
        EncounterEntry(1, 10, "Giant Scorpion", "1d3", 3.0),
        EncounterEntry(11, 20, "Mummy", "1d4", 5.0),
        EncounterEntry(21, 30, "Blue Dragon, Young", "1", 9.0),
        EncounterEntry(31, 40, "Gnoll", "1d6", 1.0),
        EncounterEntry(41, 50, "Dust Mephit", "1d3", 3.0),
        EncounterEntry(51, 60, "Basilisk", "1", 5.0),
        EncounterEntry(61, 68, "Lamia", "1", 6.0),
        EncounterEntry(69, 76, "Giant Ant", "2d4", 1.0),
        EncounterEntry(77, 84, "Giant Viper", "1d3", 2.0),
        EncounterEntry(85, 92, "Fire Mephit", "1d3", 3.0),
        EncounterEntry(93, 100, "Sphinx, Androsphinx", "1", 9.0),
    ],
    "hills": [
        EncounterEntry(1, 10, "Orc", "2d4", 0.5),
        EncounterEntry(11, 20, "Ogre", "1d3", 3.0),
        EncounterEntry(21, 30, "Troll", "1d2", 5.0),
        EncounterEntry(31, 40, "Hill Giant", "1", 7.0),
        EncounterEntry(41, 50, "Griffon", "1d3", 4.0),
        EncounterEntry(51, 60, "Hippogriff", "1d4", 2.0),
        EncounterEntry(61, 68, "Manticore", "1", 5.0),
        EncounterEntry(69, 76, "Ettin", "1", 6.0),
        EncounterEntry(77, 84, "Wyvern", "1", 7.0),
        EncounterEntry(85, 92, "Kobold", "2d6", 0.25),
        EncounterEntry(93, 100, "Bulette", "1", 7.0),
    ],
    "mountains": [
        EncounterEntry(1, 10, "Giant Eagle", "1d3", 3.0),
        EncounterEntry(11, 20, "Cloud Giant", "1", 11.0),
        EncounterEntry(21, 30, "Stone Giant", "1d2", 8.0),
        EncounterEntry(31, 40, "Red Dragon, Young", "1", 10.0),
        EncounterEntry(41, 50, "Roc", "1", 9.0),
        EncounterEntry(51, 60, "Wyvern", "1d2", 7.0),
        EncounterEntry(61, 68, "Frost Giant", "1", 9.0),
        EncounterEntry(69, 76, "Manticore", "1", 5.0),
        EncounterEntry(77, 84, "Troll", "1d3", 5.0),
        EncounterEntry(85, 92, "Chimera", "1", 7.0),
        EncounterEntry(93, 100, "Harpy", "1d4", 4.0),
    ],
    "marsh": [
        EncounterEntry(1, 10, "Crocodile", "1d3", 2.0),
        EncounterEntry(11, 20, "Giant Crocodile", "1", 4.0),
        EncounterEntry(21, 30, "Will-o'-Wisp", "1", 6.0),
        EncounterEntry(31, 40, "Hag, Sea Hag", "1", 4.0),
        EncounterEntry(41, 50, "Black Dragon, Young", "1", 7.0),
        EncounterEntry(51, 60, "Lizardfolk", "2d6", 1.0),
        EncounterEntry(61, 68, "Giant Frog", "1d4", 1.0),
        EncounterEntry(69, 76, "Bullywug", "2d4", 0.5),
        EncounterEntry(77, 84, "Hydra", "1", 7.0),
        EncounterEntry(85, 92, "Troll", "1d2", 5.0),
        EncounterEntry(93, 100, "Green Hag", "1", 5.0),
    ],
    "arctic": [
        EncounterEntry(1, 10, "Dire Wolf", "1d4", 3.0),
        EncounterEntry(11, 20, "Polar Bear", "1d2", 4.0),
        EncounterEntry(21, 30, "Winter Wolf", "1d4", 5.0),
        EncounterEntry(31, 40, "White Dragon, Young", "1", 8.0),
        EncounterEntry(41, 50, "Frost Giant", "1", 9.0),
        EncounterEntry(51, 60, "Ice Mephit", "1d4", 3.0),
        EncounterEntry(61, 68, "Remorhaz", "1", 7.0),
        EncounterEntry(69, 76, "Troll", "1d2", 5.0),
        EncounterEntry(77, 84, "Yeti", "1d2", 3.0),
        EncounterEntry(85, 92, "Snow Leopard", "1d3", 2.0),
        EncounterEntry(93, 100, "Mammoth", "1d3", 8.0),
    ],
}


def _roll_encounter_table(terrain_key: str, rng: random.Random) -> EncounterEntry | None:
    """Roll d100 and return matching encounter entry."""
    table = ENCOUNTER_TABLES.get(terrain_key)
    if not table:
        return None
    roll = rng.randint(1, 100)
    for entry in table:
        if entry.d100_low <= roll <= entry.d100_high:
            return entry
    return table[-1]


# ---------------------------------------------------------------------------
# T-052 Encounter Builder by APL
# ---------------------------------------------------------------------------

class EncounterDifficulty(Enum):
    EASY = "easy"
    AVERAGE = "average"
    CHALLENGING = "challenging"
    HARD = "hard"
    OVERWHELMING = "overwhelming"


_DIFFICULTY_EL_OFFSET: dict[str, int] = {
    "easy": -2,
    "average": 0,
    "challenging": 1,
    "hard": 2,
    "overwhelming": 4,
}


@dataclass(slots=True)
class EncounterBlueprint:
    target_el: float
    actual_el: float
    monsters: list[tuple[str, int, float]]   # (name, count, cr)
    difficulty: EncounterDifficulty
    terrain: str


def build_encounter(
    apl: int,
    difficulty: EncounterDifficulty,
    terrain: TerrainType | str,
    rng: random.Random | None = None,
) -> EncounterBlueprint:
    """Build an encounter by APL and difficulty targeting EL = APL + offset.

    Selects monsters from ENCOUNTER_TABLES[terrain], validates final EL.
    """
    if rng is None:
        rng = random.Random()

    terrain_key = terrain.value if hasattr(terrain, "value") else str(terrain)
    if terrain_key not in ENCOUNTER_TABLES:
        terrain_key = "dungeon"

    offset = _DIFFICULTY_EL_OFFSET[difficulty.value]
    target_el = float(apl + offset)
    target_el = max(0.5, target_el)

    table = ENCOUNTER_TABLES[terrain_key]

    best_monsters: list[tuple[str, int, float]] = []
    best_el = 0.0

    for attempt in range(20):
        entry = rng.choice(table)
        count = _parse_dice_avg(entry.number_appearing)
        monster_crs = [entry.cr] * max(1, count)

        el = calculate_el(monster_crs)
        if abs(el - target_el) < abs(best_el - target_el) or not best_monsters:
            best_monsters = [(entry.monster_name, max(1, count), entry.cr)]
            best_el = el

        if abs(best_el - target_el) <= 1.0:
            break

    return EncounterBlueprint(
        target_el=target_el,
        actual_el=best_el,
        monsters=best_monsters,
        difficulty=difficulty,
        terrain=terrain_key,
    )


def _parse_dice_avg(dice_str: str) -> int:
    """Parse a dice expression like '2d4' and return average count."""
    dice_str = dice_str.strip().split("+")[0]  # ignore modifiers like "1d6+1"
    if "d" in dice_str:
        parts = dice_str.split("d")
        try:
            count = int(parts[0]) if parts[0] else 1
            sides = int(parts[1])
            return max(1, int(count * (sides + 1) / 2))
        except (ValueError, IndexError):
            return 1
    try:
        return max(1, int(dice_str))
    except ValueError:
        return 1


# ---------------------------------------------------------------------------
# T-056 Full Encounter Generator
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class EncounterReport:
    blueprint: EncounterBlueprint
    xp_per_character: dict[str, int]
    treasure_type: str
    weather_description: str


def run_encounter(
    party_levels: list[int],
    apl: int,
    terrain: TerrainType | str,
    difficulty: EncounterDifficulty,
    rng: random.Random | None = None,
) -> EncounterReport:
    """Full encounter generator: build encounter, calculate XP, determine treasure.

    party_levels: list of character levels
    apl: average party level
    terrain: terrain type
    difficulty: encounter difficulty
    """
    if rng is None:
        rng = random.Random()

    blueprint = build_encounter(apl, difficulty, terrain, rng)

    xp_awards = distribute_xp(blueprint.actual_el, party_levels)
    xp_dict = {f"character_{k + 1}": v for k, v in xp_awards.items()}

    from src.rules_engine.treasure import _cr_to_treasure_letter
    treasure_letter = _cr_to_treasure_letter(blueprint.actual_el)

    return EncounterReport(
        blueprint=blueprint,
        xp_per_character=xp_dict,
        treasure_type=treasure_letter,
        weather_description="Clear skies",
    )
