"""Tests for EM-008 — SpellcasterAI (behavior.py extension)."""
from __future__ import annotations

import asyncio
import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.ai_sim.behavior import SpellcasterAI


SPELL_DIR = "data/srd_3.5/spells"


class TestSpellcasterAI:
    def test_creation_defaults(self):
        ai = SpellcasterAI(char_class="Wizard", level=5)
        assert ai.char_class == "Wizard"
        assert ai.level == 5
        assert ai.prepared_spells == []
        assert ai.llm_client is None

    def test_slots_no_dict(self):
        ai = SpellcasterAI(char_class="Cleric", level=3)
        assert not hasattr(ai, "__dict__")

    def test_max_spell_level_low(self):
        ai = SpellcasterAI(char_class="Wizard", level=1)
        assert ai._max_spell_level == 1

    def test_max_spell_level_cap(self):
        ai = SpellcasterAI(char_class="Wizard", level=20)
        assert ai._max_spell_level == 9

    def test_prepare_daily_no_llm_deterministic(self):
        """Without an LLM, picks first N spells from files."""
        ai = SpellcasterAI(char_class="Wizard", level=3)
        result = asyncio.run(ai.prepare_daily("forest", SPELL_DIR))
        assert isinstance(result, list)
        assert len(result) <= 3
        assert ai.prepared_spells == result

    def test_prepare_daily_with_mock_llm_json_response(self):
        """LLM returns JSON array — parse spell names from it."""
        # Get real spell names from level_0.json to guarantee a match
        with open(os.path.join(SPELL_DIR, "level_0.json")) as f:
            spells = json.load(f)
        name0 = spells[0]["name"]
        name1 = spells[1]["name"] if len(spells) > 1 else name0

        mock_client = MagicMock()
        mock_client.query_text = AsyncMock(return_value=json.dumps([name0, name1]))

        ai = SpellcasterAI(char_class="Wizard", level=5, llm_client=mock_client)
        result = asyncio.run(ai.prepare_daily("open plains", SPELL_DIR))

        assert name0 in result
        mock_client.query_text.assert_called_once()

    def test_prepare_daily_llm_returns_garbage_fallback(self):
        """LLM returns unparseable text → line-by-line fallback or empty list."""
        mock_client = MagicMock()
        mock_client.query_text = AsyncMock(return_value="No spells match this environment.")

        ai = SpellcasterAI(char_class="Wizard", level=2, llm_client=mock_client)
        result = asyncio.run(ai.prepare_daily("void", SPELL_DIR))
        assert isinstance(result, list)   # must not raise

    def test_prepare_daily_updates_prepared_spells(self):
        ai = SpellcasterAI(char_class="Cleric", level=4)
        asyncio.run(ai.prepare_daily("mountain pass", SPELL_DIR))
        assert ai.prepared_spells is not None

    def test_parse_spell_names_json_array(self):
        known = ["Fireball", "Fly", "Invisibility"]
        raw = json.dumps(["Fireball", "Invisibility"])
        result = SpellcasterAI._parse_spell_names(raw, known, limit=5)
        assert "Fireball" in result
        assert "Invisibility" in result

    def test_parse_spell_names_case_insensitive(self):
        known = ["Fireball", "Magic Missile"]
        raw = '["fireball", "magic missile"]'
        result = SpellcasterAI._parse_spell_names(raw, known, limit=5)
        assert "Fireball" in result

    def test_parse_spell_names_limit_respected(self):
        known = ["A", "B", "C", "D", "E"]
        raw = json.dumps(known)
        result = SpellcasterAI._parse_spell_names(raw, known, limit=2)
        assert len(result) == 2
