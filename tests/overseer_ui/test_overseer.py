"""Tests for ``src.overseer_ui`` (Task 9 — terminal Overseer)."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from src.agent_orchestration.agent_task import AgentTask, TaskStatus
from src.overseer_ui import (
    OverseerDecision,
    OverseerQueue,
    OverseerUI,
    log_path_for,
)


def _task(task_type: str = "roll_npc_stats", **overrides) -> AgentTask:
    return AgentTask(
        task_type=task_type,
        prompt=overrides.get("prompt", f"do {task_type}"),
        max_tokens=overrides.get("max_tokens", 256),
        priority=overrides.get("priority", 3),
    )


def test_log_path_for_creates_directory(tmp_path: Path):
    p = log_path_for(directory=tmp_path)
    assert p.parent == tmp_path
    assert p.name.startswith("overseer-")
    assert p.suffix == ".jsonl"


def test_queue_enqueue_peek_len(tmp_path: Path):
    q = OverseerQueue(logs_dir=tmp_path)
    assert len(q) == 0
    a = _task()
    b = _task()
    q.enqueue(a)
    q.enqueue(b)
    assert len(q) == 2
    assert q.peek() is a


def test_queue_approve_marks_completed(tmp_path: Path):
    q = OverseerQueue(logs_dir=tmp_path)
    task = _task()
    q.enqueue(task)
    # Pre-populate result so approve() can complete it.
    task.mark_in_progress()
    task.result = {"value": 42}
    # Reset to PENDING for the queue's bookkeeping.
    task.status = TaskStatus.IN_PROGRESS
    out = q.approve(note="ok")
    assert out is task
    assert task.status is TaskStatus.COMPLETED
    history = q.history()
    assert history[-1].decision == OverseerDecision.APPROVED.value


def test_queue_reject_cancels(tmp_path: Path):
    q = OverseerQueue(logs_dir=tmp_path)
    task = _task()
    q.enqueue(task)
    out = q.reject(note="hallucinated")
    assert out is task
    assert task.status is TaskStatus.CANCELLED
    assert q.history()[-1].decision == OverseerDecision.REJECTED.value


def test_queue_edit_attaches_result(tmp_path: Path):
    q = OverseerQueue(logs_dir=tmp_path)
    task = _task()
    q.enqueue(task)
    edited = q.edit(result={"corrected": True}, note="fixed CR")
    assert edited.result == {"corrected": True}
    assert edited.status is TaskStatus.COMPLETED
    assert q.history()[-1].decision == OverseerDecision.EDITED.value


def test_queue_skip_moves_to_back(tmp_path: Path):
    q = OverseerQueue(logs_dir=tmp_path)
    a, b = _task("a"), _task("b")
    q.enqueue(a)
    q.enqueue(b)
    skipped = q.skip()
    assert skipped is a
    assert q.peek() is b
    # 'a' is now at the back.
    assert q.pending()[-1] is a


def test_queue_writes_jsonl_log(tmp_path: Path):
    log_path = tmp_path / "overseer-test.jsonl"
    q = OverseerQueue(log_path=log_path)
    q.enqueue(_task("alpha"))
    q.enqueue(_task("beta"))
    q.approve(note="ok")
    q.reject(note="bad")
    contents = [json.loads(l) for l in log_path.read_text().splitlines()]
    assert len(contents) == 2
    assert contents[0]["decision"] == "approved"
    assert contents[1]["decision"] == "rejected"
    # Snapshot included
    assert contents[0]["snapshot"]["task_type"] == "alpha"


def test_queue_empty_consume_raises(tmp_path: Path):
    q = OverseerQueue(logs_dir=tmp_path)
    with pytest.raises(IndexError):
        q.approve()


def test_ui_processes_approve_and_reject(tmp_path: Path):
    q = OverseerQueue(logs_dir=tmp_path)
    q.enqueue(_task("first"))
    q.enqueue(_task("second"))
    stdin = io.StringIO("a ok\nr bad\n")
    stdout = io.StringIO()
    ui = OverseerUI(queue=q, stdin=stdin, stdout=stdout)
    ui.run()
    out = stdout.getvalue()
    assert "approved" in out
    assert "rejected" in out
    assert len(q) == 0


def test_ui_handles_quit(tmp_path: Path):
    q = OverseerQueue(logs_dir=tmp_path)
    q.enqueue(_task())
    stdin = io.StringIO("q\n")
    stdout = io.StringIO()
    OverseerUI(queue=q, stdin=stdin, stdout=stdout).run()
    # Task remains pending after quit.
    assert len(q) == 1


def test_ui_handles_invalid_command(tmp_path: Path):
    q = OverseerQueue(logs_dir=tmp_path)
    q.enqueue(_task())
    stdin = io.StringIO("foo\nq\n")
    stdout = io.StringIO()
    OverseerUI(queue=q, stdin=stdin, stdout=stdout).run()
    assert "unknown command" in stdout.getvalue()


def test_ui_edit_with_json_payload(tmp_path: Path):
    q = OverseerQueue(logs_dir=tmp_path)
    q.enqueue(_task())
    payload = json.dumps({"x": 1})
    stdin = io.StringIO(f"e {payload}\nq\n")
    stdout = io.StringIO()
    OverseerUI(queue=q, stdin=stdin, stdout=stdout).run()
    assert "edited" in stdout.getvalue()
    assert q.history()[-1].snapshot["result"] == {"x": 1}


def test_ui_list_command(tmp_path: Path):
    q = OverseerQueue(logs_dir=tmp_path)
    q.enqueue(_task("alpha"))
    q.enqueue(_task("beta"))
    stdin = io.StringIO("l\nq\n")
    stdout = io.StringIO()
    OverseerUI(queue=q, stdin=stdin, stdout=stdout).run()
    out = stdout.getvalue()
    assert "alpha" in out
    assert "beta" in out
