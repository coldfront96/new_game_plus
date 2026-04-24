"""
src/rules_engine/objects.py
----------------------------
D&D 3.5e DMG Chapter 3 — Object Hardness, HP, and Break DCs.

Covers:
- T-001: MaterialType enum and ObjectMaterial dataclass (DMG Table 3-3)
- T-012: calculate_break_dc — base DC + thickness + size modifiers
- T-013: ObjectState / DamageType enums and apply_damage_to_object
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict


# ---------------------------------------------------------------------------
# T-001: Size categories (used for break DC modifiers)
# ---------------------------------------------------------------------------

class SizeCategory(Enum):
    """Creature/object size categories used in break DC calculation."""

    FINE = "fine"
    DIMINUTIVE = "diminutive"
    TINY = "tiny"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    HUGE = "huge"
    GARGANTUAN = "gargantuan"
    COLOSSAL = "colossal"


_SIZE_DC_MOD: Dict[SizeCategory, int] = {
    SizeCategory.FINE: -16,
    SizeCategory.DIMINUTIVE: -12,
    SizeCategory.TINY: -8,
    SizeCategory.SMALL: -4,
    SizeCategory.MEDIUM: 0,
    SizeCategory.LARGE: +4,
    SizeCategory.HUGE: +8,
    SizeCategory.GARGANTUAN: +12,
    SizeCategory.COLOSSAL: +16,
}


# ---------------------------------------------------------------------------
# T-001: MaterialType enum and ObjectMaterial dataclass
# ---------------------------------------------------------------------------

class MaterialType(Enum):
    """Object material types from DMG Table 3-3."""

    WOOD = "wood"
    STONE = "stone"
    IRON = "iron"
    STEEL = "steel"
    MITHRAL = "mithral"
    ADAMANTINE = "adamantine"
    CRYSTAL = "crystal"
    ROPE = "rope"
    GLASS = "glass"


@dataclass(slots=True)
class ObjectMaterial:
    """Material statistics from DMG Table 3-3.

    Attributes:
        material_type: The :class:`MaterialType` variant.
        hardness:      Damage reduction applied to each hit on the object.
        hp_per_inch:   Hit points per inch of thickness.
        break_dc:      Base Strength check DC to break the object.
    """

    material_type: MaterialType
    hardness: int
    hp_per_inch: int
    break_dc: int


MATERIAL_STATS: Dict[MaterialType, ObjectMaterial] = {
    MaterialType.WOOD:       ObjectMaterial(MaterialType.WOOD,       hardness=5,  hp_per_inch=10, break_dc=15),
    MaterialType.STONE:      ObjectMaterial(MaterialType.STONE,      hardness=8,  hp_per_inch=15, break_dc=28),
    MaterialType.IRON:       ObjectMaterial(MaterialType.IRON,       hardness=10, hp_per_inch=30, break_dc=28),
    MaterialType.STEEL:      ObjectMaterial(MaterialType.STEEL,      hardness=10, hp_per_inch=30, break_dc=30),
    MaterialType.MITHRAL:    ObjectMaterial(MaterialType.MITHRAL,    hardness=15, hp_per_inch=30, break_dc=28),
    MaterialType.ADAMANTINE: ObjectMaterial(MaterialType.ADAMANTINE, hardness=20, hp_per_inch=40, break_dc=35),
    MaterialType.CRYSTAL:    ObjectMaterial(MaterialType.CRYSTAL,    hardness=1,  hp_per_inch=4,  break_dc=12),
    MaterialType.ROPE:       ObjectMaterial(MaterialType.ROPE,       hardness=0,  hp_per_inch=2,  break_dc=23),
    MaterialType.GLASS:      ObjectMaterial(MaterialType.GLASS,      hardness=1,  hp_per_inch=1,  break_dc=10),
}


# ---------------------------------------------------------------------------
# T-012: calculate_break_dc
# ---------------------------------------------------------------------------

def calculate_break_dc(
    material: MaterialType,
    thickness_inches: int,
    size: SizeCategory,
) -> int:
    """Return the Strength check DC required to break an object.

    Args:
        material:         Material of the object.
        thickness_inches: Thickness in inches (minimum 1).
        size:             Size category of the object.

    Returns:
        Integer DC for the break attempt.
    """
    stats = MATERIAL_STATS[material]
    thickness_bonus = 5 * max(0, thickness_inches - 1)
    size_mod = _SIZE_DC_MOD[size]
    return stats.break_dc + thickness_bonus + size_mod


# ---------------------------------------------------------------------------
# T-013: ObjectState, DamageType, apply_damage_to_object
# ---------------------------------------------------------------------------

class ObjectState(Enum):
    """Current condition of a damaged object."""

    INTACT = "intact"
    DAMAGED = "damaged"
    BROKEN = "broken"
    DESTROYED = "destroyed"


class DamageType(Enum):
    """Energy / physical damage types that can affect objects."""

    BLUDGEONING = "bludgeoning"
    PIERCING = "piercing"
    SLASHING = "slashing"
    FIRE = "fire"
    COLD = "cold"
    ACID = "acid"
    ELECTRICITY = "electricity"
    SONIC = "sonic"
    FORCE = "force"


def _effective_damage(material: MaterialType, raw_damage: int, energy_type: DamageType) -> int:
    """Return damage after applying energy immunities/resistances.

    DMG rules summary:
    - Fire:        immune for Stone/Iron/Steel/Mithral/Adamantine; full for Wood/Rope/Crystal/Glass
    - Cold:        immune for most; half for Crystal/Glass
    - Electricity: immune for Iron/Steel/Mithral/Adamantine
    - Acid:        full for Stone/Crystal; half for Iron/Steel; full otherwise
    - Sonic:       full for Crystal/Glass; half for others
    - Physical:    full (hardness still applies afterward)
    """
    if energy_type == DamageType.FIRE:
        if material in {
            MaterialType.STONE, MaterialType.IRON, MaterialType.STEEL,
            MaterialType.MITHRAL, MaterialType.ADAMANTINE,
        }:
            return 0
        return raw_damage  # Wood, Rope, Crystal, Glass → full

    if energy_type == DamageType.COLD:
        if material in {MaterialType.CRYSTAL, MaterialType.GLASS}:
            return raw_damage // 2
        return 0  # all others immune

    if energy_type == DamageType.ELECTRICITY:
        if material in {
            MaterialType.IRON, MaterialType.STEEL,
            MaterialType.MITHRAL, MaterialType.ADAMANTINE,
        }:
            return 0
        return raw_damage

    if energy_type == DamageType.ACID:
        if material in {MaterialType.STONE, MaterialType.CRYSTAL}:
            return raw_damage
        if material in {MaterialType.IRON, MaterialType.STEEL}:
            return raw_damage // 2
        return raw_damage

    if energy_type == DamageType.SONIC:
        if material in {MaterialType.CRYSTAL, MaterialType.GLASS}:
            return raw_damage
        return raw_damage // 2

    # Physical (bludgeoning / piercing / slashing) and force → full damage
    return raw_damage


def apply_damage_to_object(
    material: MaterialType,
    hp: int,
    damage: int,
    energy_type: DamageType,
) -> tuple[int, ObjectState]:
    """Apply a single hit to an object and return its new HP and condition.

    Hardness reduces effective damage after energy modifiers are applied.
    The returned :class:`ObjectState` is derived by comparing new HP against
    the *original* HP passed in as ``hp`` (treated as the current maximum for
    the purpose of this call).

    Args:
        material:    Object's material.
        hp:          Current (and reference maximum) hit points.
        damage:      Raw damage roll before any reductions.
        energy_type: Type of damage being dealt.

    Returns:
        ``(new_hp, state)`` tuple.
    """
    stats = MATERIAL_STATS[material]
    after_energy = _effective_damage(material, damage, energy_type)
    effective = max(0, after_energy - stats.hardness)
    new_hp = max(0, hp - effective)

    if effective == 0:
        state = ObjectState.INTACT
    elif new_hp <= 0:
        state = ObjectState.DESTROYED
    elif new_hp <= hp // 2:
        state = ObjectState.BROKEN
    else:
        state = ObjectState.DAMAGED

    return new_hp, state
