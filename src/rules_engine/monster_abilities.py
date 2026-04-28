"""LW-MMF-002 — Monster Special Ability Callback Engine.

Registry and implementations for the top 20 most complex SRD 3.5e monster
abilities as registered callbacks with strictly computed save DCs.

Save DC formula (3.5e SRD universal):
    DC = 10 + ½ HD + relevant ability modifier

Trigger classification
~~~~~~~~~~~~~~~~~~~~~~
``AbilityTrigger.START_OF_TURN``
    Fired once per source entity at the start of its turn against every other
    combatant in range: breath weapons, mind blasts, fear auras, gazes.

``AbilityTrigger.AFTER_HIT``
    Fired immediately after a confirmed melee/touch hit lands on the target:
    energy drain, paralysis, disease, petrification, constrict, extraction.

Usage::

    from src.rules_engine.monster_abilities import (
        ABILITY_REGISTRY, AbilityTrigger, execute_ability,
        get_abilities_for_trigger,
    )

    vampire_cb = ABILITY_REGISTRY["vampire_energy_drain"]
    result = vampire_cb.callback(attacker, target, tick)
    print(result.effect_applied, result.damage)
"""
from __future__ import annotations

import enum
import random as _random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from src.rules_engine.character_35e import Character35e

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AbilityTrigger(enum.Enum):
    START_OF_TURN = "start_of_turn"
    AFTER_HIT     = "after_hit"


@dataclass(slots=True)
class AbilityResult:
    """Outcome of a single monster special ability application."""
    ability_name: str
    source_id: str
    target_id: str
    saved: bool
    effect_applied: str   # human-readable description of the applied effect
    damage: int           # hit-point damage dealt (0 for pure-condition effects)
    tick: int


AbilityCallback = Callable[["Character35e", "Character35e", int], AbilityResult]


@dataclass
class UniqueAbility:
    """Descriptor stored in ABILITY_REGISTRY for one monster special ability."""
    name: str
    trigger: AbilityTrigger
    callback: AbilityCallback
    description: str = ""


# ---------------------------------------------------------------------------
# Global registry
# ---------------------------------------------------------------------------

ABILITY_REGISTRY: dict[str, UniqueAbility] = {}


def _reg(ability: UniqueAbility) -> None:
    ABILITY_REGISTRY[ability.name] = ability


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _ab_mod(score: int) -> int:
    return (score - 10) // 2


def _dc(source: "Character35e", ability_score: int) -> int:
    """Universal 3.5e save-DC formula: 10 + ½ HD + relevant ability modifier."""
    return 10 + source.level // 2 + _ab_mod(ability_score)


def _roll20(bonus: int) -> int:
    from src.rules_engine.dice import roll_d20
    return roll_d20(modifier=bonus).total


def _dice(n: int, sides: int, bonus: int = 0) -> int:
    return sum(_random.randint(1, sides) for _ in range(n)) + bonus


# ============================================================================
# START_OF_TURN — breath weapons, auras, gazes, mind blasts
# ============================================================================

# ---------------------------------------------------------------------------
# 1. Red Dragon — Fire Breath (cone, Reflex half)
# ---------------------------------------------------------------------------
def _dragon_fire_breath(
    source: "Character35e", target: "Character35e", tick: int
) -> AbilityResult:
    dc = _dc(source, source.constitution)
    saved = _roll20(target.reflex_save) >= dc
    raw = _dice(max(1, source.level // 2), 8)
    dmg = raw // 2 if saved else raw
    return AbilityResult(
        ability_name="dragon_fire_breath",
        source_id=source.char_id, target_id=target.char_id,
        saved=saved,
        effect_applied=f"fire_damage_{dmg}",
        damage=dmg, tick=tick,
    )

_reg(UniqueAbility(
    name="dragon_fire_breath",
    trigger=AbilityTrigger.START_OF_TURN,
    callback=_dragon_fire_breath,
    description="Cone of fire. Reflex half. DC = 10 + ½HD + Con mod.",
))


# ---------------------------------------------------------------------------
# 2. White Dragon — Cold Breath (cone, Reflex half)
# ---------------------------------------------------------------------------
def _dragon_cold_breath(
    source: "Character35e", target: "Character35e", tick: int
) -> AbilityResult:
    dc = _dc(source, source.constitution)
    saved = _roll20(target.reflex_save) >= dc
    raw = _dice(max(1, source.level // 2), 8)
    dmg = raw // 2 if saved else raw
    return AbilityResult(
        ability_name="dragon_cold_breath",
        source_id=source.char_id, target_id=target.char_id,
        saved=saved,
        effect_applied=f"cold_damage_{dmg}",
        damage=dmg, tick=tick,
    )

_reg(UniqueAbility(
    name="dragon_cold_breath",
    trigger=AbilityTrigger.START_OF_TURN,
    callback=_dragon_cold_breath,
    description="Cone of cold. Reflex half. DC = 10 + ½HD + Con mod.",
))


# ---------------------------------------------------------------------------
# 3. Blue Dragon — Lightning Breath (line, Reflex half)
# ---------------------------------------------------------------------------
def _dragon_lightning_breath(
    source: "Character35e", target: "Character35e", tick: int
) -> AbilityResult:
    dc = _dc(source, source.constitution)
    saved = _roll20(target.reflex_save) >= dc
    raw = _dice(max(1, source.level // 2), 8)
    dmg = raw // 2 if saved else raw
    return AbilityResult(
        ability_name="dragon_lightning_breath",
        source_id=source.char_id, target_id=target.char_id,
        saved=saved,
        effect_applied=f"lightning_damage_{dmg}",
        damage=dmg, tick=tick,
    )

_reg(UniqueAbility(
    name="dragon_lightning_breath",
    trigger=AbilityTrigger.START_OF_TURN,
    callback=_dragon_lightning_breath,
    description="Line of lightning. Reflex half. DC = 10 + ½HD + Con mod.",
))


# ---------------------------------------------------------------------------
# 4. Black/Green Dragon — Acid Breath (line/cone, Reflex half)
# ---------------------------------------------------------------------------
def _dragon_acid_breath(
    source: "Character35e", target: "Character35e", tick: int
) -> AbilityResult:
    dc = _dc(source, source.constitution)
    saved = _roll20(target.reflex_save) >= dc
    raw = _dice(max(1, source.level // 2), 8)
    dmg = raw // 2 if saved else raw
    return AbilityResult(
        ability_name="dragon_acid_breath",
        source_id=source.char_id, target_id=target.char_id,
        saved=saved,
        effect_applied=f"acid_damage_{dmg}",
        damage=dmg, tick=tick,
    )

_reg(UniqueAbility(
    name="dragon_acid_breath",
    trigger=AbilityTrigger.START_OF_TURN,
    callback=_dragon_acid_breath,
    description="Acid line/cone. Reflex half. DC = 10 + ½HD + Con mod.",
))


# ---------------------------------------------------------------------------
# 5. Gorgon — Petrifying Breath (60-ft cone, Fort or flesh-to-stone)
# ---------------------------------------------------------------------------
def _gorgon_petrifying_breath(
    source: "Character35e", target: "Character35e", tick: int
) -> AbilityResult:
    dc = _dc(source, source.constitution)
    saved = _roll20(target.fortitude_save) >= dc
    effect = "no_effect" if saved else "flesh_to_stone"
    return AbilityResult(
        ability_name="gorgon_petrifying_breath",
        source_id=source.char_id, target_id=target.char_id,
        saved=saved,
        effect_applied=effect,
        damage=0, tick=tick,
    )

_reg(UniqueAbility(
    name="gorgon_petrifying_breath",
    trigger=AbilityTrigger.START_OF_TURN,
    callback=_gorgon_petrifying_breath,
    description="60-ft cone. Fort or flesh to stone. DC = 10 + ½HD + Con mod.",
))


# ---------------------------------------------------------------------------
# 6. Mind Flayer — Mind Blast (60-ft cone, Will or stunned 3d4 rounds)
# ---------------------------------------------------------------------------
def _mind_flayer_mind_blast(
    source: "Character35e", target: "Character35e", tick: int
) -> AbilityResult:
    dc = _dc(source, source.intelligence)
    saved = _roll20(target.will_save) >= dc
    stun_rounds = 0 if saved else _dice(3, 4)
    effect = "no_effect" if saved else f"stunned_{stun_rounds}_rounds"
    return AbilityResult(
        ability_name="mind_flayer_mind_blast",
        source_id=source.char_id, target_id=target.char_id,
        saved=saved,
        effect_applied=effect,
        damage=0, tick=tick,
    )

_reg(UniqueAbility(
    name="mind_flayer_mind_blast",
    trigger=AbilityTrigger.START_OF_TURN,
    callback=_mind_flayer_mind_blast,
    description="60-ft cone. Will or stunned 3d4 rounds. DC = 10 + ½HD + Int mod.",
))


# ---------------------------------------------------------------------------
# 7. Lich — Fear Aura (60-ft radius, Will or flee 1d4 rounds)
# ---------------------------------------------------------------------------
def _lich_fear_aura(
    source: "Character35e", target: "Character35e", tick: int
) -> AbilityResult:
    dc = _dc(source, source.charisma)
    saved = _roll20(target.will_save) >= dc
    flee_rounds = 0 if saved else _dice(1, 4)
    effect = "no_effect" if saved else f"fleeing_{flee_rounds}_rounds"
    return AbilityResult(
        ability_name="lich_fear_aura",
        source_id=source.char_id, target_id=target.char_id,
        saved=saved,
        effect_applied=effect,
        damage=0, tick=tick,
    )

_reg(UniqueAbility(
    name="lich_fear_aura",
    trigger=AbilityTrigger.START_OF_TURN,
    callback=_lich_fear_aura,
    description="60-ft radius. Will or flee 1d4 rounds. DC = 10 + ½HD + Cha mod.",
))


# ---------------------------------------------------------------------------
# 8. Pit Fiend — Fear Aura (20-ft radius, Will or panicked 1d4 rounds)
# ---------------------------------------------------------------------------
def _pit_fiend_fear_aura(
    source: "Character35e", target: "Character35e", tick: int
) -> AbilityResult:
    dc = _dc(source, source.charisma)
    saved = _roll20(target.will_save) >= dc
    panic_rounds = 0 if saved else _dice(1, 4)
    effect = "no_effect" if saved else f"panicked_{panic_rounds}_rounds"
    return AbilityResult(
        ability_name="pit_fiend_fear_aura",
        source_id=source.char_id, target_id=target.char_id,
        saved=saved,
        effect_applied=effect,
        damage=0, tick=tick,
    )

_reg(UniqueAbility(
    name="pit_fiend_fear_aura",
    trigger=AbilityTrigger.START_OF_TURN,
    callback=_pit_fiend_fear_aura,
    description="20-ft radius. Will or panicked 1d4 rounds. DC = 10 + ½HD + Cha mod.",
))


# ---------------------------------------------------------------------------
# 9. Medusa — Petrifying Gaze (30-ft, Fort or flesh-to-stone sequence)
#    Two-stage: fail first save → slowed 1 round; fail second save → stone.
# ---------------------------------------------------------------------------
def _medusa_petrifying_gaze(
    source: "Character35e", target: "Character35e", tick: int
) -> AbilityResult:
    dc = _dc(source, source.charisma)
    saved = _roll20(target.fortitude_save) >= dc
    if saved:
        effect = "no_effect"
    else:
        # Roll second Fort save: fail → stone; pass → slowed 1 round
        second_saved = _roll20(target.fortitude_save) >= dc
        effect = "slowed_1_round" if second_saved else "flesh_to_stone"
    return AbilityResult(
        ability_name="medusa_petrifying_gaze",
        source_id=source.char_id, target_id=target.char_id,
        saved=saved,
        effect_applied=effect,
        damage=0, tick=tick,
    )

_reg(UniqueAbility(
    name="medusa_petrifying_gaze",
    trigger=AbilityTrigger.START_OF_TURN,
    callback=_medusa_petrifying_gaze,
    description="30-ft gaze. Fort (Cha-based). Fail → slowed; fail again → flesh to stone.",
))


# ---------------------------------------------------------------------------
# 10. Aboleth — Enslave (30-ft, Will or dominated; Cha-based, 3 charges/day)
# ---------------------------------------------------------------------------
def _aboleth_enslave(
    source: "Character35e", target: "Character35e", tick: int
) -> AbilityResult:
    dc = _dc(source, source.charisma)
    saved = _roll20(target.will_save) >= dc
    effect = "no_effect" if saved else "dominated_permanent"
    return AbilityResult(
        ability_name="aboleth_enslave",
        source_id=source.char_id, target_id=target.char_id,
        saved=saved,
        effect_applied=effect,
        damage=0, tick=tick,
    )

_reg(UniqueAbility(
    name="aboleth_enslave",
    trigger=AbilityTrigger.START_OF_TURN,
    callback=_aboleth_enslave,
    description="30-ft. Will (Cha-based) or dominated. 3 uses per day.",
))


# ============================================================================
# AFTER_HIT — on-hit triggered effects
# ============================================================================

# ---------------------------------------------------------------------------
# 11. Vampire — Energy Drain (2 negative levels per hit; Cha-based Fort to recover)
# ---------------------------------------------------------------------------
def _vampire_energy_drain(
    source: "Character35e", target: "Character35e", tick: int
) -> AbilityResult:
    # Negative levels are automatically applied; Fort save 24h later to make permanent.
    # DC tracked here for the pending Fort save.
    dc = _dc(source, source.charisma)
    # No immediate save — negative levels are automatic. Effect string records the
    # pending Fort DC for the 24-hour check.
    return AbilityResult(
        ability_name="vampire_energy_drain",
        source_id=source.char_id, target_id=target.char_id,
        saved=False,
        effect_applied=f"negative_levels_2_pending_fort_dc_{dc}",
        damage=0, tick=tick,
    )

_reg(UniqueAbility(
    name="vampire_energy_drain",
    trigger=AbilityTrigger.AFTER_HIT,
    callback=_vampire_energy_drain,
    description="2 automatic negative levels. Fort DC (Cha-based) in 24h to remove.",
))


# ---------------------------------------------------------------------------
# 12. Lich — Paralyzing Touch (Fort or paralyzed 1d4+1 rounds; Cha-based)
# ---------------------------------------------------------------------------
def _lich_paralyzing_touch(
    source: "Character35e", target: "Character35e", tick: int
) -> AbilityResult:
    dc = _dc(source, source.charisma)
    saved = _roll20(target.fortitude_save) >= dc
    rounds = 0 if saved else _dice(1, 4, bonus=1)
    effect = "no_effect" if saved else f"paralyzed_{rounds}_rounds"
    return AbilityResult(
        ability_name="lich_paralyzing_touch",
        source_id=source.char_id, target_id=target.char_id,
        saved=saved,
        effect_applied=effect,
        damage=0, tick=tick,
    )

_reg(UniqueAbility(
    name="lich_paralyzing_touch",
    trigger=AbilityTrigger.AFTER_HIT,
    callback=_lich_paralyzing_touch,
    description="Fort (Cha-based) or paralyzed 1d4+1 rounds. DC = 10 + ½HD + Cha mod.",
))


# ---------------------------------------------------------------------------
# 13. Mummy — Mummy Rot (Fort or cursed + diseased: 1d6 Con/day; Cha-based)
# ---------------------------------------------------------------------------
def _mummy_mummy_rot(
    source: "Character35e", target: "Character35e", tick: int
) -> AbilityResult:
    dc = _dc(source, source.charisma)
    saved = _roll20(target.fortitude_save) >= dc
    effect = "no_effect" if saved else "mummy_rot_curse_and_disease"
    return AbilityResult(
        ability_name="mummy_mummy_rot",
        source_id=source.char_id, target_id=target.char_id,
        saved=saved,
        effect_applied=effect,
        damage=0, tick=tick,
    )

_reg(UniqueAbility(
    name="mummy_mummy_rot",
    trigger=AbilityTrigger.AFTER_HIT,
    callback=_mummy_mummy_rot,
    description="Fort (Cha-based) or mummy rot: curse + disease (1d6 Con damage/day).",
))


# ---------------------------------------------------------------------------
# 14. Wight — Energy Drain (1 negative level per hit; Cha-based Fort to recover)
# ---------------------------------------------------------------------------
def _wight_energy_drain(
    source: "Character35e", target: "Character35e", tick: int
) -> AbilityResult:
    dc = _dc(source, source.charisma)
    return AbilityResult(
        ability_name="wight_energy_drain",
        source_id=source.char_id, target_id=target.char_id,
        saved=False,
        effect_applied=f"negative_level_1_pending_fort_dc_{dc}",
        damage=0, tick=tick,
    )

_reg(UniqueAbility(
    name="wight_energy_drain",
    trigger=AbilityTrigger.AFTER_HIT,
    callback=_wight_energy_drain,
    description="1 automatic negative level. Fort DC (Cha-based) in 24h to remove.",
))


# ---------------------------------------------------------------------------
# 15. Ghoul — Paralysis (Fort or paralyzed 1d4+1 rounds; elves immune; Cha-based)
# ---------------------------------------------------------------------------
def _ghoul_paralysis(
    source: "Character35e", target: "Character35e", tick: int
) -> AbilityResult:
    # Elves are immune to ghoul paralysis per 3.5e SRD.
    elf_races = {"Elf", "Half-Elf", "elf", "half-elf"}
    target_race: str = getattr(target, "race", "")
    if target_race in elf_races:
        return AbilityResult(
            ability_name="ghoul_paralysis",
            source_id=source.char_id, target_id=target.char_id,
            saved=True,
            effect_applied="immune_elf",
            damage=0, tick=tick,
        )
    dc = _dc(source, source.charisma)
    saved = _roll20(target.fortitude_save) >= dc
    rounds = 0 if saved else _dice(1, 4, bonus=1)
    effect = "no_effect" if saved else f"paralyzed_{rounds}_rounds"
    return AbilityResult(
        ability_name="ghoul_paralysis",
        source_id=source.char_id, target_id=target.char_id,
        saved=saved,
        effect_applied=effect,
        damage=0, tick=tick,
    )

_reg(UniqueAbility(
    name="ghoul_paralysis",
    trigger=AbilityTrigger.AFTER_HIT,
    callback=_ghoul_paralysis,
    description="Fort (Cha-based) or paralyzed 1d4+1 rounds. Elves immune.",
))


# ---------------------------------------------------------------------------
# 16. Cockatrice — Petrify (Fort or flesh to stone; Con-based)
# ---------------------------------------------------------------------------
def _cockatrice_petrify(
    source: "Character35e", target: "Character35e", tick: int
) -> AbilityResult:
    dc = _dc(source, source.constitution)
    saved = _roll20(target.fortitude_save) >= dc
    effect = "no_effect" if saved else "flesh_to_stone"
    return AbilityResult(
        ability_name="cockatrice_petrify",
        source_id=source.char_id, target_id=target.char_id,
        saved=saved,
        effect_applied=effect,
        damage=0, tick=tick,
    )

_reg(UniqueAbility(
    name="cockatrice_petrify",
    trigger=AbilityTrigger.AFTER_HIT,
    callback=_cockatrice_petrify,
    description="Fort (Con-based) or flesh to stone. DC = 10 + ½HD + Con mod.",
))


# ---------------------------------------------------------------------------
# 17. Green Hag — Weakness (Fort or 2d4 Str damage; Cha-based supernatural)
# ---------------------------------------------------------------------------
def _green_hag_weakness(
    source: "Character35e", target: "Character35e", tick: int
) -> AbilityResult:
    dc = _dc(source, source.charisma)
    saved = _roll20(target.fortitude_save) >= dc
    str_damage = 0 if saved else _dice(2, 4)
    effect = "no_effect" if saved else f"str_damage_{str_damage}"
    return AbilityResult(
        ability_name="green_hag_weakness",
        source_id=source.char_id, target_id=target.char_id,
        saved=saved,
        effect_applied=effect,
        damage=0, tick=tick,
    )

_reg(UniqueAbility(
    name="green_hag_weakness",
    trigger=AbilityTrigger.AFTER_HIT,
    callback=_green_hag_weakness,
    description="Fort (Cha-based) or 2d4 Str damage. DC = 10 + ½HD + Cha mod.",
))


# ---------------------------------------------------------------------------
# 18. Aboleth — Slime (Fort or skin becomes transparent membrane; Con-based)
#     Membrane requires constant moisture; exposed target takes 1d12 Con/hour.
# ---------------------------------------------------------------------------
def _aboleth_slime(
    source: "Character35e", target: "Character35e", tick: int
) -> AbilityResult:
    dc = _dc(source, source.constitution)
    saved = _roll20(target.fortitude_save) >= dc
    effect = "no_effect" if saved else "skin_to_membrane_1d12_con_per_hour"
    return AbilityResult(
        ability_name="aboleth_slime",
        source_id=source.char_id, target_id=target.char_id,
        saved=saved,
        effect_applied=effect,
        damage=0, tick=tick,
    )

_reg(UniqueAbility(
    name="aboleth_slime",
    trigger=AbilityTrigger.AFTER_HIT,
    callback=_aboleth_slime,
    description="Fort (Con-based) or skin → transparent membrane. Dry air: 1d12 Con/hr.",
))


# ---------------------------------------------------------------------------
# 19. Mind Flayer — Extract (after successful grapple pin: instant kill)
#     Requires prior grapple; treated here as a guaranteed death effect
#     gated on a Fortitude save (no spell resistance).
# ---------------------------------------------------------------------------
def _mind_flayer_extract(
    source: "Character35e", target: "Character35e", tick: int
) -> AbilityResult:
    # Only triggers when the Mind Flayer has the target pinned (grapple assumed
    # checked by the caller). Fort DC vs death; no spell resistance applies.
    dc = _dc(source, source.intelligence)
    saved = _roll20(target.fortitude_save) >= dc
    effect = "no_effect" if saved else "brain_extracted_instant_death"
    return AbilityResult(
        ability_name="mind_flayer_extract",
        source_id=source.char_id, target_id=target.char_id,
        saved=saved,
        effect_applied=effect,
        damage=0, tick=tick,
    )

_reg(UniqueAbility(
    name="mind_flayer_extract",
    trigger=AbilityTrigger.AFTER_HIT,
    callback=_mind_flayer_extract,
    description="Requires pin. Fort (Int-based) or instant death (brain extraction).",
))


# ---------------------------------------------------------------------------
# 20. Night Hag — Dream Haunting (after sleep-state contact, ongoing)
#     Targets a sleeping humanoid; no save against initiation.
#     Each night of haunting deals 1d4 Wis drain (Fort DC (Cha-based) each night).
# ---------------------------------------------------------------------------
def _night_hag_dream_haunting(
    source: "Character35e", target: "Character35e", tick: int
) -> AbilityResult:
    dc = _dc(source, source.charisma)
    saved = _roll20(target.fortitude_save) >= dc
    wis_drain = 0 if saved else _dice(1, 4)
    effect = "no_effect" if saved else f"wis_drain_{wis_drain}"
    return AbilityResult(
        ability_name="night_hag_dream_haunting",
        source_id=source.char_id, target_id=target.char_id,
        saved=saved,
        effect_applied=effect,
        damage=0, tick=tick,
    )

_reg(UniqueAbility(
    name="night_hag_dream_haunting",
    trigger=AbilityTrigger.AFTER_HIT,
    callback=_night_hag_dream_haunting,
    description="Fort (Cha-based) or 1d4 Wis drain per night of haunting.",
))


# ============================================================================
# Public API
# ============================================================================

def execute_ability(
    ability_name: str,
    source: "Character35e",
    target: "Character35e",
    tick: int,
) -> AbilityResult | None:
    """Execute a registered ability by name; returns None if not found."""
    ability = ABILITY_REGISTRY.get(ability_name)
    if ability is None:
        return None
    return ability.callback(source, target, tick)


def get_abilities_for_trigger(
    ability_names: list[str],
    trigger: AbilityTrigger,
) -> list[UniqueAbility]:
    """Filter a list of ability names to those with the given trigger."""
    return [
        ABILITY_REGISTRY[n]
        for n in ability_names
        if n in ABILITY_REGISTRY and ABILITY_REGISTRY[n].trigger == trigger
    ]
