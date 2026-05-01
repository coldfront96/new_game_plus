"""
tests/ai_sim/test_entity_deep_lore.py
----------------------------------------
Unit tests for PH6-008 — Entity.deep_lore_filepath optional field.
"""
from __future__ import annotations

import json
import pytest

from src.ai_sim.entity import Entity


# ---------------------------------------------------------------------------
# PH6-008 · deep_lore_filepath field
# ---------------------------------------------------------------------------

class TestDeepLoreFilepath:
    def test_default_is_none(self):
        e = Entity(name="Nira")
        assert e.deep_lore_filepath is None

    def test_can_set_filepath(self):
        e = Entity(name="Nira")
        e.deep_lore_filepath = "/data/npc/nira_backstory.txt"
        assert e.deep_lore_filepath == "/data/npc/nira_backstory.txt"

    def test_accepts_relative_path(self):
        e = Entity(name="Nira")
        e.deep_lore_filepath = "data/npc/nira.txt"
        assert e.deep_lore_filepath == "data/npc/nira.txt"

    def test_can_be_reset_to_none(self):
        e = Entity(name="Nira")
        e.deep_lore_filepath = "/tmp/lore.txt"
        e.deep_lore_filepath = None
        assert e.deep_lore_filepath is None

    def test_entity_still_has_all_other_fields(self):
        e = Entity(name="Nira")
        assert hasattr(e, "entity_id")
        assert hasattr(e, "is_active")
        assert hasattr(e, "tags")
        assert hasattr(e, "metadata")

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def test_to_dict_omits_field_when_none(self):
        e = Entity(name="Nira")
        d = e.to_dict()
        assert "deep_lore_filepath" not in d

    def test_to_dict_includes_field_when_set(self):
        e = Entity(name="Nira")
        e.deep_lore_filepath = "/data/nira.txt"
        d = e.to_dict()
        assert d["deep_lore_filepath"] == "/data/nira.txt"

    def test_from_dict_restores_filepath(self):
        original = Entity(name="Nira")
        original.deep_lore_filepath = "/data/nira.txt"
        restored = Entity.from_dict(original.to_dict())
        assert restored.deep_lore_filepath == "/data/nira.txt"

    def test_from_dict_filepath_none_when_absent(self):
        d = {"entity_id": "abc", "name": "Nira", "is_active": True, "tags": []}
        e = Entity.from_dict(d)
        assert e.deep_lore_filepath is None

    def test_to_json_round_trip_with_filepath(self):
        original = Entity(name="Nira")
        original.deep_lore_filepath = "/lore/nira.txt"
        restored = Entity.from_json(original.to_json())
        assert restored.deep_lore_filepath == "/lore/nira.txt"

    def test_to_json_round_trip_without_filepath(self):
        original = Entity(name="Nira")
        restored = Entity.from_json(original.to_json())
        assert restored.deep_lore_filepath is None

    def test_json_is_valid_json_with_filepath(self):
        e = Entity(name="Nira")
        e.deep_lore_filepath = "/tmp/x.txt"
        parsed = json.loads(e.to_json())
        assert parsed["deep_lore_filepath"] == "/tmp/x.txt"


# ---------------------------------------------------------------------------
# metadata field
# ---------------------------------------------------------------------------

class TestMetadataField:
    def test_metadata_default_empty_dict(self):
        e = Entity(name="Aldric")
        assert e.metadata == {}

    def test_metadata_is_independent_between_instances(self):
        e1 = Entity(name="A")
        e2 = Entity(name="B")
        e1.metadata["key"] = "value"
        assert "key" not in e2.metadata
