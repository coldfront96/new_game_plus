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

from dataclasses import dataclass
from typing import Optional

from src.rules_engine.character_35e import Character35e
from src.rules_engine.dice import RollResult, roll_d20, roll_dice


# ---------------------------------------------------------------------------
# CombatResult
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class CombatResult:
    """Outcome of a single attack action.

    Attributes:
        hit:           ``True`` if the attack met or exceeded the target AC.
        roll:          The d20 :class:`RollResult` (includes raw die value).
        attack_bonus:  Total attack modifier applied to the d20 roll.
        target_ac:     Defender's Armour Class used for the comparison.
        damage_roll:   Damage :class:`RollResult` (``None`` on a miss).
        total_damage:  Final damage dealt (0 on a miss, ≥ 1 on a hit).
        critical:      ``True`` if the attack was a natural 20 critical hit.
    """

    hit: bool
    roll: RollResult
    attack_bonus: int
    target_ac: int
    damage_roll: Optional[RollResult]
    total_damage: int
    critical: bool


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

    # Natural 20 is always a hit and a potential critical.
    _NATURAL_CRIT: int = 20
    # Natural 1 is always a miss.
    _NATURAL_FUMBLE: int = 1

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
    ) -> CombatResult:
        """Resolve a single melee (or ranged) attack.

        Steps (per the 3.5e SRD):
        1. Roll d20 + attack bonus.
        2. Compare against defender's AC.
        3. On a hit, roll damage.
        4. Natural 20 → automatic hit + double damage (simplified crit).
        5. Natural 1 → automatic miss regardless of bonuses.

        Args:
            attacker:          The attacking :class:`Character35e`.
            defender:          The defending :class:`Character35e`.
            use_ranged:        If ``True`` use DEX-based ranged attack bonus
                               instead of STR-based melee.
            damage_dice_count: Override number of damage dice (0 → unarmed).
            damage_dice_sides: Override damage die size (0 → unarmed).
            damage_bonus:      Extra flat damage added on top of STR modifier.

        Returns:
            A :class:`CombatResult` describing the outcome.
        """
        # --- Attack bonus ---------------------------------------------------
        if use_ranged:
            attack_bonus = attacker.ranged_attack
        else:
            attack_bonus = attacker.melee_attack

        # --- Attack roll (d20) ----------------------------------------------
        roll = roll_d20(modifier=attack_bonus)
        raw_d20 = roll.raw  # the actual die face (1–20)

        target_ac = defender.armor_class
        critical = raw_d20 == cls._NATURAL_CRIT

        # --- Hit determination ----------------------------------------------
        if raw_d20 == cls._NATURAL_FUMBLE:
            hit = False
        elif critical:
            hit = True
        else:
            hit = roll.total >= target_ac

        # --- Damage ----------------------------------------------------------
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

        # Determine damage dice
        d_count = damage_dice_count if damage_dice_count > 0 else cls._UNARMED_DICE_COUNT
        d_sides = damage_dice_sides if damage_dice_sides > 0 else cls._UNARMED_DICE_SIDES

        # STR modifier applies to melee damage; ranged gets no STR bonus
        str_mod = attacker.strength_mod if not use_ranged else 0
        total_modifier = str_mod + damage_bonus

        damage_roll = roll_dice(d_count, d_sides, modifier=total_modifier)

        # Minimum 1 damage on a hit (3.5e SRD rule)
        total_damage = max(1, damage_roll.total)

        # Critical hit doubles damage (simplified — ignores crit multiplier
        # variations by weapon type for now).
        if critical:
            total_damage *= 2

        return CombatResult(
            hit=True,
            roll=roll,
            attack_bonus=attack_bonus,
            target_ac=target_ac,
            damage_roll=damage_roll,
            total_damage=total_damage,
            critical=critical,
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
