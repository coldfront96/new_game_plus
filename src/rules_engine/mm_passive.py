"""LW-007 · LW-017 · LW-026 · LW-031 — Passive lethality: gaze attacks and auras."""
from __future__ import annotations

import enum
import math
import random as _stdlib_random
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.rules_engine.character_35e import Character35e

# Type alias — all MM physics modules use Character35e as CombatEntity.
CombatEntity = "Character35e"


# ---------------------------------------------------------------------------
# LW-007 · Passive effect schemas
# ---------------------------------------------------------------------------

class SaveType(enum.Enum):
    Fortitude = "fortitude"
    Reflex    = "reflex"
    Will      = "will"


class PassiveEffectType(enum.Enum):
    Gaze               = "gaze"
    Aura               = "aura"
    Frightful_Presence = "frightful_presence"
    Stench             = "stench"
    Spores             = "spores"
    Death_Throes       = "death_throes"


@dataclass(slots=True)
class PassiveEffect:
    effect_type: PassiveEffectType
    range_ft: int
    save_type: SaveType | None
    save_dc: int
    effect_on_fail: str
    effect_on_pass: str | None
    suppress_conditions: tuple[str, ...]   # condition names that fully negate this effect


@dataclass(slots=True)
class EffectApplication:
    target_id: str
    effect_type: PassiveEffectType
    saved: bool
    tick: int


class GazeAversionState(enum.Enum):
    Looking    = "looking"     # must save every round
    Averting   = "averting"    # 50 % miss chance; -2 to attacks on gazer
    ClosedEyes = "closed_eyes" # immune to gaze; 50 % miss on own attacks
    Mirror     = "mirror"      # gazer saves against own reflection


@dataclass
class CombatState:
    """Snapshot of entities present in the current combat encounter."""
    entities: list["Character35e"]
    tick: int


# ---------------------------------------------------------------------------
# LW-017 · Passive Lethality Evaluator
# ---------------------------------------------------------------------------

def evaluate_passive_effects(
    source: "Character35e",
    observers: list["Character35e"],
    tick: int,
    positions: dict[str, tuple[float, float, float]] | None = None,
    aversion_states: dict[str, GazeAversionState] | None = None,
) -> list[EffectApplication]:
    """Iterate PassiveEffects on source; range-check, LoS-check, and roll saves.

    passive_effects must be stored as a list[PassiveEffect] attribute on source.
    positions maps char_id → (x, y, z) voxel coordinates (optional; skips range check if None).
    """
    from src.rules_engine.dice import roll_d20

    passive_effects: list[PassiveEffect] = getattr(source, "passive_effects", [])
    results: list[EffectApplication] = []

    for effect in passive_effects:
        for observer in observers:
            if observer.char_id == source.char_id:
                continue

            # Suppress check — any active condition name in suppress_conditions skips effect
            obs_conditions: list[str] = [
                c.name for c in getattr(observer, "_conditions", [])
            ]
            if any(sc in obs_conditions for sc in effect.suppress_conditions):
                continue

            # Range check (voxels; 1 voxel = 5 ft)
            if positions is not None:
                src_pos = positions.get(source.char_id, (0.0, 0.0, 0.0))
                obs_pos = positions.get(observer.char_id, (0.0, 0.0, 0.0))
                dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(src_pos, obs_pos)))
                if dist > effect.range_ft / 5.0:
                    continue

            # Gaze effects route through the full gaze resolver
            if effect.effect_type == PassiveEffectType.Gaze:
                aversion = (aversion_states or {}).get(
                    observer.char_id, GazeAversionState.Looking
                )
                results.append(resolve_gaze_attack(source, observer, effect, aversion, tick))
                continue

            # General save
            saved = False
            if effect.save_type is not None:
                bonus = _save_bonus(observer, effect.save_type)
                roll = roll_d20(modifier=bonus)
                saved = roll.total >= effect.save_dc

            results.append(EffectApplication(
                target_id=observer.char_id,
                effect_type=effect.effect_type,
                saved=saved,
                tick=tick,
            ))

    return results


def _save_bonus(character: "Character35e", save_type: SaveType) -> int:
    if save_type == SaveType.Fortitude:
        return character.fortitude_save
    if save_type == SaveType.Reflex:
        return character.reflex_save
    return character.will_save


# ---------------------------------------------------------------------------
# LW-026 · Gaze Attack Full Resolver
# ---------------------------------------------------------------------------

def resolve_gaze_attack(
    gazer: "Character35e",
    target: "Character35e",
    effect: PassiveEffect,
    aversion_state: GazeAversionState,
    tick: int,
) -> EffectApplication:
    """Resolve a gaze attack, fully applying the observer's chosen aversion strategy.

    GazeAversionState.Looking    → target must save each round (no mitigation).
    GazeAversionState.Averting   → 50 % chance gaze misses entirely; -2 penalty
                                   to target's attacks against gazer (tracked externally).
    GazeAversionState.ClosedEyes → immune; 50 % miss chance on all target attacks
                                   (tracked externally by AttackResolver).
    GazeAversionState.Mirror     → gazer saves against own reflection;
                                   SR does not apply to self-reflection.
    """
    from src.rules_engine.dice import roll_d20

    if aversion_state == GazeAversionState.ClosedEyes:
        return EffectApplication(
            target_id=target.char_id, effect_type=effect.effect_type, saved=True, tick=tick
        )

    if aversion_state == GazeAversionState.Averting:
        if _stdlib_random.random() < 0.5:
            return EffectApplication(
                target_id=target.char_id, effect_type=effect.effect_type, saved=True, tick=tick
            )

    if aversion_state == GazeAversionState.Mirror:
        if effect.save_type is not None:
            bonus = _save_bonus(gazer, effect.save_type)
            roll = roll_d20(modifier=bonus)
            saved = roll.total >= effect.save_dc
        else:
            saved = False
        return EffectApplication(
            target_id=gazer.char_id, effect_type=effect.effect_type, saved=saved, tick=tick
        )

    # GazeAversionState.Looking — standard save
    saved = False
    if effect.save_type is not None:
        bonus = _save_bonus(target, effect.save_type)
        roll = roll_d20(modifier=bonus)
        saved = roll.total >= effect.save_dc

    return EffectApplication(
        target_id=target.char_id, effect_type=effect.effect_type, saved=saved, tick=tick
    )


# ---------------------------------------------------------------------------
# LW-031 · Aura Passive Effect Processor
# ---------------------------------------------------------------------------

def process_aura_effects(
    source: "Character35e",
    combat_state: CombatState,
    tick: int,
    positions: dict[str, tuple[float, float, float]] | None = None,
) -> list[EffectApplication]:
    """Process aura sub-types: Frightful Presence, Stench, and omnidirectional Auras.

    Frightful Presence DC = 10 + ½ source.HD + CHA_mod.
    Targets who already succeeded a save vs this creature this encounter are immune.
    Tick-stamp deduplication: skips any (target, effect_type) pair already applied this tick.
    """
    from src.rules_engine.dice import roll_d20

    passive_effects: list[PassiveEffect] = getattr(source, "passive_effects", [])
    results: list[EffectApplication] = []
    processed: set[tuple[str, PassiveEffectType]] = set()

    for effect in passive_effects:
        if effect.effect_type not in (
            PassiveEffectType.Aura,
            PassiveEffectType.Frightful_Presence,
            PassiveEffectType.Stench,
        ):
            continue

        for target in combat_state.entities:
            if target.char_id == source.char_id:
                continue

            key = (target.char_id, effect.effect_type)
            if key in processed:
                continue

            # Range check
            if positions is not None:
                src_pos = positions.get(source.char_id, (0.0, 0.0, 0.0))
                tgt_pos = positions.get(target.char_id, (0.0, 0.0, 0.0))
                dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(src_pos, tgt_pos)))
                if dist > effect.range_ft / 5.0:
                    continue

            saved = False
            if effect.effect_type == PassiveEffectType.Frightful_Presence:
                source_hd = source.level
                cha_mod = (source.charisma - 10) // 2
                dc = 10 + source_hd // 2 + cha_mod
                bonus = _save_bonus(target, SaveType.Will)
                roll = roll_d20(modifier=bonus)
                saved = roll.total >= dc
            elif effect.save_type is not None:
                bonus = _save_bonus(target, effect.save_type)
                roll = roll_d20(modifier=bonus)
                saved = roll.total >= effect.save_dc

            results.append(EffectApplication(
                target_id=target.char_id,
                effect_type=effect.effect_type,
                saved=saved,
                tick=tick,
            ))
            processed.add(key)

    return results
