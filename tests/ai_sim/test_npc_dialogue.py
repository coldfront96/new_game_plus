"""Tests for PH2-007 · PH2-008 — NPC context snapshot and dialogue generator."""
from __future__ import annotations

import asyncio
import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from src.ai_sim.llm_bridge import (
    EntityNotFoundError,
    build_npc_context,
    generate_npc_dialogue,
)
from src.rules_engine.character_35e import Alignment, Character35e
from src.world_sim.factions import FactionRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entity(
    name: str = "Baran",
    char_class: str = "Fighter",
    level: int = 3,
    alignment: Alignment = Alignment.NEUTRAL_EVIL,
    chunk_id: str = "chunk_A",
    faction_name: str | None = "Orc Warband",
) -> Character35e:
    entity = Character35e(name=name, char_class=char_class, level=level, alignment=alignment)
    entity.metadata["chunk_id"] = chunk_id
    if faction_name:
        entity.metadata["faction_name"] = faction_name
    return entity


def _make_faction_registry() -> dict[str, FactionRecord]:
    return {
        "Orc Warband": FactionRecord(
            name="Orc Warband",
            alignment=Alignment.CHAOTIC_EVIL,
            hostile_to=["Human Settlement", "Goblin Warband"],
        ),
        "Human Settlement": FactionRecord(
            name="Human Settlement",
            alignment=Alignment.LAWFUL_NEUTRAL,
            hostile_to=["Orc Warband"],
        ),
    }


# ---------------------------------------------------------------------------
# PH2-007 · build_npc_context
# ---------------------------------------------------------------------------

class TestBuildNpcContext:
    def test_returns_dict(self):
        entity = _make_entity()
        ctx = build_npc_context(entity.char_id, {entity.char_id: entity}, _make_faction_registry())
        assert isinstance(ctx, dict)

    def test_required_keys_present(self):
        entity = _make_entity()
        ctx = build_npc_context(entity.char_id, {entity.char_id: entity}, _make_faction_registry())
        expected = {
            "entity_id", "name", "current_hp", "max_hp", "ac", "bab",
            "conditions", "faction_name", "alignment", "hostile_factions", "chunk_id",
        }
        assert expected == set(ctx.keys())

    def test_name_matches_entity(self):
        entity = _make_entity(name="Grimtooth")
        ctx = build_npc_context(entity.char_id, {entity.char_id: entity}, {})
        assert ctx["name"] == "Grimtooth"

    def test_hp_correct(self):
        entity = _make_entity(level=3)
        ctx = build_npc_context(entity.char_id, {entity.char_id: entity}, {})
        assert ctx["max_hp"] == entity.hit_points
        assert ctx["current_hp"] == entity.hit_points  # full HP when no metadata override

    def test_current_hp_from_metadata(self):
        entity = _make_entity()
        entity.metadata["current_hp"] = 5
        ctx = build_npc_context(entity.char_id, {entity.char_id: entity}, {})
        assert ctx["current_hp"] == 5

    def test_hostile_factions_from_registry(self):
        entity = _make_entity(faction_name="Orc Warband")
        ctx = build_npc_context(
            entity.char_id,
            {entity.char_id: entity},
            _make_faction_registry(),
        )
        assert "Human Settlement" in ctx["hostile_factions"]

    def test_no_faction_produces_empty_hostile_list(self):
        entity = _make_entity(faction_name=None)
        ctx = build_npc_context(entity.char_id, {entity.char_id: entity}, {})
        assert ctx["hostile_factions"] == []
        assert ctx["faction_name"] is None

    def test_chunk_id_in_context(self):
        entity = _make_entity(chunk_id="chunk_Z")
        ctx = build_npc_context(entity.char_id, {entity.char_id: entity}, {})
        assert ctx["chunk_id"] == "chunk_Z"

    def test_entity_not_found_raises(self):
        with pytest.raises(EntityNotFoundError):
            build_npc_context("missing_id", {}, {})

    def test_conditions_from_metadata(self):
        entity = _make_entity()
        entity.metadata["active_conditions"] = ["Blinded", "Prone"]
        ctx = build_npc_context(entity.char_id, {entity.char_id: entity}, {})
        assert "Blinded" in ctx["conditions"]
        assert "Prone" in ctx["conditions"]


# ---------------------------------------------------------------------------
# PH2-008 · generate_npc_dialogue
# ---------------------------------------------------------------------------

class TestGenerateNpcDialogue:
    def _ndjson_response(self, tokens: list[str]) -> BytesIO:
        """Build a fake Ollama NDJSON streaming response."""
        lines = b""
        for i, tok in enumerate(tokens):
            is_done = (i == len(tokens) - 1)
            line = json.dumps({"response": tok, "done": is_done})
            lines += line.encode() + b"\n"
        return BytesIO(lines)

    def _run_generator(self, gen) -> list[str]:
        """Collect all tokens from an AsyncIterator synchronously."""
        async def _collect():
            return [token async for token in gen]
        return asyncio.run(_collect())

    def test_yields_tokens_from_stream(self):
        entity = _make_entity()
        registry = {entity.char_id: entity}
        fake_response = self._ndjson_response(["Hello", " there", "!"])

        mock_resp = MagicMock()
        mock_resp.__iter__ = lambda s: iter(fake_response)
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            gen = generate_npc_dialogue(
                entity.char_id, "Hi!", registry, _make_faction_registry()
            )
            tokens = self._run_generator(gen)

        assert tokens == ["Hello", " there", "!"]

    def test_fallback_on_connection_refused(self):
        import urllib.error
        entity = _make_entity(name="Grog")
        registry = {entity.char_id: entity}

        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
            gen = generate_npc_dialogue(
                entity.char_id, "Hello", registry, _make_faction_registry()
            )
            tokens = self._run_generator(gen)

        assert len(tokens) == 1
        assert "Grog" in tokens[0] or "nothing" in tokens[0].lower()

    def test_fallback_on_unknown_entity(self):
        gen = generate_npc_dialogue(
            "bad_id", "Hello", {}, {}
        )
        tokens = self._run_generator(gen)
        assert len(tokens) == 1
        assert "nothing" in tokens[0].lower() or "Unknown" in tokens[0]

    def test_custom_api_url_and_model(self):
        entity = _make_entity()
        registry = {entity.char_id: entity}
        fake_response = self._ndjson_response(["OK"])

        mock_resp = MagicMock()
        mock_resp.__iter__ = lambda s: iter(fake_response)
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        captured = {}

        def _fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=_fake_urlopen):
            gen = generate_npc_dialogue(
                entity.char_id,
                "Hi",
                registry,
                {},
                api_url="http://custom:9999/api/generate",
                model="mymodel",
            )
            self._run_generator(gen)

        assert captured["url"] == "http://custom:9999/api/generate"
