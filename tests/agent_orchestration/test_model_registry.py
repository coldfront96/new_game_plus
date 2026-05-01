"""Tests for src.agent_orchestration.model_registry."""

from __future__ import annotations

import time

import pytest

from src.agent_orchestration.model_registry import (
    DEFAULT_MODELS,
    ModelCapability,
    ModelRecord,
    ModelRegistry,
)


def _make_model(
    model_id: str,
    capability: ModelCapability,
    vram_mb: int = 5_000,
) -> ModelRecord:
    return ModelRecord(
        model_id=model_id,
        model_family="Test",
        param_size_b=7.0,
        quantization="GPTQ 4-bit",
        vram_mb=vram_mb,
        context_window=4096,
        capabilities=frozenset({capability}),
    )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def test_default_models_register():
    reg = ModelRegistry()
    assert len(reg) == len(DEFAULT_MODELS)


def test_register_custom_model():
    reg = ModelRegistry(models=[])
    m = _make_model("custom-1", ModelCapability.CODE_GEN)
    reg.register(m)
    assert "custom-1" in reg


def test_register_duplicate_raises():
    reg = ModelRegistry(models=[])
    m = _make_model("dup", ModelCapability.CODE_GEN)
    reg.register(m)
    with pytest.raises(ValueError, match="already registered"):
        reg.register(m)


def test_get_returns_none_for_unknown():
    reg = ModelRegistry(models=[])
    assert reg.get("nonexistent") is None


def test_get_returns_model():
    reg = ModelRegistry()
    m = DEFAULT_MODELS[0]
    assert reg.get(m.model_id) is m


# ---------------------------------------------------------------------------
# DEFAULT_MODELS content
# ---------------------------------------------------------------------------

def test_default_fleet_has_code_gen():
    reg = ModelRegistry()
    assert reg.select(ModelCapability.CODE_GEN) is not None


def test_default_fleet_has_world_gen():
    reg = ModelRegistry()
    assert reg.select(ModelCapability.WORLD_GEN) is not None


def test_default_fleet_has_lore_npc():
    reg = ModelRegistry()
    assert reg.select(ModelCapability.LORE_NPC) is not None


def test_default_models_fit_in_budget():
    for m in DEFAULT_MODELS:
        assert m.vram_mb <= 16_384


# ---------------------------------------------------------------------------
# select
# ---------------------------------------------------------------------------

def test_select_returns_none_when_no_candidates():
    reg = ModelRegistry(models=[])
    assert reg.select(ModelCapability.CODE_GEN) is None


def test_select_prefers_loaded_model():
    reg = ModelRegistry(models=[])
    small = _make_model("small", ModelCapability.CODE_GEN, vram_mb=4_000)
    large = _make_model("large", ModelCapability.CODE_GEN, vram_mb=8_000)
    reg.register(small)
    reg.register(large)
    reg.mark_loaded("large")
    chosen = reg.select(ModelCapability.CODE_GEN, prefer_loaded=True)
    assert chosen is not None and chosen.model_id == "large"


def test_select_picks_smallest_vram_when_none_loaded():
    reg = ModelRegistry(models=[])
    big   = _make_model("big",   ModelCapability.WORLD_GEN, vram_mb=10_000)
    small = _make_model("small", ModelCapability.WORLD_GEN, vram_mb=4_000)
    reg.register(big)
    reg.register(small)
    chosen = reg.select(ModelCapability.WORLD_GEN, prefer_loaded=False)
    assert chosen is not None and chosen.model_id == "small"


def test_select_respects_vram_budget():
    reg = ModelRegistry(models=[], vram_budget_mb=3_000)
    too_big = _make_model("big", ModelCapability.CODE_GEN, vram_mb=4_000)
    reg.register(too_big)
    assert reg.select(ModelCapability.CODE_GEN) is None


def test_available_for():
    reg = ModelRegistry(models=[])
    a = _make_model("a", ModelCapability.CODE_GEN)
    b = _make_model("b", ModelCapability.LORE_NPC)
    reg.register(a)
    reg.register(b)
    code = reg.available_for(ModelCapability.CODE_GEN)
    assert len(code) == 1 and code[0].model_id == "a"


# ---------------------------------------------------------------------------
# Load / unload lifecycle
# ---------------------------------------------------------------------------

def test_mark_loaded_tracks_model():
    reg = ModelRegistry(models=[])
    m = _make_model("m1", ModelCapability.CODE_GEN, vram_mb=4_000)
    reg.register(m)
    reg.mark_loaded("m1")
    assert reg.vram_used_mb == 4_000


def test_mark_loaded_unknown_raises():
    reg = ModelRegistry(models=[])
    with pytest.raises(KeyError):
        reg.mark_loaded("unknown")


def test_mark_loaded_over_budget_raises():
    reg = ModelRegistry(models=[], vram_budget_mb=3_000)
    m = _make_model("big", ModelCapability.CODE_GEN, vram_mb=4_000)
    reg.register(m)
    with pytest.raises(ValueError, match="exceed"):
        reg.mark_loaded("big")


def test_mark_loaded_idempotent():
    reg = ModelRegistry(models=[])
    m = _make_model("m1", ModelCapability.CODE_GEN, vram_mb=4_000)
    reg.register(m)
    reg.mark_loaded("m1")
    reg.mark_loaded("m1")  # second call must not raise or double-count
    assert reg.vram_used_mb == 4_000


def test_mark_unloaded_frees_vram():
    reg = ModelRegistry(models=[])
    m = _make_model("m1", ModelCapability.CODE_GEN, vram_mb=4_000)
    reg.register(m)
    reg.mark_loaded("m1")
    reg.mark_unloaded("m1")
    assert reg.vram_used_mb == 0


def test_mark_unloaded_unknown_is_noop():
    reg = ModelRegistry(models=[])
    reg.mark_unloaded("ghost")  # must not raise


def test_mark_used_unknown_raises():
    reg = ModelRegistry(models=[])
    with pytest.raises(KeyError):
        reg.mark_used("ghost")


def test_mark_used_updates_timestamp():
    reg = ModelRegistry(models=[])
    m = _make_model("m1", ModelCapability.CODE_GEN)
    reg.register(m)
    reg.mark_loaded("m1")
    before = reg._loaded["m1"].last_used
    time.sleep(0.01)
    reg.mark_used("m1")
    assert reg._loaded["m1"].last_used > before


# ---------------------------------------------------------------------------
# VRAM introspection
# ---------------------------------------------------------------------------

def test_vram_remaining_empty():
    reg = ModelRegistry(models=[], vram_budget_mb=16_384)
    assert reg.vram_remaining_mb == 16_384


def test_vram_remaining_after_load():
    reg = ModelRegistry(models=[], vram_budget_mb=16_384)
    m = _make_model("m1", ModelCapability.CODE_GEN, vram_mb=6_144)
    reg.register(m)
    reg.mark_loaded("m1")
    assert reg.vram_remaining_mb == 16_384 - 6_144


# ---------------------------------------------------------------------------
# LRU eviction
# ---------------------------------------------------------------------------

def test_evict_lru_returns_none_when_empty():
    reg = ModelRegistry(models=[])
    assert reg.evict_lru() is None


def test_evict_lru_removes_oldest():
    reg = ModelRegistry(models=[], vram_budget_mb=16_384)
    a = _make_model("a", ModelCapability.CODE_GEN, vram_mb=4_000)
    b = _make_model("b", ModelCapability.WORLD_GEN, vram_mb=4_000)
    reg.register(a)
    reg.register(b)
    reg.mark_loaded("a")
    time.sleep(0.01)
    reg.mark_loaded("b")
    reg.mark_used("b")
    evicted = reg.evict_lru()
    assert evicted == "a"
    assert reg.vram_used_mb == 4_000


def test_evict_to_fit_noop_if_already_loaded():
    reg = ModelRegistry(models=[], vram_budget_mb=16_384)
    m = _make_model("m1", ModelCapability.CODE_GEN, vram_mb=4_000)
    reg.register(m)
    reg.mark_loaded("m1")
    evicted = reg.evict_to_fit("m1")
    assert evicted == []
    assert reg.vram_used_mb == 4_000


def test_evict_to_fit_makes_room():
    reg = ModelRegistry(models=[], vram_budget_mb=8_000)
    a = _make_model("a", ModelCapability.CODE_GEN,  vram_mb=5_000)
    b = _make_model("b", ModelCapability.WORLD_GEN, vram_mb=5_000)
    reg.register(a)
    reg.register(b)
    reg.mark_loaded("a")
    evicted = reg.evict_to_fit("b")
    assert "a" in evicted
    assert reg.vram_remaining_mb >= 5_000


def test_evict_to_fit_unknown_raises():
    reg = ModelRegistry(models=[])
    with pytest.raises(KeyError):
        reg.evict_to_fit("ghost")


def test_evict_to_fit_over_budget_raises():
    reg = ModelRegistry(models=[], vram_budget_mb=3_000)
    m = _make_model("big", ModelCapability.CODE_GEN, vram_mb=5_000)
    reg.register(m)
    with pytest.raises(ValueError, match="exceeds the total budget"):
        reg.evict_to_fit("big")


# ---------------------------------------------------------------------------
# loaded_models property
# ---------------------------------------------------------------------------

def test_loaded_models_empty_initially():
    reg = ModelRegistry(models=[])
    assert reg.loaded_models == []


def test_loaded_models_reflects_state():
    reg = ModelRegistry(models=[], vram_budget_mb=16_384)
    m = _make_model("m1", ModelCapability.CODE_GEN)
    reg.register(m)
    reg.mark_loaded("m1")
    assert any(r.model_id == "m1" for r in reg.loaded_models)
