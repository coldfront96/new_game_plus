"""CRF-001..004 — Magic Item Crafting Pipeline.

src/rules_engine/crafting.py
-----------------------------
Implements the 3.5e SRD crafting rules for Item Creation feats:

* :func:`brew_potion`         — Brew Potion feat (caster level ≥ 3, 1st–3rd level spell)
* :func:`craft_wondrous_item` — Craft Wondrous Item feat (caster level ≥ 3)
* :func:`check_craft_dc`      — Spellcraft check to succeed at crafting

Pricing rules (DMG Chapter 7)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Potion   : spell_level × caster_level × 25 gp  (half market price)
Wondrous : market_price // 2  (character pays half to craft)
XP cost  : gp_cost // 25
Time     : 1 day per 1,000 gp of market price (min 1 day)

Usage::

    from src.rules_engine.crafting import brew_potion, craft_wondrous_item
    from src.rules_engine.magic import create_default_registry
    import random

    registry = create_default_registry()
    rng = random.Random(42)
    result = brew_potion(wizard, "Cure Light Wounds", caster_level=5,
                         registry=registry, party_gold=500, rng=rng)
    if result.success:
        party_gold -= result.gp_cost
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from src.rules_engine.magic import SpellRegistry


# ---------------------------------------------------------------------------
# CRF-001 · CraftingResult dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class CraftingResult:
    """Outcome of a single crafting attempt.

    Attributes:
        success:        Whether all prerequisites were met and gold deducted.
        item_name:      Canonical name of the crafted item.
        item_type:      Category string (``"potion"``, ``"wondrous"``).
        gp_cost:        Gold piece cost paid by the crafter.
        xp_cost:        Experience point cost paid by the crafter.
        days:           Crafting time in in-game days.
        failure_reason: Non-empty when ``success`` is ``False``; explains why.
    """

    success: bool
    item_name: str
    item_type: str = "misc"
    gp_cost: int = 0
    xp_cost: int = 0
    days: int = 1
    failure_reason: str = ""


# ---------------------------------------------------------------------------
# CRF-004 · Spellcraft DC table
# ---------------------------------------------------------------------------

CRAFT_DC_TABLE: Dict[str, int] = {
    "potion":   5,
    "wondrous": 5,
    "scroll":   5,
    "rod":      9,
    "staff":    9,
    "ring":     5,
    "weapon":   5,
    "armor":    5,
}
"""Mapping of item category → base Spellcraft DC.

The final DC = base + spell_level × 2 (or just the base for non-spell items).
"""


def check_craft_dc(
    caster: Any,
    dc: int,
    rng: Optional[random.Random] = None,
) -> bool:
    """Roll Spellcraft to meet or beat *dc*.

    Uses ``caster.metadata.get("spellcraft_ranks", 0)`` plus the INT modifier
    derived from the caster's Intelligence score.  An unrolled natural 1 always
    fails; a natural 20 always succeeds.

    Args:
        caster: A character object with ``intelligence`` and ``metadata`` attrs.
        dc:     Target Difficulty Class.
        rng:    Optional RNG for determinism.

    Returns:
        ``True`` if the check meets or beats *dc*.
    """
    rng = rng or random.Random()
    roll = rng.randint(1, 20)
    if roll == 1:
        return False
    if roll == 20:
        return True
    int_score = int(getattr(caster, "intelligence", 10) or 10)
    int_mod = (int_score - 10) // 2
    spellcraft_ranks = int(getattr(caster, "metadata", {}).get("spellcraft_ranks", 0))
    return (roll + int_mod + spellcraft_ranks) >= dc


# ---------------------------------------------------------------------------
# Internal prerequisites helpers
# ---------------------------------------------------------------------------

def _has_feat(caster: Any, feat_name: str) -> bool:
    feats = getattr(caster, "feats", [])
    return feat_name in feats


def _caster_level(caster: Any, override: Optional[int] = None) -> int:
    if override is not None:
        return override
    return int(getattr(caster, "level", 1) or 1)


def _spell_in_registry(spell_name: str, registry: SpellRegistry) -> bool:
    return registry.get(spell_name) is not None


def _spell_level_from_registry(spell_name: str, registry: SpellRegistry) -> int:
    spell = registry.get(spell_name)
    return int(spell.level) if spell is not None else 0


# ---------------------------------------------------------------------------
# CRF-002 · Brew Potion
# ---------------------------------------------------------------------------

def brew_potion(
    caster: Any,
    spell_name: str,
    caster_level: int,
    registry: SpellRegistry,
    party_gold: int,
    *,
    rng: Optional[random.Random] = None,
    check_spellcraft: bool = False,
) -> CraftingResult:
    """Craft a potion of *spell_name* per 3.5e SRD Brew Potion rules.

    Prerequisites (all must pass):

    * Caster possesses the ``"Brew Potion"`` feat.
    * ``caster_level >= 3``.
    * *spell_name* is in *registry*.
    * Spell level is 1–3 (potions cannot store higher than 3rd level).
    * ``party_gold >= gp_cost``.

    Pricing:
        ``gp_cost = spell_level × caster_level × 25``
        ``xp_cost = gp_cost // 25``

    Args:
        caster:           The crafting character.
        spell_name:       Name of the spell to store in the potion.
        caster_level:     Effective caster level (typically ``character.level``).
        registry:         Populated :class:`~src.rules_engine.magic.SpellRegistry`.
        party_gold:       Available gold pieces.
        rng:              Optional RNG (used when *check_spellcraft* is True).
        check_spellcraft: When ``True``, rolls a Spellcraft check against the
                          craft DC (``5 + spell_level * 2``).  Failure returns
                          a ``CraftingResult`` with ``success=False``.

    Returns:
        A :class:`CraftingResult` describing the outcome.
    """
    item_name = f"Potion of {spell_name}"

    if not _has_feat(caster, "Brew Potion"):
        return CraftingResult(
            success=False, item_name=item_name,
            failure_reason="Caster lacks the Brew Potion feat.",
        )

    cl = _caster_level(caster, caster_level)
    if cl < 3:
        return CraftingResult(
            success=False, item_name=item_name,
            failure_reason=f"Caster level {cl} < 3 (minimum for Brew Potion).",
        )

    if not _spell_in_registry(spell_name, registry):
        return CraftingResult(
            success=False, item_name=item_name,
            failure_reason=f"Spell '{spell_name}' not found in registry.",
        )

    spell_level = _spell_level_from_registry(spell_name, registry)
    if spell_level < 1 or spell_level > 3:
        return CraftingResult(
            success=False, item_name=item_name,
            failure_reason=(
                f"Spell level {spell_level} is out of range for potions (1–3)."
            ),
        )

    gp_cost = spell_level * cl * 25
    xp_cost = gp_cost // 25

    if party_gold < gp_cost:
        return CraftingResult(
            success=False, item_name=item_name,
            gp_cost=gp_cost, xp_cost=xp_cost,
            failure_reason=f"Insufficient gold: need {gp_cost} gp, have {party_gold}.",
        )

    if check_spellcraft:
        dc = CRAFT_DC_TABLE["potion"] + spell_level * 2
        if not check_craft_dc(caster, dc, rng):
            return CraftingResult(
                success=False, item_name=item_name,
                gp_cost=gp_cost, xp_cost=xp_cost,
                failure_reason=f"Spellcraft check failed (DC {dc}).",
            )

    return CraftingResult(
        success=True,
        item_name=item_name,
        item_type="potion",
        gp_cost=gp_cost,
        xp_cost=xp_cost,
        days=1,
    )


# ---------------------------------------------------------------------------
# CRF-003 · Craft Wondrous Item
# ---------------------------------------------------------------------------

def craft_wondrous_item(
    caster: Any,
    item_name: str,
    market_price_gp: int,
    caster_level: int,
    party_gold: int,
    *,
    rng: Optional[random.Random] = None,
    check_spellcraft: bool = False,
) -> CraftingResult:
    """Craft a wondrous item per 3.5e SRD Craft Wondrous Item rules.

    Prerequisites:

    * Caster possesses ``"Craft Wondrous Item"`` feat.
    * ``caster_level >= 3``.
    * ``party_gold >= gp_cost``.

    Pricing:
        ``gp_cost = market_price_gp // 2``
        ``xp_cost = gp_cost // 25``
        ``days = ceil(market_price_gp / 1000)`` (minimum 1)

    Args:
        caster:           The crafting character.
        item_name:        Name of the wondrous item to craft.
        market_price_gp:  Full market price of the item in gold pieces.
        caster_level:     Effective caster level.
        party_gold:       Available gold pieces.
        rng:              Optional RNG for Spellcraft check.
        check_spellcraft: When ``True``, rolls a Spellcraft check (DC 5 + spell level).

    Returns:
        A :class:`CraftingResult` describing the outcome.
    """
    if not _has_feat(caster, "Craft Wondrous Item"):
        return CraftingResult(
            success=False, item_name=item_name,
            failure_reason="Caster lacks the Craft Wondrous Item feat.",
        )

    cl = _caster_level(caster, caster_level)
    if cl < 3:
        return CraftingResult(
            success=False, item_name=item_name,
            failure_reason=f"Caster level {cl} < 3 (minimum for Craft Wondrous Item).",
        )

    if market_price_gp < 1:
        return CraftingResult(
            success=False, item_name=item_name,
            failure_reason="market_price_gp must be a positive integer.",
        )

    gp_cost = market_price_gp // 2
    xp_cost = gp_cost // 25
    days = max(1, math.ceil(market_price_gp / 1000))

    if party_gold < gp_cost:
        return CraftingResult(
            success=False, item_name=item_name,
            gp_cost=gp_cost, xp_cost=xp_cost, days=days,
            failure_reason=f"Insufficient gold: need {gp_cost} gp, have {party_gold}.",
        )

    if check_spellcraft:
        dc = CRAFT_DC_TABLE["wondrous"]
        if not check_craft_dc(caster, dc, rng):
            return CraftingResult(
                success=False, item_name=item_name,
                gp_cost=gp_cost, xp_cost=xp_cost, days=days,
                failure_reason=f"Spellcraft check failed (DC {dc}).",
            )

    return CraftingResult(
        success=True,
        item_name=item_name,
        item_type="wondrous",
        gp_cost=gp_cost,
        xp_cost=xp_cost,
        days=days,
    )
