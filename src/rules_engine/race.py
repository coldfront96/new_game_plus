"""
src/rules_engine/race.py
------------------------
Racial Trait Engine for D&D 3.5e SRD.

Defines a :class:`Race` dataclass holding canonical stat modifiers and
special abilities for each core race, plus a :class:`RaceRegistry` for
look-up by name.

Memory Optimisation
~~~~~~~~~~~~~~~~~~~
Uses ``@dataclass(slots=True)`` to eliminate per-instance ``__dict__``
overhead.

Usage::

    from src.rules_engine.race import RaceRegistry

    elf = RaceRegistry.get("Elf")
    print(elf.stat_modifiers)   # {"dexterity": 2, "constitution": -2}
    print(elf.special_abilities)  # ["Low-Light Vision", "Elven Immunities", ...]
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


# ---------------------------------------------------------------------------
# Race dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Race:
    """A playable race definition following the 3.5e SRD.

    Attributes:
        name:             Race name (e.g. ``"Elf"``).
        stat_modifiers:   Mapping of ability name → signed modifier
                          (e.g. ``{"dexterity": 2, "constitution": -2}``).
        special_abilities: List of trait/ability names (e.g. ``["Darkvision"]``).
        base_speed:        Base land speed in feet (default 30).
        size:              Size category string (default ``"Medium"``).
    """

    name: str
    stat_modifiers: Dict[str, int]
    special_abilities: List[str]
    base_speed: int = 30
    size: str = "Medium"


# ---------------------------------------------------------------------------
# RaceRegistry
# ---------------------------------------------------------------------------

class RaceRegistry:
    """Registry of canonical 3.5e SRD races.

    All data is sourced from the D&D 3.5e System Reference Document.

    Usage::

        race = RaceRegistry.get("Dwarf")
        bonus = race.stat_modifiers.get("constitution", 0)  # +2
    """

    _races: Dict[str, Race] = {
        # -------------------------------------------------------------------
        # Human: No fixed ability modifiers; gains a bonus feat and extra
        # skill points.
        # -------------------------------------------------------------------
        "Human": Race(
            name="Human",
            stat_modifiers={},
            special_abilities=["Bonus Feat", "Bonus Skill Points"],
            base_speed=30,
            size="Medium",
        ),

        # -------------------------------------------------------------------
        # Elf: +2 DEX, −2 CON.
        # Traits: Low-Light Vision, Elven Immunities (sleep immunity,
        #         +2 vs. enchantments), Keen Senses (+2 Listen/Search/Spot),
        #         Weapon Proficiency (longsword, rapier, longbow, shortbow).
        # -------------------------------------------------------------------
        "Elf": Race(
            name="Elf",
            stat_modifiers={"dexterity": 2, "constitution": -2},
            special_abilities=[
                "Low-Light Vision",
                "Elven Immunities",
                "Keen Senses",
                "Weapon Proficiency (Elven)",
            ],
            base_speed=30,
            size="Medium",
        ),

        # -------------------------------------------------------------------
        # Dwarf: +2 CON, −2 CHA.
        # Traits: Darkvision 60 ft, Stonecunning, Weapon Familiarity
        #         (dwarven waraxe/urgrosh), Stability (+4 vs. bull-rush/trip),
        #         +2 vs. poison, +2 vs. spells/SLAs, +1 attack vs. orcs/goblinoids,
        #         +4 dodge vs. giants, +2 Appraise/Craft (stone or metal).
        # -------------------------------------------------------------------
        "Dwarf": Race(
            name="Dwarf",
            stat_modifiers={"constitution": 2, "charisma": -2},
            special_abilities=[
                "Darkvision",
                "Stonecunning",
                "Weapon Familiarity (Dwarven)",
                "Stability",
                "Poison Resistance",
                "Spell Resistance",
            ],
            base_speed=20,
            size="Medium",
        ),

        # -------------------------------------------------------------------
        # Halfling: +2 DEX, −2 STR.
        # Traits: Small size, +2 climb/jump/listen/move silently,
        #         +1 all saving throws, +2 saves vs. fear, +1 attack with
        #         thrown weapons and slings.
        # -------------------------------------------------------------------
        "Halfling": Race(
            name="Halfling",
            stat_modifiers={"dexterity": 2, "strength": -2},
            special_abilities=[
                "Small Size",
                "Lucky",
                "Fearless",
                "Keen Senses",
                "Throwing Proficiency",
            ],
            base_speed=20,
            size="Small",
        ),

        # -------------------------------------------------------------------
        # Orc: +4 STR, −2 INT, −2 WIS, −2 CHA.
        # Traits: Darkvision 60 ft, Light Sensitivity (dazzled in bright),
        #         Ferocity (fight while disabled/dying).
        # -------------------------------------------------------------------
        "Orc": Race(
            name="Orc",
            stat_modifiers={
                "strength": 4,
                "intelligence": -2,
                "wisdom": -2,
                "charisma": -2,
            },
            special_abilities=[
                "Darkvision",
                "Light Sensitivity",
                "Ferocity",
            ],
            base_speed=30,
            size="Medium",
        ),

        # -------------------------------------------------------------------
        # Gnome: +2 CON, −2 STR.
        # Traits: Small size, Low-Light Vision, +1 attack vs. kobolds and
        #         goblinoids, +4 dodge AC vs. giants, +2 Listen, +2 Craft
        #         (alchemy), spell-like abilities (dancing lights, ghost sound,
        #         prestidigitation), +1 DC to illusion spells.
        # -------------------------------------------------------------------
        "Gnome": Race(
            name="Gnome",
            stat_modifiers={"constitution": 2, "strength": -2},
            special_abilities=[
                "Small Size",
                "Low-Light Vision",
                "Weapon Familiarity (Gnome)",
                "Keen Senses",
                "Illusion Aptitude",
                "Spell-Like Abilities",
            ],
            base_speed=20,
            size="Small",
        ),

        # -------------------------------------------------------------------
        # Half-Elf: No fixed ability modifiers.
        # Traits: Low-Light Vision, immunity to sleep spells, +2 saves vs.
        #         enchantments, +1 Diplomacy and Gather Information, Elven
        #         Blood (counts as both elf and human for prerequisites).
        # -------------------------------------------------------------------
        "Half-Elf": Race(
            name="Half-Elf",
            stat_modifiers={},
            special_abilities=[
                "Low-Light Vision",
                "Elven Immunities",
                "Adaptability",
                "Elven Blood",
                "Bonus Skill Points",
            ],
            base_speed=30,
            size="Medium",
        ),

        # -------------------------------------------------------------------
        # Half-Orc: +2 STR, −2 INT, −2 CHA.
        # Traits: Darkvision 60 ft, Orc Blood (counts as both orc and human
        #         for prerequisites).
        # -------------------------------------------------------------------
        "Half-Orc": Race(
            name="Half-Orc",
            stat_modifiers={"strength": 2, "intelligence": -2, "charisma": -2},
            special_abilities=[
                "Darkvision",
                "Orc Blood",
            ],
            base_speed=30,
            size="Medium",
        ),
    }

    @classmethod
    def get(cls, name: str) -> Race:
        """Return the :class:`Race` for *name*, defaulting to ``Human``.

        Args:
            name: Race name (case-sensitive, e.g. ``"Elf"``).

        Returns:
            The matching :class:`Race`, or the Human race if not found.
        """
        return cls._races.get(name, cls._races["Human"])

    @classmethod
    def all_names(cls) -> List[str]:
        """Return a sorted list of all registered race names."""
        return sorted(cls._races.keys())
