"""
src/rules_engine/magic.py
-------------------------
D&D 3.5e Spell definitions and registry for the Vancian spellcasting engine.

Provides a :class:`Spell` dataclass for canonical spell data and a
:class:`SpellRegistry` to store/look up spells efficiently.

Memory Optimisation
~~~~~~~~~~~~~~~~~~~
Uses ``@dataclass(slots=True)`` per project standard.

Usage::

    from src.rules_engine.magic import Spell, SpellRegistry

    registry = SpellRegistry()
    mm = registry.get("Magic Missile")
    print(mm.school)  # "Evocation"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class SpellSchool(Enum):
    """The eight schools of magic in D&D 3.5e."""

    ABJURATION = "Abjuration"
    CONJURATION = "Conjuration"
    DIVINATION = "Divination"
    ENCHANTMENT = "Enchantment"
    EVOCATION = "Evocation"
    ILLUSION = "Illusion"
    NECROMANCY = "Necromancy"
    TRANSMUTATION = "Transmutation"


class SpellComponent(Enum):
    """Standard spell components."""

    VERBAL = "V"
    SOMATIC = "S"
    MATERIAL = "M"
    FOCUS = "F"
    DIVINE_FOCUS = "DF"
    XP = "XP"


# ---------------------------------------------------------------------------
# Spell dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Spell:
    """Canonical D&D 3.5e spell definition.

    Attributes:
        name:             Spell name (e.g. "Magic Missile").
        level:            Spell level (0–9).
        school:           School of magic.
        components:       Required casting components.
        range:            Range description (e.g. "Medium (100 ft. + 10 ft./level)").
        duration:         Duration description (e.g. "Instantaneous").
        effect_callback:  Optional callable implementing the spell's mechanical
                          effect.  Signature: ``(caster, target, caster_level) -> Any``.
        description:      Flavour/rules text summary.
        subschool:        Optional subschool (e.g. "Creation", "Force").
        descriptor:       Optional descriptor tags (e.g. ["Force"], ["Mind-Affecting"]).
    """

    name: str
    level: int
    school: SpellSchool
    components: List[SpellComponent] = field(default_factory=list)
    range: str = "Close (25 ft. + 5 ft./2 levels)"
    duration: str = "Instantaneous"
    effect_callback: Optional[Callable[..., Any]] = field(default=None, repr=False)
    description: str = ""
    subschool: str = ""
    descriptor: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# SpellRegistry
# ---------------------------------------------------------------------------

class SpellRegistry:
    """Stores and retrieves :class:`Spell` definitions by name and level.

    Designed for efficient lookup in a large-scale simulation environment
    (optimised for 64GB RAM with potentially thousands of spell definitions).

    Usage::

        registry = SpellRegistry()
        registry.register(my_spell)
        spell = registry.get("Magic Missile")
        evocations = registry.get_by_school(SpellSchool.EVOCATION)
        level_1 = registry.get_by_level(1)
    """

    def __init__(self) -> None:
        self._by_name: Dict[str, Spell] = {}
        self._by_level: Dict[int, List[Spell]] = {i: [] for i in range(10)}
        self._by_school: Dict[SpellSchool, List[Spell]] = {
            school: [] for school in SpellSchool
        }

    def register(self, spell: Spell) -> None:
        """Register a spell in the registry.

        Args:
            spell: The spell definition to add.

        Raises:
            ValueError: If a spell with the same name is already registered.
        """
        if spell.name in self._by_name:
            raise ValueError(f"Spell '{spell.name}' is already registered.")
        self._by_name[spell.name] = spell
        self._by_level[spell.level].append(spell)
        self._by_school[spell.school].append(spell)

    def get(self, name: str) -> Optional[Spell]:
        """Look up a spell by exact name.

        Args:
            name: Exact spell name (case-sensitive).

        Returns:
            The :class:`Spell` if found, else ``None``.
        """
        return self._by_name.get(name)

    def get_by_level(self, level: int) -> List[Spell]:
        """Return all spells of a given level.

        Args:
            level: Spell level (0–9).

        Returns:
            List of spells at that level (may be empty).
        """
        return list(self._by_level.get(level, []))

    def get_by_school(self, school: SpellSchool) -> List[Spell]:
        """Return all spells belonging to a school.

        Args:
            school: The :class:`SpellSchool` to filter by.

        Returns:
            List of spells in that school (may be empty).
        """
        return list(self._by_school.get(school, []))

    @property
    def count(self) -> int:
        """Total number of registered spells."""
        return len(self._by_name)

    def __contains__(self, name: str) -> bool:
        return name in self._by_name

    def __len__(self) -> int:
        return len(self._by_name)


# ---------------------------------------------------------------------------
# Default spell definitions (SRD)
# ---------------------------------------------------------------------------

def _magic_missile_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Magic Missile: 1d4+1 force damage per missile.

    Missiles = min(5, (caster_level + 1) // 2).
    Auto-hits (no attack roll required).
    """
    num_missiles = min(5, (caster_level + 1) // 2)
    return {
        "damage_type": "Force",
        "num_missiles": num_missiles,
        "damage_per_missile": "1d4+1",
        "auto_hit": True,
    }


def _mage_armor_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Mage Armor: +4 armor bonus to AC for 1 hour/level.

    The armor bonus applies against incorporeal touch attacks since
    it is a force effect.
    """
    return {
        "ac_bonus": 4,
        "bonus_type": "armor",
        "duration_hours": caster_level,
        "force_effect": True,
    }


MAGIC_MISSILE = Spell(
    name="Magic Missile",
    level=1,
    school=SpellSchool.EVOCATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Medium (100 ft. + 10 ft./level)",
    duration="Instantaneous",
    effect_callback=_magic_missile_effect,
    description=(
        "A missile of magical energy darts forth from your fingertip and "
        "strikes its target, dealing 1d4+1 points of force damage."
    ),
    subschool="",
    descriptor=["Force"],
)

MAGE_ARMOR = Spell(
    name="Mage Armor",
    level=1,
    school=SpellSchool.CONJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.FOCUS],
    range="Touch",
    duration="1 hour/level",
    effect_callback=_mage_armor_effect,
    description=(
        "An invisible but tangible field of force surrounds the subject "
        "of a mage armor spell, providing a +4 armor bonus to AC."
    ),
    subschool="Creation",
    descriptor=["Force"],
)


# ---------------------------------------------------------------------------
# Divine spell effect callbacks
# ---------------------------------------------------------------------------

def _cure_light_wounds_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Cure Light Wounds: Cures 1d8 + caster level (max +5) hit points.

    Positive energy heals living creatures, harms undead.
    """
    bonus = min(caster_level, 5)
    return {
        "healing": f"1d8+{bonus}",
        "max_bonus": bonus,
        "harms_undead": True,
        "energy_type": "positive",
    }


def _bless_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Bless: +1 morale bonus on attack rolls and saves vs. fear.

    Affects all allies within 50 ft. burst centred on caster.
    Duration: 1 min/level.
    """
    return {
        "attack_bonus": 1,
        "bonus_type": "morale",
        "save_vs_fear_bonus": 1,
        "area": "50 ft. burst",
        "duration_minutes": caster_level,
    }


def _bane_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Bane: -1 morale penalty on attack rolls and saves vs. fear for enemies.

    Affects all enemies within 50 ft. burst centred on caster.
    Duration: 1 min/level.
    """
    return {
        "attack_penalty": -1,
        "penalty_type": "morale",
        "save_vs_fear_penalty": -1,
        "area": "50 ft. burst",
        "duration_minutes": caster_level,
    }


# ---------------------------------------------------------------------------
# Divine spell definitions (SRD)
# ---------------------------------------------------------------------------

CURE_LIGHT_WOUNDS = Spell(
    name="Cure Light Wounds",
    level=1,
    school=SpellSchool.CONJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Touch",
    duration="Instantaneous",
    effect_callback=_cure_light_wounds_effect,
    description=(
        "When laying your hand upon a living creature, you channel positive "
        "energy that cures 1d8 points of damage +1 per caster level (maximum +5)."
    ),
    subschool="Healing",
    descriptor=[],
)

BLESS = Spell(
    name="Bless",
    level=1,
    school=SpellSchool.ENCHANTMENT,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.DIVINE_FOCUS],
    range="50 ft.",
    duration="1 min./level",
    effect_callback=_bless_effect,
    description=(
        "Bless fills your allies with courage. Each ally gains a +1 morale "
        "bonus on attack rolls and on saving throws against fear effects."
    ),
    subschool="Compulsion",
    descriptor=["Mind-Affecting"],
)

BANE = Spell(
    name="Bane",
    level=1,
    school=SpellSchool.ENCHANTMENT,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.DIVINE_FOCUS],
    range="50 ft.",
    duration="1 min./level",
    effect_callback=_bane_effect,
    description=(
        "Bane fills your enemies with fear and doubt. Each affected creature "
        "takes a -1 penalty on attack rolls and a -1 penalty on saving throws "
        "against fear effects."
    ),
    subschool="Compulsion",
    descriptor=["Fear", "Mind-Affecting"],
)


# ---------------------------------------------------------------------------
# Cure spell lookup table for spontaneous casting (indexed by spell level)
# ---------------------------------------------------------------------------

CURE_SPELLS: Dict[int, str] = {
    1: "Cure Light Wounds",
    2: "Cure Moderate Wounds",
    3: "Cure Serious Wounds",
    4: "Cure Critical Wounds",
    5: "Cure Light Wounds, Mass",
    6: "Cure Moderate Wounds, Mass",
    7: "Cure Serious Wounds, Mass",
    8: "Cure Critical Wounds, Mass",
    9: "Heal, Mass",
}


def create_default_registry() -> SpellRegistry:
    """Create a :class:`SpellRegistry` pre-loaded with SRD core spells.

    Returns:
        A registry containing Magic Missile, Mage Armor, Cure Light Wounds,
        Bless, Bane, and other foundational spells.
    """
    registry = SpellRegistry()
    registry.register(MAGIC_MISSILE)
    registry.register(MAGE_ARMOR)
    registry.register(CURE_LIGHT_WOUNDS)
    registry.register(BLESS)
    registry.register(BANE)
    return registry
