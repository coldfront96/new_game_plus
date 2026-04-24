"""Tests for src/rules_engine/treasure.py"""
from __future__ import annotations

import random
import pytest

from src.rules_engine.treasure import (
    GemGrade, GemEntry, ArtObjectCategory, ArtObjectEntry,
    CoinRoll, TreasureTypeEntry, TreasureHoard,
    GEM_TABLE, ART_OBJECT_TABLE, TREASURE_TYPE_TABLES, CR_TO_TREASURE_TYPE,
    roll_gem_value, roll_art_object, generate_treasure_hoard,
)


# ---------------------------------------------------------------------------
# Schema / dataclass tests
# ---------------------------------------------------------------------------

class TestGemEntry:
    def test_slots(self):
        gem = GemEntry("Test", GemGrade.ORNAMENTAL, 10, (4, 16))
        assert gem.name == "Test"
        assert gem.grade == GemGrade.ORNAMENTAL
        assert gem.base_value_gp == 10
        assert gem.value_range_gp == (4, 16)

    def test_no_dict(self):
        gem = GemEntry("Test", GemGrade.ORNAMENTAL, 10, (4, 16))
        assert not hasattr(gem, "__dict__")


class TestArtObjectEntry:
    def test_slots(self):
        art = ArtObjectEntry("Crown", ArtObjectCategory.EXOTIC, 5000)
        assert art.name == "Crown"
        assert art.category == ArtObjectCategory.EXOTIC
        assert art.value_gp == 5000

    def test_no_dict(self):
        art = ArtObjectEntry("Crown", ArtObjectCategory.EXOTIC, 5000)
        assert not hasattr(art, "__dict__")


class TestCoinRoll:
    def test_fields(self):
        cr = CoinRoll(count=2, die=6, multiplier=1000)
        assert cr.count == 2
        assert cr.die == 6
        assert cr.multiplier == 1000


class TestTreasureHoard:
    def test_fields(self):
        hoard = TreasureHoard(
            coins={"gp": 100},
            gems=[],
            art_objects=[],
            magic_item_count=0,
            total_value_gp=100.0,
        )
        assert hoard.coins == {"gp": 100}
        assert hoard.total_value_gp == 100.0
        assert hoard.magic_item_count == 0


# ---------------------------------------------------------------------------
# GemGrade enum
# ---------------------------------------------------------------------------

class TestGemGrade:
    def test_all_grades_exist(self):
        expected = {"ORNAMENTAL", "SEMIPRECIOUS", "FANCY", "PRECIOUS", "GEMSTONE", "JEWEL"}
        actual = {g.name for g in GemGrade}
        assert expected == actual


class TestArtObjectCategory:
    def test_all_categories(self):
        expected = {"MUNDANE", "DECORATED", "MASTERWORK", "EXOTIC"}
        assert {c.name for c in ArtObjectCategory} == expected


# ---------------------------------------------------------------------------
# GEM_TABLE
# ---------------------------------------------------------------------------

class TestGemTable:
    def test_minimum_entries(self):
        assert len(GEM_TABLE) >= 30

    def test_all_grades_represented(self):
        grades = {gem.grade for gem in GEM_TABLE}
        assert grades == set(GemGrade)

    def test_ornamental_base_value(self):
        ornamentals = [g for g in GEM_TABLE if g.grade == GemGrade.ORNAMENTAL]
        assert all(g.base_value_gp == 10 for g in ornamentals)
        assert len(ornamentals) >= 5

    def test_jewel_base_value(self):
        jewels = [g for g in GEM_TABLE if g.grade == GemGrade.JEWEL]
        assert all(g.base_value_gp == 5000 for g in jewels)
        assert len(jewels) >= 3

    def test_value_range_is_tuple_of_two_ints(self):
        for gem in GEM_TABLE:
            lo, hi = gem.value_range_gp
            assert lo > 0
            assert hi > lo


# ---------------------------------------------------------------------------
# ART_OBJECT_TABLE
# ---------------------------------------------------------------------------

class TestArtObjectTable:
    def test_minimum_entries(self):
        assert len(ART_OBJECT_TABLE) >= 50

    def test_all_categories_represented(self):
        cats = {a.category for a in ART_OBJECT_TABLE}
        assert cats == set(ArtObjectCategory)

    def test_values_positive(self):
        assert all(a.value_gp > 0 for a in ART_OBJECT_TABLE)

    def test_multiple_value_bands(self):
        values = {a.value_gp for a in ART_OBJECT_TABLE}
        assert len(values) >= 8


# ---------------------------------------------------------------------------
# TREASURE_TYPE_TABLES
# ---------------------------------------------------------------------------

class TestTreasureTypeTables:
    def test_all_26_types(self):
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            assert letter in TREASURE_TYPE_TABLES, f"Missing treasure type {letter}"

    def test_type_a_has_four_coin_rolls(self):
        entry = TREASURE_TYPE_TABLES["A"]
        assert len(entry.coin_rolls) == 4

    def test_type_b_has_three_coin_rolls(self):
        entry = TREASURE_TYPE_TABLES["B"]
        assert len(entry.coin_rolls) == 3

    def test_gem_chance_range(self):
        for letter, entry in TREASURE_TYPE_TABLES.items():
            assert 0 <= entry.gem_chance_pct <= 100, f"Type {letter} bad gem chance"

    def test_art_chance_range(self):
        for letter, entry in TREASURE_TYPE_TABLES.items():
            assert 0 <= entry.art_chance_pct <= 100, f"Type {letter} bad art chance"


# ---------------------------------------------------------------------------
# CR_TO_TREASURE_TYPE
# ---------------------------------------------------------------------------

class TestCrToTreasureType:
    def test_cr1_is_a(self):
        assert CR_TO_TREASURE_TYPE["1"] == "A"

    def test_cr5_is_e(self):
        assert CR_TO_TREASURE_TYPE["5"] == "E"

    def test_cr21plus_is_n(self):
        assert CR_TO_TREASURE_TYPE["21+"] == "N"


# ---------------------------------------------------------------------------
# roll_gem_value
# ---------------------------------------------------------------------------

class TestRollGemValue:
    def _sample_gem(self) -> GemEntry:
        return GemEntry("Test Gem", GemGrade.SEMIPRECIOUS, 50, (20, 80))

    def test_normal_range(self):
        rng = random.Random(999)
        gem = self._sample_gem()
        # Override to always give d% = 50 (normal range)
        values = []
        for seed in range(100, 200):
            r = random.Random(seed)
            # patch out exceptional results by trying many seeds
            v = roll_gem_value(gem, r)
            if 20 <= v <= 80:
                values.append(v)
        assert len(values) > 0

    def test_exceptional_low_multiplier(self):
        """d% 1-10 → value × 10"""
        gem = self._sample_gem()

        class FakeRNG:
            _calls = 0
            def randint(self, a, b):
                self._calls += 1
                if self._calls == 1:
                    return 50  # base roll
                return 5  # d% = 5 → exceptional low

        result = roll_gem_value(gem, FakeRNG())  # type: ignore
        assert result == 500  # 50 × 10

    def test_exceptional_high_multiplier(self):
        """d% 91-100 → value × 100"""
        gem = self._sample_gem()

        class FakeRNG:
            _calls = 0
            def randint(self, a, b):
                self._calls += 1
                if self._calls == 1:
                    return 30  # base roll
                return 95  # d% = 95 → exceptional high

        result = roll_gem_value(gem, FakeRNG())  # type: ignore
        assert result == 3000  # 30 × 100

    def test_boundary_d_pct_10(self):
        gem = self._sample_gem()

        class FakeRNG:
            _calls = 0
            def randint(self, a, b):
                self._calls += 1
                if self._calls == 1:
                    return 40
                return 10  # boundary: still exceptional low

        result = roll_gem_value(gem, FakeRNG())  # type: ignore
        assert result == 400

    def test_boundary_d_pct_11(self):
        gem = self._sample_gem()

        class FakeRNG:
            _calls = 0
            def randint(self, a, b):
                self._calls += 1
                if self._calls == 1:
                    return 40
                return 11  # normal range

        result = roll_gem_value(gem, FakeRNG())  # type: ignore
        assert result == 40


# ---------------------------------------------------------------------------
# roll_art_object
# ---------------------------------------------------------------------------

class TestRollArtObject:
    def test_returns_art_object_entry(self):
        rng = random.Random(1)
        result = roll_art_object(rng)
        assert isinstance(result, ArtObjectEntry)

    def test_result_in_table(self):
        rng = random.Random(42)
        for _ in range(20):
            result = roll_art_object(rng)
            assert result in ART_OBJECT_TABLE


# ---------------------------------------------------------------------------
# generate_treasure_hoard
# ---------------------------------------------------------------------------

class TestGenerateTreasureHoard:
    def test_returns_treasure_hoard(self):
        rng = random.Random(0)
        hoard = generate_treasure_hoard(cr=1.0, rng=rng)
        assert isinstance(hoard, TreasureHoard)

    def test_coins_are_positive(self):
        rng = random.Random(42)
        for cr in [1, 5, 10, 20]:
            hoard = generate_treasure_hoard(cr=float(cr), rng=rng)
            for v in hoard.coins.values():
                assert v > 0

    def test_gems_are_gem_entries(self):
        rng = random.Random(7)
        hoard = generate_treasure_hoard(cr=5.0, rng=rng)
        for gem in hoard.gems:
            assert isinstance(gem, GemEntry)

    def test_art_objects_are_art_entries(self):
        rng = random.Random(7)
        hoard = generate_treasure_hoard(cr=5.0, rng=rng)
        for art in hoard.art_objects:
            assert isinstance(art, ArtObjectEntry)

    def test_magic_item_count_non_negative(self):
        rng = random.Random(3)
        for cr in [1, 5, 10, 20]:
            hoard = generate_treasure_hoard(cr=float(cr), rng=rng)
            assert hoard.magic_item_count >= 0

    def test_total_value_non_negative(self):
        rng = random.Random(99)
        for cr in [1, 5, 10, 20]:
            hoard = generate_treasure_hoard(cr=float(cr), rng=rng)
            assert hoard.total_value_gp >= 0.0

    def test_cr21_uses_type_n(self):
        # Type N has no coins, just magic items; run many times to get at least one magic item
        results = []
        for seed in range(50):
            rng = random.Random(seed)
            hoard = generate_treasure_hoard(cr=25.0, rng=rng)
            results.append(hoard)
        magic_counts = [h.magic_item_count for h in results]
        # Type N has 40% magic item chance; over 50 trials we expect some
        assert any(c > 0 for c in magic_counts)

    def test_no_rng_arg_works(self):
        hoard = generate_treasure_hoard(cr=3.0)
        assert isinstance(hoard, TreasureHoard)

    def test_hoard_total_includes_gems(self):
        class AlwaysRollRNG:
            """Always returns minimum/first value to give deterministic results."""
            def randint(self, a, b):
                return a
            def choice(self, seq):
                return seq[0]

        rng = AlwaysRollRNG()  # type: ignore
        # CR 1 → Type A: cp 25% always (returns 1, 1<=25), sp 30%, gp 35%, pp 25%
        # Gems: 20% → 1<=20 → yes, roll "2d6" → 2
        # Two gems selected → choice always returns GEM_TABLE[0]
        # For total_value, gems contribute base_value_gp
        hoard = generate_treasure_hoard(cr=1.0, rng=rng)
        gem_value = sum(g.base_value_gp for g in hoard.gems)
        art_value = sum(a.value_gp for a in hoard.art_objects)
        coin_value = sum(
            amt * {"cp": 0.01, "sp": 0.1, "gp": 1.0, "pp": 10.0}.get(c, 1.0)
            for c, amt in hoard.coins.items()
        )
        assert abs(hoard.total_value_gp - (gem_value + art_value + coin_value)) < 0.01
