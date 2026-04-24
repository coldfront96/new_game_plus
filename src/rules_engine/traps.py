"""
src/rules_engine/traps.py
--------------------------
D&D 3.5e DMG Chapter 3 — Trap Schema, Search, and Disable mechanics.

Covers:
- T-004: TrapBase dataclass and supporting enums
- T-016: resolve_trap_search / find_trap_active
- T-017: resolve_trap_disable
- T-040: MechanicalTrap and generate_mechanical_trap
- T-041: MagicalTrap and generate_magical_trap
- T-047: RoomContents and roll_room_contents
- T-057: DungeonLevel and generate_dungeon_level
"""

from __future__ import annotations

import random as _random
from dataclasses import dataclass
from enum import Enum


# ---------------------------------------------------------------------------
# T-004: Enums
# ---------------------------------------------------------------------------

class TrapType(Enum):
    """Whether a trap is mundane or magical in origin."""

    MECHANICAL = "mechanical"
    MAGIC = "magic"


class TriggerType(Enum):
    """How a trap is set off."""

    LOCATION = "location"
    PROXIMITY = "proximity"
    TOUCH = "touch"
    SOUND = "sound"
    VISUAL = "visual"
    TIMED = "timed"


class ResetType(Enum):
    """How (or whether) a trap resets after firing."""

    NO_RESET = "no_reset"
    REPAIR = "repair"
    AUTOMATIC = "automatic"
    MANUAL = "manual"


class DisableResult(Enum):
    """Outcome of a Disable Device attempt."""

    DISABLED = "disabled"
    FAILED = "failed"
    TRIGGERED = "triggered"


# ---------------------------------------------------------------------------
# T-004: TrapBase dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class TrapBase:
    """Core trap definition following DMG trap stat-block conventions.

    Attributes:
        name:       Descriptive name of the trap.
        cr:         Challenge Rating (may be fractional, e.g. ``0.5``).
        trap_type:  :class:`TrapType` — mechanical or magical.
        trigger:    :class:`TriggerType` — how the trap fires.
        reset:      :class:`ResetType` — how (if at all) the trap resets.
        search_dc:  DC to *find* the trap with a Search check.
        disable_dc: DC to *disable* the trap with a Disable Device check.
    """

    name: str
    cr: float
    trap_type: TrapType
    trigger: TriggerType
    reset: ResetType
    search_dc: int
    disable_dc: int


# ---------------------------------------------------------------------------
# T-016: Trap search resolvers
# ---------------------------------------------------------------------------

def resolve_trap_search(trap: TrapBase, searcher_search_modifier: int) -> bool:
    """Passive detection check (10 + Search modifier vs. search_dc).

    Args:
        trap:                     The trap being searched for.
        searcher_search_modifier: Total Search skill modifier.

    Returns:
        ``True`` if the passive check meets or exceeds the trap's search DC.
    """
    passive = 10 + searcher_search_modifier
    return passive >= trap.search_dc


def find_trap_active(trap: TrapBase, active_roll: int) -> bool:
    """Active Search check (d20 already rolled and added to modifier).

    Args:
        trap:         The trap being searched for.
        active_roll:  Full d20 + Search modifier result.

    Returns:
        ``True`` if the active roll meets or exceeds the trap's search DC.
    """
    return active_roll >= trap.search_dc


# ---------------------------------------------------------------------------
# T-017: Trap disable resolver
# ---------------------------------------------------------------------------

def resolve_trap_disable(trap: TrapBase, disable_roll: int) -> DisableResult:
    """Disable Device check against the trap's disable DC.

    Per DMG rules, failing by 5 or more accidentally triggers the trap.

    Args:
        trap:          The trap being disabled.
        disable_roll:  Full d20 + Disable Device modifier result.

    Returns:
        :class:`DisableResult` — DISABLED, FAILED, or TRIGGERED.
    """
    if disable_roll >= trap.disable_dc:
        return DisableResult.DISABLED
    elif disable_roll <= trap.disable_dc - 5:
        return DisableResult.TRIGGERED
    else:
        return DisableResult.FAILED


# ---------------------------------------------------------------------------
# T-040 Mechanical Trap Generator
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class MechanicalTrap:
    # TrapBase fields
    name: str
    cr: float
    trap_type: TrapType
    trigger: TriggerType
    reset: ResetType
    search_dc: int
    disable_dc: int
    # MechanicalTrap-specific fields
    damage_dice: str
    attack_bonus: int | None
    save_type: str | None
    save_dc: int | None
    reflex_negates: bool


_MECHANICAL_TRAP_TEMPLATES: list[dict] = [
    # CR 1
    {"name": "Basic Pit Trap", "cr": 1.0, "search_dc": 20, "disable_dc": 20, "damage_dice": "1d6", "attack_bonus": None, "save_type": "Reflex", "save_dc": 20, "reflex_negates": True, "trigger": TriggerType.LOCATION, "reset": ResetType.MANUAL},
    {"name": "Spiked Pit Trap", "cr": 1.0, "search_dc": 20, "disable_dc": 20, "damage_dice": "1d6+1d4", "attack_bonus": None, "save_type": "Reflex", "save_dc": 20, "reflex_negates": False, "trigger": TriggerType.LOCATION, "reset": ResetType.MANUAL},
    {"name": "Spear Trap", "cr": 1.0, "search_dc": 20, "disable_dc": 20, "damage_dice": "1d8", "attack_bonus": 10, "save_type": None, "save_dc": None, "reflex_negates": False, "trigger": TriggerType.LOCATION, "reset": ResetType.AUTOMATIC},
    # CR 2
    {"name": "Arrow Trap", "cr": 2.0, "search_dc": 20, "disable_dc": 20, "damage_dice": "1d8", "attack_bonus": 10, "save_type": None, "save_dc": None, "reflex_negates": False, "trigger": TriggerType.LOCATION, "reset": ResetType.AUTOMATIC},
    {"name": "Locking Pit Trap", "cr": 2.0, "search_dc": 20, "disable_dc": 20, "damage_dice": "2d6", "attack_bonus": None, "save_type": "Reflex", "save_dc": 22, "reflex_negates": False, "trigger": TriggerType.LOCATION, "reset": ResetType.MANUAL},
    # CR 3
    {"name": "Crossbow Trap", "cr": 3.0, "search_dc": 20, "disable_dc": 20, "damage_dice": "1d8", "attack_bonus": 14, "save_type": None, "save_dc": None, "reflex_negates": False, "trigger": TriggerType.TOUCH, "reset": ResetType.AUTOMATIC},
    {"name": "Blade Trap", "cr": 3.0, "search_dc": 22, "disable_dc": 22, "damage_dice": "2d6", "attack_bonus": 14, "save_type": None, "save_dc": None, "reflex_negates": False, "trigger": TriggerType.LOCATION, "reset": ResetType.AUTOMATIC},
    # CR 4
    {"name": "Swinging Blade Trap", "cr": 4.0, "search_dc": 23, "disable_dc": 23, "damage_dice": "2d6+5", "attack_bonus": 15, "save_type": None, "save_dc": None, "reflex_negates": False, "trigger": TriggerType.LOCATION, "reset": ResetType.AUTOMATIC},
    # CR 5
    {"name": "Falling Block Trap", "cr": 5.0, "search_dc": 25, "disable_dc": 20, "damage_dice": "6d6", "attack_bonus": None, "save_type": "Reflex", "save_dc": 20, "reflex_negates": True, "trigger": TriggerType.LOCATION, "reset": ResetType.REPAIR},
    # CR 6
    {"name": "Rolling Boulder Trap", "cr": 6.0, "search_dc": 25, "disable_dc": 25, "damage_dice": "8d6", "attack_bonus": None, "save_type": "Reflex", "save_dc": 22, "reflex_negates": True, "trigger": TriggerType.LOCATION, "reset": ResetType.REPAIR},
    # CR 8
    {"name": "Malfunctioning Arrow Trap", "cr": 8.0, "search_dc": 25, "disable_dc": 25, "damage_dice": "2d8", "attack_bonus": 20, "save_type": None, "save_dc": None, "reflex_negates": False, "trigger": TriggerType.LOCATION, "reset": ResetType.AUTOMATIC},
    # CR 10
    {"name": "Spiked Pit with Lock", "cr": 10.0, "search_dc": 25, "disable_dc": 25, "damage_dice": "4d6+4d4", "attack_bonus": None, "save_type": "Reflex", "save_dc": 25, "reflex_negates": False, "trigger": TriggerType.LOCATION, "reset": ResetType.MANUAL},
]


def generate_mechanical_trap(cr: float, rng: _random.Random | None = None) -> MechanicalTrap:
    """Generate a mechanical trap of approximately the given CR per DMG Chapter 4."""
    if rng is None:
        rng = _random.Random()

    candidates = [t for t in _MECHANICAL_TRAP_TEMPLATES if abs(t["cr"] - cr) <= 1.0]
    if not candidates:
        candidates = [min(_MECHANICAL_TRAP_TEMPLATES, key=lambda t: abs(t["cr"] - cr))]

    template = rng.choice(candidates)
    return MechanicalTrap(
        name=template["name"],
        cr=template["cr"],
        trap_type=TrapType.MECHANICAL,
        trigger=template["trigger"],
        reset=template["reset"],
        search_dc=template["search_dc"],
        disable_dc=template["disable_dc"],
        damage_dice=template["damage_dice"],
        attack_bonus=template["attack_bonus"],
        save_type=template["save_type"],
        save_dc=template["save_dc"],
        reflex_negates=template["reflex_negates"],
    )


# ---------------------------------------------------------------------------
# T-041 Magical Trap Generator
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class MagicalTrap:
    # TrapBase fields
    name: str
    cr: float
    trap_type: TrapType
    trigger: TriggerType
    reset: ResetType
    search_dc: int
    disable_dc: int
    # MagicalTrap-specific fields
    spell_effect: str
    caster_level: int
    save_dc: int | None
    aoe: str | None


_MAGICAL_TRAP_TEMPLATES: list[dict] = [
    # CR 1
    {"name": "Alarm Trap", "cr": 1.0, "search_dc": 27, "disable_dc": 27, "spell_effect": "alarm", "caster_level": 1, "save_dc": None, "aoe": None, "trigger": TriggerType.LOCATION, "reset": ResetType.NO_RESET},
    # CR 2
    {"name": "Fire Trap", "cr": 2.0, "search_dc": 26, "disable_dc": 26, "spell_effect": "fire trap", "caster_level": 3, "save_dc": 13, "aoe": "5 ft radius", "trigger": TriggerType.TOUCH, "reset": ResetType.NO_RESET},
    # CR 3
    {"name": "Glyph of Warding (Blast)", "cr": 3.0, "search_dc": 27, "disable_dc": 27, "spell_effect": "glyph of warding", "caster_level": 5, "save_dc": 14, "aoe": "5 ft radius", "trigger": TriggerType.LOCATION, "reset": ResetType.NO_RESET},
    # CR 4
    {"name": "Explosive Runes", "cr": 4.0, "search_dc": 28, "disable_dc": 28, "spell_effect": "explosive runes", "caster_level": 6, "save_dc": 15, "aoe": "10 ft radius", "trigger": TriggerType.TOUCH, "reset": ResetType.NO_RESET},
    # CR 5
    {"name": "Symbol of Pain", "cr": 5.0, "search_dc": 29, "disable_dc": 29, "spell_effect": "symbol of pain", "caster_level": 9, "save_dc": 17, "aoe": "60 ft radius", "trigger": TriggerType.VISUAL, "reset": ResetType.NO_RESET},
    # CR 6
    {"name": "Symbol of Sleep", "cr": 6.0, "search_dc": 30, "disable_dc": 30, "spell_effect": "symbol of sleep", "caster_level": 9, "save_dc": 17, "aoe": "60 ft radius", "trigger": TriggerType.VISUAL, "reset": ResetType.NO_RESET},
    {"name": "Programmed Illusion Trap", "cr": 6.0, "search_dc": 30, "disable_dc": 30, "spell_effect": "programmed illusion", "caster_level": 11, "save_dc": None, "aoe": None, "trigger": TriggerType.VISUAL, "reset": ResetType.AUTOMATIC},
    # CR 7
    {"name": "Symbol of Fear", "cr": 7.0, "search_dc": 31, "disable_dc": 31, "spell_effect": "symbol of fear", "caster_level": 11, "save_dc": 19, "aoe": "60 ft radius", "trigger": TriggerType.VISUAL, "reset": ResetType.NO_RESET},
    # CR 8
    {"name": "Glyph of Warding (Spell)", "cr": 8.0, "search_dc": 31, "disable_dc": 31, "spell_effect": "glyph of warding (spell)", "caster_level": 15, "save_dc": 22, "aoe": "5 ft radius", "trigger": TriggerType.LOCATION, "reset": ResetType.NO_RESET},
    # CR 9
    {"name": "Symbol of Insanity", "cr": 9.0, "search_dc": 34, "disable_dc": 34, "spell_effect": "symbol of insanity", "caster_level": 16, "save_dc": 22, "aoe": "60 ft radius", "trigger": TriggerType.VISUAL, "reset": ResetType.NO_RESET},
    # CR 10
    {"name": "Symbol of Death", "cr": 10.0, "search_dc": 35, "disable_dc": 35, "spell_effect": "symbol of death", "caster_level": 17, "save_dc": 23, "aoe": "60 ft radius", "trigger": TriggerType.VISUAL, "reset": ResetType.NO_RESET},
]


def generate_magical_trap(cr: float, rng: _random.Random | None = None) -> MagicalTrap:
    """Generate a magical trap of approximately the given CR per DMG Chapter 4."""
    if rng is None:
        rng = _random.Random()

    candidates = [t for t in _MAGICAL_TRAP_TEMPLATES if abs(t["cr"] - cr) <= 1.0]
    if not candidates:
        candidates = [min(_MAGICAL_TRAP_TEMPLATES, key=lambda t: abs(t["cr"] - cr))]

    template = rng.choice(candidates)
    return MagicalTrap(
        name=template["name"],
        cr=template["cr"],
        trap_type=TrapType.MAGIC,
        trigger=template["trigger"],
        reset=template["reset"],
        search_dc=template["search_dc"],
        disable_dc=template["disable_dc"],
        spell_effect=template["spell_effect"],
        caster_level=template["caster_level"],
        save_dc=template["save_dc"],
        aoe=template["aoe"],
    )


# ---------------------------------------------------------------------------
# T-047 Room Population Roller
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class RoomContents:
    monster: bool
    trap: bool
    treasure: bool
    empty: bool


def roll_room_contents(dungeon_level: int, rng: _random.Random | None = None) -> RoomContents:
    """Roll room contents for a dungeon room per DMG Chapter 4.

    Level 1 probabilities:
      Monster: 30%, Trap: 20%, Treasure: 10%, Empty: 40%
    Deeper levels increase monster/trap probability.
    """
    if rng is None:
        rng = _random.Random()

    monster_pct = min(30 + (dungeon_level - 1) * 3, 55)
    trap_pct = min(20 + (dungeon_level - 1) * 2, 35)
    treasure_pct = 10

    monster = rng.randint(1, 100) <= monster_pct
    trap = rng.randint(1, 100) <= trap_pct
    has_treasure = rng.randint(1, 100) <= treasure_pct + (5 if monster else 0)
    empty = not monster and not trap and not has_treasure

    return RoomContents(monster=monster, trap=trap, treasure=has_treasure, empty=empty)


# ---------------------------------------------------------------------------
# T-057 Trap Hoard Integrator
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class DungeonLevel:
    rooms: list[RoomContents]


def generate_dungeon_level(
    dungeon_level: int,
    num_rooms: int,
    rng: _random.Random | None = None,
) -> DungeonLevel:
    """Generate a full dungeon level with rooms, traps, and population.

    Trap CR = dungeon_level + randint(-1, 2), clamped to [0.5, 10].
    Mechanical/magical trap ratio: 60/40 at level <=5, 40/60 at level >=6.
    """
    if rng is None:
        rng = _random.Random()

    rooms = []
    for _ in range(num_rooms):
        contents = roll_room_contents(dungeon_level, rng)
        if contents.trap:
            cr = float(dungeon_level) + rng.randint(-1, 2)
            cr = max(0.5, min(10.0, cr))
            use_mechanical = rng.random() < (0.60 if dungeon_level <= 5 else 0.40)
            if use_mechanical:
                generate_mechanical_trap(cr, rng)
            else:
                generate_magical_trap(cr, rng)
            contents = RoomContents(
                monster=contents.monster,
                trap=True,
                treasure=contents.treasure,
                empty=False,
            )
        rooms.append(contents)

    return DungeonLevel(rooms=rooms)
