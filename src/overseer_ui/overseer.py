"""
src/overseer_ui/overseer.py
---------------------------
Minimal terminal Overseer UI (Task 9).

The Overseer is the human approval gate for every autonomous LLM agent
result.  The public surface is:

* :class:`OverseerQueue` — wraps a deque of :class:`AgentTask` objects
  and provides :meth:`approve`, :meth:`reject`, :meth:`edit`,
  :meth:`enqueue`, :meth:`peek`.  Every decision is appended to a daily
  JSON-lines log so a session can be replayed offline.
* :class:`OverseerUI` — a plain stdin/stdout console loop (``approve``
  / ``reject`` / ``edit`` / ``skip`` / ``quit``).  We deliberately avoid
  curses/prompt-toolkit so the module runs in CI and test fixtures
  without new runtime dependencies, matching the project's existing
  lightweight ``pytest``-only stack.  Swapping in a richer frontend
  later is a drop-in change — only :class:`OverseerUI` needs to know.
"""

from __future__ import annotations

import json
import sys
from collections import deque
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, TextIO

from src.agent_orchestration.agent_task import AgentTask, TaskStatus


# Repo-root / logs/ resolution
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_LOG_DIR = _REPO_ROOT / "logs"


# ---------------------------------------------------------------------------
# Decision enum + log helpers
# ---------------------------------------------------------------------------

class OverseerDecision(Enum):
    """Possible Overseer rulings on a queued task."""

    APPROVED = "approved"
    REJECTED = "rejected"
    EDITED = "edited"
    SKIPPED = "skipped"


def log_path_for(
    day: Optional[date] = None,
    directory: Optional[Path] = None,
) -> Path:
    """Return the JSONL log path for *day* (defaults to today, UTC)."""
    day = day or datetime.now(timezone.utc).date()
    base = directory if directory is not None else DEFAULT_LOG_DIR
    base.mkdir(parents=True, exist_ok=True)
    return base / f"overseer-{day.isoformat()}.jsonl"


# ---------------------------------------------------------------------------
# OverseerQueue
# ---------------------------------------------------------------------------

@dataclass
class _LogRecord:
    """One line in the overseer session log."""

    timestamp: str
    decision: str
    task_id: str
    task_type: str
    note: str = ""
    snapshot: Optional[Dict[str, Any]] = None


class OverseerQueue:
    """Approve/reject queue backed by a deque of :class:`AgentTask` objects.

    The queue is intentionally lightweight — storage is in-memory but
    every decision is persisted to a daily JSONL log so external tools
    can reconstruct the session.

    Attributes:
        log_path: Path to the append-only JSON-lines audit log.
    """

    def __init__(
        self,
        *,
        log_path: Optional[Path] = None,
        logs_dir: Optional[Path] = None,
    ) -> None:
        self._pending: "deque[AgentTask]" = deque()
        self._history: List[_LogRecord] = []
        self.log_path: Path = log_path or log_path_for(directory=logs_dir)

    # ------------------------------------------------------------------
    # Queue state
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._pending)

    def __bool__(self) -> bool:
        return bool(self._pending)

    def enqueue(self, task: AgentTask) -> None:
        """Add *task* to the pending queue."""
        self._pending.append(task)

    def enqueue_many(self, tasks: Iterable[AgentTask]) -> None:
        for task in tasks:
            self.enqueue(task)

    def peek(self) -> Optional[AgentTask]:
        """Return the next task without removing it."""
        return self._pending[0] if self._pending else None

    def pending(self) -> List[AgentTask]:
        """Snapshot of the pending queue (read-only)."""
        return list(self._pending)

    def history(self) -> List[_LogRecord]:
        return list(self._history)

    # ------------------------------------------------------------------
    # Decisions
    # ------------------------------------------------------------------

    def _consume(self) -> AgentTask:
        if not self._pending:
            raise IndexError("Overseer queue is empty.")
        return self._pending.popleft()

    def _log(
        self,
        decision: OverseerDecision,
        task: AgentTask,
        note: str = "",
    ) -> None:
        record = _LogRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            decision=decision.value,
            task_id=task.task_id,
            task_type=task.task_type,
            note=note,
            snapshot=task.to_dict(),
        )
        self._history.append(record)
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "timestamp": record.timestamp,
                "decision": record.decision,
                "task_id": record.task_id,
                "task_type": record.task_type,
                "note": record.note,
                "snapshot": record.snapshot,
            }) + "\n")

    def approve(self, note: str = "") -> AgentTask:
        """Approve the next task, marking it IN_PROGRESS → COMPLETED.

        If the task has a ``result`` already (agent returned one) we
        finalise it; otherwise we leave it in ``IN_PROGRESS`` for the
        downstream pipeline to complete.
        """
        task = self._consume()
        if task.status is TaskStatus.PENDING:
            task.mark_in_progress()
        if task.status is TaskStatus.IN_PROGRESS and task.result is not None:
            task.complete(task.result)
        self._log(OverseerDecision.APPROVED, task, note)
        return task

    def reject(self, note: str = "") -> AgentTask:
        """Reject the next task.  Sets ``task.status = CANCELLED``."""
        task = self._consume()
        if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            # Already terminal — log anyway but don't transition.
            self._log(OverseerDecision.REJECTED, task, note)
            return task
        try:
            task.cancel()
        except RuntimeError:
            pass
        self._log(OverseerDecision.REJECTED, task, note)
        return task

    def edit(self, result: Dict[str, Any], note: str = "") -> AgentTask:
        """Attach *result* to the next task then approve it."""
        task = self._consume()
        if task.status is TaskStatus.PENDING:
            task.mark_in_progress()
        # Force-complete with the edited result.
        if task.status is TaskStatus.IN_PROGRESS:
            task.complete(result)
        else:
            task.result = result
        self._log(OverseerDecision.EDITED, task, note)
        return task

    def skip(self, note: str = "") -> AgentTask:
        """Move the head of the queue to the back (defer a decision)."""
        task = self._consume()
        self._pending.append(task)
        self._log(OverseerDecision.SKIPPED, task, note)
        return task


# ---------------------------------------------------------------------------
# OverseerUI — minimal interactive driver
# ---------------------------------------------------------------------------

@dataclass
class OverseerUI:
    """Text-mode Overseer driver.

    The UI is intentionally simple — one command per line.  Commands:

    * ``a [note]`` / ``approve [note]`` — approve the head task.
    * ``r [note]`` / ``reject [note]``  — reject it.
    * ``e <json>``                      — attach ``<json>`` as the task's
      result and approve.
    * ``s``                             — skip (defer).
    * ``l``                             — list all pending tasks.
    * ``q``                             — quit the loop.

    Attributes:
        queue:  The :class:`OverseerQueue` being driven.
        stdin:  Input stream.
        stdout: Output stream.
    """

    queue: OverseerQueue
    stdin: TextIO = field(default_factory=lambda: sys.stdin)
    stdout: TextIO = field(default_factory=lambda: sys.stdout)

    def _print(self, msg: str = "") -> None:
        print(msg, file=self.stdout)

    def _readline(self) -> str:
        line = self.stdin.readline()
        if line == "":
            return "q"  # treat EOF as quit
        return line.rstrip("\n")

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------

    def _render_task(self, task: AgentTask) -> str:
        lines = [
            f"  id      : {task.task_id}",
            f"  type    : {task.task_type}",
            f"  priority: {task.priority}",
            f"  status  : {task.status.name}",
            f"  prompt  : {task.prompt[:120]}",
        ]
        if task.result:
            lines.append(f"  result  : {json.dumps(task.result)[:200]}")
        return "\n".join(lines)

    def _render_pending_list(self) -> str:
        out = [f"Pending tasks: {len(self.queue)}"]
        for i, task in enumerate(self.queue.pending(), start=1):
            out.append(f"  {i}. [{task.priority}] {task.task_type} — "
                       f"{task.task_id[:8]}…  ({task.status.name})")
        return "\n".join(out)

    # ------------------------------------------------------------------
    # Public loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Drive the approve/reject loop until ``q`` or the queue is empty."""
        self._print("=== New Game Plus — Overseer (text mode) ===")
        self._print("Commands: a[pprove] | r[eject] | e<json> | s[kip] | l[ist] | q[uit]")
        while True:
            task = self.queue.peek()
            if task is None:
                self._print("")
                self._print("(queue empty)")
                return
            self._print("")
            self._print(f"-- Next task ({len(self.queue)} pending) --")
            self._print(self._render_task(task))
            self._print("> ", )
            raw = self._readline().strip()
            if not raw:
                continue
            cmd, _, tail = raw.partition(" ")
            cmd = cmd.lower()
            if cmd in ("q", "quit", "exit"):
                return
            if cmd in ("l", "list"):
                self._print(self._render_pending_list())
                continue
            if cmd in ("a", "approve"):
                self.queue.approve(note=tail)
                self._print(f"  ✓ approved {task.task_id[:8]}…")
                continue
            if cmd in ("r", "reject"):
                self.queue.reject(note=tail)
                self._print(f"  ✗ rejected {task.task_id[:8]}…")
                continue
            if cmd in ("s", "skip"):
                self.queue.skip(note=tail)
                self._print(f"  … deferred {task.task_id[:8]}…")
                continue
            if cmd in ("e", "edit"):
                try:
                    result = json.loads(tail) if tail else {}
                except json.JSONDecodeError as err:
                    self._print(f"  ! invalid JSON: {err}")
                    continue
                self.queue.edit(result=result)
                self._print(f"  ✎ edited + approved {task.task_id[:8]}…")
                continue
            self._print(f"  ? unknown command: {cmd!r}")
