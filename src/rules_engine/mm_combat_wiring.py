"""LW-044 — Wire all MM Physics subsystems into the CombatEngine turn loop.

Integration points (called by CombatEngine or any turn-based orchestrator):
  start_of_turn()   — aura passive effects for each entity with an Aura PassiveEffect.
  after_attack()    — Improved Grab attempt; SR check before spell damage.
  apply_damage()    — DR applied to all physical damage.
  end_of_round()    — healing tick (Regen + Fast Heal precedence) for every RegenerationRecord.
  on_death()        — decrement species world count via SpawnDirector.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.rules_engine.character_35e import Character35e
    from src.rules_engine.mm_passive import PassiveEffect, EffectApplication, CombatState
    from src.rules_engine.mm_grapple import GrappleState
    from src.rules_engine.mm_immortal import RegenerationRecord, DamageEvent, HealingResult
    from src.rules_engine.mm_metaphysical import DRRecord, SRRecord, SRResult
    from src.world_sim.spawn_director import SpawnDirector

_log = logging.getLogger(__name__)


@dataclass
class MMPhysicsContext:
    """Per-encounter registry of all MM physics state.  Attach one to each CombatEngine."""
    regen_records: dict[str, "RegenerationRecord"] = field(default_factory=dict)
    dr_records:    dict[str, "DRRecord"]           = field(default_factory=dict)
    sr_records:    dict[str, "SRRecord"]           = field(default_factory=dict)
    grapple_states: dict[str, "GrappleState"]      = field(default_factory=dict)
    damage_logs:   dict[str, list["DamageEvent"]]  = field(default_factory=dict)
    aversion_states: dict[str, object]             = field(default_factory=dict)
    positions: dict[str, tuple[float, float, float]] = field(default_factory=dict)
    spawn_director: "SpawnDirector | None"         = None


# ---------------------------------------------------------------------------
# Start of entity turn
# ---------------------------------------------------------------------------

def start_of_turn(
    source: "Character35e",
    combat_state: "CombatState",
    ctx: MMPhysicsContext,
    tick: int,
) -> list["EffectApplication"]:
    """Process aura PassiveEffects for source at the start of its turn."""
    from src.rules_engine.mm_passive import process_aura_effects

    return process_aura_effects(source, combat_state, tick, positions=ctx.positions)


# ---------------------------------------------------------------------------
# After attack resolution
# ---------------------------------------------------------------------------

def after_attack(
    attacker: "Character35e",
    target: "Character35e",
    hit_confirmed: bool,
    is_natural_attack: bool,
    spell_name: str | None,
    spell_tags: tuple[str, ...],
    ctx: MMPhysicsContext,
    tick: int,
) -> dict:
    """Handle Improved Grab and SR checks immediately after an attack resolves.

    Returns a dict with keys:
      'grapple_state'  — new GrappleState or None
      'sr_result'      — SRResult or None
      'spell_blocked'  — bool (True if SR blocked the spell)
    """
    from src.rules_engine.mm_grapple import attempt_improved_grab
    from src.rules_engine.mm_metaphysical import apply_sr_interaction_rules

    result: dict = {"grapple_state": None, "sr_result": None, "spell_blocked": False}

    # Improved Grab — only on confirmed natural attack hits
    if hit_confirmed and is_natural_attack:
        gs = attempt_improved_grab(attacker, target, hit_confirmed=True, tick=tick)
        if gs is not None:
            ctx.grapple_states[gs.grapple_id] = gs
            result["grapple_state"] = gs
            _log.debug("Improved Grab initiated: %s", gs.grapple_id)

    # Spell Resistance check — runs before any spell damage is applied
    if spell_name is not None:
        sr_record = ctx.sr_records.get(target.char_id)
        if sr_record is not None:
            sr_result = apply_sr_interaction_rules(
                spell_name, spell_tags, attacker, target, sr_record
            )
            result["sr_result"] = sr_result
            result["spell_blocked"] = not sr_result.penetrated

    return result


# ---------------------------------------------------------------------------
# Damage application
# ---------------------------------------------------------------------------

def apply_damage(
    target: "Character35e",
    raw_damage: int,
    weapon_properties: tuple[str, ...],
    ctx: MMPhysicsContext,
    tick: int,
    damage_type: str = "Physical",
) -> int:
    """Apply DR to raw physical damage; log the damage event for regen checks.

    Returns post-DR damage (minimum 0).
    """
    from src.rules_engine.mm_metaphysical import apply_damage_reduction
    from src.rules_engine.mm_immortal import DamageEvent, apply_regeneration_weakness_check

    dr_record = ctx.dr_records.get(target.char_id)
    post_dr = raw_damage
    if dr_record is not None:
        post_dr = apply_damage_reduction(raw_damage, weapon_properties, dr_record)

    # Log damage event for regen suppression tracking
    event = DamageEvent(damage_type=damage_type, amount=post_dr, tick=tick)
    ctx.damage_logs.setdefault(target.char_id, []).append(event)

    regen_record = ctx.regen_records.get(target.char_id)
    if regen_record is not None:
        apply_regeneration_weakness_check(regen_record, event, tick)

    return post_dr


# ---------------------------------------------------------------------------
# End of round
# ---------------------------------------------------------------------------

def end_of_round(
    entities: list["Character35e"],
    ctx: MMPhysicsContext,
    tick: int,
) -> dict[str, "HealingResult"]:
    """Run the healing tick for every entity that has a RegenerationRecord.

    Returns a map of char_id → HealingResult.
    """
    from src.rules_engine.mm_immortal import resolve_healing_precedence

    results: dict = {}
    for entity in entities:
        record = ctx.regen_records.get(entity.char_id)
        if record is None:
            continue
        healing = resolve_healing_precedence(entity, record, tick)
        results[entity.char_id] = healing
        if healing.hp_restored > 0:
            current = getattr(entity, "_current_hp", entity.hit_points)
            object.__setattr__(entity, "_current_hp", min(entity.hit_points, current + healing.hp_restored)) \
                if hasattr(type(entity), "__slots__") else \
                setattr(entity, "_current_hp", min(entity.hit_points, current + healing.hp_restored))
    return results


# ---------------------------------------------------------------------------
# On entity death
# ---------------------------------------------------------------------------

def on_death(
    entity: "Character35e",
    chunk_id: str,
    ctx: MMPhysicsContext,
    permanent: bool = True,
) -> None:
    """Decrement species world count via SpawnDirector when an entity dies permanently."""
    if ctx.spawn_director is None:
        return
    species_id = getattr(entity, "species_id", entity.char_id)
    ctx.spawn_director.notify_death(species_id, chunk_id, permanent=permanent)
    _log.debug("on_death: species=%s chunk=%s permanent=%s", species_id, chunk_id, permanent)
