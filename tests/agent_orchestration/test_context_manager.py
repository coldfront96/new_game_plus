"""Tests for src.agent_orchestration.context_manager."""

from __future__ import annotations

import pytest

from src.agent_orchestration.context_manager import (
    ContextManager,
    ContextWindow,
    estimate_tokens,
    _sentences_similar,
)


# ---------------------------------------------------------------------------
# estimate_tokens
# ---------------------------------------------------------------------------

def test_estimate_tokens_single_word():
    assert estimate_tokens("hello") >= 1


def test_estimate_tokens_scales_with_length():
    short = estimate_tokens("hello world")
    long  = estimate_tokens("hello world " * 10)
    assert long > short


def test_estimate_tokens_empty_string():
    assert estimate_tokens("") >= 1  # min-clamp to 1


# ---------------------------------------------------------------------------
# ContextWindow
# ---------------------------------------------------------------------------

def test_context_window_prompt_budget():
    w = ContextWindow(model_id="test", max_tokens=1024, reserved_for_response=200)
    assert w.prompt_budget == 824


def test_context_window_prompt_budget_floor():
    w = ContextWindow(model_id="test", max_tokens=100, reserved_for_response=200)
    assert w.prompt_budget >= 1


# ---------------------------------------------------------------------------
# ContextManager.fits
# ---------------------------------------------------------------------------

def test_fits_small_prompts():
    window = ContextWindow(model_id="m", max_tokens=4096, reserved_for_response=512)
    cm = ContextManager(window)
    assert cm.fits("You are a DM.", "Describe the tavern.") is True


def test_fits_huge_user_prompt():
    window = ContextWindow(model_id="m", max_tokens=100, reserved_for_response=10)
    cm = ContextManager(window)
    huge = "word " * 10_000
    assert cm.fits("System.", huge) is False


# ---------------------------------------------------------------------------
# ContextManager.chunk_prompt — no splitting needed
# ---------------------------------------------------------------------------

def test_chunk_prompt_single_chunk_when_fits():
    window = ContextWindow(model_id="m", max_tokens=4096, reserved_for_response=512)
    cm = ContextManager(window)
    chunks = cm.chunk_prompt("System context.", "Short user message.")
    assert len(chunks) == 1
    assert "System context." in chunks[0]
    assert "Short user message." in chunks[0]


# ---------------------------------------------------------------------------
# ContextManager.chunk_prompt — splitting
# ---------------------------------------------------------------------------

def test_chunk_prompt_splits_long_prompt():
    window = ContextWindow(
        model_id="m",
        max_tokens=50,
        reserved_for_response=10,
        overlap_tokens=5,
    )
    cm = ContextManager(window)
    long_user = "word " * 200
    chunks = cm.chunk_prompt("Sys.", long_user)
    assert len(chunks) > 1


def test_each_chunk_contains_system_prompt():
    window = ContextWindow(
        model_id="m",
        max_tokens=50,
        reserved_for_response=10,
        overlap_tokens=5,
    )
    cm = ContextManager(window)
    long_user = "word " * 200
    chunks = cm.chunk_prompt("SYSTEM_MARKER", long_user)
    for chunk in chunks:
        assert "SYSTEM_MARKER" in chunk


def test_chunk_count_matches_chunks():
    window = ContextWindow(
        model_id="m",
        max_tokens=50,
        reserved_for_response=10,
        overlap_tokens=0,
    )
    cm = ContextManager(window)
    long_user = "word " * 300
    assert cm.chunk_count("Sys.", long_user) == len(cm.chunk_prompt("Sys.", long_user))


def test_chunks_cover_all_content():
    window = ContextWindow(
        model_id="m",
        max_tokens=50,
        reserved_for_response=10,
        overlap_tokens=0,
    )
    cm = ContextManager(window)
    words = [f"w{i}" for i in range(200)]
    long_user = " ".join(words)
    chunks = cm.chunk_prompt("S.", long_user)
    all_text = " ".join(chunks)
    # Every word should appear at least once across all chunks.
    for word in words:
        assert word in all_text


# ---------------------------------------------------------------------------
# ContextManager.stitch_results
# ---------------------------------------------------------------------------

def test_stitch_empty():
    cm = ContextManager(ContextWindow(model_id="m", max_tokens=4096))
    assert cm.stitch_results([]) == ""


def test_stitch_single():
    cm = ContextManager(ContextWindow(model_id="m", max_tokens=4096))
    assert cm.stitch_results(["Hello world."]) == "Hello world."


def test_stitch_multiple_distinct():
    cm = ContextManager(ContextWindow(model_id="m", max_tokens=4096))
    result = cm.stitch_results(["Part one.", "Part two.", "Part three."])
    assert "Part one" in result
    assert "Part two" in result
    assert "Part three" in result


def test_stitch_separator():
    cm = ContextManager(ContextWindow(model_id="m", max_tokens=4096))
    result = cm.stitch_results(["A", "B"], separator=" | ")
    assert "|" in result


# ---------------------------------------------------------------------------
# _sentences_similar
# ---------------------------------------------------------------------------

def test_sentences_similar_identical():
    assert _sentences_similar("the quick brown fox", "the quick brown fox") is True


def test_sentences_similar_different():
    assert _sentences_similar("the quick brown fox", "a slow green turtle") is False


def test_sentences_similar_empty():
    assert _sentences_similar("", "something") is False
