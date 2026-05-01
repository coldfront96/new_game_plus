"""EM-008 · EM-009 — LLM Bridge System for New Game Plus.

src/ai_sim/llm_bridge.py
------------------------
LLM Bridge System for New Game Plus.

Provides an asynchronous bridge between the 3.5e rules engine and a locally
running Large Language Model inference server (e.g. Ollama on
``localhost:11434`` or LM Studio on ``localhost:1234``).

The bridge is intentionally **physics-first**: the LLM only receives a
strict, factual snapshot of what the entity can physically perceive and what
its 3.5e stat block actually permits.  It cannot hallucinate capabilities.

Key types
~~~~~~~~~
* :class:`CognitiveState` — compressed, serialisable snapshot of a
  :class:`~src.rules_engine.character_35e.Character35e` stat block.
* :class:`LLMClient` — async HTTP client that POSTs to an
  OpenAI-compatible ``/v1/chat/completions`` endpoint.

Usage::

    import asyncio
    from src.ai_sim.llm_bridge import CognitiveState, LLMClient
    from src.rules_engine.character_35e import Character35e

    char = Character35e(name="Zara", char_class="Wizard", level=5)
    state = CognitiveState.from_character(char, visible_entities=[])
    client = LLMClient()
    result = asyncio.run(client.query_model(
        system_prompt="You are Zara, a tactical Wizard.",
        cognitive_state=state,
        user_prompt="Decide your next action.",
    ))
    print(result)
"""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# CognitiveState
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class CognitiveState:
    """A compressed, JSON-serialisable snapshot of a character's situation.

    This is the sole data the LLM receives about the game world.  All
    information is derived from physical systems (stat blocks, vision
    results, action trackers) to prevent hallucinated capabilities.

    Attributes:
        character_name:    The entity's name.
        char_class:        D&D 3.5e class (e.g. ``"Wizard"``).
        level:             Character level.
        current_hp:        Hit points remaining.
        max_hp:            Maximum hit points.
        conditions:        List of active condition names (e.g. ``["Blinded"]``).
        known_spells:      List of spell names available to the character.
        action_tracker:    Dict snapshot of the :class:`~src.rules_engine.actions.ActionTracker`
                           (keys: ``standard_used``, ``move_used``, ``swift_used``).
        visible_entities:  List of dicts describing entities the character can
                           currently see (from the Vision system).
        memory_log:        Recent log entries from the entity's
                           :class:`~src.ai_sim.components.MemoryBank`.
    """

    character_name: str
    char_class: str
    level: int
    current_hp: int
    max_hp: int
    conditions: List[str]
    known_spells: List[str]
    action_tracker: Dict[str, bool]
    visible_entities: List[Dict[str, Any]]
    memory_log: List[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_character(
        cls,
        character: Any,
        visible_entities: List[Dict[str, Any]],
        *,
        current_hp: Optional[int] = None,
        conditions: Optional[List[str]] = None,
        action_tracker: Optional[Any] = None,
        memory_log: Optional[List[str]] = None,
    ) -> "CognitiveState":
        """Build a :class:`CognitiveState` from a
        :class:`~src.rules_engine.character_35e.Character35e` stat block.

        Args:
            character:        The 3.5e stat block to compress.
            visible_entities: Factual list of visible entity descriptors
                              (produced by the Vision system).
            current_hp:       The entity's **current** HP at query time.
                              Supply this from the entity's
                              :class:`~src.ai_sim.components.Health` component
                              so the LLM receives accurate damage information.
                              When ``None``, the derived maximum from the stat
                              block is used (assumes full health).
            conditions:       Optional list of active condition names.
            action_tracker:   Optional
                              :class:`~src.rules_engine.actions.ActionTracker`.
                              When omitted, all action slots are shown as
                              available.
            memory_log:       Optional recent log entries from
                              :class:`~src.ai_sim.components.MemoryBank`.

        Returns:
            A fully populated :class:`CognitiveState`.
        """
        # Gather known spells from any attached spell manager
        known: List[str] = []
        if getattr(character, "spellbook", None) is not None:
            known = list(character.spellbook.spells.keys())
        elif getattr(character, "spells_known", None) is not None:
            known = list(character.spells_known.spells.keys())
        elif getattr(character, "spontaneous_caster", None) is not None:
            known = list(character.spontaneous_caster.spells_known.keys())

        # Action tracker snapshot
        if action_tracker is not None:
            tracker_dict: Dict[str, bool] = {
                "standard_used": bool(action_tracker.standard_used),
                "move_used": bool(action_tracker.move_used),
                "swift_used": bool(action_tracker.swift_used),
            }
        else:
            tracker_dict = {
                "standard_used": False,
                "move_used": False,
                "swift_used": False,
            }

        max_hp_val = int(character.hit_points)
        current_hp_val = int(current_hp) if current_hp is not None else max_hp_val

        return cls(
            character_name=character.name,
            char_class=character.char_class,
            level=character.level,
            current_hp=current_hp_val,
            max_hp=max_hp_val,
            conditions=list(conditions or []),
            known_spells=known,
            action_tracker=tracker_dict,
            visible_entities=list(visible_entities),
            memory_log=list(memory_log or []),
        )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain JSON-serialisable dict of this cognitive state."""
        return {
            "character_name": self.character_name,
            "char_class": self.char_class,
            "level": self.level,
            "current_hp": self.current_hp,
            "max_hp": self.max_hp,
            "conditions": self.conditions,
            "known_spells": self.known_spells,
            "action_tracker": self.action_tracker,
            "visible_entities": self.visible_entities,
            "memory_log": self.memory_log,
        }


# ---------------------------------------------------------------------------
# LLMClient
# ---------------------------------------------------------------------------

#: Default endpoint for a local Ollama server (OpenAI-compatible).
_DEFAULT_BASE_URL: str = "http://localhost:11434"
#: Default chat completions path (OpenAI-compatible).
_DEFAULT_CHAT_PATH: str = "/v1/chat/completions"
#: Default model name to request.
_DEFAULT_MODEL: str = "mistral"
#: HTTP timeout for the inference request in seconds.
_DEFAULT_TIMEOUT: float = 30.0


class LLMClient:
    """Async HTTP client that queries a local OpenAI-compatible LLM server.

    The client is designed to be **non-blocking**: the inference call is
    dispatched in a background thread via :func:`asyncio.to_thread` so the
    main engine tick-loop is never stalled waiting for a GPU response.

    Args:
        base_url: Base URL of the local inference server.
                  Defaults to ``"http://localhost:11434"`` (Ollama).
        model:    Model identifier to send in the request body.
        timeout:  HTTP read timeout in seconds.
    """

    def __init__(
        self,
        base_url: str = _DEFAULT_BASE_URL,
        model: str = _DEFAULT_MODEL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._url = base_url.rstrip("/") + _DEFAULT_CHAT_PATH
        self._model = model
        self._timeout = timeout

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def query_model(
        self,
        system_prompt: str,
        cognitive_state: CognitiveState,
        user_prompt: str,
    ) -> str:
        """Send a chat-completion request to the local LLM and return the reply.

        The :class:`CognitiveState` is serialised as JSON and appended to
        *system_prompt* so the model has full mechanical context.  The HTTP
        request is executed in a thread pool via :func:`asyncio.to_thread`
        to avoid blocking the main event loop.

        Args:
            system_prompt:   Role/context description for the model.
            cognitive_state: Factual game-state snapshot.
            user_prompt:     The decision prompt (e.g. "Choose your next action.").

        Returns:
            The model's raw text response, or an empty string on failure.
        """
        enriched_system = (
            f"{system_prompt}\n\n"
            f"CURRENT GAME STATE (JSON):\n"
            f"{json.dumps(cognitive_state.to_dict(), indent=2)}"
        )

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": enriched_system},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
        }

        return await asyncio.to_thread(self._post, payload)

    async def query_text(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Send a simple text query to the LLM without a CognitiveState.

        Useful for non-entity tasks such as faction lore generation and
        spellcaster daily preparation that don't require a mechanical snapshot.

        Args:
            system_prompt: Role/context description for the model.
            user_prompt:   The question or instruction for the model.

        Returns:
            The model's raw text response, or an empty string on failure.
        """
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            "stream": False,
        }
        return await asyncio.to_thread(self._post, payload)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _post(self, payload: Dict[str, Any]) -> str:
        """Blocking HTTP POST — executed off the main thread.

        Args:
            payload: The request body dict (will be JSON-encoded).

        Returns:
            The model's message content, or an empty string on any error.
        """
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self._url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
        except (urllib.error.URLError, OSError, json.JSONDecodeError, IndexError):
            return ""
