"""
src/rules_engine/spell_effects.py
----------------------------------
Spell effect dispatcher: bridges the per-spell effect_callback dicts
returned by :mod:`src.rules_engine.magic` into concrete mechanical
outcomes — rolled damage, applied healing, applied conditions, etc.

The callbacks in ``magic.py`` deliberately return *descriptive* dicts
(e.g. ``{"damage": "6d6", "save": "Reflex half"}``); this module is
the only place that actually *rolls* the dice and *mutates* combatant
state so that responsibility stays out of the data layer.

Usage::

    from src.rules_engine.spell_effects import SpellDispatcher, SpellResult
    from src.rules_engine.magic import create_default_registry
    import random

    registry = create_default_registry()
    rng = random.Random()
    result = SpellDispatcher.dispatch(
        "Magic Missile", caster=wizard, target=goblin,
        caster_level=5, registry=registry, rng=rng,
    )
    if result.damage_dealt:
        apply_damage(goblin, result.damage_dealt)
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.rules_engine.dice import roll_damage, roll_d20
from src.rules_engine.magic import SpellRegistry


# ---------------------------------------------------------------------------
# SpellResult
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class SpellResult:
    """Outcome of a single spell dispatch.

    Attributes:
        spell_name:      The spell that was cast.
        outcome:         One of ``"damage"``, ``"healing"``, ``"condition"``,
                         ``"buff"``, ``"utility"``.
        damage_dealt:    Total HP lost by the primary target (0 if none).
        healing_done:    Total HP restored (0 if none).
        conditions_applied: Names of conditions applied to the target.
        saved:           Whether the target made their saving throw.
        narrative:       Human-readable one-line description of what happened.
        raw_effect:      The unmodified dict from the effect_callback.
    """

    spell_name: str
    outcome: str = "utility"
    damage_dealt: int = 0
    healing_done: int = 0
    conditions_applied: List[str] = field(default_factory=list)
    saved: bool = False
    narrative: str = ""
    raw_effect: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DICE_RE = re.compile(r"^(?P<count>\d+)[dD](?P<sides>\d+)(?:\s*[+-]\s*\d+)?$")


def _roll_expr(expression: str, rng: Optional[random.Random] = None) -> int:
    """Roll a dice expression using the shared rng if provided."""
    if rng is not None:
        old_state = random.getstate()
        random.setstate(rng.getstate())
        result = roll_damage(expression).total
        rng.setstate(random.getstate())
        random.setstate(old_state)
    else:
        result = roll_damage(expression).total
    return max(0, result)


def _saving_throw(
    save_type: str,
    target: Any,
    dc: int,
    rng: Optional[random.Random] = None,
) -> bool:
    """Roll a saving throw for *target* against *dc*.

    Returns ``True`` if the target *succeeds* (saves).
    """
    rng = rng or random.Random()
    roll = rng.randint(1, 20)
    save_mod = 0
    label = save_type.lower()
    if "reflex" in label:
        save_mod = getattr(target, "reflex_save", 0)
    elif "will" in label:
        save_mod = getattr(target, "will_save", 0)
    elif "fortitude" in label:
        save_mod = getattr(target, "fortitude_save", 0)
    if roll == 1: return False
    if roll == 20: return True
    return (roll + save_mod) >= dc


def _target_level(target: Any) -> int:
    """Best-effort HD/level for save-immunity checks."""
    return int(getattr(target, "level", 1) or 1)


# ---------------------------------------------------------------------------
# SpellDispatcher
# ---------------------------------------------------------------------------

class SpellDispatcher:
    """Resolves spells from the SRD registry into concrete mechanical outcomes.

    All methods are class-methods; no instance state is needed.
    """

    # Offensive spells ranked by priority within each class; used by the
    # combat AI to pick the "best" spell to cast in a turn.
    OFFENSIVE_PRIORITY: Dict[str, List[str]] = {
        "Wizard": [
            "Fireball", "Lightning Bolt", "Cone of Cold", "Ice Storm",
            "Scorching Ray", "Burning Hands", "Magic Missile",
            "Sleep", "Hold Person", "Color Spray",
        ],
        "Sorcerer": [
            "Fireball", "Lightning Bolt", "Scorching Ray",
            "Magic Missile", "Sleep", "Color Spray",
        ],
        "Cleric": [
            "Bless", "Bane",
            "Hold Person", "Cause Fear",
        ],
        "Druid": [
            "Summon Nature's Ally I", "Burning Hands", "Cause Fear",
        ],
        "Bard": [
            "Sleep", "Cause Fear", "Color Spray",
        ],
    }

    # Healing spells (used by cleric AI)
    HEALING_SPELLS: List[str] = [
        "Cure Light Wounds", "Cure Moderate Wounds",
        "Cure Serious Wounds", "Cure Critical Wounds",
    ]

    @classmethod
    def dispatch(
        cls,
        spell_name: str,
        *,
        caster: Any,
        target: Any,
        caster_level: int,
        registry: SpellRegistry,
        rng: Optional[random.Random] = None,
        save_dc: int = 14,
    ) -> SpellResult:
        """Execute *spell_name* from *caster* against *target*.

        Args:
            spell_name:    Name of the spell to cast.
            caster:        The casting :class:`~src.rules_engine.character_35e.Character35e`.
            target:        The target character (may be the same as caster for self-buffs).
            caster_level:  Effective caster level for scaling.
            registry:      Populated :class:`SpellRegistry` to look up the spell.
            rng:           RNG for determinism.
            save_dc:       The spell's save DC (10 + spell_level + ability_mod).

        Returns:
            A :class:`SpellResult` describing what happened.
        """
        rng = rng or random.Random()
        spell = registry.get(spell_name)
        if spell is None or spell.effect_callback is None:
            return SpellResult(
                spell_name=spell_name,
                outcome="utility",
                narrative=f"{spell_name} had no resolvable effect.",
            )

        effect = spell.effect_callback(caster, target, caster_level)
        if not effect:
            return SpellResult(spell_name=spell_name, outcome="utility",
                               raw_effect={}, narrative=f"{spell_name} was cast.")

        return cls._resolve_effect(
            spell_name=spell_name,
            effect=effect,
            caster=caster,
            target=target,
            caster_level=caster_level,
            save_dc=save_dc,
            rng=rng,
        )

    @classmethod
    def _resolve_effect(
        cls,
        spell_name: str,
        effect: Dict[str, Any],
        caster: Any,
        target: Any,
        caster_level: int,
        save_dc: int,
        rng: random.Random,
    ) -> SpellResult:
        caster_name = getattr(caster, "name", "Caster")
        target_name = getattr(target, "name", "Target")

        # --- Magic Missile (auto-hit, multiple missiles) ---
        if effect.get("auto_hit") and "damage_per_missile" in effect:
            expr = effect["damage_per_missile"]
            num = int(effect.get("num_missiles", 1))
            total = sum(max(1, _roll_expr(expr, rng)) for _ in range(num))
            return SpellResult(
                spell_name=spell_name,
                outcome="damage",
                damage_dealt=total,
                raw_effect=effect,
                narrative=(
                    f"{caster_name} launches {num} Magic Missile(s) at "
                    f"{target_name} for {total} force damage."
                ),
            )

        # --- Standard damage spell (damage key, optional Reflex save) ---
        if "damage" in effect and _DICE_RE.match(str(effect["damage"])):
            rolled = _roll_expr(str(effect["damage"]), rng)
            save_spec: str = str(effect.get("save", ""))
            saved = False
            if save_spec:
                saved = _saving_throw(save_spec, target, save_dc, rng)
            final_dmg = (rolled // 2) if (saved and "half" in save_spec.lower()) else rolled
            dmg_type = effect.get("damage_type", "")
            save_note = f" ({target_name} saved, half damage)" if saved else ""
            return SpellResult(
                spell_name=spell_name,
                outcome="damage",
                damage_dealt=final_dmg,
                saved=saved,
                raw_effect=effect,
                narrative=(
                    f"{caster_name} casts {spell_name} dealing {final_dmg} "
                    f"{dmg_type} damage to {target_name}{save_note}."
                ),
            )

        # --- Healing spell ---
        if "healing" in effect:
            rolled = max(1, _roll_expr(str(effect["healing"]), rng))
            return SpellResult(
                spell_name=spell_name,
                outcome="healing",
                healing_done=rolled,
                raw_effect=effect,
                narrative=(
                    f"{caster_name} casts {spell_name} on {target_name}, "
                    f"restoring {rolled} HP."
                ),
            )

        # --- Condition spell (Sleep, Hold Person, Cause Fear, etc.) ---
        if "condition" in effect or "hit_dice_affected" in effect:
            condition_name = str(
                effect.get("condition") or effect.get("immune", ["unknown"])[0]
            )
            # Sleep has hit_dice_affected instead of condition name
            if "hit_dice_affected" in effect:
                condition_name = "Unconscious"
                target_hd = _target_level(target)
                hd_cap = int(effect["hit_dice_affected"])
                if target_hd > hd_cap:
                    return SpellResult(
                        spell_name=spell_name,
                        outcome="condition",
                        saved=True,
                        raw_effect=effect,
                        narrative=(
                            f"{target_name} is immune to {spell_name} "
                            f"(HD {target_hd} > {hd_cap})."
                        ),
                    )
            save_spec = str(effect.get("save", ""))
            saved = False
            if save_spec:
                saved = _saving_throw(save_spec, target, save_dc, rng)
            if saved:
                return SpellResult(
                    spell_name=spell_name,
                    outcome="condition",
                    saved=True,
                    raw_effect=effect,
                    narrative=f"{target_name} resists {spell_name}.",
                )
            duration = int(effect.get("duration_rounds", caster_level))
            return SpellResult(
                spell_name=spell_name,
                outcome="condition",
                conditions_applied=[condition_name],
                raw_effect=effect,
                narrative=(
                    f"{target_name} is afflicted by {spell_name} "
                    f"({condition_name}, {duration} rounds)."
                ),
            )

        # --- Buff / utility (Mage Armor, Bless, Haste, Fly, etc.) ---
        return SpellResult(
            spell_name=spell_name,
            outcome="buff",
            raw_effect=effect,
            narrative=f"{caster_name} casts {spell_name}.",
        )

    @classmethod
    def best_offensive_spell(
        cls,
        caster: Any,
        registry: SpellRegistry,
        *,
        targeting_ally: bool = False,
    ) -> Optional[str]:
        """Return the name of the best offensive spell *caster* can cast right now.

        Checks ``spell_slot_manager.available()`` so that expended slots are
        respected.  Returns ``None`` if no offensive spell is castable.

        Args:
            caster:         A :class:`~src.rules_engine.character_35e.Character35e`.
            registry:       The populated spell registry.
            targeting_ally: When ``True``, returns a healing spell instead
                            (used by Clerics when an ally is below 50% HP).
        """
        char_class = getattr(caster, "char_class", "")
        ssm = getattr(caster, "spell_slot_manager", None)
        if ssm is None:
            return None

        priority = cls.OFFENSIVE_PRIORITY.get(char_class, [])
        if targeting_ally:
            priority = list(reversed(cls.HEALING_SPELLS))
        for name in priority:
            spell = registry.get(name)
            if spell is None:
                continue
            spell_level = spell.level
            if ssm.available(spell_level) > 0:
                return name
        return None
