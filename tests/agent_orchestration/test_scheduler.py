"""Tests for ``src.agent_orchestration.scheduler`` (Task 10)."""

from __future__ import annotations

import pytest

from src.agent_orchestration import AgentTask, Scheduler, TaskStatus


def _task(priority: int, task_type: str = "roll_npc_stats") -> AgentTask:
    return AgentTask(
        task_type=task_type,
        prompt=f"do {task_type}",
        priority=priority,
        max_retries=2,
    )


def test_scheduler_dispatches_highest_priority_first():
    sched = Scheduler(max_concurrency=1)
    low = _task(priority=9)
    high = _task(priority=1)
    mid = _task(priority=5)
    sched.submit(low)
    sched.submit(high)
    sched.submit(mid)
    assert sched.next_task() is high
    sched.complete(high, result={"name": "x"})
    assert sched.next_task() is mid


def test_scheduler_respects_concurrency_cap():
    sched = Scheduler(max_concurrency=2)
    a, b, c = _task(1), _task(2), _task(3)
    sched.submit_many([a, b, c])
    first = sched.next_task()
    second = sched.next_task()
    third = sched.next_task()  # capped — should be None
    assert first is a and second is b
    assert third is None
    sched.complete(a, result={})
    fourth = sched.next_task()
    assert fourth is c


def test_scheduler_complete_transitions_status():
    sched = Scheduler()
    t = _task(1)
    sched.submit(t)
    sched.next_task()
    sched.complete(t, result={"value": 1})
    assert t.status is TaskStatus.COMPLETED
    assert t.result == {"value": 1}


def test_scheduler_fail_requeues_with_retries():
    sched = Scheduler()
    t = _task(1)
    sched.submit(t)
    sched.next_task()
    sched.fail(t, "transient")
    # Retry budget left → re-queued, not terminal.
    assert t.status is TaskStatus.PENDING
    assert sched.pending_count == 1
    # Drain remaining retries → terminal.
    sched.next_task()
    sched.fail(t, "still bad")
    assert t.status is TaskStatus.FAILED
    assert sched.pending_count == 0


def test_scheduler_cancel_pending():
    sched = Scheduler()
    t = _task(1)
    sched.submit(t)
    assert sched.cancel(t.task_id) is True
    assert t.status is TaskStatus.CANCELLED
    assert sched.next_task() is None


def test_scheduler_rejects_terminal_tasks():
    sched = Scheduler()
    t = _task(1)
    t.status = TaskStatus.COMPLETED
    with pytest.raises(ValueError):
        sched.submit(t)


def test_scheduler_rejects_duplicates():
    sched = Scheduler()
    t = _task(1)
    sched.submit(t)
    with pytest.raises(ValueError):
        sched.submit(t)


def test_scheduler_pending_returns_priority_order():
    sched = Scheduler()
    a = _task(5)
    b = _task(1)
    c = _task(3)
    sched.submit(a)
    sched.submit(b)
    sched.submit(c)
    assert sched.pending() == [b, c, a]
