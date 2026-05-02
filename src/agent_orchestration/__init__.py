"""
src/agent_orchestration
-----------------------
Multi-agent LLM orchestration layer.

Public surface (Task 10):

* :class:`AgentTask` / :class:`TaskStatus` — task data class.
* :class:`Scheduler` — priority queue dispatcher with concurrency cap.
* :class:`PromptBuilder` — composes prompts from task spec + 3.5e SRD context.
* :class:`ResultParser` — validates LLM output against expected schemas.
* :class:`LLMTaskRunner` — glue that pulls tasks off the :class:`Scheduler`,
  invokes :class:`~src.ai_sim.llm_bridge.LLMClient`, and parses the
  result, surfacing failures back to the Overseer.
* :func:`build_llm_pipeline` — one-call factory for the complete wired stack.
"""

from src.agent_orchestration.action_dispatcher import (
    ActionDecodeError,
    ActionDispatcher,
    AgentAction,
    AgentActionType,
    DispatchResult,
    decode_action,
)
from src.agent_orchestration.agent_task import AgentTask, TaskStatus, TaskType
from src.agent_orchestration.prompt_builder import PromptBuilder
from src.agent_orchestration.result_parser import (
    ParseResult,
    ResultParser,
    SchemaError,
)
from src.agent_orchestration.pipeline import build_llm_pipeline
from src.agent_orchestration.scheduler import Scheduler
from src.agent_orchestration.task_runner import LLMTaskRunner

__all__ = [
    "ActionDecodeError",
    "ActionDispatcher",
    "AgentAction",
    "AgentActionType",
    "AgentTask",
    "DispatchResult",
    "LLMTaskRunner",
    "ParseResult",
    "PromptBuilder",
    "ResultParser",
    "SchemaError",
    "Scheduler",
    "TaskStatus",
    "TaskType",
    "build_llm_pipeline",
    "decode_action",
]
