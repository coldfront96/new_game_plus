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
    """The eight schools of magic in D&D 3.5e, plus Universal."""

    ABJURATION = "Abjuration"
    CONJURATION = "Conjuration"
    DIVINATION = "Divination"
    ENCHANTMENT = "Enchantment"
    EVOCATION = "Evocation"
    ILLUSION = "Illusion"
    NECROMANCY = "Necromancy"
    TRANSMUTATION = "Transmutation"
    UNIVERSAL = "Universal"


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
    """Fly: fly speed 60 ft (good maneuverability), 40 ft in medium/heavy armor."""
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


# ---------------------------------------------------------------------------
# Level 4 effect callbacks – Phase 2 additions
# ---------------------------------------------------------------------------

def _dimension_door_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Dimension Door: teleports caster (+ medium load) up to Long range."""
    return {
        "range": "Long (400 ft. + 40 ft./level)",
        "can_bring_others": True,
        "max_carry": "medium load",
        "teleport_type": "short",
    }


def _polymorph_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Polymorph: transforms willing creature into animal/magical beast (1-15 HD)."""
    return {
        "max_hd": 15,
        "gains_physical_stats": True,
        "retains_mental_stats": True,
        "duration_minutes": caster_level,
    }


def _greater_invisibility_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Greater Invisibility: invisible for 1 round/level; does NOT end on attack."""
    return {
        "ends_on_attack": False,
        "duration_rounds": caster_level,
    }


def _ice_storm_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Ice Storm: 3d6 bludgeoning + 2d6 cold in 20-ft radius cylinder."""
    return {
        "bludgeoning_damage": "3d6",
        "cold_damage": "2d6",
        "area": "20-ft radius, 10-ft high cylinder",
        "duration": "1 full round",
        "hampers_movement": True,
    }


def _stoneskin_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Stoneskin: DR 10/adamantine, absorbs up to 10/level damage (max 150)."""
    return {
        "dr": "10/adamantine",
        "max_absorption": min(caster_level * 10, 150),
        "duration_minutes": caster_level * 10,
    }


def _confusion_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Confusion: 15-ft radius burst, Will negates, confused 1 round/level."""
    return {
        "area": "15-ft radius burst",
        "save": "Will negates",
        "duration_rounds": caster_level,
    }


def _arcane_eye_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Arcane Eye: invisible eye moves 30 ft/round, concentration up to 1 min/level."""
    return {
        "move_speed_ft": 30,
        "fly_speed_ft": None,
        "concentration": True,
        "can_see_magic": False,
    }


def _black_tentacles_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Black Tentacles: 20-ft radius, tentacles +7 grapple, 1d6+4/round."""
    return {
        "area": "20-ft radius spread",
        "grapple_bonus": 7,
        "damage_per_round": "1d6+4",
        "duration_rounds": caster_level,
    }


# ---------------------------------------------------------------------------
# Level 4 spell constants – Phase 2 additions
# ---------------------------------------------------------------------------

DIMENSION_DOOR = Spell(
    name="Dimension Door",
    level=4,
    school=SpellSchool.CONJURATION,
    components=[SpellComponent.VERBAL],
    range="Long (400 ft. + 40 ft./level)",
    duration="Instantaneous",
    effect_callback=_dimension_door_effect,
    description=(
        "You instantly transfer yourself from your current location to any other "
        "spot within range. You always arrive at exactly the spot desired—whether "
        "by simply visualizing the area or by stating direction and distance."
    ),
    subschool="Teleportation",
    descriptor=[],
)

POLYMORPH = Spell(
    name="Polymorph",
    level=4,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="Touch",
    duration="1 min./level",
    effect_callback=_polymorph_effect,
    description=(
        "This spell transforms a willing creature into an animal or magical beast "
        "with up to 15 Hit Dice. The subject gains the new form's physical "
        "characteristics while retaining its own mental statistics."
    ),
    subschool="",
    descriptor=[],
)

GREATER_INVISIBILITY = Spell(
    name="Greater Invisibility",
    level=4,
    school=SpellSchool.ILLUSION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Personal or Touch",
    duration="1 round/level (D)",
    effect_callback=_greater_invisibility_effect,
    description=(
        "This spell functions like invisibility, except that it doesn't end if "
        "the subject attacks."
    ),
    subschool="Glamer",
    descriptor=[],
)

ICE_STORM = Spell(
    name="Ice Storm",
    level=4,
    school=SpellSchool.EVOCATION,
    components=[
        SpellComponent.VERBAL, SpellComponent.SOMATIC,
        SpellComponent.MATERIAL, SpellComponent.DIVINE_FOCUS,
    ],
    range="Long (400 ft. + 40 ft./level)",
    duration="1 full round",
    effect_callback=_ice_storm_effect,
    description=(
        "Great magical hailstones pound down for 1 full round, dealing 3d6 points "
        "of bludgeoning damage and 2d6 points of cold damage to every creature in "
        "the area."
    ),
    subschool="",
    descriptor=["Cold"],
)

STONESKIN = Spell(
    name="Stoneskin",
    level=4,
    school=SpellSchool.ABJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="Touch",
    duration="10 min./level or until discharged",
    effect_callback=_stoneskin_effect,
    description=(
        "The warded creature gains resistance to blows, cuts, stabs, and slashes. "
        "The subject gains damage reduction 10/adamantine."
    ),
    subschool="",
    descriptor=[],
)

CONFUSION = Spell(
    name="Confusion",
    level=4,
    school=SpellSchool.ENCHANTMENT,
    components=[
        SpellComponent.VERBAL, SpellComponent.SOMATIC,
        SpellComponent.MATERIAL, SpellComponent.DIVINE_FOCUS,
    ],
    range="Medium (100 ft. + 10 ft./level)",
    duration="1 round/level",
    effect_callback=_confusion_effect,
    description=(
        "This spell causes confusion in the targets, making them unable to "
        "independently determine what they will do. Roll on the following table "
        "each round to see what they do."
    ),
    subschool="Compulsion",
    descriptor=["Mind-Affecting"],
)

ARCANE_EYE = Spell(
    name="Arcane Eye",
    level=4,
    school=SpellSchool.DIVINATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="Unlimited",
    duration="1 min./level (concentration)",
    effect_callback=_arcane_eye_effect,
    description=(
        "You create an invisible magical sensor that sends you visual information. "
        "The sensor moves at up to 30 feet per round and shares your vision."
    ),
    subschool="Scrying",
    descriptor=[],
)

BLACK_TENTACLES = Spell(
    name="Black Tentacles",
    level=4,
    school=SpellSchool.CONJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="Medium (100 ft. + 10 ft./level)",
    duration="1 round/level",
    effect_callback=_black_tentacles_effect,
    description=(
        "This spell conjures a field of rubbery black tentacles, each 10 feet "
        "long. These tentacles grasp and squeeze any creature within the area, "
        "dealing 1d6+4 points of bludgeoning damage each round."
    ),
    subschool="Creation",
    descriptor=[],
)


# ---------------------------------------------------------------------------
# Level 5 effect callbacks – Phase 2 additions
# ---------------------------------------------------------------------------

def _cone_of_cold_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Cone of Cold: 1d6/level cold damage (max 15d6) in 60-ft cone, Reflex half."""
    return {
        "damage": f"{min(caster_level, 15)}d6",
        "damage_type": "Cold",
        "area": "60-ft cone",
        "save": "Reflex half",
    }


def _telekinesis_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Telekinesis: move up to 25 lb/level (max 375 lb) or violent thrust."""
    return {
        "max_weight_lbs": min(caster_level * 25, 375),
        "violent_thrust_damage": "1d6 per 25 lbs",
        "move_speed_ft": 20,
    }


def _wall_of_force_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Wall of Force: impenetrable wall, immune to dispel magic, 1 round/level."""
    return {
        "blocks_all": True,
        "immune_to_dispel": True,
        "vulnerable_to_disintegrate": True,
        "duration_rounds": caster_level,
    }


def _cloudkill_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Cloudkill: 20-ft spread, kills <=3 HD, Fort for 4-6 HD, 1d4 CON for 7+."""
    return {
        "area": "20-ft spread",
        "move_ft_per_round": 10,
        "instant_death_hd": 3,
        "fort_save_hd_threshold": 6,
        "con_damage": "1d4",
    }


def _dominate_person_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Dominate Person: humanoid under caster control, 1 day/level (Will negates)."""
    return {
        "save": "Will negates",
        "duration_days": caster_level,
        "allows_new_save": True,
    }


def _feeblemind_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Feeblemind: INT and CHA drop to 1 (Will negates; +4 DC vs arcane casters)."""
    return {
        "int_score": 1,
        "cha_score": 1,
        "save": "Will negates",
        "harder_vs_arcane_casters": True,
    }


def _permanency_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Permanency: makes certain spells permanent, costs XP."""
    return {
        "xp_cost": 500 + caster_level * 100,
        "eligible_spells": ["Darkvision", "Detect Magic", "See Invisibility", "Tongues"],
    }


def _sending_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Sending: send 25-word message to any creature; recipient can reply."""
    return {
        "max_words": 25,
        "range": "unlimited",
        "reply_words": 25,
    }


# ---------------------------------------------------------------------------
# Level 5 spell constants – Phase 2 additions
# ---------------------------------------------------------------------------

CONE_OF_COLD = Spell(
    name="Cone of Cold",
    level=5,
    school=SpellSchool.EVOCATION,
    components=[
        SpellComponent.VERBAL, SpellComponent.SOMATIC,
        SpellComponent.MATERIAL, SpellComponent.FOCUS,
    ],
    range="60-ft cone",
    duration="Instantaneous",
    effect_callback=_cone_of_cold_effect,
    description=(
        "Cone of cold creates an area of extreme cold, originating at your hand "
        "and extending outward in a cone. It drains heat, dealing 1d6 points of "
        "cold damage per caster level (maximum 15d6)."
    ),
    subschool="",
    descriptor=["Cold"],
)

TELEKINESIS = Spell(
    name="Telekinesis",
    level=5,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Long (400 ft. + 40 ft./level)",
    duration="Concentration, up to 1 round/level, or instantaneous",
    effect_callback=_telekinesis_effect,
    description=(
        "You move objects or creatures by concentrating on them. You can move "
        "up to 25 pounds per caster level (maximum 375 pounds) up to 20 feet "
        "per round, or fling objects violently."
    ),
    subschool="",
    descriptor=[],
)

WALL_OF_FORCE = Spell(
    name="Wall of Force",
    level=5,
    school=SpellSchool.EVOCATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="1 round/level (D)",
    effect_callback=_wall_of_force_effect,
    description=(
        "A wall of force spell creates an invisible wall of pure force. The wall "
        "cannot be broken, damaged, burned, melted, or destroyed by most magical "
        "means. It is not affected by dispel magic."
    ),
    subschool="",
    descriptor=["Force"],
)

CLOUDKILL = Spell(
    name="Cloudkill",
    level=5,
    school=SpellSchool.CONJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Medium (100 ft. + 10 ft./level)",
    duration="1 round/level",
    effect_callback=_cloudkill_effect,
    description=(
        "This spell generates a bank of fog, similar to a fog cloud, except that "
        "its vapors are yellowish green and poisonous. Creatures with 3 or fewer "
        "HD are slain instantly, and those with 4–6 HD must make a Fortitude save."
    ),
    subschool="Creation",
    descriptor=[],
)

DOMINATE_PERSON = Spell(
    name="Dominate Person",
    level=5,
    school=SpellSchool.ENCHANTMENT,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="1 day/level",
    effect_callback=_dominate_person_effect,
    description=(
        "You can control the actions of any humanoid creature through a telepathic "
        "link that you establish with the subject's mind."
    ),
    subschool="Compulsion",
    descriptor=["Mind-Affecting"],
)

FEEBLEMIND = Spell(
    name="Feeblemind",
    level=5,
    school=SpellSchool.ENCHANTMENT,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="Medium (100 ft. + 10 ft./level)",
    duration="Instantaneous",
    effect_callback=_feeblemind_effect,
    description=(
        "If the target fails its Will save, its Intelligence and Charisma scores "
        "each drop to 1. The affected creature is unable to use Intelligence- or "
        "Charisma-based skills."
    ),
    subschool="Compulsion",
    descriptor=["Mind-Affecting"],
)

PERMANENCY = Spell(
    name="Permanency",
    level=5,
    school=SpellSchool.UNIVERSAL,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.XP],
    range="See text",
    duration="Permanent",
    effect_callback=_permanency_effect,
    description=(
        "This spell makes certain other spells permanent. Casting permanency on "
        "yourself requires an XP expenditure."
    ),
    subschool="",
    descriptor=[],
)

SENDING = Spell(
    name="Sending",
    level=5,
    school=SpellSchool.EVOCATION,
    components=[
        SpellComponent.VERBAL, SpellComponent.SOMATIC,
        SpellComponent.MATERIAL, SpellComponent.DIVINE_FOCUS,
    ],
    range="See text",
    duration="1 round",
    effect_callback=_sending_effect,
    description=(
        "You contact a particular creature with which you are familiar and send "
        "a short message of 25 words or less. The subject recognizes you if it "
        "knows you. It can send a return message of 25 words or less."
    ),
    subschool="",
    descriptor=[],
)


# ---------------------------------------------------------------------------
# Level 6 effect callbacks – Phase 2 additions
# ---------------------------------------------------------------------------

def _disintegrate_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Disintegrate: ray, Fort partial; hit: 2d6/level (max 40d6) or dust; save: 5d6."""
    return {
        "damage": f"{min(caster_level * 2, 40)}d6",
        "save_damage": "5d6",
        "save": "Fortitude partial",
        "dust_on_death": True,
    }


def _chain_lightning_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Chain Lightning: 1d6/level (max 20d6) primary, arcs to 1/level secondaries."""
    return {
        "primary_damage": f"{min(caster_level, 20)}d6",
        "max_secondary_targets": min(caster_level, 20),
        "secondary_damage": "half",
        "save": "Reflex half",
    }


def _globe_of_invulnerability_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Globe of Invulnerability: blocks spell effects of 4th level or lower."""
    return {
        "blocks_spell_levels": [0, 1, 2, 3, 4],
        "radius_ft": 10,
        "duration_rounds": caster_level,
    }


def _true_seeing_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """True Seeing: see through disguises, illusions, invisible, ethereal."""
    return {
        "range_ft": 120,
        "see_invisible": True,
        "see_through_illusions": True,
        "see_ethereal": True,
        "see_true_form": True,
    }


def _contingency_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Contingency: sets trigger for another spell (max level = CL//3)."""
    return {
        "max_contingent_spell_level": caster_level // 3,
        "duration_days": caster_level,
    }


def _legend_lore_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Legend Lore: gains information about person, place, or thing."""
    return {
        "reveals_legend": True,
        "casting_time": "variable",
    }


def _repulsion_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Repulsion: creatures cannot approach within radius (Will negates)."""
    return {
        "radius_ft": caster_level * 10,
        "save": "Will negates",
        "duration_rounds": caster_level,
    }


def _mislead_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Mislead: caster becomes invisible; illusory double created."""
    return {
        "caster_invisible": True,
        "double_created": True,
        "duration_rounds": caster_level,
    }


# ---------------------------------------------------------------------------
# Level 6 spell constants – Phase 2 additions
# ---------------------------------------------------------------------------

DISINTEGRATE = Spell(
    name="Disintegrate",
    level=6,
    school=SpellSchool.TRANSMUTATION,
    components=[
        SpellComponent.VERBAL, SpellComponent.SOMATIC,
        SpellComponent.MATERIAL, SpellComponent.FOCUS,
    ],
    range="Medium (100 ft. + 10 ft./level)",
    duration="Instantaneous",
    effect_callback=_disintegrate_effect,
    description=(
        "A thin, green ray springs from your pointing finger. You must make a "
        "successful ranged touch attack to hit. Any creature struck by the ray "
        "takes 2d6 points of damage per caster level (to a maximum of 40d6)."
    ),
    subschool="",
    descriptor=[],
)

CHAIN_LIGHTNING = Spell(
    name="Chain Lightning",
    level=6,
    school=SpellSchool.EVOCATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.FOCUS],
    range="Long (400 ft. + 40 ft./level)",
    duration="Instantaneous",
    effect_callback=_chain_lightning_effect,
    description=(
        "This spell creates an electrical discharge that begins as a single stroke "
        "of lightning, dealing 1d6 points of electricity damage per caster level "
        "(maximum 20d6) to the primary target."
    ),
    subschool="",
    descriptor=["Electricity"],
)

GLOBE_OF_INVULNERABILITY = Spell(
    name="Globe of Invulnerability",
    level=6,
    school=SpellSchool.ABJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="10 ft.",
    duration="1 round/level (D)",
    effect_callback=_globe_of_invulnerability_effect,
    description=(
        "An immobile, faintly shimmering magical sphere surrounds you and excludes "
        "all spell effects of 4th level or lower. The area or effect of any such "
        "spells does not include the area of the globe."
    ),
    subschool="",
    descriptor=[],
)

TRUE_SEEING = Spell(
    name="True Seeing",
    level=6,
    school=SpellSchool.DIVINATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="Touch",
    duration="1 min./level",
    effect_callback=_true_seeing_effect,
    description=(
        "You confer on the subject the ability to notice spell effects, see the "
        "true form of polymorphed, changed, or transmuted things, and see into "
        "the Ethereal Plane."
    ),
    subschool="",
    descriptor=[],
)

CONTINGENCY = Spell(
    name="Contingency",
    level=6,
    school=SpellSchool.EVOCATION,
    components=[
        SpellComponent.VERBAL, SpellComponent.SOMATIC,
        SpellComponent.MATERIAL, SpellComponent.FOCUS,
    ],
    range="Personal",
    duration="1 day/level or until discharged",
    effect_callback=_contingency_effect,
    description=(
        "You can place another spell upon your person so that it comes into effect "
        "under some condition you dictate when casting contingency."
    ),
    subschool="",
    descriptor=[],
)

LEGEND_LORE = Spell(
    name="Legend Lore",
    level=6,
    school=SpellSchool.DIVINATION,
    components=[
        SpellComponent.VERBAL, SpellComponent.SOMATIC,
        SpellComponent.MATERIAL, SpellComponent.FOCUS,
    ],
    range="Personal",
    duration="See text",
    effect_callback=_legend_lore_effect,
    description=(
        "Legend lore brings to your mind legends about an important person, place, "
        "or thing. If the person or thing is at hand, the casting time is only 1d4x10 "
        "minutes."
    ),
    subschool="",
    descriptor=[],
)

REPULSION = Spell(
    name="Repulsion",
    level=6,
    school=SpellSchool.ABJURATION,
    components=[
        SpellComponent.VERBAL, SpellComponent.SOMATIC,
        SpellComponent.FOCUS, SpellComponent.DIVINE_FOCUS,
    ],
    range="10 ft.",
    duration="1 round/level (D)",
    effect_callback=_repulsion_effect,
    description=(
        "An invisible, mobile field surrounds you and prevents creatures from "
        "approaching you. You decide how large the field is at the time of casting "
        "(up to one 10-foot cube per level)."
    ),
    subschool="",
    descriptor=[],
)

MISLEAD = Spell(
    name="Mislead",
    level=6,
    school=SpellSchool.ILLUSION,
    components=[SpellComponent.SOMATIC],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="1 round/level (concentration + 3 rounds)",
    effect_callback=_mislead_effect,
    description=(
        "You become invisible and an illusory double of you appears. You are "
        "invisible for 1 round per level, and the double lasts for the same "
        "duration."
    ),
    subschool="Figment/Glamer",
    descriptor=[],
)


# ---------------------------------------------------------------------------
# Level 7 effect callbacks – Phase 2 additions
# ---------------------------------------------------------------------------

def _finger_of_death_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Finger of Death: Fort partial; fail: slain; save: 3d6+CL damage."""
    return {
        "save": "Fortitude partial",
        "save_damage": f"3d6+{caster_level}",
        "death_on_fail": True,
    }


def _power_word_blind_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Power Word Blind: blinds by HP total; no save."""
    return {
        "no_save": True,
        "threshold_permanent_hp": 50,
        "threshold_short_hp": 100,
    }


def _spell_turning_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Spell Turning: reflects 1d4+6 spell levels of targeted spells."""
    return {
        "spell_levels_to_reflect": "1d4+6",
        "affects_area_spells": False,
        "duration_minutes": caster_level * 10,
    }


def _limited_wish_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Limited Wish: alters reality within limits (costs 300 XP)."""
    return {
        "xp_cost": 300,
        "partially_emulate_spells": True,
        "undo_misfortune": True,
    }


def _prismatic_spray_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Prismatic Spray: 60-ft cone, 7 random effects per target."""
    return {
        "area": "60-ft cone",
        "effects": 7,
        "save": "varies",
    }


def _reverse_gravity_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Reverse Gravity: 20-ft radius, 40 ft high; creatures fall upward."""
    return {
        "area": "20-ft radius, 40-ft high cylinder",
        "duration_rounds": caster_level,
    }


def _ethereal_jaunt_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Ethereal Jaunt: caster becomes ethereal for 1 round/level."""
    return {
        "ethereal": True,
        "see_material_plane": True,
        "duration_rounds": caster_level,
    }


def _mordenkainens_sword_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Mordenkainen's Sword: force longsword +3, 4d6+3 force damage, BAB=CL."""
    return {
        "attack_bonus": 3,
        "damage": "4d6+3",
        "damage_type": "Force",
        "bab": caster_level,
        "duration_rounds": caster_level,
    }


# ---------------------------------------------------------------------------
# Level 7 spell constants – Phase 2 additions
# ---------------------------------------------------------------------------

FINGER_OF_DEATH = Spell(
    name="Finger of Death",
    level=7,
    school=SpellSchool.NECROMANCY,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="Instantaneous",
    effect_callback=_finger_of_death_effect,
    description=(
        "You can slay any living creature within range. The target is entitled "
        "to a Fortitude saving throw to survive the attack. If the save is "
        "successful, the creature instead takes 3d6 points of damage + 1 point "
        "per caster level."
    ),
    subschool="",
    descriptor=["Death"],
)

POWER_WORD_BLIND = Spell(
    name="Power Word Blind",
    level=7,
    school=SpellSchool.ENCHANTMENT,
    components=[SpellComponent.VERBAL],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="See text",
    effect_callback=_power_word_blind_effect,
    description=(
        "You utter a single word of power that causes one creature of your "
        "choice to become blinded, whether the creature can hear the word or not."
    ),
    subschool="Compulsion",
    descriptor=["Mind-Affecting"],
)

SPELL_TURNING = Spell(
    name="Spell Turning",
    level=7,
    school=SpellSchool.ABJURATION,
    components=[
        SpellComponent.VERBAL, SpellComponent.SOMATIC,
        SpellComponent.MATERIAL, SpellComponent.FOCUS,
    ],
    range="Personal",
    duration="Until expended, up to 10 min./level",
    effect_callback=_spell_turning_effect,
    description=(
        "Spells and spell-like effects targeted on you are turned back upon the "
        "original caster. The turning effect reflects 1d4+6 spell levels."
    ),
    subschool="",
    descriptor=[],
)

LIMITED_WISH = Spell(
    name="Limited Wish",
    level=7,
    school=SpellSchool.UNIVERSAL,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.XP],
    range="See text",
    duration="See text",
    effect_callback=_limited_wish_effect,
    description=(
        "A limited wish lets you create nearly any type of effect. For example, "
        "a limited wish can duplicate any spell of 7th level or lower, provided "
        "the spell does not belong to one of your opposition schools."
    ),
    subschool="",
    descriptor=[],
)

PRISMATIC_SPRAY = Spell(
    name="Prismatic Spray",
    level=7,
    school=SpellSchool.EVOCATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="60-ft cone",
    duration="Instantaneous",
    effect_callback=_prismatic_spray_effect,
    description=(
        "This spell causes seven shimmering, intertwined, multicolored beams of "
        "light to spray from your hand. Each beam has a different power and "
        "purpose."
    ),
    subschool="",
    descriptor=[],
)

REVERSE_GRAVITY = Spell(
    name="Reverse Gravity",
    level=7,
    school=SpellSchool.TRANSMUTATION,
    components=[
        SpellComponent.VERBAL, SpellComponent.SOMATIC,
        SpellComponent.MATERIAL, SpellComponent.FOCUS,
    ],
    range="Medium (100 ft. + 10 ft./level)",
    duration="1 round/level (D)",
    effect_callback=_reverse_gravity_effect,
    description=(
        "This spell reverses gravity in an area, causing all creatures and objects "
        "not somehow anchored to the ground to fall upward and reach the top of "
        "the area in 1 round."
    ),
    subschool="",
    descriptor=[],
)

ETHEREAL_JAUNT = Spell(
    name="Ethereal Jaunt",
    level=7,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Personal",
    duration="1 round/level (D)",
    effect_callback=_ethereal_jaunt_effect,
    description=(
        "You become ethereal, along with your equipment. For the duration of the "
        "spell, you are in the Ethereal Plane, which overlaps the Material Plane."
    ),
    subschool="",
    descriptor=[],
)

MORDENKAINENS_SWORD = Spell(
    name="Mordenkainen's Sword",
    level=7,
    school=SpellSchool.EVOCATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.FOCUS],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="1 round/level (D)",
    effect_callback=_mordenkainens_sword_effect,
    description=(
        "You evoke a shimmering, sword-like plane of force that hovers near you "
        "and attacks opponents as you direct. The sword attacks as a fighter equal "
        "to your caster level."
    ),
    subschool="",
    descriptor=["Force"],
)


# ---------------------------------------------------------------------------
# Level 8 effect callbacks – Phase 2 additions
# ---------------------------------------------------------------------------

def _power_word_stun_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Power Word Stun: stuns by HP total; no save."""
    return {
        "no_save": True,
        "threshold_4d4_hp": 50,
        "threshold_2d4_hp": 100,
    }


def _mind_blank_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Mind Blank: immune to mind-affecting and divination for 24 hours."""
    return {
        "immune_mind_affecting": True,
        "immune_divination": True,
        "duration_hours": 24,
    }


def _prismatic_wall_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Prismatic Wall: 8-layer wall of magical effects, 10 min/level."""
    return {
        "layers": 8,
        "blinds_on_gaze": True,
        "duration_minutes": caster_level * 10,
    }


def _maze_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Maze: traps creature in extradimensional maze; exit on Int DC 20."""
    return {
        "save": "none",
        "exit_dc": 20,
        "minotaur_escape": True,
    }


def _clone_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Clone: exact duplicate; soul enters clone when original dies."""
    return {
        "soul_transfer": True,
        "material_cost_gp": 1000,
        "time_to_mature_days": 2 * (20 - caster_level) if caster_level < 20 else 0,
    }


def _greater_prying_eyes_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Greater Prying Eyes: 1d4+1/level eyes (max 20) with True Seeing."""
    return {
        "num_eyes": f"1d4+{min(caster_level, 20)}",
        "max_eyes": 20,
        "true_seeing": True,
        "speed_ft": 30,
    }


def _sunburst_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Sunburst: 80-ft burst, 6d6 fire (Reflex half), blind; undead 1d6/level."""
    return {
        "damage": "6d6",
        "blind_save": "Fortitude negates",
        "area": "80-ft radius burst",
        "undead_damage": f"{min(caster_level, 25)}d6",
    }


def _polar_ray_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Polar Ray: ranged touch, 1d6/level cold (max 25d6) + 2d4 DEX drain."""
    return {
        "damage": f"{min(caster_level, 25)}d6",
        "damage_type": "Cold",
        "dex_drain": "2d4",
        "attack": "ranged touch",
    }


# ---------------------------------------------------------------------------
# Level 8 spell constants – Phase 2 additions
# ---------------------------------------------------------------------------

POWER_WORD_STUN = Spell(
    name="Power Word Stun",
    level=8,
    school=SpellSchool.ENCHANTMENT,
    components=[SpellComponent.VERBAL],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="See text",
    effect_callback=_power_word_stun_effect,
    description=(
        "You utter a single word of power that causes one creature of your choice "
        "to become stunned, whether or not it can hear the word."
    ),
    subschool="Compulsion",
    descriptor=["Mind-Affecting"],
)

MIND_BLANK = Spell(
    name="Mind Blank",
    level=8,
    school=SpellSchool.ABJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="24 hours",
    effect_callback=_mind_blank_effect,
    description=(
        "The subject is protected from all devices and spells that gather "
        "information about the target through divination magic, and is immune "
        "to all mind-affecting spells and effects."
    ),
    subschool="",
    descriptor=[],
)

PRISMATIC_WALL = Spell(
    name="Prismatic Wall",
    level=8,
    school=SpellSchool.ABJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="10 min./level (D)",
    effect_callback=_prismatic_wall_effect,
    description=(
        "Prismatic wall creates a vertical, opaque wall—a shimmering, "
        "multicolored plane of light that protects you from all forms of attack."
    ),
    subschool="",
    descriptor=[],
)

MAZE = Spell(
    name="Maze",
    level=8,
    school=SpellSchool.CONJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="See text",
    effect_callback=_maze_effect,
    description=(
        "You banish the subject into an extradimensional labyrinth. Each round "
        "on its turn, it may attempt to escape the labyrinth by making a DC 20 "
        "Intelligence check."
    ),
    subschool="Teleportation",
    descriptor=[],
)

CLONE = Spell(
    name="Clone",
    level=8,
    school=SpellSchool.NECROMANCY,
    components=[
        SpellComponent.VERBAL, SpellComponent.SOMATIC,
        SpellComponent.MATERIAL, SpellComponent.FOCUS,
    ],
    range="Touch",
    duration="Instantaneous",
    effect_callback=_clone_effect,
    description=(
        "This spell makes an inert duplicate of a creature. If the original "
        "individual has been slain, its soul immediately transfers to the clone."
    ),
    subschool="",
    descriptor=[],
)

GREATER_PRYING_EYES = Spell(
    name="Greater Prying Eyes",
    level=8,
    school=SpellSchool.DIVINATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="One mile",
    duration="1 hour/level",
    effect_callback=_greater_prying_eyes_effect,
    description=(
        "This spell functions like prying eyes, except that the eyes can see "
        "everything as if they had true seeing."
    ),
    subschool="Scrying",
    descriptor=[],
)

SUNBURST = Spell(
    name="Sunburst",
    level=8,
    school=SpellSchool.EVOCATION,
    components=[
        SpellComponent.VERBAL, SpellComponent.SOMATIC,
        SpellComponent.MATERIAL, SpellComponent.DIVINE_FOCUS,
    ],
    range="Long (400 ft. + 40 ft./level)",
    duration="Instantaneous",
    effect_callback=_sunburst_effect,
    description=(
        "Sunburst causes a globe of searing radiance to explode silently from a "
        "point you select. All creatures in the globe are blinded and take 6d6 "
        "points of damage. Undead creatures take 1d6 points of damage per caster "
        "level (maximum 25d6)."
    ),
    subschool="",
    descriptor=["Light"],
)

POLAR_RAY = Spell(
    name="Polar Ray",
    level=8,
    school=SpellSchool.EVOCATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.FOCUS],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="Instantaneous",
    effect_callback=_polar_ray_effect,
    description=(
        "A blue-white ray of freezing air and ice springs from your hand. You "
        "must succeed on a ranged touch attack with the ray to deal 1d6 points "
        "of cold damage per caster level (maximum 25d6) and 2d4 points of "
        "Dexterity drain."
    ),
    subschool="",
    descriptor=["Cold"],
)


# ---------------------------------------------------------------------------
# Level 9 effect callbacks – Phase 2 additions
# ---------------------------------------------------------------------------

def _wish_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Wish: most powerful arcane spell, alters reality (5000 XP cost)."""
    return {
        "xp_cost": 5000,
        "duplicates_any_arcane": True,
        "alters_reality": True,
    }


def _time_stop_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Time Stop: caster acts alone for 1d4+1 rounds while time is stopped."""
    return {
        "duration_rounds": "1d4+1",
        "only_caster_acts": True,
    }


def _meteor_swarm_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Meteor Swarm: 4 spheres, each 40-ft radius, direct hit + area fire."""
    return {
        "spheres": 4,
        "direct_hit_bludgeoning": "2d6",
        "direct_hit_fire": "6d6",
        "area_fire": "6d6",
        "area": "40-ft radius per sphere",
        "save": "Reflex half area",
    }


def _wail_of_the_banshee_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Wail of the Banshee: kills 1 creature/level in 40-ft spread (Fort negates)."""
    return {
        "max_targets": caster_level,
        "area": "40-ft spread",
        "save": "Fortitude negates",
        "death_effect": True,
    }


def _power_word_kill_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Power Word Kill: kills creature with <=100 HP; no save."""
    return {
        "no_save": True,
        "max_hp_threshold": 100,
    }


def _shapechange_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Shapechange: take form of any creature 1/4–25 HD, change freely."""
    return {
        "min_hd": 0.25,
        "max_hd": 25,
        "duration_minutes": caster_level * 10,
        "free_changes": True,
    }


def _gate_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Gate: portal to another plane OR calls powerful extraplanar being."""
    return {
        "portal": True,
        "calling": True,
        "calls_cr": "up to caster_level",
        "duration_rounds": caster_level,
    }


def _foresight_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    """Foresight: never surprised, +2 insight AC and Reflex, 10 min/level."""
    return {
        "never_surprised": True,
        "never_flat_footed": True,
        "insight_ac_bonus": 2,
        "insight_reflex_bonus": 2,
        "duration_minutes": caster_level * 10,
    }


# ---------------------------------------------------------------------------
# Level 9 spell constants – Phase 2 additions
# ---------------------------------------------------------------------------

WISH = Spell(
    name="Wish",
    level=9,
    school=SpellSchool.UNIVERSAL,
    components=[SpellComponent.VERBAL, SpellComponent.XP],
    range="Unlimited",
    duration="See text",
    effect_callback=_wish_effect,
    description=(
        "Wish is the mightiest spell a wizard or sorcerer can cast. By simply "
        "speaking aloud, you can alter reality to better suit you."
    ),
    subschool="",
    descriptor=[],
)

TIME_STOP = Spell(
    name="Time Stop",
    level=9,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL],
    range="Personal",
    duration="1d4+1 rounds (apparent time)",
    effect_callback=_time_stop_effect,
    description=(
        "This spell seems to make time cease to flow for everyone but you. In "
        "fact, you speed up so greatly that all other creatures seem frozen, though "
        "they are actually still moving at their normal speeds."
    ),
    subschool="",
    descriptor=[],
)

METEOR_SWARM = Spell(
    name="Meteor Swarm",
    level=9,
    school=SpellSchool.EVOCATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Long (400 ft. + 40 ft./level)",
    duration="Instantaneous",
    effect_callback=_meteor_swarm_effect,
    description=(
        "Meteor swarm is a very powerful and spectacular spell that is similar "
        "to fireball in many aspects. When you cast it, four 2-foot-diameter "
        "spheres spring from your outstretched hand and streak in straight lines "
        "to the spots you select."
    ),
    subschool="",
    descriptor=["Fire"],
)

WAIL_OF_THE_BANSHEE = Spell(
    name="Wail of the Banshee",
    level=9,
    school=SpellSchool.NECROMANCY,
    components=[SpellComponent.VERBAL],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="Instantaneous",
    effect_callback=_wail_of_the_banshee_effect,
    description=(
        "You emit a terrible, soul-chilling scream that possibly kills one "
        "creature per caster level."
    ),
    subschool="",
    descriptor=["Death", "Sonic"],
)

POWER_WORD_KILL = Spell(
    name="Power Word Kill",
    level=9,
    school=SpellSchool.ENCHANTMENT,
    components=[SpellComponent.VERBAL],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="Instantaneous",
    effect_callback=_power_word_kill_effect,
    description=(
        "You utter a single word of power that instantly kills one creature of "
        "your choice, whether or not it can hear the word. The creature can have "
        "at most 100 hit points."
    ),
    subschool="Compulsion",
    descriptor=["Death", "Mind-Affecting"],
)

SHAPECHANGE = Spell(
    name="Shapechange",
    level=9,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.FOCUS],
    range="Personal",
    duration="10 min./level (D)",
    effect_callback=_shapechange_effect,
    description=(
        "This spell functions like polymorph, except that it enables you to "
        "assume the form of any single nonunique creature (of any type) from "
        "Fine to Colossal size."
    ),
    subschool="",
    descriptor=[],
)

GATE = Spell(
    name="Gate",
    level=9,
    school=SpellSchool.CONJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Medium (100 ft. + 10 ft./level)",
    duration="Concentration up to 1 round/level (D)",
    effect_callback=_gate_effect,
    description=(
        "Casting a gate spell has two effects. First, it creates an interdimensional "
        "connection between your plane of existence and a plane you specify, allowing "
        "travel between those two planes. Second, you may call a particular individual "
        "or kind of being to come through the gate."
    ),
    subschool="Creation",
    descriptor=[],
)

FORESIGHT = Spell(
    name="Foresight",
    level=9,
    school=SpellSchool.DIVINATION,
    components=[
        SpellComponent.VERBAL, SpellComponent.SOMATIC,
        SpellComponent.MATERIAL, SpellComponent.FOCUS,
    ],
    range="Personal or Touch",
    duration="10 min./level",
    effect_callback=_foresight_effect,
    description=(
        "This powerful divination grants you a powerful sixth sense in relation "
        "to yourself or another. Once foresight is cast, you receive instantaneous "
        "warnings of impending danger or harm to the subject of the spell."
    ),
    subschool="",
    descriptor=[],
)


def create_default_registry() -> SpellRegistry:
    """Create a :class:`SpellRegistry` pre-loaded with SRD core spells.

    Returns:
        A registry containing all Phase 0 foundational spells, the Phase 1
        Wizard/Sorcerer arcane spells (levels 0–3), and the Phase 2
        Wizard/Sorcerer arcane spells (levels 4–9), for a total of 91
        registered spells.
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

    # ---- Phase 2: Level 4 additions (8) ----
    registry.register(DIMENSION_DOOR)
    registry.register(POLYMORPH)
    registry.register(GREATER_INVISIBILITY)
    registry.register(ICE_STORM)
    registry.register(STONESKIN)
    registry.register(CONFUSION)
    registry.register(ARCANE_EYE)
    registry.register(BLACK_TENTACLES)

    # ---- Phase 2: Level 5 additions (8) ----
    registry.register(CONE_OF_COLD)
    registry.register(TELEKINESIS)
    registry.register(WALL_OF_FORCE)
    registry.register(CLOUDKILL)
    registry.register(DOMINATE_PERSON)
    registry.register(FEEBLEMIND)
    registry.register(PERMANENCY)
    registry.register(SENDING)

    # ---- Phase 2: Level 6 additions (8) ----
    registry.register(DISINTEGRATE)
    registry.register(CHAIN_LIGHTNING)
    registry.register(GLOBE_OF_INVULNERABILITY)
    registry.register(TRUE_SEEING)
    registry.register(CONTINGENCY)
    registry.register(LEGEND_LORE)
    registry.register(REPULSION)
    registry.register(MISLEAD)

    # ---- Phase 2: Level 7 additions (8) ----
    registry.register(FINGER_OF_DEATH)
    registry.register(POWER_WORD_BLIND)
    registry.register(SPELL_TURNING)
    registry.register(LIMITED_WISH)
    registry.register(PRISMATIC_SPRAY)
    registry.register(REVERSE_GRAVITY)
    registry.register(ETHEREAL_JAUNT)
    registry.register(MORDENKAINENS_SWORD)

    # ---- Phase 2: Level 8 additions (8) ----
    registry.register(POWER_WORD_STUN)
    registry.register(MIND_BLANK)
    registry.register(PRISMATIC_WALL)
    registry.register(MAZE)
    registry.register(CLONE)
    registry.register(GREATER_PRYING_EYES)
    registry.register(SUNBURST)
    registry.register(POLAR_RAY)

    # ---- Phase 2: Level 9 additions (8) ----
    registry.register(WISH)
    registry.register(TIME_STOP)
    registry.register(METEOR_SWARM)
    registry.register(WAIL_OF_THE_BANSHEE)
    registry.register(POWER_WORD_KILL)
    registry.register(SHAPECHANGE)
    registry.register(GATE)
    registry.register(FORESIGHT)

    return registry
