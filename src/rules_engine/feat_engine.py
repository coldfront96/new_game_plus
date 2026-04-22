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
