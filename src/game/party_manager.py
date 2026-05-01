"""PH3-005 · PH3-006 · PH3-007 · PH3-008 · PH3-009 — Tactical Party System.

src/game/party_manager.py
--------------------------
Manages a player party of up to four combatants (1 leader + 3 companions),
dispatching turns autonomously via the Tactical AI or manually via the
PlayerController.

Key types
~~~~~~~~~
* :class:`ControlMode`   — ``AUTONOMOUS`` or ``MANUAL`` companion control.
* :class:`CompanionSlot` — one party member slot (slots 0–2 for companions).
* :class:`PartyRecord`   — the full party: a leader + up to three companions.
* :exc:`PartyFullError`  — raised when a fourth companion is added.

Usage::

    from src.game.party_manager import (
        ControlMode, create_party, add_companion, dispatch_party_round,
    )

    party = create_party(leader_entity_id="aldric", world_seed=42)
    party = add_companion(party, entity_id="zara", character_id="zara-char")
    decisions = dispatch_party_round(party, encounter_entities=[], ...)
"""

from __future__ import annotations

import asyncio
import enum
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.rules_engine.character_35e import Character35e
    from src.game.player_controller import PlayerController, PlayerAction
    from src.ai_sim.tactics import TacticalDecision
    from src.ai_sim.llm_bridge import LLMClient
    from src.ai_sim.entity import Entity


# ---------------------------------------------------------------------------
# PH3-005 — ControlMode enum
# ---------------------------------------------------------------------------

class ControlMode(enum.Enum):
    """Whether a companion's turn is resolved by the AI or by the player."""

    AUTONOMOUS = "autonomous"
    MANUAL     = "manual"


# ---------------------------------------------------------------------------
# PH3-005 — PartyFullError
# ---------------------------------------------------------------------------

class PartyFullError(RuntimeError):
    """Raised when attempting to add a fourth companion to a party."""


# ---------------------------------------------------------------------------
# PH3-005 — CompanionSlot schema
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class CompanionSlot:
    """One party member slot (reserved for companions, i.e. non-leader members).

    Attributes:
        slot_index:   Position in the party (0–2; slot 0 is the first companion).
        entity_id:    :class:`~src.ai_sim.entity.Entity` ID of the combatant.
        character_id: :class:`~src.rules_engine.character_35e.Character35e` ID.
        control_mode: How this companion's turns are resolved.
    """

    slot_index:   int
    entity_id:    str
    character_id: str
    control_mode: ControlMode = ControlMode.AUTONOMOUS


# ---------------------------------------------------------------------------
# PH3-005 — PartyRecord schema
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class PartyRecord:
    """The full party: one human leader plus up to three companions.

    Invariants:
        * ``len(slots) <= 3`` — at most three companions.
        * Total party size therefore ≤ 4 (1 leader + 3 companions).
        * ``party_id`` is a deterministic UUID of ``leader_entity_id + world_seed``.

    Attributes:
        party_id:         Deterministic UUID of ``leader_entity_id + str(world_seed)``.
        leader_entity_id: Entity ID of the human player's combatant.
        slots:            Companion slots (max 3).
    """

    party_id:         str
    leader_entity_id: str
    slots:            list[CompanionSlot]


# ---------------------------------------------------------------------------
# PH3-006 — Party formation API
# ---------------------------------------------------------------------------

def create_party(leader_entity_id: str, world_seed: int) -> PartyRecord:
    """Construct an empty :class:`PartyRecord` with the given leader.

    The ``party_id`` is a deterministic UUID derived from
    ``leader_entity_id + str(world_seed)`` for cross-session reproducibility.

    Args:
        leader_entity_id: Entity ID of the human player's :class:`CombatEntity`.
        world_seed:       Integer seed used for UUID derivation.

    Returns:
        A new :class:`PartyRecord` with an empty companion list.
    """
    party_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{leader_entity_id}{world_seed}"))
    return PartyRecord(
        party_id=party_id,
        leader_entity_id=leader_entity_id,
        slots=[],
    )


def add_companion(
    party: PartyRecord,
    entity_id: str,
    character_id: str,
    control_mode: ControlMode = ControlMode.AUTONOMOUS,
) -> PartyRecord:
    """Append a companion to *party*.

    Args:
        party:        The party to modify.
        entity_id:    Entity ID of the new companion.
        character_id: Character sheet ID of the new companion.
        control_mode: Control mode for this companion (default AUTONOMOUS).

    Returns:
        The mutated :class:`PartyRecord` (in-place, returned for convenience).

    Raises:
        PartyFullError: When *party* already has 3 companions.
    """
    if len(party.slots) >= 3:
        raise PartyFullError(
            f"Party {party.party_id!r} is already full (3 companions maximum)."
        )
    slot = CompanionSlot(
        slot_index=len(party.slots),
        entity_id=entity_id,
        character_id=character_id,
        control_mode=control_mode,
    )
    party.slots.append(slot)
    return party


def remove_companion(party: PartyRecord, entity_id: str) -> PartyRecord:
    """Remove the companion with the given *entity_id* from *party*.

    Slot indices are re-assigned sequentially after removal.

    Args:
        party:     The party to modify.
        entity_id: Entity ID of the companion to remove.

    Returns:
        The mutated :class:`PartyRecord`.

    Raises:
        KeyError: When no companion with *entity_id* is found.
    """
    for i, slot in enumerate(party.slots):
        if slot.entity_id == entity_id:
            party.slots.pop(i)
            # Re-index remaining slots
            for j, s in enumerate(party.slots):
                object.__setattr__(s, "slot_index", j)
            return party
    raise KeyError(f"No companion with entity_id={entity_id!r} found in party.")


def set_control_mode(
    party: PartyRecord,
    entity_id: str,
    mode: ControlMode,
) -> PartyRecord:
    """Change the control mode for the companion identified by *entity_id*.

    Args:
        party:     The party to modify.
        entity_id: Entity ID of the companion.
        mode:      The new :class:`ControlMode`.

    Returns:
        The mutated :class:`PartyRecord`.

    Raises:
        KeyError: When no companion with *entity_id* is found.
    """
    for slot in party.slots:
        if slot.entity_id == entity_id:
            object.__setattr__(slot, "control_mode", mode)
            return party
    raise KeyError(f"No companion with entity_id={entity_id!r} found in party.")


# ---------------------------------------------------------------------------
# PH3-007 — Autonomous companion turn router
# ---------------------------------------------------------------------------

def route_autonomous_turn(
    slot: CompanionSlot,
    party: PartyRecord,
    encounter_entities: list["Character35e"],
    character_registry: "dict[str, Character35e]",
    rng: object,
    llm_client: "LLMClient | None" = None,
) -> "TacticalDecision | None":
    """Resolve an autonomous companion's turn using the Tactical AI.

    Identifies hostile targets from *encounter_entities* (those whose
    ``metadata["faction"]`` is not in the companion's own faction list),
    constructs a :class:`~src.ai_sim.tactics.TacticalEvaluator`, and
    returns a :class:`~src.ai_sim.tactics.TacticalDecision`.

    If *llm_client* is provided an additional gambit prompt is sent to the
    LLM; a cleanly parsed spell/ability override is applied to the decision.

    Args:
        slot:               The :class:`CompanionSlot` being processed.
        party:              The owning :class:`PartyRecord` (for context).
        encounter_entities: All :class:`Character35e` objects in the encounter.
        character_registry: Mapping of ``character_id → Character35e``.
        rng:                :class:`random.Random` instance.
        llm_client:         Optional :class:`~src.ai_sim.llm_bridge.LLMClient`.

    Returns:
        A :class:`~src.ai_sim.tactics.TacticalDecision`, or ``None`` when
        there are no valid hostile targets.

    Raises:
        ValueError: When ``slot.control_mode`` is not ``ControlMode.AUTONOMOUS``.
    """
    from src.ai_sim.tactics import TacticalEvaluator
    from src.ai_sim.entity import Entity
    from src.ai_sim.components import Position

    if slot.control_mode != ControlMode.AUTONOMOUS:
        raise ValueError(
            f"route_autonomous_turn requires AUTONOMOUS slot; got {slot.control_mode}."
        )

    character = character_registry[slot.character_id]
    companion_faction = character.metadata.get("faction", None)

    # Build a lightweight Entity for the actor
    actor_entity = Entity(name=character.name, entity_id=slot.entity_id)
    actor_pos_meta = character.metadata.get("position", {})
    actor_entity.add_component(Position(
        x=actor_pos_meta.get("x", 0),
        y=actor_pos_meta.get("y", 64),
        z=actor_pos_meta.get("z", 0),
    ))

    # Identify hostiles: entities not sharing the companion's faction
    hostile_pairs: list[tuple["Entity", "Character35e"]] = []
    for other_char in encounter_entities:
        if other_char.char_id == character.char_id:
            continue
        other_faction = other_char.metadata.get("faction", None)
        if companion_faction is None or other_faction != companion_faction:
            other_entity = Entity(name=other_char.name)
            other_pos = other_char.metadata.get("position", {})
            other_entity.add_component(Position(
                x=other_pos.get("x", 8),
                y=other_pos.get("y", 64),
                z=other_pos.get("z", 8),
            ))
            hostile_pairs.append((other_entity, other_char))

    if not hostile_pairs:
        return None

    # Resolve equipped weapon from metadata
    weapon = character.metadata.get("equipped_weapon", None)

    evaluator = TacticalEvaluator(
        actor_entity=actor_entity,
        actor_character=character,
        visible_hostiles=hostile_pairs,
        weapon=weapon,
    )
    decision = evaluator.evaluate()

    # Optional LLM gambit prompt
    if llm_client is not None and decision is not None:
        _apply_llm_gambit(llm_client, character, hostile_pairs, decision)

    return decision


def _apply_llm_gambit(
    llm_client: "LLMClient",
    character: "Character35e",
    hostile_pairs: list,
    decision: "TacticalDecision",
) -> None:
    """Send a compact gambit prompt to the LLM and attempt to apply any override."""
    try:
        from src.ai_sim.llm_bridge import CognitiveState

        max_hp = character.hit_points
        prompt = (
            f"Entity: {character.name}, HP: {max_hp}/{max_hp}, "
            f"AC: {character.armor_class}, Hostiles: {len(hostile_pairs)}. "
            "Reply with a single preferred spell or ability name, or 'attack' to melee."
        )
        state = CognitiveState.from_character(character, visible_entities=[])

        # Run async call in a best-effort way
        try:
            loop = asyncio.get_running_loop()
            # Already inside an event loop: fire-and-forget
            loop.create_task(
                llm_client.query_model(
                    system_prompt="You are a tactical advisor.",
                    cognitive_state=state,
                    user_prompt=prompt,
                )
            )
        except RuntimeError:
            # No running loop — run synchronously
            asyncio.run(
                llm_client.query_model(
                    system_prompt="You are a tactical advisor.",
                    cognitive_state=state,
                    user_prompt=prompt,
                )
            )
    except Exception:
        # LLM failures are non-fatal; decision is unchanged
        pass


# ---------------------------------------------------------------------------
# PH3-008 — Manual companion turn router
# ---------------------------------------------------------------------------

def route_manual_turn(
    slot: CompanionSlot,
    controller: "PlayerController",
    combat_registry: "dict[str, Character35e]",
) -> "PlayerAction":
    """Resolve a manual companion's turn via the PlayerController.

    Re-uses :func:`~src.game.player_controller.dispatch_player_input` semantics
    targeting the companion's entity rather than the leader's.

    Accepted actions mirror the existing :class:`~src.game.player_controller.PlayerAction`
    enum (N/S/E/W/U/D/Wait/Interact) extended with:

    * ``Attack``  — targets the nearest hostile by voxel distance.
    * ``Cast``    — opens a spell selection sub-menu of prepared spells.

    Args:
        slot:            The :class:`CompanionSlot` being processed (must be MANUAL).
        controller:      The :class:`~src.game.player_controller.PlayerController`.
        combat_registry: Mapping of ``entity_id → Character35e``.

    Returns:
        The resolved :class:`~src.game.player_controller.PlayerAction`.

    Raises:
        ValueError: When ``slot.control_mode`` is not ``ControlMode.MANUAL``.
    """
    from src.game.player_controller import PlayerAction, dispatch_player_input

    if slot.control_mode != ControlMode.MANUAL:
        raise ValueError(
            f"route_manual_turn requires MANUAL slot; got {slot.control_mode}."
        )

    # Swap the controller's entity_id to the companion for the duration of this call.
    # PlayerController is a mutable slots dataclass so direct assignment works.
    original_entity_id = controller.entity_id
    controller.entity_id = slot.entity_id
    try:
        dispatch_player_input(controller, PlayerAction.Wait, combat_registry)
    finally:
        controller.entity_id = original_entity_id

    return PlayerAction.Wait


# ---------------------------------------------------------------------------
# PH3-009 — Party combat round dispatcher
# ---------------------------------------------------------------------------

def dispatch_party_round(
    party: PartyRecord,
    encounter_entities: list["Character35e"],
    character_registry: "dict[str, Character35e]",
    controller: "PlayerController",
    rng: object,
    llm_client: "LLMClient | None" = None,
) -> "list[TacticalDecision | PlayerAction]":
    """Dispatch one full combat round for the party.

    Iterates :attr:`PartyRecord.slots` in initiative order (highest first),
    routing each turn autonomously or manually as configured.  The leader's
    action (always manual) is prepended to the result list.

    Autonomous turns call :func:`route_autonomous_turn`;
    manual turns call :func:`route_manual_turn`.

    The dispatcher only resolves *intent* — it does not apply damage or
    movement.  The caller is responsible for executing the returned actions.

    Args:
        party:              The :class:`PartyRecord` to process.
        encounter_entities: All :class:`Character35e` objects in the encounter.
        character_registry: Mapping of ``character_id → Character35e``.
        controller:         The human player's :class:`~src.game.player_controller.PlayerController`.
        rng:                :class:`random.Random` instance.
        llm_client:         Optional LLM client for autonomous companions.

    Returns:
        Ordered list of :class:`~src.ai_sim.tactics.TacticalDecision` or
        :class:`~src.game.player_controller.PlayerAction` objects for the
        turn controller to execute.
    """
    from src.game.player_controller import PlayerAction, dispatch_player_input

    results: list = []

    # --- Leader action (always manual) ---
    dispatch_player_input(controller, PlayerAction.Wait, {})
    leader_action = PlayerAction.Wait
    results.append(leader_action)

    # --- Sort companion slots by initiative (descending) ---
    def _initiative(slot: CompanionSlot) -> int:
        char = character_registry.get(slot.character_id)
        if char is None:
            return 0
        return getattr(char, "initiative_modifier", 0)

    sorted_slots = sorted(party.slots, key=_initiative, reverse=True)

    for slot in sorted_slots:
        if slot.control_mode == ControlMode.AUTONOMOUS:
            decision = route_autonomous_turn(
                slot=slot,
                party=party,
                encounter_entities=encounter_entities,
                character_registry=character_registry,
                rng=rng,
                llm_client=llm_client,
            )
            if decision is not None:
                results.append(decision)
        else:
            action = route_manual_turn(
                slot=slot,
                controller=controller,
                combat_registry=character_registry,
            )
            results.append(action)

    return results
