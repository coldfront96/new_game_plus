"""
src/ai_sim/master_minion.py
----------------------------
AI simulation integration stub for the master/minion turn-tracking subsystem.

Provides :func:`resolve_minion_turns` which drives the
:class:`~src.rules_engine.linked_entity.MasterMinionTurnTracker` through a
single combat round, rolling initiative for each link and synchronising
action costs into the shared round state.

Usage::

    import random
    from src.ai_sim.master_minion import resolve_minion_turns
    from src.rules_engine.linked_entity import MasterMinionTurnTracker

    tracker = MasterMinionTurnTracker(links=[...], initiative_map={})
    round_state = resolve_minion_turns(tracker, {}, random)
"""

from __future__ import annotations

from typing import Any

from src.rules_engine.linked_entity import MasterMinionLink, MasterMinionTurnTracker


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
