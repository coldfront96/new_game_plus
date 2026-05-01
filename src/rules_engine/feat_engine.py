"""
src/rules_engine/feat_engine.py
-------------------------------
D&D 3.5e Feat Engine for the New Game Plus rules engine.

Implements a registry-based feat system that dynamically modifies character
stats (AC, attack, damage, initiative, saving throws, HP, etc.) according to
3.5e SRD rules.

The :class:`FeatRegistry` provides O(1) lookup for feat logic, avoiding
expensive string comparisons during combat resolution.  The prerequisite
engine enforces the official SRD requirements before a feat may be added to a
character (e.g. Power Attack requires STR 13; Cleave requires Power Attack).

Usage::

    from src.rules_engine.feat_engine import FeatRegistry, FEAT_CATALOG
    from src.rules_engine.character_35e import Character35e

    fighter = Character35e(
        name="Aldric", char_class="Fighter", level=5,
        strength=16, dexterity=13, feats=[]
    )

    # Safely add a feat (validates prerequisites):
    ok = FeatRegistry.add_feat(fighter, "Power Attack")   # True
    ok = FeatRegistry.add_feat(fighter, "Cleave")          # True — PA present

    # Query bonuses for combat resolution:
    init_bonus = FeatRegistry.get_initiative_bonus(fighter)
    hp_bonus   = FeatRegistry.get_hp_bonus(fighter)       # Toughness
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Dict, Optional, Tuple

if TYPE_CHECKING:
    from src.rules_engine.character_35e import Character35e


# ---------------------------------------------------------------------------
# Bonus type enumeration (3.5e stacking rules)
# ---------------------------------------------------------------------------

class BonusType(Enum):
    """3.5e bonus types — same-type bonuses do not stack (except dodge)."""

    UNTYPED = auto()
    DODGE = auto()
    COMPETENCE = auto()
    ENHANCEMENT = auto()
    INSIGHT = auto()
    MORALE = auto()
    LUCK = auto()


# ---------------------------------------------------------------------------
# Feat data class
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Feat:
    """Base representation of a 3.5e feat.

    Attributes:
        name:          Canonical feat name (e.g. ``"Improved Initiative"``).
        description:   Short SRD description.
        prerequisites: Human-readable prerequisite string.
        bonus_type:    The type of bonus this feat provides.
    """

    name: str
    description: str = ""
    prerequisites: str = ""
    bonus_type: BonusType = BonusType.UNTYPED


# ---------------------------------------------------------------------------
# Feat prerequisite data class
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class FeatPrerequisite:
    """Structured representation of a feat's mechanical prerequisites.

    All fields are optional; omitted fields impose no constraint.

    Attributes:
        min_str:         Minimum Strength score required.
        min_dex:         Minimum Dexterity score required.
        min_con:         Minimum Constitution score required.
        min_int:         Minimum Intelligence score required.
        min_wis:         Minimum Wisdom score required.
        min_cha:         Minimum Charisma score required.
        min_bab:         Minimum Base Attack Bonus required.
        required_feats:  Tuple of feat names that must already be possessed.
        required_class:  If non-empty, the character must belong to this class.
        min_class_level: Minimum level in ``required_class`` (only checked when
                         ``required_class`` is non-empty).
    """

    min_str: int = 0
    min_dex: int = 0
    min_con: int = 0
    min_int: int = 0
    min_wis: int = 0
    min_cha: int = 0
    min_bab: int = 0
    required_feats: Tuple[str, ...] = ()
    required_class: str = ""
    min_class_level: int = 0


# ---------------------------------------------------------------------------
# Canonical feat catalog (SRD descriptions)
# ---------------------------------------------------------------------------

FEAT_CATALOG: Dict[str, Feat] = {
    # ---- Combat feats -------------------------------------------------------
    "Power Attack": Feat(
        name="Power Attack",
        description=(
            "On your action, before making attack rolls for a round, you may "
            "choose to subtract a number from all melee attack rolls and add "
            "the same number to all melee damage rolls (double for two-handed "
            "weapons). This number may not exceed your base attack bonus."
        ),
        prerequisites="STR 13",
        bonus_type=BonusType.UNTYPED,
    ),
    "Cleave": Feat(
        name="Cleave",
        description=(
            "If you deal a creature enough damage to make it drop (typically "
            "by killing it or knocking it unconscious), you get an immediate "
            "extra melee attack against another creature within reach."
        ),
        prerequisites="STR 13, Power Attack",
        bonus_type=BonusType.UNTYPED,
    ),
    "Great Cleave": Feat(
        name="Great Cleave",
        description=(
            "As Cleave, but you have no limit to the number of times you can "
            "use it per round."
        ),
        prerequisites="STR 13, Cleave, BAB +4",
        bonus_type=BonusType.UNTYPED,
    ),
    "Dodge": Feat(
        name="Dodge",
        description=(
            "During your action, you designate an opponent and receive a +1 "
            "dodge bonus to Armor Class against attacks from that opponent."
        ),
        prerequisites="DEX 13",
        bonus_type=BonusType.DODGE,
    ),
    "Mobility": Feat(
        name="Mobility",
        description=(
            "You get a +4 dodge bonus to Armor Class against attacks of "
            "opportunity caused when you move out of or within a threatened area."
        ),
        prerequisites="DEX 13, Dodge",
        bonus_type=BonusType.DODGE,
    ),
    "Spring Attack": Feat(
        name="Spring Attack",
        description=(
            "When using the attack action with a melee weapon, you can move "
            "both before and after the attack, provided that your total "
            "distance moved is not greater than your speed."
        ),
        prerequisites="DEX 13, Dodge, Mobility, BAB +4",
        bonus_type=BonusType.UNTYPED,
    ),
    "Combat Reflexes": Feat(
        name="Combat Reflexes",
        description=(
            "You may make a number of additional attacks of opportunity per "
            "round equal to your Dexterity bonus. You can make attacks of "
            "opportunity while flat-footed."
        ),
        prerequisites="None",
        bonus_type=BonusType.UNTYPED,
    ),
    "Improved Initiative": Feat(
        name="Improved Initiative",
        description="You get a +4 bonus on initiative checks.",
        prerequisites="None",
        bonus_type=BonusType.UNTYPED,
    ),
    "Weapon Focus": Feat(
        name="Weapon Focus",
        description=(
            "You gain a +1 bonus on all attack rolls you make using the "
            "selected weapon."
        ),
        prerequisites="BAB +1",
        bonus_type=BonusType.UNTYPED,
    ),
    "Weapon Specialization": Feat(
        name="Weapon Specialization",
        description=(
            "You gain a +2 bonus on all damage rolls you make using the "
            "selected weapon."
        ),
        prerequisites="Weapon Focus (same weapon), Fighter level 4",
        bonus_type=BonusType.UNTYPED,
    ),
    "Improved Critical": Feat(
        name="Improved Critical",
        description=(
            "When using the weapon you selected, your threat range is doubled. "
            "This benefit doesn't stack with any other effect that expands the "
            "threat range of a weapon."
        ),
        prerequisites="Proficient with weapon, BAB +8",
        bonus_type=BonusType.UNTYPED,
    ),
    # ---- Metamagic feats (placeholder — effect resolved in spellcasting) ----
    "Empower Spell": Feat(
        name="Empower Spell",
        description=(
            "All variable, numeric effects of an empowered spell are increased "
            "by one half. Saving throws and opposed rolls are not affected. "
            "An empowered spell uses a spell slot two levels higher than normal."
        ),
        prerequisites="None",
        bonus_type=BonusType.UNTYPED,
    ),
    "Maximize Spell": Feat(
        name="Maximize Spell",
        description=(
            "All variable, numeric effects of a spell modified by this feat are "
            "maximized. Saving throws and opposed rolls are not affected. A "
            "maximized spell uses a spell slot three levels higher than normal."
        ),
        prerequisites="None",
        bonus_type=BonusType.UNTYPED,
    ),
    # ---- General feats -------------------------------------------------------
    "Toughness": Feat(
        name="Toughness",
        description="You gain +3 hit points.",
        prerequisites="None",
        bonus_type=BonusType.UNTYPED,
    ),
    "Great Fortitude": Feat(
        name="Great Fortitude",
        description="You get a +2 bonus on all Fortitude saving throws.",
        prerequisites="None",
        bonus_type=BonusType.UNTYPED,
    ),
    "Iron Will": Feat(
        name="Iron Will",
        description="You get a +2 bonus on all Will saving throws.",
        prerequisites="None",
        bonus_type=BonusType.UNTYPED,
    ),
    "Lightning Reflexes": Feat(
        name="Lightning Reflexes",
        description="You get a +2 bonus on all Reflex saving throws.",
        prerequisites="None",
        bonus_type=BonusType.UNTYPED,
    ),
    # ---- Two-weapon fighting chain ------------------------------------------
    "Two-Weapon Fighting": Feat(
        name="Two-Weapon Fighting",
        description=(
            "Your penalties on attack rolls for fighting with two weapons are "
            "reduced. The penalty for your primary hand lessens by 2 and the "
            "one for your off hand lessens by 6."
        ),
        prerequisites="DEX 15",
        bonus_type=BonusType.UNTYPED,
    ),
    "Improved Two-Weapon Fighting": Feat(
        name="Improved Two-Weapon Fighting",
        description=(
            "In addition to the standard single extra attack you get with an "
            "off-hand weapon, you get a second attack with it, albeit at a "
            "-5 penalty."
        ),
        prerequisites="DEX 17, Two-Weapon Fighting, BAB +6",
        bonus_type=BonusType.UNTYPED,
    ),
    "Greater Two-Weapon Fighting": Feat(
        name="Greater Two-Weapon Fighting",
        description=(
            "You get a third attack with your off-hand weapon, albeit at a "
            "-10 penalty."
        ),
        prerequisites="DEX 19, Improved Two-Weapon Fighting, BAB +11",
        bonus_type=BonusType.UNTYPED,
    ),
    # ---- Archery chain -------------------------------------------------------
    "Point Blank Shot": Feat(
        name="Point Blank Shot",
        description=(
            "You get a +1 bonus on attack and damage rolls with ranged weapons "
            "at ranges of up to 30 feet."
        ),
        prerequisites="None",
        bonus_type=BonusType.UNTYPED,
    ),
    "Rapid Shot": Feat(
        name="Rapid Shot",
        description=(
            "You can get one extra attack per round with a ranged weapon. The "
            "attack is at your highest base attack bonus, but each attack you "
            "make in that round (the extra one and the normal ones) takes a -2 "
            "penalty."
        ),
        prerequisites="DEX 13, Point Blank Shot",
        bonus_type=BonusType.UNTYPED,
    ),
    "Precise Shot": Feat(
        name="Precise Shot",
        description=(
            "You can shoot or throw ranged weapons at an opponent engaged in "
            "melee without taking the standard -4 penalty on your attack roll."
        ),
        prerequisites="Point Blank Shot",
        bonus_type=BonusType.UNTYPED,
    ),
    "Far Shot": Feat(
        name="Far Shot",
        description=(
            "When you use a projectile weapon, its range increment increases "
            "by one half (multiply by 1.5). When you use a thrown weapon, its "
            "range increment is doubled."
        ),
        prerequisites="Point Blank Shot",
        bonus_type=BonusType.UNTYPED,
    ),
    "Shot on the Run": Feat(
        name="Shot on the Run",
        description=(
            "When using the attack action with a ranged weapon, you can move "
            "both before and after the attack."
        ),
        prerequisites="DEX 13, Dodge, Mobility, Point Blank Shot, BAB +4",
        bonus_type=BonusType.UNTYPED,
    ),
    # ---- Unarmed / monk chain ------------------------------------------------
    "Improved Unarmed Strike": Feat(
        name="Improved Unarmed Strike",
        description=(
            "You are considered to be armed even when unarmed — you do not "
            "provoke attacks of opportunity when you attack foes while "
            "unarmed. Your unarmed strikes can deal lethal or nonlethal "
            "damage."
        ),
        prerequisites="None",
        bonus_type=BonusType.UNTYPED,
    ),
    "Stunning Fist": Feat(
        name="Stunning Fist",
        description=(
            "You must declare that you are using this feat before you make "
            "your attack roll. On a successful hit, the target must make a "
            "Fortitude save (DC 10 + half your character level + WIS modifier) "
            "or be stunned for 1 round."
        ),
        prerequisites="DEX 13, WIS 13, Improved Unarmed Strike, BAB +8",
        bonus_type=BonusType.UNTYPED,
    ),
    "Deflect Arrows": Feat(
        name="Deflect Arrows",
        description=(
            "You must have at least one hand free. Once per round when you "
            "would normally be hit with a ranged weapon, you may deflect it "
            "so that you take no damage from it."
        ),
        prerequisites="DEX 13, Improved Unarmed Strike",
        bonus_type=BonusType.UNTYPED,
    ),
    # ---- Combat chain --------------------------------------------------------
    "Combat Expertise": Feat(
        name="Combat Expertise",
        description=(
            "When you use the attack action or the full-attack action in melee, "
            "you can take a penalty of as much as -5 on your attack roll and "
            "add the same number (+5 or less) as a dodge bonus to your Armor "
            "Class. This number may not exceed your base attack bonus."
        ),
        prerequisites="INT 13",
        bonus_type=BonusType.DODGE,
    ),
    "Whirlwind Attack": Feat(
        name="Whirlwind Attack",
        description=(
            "When you use the full-attack action, you can give up your regular "
            "attacks and instead make one melee attack at your full base attack "
            "bonus against each opponent within reach."
        ),
        prerequisites="DEX 13, INT 13, Combat Expertise, Dodge, Mobility, Spring Attack, BAB +4",
        bonus_type=BonusType.UNTYPED,
    ),
    # ---- General feats -------------------------------------------------------
    "Alertness": Feat(
        name="Alertness",
        description="You get a +2 bonus on all Listen checks and Spot checks.",
        prerequisites="None",
        bonus_type=BonusType.UNTYPED,
    ),
    "Endurance": Feat(
        name="Endurance",
        description=(
            "You gain a +4 bonus on the following checks and saves: swim "
            "checks made to resist nonlethal damage, Constitution checks made "
            "to continue running, Constitution checks made to avoid nonlethal "
            "damage from a forced march, Constitution checks made to hold your "
            "breath, Constitution checks made to avoid nonlethal damage from "
            "starvation or thirst, Fortitude saves made to avoid nonlethal "
            "damage from hot or cold environments, and Fortitude saves made to "
            "resist damage from suffocation."
        ),
        prerequisites="None",
        bonus_type=BonusType.UNTYPED,
    ),
    "Diehard": Feat(
        name="Diehard",
        description=(
            "When your hit point total is below 0, but you are not dead, you "
            "automatically become stable. You don't have to roll d% to see if "
            "you lose 1 hit point each round. You may choose to act as if you "
            "were disabled, rather than dying."
        ),
        prerequisites="Endurance",
        bonus_type=BonusType.UNTYPED,
    ),
    "Run": Feat(
        name="Run",
        description=(
            "When running, you move five times your normal speed (if wearing "
            "medium, light, or no armor and carrying no more than a medium "
            "load) or four times your speed (if wearing heavy armor or "
            "carrying a heavy load). If you make a jump after a running start, "
            "you receive a +4 bonus on your Jump check."
        ),
        prerequisites="None",
        bonus_type=BonusType.UNTYPED,
    ),
    "Blind-Fight": Feat(
        name="Blind-Fight",
        description=(
            "In melee, every time you miss because of concealment, you can "
            "reroll your miss chance percentile roll one time to see if you "
            "actually hit. An invisible attacker gets no advantages related "
            "to hitting you in melee. You take only half the normal penalty "
            "to speed when moving while unable to see. In darkness, non-elves "
            "can attack invisible opponents without penalty."
        ),
        prerequisites="None",
        bonus_type=BonusType.UNTYPED,
    ),
    "Track": Feat(
        name="Track",
        description=(
            "To find tracks or to follow them for 1 mile requires a Survival "
            "check. You must make another Survival check every time the tracks "
            "become difficult to follow."
        ),
        prerequisites="None",
        bonus_type=BonusType.UNTYPED,
    ),
    # ---- Spellcaster feats --------------------------------------------------
    "Spell Focus": Feat(
        name="Spell Focus",
        description=(
            "Add +1 to the Difficulty Class for all saving throws against "
            "spells from the school of magic you select."
        ),
        prerequisites="None",
        bonus_type=BonusType.UNTYPED,
    ),
    "Greater Spell Focus": Feat(
        name="Greater Spell Focus",
        description=(
            "Add +1 to the Difficulty Class for all saving throws against "
            "spells from the school of magic you select. This bonus stacks "
            "with the bonus from Spell Focus."
        ),
        prerequisites="Spell Focus",
        bonus_type=BonusType.UNTYPED,
    ),
    "Spell Penetration": Feat(
        name="Spell Penetration",
        description=(
            "You get a +2 bonus on caster level checks made to overcome a "
            "creature's spell resistance."
        ),
        prerequisites="None",
        bonus_type=BonusType.UNTYPED,
    ),
    "Greater Spell Penetration": Feat(
        name="Greater Spell Penetration",
        description=(
            "You get a +2 bonus on caster level checks made to overcome a "
            "creature's spell resistance. This bonus stacks with the one from "
            "Spell Penetration."
        ),
        prerequisites="Spell Penetration",
        bonus_type=BonusType.UNTYPED,
    ),
    "Augment Summoning": Feat(
        name="Augment Summoning",
        description=(
            "Each creature you conjure with any summon spell gains a +4 "
            "enhancement bonus to Strength and Constitution for the duration "
            "of the spell that summoned it."
        ),
        prerequisites="Spell Focus",
        bonus_type=BonusType.ENHANCEMENT,
    ),
    "Natural Spell": Feat(
        name="Natural Spell",
        description=(
            "You can complete the verbal and somatic components of spells "
            "while in a wild shape. You substitute various sounds and gestures "
            "for the normal verbal and somatic components of a spell."
        ),
        prerequisites="WIS 13",
        bonus_type=BonusType.UNTYPED,
    ),
    "Extra Turning": Feat(
        name="Extra Turning",
        description=(
            "You may turn or rebuke undead four more times per day than normal."
        ),
        prerequisites="Ability to turn or rebuke undead",
        bonus_type=BonusType.UNTYPED,
    ),
    # ---- Mounted feats -------------------------------------------------------
    "Mounted Combat": Feat(
        name="Mounted Combat",
        description=(
            "Once per round when your mount is hit in combat, you may "
            "attempt a Ride check (as a reaction) to negate the hit."
        ),
        prerequisites="Ride 1 rank",
        bonus_type=BonusType.UNTYPED,
    ),
    "Ride-By Attack": Feat(
        name="Ride-By Attack",
        description=(
            "When you are mounted and use the charge action, you may move and "
            "attack as if with a standard charge and then continue moving up "
            "to your remaining movement."
        ),
        prerequisites="Mounted Combat",
        bonus_type=BonusType.UNTYPED,
    ),
    # ---- Item creation feats (stubs — effect resolved in crafting system) ----
    "Brew Potion": Feat(
        name="Brew Potion",
        description=(
            "You can create potions, which are spells stored in liquid form. "
            "Brewing a potion takes 1 day. When you create a potion, you set "
            "the caster level."
        ),
        prerequisites="Caster level 3",
        bonus_type=BonusType.UNTYPED,
    ),
    "Craft Wondrous Item": Feat(
        name="Craft Wondrous Item",
        description=(
            "You can create any wondrous item whose prerequisites you meet. "
            "Crafting a wondrous item takes 1 day for each 1,000 gp in its "
            "price."
        ),
        prerequisites="Caster level 3",
        bonus_type=BonusType.UNTYPED,
    ),
}


# ---------------------------------------------------------------------------
# Power Attack intent
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class PowerAttackIntent:
    """Represents a character's intent to use Power Attack.

    In 3.5e, a character can subtract a value from their melee attack
    roll (up to their BAB) and add that same value to melee damage.
    Two-handed weapons get double the damage bonus.

    Attributes:
        penalty:       Amount subtracted from attack rolls (1 to BAB).
        two_handed:    If ``True``, damage bonus is doubled (2× penalty).
    """

    penalty: int
    two_handed: bool = False

    @property
    def damage_bonus(self) -> int:
        """Damage bonus gained from the Power Attack trade-off.

        Returns:
            ``penalty`` for one-handed, ``penalty × 2`` for two-handed.
        """
        if self.two_handed:
            return self.penalty * 2
        return self.penalty


# ---------------------------------------------------------------------------
# Feat Registry
# ---------------------------------------------------------------------------

class FeatRegistry:
    """Registry-based lookup for feat logic and prerequisite enforcement.

    All feat effects are resolved via class-level dictionaries keyed by
    feat name, providing O(1) access during combat ticks. This avoids
    repeated string comparisons and if/elif chains.

    The prerequisite engine enforces 3.5e SRD requirements.  Use
    :meth:`add_feat` to safely add feats to a character; it returns
    ``False`` if the character does not meet the requirements.
    """

    # Maps feat name → initiative bonus value
    _INITIATIVE_BONUSES: Dict[str, int] = {
        "Improved Initiative": 4,
    }

    # Maps feat name → attack bonus value (flat, requires weapon match)
    _ATTACK_BONUSES: Dict[str, int] = {
        "Weapon Focus": 1,
    }

    # Maps feat name → flat damage bonus (requires weapon match)
    _DAMAGE_BONUSES: Dict[str, int] = {
        "Weapon Specialization": 2,
    }

    # Maps feat name → Fortitude save bonus
    _FORTITUDE_BONUSES: Dict[str, int] = {
        "Great Fortitude": 2,
    }

    # Maps feat name → Reflex save bonus
    _REFLEX_BONUSES: Dict[str, int] = {
        "Lightning Reflexes": 2,
    }

    # Maps feat name → Will save bonus
    _WILL_BONUSES: Dict[str, int] = {
        "Iron Will": 2,
    }

    # Maps feat name → flat HP bonus (added once, not per level)
    _HP_BONUSES: Dict[str, int] = {
        "Toughness": 3,
    }

    # Maps feat name → AC bonus value (dodge bonuses stack per SRD)
    _AC_BONUSES: Dict[str, int] = {
        "Dodge": 1,
    }

    # Maps feat name → Listen/Spot/skill bonus (Alertness)
    _SKILL_BONUSES: Dict[str, Dict[str, int]] = {
        "Alertness": {"Listen": 2, "Spot": 2},
    }

    # Maps feat name → spell save DC bonus (Spell Focus / Greater Spell Focus)
    _SPELL_DC_BONUSES: Dict[str, int] = {
        "Spell Focus": 1,
        "Greater Spell Focus": 1,
    }

    # Maps feat name → caster level bonus (Spell Penetration / Greater)
    _CASTER_LEVEL_BONUSES: Dict[str, int] = {
        "Spell Penetration": 2,
        "Greater Spell Penetration": 2,
    }

    # Maps feat name → extra turning attempts per day
    _EXTRA_TURNING: Dict[str, int] = {
        "Extra Turning": 4,
    }

    # Set of feat names that support Power Attack mechanic
    _POWER_ATTACK_FEATS: set = {"Power Attack"}

    # Structured prerequisites per feat (omitted → no prerequisites)
    _PREREQUISITES: Dict[str, FeatPrerequisite] = {
        "Power Attack": FeatPrerequisite(min_str=13),
        "Cleave": FeatPrerequisite(
            min_str=13,
            required_feats=("Power Attack",),
        ),
        "Great Cleave": FeatPrerequisite(
            min_str=13,
            required_feats=("Cleave",),
            min_bab=4,
        ),
        "Dodge": FeatPrerequisite(min_dex=13),
        "Mobility": FeatPrerequisite(
            min_dex=13,
            required_feats=("Dodge",),
        ),
        "Spring Attack": FeatPrerequisite(
            min_dex=13,
            required_feats=("Dodge", "Mobility"),
            min_bab=4,
        ),
        "Weapon Focus": FeatPrerequisite(min_bab=1),
        "Weapon Specialization": FeatPrerequisite(
            required_feats=("Weapon Focus",),
            required_class="Fighter",
            min_class_level=4,
        ),
        "Improved Critical": FeatPrerequisite(min_bab=8),
        # Two-weapon fighting chain
        "Two-Weapon Fighting": FeatPrerequisite(min_dex=15),
        "Improved Two-Weapon Fighting": FeatPrerequisite(
            min_dex=17,
            required_feats=("Two-Weapon Fighting",),
            min_bab=6,
        ),
        "Greater Two-Weapon Fighting": FeatPrerequisite(
            min_dex=19,
            required_feats=("Improved Two-Weapon Fighting",),
            min_bab=11,
        ),
        # Archery chain
        "Rapid Shot": FeatPrerequisite(min_dex=13, required_feats=("Point Blank Shot",)),
        "Precise Shot": FeatPrerequisite(required_feats=("Point Blank Shot",)),
        "Far Shot": FeatPrerequisite(required_feats=("Point Blank Shot",)),
        "Shot on the Run": FeatPrerequisite(
            min_dex=13,
            required_feats=("Dodge", "Mobility", "Point Blank Shot"),
            min_bab=4,
        ),
        # Unarmed chain
        "Stunning Fist": FeatPrerequisite(
            min_dex=13,
            min_wis=13,
            required_feats=("Improved Unarmed Strike",),
            min_bab=8,
        ),
        "Deflect Arrows": FeatPrerequisite(
            min_dex=13,
            required_feats=("Improved Unarmed Strike",),
        ),
        # Combat chain
        "Combat Expertise": FeatPrerequisite(min_int=13),
        "Whirlwind Attack": FeatPrerequisite(
            min_dex=13,
            min_int=13,
            required_feats=("Combat Expertise", "Dodge", "Mobility", "Spring Attack"),
            min_bab=4,
        ),
        # General
        "Diehard": FeatPrerequisite(required_feats=("Endurance",)),
        # Spellcaster
        "Greater Spell Focus": FeatPrerequisite(required_feats=("Spell Focus",)),
        "Greater Spell Penetration": FeatPrerequisite(required_feats=("Spell Penetration",)),
        "Augment Summoning": FeatPrerequisite(required_feats=("Spell Focus",)),
        "Natural Spell": FeatPrerequisite(min_wis=13),
        # Mounted
        "Ride-By Attack": FeatPrerequisite(required_feats=("Mounted Combat",)),
        # Feats with no prerequisites are intentionally absent from this dict.
    }

    # ------------------------------------------------------------------
    # Prerequisite engine
    # ------------------------------------------------------------------

    @classmethod
    def meets_prerequisites(
        cls,
        character: "Character35e",
        feat_name: str,
    ) -> bool:
        """Check whether *character* meets all prerequisites for *feat_name*.

        Feats not listed in ``_PREREQUISITES`` are considered to have no
        requirements and always return ``True``.

        Args:
            character:  The character to evaluate.
            feat_name:  The canonical feat name to check.

        Returns:
            ``True`` if all prerequisites are satisfied, ``False`` otherwise.
        """
        prereq = cls._PREREQUISITES.get(feat_name)
        if prereq is None:
            return True

        # Ability score minimums
        if character.strength < prereq.min_str:
            return False
        if character.dexterity < prereq.min_dex:
            return False
        if character.constitution < prereq.min_con:
            return False
        if character.intelligence < prereq.min_int:
            return False
        if character.wisdom < prereq.min_wis:
            return False
        if character.charisma < prereq.min_cha:
            return False

        # Minimum base attack bonus
        if character.base_attack_bonus < prereq.min_bab:
            return False

        # Required feats
        char_feats = set(character.feats)
        for required in prereq.required_feats:
            if required not in char_feats:
                return False

        # Class restriction
        if prereq.required_class:
            if character.char_class != prereq.required_class:
                return False
            if character.level < prereq.min_class_level:
                return False

        return True

    @classmethod
    def add_feat(
        cls,
        character: "Character35e",
        feat_name: str,
    ) -> bool:
        """Attempt to add *feat_name* to *character*, enforcing prerequisites.

        If the character already possesses the feat, this is a no-op that
        returns ``True``.

        Args:
            character:  The character to modify.
            feat_name:  The canonical feat name to add.

        Returns:
            ``True`` if the feat was added (or already present),
            ``False`` if the character does not meet the prerequisites.
        """
        if feat_name in character.feats:
            return True
        if not cls.meets_prerequisites(character, feat_name):
            return False
        character.feats.append(feat_name)
        return True

    # ------------------------------------------------------------------
    # Initiative
    # ------------------------------------------------------------------

    @classmethod
    def get_initiative_bonus(cls, character: "Character35e") -> int:
        """Compute total initiative bonus from character's feats.

        Args:
            character: The character whose feats are checked.

        Returns:
            Sum of all initiative bonuses granted by feats.
        """
        bonus = 0
        for feat_name in character.feats:
            bonus += cls._INITIATIVE_BONUSES.get(feat_name, 0)
        return bonus

    # ------------------------------------------------------------------
    # Attack bonus
    # ------------------------------------------------------------------

    @classmethod
    def get_attack_bonus(
        cls,
        character: "Character35e",
        weapon_type: Optional[str] = None,
    ) -> int:
        """Compute total attack bonus from character's feats.

        For Weapon Focus, the bonus only applies if the character's
        metadata contains a ``"weapon_focus_type"`` key matching the
        ``weapon_type`` argument, or if no weapon_type check is needed.

        Args:
            character:   The character whose feats are checked.
            weapon_type: The weapon type being used for the attack.

        Returns:
            Sum of all applicable attack bonuses from feats.
        """
        bonus = 0
        for feat_name in character.feats:
            if feat_name == "Weapon Focus":
                focus_type = character.metadata.get("weapon_focus_type", "")
                if weapon_type is None or focus_type == weapon_type:
                    bonus += cls._ATTACK_BONUSES.get(feat_name, 0)
            else:
                bonus += cls._ATTACK_BONUSES.get(feat_name, 0)
        return bonus

    # ------------------------------------------------------------------
    # Damage bonus
    # ------------------------------------------------------------------

    @classmethod
    def get_damage_bonus(
        cls,
        character: "Character35e",
        weapon_type: Optional[str] = None,
    ) -> int:
        """Compute total damage bonus from character's feats.

        For Weapon Specialization, the bonus only applies when the
        character's ``"weapon_focus_type"`` metadata matches the
        ``weapon_type`` argument (or when no weapon_type is specified).

        Args:
            character:   The character whose feats are checked.
            weapon_type: The weapon type being used for the attack.

        Returns:
            Sum of all applicable damage bonuses from feats.
        """
        bonus = 0
        for feat_name in character.feats:
            if feat_name == "Weapon Specialization":
                focus_type = character.metadata.get("weapon_focus_type", "")
                if weapon_type is None or focus_type == weapon_type:
                    bonus += cls._DAMAGE_BONUSES.get(feat_name, 0)
            else:
                bonus += cls._DAMAGE_BONUSES.get(feat_name, 0)
        return bonus

    # ------------------------------------------------------------------
    # Saving throw bonuses
    # ------------------------------------------------------------------

    @classmethod
    def get_fortitude_bonus(cls, character: "Character35e") -> int:
        """Compute total Fortitude save bonus from feats (e.g. Great Fortitude).

        Args:
            character: The character whose feats are checked.

        Returns:
            Sum of all Fortitude save bonuses granted by feats.
        """
        bonus = 0
        for feat_name in character.feats:
            bonus += cls._FORTITUDE_BONUSES.get(feat_name, 0)
        return bonus

    @classmethod
    def get_reflex_bonus(cls, character: "Character35e") -> int:
        """Compute total Reflex save bonus from feats (e.g. Lightning Reflexes).

        Args:
            character: The character whose feats are checked.

        Returns:
            Sum of all Reflex save bonuses granted by feats.
        """
        bonus = 0
        for feat_name in character.feats:
            bonus += cls._REFLEX_BONUSES.get(feat_name, 0)
        return bonus

    @classmethod
    def get_will_bonus(cls, character: "Character35e") -> int:
        """Compute total Will save bonus from feats (e.g. Iron Will).

        Args:
            character: The character whose feats are checked.

        Returns:
            Sum of all Will save bonuses granted by feats.
        """
        bonus = 0
        for feat_name in character.feats:
            bonus += cls._WILL_BONUSES.get(feat_name, 0)
        return bonus

    # ------------------------------------------------------------------
    # HP bonus
    # ------------------------------------------------------------------

    @classmethod
    def get_hp_bonus(cls, character: "Character35e") -> int:
        """Compute total flat HP bonus from feats (e.g. Toughness grants +3).

        The Toughness bonus is a fixed amount, not per-level.

        Args:
            character: The character whose feats are checked.

        Returns:
            Sum of all flat HP bonuses granted by feats.
        """
        bonus = 0
        for feat_name in character.feats:
            bonus += cls._HP_BONUSES.get(feat_name, 0)
        return bonus

    # ------------------------------------------------------------------
    # Power Attack
    # ------------------------------------------------------------------

    @classmethod
    def has_power_attack(cls, character: "Character35e") -> bool:
        """Check if a character has the Power Attack feat.

        Args:
            character: The character to check.

        Returns:
            ``True`` if Power Attack is in the character's feat list.
        """
        return any(f in cls._POWER_ATTACK_FEATS for f in character.feats)

    @classmethod
    def validate_power_attack(
        cls,
        character: "Character35e",
        intent: PowerAttackIntent,
    ) -> bool:
        """Validate a Power Attack intent against 3.5e rules.

        The penalty cannot exceed the character's BAB and must be at
        least 1. The character must also have the Power Attack feat and
        STR 13+.

        Args:
            character: The character attempting Power Attack.
            intent:    The intended Power Attack parameters.

        Returns:
            ``True`` if the intent is valid per SRD rules.
        """
        if not cls.has_power_attack(character):
            return False
        if character.strength < 13:
            return False
        if intent.penalty < 1:
            return False
        if intent.penalty > character.base_attack_bonus:
            return False
        return True

    @classmethod
    def apply_power_attack(
        cls,
        character: "Character35e",
        intent: PowerAttackIntent,
    ) -> Tuple[int, int]:
        """Compute attack and damage modifiers from Power Attack.

        Args:
            character: The character using Power Attack.
            intent:    The Power Attack parameters.

        Returns:
            Tuple of ``(attack_modifier, damage_modifier)`` where
            attack_modifier is negative and damage_modifier is positive.
            Returns ``(0, 0)`` if the intent is invalid.
        """
        if not cls.validate_power_attack(character, intent):
            return (0, 0)
        return (-intent.penalty, intent.damage_bonus)

    # ------------------------------------------------------------------
    # AC bonuses from feats
    # ------------------------------------------------------------------

    @classmethod
    def get_ac_bonus(cls, character: "Character35e") -> int:
        """Compute total AC bonus from character's feats.

        Dodge provides a +1 dodge bonus to AC.  Dodge bonuses stack with
        each other per the 3.5e stacking rules.

        Args:
            character: The character whose feats are checked.

        Returns:
            Sum of all AC bonuses from feats.
        """
        bonus = 0
        for feat_name in character.feats:
            bonus += cls._AC_BONUSES.get(feat_name, 0)
        return bonus

    # ------------------------------------------------------------------
    # Improved Critical
    # ------------------------------------------------------------------

    @classmethod
    def get_threat_range_multiplier(cls, character: "Character35e") -> int:
        """Return the threat-range multiplier granted by Improved Critical.

        The Improved Critical feat doubles a weapon's threat range.  This
        method returns ``2`` if the character has the feat, ``1`` otherwise.
        The caller is responsible for applying it to the base threat range.

        Per the SRD, this does not stack with other threat-range expansion
        effects (e.g. Keen weapon enhancement).

        Args:
            character: The character whose feats are checked.

        Returns:
            ``2`` if Improved Critical is present, ``1`` otherwise.
        """
        return 2 if "Improved Critical" in character.feats else 1

    # ------------------------------------------------------------------
    # Combat Reflexes
    # ------------------------------------------------------------------

    @classmethod
    def get_aoo_count(cls, character: "Character35e") -> int:
        """Return the number of attacks of opportunity per round.

        Without Combat Reflexes a character gets exactly one AoO per
        round (base 1, ignoring DEX).  With Combat Reflexes the total
        equals ``1 + DEX modifier`` (minimum 1).

        Args:
            character: The character whose feats are checked.

        Returns:
            Maximum AoOs per round.
        """
        if "Combat Reflexes" not in character.feats:
            return 1
        dex_mod = (character.dexterity - 10) // 2
        return max(1, 1 + dex_mod)

    # ------------------------------------------------------------------
    # Spell save DC bonus (Spell Focus / Greater Spell Focus)
    # ------------------------------------------------------------------

    @classmethod
    def get_spell_dc_bonus(cls, character: "Character35e") -> int:
        """Return total spell save DC bonus from feats.

        Spell Focus grants +1 and Greater Spell Focus grants an additional
        +1, for a maximum of +2 from this feat chain.

        Args:
            character: The character whose feats are checked.

        Returns:
            Sum of all spell DC bonuses from feats.
        """
        bonus = 0
        for feat_name in character.feats:
            bonus += cls._SPELL_DC_BONUSES.get(feat_name, 0)
        return bonus

    # ------------------------------------------------------------------
    # Caster level bonus (Spell Penetration / Greater)
    # ------------------------------------------------------------------

    @classmethod
    def get_caster_level_bonus(cls, character: "Character35e") -> int:
        """Return total caster level bonus for overcoming spell resistance.

        Spell Penetration grants +2 and Greater Spell Penetration grants
        an additional +2, for a maximum of +4 from this feat chain.

        Args:
            character: The character whose feats are checked.

        Returns:
            Total bonus to caster level checks vs. spell resistance.
        """
        bonus = 0
        for feat_name in character.feats:
            bonus += cls._CASTER_LEVEL_BONUSES.get(feat_name, 0)
        return bonus

    # ------------------------------------------------------------------
    # Skill bonuses (Alertness etc.)
    # ------------------------------------------------------------------

    @classmethod
    def get_skill_bonus(cls, character: "Character35e", skill: str) -> int:
        """Return total feat bonus for a specific skill.

        For example, Alertness grants +2 to both Listen and Spot.

        Args:
            character: The character whose feats are checked.
            skill:     The exact skill name (e.g. ``"Listen"``).

        Returns:
            Sum of all feat bonuses for the specified skill.
        """
        bonus = 0
        for feat_name in character.feats:
            skill_map = cls._SKILL_BONUSES.get(feat_name, {})
            bonus += skill_map.get(skill, 0)
        return bonus

    # ------------------------------------------------------------------
    # Extra turning attempts (Extra Turning feat)
    # ------------------------------------------------------------------

    @classmethod
    def get_extra_turning_attempts(cls, character: "Character35e") -> int:
        """Return extra turning/rebuking attempts per day from feats.

        Extra Turning grants 4 additional turning attempts per day.

        Args:
            character: The character whose feats are checked.

        Returns:
            Total additional turning attempts from feats.
        """
        bonus = 0
        for feat_name in character.feats:
            bonus += cls._EXTRA_TURNING.get(feat_name, 0)
        return bonus

    # ------------------------------------------------------------------
    # Two-weapon fighting
    # ------------------------------------------------------------------

    @classmethod
    def has_two_weapon_fighting(cls, character: "Character35e") -> bool:
        """Return True if the character has the Two-Weapon Fighting feat."""
        return "Two-Weapon Fighting" in character.feats

    @classmethod
    def get_twf_penalties(cls, character: "Character35e") -> Tuple[int, int]:
        """Return ``(primary_penalty, offhand_penalty)`` for two-weapon fighting.

        Without the feat the penalties are -6 (primary) / -10 (offhand) for
        equal-weight weapons.  Two-Weapon Fighting reduces them to -4/-4 (the
        SRD light-weapon bonus is handled by the caller).  Without the feat,
        returns (-6, -10).

        Args:
            character: The character whose feats are checked.

        Returns:
            Tuple of ``(primary_penalty, offhand_penalty)``.
        """
        if "Two-Weapon Fighting" in character.feats:
            return (-4, -4)
        return (-6, -10)
