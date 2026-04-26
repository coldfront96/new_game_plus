"""LW-009 · LW-019 · LW-030 · LW-033 — Regeneration, Fast Healing, and healing precedence."""
from __future__ import annotations

import enum
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.rules_engine.character_35e import Character35e

_log = logging.getLogger(__name__)

CombatEntity = "Character35e"
DamageLog = list["DamageEvent"]


# ---------------------------------------------------------------------------
# LW-009 · Schemas
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class RegenerationRecord:
    """Tracks regeneration and fast healing state for a single entity.

    Regeneration is suppressed for the full round in which a listed weakness
    damage type is received.  Fast Healing is never suppressed.
    suppressed_until_tick: Regeneration is inactive while current_tick <= this value.
    """
    entity_id: str
    regen_hp_per_round: int
    fast_heal_hp_per_round: int
    elemental_weaknesses: tuple[str, ...]   # e.g. ("Fire",) for Troll
    alignment_weaknesses: tuple[str, ...]   # e.g. ("Good", "Silver") for certain demons
    suppressed_until_tick: int


@dataclass(slots=True)
class DamageEvent:
    damage_type: str   # e.g. "Fire", "Cold", "Good", "Slashing"
    amount: int
    tick: int


# ---------------------------------------------------------------------------
# LW-019 · Fast Healing Tick Processor
# ---------------------------------------------------------------------------

def process_healing_tick(
    entity: "Character35e",
    record: RegenerationRecord,
    damage_log: DamageLog,
    tick: int,
) -> int:
    """Apply fast heal or regeneration for one round; return net HP restored.

    Fast Healing: adds fast_heal_hp_per_round unconditionally (capped at max HP).
    Does not restore missing limbs or ability damage.
    Regeneration: skipped if a weakness damage type appears in this round's damage_log.
    Both paths are subject to resolve_healing_precedence (LW-033) when called together.
    """
    max_hp: int = entity.hit_points
    current_hp: int = getattr(entity, "_current_hp", max_hp)
    net = 0

    # Regeneration path
    if record.regen_hp_per_round > 0:
        this_round = [e for e in damage_log if e.tick == tick]
        suppressed = any(
            e.damage_type in record.elemental_weaknesses
            or e.damage_type in record.alignment_weaknesses
            for e in this_round
        )
        if suppressed:
            record.suppressed_until_tick = tick + 1
        elif not _regen_suppressed(record, tick):
            net += min(record.regen_hp_per_round, max_hp - current_hp)

    # Fast Healing path — fires only if regen is not also active this round
    if record.fast_heal_hp_per_round > 0 and not _regen_active(record, tick):
        net += min(record.fast_heal_hp_per_round, max_hp - current_hp)

    return max(0, net)


def _regen_active(record: RegenerationRecord, tick: int) -> bool:
    return record.regen_hp_per_round > 0 and not _regen_suppressed(record, tick)


def _regen_suppressed(record: RegenerationRecord, tick: int) -> bool:
    return record.suppressed_until_tick >= tick


# ---------------------------------------------------------------------------
# LW-030 · Regeneration Weakness Suppression
# ---------------------------------------------------------------------------

def apply_regeneration_weakness_check(
    record: RegenerationRecord,
    damage_event: DamageEvent,
    tick: int,
) -> RegenerationRecord:
    """Suppress regeneration next round when a weakness damage type is received.

    Lethal damage from a weakness source is NOT converted to nonlethal
    (unlike standard Regeneration behavior) and is applied directly to HP.
    """
    is_weakness = (
        damage_event.damage_type in record.elemental_weaknesses
        or damage_event.damage_type in record.alignment_weaknesses
    )
    if is_weakness:
        record.suppressed_until_tick = tick + 1
        _log.debug(
            "Regen weakness: entity=%s type=%s suppressed until tick %d",
            record.entity_id, damage_event.damage_type, record.suppressed_until_tick,
        )
    return record


# ---------------------------------------------------------------------------
# LW-033 · Healing Precedence Resolver
# ---------------------------------------------------------------------------

class HealingSource(enum.Enum):
    Regeneration = "regeneration"
    FastHealing  = "fast_healing"
    Both         = "both"   # invalid per RAW — never returned by this function


@dataclass(slots=True)
class HealingResult:
    hp_restored: int
    source: HealingSource
    regen_was_suppressed: bool


def resolve_healing_precedence(
    entity: "Character35e",
    record: RegenerationRecord,
    tick: int,
) -> HealingResult:
    """Determine which healing source fires this round.

    Per 3.5e RAW, Regeneration supersedes Fast Healing — they do not stack.
    If Regeneration is suppressed this round, Fast Healing activates instead.
    """
    max_hp: int = entity.hit_points
    current_hp: int = getattr(entity, "_current_hp", max_hp)
    deficit = max_hp - current_hp
    suppressed = _regen_suppressed(record, tick)

    if record.regen_hp_per_round > 0 and not suppressed:
        restored = min(record.regen_hp_per_round, deficit)
        _log.debug("Heal tick=%d entity=%s REGEN +%d", tick, record.entity_id, restored)
        return HealingResult(
            hp_restored=restored,
            source=HealingSource.Regeneration,
            regen_was_suppressed=False,
        )

    if record.fast_heal_hp_per_round > 0:
        restored = min(record.fast_heal_hp_per_round, deficit)
        _log.debug(
            "Heal tick=%d entity=%s FAST_HEAL +%d (regen_suppressed=%s)",
            tick, record.entity_id, restored, suppressed,
        )
        return HealingResult(
            hp_restored=restored,
            source=HealingSource.FastHealing,
            regen_was_suppressed=suppressed,
        )

    return HealingResult(hp_restored=0, source=HealingSource.FastHealing, regen_was_suppressed=suppressed)
