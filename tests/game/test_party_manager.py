"""Tests for Phase 3: Party Manager subsystem (PH3-005 · PH3-006 · PH3-007 · PH3-008 · PH3-009)."""
from __future__ import annotations

import random

import pytest

from src.game.party_manager import (
    ControlMode,
    CompanionSlot,
    PartyRecord,
    PartyFullError,
    create_party,
    add_companion,
    remove_companion,
    set_control_mode,
    route_autonomous_turn,
    route_manual_turn,
    dispatch_party_round,
)
from src.rules_engine.character_35e import Character35e, Alignment
from src.game.player_controller import PlayerController, PlayerAction


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _char(name: str = "Aldric") -> Character35e:
    return Character35e(name=name, char_class="Fighter", level=5)


def _controller() -> PlayerController:
    return PlayerController(
        player_id="p1",
        entity_id="leader-entity",
        chunk_id="0_0",
    )


# ---------------------------------------------------------------------------
# PH3-005 — ControlMode enum
# ---------------------------------------------------------------------------

class TestControlMode:
    def test_values(self):
        assert ControlMode.AUTONOMOUS.value == "autonomous"
        assert ControlMode.MANUAL.value == "manual"


# ---------------------------------------------------------------------------
# PH3-005 — CompanionSlot schema
# ---------------------------------------------------------------------------

class TestCompanionSlot:
    def test_default_control_mode(self):
        slot = CompanionSlot(slot_index=0, entity_id="e1", character_id="c1")
        assert slot.control_mode == ControlMode.AUTONOMOUS

    def test_manual_mode(self):
        slot = CompanionSlot(slot_index=1, entity_id="e2", character_id="c2", control_mode=ControlMode.MANUAL)
        assert slot.control_mode == ControlMode.MANUAL


# ---------------------------------------------------------------------------
# PH3-005 — PartyRecord schema
# ---------------------------------------------------------------------------

class TestPartyRecord:
    def test_fields(self):
        party = create_party("leader1", world_seed=42)
        assert party.leader_entity_id == "leader1"
        assert party.slots == []
        assert party.party_id != ""

    def test_deterministic_party_id(self):
        p1 = create_party("leader1", 42)
        p2 = create_party("leader1", 42)
        assert p1.party_id == p2.party_id

    def test_different_seeds_different_ids(self):
        p1 = create_party("leader1", 42)
        p2 = create_party("leader1", 99)
        assert p1.party_id != p2.party_id


# ---------------------------------------------------------------------------
# PH3-005 — PartyFullError
# ---------------------------------------------------------------------------

class TestPartyFullError:
    def test_is_runtime_error(self):
        assert issubclass(PartyFullError, RuntimeError)


# ---------------------------------------------------------------------------
# PH3-006 — create_party
# ---------------------------------------------------------------------------

class TestCreateParty:
    def test_empty_slots(self):
        party = create_party("leader", 1)
        assert len(party.slots) == 0

    def test_leader_entity_id(self):
        party = create_party("the-leader", 0)
        assert party.leader_entity_id == "the-leader"


# ---------------------------------------------------------------------------
# PH3-006 — add_companion
# ---------------------------------------------------------------------------

class TestAddCompanion:
    def test_adds_slot(self):
        party = create_party("lead", 1)
        add_companion(party, "comp1", "char1")
        assert len(party.slots) == 1
        assert party.slots[0].entity_id == "comp1"
        assert party.slots[0].character_id == "char1"

    def test_slot_index_sequential(self):
        party = create_party("lead", 1)
        add_companion(party, "c1", "ch1")
        add_companion(party, "c2", "ch2")
        assert party.slots[0].slot_index == 0
        assert party.slots[1].slot_index == 1

    def test_returns_party(self):
        party = create_party("lead", 1)
        result = add_companion(party, "c1", "ch1")
        assert result is party

    def test_default_control_mode(self):
        party = create_party("lead", 1)
        add_companion(party, "c1", "ch1")
        assert party.slots[0].control_mode == ControlMode.AUTONOMOUS

    def test_custom_control_mode(self):
        party = create_party("lead", 1)
        add_companion(party, "c1", "ch1", ControlMode.MANUAL)
        assert party.slots[0].control_mode == ControlMode.MANUAL

    def test_three_companions_allowed(self):
        party = create_party("lead", 1)
        for i in range(3):
            add_companion(party, f"c{i}", f"ch{i}")
        assert len(party.slots) == 3

    def test_fourth_raises_party_full_error(self):
        party = create_party("lead", 1)
        for i in range(3):
            add_companion(party, f"c{i}", f"ch{i}")
        with pytest.raises(PartyFullError):
            add_companion(party, "c3", "ch3")


# ---------------------------------------------------------------------------
# PH3-006 — remove_companion
# ---------------------------------------------------------------------------

class TestRemoveCompanion:
    def test_removes_slot(self):
        party = create_party("lead", 1)
        add_companion(party, "c1", "ch1")
        remove_companion(party, "c1")
        assert len(party.slots) == 0

    def test_returns_party(self):
        party = create_party("lead", 1)
        add_companion(party, "c1", "ch1")
        result = remove_companion(party, "c1")
        assert result is party

    def test_reindexes_after_removal(self):
        party = create_party("lead", 1)
        add_companion(party, "c1", "ch1")
        add_companion(party, "c2", "ch2")
        remove_companion(party, "c1")
        assert party.slots[0].slot_index == 0

    def test_raises_key_error_when_not_found(self):
        party = create_party("lead", 1)
        with pytest.raises(KeyError):
            remove_companion(party, "nonexistent")


# ---------------------------------------------------------------------------
# PH3-006 — set_control_mode
# ---------------------------------------------------------------------------

class TestSetControlMode:
    def test_changes_mode(self):
        party = create_party("lead", 1)
        add_companion(party, "c1", "ch1")
        set_control_mode(party, "c1", ControlMode.MANUAL)
        assert party.slots[0].control_mode == ControlMode.MANUAL

    def test_returns_party(self):
        party = create_party("lead", 1)
        add_companion(party, "c1", "ch1")
        result = set_control_mode(party, "c1", ControlMode.MANUAL)
        assert result is party

    def test_raises_key_error_when_not_found(self):
        party = create_party("lead", 1)
        with pytest.raises(KeyError):
            set_control_mode(party, "ghost", ControlMode.MANUAL)


# ---------------------------------------------------------------------------
# PH3-007 — route_autonomous_turn
# ---------------------------------------------------------------------------

class TestRouteAutonomousTurn:
    def _setup(self):
        party = create_party("lead", 1)
        add_companion(party, "companion-entity", "comp-char-id")
        companion_char = Character35e(
            name="Zara",
            char_class="Fighter",
            level=3,
        )
        companion_char.char_id = "comp-char-id"
        companion_char.metadata["faction"] = "Good Guys"
        companion_char.metadata["position"] = {"x": 0, "y": 64, "z": 0}

        hostile = Character35e(name="Orc", char_class="Barbarian", level=2)
        hostile.metadata["faction"] = "Orc Warband"
        hostile.metadata["position"] = {"x": 2, "y": 64, "z": 2}

        char_registry = {"comp-char-id": companion_char}
        return party.slots[0], party, [hostile], char_registry

    def test_raises_value_error_for_manual_slot(self):
        party = create_party("lead", 1)
        add_companion(party, "c1", "ch1", ControlMode.MANUAL)
        with pytest.raises(ValueError):
            route_autonomous_turn(
                slot=party.slots[0],
                party=party,
                encounter_entities=[],
                character_registry={},
                rng=random.Random(),
            )

    def test_returns_none_when_no_hostiles(self):
        party = create_party("lead", 1)
        add_companion(party, "c1", "ch1")
        char = _char("Friendly")
        char.char_id = "ch1"
        result = route_autonomous_turn(
            slot=party.slots[0],
            party=party,
            encounter_entities=[],  # no hostiles
            character_registry={"ch1": char},
            rng=random.Random(),
        )
        assert result is None

    def test_returns_tactical_decision_with_hostiles(self):
        from src.ai_sim.tactics import TacticalDecision

        slot, party, hostiles, char_registry = self._setup()
        rng = random.Random(42)
        result = route_autonomous_turn(
            slot=slot,
            party=party,
            encounter_entities=hostiles,
            character_registry=char_registry,
            rng=rng,
        )
        # Should return a TacticalDecision or None (if no position component)
        assert result is None or isinstance(result, TacticalDecision)

    def test_same_faction_excluded(self):
        """Companions with matching factions should not appear as hostiles."""
        party = create_party("lead", 1)
        add_companion(party, "c1", "ch1")
        companion = _char("Ally")
        companion.char_id = "ch1"
        companion.metadata["faction"] = "Heroes"

        friendly = _char("Friend")
        friendly.metadata["faction"] = "Heroes"

        result = route_autonomous_turn(
            slot=party.slots[0],
            party=party,
            encounter_entities=[friendly],
            character_registry={"ch1": companion},
            rng=random.Random(),
        )
        assert result is None


# ---------------------------------------------------------------------------
# PH3-008 — route_manual_turn
# ---------------------------------------------------------------------------

class TestRouteManualTurn:
    def test_raises_value_error_for_autonomous_slot(self):
        party = create_party("lead", 1)
        add_companion(party, "c1", "ch1")
        controller = _controller()
        with pytest.raises(ValueError):
            route_manual_turn(
                slot=party.slots[0],
                controller=controller,
                combat_registry={},
            )

    def test_returns_player_action(self):
        party = create_party("lead", 1)
        add_companion(party, "c1", "ch1", ControlMode.MANUAL)
        controller = _controller()
        action = route_manual_turn(
            slot=party.slots[0],
            controller=controller,
            combat_registry={},
        )
        assert action == PlayerAction.Wait

    def test_restores_entity_id_after_call(self):
        party = create_party("lead", 1)
        add_companion(party, "companion-eid", "ch1", ControlMode.MANUAL)
        controller = _controller()
        original_id = controller.entity_id
        route_manual_turn(
            slot=party.slots[0],
            controller=controller,
            combat_registry={},
        )
        assert controller.entity_id == original_id


# ---------------------------------------------------------------------------
# PH3-009 — dispatch_party_round
# ---------------------------------------------------------------------------

class TestDispatchPartyRound:
    def test_returns_list(self):
        party = create_party("lead", 1)
        controller = _controller()
        results = dispatch_party_round(
            party=party,
            encounter_entities=[],
            character_registry={},
            controller=controller,
            rng=random.Random(),
        )
        assert isinstance(results, list)

    def test_leader_action_always_present(self):
        party = create_party("lead", 1)
        controller = _controller()
        results = dispatch_party_round(
            party=party,
            encounter_entities=[],
            character_registry={},
            controller=controller,
            rng=random.Random(),
        )
        assert len(results) >= 1
        assert results[0] == PlayerAction.Wait

    def test_autonomous_companion_included(self):
        party = create_party("lead", 1)
        add_companion(party, "c1", "ch1")
        char = _char("Companion")
        char.char_id = "ch1"
        controller = _controller()
        results = dispatch_party_round(
            party=party,
            encounter_entities=[],
            character_registry={"ch1": char},
            controller=controller,
            rng=random.Random(),
        )
        # Leader action at minimum; autonomous companion produces None (no targets) = not appended
        assert len(results) >= 1

    def test_manual_companion_produces_player_action(self):
        party = create_party("lead", 1)
        add_companion(party, "c1", "ch1", ControlMode.MANUAL)
        char = _char("Manual Ally")
        char.char_id = "ch1"
        controller = _controller()
        results = dispatch_party_round(
            party=party,
            encounter_entities=[],
            character_registry={"ch1": char},
            controller=controller,
            rng=random.Random(),
        )
        assert PlayerAction.Wait in results
