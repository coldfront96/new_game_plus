"""
tests/core/test_registry.py
---------------------------
Unit tests for the generic :class:`~src.core.registry.Registry`.

Covers:
- Registration, lookup, require-vs-get semantics.
- Duplicate-key protection and the ``overwrite`` escape hatch.
- Unregister, iteration helpers, membership, length, repr.
- Generic typing: the same Registry implementation works for strings,
  dataclasses, and arbitrary objects.
"""

from dataclasses import dataclass

import pytest

from src.core.registry import Registry


# ---------------------------------------------------------------------------
# Basic lifecycle
# ---------------------------------------------------------------------------

class TestRegistryBasics:
    def test_empty_registry_has_zero_len(self):
        reg: Registry[str] = Registry("materials")
        assert len(reg) == 0

    def test_empty_registry_get_returns_none(self):
        reg: Registry[str] = Registry()
        assert reg.get("missing") is None

    def test_register_and_get(self):
        reg: Registry[str] = Registry("materials")
        reg.register("stone", "STONE")
        assert reg.get("stone") == "STONE"

    def test_register_increments_length(self):
        reg: Registry[int] = Registry()
        reg.register("a", 1)
        reg.register("b", 2)
        assert len(reg) == 2

    def test_default_registry_name(self):
        reg: Registry[int] = Registry()
        assert reg.name == "registry"

    def test_custom_registry_name(self):
        reg: Registry[int] = Registry("spells")
        assert reg.name == "spells"


# ---------------------------------------------------------------------------
# Duplicate protection & overwrite semantics
# ---------------------------------------------------------------------------

class TestRegistryDuplicateProtection:
    def test_duplicate_key_raises_by_default(self):
        reg: Registry[str] = Registry("materials")
        reg.register("stone", "STONE")
        with pytest.raises(KeyError, match="already registered"):
            reg.register("stone", "GRANITE")

    def test_duplicate_key_error_mentions_registry_name(self):
        reg: Registry[str] = Registry("materials")
        reg.register("stone", "STONE")
        with pytest.raises(KeyError, match="materials"):
            reg.register("stone", "GRANITE")

    def test_duplicate_key_error_mentions_key(self):
        reg: Registry[str] = Registry("materials")
        reg.register("stone", "STONE")
        with pytest.raises(KeyError, match="'stone'"):
            reg.register("stone", "GRANITE")

    def test_overwrite_true_replaces_value(self):
        reg: Registry[str] = Registry()
        reg.register("stone", "STONE")
        reg.register("stone", "GRANITE", overwrite=True)
        assert reg.get("stone") == "GRANITE"

    def test_overwrite_does_not_increase_length(self):
        reg: Registry[str] = Registry()
        reg.register("stone", "STONE")
        reg.register("stone", "GRANITE", overwrite=True)
        assert len(reg) == 1

    def test_failed_duplicate_register_preserves_original_value(self):
        reg: Registry[str] = Registry("materials")
        reg.register("stone", "STONE")
        with pytest.raises(KeyError):
            reg.register("stone", "GRANITE")
        assert reg.get("stone") == "STONE"


# ---------------------------------------------------------------------------
# require() vs get()
# ---------------------------------------------------------------------------

class TestRegistryRequire:
    def test_require_returns_registered_value(self):
        reg: Registry[int] = Registry()
        reg.register("x", 42)
        assert reg.require("x") == 42

    def test_require_missing_key_raises(self):
        reg: Registry[int] = Registry("spells")
        with pytest.raises(KeyError, match="not registered"):
            reg.require("absent")

    def test_require_error_mentions_registry_name_and_key(self):
        reg: Registry[int] = Registry("spells")
        with pytest.raises(KeyError, match="spells"):
            reg.require("absent")
        with pytest.raises(KeyError, match="'absent'"):
            reg.require("absent")


# ---------------------------------------------------------------------------
# unregister
# ---------------------------------------------------------------------------

class TestRegistryUnregister:
    def test_unregister_returns_removed_value(self):
        reg: Registry[str] = Registry()
        reg.register("stone", "STONE")
        assert reg.unregister("stone") == "STONE"

    def test_unregister_decreases_length(self):
        reg: Registry[str] = Registry()
        reg.register("stone", "STONE")
        reg.register("dirt", "DIRT")
        reg.unregister("stone")
        assert len(reg) == 1

    def test_unregister_missing_key_returns_none(self):
        reg: Registry[str] = Registry()
        assert reg.unregister("missing") is None

    def test_unregister_then_get_returns_none(self):
        reg: Registry[str] = Registry()
        reg.register("stone", "STONE")
        reg.unregister("stone")
        assert reg.get("stone") is None

    def test_unregister_then_register_same_key_succeeds(self):
        reg: Registry[str] = Registry()
        reg.register("stone", "STONE")
        reg.unregister("stone")
        reg.register("stone", "GRANITE")
        assert reg.get("stone") == "GRANITE"


# ---------------------------------------------------------------------------
# Iteration and membership
# ---------------------------------------------------------------------------

class TestRegistryIteration:
    def test_keys_iterates_all_keys(self):
        reg: Registry[int] = Registry()
        reg.register("a", 1)
        reg.register("b", 2)
        reg.register("c", 3)
        assert set(reg.keys()) == {"a", "b", "c"}

    def test_values_iterates_all_values(self):
        reg: Registry[int] = Registry()
        reg.register("a", 1)
        reg.register("b", 2)
        reg.register("c", 3)
        assert set(reg.values()) == {1, 2, 3}

    def test_keys_on_empty_registry(self):
        reg: Registry[int] = Registry()
        assert list(reg.keys()) == []

    def test_values_on_empty_registry(self):
        reg: Registry[int] = Registry()
        assert list(reg.values()) == []

    def test_contains_true_for_registered_key(self):
        reg: Registry[int] = Registry()
        reg.register("x", 42)
        assert "x" in reg

    def test_contains_false_for_missing_key(self):
        reg: Registry[int] = Registry()
        assert "x" not in reg

    def test_contains_false_after_unregister(self):
        reg: Registry[int] = Registry()
        reg.register("x", 42)
        reg.unregister("x")
        assert "x" not in reg


# ---------------------------------------------------------------------------
# __repr__
# ---------------------------------------------------------------------------

class TestRegistryRepr:
    def test_repr_empty(self):
        reg: Registry[int] = Registry("materials")
        assert repr(reg) == "Registry('materials', 0 entries)"

    def test_repr_with_entries(self):
        reg: Registry[int] = Registry("materials")
        reg.register("a", 1)
        reg.register("b", 2)
        assert repr(reg) == "Registry('materials', 2 entries)"

    def test_repr_uses_registry_name(self):
        reg: Registry[int] = Registry("spells")
        assert "spells" in repr(reg)


# ---------------------------------------------------------------------------
# Generic typing — holds arbitrary value types
# ---------------------------------------------------------------------------

@dataclass
class _Material:
    name: str
    hardness: int


class TestRegistryGenericTyping:
    def test_registry_holds_dataclass_instances(self):
        reg: Registry[_Material] = Registry("materials")
        stone = _Material(name="Stone", hardness=7)
        reg.register("stone", stone)
        assert reg.get("stone") is stone
        assert reg.get("stone").hardness == 7

    def test_registry_holds_callables(self):
        def greet() -> str:
            return "hello"

        reg: Registry = Registry("handlers")
        reg.register("greet", greet)
        assert reg.get("greet")() == "hello"

    def test_registry_holds_none_value(self):
        # A Registry value of None must be distinguishable from "key absent"
        # at the require() level, even though get() cannot distinguish.
        reg: Registry = Registry()
        reg.register("nothing", None)
        assert "nothing" in reg
        assert reg.require("nothing") is None
        # get() cannot disambiguate (documented limitation):
        assert reg.get("nothing") is None
        assert reg.get("also-missing") is None
