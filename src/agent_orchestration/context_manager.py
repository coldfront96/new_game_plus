"""
src/agent_orchestration/context_manager.py
------------------------------------------
Sliding-window context chunking for the local LLM inference layer.

When an assembled prompt exceeds a model's native context window the
:class:`ContextManager` splits it into sequential overlapping chunks,
processes each independently, and stitches the results back together.

All token-count estimates use a simple word-based heuristic
(≈ 0.75 words per token) so no tokenizer binary is required at runtime.
For production use the estimate is conservative — real token counts for
English prose are close to this ratio.

Usage::

    from src.agent_orchestration.context_manager import ContextManager, ContextWindow

    window = ContextWindow(model_id="llama3-8b", max_tokens=4096, reserved_for_response=512)
    cm = ContextManager(window)

    chunks = cm.chunk_prompt(long_system_prompt, user_prompt)
    results = [call_llm(chunk) for chunk in chunks]
    final   = cm.stitch_results(results)
"""

from __future__ import annotations

import math
import textwrap
from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Token estimation
# ---------------------------------------------------------------------------

_WORDS_PER_TOKEN: float = 0.75


def estimate_tokens(text: str) -> int:
    """Rough token count from word count (1 token ≈ 0.75 words)."""
    words = len(text.split())
    return max(1, math.ceil(words / _WORDS_PER_TOKEN))


# ---------------------------------------------------------------------------
# ContextWindow — per-model capacity descriptor
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ContextWindow:
    """Describes a model's token capacity.

    Attributes:
        model_id:              Identifier matching :class:`ModelRecord.model_id`.
        max_tokens:            Total tokens the model can accept (prompt +
                               response combined).
        reserved_for_response: Tokens reserved for the model's reply; the
                               available prompt budget is
                               ``max_tokens - reserved_for_response``.
        overlap_tokens:        How many tokens of context to repeat between
                               consecutive chunks so the model retains continuity.
    """
    model_id: str
    max_tokens: int
    reserved_for_response: int = 512
    overlap_tokens: int = 128

    @property
    def prompt_budget(self) -> int:
        """Maximum tokens available for the prompt portion."""
        return max(1, self.max_tokens - self.reserved_for_response)


# ---------------------------------------------------------------------------
# ContextManager
# ---------------------------------------------------------------------------

class ContextManager:
    """Splits oversized prompts and stitches chunked results.

    Args:
        window: The :class:`ContextWindow` for the target model.
    """

    def __init__(self, window: ContextWindow) -> None:
        self.window = window

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fits(self, system_prompt: str, user_prompt: str) -> bool:
        """Return ``True`` if both prompts fit within the prompt budget."""
        total = estimate_tokens(system_prompt) + estimate_tokens(user_prompt)
        return total <= self.window.prompt_budget

    def chunk_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> List[str]:
        """Split *user_prompt* into token-budget-sized chunks.

        The *system_prompt* is prepended verbatim to every chunk so the
        model always has the full instruction context.  If the combined
        prompts already fit within the budget a single-element list is
        returned.

        Args:
            system_prompt: Instruction context (role, rules, constraints).
            user_prompt:   The variable content to chunk.

        Returns:
            List of fully-formed prompt strings, each within budget.
        """
        sys_tokens = estimate_tokens(system_prompt)
        available = self.window.prompt_budget - sys_tokens

        if available <= 0:
            # System prompt alone exceeds budget — return as-is and let
            # the caller handle the truncation or model error.
            return [f"{system_prompt}\n\n{user_prompt}"]

        user_tokens = estimate_tokens(user_prompt)
        if user_tokens <= available:
            return [f"{system_prompt}\n\n{user_prompt}"]

        # Chunk the user prompt by words.
        words = user_prompt.split()
        words_per_chunk = max(1, int(available * _WORDS_PER_TOKEN))
        overlap_words   = max(0, int(self.window.overlap_tokens * _WORDS_PER_TOKEN))

        chunks: List[str] = []
        start = 0
        while start < len(words):
            end   = min(start + words_per_chunk, len(words))
            chunk_words = words[start:end]
            chunk_text  = " ".join(chunk_words)
            chunks.append(f"{system_prompt}\n\n{chunk_text}")
            if end >= len(words):
                break
            # Advance with overlap so context bleeds into the next chunk.
            start = end - overlap_words

        return chunks if chunks else [f"{system_prompt}\n\n{user_prompt}"]

    def stitch_results(self, results: List[str], separator: str = "\n\n") -> str:
        """Concatenate per-chunk LLM responses into a single result.

        Consecutive duplicate sentences at chunk boundaries are removed so
        the overlap does not produce repeated text in the final output.

        Args:
            results:   Ordered list of per-chunk model responses.
            separator: String inserted between stitched segments.

        Returns:
            Single combined response string.
        """
        if not results:
            return ""
        if len(results) == 1:
            return results[0]

        stitched_parts: List[str] = [results[0].strip()]
        for segment in results[1:]:
            segment = segment.strip()
            if not segment:
                continue
            # Drop leading sentences that duplicate the tail of the prior part.
            prev_tail  = _last_sentence(stitched_parts[-1])
            seg_lead   = _first_sentence(segment)
            if prev_tail and seg_lead and _sentences_similar(prev_tail, seg_lead):
                # Strip the leading duplicated sentence.
                idx = segment.find(seg_lead)
                segment = segment[idx + len(seg_lead):].lstrip(". \n")
            if segment:
                stitched_parts.append(segment)

        return separator.join(stitched_parts)

    def chunk_count(self, system_prompt: str, user_prompt: str) -> int:
        """Return the number of chunks :meth:`chunk_prompt` would produce."""
        return len(self.chunk_prompt(system_prompt, user_prompt))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _first_sentence(text: str) -> str:
    """Return the first sentence of *text* (up to the first period/newline)."""
    for sep in (".", "\n"):
        idx = text.find(sep)
        if idx != -1:
            return text[: idx + 1].strip()
    return text.strip()


def _last_sentence(text: str) -> str:
    """Return the last sentence of *text*."""
    for sep in (".", "\n"):
        idx = text.rfind(sep, 0, len(text) - 1)
        if idx != -1:
            return text[idx + 1 :].strip()
    return text.strip()


def _sentences_similar(a: str, b: str, threshold: float = 0.8) -> bool:
    """Return ``True`` if *a* and *b* share at least *threshold* word overlap."""
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return False
    overlap = len(words_a & words_b) / min(len(words_a), len(words_b))
    return overlap >= threshold
