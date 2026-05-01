"""
src/game/session.py
-------------------
High-level play session — wires the :class:`~src.game.turn_controller.TurnController`
into the existing combat resolver and prints a running narrative.

Design (Task 5)
~~~~~~~~~~~~~~~
* Build monster stat blocks from a blueprint returned by
  :func:`~src.rules_engine.encounter_extended.build_encounter`.
* Create a ``current_hp`` entry in each combatant's ``metadata`` so we can
  track death without mutating the derived :attr:`Character35e.hit_points`
  property.
* Attach an :class:`~src.core.event_bus.EventBus` so combat publishes
  ``attack_resolved`` / ``combatant_defeated`` events that the CLI
  subscribes to for narration.
* On each turn, the default AI simply full-attacks the nearest living
  opposing combatant (this is a *playability* milestone, not a tactical
  AI milestone).
* Exit the loop when one side is wiped, the combatant list flees, or the
  safety cap on rounds is reached.
"""

from __future__ import annotations

import random
import re
import sys
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, TextIO, Tuple

from src.core.event_bus import EventBus
from src.game.turn_controller import TurnController
from src.rules_engine.actions import ActionTracker, ActionType
from src.rules_engine.character_35e import Alignment, Character35e, Size
from src.rules_engine.combat import AttackResolver, CombatResult
from src.rules_engine.conditions import Condition, ConditionManager
from src.rules_engine.encounter import distribute_xp
from src.rules_engine.encounter_extended import (
    EncounterBlueprint,
    EncounterDifficulty,
    build_encounter,
)
from src.rules_engine.magic import create_default_registry
from src.rules_engine.progression import XPManager
from src.rules_engine.spell_effects import SpellDispatcher, SpellResult
from src.rules_engine.spellcasting import SpellResolver, get_key_ability
from src.rules_engine.treasure import (
    TreasureHoard,
    generate_treasure_hoard,
    _cr_to_treasure_letter,
)


# ---------------------------------------------------------------------------
# Combatant bookkeeping
# ---------------------------------------------------------------------------

HP_KEY = "current_hp"
SIDE_KEY = "side"          # "party" or "enemy"
DEAD_KEY = "dead"


def _ensure_hp(character: Character35e) -> None:
    """Ensure ``metadata['current_hp']`` is initialised to max HP."""
    if HP_KEY not in character.metadata:
        character.metadata[HP_KEY] = character.hit_points
    character.metadata.setdefault(DEAD_KEY, False)


def current_hp(character: Character35e) -> int:
    """Return the combatant's current hit points (initialises if missing)."""
    _ensure_hp(character)
    return int(character.metadata[HP_KEY])


def apply_damage(character: Character35e, amount: int) -> int:
    """Reduce *character*'s ``current_hp`` by *amount* (floored at −10).

    Returns the remaining hit points.
    """
    _ensure_hp(character)
    new_hp = int(character.metadata[HP_KEY]) - max(0, amount)
    new_hp = max(-10, new_hp)
    character.metadata[HP_KEY] = new_hp
    if new_hp <= 0:
        character.metadata[DEAD_KEY] = True
    return new_hp


def is_alive(character: Character35e) -> bool:
    """Return ``True`` if *character* is still combat-capable."""
    _ensure_hp(character)
    return current_hp(character) > 0 and not character.metadata.get(DEAD_KEY, False)


# ---------------------------------------------------------------------------
# SRD Monster index (loaded lazily, cached for the process lifetime)
# ---------------------------------------------------------------------------

_MONSTER_INDEX: Dict[str, dict] = {}
_MONSTER_INDEX_BUILT = False

_SRD_SIZE_MAP: Dict[str, Size] = {
    "fine": Size.FINE,
    "diminutive": Size.DIMINUTIVE if hasattr(Size, "DIMINUTIVE") else Size.TINY,
    "tiny": Size.TINY,
    "small": Size.SMALL,
    "medium": Size.MEDIUM,
    "large": Size.LARGE,
    "huge": Size.HUGE,
    "gargantuan": Size.GARGANTUAN,
    "colossal": Size.COLOSSAL,
}

_ALIGNMENT_MAP: Dict[str, Alignment] = {
    "lawful good": Alignment.LAWFUL_GOOD,
    "neutral good": Alignment.NEUTRAL_GOOD,
    "chaotic good": Alignment.CHAOTIC_GOOD,
    "lawful neutral": Alignment.LAWFUL_NEUTRAL,
    "true neutral": Alignment.TRUE_NEUTRAL,
    "neutral": Alignment.TRUE_NEUTRAL,
    "chaotic neutral": Alignment.CHAOTIC_NEUTRAL,
    "lawful evil": Alignment.LAWFUL_EVIL,
    "neutral evil": Alignment.NEUTRAL_EVIL,
    "chaotic evil": Alignment.CHAOTIC_EVIL,
}


def _normalize_name(name: str) -> str:
    """Lowercase, strip punctuation, collapse spaces for index lookups."""
    return re.sub(r"[^a-z0-9 ]", "", name.lower()).strip()


def _build_monster_index() -> None:
    global _MONSTER_INDEX, _MONSTER_INDEX_BUILT
    if _MONSTER_INDEX_BUILT:
        return
    from src.rules_engine.srd_loader import load_monsters
    for entry in load_monsters():
        key = _normalize_name(entry.get("name", ""))
        if key:
            _MONSTER_INDEX[key] = entry
    _MONSTER_INDEX_BUILT = True


def _parse_alignment(raw: str) -> Alignment:
    for segment in raw.lower().split(","):
        segment = segment.strip()
        for key, alignment in _ALIGNMENT_MAP.items():
            if key in segment:
                return alignment
    return Alignment.TRUE_NEUTRAL


def _monster_from_srd(entry: dict, display_name: str) -> Character35e:
    """Build a Character35e from an SRD monster JSON entry."""
    abilities = entry.get("abilities", {})
    str_ = int(abilities.get("str", 10))
    dex = int(abilities.get("dex", 10))
    con = int(abilities.get("con", 10))
    int_ = int(abilities.get("int", 10))
    wis = int(abilities.get("wis", 10))
    cha = int(abilities.get("cha", 10))

    size_str = entry.get("size", "Medium").split()[0].lower()
    size = _SRD_SIZE_MAP.get(size_str, Size.MEDIUM)

    alignment = _parse_alignment(entry.get("alignment", "Neutral"))

    base_attack = int(entry.get("base_attack", 1))
    level = max(1, base_attack)

    speed_data = entry.get("speed", {})
    base_speed = int(speed_data.get("land", 30)) if isinstance(speed_data, dict) else 30

    monster = Character35e(
        name=display_name,
        char_class="Fighter",
        level=level,
        race=entry.get("type", "Humanoid"),
        alignment=alignment,
        size=size,
        strength=str_,
        dexterity=dex,
        constitution=con,
        intelligence=int_,
        wisdom=wis,
        charisma=cha,
        base_speed=base_speed,
    )

    hp_avg = int(entry.get("hp_avg", monster.hit_points))
    monster.metadata[HP_KEY] = hp_avg

    dex_mod = (dex - 10) // 2
    srd_ac = int(entry.get("armor_class", {}).get("total", 10))
    natural_armor = max(0, srd_ac - (10 + dex_mod + size.value))
    monster.metadata["natural_armor_bonus"] = natural_armor
    monster.metadata[DEAD_KEY] = False

    return monster


def build_monsters_from_srd(
    blueprint: EncounterBlueprint,
    rng: Optional[random.Random] = None,
) -> List[Character35e]:
    """Build monster combatants using SRD stat blocks where available.

    Looks up each monster by name in the loaded SRD index.  Falls back to
    the Fighter-approximation path when a name is not found.
    """
    _build_monster_index()
    monsters: List[Character35e] = []
    for name, count, cr in blueprint.monsters:
        key = _normalize_name(name)
        entry = _MONSTER_INDEX.get(key)
        for idx in range(count):
            display = f"{name} #{idx + 1}" if count > 1 else name
            if entry is not None:
                mon = _monster_from_srd(entry, display)
            else:
                level = max(1, int(round(cr)))
                mon = Character35e(
                    name=display,
                    char_class="Fighter",
                    level=level,
                    race="Human",
                    alignment=Alignment.CHAOTIC_EVIL,
                    size=Size.MEDIUM,
                    strength=12 + min(4, level),
                    dexterity=12,
                    constitution=12 + min(4, level),
                    intelligence=8,
                    wisdom=10,
                    charisma=8,
                )
            mon.metadata[SIDE_KEY] = "enemy"
            mon.metadata["cr"] = cr
            monsters.append(mon)
    return monsters


# ---------------------------------------------------------------------------
# Long rest / party rest
# ---------------------------------------------------------------------------

def long_rest(character: Character35e) -> int:
    """Apply an 8-hour long rest to *character*.

    Recovers all expended spell slots and restores hit points equal to the
    character's level (natural healing per the 3.5e SRD).  HP is clamped
    to the character's maximum.

    Args:
        character: The character to rest.

    Returns:
        Number of hit points actually restored.
    """
    ssm = character.spell_slot_manager
    if ssm is not None:
        ssm.rest()

    max_hp = character.hit_points
    current = int(character.metadata.get(HP_KEY, max_hp))
    healed = character.level
    new_hp = min(max_hp, current + healed)
    character.metadata[HP_KEY] = new_hp
    character.metadata[DEAD_KEY] = new_hp <= 0
    return new_hp - current


def rest_party(party: Sequence[Character35e]) -> Dict[str, int]:
    """Apply a long rest to every member of *party*.

    Args:
        party: Iterable of characters to rest.

    Returns:
        Mapping of ``char_id → hp_restored``.
    """
    return {c.char_id: long_rest(c) for c in party}


# ---------------------------------------------------------------------------
# Monster factory (legacy — kept for backward compatibility)
# ---------------------------------------------------------------------------

def build_monsters_from_blueprint(
    blueprint: EncounterBlueprint,
) -> List[Character35e]:
    """Instantiate Fighter-approximation stand-ins for the blueprint.

    .. deprecated::
        Use :func:`build_monsters_from_srd` which loads real SRD stat blocks.
    """
    monsters: List[Character35e] = []
    for name, count, cr in blueprint.monsters:
        level = max(1, int(round(cr)))
        for idx in range(count):
            mon = Character35e(
                name=f"{name} #{idx + 1}" if count > 1 else name,
                char_class="Fighter",
                level=level,
                race="Human",
                alignment=Alignment.CHAOTIC_EVIL,
                size=Size.MEDIUM,
                strength=12 + min(4, level),
                dexterity=12,
                constitution=12 + min(4, level),
                intelligence=8,
                wisdom=10,
                charisma=8,
            )
            mon.metadata[SIDE_KEY] = "enemy"
            mon.metadata["cr"] = cr
            monsters.append(mon)
    return monsters


# ---------------------------------------------------------------------------
# Session report
# ---------------------------------------------------------------------------

@dataclass
class SessionReport:
    """Outcome of a single play session.

    Attributes:
        outcome:           ``"victory"``, ``"defeat"``, or ``"stalemate"``.
        rounds:            Number of combat rounds that elapsed.
        blueprint:         The encounter blueprint used.
        xp_awarded:        Mapping ``char_id → XP`` awarded.
        treasure:          Generated :class:`TreasureHoard` (empty on defeat).
        survivors:         List of still-alive party members at end of combat.
        casualties:        List of defeated party members.
        log:               Chronological list of human-readable log lines.
    """

    outcome: str
    rounds: int
    blueprint: EncounterBlueprint
    xp_awarded: Dict[str, int] = field(default_factory=dict)
    treasure: Optional[TreasureHoard] = None
    survivors: List[Character35e] = field(default_factory=list)
    casualties: List[Character35e] = field(default_factory=list)
    log: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Default target selection + attack action
# ---------------------------------------------------------------------------

def _pick_target(
    attacker: Character35e,
    combatants: Sequence[Character35e],
) -> Optional[Character35e]:
    """Pick the first living opposite-side combatant as the target."""
    attacker_side = attacker.metadata.get(SIDE_KEY, "party")
    for c in combatants:
        if c is attacker:
            continue
        if not is_alive(c):
            continue
        if c.metadata.get(SIDE_KEY) != attacker_side:
            return c
    return None


def _weapon_damage_dice(character: Character35e) -> Tuple[int, int]:
    """Return ``(count, sides)`` for this character's main-hand weapon.

    Falls back to unarmed (handled by :class:`AttackResolver` → 1d3) when
    no :class:`EquipmentManager` is attached.
    """
    if character.equipment_manager is not None:
        count, sides = character.equipment_manager.get_weapon_damage_dice()
        if count > 0 and sides > 0:
            return count, sides
    return 0, 0


# ---------------------------------------------------------------------------
# play_session — the end-to-end glue
# ---------------------------------------------------------------------------

def play_session(
    party: Sequence[Character35e],
    *,
    apl: int,
    terrain: str,
    difficulty: str = "average",
    rng: Optional[random.Random] = None,
    max_rounds: int = 20,
    stdout: Optional[TextIO] = None,
    blueprint: Optional[EncounterBlueprint] = None,
) -> SessionReport:
    """Run a full party-vs-encounter session.

    Args:
        party:       Pre-built list of player :class:`Character35e`.
        apl:         Average party level.
        terrain:     Terrain key (e.g. ``"dungeon"``).
        difficulty:  One of ``easy|average|challenging|hard|overwhelming``.
        rng:         RNG for determinism.
        max_rounds:  Hard cap on rounds to prevent infinite loops.
        stdout:      Optional output stream for narration (defaults to
                     :data:`sys.stdout`).  Pass ``None`` → stdout; pass
                     ``open(os.devnull, "w")`` to silence.
        blueprint:   Optionally pre-computed encounter blueprint; when
                     ``None`` one is built from the APL/terrain inputs.

    Returns:
        A :class:`SessionReport`.
    """
    out = stdout if stdout is not None else sys.stdout
    rng = rng or random.Random()

    if blueprint is None:
        blueprint = build_encounter(
            apl, EncounterDifficulty(difficulty), terrain, rng
        )

    monsters = build_monsters_from_srd(blueprint, rng)
    for pc in party:
        _ensure_hp(pc)
        pc.metadata.setdefault(SIDE_KEY, "party")
    for m in monsters:
        _ensure_hp(m)

    combatants: List[Character35e] = list(party) + list(monsters)

    event_bus = EventBus()
    conditions = ConditionManager(event_bus=event_bus)
    spell_registry = create_default_registry()
    log: List[str] = []

    def _log(msg: str) -> None:
        log.append(msg)
        print(msg, file=out)

    def _on_turn_start(payload):
        _log(
            f"  -- {payload['name']} (round {payload['round']}, "
            f"init {payload['initiative']}) --"
        )

    event_bus.subscribe("turn_started", _on_turn_start)

    controller = TurnController.from_combatants(
        combatants,
        rng=rng,
        condition_manager=conditions,
        event_bus=event_bus,
    )

    _log("=" * 60)
    _log(f"Encounter EL {blueprint.actual_el} — {difficulty} @ {terrain}")
    for name, count, cr in blueprint.monsters:
        _log(f"  • {count}× {name} (CR {cr})")
    _log("Initiative order:")
    for entry in controller.order:
        side = entry.combatant.metadata.get(SIDE_KEY, "?")
        _log(
            f"  {entry.initiative:>3}  {entry.combatant.name} ({side}, "
            f"{entry.combatant.char_class} L{entry.combatant.level})"
        )
    _log("=" * 60)

    def _try_cast_spell(attacker: Character35e, target: Character35e) -> bool:
        """Attempt to cast the best available spell. Returns True if cast."""
        if not attacker.is_caster:
            return False
        ssm = attacker.spell_slot_manager
        if ssm is None or ssm.total_available() == 0:
            return False

        # Clerics heal a badly-wounded ally instead of attacking
        targeting_ally = False
        heal_target = target
        if attacker.char_class == "Cleric":
            attacker_side = attacker.metadata.get(SIDE_KEY, "party")
            for c in combatants:
                if (
                    c is not attacker
                    and is_alive(c)
                    and c.metadata.get(SIDE_KEY) == attacker_side
                    and current_hp(c) < c.hit_points // 2
                ):
                    heal_target = c
                    targeting_ally = True
                    break

        spell_name = SpellDispatcher.best_offensive_spell(
            attacker, spell_registry, targeting_ally=targeting_ally
        )
        if spell_name is None:
            return False

        # Compute save DC from the spell's level and caster's key ability
        from src.rules_engine.magic import create_default_registry as _reg
        spell = spell_registry.get(spell_name)
        if spell is None:
            return False

        key_ability = get_key_ability(attacker.char_class) if attacker.is_caster else "intelligence"
        ability_score = getattr(attacker, key_ability, 10)
        ability_mod = (ability_score - 10) // 2
        save_dc = 10 + spell.level + ability_mod

        actual_target = heal_target if targeting_ally else target
        result = SpellDispatcher.dispatch(
            spell_name,
            caster=attacker,
            target=actual_target,
            caster_level=attacker.caster_level,
            registry=spell_registry,
            rng=rng,
            save_dc=save_dc,
        )

        # Expend the slot
        ssm.expend(spell.level)

        # Apply mechanical outcomes
        if result.damage_dealt > 0:
            remaining = apply_damage(actual_target, result.damage_dealt)
            _log(f"    {result.narrative}  [{actual_target.name} HP: {remaining}]")
            event_bus.publish("spell_resolved", {
                "caster": attacker.char_id,
                "target": actual_target.char_id,
                "spell": spell_name,
                "damage": result.damage_dealt,
            })
            if remaining <= 0:
                _log(f"    {actual_target.name} is defeated!")
                event_bus.publish("combatant_defeated", {
                    "char_id": actual_target.char_id,
                    "name": actual_target.name,
                })
        elif result.healing_done > 0:
            _ensure_hp(actual_target)
            new_hp = min(
                current_hp(actual_target) + result.healing_done,
                actual_target.hit_points,
            )
            actual_target.metadata[HP_KEY] = new_hp
            _log(f"    {result.narrative}  [{actual_target.name} HP: {new_hp}]")
        elif result.conditions_applied:
            for cond_name in result.conditions_applied:
                duration = int(result.raw_effect.get("duration_rounds", attacker.caster_level))
                cond = Condition(
                    name=cond_name,
                    duration=duration,
                    cannot_act=(cond_name.lower() in ("unconscious", "paralyzed", "stunned")),
                )
                conditions.apply_condition(actual_target, cond)
            _log(f"    {result.narrative}")
        else:
            _log(f"    {result.narrative}")

        return True

    def _attack_action(
        attacker: Character35e, tracker: ActionTracker
    ) -> bool:
        if not is_alive(attacker):
            return False
        target = _pick_target(attacker, combatants)
        if target is None:
            return True  # nothing to fight — end the round early
        if not tracker.has_action(ActionType.STANDARD):
            return False
        tracker.consume_action(ActionType.STANDARD)

        # Casters try to cast before falling back to weapon attacks
        if _try_cast_spell(attacker, target):
            return False

        dice_count, dice_sides = _weapon_damage_dice(attacker)
        results = AttackResolver.resolve_full_attack(
            attacker,
            target,
            damage_dice_count=dice_count,
            damage_dice_sides=dice_sides,
        )
        for result in results:
            event_bus.publish("attack_resolved", {
                "attacker": attacker.char_id,
                "defender": target.char_id,
                "hit": result.hit,
                "damage": result.total_damage,
                "critical": result.critical,
            })
            if result.hit:
                remaining = apply_damage(target, result.total_damage)
                crit = " (CRITICAL!)" if result.critical else ""
                _log(
                    f"    {attacker.name} hits {target.name} for "
                    f"{result.total_damage} damage{crit}  [{target.name} HP: "
                    f"{remaining}]"
                )
                if remaining <= 0:
                    _log(f"    {target.name} is defeated!")
                    event_bus.publish("combatant_defeated", {
                        "char_id": target.char_id,
                        "name": target.name,
                    })
                    break
            else:
                _log(
                    f"    {attacker.name} misses {target.name} "
                    f"(rolled {result.roll.total} vs AC {result.target_ac})"
                )
        return False

    # --- Main combat loop -------------------------------------------------
    outcome = "stalemate"
    for _ in range(max_rounds):
        controller.run_round(_attack_action)
        party_alive = any(is_alive(c) for c in party)
        enemies_alive = any(is_alive(m) for m in monsters)
        if not enemies_alive and party_alive:
            outcome = "victory"
            break
        if not party_alive:
            outcome = "defeat"
            break
        if not enemies_alive and not party_alive:
            outcome = "mutual"
            break

    # --- XP + treasure ----------------------------------------------------
    xp_awarded: Dict[str, int] = {}
    treasure: Optional[TreasureHoard] = None
    if outcome == "victory":
        awards = distribute_xp(
            blueprint.actual_el,
            [c.level for c in party],
        )
        for idx, pc in enumerate(party):
            xp_awarded[pc.char_id] = awards.get(idx, 0)
            _log(f"  XP awarded to {pc.name}: {awards.get(idx, 0)}")
        treasure = generate_treasure_hoard(blueprint.actual_el, rng=rng)
        _log(
            f"  Treasure (type {_cr_to_treasure_letter(blueprint.actual_el)}):"
            f" {treasure.total_value_gp:.0f} gp value"
        )

    survivors = [c for c in party if is_alive(c)]
    casualties = [c for c in party if not is_alive(c)]

    return SessionReport(
        outcome=outcome,
        rounds=controller.round_counter,
        blueprint=blueprint,
        xp_awarded=xp_awarded,
        treasure=treasure,
        survivors=survivors,
        casualties=casualties,
        log=log,
    )
