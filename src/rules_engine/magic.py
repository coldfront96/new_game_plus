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

# ---------------------------------------------------------------------------
# Sorcerer "instinctive" spell definitions (SRD)
# ---------------------------------------------------------------------------

def _shield_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Shield: Invisible disc provides +4 shield bonus to AC.

    Blocks Magic Missiles. Duration: 1 min./level.
    """
    return {
        "ac_bonus": 4,
        "bonus_type": "shield",
        "blocks_magic_missile": True,
        "duration_minutes": caster_level,
        "force_effect": True,
    }


def _burning_hands_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Burning Hands: 1d4/level fire damage (max 5d4) in a 15-ft. cone.

    Reflex save for half.
    """
    dice = min(caster_level, 5)
    return {
        "damage": f"{dice}d4",
        "damage_type": "Fire",
        "area": "15 ft. cone",
        "save": "Reflex half",
        "max_dice": 5,
    }


SHIELD = Spell(
    name="Shield",
    level=1,
    school=SpellSchool.ABJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Personal",
    duration="1 min./level",
    effect_callback=_shield_effect,
    description=(
        "Shield creates an invisible, tower shield-sized mobile disk of "
        "force that hovers in front of you. It negates magic missile attacks "
        "directed at you and provides a +4 shield bonus to AC."
    ),
    subschool="",
    descriptor=["Force"],
)

BURNING_HANDS = Spell(
    name="Burning Hands",
    level=1,
    school=SpellSchool.EVOCATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="15 ft.",
    duration="Instantaneous",
    effect_callback=_burning_hands_effect,
    description=(
        "A cone of searing flame shoots from your fingertips. Any creature "
        "in the area of the flames takes 1d4 points of fire damage per "
        "caster level (maximum 5d4)."
    ),
    subschool="",
    descriptor=["Fire"],
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


# ---------------------------------------------------------------------------
# Bard spell effect callbacks
# ---------------------------------------------------------------------------

def _sleep_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Sleep: Causes creatures with low HD to fall into a magical slumber.

    Affects 4 HD of creatures. Does not affect undead or creatures with
    more than 4 HD.
    """
    return {
        "hit_dice_affected": 4,
        "duration_minutes": caster_level,
        "area": "Close (25 ft. + 5 ft./2 levels)",
        "save": "Will negates",
        "immune": ["undead", "creatures with 5+ HD"],
    }


def _identify_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Identify: Determines properties of a magic item.

    Reveals all magic properties of a single item, including how to
    activate the item's functions (if appropriate).
    """
    return {
        "reveals_properties": True,
        "reveals_activation": True,
        "items_examined": 1,
        "duration": "Instantaneous",
        "material_cost_gp": 100,
    }


def _ghost_sound_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Ghost Sound: Figment sounds.

    Creates the volume of sound that a group of four humans per caster
    level could make (max 20 humans at caster level 5).
    """
    humans_equivalent = min(caster_level * 4, 20)
    return {
        "volume": f"{humans_equivalent} humans",
        "duration_rounds": caster_level,
        "save": "Will disbelief",
        "figment": True,
    }


# ---------------------------------------------------------------------------
# Bard spell definitions (SRD)
# ---------------------------------------------------------------------------

SLEEP = Spell(
    name="Sleep",
    level=1,
    school=SpellSchool.ENCHANTMENT,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="Medium (100 ft. + 10 ft./level)",
    duration="1 min./level",
    effect_callback=_sleep_effect,
    description=(
        "A sleep spell causes a magical slumber to come upon 4 Hit Dice "
        "of creatures. Creatures with the fewest HD are affected first."
    ),
    subschool="Compulsion",
    descriptor=["Mind-Affecting"],
)

IDENTIFY = Spell(
    name="Identify",
    level=1,
    school=SpellSchool.DIVINATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="Touch",
    duration="Instantaneous",
    effect_callback=_identify_effect,
    description=(
        "The spell determines all magic properties of a single magic item, "
        "including how to activate those functions (if appropriate), and how "
        "many charges are left (if any)."
    ),
    subschool="",
    descriptor=[],
)

GHOST_SOUND = Spell(
    name="Ghost Sound",
    level=0,
    school=SpellSchool.ILLUSION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="1 round/level",
    effect_callback=_ghost_sound_effect,
    description=(
        "Ghost sound allows you to create a volume of sound that rises, "
        "recedes, approaches, or remains at a fixed place. You choose what "
        "type of sound ghost sound creates when casting it."
    ),
    subschool="Figment",
    descriptor=[],
)


def create_default_registry() -> SpellRegistry:
    """Create a :class:`SpellRegistry` pre-loaded with SRD core spells.

    Returns:
        A registry containing Magic Missile, Mage Armor, Shield,
        Burning Hands, Cure Light Wounds, Bless, Bane, and other
        foundational spells including Bard-specific spells.
    """
    registry = SpellRegistry()
    registry.register(MAGIC_MISSILE)
    registry.register(MAGE_ARMOR)
    registry.register(SHIELD)
    registry.register(BURNING_HANDS)
    registry.register(CURE_LIGHT_WOUNDS)
    registry.register(BLESS)
    registry.register(BANE)
    registry.register(SLEEP)
    registry.register(IDENTIFY)
    registry.register(GHOST_SOUND)
    return registry
