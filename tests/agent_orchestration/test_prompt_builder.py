"""Tests for ``src.agent_orchestration.prompt_builder`` (Task 10)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.agent_orchestration import AgentTask, PromptBuilder, TaskType


def _make_task(task_type: str = TaskType.ROLL_NPC_STATS.value, **kw) -> AgentTask:
    return AgentTask(
        task_type=task_type,
        prompt=kw.get("prompt", "Generate a level 5 Fighter."),
        max_tokens=kw.get("max_tokens", 1024),
        priority=kw.get("priority", 3),
        context=kw.get("context"),
    )


def test_build_returns_system_and_user_messages():
    builder = PromptBuilder()
    task = _make_task()
    msgs = builder.build(task)
    assert msgs[0]["role"] == "system"
    assert msgs[-1]["role"] == "user"
    assert msgs[-1]["content"] == task.prompt


def test_build_injects_relevant_srd_context():
    builder = PromptBuilder()
    task = _make_task(task_type=TaskType.ROLL_NPC_STATS.value)
    msgs = builder.build(task)
    system_text = msgs[0]["content"]
    # NPC stats task pulls races + classes + feats.  At least one race
    # marker should appear in the merged context.
    assert "Reference SRD context" in system_text
    assert "Human" in system_text or "Elf" in system_text


def test_build_includes_task_context_when_present():
    builder = PromptBuilder()
    task = _make_task(context={"hint": "low INT, high CHA"})
    msgs = builder.build(task)
    # Context message inserted between primary system and user.
    assert any(
        m["role"] == "system" and "low INT" in m["content"]
        for m in msgs
    )


def test_build_respects_token_budget(tmp_path: Path):
    # Tiny budget should aggressively trim; user prompt remains untouched.
    builder = PromptBuilder()
    task = _make_task()
    msgs = builder.build(task, context_budget_tokens=64)
    estimated = builder.estimate_tokens(msgs)
    # Even with tiny budget, the user prompt (~10 tokens) is preserved.
    assert msgs[-1]["content"] == task.prompt
    # Total must be in a reasonable bound — not unlimited.
    assert estimated < 4_000


def test_unknown_task_type_uses_no_srd_context():
    builder = PromptBuilder()
    task = _make_task(task_type="custom")
    msgs = builder.build(task)
    # No SRD reference block when no categories are declared for this type.
    assert "Reference SRD context" not in msgs[0]["content"]


def test_custom_data_dir_returns_empty_context(tmp_path: Path):
    builder = PromptBuilder(data_dir=tmp_path)
    task = _make_task()
    msgs = builder.build(task)
    # Empty dirs → no SRD content injected at all.
    assert "Reference SRD context" not in msgs[0]["content"]


# ---------------------------------------------------------------------------
# IP-safety mode
# ---------------------------------------------------------------------------

class TestIpSafeMode:
    """ip_safe_mode=True injects the Clean-Room Translation Protocol reminder
    into content-generation prompts but not into non-content tasks."""

    _CONTENT_TYPES = [
        TaskType.GENERATE_ENCOUNTER.value,
        TaskType.GENERATE_DUNGEON.value,
        TaskType.ROLL_NPC_STATS.value,
        TaskType.WRITE_LORE.value,
        TaskType.CUSTOM.value,
    ]

    def test_ip_safe_on_by_default(self):
        builder = PromptBuilder()
        assert builder.ip_safe_mode is True

    def test_reminder_injected_for_encounter_task(self):
        builder = PromptBuilder(ip_safe_mode=True)
        task = _make_task(task_type=TaskType.GENERATE_ENCOUNTER.value)
        msgs = builder.build(task)
        system = msgs[0]["content"]
        assert "IP SAFETY" in system
        assert "Mind Flayer" in system
        assert "Beholder" in system

    def test_reminder_injected_for_npc_stats_task(self):
        builder = PromptBuilder(ip_safe_mode=True)
        task = _make_task(task_type=TaskType.ROLL_NPC_STATS.value)
        system = builder.build(task)[0]["content"]
        assert "IP SAFETY" in system

    def test_reminder_injected_for_write_lore_task(self):
        builder = PromptBuilder(ip_safe_mode=True)
        task = _make_task(task_type=TaskType.WRITE_LORE.value)
        system = builder.build(task)[0]["content"]
        assert "IP SAFETY" in system

    def test_reminder_not_injected_when_mode_off(self):
        builder = PromptBuilder(ip_safe_mode=False)
        for tt in self._CONTENT_TYPES:
            task = _make_task(task_type=tt)
            system = builder.build(task)[0]["content"]
            assert "IP SAFETY" not in system, f"Unexpected reminder for {tt}"

    def test_reminder_absent_for_code_generation(self):
        """CODE_GENERATION is not a content-generation task — no reminder."""
        builder = PromptBuilder(ip_safe_mode=True)
        task = _make_task(task_type=TaskType.CODE_GENERATION.value)
        system = builder.build(task)[0]["content"]
        assert "IP SAFETY" not in system

    def test_srd_context_and_reminder_coexist(self):
        """Reminder and SRD context block should both appear in the same system message."""
        builder = PromptBuilder(ip_safe_mode=True)
        task = _make_task(task_type=TaskType.ROLL_NPC_STATS.value)
        system = builder.build(task)[0]["content"]
        assert "IP SAFETY" in system
        assert "Reference SRD context" in system
