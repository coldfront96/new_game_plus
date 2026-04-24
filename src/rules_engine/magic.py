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
# Summon Nature's Ally spell lookup table for Druid spontaneous casting
# ---------------------------------------------------------------------------

SUMMON_NATURES_ALLY_SPELLS: Dict[int, str] = {
    1: "Summon Nature's Ally I",
    2: "Summon Nature's Ally II",
    3: "Summon Nature's Ally III",
    4: "Summon Nature's Ally IV",
    5: "Summon Nature's Ally V",
    6: "Summon Nature's Ally VI",
    7: "Summon Nature's Ally VII",
    8: "Summon Nature's Ally VIII",
    9: "Summon Nature's Ally IX",
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


def _summon_natures_ally_i_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Summon Nature's Ally I: Summons a 1st-level creature to fight for the caster.

    The summoned creature appears where the caster designates and acts on
    the caster's turn. Duration: 1 round/level.
    """
    return {
        "summoned_creature_level": 1,
        "duration_rounds": caster_level,
        "alignment_restrictions": "within one step of caster's alignment",
    }


SUMMON_NATURES_ALLY_I = Spell(
    name="Summon Nature's Ally I",
    level=1,
    school=SpellSchool.CONJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.DIVINE_FOCUS],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="1 round/level",
    effect_callback=_summon_natures_ally_i_effect,
    description=(
        "This spell summons a natural creature. It appears where you designate "
        "and acts immediately, on your turn. It attacks your opponents to the best "
        "of its ability. Duration: 1 round/level."
    ),
    subschool="Summoning",
    descriptor=[],
)


# ---------------------------------------------------------------------------
# Level 0 (cantrip) effect callbacks – Phase 1 additions
# ---------------------------------------------------------------------------

def _detect_magic_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Detect Magic: detects spell auras within Close range."""
    return {
        "range": "Close (25 ft. + 5 ft./2 levels)",
        "duration": f"Concentration up to {caster_level} min.",
        "detects": "spell auras",
        "save": "none",
    }


def _ray_of_frost_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Ray of Frost: ranged touch attack, 1d3 cold damage."""
    return {
        "damage": "1d3",
        "damage_type": "Cold",
        "attack": "ranged touch",
        "save": "none",
    }


def _resistance_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Resistance: +1 resistance bonus on saving throws for 1 minute."""
    return {
        "save_bonus": 1,
        "bonus_type": "resistance",
        "duration_minutes": 1,
    }


def _mage_hand_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Mage Hand: telekinetically move object up to 5 lb."""
    return {
        "max_weight_lb": 5,
        "range": "Close (25 ft. + 5 ft./2 levels)",
        "duration": "Concentration",
    }


def _read_magic_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Read Magic: decipher magical writings for 10 min/level."""
    return {
        "deciphers_magical_writing": True,
        "duration_minutes": caster_level * 10,
    }


def _acid_splash_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Acid Splash: ranged touch attack, 1d3 acid damage."""
    return {
        "damage": "1d3",
        "damage_type": "Acid",
        "attack": "ranged touch",
        "save": "none",
    }


def _daze_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Daze: humanoid up to 4 HD dazed 1 round (Will negates)."""
    return {
        "condition": "dazed",
        "duration_rounds": 1,
        "max_hd": 4,
        "target": "humanoid",
        "save": "Will negates",
    }


def _light_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Light: object sheds 20-ft bright + 20-ft shadowy light."""
    return {
        "bright_light_radius_ft": 20,
        "shadowy_light_radius_ft": 20,
        "duration_minutes": caster_level * 10,
    }


# ---------------------------------------------------------------------------
# Level 0 spell constants – Phase 1 additions
# ---------------------------------------------------------------------------

DETECT_MAGIC = Spell(
    name="Detect Magic",
    level=0,
    school=SpellSchool.DIVINATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="Concentration, up to 1 min./level",
    effect_callback=_detect_magic_effect,
    description=(
        "You detect magical auras. The amount of information revealed depends "
        "on how long you study a particular area or subject."
    ),
    subschool="",
    descriptor=[],
)

RAY_OF_FROST = Spell(
    name="Ray of Frost",
    level=0,
    school=SpellSchool.EVOCATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="Instantaneous",
    effect_callback=_ray_of_frost_effect,
    description=(
        "A ray of freezing air and ice projects from your pointing finger. "
        "You must succeed on a ranged touch attack with the ray to deal 1d3 "
        "points of cold damage."
    ),
    subschool="",
    descriptor=["Cold"],
)

RESISTANCE = Spell(
    name="Resistance",
    level=0,
    school=SpellSchool.ABJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="Touch",
    duration="1 minute",
    effect_callback=_resistance_effect,
    description=(
        "You imbue the subject with magical energy that protects it from harm, "
        "granting it a +1 resistance bonus on saves."
    ),
    subschool="",
    descriptor=[],
)

MAGE_HAND = Spell(
    name="Mage Hand",
    level=0,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="Concentration",
    effect_callback=_mage_hand_effect,
    description=(
        "You point your finger at an object and can lift it and move it at will "
        "from a distance. The object can weigh no more than 5 pounds."
    ),
    subschool="",
    descriptor=[],
)

READ_MAGIC = Spell(
    name="Read Magic",
    level=0,
    school=SpellSchool.DIVINATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.FOCUS],
    range="Personal",
    duration="10 min./level",
    effect_callback=_read_magic_effect,
    description=(
        "By means of read magic, you can decipher magical inscriptions on "
        "objects—books, scrolls, weapons, and the like—that would otherwise "
        "be unintelligible."
    ),
    subschool="",
    descriptor=[],
)

ACID_SPLASH = Spell(
    name="Acid Splash",
    level=0,
    school=SpellSchool.CONJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="Instantaneous",
    effect_callback=_acid_splash_effect,
    description=(
        "You fire a small orb of acid at the target. You must succeed on a "
        "ranged touch attack to hit your target. The orb deals 1d3 points of "
        "acid damage."
    ),
    subschool="Creation",
    descriptor=["Acid"],
)

DAZE = Spell(
    name="Daze",
    level=0,
    school=SpellSchool.ENCHANTMENT,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="1 round",
    effect_callback=_daze_effect,
    description=(
        "This enchantment clouds the mind of a humanoid creature with 4 or "
        "fewer Hit Dice, causing it to become dazed."
    ),
    subschool="Compulsion",
    descriptor=["Mind-Affecting"],
)

LIGHT = Spell(
    name="Light",
    level=0,
    school=SpellSchool.EVOCATION,
    components=[SpellComponent.VERBAL, SpellComponent.MATERIAL],
    range="Touch",
    duration="10 min./level",
    effect_callback=_light_effect,
    description=(
        "This spell causes a touched object to glow like a torch, shedding "
        "bright light in a 20-foot radius and dim light for an additional 20 feet."
    ),
    subschool="",
    descriptor=[],
)


# ---------------------------------------------------------------------------
# Level 1 effect callbacks – Phase 1 additions
# ---------------------------------------------------------------------------

def _charm_person_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Charm Person: humanoid is friendly for 1 hour/level (Will negates)."""
    return {
        "condition": "charmed",
        "target": "humanoid",
        "duration_hours": caster_level,
        "save": "Will negates",
    }


def _color_spray_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Color Spray: area effect – unconscious/blinded/stunned by HD."""
    return {
        "area": "15-ft cone",
        "effects": {
            "2_hd_or_less": "unconscious 2d4 rounds",
            "3_to_4_hd": "blinded 1d4 rounds",
            "5_plus_hd": "stunned 1 round",
        },
        "save": "Will negates",
    }


def _feather_fall_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Feather Fall: targets fall at 60 ft/round, no damage."""
    return {
        "fall_rate_ft_per_round": 60,
        "damage_on_landing": 0,
        "duration_rounds": caster_level,
    }


def _grease_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Grease: 10-ft square or one object, Reflex save or fall."""
    return {
        "area": "10-ft square",
        "duration_rounds": caster_level,
        "save": "Reflex or fall",
    }


def _ray_of_enfeeblement_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Ray of Enfeeblement: ranged touch, 1d6+min(CL//2,5) Str penalty."""
    penalty = f"1d6+{min(caster_level // 2, 5)}"
    return {
        "str_penalty": penalty,
        "attack": "ranged touch",
        "save": "none",
        "duration_rounds": caster_level,
    }


def _true_strike_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """True Strike: +20 insight bonus on next single attack roll."""
    return {
        "attack_bonus": 20,
        "bonus_type": "insight",
        "applies_to": "next single attack roll",
        "ignore_miss_chance": True,
    }


def _cause_fear_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Cause Fear: creature with 5 or fewer HD becomes frightened (Will negates)."""
    return {
        "condition": "frightened",
        "max_hd": 5,
        "duration_rounds": "1d4",
        "save": "Will negates",
    }


def _enlarge_person_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Enlarge Person: humanoid grows one size (STR +2, DEX -2, -1 attack/AC)."""
    return {
        "target": "humanoid",
        "size_change": "+1 size category",
        "str_bonus": 2,
        "dex_penalty": -2,
        "attack_penalty": -1,
        "ac_penalty": -1,
        "duration_minutes": caster_level,
    }


# ---------------------------------------------------------------------------
# Level 1 spell constants – Phase 1 additions
# ---------------------------------------------------------------------------

CHARM_PERSON = Spell(
    name="Charm Person",
    level=1,
    school=SpellSchool.ENCHANTMENT,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="1 hour/level",
    effect_callback=_charm_person_effect,
    description=(
        "This charm makes a humanoid creature regard you as its trusted friend "
        "and ally. The spell does not enable you to control the charmed person "
        "as if it were an automaton."
    ),
    subschool="Compulsion",
    descriptor=["Mind-Affecting"],
)

COLOR_SPRAY = Spell(
    name="Color Spray",
    level=1,
    school=SpellSchool.ILLUSION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="15-ft cone",
    duration="Instantaneous",
    effect_callback=_color_spray_effect,
    description=(
        "A vivid cone of clashing colors springs from your hand, causing "
        "creatures to become stunned, blinded, or unconscious."
    ),
    subschool="Pattern",
    descriptor=["Mind-Affecting"],
)

FEATHER_FALL = Spell(
    name="Feather Fall",
    level=1,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="Until landing or 1 round/level",
    effect_callback=_feather_fall_effect,
    description=(
        "The affected creatures or objects fall slowly. Feather fall instantly "
        "changes the rate at which the targets fall to a mere 60 feet per round "
        "(equivalent to the end of a fall from a few feet), with no damage upon "
        "landing while the spell is in effect."
    ),
    subschool="",
    descriptor=[],
)

GREASE = Spell(
    name="Grease",
    level=1,
    school=SpellSchool.CONJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="1 round/level",
    effect_callback=_grease_effect,
    description=(
        "A grease spell covers a solid surface with a layer of slippery grease. "
        "Any creature in the area when the spell is cast must make a successful "
        "Reflex save or fall."
    ),
    subschool="Creation",
    descriptor=[],
)

RAY_OF_ENFEEBLEMENT = Spell(
    name="Ray of Enfeeblement",
    level=1,
    school=SpellSchool.NECROMANCY,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="1 round/level",
    effect_callback=_ray_of_enfeeblement_effect,
    description=(
        "A coruscating ray springs from your hand. You must succeed on a ranged "
        "touch attack to strike a target. The subject takes a penalty to Strength "
        "equal to 1d6+1 per two caster levels (maximum 1d6+5)."
    ),
    subschool="",
    descriptor=[],
)

TRUE_STRIKE = Spell(
    name="True Strike",
    level=1,
    school=SpellSchool.DIVINATION,
    components=[SpellComponent.VERBAL, SpellComponent.FOCUS],
    range="Personal",
    duration="See text",
    effect_callback=_true_strike_effect,
    description=(
        "You gain temporary, intuitive insight into the immediate future during "
        "your next attack. Your next single attack roll gains a +20 insight "
        "bonus. Additionally, you are not affected by the miss chance that "
        "applies to attacks made against a concealed target."
    ),
    subschool="",
    descriptor=[],
)

CAUSE_FEAR = Spell(
    name="Cause Fear",
    level=1,
    school=SpellSchool.NECROMANCY,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="1d4 rounds",
    effect_callback=_cause_fear_effect,
    description=(
        "The affected creature becomes frightened. If the subject succeeds on a "
        "Will save, it is shaken for 1 round. Creatures with 6 or more HD are "
        "immune to this spell."
    ),
    subschool="",
    descriptor=["Fear", "Mind-Affecting"],
)

ENLARGE_PERSON = Spell(
    name="Enlarge Person",
    level=1,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="1 min./level",
    effect_callback=_enlarge_person_effect,
    description=(
        "This spell causes instant growth of a humanoid creature, doubling its "
        "height and multiplying its weight by 8. This increase changes the "
        "creature's size category to the next larger one."
    ),
    subschool="",
    descriptor=[],
)


# ---------------------------------------------------------------------------
# Level 2 effect callbacks – Phase 1 additions
# ---------------------------------------------------------------------------

def _scorching_ray_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Scorching Ray: 1+1/4 levels rays (max 3), each 4d6 fire, ranged touch."""
    rays = min(3, 1 + caster_level // 4)
    return {
        "rays": rays,
        "damage_per_ray": "4d6",
        "damage_type": "Fire",
        "attack": "ranged touch",
    }


def _invisibility_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Invisibility: target invisible for 1 min/level or until cast/attack."""
    return {
        "condition": "invisible",
        "duration_minutes": caster_level,
        "ends_on_attack_or_cast": True,
    }


def _mirror_image_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Mirror Image: 1d4+1/3 levels illusory doubles (max 8)."""
    max_images = min(1 + caster_level // 3, 8)
    return {
        "images": "1d4+1",
        "max_images": max_images,
        "duration_minutes": caster_level,
    }


def _web_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Web: 20-ft radius, STR 20 check to break free, 10 min/level."""
    return {
        "area": "20-ft radius spread",
        "str_check_dc": 20,
        "duration_minutes": caster_level * 10,
        "save": "Reflex or entangled",
    }


def _bulls_strength_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Bull's Strength: +4 enhancement bonus to STR for 1 min/level."""
    return {
        "str_bonus": 4,
        "bonus_type": "enhancement",
        "duration_minutes": caster_level,
    }


def _blur_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Blur: 20% miss chance from attacks for 1 min/level."""
    return {
        "miss_chance_percent": 20,
        "duration_minutes": caster_level,
        "concealment": True,
    }


def _resist_energy_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Resist Energy: absorbs 10 points of damage of chosen energy type."""
    return {
        "absorption": 10,
        "energy_types": ["fire", "cold", "acid", "electricity", "sonic"],
        "duration_minutes": caster_level * 10,
    }


def _bears_endurance_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Bear's Endurance: +4 enhancement bonus to CON for 1 min/level."""
    return {
        "con_bonus": 4,
        "bonus_type": "enhancement",
        "duration_minutes": caster_level,
    }


# ---------------------------------------------------------------------------
# Level 2 spell constants – Phase 1 additions
# ---------------------------------------------------------------------------

SCORCHING_RAY = Spell(
    name="Scorching Ray",
    level=2,
    school=SpellSchool.EVOCATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="Instantaneous",
    effect_callback=_scorching_ray_effect,
    description=(
        "You blast your enemies with fiery rays. You may fire one ray, plus one "
        "additional ray for every four levels beyond 3rd (to a maximum of three "
        "rays at 11th level). Each ray requires a ranged touch attack to hit and "
        "deals 4d6 points of fire damage."
    ),
    subschool="",
    descriptor=["Fire"],
)

INVISIBILITY = Spell(
    name="Invisibility",
    level=2,
    school=SpellSchool.ILLUSION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL, SpellComponent.FOCUS],
    range="Personal or Touch",
    duration="1 min./level (D)",
    effect_callback=_invisibility_effect,
    description=(
        "The creature or object touched becomes invisible, vanishing from sight, "
        "even from darkvision. If the recipient is a creature carrying gear, that "
        "vanishes, too. The spell ends if the subject attacks any creature."
    ),
    subschool="Glamer",
    descriptor=[],
)

MIRROR_IMAGE = Spell(
    name="Mirror Image",
    level=2,
    school=SpellSchool.ILLUSION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Personal",
    duration="1 min./level",
    effect_callback=_mirror_image_effect,
    description=(
        "Several illusory duplicates of you pop into being, making it difficult "
        "for enemies to know which target to attack. The images mimic your "
        "actions, pretending to cast spells when you do."
    ),
    subschool="Figment",
    descriptor=[],
)

WEB = Spell(
    name="Web",
    level=2,
    school=SpellSchool.CONJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="Medium (100 ft. + 10 ft./level)",
    duration="10 min./level",
    effect_callback=_web_effect,
    description=(
        "Web creates a many-layered mass of strong, sticky strands. These strands "
        "trap those caught in them. The strands are similar to spider webs but "
        "far larger and tougher."
    ),
    subschool="Creation",
    descriptor=[],
)

BULLS_STRENGTH = Spell(
    name="Bull's Strength",
    level=2,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL, SpellComponent.DIVINE_FOCUS],
    range="Touch",
    duration="1 min./level",
    effect_callback=_bulls_strength_effect,
    description=(
        "The subject becomes stronger. The spell grants a +4 enhancement bonus "
        "to Strength, adding the usual benefits to melee attack rolls, melee "
        "damage rolls, and other uses of the Strength modifier."
    ),
    subschool="",
    descriptor=[],
)

BLUR = Spell(
    name="Blur",
    level=2,
    school=SpellSchool.ILLUSION,
    components=[SpellComponent.VERBAL],
    range="Personal or Touch",
    duration="1 min./level",
    effect_callback=_blur_effect,
    description=(
        "The subject's outline appears blurred, shifting, and wavery. This "
        "distortion grants the subject concealment (20% miss chance). A see "
        "invisibility spell does not counteract the blur effect."
    ),
    subschool="Glamer",
    descriptor=[],
)

RESIST_ENERGY = Spell(
    name="Resist Energy",
    level=2,
    school=SpellSchool.ABJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.DIVINE_FOCUS],
    range="Touch",
    duration="10 min./level",
    effect_callback=_resist_energy_effect,
    description=(
        "This abjuration grants a creature limited protection from damage of "
        "whichever one of five energy types you select: acid, cold, electricity, "
        "fire, or sonic. The subject gains resist energy 10 against the chosen "
        "energy type."
    ),
    subschool="",
    descriptor=[],
)

BEARS_ENDURANCE = Spell(
    name="Bear's Endurance",
    level=2,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL, SpellComponent.DIVINE_FOCUS],
    range="Touch",
    duration="1 min./level",
    effect_callback=_bears_endurance_effect,
    description=(
        "The affected creature gains enhanced physical stamina. The spell grants "
        "the subject a +4 enhancement bonus to Constitution, which adds the usual "
        "benefits to hit points, Fortitude saves, and so forth."
    ),
    subschool="",
    descriptor=[],
)


# ---------------------------------------------------------------------------
# Level 3 effect callbacks – Phase 1 additions
# ---------------------------------------------------------------------------

def _fireball_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Fireball: 1d6/level fire damage (max 10d6) in 20-ft radius, Reflex half."""
    dice = min(caster_level, 10)
    return {
        "damage": f"{dice}d6",
        "damage_type": "Fire",
        "area": "20-ft radius burst",
        "save": "Reflex half",
        "range": "Long (400 ft. + 40 ft./level)",
    }


def _lightning_bolt_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Lightning Bolt: 1d6/level electricity (max 10d6), 5-ft wide 120-ft line."""
    dice = min(caster_level, 10)
    return {
        "damage": f"{dice}d6",
        "damage_type": "Electricity",
        "area": "5-ft wide, 120-ft line",
        "save": "Reflex half",
    }


def _dispel_magic_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Dispel Magic: d20+CL (max +10) vs 11+target spell's caster level."""
    return {
        "max_caster_level_check": 10 + min(caster_level, 10),
        "targeted": True,
        "area": "one spell or creature/object",
    }


def _haste_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Haste: extra attack, +30 ft speed, +1 dodge AC, +1 Reflex."""
    return {
        "extra_attack": True,
        "speed_bonus_ft": 30,
        "dodge_ac_bonus": 1,
        "reflex_bonus": 1,
        "targets": "one creature/level",
        "duration_rounds": caster_level,
    }


def _hold_person_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Hold Person: humanoid paralyzed for 1 round/level (Will negates)."""
    return {
        "condition": "paralyzed",
        "target": "humanoid",
        "duration_rounds": caster_level,
        "save": "Will negates",
    }


def _fly_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Fly: fly speed 60 ft (poor), 40 ft in medium/heavy armor."""
    return {
        "fly_speed_ft": 60,
        "fly_speed_encumbered_ft": 40,
        "maneuverability": "good",
        "duration_minutes": caster_level,
    }


def _slow_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Slow: one action/round, -1 attack/AC/Reflex, half speed (Will negates)."""
    return {
        "max_action": "one standard or move action per round",
        "attack_penalty": -1,
        "ac_penalty": -1,
        "reflex_penalty": -1,
        "speed_multiplier": 0.5,
        "targets": f"one creature/level (max {caster_level})",
        "duration_rounds": caster_level,
        "save": "Will negates",
    }


def _vampiric_touch_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Vampiric Touch: 1d6/2 levels (max 10d6) damage, caster gains temp HP."""
    dice = min(caster_level // 2, 10)
    return {
        "damage": f"{dice}d6",
        "heals_caster": True,
        "temp_hp_duration_hours": 1,
    }


# ---------------------------------------------------------------------------
# Level 3 spell constants – Phase 1 additions
# ---------------------------------------------------------------------------

FIREBALL = Spell(
    name="Fireball",
    level=3,
    school=SpellSchool.EVOCATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="Long (400 ft. + 40 ft./level)",
    duration="Instantaneous",
    effect_callback=_fireball_effect,
    description=(
        "A fireball spell generates a searing explosion of flame that detonates "
        "with a low roar and deals 1d6 points of fire damage per caster level "
        "(maximum 10d6) to every creature within the area."
    ),
    subschool="",
    descriptor=["Fire"],
)

LIGHTNING_BOLT = Spell(
    name="Lightning Bolt",
    level=3,
    school=SpellSchool.EVOCATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="120 ft.",
    duration="Instantaneous",
    effect_callback=_lightning_bolt_effect,
    description=(
        "You release a powerful stroke of electrical energy that deals 1d6 "
        "points of electricity damage per caster level (maximum 10d6) to each "
        "creature within its area."
    ),
    subschool="",
    descriptor=["Electricity"],
)

DISPEL_MAGIC = Spell(
    name="Dispel Magic",
    level=3,
    school=SpellSchool.ABJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Medium (100 ft. + 10 ft./level)",
    duration="Instantaneous",
    effect_callback=_dispel_magic_effect,
    description=(
        "You can use dispel magic to end ongoing spells that have been cast on "
        "a creature or object, to temporarily suppress the magical abilities of "
        "a magic item, or to counter another spellcaster's spell."
    ),
    subschool="",
    descriptor=[],
)

HASTE = Spell(
    name="Haste",
    level=3,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="1 round/level",
    effect_callback=_haste_effect,
    description=(
        "The transmuted creatures move and act more quickly than normal. This "
        "extra speed has several effects: each hasted creature may make one extra "
        "attack in any round when it takes a full attack action."
    ),
    subschool="",
    descriptor=[],
)

HOLD_PERSON = Spell(
    name="Hold Person",
    level=3,
    school=SpellSchool.ENCHANTMENT,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.FOCUS, SpellComponent.DIVINE_FOCUS],
    range="Medium (100 ft. + 10 ft./level)",
    duration="1 round/level",
    effect_callback=_hold_person_effect,
    description=(
        "The subject becomes paralyzed and freezes in place. It is aware and "
        "breathes normally but cannot take any actions, even speech."
    ),
    subschool="Compulsion",
    descriptor=["Mind-Affecting"],
)

FLY = Spell(
    name="Fly",
    level=3,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.FOCUS],
    range="Touch",
    duration="1 min./level",
    effect_callback=_fly_effect,
    description=(
        "The subject can fly at a speed of 60 feet (or 40 feet if it wears "
        "medium or heavy armor). The subject can fly up, down, and laterally. "
        "The subject gains a maneuverability of good."
    ),
    subschool="",
    descriptor=[],
)

SLOW = Spell(
    name="Slow",
    level=3,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="1 round/level",
    effect_callback=_slow_effect,
    description=(
        "An affected creature moves and attacks at a drastically slowed rate. "
        "A slowed creature can take only a single move action or standard action "
        "each turn, but not both (nor may it take full-round actions)."
    ),
    subschool="",
    descriptor=[],
)

VAMPIRIC_TOUCH = Spell(
    name="Vampiric Touch",
    level=3,
    school=SpellSchool.NECROMANCY,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Touch",
    duration="Instantaneous/1 hour",
    effect_callback=_vampiric_touch_effect,
    description=(
        "You must succeed on a melee touch attack. Your touch deals 1d6 points "
        "of damage per two caster levels (maximum 10d6). You gain temporary hit "
        "points equal to the damage you deal. You cannot gain more than the "
        "subject's current hit points +10, which is enough to kill the subject."
    ),
    subschool="",
    descriptor=[],
)


def create_default_registry() -> SpellRegistry:
    """Create a :class:`SpellRegistry` pre-loaded with SRD core spells.

    Returns:
        A registry containing all Phase 0 foundational spells plus the
        Phase 1 Wizard/Sorcerer arcane spells (levels 0–3), for a total
        of 43 registered spells.
    """
    registry = SpellRegistry()

    # ---- Phase 0: original 11 spells ----
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
    registry.register(SUMMON_NATURES_ALLY_I)

    # ---- Phase 1: Level 0 additions (8) ----
    registry.register(DETECT_MAGIC)
    registry.register(RAY_OF_FROST)
    registry.register(RESISTANCE)
    registry.register(MAGE_HAND)
    registry.register(READ_MAGIC)
    registry.register(ACID_SPLASH)
    registry.register(DAZE)
    registry.register(LIGHT)

    # ---- Phase 1: Level 1 additions (8) ----
    registry.register(CHARM_PERSON)
    registry.register(COLOR_SPRAY)
    registry.register(FEATHER_FALL)
    registry.register(GREASE)
    registry.register(RAY_OF_ENFEEBLEMENT)
    registry.register(TRUE_STRIKE)
    registry.register(CAUSE_FEAR)
    registry.register(ENLARGE_PERSON)

    # ---- Phase 1: Level 2 additions (8) ----
    registry.register(SCORCHING_RAY)
    registry.register(INVISIBILITY)
    registry.register(MIRROR_IMAGE)
    registry.register(WEB)
    registry.register(BULLS_STRENGTH)
    registry.register(BLUR)
    registry.register(RESIST_ENERGY)
    registry.register(BEARS_ENDURANCE)

    # ---- Phase 1: Level 3 additions (8) ----
    registry.register(FIREBALL)
    registry.register(LIGHTNING_BOLT)
    registry.register(DISPEL_MAGIC)
    registry.register(HASTE)
    registry.register(HOLD_PERSON)
    registry.register(FLY)
    registry.register(SLOW)
    registry.register(VAMPIRIC_TOUCH)

    return registry
