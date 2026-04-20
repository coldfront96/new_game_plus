"""
src/ai_sim/behavior.py
-----------------------
Finite State Machine (FSM) for entity AI behavior in New Game Plus.

Entities cycle through behavioral states to satisfy their needs:

    IDLE → SEARCH_FOR_TASK → MOVE_TO_TARGET → PERFORM_ACTION → IDLE

The FSM integrates with the D&D 3.5e skill system — for example, a
hungry entity uses a Survival skill check to forage for food.

Usage::

    from src.ai_sim.behavior import BehaviorFSM, BehaviorState, EntityTask

    fsm = BehaviorFSM()
    fsm.transition(BehaviorState.SEARCH_FOR_TASK)
    print(fsm.state)  # BehaviorState.SEARCH_FOR_TASK
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Tuple


# ---------------------------------------------------------------------------
# Behavior States
# ---------------------------------------------------------------------------

class BehaviorState(Enum):
    """Finite state machine states for entity AI."""

    IDLE = auto()
    SEARCH_FOR_TASK = auto()
    MOVE_TO_TARGET = auto()
    PERFORM_ACTION = auto()


# ---------------------------------------------------------------------------
# Task types
# ---------------------------------------------------------------------------

class TaskType(Enum):
    """Types of tasks an entity can pursue."""

    NONE = auto()
    FORAGE = auto()
    REST = auto()
    SOCIALIZE = auto()
    WORK = auto()


# ---------------------------------------------------------------------------
# EntityTask
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class EntityTask:
    """A task assigned to an entity by the behavior FSM.

    Attributes:
        task_type:       The type of task being performed.
        target_position: World coordinates (x, y, z) of the task target.
                         ``None`` if the task has no spatial target yet.
        skill_name:      The 3.5e skill used for this task (e.g. "Survival").
        dc:              Difficulty Class for the skill check to complete.
        completed:       Whether the task has been completed.
    """

    task_type: TaskType = TaskType.NONE
    target_position: Optional[Tuple[int, int, int]] = None
    skill_name: Optional[str] = None
    dc: int = 10
    completed: bool = False


# ---------------------------------------------------------------------------
# BehaviorFSM
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class BehaviorFSM:
    """Finite State Machine managing entity AI behavior transitions.

    Implements the state cycle:
        IDLE → SEARCH_FOR_TASK → MOVE_TO_TARGET → PERFORM_ACTION → IDLE

    The FSM enforces valid transitions and tracks the entity's current
    task assignment.

    Attributes:
        state:        Current behavioral state.
        current_task: The task the entity is working towards.
        ticks_in_state: Number of ticks spent in the current state.
    """

    state: BehaviorState = BehaviorState.IDLE
    current_task: EntityTask = field(default_factory=EntityTask)
    ticks_in_state: int = 0

    # Valid state transitions
    _VALID_TRANSITIONS = {
        BehaviorState.IDLE: {
            BehaviorState.SEARCH_FOR_TASK,
        },
        BehaviorState.SEARCH_FOR_TASK: {
            BehaviorState.MOVE_TO_TARGET,
            BehaviorState.IDLE,  # No task found → back to idle
        },
        BehaviorState.MOVE_TO_TARGET: {
            BehaviorState.PERFORM_ACTION,
            BehaviorState.IDLE,  # Path blocked or interrupted
        },
        BehaviorState.PERFORM_ACTION: {
            BehaviorState.IDLE,  # Task completed or failed
            BehaviorState.SEARCH_FOR_TASK,  # Need another task immediately
        },
    }

    def transition(self, new_state: BehaviorState) -> bool:
        """Attempt to transition to *new_state*.

        Args:
            new_state: The desired next state.

        Returns:
            ``True`` if the transition was valid and performed;
            ``False`` if the transition is not allowed from the current state.
        """
        valid_targets = self._VALID_TRANSITIONS.get(self.state, set())
        if new_state not in valid_targets:
            return False
        self.state = new_state
        self.ticks_in_state = 0
        return True

    def assign_task(self, task: EntityTask) -> None:
        """Assign a task and transition to SEARCH_FOR_TASK if idle.

        Args:
            task: The :class:`EntityTask` to assign.
        """
        self.current_task = task
        if self.state == BehaviorState.IDLE:
            self.transition(BehaviorState.SEARCH_FOR_TASK)

    def complete_task(self) -> None:
        """Mark the current task as completed and return to IDLE."""
        self.current_task.completed = True
        self.state = BehaviorState.IDLE
        self.ticks_in_state = 0

    def reset(self) -> None:
        """Reset the FSM to initial IDLE state with no task."""
        self.state = BehaviorState.IDLE
        self.current_task = EntityTask()
        self.ticks_in_state = 0

    def tick(self) -> None:
        """Increment the tick counter for the current state."""
        self.ticks_in_state += 1

    @property
    def is_idle(self) -> bool:
        """Return ``True`` if the entity is currently idle."""
        return self.state == BehaviorState.IDLE

    @property
    def has_task(self) -> bool:
        """Return ``True`` if the entity has an active (non-NONE) task."""
        return (
            self.current_task.task_type != TaskType.NONE
            and not self.current_task.completed
        )
