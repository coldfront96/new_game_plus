"""
src/rules_engine/planar.py
--------------------------
D&D 3.5e Planar Physics subsystem.

Implements planar traits, gravity/time/magic resolvers, plane registries,
and the planar travel + encounter generator (DMG Chapter 5).

Implemented tiers:
    E-014 — Planar Trait Enum Set
    E-015 — Plane Base Schema
    E-030 — Gravity Trait Effect Resolver
    E-031 — Time Trait Effect Resolver
    E-032 — Magic Trait Effect Resolver
    E-033 — Elemental & Energy Dominance Resolver
    E-044 — Inner Plane Registry
    E-045 — Outer Plane Registry
    E-046 — Transitive Plane Registry
    E-055 — Planar Transition Engine
    E-061 — Planar Spell Modifier Engine
    E-062 — Planar Encounter Adapter
    E-067 — Planar Travel + Encounter Generator
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


# ---------------------------------------------------------------------------
# E-014 — Planar Trait Enums
# ---------------------------------------------------------------------------

class GravityTrait(Enum):
    Normal = auto()
    Heavy = auto()
    Light = auto()
    NoGravity = auto()               # "None" in spec — NoGravity avoids keyword clash
    Objective_Directional = auto()
    Subjective_Directional = auto()


class TimeTrait(Enum):
    Normal = auto()
    Flowing = auto()    # fixed ratio to prime material
    Erratic = auto()    # random ratio per visit
    Timeless = auto()   # suspended aging/hunger/spells while in plane


class AlignmentTrait(Enum):
    """Mildly/Strongly × axis, plus TrueNeutral."""
    Neutral = auto()
    MildlyLawful = auto()
    MildlyNeutral = auto()
    MildlyChaotic = auto()
    MildlyGood = auto()
    MildlyEvil = auto()
    StronglyLawful = auto()
    StronglyNeutral = auto()
    StronglyChaotic = auto()
    StronglyGood = auto()
    StronglyEvil = auto()


class MagicTrait(Enum):
    Normal = auto()
    Enhanced = auto()   # +1 CL for matching school/descriptor
    Impeded = auto()    # Spellcraft DC 20+spell_level or fails
    Wild = auto()       # wild magic surges
    Dead = auto()       # all spells fail
    Limited = auto()    # only certain schools function


class ElementalDominance(Enum):
    NoElement = auto()  # "None" in spec
    Air = auto()
    Earth = auto()
    Fire = auto()
    Water = auto()


class EnergyDominance(Enum):
    NoEnergy = auto()   # "None" in spec
    Positive = auto()
    Negative = auto()


class PlaneCategory(Enum):
    Material = auto()
    Inner = auto()
    Outer = auto()
    Transitive = auto()
    Demiplane = auto()


# ---------------------------------------------------------------------------
# E-015 — Plane Base Schema
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class PlaneBase:
    name: str
    category: PlaneCategory
    gravity: GravityTrait
    time: TimeTrait
    realm_size: str       # "Finite", "Infinite", "SelfContained"
    morphic: str          # "Alterable", "Highly", "Magically", "Divinely", "Sentient", "Static"
    elemental: ElementalDominance
    energy: EnergyDominance
    alignment: AlignmentTrait
    magic: MagicTrait
    connecting_planes: tuple[str, ...]   # names of planes reachable from this one
    enhanced_schools: tuple[str, ...]    # spell schools/descriptors enhanced here
    impeded_schools: tuple[str, ...]     # spell schools/descriptors impeded here


# ---------------------------------------------------------------------------
# E-030 — Gravity Trait Effect Resolver
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ActionContext:
    """Context for computing gravity effects on an action."""
    character_weight_lb: float
    base_strength: int
    base_dexterity: int
    base_speed_ft: int
    has_balance_skill: bool = False
    balance_skill_ranks: int = 0
    chosen_gravity_direction: Optional[str] = None  # for Subjective_Directional


@dataclass(slots=True)
class GravityEffect:
    effective_weight_lb: float
    attack_modifier: int
    str_check_modifier: int
    dex_check_modifier: int
    jump_distance_multiplier: float
    falling_damage_per_10ft_dice: int  # Normal=1d6, Light=1d4, None/Heavy varies
    requires_balance_check: bool
    balance_dc: int
    movement_possible: bool


def apply_gravity_trait(trait: GravityTrait, ctx: ActionContext) -> GravityEffect:
    """DMG Ch 5 gravity rules."""
    if trait == GravityTrait.Normal:
        return GravityEffect(
            effective_weight_lb=ctx.character_weight_lb,
            attack_modifier=0,
            str_check_modifier=0,
            dex_check_modifier=0,
            jump_distance_multiplier=1.0,
            falling_damage_per_10ft_dice=6,
            requires_balance_check=False,
            balance_dc=0,
            movement_possible=True,
        )
    if trait == GravityTrait.Heavy:
        return GravityEffect(
            effective_weight_lb=ctx.character_weight_lb * 1.5,
            attack_modifier=-1,
            str_check_modifier=-1,
            dex_check_modifier=-1,
            jump_distance_multiplier=1.0,
            falling_damage_per_10ft_dice=6,
            requires_balance_check=False,
            balance_dc=0,
            movement_possible=True,
        )
    if trait == GravityTrait.Light:
        return GravityEffect(
            effective_weight_lb=ctx.character_weight_lb * 0.5,
            attack_modifier=1,
            str_check_modifier=1,
            dex_check_modifier=1,
            jump_distance_multiplier=2.0,
            falling_damage_per_10ft_dice=4,  # 1d4 per 20 ft
            requires_balance_check=False,
            balance_dc=0,
            movement_possible=True,
        )
    if trait == GravityTrait.NoGravity:
        return GravityEffect(
            effective_weight_lb=0.0,
            attack_modifier=0,
            str_check_modifier=0,
            dex_check_modifier=0,
            jump_distance_multiplier=1.0,
            falling_damage_per_10ft_dice=0,
            requires_balance_check=True,
            balance_dc=16,
            movement_possible=True,
        )
    if trait == GravityTrait.Objective_Directional:
        return GravityEffect(
            effective_weight_lb=ctx.character_weight_lb,
            attack_modifier=0,
            str_check_modifier=0,
            dex_check_modifier=0,
            jump_distance_multiplier=1.0,
            falling_damage_per_10ft_dice=6,
            requires_balance_check=False,
            balance_dc=0,
            movement_possible=True,
        )
    # Subjective_Directional
    needs_check = ctx.chosen_gravity_direction is None
    return GravityEffect(
        effective_weight_lb=ctx.character_weight_lb,
        attack_modifier=0,
        str_check_modifier=0,
        dex_check_modifier=0,
        jump_distance_multiplier=1.0,
        falling_damage_per_10ft_dice=6,
        requires_balance_check=needs_check,
        balance_dc=16 if needs_check else 0,
        movement_possible=True,
    )


# ---------------------------------------------------------------------------
# E-031 — Time Trait Effect Resolver
# ---------------------------------------------------------------------------

_TIMELESS_LIFESPAN_HOURS = 80 * 365 * 24  # 80-year human lifespan in hours


@dataclass(slots=True)
class TimeDilationResult:
    prime_material_hours_elapsed: float
    subjective_hours: float
    aging_applied: bool
    spell_durations_suspended: bool
    hunger_suspended: bool
    catastrophic_aging_fort_dc: Optional[int]


def apply_time_trait(
    trait: TimeTrait,
    hours_in_plane: float,
    flow_ratio: float = 1.0,
    rng=None,
) -> TimeDilationResult:
    """DMG Ch 5 time rules."""
    if trait == TimeTrait.Normal:
        return TimeDilationResult(
            prime_material_hours_elapsed=hours_in_plane,
            subjective_hours=hours_in_plane,
            aging_applied=True,
            spell_durations_suspended=False,
            hunger_suspended=False,
            catastrophic_aging_fort_dc=None,
        )
    if trait == TimeTrait.Flowing:
        prime = hours_in_plane * flow_ratio
        return TimeDilationResult(
            prime_material_hours_elapsed=prime,
            subjective_hours=hours_in_plane,
            aging_applied=True,
            spell_durations_suspended=False,
            hunger_suspended=False,
            catastrophic_aging_fort_dc=None,
        )
    if trait == TimeTrait.Erratic:
        if rng is not None:
            ratio = rng.randint(1, 100) / 100.0
        else:
            ratio = 0.5
        prime = hours_in_plane * ratio
        return TimeDilationResult(
            prime_material_hours_elapsed=prime,
            subjective_hours=hours_in_plane,
            aging_applied=True,
            spell_durations_suspended=False,
            hunger_suspended=False,
            catastrophic_aging_fort_dc=None,
        )
    # Timeless
    aging_dc = 25 if hours_in_plane > _TIMELESS_LIFESPAN_HOURS else None
    return TimeDilationResult(
        prime_material_hours_elapsed=0.0,
        subjective_hours=hours_in_plane,
        aging_applied=False,
        spell_durations_suspended=True,
        hunger_suspended=True,
        catastrophic_aging_fort_dc=aging_dc,
    )


# ---------------------------------------------------------------------------
# E-032 — Magic Trait Effect Resolver
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class MagicTraitResult:
    caster_level_modifier: int
    save_dc_modifier: int
    spell_fails: bool
    wild_surge_table_id: Optional[str]
    impeded_check_dc: Optional[int]


def apply_magic_trait(
    trait: MagicTrait,
    school: str,
    descriptors: tuple[str, ...],
    spell_level: int = 0,
    enhanced_schools: tuple[str, ...] = (),
    impeded_schools: tuple[str, ...] = (),
) -> MagicTraitResult:
    """DMG Ch 5 magic rules."""
    if trait == MagicTrait.Normal:
        return MagicTraitResult(
            caster_level_modifier=0,
            save_dc_modifier=0,
            spell_fails=False,
            wild_surge_table_id=None,
            impeded_check_dc=None,
        )
    if trait == MagicTrait.Enhanced:
        matches = school in enhanced_schools or any(d in enhanced_schools for d in descriptors)
        cl_mod = 1 if matches else 0
        return MagicTraitResult(
            caster_level_modifier=cl_mod,
            save_dc_modifier=0,
            spell_fails=False,
            wild_surge_table_id=None,
            impeded_check_dc=None,
        )
    if trait == MagicTrait.Impeded:
        is_impeded = school in impeded_schools or any(d in impeded_schools for d in descriptors)
        dc = (20 + spell_level) if is_impeded else None
        return MagicTraitResult(
            caster_level_modifier=0,
            save_dc_modifier=0,
            spell_fails=False,
            wild_surge_table_id=None,
            impeded_check_dc=dc,
        )
    if trait == MagicTrait.Wild:
        return MagicTraitResult(
            caster_level_modifier=0,
            save_dc_modifier=0,
            spell_fails=False,
            wild_surge_table_id="wild_magic_table",
            impeded_check_dc=None,
        )
    if trait == MagicTrait.Dead:
        return MagicTraitResult(
            caster_level_modifier=0,
            save_dc_modifier=0,
            spell_fails=True,
            wild_surge_table_id=None,
            impeded_check_dc=None,
        )
    # Limited
    allowed = school in enhanced_schools or any(d in enhanced_schools for d in descriptors)
    return MagicTraitResult(
        caster_level_modifier=0,
        save_dc_modifier=0,
        spell_fails=not allowed,
        wild_surge_table_id=None,
        impeded_check_dc=None,
    )


# ---------------------------------------------------------------------------
# E-033 — Elemental & Energy Dominance Resolvers
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ElementalEffect:
    damage_per_round: int
    damage_type: str
    requires_protection: bool
    protection_spell: str
    encased_movement_penalty: bool


@dataclass(slots=True)
class EnergyEffect:
    fast_healing: int
    negative_levels_per_round: int
    fort_dc: Optional[int]
    on_fail: str
    is_minor: bool


def apply_elemental_dominance(
    elem: ElementalDominance,
    has_protection: bool = False,
) -> ElementalEffect:
    """DMG Ch 5 elemental dominance rules."""
    if elem == ElementalDominance.NoElement:
        return ElementalEffect(
            damage_per_round=0,
            damage_type="none",
            requires_protection=False,
            protection_spell="",
            encased_movement_penalty=False,
        )
    if elem == ElementalDominance.Fire:
        dmg = 0 if has_protection else 30  # 3d10 average ~16, use 30 for max; store dice count
        return ElementalEffect(
            damage_per_round=0 if has_protection else 30,
            damage_type="fire",
            requires_protection=True,
            protection_spell="Protection from Energy (Fire)",
            encased_movement_penalty=False,
        )
    if elem == ElementalDominance.Water:
        return ElementalEffect(
            damage_per_round=0 if has_protection else 1,  # drowning rules apply
            damage_type="water",
            requires_protection=True,
            protection_spell="Water Breathing",
            encased_movement_penalty=False,
        )
    if elem == ElementalDominance.Air:
        return ElementalEffect(
            damage_per_round=0 if has_protection else 6,  # 1d6 falling
            damage_type="air",
            requires_protection=True,
            protection_spell="Fly",
            encased_movement_penalty=False,
        )
    # Earth
    return ElementalEffect(
        damage_per_round=0,
        damage_type="earth",
        requires_protection=True,
        protection_spell="Passwall",
        encased_movement_penalty=not has_protection,
    )


def apply_energy_dominance(
    energy: EnergyDominance,
    is_minor: bool = True,
) -> EnergyEffect:
    """DMG Ch 5 energy dominance rules."""
    if energy == EnergyDominance.NoEnergy:
        return EnergyEffect(
            fast_healing=0,
            negative_levels_per_round=0,
            fort_dc=None,
            on_fail="",
            is_minor=is_minor,
        )
    if energy == EnergyDominance.Positive:
        if is_minor:
            return EnergyEffect(
                fast_healing=2,
                negative_levels_per_round=0,
                fort_dc=None,
                on_fail="",
                is_minor=True,
            )
        return EnergyEffect(
            fast_healing=0,
            negative_levels_per_round=0,
            fort_dc=20,
            on_fail="explode",
            is_minor=False,
        )
    # Negative
    if is_minor:
        return EnergyEffect(
            fast_healing=0,
            negative_levels_per_round=1,  # 1d6 negative levels — store 1 as base
            fort_dc=25,
            on_fail="",
            is_minor=True,
        )
    return EnergyEffect(
        fast_healing=0,
        negative_levels_per_round=0,
        fort_dc=25,
        on_fail="turned_to_dust",
        is_minor=False,
    )


# ---------------------------------------------------------------------------
# E-044 — Inner Plane Registry
# ---------------------------------------------------------------------------

INNER_PLANE_REGISTRY: dict[str, PlaneBase] = {
    "Elemental Air": PlaneBase(
        name="Elemental Air",
        category=PlaneCategory.Inner,
        gravity=GravityTrait.Light,
        time=TimeTrait.Normal,
        realm_size="Infinite",
        morphic="Highly",
        elemental=ElementalDominance.Air,
        energy=EnergyDominance.NoEnergy,
        alignment=AlignmentTrait.Neutral,
        magic=MagicTrait.Normal,
        connecting_planes=("Elemental Fire", "Elemental Earth", "Elemental Water", "Prime Material", "Astral Plane"),
        enhanced_schools=("Air",),
        impeded_schools=("Earth",),
    ),
    "Elemental Earth": PlaneBase(
        name="Elemental Earth",
        category=PlaneCategory.Inner,
        gravity=GravityTrait.Normal,
        time=TimeTrait.Normal,
        realm_size="Infinite",
        morphic="Highly",
        elemental=ElementalDominance.Earth,
        energy=EnergyDominance.NoEnergy,
        alignment=AlignmentTrait.Neutral,
        magic=MagicTrait.Normal,
        connecting_planes=("Elemental Air", "Elemental Fire", "Elemental Water", "Prime Material", "Astral Plane"),
        enhanced_schools=("Earth",),
        impeded_schools=("Air",),
    ),
    "Elemental Fire": PlaneBase(
        name="Elemental Fire",
        category=PlaneCategory.Inner,
        gravity=GravityTrait.Normal,
        time=TimeTrait.Normal,
        realm_size="Infinite",
        morphic="Highly",
        elemental=ElementalDominance.Fire,
        energy=EnergyDominance.NoEnergy,
        alignment=AlignmentTrait.MildlyNeutral,
        magic=MagicTrait.Normal,
        connecting_planes=("Elemental Air", "Elemental Earth", "Elemental Water", "Prime Material", "Astral Plane"),
        enhanced_schools=("Fire",),
        impeded_schools=("Cold", "Water"),
    ),
    "Elemental Water": PlaneBase(
        name="Elemental Water",
        category=PlaneCategory.Inner,
        gravity=GravityTrait.NoGravity,
        time=TimeTrait.Normal,
        realm_size="Infinite",
        morphic="Highly",
        elemental=ElementalDominance.Water,
        energy=EnergyDominance.NoEnergy,
        alignment=AlignmentTrait.Neutral,
        magic=MagicTrait.Normal,
        connecting_planes=("Elemental Air", "Elemental Earth", "Elemental Fire", "Prime Material", "Astral Plane"),
        enhanced_schools=("Water",),
        impeded_schools=("Fire",),
    ),
    "Positive Energy Plane": PlaneBase(
        name="Positive Energy Plane",
        category=PlaneCategory.Inner,
        gravity=GravityTrait.Light,
        time=TimeTrait.Normal,
        realm_size="Infinite",
        morphic="Highly",
        elemental=ElementalDominance.NoElement,
        energy=EnergyDominance.Positive,
        alignment=AlignmentTrait.Neutral,
        magic=MagicTrait.Normal,
        connecting_planes=("Prime Material", "Astral Plane"),
        enhanced_schools=(),
        impeded_schools=(),
    ),
    "Negative Energy Plane": PlaneBase(
        name="Negative Energy Plane",
        category=PlaneCategory.Inner,
        gravity=GravityTrait.Heavy,
        time=TimeTrait.Normal,
        realm_size="Infinite",
        morphic="Highly",
        elemental=ElementalDominance.NoElement,
        energy=EnergyDominance.Negative,
        alignment=AlignmentTrait.Neutral,
        magic=MagicTrait.Normal,
        connecting_planes=("Prime Material", "Astral Plane"),
        enhanced_schools=(),
        impeded_schools=(),
    ),
}


# ---------------------------------------------------------------------------
# E-045 — Outer Plane Registry
# ---------------------------------------------------------------------------

OUTER_PLANE_REGISTRY: dict[str, PlaneBase] = {
    "Seven Mounting Heavens of Celestia": PlaneBase(
        name="Seven Mounting Heavens of Celestia",
        category=PlaneCategory.Outer,
        gravity=GravityTrait.Normal,
        time=TimeTrait.Normal,
        realm_size="Infinite",
        morphic="Divinely",
        elemental=ElementalDominance.NoElement,
        energy=EnergyDominance.NoEnergy,
        alignment=AlignmentTrait.StronglyGood,
        magic=MagicTrait.Normal,
        connecting_planes=("Astral Plane", "Twin Paradises of Bytopia", "Peaceable Kingdoms of Arcadia"),
        enhanced_schools=("Good", "Law"),
        impeded_schools=("Evil", "Chaos"),
    ),
    "Twin Paradises of Bytopia": PlaneBase(
        name="Twin Paradises of Bytopia",
        category=PlaneCategory.Outer,
        gravity=GravityTrait.Normal,
        time=TimeTrait.Normal,
        realm_size="Infinite",
        morphic="Divinely",
        elemental=ElementalDominance.NoElement,
        energy=EnergyDominance.NoEnergy,
        alignment=AlignmentTrait.StronglyGood,
        magic=MagicTrait.Normal,
        connecting_planes=("Astral Plane", "Seven Mounting Heavens of Celestia", "Blessed Fields of Elysium"),
        enhanced_schools=("Good", "Law"),
        impeded_schools=("Evil", "Chaos"),
    ),
    "Blessed Fields of Elysium": PlaneBase(
        name="Blessed Fields of Elysium",
        category=PlaneCategory.Outer,
        gravity=GravityTrait.Normal,
        time=TimeTrait.Normal,
        realm_size="Infinite",
        morphic="Divinely",
        elemental=ElementalDominance.NoElement,
        energy=EnergyDominance.NoEnergy,
        alignment=AlignmentTrait.StronglyGood,
        magic=MagicTrait.Normal,
        connecting_planes=("Astral Plane", "Twin Paradises of Bytopia", "Wilderness of the Beastlands"),
        enhanced_schools=("Good",),
        impeded_schools=("Evil",),
    ),
    "Wilderness of the Beastlands": PlaneBase(
        name="Wilderness of the Beastlands",
        category=PlaneCategory.Outer,
        gravity=GravityTrait.Normal,
        time=TimeTrait.Normal,
        realm_size="Infinite",
        morphic="Divinely",
        elemental=ElementalDominance.NoElement,
        energy=EnergyDominance.NoEnergy,
        alignment=AlignmentTrait.StronglyGood,
        magic=MagicTrait.Normal,
        connecting_planes=("Astral Plane", "Blessed Fields of Elysium", "Olympian Glades of Arborea"),
        enhanced_schools=("Good",),
        impeded_schools=("Evil",),
    ),
    "Olympian Glades of Arborea": PlaneBase(
        name="Olympian Glades of Arborea",
        category=PlaneCategory.Outer,
        gravity=GravityTrait.Normal,
        time=TimeTrait.Normal,
        realm_size="Infinite",
        morphic="Divinely",
        elemental=ElementalDominance.NoElement,
        energy=EnergyDominance.NoEnergy,
        alignment=AlignmentTrait.MildlyChaotic,
        magic=MagicTrait.Normal,
        connecting_planes=("Astral Plane", "Wilderness of the Beastlands", "Heroic Domains of Ysgard"),
        enhanced_schools=("Chaos", "Good"),
        impeded_schools=("Law",),
    ),
    "Heroic Domains of Ysgard": PlaneBase(
        name="Heroic Domains of Ysgard",
        category=PlaneCategory.Outer,
        gravity=GravityTrait.Normal,
        time=TimeTrait.Normal,
        realm_size="Infinite",
        morphic="Divinely",
        elemental=ElementalDominance.NoElement,
        energy=EnergyDominance.NoEnergy,
        alignment=AlignmentTrait.MildlyGood,
        magic=MagicTrait.Normal,
        connecting_planes=("Astral Plane", "Olympian Glades of Arborea", "Ever-Changing Chaos of Limbo"),
        enhanced_schools=("Good", "Chaos"),
        impeded_schools=(),
    ),
    "Ever-Changing Chaos of Limbo": PlaneBase(
        name="Ever-Changing Chaos of Limbo",
        category=PlaneCategory.Outer,
        gravity=GravityTrait.Subjective_Directional,
        time=TimeTrait.Normal,
        realm_size="Infinite",
        morphic="Highly",
        elemental=ElementalDominance.NoElement,
        energy=EnergyDominance.NoEnergy,
        alignment=AlignmentTrait.StronglyChaotic,
        magic=MagicTrait.Normal,
        connecting_planes=("Astral Plane", "Heroic Domains of Ysgard", "Windswept Depths of Pandemonium"),
        enhanced_schools=("Chaos",),
        impeded_schools=("Law",),
    ),
    "Windswept Depths of Pandemonium": PlaneBase(
        name="Windswept Depths of Pandemonium",
        category=PlaneCategory.Outer,
        gravity=GravityTrait.NoGravity,
        time=TimeTrait.Normal,
        realm_size="Infinite",
        morphic="Alterable",
        elemental=ElementalDominance.NoElement,
        energy=EnergyDominance.NoEnergy,
        alignment=AlignmentTrait.StronglyChaotic,
        magic=MagicTrait.Normal,
        connecting_planes=("Astral Plane", "Ever-Changing Chaos of Limbo", "Infinite Layers of the Abyss"),
        enhanced_schools=("Chaos",),
        impeded_schools=("Law",),
    ),
    "Infinite Layers of the Abyss": PlaneBase(
        name="Infinite Layers of the Abyss",
        category=PlaneCategory.Outer,
        gravity=GravityTrait.Subjective_Directional,
        time=TimeTrait.Normal,
        realm_size="Infinite",
        morphic="Divinely",
        elemental=ElementalDominance.NoElement,
        energy=EnergyDominance.NoEnergy,
        alignment=AlignmentTrait.StronglyChaotic,
        magic=MagicTrait.Normal,
        connecting_planes=("Astral Plane", "Windswept Depths of Pandemonium", "Tarterian Depths of Carceri"),
        enhanced_schools=("Evil", "Chaos"),
        impeded_schools=("Good", "Law"),
    ),
    "Tarterian Depths of Carceri": PlaneBase(
        name="Tarterian Depths of Carceri",
        category=PlaneCategory.Outer,
        gravity=GravityTrait.Normal,
        time=TimeTrait.Normal,
        realm_size="Infinite",
        morphic="Alterable",
        elemental=ElementalDominance.NoElement,
        energy=EnergyDominance.NoEnergy,
        alignment=AlignmentTrait.MildlyChaotic,
        magic=MagicTrait.Normal,
        connecting_planes=("Astral Plane", "Infinite Layers of the Abyss", "Gray Waste of Hades"),
        enhanced_schools=("Evil",),
        impeded_schools=("Good",),
    ),
    "Gray Waste of Hades": PlaneBase(
        name="Gray Waste of Hades",
        category=PlaneCategory.Outer,
        gravity=GravityTrait.Normal,
        time=TimeTrait.Normal,
        realm_size="Infinite",
        morphic="Alterable",
        elemental=ElementalDominance.NoElement,
        energy=EnergyDominance.NoEnergy,
        alignment=AlignmentTrait.MildlyEvil,
        magic=MagicTrait.Normal,
        connecting_planes=("Astral Plane", "Tarterian Depths of Carceri", "Bleak Eternity of Gehenna"),
        enhanced_schools=("Evil",),
        impeded_schools=("Good",),
    ),
    "Bleak Eternity of Gehenna": PlaneBase(
        name="Bleak Eternity of Gehenna",
        category=PlaneCategory.Outer,
        gravity=GravityTrait.Objective_Directional,
        time=TimeTrait.Normal,
        realm_size="Infinite",
        morphic="Alterable",
        elemental=ElementalDominance.NoElement,
        energy=EnergyDominance.NoEnergy,
        alignment=AlignmentTrait.MildlyEvil,
        magic=MagicTrait.Normal,
        connecting_planes=("Astral Plane", "Gray Waste of Hades", "Nine Hells of Baator"),
        enhanced_schools=("Evil",),
        impeded_schools=("Good",),
    ),
    "Nine Hells of Baator": PlaneBase(
        name="Nine Hells of Baator",
        category=PlaneCategory.Outer,
        gravity=GravityTrait.Normal,
        time=TimeTrait.Normal,
        realm_size="Infinite",
        morphic="Divinely",
        elemental=ElementalDominance.NoElement,
        energy=EnergyDominance.NoEnergy,
        alignment=AlignmentTrait.StronglyEvil,
        magic=MagicTrait.Normal,
        connecting_planes=("Astral Plane", "Bleak Eternity of Gehenna", "Infernal Battlefield of Acheron"),
        enhanced_schools=("Evil", "Law"),
        impeded_schools=("Good", "Chaos"),
    ),
    "Infernal Battlefield of Acheron": PlaneBase(
        name="Infernal Battlefield of Acheron",
        category=PlaneCategory.Outer,
        gravity=GravityTrait.Objective_Directional,
        time=TimeTrait.Normal,
        realm_size="Infinite",
        morphic="Alterable",
        elemental=ElementalDominance.NoElement,
        energy=EnergyDominance.NoEnergy,
        alignment=AlignmentTrait.StronglyLawful,
        magic=MagicTrait.Normal,
        connecting_planes=("Astral Plane", "Nine Hells of Baator", "Clockwork Nirvana of Mechanus"),
        enhanced_schools=("Law",),
        impeded_schools=("Chaos",),
    ),
    "Clockwork Nirvana of Mechanus": PlaneBase(
        name="Clockwork Nirvana of Mechanus",
        category=PlaneCategory.Outer,
        gravity=GravityTrait.Objective_Directional,
        time=TimeTrait.Normal,
        realm_size="Infinite",
        morphic="Divinely",
        elemental=ElementalDominance.NoElement,
        energy=EnergyDominance.NoEnergy,
        alignment=AlignmentTrait.StronglyLawful,
        magic=MagicTrait.Normal,
        connecting_planes=("Astral Plane", "Infernal Battlefield of Acheron", "Peaceable Kingdoms of Arcadia"),
        enhanced_schools=("Law",),
        impeded_schools=("Chaos",),
    ),
    "Peaceable Kingdoms of Arcadia": PlaneBase(
        name="Peaceable Kingdoms of Arcadia",
        category=PlaneCategory.Outer,
        gravity=GravityTrait.Normal,
        time=TimeTrait.Normal,
        realm_size="Infinite",
        morphic="Divinely",
        elemental=ElementalDominance.NoElement,
        energy=EnergyDominance.NoEnergy,
        alignment=AlignmentTrait.StronglyLawful,
        magic=MagicTrait.Normal,
        connecting_planes=("Astral Plane", "Clockwork Nirvana of Mechanus", "Seven Mounting Heavens of Celestia"),
        enhanced_schools=("Good", "Law"),
        impeded_schools=("Evil", "Chaos"),
    ),
    "Concordant Domain of the Outlands": PlaneBase(
        name="Concordant Domain of the Outlands",
        category=PlaneCategory.Outer,
        gravity=GravityTrait.Normal,
        time=TimeTrait.Normal,
        realm_size="Infinite",
        morphic="Alterable",
        elemental=ElementalDominance.NoElement,
        energy=EnergyDominance.NoEnergy,
        alignment=AlignmentTrait.Neutral,
        magic=MagicTrait.Normal,
        connecting_planes=("Astral Plane", "All Outer Planes"),
        enhanced_schools=(),
        impeded_schools=(),
    ),
}


# ---------------------------------------------------------------------------
# E-046 — Transitive Plane Registry
# ---------------------------------------------------------------------------

TRANSITIVE_PLANE_REGISTRY: dict[str, PlaneBase] = {
    "Astral Plane": PlaneBase(
        name="Astral Plane",
        category=PlaneCategory.Transitive,
        gravity=GravityTrait.Subjective_Directional,
        time=TimeTrait.Timeless,
        realm_size="Infinite",
        morphic="Alterable",
        elemental=ElementalDominance.NoElement,
        energy=EnergyDominance.NoEnergy,
        alignment=AlignmentTrait.Neutral,
        magic=MagicTrait.Enhanced,
        connecting_planes=("Prime Material", "All Outer Planes"),
        enhanced_schools=("Divination",),
        impeded_schools=(),
    ),
    "Ethereal Plane": PlaneBase(
        name="Ethereal Plane",
        category=PlaneCategory.Transitive,
        gravity=GravityTrait.NoGravity,
        time=TimeTrait.Normal,
        realm_size="Infinite",
        morphic="Alterable",
        elemental=ElementalDominance.NoElement,
        energy=EnergyDominance.NoEnergy,
        alignment=AlignmentTrait.Neutral,
        magic=MagicTrait.Normal,
        connecting_planes=("Prime Material", "Inner Planes"),
        enhanced_schools=(),
        impeded_schools=(),
    ),
    "Plane of Shadow": PlaneBase(
        name="Plane of Shadow",
        category=PlaneCategory.Transitive,
        gravity=GravityTrait.Normal,
        time=TimeTrait.Normal,
        realm_size="Infinite",
        morphic="Magically",
        elemental=ElementalDominance.NoElement,
        energy=EnergyDominance.NoEnergy,
        alignment=AlignmentTrait.Neutral,
        magic=MagicTrait.Enhanced,
        connecting_planes=("Prime Material", "Ethereal Plane"),
        enhanced_schools=("Shadow",),
        impeded_schools=("Light",),
    ),
    "Plane of Mirrors": PlaneBase(
        name="Plane of Mirrors",
        category=PlaneCategory.Demiplane,
        gravity=GravityTrait.Normal,
        time=TimeTrait.Normal,
        realm_size="Finite",
        morphic="Sentient",
        elemental=ElementalDominance.NoElement,
        energy=EnergyDominance.NoEnergy,
        alignment=AlignmentTrait.Neutral,
        magic=MagicTrait.Normal,
        connecting_planes=("Prime Material",),
        enhanced_schools=("Illusion",),
        impeded_schools=(),
    ),
}

# Unified lookup across all registries
ALL_PLANES: dict[str, PlaneBase] = {
    **INNER_PLANE_REGISTRY,
    **OUTER_PLANE_REGISTRY,
    **TRANSITIVE_PLANE_REGISTRY,
}


# ---------------------------------------------------------------------------
# E-055 — Planar Transition Engine
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class PlanarTransitionResult:
    success: bool
    reason: str
    new_plane: Optional[PlaneBase]
    gravity_effect: Optional[GravityEffect]
    time_dilation: Optional[TimeDilationResult]
    magic_suppressed_schools: list[str]
    encumbrance_recomputed: bool


def transition_plane(
    traveler_id: str,
    from_plane: PlaneBase,
    to_plane: PlaneBase,
    has_plane_shift: bool = False,
    traveler_weight_lb: float = 150.0,
    traveler_strength: int = 10,
    traveler_dexterity: int = 10,
    traveler_speed_ft: int = 30,
    hours_spent: float = 0.0,
    rng=None,
) -> PlanarTransitionResult:
    """Verify reachability, apply gravity/time/magic effects."""
    reachable = (
        to_plane.name in from_plane.connecting_planes
        or "All Outer Planes" in from_plane.connecting_planes
        or has_plane_shift
    )
    if not reachable:
        return PlanarTransitionResult(
            success=False,
            reason=f"{to_plane.name} is not reachable from {from_plane.name} without Plane Shift.",
            new_plane=None,
            gravity_effect=None,
            time_dilation=None,
            magic_suppressed_schools=[],
            encumbrance_recomputed=False,
        )

    ctx = ActionContext(
        character_weight_lb=traveler_weight_lb,
        base_strength=traveler_strength,
        base_dexterity=traveler_dexterity,
        base_speed_ft=traveler_speed_ft,
    )
    gravity_effect = apply_gravity_trait(to_plane.gravity, ctx)
    time_dilation = apply_time_trait(to_plane.time, hours_spent, rng=rng)
    suppressed: list[str] = list(to_plane.impeded_schools)
    encumbrance_recomputed = to_plane.gravity != GravityTrait.Normal

    return PlanarTransitionResult(
        success=True,
        reason="Transition successful.",
        new_plane=to_plane,
        gravity_effect=gravity_effect,
        time_dilation=time_dilation,
        magic_suppressed_schools=suppressed,
        encumbrance_recomputed=encumbrance_recomputed,
    )


# ---------------------------------------------------------------------------
# E-061 — Planar Spell Modifier Engine
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class SpellResolutionResult:
    spell_name: str
    final_caster_level: int
    final_save_dc: int
    spell_fails: bool
    wild_surge: bool
    notes: list[str]


def resolve_spell_in_plane(
    spell_name: str,
    spell_school: str,
    spell_descriptors: tuple[str, ...],
    spell_level: int,
    base_caster_level: int,
    base_save_dc: int,
    current_plane: PlaneBase,
    rng=None,
) -> SpellResolutionResult:
    """Apply magic trait modifiers to a spell cast in the given plane."""
    notes: list[str] = []
    magic_result = apply_magic_trait(
        current_plane.magic,
        spell_school,
        spell_descriptors,
        spell_level,
        current_plane.enhanced_schools,
        current_plane.impeded_schools,
    )

    if magic_result.spell_fails:
        return SpellResolutionResult(
            spell_name=spell_name,
            final_caster_level=base_caster_level,
            final_save_dc=base_save_dc,
            spell_fails=True,
            wild_surge=False,
            notes=[f"Spell fails: {current_plane.magic.name} trait on {current_plane.name}."],
        )

    wild_surge = magic_result.wild_surge_table_id is not None
    cl = base_caster_level + magic_result.caster_level_modifier
    dc = base_save_dc + magic_result.save_dc_modifier

    if magic_result.caster_level_modifier != 0:
        notes.append(f"CL {'+' if magic_result.caster_level_modifier > 0 else ''}{magic_result.caster_level_modifier} from {current_plane.magic.name} trait.")
    if magic_result.impeded_check_dc is not None:
        notes.append(f"Spellcraft DC {magic_result.impeded_check_dc} required to cast {spell_name}.")
    if wild_surge:
        notes.append(f"Wild magic surge: roll on {magic_result.wild_surge_table_id}.")

    return SpellResolutionResult(
        spell_name=spell_name,
        final_caster_level=cl,
        final_save_dc=dc,
        spell_fails=False,
        wild_surge=wild_surge,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# E-062 — Planar Encounter Adapter
# ---------------------------------------------------------------------------

_FIRE_SUBSTITUTIONS: dict[str, str] = {
    "Hill Giant": "Salamander",
    "Mountain Giant": "Azer",
    "Giant": "Magmin",
    "Hills creature": "Salamander",
    "Mountains creature": "Azer",
}

_PLANE_HAZARDS: dict[ElementalDominance, str] = {
    ElementalDominance.Fire: "3d10 fire damage per round (Fire Dominant)",
    ElementalDominance.Water: "Drowning hazard (Water Dominant)",
    ElementalDominance.Air: "1d6 falling damage without flight (Air Dominant)",
    ElementalDominance.Earth: "Encased movement penalty (Earth Dominant)",
    ElementalDominance.NoElement: "",
}

_ENERGY_HAZARDS: dict[EnergyDominance, str] = {
    EnergyDominance.Positive: "Fast healing 2/round; Fort DC 20 or explode (major)",
    EnergyDominance.Negative: "Fort DC 25 or negative levels/round",
    EnergyDominance.NoEnergy: "",
}


@dataclass(slots=True)
class EncounterBlueprint:
    creatures: list[str]
    environment_hazards: list[str]
    plane_name: str
    modified: bool


def adapt_encounter_for_plane(
    creatures: list[str],
    plane: PlaneBase,
    rng=None,
) -> EncounterBlueprint:
    """Remap creatures and add environmental hazards for the given plane."""
    modified = False
    remapped: list[str] = []

    for creature in creatures:
        if plane.elemental == ElementalDominance.Fire:
            replacement = None
            for key, sub in _FIRE_SUBSTITUTIONS.items():
                if key.lower() in creature.lower():
                    replacement = sub
                    break
            if replacement:
                remapped.append(replacement)
                modified = True
            else:
                remapped.append(creature)
        else:
            remapped.append(creature)

    hazards: list[str] = []
    elem_hazard = _PLANE_HAZARDS.get(plane.elemental, "")
    if elem_hazard:
        hazards.append(elem_hazard)
    energy_hazard = _ENERGY_HAZARDS.get(plane.energy, "")
    if energy_hazard:
        hazards.append(energy_hazard)
    if plane.gravity == GravityTrait.NoGravity:
        hazards.append("Balance DC 16 required for movement (No Gravity)")
    if plane.gravity == GravityTrait.Subjective_Directional:
        hazards.append("Balance DC 16 first move to set gravity direction (Subjective Directional)")

    return EncounterBlueprint(
        creatures=remapped,
        environment_hazards=hazards,
        plane_name=plane.name,
        modified=modified or bool(hazards),
    )


# ---------------------------------------------------------------------------
# E-067 — Planar Travel + Encounter Generator
# ---------------------------------------------------------------------------

_PRIME_MATERIAL = PlaneBase(
    name="Prime Material",
    category=PlaneCategory.Material,
    gravity=GravityTrait.Normal,
    time=TimeTrait.Normal,
    realm_size="Infinite",
    morphic="Alterable",
    elemental=ElementalDominance.NoElement,
    energy=EnergyDominance.NoEnergy,
    alignment=AlignmentTrait.Neutral,
    magic=MagicTrait.Normal,
    connecting_planes=tuple(ALL_PLANES.keys()),
    enhanced_schools=(),
    impeded_schools=(),
)


@dataclass
class ExcursionReport:
    planes_visited: list[str]
    total_prime_material_hours: float
    total_subjective_hours: float
    encounters: list[EncounterBlueprint]
    spell_results: list[SpellResolutionResult]
    catastrophic_aging_checks: list[str]
    xp_earned: int
    notes: list[str]


def run_planar_excursion(
    traveler_ids: list[str],
    itinerary: list[str],
    spells_cast: list[dict],
    hours_per_plane: float = 24.0,
    rng=None,
) -> ExcursionReport:
    """Iterate planes in itinerary order, applying all planar systems."""
    planes_visited: list[str] = []
    total_prime_hours = 0.0
    total_subjective_hours = 0.0
    encounters: list[EncounterBlueprint] = []
    spell_results: list[SpellResolutionResult] = []
    catastrophic_checks: list[str] = []
    notes: list[str] = []
    xp = 0

    current_plane = _PRIME_MATERIAL

    for plane_name in itinerary:
        plane = ALL_PLANES.get(plane_name)
        if plane is None:
            notes.append(f"Unknown plane '{plane_name}' — skipped.")
            continue

        transition = transition_plane(
            traveler_id=traveler_ids[0] if traveler_ids else "unknown",
            from_plane=current_plane,
            to_plane=plane,
            has_plane_shift=True,  # assume travelers have means to travel
            traveler_weight_lb=150.0,
            hours_spent=hours_per_plane,
            rng=rng,
        )

        if not transition.success:
            notes.append(f"Transition to {plane_name} failed: {transition.reason}")
            continue

        planes_visited.append(plane_name)
        xp += 50

        time_result = apply_time_trait(plane.time, hours_per_plane, rng=rng)
        total_prime_hours += time_result.prime_material_hours_elapsed
        total_subjective_hours += time_result.subjective_hours

        if time_result.catastrophic_aging_fort_dc is not None:
            for tid in traveler_ids:
                catastrophic_checks.append(tid)

        encounter = adapt_encounter_for_plane(
            creatures=["Giant", "Hill Giant", "Bandit"],
            plane=plane,
            rng=rng,
        )
        encounters.append(encounter)
        xp += 100

        for spell_dict in spells_cast:
            result = resolve_spell_in_plane(
                spell_name=spell_dict.get("name", "Unknown Spell"),
                spell_school=spell_dict.get("school", "Evocation"),
                spell_descriptors=tuple(spell_dict.get("descriptors", [])),
                spell_level=spell_dict.get("level", 1),
                base_caster_level=spell_dict.get("caster_level", 5),
                base_save_dc=spell_dict.get("save_dc", 15),
                current_plane=plane,
                rng=rng,
            )
            spell_results.append(result)

        current_plane = plane

    return ExcursionReport(
        planes_visited=planes_visited,
        total_prime_material_hours=total_prime_hours,
        total_subjective_hours=total_subjective_hours,
        encounters=encounters,
        spell_results=spell_results,
        catastrophic_aging_checks=catastrophic_checks,
        xp_earned=xp,
        notes=notes,
    )
