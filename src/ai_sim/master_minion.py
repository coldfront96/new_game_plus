"""
src/ai_sim/master_minion.py
----------------------------
AI simulation integration for the master/minion turn-tracking subsystem.

Implements:
    E-056 (via linked_entity.py) — MasterMinionTurnTracker
    E-064 — simulate_round_with_links / RoundReport

Provides :func:`resolve_minion_turns` (lower-level driver) and the
higher-level :func:`simulate_round_with_links` (full per-round combat driver
for parties with master/minion links, per task E-064).

Usage::

    import random
    from src.ai_sim.master_minion import simulate_round_with_links
    from src.rules_engine.linked_entity import MasterMinionLink, LinkType

    links = [MasterMinionLink(
        master_id="wizard1", minion_id="familiar1",
        link_type=LinkType.Familiar,
        share_spells=True, empathic_link=True,
        delivery_touch=True, scry_on_familiar=True,
    )]
    party = [wizard_char]
    report = simulate_round_with_links(party, links, encounter=None, rng=random)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from src.rules_engine.linked_entity import (
    LinkType,
    MasterMinionLink,
    MasterMinionTurnTracker,
    share_spell,
    empathic_link_message,
)


# ---------------------------------------------------------------------------
# E-064 — RoundReport dataclass
# ---------------------------------------------------------------------------

@dataclass
class RoundReport:
    """Summary of one combined master/minion combat round.

    Attributes:
        initiative_order: Entity IDs sorted from highest to lowest initiative.
        initiative_map:   Mapping of entity_id → initiative roll.
        move_actions_spent: Set of master IDs that spent their Move action
            issuing a command to their minion this round.
        damage_propagated: Mapping of master_id → HP lost due to the
            "master-familiar damage link" rule (1 hp per 5 hp dealt to the
            familiar, rounded down).
        share_spell_results: List of descriptive strings for any share-spell
            attempts that occurred (from ``link.share_spells`` links).
        empathic_messages: List of empathic-link transmissions this round.
        notes: Miscellaneous per-round log entries.
    """

    initiative_order: list[str] = field(default_factory=list)
    initiative_map: dict[str, int] = field(default_factory=dict)
    move_actions_spent: set[str] = field(default_factory=set)
    damage_propagated: dict[str, int] = field(default_factory=dict)
    share_spell_results: list[str] = field(default_factory=list)
    empathic_messages: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# E-064 — simulate_round_with_links
# ---------------------------------------------------------------------------

# PHB: master takes 1 hp for every 5 hp dealt to the familiar (round down).
_FAMILIAR_DAMAGE_RATIO = 5


def simulate_round_with_links(
    party: list,
    links: list[MasterMinionLink],
    encounter: Any,
    rng: Any,
) -> RoundReport:
    """Run one full combat round for a party that includes master/minion pairs.

    Per task E-064:

    1. **Initiative** — each master and each minion rolls independently
       (``d20``); the combined initiative order is built from the full set.
    2. **Command cost** — commanding a minion costs the master a Move action;
       this is recorded in :attr:`RoundReport.move_actions_spent`.
    3. **Familiar share-spells** — for Familiar links with ``share_spells``
       enabled, any party members whose metadata carries a pending
       ``"pending_share_spell"`` entry trigger a share-spell attempt; the
       result is logged in :attr:`RoundReport.share_spell_results`.
    4. **Empathic link** — Familiar/SpecialMount links with ``empathic_link``
       enabled emit a summary message for each master that has a
       ``"empathic_sense"`` entry in metadata.
    5. **Damage propagation** — if a master's metadata contains
       ``"familiar_damage_taken"`` (HP dealt to familiar this round), the
       master loses ``familiar_damage_taken // 5`` HP and the amount is
       recorded in :attr:`RoundReport.damage_propagated`.

    Args:
        party:     List of :class:`~src.rules_engine.character_35e.Character35e`
                   (or any object with ``char_id``, ``metadata``,
                   ``dexterity_mod`` attributes and a mutable ``hp`` field).
        links:     Active :class:`~src.rules_engine.linked_entity.MasterMinionLink`
                   objects.
        encounter: Encounter blueprint or ``None`` (unused by this function;
                   reserved for future integration with E-062).
        rng:       Object exposing ``randint(a, b)`` (e.g. ``random`` module).

    Returns:
        A :class:`RoundReport` summarising initiative order, move costs,
        damage propagation, and link messages for the round.
    """
    report = RoundReport()

    # --- Step 1: Build initiative map for all party members + minions ---
    # Party members: use dexterity_mod if available
    init_map: dict[str, int] = {}
    for combatant in party:
        dex_bonus = getattr(combatant, "dexterity_mod", 0)
        roll = rng.randint(1, 20) + dex_bonus
        init_map[combatant.char_id] = roll

    # Use the tracker for all links (rolls minion initiative independently)
    tracker = MasterMinionTurnTracker(links=list(links), initiative_map={})
    for link in links:
        master_init, minion_init = tracker.roll_initiative_for_link(link, rng)
        init_map[link.master_id] = master_init  # overwrite with tracked roll
        init_map[link.minion_id] = minion_init

    report.initiative_map = dict(init_map)
    report.initiative_order = sorted(init_map, key=lambda k: init_map[k], reverse=True)

    # --- Step 2: Command cost — each master spends a Move action per link ---
    round_state: dict = {}
    round_state = tracker.synchronise_actions(round_state)
    report.move_actions_spent = set(round_state.get("move_action_spent", set()))

    # --- Steps 3–5: Per-link effects ---
    # Build a lookup from char_id → character object for metadata access
    char_by_id: dict[str, Any] = {c.char_id: c for c in party}

    for link in links:
        master = char_by_id.get(link.master_id)
        if master is None:
            report.notes.append(
                f"Master '{link.master_id}' not found in party; skipping link effects."
            )
            continue

        # Step 3: Share-spell
        if link.link_type == LinkType.Familiar and link.share_spells:
            pending = master.metadata.get("pending_share_spell")
            if pending:
                spell_name = pending.get("name", "unknown")
                spell_range = pending.get("range", "Personal")
                distance_ft = float(pending.get("distance_ft", 0.0))
                result = share_spell(link, spell_name, spell_range, distance_ft)
                report.share_spell_results.append(result.reason)

        # Step 4: Empathic link
        if link.empathic_link:
            sense = master.metadata.get("empathic_sense")
            if sense:
                distance_miles = float(master.metadata.get("familiar_distance_miles", 0.0))
                msg = empathic_link_message(link, sense, distance_miles)
                report.empathic_messages.append(msg)

        # Step 5: Damage propagation (1 HP per 5 HP dealt to familiar)
        if link.link_type == LinkType.Familiar:
            familiar_dmg = int(master.metadata.get("familiar_damage_taken", 0))
            if familiar_dmg > 0:
                hp_loss = familiar_dmg // _FAMILIAR_DAMAGE_RATIO
                if hp_loss > 0:
                    # Apply damage to master
                    current_hp = getattr(master, "current_hp", None)
                    if current_hp is None:
                        current_hp = getattr(master, "hp", 0)
                    new_hp = max(0, current_hp - hp_loss)
                    try:
                        master.current_hp = new_hp
                    except AttributeError:
                        try:
                            object.__setattr__(master, "current_hp", new_hp)
                        except (AttributeError, TypeError):
                            pass
                    report.damage_propagated[link.master_id] = hp_loss
                    report.notes.append(
                        f"Master '{link.master_id}' takes {hp_loss} hp from familiar damage "
                        f"({familiar_dmg} hp dealt to familiar)."
                    )
                # Clear the familiar damage counter for next round
                master.metadata["familiar_damage_taken"] = 0

    return report


# ---------------------------------------------------------------------------
# Lower-level helper (kept for backward compatibility)
# ---------------------------------------------------------------------------

def resolve_minion_turns(
    tracker: MasterMinionTurnTracker,
    round_state: dict,
    rng: Any,
) -> dict:
    """Drive one full round of master/minion initiative and action economy.

    For every link registered in *tracker*:
    1. Rolls initiative independently for master and minion via
       :meth:`~MasterMinionTurnTracker.roll_initiative_for_link`.
    2. Synchronises action costs (commanding a minion spends a Move action)
       via :meth:`~MasterMinionTurnTracker.synchronise_actions`.

    Args:
        tracker:     The active :class:`MasterMinionTurnTracker`.
        round_state: Mutable combat round state dictionary shared across
                     all systems for the current round.
        rng:         RNG object exposing ``randint(a, b)`` (e.g. ``random``
                     module or any compatible object).

    Returns:
        Updated *round_state* dict with initiative rolls recorded in
        ``tracker.initiative_map`` and move-action costs noted under the
        ``"move_action_spent"`` key.
    """
    for link in tracker.links:
        tracker.roll_initiative_for_link(link, rng)

    round_state = tracker.synchronise_actions(round_state)
    round_state["initiative_map"] = dict(tracker.initiative_map)
    return round_state

