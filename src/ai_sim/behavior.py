"""EM-008 — SpellcasterAI (Caster AI subsystem).

src/ai_sim/behavior.py
-----------------------
Finite State Machine (FSM) for entity AI behavior in New Game Plus.

Entities cycle through behavioral states to satisfy their needs:

    IDLE → SEARCH_FOR_TASK → MOVE_TO_TARGET → PERFORM_ACTION → IDLE

Combat interrupts this cycle via the dedicated ``IN_COMBAT`` state.
When in ``IN_COMBAT``, the entity delegates action allocation to the
:class:`~src.ai_sim.tactics.TacticalEvaluator` each turn (driven by
:class:`~src.ai_sim.systems.TurnManagerSystem`).

The FSM integrates with the D&D 3.5e skill system — for example, a
hungry entity uses a Survival skill check to forage for food.

Usage::

    from src.ai_sim.behavior import BehaviorFSM, BehaviorState, EntityTask

    fsm = BehaviorFSM()
    fsm.transition(BehaviorState.SEARCH_FOR_TASK)
    print(fsm.state)  # BehaviorState.SEARCH_FOR_TASK

    # Enter combat
    fsm.enter_combat()
    print(fsm.state)  # BehaviorState.IN_COMBAT
    fsm.exit_combat()
    print(fsm.state)  # BehaviorState.IDLE
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from src.ai_sim.llm_bridge import LLMClient


# ---------------------------------------------------------------------------
# Behavior States
# ---------------------------------------------------------------------------

class BehaviorState(Enum):
    """Finite state machine states for entity AI."""

    IDLE = auto()
    SEARCH_FOR_TASK = auto()
    MOVE_TO_TARGET = auto()
    PERFORM_ACTION = auto()
    IN_COMBAT = auto()


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

    Combat interrupts the normal cycle via the ``IN_COMBAT`` state.
    Any non-combat state may transition to ``IN_COMBAT``; when combat
    ends the FSM returns to ``IDLE``.

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
            BehaviorState.IN_COMBAT,
        },
        BehaviorState.SEARCH_FOR_TASK: {
            BehaviorState.MOVE_TO_TARGET,
            BehaviorState.IDLE,  # No task found → back to idle
            BehaviorState.IN_COMBAT,
        },
        BehaviorState.MOVE_TO_TARGET: {
            BehaviorState.PERFORM_ACTION,
            BehaviorState.IDLE,  # Path blocked or interrupted
            BehaviorState.IN_COMBAT,
        },
        BehaviorState.PERFORM_ACTION: {
            BehaviorState.IDLE,  # Task completed or failed
            BehaviorState.SEARCH_FOR_TASK,  # Need another task immediately
            BehaviorState.IN_COMBAT,
        },
        BehaviorState.IN_COMBAT: {
            BehaviorState.IDLE,  # Combat ended
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
    def is_in_combat(self) -> bool:
        """Return ``True`` if the entity is currently in combat."""
        return self.state == BehaviorState.IN_COMBAT

    def enter_combat(self) -> bool:
        """Transition to the ``IN_COMBAT`` state from any non-combat state.

        Returns:
            ``True`` if the transition was valid and performed;
            ``False`` if already in ``IN_COMBAT`` or if the transition is
            not permitted from the current state.
        """
        return self.transition(BehaviorState.IN_COMBAT)

    def exit_combat(self) -> bool:
        """Exit ``IN_COMBAT`` state and return to ``IDLE``.

        Returns:
            ``True`` if the transition was valid and performed;
            ``False`` if not currently in ``IN_COMBAT``.
        """
        return self.transition(BehaviorState.IDLE)

    @property
    def has_task(self) -> bool:
        """Return ``True`` if the entity has an active (non-NONE) task."""
        return (
            self.current_task.task_type != TaskType.NONE
            and not self.current_task.completed
        )


# ---------------------------------------------------------------------------
# EM-008 · SpellcasterAI
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class SpellcasterAI:
    """AI helper that selects a daily spell loadout for a spellcasting entity.

    Attributes:
        char_class:      Class name (e.g. "Wizard", "Cleric").
        level:           Character level — determines max accessible spell level.
        prepared_spells: Spells selected for the current day (updated by
                         :meth:`prepare_daily`).
        llm_client:      Optional LLM client.  When present, the LLM chooses
                         spells; when absent, a deterministic fallback is used.
    """

    char_class:      str
    level:           int
    prepared_spells: list[str] = field(default_factory=list)
    llm_client:      Optional["LLMClient"] = field(default=None)

    # Maximum spell level accessible = ceil(level / 2), capped at 9
    @property
    def _max_spell_level(self) -> int:
        return min(9, (self.level + 1) // 2)

    async def prepare_daily(
        self,
        chunk_environment: str,
        spell_data_dir: str = "data/srd_3.5/spells",
    ) -> list[str]:
        """Select spells for the day based on current chunk environment.

        If an LLM client is available, it asks the model to choose from the
        available spell list given the environment description.  Otherwise a
        deterministic fallback picks the first N spells up to the caster's
        level from each accessible level file.

        Args:
            chunk_environment: Free-text description of the current terrain
                               and biome (e.g. "dense forest, river nearby").
            spell_data_dir:    Directory containing ``level_0.json`` …
                               ``level_9.json`` spell data files.

        Returns:
            The updated list of prepared spell names (also stored in
            ``self.prepared_spells``).
        """
        all_spells: list[dict] = []
        for lvl in range(0, self._max_spell_level + 1):
            path = os.path.join(spell_data_dir, f"level_{lvl}.json")
            if not os.path.exists(path):
                continue
            try:
                with open(path, encoding="utf-8") as fh:
                    all_spells.extend(json.load(fh))
            except (json.JSONDecodeError, OSError):
                pass

        spell_names = [s["name"] for s in all_spells if "name" in s]
        slots_available = max(1, self.level)

        if self.llm_client is not None and spell_names:
            spell_list_txt = "\n".join(f"- {n}" for n in spell_names[:80])
            system_prompt = (
                f"You are a {self.char_class} of level {self.level} "
                f"preparing spells for the day."
            )
            user_prompt = (
                f"Current environment: {chunk_environment}\n\n"
                f"Available spells (up to spell level {self._max_spell_level}):\n"
                f"{spell_list_txt}\n\n"
                f"Choose up to {slots_available} spells best suited to this environment. "
                f"Reply with ONLY a JSON array of spell names, e.g. [\"Fireball\", \"Fly\"]."
            )
            raw = await self.llm_client.query_text(system_prompt, user_prompt)
            chosen = self._parse_spell_names(raw, spell_names, slots_available)
        else:
            chosen = spell_names[:slots_available]

        self.prepared_spells = chosen
        return self.prepared_spells

    @staticmethod
    def _parse_spell_names(
        raw_response: str,
        known_spells: list[str],
        limit: int,
    ) -> list[str]:
        """Extract spell names from the LLM response that match known spells.

        Tries to parse a JSON array first; falls back to line-by-line matching.
        """
        known_set = {s.lower(): s for s in known_spells}
        chosen: list[str] = []

        # Attempt JSON array parse
        try:
            start = raw_response.index("[")
            end   = raw_response.rindex("]") + 1
            candidates = json.loads(raw_response[start:end])
            for c in candidates:
                canonical = known_set.get(str(c).strip().lower())
                if canonical and canonical not in chosen:
                    chosen.append(canonical)
                if len(chosen) >= limit:
                    break
            if chosen:
                return chosen
        except (ValueError, json.JSONDecodeError):
            pass

        # Fallback: line-by-line matching
        for line in raw_response.splitlines():
            name = line.strip().lstrip("-• ").strip()
            canonical = known_set.get(name.lower())
            if canonical and canonical not in chosen:
                chosen.append(canonical)
            if len(chosen) >= limit:
                break

        return chosen
