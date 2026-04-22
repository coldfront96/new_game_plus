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


# ---------------------------------------------------------------------------
# Turn Undead (Cleric / Paladin)
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class TurnUndeadResult:
    """Outcome of a single Turn Undead attempt.

    Attributes:
        check_roll:       The d20 + CHA modifier turning check roll.
        max_hd_affected:  Maximum Hit Dice of undead that can be turned or
                          destroyed.  May be negative if the check is very low.
        damage_roll:      The 2d6 + Cleric level + CHA modifier turning damage
                          roll, which determines how many total HD worth of
                          undead are affected.
    """

    check_roll: "RollResult"
    max_hd_affected: int
    damage_roll: "RollResult"


@dataclass(slots=True)
class TurnUndeadManager:
    """Manages Turn Undead uses per day for a Cleric.

    Per 3.5e SRD: A Cleric can attempt to turn undead a number of times
    per day equal to 3 + their Charisma modifier.  Each attempt requires
    a turning check (1d20 + CHA mod) to determine the maximum HD of undead
    that can be affected, followed by a turning damage roll (2d6 + Cleric
    level + CHA mod) to determine the total HD affected.

    Attributes:
        uses_per_day:    Maximum daily Turn Undead uses.
        uses_remaining:  Remaining uses for the current day.
        cleric_level:    The Cleric's class level (used in damage roll).
        cha_mod:         The Cleric's Charisma modifier.
    """

    uses_per_day: int
    uses_remaining: int
    cleric_level: int
    cha_mod: int

    # 3.5e SRD turning check result → max HD offset from Cleric level.
    # The check total (d20 + CHA mod) is mapped to an offset applied to
    # cleric level to produce the maximum HD of undead affected.
    _CHECK_TABLE: tuple = field(
        default=(
            (0,  -4),   # result ≤ 0   → cleric_level - 4
            (3,  -3),   # result 1–3   → cleric_level - 3
            (6,  -2),   # result 4–6   → cleric_level - 2
            (9,  -1),   # result 7–9   → cleric_level - 1
            (12,  0),   # result 10–12 → cleric_level
            (15,  1),   # result 13–15 → cleric_level + 1
            (18,  2),   # result 16–18 → cleric_level + 2
            (21,  3),   # result 19–21 → cleric_level + 3
            (999, 4),   # result ≥ 22  → cleric_level + 4
        ),
        init=False,
        repr=False,
    )

    @classmethod
    def for_cleric(cls, level: int, cha_mod: int) -> "TurnUndeadManager":
        """Create a TurnUndeadManager for a Cleric at the given level.

        Args:
            level:   Cleric class level (1–20).
            cha_mod: The Cleric's Charisma modifier.

        Returns:
            A configured :class:`TurnUndeadManager`.
        """
        uses = 3 + cha_mod
        return cls(
            uses_per_day=uses,
            uses_remaining=uses,
            cleric_level=level,
            cha_mod=cha_mod,
        )

    def can_turn(self) -> bool:
        """Check if any Turn Undead uses remain.

        Returns:
            ``True`` if at least one use is available.
        """
        return self.uses_remaining > 0

    def attempt_turn(self) -> Optional["TurnUndeadResult"]:
        """Attempt to turn undead, expending one daily use.

        Per 3.5e SRD: Roll d20 + CHA mod for the turning check, map the
        result to a maximum HD using the SRD table, then roll turning
        damage (2d6 + Cleric level + CHA mod).

        Returns:
            A :class:`TurnUndeadResult` if a use was available,
            ``None`` if no uses remain.
        """
        if not self.can_turn():
            return None
        self.uses_remaining -= 1
        check_roll = roll_dice(1, 20, modifier=self.cha_mod)
        max_hd = self._hd_from_check(check_roll.total)
        damage_roll = roll_dice(2, 6, modifier=self.cleric_level + self.cha_mod)
        return TurnUndeadResult(
            check_roll=check_roll,
            max_hd_affected=max_hd,
            damage_roll=damage_roll,
        )

    def _hd_from_check(self, result: int) -> int:
        """Map a turning check total to the maximum HD of undead affected.

        Args:
            result: The turning check total (d20 + CHA mod).

        Returns:
            Maximum Hit Dice of undead that can be turned or destroyed.
        """
        for threshold, offset in self._CHECK_TABLE:
            if result <= threshold:
                return self.cleric_level + offset
        return self.cleric_level + 4  # fallback (unreachable with table above)

    def rest(self) -> None:
        """Restore all Turn Undead uses (long rest / new day)."""
        self.uses_remaining = self.uses_per_day


# ---------------------------------------------------------------------------
# Wild Shape (Druid)
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class WildShapeForm:
    """Template describing the physical stats of an animal form.

    Attributes:
        name:         Display name of the form (e.g. ``"Brown Bear"``).
        size:         Size category name (e.g. ``"LARGE"``), matching the
                      :class:`~src.rules_engine.character_35e.Size` enum key.
        strength:     STR score of the animal form.
        dexterity:    DEX score of the animal form.
        constitution: CON score of the animal form.
        natural_armor: Natural armor bonus granted by the animal form.
    """

    name: str
    size: str
    strength: int
    dexterity: int
    constitution: int
    natural_armor: int


@dataclass(slots=True)
class WildShapeState:
    """Tracks whether Wild Shape is active and preserves original stats.

    Attributes:
        active:               ``True`` while the Druid is in animal form.
        original_str:         STR score before shifting.
        original_dex:         DEX score before shifting.
        original_con:         CON score before shifting.
        original_size_name:   Size enum key (e.g. ``"MEDIUM"``) before shifting.
        form_name:            Name of the current animal form.
        natural_armor_bonus:  Natural armor bonus of the current form.
    """

    active: bool = False
    original_str: int = 10
    original_dex: int = 10
    original_con: int = 10
    original_size_name: str = "MEDIUM"
    form_name: str = ""
    natural_armor_bonus: int = 0


@dataclass(slots=True)
class WildShapeManager:
    """Manages Wild Shape uses per day for a Druid.

    Per 3.5e SRD: A Druid gains Wild Shape at 5th level with 1 use per
    day, gaining additional uses at higher levels (see :meth:`for_druid`).

    Attributes:
        uses_per_day:    Maximum daily Wild Shape uses.
        uses_remaining:  Remaining uses for the current day.
        druid_level:     The Druid's class level.
        state:           Current :class:`WildShapeState`.
    """

    uses_per_day: int
    uses_remaining: int
    druid_level: int
    state: WildShapeState = field(default_factory=WildShapeState)

    @classmethod
    def for_druid(cls, level: int) -> "WildShapeManager":
        """Create a WildShapeManager for a Druid at the given level.

        Per 3.5e SRD Wild Shape progression::

            Level 1–4:  no Wild Shape
            Level 5:    1/day
            Level 6:    2/day
            Level 7–9:  3/day
            Level 10–14: 4/day
            Level 15–17: 5/day
            Level 18–20: 6/day

        Args:
            level: Druid class level (1–20).

        Returns:
            A configured :class:`WildShapeManager`.
        """
        uses = cls._uses_from_level(level)
        return cls(uses_per_day=uses, uses_remaining=uses, druid_level=level)

    @staticmethod
    def _uses_from_level(level: int) -> int:
        """Return Wild Shape uses per day for the given Druid level."""
        if level < 5:
            return 0
        elif level < 7:
            return level - 4   # 5→1, 6→2
        elif level < 10:
            return 3           # 7→3, 8→3, 9→3
        elif level < 15:
            return 4           # 10→4 … 14→4
        elif level < 18:
            return 5           # 15→5 … 17→5
        else:
            return 6           # 18→6 … 20→6

    def can_shape(self) -> bool:
        """Check if the Druid can use Wild Shape right now.

        Returns:
            ``True`` if uses remain and Wild Shape is not already active.
        """
        return self.uses_remaining > 0 and not self.state.active

    def shift(
        self,
        character: "Character35e",
        form: WildShapeForm,
    ) -> Optional[WildShapeState]:
        """Shift the character into an animal *form*, expending one use.

        Saves the character's original STR, DEX, CON, and size, then
        applies the form's physical attributes.  Call :meth:`revert` to
        restore the originals.

        Args:
            character: The Druid character to transform.
            form:      The target :class:`WildShapeForm`.

        Returns:
            The updated :class:`WildShapeState` on success,
            ``None`` if no uses remain or already in a form.
        """
        if not self.can_shape():
            return None
        self.uses_remaining -= 1

        from src.rules_engine.character_35e import Size  # noqa: PLC0415

        # Preserve original values.
        self.state.original_str = character.strength
        self.state.original_dex = character.dexterity
        self.state.original_con = character.constitution
        self.state.original_size_name = character.size.name
        self.state.form_name = form.name
        self.state.natural_armor_bonus = form.natural_armor

        # Apply the animal form's attributes.
        character.strength = form.strength
        character.dexterity = form.dexterity
        character.constitution = form.constitution
        character.size = Size[form.size.upper()]
        self.state.active = True
        return self.state

    def revert(self, character: "Character35e") -> None:
        """Return the character to their natural form, restoring all stats.

        Args:
            character: The Druid character to revert.
        """
        if not self.state.active:
            return
        from src.rules_engine.character_35e import Size  # noqa: PLC0415

        character.strength = self.state.original_str
        character.dexterity = self.state.original_dex
        character.constitution = self.state.original_con
        character.size = Size[self.state.original_size_name]
        self.state.active = False
        self.state.natural_armor_bonus = 0
        self.state.form_name = ""

    def rest(self) -> None:
        """Restore all Wild Shape uses (long rest / new day)."""
        self.uses_remaining = self.uses_per_day


# ---------------------------------------------------------------------------
# Smite Evil (Paladin)
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class SmiteEvilResult:
    """Bonuses granted by a single Smite Evil activation.

    Attributes:
        attack_bonus:  CHA modifier added to the attack roll.
        damage_bonus:  Paladin level added to the damage roll.
    """

    attack_bonus: int
    damage_bonus: int


@dataclass(slots=True)
class SmiteEvilManager:
    """Manages Smite Evil uses per day for a Paladin.

    Per 3.5e SRD: A Paladin can smite evil once per day at 1st level,
    plus one additional time per day for every five levels thereafter
    (2/day at 6th, 3/day at 11th, 4/day at 16th).

    When smiting, the Paladin adds their Charisma modifier to the attack
    roll and their Paladin level to the damage roll against an evil target.

    Attributes:
        uses_per_day:    Maximum daily Smite Evil uses.
        uses_remaining:  Remaining uses for the current day.
        paladin_level:   The Paladin's class level (used in damage bonus).
        cha_mod:         The Paladin's Charisma modifier (used in attack bonus).
    """

    uses_per_day: int
    uses_remaining: int
    paladin_level: int
    cha_mod: int

    @classmethod
    def for_paladin(cls, level: int, cha_mod: int) -> "SmiteEvilManager":
        """Create a SmiteEvilManager for a Paladin at the given level.

        Per 3.5e SRD Smite Evil progression:
        1/day at level 1, 2/day at level 5, 3/day at level 10,
        4/day at level 15, 5/day at level 20.
        Formula: ``1 + level // 5``.

        Args:
            level:   Paladin class level (1–20).
            cha_mod: The Paladin's Charisma modifier.

        Returns:
            A configured :class:`SmiteEvilManager`.
        """
        uses = 1 + level // 5
        return cls(
            uses_per_day=uses,
            uses_remaining=uses,
            paladin_level=level,
            cha_mod=cha_mod,
        )

    def can_smite(self) -> bool:
        """Check if any Smite Evil uses remain.

        Returns:
            ``True`` if at least one use is available.
        """
        return self.uses_remaining > 0

    def activate(self) -> Optional[SmiteEvilResult]:
        """Activate Smite Evil, expending one daily use.

        Returns:
            A :class:`SmiteEvilResult` with the attack and damage bonuses,
            or ``None`` if no uses remain.
        """
        if not self.can_smite():
            return None
        self.uses_remaining -= 1
        return SmiteEvilResult(
            attack_bonus=self.cha_mod,
            damage_bonus=self.paladin_level,
        )

    def rest(self) -> None:
        """Restore all Smite Evil uses (long rest / new day)."""
        self.uses_remaining = self.uses_per_day


# ---------------------------------------------------------------------------
# Lay on Hands (Paladin)
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class LayOnHandsManager:
    """Manages the Lay on Hands daily healing pool for a Paladin.

    Per 3.5e SRD: A Paladin can heal a number of hit points equal to
    their Paladin level multiplied by their Charisma modifier each day.
    The pool may be split across multiple uses in any increment.

    Attributes:
        pool_max:       Maximum healing pool for the day.
        pool_remaining: Healing points remaining in the current day's pool.
    """

    pool_max: int
    pool_remaining: int

    @classmethod
    def for_paladin(cls, level: int, cha_mod: int) -> "LayOnHandsManager":
        """Create a LayOnHandsManager for a Paladin at the given level.

        Args:
            level:   Paladin class level (1–20).
            cha_mod: The Paladin's Charisma modifier.

        Returns:
            A configured :class:`LayOnHandsManager`.
        """
        pool = max(0, level * cha_mod)
        return cls(pool_max=pool, pool_remaining=pool)

    def can_heal(self, amount: int = 1) -> bool:
        """Check if the pool has at least *amount* points remaining.

        Args:
            amount: Minimum healing desired (default 1).

        Returns:
            ``True`` if the pool can supply at least *amount* points.
        """
        return self.pool_remaining >= amount

    def heal(self, amount: int) -> int:
        """Draw *amount* points from the healing pool.

        Draws up to *amount* points; will not overdraw the pool.

        Args:
            amount: Healing points requested.

        Returns:
            Actual healing provided (≤ *amount*, ≥ 0).
        """
        healed = min(amount, self.pool_remaining)
        self.pool_remaining -= healed
        return healed

    def rest(self) -> None:
        """Restore the full healing pool (long rest / new day)."""
        self.pool_remaining = self.pool_max


# ---------------------------------------------------------------------------
# Favored Enemy (Ranger)
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class FavoredEnemyEntry:
    """A single Favored Enemy entry with its associated bonus.

    Attributes:
        creature_type: The creature type string (e.g. ``"Undead"``,
                       ``"Humanoid"``).
        bonus:         The current bonus value (+2, +4, +6, etc.).
    """

    creature_type: str
    bonus: int


@dataclass(slots=True)
class FavoredEnemyManager:
    """Manages a Ranger's Favored Enemy list and bonuses.

    Per 3.5e SRD: A Ranger gains a Favored Enemy at 1st level with a +2
    bonus, plus an additional Favored Enemy at 5th level and every five
    levels thereafter (5, 10, 15, 20).  Each time the Ranger gains a new
    Favored Enemy, all existing bonuses increase by +2.

    The bonus applies to weapon damage rolls and to the following skill
    checks against the favored enemy type: Bluff, Listen, Sense Motive,
    Spot, and Survival.

    Attributes:
        enemies: Ordered list of :class:`FavoredEnemyEntry` objects,
                 starting with the primary (highest-bonus) enemy type.
    """

    enemies: list  # List[FavoredEnemyEntry]

    @classmethod
    def for_ranger(
        cls,
        level: int,
        enemy_types: list,  # List[str]
    ) -> "FavoredEnemyManager":
        """Create a FavoredEnemyManager for a Ranger at the given level.

        The first element of *enemy_types* is treated as the primary
        (original) Favored Enemy type.  Additional types are added in
        order as additional Favored Enemy choices.  Only as many types
        as are available for the Ranger's level are used.

        Bonus assignment (per SRD): the primary enemy always has the
        highest bonus.  Each additional enemy has a bonus 2 points lower
        than the previous one.

        Args:
            level:       Ranger class level (1–20).
            enemy_types: Ordered list of chosen enemy type strings.

        Returns:
            A configured :class:`FavoredEnemyManager`.
        """
        # Number of available Favored Enemy slots at this level.
        slots = 1 + level // 5
        used_types = enemy_types[:slots]
        num = len(used_types)

        entries = []
        for i, etype in enumerate(used_types):
            # Primary enemy (i=0) gets the highest bonus.
            # Each subsequent enemy is +2 lower.
            bonus = 2 * num - 2 * i
            entries.append(FavoredEnemyEntry(creature_type=etype, bonus=bonus))
        return cls(enemies=entries)

    def get_bonus(self, creature_type: str) -> int:
        """Return the total Favored Enemy bonus for *creature_type*.

        Args:
            creature_type: The creature type to look up (case-insensitive).

        Returns:
            The bonus value, or ``0`` if the type is not a Favored Enemy.
        """
        lower = creature_type.lower()
        for entry in self.enemies:
            if entry.creature_type.lower() == lower:
                return entry.bonus
        return 0

    def skill_bonus(self, creature_type: str) -> int:
        """Skill check bonus (Listen, Spot, Survival, etc.) against *creature_type*.

        Args:
            creature_type: The creature type to look up.

        Returns:
            The bonus value, or ``0`` if not a favored enemy.
        """
        return self.get_bonus(creature_type)

    def damage_bonus(self, creature_type: str) -> int:
        """Weapon damage bonus against *creature_type*.

        Args:
            creature_type: The creature type to look up.

        Returns:
            The bonus value, or ``0`` if not a favored enemy.
        """
        return self.get_bonus(creature_type)
