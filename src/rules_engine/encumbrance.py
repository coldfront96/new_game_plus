"""
src/rules_engine/encumbrance.py
--------------------------------
D&D 3.5e Encumbrance Physics subsystem.

Implements the carrying-capacity and load-penalty rules from PHB Chapter 9
(Carrying Capacity, Table 9-1 and Table 9-2).

Tier 0 — Base schemas & enums (no external dependencies beyond stdlib).

    * :class:`LoadCategory` — Light / Medium / Heavy / Overload
    * :class:`LiftCategory` — LiftOverHead / LiftOffGround / PushOrDrag
    * :class:`CarryingCapacityRow` — per-Strength lookup row
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.rules_engine.character_35e import Character35e, Size


# ---------------------------------------------------------------------------
# Load Category
# ---------------------------------------------------------------------------

class LoadCategory(Enum):
    """Encumbrance load category derived from carried weight vs. capacity.

    PHB Ch 9, Table 9-2.

    * ``Light``    — weight ≤ light_max_lb; no speed/AC/skill penalty.
    * ``Medium``   — light_max < weight ≤ medium_max; max Dex +3, ACP −3,
                     speed penalty (30 ft → 20 ft; 20 ft → 15 ft).
    * ``Heavy``    — medium_max < weight ≤ heavy_max; max Dex +1, ACP −6,
                     speed penalty (30 ft → 20 ft; 20 ft → 15 ft),
                     run ×3 only (not ×4).
    * ``Overload`` — weight > heavy_max; character cannot move voluntarily.
    """

    Light = auto()
    Medium = auto()
    Heavy = auto()
    Overload = auto()


# ---------------------------------------------------------------------------
# Lift Category
# ---------------------------------------------------------------------------

class LiftCategory(Enum):
    """One-time lifting actions distinct from sustained carrying load.

    PHB Ch 9 — "Lifting and Dragging" sidebar.

    * ``LiftOverHead``  — maximum weight the character can hoist overhead
                          equals the heavy-load maximum (= carrying capacity
                          heavy_max_lb).
    * ``LiftOffGround`` — max weight lifted off the ground = 2 × heavy_max.
    * ``PushOrDrag``    — max weight pushed or dragged across floor = 5 × heavy_max.
    """

    LiftOverHead = auto()
    LiftOffGround = auto()
    PushOrDrag = auto()


# ---------------------------------------------------------------------------
# Carrying Capacity Row Schema (E-002)
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class CarryingCapacityRow:
    """One row of PHB Table 9-1 — carrying limits for a single Strength score.

    For Strength values 1–29 the table is looked up explicitly; for STR 30+
    the values are computed by applying a ×4 multiplier per additional +10
    Strength above 29 (documented in the PHB Ch 9 footnote).

    Attributes:
        strength:      The Strength score this row applies to (1–29 explicit;
                       30+ computed).
        light_max_lb:  Maximum load in pounds for a Light load category.
        medium_max_lb: Maximum load in pounds for a Medium load category.
        heavy_max_lb:  Maximum load in pounds for a Heavy load category
                       (also equals the maximum overhead lift weight).
    """

    strength: int
    light_max_lb: float
    medium_max_lb: float
    heavy_max_lb: float


# ---------------------------------------------------------------------------
# E-035 — Carrying Capacity Lookup Table (PHB Table 9-1, STR 1-29)
# ---------------------------------------------------------------------------

CARRYING_CAPACITY_TABLE: dict[int, CarryingCapacityRow] = {
    1:  CarryingCapacityRow(strength=1,  light_max_lb=3.0,   medium_max_lb=6.0,   heavy_max_lb=10.0),
    2:  CarryingCapacityRow(strength=2,  light_max_lb=6.0,   medium_max_lb=13.0,  heavy_max_lb=20.0),
    3:  CarryingCapacityRow(strength=3,  light_max_lb=10.0,  medium_max_lb=20.0,  heavy_max_lb=30.0),
    4:  CarryingCapacityRow(strength=4,  light_max_lb=13.0,  medium_max_lb=26.0,  heavy_max_lb=40.0),
    5:  CarryingCapacityRow(strength=5,  light_max_lb=16.0,  medium_max_lb=33.0,  heavy_max_lb=50.0),
    6:  CarryingCapacityRow(strength=6,  light_max_lb=20.0,  medium_max_lb=40.0,  heavy_max_lb=60.0),
    7:  CarryingCapacityRow(strength=7,  light_max_lb=23.0,  medium_max_lb=46.0,  heavy_max_lb=70.0),
    8:  CarryingCapacityRow(strength=8,  light_max_lb=26.0,  medium_max_lb=53.0,  heavy_max_lb=80.0),
    9:  CarryingCapacityRow(strength=9,  light_max_lb=30.0,  medium_max_lb=60.0,  heavy_max_lb=90.0),
    10: CarryingCapacityRow(strength=10, light_max_lb=33.0,  medium_max_lb=66.0,  heavy_max_lb=100.0),
    11: CarryingCapacityRow(strength=11, light_max_lb=38.0,  medium_max_lb=76.0,  heavy_max_lb=115.0),
    12: CarryingCapacityRow(strength=12, light_max_lb=43.0,  medium_max_lb=86.0,  heavy_max_lb=130.0),
    13: CarryingCapacityRow(strength=13, light_max_lb=50.0,  medium_max_lb=100.0, heavy_max_lb=150.0),
    14: CarryingCapacityRow(strength=14, light_max_lb=58.0,  medium_max_lb=116.0, heavy_max_lb=175.0),
    15: CarryingCapacityRow(strength=15, light_max_lb=66.0,  medium_max_lb=133.0, heavy_max_lb=200.0),
    16: CarryingCapacityRow(strength=16, light_max_lb=76.0,  medium_max_lb=153.0, heavy_max_lb=230.0),
    17: CarryingCapacityRow(strength=17, light_max_lb=86.0,  medium_max_lb=173.0, heavy_max_lb=260.0),
    18: CarryingCapacityRow(strength=18, light_max_lb=100.0, medium_max_lb=200.0, heavy_max_lb=300.0),
    19: CarryingCapacityRow(strength=19, light_max_lb=116.0, medium_max_lb=233.0, heavy_max_lb=350.0),
    20: CarryingCapacityRow(strength=20, light_max_lb=133.0, medium_max_lb=266.0, heavy_max_lb=400.0),
    21: CarryingCapacityRow(strength=21, light_max_lb=153.0, medium_max_lb=306.0, heavy_max_lb=460.0),
    22: CarryingCapacityRow(strength=22, light_max_lb=173.0, medium_max_lb=346.0, heavy_max_lb=520.0),
    23: CarryingCapacityRow(strength=23, light_max_lb=200.0, medium_max_lb=400.0, heavy_max_lb=600.0),
    24: CarryingCapacityRow(strength=24, light_max_lb=233.0, medium_max_lb=466.0, heavy_max_lb=700.0),
    25: CarryingCapacityRow(strength=25, light_max_lb=266.0, medium_max_lb=533.0, heavy_max_lb=800.0),
    26: CarryingCapacityRow(strength=26, light_max_lb=306.0, medium_max_lb=613.0, heavy_max_lb=920.0),
    27: CarryingCapacityRow(strength=27, light_max_lb=346.0, medium_max_lb=693.0, heavy_max_lb=1040.0),
    28: CarryingCapacityRow(strength=28, light_max_lb=400.0, medium_max_lb=800.0, heavy_max_lb=1200.0),
    29: CarryingCapacityRow(strength=29, light_max_lb=466.0, medium_max_lb=933.0, heavy_max_lb=1400.0),
}


# ---------------------------------------------------------------------------
# E-034 — PHB Equipment Weight Registry
# ---------------------------------------------------------------------------

EQUIPMENT_WEIGHT_REGISTRY: dict[str, float] = {
    # ------------------------------------------------------------------
    # PHB Table 7-4 Weapons (Simple — Unarmed)
    # ------------------------------------------------------------------
    "Unarmed Strike": 0.0,
    "Gauntlet": 1.0,
    # Simple — Light Melee
    "Dagger": 1.0,
    "Dagger Punching": 1.0,
    "Spiked Gauntlet": 1.0,
    "Light Mace": 4.0,
    "Sickle": 2.0,
    # Simple — One-Handed Melee
    "Club": 3.0,
    "Heavy Mace": 8.0,
    "Morningstar": 6.0,
    "Shortspear": 3.0,
    # Simple — Two-Handed Melee
    "Longspear": 9.0,
    "Quarterstaff": 4.0,
    "Spear": 6.0,
    # Simple — Ranged
    "Heavy Crossbow": 8.0,
    "Light Crossbow": 4.0,
    "Dart": 0.5,
    "Javelin": 2.0,
    "Sling": 0.0,
    # ------------------------------------------------------------------
    # PHB Table 7-4 Weapons (Martial — Light Melee)
    # ------------------------------------------------------------------
    "Handaxe": 3.0,
    "Light Hammer": 2.0,
    "Light Pick": 3.0,
    "Sap": 2.0,
    "Short Sword": 2.0,
    "Shortsword": 2.0,
    # Martial — One-Handed Melee
    "Battleaxe": 6.0,
    "Flail": 5.0,
    "Longsword": 4.0,
    "Heavy Pick": 6.0,
    "Rapier": 2.0,
    "Scimitar": 4.0,
    "Trident": 4.0,
    "Warhammer": 5.0,
    # Martial — Two-Handed Melee
    "Falchion": 8.0,
    "Glaive": 10.0,
    "Greataxe": 12.0,
    "Greatclub": 8.0,
    "Great Flail": 10.0,
    "Greatsword": 8.0,
    "Guisarme": 12.0,
    "Halberd": 12.0,
    "Lance": 10.0,
    "Ranseur": 12.0,
    "Scythe": 10.0,
    # Martial — Ranged
    "Longbow": 3.0,
    "Longbow Composite": 3.0,
    "Shortbow": 2.0,
    "Shortbow Composite": 2.0,
    # ------------------------------------------------------------------
    # PHB Table 7-4 Weapons (Exotic)
    # ------------------------------------------------------------------
    "Bastard Sword": 6.0,
    "Dwarven Waraxe": 8.0,
    "Whip": 2.0,
    "Orc Double Axe": 15.0,
    "Spiked Chain": 10.0,
    "Dire Flail": 10.0,
    "Gnome Hooked Hammer": 6.0,
    "Two-Bladed Sword": 10.0,
    "Dwarven Urgrosh": 12.0,
    "Hand Crossbow": 2.0,
    "Heavy Repeating Crossbow": 12.0,
    "Light Repeating Crossbow": 6.0,
    "Bolas": 2.0,
    "Net": 6.0,
    "Shuriken": 0.5,
    "Kama": 2.0,
    "Nunchaku": 2.0,
    "Siangham": 1.0,
    # ------------------------------------------------------------------
    # PHB Table 7-5 Armor
    # ------------------------------------------------------------------
    # Light Armor
    "Padded Armor": 10.0,
    "Leather Armor": 15.0,
    "Studded Leather": 20.0,
    "Chain Shirt": 25.0,
    # Medium Armor
    "Hide Armor": 25.0,
    "Scale Mail": 30.0,
    "Chainmail": 40.0,
    "Chain Mail": 40.0,
    "Breastplate": 30.0,
    # Heavy Armor
    "Splint Mail": 45.0,
    "Banded Mail": 35.0,
    "Half-Plate": 50.0,
    "Full Plate": 50.0,
    # Shields
    "Buckler": 5.0,
    "Light Wooden Shield": 5.0,
    "Light Steel Shield": 6.0,
    "Heavy Wooden Shield": 10.0,
    "Heavy Steel Shield": 15.0,
    "Tower Shield": 45.0,
    # ------------------------------------------------------------------
    # PHB Table 7-8 Adventuring Gear
    # ------------------------------------------------------------------
    "Backpack": 2.0,
    "Barrel": 30.0,
    "Basket": 1.0,
    "Bedroll": 5.0,
    "Bell": 0.0,
    "Blanket Winter": 3.0,
    "Block and Tackle": 5.0,
    "Book": 3.0,
    "Bottle Glass": 1.0,
    "Bucket": 2.0,
    "Caltrops": 2.0,
    "Candle": 0.0,
    "Canvas": 1.0,
    "Case Map or Scroll": 0.5,
    "Chain 10ft": 2.0,
    "Chalk": 0.0,
    "Chest Large": 25.0,
    "Chest Small": 25.0,
    "Crowbar": 5.0,
    "Firewood per Day": 20.0,
    "Fishhook": 0.0,
    "Fishing Net 25 sq ft": 5.0,
    "Flask": 1.5,
    "Flint and Steel": 0.0,
    "Grappling Hook": 4.0,
    "Hammer": 2.0,
    "Hourglass": 1.0,
    "Ink 1 oz Vial": 0.0,
    "Inkpen": 0.0,
    "Jug Clay": 9.0,
    "Ladder 10ft": 20.0,
    "Lamp Common": 1.0,
    "Lantern Bullseye": 3.0,
    "Lantern Hooded": 2.0,
    "Lock Average": 1.0,
    "Lock Good": 1.0,
    "Lock Simple": 1.0,
    "Lock Superior": 1.0,
    "Manacles": 2.0,
    "Manacles Masterwork": 2.0,
    "Mirror Small Steel": 0.5,
    "Mug Tankard Clay": 1.0,
    "Oil 1 Pint Flask": 1.0,
    "Paper Sheet": 0.0,
    "Parchment Sheet": 0.0,
    "Pick Mining": 10.0,
    "Pitcher Clay": 5.0,
    "Piton": 0.5,
    "Pole 10ft": 8.0,
    "Pot Iron": 10.0,
    "Pouch Belt": 0.5,
    "Rations Trail": 1.0,
    "Rope Hemp 50ft": 10.0,
    "Rope Silk 50ft": 5.0,
    "Sack": 0.5,
    "Sealing Wax": 1.0,
    "Shovel Spade": 8.0,
    "Signal Whistle": 0.0,
    "Signet Ring": 0.0,
    "Sledge": 10.0,
    "Soap 1 Lb": 1.0,
    "Spellbook Blank": 3.0,
    "Spike Iron": 0.5,
    "Tent": 20.0,
    "Torch": 1.0,
    "Vial 1 Oz": 0.1,
    "Waterskin": 4.0,
    "Whetstone": 1.0,
    # ------------------------------------------------------------------
    # PHB Table 7-7 Mounts / Vehicles (tack/gear items)
    # ------------------------------------------------------------------
    "Barding Medium Creature Chain": 40.0,
    "Barding Medium Creature Plate": 50.0,
    "Bit and Bridle": 1.0,
    "Feed per Day": 10.0,
    "Saddle Exotic Military": 40.0,
    "Saddle Exotic Pack": 20.0,
    "Saddle Exotic Riding": 30.0,
    "Saddle Military": 30.0,
    "Saddle Pack": 15.0,
    "Saddle Riding": 25.0,
    "Saddlebags": 8.0,
    "Stabling per Day": 0.0,
    # ------------------------------------------------------------------
    # Trade goods / food / misc (PHB Chapter 7 & SRD)
    # ------------------------------------------------------------------
    "Ale Gallon": 8.0,
    "Ale Mug": 1.0,
    "Bread Loaf": 0.5,
    "Cheese Hunk": 0.5,
    "Chicken": 4.0,
    "Cinnamon lb": 1.0,
    "Cloth Fine Sq Yd": 1.0,
    "Copper Piece": 0.02,
    "Cow": 1000.0,
    "Dog Riding": 0.0,
    "Flour lb": 1.0,
    "Gem Cantrip": 0.0,
    "Gold Piece": 0.02,
    "Honey lb": 1.5,
    "Iron lb": 1.0,
    "Lard lb": 1.0,
    "Meat lb": 1.0,
    "Milk Gallon": 8.5,
    "Pepper lb": 1.0,
    "Pig": 120.0,
    "Platinum Piece": 0.02,
    "Salt lb": 1.0,
    "Silver Piece": 0.02,
    "Sugar lb": 1.0,
    "Wheat lb": 1.0,
    "Wine Common Pitcher": 6.0,
    "Wine Fine Bottle": 1.5,
}


# ---------------------------------------------------------------------------
# E-016 — Item Weight Aggregator
# ---------------------------------------------------------------------------

def coin_weight(coins: dict[str, int]) -> float:
    """PHB rule: 50 coins = 1 lb regardless of metal type.

    Args:
        coins: Mapping of coin type to quantity.
                Keys accepted: ``'cp'``, ``'sp'``, ``'ep'``, ``'gp'``, ``'pp'``.

    Returns:
        Weight in pounds (total coins / 50).
    """
    _ACCEPTED = frozenset({"cp", "sp", "ep", "gp", "pp"})
    total_coins = sum(v for k, v in coins.items() if k in _ACCEPTED)
    return total_coins / 50.0


def total_carried_weight(character: "Character35e") -> float:
    """Sum weight_lb across all equipped items in EquipmentManager slots.

    Applies PHB rule: 50 coins = 1 lb via :func:`coin_weight`.

    Args:
        character: A :class:`~src.rules_engine.character_35e.Character35e` instance.

    Returns:
        Total carried weight in pounds, rounded to nearest 0.1 lb.
    """
    total = 0.0

    if character.equipment_manager is not None:
        for item in character.equipment_manager.slots.values():
            if item is not None:
                total += item.weight_lb

    coins = character.metadata.get("coins", {})
    if coins:
        total += coin_weight(coins)

    return round(total, 1)


# ---------------------------------------------------------------------------
# E-017 — STR-Based Carrying Capacity Calculator
# ---------------------------------------------------------------------------

# Size multipliers (PHB Ch 9)
_SIZE_MULTIPLIERS: dict = {}


def _get_size_multipliers() -> dict:
    """Lazily build size multiplier map after Size enum is importable."""
    if _SIZE_MULTIPLIERS:
        return _SIZE_MULTIPLIERS
    from src.rules_engine.character_35e import Size
    _SIZE_MULTIPLIERS.update({
        Size.FINE:       1.0 / 8.0,
        Size.DIMINUTIVE: 1.0 / 4.0,
        Size.TINY:       1.0 / 2.0,
        Size.SMALL:      3.0 / 4.0,
        Size.MEDIUM:     1.0,
        Size.LARGE:      2.0,
        Size.HUGE:       4.0,
        Size.GARGANTUAN: 8.0,
        Size.COLOSSAL:   16.0,
    })
    return _SIZE_MULTIPLIERS


def carrying_capacity(
    strength: int,
    size: "Size",
    quadruped: bool = False,
) -> CarryingCapacityRow:
    """PHB Table 9-1 lookup for STR 1–29; formula for STR 30+.

    For STR 30+: apply ×4 multiplier per +10 STR above 29.
    Size modifiers applied per PHB Ch 9.
    Quadruped multiplier: ×1.5 applied after size.

    Args:
        strength:  Strength ability score (≥ 1).
        size:      Creature size category.
        quadruped: If ``True``, apply ×1.5 multiplier (PHB Ch 9 sidebar).

    Returns:
        A :class:`CarryingCapacityRow` with adjusted thresholds.
    """
    multipliers = _get_size_multipliers()

    if strength <= 0:
        strength = 1

    # Resolve base row for a Medium biped
    if strength <= 29:
        base = CARRYING_CAPACITY_TABLE[strength]
        base_light  = base.light_max_lb
        base_medium = base.medium_max_lb
        base_heavy  = base.heavy_max_lb
    else:
        # STR 30+: compute by iterating bands of +10
        bands_above = math.ceil((strength - 29) / 10)
        scale = 4 ** bands_above
        ref = CARRYING_CAPACITY_TABLE[29]
        base_light  = ref.light_max_lb  * scale
        base_medium = ref.medium_max_lb * scale
        base_heavy  = ref.heavy_max_lb  * scale

    # Apply size multiplier
    size_mult = multipliers.get(size, 1.0)
    light  = base_light  * size_mult
    medium = base_medium * size_mult
    heavy  = base_heavy  * size_mult

    # Apply quadruped multiplier
    if quadruped:
        light  *= 1.5
        medium *= 1.5
        heavy  *= 1.5

    return CarryingCapacityRow(
        strength=strength,
        light_max_lb=round(light, 2),
        medium_max_lb=round(medium, 2),
        heavy_max_lb=round(heavy, 2),
    )


# ---------------------------------------------------------------------------
# E-018 — Load Category Resolver
# ---------------------------------------------------------------------------

def resolve_load_category(
    weight_lb: float,
    capacity: CarryingCapacityRow,
) -> LoadCategory:
    """Return the :class:`LoadCategory` for a given weight vs. capacity.

    Args:
        weight_lb: Total carried weight in pounds.
        capacity:  Capacity row for the character's Strength.

    Returns:
        ``Light``, ``Medium``, ``Heavy``, or ``Overload``.
    """
    if weight_lb <= capacity.light_max_lb:
        return LoadCategory.Light
    if weight_lb <= capacity.medium_max_lb:
        return LoadCategory.Medium
    if weight_lb <= capacity.heavy_max_lb:
        return LoadCategory.Heavy
    return LoadCategory.Overload


# ---------------------------------------------------------------------------
# E-019 — Load Penalty Application
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class LoadPenalties:
    """Penalties imposed by a character's encumbrance load category.

    PHB Table 9-2.

    Attributes:
        max_dex_to_ac:      Cap on Dexterity modifier applied to AC.
                            ``None`` means no cap (Light load).
        armor_check_penalty: Penalty to Str/Dex skill checks (non-positive int).
        speed_table:        Mapping of base_speed_ft → reduced_speed_ft.
                            Empty dict means no speed penalty.
        run_multiplier:     Run speed multiplier. Default 4 (PHB); Heavy sets to 3.
    """

    max_dex_to_ac: Optional[int]
    armor_check_penalty: int
    speed_table: dict
    run_multiplier: int = 4


def apply_load_penalties(load: LoadCategory) -> LoadPenalties:
    """Return :class:`LoadPenalties` for the given load category.

    PHB Table 9-2:
    * **Light**:   no penalties.
    * **Medium**:  max Dex +3, ACP −3, speed {30→20, 20→15, 15→10}.
    * **Heavy**:   max Dex +1, ACP −6, speed {30→20, 20→15, 15→10}, run ×3.
    * **Overload**: max Dex 0, ACP −6, all speeds → 0 (cannot move).

    Args:
        load: The encumbrance :class:`LoadCategory`.

    Returns:
        A :class:`LoadPenalties` dataclass.
    """
    _MEDIUM_SPEED = {30: 20, 20: 15, 15: 10}
    _HEAVY_SPEED  = {30: 20, 20: 15, 15: 10}

    if load == LoadCategory.Light:
        return LoadPenalties(
            max_dex_to_ac=None,
            armor_check_penalty=0,
            speed_table={},
            run_multiplier=4,
        )
    if load == LoadCategory.Medium:
        return LoadPenalties(
            max_dex_to_ac=3,
            armor_check_penalty=-3,
            speed_table=dict(_MEDIUM_SPEED),
            run_multiplier=4,
        )
    if load == LoadCategory.Heavy:
        return LoadPenalties(
            max_dex_to_ac=1,
            armor_check_penalty=-6,
            speed_table=dict(_HEAVY_SPEED),
            run_multiplier=3,
        )
    # Overload
    return LoadPenalties(
        max_dex_to_ac=0,
        armor_check_penalty=-6,
        speed_table={},  # all movement → 0
        run_multiplier=1,
    )


# ---------------------------------------------------------------------------
# E-020 — Voxel Speed Conversion
# ---------------------------------------------------------------------------

def voxel_speed_from_feet(speed_ft: int, voxel_ft_per_unit: int = 5) -> int:
    """Convert a speed in feet to voxel units.

    Args:
        speed_ft:          Speed in feet.
        voxel_ft_per_unit: Feet per voxel (default 5 ft).

    Returns:
        Speed in voxels (integer division).
    """
    if voxel_ft_per_unit <= 0:
        raise ValueError("voxel_ft_per_unit must be positive")
    return speed_ft // voxel_ft_per_unit


def apply_load_to_voxel_speed(
    base_voxel_speed: int,
    load: LoadCategory,
    armor_category: str = "none",
) -> int:
    """Return effective voxel speed after applying load penalties.

    If armor is medium or heavy the armor speed reduction is already applied
    elsewhere; in that case the Medium/Heavy *load* speed reduction is NOT
    double-applied.

    Args:
        base_voxel_speed: Character's base speed in voxels (before load penalty).
        load:             Current encumbrance load category.
        armor_category:   Heaviest equipped armor category string
                          (``"none"``, ``"light"``, ``"medium"``, ``"heavy"``).

    Returns:
        Effective speed in voxels.
    """
    if load == LoadCategory.Light:
        return base_voxel_speed

    if load == LoadCategory.Overload:
        return 0

    # Medium or Heavy load — check if speed reduction should be applied
    armor_already_penalized = armor_category in ("medium", "heavy")
    if armor_already_penalized:
        # Armor already applied the speed table; don't double-apply
        return base_voxel_speed

    # Convert to feet, look up in speed table, convert back
    penalties = apply_load_penalties(load)
    speed_ft = base_voxel_speed * 5
    reduced_ft = penalties.speed_table.get(speed_ft, speed_ft)
    return reduced_ft // 5


# ---------------------------------------------------------------------------
# E-047 — Encumbered Character State Builder
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class EncumbranceState:
    """Immutable encumbrance snapshot for a character.

    Attributes:
        total_weight_lb:          Total weight carried (lbs).
        capacity:                 Carrying capacity row for the character's STR.
        load:                     Resolved load category.
        penalties:                Load penalties dataclass.
        effective_speed_ft:       Speed in feet after load reduction.
        effective_speed_voxel:    Speed in voxels after load reduction.
        max_dex_to_ac_after_armor: Most restrictive Dex cap (armor + load).
        armor_check_penalty_total: Stacked ACP from armor and load.
    """

    total_weight_lb: float
    capacity: CarryingCapacityRow
    load: LoadCategory
    penalties: LoadPenalties
    effective_speed_ft: int
    effective_speed_voxel: int
    max_dex_to_ac_after_armor: Optional[int]
    armor_check_penalty_total: int


def compute_encumbrance_state(character: "Character35e") -> EncumbranceState:
    """Compute an immutable encumbrance snapshot for the given character.

    Steps:
    1. Sum all carried item weights (+ coins) via :func:`total_carried_weight`.
    2. Look up carrying capacity via :func:`carrying_capacity`.
    3. Resolve load category via :func:`resolve_load_category`.
    4. Fetch load penalties via :func:`apply_load_penalties`.
    5. Determine effective speed (avoid double-applying speed penalty if armor
       is already medium/heavy).
    6. Stack ACP: armor ACP + load ACP.
    7. Apply most-restrictive Dex cap between armor and load.

    Args:
        character: A fully initialised :class:`~src.rules_engine.character_35e.Character35e`.

    Returns:
        An :class:`EncumbranceState` snapshot.
    """
    weight = total_carried_weight(character)

    is_quadruped = bool(character.metadata.get("quadruped", False))
    cap_row = carrying_capacity(character.strength, character.size, is_quadruped)

    load = resolve_load_category(weight, cap_row)
    penalties = apply_load_penalties(load)

    # Armor category for double-penalty detection
    armor_cat = "none"
    armor_acp = 0
    armor_max_dex: Optional[int] = None
    if character.equipment_manager is not None:
        armor_cat = character.equipment_manager.get_armor_category()
        armor_acp = character.equipment_manager.get_total_acp()
        armor_max_dex = character.equipment_manager.get_min_max_dex_bonus()

    # Effective speed
    base_speed_ft: int = character.base_speed
    if load == LoadCategory.Overload:
        effective_speed_ft = 0
    elif armor_cat in ("medium", "heavy"):
        # Armor already penalized speed — don't double-apply load speed table
        effective_speed_ft = base_speed_ft
    else:
        effective_speed_ft = penalties.speed_table.get(base_speed_ft, base_speed_ft)

    effective_speed_voxel = voxel_speed_from_feet(effective_speed_ft)

    # ACP stacks
    acp_total = armor_acp + penalties.armor_check_penalty

    # Most restrictive Dex cap
    caps = [c for c in (armor_max_dex, penalties.max_dex_to_ac) if c is not None]
    combined_max_dex: Optional[int] = min(caps) if caps else None

    return EncumbranceState(
        total_weight_lb=weight,
        capacity=cap_row,
        load=load,
        penalties=penalties,
        effective_speed_ft=effective_speed_ft,
        effective_speed_voxel=effective_speed_voxel,
        max_dex_to_ac_after_armor=combined_max_dex,
        armor_check_penalty_total=acp_total,
    )


# ---------------------------------------------------------------------------
# E-063 — Encumbrance-Aware Combat & Movement
# ---------------------------------------------------------------------------

def apply_encumbrance_to_combat_state(
    character: "Character35e",
    combat_state: object,
) -> object:
    """Apply the character's current encumbrance state to *combat_state*.

    Computes an :class:`EncumbranceState` snapshot and writes the relevant
    fields into ``character.metadata`` so that :attr:`Character35e.armor_class`
    and :attr:`Character35e.voxel_speed` automatically incorporate the load
    penalties on the next access.

    Metadata keys written:
      * ``"load_max_dex_cap"``  — ``int | None``; the Dex-to-AC cap imposed by
        load alone (Medium: +3, Heavy: +1, Light/Overload: ``None``).  The
        ``armor_class`` property caps Dex at this value in addition to any
        armor max-Dex cap.
      * ``"load_acp"``          — ``int``; the armor-check penalty added by
        load (0, −3, or −6).  Callers can sum this with the armor ACP for
        skill checks (Climb, Jump, Swim, Tumble, Hide, Move Silently).
      * ``"enc_voxel_speed"``   — ``int``; the effective voxel-grid speed
        after stacking armor and load speed penalties (no double-apply).  The
        ``voxel_speed`` property returns this override when present.
      * ``"enc_stationary"``    — ``bool``; ``True`` when the character is
        Overloaded and may not move voluntarily (only standard/free actions).

    Args:
        character:    A fully initialised
                      :class:`~src.rules_engine.character_35e.Character35e`.
        combat_state: Any combat-round state container (e.g.
                      :class:`~src.rules_engine.mm_passive.CombatState`).
                      The object is returned unchanged; the encumbrance effects
                      are written to *character* directly.

    Returns:
        The unmodified *combat_state* (pass-through for chaining).
    """
    enc = compute_encumbrance_state(character)

    # Load-only Dex cap (Medium → +3, Heavy → +1, Light/Overload → None)
    character.metadata["load_max_dex_cap"] = enc.penalties.max_dex_to_ac

    # Load-only ACP (0 for Light, -3 for Medium, -6 for Heavy, -6 for Overload)
    character.metadata["load_acp"] = enc.penalties.armor_check_penalty

    # Effective voxel speed (armor + load, no double-apply)
    character.metadata["enc_voxel_speed"] = enc.effective_speed_voxel

    # Stationary flag for Overload
    character.metadata["enc_stationary"] = (enc.load == LoadCategory.Overload)

    return combat_state
