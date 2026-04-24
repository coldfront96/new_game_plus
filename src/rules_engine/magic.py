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


# ---------------------------------------------------------------------------
# Phase 3: Cleric / Paladin divine spell effect callbacks
# ---------------------------------------------------------------------------

# -- Level 0 --

def _guidance_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"bonus": 1, "bonus_type": "competence", "save": "until discharged"}


def _virtue_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"temp_hp": 1, "duration_minutes": 1}


def _inflict_minor_wounds_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"damage": 1, "attack": "touch", "heals_undead": True}


def _detect_undead_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"range_ft": 60, "detects_undead": True, "can_determine_strength": True}


def _create_water_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"gallons": caster_level * 2, "maximum": None}


def _purify_food_and_drink_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"cubic_feet": caster_level}


# -- Level 1 --

def _command_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "save": "Will negates",
        "duration_rounds": 1,
        "commands": ["approach", "drop", "fall", "flee", "halt"],
    }


def _sanctuary_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"save_to_attack": "Will DC", "duration_rounds": caster_level}


def _divine_favor_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    bonus = min(max(1, caster_level // 3), 3)
    return {
        "attack_bonus": bonus,
        "damage_bonus": bonus,
        "bonus_type": "luck",
        "duration_minutes": 1,
    }


def _doom_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "penalty": -2,
        "condition": "shaken",
        "save": "Will negates",
        "duration_minutes": caster_level,
    }


def _entropic_shield_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"ranged_miss_chance": 0.20, "duration_minutes": caster_level}


# -- Level 2 --

def _cure_moderate_wounds_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "healing": f"2d8+{min(caster_level, 10)}",
        "harms_undead": True,
        "energy_type": "positive",
    }


def _silence_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "area": "20-ft radius emanation",
        "save": "Will negates (creature)",
        "negates_verbal": True,
        "duration_rounds": caster_level,
    }


def _spiritual_weapon_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "damage": "1d8",
        "enhancement": min(1 + caster_level // 3, 5),
        "bab": caster_level,
        "duration_rounds": caster_level,
    }


def _consecrate_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "area": "20-ft radius burst",
        "undead_penalty": -1,
        "positive_channeling_bonus": True,
        "duration_hours": caster_level * 2,
    }


def _aid_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "attack_bonus": 1,
        "save_vs_fear_bonus": 1,
        "temp_hp": f"1d8+{min(caster_level, 10)}",
        "duration_minutes": caster_level,
    }


def _desecrate_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "area": "20-ft radius burst",
        "undead_bonus": 1,
        "undead_hp_per_hd": 1,
        "duration_hours": caster_level * 2,
    }


def _blindness_deafness_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"save": "Fortitude negates", "permanent": True, "target_sense": "choice"}


# -- Level 3 --

def _cure_serious_wounds_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "healing": f"3d8+{min(caster_level, 15)}",
        "harms_undead": True,
    }


def _prayer_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "ally_bonus": 1,
        "enemy_penalty": -1,
        "bonus_type": "luck",
        "area": "40-ft burst",
        "duration_rounds": caster_level,
    }


def _searing_light_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "damage": f"{min(caster_level // 2, 5)}d8",
        "undead_damage": f"{min(caster_level, 10)}d8",
        "damage_type": "Light/Radiant",
        "attack": "ranged touch",
    }


def _speak_with_dead_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "max_questions": min(caster_level // 2, 6),
        "duration_minutes": caster_level * 10,
    }


def _inflict_serious_wounds_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "damage": f"3d8+{min(caster_level, 15)}",
        "heals_undead": True,
        "attack": "touch",
    }


# -- Level 4 --

def _cure_critical_wounds_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "healing": f"4d8+{min(caster_level, 20)}",
        "harms_undead": True,
    }


def _divine_power_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "bab_set_to": caster_level,
        "str_bonus": 6,
        "bonus_hp": caster_level,
        "duration_rounds": caster_level,
    }


def _freedom_of_movement_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "ignore_grapple": True,
        "ignore_entangle": True,
        "move_underwater": True,
        "duration_minutes": caster_level * 10,
    }


def _neutralize_poison_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "neutralizes_active_poison": True,
        "detoxify_duration_minutes": caster_level * 10,
    }


def _restoration_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "removes_ability_damage": True,
        "removes_negative_levels": True,
        "removes_magical_aging": False,
        "material_cost_gp": 100,
    }


# -- Level 5 --

def _flame_strike_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "damage": f"{min(caster_level, 15)}d6",
        "fire_half": True,
        "divine_half": True,
        "area": "10-ft radius, 40-ft high column",
        "save": "Reflex half",
    }


def _insect_plague_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "swarms": min(caster_level // 3, 6),
        "damage_per_swarm": "1d6",
        "distraction": True,
        "duration_minutes": caster_level,
    }


def _righteous_might_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "str_bonus": 8,
        "con_bonus": 4,
        "natural_armor_bonus": 2,
        "size_increase": 1,
        "dr": "3/evil",
        "duration_rounds": caster_level,
    }


def _break_enchantment_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "max_targets": caster_level,
        "removes_enchantment": True,
        "removes_curse": True,
        "removes_petrification": True,
    }


# -- Level 6 --

def _blade_barrier_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "damage": f"{min(caster_level, 20)}d6",
        "save": "Reflex half",
        "duration_minutes": caster_level * 10,
    }


def _word_of_recall_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"teleports_to": "pre-designated sanctuary", "willing_only": True}


# -- Level 7 --

def _resurrection_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "max_years_dead": caster_level * 10,
        "restores_1_negative_level": True,
        "material_cost_gp": 10000,
    }


# -- Level 9 --

def _mass_heal_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "healing": min(caster_level * 10, 250),
        "area": "30-ft burst",
        "harms_undead": True,
    }


# -- Paladin Level 1 --

def _detect_evil_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "detects_alignment": "evil",
        "range_ft": 60,
        "duration_concentration": True,
    }


def _protection_from_evil_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "ac_bonus": 2,
        "save_bonus": 2,
        "bonus_type": "deflection/resistance",
        "blocks_possession": True,
        "duration_minutes": caster_level,
    }


def _bless_weapon_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "enhancement_bonus": 1,
        "bypasses_dr_vs_evil_outsiders": True,
        "bypasses_dr_vs_undead": True,
        "duration_minutes": caster_level,
    }


# -- Paladin Level 2 --

def _delay_poison_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"suspends_poison": True, "duration_hours": caster_level}


def _shield_other_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "damage_split": True,
        "save_bonus": 1,
        "ac_bonus": 1,
        "duration_hours": caster_level,
    }


def _owls_wisdom_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"wis_bonus": 4, "bonus_type": "enhancement", "duration_minutes": caster_level}


# -- Paladin Level 3 --

def _daylight_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "bright_radius_ft": 60,
        "shadowy_radius_ft": 60,
        "dispels_darkness_level": 3,
        "duration_minutes": caster_level * 10,
    }


def _remove_blindness_deafness_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"removes_blindness": True, "removes_deafness": True, "save": "none"}


# -- Paladin Level 4 --

def _holy_sword_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "enhancement_bonus": 5,
        "holy_damage": "2d6",
        "vs_evil_only": True,
        "duration_rounds": caster_level,
    }


def _mark_of_justice_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "permanent": True,
        "triggered_curse": True,
        "remove_with": "break enchantment or remove curse",
    }


def _dispel_evil_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "ac_bonus_vs_evil": 4,
        "dispel_evil_spell": True,
        "banish_evil_extraplanar": True,
        "duration_rounds": caster_level,
    }


def _holy_aura_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "deflection_bonus": 4,
        "resistance_bonus": 4,
        "spell_resistance": 25,
        "blinds_evil_attackers": True,
        "duration_rounds": caster_level,
    }


# ---------------------------------------------------------------------------
# Phase 3: Cleric / Paladin divine spell constants
# ---------------------------------------------------------------------------

# -- Cleric Level 0 --

GUIDANCE = Spell(
    name="Guidance",
    level=0,
    school=SpellSchool.DIVINATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Touch",
    duration="1 minute or until discharged",
    effect_callback=_guidance_effect,
    description=(
        "This spell imbues the subject with a touch of divine guidance. The "
        "creature gets a +1 competence bonus on a single attack roll, saving "
        "throw, or skill check."
    ),
    subschool="",
    descriptor=[],
)

VIRTUE = Spell(
    name="Virtue",
    level=0,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.DIVINE_FOCUS],
    range="Touch",
    duration="1 minute",
    effect_callback=_virtue_effect,
    description=(
        "The subject gains 1 temporary hit point."
    ),
    subschool="",
    descriptor=[],
)

INFLICT_MINOR_WOUNDS = Spell(
    name="Inflict Minor Wounds",
    level=0,
    school=SpellSchool.NECROMANCY,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Touch",
    duration="Instantaneous",
    effect_callback=_inflict_minor_wounds_effect,
    description=(
        "When laying your hand upon a creature, you channel negative energy "
        "that deals 1 point of damage. Since undead are powered by negative "
        "energy, this spell cures such a creature of 1 point of damage."
    ),
    subschool="",
    descriptor=[],
)

DETECT_UNDEAD = Spell(
    name="Detect Undead",
    level=0,
    school=SpellSchool.DIVINATION,
    components=[
        SpellComponent.VERBAL, SpellComponent.SOMATIC,
        SpellComponent.MATERIAL, SpellComponent.DIVINE_FOCUS,
    ],
    range="60 ft.",
    duration="Concentration, up to 1 min./level",
    effect_callback=_detect_undead_effect,
    description=(
        "You can detect the aura that surrounds undead creatures. The amount "
        "of information revealed depends on how long you study a particular "
        "area or subject."
    ),
    subschool="",
    descriptor=[],
)

CREATE_WATER = Spell(
    name="Create Water",
    level=0,
    school=SpellSchool.CONJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="Instantaneous",
    effect_callback=_create_water_effect,
    description=(
        "This spell generates wholesome, drinkable water, just like clean "
        "rain water. Water can be created in an area as small as will actually "
        "contain the liquid, or in an area three times as large (up to 2 gallons/level)."
    ),
    subschool="Creation",
    descriptor=["Water"],
)

PURIFY_FOOD_AND_DRINK = Spell(
    name="Purify Food and Drink",
    level=0,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="10 ft.",
    duration="Instantaneous",
    effect_callback=_purify_food_and_drink_effect,
    description=(
        "This spell makes spoiled, rotten, diseased, or otherwise contaminated "
        "food and water pure and suitable for eating and drinking."
    ),
    subschool="",
    descriptor=[],
)

# -- Cleric Level 1 --

COMMAND = Spell(
    name="Command",
    level=1,
    school=SpellSchool.ENCHANTMENT,
    components=[SpellComponent.VERBAL],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="1 round",
    effect_callback=_command_effect,
    description=(
        "You give the subject a single command, which it obeys to the best "
        "of its ability at its earliest opportunity."
    ),
    subschool="Compulsion",
    descriptor=["Language-Dependent", "Mind-Affecting"],
)

SANCTUARY = Spell(
    name="Sanctuary",
    level=1,
    school=SpellSchool.ABJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.DIVINE_FOCUS],
    range="Touch",
    duration="1 round/level",
    effect_callback=_sanctuary_effect,
    description=(
        "Any opponent attempting to strike or otherwise directly attack the "
        "warded creature, even with a targeted spell, must attempt a Will save. "
        "If the save succeeds, the opponent can attack normally and is unaffected "
        "by that casting of the spell."
    ),
    subschool="",
    descriptor=[],
)

DIVINE_FAVOR = Spell(
    name="Divine Favor",
    level=1,
    school=SpellSchool.EVOCATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.DIVINE_FOCUS],
    range="Personal",
    duration="1 minute",
    effect_callback=_divine_favor_effect,
    description=(
        "Calling upon the strength and wisdom of a deity, you gain a +1 luck "
        "bonus on attack and weapon damage rolls for every three caster levels "
        "you have (at least +1, maximum +3)."
    ),
    subschool="",
    descriptor=[],
)

DOOM = Spell(
    name="Doom",
    level=1,
    school=SpellSchool.NECROMANCY,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.DIVINE_FOCUS],
    range="Medium (100 ft. + 10 ft./level)",
    duration="1 min./level",
    effect_callback=_doom_effect,
    description=(
        "This spell fills a single subject with a feeling of horrible dread "
        "that causes it to become shaken."
    ),
    subschool="",
    descriptor=["Fear", "Mind-Affecting"],
)

ENTROPIC_SHIELD = Spell(
    name="Entropic Shield",
    level=1,
    school=SpellSchool.ABJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Personal",
    duration="1 min./level",
    effect_callback=_entropic_shield_effect,
    description=(
        "A magical field appears around you, glowing with a chaotic blast of "
        "multicolored hues. This field deflects incoming arrows, rays, and other "
        "ranged attacks, giving ranged attacks a 20% miss chance."
    ),
    subschool="",
    descriptor=[],
)

# -- Cleric Level 2 --

CURE_MODERATE_WOUNDS = Spell(
    name="Cure Moderate Wounds",
    level=2,
    school=SpellSchool.CONJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Touch",
    duration="Instantaneous",
    effect_callback=_cure_moderate_wounds_effect,
    description=(
        "When laying your hand upon a living creature, you channel positive "
        "energy that cures 2d8 points of damage +1 per caster level (maximum +10)."
    ),
    subschool="Healing",
    descriptor=[],
)

SILENCE = Spell(
    name="Silence",
    level=2,
    school=SpellSchool.ILLUSION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Long (400 ft. + 40 ft./level)",
    duration="1 round/level",
    effect_callback=_silence_effect,
    description=(
        "Upon the casting of this spell, complete silence prevails in the "
        "affected area. All sound is stopped: Conversation is impossible, "
        "spells with verbal components cannot be cast, and no noise whatsoever issues from, travels into, or through the area."
    ),
    subschool="Glamer",
    descriptor=[],
)

SPIRITUAL_WEAPON = Spell(
    name="Spiritual Weapon",
    level=2,
    school=SpellSchool.EVOCATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.DIVINE_FOCUS],
    range="Medium (100 ft. + 10 ft./level)",
    duration="1 round/level",
    effect_callback=_spiritual_weapon_effect,
    description=(
        "A weapon made of pure force springs into existence and attacks "
        "opponents at a distance, as you direct it, dealing 1d8 force damage "
        "per hit, +1 per three caster levels (maximum +5)."
    ),
    subschool="",
    descriptor=["Force"],
)

CONSECRATE = Spell(
    name="Consecrate",
    level=2,
    school=SpellSchool.EVOCATION,
    components=[
        SpellComponent.VERBAL, SpellComponent.SOMATIC,
        SpellComponent.MATERIAL, SpellComponent.DIVINE_FOCUS,
    ],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="2 hours/level",
    effect_callback=_consecrate_effect,
    description=(
        "This spell blesses an area with positive energy. The DC to turn "
        "undead increases by +3, and undead in the area suffer a -1 penalty "
        "on attack rolls, damage rolls, and saving throws."
    ),
    subschool="",
    descriptor=["Good"],
)

AID = Spell(
    name="Aid",
    level=2,
    school=SpellSchool.ENCHANTMENT,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.DIVINE_FOCUS],
    range="Touch",
    duration="1 min./level",
    effect_callback=_aid_effect,
    description=(
        "Aid grants the target a +1 morale bonus on attack rolls and saves "
        "against fear effects, plus temporary hit points equal to 1d8 + "
        "caster level (maximum +10)."
    ),
    subschool="Compulsion",
    descriptor=["Mind-Affecting"],
)

DESECRATE = Spell(
    name="Desecrate",
    level=2,
    school=SpellSchool.EVOCATION,
    components=[
        SpellComponent.VERBAL, SpellComponent.SOMATIC,
        SpellComponent.MATERIAL, SpellComponent.DIVINE_FOCUS,
    ],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="2 hours/level",
    effect_callback=_desecrate_effect,
    description=(
        "This spell imbues an area with negative energy. Undead created within "
        "or summoned into such an area gain +1 hit point per HD."
    ),
    subschool="",
    descriptor=["Evil"],
)

BLINDNESS_DEAFNESS = Spell(
    name="Blindness/Deafness",
    level=2,
    school=SpellSchool.NECROMANCY,
    components=[SpellComponent.VERBAL],
    range="Medium (100 ft. + 10 ft./level)",
    duration="Permanent",
    effect_callback=_blindness_deafness_effect,
    description=(
        "You call upon the powers of unlife to render the subject blinded or "
        "deafened, as you choose."
    ),
    subschool="",
    descriptor=[],
)

# -- Cleric Level 3 --

CURE_SERIOUS_WOUNDS = Spell(
    name="Cure Serious Wounds",
    level=3,
    school=SpellSchool.CONJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Touch",
    duration="Instantaneous",
    effect_callback=_cure_serious_wounds_effect,
    description=(
        "When laying your hand upon a living creature, you channel positive "
        "energy that cures 3d8 points of damage +1 per caster level (maximum +15)."
    ),
    subschool="Healing",
    descriptor=[],
)

PRAYER = Spell(
    name="Prayer",
    level=3,
    school=SpellSchool.ENCHANTMENT,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.DIVINE_FOCUS],
    range="40 ft.",
    duration="1 round/level",
    effect_callback=_prayer_effect,
    description=(
        "You bring special favor upon yourself and your allies while bringing "
        "discord to your enemies. Each round, all allies within the area receive "
        "a +1 luck bonus on attack rolls, weapon damage rolls, saves, and skill "
        "checks, while each enemy suffers a -1 penalty."
    ),
    subschool="Compulsion",
    descriptor=["Mind-Affecting"],
)

SEARING_LIGHT = Spell(
    name="Searing Light",
    level=3,
    school=SpellSchool.EVOCATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Medium (100 ft. + 10 ft./level)",
    duration="Instantaneous",
    effect_callback=_searing_light_effect,
    description=(
        "Focusing divine power like a ray of the sun, you project a blast of "
        "light from your open palm. You must succeed on a ranged touch attack "
        "to strike your target. A creature struck by this ray of light takes "
        "1d8 points of damage per two caster levels (maximum 5d8)."
    ),
    subschool="",
    descriptor=[],
)

SPEAK_WITH_DEAD = Spell(
    name="Speak with Dead",
    level=3,
    school=SpellSchool.NECROMANCY,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.DIVINE_FOCUS],
    range="10 ft.",
    duration="10 min./level",
    effect_callback=_speak_with_dead_effect,
    description=(
        "You grant the semblance of life and intelligence to a corpse, allowing "
        "it to answer several questions that you put to it. You may ask one "
        "question per two caster levels (maximum six questions)."
    ),
    subschool="",
    descriptor=["Language-Dependent"],
)

INFLICT_SERIOUS_WOUNDS = Spell(
    name="Inflict Serious Wounds",
    level=3,
    school=SpellSchool.NECROMANCY,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Touch",
    duration="Instantaneous",
    effect_callback=_inflict_serious_wounds_effect,
    description=(
        "When laying your hand upon a creature, you channel negative energy "
        "that deals 3d8 points of damage +1 per caster level (maximum +15)."
    ),
    subschool="",
    descriptor=[],
)

# -- Cleric Level 4 --

CURE_CRITICAL_WOUNDS = Spell(
    name="Cure Critical Wounds",
    level=4,
    school=SpellSchool.CONJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Touch",
    duration="Instantaneous",
    effect_callback=_cure_critical_wounds_effect,
    description=(
        "When laying your hand upon a living creature, you channel positive "
        "energy that cures 4d8 points of damage +1 per caster level (maximum +20)."
    ),
    subschool="Healing",
    descriptor=[],
)

DIVINE_POWER = Spell(
    name="Divine Power",
    level=4,
    school=SpellSchool.EVOCATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.DIVINE_FOCUS],
    range="Personal",
    duration="1 round/level",
    effect_callback=_divine_power_effect,
    description=(
        "Calling upon the divine power of your patron, you imbue yourself with "
        "strength and skill in combat. Your base attack bonus equals your caster "
        "level, you gain a +6 enhancement bonus to Strength, and you gain 1 "
        "temporary hit point per caster level."
    ),
    subschool="",
    descriptor=[],
)

FREEDOM_OF_MOVEMENT = Spell(
    name="Freedom of Movement",
    level=4,
    school=SpellSchool.ABJURATION,
    components=[
        SpellComponent.VERBAL, SpellComponent.SOMATIC,
        SpellComponent.MATERIAL, SpellComponent.DIVINE_FOCUS,
    ],
    range="Personal or Touch",
    duration="10 min./level",
    effect_callback=_freedom_of_movement_effect,
    description=(
        "This spell enables you or a creature you touch to move and attack "
        "normally for the duration of the spell, even under the influence of "
        "magic that usually impedes movement."
    ),
    subschool="",
    descriptor=[],
)

NEUTRALIZE_POISON = Spell(
    name="Neutralize Poison",
    level=4,
    school=SpellSchool.CONJURATION,
    components=[
        SpellComponent.VERBAL, SpellComponent.SOMATIC,
        SpellComponent.MATERIAL, SpellComponent.DIVINE_FOCUS,
    ],
    range="Touch",
    duration="10 min./level",
    effect_callback=_neutralize_poison_effect,
    description=(
        "You detoxify any sort of venom in the creature or object touched. "
        "A poisoned creature suffers no additional effects from the poison, "
        "and any temporary effects are ended."
    ),
    subschool="Healing",
    descriptor=[],
)

RESTORATION = Spell(
    name="Restoration",
    level=4,
    school=SpellSchool.CONJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="Touch",
    duration="Instantaneous",
    effect_callback=_restoration_effect,
    description=(
        "This spell functions like lesser restoration, except that it also "
        "dispels negative energy levels and restores one experience level to "
        "a creature who has had a level drained."
    ),
    subschool="Healing",
    descriptor=[],
)

# -- Cleric Level 5 --

FLAME_STRIKE = Spell(
    name="Flame Strike",
    level=5,
    school=SpellSchool.EVOCATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.DIVINE_FOCUS],
    range="Medium (100 ft. + 10 ft./level)",
    duration="Instantaneous",
    effect_callback=_flame_strike_effect,
    description=(
        "A flame strike produces a vertical column of divine fire roaring "
        "downward. The spell deals 1d6 points of damage per caster level "
        "(maximum 15d6). Half the damage is fire damage, but the other half "
        "results directly from divine power and is therefore not subject to "
        "being reduced by resistance to fire-based attacks."
    ),
    subschool="",
    descriptor=["Fire"],
)

INSECT_PLAGUE = Spell(
    name="Insect Plague",
    level=5,
    school=SpellSchool.CONJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.DIVINE_FOCUS],
    range="Long (400 ft. + 40 ft./level)",
    duration="1 min./level",
    effect_callback=_insect_plague_effect,
    description=(
        "You summon a number of swarms of locusts (maximum 6 swarms, 1 per "
        "3 levels). The swarms spread out in a cloud that covers a 60-foot "
        "diameter area."
    ),
    subschool="Summoning",
    descriptor=[],
)

RIGHTEOUS_MIGHT = Spell(
    name="Righteous Might",
    level=5,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.DIVINE_FOCUS],
    range="Personal",
    duration="1 round/level",
    effect_callback=_righteous_might_effect,
    description=(
        "Your height doubles, and your weight increases by a factor of eight. "
        "Your size category changes to the next larger size. You gain a +8 "
        "size bonus to Strength, a +4 size bonus to Constitution, and a +2 "
        "size bonus to natural armor."
    ),
    subschool="",
    descriptor=[],
)

BREAK_ENCHANTMENT = Spell(
    name="Break Enchantment",
    level=5,
    school=SpellSchool.ABJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="Instantaneous",
    effect_callback=_break_enchantment_effect,
    description=(
        "This spell frees victims from enchantments, transmutations, and curses. "
        "Break enchantment can reverse even an instantaneous effect."
    ),
    subschool="",
    descriptor=[],
)

# -- Cleric Level 6 --

BLADE_BARRIER = Spell(
    name="Blade Barrier",
    level=6,
    school=SpellSchool.EVOCATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Medium (100 ft. + 10 ft./level)",
    duration="10 min./level",
    effect_callback=_blade_barrier_effect,
    description=(
        "An immobile, vertical curtain of whirling blades shaped of pure force "
        "springs into existence. Any creature passing through the wall takes "
        "1d6 points of damage per caster level (maximum 20d6), with a Reflex "
        "save for half damage."
    ),
    subschool="",
    descriptor=["Force"],
)

WORD_OF_RECALL = Spell(
    name="Word of Recall",
    level=6,
    school=SpellSchool.CONJURATION,
    components=[SpellComponent.VERBAL],
    range="Unlimited",
    duration="Instantaneous",
    effect_callback=_word_of_recall_effect,
    description=(
        "Word of recall teleports you instantly back to your sanctuary when "
        "the word is uttered."
    ),
    subschool="Teleportation",
    descriptor=[],
)

# -- Cleric Level 7 --

RESURRECTION = Spell(
    name="Resurrection",
    level=7,
    school=SpellSchool.CONJURATION,
    components=[
        SpellComponent.VERBAL, SpellComponent.SOMATIC,
        SpellComponent.MATERIAL, SpellComponent.DIVINE_FOCUS,
    ],
    range="Touch",
    duration="Instantaneous",
    effect_callback=_resurrection_effect,
    description=(
        "This spell functions like raise dead, except that you are able to "
        "restore life to any deceased creature. The creature can have been "
        "dead for as long as 10 years per caster level."
    ),
    subschool="Healing",
    descriptor=[],
)

# -- Cleric Level 9 --

MASS_HEAL = Spell(
    name="Mass Heal",
    level=9,
    school=SpellSchool.CONJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="Instantaneous",
    effect_callback=_mass_heal_effect,
    description=(
        "This spell functions like heal, except that it affects multiple "
        "creatures, and the maximum number of hit points restored to each "
        "is 250."
    ),
    subschool="Healing",
    descriptor=[],
)

# -- Paladin Level 1 --

DETECT_EVIL = Spell(
    name="Detect Evil",
    level=1,
    school=SpellSchool.DIVINATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.DIVINE_FOCUS],
    range="60 ft.",
    duration="Concentration, up to 10 min./level",
    effect_callback=_detect_evil_effect,
    description=(
        "You can sense the presence of evil. The amount of information revealed "
        "depends on how long you study a particular area or subject."
    ),
    subschool="",
    descriptor=[],
)

PROTECTION_FROM_EVIL = Spell(
    name="Protection from Evil",
    level=1,
    school=SpellSchool.ABJURATION,
    components=[
        SpellComponent.VERBAL, SpellComponent.SOMATIC,
        SpellComponent.MATERIAL, SpellComponent.DIVINE_FOCUS,
    ],
    range="Touch",
    duration="1 min./level",
    effect_callback=_protection_from_evil_effect,
    description=(
        "This spell wards a creature from attacks by evil creatures, from "
        "mental control, and from summoned creatures. It creates a magical "
        "barrier around the subject at a distance of 1 foot."
    ),
    subschool="",
    descriptor=["Good"],
)

BLESS_WEAPON = Spell(
    name="Bless Weapon",
    level=1,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Touch",
    duration="1 min./level",
    effect_callback=_bless_weapon_effect,
    description=(
        "This transmutation makes a weapon strike true against evil foes. "
        "The weapon is treated as having a +1 enhancement bonus for the "
        "purpose of bypassing the damage reduction of evil creatures."
    ),
    subschool="",
    descriptor=["Good"],
)

# -- Paladin Level 2 --

DELAY_POISON = Spell(
    name="Delay Poison",
    level=2,
    school=SpellSchool.CONJURATION,
    components=[
        SpellComponent.VERBAL, SpellComponent.SOMATIC,
        SpellComponent.MATERIAL, SpellComponent.DIVINE_FOCUS,
    ],
    range="Touch",
    duration="1 hour/level",
    effect_callback=_delay_poison_effect,
    description=(
        "The subject becomes temporarily immune to poison. Any poison in its "
        "system or any poison to which it is exposed during the spell's duration "
        "does not affect the subject until the spell's duration has expired."
    ),
    subschool="Healing",
    descriptor=[],
)

SHIELD_OTHER = Spell(
    name="Shield Other",
    level=2,
    school=SpellSchool.ABJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.FOCUS],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="1 hour/level",
    effect_callback=_shield_other_effect,
    description=(
        "This spell wards the subject and creates a mystic connection between "
        "you and the subject so that some of its wounds are transferred to you. "
        "The subject gains a +1 deflection bonus to AC and a +1 resistance "
        "bonus on saves."
    ),
    subschool="",
    descriptor=[],
)

OWLS_WISDOM = Spell(
    name="Owl's Wisdom",
    level=2,
    school=SpellSchool.TRANSMUTATION,
    components=[
        SpellComponent.VERBAL, SpellComponent.SOMATIC,
        SpellComponent.MATERIAL, SpellComponent.DIVINE_FOCUS,
    ],
    range="Touch",
    duration="1 min./level",
    effect_callback=_owls_wisdom_effect,
    description=(
        "The transmuted creature becomes wiser. The spell grants a +4 "
        "enhancement bonus to Wisdom, adding the usual benefits to Wisdom-related skills."
    ),
    subschool="",
    descriptor=[],
)

# -- Paladin Level 3 --

DAYLIGHT = Spell(
    name="Daylight",
    level=3,
    school=SpellSchool.EVOCATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Touch",
    duration="10 min./level",
    effect_callback=_daylight_effect,
    description=(
        "The object touched sheds light as bright as full daylight in a "
        "60-foot radius, and dim light for an additional 60 feet beyond that. "
        "Creatures that take penalties in bright light also take them while "
        "within the radius of this magical light."
    ),
    subschool="",
    descriptor=["Light"],
)

REMOVE_BLINDNESS_DEAFNESS = Spell(
    name="Remove Blindness/Deafness",
    level=3,
    school=SpellSchool.CONJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Touch",
    duration="Instantaneous",
    effect_callback=_remove_blindness_deafness_effect,
    description=(
        "Remove blindness/deafness cures blindness or deafness (your choice), "
        "whether the effect is normal or magical in nature."
    ),
    subschool="Healing",
    descriptor=[],
)

# -- Paladin Level 4 --

HOLY_SWORD = Spell(
    name="Holy Sword",
    level=4,
    school=SpellSchool.EVOCATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Touch",
    duration="1 round/level",
    effect_callback=_holy_sword_effect,
    description=(
        "This spell allows you to channel holy power into your sword, or any "
        "other melee weapon you choose. The weapon acts as a +5 holy weapon "
        "(+2d6 damage against evil creatures)."
    ),
    subschool="",
    descriptor=["Good"],
)

MARK_OF_JUSTICE = Spell(
    name="Mark of Justice",
    level=4,
    school=SpellSchool.NECROMANCY,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.DIVINE_FOCUS],
    range="Touch",
    duration="Permanent",
    effect_callback=_mark_of_justice_effect,
    description=(
        "You draw a visible mark on the subject and state some behavior on "
        "the part of the subject that will activate the mark."
    ),
    subschool="",
    descriptor=[],
)

DISPEL_EVIL = Spell(
    name="Dispel Evil",
    level=4,
    school=SpellSchool.ABJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.DIVINE_FOCUS],
    range="Personal",
    duration="1 round/level or until expended",
    effect_callback=_dispel_evil_effect,
    description=(
        "Shimmering, white holy energy surrounds you. This energy has three "
        "effects. First, you gain a +4 deflection bonus to AC against attacks "
        "by evil creatures."
    ),
    subschool="",
    descriptor=["Good"],
)

HOLY_AURA = Spell(
    name="Holy Aura",
    level=4,
    school=SpellSchool.ABJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.FOCUS],
    range="20 ft.",
    duration="1 round/level",
    effect_callback=_holy_aura_effect,
    description=(
        "A brilliant divine radiance surrounds the subjects, protecting them "
        "from attacks, granting them resistance to spells cast by evil creatures, "
        "and causing evil creatures to become blinded when they strike the subjects."
    ),
    subschool="",
    descriptor=["Good"],
)


# ---------------------------------------------------------------------------
# Phase 4: Druid & Ranger Nature Spells – effect callbacks
# ---------------------------------------------------------------------------

# -- Druid Level 0 --

def _flare_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"penalty": -1, "duration_minutes": 1, "save": "Fortitude negates"}


def _know_direction_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"reveals": "north direction"}


def _cure_minor_wounds_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"healing": 1}


def _detect_animals_or_plants_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"detects": ["animals", "plants"], "range_ft": 60}


def _shillelagh_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"enhancement_bonus": 1, "damage_die": "2d6", "duration_minutes": caster_level}


def _mending_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"repairs_hp": "1d4", "target": "object"}


# -- Druid Level 1 --

def _entangle_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "area": "40-ft radius",
        "save": "Reflex negates",
        "escape": "Strength or Escape Artist DC 20",
        "duration_minutes": caster_level,
    }


def _faerie_fire_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "attack_bonus_against": 2,
        "negates_invisibility": True,
        "duration_minutes": caster_level,
    }


def _longstrider_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"speed_bonus_ft": 10, "bonus_type": "enhancement", "duration_hours": caster_level}


def _speak_with_animals_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"communicates_with": "animals", "duration_minutes": caster_level}


def _animal_friendship_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"animal_only": True, "max_hd": caster_level}


def _produce_flame_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    bonus = min(caster_level, 5)
    return {
        "melee_bonus": bonus,
        "damage": f"1d6+{bonus}",
        "damage_type": "Fire",
        "duration_minutes": caster_level,
    }


# -- Druid Level 2 --

def _barkskin_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    bonus = min(2 + (caster_level - 3) // 3, 5)
    return {
        "natural_armor_bonus": bonus,
        "bonus_type": "natural armor",
        "duration_minutes": caster_level * 10,
    }


def _call_lightning_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "damage_indoor": "3d6",
        "damage_outdoor": "3d10",
        "bolts_available": caster_level,
        "save": "Reflex half",
    }


def _charm_animal_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"animal_only": True, "duration_hours": caster_level, "save": "Will negates"}


def _warp_wood_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"cubic_feet": caster_level, "destroys_wooden_weapons": True}


def _flame_blade_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "damage": f"1d8+{min(caster_level // 2, 10)}",
        "damage_type": "Fire",
        "duration_minutes": caster_level,
    }


def _tree_shape_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"form": "Medium tree", "can_observe": True, "duration_hours": caster_level}


# -- Druid Level 3 --

def _contagion_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"disease": "one of 6 diseases", "incubation": "1d3 days", "save": "Fortitude negates"}


def _water_breathing_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"targets": "1 creature/level", "duration_hours": caster_level * 2}


def _poison_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "initial_damage": "1d10 Con",
        "secondary_damage": "1d10 Con",
        "save": "Fortitude half",
        "attack": "touch",
    }


def _spike_growth_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "area_per_level": "20 sq ft",
        "damage_per_5ft": "1d4",
        "speed_reduced": True,
        "duration_hours": caster_level,
    }


def _quench_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "extinguishes_fires": True,
        "fire_creature_damage": f"{min(caster_level, 10)}d6",
        "area": "20-ft radius",
    }


# -- Druid Level 4 --

def _rusting_grasp_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"destroys_metal": True, "attack": "touch", "damage_to_creature": "3d6"}


def _command_plants_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"targets": "plant creatures", "save": "Will negates", "duration_days": caster_level}


def _reincarnate_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"new_body": "random race", "soul_restored": True, "material_cost_gp": 1000}


def _repel_vermin_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "radius_ft": 10,
        "save": "Will negates (intelligent)",
        "duration_minutes": caster_level * 10,
    }


# -- Druid Level 5 --

def _animal_growth_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "targets": "1 animal per 2 levels",
        "str_bonus": 8,
        "con_bonus": 4,
        "natural_armor": 2,
        "duration_minutes": caster_level,
    }


def _awaken_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"grants_intelligence": True, "xp_cost": 250 * 5, "target": "animal or tree"}


def _wall_of_fire_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "proximity_10ft_damage": "2d4",
        "proximity_20ft_damage": "1d4",
        "pass_through_damage": f"2d6+{min(caster_level, 20)}",
        "damage_type": "Fire",
    }


def _call_lightning_storm_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "damage_per_bolt": "5d6",
        "save": "Reflex half",
        "bolts_available": caster_level,
        "duration_minutes": caster_level * 10,
    }


# -- Druid Level 6 --

def _antilife_shell_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "radius_ft": 10,
        "excludes": "living creatures",
        "duration_minutes": caster_level * 10,
    }


def _liveoak_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"animates_oak": True, "sentry": True, "duration_days": caster_level}


# -- Druid Level 7 --

def _control_weather_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "radius_miles": 2,
        "duration_hours": "4d12",
        "weather_types": ["clear", "hot", "cold", "rain", "snow", "sleet", "hail", "hurricane"],
    }


# -- Druid Level 8 --

def _earthquake_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "area": "80-ft radius",
        "duration_rounds": 1,
        "collapses_structures": True,
        "fissures": True,
    }


# -- Druid Level 9 --

def _elemental_swarm_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "phase_1": "2d4 Large elementals",
        "phase_2": "1d4 Huge elementals",
        "phase_3": "1 Elder elemental",
        "duration_minutes": caster_level * 10,
    }


def _storm_of_vengeance_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "area": "360-ft radius",
        "max_rounds": 10,
        "effects": ["acid rain", "lightning", "hail", "divine fire"],
    }


# -- Ranger Level 1 --

def _alarm_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"radius_ft": 20, "mental_or_audible": True, "duration_hours": 8}


def _animal_messenger_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"animal_size": "Tiny", "duration_days": caster_level}


def _jump_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"jump_bonus": min(10 * ((caster_level + 2) // 3), 30), "duration_minutes": caster_level}


# -- Ranger Level 2 --

def _snare_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"trigger": "touch", "reflex_dc": 23, "holds_creature": True}


def _pass_without_trace_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"leaves_no_tracks": True, "leaves_no_scent": True, "duration_hours": caster_level}


def _wind_wall_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "deflects_arrows": True,
        "deflects_gases": True,
        "deflects_tiny": True,
        "duration_rounds": caster_level,
    }


# -- Ranger Level 3 --

def _heal_animal_companion_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"healing": min(caster_level * 10, 150), "animal_companion_only": True}


def _remove_disease_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"removes_disease": True, "magical_diseases": True}


# -- Ranger Level 4 --

def _commune_with_nature_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {
        "range_miles": caster_level,
        "reveals": ["terrain", "bodies of water", "plants", "animals", "minerals"],
    }


def _tree_stride_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"range_miles": 3, "teleport_between_trees": True, "duration_hours": caster_level}


def _find_the_path_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"shows_path": True, "avoids_obstacles": True, "duration_minutes": caster_level * 10}


# ---------------------------------------------------------------------------
# Phase 4: Druid & Ranger Nature Spells – Spell constants
# ---------------------------------------------------------------------------

# -- Druid Level 0 (orisons) --

FLARE = Spell(
    name="Flare",
    level=0,
    school=SpellSchool.EVOCATION,
    components=[SpellComponent.VERBAL],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="Instantaneous",
    effect_callback=_flare_effect,
    description=(
        "Dazzles one creature, imposing a -1 penalty on attack rolls for 1 minute "
        "(Fortitude negates)."
    ),
    subschool="",
    descriptor=["Fire"],
)

KNOW_DIRECTION = Spell(
    name="Know Direction",
    level=0,
    school=SpellSchool.DIVINATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Personal",
    duration="Instantaneous",
    effect_callback=_know_direction_effect,
    description="You instantly know which direction is north.",
    subschool="",
    descriptor=[],
)

CURE_MINOR_WOUNDS = Spell(
    name="Cure Minor Wounds",
    level=0,
    school=SpellSchool.CONJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Touch",
    duration="Instantaneous",
    effect_callback=_cure_minor_wounds_effect,
    description="Cures 1 point of damage.",
    subschool="Healing",
    descriptor=[],
)

DETECT_ANIMALS_OR_PLANTS = Spell(
    name="Detect Animals or Plants",
    level=0,
    school=SpellSchool.DIVINATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="60 ft. cone",
    duration="Concentration, up to 10 min./level",
    effect_callback=_detect_animals_or_plants_effect,
    description="Detects kinds of animals or plants within a 60-ft. cone.",
    subschool="",
    descriptor=[],
)

SHILLELAGH = Spell(
    name="Shillelagh",
    level=0,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.DIVINE_FOCUS],
    range="Touch",
    duration="1 min./level",
    effect_callback=_shillelagh_effect,
    description="Your club or quarterstaff becomes +1 magical and deals 2d6 damage.",
    subschool="",
    descriptor=[],
)

MENDING = Spell(
    name="Mending",
    level=0,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="10 ft.",
    duration="Instantaneous",
    effect_callback=_mending_effect,
    description="Repairs 1d4 hit points of damage to an object.",
    subschool="",
    descriptor=[],
)

# -- Druid Level 1 --

ENTANGLE = Spell(
    name="Entangle",
    level=1,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.DIVINE_FOCUS],
    range="Long (400 ft. + 40 ft./level)",
    duration="1 min./level",
    effect_callback=_entangle_effect,
    description=(
        "Plants entangle creatures in a 40-ft. radius (Reflex negates); "
        "escape requires Strength or Escape Artist DC 20."
    ),
    subschool="",
    descriptor=[],
)

FAERIE_FIRE = Spell(
    name="Faerie Fire",
    level=1,
    school=SpellSchool.EVOCATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.DIVINE_FOCUS],
    range="Long (400 ft. + 40 ft./level)",
    duration="1 min./level",
    effect_callback=_faerie_fire_effect,
    description=(
        "Outlines subjects with pale fire, granting +2 attack bonus against them "
        "and negating invisibility."
    ),
    subschool="",
    descriptor=[],
)

LONGSTRIDER = Spell(
    name="Longstrider",
    level=1,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="Personal",
    duration="1 hour/level",
    effect_callback=_longstrider_effect,
    description="Your speed increases by 10 feet (enhancement bonus).",
    subschool="",
    descriptor=[],
)

SPEAK_WITH_ANIMALS = Spell(
    name="Speak with Animals",
    level=1,
    school=SpellSchool.DIVINATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Personal",
    duration="1 min./level",
    effect_callback=_speak_with_animals_effect,
    description="You can communicate verbally and mentally with animals.",
    subschool="",
    descriptor=[],
)

ANIMAL_FRIENDSHIP = Spell(
    name="Animal Friendship",
    level=1,
    school=SpellSchool.ENCHANTMENT,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="Instantaneous",
    effect_callback=_animal_friendship_effect,
    description="Makes an animal permanently friendly toward you.",
    subschool="Charm",
    descriptor=["Animal", "Mind-Affecting"],
)

PRODUCE_FLAME = Spell(
    name="Produce Flame",
    level=1,
    school=SpellSchool.EVOCATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Personal",
    duration="1 min./level",
    effect_callback=_produce_flame_effect,
    description="Flames appear in your hand; melee or thrown attack deals 1d6+min(CL,5) fire damage.",
    subschool="",
    descriptor=["Fire"],
)

# -- Druid Level 2 --

BARKSKIN = Spell(
    name="Barkskin",
    level=2,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.DIVINE_FOCUS],
    range="Touch",
    duration="10 min./level",
    effect_callback=_barkskin_effect,
    description=(
        "Grants +2 natural armor bonus, increasing by +1 per 3 caster levels above 3rd "
        "(maximum +5)."
    ),
    subschool="",
    descriptor=[],
)

CALL_LIGHTNING = Spell(
    name="Call Lightning",
    level=2,
    school=SpellSchool.CONJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Medium (100 ft. + 10 ft./level)",
    duration="1 min./level",
    effect_callback=_call_lightning_effect,
    description="Calls lightning bolts dealing 3d6 (indoors) or 3d10 (outdoors) per bolt.",
    subschool="Summoning",
    descriptor=["Electricity"],
)

CHARM_ANIMAL = Spell(
    name="Charm Animal",
    level=2,
    school=SpellSchool.ENCHANTMENT,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="1 hour/level",
    effect_callback=_charm_animal_effect,
    description="Makes one animal your ally (Will negates).",
    subschool="Charm",
    descriptor=["Animal", "Mind-Affecting"],
)

WARP_WOOD = Spell(
    name="Warp Wood",
    level=2,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="Instantaneous",
    effect_callback=_warp_wood_effect,
    description="Bends and warps 1 cu. ft. of wood per caster level.",
    subschool="",
    descriptor=[],
)

FLAME_BLADE = Spell(
    name="Flame Blade",
    level=2,
    school=SpellSchool.EVOCATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.DIVINE_FOCUS],
    range="Personal",
    duration="1 min./level",
    effect_callback=_flame_blade_effect,
    description="A blade of fire deals 1d8+min(CL/2,10) fire damage.",
    subschool="",
    descriptor=["Fire"],
)

TREE_SHAPE = Spell(
    name="Tree Shape",
    level=2,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="Personal",
    duration="1 hour/level",
    effect_callback=_tree_shape_effect,
    description="You appear as a Medium tree while retaining the ability to observe your surroundings.",
    subschool="",
    descriptor=[],
)

# -- Druid Level 3 --

CONTAGION = Spell(
    name="Contagion",
    level=3,
    school=SpellSchool.NECROMANCY,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Touch",
    duration="Instantaneous",
    effect_callback=_contagion_effect,
    description="Infects subject with a chosen disease (Fortitude negates).",
    subschool="",
    descriptor=["Evil"],
)

WATER_BREATHING = Spell(
    name="Water Breathing",
    level=3,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="Touch",
    duration="2 hours/level",
    effect_callback=_water_breathing_effect,
    description="Touched subjects can breathe underwater.",
    subschool="",
    descriptor=[],
)

POISON = Spell(
    name="Poison",
    level=3,
    school=SpellSchool.NECROMANCY,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.DIVINE_FOCUS],
    range="Touch",
    duration="Instantaneous",
    effect_callback=_poison_effect,
    description=(
        "Touch attack deals 1d10 Constitution damage (Fortitude half), "
        "with the same secondary damage 1 round later."
    ),
    subschool="",
    descriptor=["Poison"],
)

SPIKE_GROWTH = Spell(
    name="Spike Growth",
    level=3,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.DIVINE_FOCUS],
    range="Medium (100 ft. + 10 ft./level)",
    duration="1 hour/level",
    effect_callback=_spike_growth_effect,
    description="Spikes on the ground deal 1d4 damage per 5 ft. moved through and slow movement.",
    subschool="",
    descriptor=["Force"],
)

QUENCH = Spell(
    name="Quench",
    level=3,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.DIVINE_FOCUS],
    range="Medium (100 ft. + 10 ft./level)",
    duration="Instantaneous",
    effect_callback=_quench_effect,
    description=(
        "Extinguishes all nonmagical fires in a 20-ft. radius; "
        "deals 1d6/level (max 10d6) to fire creatures."
    ),
    subschool="",
    descriptor=[],
)

# -- Druid Level 4 --

RUSTING_GRASP = Spell(
    name="Rusting Grasp",
    level=4,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.DIVINE_FOCUS],
    range="Touch",
    duration="See text",
    effect_callback=_rusting_grasp_effect,
    description="Destroys ferrous metal on touch; deals 3d6 to iron-based creatures.",
    subschool="",
    descriptor=[],
)

COMMAND_PLANTS = Spell(
    name="Command Plants",
    level=4,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="1 day/level",
    effect_callback=_command_plants_effect,
    description="Controls the actions of plant creatures (Will negates).",
    subschool="",
    descriptor=["Plant", "Mind-Affecting"],
)

REINCARNATE = Spell(
    name="Reincarnate",
    level=4,
    school=SpellSchool.TRANSMUTATION,
    components=[
        SpellComponent.VERBAL, SpellComponent.SOMATIC,
        SpellComponent.MATERIAL, SpellComponent.DIVINE_FOCUS,
    ],
    range="Touch",
    duration="Instantaneous",
    effect_callback=_reincarnate_effect,
    description="Returns a dead soul in a new body of a randomly determined race (1,000 gp material cost).",
    subschool="",
    descriptor=[],
)

REPEL_VERMIN = Spell(
    name="Repel Vermin",
    level=4,
    school=SpellSchool.ABJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.DIVINE_FOCUS],
    range="10 ft.",
    duration="10 min./level",
    effect_callback=_repel_vermin_effect,
    description=(
        "Insects, spiders, and other vermin cannot enter a 10-ft. radius "
        "(Will negates for intelligent vermin)."
    ),
    subschool="",
    descriptor=[],
)

# -- Druid Level 5 --

ANIMAL_GROWTH = Spell(
    name="Animal Growth",
    level=5,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Medium (100 ft. + 10 ft./level)",
    duration="1 min./level",
    effect_callback=_animal_growth_effect,
    description=(
        "One animal per two levels grows one size category "
        "(STR +8, CON +4, +2 natural armor)."
    ),
    subschool="",
    descriptor=[],
)

AWAKEN = Spell(
    name="Awaken",
    level=5,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="Touch",
    duration="Instantaneous",
    effect_callback=_awaken_effect,
    description="Bestows human-level intelligence on an animal or tree (250 XP per HD cost).",
    subschool="",
    descriptor=[],
)

WALL_OF_FIRE = Spell(
    name="Wall of Fire",
    level=5,
    school=SpellSchool.EVOCATION,
    components=[
        SpellComponent.VERBAL, SpellComponent.SOMATIC,
        SpellComponent.MATERIAL, SpellComponent.DIVINE_FOCUS,
    ],
    range="Medium (100 ft. + 10 ft./level)",
    duration="Concentration + 1 round/level",
    effect_callback=_wall_of_fire_effect,
    description=(
        "Wall of fire deals 2d4 fire within 10 ft., 1d4 within 20 ft., "
        "and 2d6+CL to pass through."
    ),
    subschool="",
    descriptor=["Fire"],
)

CALL_LIGHTNING_STORM = Spell(
    name="Call Lightning Storm",
    level=5,
    school=SpellSchool.CONJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Medium (100 ft. + 10 ft./level)",
    duration="10 min./level",
    effect_callback=_call_lightning_storm_effect,
    description="Like Call Lightning but deals 5d6 per bolt and works anywhere.",
    subschool="Summoning",
    descriptor=["Electricity"],
)

# -- Druid Level 6 --

ANTILIFE_SHELL = Spell(
    name="Antilife Shell",
    level=6,
    school=SpellSchool.ABJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.DIVINE_FOCUS],
    range="10 ft.",
    duration="10 min./level",
    effect_callback=_antilife_shell_effect,
    description="Keeps living creatures out of a 10-ft. radius.",
    subschool="",
    descriptor=[],
)

LIVEOAK = Spell(
    name="Liveoak",
    level=6,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Touch",
    duration="1 day/level",
    effect_callback=_liveoak_effect,
    description="Imbues a Large oak tree with sentry power (animates like a treant).",
    subschool="",
    descriptor=[],
)

# -- Druid Level 7 --

CONTROL_WEATHER = Spell(
    name="Control Weather",
    level=7,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="2 miles",
    duration="4d12 hours",
    effect_callback=_control_weather_effect,
    description="Changes the weather in a 2-mile radius.",
    subschool="",
    descriptor=[],
)

# -- Druid Level 8 --

EARTHQUAKE = Spell(
    name="Earthquake",
    level=8,
    school=SpellSchool.EVOCATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.DIVINE_FOCUS],
    range="Long (400 ft. + 40 ft./level)",
    duration="1 round",
    effect_callback=_earthquake_effect,
    description=(
        "Seismic disturbance in an 80-ft. radius collapses structures "
        "and opens fissures for 1 round."
    ),
    subschool="",
    descriptor=["Earth"],
)

# -- Druid Level 9 --

ELEMENTAL_SWARM = Spell(
    name="Elemental Swarm",
    level=9,
    school=SpellSchool.CONJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Medium (100 ft. + 10 ft./level)",
    duration="10 min./level",
    effect_callback=_elemental_swarm_effect,
    description=(
        "Summons 2d4 Large elementals, then 1d4 Huge elementals, "
        "then 1 Elder elemental in sequence."
    ),
    subschool="Summoning",
    descriptor=[],
)

STORM_OF_VENGEANCE = Spell(
    name="Storm of Vengeance",
    level=9,
    school=SpellSchool.CONJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Long (400 ft. + 40 ft./level)",
    duration="Concentration (maximum 10 rounds)",
    effect_callback=_storm_of_vengeance_effect,
    description=(
        "Massive storm with escalating effects over 10 rounds: "
        "acid rain, lightning, hail, and divine fire."
    ),
    subschool="Summoning",
    descriptor=[],
)

# -- Ranger Level 1 --

ALARM = Spell(
    name="Alarm",
    level=1,
    school=SpellSchool.ABJURATION,
    components=[
        SpellComponent.VERBAL, SpellComponent.SOMATIC,
        SpellComponent.FOCUS, SpellComponent.MATERIAL,
    ],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="8 hours",
    effect_callback=_alarm_effect,
    description="Wards an area to sound a mental or audible alarm when entered.",
    subschool="",
    descriptor=[],
)

ANIMAL_MESSENGER = Spell(
    name="Animal Messenger",
    level=1,
    school=SpellSchool.ENCHANTMENT,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="1 day/level",
    effect_callback=_animal_messenger_effect,
    description="Sends a Tiny animal to deliver your message.",
    subschool="Compulsion",
    descriptor=["Animal", "Mind-Affecting"],
)

JUMP = Spell(
    name="Jump",
    level=1,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="Touch",
    duration="1 min./level",
    effect_callback=_jump_effect,
    description="Subject gains an enhancement bonus on Jump checks (up to +30).",
    subschool="",
    descriptor=[],
)

# -- Ranger Level 2 --

SNARE = Spell(
    name="Snare",
    level=2,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.DIVINE_FOCUS],
    range="Touch",
    duration="Until triggered",
    effect_callback=_snare_effect,
    description="Creates a vine or rope snare (Reflex DC 23 or creature is held).",
    subschool="",
    descriptor=[],
)

PASS_WITHOUT_TRACE = Spell(
    name="Pass without Trace",
    level=2,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.DIVINE_FOCUS],
    range="Touch",
    duration="1 hour/level",
    effect_callback=_pass_without_trace_effect,
    description="One creature per level leaves no tracks or scent.",
    subschool="",
    descriptor=[],
)

WIND_WALL = Spell(
    name="Wind Wall",
    level=2,
    school=SpellSchool.EVOCATION,
    components=[
        SpellComponent.VERBAL, SpellComponent.SOMATIC,
        SpellComponent.MATERIAL, SpellComponent.DIVINE_FOCUS,
    ],
    range="Medium (100 ft. + 10 ft./level)",
    duration="1 round/level",
    effect_callback=_wind_wall_effect,
    description="Wall of wind deflects arrows, gas clouds, and Tiny or smaller creatures.",
    subschool="",
    descriptor=["Air"],
)

# -- Ranger Level 3 --

HEAL_ANIMAL_COMPANION = Spell(
    name="Heal Animal Companion",
    level=3,
    school=SpellSchool.CONJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Touch",
    duration="Instantaneous",
    effect_callback=_heal_animal_companion_effect,
    description="Heals 10 hit points per caster level (maximum 150) to an animal companion.",
    subschool="Healing",
    descriptor=[],
)

REMOVE_DISEASE = Spell(
    name="Remove Disease",
    level=3,
    school=SpellSchool.CONJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="Touch",
    duration="Instantaneous",
    effect_callback=_remove_disease_effect,
    description="Cures all diseases affecting subject, including magical diseases.",
    subschool="Healing",
    descriptor=[],
)

# -- Ranger Level 4 --

COMMUNE_WITH_NATURE = Spell(
    name="Commune with Nature",
    level=4,
    school=SpellSchool.DIVINATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Personal",
    duration="Instantaneous",
    effect_callback=_commune_with_nature_effect,
    description="Learn about terrain features (terrain, water, plants, animals, minerals) in a 1 mile/level radius.",
    subschool="",
    descriptor=[],
)

TREE_STRIDE = Spell(
    name="Tree Stride",
    level=4,
    school=SpellSchool.CONJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.DIVINE_FOCUS],
    range="Personal",
    duration="1 hour/level",
    effect_callback=_tree_stride_effect,
    description="Step into one tree and emerge from another of the same species within 3 miles.",
    subschool="Teleportation",
    descriptor=[],
)

FIND_THE_PATH = Spell(
    name="Find the Path",
    level=4,
    school=SpellSchool.DIVINATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="Personal or Touch",
    duration="10 min./level",
    effect_callback=_find_the_path_effect,
    description="Shows the shortest, most direct route to a named location.",
    subschool="",
    descriptor=[],
)


# ---------------------------------------------------------------------------
# Phase 5: Bard Arcane Spells – effect callbacks
# ---------------------------------------------------------------------------

def _dancing_lights_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"lights": 4, "light_type": "torch or lantern", "duration_minutes": caster_level}


def _lullaby_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"listen_penalty": -5, "will_vs_sleep_penalty": -2, "save": "Will negates",
            "duration_minutes": caster_level}


def _message_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"range": "Medium", "whisper_to_multiple": True,
            "duration_minutes": caster_level * 10}


def _open_close_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"opens": True, "closes": True, "max_weight_lbs": 30}


def _summon_instrument_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"instrument_type": "any common instrument", "duration_minutes": caster_level}


def _animate_rope_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"entangle": True, "rope_length_ft": caster_level, "duration_rounds": caster_level}


def _comprehend_languages_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"understands_all_languages": True, "duration_minutes": caster_level * 10}


def _expeditious_retreat_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"speed_bonus_ft": 30, "duration_minutes": caster_level}


def _hypnotism_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"hd_affected": f"2d4+{caster_level}", "save": "Will negates", "duration_rounds": "2d4"}


def _tashas_hideous_laughter_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"dex_penalty": -4, "incapacitated": True, "save": "Will negates",
            "duration_rounds": caster_level}


def _undetectable_alignment_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"conceals_alignment": True, "duration_hours": 24}


def _ventriloquism_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"duration_minutes": caster_level, "will_disbelief": True}


def _disguise_self_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"alters_appearance": True, "height_change_ft": 1,
            "duration_minutes": caster_level * 10}


def _alter_self_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"max_size": "Large", "gains_natural_armor": True,
            "duration_minutes": caster_level * 10}


def _cats_grace_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"dex_bonus": 4, "bonus_type": "enhancement", "duration_minutes": caster_level}


def _eagles_splendor_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"cha_bonus": 4, "bonus_type": "enhancement", "duration_minutes": caster_level}


def _enthrall_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"audience_enraptured": True, "save": "Will negates",
            "duration": "until speech ends (max 1 hour)"}


def _heroism_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"attack_bonus": 2, "save_bonus": 2, "skill_bonus": 2, "bonus_type": "morale",
            "duration_minutes": caster_level * 10}


def _locate_object_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"range": "Long (400 ft. + 40 ft./level)", "duration_minutes": caster_level}


def _minor_image_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"includes_sound": True, "will_disbelief": True}


def _misdirection_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"misleads_divination": True, "duration_hours": caster_level}


def _whispering_wind_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"range_miles": caster_level, "message_words": 25}


def _charm_monster_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"save": "Will negates", "duration_days": caster_level}


def _clairaudience_clairvoyance_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"range": "Long (400 ft. + 40 ft./level)", "choose": "hearing or vision",
            "duration_minutes": caster_level}


def _gaseous_form_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"fly_speed_ft": 10, "maneuverability": "perfect", "immune_to_physical": True,
            "duration_minutes": caster_level * 2}


def _good_hope_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"bonus": 2, "bonus_type": "morale", "duration_minutes": caster_level}


def _phantom_steed_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"hp": 7 + caster_level, "speed_ft": min(caster_level * 20, 240),
            "duration_hours": caster_level}


def _scrying_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"save": "Will negates (modified)", "duration_minutes": caster_level,
            "remote_viewing": True}


def _sculpt_sound_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"changes_sounds": True, "duration_hours": caster_level}


def _shout_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"damage": "5d6", "damage_type": "Sonic", "area": "30-ft cone",
            "save": "Reflex half", "deafen_rounds": "2d6"}


def _zone_of_silence_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"radius_ft": 5, "silence_outward": True, "duration_minutes": caster_level * 10}


def _modify_memory_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"memory_minutes": 5, "permanent": True, "save": "Will negates"}


def _greater_heroism_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"attack_bonus": 4, "save_bonus": 4, "skill_bonus": 4, "bonus_type": "morale",
            "temp_hp": caster_level, "immune_fear": True, "duration_minutes": caster_level}


def _mass_suggestion_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"targets": caster_level, "save": "Will negates", "duration_hours": caster_level}


def _mirage_arcana_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"area": "1-mile radius", "duration_hours": caster_level}


def _shadow_walk_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"speed_miles_per_hour": 50, "plane": "Shadow", "duration_hours": caster_level}


def _song_of_discord_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"area": "20-ft radius", "save": "Will negates", "attack_allies": True,
            "duration_rounds": caster_level}


def _greater_scrying_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"duration_hours": caster_level, "save": "Will negates (modified)",
            "better_success": True}


def _irresistible_dance_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"no_save": True, "duration_rounds": "1d4+1", "dancing": True}


def _mass_charm_monster_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"targets": caster_level, "save": "Will negates", "duration_days": caster_level}


def _sympathetic_vibration_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"damage_per_round": "2d10", "damage_type": "Sonic",
            "target": "freestanding structure", "duration_rounds": caster_level}


def _veil_effect(caster: Any, target: Any, caster_level: int) -> Dict[str, Any]:
    return {"targets": caster_level, "will_disbelief": True, "duration_hours": caster_level}


# ---------------------------------------------------------------------------
# Phase 5: Bard Arcane Spells – Spell constants
# ---------------------------------------------------------------------------

DANCING_LIGHTS = Spell(
    name="Dancing Lights",
    level=0,
    school=SpellSchool.EVOCATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Medium (100 ft. + 10 ft./level)",
    duration="1 minute (D)",
    effect_callback=_dancing_lights_effect,
    description="Creates up to four lights resembling torches, lanterns, or glowing orbs.",
    subschool="",
    descriptor=["Light"],
)

LULLABY = Spell(
    name="Lullaby",
    level=0,
    school=SpellSchool.ENCHANTMENT,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Medium (100 ft. + 10 ft./level)",
    duration="Concentration + 1 round/level",
    effect_callback=_lullaby_effect,
    description="Makes subject drowsy; -5 on Listen checks, -2 on Will saves vs sleep.",
    subschool="Compulsion",
    descriptor=["Mind-Affecting"],
)

MESSAGE = Spell(
    name="Message",
    level=0,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.FOCUS],
    range="Medium (100 ft. + 10 ft./level)",
    duration="10 min./level",
    effect_callback=_message_effect,
    description="Whisper messages to designated creatures.",
    subschool="",
    descriptor=[],
)

OPEN_CLOSE = Spell(
    name="Open/Close",
    level=0,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.FOCUS],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="Instantaneous",
    effect_callback=_open_close_effect,
    description="Opens or closes small or light things.",
    subschool="",
    descriptor=[],
)

SUMMON_INSTRUMENT = Spell(
    name="Summon Instrument",
    level=0,
    school=SpellSchool.CONJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="0 ft.",
    duration="1 min./level (D)",
    effect_callback=_summon_instrument_effect,
    description="Summons a musical instrument to the caster's hands.",
    subschool="Summoning",
    descriptor=[],
)

ANIMATE_ROPE = Spell(
    name="Animate Rope",
    level=1,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Medium (100 ft. + 10 ft./level)",
    duration="1 round/level",
    effect_callback=_animate_rope_effect,
    description="Makes a rope move at your command, entangling a target.",
    subschool="",
    descriptor=[],
)

COMPREHEND_LANGUAGES = Spell(
    name="Comprehend Languages",
    level=1,
    school=SpellSchool.DIVINATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC,
                SpellComponent.MATERIAL, SpellComponent.FOCUS],
    range="Personal",
    duration="10 min./level",
    effect_callback=_comprehend_languages_effect,
    description="You understand all spoken and written languages.",
    subschool="",
    descriptor=[],
)

EXPEDITIOUS_RETREAT = Spell(
    name="Expeditious Retreat",
    level=1,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Personal",
    duration="1 min./level",
    effect_callback=_expeditious_retreat_effect,
    description="Your speed increases by 30 ft.",
    subschool="",
    descriptor=[],
)

HYPNOTISM = Spell(
    name="Hypnotism",
    level=1,
    school=SpellSchool.ENCHANTMENT,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="2d4 rounds",
    effect_callback=_hypnotism_effect,
    description="Fascinates 2d4 HD of creatures.",
    subschool="Compulsion",
    descriptor=["Mind-Affecting"],
)

TASHAS_HIDEOUS_LAUGHTER = Spell(
    name="Tasha's Hideous Laughter",
    level=1,
    school=SpellSchool.ENCHANTMENT,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="1 round/level",
    effect_callback=_tashas_hideous_laughter_effect,
    description="Subject loses actions for 1 round/level due to uncontrollable laughter.",
    subschool="Compulsion",
    descriptor=["Mind-Affecting"],
)

UNDETECTABLE_ALIGNMENT = Spell(
    name="Undetectable Alignment",
    level=1,
    school=SpellSchool.ABJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="24 hours",
    effect_callback=_undetectable_alignment_effect,
    description="Conceals alignment for 24 hours.",
    subschool="",
    descriptor=[],
)

VENTRILOQUISM = Spell(
    name="Ventriloquism",
    level=1,
    school=SpellSchool.ILLUSION,
    components=[SpellComponent.VERBAL, SpellComponent.FOCUS],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="1 min./level (D)",
    effect_callback=_ventriloquism_effect,
    description="Throws voice for 1 min./level.",
    subschool="Figment",
    descriptor=[],
)

DISGUISE_SELF = Spell(
    name="Disguise Self",
    level=1,
    school=SpellSchool.ILLUSION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Personal",
    duration="10 min./level (D)",
    effect_callback=_disguise_self_effect,
    description="Changes your appearance.",
    subschool="Glamer",
    descriptor=[],
)

ALTER_SELF = Spell(
    name="Alter Self",
    level=2,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="Personal",
    duration="10 min./level (D)",
    effect_callback=_alter_self_effect,
    description="Assume form of a similar creature.",
    subschool="",
    descriptor=[],
)

CATS_GRACE = Spell(
    name="Cat's Grace",
    level=2,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="Touch",
    duration="1 min./level",
    effect_callback=_cats_grace_effect,
    description="Subject gains +4 to DEX for 1 min./level.",
    subschool="",
    descriptor=[],
)

EAGLES_SPLENDOR = Spell(
    name="Eagle's Splendor",
    level=2,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC,
                SpellComponent.MATERIAL, SpellComponent.DIVINE_FOCUS],
    range="Touch",
    duration="1 min./level",
    effect_callback=_eagles_splendor_effect,
    description="Subject gains +4 to CHA for 1 min./level.",
    subschool="",
    descriptor=[],
)

ENTHRALL = Spell(
    name="Enthrall",
    level=2,
    school=SpellSchool.ENCHANTMENT,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Medium (100 ft. + 10 ft./level)",
    duration="1 hour or less",
    effect_callback=_enthrall_effect,
    description="Captivates all within 100 ft. + 10 ft./level.",
    subschool="Charm",
    descriptor=["Language-Dependent", "Mind-Affecting"],
)

HEROISM = Spell(
    name="Heroism",
    level=2,
    school=SpellSchool.ENCHANTMENT,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Touch",
    duration="10 min./level",
    effect_callback=_heroism_effect,
    description="Gives +2 morale bonus on attack rolls, saves, and skill checks.",
    subschool="Compulsion",
    descriptor=["Mind-Affecting"],
)

LOCATE_OBJECT = Spell(
    name="Locate Object",
    level=2,
    school=SpellSchool.DIVINATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC,
                SpellComponent.FOCUS, SpellComponent.DIVINE_FOCUS],
    range="Long (400 ft. + 40 ft./level)",
    duration="1 min./level",
    effect_callback=_locate_object_effect,
    description="Senses direction toward object (specific or type).",
    subschool="",
    descriptor=[],
)

MINOR_IMAGE = Spell(
    name="Minor Image",
    level=2,
    school=SpellSchool.ILLUSION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.FOCUS],
    range="Long (400 ft. + 40 ft./level)",
    duration="Concentration + 2 rounds",
    effect_callback=_minor_image_effect,
    description="As Silent Image, plus some sound.",
    subschool="Figment",
    descriptor=[],
)

MISDIRECTION = Spell(
    name="Misdirection",
    level=2,
    school=SpellSchool.ILLUSION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="1 hour/level",
    effect_callback=_misdirection_effect,
    description="Misleads divinations for one creature or object.",
    subschool="Glamer",
    descriptor=[],
)

WHISPERING_WIND = Spell(
    name="Whispering Wind",
    level=2,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="1 mile/level",
    duration="No limit or until discharged",
    effect_callback=_whispering_wind_effect,
    description="Sends a short message 1 mile/level.",
    subschool="",
    descriptor=["Air"],
)

CHARM_MONSTER = Spell(
    name="Charm Monster",
    level=3,
    school=SpellSchool.ENCHANTMENT,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="1 day/level",
    effect_callback=_charm_monster_effect,
    description="Makes monster believe it is your ally.",
    subschool="Charm",
    descriptor=["Mind-Affecting"],
)

CLAIRAUDIENCE_CLAIRVOYANCE = Spell(
    name="Clairaudience/Clairvoyance",
    level=3,
    school=SpellSchool.DIVINATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.FOCUS],
    range="Long (400 ft. + 40 ft./level)",
    duration="1 min./level (D)",
    effect_callback=_clairaudience_clairvoyance_effect,
    description="Hear or see at a distance for 1 min./level.",
    subschool="Scrying",
    descriptor=[],
)

GASEOUS_FORM = Spell(
    name="Gaseous Form",
    level=3,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.MATERIAL],
    range="Touch",
    duration="2 min./level (D)",
    effect_callback=_gaseous_form_effect,
    description="Subject and gear become insubstantial, misty, and translucent.",
    subschool="",
    descriptor=[],
)

GOOD_HOPE = Spell(
    name="Good Hope",
    level=3,
    school=SpellSchool.ENCHANTMENT,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Medium (100 ft. + 10 ft./level)",
    duration="1 min./level",
    effect_callback=_good_hope_effect,
    description="Subjects gain +2 morale bonus on saving throws, attack rolls, ability checks, skill checks, and weapon damage rolls.",
    subschool="Compulsion",
    descriptor=["Mind-Affecting"],
)

PHANTOM_STEED = Spell(
    name="Phantom Steed",
    level=3,
    school=SpellSchool.CONJURATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="0 ft.",
    duration="1 hour/level",
    effect_callback=_phantom_steed_effect,
    description="Magic horse appears for 1 hour/level.",
    subschool="Creation",
    descriptor=[],
)

SCRYING = Spell(
    name="Scrying",
    level=3,
    school=SpellSchool.DIVINATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC,
                SpellComponent.MATERIAL, SpellComponent.FOCUS],
    range="See text",
    duration="1 min./level",
    effect_callback=_scrying_effect,
    description="Spies on subject from a distance.",
    subschool="Scrying",
    descriptor=[],
)

SCULPT_SOUND = Spell(
    name="Sculpt Sound",
    level=3,
    school=SpellSchool.TRANSMUTATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="1 hour/level (D)",
    effect_callback=_sculpt_sound_effect,
    description="Creates new sounds or changes existing ones.",
    subschool="",
    descriptor=[],
)

SHOUT = Spell(
    name="Shout",
    level=4,
    school=SpellSchool.EVOCATION,
    components=[SpellComponent.VERBAL],
    range="30 ft.",
    duration="Instantaneous",
    effect_callback=_shout_effect,
    description="Deafens all within cone and deals 5d6 sonic damage.",
    subschool="",
    descriptor=["Sonic"],
)

ZONE_OF_SILENCE = Spell(
    name="Zone of Silence",
    level=4,
    school=SpellSchool.ILLUSION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Personal",
    duration="1 hour/level (D)",
    effect_callback=_zone_of_silence_effect,
    description="Keeps eavesdroppers from overhearing you.",
    subschool="Glamer",
    descriptor=[],
)

MODIFY_MEMORY = Spell(
    name="Modify Memory",
    level=4,
    school=SpellSchool.ENCHANTMENT,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="Permanent",
    effect_callback=_modify_memory_effect,
    description="Changes 5 minutes of subject's memories.",
    subschool="Compulsion",
    descriptor=["Mind-Affecting"],
)

GREATER_HEROISM = Spell(
    name="Greater Heroism",
    level=5,
    school=SpellSchool.ENCHANTMENT,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Touch",
    duration="1 min./level",
    effect_callback=_greater_heroism_effect,
    description="Gives +4 morale bonus on attack rolls, saves, and skill checks, and 1 temporary HP/level; immunity to fear.",
    subschool="Compulsion",
    descriptor=["Mind-Affecting"],
)

MASS_SUGGESTION = Spell(
    name="Mass Suggestion",
    level=5,
    school=SpellSchool.ENCHANTMENT,
    components=[SpellComponent.VERBAL, SpellComponent.MATERIAL],
    range="Medium (100 ft. + 10 ft./level)",
    duration="1 hour/level or until completed",
    effect_callback=_mass_suggestion_effect,
    description="Compels subjects to follow stated course of action.",
    subschool="Compulsion",
    descriptor=["Language-Dependent", "Mind-Affecting"],
)

MIRAGE_ARCANA = Spell(
    name="Mirage Arcana",
    level=5,
    school=SpellSchool.ILLUSION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Long (400 ft. + 40 ft./level)",
    duration="Concentration + 1 hour/level (D)",
    effect_callback=_mirage_arcana_effect,
    description="Makes terrain look like other terrain.",
    subschool="Glamer",
    descriptor=[],
)

SHADOW_WALK = Spell(
    name="Shadow Walk",
    level=5,
    school=SpellSchool.ILLUSION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Touch",
    duration="1 hour/level (D)",
    effect_callback=_shadow_walk_effect,
    description="Step into shadow to travel rapidly.",
    subschool="Shadow",
    descriptor=[],
)

SONG_OF_DISCORD = Spell(
    name="Song of Discord",
    level=5,
    school=SpellSchool.ENCHANTMENT,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Medium (100 ft. + 10 ft./level)",
    duration="1 round/level",
    effect_callback=_song_of_discord_effect,
    description="Forces targets to attack each other.",
    subschool="Compulsion",
    descriptor=["Mind-Affecting"],
)

GREATER_SCRYING = Spell(
    name="Greater Scrying",
    level=6,
    school=SpellSchool.DIVINATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="See text",
    duration="1 hour/level",
    effect_callback=_greater_scrying_effect,
    description="As scrying, but faster and longer.",
    subschool="Scrying",
    descriptor=[],
)

IRRESISTIBLE_DANCE = Spell(
    name="Irresistible Dance",
    level=6,
    school=SpellSchool.ENCHANTMENT,
    components=[SpellComponent.VERBAL],
    range="Touch",
    duration="1d4+1 rounds",
    effect_callback=_irresistible_dance_effect,
    description="Forces subject to dance.",
    subschool="Compulsion",
    descriptor=["Mind-Affecting"],
)

MASS_CHARM_MONSTER = Spell(
    name="Mass Charm Monster",
    level=6,
    school=SpellSchool.ENCHANTMENT,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Close (25 ft. + 5 ft./2 levels)",
    duration="1 day/level",
    effect_callback=_mass_charm_monster_effect,
    description="As charm monster, but all within 30 ft.",
    subschool="Charm",
    descriptor=["Mind-Affecting"],
)

SYMPATHETIC_VIBRATION = Spell(
    name="Sympathetic Vibration",
    level=6,
    school=SpellSchool.EVOCATION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC, SpellComponent.FOCUS],
    range="Touch",
    duration="Up to 1 round/level",
    effect_callback=_sympathetic_vibration_effect,
    description="Deals 2d10 sonic damage per round to a freestanding structure.",
    subschool="",
    descriptor=["Sonic"],
)

VEIL = Spell(
    name="Veil",
    level=6,
    school=SpellSchool.ILLUSION,
    components=[SpellComponent.VERBAL, SpellComponent.SOMATIC],
    range="Long (400 ft. + 40 ft./level)",
    duration="Concentration + 1 hour/level (D)",
    effect_callback=_veil_effect,
    description="Changes appearance of a group of creatures.",
    subschool="Glamer",
    descriptor=[],
)


def create_default_registry() -> SpellRegistry:
    """Create a :class:`SpellRegistry` pre-loaded with SRD core spells.

    Returns:
        A registry containing all Phase 0 foundational spells, the Phase 1
        Wizard/Sorcerer arcane spells (levels 0–3), the Phase 2
        Wizard/Sorcerer arcane spells (levels 4–9), the Phase 3
        Cleric/Paladin divine spells, the Phase 4 Druid/Ranger nature
        spells, and the Phase 5 Bard arcane spells, for a total of 229
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

    # ---- Phase 3: Cleric Level 0 (6) ----
    registry.register(GUIDANCE)
    registry.register(VIRTUE)
    registry.register(INFLICT_MINOR_WOUNDS)
    registry.register(DETECT_UNDEAD)
    registry.register(CREATE_WATER)
    registry.register(PURIFY_FOOD_AND_DRINK)

    # ---- Phase 3: Cleric Level 1 (5) ----
    registry.register(COMMAND)
    registry.register(SANCTUARY)
    registry.register(DIVINE_FAVOR)
    registry.register(DOOM)
    registry.register(ENTROPIC_SHIELD)

    # ---- Phase 3: Cleric Level 2 (7) ----
    registry.register(CURE_MODERATE_WOUNDS)
    registry.register(SILENCE)
    registry.register(SPIRITUAL_WEAPON)
    registry.register(CONSECRATE)
    registry.register(AID)
    registry.register(DESECRATE)
    registry.register(BLINDNESS_DEAFNESS)

    # ---- Phase 3: Cleric Level 3 (5) ----
    registry.register(CURE_SERIOUS_WOUNDS)
    registry.register(PRAYER)
    registry.register(SEARING_LIGHT)
    registry.register(SPEAK_WITH_DEAD)
    registry.register(INFLICT_SERIOUS_WOUNDS)

    # ---- Phase 3: Cleric Level 4 (5) ----
    registry.register(CURE_CRITICAL_WOUNDS)
    registry.register(DIVINE_POWER)
    registry.register(FREEDOM_OF_MOVEMENT)
    registry.register(NEUTRALIZE_POISON)
    registry.register(RESTORATION)

    # ---- Phase 3: Cleric Level 5 (4) ----
    registry.register(FLAME_STRIKE)
    registry.register(INSECT_PLAGUE)
    registry.register(RIGHTEOUS_MIGHT)
    registry.register(BREAK_ENCHANTMENT)

    # ---- Phase 3: Cleric Level 6 (2) ----
    registry.register(BLADE_BARRIER)
    registry.register(WORD_OF_RECALL)

    # ---- Phase 3: Cleric Level 7 (1) ----
    registry.register(RESURRECTION)

    # ---- Phase 3: Cleric Level 9 (1) ----
    registry.register(MASS_HEAL)

    # ---- Phase 3: Paladin Level 1 (3) ----
    registry.register(DETECT_EVIL)
    registry.register(PROTECTION_FROM_EVIL)
    registry.register(BLESS_WEAPON)

    # ---- Phase 3: Paladin Level 2 (3) ----
    registry.register(DELAY_POISON)
    registry.register(SHIELD_OTHER)
    registry.register(OWLS_WISDOM)

    # ---- Phase 3: Paladin Level 3 (2) ----
    registry.register(DAYLIGHT)
    registry.register(REMOVE_BLINDNESS_DEAFNESS)

    # ---- Phase 3: Paladin Level 4 (4) ----
    registry.register(HOLY_SWORD)
    registry.register(MARK_OF_JUSTICE)
    registry.register(DISPEL_EVIL)
    registry.register(HOLY_AURA)

    # ---- Phase 4: Druid Level 0 orisons (6) ----
    registry.register(FLARE)
    registry.register(KNOW_DIRECTION)
    registry.register(CURE_MINOR_WOUNDS)
    registry.register(DETECT_ANIMALS_OR_PLANTS)
    registry.register(SHILLELAGH)
    registry.register(MENDING)

    # ---- Phase 4: Druid Level 1 (6) ----
    registry.register(ENTANGLE)
    registry.register(FAERIE_FIRE)
    registry.register(LONGSTRIDER)
    registry.register(SPEAK_WITH_ANIMALS)
    registry.register(ANIMAL_FRIENDSHIP)
    registry.register(PRODUCE_FLAME)

    # ---- Phase 4: Druid Level 2 (6) ----
    registry.register(BARKSKIN)
    registry.register(CALL_LIGHTNING)
    registry.register(CHARM_ANIMAL)
    registry.register(WARP_WOOD)
    registry.register(FLAME_BLADE)
    registry.register(TREE_SHAPE)

    # ---- Phase 4: Druid Level 3 (5) ----
    registry.register(CONTAGION)
    registry.register(WATER_BREATHING)
    registry.register(POISON)
    registry.register(SPIKE_GROWTH)
    registry.register(QUENCH)

    # ---- Phase 4: Druid Level 4 (4) ----
    registry.register(RUSTING_GRASP)
    registry.register(COMMAND_PLANTS)
    registry.register(REINCARNATE)
    registry.register(REPEL_VERMIN)

    # ---- Phase 4: Druid Level 5 (4) ----
    registry.register(ANIMAL_GROWTH)
    registry.register(AWAKEN)
    registry.register(WALL_OF_FIRE)
    registry.register(CALL_LIGHTNING_STORM)

    # ---- Phase 4: Druid Level 6 (2) ----
    registry.register(ANTILIFE_SHELL)
    registry.register(LIVEOAK)

    # ---- Phase 4: Druid Level 7 (1) ----
    registry.register(CONTROL_WEATHER)

    # ---- Phase 4: Druid Level 8 (1) ----
    registry.register(EARTHQUAKE)

    # ---- Phase 4: Druid Level 9 (2) ----
    registry.register(ELEMENTAL_SWARM)
    registry.register(STORM_OF_VENGEANCE)

    # ---- Phase 4: Ranger Level 1 (3) ----
    registry.register(ALARM)
    registry.register(ANIMAL_MESSENGER)
    registry.register(JUMP)

    # ---- Phase 4: Ranger Level 2 (3) ----
    registry.register(SNARE)
    registry.register(PASS_WITHOUT_TRACE)
    registry.register(WIND_WALL)

    # ---- Phase 4: Ranger Level 3 (2) ----
    registry.register(HEAL_ANIMAL_COMPANION)
    registry.register(REMOVE_DISEASE)

    # ---- Phase 4: Ranger Level 4 (3) ----
    registry.register(COMMUNE_WITH_NATURE)
    registry.register(TREE_STRIDE)
    registry.register(FIND_THE_PATH)

    # ---- Phase 5: Bard Level 0 (5) ----
    registry.register(DANCING_LIGHTS)
    registry.register(LULLABY)
    registry.register(MESSAGE)
    registry.register(OPEN_CLOSE)
    registry.register(SUMMON_INSTRUMENT)

    # ---- Phase 5: Bard Level 1 (8) ----
    registry.register(ANIMATE_ROPE)
    registry.register(COMPREHEND_LANGUAGES)
    registry.register(EXPEDITIOUS_RETREAT)
    registry.register(HYPNOTISM)
    registry.register(TASHAS_HIDEOUS_LAUGHTER)
    registry.register(UNDETECTABLE_ALIGNMENT)
    registry.register(VENTRILOQUISM)
    registry.register(DISGUISE_SELF)

    # ---- Phase 5: Bard Level 2 (9) ----
    registry.register(ALTER_SELF)
    registry.register(CATS_GRACE)
    registry.register(EAGLES_SPLENDOR)
    registry.register(ENTHRALL)
    registry.register(HEROISM)
    registry.register(LOCATE_OBJECT)
    registry.register(MINOR_IMAGE)
    registry.register(MISDIRECTION)
    registry.register(WHISPERING_WIND)

    # ---- Phase 5: Bard Level 3 (7) ----
    registry.register(CHARM_MONSTER)
    registry.register(CLAIRAUDIENCE_CLAIRVOYANCE)
    registry.register(GASEOUS_FORM)
    registry.register(GOOD_HOPE)
    registry.register(PHANTOM_STEED)
    registry.register(SCRYING)
    registry.register(SCULPT_SOUND)

    # ---- Phase 5: Bard Level 4 (3) ----
    registry.register(SHOUT)
    registry.register(ZONE_OF_SILENCE)
    registry.register(MODIFY_MEMORY)

    # ---- Phase 5: Bard Level 5 (5) ----
    registry.register(GREATER_HEROISM)
    registry.register(MASS_SUGGESTION)
    registry.register(MIRAGE_ARCANA)
    registry.register(SHADOW_WALK)
    registry.register(SONG_OF_DISCORD)

    # ---- Phase 5: Bard Level 6 (5) ----
    registry.register(GREATER_SCRYING)
    registry.register(IRRESISTIBLE_DANCE)
    registry.register(MASS_CHARM_MONSTER)
    registry.register(SYMPATHETIC_VIBRATION)
    registry.register(VEIL)

    return registry
