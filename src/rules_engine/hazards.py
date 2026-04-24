"""
src/rules_engine/hazards.py
---------------------------
D&D 3.5e DMG Environmental Hazards and Afflictions engine.

Implements:
- Falling damage (DMG p.302): 1d6 per 10 ft, capped at 20d6, with optional
  Jump/Tumble skill checks to mitigate.
- Heat and Cold dangers (DMG p.302-303): nonlethal damage per exposure period
  with Fortitude saves.
- Starvation and thirst (DMG p.304): nonlethal damage accumulation after
  subsistence limits are exceeded.
- Poisons (DMG p.297-298): Initial Fort save → initial effect → 1-minute
  secondary Fort save → secondary effect.
- Diseases (DMG p.292-293): Infection Fort save → incubation → daily Fort
  save → effect.

Usage::

    from src.rules_engine.hazards import (
        calculate_falling_damage,
        HeatDanger, ColdDanger, StarvationTracker,
        Poison, Disease, POISON_REGISTRY, DISEASE_REGISTRY,
        AfflictionResult,
    )

    # Falling 40 ft with no mitigation
    result = calculate_falling_damage(distance_ft=40)
    print(result.damage)   # 1–24 HP

    # Apply black adder venom
    poison = POISON_REGISTRY["black_adder_venom"]
    result = poison.apply(fort_save_roll=8)
    print(result.phase, result.effect)
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _roll_dice(count: int, sides: int) -> int:
    """Roll *count* d-*sides* and return the sum."""
    return sum(random.randint(1, sides) for _ in range(count))


def _d20() -> int:
    return random.randint(1, 20)


# ---------------------------------------------------------------------------
# Falling Damage  (DMG p.302)
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class FallResult:
    """Result of a falling-damage calculation.

    Attributes:
        distance_ft:        Actual distance fallen in feet.
        dice_rolled:        Number of d6s rolled (1 per 10 ft, max 20).
        raw_roll:           Sum of the d6s before any mitigation.
        mitigation:         HP of damage avoided by Jump/Tumble check.
        damage:             Final damage dealt (raw_roll - mitigation, min 0).
        skill_check_used:   Name of the mitigating skill, if any.
    """

    distance_ft: int
    dice_rolled: int
    raw_roll: int
    mitigation: int
    damage: int
    skill_check_used: Optional[str]


def calculate_falling_damage(
    distance_ft: int,
    jump_check: Optional[int] = None,
    tumble_check: Optional[int] = None,
) -> FallResult:
    """Calculate falling damage per 3.5e DMG p.302.

    A creature takes 1d6 points of damage per 10 feet fallen, to a maximum
    of 20d6.

    **Jump check mitigation** (DC 15): A successful Jump check (made as a
    free action before landing) lets the character treat the fall as 10 ft
    shorter for damage purposes (minimum 0 ft).

    **Tumble check mitigation** (DC 15): A successful Tumble check at the
    moment of landing lets the character treat the fall as 10 ft shorter
    for damage purposes (stacks with Jump).

    Args:
        distance_ft:   Total distance of the fall in feet.
        jump_check:    Result of a Jump skill check, if attempted.
                       Pass ``None`` to skip.
        tumble_check:  Result of a Tumble skill check, if attempted.
                       Pass ``None`` to skip.

    Returns:
        A :class:`FallResult` with full details of the roll and mitigation.
    """
    if distance_ft <= 0:
        return FallResult(
            distance_ft=distance_ft,
            dice_rolled=0,
            raw_roll=0,
            mitigation=0,
            damage=0,
            skill_check_used=None,
        )

    # Determine mitigation from skill checks (each reduces effective fall by 10 ft)
    mitigation_ft = 0
    skills_used: List[str] = []
    _SKILL_DC = 15

    if jump_check is not None and jump_check >= _SKILL_DC:
        mitigation_ft += 10
        skills_used.append("Jump")
    if tumble_check is not None and tumble_check >= _SKILL_DC:
        mitigation_ft += 10
        skills_used.append("Tumble")

    effective_distance = max(0, distance_ft - mitigation_ft)

    # 1d6 per 10 ft, cap at 20d6
    dice_count = min(20, max(1, effective_distance // 10)) if effective_distance >= 10 else 0

    raw_roll = _roll_dice(dice_count, 6) if dice_count > 0 else 0

    # Mitigation in HP terms = difference between uncapped and capped rolls
    # (simplified as the HP saved by the reduced dice count)
    original_dice = min(20, max(1, distance_ft // 10)) if distance_ft >= 10 else 0
    # We report numeric HP mitigation as the expected-value difference to give
    # callers a meaningful number; the roll itself already reflects the
    # reduced distance.
    hp_mitigation = max(0, (original_dice - dice_count) * 3)  # 3 = avg d6/2 rounded

    return FallResult(
        distance_ft=distance_ft,
        dice_rolled=dice_count,
        raw_roll=raw_roll,
        mitigation=hp_mitigation,
        damage=raw_roll,
        skill_check_used=", ".join(skills_used) if skills_used else None,
    )


# ---------------------------------------------------------------------------
# Heat Danger  (DMG p.303-304)
# ---------------------------------------------------------------------------

class HeatLevel(Enum):
    """Environmental heat categories from the 3.5e DMG."""
    WARM = auto()        # 90–110°F: Fort DC 15 per hour, 1d4 nonlethal
    SEVERE = auto()      # 110–140°F: Fort DC 15 per 10 minutes, 1d4 nonlethal
    EXTREME = auto()     # 140°F+  : Fort DC 15 per minute, 1d4 nonlethal + 1 lethal


@dataclass(slots=True)
class HeatExposureResult:
    """Outcome of a single heat exposure check.

    Attributes:
        level:              The heat level category.
        fort_dc:            The required Fortitude save DC.
        fort_roll:          Total of the Fortitude save roll.
        save_succeeded:     Whether the character passed.
        nonlethal_damage:   Nonlethal HP damage dealt (0 on success).
        lethal_damage:      Lethal HP damage dealt (only for EXTREME).
    """

    level: HeatLevel
    fort_dc: int
    fort_roll: int
    save_succeeded: bool
    nonlethal_damage: int
    lethal_damage: int


@dataclass(slots=True)
class HeatDanger:
    """Heat danger tracker per 3.5e DMG p.303-304.

    Tracks cumulative nonlethal damage from heat exposure and handles the
    escalating DC per failed save.

    Attributes:
        level:                The heat level category.
        constitution_mod:     The character's CON modifier for Fort saves.
        cumulative_nonlethal: Running total of nonlethal damage accumulated.
    """

    level: HeatLevel
    constitution_mod: int = 0
    cumulative_nonlethal: int = 0

    # DC escalates by +1 for each failed save (DMG)
    _failed_saves: int = field(default=0)

    @property
    def current_dc(self) -> int:
        """Fort DC for the current check (base 15 + 1 per prior failure)."""
        return 15 + self._failed_saves

    def expose(self, fort_bonus: int) -> HeatExposureResult:
        """Perform one heat exposure check.

        Args:
            fort_bonus: The character's total Fortitude save bonus
                        (base save + CON mod + any magical bonuses).

        Returns:
            A :class:`HeatExposureResult` describing the outcome.
        """
        dc = self.current_dc
        roll = _d20() + fort_bonus
        succeeded = roll >= dc

        nonlethal = 0
        lethal = 0
        if not succeeded:
            self._failed_saves += 1
            nonlethal = _roll_dice(1, 4)
            self.cumulative_nonlethal += nonlethal
            if self.level is HeatLevel.EXTREME:
                lethal = 1

        return HeatExposureResult(
            level=self.level,
            fort_dc=dc,
            fort_roll=roll,
            save_succeeded=succeeded,
            nonlethal_damage=nonlethal,
            lethal_damage=lethal,
        )


# ---------------------------------------------------------------------------
# Cold Danger  (DMG p.302-303)
# ---------------------------------------------------------------------------

class ColdLevel(Enum):
    """Environmental cold categories from the 3.5e DMG."""
    COLD = auto()       # 40–0°F:  Fort DC 15 per hour, 1d6 nonlethal
    SEVERE = auto()     # 0°F and below: Fort DC 15 per 10 min, 1d6 nonlethal
    EXTREME = auto()    # –20°F and below: Fort DC 15 per minute, 1d6 nonlethal + 1 lethal


@dataclass(slots=True)
class ColdExposureResult:
    """Outcome of a single cold exposure check."""

    level: ColdLevel
    fort_dc: int
    fort_roll: int
    save_succeeded: bool
    nonlethal_damage: int
    lethal_damage: int


@dataclass(slots=True)
class ColdDanger:
    """Cold danger tracker per 3.5e DMG p.302-303.

    Attributes:
        level:                The cold level category.
        cumulative_nonlethal: Running total of nonlethal damage accumulated.
    """

    level: ColdLevel
    cumulative_nonlethal: int = 0
    _failed_saves: int = field(default=0)

    @property
    def current_dc(self) -> int:
        """Fort DC for the current check (base 15 + 1 per prior failure)."""
        return 15 + self._failed_saves

    def expose(self, fort_bonus: int) -> ColdExposureResult:
        """Perform one cold exposure check.

        Args:
            fort_bonus: The character's total Fortitude save bonus.

        Returns:
            A :class:`ColdExposureResult` describing the outcome.
        """
        dc = self.current_dc
        roll = _d20() + fort_bonus
        succeeded = roll >= dc

        nonlethal = 0
        lethal = 0
        if not succeeded:
            self._failed_saves += 1
            nonlethal = _roll_dice(1, 6)
            self.cumulative_nonlethal += nonlethal
            if self.level is ColdLevel.EXTREME:
                lethal = 1

        return ColdExposureResult(
            level=self.level,
            fort_dc=dc,
            fort_roll=roll,
            save_succeeded=succeeded,
            nonlethal_damage=nonlethal,
            lethal_damage=lethal,
        )


# ---------------------------------------------------------------------------
# Starvation & Thirst  (DMG p.304)
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class StarvationTracker:
    """Track starvation and dehydration per 3.5e DMG p.304.

    A character can go without water for 1 day + CON modifier hours (minimum
    1 hour). After that, the character must make a DC 10 Fortitude save each
    hour or take 1d6 points of nonlethal damage.

    A character can go without food for 3 days without penalty. After that,
    the character must make a DC 10 Fortitude save each day or take 1d6
    points of nonlethal damage.

    The DC increases by +1 for each previous failed save.

    Attributes:
        constitution_mod:       CON modifier of the character.
        days_without_food:      Running count of days without food.
        hours_without_water:    Running count of hours without water.
        cumulative_nonlethal:   Total nonlethal damage from starvation/thirst.
    """

    constitution_mod: int = 0
    days_without_food: int = 0
    hours_without_water: int = 0
    cumulative_nonlethal: int = 0
    _food_failed_saves: int = field(default=0)
    _water_failed_saves: int = field(default=0)

    @property
    def water_grace_hours(self) -> int:
        """Hours before dehydration checks begin (1 day + CON mod, min 1 hour)."""
        return max(1, 24 + self.constitution_mod)

    @property
    def food_grace_days(self) -> int:
        """Days before starvation checks begin (always 3 per SRD)."""
        return 3

    def advance_hour(self, fort_bonus: int) -> Optional[int]:
        """Advance time by one hour for dehydration tracking.

        If the character has exceeded the water grace period, a Fort save is
        required.

        Args:
            fort_bonus: Character's total Fortitude save bonus.

        Returns:
            Nonlethal damage dealt this hour, or ``None`` if no check needed.
        """
        self.hours_without_water += 1
        if self.hours_without_water <= self.water_grace_hours:
            return None

        dc = 10 + self._water_failed_saves
        roll = _d20() + fort_bonus
        if roll < dc:
            self._water_failed_saves += 1
            dmg = _roll_dice(1, 6)
            self.cumulative_nonlethal += dmg
            return dmg
        return 0

    def advance_day(self, fort_bonus: int) -> Optional[int]:
        """Advance time by one day for starvation tracking.

        If the character has exceeded the food grace period, a Fort save is
        required.

        Args:
            fort_bonus: Character's total Fortitude save bonus.

        Returns:
            Nonlethal damage dealt this day, or ``None`` if no check needed.
        """
        self.days_without_food += 1
        if self.days_without_food <= self.food_grace_days:
            return None

        dc = 10 + self._food_failed_saves
        roll = _d20() + fort_bonus
        if roll < dc:
            self._food_failed_saves += 1
            dmg = _roll_dice(1, 6)
            self.cumulative_nonlethal += dmg
            return dmg
        return 0

    def eat(self) -> None:
        """Reset starvation counter after the character eats."""
        self.days_without_food = 0
        self._food_failed_saves = 0

    def drink(self) -> None:
        """Reset dehydration counter after the character drinks."""
        self.hours_without_water = 0
        self._water_failed_saves = 0


# ---------------------------------------------------------------------------
# Affliction framework (Poisons & Diseases)
# ---------------------------------------------------------------------------

class AfflictionPhase(Enum):
    """Phase of an ongoing affliction."""
    INITIAL = auto()    # Immediately after exposure
    SECONDARY = auto()  # After the secondary delay period
    RESOLVED = auto()   # No longer active


@dataclass(slots=True)
class AfflictionResult:
    """Outcome of an affliction save attempt.

    Attributes:
        phase:          Which phase was just resolved.
        fort_dc:        The required Fortitude save DC.
        fort_roll:      Total of the Fortitude save roll (d20 + modifier).
        save_succeeded: Whether the save was made.
        effect:         Human-readable description of the effect applied.
        ability_damage: Mapping of ability name → damage dealt (e.g. ``{"STR": 2}``).
    """

    phase: AfflictionPhase
    fort_dc: int
    fort_roll: int
    save_succeeded: bool
    effect: str
    ability_damage: Dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Poison  (DMG p.297-298)
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Poison:
    """A 3.5e SRD poison definition.

    The full poison sequence per DMG p.297:
    1. Creature is exposed (injury, ingestion, inhaled, contact).
    2. **Initial Fort save** vs. DC — on failure apply *initial_effect*.
    3. Wait *secondary_delay_minutes* (typically 1 minute).
    4. **Secondary Fort save** vs. DC — on failure apply *secondary_effect*.

    Attributes:
        name:                    Poison name.
        dc:                      Fortitude save DC.
        initial_effect:          Description of the initial effect.
        secondary_effect:        Description of the secondary effect.
        initial_ability_dmg:     Ability damage on initial save failure
                                 (e.g. ``{"CON": 1}``).
        secondary_ability_dmg:   Ability damage on secondary save failure.
        secondary_delay_minutes: Minutes between initial and secondary saves.
        delivery:                Delivery method (e.g. ``"Injury"``).
        price_gp:                Market price in gold pieces (SRD reference).
    """

    name: str
    dc: int
    initial_effect: str
    secondary_effect: str
    initial_ability_dmg: Dict[str, int] = field(default_factory=dict)
    secondary_ability_dmg: Dict[str, int] = field(default_factory=dict)
    secondary_delay_minutes: int = 1
    delivery: str = "Injury"
    price_gp: int = 0

    def apply_initial(self, fort_bonus: int) -> AfflictionResult:
        """Roll the initial Fortitude save and apply effect on failure.

        Args:
            fort_bonus: Character's total Fortitude save bonus.

        Returns:
            An :class:`AfflictionResult` for the initial phase.
        """
        roll = _d20() + fort_bonus
        succeeded = roll >= self.dc
        return AfflictionResult(
            phase=AfflictionPhase.INITIAL,
            fort_dc=self.dc,
            fort_roll=roll,
            save_succeeded=succeeded,
            effect="No effect" if succeeded else self.initial_effect,
            ability_damage={} if succeeded else dict(self.initial_ability_dmg),
        )

    def apply_secondary(self, fort_bonus: int) -> AfflictionResult:
        """Roll the secondary Fortitude save and apply effect on failure.

        Args:
            fort_bonus: Character's total Fortitude save bonus.

        Returns:
            An :class:`AfflictionResult` for the secondary phase.
        """
        roll = _d20() + fort_bonus
        succeeded = roll >= self.dc
        return AfflictionResult(
            phase=AfflictionPhase.SECONDARY,
            fort_dc=self.dc,
            fort_roll=roll,
            save_succeeded=succeeded,
            effect="No effect" if succeeded else self.secondary_effect,
            ability_damage={} if succeeded else dict(self.secondary_ability_dmg),
        )


# ---------------------------------------------------------------------------
# Disease  (DMG p.292-293)
# ---------------------------------------------------------------------------

class DiseaseType(Enum):
    """Infection vector for a disease."""
    CONTACT = auto()
    INHALED = auto()
    INJURY = auto()


@dataclass(slots=True)
class Disease:
    """A 3.5e SRD disease definition.

    The full disease sequence per DMG p.292:
    1. Creature is exposed (contact, inhaled, or injury).
    2. **Infection Fort save** vs. DC — on failure the disease takes hold.
    3. Wait *incubation_days* (disease-specific).
    4. **Daily Fort save** vs. DC — on failure apply *effect* for that day.
       Two consecutive successful saves cure the disease.

    Attributes:
        name:             Disease name.
        dc:               Fortitude save DC.
        incubation_days:  Days until first daily save is required.
        effect:           Description of the daily effect on failure.
        ability_dmg:      Ability damage per failed daily save.
        disease_type:     Contact, inhaled, or injury vector.
    """

    name: str
    dc: int
    incubation_days: int
    effect: str
    ability_dmg: Dict[str, int] = field(default_factory=dict)
    disease_type: DiseaseType = DiseaseType.INJURY

    def roll_infection(self, fort_bonus: int) -> AfflictionResult:
        """Roll the initial infection save.

        Args:
            fort_bonus: Character's total Fortitude save bonus.

        Returns:
            :class:`AfflictionResult` — if ``save_succeeded`` is ``True``,
            the disease does not take hold.
        """
        roll = _d20() + fort_bonus
        succeeded = roll >= self.dc
        return AfflictionResult(
            phase=AfflictionPhase.INITIAL,
            fort_dc=self.dc,
            fort_roll=roll,
            save_succeeded=succeeded,
            effect="No infection" if succeeded else f"Infected with {self.name}",
            ability_damage={},
        )

    def roll_daily_save(self, fort_bonus: int) -> AfflictionResult:
        """Roll a daily disease progression save.

        Args:
            fort_bonus: Character's total Fortitude save bonus.

        Returns:
            :class:`AfflictionResult` for this day's progression check.
        """
        roll = _d20() + fort_bonus
        succeeded = roll >= self.dc
        return AfflictionResult(
            phase=AfflictionPhase.SECONDARY,
            fort_dc=self.dc,
            fort_roll=roll,
            save_succeeded=succeeded,
            effect="Resisted today" if succeeded else self.effect,
            ability_damage={} if succeeded else dict(self.ability_dmg),
        )


# ---------------------------------------------------------------------------
# Poison Registry  (SRD iconic poisons — DMG p.297-298)
# ---------------------------------------------------------------------------

POISON_REGISTRY: Dict[str, Poison] = {
    "black_adder_venom": Poison(
        name="Black Adder Venom",
        dc=11,
        delivery="Injury",
        initial_effect="1d6 CON",
        secondary_effect="1d6 CON",
        initial_ability_dmg={"CON": 1},     # simplified: roll delegated to caller
        secondary_ability_dmg={"CON": 1},
        secondary_delay_minutes=1,
        price_gp=120,
    ),
    "large_scorpion_venom": Poison(
        name="Large Scorpion Venom",
        dc=18,
        delivery="Injury",
        initial_effect="1d6 STR",
        secondary_effect="1d6 STR",
        initial_ability_dmg={"STR": 1},
        secondary_ability_dmg={"STR": 1},
        secondary_delay_minutes=1,
        price_gp=200,
    ),
    "wyvern_poison": Poison(
        name="Wyvern Poison",
        dc=17,
        delivery="Injury",
        initial_effect="2d6 CON",
        secondary_effect="2d6 CON",
        initial_ability_dmg={"CON": 2},
        secondary_ability_dmg={"CON": 2},
        secondary_delay_minutes=1,
        price_gp=3000,
    ),
    "sassone_leaf_residue": Poison(
        name="Sassone Leaf Residue",
        dc=16,
        delivery="Contact",
        initial_effect="2d12 HP",
        secondary_effect="1d6 CON",
        initial_ability_dmg={},
        secondary_ability_dmg={"CON": 1},
        secondary_delay_minutes=1,
        price_gp=300,
    ),
    "oil_of_taggit": Poison(
        name="Oil of Taggit",
        dc=15,
        delivery="Ingested",
        initial_effect="Unconscious",
        secondary_effect="2d6 WIS",
        initial_ability_dmg={},
        secondary_ability_dmg={"WIS": 2},
        secondary_delay_minutes=1,
        price_gp=90,
    ),
    "arsenic": Poison(
        name="Arsenic",
        dc=13,
        delivery="Ingested",
        initial_effect="1 CON",
        secondary_effect="1d8 CON",
        initial_ability_dmg={"CON": 1},
        secondary_ability_dmg={"CON": 1},
        secondary_delay_minutes=1,
        price_gp=120,
    ),
}


# ---------------------------------------------------------------------------
# Disease Registry  (SRD iconic diseases — DMG p.292-293)
# ---------------------------------------------------------------------------

DISEASE_REGISTRY: Dict[str, Disease] = {
    "mummy_rot": Disease(
        name="Mummy Rot",
        dc=20,
        incubation_days=1,
        effect="1d6 CON and CHA",
        ability_dmg={"CON": 1, "CHA": 1},
        disease_type=DiseaseType.CONTACT,
    ),
    "filth_fever": Disease(
        name="Filth Fever",
        dc=12,
        incubation_days=1,
        effect="1d3 DEX and CON",
        ability_dmg={"DEX": 1, "CON": 1},
        disease_type=DiseaseType.INJURY,
    ),
    "cackle_fever": Disease(
        name="Cackle Fever",
        dc=16,
        incubation_days=1,
        effect="1d6 WIS",
        ability_dmg={"WIS": 1},
        disease_type=DiseaseType.INHALED,
    ),
    "red_ache": Disease(
        name="Red Ache",
        dc=15,
        incubation_days=3,
        effect="1d6 STR",
        ability_dmg={"STR": 1},
        disease_type=DiseaseType.INJURY,
    ),
    "blinding_sickness": Disease(
        name="Blinding Sickness",
        dc=16,
        incubation_days=1,
        effect="1d4 STR; cumulative 4+ STR damage causes blindness",
        ability_dmg={"STR": 1},
        disease_type=DiseaseType.INGESTED if False else DiseaseType.INJURY,
    ),
    "shakes": Disease(
        name="Shakes",
        dc=13,
        incubation_days=1,
        effect="1d8 DEX",
        ability_dmg={"DEX": 1},
        disease_type=DiseaseType.CONTACT,
    ),
}
