"""
src/agent_orchestration/pipeline.py
------------------------------------
Factory that wires the complete LLM agent pipeline in one call.

The pipeline connects every orchestration component into a ready-to-run
:class:`~src.agent_orchestration.task_runner.LLMTaskRunner`::

    Scheduler
      └─► PromptBuilder  (with ip_safe_mode)
            └─► LLMClient.query_messages  (CompletionFn adapter)
                  └─► ResultParser
                        └─► OverseerQueue  (on parse failure)

Usage::

    from src.agent_orchestration.pipeline import build_llm_pipeline
    from src.overseer_ui.overseer import OverseerQueue

    queue   = OverseerQueue()
    runner  = build_llm_pipeline(overseer_queue=queue)

    # Submit a task and run it
    from src.agent_orchestration import AgentTask, TaskType
    task = AgentTask(
        task_type=TaskType.GENERATE_ENCOUNTER.value,
        prompt="Generate a CR 5 forest encounter.",
        max_tokens=512,
        priority=3,
    )
    runner.scheduler.submit(task)
    result_task = runner.run_one_sync()
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from src.agent_orchestration.prompt_builder import PromptBuilder
from src.agent_orchestration.result_parser import ResultParser
from src.agent_orchestration.scheduler import Scheduler
from src.agent_orchestration.task_runner import LLMTaskRunner
from src.ai_sim.llm_bridge import LLMClient


def build_llm_pipeline(
    *,
    base_url: str = "http://localhost:11434",
    model: str = "mistral",
    overseer_queue: Optional[object] = None,
    max_concurrency: int = 1,
    ip_safe: bool = True,
    data_dir: Optional[Path] = None,
    model_id: Optional[str] = None,
) -> LLMTaskRunner:
    """Build and return a fully wired :class:`LLMTaskRunner`.

    All arguments are optional — defaults target a local Ollama server
    running the Mistral model, matching the project's target hardware.

    Args:
        base_url:         Base URL of the local OpenAI-compatible inference
                          server. Defaults to ``"http://localhost:11434"``
                          (Ollama).
        model:            Model identifier sent in each request body.
                          Defaults to ``"mistral"`` (LORE_NPC capability).
        overseer_queue:   :class:`~src.overseer_ui.overseer.OverseerQueue`
                          instance. Tasks that fail parsing are forwarded
                          here for human review. Pass ``None`` to discard
                          failures silently (useful in tests / CI).
        max_concurrency:  Maximum tasks dispatched simultaneously.
                          Keep at ``1`` unless running multiple inference
                          workers behind a load balancer.
        ip_safe:          When ``True`` (default), the
                          :class:`~src.agent_orchestration.prompt_builder.PromptBuilder`
                          injects the Clean-Room Translation Protocol
                          reminder into every content-generation prompt,
                          preventing the LLM from outputting WotC Product
                          Identity names.
        data_dir:         Override for the SRD data directory. Passed to
                          :class:`~src.agent_orchestration.prompt_builder.PromptBuilder`
                          so tests can point at a fixture directory without
                          touching the real ``data/`` tree.
        model_id:         Optional model-ID label forwarded to
                          :meth:`~src.agent_orchestration.task_runner.LLMTaskRunner`
                          for audit-log traceability.  Defaults to *model*.

    Returns:
        A :class:`~src.agent_orchestration.task_runner.LLMTaskRunner` whose
        :attr:`~src.agent_orchestration.task_runner.LLMTaskRunner.scheduler`
        is empty and ready to accept submitted tasks.
    """
    scheduler = Scheduler(max_concurrency=max_concurrency)
    prompt_builder = PromptBuilder(data_dir=data_dir, ip_safe_mode=ip_safe)
    result_parser = ResultParser()
    client = LLMClient(base_url=base_url, model=model)

    return LLMTaskRunner(
        scheduler=scheduler,
        prompt_builder=prompt_builder,
        result_parser=result_parser,
        completion_fn=client.query_messages,
        overseer_queue=overseer_queue,
        model_id=model_id or model,
    )
