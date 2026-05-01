"""
src/agent_orchestration/model_registry.py
-----------------------------------------
Tracks available local LLM models, their VRAM footprint, and capabilities.

The registry enforces the hardware constraint described in the README:
no more than one model loaded at a time to stay within the 16 GB VRAM
budget of the RTX 4070 Ti Super.  Eviction follows a Least-Recently-Used
(LRU) policy — when a new model needs to load, the one that has been idle
longest is unloaded first.

Usage::

    from src.agent_orchestration.model_registry import (
        ModelRegistry, ModelCapability, DEFAULT_MODELS,
    )

    registry = ModelRegistry(vram_budget_mb=16_384)
    model = registry.select(ModelCapability.CODE_GEN)
    if model:
        print(model.model_id, model.vram_mb, "MB")

    registry.mark_loaded(model.model_id)
    registry.mark_used(model.model_id)
    # ... inference ...
    registry.mark_unloaded(model.model_id)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# ModelCapability
# ---------------------------------------------------------------------------

class ModelCapability(Enum):
    """High-level task categories a local model can handle."""
    CODE_GEN  = auto()   # DeepSeek Coder — writing/debugging engine code
    WORLD_GEN = auto()   # Llama 3 — generating dungeons, biomes, events
    LORE_NPC  = auto()   # Mistral — NPC dialogue, faction lore, artifacts


# ---------------------------------------------------------------------------
# ModelRecord
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ModelRecord:
    """Static description of one local quantised model.

    Attributes:
        model_id:       Unique identifier, e.g. ``"deepseek-coder-6.7b-gptq"``.
        model_family:   Human-readable family name (``"DeepSeek Coder"``, etc.).
        param_size_b:   Parameter count in billions.
        quantization:   Quantisation format (``"GPTQ 4-bit"``, ``"GGUF Q4_K_M"``).
        vram_mb:        Estimated VRAM usage in megabytes when loaded.
        context_window: Maximum token context the model accepts.
        capabilities:   Set of :class:`ModelCapability` values this model supports.
        model_path:     Optional filesystem path to the model weights.
    """
    model_id:       str
    model_family:   str
    param_size_b:   float
    quantization:   str
    vram_mb:        int
    context_window: int
    capabilities:   frozenset[ModelCapability]
    model_path:     Optional[str] = None


# ---------------------------------------------------------------------------
# Default model fleet (from README §5.2)
# ---------------------------------------------------------------------------

DEFAULT_MODELS: list[ModelRecord] = [
    ModelRecord(
        model_id       = "deepseek-coder-6.7b-gptq",
        model_family   = "DeepSeek Coder v2",
        param_size_b   = 6.7,
        quantization   = "GPTQ 4-bit",
        vram_mb        = 5_120,
        context_window = 4_096,
        capabilities   = frozenset({ModelCapability.CODE_GEN}),
    ),
    ModelRecord(
        model_id       = "llama3-8b-gguf-q4",
        model_family   = "Llama 3",
        param_size_b   = 8.0,
        quantization   = "GGUF Q4_K_M",
        vram_mb        = 6_144,
        context_window = 8_192,
        capabilities   = frozenset({ModelCapability.WORLD_GEN}),
    ),
    ModelRecord(
        model_id       = "mistral-7b-awq-4bit",
        model_family   = "Mistral",
        param_size_b   = 7.0,
        quantization   = "AWQ 4-bit",
        vram_mb        = 5_120,
        context_window = 8_192,
        capabilities   = frozenset({ModelCapability.LORE_NPC}),
    ),
]


# ---------------------------------------------------------------------------
# ModelRegistry
# ---------------------------------------------------------------------------

@dataclass
class _LoadedEntry:
    """Internal bookkeeping for a currently-loaded model."""
    model_id:    str
    loaded_at:   float = field(default_factory=time.monotonic)
    last_used:   float = field(default_factory=time.monotonic)


class ModelRegistry:
    """Tracks available models and enforces the single-model VRAM constraint.

    Args:
        vram_budget_mb: Total VRAM available in megabytes (default 16 384 for
                        an RTX 4070 Ti Super).
        models:         Model fleet to register; defaults to
                        :data:`DEFAULT_MODELS`.
    """

    def __init__(
        self,
        vram_budget_mb: int = 16_384,
        models: Optional[List[ModelRecord]] = None,
    ) -> None:
        self.vram_budget_mb: int = vram_budget_mb
        self._records:  Dict[str, ModelRecord]  = {}
        self._loaded:   Dict[str, _LoadedEntry] = {}

        for model in (models if models is not None else DEFAULT_MODELS):
            self.register(model)

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, model: ModelRecord) -> None:
        """Add *model* to the registry.

        Raises:
            ValueError: If a model with the same ``model_id`` is already
                        registered.
        """
        if model.model_id in self._records:
            raise ValueError(
                f"Model '{model.model_id}' is already registered."
            )
        self._records[model.model_id] = model

    def get(self, model_id: str) -> Optional[ModelRecord]:
        """Return the :class:`ModelRecord` for *model_id*, or ``None``."""
        return self._records.get(model_id)

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def select(
        self,
        capability: ModelCapability,
        *,
        prefer_loaded: bool = True,
    ) -> Optional[ModelRecord]:
        """Return the best available model for *capability*.

        Preference order:
        1. Already-loaded model that supports *capability* (if
           *prefer_loaded* is ``True``).
        2. Model with the smallest VRAM footprint that fits in the budget
           and supports *capability*.

        Returns ``None`` if no suitable model is registered.
        """
        candidates = [
            m for m in self._records.values()
            if capability in m.capabilities
            and m.vram_mb <= self.vram_budget_mb
        ]
        if not candidates:
            return None

        if prefer_loaded:
            loaded_candidates = [
                m for m in candidates if m.model_id in self._loaded
            ]
            if loaded_candidates:
                # Return the most-recently-used loaded candidate.
                return max(
                    loaded_candidates,
                    key=lambda m: self._loaded[m.model_id].last_used,
                )

        # Smallest VRAM footprint wins (fits budget most easily).
        return min(candidates, key=lambda m: m.vram_mb)

    def available_for(self, capability: ModelCapability) -> List[ModelRecord]:
        """Return all registered models supporting *capability*."""
        return [
            m for m in self._records.values()
            if capability in m.capabilities
        ]

    # ------------------------------------------------------------------
    # Load / unload lifecycle
    # ------------------------------------------------------------------

    def mark_loaded(self, model_id: str) -> None:
        """Record that *model_id* has been loaded into VRAM.

        Raises:
            KeyError:   If *model_id* is not registered.
            ValueError: If loading would exceed the VRAM budget.
        """
        if model_id not in self._records:
            raise KeyError(f"Model '{model_id}' is not registered.")
        if model_id in self._loaded:
            return  # Already tracked as loaded.
        model = self._records[model_id]
        used = self.vram_used_mb
        if used + model.vram_mb > self.vram_budget_mb:
            raise ValueError(
                f"Loading '{model_id}' ({model.vram_mb} MB) would exceed "
                f"the {self.vram_budget_mb} MB VRAM budget "
                f"({used} MB already in use). Call evict_lru() first."
            )
        self._loaded[model_id] = _LoadedEntry(model_id=model_id)

    def mark_unloaded(self, model_id: str) -> None:
        """Record that *model_id* has been unloaded from VRAM."""
        self._loaded.pop(model_id, None)

    def mark_used(self, model_id: str) -> None:
        """Update the last-used timestamp for *model_id* (LRU tracking).

        Raises:
            KeyError: If *model_id* is not currently loaded.
        """
        entry = self._loaded.get(model_id)
        if entry is None:
            raise KeyError(
                f"Model '{model_id}' is not currently loaded; "
                "call mark_loaded() first."
            )
        entry.last_used = time.monotonic()

    # ------------------------------------------------------------------
    # LRU eviction
    # ------------------------------------------------------------------

    def evict_lru(self) -> Optional[str]:
        """Unload the least-recently-used loaded model.

        Returns:
            The ``model_id`` of the evicted model, or ``None`` if no
            model is currently loaded.
        """
        if not self._loaded:
            return None
        lru_id = min(self._loaded, key=lambda mid: self._loaded[mid].last_used)
        self.mark_unloaded(lru_id)
        return lru_id

    def evict_to_fit(self, model_id: str) -> List[str]:
        """Evict models until *model_id* fits in the remaining VRAM budget.

        Evicts in LRU order.  If *model_id* is already loaded this is a
        no-op.  Returns the list of evicted model IDs (may be empty).

        Raises:
            KeyError:   If *model_id* is not registered.
            ValueError: If the model's VRAM requirement exceeds the total
                        budget even with nothing else loaded.
        """
        if model_id not in self._records:
            raise KeyError(f"Model '{model_id}' is not registered.")
        model = self._records[model_id]
        if model.vram_mb > self.vram_budget_mb:
            raise ValueError(
                f"Model '{model_id}' requires {model.vram_mb} MB which "
                f"exceeds the total budget of {self.vram_budget_mb} MB."
            )
        evicted: List[str] = []
        while self.vram_remaining_mb < model.vram_mb:
            mid = self.evict_lru()
            if mid is None:
                break
            evicted.append(mid)
        return evicted

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def loaded_models(self) -> List[ModelRecord]:
        """Models currently tracked as loaded."""
        return [self._records[mid] for mid in self._loaded if mid in self._records]

    @property
    def vram_used_mb(self) -> int:
        """Sum of VRAM used by all currently-loaded models."""
        return sum(
            self._records[mid].vram_mb
            for mid in self._loaded
            if mid in self._records
        )

    @property
    def vram_remaining_mb(self) -> int:
        """VRAM still available."""
        return self.vram_budget_mb - self.vram_used_mb

    def __len__(self) -> int:
        return len(self._records)

    def __contains__(self, model_id: str) -> bool:
        return model_id in self._records
