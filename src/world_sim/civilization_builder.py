"""PH2-001 · PH2-002 · PH2-003 · PH2-004 · PH2-005 — Civilization & Economy subsystem.

Phase 2 — Player Interaction & Civilised Ecology.
Provides deterministic town placement, biome safety classification, merchant
inventory schema, and the population-linked inventory calculator.
"""
from __future__ import annotations

import enum
import hashlib
import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.world_sim.biome import Biome
    from src.world_sim.factions import FactionRecord
    from src.world_sim.population import PopulationLedger, SpeciesPopRecord, WorldChunk


# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

TownRegistry = dict[str, "TownRecord"]
MerchantRegistry = dict[str, "MerchantInventoryRecord"]


# ---------------------------------------------------------------------------
# PH2-001 · TownRecord Schema
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class TownRecord:
    """A procedurally placed town anchored to a specific world chunk.

    Attributes:
        town_id:          Deterministic identifier derived from ``chunk_id + seed``.
        name:             Human-readable town name.
        chunk_id:         World-sim chunk that hosts this town.
        biome:            Biome of the host chunk.
        faction_name:     Name of the governing faction, or ``None``.
        population_count: Approximate NPC population.
        merchant_ids:     IDs of merchants operating in this town.
    """

    town_id: str
    name: str
    chunk_id: str
    biome: "Biome"
    faction_name: str | None
    population_count: int
    merchant_ids: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# PH2-002 · Safe Biome Classifier
# ---------------------------------------------------------------------------

def is_safe_biome(biome: "Biome") -> bool:
    """Return ``True`` if *biome* is suitable for permanent settlement.

    Allowed biomes (hospitable terrain):
        ``Temperate_Plain``, ``Temperate_Forest``, ``Temperate_Hill``,
        ``Warm_Plain``, ``Warm_Forest``, ``Any_Urban``.

    All hostile, transient, and planar biomes return ``False``.

    Args:
        biome: A :class:`~src.world_sim.biome.Biome` enum value.

    Returns:
        ``True`` if the biome supports permanent settlement.
    """
    from src.world_sim.biome import Biome

    _SAFE_BIOMES: frozenset[Biome] = frozenset({
        Biome.Temperate_Plain,
        Biome.Temperate_Forest,
        Biome.Temperate_Hill,
        Biome.Warm_Plain,
        Biome.Warm_Forest,
        Biome.Any_Urban,
    })
    return biome in _SAFE_BIOMES


# ---------------------------------------------------------------------------
# PH2-003 · Procedural Town Generator
# ---------------------------------------------------------------------------

def _derive_town_id(chunk_id: str, seed: int) -> str:
    """Return a deterministic hex town_id from *chunk_id* and *seed*."""
    raw = f"{chunk_id}:{seed}".encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def _town_name_from_id(town_id: str) -> str:
    """Derive a simple reproducible placeholder town name from *town_id*."""
    prefixes = [
        "Ash", "Bright", "Crest", "Dawn", "Elder",
        "Fern", "Gold", "Haven", "Iron", "Jade",
        "Knoll", "Lake", "Mill", "North", "Oak",
        "Pine", "River", "Stone", "Timber", "Vale",
    ]
    suffixes = [
        "burg", "dale", "fall", "field", "ford",
        "gate", "ham", "haven", "hill", "hold",
        "keep", "manor", "mere", "moor", "port",
        "reach", "stead", "thorpe", "ton", "wick",
    ]
    idx = int(town_id[:4], 16)
    prefix = prefixes[idx % len(prefixes)]
    suffix = suffixes[(idx >> 8) % len(suffixes)]
    return f"{prefix}{suffix}"


def _faction_affinity_score(faction: "FactionRecord", biome: "Biome") -> int:
    """Return an alignment-affinity score for placing *faction* in *biome*.

    Lawful factions prefer ``Any_Urban``; Neutral factions prefer plains/forests.
    Higher score → stronger preference.
    """
    from src.world_sim.biome import Biome
    from src.rules_engine.character_35e import Alignment

    alignment = faction.alignment
    is_lawful = alignment in (
        Alignment.LAWFUL_GOOD,
        Alignment.LAWFUL_NEUTRAL,
        Alignment.LAWFUL_EVIL,
    )
    is_neutral = alignment in (
        Alignment.TRUE_NEUTRAL,
        Alignment.NEUTRAL_GOOD,
        Alignment.NEUTRAL_EVIL,
    )

    if is_lawful and biome == Biome.Any_Urban:
        return 3
    if is_lawful and biome in (Biome.Temperate_Plain, Biome.Warm_Plain):
        return 2
    if is_neutral and biome in (
        Biome.Temperate_Plain,
        Biome.Warm_Plain,
        Biome.Temperate_Forest,
        Biome.Warm_Forest,
    ):
        return 3
    return 1


def generate_towns(
    world_chunks: "list[WorldChunk]",
    faction_registry: "dict[str, FactionRecord]",
    seed: int,
    max_towns_per_biome: int = 3,
) -> TownRegistry:
    """Procedurally place towns across the world using a deterministic RNG.

    Algorithm
    ~~~~~~~~~
    1. Iterate all *world_chunks*.
    2. Skip chunks whose biome fails :func:`is_safe_biome`.
    3. For each eligible chunk, roll a placement chance derived from
       ``seed + chunk_id`` hash (30 % base chance).
    4. Track how many towns have been placed per biome; skip once the
       *max_towns_per_biome* cap is reached.
    5. Assign the :class:`~src.world_sim.factions.FactionRecord` with the
       highest affinity score for the chunk's biome.
    6. Return the complete :data:`TownRegistry`.

    Args:
        world_chunks:        All world chunks to evaluate.
        faction_registry:    Name → FactionRecord mapping.
        seed:                World generation seed (guarantees reproducibility).
        max_towns_per_biome: Maximum towns placed per distinct biome.

    Returns:
        A :data:`TownRegistry` (``dict[str, TownRecord]``) keyed by ``town_id``.
    """
    registry: TownRegistry = {}
    biome_counts: dict[str, int] = {}
    factions = list(faction_registry.values())

    for chunk in world_chunks:
        if not is_safe_biome(chunk.biome):
            continue

        biome_key = chunk.biome.value
        if biome_counts.get(biome_key, 0) >= max_towns_per_biome:
            continue

        # Deterministic placement roll (0–99); place if < 30.
        roll_hash = int(hashlib.sha256(f"{seed}:{chunk.chunk_id}".encode()).hexdigest()[:8], 16)
        placement_roll = roll_hash % 100
        if placement_roll >= 30:
            continue

        town_id = _derive_town_id(chunk.chunk_id, seed)
        if town_id in registry:
            # Collision from a different chunk — skip to maintain one-town-per-chunk.
            continue

        # Pick best faction by affinity score.
        best_faction: "FactionRecord | None" = None
        best_score = -1
        for faction in factions:
            score = _faction_affinity_score(faction, chunk.biome)
            if score > best_score:
                best_score = score
                best_faction = faction

        merchant_id = f"merchant_{town_id}"
        record = TownRecord(
            town_id=town_id,
            name=_town_name_from_id(town_id),
            chunk_id=chunk.chunk_id,
            biome=chunk.biome,
            faction_name=best_faction.name if best_faction else None,
            population_count=100 + (roll_hash % 900),
            merchant_ids=[merchant_id],
        )
        registry[town_id] = record
        biome_counts[biome_key] = biome_counts.get(biome_key, 0) + 1

    return registry


# ---------------------------------------------------------------------------
# PH2-004 · MerchantInventoryRecord Schema
# ---------------------------------------------------------------------------

class ItemCategory(enum.Enum):
    """Broad category for a tradeable item."""

    RawMaterial = "raw_material"
    Weapon      = "weapon"
    Armour      = "armour"
    Provision   = "provision"
    Alchemical  = "alchemical"
    Misc        = "misc"


@dataclass(slots=True)
class InventoryItem:
    """A single item type that may appear in a merchant's stock.

    Attributes:
        item_name:      Human-readable item name.
        base_price_gp:  Gold piece value before any price modifiers.
        category:       Broad :class:`ItemCategory`.
    """

    item_name: str
    base_price_gp: int
    category: ItemCategory


@dataclass(slots=True)
class MerchantInventoryRecord:
    """A merchant's stock at a given moment, linked to their home town.

    Attributes:
        merchant_id: Unique merchant identifier.
        town_id:     The :class:`TownRecord` town this merchant operates in.
        stock:       Mapping of ``item_name → quantity`` (0 means out of stock).
    """

    merchant_id: str
    town_id: str
    stock: dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# PH2-005 · Population-Linked Inventory Calculator
# ---------------------------------------------------------------------------

#: Maps species_id to a list of (item_name, drop_rate_coefficient) pairs.
#: The coefficient is multiplied by the local population count to produce stock.
SPECIES_TO_LOOT: dict[str, list[tuple[str, float]]] = {
    "deer":    [("Leather",    0.10), ("Raw Meat",   0.15)],
    "wolf":    [("Wolf Pelt",  0.08), ("Bone",       0.12)],
    "bear":    [("Bear Hide",  0.06), ("Bear Claw",  0.05)],
    "boar":    [("Leather",    0.09), ("Raw Meat",   0.12)],
    "rabbit":  [("Rabbit Fur", 0.20), ("Raw Meat",   0.25)],
    "elk":     [("Leather",    0.08), ("Antler",     0.07)],
    "fox":     [("Fox Pelt",   0.12), ("Bone",       0.06)],
    "goblin":  [("Bone",       0.05), ("Iron Scrap", 0.04)],
    "orc":     [("Bone",       0.06), ("Iron Scrap", 0.06)],
    "spider":  [("Spider Silk", 0.07), ("Venom Sac", 0.04)],
    "bat":     [("Bone",       0.05), ("Bat Wing",   0.08)],
    "rat":     [("Rat Pelt",   0.15), ("Bone",       0.10)],
}

#: Minimum base_price_gp for items synthesised from SPECIES_TO_LOOT.
_LOOT_PRICES: dict[str, int] = {
    "Leather":     2,
    "Raw Meat":    1,
    "Wolf Pelt":   5,
    "Bone":        1,
    "Bear Hide":  10,
    "Bear Claw":   4,
    "Bear Pelt":   8,
    "Rabbit Fur":  1,
    "Antler":      3,
    "Fox Pelt":    4,
    "Iron Scrap":  2,
    "Spider Silk":10,
    "Venom Sac":   6,
    "Bat Wing":    2,
    "Rat Pelt":    1,
}

#: Stock quantity is clamped to [0, 99].
_STOCK_MAX = 99
_STOCK_MIN = 0


def calculate_merchant_inventory(
    town: TownRecord,
    ledger: "PopulationLedger",
    species_registry: "dict[str, SpeciesPopRecord]",
    item_table: "dict[str, InventoryItem]",
) -> MerchantInventoryRecord:
    """Build a :class:`MerchantInventoryRecord` from current population data.

    For each species whose chunk matches *town.chunk_id*, reads the local
    population count from *ledger* and maps it to item quantities via
    :data:`SPECIES_TO_LOOT`.

    Stock quantity = ``floor(local_count × drop_rate_coefficient)``,
    clamped to ``[0, 99]``.

    Args:
        town:             The town whose merchant is being stocked.
        ledger:           Current population ledger.
        species_registry: Species-id → :class:`~src.world_sim.population.SpeciesPopRecord`.
        item_table:       Known :class:`InventoryItem` definitions (may be empty;
                          species-derived items are synthesised automatically).

    Returns:
        A :class:`MerchantInventoryRecord` for the town's first merchant.
    """
    merchant_id = town.merchant_ids[0] if town.merchant_ids else f"merchant_{town.town_id}"
    stock: dict[str, int] = {}

    for species_id, pop_record in ledger.items():
        local_count = pop_record.local_counts.get(town.chunk_id, 0)
        if local_count <= 0:
            continue
        loot_entries = SPECIES_TO_LOOT.get(species_id)
        if not loot_entries:
            continue
        for item_name, drop_rate in loot_entries:
            qty = math.floor(local_count * drop_rate)
            qty = max(_STOCK_MIN, min(_STOCK_MAX, qty))
            stock[item_name] = stock.get(item_name, 0) + qty
            # Re-clamp after accumulation.
            stock[item_name] = min(_STOCK_MAX, stock[item_name])

    return MerchantInventoryRecord(
        merchant_id=merchant_id,
        town_id=town.town_id,
        stock=stock,
    )
