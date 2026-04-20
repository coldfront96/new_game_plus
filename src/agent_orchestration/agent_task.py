"""
src/agent_orchestration/agent_task.py
-------------------------------------
Task data structure for queuing work to offline local LLM agents.

An :class:`AgentTask` represents a single unit of work dispatched to a
local AI model (e.g. DeepSeek, Llama).  Tasks are serialisable, carry
a strict token budget for VRAM-aware prompt chunking, and track their
lifecycle through well-defined statuses.

Usage::

    from src.agent_orchestration.agent_task import AgentTask, TaskStatus

    task = AgentTask(
        task_type="generate_dungeon",
        prompt="Create a 5-room dungeon for a level 3 party.",
        max_tokens=2048,
        priority=2,
    )

    print(task)
    print(task.status)  # TaskStatus.PENDING

    task.mark_in_progress()
    task.complete(result={"rooms": [...]})
    print(task.status)  # TaskStatus.COMPLETED
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class TaskStatus(Enum):
    """Lifecycle states for an :class:`AgentTask`."""

    PENDING = auto()
    """Task created and waiting in the queue."""

    IN_PROGRESS = auto()
    """Task dispatched to a local LLM agent; awaiting response."""

    COMPLETED = auto()
    """Agent returned a structured result successfully."""

    FAILED = auto()
    """Agent returned an error or the response failed validation."""

    CANCELLED = auto()
    """Task was cancelled by the Overseer before completion."""


class TaskType(Enum):
    """Well-known categories of agent work.

    Using an enum prevents free-form typos and enables efficient
    routing in the orchestration layer.
    """

    GENERATE_DUNGEON = "generate_dungeon"
    """Procedurally generate a dungeon layout."""

    ROLL_NPC_STATS = "roll_npc_stats"
    """Generate an NPC stat block following 3.5e rules."""

    WRITE_LORE = "write_lore"
    """Produce narrative lore text for a location or faction."""

    GENERATE_ENCOUNTER = "generate_encounter"
    """Build a combat encounter table for a given CR range."""

    GENERATE_ITEM = "generate_item"
    """Procedurally create a magic item description."""

    CODE_GENERATION = "code_generation"
    """Generate or refactor Python source code."""

    CUSTOM = "custom"
    """Catch-all for user-defined tasks."""


# ---------------------------------------------------------------------------
# AgentTask
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class AgentTask:
    """A single queued work item for an offline local LLM agent.

    Memory Optimisation
    ~~~~~~~~~~~~~~~~~~~
    Uses ``slots=True`` to prevent ``__dict__`` allocation, reducing
    per-instance RAM overhead during deep procedural-generation ticks
    where thousands of tasks may exist simultaneously.

    Attributes:
        task_id:       Globally unique identifier (UUID4). Auto-generated.
        task_type:     Category label used to route the task to the correct
                       agent pipeline.
        prompt:        The natural-language instruction sent to the model.
        max_tokens:    Hard cap on response length in tokens.  Used by the
                       orchestration layer for VRAM budget planning and
                       prompt chunking.
        priority:      Integer priority (lower = higher priority).  The
                       scheduler dequeues lower-priority numbers first.
        status:        Current lifecycle state.
        context:       Optional dictionary of structured data injected
                       alongside the prompt (e.g. current world state,
                       SRD excerpts).
        result:        Structured output returned by the agent on success.
        error:         Human-readable error message on failure.
        created_at:    ISO-8601 timestamp when the task was created.
        completed_at:  ISO-8601 timestamp when the task reached a terminal
                       state (``COMPLETED``, ``FAILED``, or ``CANCELLED``).
        model_id:      Identifier of the local model to target
                       (e.g. ``"deepseek-coder-v2"``).
        tags:          Free-form labels for filtering/grouping tasks.
        retry_count:   Number of times this task has been retried after
                       failure.
        max_retries:   Maximum allowed retries before permanent failure.
    """

    task_type: str
    prompt: str
    max_tokens: int = 2048
    priority: int = 5
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: TaskStatus = TaskStatus.PENDING
    context: Optional[Dict[str, Any]] = field(default=None)
    result: Optional[Dict[str, Any]] = field(default=None)
    error: Optional[str] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    completed_at: Optional[str] = None
    model_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3

    # ------------------------------------------------------------------
    # Lifecycle transitions
    # ------------------------------------------------------------------

    def mark_in_progress(self, model_id: Optional[str] = None) -> None:
        """Transition to ``IN_PROGRESS`` when dispatched to an agent.

        Args:
            model_id: Optional identifier of the model handling this task.

        Raises:
            RuntimeError: If the task is not in ``PENDING`` status.
        """
        if self.status is not TaskStatus.PENDING:
            raise RuntimeError(
                f"Cannot start task {self.task_id[:8]}…: "
                f"status is {self.status.name}, expected PENDING."
            )
        self.status = TaskStatus.IN_PROGRESS
        if model_id is not None:
            self.model_id = model_id

    def complete(self, result: Dict[str, Any]) -> None:
        """Mark the task as successfully completed with *result*.

        Args:
            result: Structured output from the agent.

        Raises:
            RuntimeError: If the task is not ``IN_PROGRESS``.
        """
        if self.status is not TaskStatus.IN_PROGRESS:
            raise RuntimeError(
                f"Cannot complete task {self.task_id[:8]}…: "
                f"status is {self.status.name}, expected IN_PROGRESS."
            )
        self.status = TaskStatus.COMPLETED
        self.result = result
        self.completed_at = datetime.now(timezone.utc).isoformat()

    def fail(self, error: str) -> None:
        """Mark the task as failed with an *error* message.

        If ``retry_count < max_retries`` the task is reset to ``PENDING``
        so the scheduler can re-dispatch it.  Otherwise it transitions
        to ``FAILED``.

        Args:
            error: Human-readable failure description.
        """
        if self.status is not TaskStatus.IN_PROGRESS:
            raise RuntimeError(
                f"Cannot fail task {self.task_id[:8]}…: "
                f"status is {self.status.name}, expected IN_PROGRESS."
            )
        self.error = error
        self.retry_count += 1
        if self.retry_count < self.max_retries:
            self.status = TaskStatus.PENDING
        else:
            self.status = TaskStatus.FAILED
            self.completed_at = datetime.now(timezone.utc).isoformat()

    def cancel(self) -> None:
        """Cancel the task (can be called from any non-terminal state).

        Raises:
            RuntimeError: If the task is already ``COMPLETED`` or ``FAILED``.
        """
        if self.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            raise RuntimeError(
                f"Cannot cancel task {self.task_id[:8]}…: "
                f"already in terminal state {self.status.name}."
            )
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    @property
    def is_terminal(self) -> bool:
        """``True`` if the task is in a terminal state."""
        return self.status in (
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        )

    @property
    def estimated_vram_mb(self) -> float:
        """Rough VRAM estimate in MiB based on ``max_tokens``.

        Uses the rule-of-thumb: ~2 bytes per token for KV-cache overhead
        at FP16 precision.  This is a *lower bound*; actual usage depends
        on model architecture and batch size.
        """
        return (self.max_tokens * 2) / (1024 * 1024)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dictionary (JSON-compatible)."""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "prompt": self.prompt,
            "max_tokens": self.max_tokens,
            "priority": self.priority,
            "status": self.status.name,
            "context": self.context,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "model_id": self.model_id,
            "tags": self.tags,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentTask":
        """Deserialise from a plain dictionary produced by :meth:`to_dict`.

        Args:
            data: Dictionary with keys matching :class:`AgentTask` fields.

        Returns:
            A new :class:`AgentTask` instance.
        """
        return cls(
            task_id=data["task_id"],
            task_type=data["task_type"],
            prompt=data["prompt"],
            max_tokens=data.get("max_tokens", 2048),
            priority=data.get("priority", 5),
            status=TaskStatus[data["status"]],
            context=data.get("context"),
            result=data.get("result"),
            error=data.get("error"),
            created_at=data.get("created_at", ""),
            completed_at=data.get("completed_at"),
            model_id=data.get("model_id"),
            tags=data.get("tags", []),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
        )

    def to_json(self) -> str:
        """Serialise to a JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "AgentTask":
        """Deserialise from a JSON string."""
        return cls.from_dict(json.loads(json_str))

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"AgentTask(id={self.task_id[:8]}…, type={self.task_type!r}, "
            f"status={self.status.name}, priority={self.priority}, "
            f"max_tokens={self.max_tokens})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AgentTask):
            return NotImplemented
        return self.task_id == other.task_id

    def __hash__(self) -> int:
        return hash(self.task_id)
