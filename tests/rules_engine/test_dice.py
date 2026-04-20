"""
tests/rules_engine/test_dice.py
-------------------------------
Unit tests for src.rules_engine.dice (dice rolling utilities).
"""

import pytest

from src.rules_engine.dice import RollResult, roll_d20, roll_damage, roll_dice


# ---------------------------------------------------------------------------
# RollResult dataclass
# ---------------------------------------------------------------------------

class TestRollResult:
    def test_slots_enabled(self):
        assert hasattr(RollResult, "__slots__")

    def test_fields_stored(self):
        r = RollResult(raw=14, modifier=3, total=17)
        assert r.raw == 14
        assert r.modifier == 3
        assert r.total == 17

    def test_equality(self):
        a = RollResult(raw=10, modifier=2, total=12)
        b = RollResult(raw=10, modifier=2, total=12)
        assert a == b

    def test_repr(self):
        r = RollResult(raw=1, modifier=0, total=1)
        assert "RollResult" in repr(r)


# ---------------------------------------------------------------------------
# roll_dice
# ---------------------------------------------------------------------------

class TestRollDice:
    def test_single_d6(self):
        r = roll_dice(1, 6)
        assert 1 <= r.raw <= 6
        assert r.modifier == 0
        assert r.total == r.raw

    def test_with_modifier(self):
        r = roll_dice(1, 6, modifier=5)
        assert r.modifier == 5
        assert r.total == r.raw + 5

    def test_negative_modifier(self):
        r = roll_dice(1, 6, modifier=-3)
        assert r.modifier == -3
        assert r.total == r.raw - 3

    def test_multiple_dice(self):
        r = roll_dice(3, 6)
        assert 3 <= r.raw <= 18

    def test_count_zero_raises(self):
        with pytest.raises(ValueError, match="count"):
            roll_dice(0, 6)

    def test_sides_zero_raises(self):
        with pytest.raises(ValueError, match="sides"):
            roll_dice(1, 0)

    def test_deterministic_d1(self):
        """A 1-sided die always yields 1."""
        r = roll_dice(5, 1)
        assert r.raw == 5
        assert r.total == 5


# ---------------------------------------------------------------------------
# roll_d20
# ---------------------------------------------------------------------------

class TestRollD20:
    def test_range(self):
        for _ in range(50):
            r = roll_d20()
            assert 1 <= r.raw <= 20

    def test_modifier_applied(self):
        r = roll_d20(modifier=7)
        assert r.modifier == 7
        assert r.total == r.raw + 7

    def test_negative_modifier(self):
        r = roll_d20(modifier=-2)
        assert r.modifier == -2

    def test_default_modifier_zero(self):
        r = roll_d20()
        assert r.modifier == 0


# ---------------------------------------------------------------------------
# roll_damage
# ---------------------------------------------------------------------------

class TestRollDamage:
    def test_simple_expression(self):
        r = roll_damage("2d6")
        assert 2 <= r.raw <= 12
        assert r.modifier == 0
        assert r.total == r.raw

    def test_plus_modifier(self):
        r = roll_damage("1d8+3")
        assert 1 <= r.raw <= 8
        assert r.modifier == 3
        assert r.total == r.raw + 3

    def test_minus_modifier(self):
        r = roll_damage("1d4-1")
        assert r.modifier == -1

    def test_whitespace_tolerance(self):
        r = roll_damage("  2d6 + 4 ")
        assert r.modifier == 4

    def test_uppercase_d(self):
        r = roll_damage("1D20+2")
        assert 1 <= r.raw <= 20
        assert r.modifier == 2

    def test_invalid_expression_raises(self):
        with pytest.raises(ValueError, match="Invalid"):
            roll_damage("not_a_roll")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="Invalid"):
            roll_damage("")

    def test_single_die(self):
        r = roll_damage("1d1")
        assert r.raw == 1
        assert r.total == 1
