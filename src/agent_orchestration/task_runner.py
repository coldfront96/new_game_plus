"""
src/agent_orchestration/task_runner.py
--------------------------------------
Glue between the :class:`Scheduler`, :class:`PromptBuilder`,
:class:`ResultParser`, and :mod:`src.ai_sim.llm_bridge.LLMClient`
(Task 10).

The runner pulls one (or more) tasks off the scheduler, builds the
prompt, queries the LLM via :class:`LLMClient`, parses the response,
and either marks the task complete or surfaces the failure back to the
:class:`~src.overseer_ui.OverseerQueue`.

The async wrapper :meth:`LLMTaskRunner.run_one` keeps the main game
tick non-blocking — the LLM call goes through ``asyncio.to_thread``
inside :class:`LLMClient`.  For tests we accept any callable as the
*completion_fn* injection point, so no live HTTP is required.
"""

from __future__ import annotations

import asyncio
import inspect
import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence, Union

from src.agent_orchestration.agent_task import AgentTask, TaskStatus, TaskType
from src.agent_orchestration.prompt_builder import PromptBuilder
from src.agent_orchestration.result_parser import ParseResult, ResultParser
from src.agent_orchestration.scheduler import Scheduler


# Completion fn signature: (messages: list[dict]) -> str | Awaitable[str]
CompletionFn = Callable[
    [List[Dict[str, str]]],
    Union[str, Awaitable[str]],
]


@dataclass
class LLMTaskRunner:
    """Wires the scheduler + prompt builder + LLM client + result parser.

    Attributes:
        scheduler:          The :class:`Scheduler` to pull tasks from.
        prompt_builder:     A :class:`PromptBuilder` for context injection.
        result_parser:      A :class:`ResultParser` for validating responses.
        completion_fn:      Callable returning the LLM's raw text response.
                            For production use, wrap an :class:`LLMClient`;
                            for tests, inject a deterministic stub.
        overseer_queue:     Optional :class:`~src.overseer_ui.OverseerQueue`
                            — failed parses are forwarded here so a human
                            can review/edit/reject.
        model_id:           Optional model identifier passed to
                            :meth:`AgentTask.mark_in_progress`.
        action_dispatcher:  Optional :class:`~src.agent_orchestration
                            .action_dispatcher.ActionDispatcher`.  When
                            present, AGENT_DECISION tasks are validated via
                            :func:`~src.agent_orchestration.action_dispatcher
                            .decode_action` immediately after parsing so that
                            unrecognised action types fail fast — before the
                            task reaches ``COMPLETED`` and the OverseerQueue.
    """

    scheduler: Scheduler
    prompt_builder: PromptBuilder
    result_parser: ResultParser
    completion_fn: CompletionFn
    overseer_queue: Any = None
    model_id: Optional[str] = None
    action_dispatcher: Any = None  # Optional[ActionDispatcher] — typed as Any to avoid circular import

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _invoke_completion(
        self, messages: List[Dict[str, str]]
    ) -> str:
        result = self.completion_fn(messages)
        if inspect.isawaitable(result):
            return await result
        return result

    def _handle_parse_failure(
        self, task: AgentTask, parsed: ParseResult
    ) -> None:
        if self.overseer_queue is not None:
            # Re-queue for human review (Overseer can edit + approve).
            task.error = parsed.error
            task.result = {
                "raw": parsed.raw_text,
                "parse_error": parsed.error,
            }
            self.overseer_queue.enqueue(task)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_one(self) -> Optional[AgentTask]:
        """Pull one task off the scheduler, run it, and return it.

        Returns:
            The processed task (in its final state), or ``None`` if no
            task was available within the concurrency cap.
        """
        task = self.scheduler.next_task(model_id=self.model_id)
        if task is None:
            return None
        try:
            messages = self.prompt_builder.build(task)
            raw = await self._invoke_completion(messages)
            parsed = self.result_parser.parse(raw, task.task_type)
            if parsed.ok:
                result_data = parsed.data or {}
                # For AGENT_DECISION tasks, validate the decoded action type
                # immediately so unrecognised action_type values fail at the
                # runner level rather than silently completing.
                if (
                    task.task_type == TaskType.AGENT_DECISION.value
                    and self.action_dispatcher is not None
                ):
                    from src.agent_orchestration.action_dispatcher import (
                        ActionDecodeError,
                        decode_action,
                    )
                    try:
                        decode_action(result_data)
                    except ActionDecodeError as decode_err:
                        bad = ParseResult(
                            ok=False,
                            data=result_data,
                            error=str(decode_err),
                            raw_text=parsed.raw_text,
                        )
                        self.scheduler.fail(task, str(decode_err))
                        if task.status is not TaskStatus.PENDING:
                            self._handle_parse_failure(task, bad)
                        return task
                self.scheduler.complete(task, result=result_data)
            else:
                self.scheduler.fail(task, parsed.error)
                # If the failure isn't auto-retried, escalate to the Overseer.
                if task.status is not TaskStatus.PENDING:
                    self._handle_parse_failure(task, parsed)
        except Exception as err:  # noqa: BLE001 — bridge isolation
            self.scheduler.fail(task, f"runner exception: {err!r}")
        return task

    async def run_until_empty(self, *, limit: Optional[int] = None) -> List[AgentTask]:
        """Drain the scheduler.  Returns the list of processed tasks."""
        processed: List[AgentTask] = []
        count = 0
        while True:
            if limit is not None and count >= limit:
                break
            task = await self.run_one()
            if task is None:
                if self.scheduler.pending_count == 0:
                    break
                # No capacity right now — yield to the event loop.
                await asyncio.sleep(0)
                continue
            processed.append(task)
            count += 1
        return processed

    def run_one_sync(self) -> Optional[AgentTask]:
        """Synchronous helper for scripts/tests that don't run an event loop."""
        return asyncio.run(self.run_one())

    def run_until_empty_sync(
        self, *, limit: Optional[int] = None
    ) -> List[AgentTask]:
        return asyncio.run(self.run_until_empty(limit=limit))
