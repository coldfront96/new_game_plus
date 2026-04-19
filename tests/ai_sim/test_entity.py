"""
tests/ai_sim/test_entity.py
---------------------------
Unit tests for src.ai_sim.entity (Entity base class).
"""

import json
import pytest

from src.ai_sim.entity import Entity
from src.ai_sim.components import Position, Health, Needs, Stats, Inventory


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

class TestEntityConstruction:
    def test_name_stored(self):
        e = Entity(name="Aldric")
        assert e.name == "Aldric"

    def test_entity_id_auto_generated(self):
        e = Entity(name="Aldric")
        assert isinstance(e.entity_id, str) and len(e.entity_id) == 36  # UUID4

    def test_explicit_entity_id(self):
        e = Entity(name="Aldric", entity_id="fixed-id-123")
        assert e.entity_id == "fixed-id-123"

    def test_active_by_default(self):
        e = Entity(name="Aldric")
        assert e.is_active is True

    def test_no_tags_by_default(self):
        e = Entity(name="Aldric")
        assert len(e.tags) == 0

    def test_no_components_by_default(self):
        e = Entity(name="Aldric")
        assert len(e.components) == 0


# ---------------------------------------------------------------------------
# Component management
# ---------------------------------------------------------------------------

class TestEntityComponents:
    def test_add_and_get_component(self):
        e = Entity(name="Aldric")
        pos = Position(x=10, y=64, z=10)
        e.add_component(pos)
        retrieved = e.get_component(Position)
        assert retrieved is pos

    def test_has_component_true(self):
        e = Entity(name="Aldric")
        e.add_component(Health(current=100, maximum=100))
        assert e.has_component(Health) is True

    def test_has_component_false(self):
        e = Entity(name="Aldric")
        assert e.has_component(Health) is False

    def test_get_missing_component_returns_none(self):
        e = Entity(name="Aldric")
        assert e.get_component(Health) is None

    def test_add_component_replaces_existing(self):
        e = Entity(name="Aldric")
        old_hp = Health(current=100, maximum=100)
        new_hp = Health(current=50, maximum=200)
        e.add_component(old_hp)
        e.add_component(new_hp)
        assert e.get_component(Health) is new_hp

    def test_remove_component(self):
        e = Entity(name="Aldric")
        pos = Position()
        e.add_component(pos)
        removed = e.remove_component(Position)
        assert removed is pos
        assert e.has_component(Position) is False

    def test_remove_missing_component_returns_none(self):
        e = Entity(name="Aldric")
        assert e.remove_component(Position) is None

    def test_add_component_fluent_chaining(self):
        e = Entity(name="Aldric")
        result = e.add_component(Position()).add_component(Health(current=80, maximum=80))
        assert result is e
        assert e.has_component(Position)
        assert e.has_component(Health)

    def test_components_property_is_copy(self):
        e = Entity(name="Aldric")
        e.add_component(Stats())
        snapshot = e.components
        # Mutating the snapshot should not affect the entity
        snapshot.clear()
        assert e.has_component(Stats) is True

    def test_multiple_component_types(self):
        e = Entity(name="Aldric")
        e.add_component(Position(x=5, y=70, z=5))
        e.add_component(Health(current=80, maximum=100))
        e.add_component(Stats(strength=15))
        assert e.has_component(Position)
        assert e.has_component(Health)
        assert e.has_component(Stats)
        assert len(e.components) == 3


# ---------------------------------------------------------------------------
# Tag management
# ---------------------------------------------------------------------------

class TestEntityTags:
    def test_add_tag(self):
        e = Entity(name="Aldric")
        e.add_tag("colonist")
        assert e.has_tag("colonist") is True

    def test_add_tag_fluent_chaining(self):
        e = Entity(name="Aldric")
        result = e.add_tag("colonist").add_tag("warrior")
        assert result is e
        assert e.has_tag("warrior")

    def test_add_empty_tag_raises(self):
        e = Entity(name="Aldric")
        with pytest.raises(ValueError):
            e.add_tag("")

    def test_remove_tag_present(self):
        e = Entity(name="Aldric")
        e.add_tag("on_fire")
        removed = e.remove_tag("on_fire")
        assert removed is True
        assert not e.has_tag("on_fire")

    def test_remove_tag_absent(self):
        e = Entity(name="Aldric")
        assert e.remove_tag("ghost_tag") is False

    def test_has_all_tags_true(self):
        e = Entity(name="Aldric")
        e.add_tag("colonist").add_tag("warrior")
        assert e.has_all_tags("colonist", "warrior") is True

    def test_has_all_tags_partial_false(self):
        e = Entity(name="Aldric")
        e.add_tag("colonist")
        assert e.has_all_tags("colonist", "warrior") is False

    def test_has_any_tag_true(self):
        e = Entity(name="Aldric")
        e.add_tag("miner")
        assert e.has_any_tag("warrior", "miner") is True

    def test_has_any_tag_false(self):
        e = Entity(name="Aldric")
        assert e.has_any_tag("warrior", "miner") is False

    def test_duplicate_tag_has_no_effect(self):
        e = Entity(name="Aldric")
        e.add_tag("colonist")
        e.add_tag("colonist")
        # Sets deduplicate; only one entry expected
        assert sum(1 for t in e.tags if t == "colonist") == 1


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

class TestEntityLifecycle:
    def test_destroy_marks_inactive(self):
        e = Entity(name="Aldric")
        e.destroy()
        assert e.is_active is False


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

class TestEntitySerialisation:
    def test_to_dict_contains_required_keys(self):
        e = Entity(name="Aldric")
        d = e.to_dict()
        for key in ("entity_id", "name", "is_active", "tags", "component_types"):
            assert key in d

    def test_from_dict_round_trip(self):
        original = Entity(name="Bridget", entity_id="abc-123", is_active=False)
        original.add_tag("healer")
        restored = Entity.from_dict(original.to_dict())
        assert restored.entity_id == original.entity_id
        assert restored.name == original.name
        assert restored.is_active == original.is_active
        assert "healer" in restored.tags

    def test_to_json_round_trip(self):
        original = Entity(name="Corvin")
        original.add_tag("ranger")
        json_str = original.to_json()
        restored = Entity.from_json(json_str)
        assert restored.entity_id == original.entity_id
        assert restored.name == original.name

    def test_json_is_valid_json(self):
        e = Entity(name="Doris")
        parsed = json.loads(e.to_json())
        assert parsed["name"] == "Doris"


# ---------------------------------------------------------------------------
# Equality and hashing
# ---------------------------------------------------------------------------

class TestEntityEquality:
    def test_same_id_equal(self):
        e1 = Entity(name="Alpha", entity_id="same-id")
        e2 = Entity(name="Beta", entity_id="same-id")
        assert e1 == e2

    def test_different_id_not_equal(self):
        e1 = Entity(name="Alpha")
        e2 = Entity(name="Alpha")
        assert e1 != e2  # UUIDs differ

    def test_hashable_usable_in_set(self):
        e = Entity(name="Alpha", entity_id="hash-test")
        entity_set = {e}
        assert e in entity_set

    def test_repr_contains_name(self):
        e = Entity(name="Aldric")
        assert "Aldric" in repr(e)
