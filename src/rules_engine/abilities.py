"""
src/rules_engine/abilities.py
-----------------------------
D&D 3.5e Class Abilities engine for the New Game Plus rules engine.

Implements class-specific special abilities that modify combat mechanics
beyond what feats provide. Focuses on defensive class features from the
3.5e SRD.

Usage::

    from src.rules_engine.abilities import AbilityRegistry, Evasion, UncannyDodge
    from src.rules_engine.character_35e import Character35e

    rogue = Character35e(
        name="Shadow", char_class="Rogue", level=3, dexterity=16,
    )

    # Check if the rogue has Evasion
    if AbilityRegistry.has_evasion(rogue):
        # On successful Reflex save, take zero damage
        damage = Evasion.resolve_damage(save_succeeded=True, base_damage=20)
        # damage == 0
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from src.rules_engine.character_35e import Character35e


# ---------------------------------------------------------------------------
# Evasion
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Evasion:
    """3.5e Evasion ability (Rogue 2, Monk 2).

    When a character with Evasion makes a successful Reflex saving throw
    against an attack that normally deals half damage on a success, the
    character takes no damage instead.

    On a failed save, the character takes full damage (no half-damage
    reduction from Evasion alone).
    """

    @staticmethod
    def resolve_damage(save_succeeded: bool, base_damage: int) -> int:
        """Resolve damage considering Evasion.

        Args:
            save_succeeded: Whether the Reflex save was successful.
            base_damage:    The full damage from the area effect.

        Returns:
            0 if save succeeded (Evasion negates), otherwise full damage.
        """
        if save_succeeded:
            return 0
        return base_damage


@dataclass(slots=True)
class ImprovedEvasion:
    """3.5e Improved Evasion (Rogue 10, Monk 9).

    Like Evasion, but on a failed save the character takes only half
    damage instead of full damage.
    """

    @staticmethod
    def resolve_damage(save_succeeded: bool, base_damage: int) -> int:
        """Resolve damage considering Improved Evasion.

        Args:
            save_succeeded: Whether the Reflex save was successful.
            base_damage:    The full damage from the area effect.

        Returns:
            0 on success, half damage (rounded down) on failure.
        """
        if save_succeeded:
            return 0
        return base_damage // 2


# ---------------------------------------------------------------------------
# Uncanny Dodge
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class UncannyDodge:
    """3.5e Uncanny Dodge (Rogue 4, Barbarian 2).

    A character with Uncanny Dodge retains their Dexterity bonus to AC
    even when flat-footed or struck by an invisible attacker. They still
    lose their DEX bonus if immobilized.

    Attributes:
        retains_dex_bonus: Always ``True`` for characters with this ability.
    """

    retains_dex_bonus: bool = True

    @staticmethod
    def get_flat_footed_ac(character: "Character35e") -> int:
        """Compute flat-footed AC for a character with Uncanny Dodge.

        Unlike normal flat-footed AC (which drops DEX bonus), Uncanny
        Dodge retains the DEX bonus.

        Args:
            character: The character with Uncanny Dodge.

        Returns:
            AC value including DEX bonus even when flat-footed.
        """
        from src.rules_engine.character_35e import _ability_modifier

        dex_mod = _ability_modifier(character.dexterity)
        # Only add positive DEX mod (negative DEX still applies normally)
        dex_bonus = max(0, dex_mod)
        base_ff_ac = 10 + character.size.value
        if character.equipment_manager is not None:
            base_ff_ac += character.equipment_manager.get_armor_bonus()
            base_ff_ac += character.equipment_manager.get_shield_bonus()
        return base_ff_ac + dex_bonus


# ---------------------------------------------------------------------------
# Ability Registry
# ---------------------------------------------------------------------------

class AbilityRegistry:
    """Registry for class ability lookups.

    Provides O(1) checks for whether a character qualifies for specific
    class abilities based on class and level requirements from the 3.5e SRD.
    """

    # Class → minimum level for Evasion
    _EVASION_CLASSES: Dict[str, int] = {
        "Rogue": 2,
        "Monk": 2,
    }

    # Class → minimum level for Improved Evasion
    _IMPROVED_EVASION_CLASSES: Dict[str, int] = {
        "Rogue": 10,
        "Monk": 9,
    }

    # Class → minimum level for Uncanny Dodge
    _UNCANNY_DODGE_CLASSES: Dict[str, int] = {
        "Rogue": 4,
        "Barbarian": 2,
    }

    @classmethod
    def has_evasion(cls, character: "Character35e") -> bool:
        """Check if a character has Evasion based on class and level.

        Args:
            character: The character to check.

        Returns:
            ``True`` if the character's class grants Evasion at their level.
        """
        required_level = cls._EVASION_CLASSES.get(character.char_class)
        if required_level is None:
            return False
        return character.level >= required_level

    @classmethod
    def has_improved_evasion(cls, character: "Character35e") -> bool:
        """Check if a character has Improved Evasion.

        Args:
            character: The character to check.

        Returns:
            ``True`` if the character qualifies for Improved Evasion.
        """
        required_level = cls._IMPROVED_EVASION_CLASSES.get(character.char_class)
        if required_level is None:
            return False
        return character.level >= required_level

    @classmethod
    def has_uncanny_dodge(cls, character: "Character35e") -> bool:
        """Check if a character has Uncanny Dodge.

        Args:
            character: The character to check.

        Returns:
            ``True`` if the character qualifies for Uncanny Dodge.
        """
        required_level = cls._UNCANNY_DODGE_CLASSES.get(character.char_class)
        if required_level is None:
            return False
        return character.level >= required_level

    @classmethod
    def resolve_flat_footed_ac(cls, character: "Character35e") -> int:
        """Resolve flat-footed AC considering Uncanny Dodge.

        If the character has Uncanny Dodge, they retain their DEX bonus.
        Otherwise, normal flat-footed AC rules apply.

        Args:
            character: The character whose flat-footed AC to compute.

        Returns:
            The effective flat-footed AC.
        """
        if cls.has_uncanny_dodge(character):
            return UncannyDodge.get_flat_footed_ac(character)
        return character.flat_footed_ac
