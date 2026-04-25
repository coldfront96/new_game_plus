"""
src/overseer_ui
---------------
Human approval gate for autonomous LLM agents operating under 3.5e rules.

Exposes:

* :class:`OverseerQueue` — an in-memory approve/reject queue of
  :class:`~src.agent_orchestration.agent_task.AgentTask` objects, with
  JSON-lines persistence to ``logs/overseer-YYYY-MM-DD.jsonl``.
* :class:`OverseerUI` — a text-mode terminal interface driving the
  queue.  It uses plain stdin/stdout so it works in CI, headless
  containers, and real TTYs without pulling in curses/prompt-toolkit as
  a hard dependency.  The console loop is intentionally small — the
  queue API is what's interesting for agents and tests.
"""

from src.overseer_ui.overseer import (  # noqa: F401
    OverseerDecision,
    OverseerQueue,
    OverseerUI,
    log_path_for,
)

__all__ = ["OverseerDecision", "OverseerQueue", "OverseerUI", "log_path_for"]
