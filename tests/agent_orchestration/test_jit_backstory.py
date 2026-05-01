"""
tests/agent_orchestration/test_jit_backstory.py
-------------------------------------------------
Unit tests for PH6-009 — load_deep_lore, build_dialogue_context,
clear_dialogue_lore.
"""
from __future__ import annotations

import tempfile
import os
import pytest

from src.agent_orchestration.context_manager import (
    build_dialogue_context,
    clear_dialogue_lore,
    load_deep_lore,
    ContextWindow,
)
from src.ai_sim.entity import Entity


# ---------------------------------------------------------------------------
# PH6-009 · load_deep_lore
# ---------------------------------------------------------------------------

class TestLoadDeepLore:
    def test_returns_none_when_filepath_is_none(self):
        e = Entity(name="Nira")
        assert load_deep_lore(e) is None

    def test_returns_none_when_file_does_not_exist(self):
        e = Entity(name="Nira")
        e.deep_lore_filepath = "/nonexistent/path/to/lore.txt"
        assert load_deep_lore(e) is None

    def test_returns_file_content(self, tmp_path):
        lore_file = tmp_path / "nira_lore.txt"
        lore_file.write_text("Once upon a time in the Underdark…")
        e = Entity(name="Nira")
        e.deep_lore_filepath = str(lore_file)
        result = load_deep_lore(e)
        assert result == "Once upon a time in the Underdark…"

    def test_returns_full_multiline_content(self, tmp_path):
        text = "Line 1\nLine 2\nLine 3"
        lore_file = tmp_path / "lore.txt"
        lore_file.write_text(text)
        e = Entity(name="Nira")
        e.deep_lore_filepath = str(lore_file)
        assert load_deep_lore(e) == text

    def test_empty_file_returns_empty_string(self, tmp_path):
        lore_file = tmp_path / "empty.txt"
        lore_file.write_text("")
        e = Entity(name="Nira")
        e.deep_lore_filepath = str(lore_file)
        assert load_deep_lore(e) == ""


# ---------------------------------------------------------------------------
# PH6-009 · build_dialogue_context
# ---------------------------------------------------------------------------

class TestBuildDialogueContext:
    def test_returns_list_of_strings(self):
        e = Entity(name="Nira")
        result = build_dialogue_context("sys", "user", e)
        assert isinstance(result, list)
        assert all(isinstance(s, str) for s in result)

    def test_no_lore_single_chunk(self):
        e = Entity(name="Nira")
        result = build_dialogue_context("System prompt.", "User prompt.", e)
        assert len(result) >= 1
        assert "System prompt." in result[0]
        assert "User prompt." in result[0]

    def test_lore_prepended_to_system_prompt(self, tmp_path):
        lore_file = tmp_path / "lore.txt"
        lore_file.write_text("Ancient lore text.")
        e = Entity(name="Nira")
        e.deep_lore_filepath = str(lore_file)
        result = build_dialogue_context("System.", "User.", e)
        # Lore should appear before the system prompt in the first chunk
        combined = result[0]
        lore_pos = combined.find("Ancient lore text.")
        sys_pos  = combined.find("System.")
        assert lore_pos != -1
        assert sys_pos != -1
        assert lore_pos < sys_pos

    def test_missing_lore_file_does_not_raise(self):
        e = Entity(name="Nira")
        e.deep_lore_filepath = "/nonexistent/lore.txt"
        result = build_dialogue_context("System.", "User.", e)
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_accepts_custom_window(self):
        e = Entity(name="Nira")
        window = ContextWindow(model_id="test-model", max_tokens=512, reserved_for_response=128)
        result = build_dialogue_context("Sys.", "User.", e, window=window)
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# PH6-009 · clear_dialogue_lore
# ---------------------------------------------------------------------------

class TestClearDialogueLore:
    def test_none_is_noop(self):
        # Should not raise
        clear_dialogue_lore(None)

    def test_non_none_string_does_not_raise(self):
        clear_dialogue_lore("some lore text")

    def test_empty_string_does_not_raise(self):
        clear_dialogue_lore("")

    def test_typical_finally_pattern_does_not_raise(self, tmp_path):
        """Simulate the recommended finally-block usage."""
        lore_file = tmp_path / "lore.txt"
        lore_file.write_text("Lore content.")
        e = Entity(name="Nira")
        e.deep_lore_filepath = str(lore_file)

        lore_text = None
        try:
            lore_text = load_deep_lore(e)
            chunks = build_dialogue_context("Sys.", "User.", e)
            assert isinstance(chunks, list)
        finally:
            clear_dialogue_lore(lore_text)
        # No exception — test passes
