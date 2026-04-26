"""LW-010 · LW-020 · LW-028 · LW-034 — Damage Reduction and Spell Resistance."""
from __future__ import annotations

import enum
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.rules_engine.character_35e import Character35e

_log = logging.getLogger(__name__)
CombatEntity = "Character35e"


# ---------------------------------------------------------------------------
# LW-010 · Schemas
# ---------------------------------------------------------------------------

class DRConjunction(enum.Enum):
    And = "and"   # ALL listed bypass materials required simultaneously, e.g. 10/Cold Iron and Magic
    Or  = "or"    # ANY single bypass material is sufficient, e.g. 5/Silver or Cold Iron


@dataclass(slots=True)
class DRRecord:
    entity_id: str
    dr_amount: int
    bypass_conjunction: DRConjunction
    bypass_materials: tuple[str, ...]   # e.g. ("Good",), ("Silver", "Magic"), ()


@dataclass(slots=True)
class SRRecord:
    entity_id: str
    sr_value: int
    voluntarily_suppressed: bool


@dataclass(slots=True)
class SRResult:
    penetrated: bool
    roll: int
    caster_level: int
    sr_value: int
    exception_applied: str | None = None


# ---------------------------------------------------------------------------
# LW-020 · Spell Resistance Pre-Roll
# ---------------------------------------------------------------------------

def check_spell_resistance(
    caster: "Character35e",
    target: "Character35e",
    sr_record: SRRecord,
) -> SRResult:
    """Roll caster level check against SR; result is appended to the combat audit trail.

    Returns penetrated=True without rolling if the target voluntarily suppressed SR.
    """
    from src.rules_engine.dice import roll_d20

    if sr_record.voluntarily_suppressed:
        result = SRResult(
            penetrated=True,
            roll=0,
            caster_level=caster.caster_level,
            sr_value=sr_record.sr_value,
            exception_applied="voluntarily_suppressed",
        )
        _log.debug("SR check: %s suppressed SR — auto-penetrated", target.char_id)
        return result

    roll = roll_d20(modifier=caster.caster_level)
    penetrated = roll.total >= sr_record.sr_value

    _log.debug(
        "SR check: caster=%s target=%s roll=%d+%d=%d vs SR %d → %s",
        caster.char_id, target.char_id, roll.raw, caster.caster_level,
        roll.total, sr_record.sr_value, "penetrated" if penetrated else "blocked",
    )
    return SRResult(
        penetrated=penetrated,
        roll=roll.raw,
        caster_level=caster.caster_level,
        sr_value=sr_record.sr_value,
    )


# ---------------------------------------------------------------------------
# LW-028 · DR Resolution Engine
# ---------------------------------------------------------------------------

_ENERGY_TYPES = frozenset({
    "Fire", "Cold", "Acid", "Electricity", "Sonic",
    "Positive", "Negative", "Force",
})


def apply_damage_reduction(
    raw_damage: int,
    weapon_properties: tuple[str, ...],
    dr_record: DRRecord,
) -> int:
    """Apply DR to raw physical damage; return post-DR damage (minimum 0).

    And-conjunction: ALL bypass_materials must appear in weapon_properties.
    Or-conjunction:  ANY single bypass_material is sufficient.
    Pure energy damage types, 'no_physical_component' spells, and [Force]
    spells bypass DR entirely regardless of conjunction.
    """
    props = set(weapon_properties)

    # Energy damage and non-physical spells bypass DR entirely
    if props & _ENERGY_TYPES:
        return raw_damage
    if "no_physical_component" in props:
        return raw_damage

    if _check_bypass(props, dr_record):
        return raw_damage

    return max(0, raw_damage - dr_record.dr_amount)


def _check_bypass(props: set[str], dr_record: DRRecord) -> bool:
    if not dr_record.bypass_materials:
        return False
    materials = set(dr_record.bypass_materials)
    if dr_record.bypass_conjunction == DRConjunction.Or:
        return bool(props & materials)
    return materials.issubset(props)   # And — all required simultaneously


# ---------------------------------------------------------------------------
# LW-034 · Spell Resistance Interaction Rules
# ---------------------------------------------------------------------------

def apply_sr_interaction_rules(
    spell_name: str,
    spell_tags: tuple[str, ...],
    caster: "Character35e",
    target: "Character35e",
    sr_record: SRRecord,
) -> SRResult:
    """Apply the full 3.5e SR exception table; fall through to check_spell_resistance.

    SR does NOT apply when any of the following are true:
    - 'SR_No'         — spell explicitly has SR: No
    - 'Supernatural'  — supernatural ability, not a spell
    - 'Breath_Weapon' — natural breath weapon
    - 'Force' + 'Bypasses_SR' — explicit Force descriptor that states it bypasses SR

    Area spells check SR individually per target (caller iterates targets separately).
    Touch spells check SR at moment of contact, not cast time (caller provides timing).
    Harmless spells still check SR if the target is hostile and did not lower SR voluntarily.
    """
    tags = set(spell_tags)

    _EXCEPTIONS: dict[str, str] = {
        "SR_No":       "SR_No",
        "Supernatural": "Supernatural",
        "Breath_Weapon": "Breath_Weapon",
    }
    for tag, label in _EXCEPTIONS.items():
        if tag in tags:
            return SRResult(
                penetrated=True,
                roll=0,
                caster_level=caster.caster_level,
                sr_value=sr_record.sr_value,
                exception_applied=label,
            )

    if "Force" in tags and "Bypasses_SR" in tags:
        return SRResult(
            penetrated=True,
            roll=0,
            caster_level=caster.caster_level,
            sr_value=sr_record.sr_value,
            exception_applied="Force_Bypasses_SR",
        )

    # Harmless spells still check SR if target did not voluntarily suppress
    # (fall through to normal SR check — no special handling needed here)

    return check_spell_resistance(caster, target, sr_record)
