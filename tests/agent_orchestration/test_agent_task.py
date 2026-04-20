"""
tests/agent_orchestration/test_agent_task.py
--------------------------------------------
Unit tests for src.agent_orchestration.agent_task (AgentTask).
"""

import json
import pytest

from src.agent_orchestration.agent_task import AgentTask, TaskStatus, TaskType


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

class TestAgentTaskConstruction:
    def test_required_fields(self):
        t = AgentTask(task_type="generate_dungeon", prompt="Build a dungeon.")
        assert t.task_type == "generate_dungeon"
        assert t.prompt == "Build a dungeon."

    def test_task_id_auto_generated(self):
        t = AgentTask(task_type="roll_npc_stats", prompt="Roll stats.")
        assert isinstance(t.task_id, str) and len(t.task_id) == 36

    def test_explicit_task_id(self):
        t = AgentTask(task_type="write_lore", prompt="x", task_id="my-id")
        assert t.task_id == "my-id"

    def test_default_status_pending(self):
        t = AgentTask(task_type="write_lore", prompt="x")
        assert t.status is TaskStatus.PENDING

    def test_default_max_tokens(self):
        t = AgentTask(task_type="write_lore", prompt="x")
        assert t.max_tokens == 2048

    def test_default_priority(self):
        t = AgentTask(task_type="write_lore", prompt="x")
        assert t.priority == 5

    def test_custom_max_tokens(self):
        t = AgentTask(task_type="write_lore", prompt="x", max_tokens=4096)
        assert t.max_tokens == 4096

    def test_custom_priority(self):
        t = AgentTask(task_type="write_lore", prompt="x", priority=1)
        assert t.priority == 1

    def test_context_defaults_none(self):
        t = AgentTask(task_type="write_lore", prompt="x")
        assert t.context is None

    def test_result_defaults_none(self):
        t = AgentTask(task_type="write_lore", prompt="x")
        assert t.result is None

    def test_error_defaults_none(self):
        t = AgentTask(task_type="write_lore", prompt="x")
        assert t.error is None

    def test_created_at_is_iso_string(self):
        t = AgentTask(task_type="write_lore", prompt="x")
        assert isinstance(t.created_at, str) and "T" in t.created_at

    def test_tags_default_empty(self):
        t = AgentTask(task_type="write_lore", prompt="x")
        assert t.tags == []

    def test_retry_defaults(self):
        t = AgentTask(task_type="write_lore", prompt="x")
        assert t.retry_count == 0
        assert t.max_retries == 3

    def test_slots_enabled(self):
        """Verify that slots=True prevents __dict__ creation."""
        t = AgentTask(task_type="write_lore", prompt="x")
        assert not hasattr(t, "__dict__")


# ---------------------------------------------------------------------------
# Lifecycle transitions
# ---------------------------------------------------------------------------

class TestAgentTaskLifecycle:
    def test_mark_in_progress(self):
        t = AgentTask(task_type="generate_dungeon", prompt="x")
        t.mark_in_progress()
        assert t.status is TaskStatus.IN_PROGRESS

    def test_mark_in_progress_with_model_id(self):
        t = AgentTask(task_type="generate_dungeon", prompt="x")
        t.mark_in_progress(model_id="deepseek-coder-v2")
        assert t.model_id == "deepseek-coder-v2"

    def test_mark_in_progress_only_from_pending(self):
        t = AgentTask(task_type="generate_dungeon", prompt="x")
        t.mark_in_progress()
        with pytest.raises(RuntimeError):
            t.mark_in_progress()

    def test_complete(self):
        t = AgentTask(task_type="generate_dungeon", prompt="x")
        t.mark_in_progress()
        t.complete(result={"rooms": 5})
        assert t.status is TaskStatus.COMPLETED
        assert t.result == {"rooms": 5}
        assert t.completed_at is not None

    def test_complete_only_from_in_progress(self):
        t = AgentTask(task_type="generate_dungeon", prompt="x")
        with pytest.raises(RuntimeError):
            t.complete(result={})

    def test_fail_retries(self):
        t = AgentTask(task_type="generate_dungeon", prompt="x", max_retries=2)
        t.mark_in_progress()
        t.fail(error="timeout")
        # First failure: retry_count=1, still under max_retries=2 → PENDING
        assert t.status is TaskStatus.PENDING
        assert t.retry_count == 1
        assert t.error == "timeout"

    def test_fail_exhausts_retries(self):
        t = AgentTask(task_type="generate_dungeon", prompt="x", max_retries=1)
        t.mark_in_progress()
        t.fail(error="out of memory")
        # retry_count=1 >= max_retries=1 → FAILED
        assert t.status is TaskStatus.FAILED
        assert t.completed_at is not None

    def test_fail_only_from_in_progress(self):
        t = AgentTask(task_type="generate_dungeon", prompt="x")
        with pytest.raises(RuntimeError):
            t.fail(error="nope")

    def test_cancel_from_pending(self):
        t = AgentTask(task_type="generate_dungeon", prompt="x")
        t.cancel()
        assert t.status is TaskStatus.CANCELLED
        assert t.completed_at is not None

    def test_cancel_from_in_progress(self):
        t = AgentTask(task_type="generate_dungeon", prompt="x")
        t.mark_in_progress()
        t.cancel()
        assert t.status is TaskStatus.CANCELLED

    def test_cancel_from_completed_raises(self):
        t = AgentTask(task_type="generate_dungeon", prompt="x")
        t.mark_in_progress()
        t.complete(result={})
        with pytest.raises(RuntimeError):
            t.cancel()

    def test_cancel_from_failed_raises(self):
        t = AgentTask(task_type="generate_dungeon", prompt="x", max_retries=0)
        t.mark_in_progress()
        t.fail(error="err")
        with pytest.raises(RuntimeError):
            t.cancel()


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

class TestAgentTaskQueries:
    def test_is_terminal_pending(self):
        t = AgentTask(task_type="write_lore", prompt="x")
        assert t.is_terminal is False

    def test_is_terminal_completed(self):
        t = AgentTask(task_type="write_lore", prompt="x")
        t.mark_in_progress()
        t.complete(result={})
        assert t.is_terminal is True

    def test_is_terminal_cancelled(self):
        t = AgentTask(task_type="write_lore", prompt="x")
        t.cancel()
        assert t.is_terminal is True

    def test_estimated_vram_mb(self):
        t = AgentTask(task_type="write_lore", prompt="x", max_tokens=1024)
        # 1024 tokens × 2 bytes / 1 MiB = 0.001953125
        assert t.estimated_vram_mb == pytest.approx(1024 * 2 / (1024 * 1024))


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

class TestAgentTaskSerialisation:
    def test_to_dict_contains_required_keys(self):
        t = AgentTask(task_type="roll_npc_stats", prompt="Roll it.")
        d = t.to_dict()
        for key in ("task_id", "task_type", "prompt", "status", "max_tokens"):
            assert key in d

    def test_from_dict_round_trip(self):
        original = AgentTask(
            task_type="write_lore",
            prompt="Write something.",
            priority=2,
            tags=["world", "lore"],
        )
        restored = AgentTask.from_dict(original.to_dict())
        assert restored.task_id == original.task_id
        assert restored.task_type == original.task_type
        assert restored.prompt == original.prompt
        assert restored.priority == original.priority
        assert restored.tags == ["world", "lore"]

    def test_to_json_round_trip(self):
        original = AgentTask(task_type="generate_dungeon", prompt="Go.")
        json_str = original.to_json()
        restored = AgentTask.from_json(json_str)
        assert restored.task_id == original.task_id

    def test_json_is_valid_json(self):
        t = AgentTask(task_type="roll_npc_stats", prompt="Roll it.")
        parsed = json.loads(t.to_json())
        assert parsed["task_type"] == "roll_npc_stats"


# ---------------------------------------------------------------------------
# Equality and hashing
# ---------------------------------------------------------------------------

class TestAgentTaskEquality:
    def test_same_id_equal(self):
        t1 = AgentTask(task_type="a", prompt="b", task_id="same")
        t2 = AgentTask(task_type="c", prompt="d", task_id="same")
        assert t1 == t2

    def test_different_id_not_equal(self):
        t1 = AgentTask(task_type="a", prompt="b")
        t2 = AgentTask(task_type="a", prompt="b")
        assert t1 != t2

    def test_hashable_usable_in_set(self):
        t = AgentTask(task_type="a", prompt="b", task_id="hash-test")
        assert t in {t}

    def test_repr_contains_type(self):
        t = AgentTask(task_type="generate_dungeon", prompt="x")
        assert "generate_dungeon" in repr(t)


# ---------------------------------------------------------------------------
# TaskType enum
# ---------------------------------------------------------------------------

class TestTaskType:
    def test_generate_dungeon_value(self):
        assert TaskType.GENERATE_DUNGEON.value == "generate_dungeon"

    def test_custom_value(self):
        assert TaskType.CUSTOM.value == "custom"

    def test_all_members_have_string_values(self):
        for member in TaskType:
            assert isinstance(member.value, str)
