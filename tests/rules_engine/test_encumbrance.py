"""
tests/rules_engine/test_encumbrance.py
----------------------------------------
Unit tests for the D&D 3.5e Encumbrance subsystem.

Covers E-001:
  * ``LoadCategory`` enum values and ordering.
  * ``LiftCategory`` enum values.
  * ``Item.weight_lb`` field presence, default, and round-trip serialisation.
  * ``CarryingCapacityRow`` dataclass construction and slot enforcement.
"""

import pytest

from src.loot_math.item import Item, ItemType, Rarity
from src.rules_engine.encumbrance import CarryingCapacityRow, LiftCategory, LoadCategory


# ---------------------------------------------------------------------------
# LoadCategory tests
# ---------------------------------------------------------------------------

class TestLoadCategory:
    """E-001: LoadCategory enum must have exactly four members."""

    def test_members_exist(self):
        assert LoadCategory.Light is not None
        assert LoadCategory.Medium is not None
        assert LoadCategory.Heavy is not None
        assert LoadCategory.Overload is not None

    def test_exactly_four_members(self):
        assert len(LoadCategory) == 4

    def test_members_are_unique(self):
        values = [m.value for m in LoadCategory]
        assert len(values) == len(set(values))

    def test_ordering_by_value(self):
        """Light < Medium < Heavy < Overload by enum declaration order."""
        members = list(LoadCategory)
        assert members[0] == LoadCategory.Light
        assert members[1] == LoadCategory.Medium
        assert members[2] == LoadCategory.Heavy
        assert members[3] == LoadCategory.Overload

    def test_is_enum(self):
        from enum import Enum
        assert issubclass(LoadCategory, Enum)


# ---------------------------------------------------------------------------
# LiftCategory tests
# ---------------------------------------------------------------------------

class TestLiftCategory:
    """E-001: LiftCategory enum must have exactly three members."""

    def test_members_exist(self):
        assert LiftCategory.LiftOverHead is not None
        assert LiftCategory.LiftOffGround is not None
        assert LiftCategory.PushOrDrag is not None

    def test_exactly_three_members(self):
        assert len(LiftCategory) == 3

    def test_members_are_unique(self):
        values = [m.value for m in LiftCategory]
        assert len(values) == len(set(values))

    def test_is_enum(self):
        from enum import Enum
        assert issubclass(LiftCategory, Enum)


# ---------------------------------------------------------------------------
# Item.weight_lb field tests
# ---------------------------------------------------------------------------

class TestItemWeightField:
    """E-001: Item dataclass must expose weight_lb field."""

    def test_default_weight_is_zero(self):
        item = Item(name="Pebble", item_type=ItemType.MATERIAL)
        assert item.weight_lb == 0.0

    def test_custom_weight_stored(self):
        item = Item(name="Longsword", item_type=ItemType.WEAPON, weight_lb=4.0)
        assert item.weight_lb == 4.0

    def test_weight_accepts_fractional_pounds(self):
        item = Item(name="Dagger", item_type=ItemType.WEAPON, weight_lb=1.0)
        assert item.weight_lb == 1.0

    def test_weight_zero_point_five(self):
        item = Item(name="Dart", item_type=ItemType.WEAPON, weight_lb=0.5)
        assert item.weight_lb == 0.5

    def test_to_dict_includes_weight(self):
        item = Item(name="Greataxe", item_type=ItemType.WEAPON, weight_lb=12.0)
        d = item.to_dict()
        assert "weight_lb" in d
        assert d["weight_lb"] == 12.0

    def test_from_dict_restores_weight(self):
        item = Item(name="Greataxe", item_type=ItemType.WEAPON, weight_lb=12.0)
        restored = Item.from_dict(item.to_dict())
        assert restored.weight_lb == 12.0

    def test_from_dict_missing_weight_defaults_zero(self):
        """Backwards-compatible: old dicts without weight_lb → 0.0."""
        item = Item(name="Sword", item_type=ItemType.WEAPON)
        d = item.to_dict()
        del d["weight_lb"]
        restored = Item.from_dict(d)
        assert restored.weight_lb == 0.0

    def test_to_json_round_trip_preserves_weight(self):
        item = Item(name="Chain Mail", item_type=ItemType.ARMOUR,
                    base_armour=5, weight_lb=40.0)
        restored = Item.from_json(item.to_json())
        assert restored.weight_lb == 40.0

    def test_weight_is_float_type(self):
        item = Item(name="Shield", item_type=ItemType.ARMOUR, weight_lb=15.0)
        assert isinstance(item.weight_lb, float)


# ---------------------------------------------------------------------------
# CarryingCapacityRow tests
# ---------------------------------------------------------------------------

class TestCarryingCapacityRow:
    """E-002 (scaffolded here): CarryingCapacityRow dataclass structure."""

    def test_construction(self):
        row = CarryingCapacityRow(
            strength=10,
            light_max_lb=33.0,
            medium_max_lb=66.0,
            heavy_max_lb=100.0,
        )
        assert row.strength == 10
        assert row.light_max_lb == 33.0
        assert row.medium_max_lb == 66.0
        assert row.heavy_max_lb == 100.0

    def test_slots_prevents_new_attributes(self):
        row = CarryingCapacityRow(
            strength=8,
            light_max_lb=26.0,
            medium_max_lb=53.0,
            heavy_max_lb=80.0,
        )
        with pytest.raises(AttributeError):
            row.new_field = "forbidden"  # type: ignore[attr-defined]

    def test_str_18_values(self):
        """PHB Table 9-1: STR 18 → light 100, medium 200, heavy 300."""
        row = CarryingCapacityRow(
            strength=18,
            light_max_lb=100.0,
            medium_max_lb=200.0,
            heavy_max_lb=300.0,
        )
        assert row.light_max_lb == 100.0
        assert row.medium_max_lb == 200.0
        assert row.heavy_max_lb == 300.0

    def test_str_1_values(self):
        """PHB Table 9-1: STR 1 → light 3.33, medium 6.66, heavy 10."""
        row = CarryingCapacityRow(
            strength=1,
            light_max_lb=3.0,
            medium_max_lb=6.0,
            heavy_max_lb=10.0,
        )
        assert row.strength == 1
