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

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, Optional

from src.rules_engine.dice import roll_dice

if TYPE_CHECKING:
    from src.rules_engine.character_35e import Character35e
    from src.rules_engine.dice import RollResult


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


# ---------------------------------------------------------------------------
# Bardic Music
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class InspireCourageBonus:
    """Result of an Inspire Courage activation.

    Per 3.5e SRD: Inspire Courage grants a morale bonus on saving throws
    against charm and fear effects, and a morale bonus on attack and weapon
    damage rolls.

    Attributes:
        attack_bonus:  Morale bonus to attack rolls.
        damage_bonus:  Morale bonus to weapon damage rolls.
        save_bonus:    Morale bonus to saves vs. charm and fear.
    """

    attack_bonus: int = 1
    damage_bonus: int = 1
    save_bonus: int = 1


@dataclass(slots=True)
class BardicMusicManager:
    """Manages Bardic Music uses per day for a Bard.

    Per 3.5e SRD: A Bard can use Bardic Music a number of times per day
    equal to their Bard level. Each use requires a Perform check and
    expends one daily use.

    Attributes:
        uses_per_day: Maximum daily uses (equal to Bard level).
        uses_remaining: Remaining uses for the current day.
    """

    uses_per_day: int
    uses_remaining: int

    @classmethod
    def for_bard(cls, level: int) -> "BardicMusicManager":
        """Create a BardicMusicManager for a Bard at the given level.

        Args:
            level: Bard class level (1–20).

        Returns:
            A configured :class:`BardicMusicManager`.
        """
        return cls(uses_per_day=level, uses_remaining=level)

    def can_use(self) -> bool:
        """Check if the Bard has remaining Bardic Music uses.

        Returns:
            ``True`` if at least one use remains.
        """
        return self.uses_remaining > 0

    def inspire_courage(self) -> Optional[InspireCourageBonus]:
        """Activate Inspire Courage, expending one Bardic Music use.

        Per 3.5e SRD: An affected ally receives a +1 morale bonus on
        saving throws against charm and fear effects and a +1 morale
        bonus on attack and weapon damage rolls.

        Returns:
            An :class:`InspireCourageBonus` if activation succeeds,
            ``None`` if no uses remain.
        """
        if not self.can_use():
            return None
        self.uses_remaining -= 1
        return InspireCourageBonus(attack_bonus=1, damage_bonus=1, save_bonus=1)

    def rest(self) -> None:
        """Restore all Bardic Music uses (long rest / new day)."""
        self.uses_remaining = self.uses_per_day


# ---------------------------------------------------------------------------
# Barbarian Rage
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class RageState:
    """Tracks the active modifiers applied during a Barbarian Rage.

    Per 3.5e SRD: While raging a Barbarian gains +4 STR, +4 CON,
    +2 morale bonus on Will saves, but suffers a -2 penalty to AC.
    The CON increase generates temporary hit points (2 × character level).

    Attributes:
        active:      Whether the rage is currently in effect.
        str_bonus:   STR score bonus while raging (+4).
        con_bonus:   CON score bonus while raging (+4).
        will_bonus:  Morale bonus to Will saves while raging (+2).
        ac_penalty:  AC penalty while raging (stored as negative, -2).
        temp_hp:     Temporary hit points gained from the CON increase.
    """

    active: bool = False
    str_bonus: int = 0
    con_bonus: int = 0
    will_bonus: int = 0
    ac_penalty: int = 0
    temp_hp: int = 0


@dataclass(slots=True)
class RageManager:
    """Manages Barbarian Rage uses per day and active rage state.

    Per 3.5e SRD: A Barbarian can rage once per day at 1st level,
    plus one additional time per day for every four levels thereafter
    (2/day at 4th, 3/day at 8th, etc.).

    Attributes:
        uses_per_day:    Maximum daily rage uses.
        uses_remaining:  Remaining uses for the current day.
        state:           Current :class:`RageState` (active or inactive).
    """

    uses_per_day: int
    uses_remaining: int
    state: RageState = field(default_factory=RageState)

    @classmethod
    def for_barbarian(cls, level: int) -> "RageManager":
        """Create a RageManager for a Barbarian at the given level.

        Args:
            level: Barbarian class level (1–20).

        Returns:
            A configured :class:`RageManager`.
        """
        # 1 use at level 1, +1 every 4 levels (1→1, 4→2, 8→3, 12→4…)
        uses = 1 + level // 4
        return cls(uses_per_day=uses, uses_remaining=uses)

    def can_rage(self) -> bool:
        """Check if the Barbarian can currently rage.

        Returns:
            ``True`` if there are uses remaining and rage is not active.
        """
        return self.uses_remaining > 0 and not self.state.active

    def activate(self, character: "Character35e") -> Optional[RageState]:
        """Activate Rage, applying all bonuses and penalties.

        Per 3.5e SRD: +4 STR, +4 CON, +2 morale Will save, -2 AC.
        The CON increase grants temporary hit points equal to 2 × level
        (since +4 CON raises the CON modifier by +2, yielding 2 extra HP
        per character level).

        Args:
            character: The Barbarian entering rage (used to compute temp HP).

        Returns:
            The updated :class:`RageState` if activation succeeds,
            ``None`` if no uses remain or rage is already active.
        """
        if not self.can_rage():
            return None
        self.uses_remaining -= 1
        self.state.active = True
        self.state.str_bonus = 4
        self.state.con_bonus = 4
        self.state.will_bonus = 2
        self.state.ac_penalty = -2
        # +4 CON raises CON modifier by +2 → 2 temp HP per character level
        self.state.temp_hp = 2 * character.level
        return self.state

    def deactivate(self) -> None:
        """End the Rage, removing all temporary bonuses and penalties."""
        self.state.active = False
        self.state.str_bonus = 0
        self.state.con_bonus = 0
        self.state.will_bonus = 0
        self.state.ac_penalty = 0
        self.state.temp_hp = 0

    def rest(self) -> None:
        """Restore all Rage uses (long rest / new day)."""
        self.uses_remaining = self.uses_per_day


# ---------------------------------------------------------------------------
# Sneak Attack
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class SneakAttack:
    """3.5e Rogue Sneak Attack ability.

    Per 3.5e SRD: A Rogue deals extra d6 damage whenever the target is
    denied its Dexterity bonus to AC (flat-footed) or when the Rogue
    flanks the target.  The bonus damage is +1d6 at 1st level, +2d6 at
    3rd level, +3d6 at 5th level, and so on (every 2 Rogue levels).

    This class is stateless; all methods are static.
    """

    @staticmethod
    def dice_count(level: int) -> int:
        """Return the number of d6 dice rolled for Sneak Attack at *level*.

        Args:
            level: Rogue class level (1–20).

        Returns:
            Number of d6 dice (1 at L1, 2 at L3, 3 at L5, …).
        """
        return (level + 1) // 2

    @staticmethod
    def roll_damage(level: int) -> "RollResult":
        """Roll Sneak Attack bonus damage for a Rogue of *level*.

        Args:
            level: Rogue class level.

        Returns:
            A :class:`~src.rules_engine.dice.RollResult` for the bonus dice.
        """
        count = SneakAttack.dice_count(level)
        return roll_dice(count, 6)
