"""
src/agent_orchestration/prompt_builder.py
-----------------------------------------
Composes prompts for a local LLM from an :class:`AgentTask` plus the
relevant 3.5e SRD context (Task 10).

The :class:`PromptBuilder` is intentionally deterministic and cheap:

* It loads each SRD category lazily via
  :mod:`src.rules_engine.srd_loader` (Task 7) and caches the result on
  the instance so repeated builds don't re-parse JSON.
* It selects only the SRD slice relevant to the task's ``task_type`` —
  e.g. an NPC-stats task gets races + classes; an encounter task gets
  encounter tables + monsters.
* It enforces a soft token budget (approximated as ``len(text) // 4``
  for ASCII-ish text) by trimming the SRD context first; the
  user-supplied prompt is never truncated.

The output is a list of OpenAI-compatible ``{"role", "content"}`` dicts
ready to feed into :class:`~src.ai_sim.llm_bridge.LLMClient`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from src.agent_orchestration.agent_task import AgentTask, TaskType
from src.rules_engine import srd_loader


# Approximate tokens-per-character ratio for English prose (very rough).
_TOKENS_PER_CHAR: float = 0.25

# Task types that can generate named creatures/characters — must receive the
# IP-safety reminder so the model never echoes WotC Product Identity names.
_IP_SAFE_TASK_TYPES: frozenset[str] = frozenset({
    TaskType.ROLL_NPC_STATS.value,
    TaskType.GENERATE_ENCOUNTER.value,
    TaskType.GENERATE_DUNGEON.value,
    TaskType.WRITE_LORE.value,
    TaskType.CUSTOM.value,
})

# Injected verbatim when ip_safe_mode=True for the above task types.
_IP_SAFE_REMINDER: str = (
    "CONTENT COMPLIANCE — IP SAFETY (mandatory):\n"
    "Do NOT use WotC Product Identity names: Beholder, Mind Flayer, "
    "Displacer Beast, Githyanki, Githzerai, Neogi, Illithid, or any other "
    "name designated as WotC PI in published sourcebooks.\n"
    "If the requested archetype matches a WotC PI creature, invent a wholly "
    "original name, appearance, and lore — copy only the mechanical stat block.\n"
    "SRD-compliant and public-domain creatures (Dragon, Hydra, Goblin, "
    "Skeleton, Giant, Griffon, etc.) may keep their canonical names."
)


def _approx_token_count(text: str) -> int:
    """Return an approximate token count for *text* (≈ chars / 4)."""
    if not text:
        return 0
    return max(1, int(len(text) * _TOKENS_PER_CHAR))


# Map known task types to the SRD categories they care about.
_TASK_CONTEXT_MAP: Dict[str, Sequence[str]] = {
    TaskType.ROLL_NPC_STATS.value: ("races", "classes", "feats"),
    TaskType.GENERATE_DUNGEON.value: ("encounter_tables", "monsters"),
    TaskType.GENERATE_ENCOUNTER.value: ("encounter_tables", "monsters"),
    TaskType.GENERATE_ITEM.value: ("magic_items",),
    TaskType.WRITE_LORE.value: ("races",),
    TaskType.CODE_GENERATION.value: (),
    TaskType.CUSTOM.value: (),
}


@dataclass
class PromptBuilder:
    """Builds prompts from :class:`AgentTask` + SRD context.

    Attributes:
        data_dir:        Override for the SRD directory (tests).
        system_prefix:   Constant text inserted at the top of the system
                         message (e.g. project-wide tone instructions).
    """

    data_dir: Optional[Path] = None
    system_prefix: str = (
        "You are a content-generation agent for the New Game Plus engine. "
        "Every response must be valid JSON, follow the requested schema "
        "exactly, and stay strictly within D&D 3.5e SRD rules."
    )
    ip_safe_mode: bool = True
    _context_cache: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # SRD context loading (lazy + cached)
    # ------------------------------------------------------------------

    def _load_category(self, category: str) -> Any:
        if category not in self._context_cache:
            loader = {
                "spells": srd_loader.load_spells,
                "feats": srd_loader.load_feats,
                "races": srd_loader.load_races,
                "classes": srd_loader.load_classes,
                "monsters": srd_loader.load_monsters,
                "magic_items": srd_loader.load_magic_items,
                "poisons_diseases": srd_loader.load_poisons_diseases,
                "gems_art": srd_loader.load_gems_art,
                "encounter_tables": srd_loader.load_encounter_tables,
            }.get(category)
            self._context_cache[category] = (
                loader(self.data_dir) if loader else []
            )
        return self._context_cache[category]

    def _gather_context(
        self,
        task_type: str,
        extra_categories: Sequence[str] = (),
    ) -> Dict[str, Any]:
        categories = list(_TASK_CONTEXT_MAP.get(task_type, ())) + list(extra_categories)
        return {cat: self._load_category(cat) for cat in categories}

    # ------------------------------------------------------------------
    # Prompt assembly
    # ------------------------------------------------------------------

    def _trim_context_to_budget(
        self,
        context: Dict[str, Any],
        budget_tokens: int,
    ) -> Dict[str, Any]:
        """Iteratively shrink *context* until it fits inside *budget_tokens*.

        We progressively halve list-valued categories (taking only the
        first half) until the serialised size fits.  Dict-valued
        categories shrink by dropping every other key.
        """
        if budget_tokens <= 0:
            return {}
        trimmed = {k: v for k, v in context.items()}
        while _approx_token_count(json.dumps(trimmed)) > budget_tokens:
            shrunk_any = False
            for key, value in list(trimmed.items()):
                if isinstance(value, list) and len(value) > 1:
                    trimmed[key] = value[: max(1, len(value) // 2)]
                    shrunk_any = True
                elif isinstance(value, dict) and len(value) > 1:
                    keys = list(value.keys())
                    trimmed[key] = {
                        k: value[k] for i, k in enumerate(keys) if i % 2 == 0
                    }
                    shrunk_any = True
            if not shrunk_any:
                break
        return trimmed

    def build(
        self,
        task: AgentTask,
        *,
        extra_categories: Sequence[str] = (),
        context_budget_tokens: Optional[int] = None,
    ) -> List[Dict[str, str]]:
        """Compose a list of chat messages for *task*.

        Args:
            task:                 The task to build a prompt for.
            extra_categories:     Additional SRD categories to inject
                                  alongside the type-driven defaults.
            context_budget_tokens: Soft cap on tokens spent on SRD
                                  context.  Defaults to ``task.max_tokens //
                                  2`` so the model has room to reply.

        Returns:
            A list of ``{"role": ..., "content": ...}`` dicts.
        """
        budget = context_budget_tokens
        if budget is None:
            budget = max(256, task.max_tokens // 2)

        context = self._gather_context(task.task_type, extra_categories)
        # Drop categories that resolved to empty payloads — they add
        # nothing useful and bloat the system prompt.
        context = {
            k: v for k, v in context.items()
            if v not in (None, [], {}, ())
        }
        trimmed = self._trim_context_to_budget(context, budget)

        system_parts = [self.system_prefix.strip()]
        if self.ip_safe_mode and task.task_type in _IP_SAFE_TASK_TYPES:
            system_parts.append(_IP_SAFE_REMINDER)
        if trimmed:
            system_parts.append(
                "Reference SRD context (JSON):\n"
                + json.dumps(trimmed, indent=2)
            )

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": "\n\n".join(system_parts)},
        ]
        if task.context:
            messages.append({
                "role": "system",
                "content": "Task context (JSON):\n"
                           + json.dumps(task.context, indent=2),
            })
        messages.append({"role": "user", "content": task.prompt})
        return messages

    def estimate_tokens(self, messages: Sequence[Dict[str, str]]) -> int:
        """Approximate the token cost of *messages* (rough ASCII heuristic)."""
        return sum(_approx_token_count(m.get("content", "")) for m in messages)
