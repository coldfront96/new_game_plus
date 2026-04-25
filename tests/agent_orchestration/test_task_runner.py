"""Tests for ``src.agent_orchestration.task_runner`` (Task 10)."""

from __future__ import annotations

import asyncio
import json
from typing import List

import pytest

from src.agent_orchestration import (
    AgentTask,
    LLMTaskRunner,
    PromptBuilder,
    ResultParser,
    Scheduler,
    TaskStatus,
    TaskType,
)
from src.overseer_ui import OverseerQueue


def _make_task() -> AgentTask:
    return AgentTask(
        task_type=TaskType.ROLL_NPC_STATS.value,
        prompt="Generate a level 3 Cleric.",
        max_tokens=512,
        priority=1,
        max_retries=2,
    )


def _valid_npc_payload() -> str:
    return json.dumps({
        "name": "Mira",
        "char_class": "Cleric",
        "level": 3,
        "strength": 12,
        "dexterity": 10,
        "constitution": 14,
        "intelligence": 11,
        "wisdom": 16,
        "charisma": 13,
    })


def test_runner_completes_valid_task():
    sched = Scheduler()
    task = _make_task()
    sched.submit(task)
    runner = LLMTaskRunner(
        scheduler=sched,
        prompt_builder=PromptBuilder(),
        result_parser=ResultParser(),
        completion_fn=lambda msgs: _valid_npc_payload(),
    )
    processed = runner.run_one_sync()
    assert processed is task
    assert task.status is TaskStatus.COMPLETED
    assert task.result["name"] == "Mira"


def test_runner_fails_and_retries_on_bad_json():
    sched = Scheduler()
    task = _make_task()
    sched.submit(task)
    calls: List[int] = []

    def stub(messages):
        calls.append(1)
        return "this is not JSON"

    runner = LLMTaskRunner(
        scheduler=sched,
        prompt_builder=PromptBuilder(),
        result_parser=ResultParser(),
        completion_fn=stub,
    )
    runner.run_one_sync()
    # First failure → re-queued for retry.
    assert task.status is TaskStatus.PENDING
    runner.run_one_sync()
    # Second failure → terminal FAILED (max_retries=2).
    assert task.status is TaskStatus.FAILED
    assert len(calls) == 2


def test_runner_escalates_to_overseer_on_terminal_failure(tmp_path):
    sched = Scheduler()
    task = AgentTask(
        task_type=TaskType.ROLL_NPC_STATS.value,
        prompt="…",
        max_retries=1,  # one retry allowed → fail twice → terminal
        priority=1,
    )
    sched.submit(task)
    queue = OverseerQueue(logs_dir=tmp_path)
    runner = LLMTaskRunner(
        scheduler=sched,
        prompt_builder=PromptBuilder(),
        result_parser=ResultParser(),
        completion_fn=lambda msgs: "no json",
        overseer_queue=queue,
    )
    runner.run_until_empty_sync()
    assert task.status is TaskStatus.FAILED
    # Escalated to the queue for human review.
    assert any(t.task_id == task.task_id for t in queue.pending())


def test_runner_handles_async_completion_fn():
    sched = Scheduler()
    task = _make_task()
    sched.submit(task)

    async def stub(messages):
        return _valid_npc_payload()

    runner = LLMTaskRunner(
        scheduler=sched,
        prompt_builder=PromptBuilder(),
        result_parser=ResultParser(),
        completion_fn=stub,
    )
    asyncio.run(runner.run_one())
    assert task.status is TaskStatus.COMPLETED


def test_runner_drains_multiple_tasks():
    sched = Scheduler(max_concurrency=1)
    for _ in range(3):
        sched.submit(_make_task())
    runner = LLMTaskRunner(
        scheduler=sched,
        prompt_builder=PromptBuilder(),
        result_parser=ResultParser(),
        completion_fn=lambda msgs: _valid_npc_payload(),
    )
    processed = runner.run_until_empty_sync()
    assert len(processed) == 3
    assert all(t.status is TaskStatus.COMPLETED for t in processed)


def test_runner_records_model_id():
    sched = Scheduler()
    task = _make_task()
    sched.submit(task)
    runner = LLMTaskRunner(
        scheduler=sched,
        prompt_builder=PromptBuilder(),
        result_parser=ResultParser(),
        completion_fn=lambda msgs: _valid_npc_payload(),
        model_id="mistral-test",
    )
    runner.run_one_sync()
    assert task.model_id == "mistral-test"
