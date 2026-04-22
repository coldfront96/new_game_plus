"""
src/rules_engine/combat.py
--------------------------
Combat resolution logic built on D&D 3.5e SRD rules.

The :class:`AttackResolver` takes an attacker and a defender
(:class:`~src.rules_engine.character_35e.Character35e` instances) and
resolves a melee or ranged attack, returning a :class:`CombatResult`
that describes the outcome.

Usage::

    from src.rules_engine.character_35e import Character35e
    from src.rules_engine.combat import AttackResolver

    fighter = Character35e(name="Aldric", char_class="Fighter", level=5,
                           strength=16, dexterity=13, constitution=14)
    goblin  = Character35e(name="Goblin", char_class="Rogue", level=1,
                           strength=8, dexterity=14, size=Size.SMALL)

    result = AttackResolver.resolve_attack(fighter, goblin)
    print(result)
    # CombatResult(hit=True, roll=..., attack_bonus=8, target_ac=12,
    #              damage_roll=..., total_damage=7, critical=False)
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from src.rules_engine.character_35e import Character35e
from src.rules_engine.dice import RollResult, roll_d20, roll_dice
from src.loot_math.item import Item as _Item

if TYPE_CHECKING:
    from src.terrain.lighting import LightLevel


# ---------------------------------------------------------------------------
# CombatResult
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class CombatResult:
    """Outcome of a single attack action.

    Attributes:
        hit:                    ``True`` if the attack met or exceeded the target AC.
        roll:                   The d20 :class:`RollResult` (includes raw die value).
        attack_bonus:           Total attack modifier applied to the d20 roll.
        target_ac:              Defender's Armour Class used for the comparison.
        damage_roll:            Damage :class:`RollResult` (``None`` on a miss).
        total_damage:           Final damage dealt after DR (0 on a miss, ≥ 1 on a hit).
        critical:               ``True`` if the attack was a confirmed critical hit.
        damage_reduction_applied: DR subtracted from the raw damage total (0 if none).
        miss_chance_roll:       The d% roll used for concealment check (``None`` if no
                                miss-chance check was performed).
        miss_chance_threshold:  The miss-chance percentage that applied (0, 20, or 50).
        miss_chance_triggered:  ``True`` if the miss-chance roll caused the attack to
                                miss despite otherwise hitting AC.
        sneak_attack_damage:    Extra damage dealt by a Rogue's Sneak Attack (0 if none).
        smite_evil_damage:      Extra damage added by Paladin Smite Evil (0 if none).
        favored_enemy_damage:   Extra damage added by Ranger Favored Enemy (0 if none).
    """

    hit: bool
    roll: RollResult
    attack_bonus: int
    target_ac: int
    damage_roll: Optional[RollResult]
    total_damage: int
    critical: bool
    damage_reduction_applied: int = 0
    miss_chance_roll: Optional[int] = None
    miss_chance_threshold: int = 0
    miss_chance_triggered: bool = False
    sneak_attack_damage: int = 0
    smite_evil_damage: int = 0
    favored_enemy_damage: int = 0


# ---------------------------------------------------------------------------
# AttackResolver
# ---------------------------------------------------------------------------

class AttackResolver:
    """Stateless resolver for D&D 3.5e attack actions.

    All methods are class/static — no instance state is required.
    """

    # Standard 3.5e unarmed damage: 1d3 for Medium, modified by STR.
    _UNARMED_DICE_COUNT: int = 1
    _UNARMED_DICE_SIDES: int = 3

    # Natural 1 is always a miss.
    _NATURAL_FUMBLE: int = 1

    # 3.5e SRD Monk unarmed strike progression (Medium Monk).
    # Maps minimum Monk level → (dice_count, dice_sides).
    _MONK_UNARMED_TABLE: tuple = (
        (16, 2, 8),   # Level 16+: 2d8
        (12, 2, 6),   # Level 12+: 2d6
        ( 8, 1, 10),  # Level  8+: 1d10
        ( 4, 1,  8),  # Level  4+: 1d8
        ( 1, 1,  6),  # Level  1+: 1d6
    )

    @classmethod
    def _monk_unarmed_dice(cls, level: int) -> tuple:
        """Return (count, sides) for a Monk's unarmed strike at *level*.

        Args:
            level: Monk class level (1–20).

        Returns:
            Tuple of ``(dice_count, dice_sides)``.
        """
        for min_level, count, sides in cls._MONK_UNARMED_TABLE:
            if level >= min_level:
                return count, sides
        return 1, 6  # fallback (should not be reached)

    @classmethod
    def _parse_damage_reduction(cls, dr_str: str) -> int:
        """Parse a DR string such as ``"5/Magic"`` or ``"3/-"`` and return
        the numeric reduction amount.  Returns ``0`` for empty or invalid strings.
        """
        if not dr_str:
            return 0
        try:
            return int(dr_str.split("/")[0])
        except (ValueError, IndexError):
            return 0

    @classmethod
    def resolve_attack(
        cls,
        attacker: Character35e,
        defender: Character35e,
        *,
        use_ranged: bool = False,
        damage_dice_count: int = 0,
        damage_dice_sides: int = 0,
        damage_bonus: int = 0,
        threat_range: int = 20,
        damage_multiplier: int = 2,
        defender_light_level: Optional["LightLevel"] = None,
        attacker_has_darkvision: bool = False,
        target_is_flat_footed: bool = False,
        smite_evil_attack_bonus: int = 0,
        smite_evil_damage_bonus: int = 0,
        favored_enemy_damage_bonus: int = 0,
    ) -> CombatResult:
        """Resolve a single melee (or ranged) attack.

        Steps (per the 3.5e SRD):
        1. Roll d20 + attack bonus (+ Smite Evil CHA bonus if active).
        2. Natural 1 → automatic miss.
        3. Compare total against defender's AC (hit or miss).
        4. Natural 20 or any roll ≥ *threat_range* is a *critical threat*.
        5. On a critical threat, roll a second *confirmation* roll against AC.
           If the confirmation hits, the attack is a *confirmed critical*.
        6. On a hit, check concealment miss chance from lighting:
           - DIM light → 20 % miss chance (Concealment).
           - DARKNESS → 50 % miss chance (Total Concealment) unless the
             attacker has Darkvision (within range).
           Roll d% (1–100); if the roll ≤ miss_chance the attack misses.
        7. On a hit, roll damage; multiply by *damage_multiplier* on a
           confirmed critical.  Add Smite Evil and Favored Enemy bonuses.
        8. Subtract the defender's ``damage_reduction`` from the final damage.
           Minimum 1 damage on a hit (applied before DR has a floor of 0 net).

        Args:
            attacker:              The attacking :class:`Character35e`.
            defender:              The defending :class:`Character35e`.
            use_ranged:            If ``True`` use DEX-based ranged attack bonus
                                   instead of STR-based melee.
            damage_dice_count:     Override number of damage dice (0 → unarmed).
            damage_dice_sides:     Override damage die size (0 → unarmed).
            damage_bonus:          Extra flat damage added on top of STR modifier.
            threat_range:          Minimum die face that generates a critical threat
                                   (default 20; weapons with 19-20 pass 19, etc.).
            damage_multiplier:     Damage multiplier applied on a confirmed critical
                                   (default ×2; greataxe uses ×3, etc.).
            defender_light_level:  The :class:`~src.terrain.lighting.LightLevel` at
                                   the defender's position.  ``None`` means no
                                   lighting modifier is applied (treat as BRIGHT).
            attacker_has_darkvision: If ``True`` the attacker has Darkvision and
                                   ignores the miss chance from DARKNESS.
            target_is_flat_footed: If ``True`` and the attacker is a Rogue, Sneak
                                   Attack damage is added (unless the defender has
                                   Uncanny Dodge).
            smite_evil_attack_bonus: Flat bonus added to the attack roll from a
                                   Paladin's active Smite Evil (typically the
                                   Paladin's CHA modifier).  Pass 0 if not smiting.
            smite_evil_damage_bonus: Flat bonus added to damage from Smite Evil
                                   (typically the Paladin's class level).  Only
                                   applied on a hit.  Pass 0 if not smiting.
            favored_enemy_damage_bonus: Flat damage bonus from a Ranger's Favored
                                   Enemy feature against the current target's
                                   creature type.  Pass 0 if not applicable.

        Returns:
            A :class:`CombatResult` describing the outcome.
        """
        # --- Attack bonus ---------------------------------------------------
        if use_ranged:
            attack_bonus = attacker.ranged_attack
        else:
            attack_bonus = attacker.melee_attack

        # Smite Evil adds CHA modifier to the attack roll.
        attack_bonus += smite_evil_attack_bonus

        # --- Attack roll (d20) ----------------------------------------------
        roll = roll_d20(modifier=attack_bonus)
        raw_d20 = roll.raw  # the actual die face (1–20)

        target_ac = defender.armor_class

        # --- Hit determination ----------------------------------------------
        if raw_d20 == cls._NATURAL_FUMBLE:
            return CombatResult(
                hit=False,
                roll=roll,
                attack_bonus=attack_bonus,
                target_ac=target_ac,
                damage_roll=None,
                total_damage=0,
                critical=False,
            )

        hit = roll.total >= target_ac

        # --- Critical threat & confirmation ---------------------------------
        is_threat = raw_d20 >= threat_range
        confirmed_critical = False
        if is_threat and hit:
            # Natural 20 is always a hit; confirm roll must also meet AC.
            confirm_roll = roll_d20(modifier=attack_bonus)
            confirmed_critical = confirm_roll.total >= target_ac
        elif is_threat:
            # Threat on a miss: confirmation would also need to beat AC.
            confirm_roll = roll_d20(modifier=attack_bonus)
            if confirm_roll.total >= target_ac:
                hit = True
                confirmed_critical = True

        if not hit:
            return CombatResult(
                hit=False,
                roll=roll,
                attack_bonus=attack_bonus,
                target_ac=target_ac,
                damage_roll=None,
                total_damage=0,
                critical=False,
            )

        # --- Concealment miss chance (3.5e SRD) --------------------------------
        # Imported inline to avoid a circular import at module level.
        miss_chance_roll: Optional[int] = None
        miss_chance_threshold: int = 0
        miss_chance_triggered: bool = False

        if defender_light_level is not None:
            from src.terrain.lighting import LightLevel  # noqa: PLC0415

            if defender_light_level == LightLevel.DIM:
                # Concealment: 20 % miss chance
                miss_chance_threshold = 20
                miss_chance_roll = random.randint(1, 100)
                if miss_chance_roll <= miss_chance_threshold:
                    miss_chance_triggered = True
                    return CombatResult(
                        hit=False,
                        roll=roll,
                        attack_bonus=attack_bonus,
                        target_ac=target_ac,
                        damage_roll=None,
                        total_damage=0,
                        critical=False,
                        miss_chance_roll=miss_chance_roll,
                        miss_chance_threshold=miss_chance_threshold,
                        miss_chance_triggered=True,
                    )

            elif defender_light_level == LightLevel.DARKNESS and not attacker_has_darkvision:
                # Total Concealment: 50 % miss chance
                miss_chance_threshold = 50
                miss_chance_roll = random.randint(1, 100)
                if miss_chance_roll <= miss_chance_threshold:
                    miss_chance_triggered = True
                    return CombatResult(
                        hit=False,
                        roll=roll,
                        attack_bonus=attack_bonus,
                        target_ac=target_ac,
                        damage_roll=None,
                        total_damage=0,
                        critical=False,
                        miss_chance_roll=miss_chance_roll,
                        miss_chance_threshold=miss_chance_threshold,
                        miss_chance_triggered=True,
                    )

        # --- Damage ----------------------------------------------------------
        # Monk unarmed progression: if the attacker is a Monk and no weapon
        # dice were provided, use the 3.5e SRD Monk unarmed strike table
        # instead of the default 1d3 unarmed damage.
        if (
            attacker.char_class == "Monk"
            and damage_dice_count == 0
            and damage_dice_sides == 0
        ):
            d_count, d_sides = cls._monk_unarmed_dice(attacker.level)
        else:
            d_count = damage_dice_count if damage_dice_count > 0 else cls._UNARMED_DICE_COUNT
            d_sides = damage_dice_sides if damage_dice_sides > 0 else cls._UNARMED_DICE_SIDES

        # STR modifier applies to melee damage; ranged gets no STR bonus
        str_mod = attacker.strength_mod if not use_ranged else 0
        total_modifier = str_mod + damage_bonus

        damage_roll = roll_dice(d_count, d_sides, modifier=total_modifier)

        # Minimum 1 damage on a hit (3.5e SRD rule)
        total_damage = max(1, damage_roll.total)

        # Apply critical multiplier on confirmed crits.
        if confirmed_critical:
            total_damage *= damage_multiplier

        # --- Sneak Attack (Rogue) -------------------------------------------
        # A Rogue deals bonus Sneak Attack damage when the target is denied
        # its DEX bonus to AC (flat-footed) and does not have Uncanny Dodge.
        sneak_attack_damage = 0
        if attacker.char_class == "Rogue" and target_is_flat_footed:
            from src.rules_engine.abilities import AbilityRegistry, SneakAttack  # noqa: PLC0415

            if not AbilityRegistry.has_uncanny_dodge(defender):
                sa_roll = SneakAttack.roll_damage(attacker.level)
                sneak_attack_damage = max(0, sa_roll.total)
                total_damage += sneak_attack_damage

        # --- Smite Evil (Paladin) -------------------------------------------
        # Add Paladin level to damage when Smite Evil is active against an
        # evil target.  The caller is responsible for checking alignment and
        # passing a non-zero smite_evil_damage_bonus only when appropriate.
        if smite_evil_damage_bonus:
            total_damage += smite_evil_damage_bonus

        # --- Favored Enemy (Ranger) -----------------------------------------
        # Add the Favored Enemy damage bonus when the target matches a Ranger's
        # Favored Enemy type.  The caller resolves the creature type and passes
        # the pre-calculated bonus.
        if favored_enemy_damage_bonus:
            total_damage += favored_enemy_damage_bonus

        # Subtract defender's Damage Reduction.
        dr_value = cls._parse_damage_reduction(defender.damage_reduction)
        total_damage = max(0, total_damage - dr_value)

        return CombatResult(
            hit=True,
            roll=roll,
            attack_bonus=attack_bonus,
            target_ac=target_ac,
            damage_roll=damage_roll,
            total_damage=total_damage,
            critical=confirmed_critical,
            damage_reduction_applied=dr_value,
            miss_chance_roll=miss_chance_roll,
            miss_chance_threshold=miss_chance_threshold,
            miss_chance_triggered=False,
            sneak_attack_damage=sneak_attack_damage,
            smite_evil_damage=smite_evil_damage_bonus if smite_evil_damage_bonus else 0,
            favored_enemy_damage=favored_enemy_damage_bonus if favored_enemy_damage_bonus else 0,
        )


# ---------------------------------------------------------------------------
# TripResult
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class TripResult:
    """Outcome of a Trip attempt.

    Attributes:
        success:          ``True`` if the trip succeeded (target is now Prone).
        attacker_roll:    The attacker's opposed Strength check result.
        defender_roll:    The defender's opposed Strength check result.
        attacker_total:   Attacker's total (roll + STR mod + size modifier).
        defender_total:   Defender's total (roll + STR or DEX mod + size modifier).
    """

    success: bool
    attacker_roll: RollResult
    defender_roll: RollResult
    attacker_total: int
    defender_total: int


# ---------------------------------------------------------------------------
# TripResolver
# ---------------------------------------------------------------------------

# 3.5e SRD special size modifiers for trip/grapple (larger = bonus)
_TRIP_SIZE_MODIFIER = {
    "FINE": -16,
    "DIMINUTIVE": -12,
    "TINY": -8,
    "SMALL": -4,
    "MEDIUM": 0,
    "LARGE": 4,
    "HUGE": 8,
    "GARGANTUAN": 12,
    "COLOSSAL": 16,
}


class TripResolver:
    """Stateless resolver for D&D 3.5e Trip maneuver.

    Per the 3.5e SRD, a Trip is resolved as an opposed Strength check:
    1. Attacker rolls d20 + STR mod + special size modifier.
    2. Defender rolls d20 + STR mod (or DEX mod, whichever is higher) +
       special size modifier.
    3. If the attacker's total meets or exceeds the defender's, the trip
       succeeds and the target gains the Prone condition.

    The special size modifier for trip uses +4 per size category above
    Medium and -4 per size below (opposite of the AC size modifier).
    """

    @classmethod
    def resolve_trip(
        cls,
        attacker: Character35e,
        defender: Character35e,
    ) -> TripResult:
        """Resolve a Trip attempt between attacker and defender.

        Args:
            attacker: The character attempting the trip.
            defender: The character being tripped.

        Returns:
            A :class:`TripResult` describing the outcome.
        """
        # Attacker: d20 + STR mod + trip size modifier
        attacker_size_mod = _TRIP_SIZE_MODIFIER.get(attacker.size.name, 0)
        attacker_modifier = attacker.strength_mod + attacker_size_mod
        attacker_roll = roll_d20(modifier=attacker_modifier)

        # Defender: d20 + max(STR mod, DEX mod) + trip size modifier
        defender_size_mod = _TRIP_SIZE_MODIFIER.get(defender.size.name, 0)
        defender_ability_mod = max(defender.strength_mod, defender.dexterity_mod)
        defender_modifier = defender_ability_mod + defender_size_mod
        defender_roll = roll_d20(modifier=defender_modifier)

        # Opposed check: attacker wins ties
        success = attacker_roll.total >= defender_roll.total

        return TripResult(
            success=success,
            attacker_roll=attacker_roll,
            defender_roll=defender_roll,
            attacker_total=attacker_roll.total,
            defender_total=defender_roll.total,
        )


# ---------------------------------------------------------------------------
# GrappleResult
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class GrappleResult:
    """Outcome of a Grapple attempt.

    Attributes:
        success:        ``True`` if the grapple succeeded (target is grappled).
        attacker_roll:  The attacker's grapple check :class:`RollResult`.
        defender_roll:  The defender's grapple check :class:`RollResult`.
        attacker_total: Attacker's total (d20 + BAB + STR mod + size modifier).
        defender_total: Defender's total (d20 + BAB + STR mod + size modifier).
    """

    success: bool
    attacker_roll: RollResult
    defender_roll: RollResult
    attacker_total: int
    defender_total: int


# ---------------------------------------------------------------------------
# GrappleResolver
# ---------------------------------------------------------------------------

class GrappleResolver:
    """Stateless resolver for D&D 3.5e Grapple maneuver.

    Per the 3.5e SRD, a Grapple check is resolved as an opposed grapple check:
    1. Attacker rolls d20 + BAB + STR mod + special size modifier.
    2. Defender rolls d20 + BAB + STR mod + special size modifier.
    3. If the attacker's total meets or exceeds the defender's, the grapple
       succeeds and the target is considered Grappled.

    The special grapple size modifier mirrors the trip size modifier:
    +4 per size category above Medium, -4 per size below.
    """

    @classmethod
    def resolve_grapple(
        cls,
        attacker: Character35e,
        defender: Character35e,
    ) -> GrappleResult:
        """Resolve a Grapple attempt between attacker and defender.

        Args:
            attacker: The character initiating the grapple.
            defender: The character being grappled.

        Returns:
            A :class:`GrappleResult` describing the outcome.
        """
        # Attacker: d20 + BAB + STR mod + grapple size modifier
        attacker_size_mod = _TRIP_SIZE_MODIFIER.get(attacker.size.name, 0)
        attacker_modifier = (
            attacker.base_attack_bonus + attacker.strength_mod + attacker_size_mod
        )
        attacker_roll = roll_d20(modifier=attacker_modifier)

        # Defender: d20 + BAB + STR mod + grapple size modifier
        defender_size_mod = _TRIP_SIZE_MODIFIER.get(defender.size.name, 0)
        defender_modifier = (
            defender.base_attack_bonus + defender.strength_mod + defender_size_mod
        )
        defender_roll = roll_d20(modifier=defender_modifier)

        # Opposed check: attacker wins ties
        success = attacker_roll.total >= defender_roll.total

        return GrappleResult(
            success=success,
            attacker_roll=attacker_roll,
            defender_roll=defender_roll,
            attacker_total=attacker_roll.total,
            defender_total=defender_roll.total,
        )


# ---------------------------------------------------------------------------
# BullRushResult
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class BullRushResult:
    """Outcome of a Bull Rush attempt.

    Attributes:
        success:        ``True`` if the bull rush succeeded.
        attacker_roll:  The attacker's Strength check :class:`RollResult`.
        defender_roll:  The defender's Strength check :class:`RollResult`.
        attacker_total: Attacker's total (d20 + STR mod + size bonus + charge).
        defender_total: Defender's total (d20 + STR mod + size bonus).
        push_distance:  Feet the defender is pushed (0 on failure, ≥ 5 on success).
    """

    success: bool
    attacker_roll: RollResult
    defender_roll: RollResult
    attacker_total: int
    defender_total: int
    push_distance: int


# ---------------------------------------------------------------------------
# BullRushResolver
# ---------------------------------------------------------------------------

class BullRushResolver:
    """Stateless resolver for D&D 3.5e Bull Rush maneuver.

    Per the 3.5e SRD, a Bull Rush is resolved as an opposed Strength check:
    1. Attacker rolls d20 + STR mod + size modifier (+ 2 if charging).
    2. Defender rolls d20 + STR mod + size modifier.
    3. If the attacker wins, the defender is pushed 5 ft plus 5 ft for every
       5 points by which the attacker exceeds the defender's result.

    The size modifier for bull rush follows the same table as trip/grapple
    (+4 per size category above Medium, -4 per size below).
    """

    @classmethod
    def resolve_bull_rush(
        cls,
        attacker: Character35e,
        defender: Character35e,
        *,
        charging: bool = False,
    ) -> BullRushResult:
        """Resolve a Bull Rush attempt between attacker and defender.

        Args:
            attacker: The character initiating the bull rush.
            defender: The character being pushed.
            charging: If ``True``, the attacker gains +2 to the check for
                      charging into the bull rush (3.5e SRD rule).

        Returns:
            A :class:`BullRushResult` describing the outcome.
        """
        # Attacker: d20 + STR mod + size modifier (+ 2 if charging)
        attacker_size_mod = _TRIP_SIZE_MODIFIER.get(attacker.size.name, 0)
        charge_bonus = 2 if charging else 0
        attacker_modifier = attacker.strength_mod + attacker_size_mod + charge_bonus
        attacker_roll = roll_d20(modifier=attacker_modifier)

        # Defender: d20 + STR mod + size modifier
        defender_size_mod = _TRIP_SIZE_MODIFIER.get(defender.size.name, 0)
        defender_modifier = defender.strength_mod + defender_size_mod
        defender_roll = roll_d20(modifier=defender_modifier)

        # Opposed check: attacker wins ties
        success = attacker_roll.total >= defender_roll.total

        # Push distance: 5 ft base + 5 ft per 5 points of margin
        if success:
            margin = attacker_roll.total - defender_roll.total
            push_distance = 5 + (margin // 5) * 5
        else:
            push_distance = 0

        return BullRushResult(
            success=success,
            attacker_roll=attacker_roll,
            defender_roll=defender_roll,
            attacker_total=attacker_roll.total,
            defender_total=defender_roll.total,
            push_distance=push_distance,
        )


# ---------------------------------------------------------------------------
# SunderResult
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class SunderResult:
    """Outcome of a Sunder attempt against an item.

    Attributes:
        hit:            ``True`` if the attack roll met or exceeded the item AC.
        roll:           The d20 :class:`RollResult`.
        attack_bonus:   Total attack modifier applied to the d20 roll.
        target_item_ac: The Armour Class of the target item.
        damage_dealt:   Net damage dealt to the item after hardness reduction
                        (0 if missed or fully absorbed by hardness).
        item_broken:    ``True`` if the item's durability has reached zero.
    """

    hit: bool
    roll: RollResult
    attack_bonus: int
    target_item_ac: int
    damage_dealt: int
    item_broken: bool


# ---------------------------------------------------------------------------
# SunderResolver
# ---------------------------------------------------------------------------


class SunderResolver:
    """Stateless resolver for D&D 3.5e Sunder maneuver.

    Per the 3.5e SRD, a Sunder is an attack against an opponent's weapon or
    shield:
    1. Make a melee attack roll against the item's AC
       (10 + attacker's STR mod + item's enhancement bonus).
    2. If the attack hits, deal weapon damage.
    3. Subtract the item's hardness from the damage; remainder reduces item HP
       (tracked here as ``durability``).
    4. If durability reaches 0, the item is destroyed (broken).

    Hardness and item HP are read from the target item's ``metadata``:
    ``"hardness"`` (default 10 for steel) and durability from the item's
    ``durability`` field (which also serves as item HP in this system).
    """

    # Default hardness values for common materials (3.5e SRD table)
    _DEFAULT_HARDNESS: int = 10  # steel

    @classmethod
    def resolve_sunder(
        cls,
        attacker: Character35e,
        target_item: _Item,
        *,
        damage_dice_count: int = 0,
        damage_dice_sides: int = 0,
        damage_bonus: int = 0,
    ) -> SunderResult:
        """Resolve a Sunder attempt by *attacker* against *target_item*.

        Args:
            attacker:          The character performing the sunder.
            target_item:       The :class:`Item` being targeted.
            damage_dice_count: Override number of damage dice (0 → unarmed 1d3).
            damage_dice_sides: Override damage die size (0 → unarmed 1d3).
            damage_bonus:      Extra flat damage on top of STR modifier.

        Returns:
            A :class:`SunderResult` describing the outcome.
        """
        # Item AC = 10 + enhancement bonus of the item
        enhancement = int(target_item.metadata.get("enhancement_bonus", 0))
        item_ac = 10 + enhancement

        # Attack bonus uses attacker's melee_attack
        attack_bonus = attacker.melee_attack
        roll = roll_d20(modifier=attack_bonus)
        raw_d20 = roll.raw

        # Natural 1 always misses; natural 20 always hits
        if raw_d20 == 1:
            hit = False
        elif raw_d20 == 20:
            hit = True
        else:
            hit = roll.total >= item_ac

        if not hit:
            return SunderResult(
                hit=False,
                roll=roll,
                attack_bonus=attack_bonus,
                target_item_ac=item_ac,
                damage_dealt=0,
                item_broken=False,
            )

        # Damage roll
        d_count = damage_dice_count if damage_dice_count > 0 else 1
        d_sides = damage_dice_sides if damage_dice_sides > 0 else 3
        total_modifier = attacker.strength_mod + damage_bonus
        damage_roll = roll_dice(d_count, d_sides, modifier=total_modifier)
        raw_damage = max(0, damage_roll.total)

        # Subtract hardness; remainder damages the item
        hardness = int(target_item.metadata.get("hardness", cls._DEFAULT_HARDNESS))
        net_damage = max(0, raw_damage - hardness)

        item_broken = False
        if net_damage > 0 and target_item.durability is not None:
            target_item.use(net_damage)
            item_broken = target_item.is_broken()

        return SunderResult(
            hit=True,
            roll=roll,
            attack_bonus=attack_bonus,
            target_item_ac=item_ac,
            damage_dealt=net_damage,
            item_broken=item_broken,
        )
