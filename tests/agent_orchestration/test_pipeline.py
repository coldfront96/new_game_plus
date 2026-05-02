"""Tests for src.agent_orchestration.pipeline (build_llm_pipeline factory)."""

from __future__ import annotations

import json

import pytest

from src.agent_orchestration import AgentTask, LLMTaskRunner, TaskStatus, TaskType
from src.agent_orchestration.pipeline import build_llm_pipeline
from src.overseer_ui.overseer import OverseerQueue


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_encounter_payload() -> str:
    return json.dumps({"monsters": ["Goblin", "Wolf"], "terrain": "forest"})


def _valid_npc_payload() -> str:
    return json.dumps({
        "name": "Elara",
        "char_class": "Ranger",
        "level": 4,
        "strength": 14,
        "dexterity": 16,
        "constitution": 12,
        "intelligence": 11,
        "wisdom": 13,
        "charisma": 10,
    })


def _stub_runner(response: str, *, ip_safe: bool = True) -> LLMTaskRunner:
    """Return a pipeline runner with a synchronous stub completion_fn."""
    runner = build_llm_pipeline(ip_safe=ip_safe)
    runner.completion_fn = lambda msgs: response
    return runner


# ---------------------------------------------------------------------------
# Factory construction
# ---------------------------------------------------------------------------

class TestBuildLlmPipeline:
    def test_returns_llm_task_runner(self):
        runner = build_llm_pipeline()
        assert isinstance(runner, LLMTaskRunner)

    def test_scheduler_starts_empty(self):
        runner = build_llm_pipeline()
        assert runner.scheduler.pending_count == 0

    def test_overseer_queue_wired(self):
        q = OverseerQueue()
        runner = build_llm_pipeline(overseer_queue=q)
        assert runner.overseer_queue is q

    def test_overseer_none_by_default(self):
        runner = build_llm_pipeline()
        assert runner.overseer_queue is None

    def test_model_id_defaults_to_model_name(self):
        runner = build_llm_pipeline(model="llama3")
        assert runner.model_id == "llama3"

    def test_explicit_model_id_overrides(self):
        runner = build_llm_pipeline(model="llama3", model_id="llama3-8b-gguf-q4")
        assert runner.model_id == "llama3-8b-gguf-q4"

    def test_ip_safe_mode_propagates_to_prompt_builder(self):
        runner_safe = build_llm_pipeline(ip_safe=True)
        runner_unsafe = build_llm_pipeline(ip_safe=False)
        assert runner_safe.prompt_builder.ip_safe_mode is True
        assert runner_unsafe.prompt_builder.ip_safe_mode is False


# ---------------------------------------------------------------------------
# End-to-end task execution (stub LLM — no network)
# ---------------------------------------------------------------------------

class TestPipelineExecution:
    def test_valid_encounter_task_completes(self):
        runner = _stub_runner(_valid_encounter_payload())
        task = AgentTask(
            task_type=TaskType.GENERATE_ENCOUNTER.value,
            prompt="Forest encounter, APL 3.",
            max_tokens=512,
            priority=2,
        )
        runner.scheduler.submit(task)
        result = runner.run_one_sync()
        assert result is task
        assert task.status is TaskStatus.COMPLETED
        assert "Goblin" in task.result["monsters"]

    def test_valid_npc_task_completes(self):
        runner = _stub_runner(_valid_npc_payload())
        task = AgentTask(
            task_type=TaskType.ROLL_NPC_STATS.value,
            prompt="Generate a level 4 Ranger.",
            max_tokens=512,
            priority=3,
        )
        runner.scheduler.submit(task)
        result = runner.run_one_sync()
        assert result is task
        assert task.status is TaskStatus.COMPLETED
        assert task.result["char_class"] == "Ranger"

    def test_invalid_json_response_fails_and_escalates(self):
        q = OverseerQueue()
        runner = build_llm_pipeline(overseer_queue=q)
        runner.completion_fn = lambda msgs: "this is not json"
        task = AgentTask(
            task_type=TaskType.ROLL_NPC_STATS.value,
            prompt="Generate stats.",
            max_tokens=256,
            priority=5,
            max_retries=0,
        )
        runner.scheduler.submit(task)
        runner.run_one_sync()
        assert task.status is TaskStatus.FAILED
        assert len(q) == 1  # escalated to Overseer

    def test_empty_scheduler_returns_none(self):
        runner = build_llm_pipeline()
        assert runner.run_one_sync() is None


# ---------------------------------------------------------------------------
# IP-safety: reminder injected into system prompt for content tasks
# ---------------------------------------------------------------------------

class TestIpSafetyInjection:
    _CONTENT_TYPES = [
        TaskType.GENERATE_ENCOUNTER.value,
        TaskType.GENERATE_DUNGEON.value,
        TaskType.ROLL_NPC_STATS.value,
        TaskType.WRITE_LORE.value,
    ]

    def _capture_system_prompt(self, task_type: str) -> str:
        """Run the pipeline with a spy completion_fn to capture messages."""
        captured: list[list] = []

        def _spy(msgs):
            captured.append(msgs)
            return json.dumps({"monsters": [], "rooms": [], "name": "X",
                               "char_class": "Fighter", "level": 1,
                               "strength": 10, "dexterity": 10, "constitution": 10,
                               "intelligence": 10, "wisdom": 10, "charisma": 10,
                               "title": "T", "body": "B",
                               "language": "python", "code": "pass"})

        runner = build_llm_pipeline(ip_safe=True)
        runner.completion_fn = _spy
        task = AgentTask(
            task_type=task_type,
            prompt="Test.",
            max_tokens=256,
            priority=1,
            max_retries=0,
        )
        runner.scheduler.submit(task)
        runner.run_one_sync()
        assert captured, "completion_fn was never called"
        system_msg = next(m for m in captured[0] if m["role"] == "system")
        return system_msg["content"]

    def test_ip_reminder_present_for_encounter_task(self):
        content = self._capture_system_prompt(TaskType.GENERATE_ENCOUNTER.value)
        assert "IP SAFETY" in content
        assert "Mind Flayer" in content

    def test_ip_reminder_present_for_npc_stats_task(self):
        content = self._capture_system_prompt(TaskType.ROLL_NPC_STATS.value)
        assert "IP SAFETY" in content

    def test_ip_reminder_absent_when_mode_off(self):
        runner = build_llm_pipeline(ip_safe=False)
        captured: list[list] = []
        runner.completion_fn = lambda msgs: (captured.append(msgs), _valid_npc_payload())[1]
        task = AgentTask(
            task_type=TaskType.ROLL_NPC_STATS.value,
            prompt="Test.",
            max_tokens=256,
            priority=1,
            max_retries=0,
        )
        runner.scheduler.submit(task)
        runner.run_one_sync()
        system_content = next(m for m in captured[0] if m["role"] == "system")["content"]
        assert "IP SAFETY" not in system_content
