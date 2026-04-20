"""
src/rules_engine/feat_engine.py
-------------------------------
D&D 3.5e Feat Engine for the New Game Plus rules engine.

Implements a registry-based feat system that dynamically modifies character
stats (AC, attack, damage, initiative, etc.) according to 3.5e SRD rules.

The :class:`FeatRegistry` provides O(1) lookup for feat logic, avoiding
expensive string comparisons during combat resolution.

Usage::

    from src.rules_engine.feat_engine import FeatRegistry
    from src.rules_engine.character_35e import Character35e

    fighter = Character35e(
        name="Aldric", char_class="Fighter", level=5,
        strength=16, dexterity=13, feats=["Improved Initiative"]
    )

    init_bonus = FeatRegistry.get_initiative_bonus(fighter)
    # +4 from Improved Initiative
"""

from __future__ import annotations

from dataclasses import dataclass
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
    """Registry-based lookup for feat logic.

    All feat effects are resolved via class-level dictionaries keyed by
    feat name, providing O(1) access during combat ticks. This avoids
    repeated string comparisons and if/elif chains.
    """

    # Maps feat name → initiative bonus value
    _INITIATIVE_BONUSES: Dict[str, int] = {
        "Improved Initiative": 4,
    }

    # Maps feat name → attack bonus value (flat, requires weapon match)
    _ATTACK_BONUSES: Dict[str, int] = {
        "Weapon Focus": 1,
    }

    # Set of feat names that support Power Attack mechanic
    _POWER_ATTACK_FEATS: set = {"Power Attack"}

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

        Currently no standard feats provide flat AC bonuses, but the
        hook is available for future expansion (e.g. Dodge feat).

        Args:
            character: The character whose feats are checked.

        Returns:
            Sum of all AC bonuses from feats.
        """
        return 0
