"""
tests/ai_sim/test_llm_bridge.py
--------------------------------
Unit tests for the LLM Bridge System.

Tests verify:
* :class:`~src.ai_sim.llm_bridge.CognitiveState` correctly compresses a
  :class:`~src.rules_engine.character_35e.Character35e` stat block.
* :class:`~src.ai_sim.llm_bridge.LLMClient` correctly formats and sends a
  request, and parses the OpenAI-compatible response.
* :func:`~src.ai_sim.systems._parse_llm_response` handles JSON, XML, and
  plain-text fallback formats.
* :class:`~src.ai_sim.systems.CognitionSystem` schedules an async LLM query
  and injects a valid :class:`~src.ai_sim.systems.LLMIntent` into the pending
  queue.
* :class:`~src.ai_sim.components.MemoryBank` correctly rolls over entries and
  caps at capacity.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ai_sim.components import MemoryBank
from src.ai_sim.entity import Entity
from src.ai_sim.llm_bridge import CognitiveState, LLMClient
from src.ai_sim.systems import (
    CognitionSystem,
    LLMIntent,
    _parse_llm_response,
)
from src.core.event_bus import EventBus
from src.rules_engine.character_35e import Character35e


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def wizard():
    return Character35e(
        name="Zara",
        char_class="Wizard",
        level=5,
        intelligence=18,
    )


@pytest.fixture
def fighter():
    return Character35e(
        name="Aldric",
        char_class="Fighter",
        level=3,
        strength=16,
    )


@pytest.fixture
def bus():
    return EventBus()


# ---------------------------------------------------------------------------
# MemoryBank tests
# ---------------------------------------------------------------------------

class TestMemoryBank:
    def test_record_adds_entry(self):
        bank = MemoryBank()
        bank.record("I attacked the Orc")
        assert bank.recent() == ["I attacked the Orc"]

    def test_record_rolls_over_at_capacity(self):
        bank = MemoryBank(capacity=3)
        for i in range(5):
            bank.record(f"event {i}")
        entries = bank.recent()
        assert len(entries) == 3
        assert entries == ["event 2", "event 3", "event 4"]

    def test_recent_returns_copy(self):
        bank = MemoryBank()
        bank.record("first event")
        copy = bank.recent()
        copy.append("injected")
        assert len(bank.recent()) == 1

    def test_default_capacity_is_ten(self):
        bank = MemoryBank()
        for i in range(15):
            bank.record(f"e{i}")
        assert len(bank.recent()) == 10

    def test_empty_bank(self):
        bank = MemoryBank()
        assert bank.recent() == []


# ---------------------------------------------------------------------------
# CognitiveState tests
# ---------------------------------------------------------------------------

class TestCognitiveState:
    def test_from_character_basic_fields(self, wizard):
        state = CognitiveState.from_character(wizard, visible_entities=[])
        assert state.character_name == "Zara"
        assert state.char_class == "Wizard"
        assert state.level == 5
        assert state.current_hp > 0
        assert state.max_hp == state.current_hp
        assert state.conditions == []
        assert state.visible_entities == []

    def test_action_tracker_all_available_by_default(self, wizard):
        state = CognitiveState.from_character(wizard, visible_entities=[])
        assert state.action_tracker == {
            "standard_used": False,
            "move_used": False,
            "swift_used": False,
        }

    def test_action_tracker_from_real_tracker(self, wizard):
        from src.rules_engine.actions import ActionTracker
        tracker = ActionTracker(standard_used=True, move_used=False, swift_used=True)
        state = CognitiveState.from_character(
            wizard, visible_entities=[], action_tracker=tracker
        )
        assert state.action_tracker["standard_used"] is True
        assert state.action_tracker["move_used"] is False
        assert state.action_tracker["swift_used"] is True

    def test_conditions_forwarded(self, wizard):
        state = CognitiveState.from_character(
            wizard, visible_entities=[], conditions=["Blinded", "Prone"]
        )
        assert state.conditions == ["Blinded", "Prone"]

    def test_memory_log_forwarded(self, wizard):
        state = CognitiveState.from_character(
            wizard, visible_entities=[], memory_log=["I cast Mage Armor"]
        )
        assert state.memory_log == ["I cast Mage Armor"]

    def test_visible_entities_forwarded(self, wizard):
        vis = [{"name": "Goblin", "distance_ft": 10.0}]
        state = CognitiveState.from_character(wizard, visible_entities=vis)
        assert state.visible_entities == vis

    def test_to_dict_is_json_serialisable(self, wizard):
        state = CognitiveState.from_character(wizard, visible_entities=[])
        d = state.to_dict()
        serialised = json.dumps(d)
        recovered = json.loads(serialised)
        assert recovered["character_name"] == "Zara"
        assert "action_tracker" in recovered
        assert "known_spells" in recovered

    def test_to_dict_keys(self, wizard):
        state = CognitiveState.from_character(wizard, visible_entities=[])
        keys = set(state.to_dict().keys())
        assert keys == {
            "character_name", "char_class", "level", "current_hp", "max_hp",
            "conditions", "known_spells", "action_tracker", "visible_entities",
            "memory_log",
        }


# ---------------------------------------------------------------------------
# _parse_llm_response tests
# ---------------------------------------------------------------------------

class TestParseLLMResponse:
    def test_valid_json_object(self):
        raw = '{"action": "attack", "target": "Orc", "detail": "melee swing"}'
        intent = _parse_llm_response(raw)
        assert intent is not None
        assert intent.action == "attack"
        assert intent.target == "Orc"
        assert intent.detail == "melee swing"

    def test_json_embedded_in_prose(self):
        raw = 'I think I should {"action": "cast_spell", "target": "Goblin", "detail": "Magic Missile"} because it is optimal.'
        intent = _parse_llm_response(raw)
        assert intent is not None
        assert intent.action == "cast_spell"

    def test_json_case_insensitive_action(self):
        raw = '{"action": "ATTACK", "target": "Dragon"}'
        intent = _parse_llm_response(raw)
        assert intent is not None
        assert intent.action == "attack"

    def test_xml_verb_attribute(self):
        raw = '<action verb="move" target="North">advance toward the door</action>'
        intent = _parse_llm_response(raw)
        assert intent is not None
        assert intent.action == "move"
        assert intent.target == "North"
        assert intent.detail == "advance toward the door"

    def test_xml_action_attribute(self):
        raw = '<action action="withdraw" target=""/>retreat from combat'
        intent = _parse_llm_response(raw)
        assert intent is not None
        assert intent.action == "withdraw"

    def test_keyword_fallback(self):
        raw = "I will dodge quickly."
        intent = _parse_llm_response(raw)
        assert intent is not None
        assert intent.action == "dodge"

    def test_returns_none_for_empty_string(self):
        assert _parse_llm_response("") is None

    def test_returns_none_for_unrecognised_response(self):
        assert _parse_llm_response("Lorem ipsum dolor sit amet.") is None

    def test_wait_action(self):
        raw = '{"action": "wait"}'
        intent = _parse_llm_response(raw)
        assert intent is not None
        assert intent.action == "wait"

    def test_use_item_action(self):
        raw = '{"action": "use_item", "target": "Healing Potion"}'
        intent = _parse_llm_response(raw)
        assert intent is not None
        assert intent.action == "use_item"
        assert intent.target == "Healing Potion"

    def test_raw_stored_on_intent(self):
        raw = '{"action": "attack"}'
        intent = _parse_llm_response(raw)
        assert intent is not None
        assert intent.raw == raw


# ---------------------------------------------------------------------------
# LLMClient tests
# ---------------------------------------------------------------------------

class TestLLMClient:
    def _make_http_response(self, content: str) -> bytes:
        """Build a minimal OpenAI-compatible JSON response body."""
        payload = {
            "choices": [
                {"message": {"content": content}}
            ]
        }
        return json.dumps(payload).encode("utf-8")

    def test_query_model_returns_content(self, wizard):
        state = CognitiveState.from_character(wizard, visible_entities=[])
        expected_reply = '{"action": "attack", "target": "Orc"}'

        mock_resp = MagicMock()
        mock_resp.read.return_value = self._make_http_response(expected_reply)
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            client = LLMClient()
            result = asyncio.run(client.query_model(
                system_prompt="You are a Wizard.",
                cognitive_state=state,
                user_prompt="What do you do?",
            ))

        assert result == expected_reply

    def test_query_model_returns_empty_on_connection_error(self, wizard):
        import urllib.error
        state = CognitiveState.from_character(wizard, visible_entities=[])

        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            client = LLMClient()
            result = asyncio.run(client.query_model(
                system_prompt="You are a Wizard.",
                cognitive_state=state,
                user_prompt="What do you do?",
            ))

        assert result == ""

    def test_query_model_sends_correct_model(self, wizard):
        state = CognitiveState.from_character(wizard, visible_entities=[])
        captured: list = []

        def fake_urlopen(req, timeout=None):
            body = json.loads(req.data.decode("utf-8"))
            captured.append(body)
            mock_resp = MagicMock()
            mock_resp.read.return_value = self._make_http_response("ok")
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            client = LLMClient(model="llama3")
            asyncio.run(client.query_model("sys", state, "user"))

        assert captured[0]["model"] == "llama3"

    def test_query_model_includes_cognitive_state_in_system_prompt(self, wizard):
        state = CognitiveState.from_character(wizard, visible_entities=[])
        captured: list = []

        def fake_urlopen(req, timeout=None):
            body = json.loads(req.data.decode("utf-8"))
            captured.append(body)
            mock_resp = MagicMock()
            mock_resp.read.return_value = self._make_http_response("")
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            client = LLMClient()
            asyncio.run(client.query_model("Role prompt", state, "Decide."))

        system_msg = captured[0]["messages"][0]["content"]
        assert "CURRENT GAME STATE" in system_msg
        assert "Zara" in system_msg  # character name in state JSON

    def test_custom_base_url(self, wizard):
        state = CognitiveState.from_character(wizard, visible_entities=[])
        captured_urls: list = []

        def fake_urlopen(req, timeout=None):
            captured_urls.append(req.full_url)
            mock_resp = MagicMock()
            mock_resp.read.return_value = self._make_http_response("")
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            client = LLMClient(base_url="http://localhost:1234")
            asyncio.run(client.query_model("sys", state, "user"))

        assert captured_urls[0] == "http://localhost:1234/v1/chat/completions"


# ---------------------------------------------------------------------------
# CognitionSystem tests
# ---------------------------------------------------------------------------

class TestCognitionSystem:
    def _make_entity(self) -> Entity:
        e = Entity(name="test_entity")
        return e

    def _make_fsm_in_combat(self) -> MagicMock:
        from src.ai_sim.behavior import BehaviorState
        fsm = MagicMock()
        fsm.state = BehaviorState.IN_COMBAT
        return fsm

    def test_register_entity_increments_count(self, bus, fighter):
        system = CognitionSystem(event_bus=bus, llm_client=AsyncMock())
        entity = self._make_entity()
        bank = MemoryBank()
        system.register_entity(entity, fighter, bank)
        assert system.entity_count == 1

    def test_pop_intent_returns_none_before_query(self, bus, fighter):
        system = CognitionSystem(event_bus=bus, llm_client=AsyncMock())
        entity = self._make_entity()
        bank = MemoryBank()
        system.register_entity(entity, fighter, bank)
        assert system.pop_intent(entity) is None

    def test_pop_intent_returns_none_for_unknown_entity(self, bus):
        system = CognitionSystem(event_bus=bus, llm_client=AsyncMock())
        unknown = self._make_entity()
        assert system.pop_intent(unknown) is None

    def test_pop_intent_clears_pending(self, bus, fighter):
        """After pop_intent returns an intent, subsequent call returns None."""
        system = CognitionSystem(event_bus=bus, llm_client=AsyncMock())
        entity = self._make_entity()
        bank = MemoryBank()
        system.register_entity(entity, fighter, bank)

        # Manually inject an intent to simulate a completed async query
        entry = system._entries[0]
        entry.pending_intent = LLMIntent(action="attack", target="Goblin")

        first = system.pop_intent(entity)
        assert first is not None
        assert first.action == "attack"
        assert system.pop_intent(entity) is None

    def test_cognition_system_parses_json_response_into_attack_intent(
        self, bus, fighter
    ):
        """Full pipeline: mocked LLM returns JSON → CognitionSystem stores LLMIntent."""
        json_reply = '{"action": "attack", "target": "Orc Warrior", "detail": "melee longsword"}'

        mock_client = MagicMock()
        mock_client.query_model = AsyncMock(return_value=json_reply)

        system = CognitionSystem(event_bus=bus, llm_client=mock_client)
        entity = self._make_entity()

        # Attach a MemoryBank component and a mock FSM (IN_COMBAT state)
        bank = MemoryBank()
        bank.record("I entered combat with an Orc")
        entity.add_component(bank)
        entity.add_component(self._make_fsm_in_combat())

        system.register_entity(entity, fighter, bank)

        # Run the async machinery in a fresh event loop
        async def run():
            system.update()
            # Give the scheduled task a chance to complete
            await asyncio.sleep(0)
            await asyncio.sleep(0)

        asyncio.run(run())

        intent = system.pop_intent(entity)
        assert intent is not None
        assert intent.action == "attack"
        assert intent.target == "Orc Warrior"
        assert intent.detail == "melee longsword"

    def test_cognition_system_parses_xml_response(self, bus, fighter):
        """Full pipeline: mocked LLM returns XML → CognitionSystem stores LLMIntent."""
        xml_reply = '<action verb="cast_spell" target="Goblin">Magic Missile</action>'

        mock_client = MagicMock()
        mock_client.query_model = AsyncMock(return_value=xml_reply)

        system = CognitionSystem(event_bus=bus, llm_client=mock_client)
        entity = self._make_entity()
        bank = MemoryBank()
        entity.add_component(bank)
        entity.add_component(self._make_fsm_in_combat())

        system.register_entity(entity, fighter, bank)

        async def run():
            system.update()
            await asyncio.sleep(0)
            await asyncio.sleep(0)

        asyncio.run(run())

        intent = system.pop_intent(entity)
        assert intent is not None
        assert intent.action == "cast_spell"
        assert intent.target == "Goblin"

    def test_cognition_system_publishes_event_on_intent_ready(self, bus, fighter):
        """A ``llm_intent_ready`` event is published when an intent is resolved."""
        json_reply = '{"action": "move", "target": "Door"}'

        mock_client = MagicMock()
        mock_client.query_model = AsyncMock(return_value=json_reply)

        received_events: list = []
        bus.subscribe("llm_intent_ready", received_events.append)

        system = CognitionSystem(event_bus=bus, llm_client=mock_client)
        entity = self._make_entity()
        bank = MemoryBank()
        entity.add_component(bank)
        entity.add_component(self._make_fsm_in_combat())

        system.register_entity(entity, fighter, bank)

        async def run():
            system.update()
            await asyncio.sleep(0)
            await asyncio.sleep(0)

        asyncio.run(run())

        assert len(received_events) == 1
        assert received_events[0]["action"] == "move"

    def test_cognition_system_no_double_query(self, bus, fighter):
        """While a query is in flight, a second update does not fire another."""
        call_count: list[int] = [0]

        async def slow_query(*args, **kwargs) -> str:
            call_count[0] += 1
            await asyncio.sleep(10)  # simulate slow LLM
            return '{"action": "wait"}'

        mock_client = MagicMock()
        mock_client.query_model = slow_query

        system = CognitionSystem(event_bus=bus, llm_client=mock_client)
        entity = self._make_entity()
        bank = MemoryBank()
        entity.add_component(bank)
        entity.add_component(self._make_fsm_in_combat())

        system.register_entity(entity, fighter, bank)

        async def run():
            system.update()
            await asyncio.sleep(0)  # let first task start
            system.update()  # second update — should NOT enqueue another
            await asyncio.sleep(0)

        asyncio.run(run())

        assert call_count[0] == 1  # only one query was issued

    def test_inactive_entity_skipped(self, bus, fighter):
        """Inactive entities are not queried."""
        mock_client = MagicMock()
        mock_client.query_model = AsyncMock(return_value='{"action": "attack"}')

        system = CognitionSystem(event_bus=bus, llm_client=mock_client)
        entity = self._make_entity()
        entity.destroy()  # marks entity inactive
        bank = MemoryBank()
        entity.add_component(self._make_fsm_in_combat())

        system.register_entity(entity, fighter, bank)

        async def run():
            system.update()
            await asyncio.sleep(0)

        asyncio.run(run())

        assert mock_client.query_model.call_count == 0

    def test_llm_intent_dataclass_slots(self):
        """LLMIntent uses __slots__ (no __dict__)."""
        intent = LLMIntent(action="attack")
        assert not hasattr(intent, "__dict__")

    def test_memory_bank_log_forwarded_to_llm(self, bus, fighter):
        """Memory bank entries appear in the cognitive state sent to the LLM."""
        captured_states: list = []

        async def capture_query(system_prompt, cognitive_state, user_prompt):
            captured_states.append(cognitive_state)
            return '{"action": "wait"}'

        mock_client = MagicMock()
        mock_client.query_model = capture_query

        system = CognitionSystem(event_bus=bus, llm_client=mock_client)
        entity = self._make_entity()
        bank = MemoryBank()
        bank.record("I took 5 damage from the Orc")
        bank.record("I successfully cast Mage Armor")
        entity.add_component(bank)
        entity.add_component(self._make_fsm_in_combat())

        system.register_entity(entity, fighter, bank)

        async def run():
            system.update()
            await asyncio.sleep(0)
            await asyncio.sleep(0)

        asyncio.run(run())

        assert len(captured_states) == 1
        assert "I took 5 damage from the Orc" in captured_states[0].memory_log
        assert "I successfully cast Mage Armor" in captured_states[0].memory_log
