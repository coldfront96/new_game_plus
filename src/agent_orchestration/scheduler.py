"""
src/agent_orchestration/scheduler.py
------------------------------------
Priority-queue scheduler for :class:`AgentTask` objects (Task 10).

Picks the highest-priority pending task (lower priority number = higher
urgency, mirroring the existing ``AgentTask.priority`` semantics) and
respects a configurable concurrency cap so the dispatcher never has more
in-flight tasks than the local model fleet can handle.

The scheduler is intentionally synchronous — async dispatch happens in
:class:`~src.agent_orchestration.task_runner.LLMTaskRunner`.  This module
only owns the bookkeeping.
"""

from __future__ import annotations

import heapq
import itertools
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

from src.agent_orchestration.agent_task import AgentTask, TaskStatus


@dataclass(order=True)
class _Entry:
    """Heap entry: (priority, sequence_number, task_id)."""

    priority: int
    sequence: int
    task_id: str = field(compare=False)


class Scheduler:
    """Priority-queue scheduler for :class:`AgentTask` objects.

    Attributes:
        max_concurrency: Maximum number of tasks allowed in
                         :attr:`TaskStatus.IN_PROGRESS` simultaneously.
    """

    def __init__(self, *, max_concurrency: int = 1) -> None:
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be ≥ 1")
        self.max_concurrency: int = max_concurrency
        self._heap: List[_Entry] = []
        self._tasks: Dict[str, AgentTask] = {}
        self._in_progress: Dict[str, AgentTask] = {}
        self._counter = itertools.count()

    # ------------------------------------------------------------------
    # Inspection helpers
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._tasks) + len(self._in_progress)

    @property
    def pending_count(self) -> int:
        return len(self._tasks)

    @property
    def in_progress_count(self) -> int:
        return len(self._in_progress)

    @property
    def has_capacity(self) -> bool:
        return self.in_progress_count < self.max_concurrency

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def submit(self, task: AgentTask) -> None:
        """Add *task* to the pending heap.

        Raises:
            ValueError: If a task with the same ``task_id`` is already
                        tracked by this scheduler.
        """
        if task.task_id in self._tasks or task.task_id in self._in_progress:
            raise ValueError(
                f"Task {task.task_id[:8]}… already submitted to scheduler."
            )
        if task.is_terminal:
            raise ValueError(
                f"Task {task.task_id[:8]}… is in terminal state "
                f"{task.status.name}; cannot submit."
            )
        self._tasks[task.task_id] = task
        heapq.heappush(
            self._heap,
            _Entry(
                priority=task.priority,
                sequence=next(self._counter),
                task_id=task.task_id,
            ),
        )

    def submit_many(self, tasks: Iterable[AgentTask]) -> None:
        for task in tasks:
            self.submit(task)

    def next_task(self, model_id: Optional[str] = None) -> Optional[AgentTask]:
        """Return the next pending task, transitioning it to IN_PROGRESS.

        Returns:
            The chosen task, or ``None`` if the queue is empty or the
            concurrency cap has been reached.
        """
        if not self.has_capacity:
            return None
        while self._heap:
            entry = heapq.heappop(self._heap)
            task = self._tasks.pop(entry.task_id, None)
            if task is None:
                # Task was cancelled before dispatch — skip.
                continue
            if task.status is not TaskStatus.PENDING:
                # Already moved on (e.g. cancelled) — skip.
                continue
            task.mark_in_progress(model_id=model_id)
            self._in_progress[task.task_id] = task
            return task
        return None

    def complete(self, task: AgentTask, result: Dict) -> None:
        """Mark a previously-dispatched task as completed."""
        if task.task_id not in self._in_progress:
            raise KeyError(
                f"Task {task.task_id[:8]}… is not in_progress in this scheduler."
            )
        task.complete(result)
        self._in_progress.pop(task.task_id, None)

    def fail(self, task: AgentTask, error: str) -> None:
        """Mark a task as failed.  May re-queue if retries remain."""
        if task.task_id not in self._in_progress:
            raise KeyError(
                f"Task {task.task_id[:8]}… is not in_progress in this scheduler."
            )
        self._in_progress.pop(task.task_id, None)
        task.fail(error)
        if task.status is TaskStatus.PENDING:
            # Re-queue for another attempt at the same priority.
            self._tasks[task.task_id] = task
            heapq.heappush(
                self._heap,
                _Entry(
                    priority=task.priority,
                    sequence=next(self._counter),
                    task_id=task.task_id,
                ),
            )

    def cancel(self, task_id: str) -> bool:
        """Cancel a pending task by id.  Returns ``True`` on success."""
        task = self._tasks.pop(task_id, None)
        if task is None:
            return False
        task.cancel()
        return True

    def pending(self) -> List[AgentTask]:
        """Return pending tasks ordered by priority (then submission order)."""
        ordered: List[Tuple[_Entry, AgentTask]] = []
        for entry in list(self._heap):
            task = self._tasks.get(entry.task_id)
            if task is not None:
                ordered.append((entry, task))
        ordered.sort(key=lambda item: (item[0].priority, item[0].sequence))
        return [task for _, task in ordered]

    def in_progress(self) -> List[AgentTask]:
        return list(self._in_progress.values())
