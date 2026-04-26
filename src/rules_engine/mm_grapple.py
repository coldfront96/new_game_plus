"""LW-008 · LW-018 · LW-027 · LW-032 — Advanced grappling: Improved Grab, Swallow Whole, escape."""
from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.rules_engine.character_35e import Character35e

CombatEntity = "Character35e"


# ---------------------------------------------------------------------------
# LW-008 · Grapple schemas
# ---------------------------------------------------------------------------

class GrappleOutcome(enum.Enum):
    Grappled     = "grappled"
    Pinned       = "pinned"
    Swallowed    = "swallowed"
    Escaped      = "escaped"
    GrapplerDead = "grappler_dead"


@dataclass(slots=True)
class GrappleState:
    """Nullified (improved_grab_active=False, pin_active=False) on Escaped or GrapplerDead."""
    grapple_id: str
    grappler_id: str
    grappled_id: str
    initiated_tick: int
    swallow_depth: int             # 0 = not swallowed, 1 = inside stomach
    constrict_damage_dice: str | None
    improved_grab_active: bool
    pin_active: bool


# ---------------------------------------------------------------------------
# LW-018 · Improved Grab Initiator
# ---------------------------------------------------------------------------

def attempt_improved_grab(
    attacker: "Character35e",
    target: "Character35e",
    hit_confirmed: bool,
    tick: int,
) -> GrappleState | None:
    """Initiate an Improved Grab on a confirmed natural attack hit.

    Does NOT provoke an attack of opportunity from the target (core rule).
    Returns GrappleState on attacker win, None on failure or missing feat.
    """
    if not hit_confirmed:
        return None
    if "Improved Grab" not in attacker.feats:
        return None

    from src.rules_engine.dice import roll_d20

    atk_roll = roll_d20(modifier=attacker.grapple_modifier)
    def_roll = roll_d20(modifier=target.grapple_modifier)

    if atk_roll.total <= def_roll.total:
        return None

    return GrappleState(
        grapple_id=str(uuid.uuid4()),
        grappler_id=attacker.char_id,
        grappled_id=target.char_id,
        initiated_tick=tick,
        swallow_depth=0,
        constrict_damage_dice=None,
        improved_grab_active=True,
        pin_active=False,
    )


# ---------------------------------------------------------------------------
# LW-027 · Constrict & Swallow Whole Processor
# ---------------------------------------------------------------------------

def process_grapple_round(
    state: GrappleState,
    attacker: "Character35e",
    target: "Character35e",
    tick: int,
) -> tuple[GrappleState, int]:
    """Resolve one round of a maintained grapple.

    Returns (updated_state, constrict_damage_dealt).
    - Rolls to maintain (opposed grapple check); on failure returns nullified state.
    - On success with constrict_damage_dice: auto-deals constrict damage (no attack roll).
    - Swallow Whole: attempted if pinned, attacker ≥ Large, target ≥ 2 size categories smaller.
    - While swallowed: target takes per-round acid (2d6) + bludgeoning (1d8+STR mod) damage.
    Escape path: internal damage equal to ¼ swallower's max HP breaks free (tracked by caller).
    """
    from src.rules_engine.dice import roll_d20, roll_damage
    from src.rules_engine.character_35e import Size

    atk_roll = roll_d20(modifier=attacker.grapple_modifier)
    def_roll = roll_d20(modifier=target.grapple_modifier)

    if atk_roll.total <= def_roll.total:
        # Grapple broken
        return (
            GrappleState(
                grapple_id=state.grapple_id,
                grappler_id=state.grappler_id,
                grappled_id=state.grappled_id,
                initiated_tick=state.initiated_tick,
                swallow_depth=state.swallow_depth,
                constrict_damage_dice=state.constrict_damage_dice,
                improved_grab_active=False,
                pin_active=False,
            ),
            0,
        )

    # Constrict damage (auto, no attack roll)
    constrict_dmg = 0
    if state.constrict_damage_dice:
        constrict_dmg = roll_damage(state.constrict_damage_dice).total

    # Swallow Whole — requires: pin active, attacker Large+, target 2+ sizes smaller
    new_swallow_depth = state.swallow_depth
    if (
        state.swallow_depth == 0
        and state.pin_active
        and _size_ord(attacker) >= _size_ord_name("Large")
        and _size_ord(target) <= _size_ord(attacker) - 2
    ):
        sw_roll = roll_d20(modifier=attacker.grapple_modifier)
        if sw_roll.total > def_roll.total:
            new_swallow_depth = 1

    new_state = GrappleState(
        grapple_id=state.grapple_id,
        grappler_id=state.grappler_id,
        grappled_id=state.grappled_id,
        initiated_tick=state.initiated_tick,
        swallow_depth=new_swallow_depth,
        constrict_damage_dice=state.constrict_damage_dice,
        improved_grab_active=state.improved_grab_active,
        pin_active=state.pin_active,
    )
    return new_state, constrict_dmg


def _size_ord(character: "Character35e") -> int:
    """Return a size ordinal where larger = higher integer (inverts the Size enum value)."""
    return -character.size.value


def _size_ord_name(size_name: str) -> int:
    from src.rules_engine.character_35e import Size
    return -Size[size_name].value


# ---------------------------------------------------------------------------
# LW-032 · Complex Grapple Escape Logic
# ---------------------------------------------------------------------------

class EscapeMethod(enum.Enum):
    Grapple_Check     = "grapple_check"
    Escape_Artist     = "escape_artist"
    Teleport          = "teleport"
    Dimensional_Shift = "dimensional_shift"


def attempt_escape_grapple(
    state: GrappleState,
    escapee: "Character35e",
    grappler: "Character35e",
    method: EscapeMethod,
    tick: int,
) -> GrappleOutcome:
    """Attempt to escape a grapple using the specified method.

    While swallow_depth == 1, only Teleport or Dimensional_Shift are valid —
    Grapple_Check and Escape_Artist cannot be used from inside a swallower.
    Teleport/Dimensional_Shift always succeed (cost: standard action, tracked by caller).
    Returns nullified GrappleState meaning on GrappleOutcome.Escaped (caller is responsible
    for discarding the state).
    """
    from src.rules_engine.dice import roll_d20

    # Inside stomach — only magical escape works
    if state.swallow_depth == 1:
        if method in (EscapeMethod.Teleport, EscapeMethod.Dimensional_Shift):
            return GrappleOutcome.Escaped
        return GrappleOutcome.Swallowed

    # Magical escapes always succeed
    if method in (EscapeMethod.Teleport, EscapeMethod.Dimensional_Shift):
        return GrappleOutcome.Escaped

    if method == EscapeMethod.Grapple_Check:
        esc_roll = roll_d20(modifier=escapee.grapple_modifier)
        grp_roll = roll_d20(modifier=grappler.grapple_modifier)
        if esc_roll.total > grp_roll.total:
            return GrappleOutcome.Escaped
        return GrappleOutcome.Pinned if state.pin_active else GrappleOutcome.Grappled

    if method == EscapeMethod.Escape_Artist:
        dex_mod = (escapee.dexterity - 10) // 2
        skills = escapee.skills if isinstance(getattr(escapee, "skills", None), dict) else {}
        ea_ranks = skills.get("Escape Artist", 0)
        esc_roll = roll_d20(modifier=ea_ranks + dex_mod)
        grp_roll = roll_d20(modifier=grappler.grapple_modifier)
        if esc_roll.total > grp_roll.total:
            return GrappleOutcome.Escaped
        return GrappleOutcome.Grappled

    return GrappleOutcome.Grappled
