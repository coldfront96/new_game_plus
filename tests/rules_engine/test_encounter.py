"""Tests for src/rules_engine/encounter.py"""
from __future__ import annotations

import pytest

from src.rules_engine.encounter import (
    CR_TO_XP, xp_for_cr, xp_per_character, calculate_el, distribute_xp,
    _nearest_cr,
)


# ---------------------------------------------------------------------------
# CR_TO_XP table
# ---------------------------------------------------------------------------

class TestCrToXp:
    def test_has_cr1_through_cr20(self):
        for cr in range(1, 21):
            assert float(cr) in CR_TO_XP, f"Missing CR {cr}"

    def test_fractional_crs(self):
        assert 0.25 in CR_TO_XP
        assert 0.5 in CR_TO_XP
        assert 0.125 in CR_TO_XP

    def test_cr1_equals_300(self):
        assert CR_TO_XP[1] == 300

    def test_cr10_equals_9600(self):
        assert CR_TO_XP[10] == 9_600

    def test_cr20_equals_307200(self):
        assert CR_TO_XP[20] == 307_200

    def test_cr30_exists(self):
        assert 30 in CR_TO_XP

    def test_values_increase_monotonically(self):
        sorted_keys = sorted(CR_TO_XP.keys())
        for a, b in zip(sorted_keys, sorted_keys[1:]):
            assert CR_TO_XP[a] < CR_TO_XP[b], f"XP not increasing at CR {a}→{b}"


# ---------------------------------------------------------------------------
# xp_for_cr
# ---------------------------------------------------------------------------

class TestXpForCr:
    def test_exact_cr(self):
        assert xp_for_cr(1.0) == 300
        assert xp_for_cr(5.0) == 1_600
        assert xp_for_cr(10.0) == 9_600

    def test_fractional_cr_half(self):
        assert xp_for_cr(0.5) == 200

    def test_fractional_cr_quarter(self):
        assert xp_for_cr(0.25) == 100

    def test_nearest_lookup_for_unknown_cr(self):
        # CR 1.1 should map to CR 1 (nearest)
        result = xp_for_cr(1.1)
        assert result == CR_TO_XP[1]

    def test_cr_0_returns_something(self):
        result = xp_for_cr(0.0)
        assert result > 0


# ---------------------------------------------------------------------------
# xp_per_character
# ---------------------------------------------------------------------------

class TestXpPerCharacter:
    def test_equal_level_full_xp_divided_by_party(self):
        # APL == CR → multiplier 1.0
        xp = xp_per_character(cr=5.0, apl=5, party_size=4)
        expected = int(CR_TO_XP[5] / 4 * 1.0)
        assert xp == expected

    def test_party_above_encounter_trivial(self):
        # APL 10, CR 5 → diff = +5 → trivial → 0 XP
        xp = xp_per_character(cr=5.0, apl=10, party_size=4)
        assert xp == 0

    def test_party_slightly_above_less_xp(self):
        # APL > CR by 1 → 0.75×
        xp = xp_per_character(cr=5.0, apl=6, party_size=4)
        expected = int(CR_TO_XP[5] / 4 * 0.75)
        assert xp == expected

    def test_party_below_encounter_more_xp(self):
        # APL < CR by 1 → 1.5×
        xp = xp_per_character(cr=5.0, apl=4, party_size=4)
        expected = int(CR_TO_XP[5] / 4 * 1.5)
        assert xp == expected

    def test_dangerous_encounter_3x(self):
        # APL < CR by 3+ → 3.0×
        xp = xp_per_character(cr=10.0, apl=5, party_size=4)
        expected = int(CR_TO_XP[10] / 4 * 3.0)
        assert xp == expected

    def test_party_size_scales_xp(self):
        xp_4 = xp_per_character(cr=5.0, apl=5, party_size=4)
        xp_8 = xp_per_character(cr=5.0, apl=5, party_size=8)
        assert xp_4 == xp_8 * 2  # larger party → less per char

    def test_never_negative(self):
        xp = xp_per_character(cr=1.0, apl=20, party_size=4)
        assert xp >= 0


# ---------------------------------------------------------------------------
# calculate_el
# ---------------------------------------------------------------------------

class TestCalculateEl:
    def test_single_monster_el_equals_cr(self):
        el = calculate_el([5.0])
        assert el == 5.0

    def test_two_same_cr_el_is_higher(self):
        # Two CR 3 → XP = 2 × 800 = 1600 = CR 5
        el = calculate_el([3.0, 3.0])
        assert el == 5.0

    def test_four_same_cr_el_is_much_higher(self):
        # Four CR 3 → 4 × 800 = 3200 = CR 7
        el = calculate_el([3.0, 3.0, 3.0, 3.0])
        assert el == 7.0

    def test_two_cr1_monsters(self):
        # 2 × 300 = 600 = CR 2
        el = calculate_el([1.0, 1.0])
        assert el == 2.0

    def test_four_cr1_monsters(self):
        # 4 × 300 = 1200 = CR 4
        el = calculate_el([1.0, 1.0, 1.0, 1.0])
        assert el == 4.0

    def test_empty_list_returns_zero(self):
        el = calculate_el([])
        assert el == 0.0

    def test_mixed_crs(self):
        # CR 5 (1600) + CR 3 (800) = 2400 = CR 6
        el = calculate_el([5.0, 3.0])
        assert el == 6.0

    def test_single_high_cr(self):
        el = calculate_el([20.0])
        assert el == 20.0


# ---------------------------------------------------------------------------
# distribute_xp
# ---------------------------------------------------------------------------

class TestDistributeXp:
    def test_even_party_equal_xp(self):
        party = [5, 5, 5, 5]
        result = distribute_xp(encounter_el=5.0, party_levels=party)
        assert len(result) == 4
        xp_values = list(result.values())
        assert all(v == xp_values[0] for v in xp_values)

    def test_returns_dict_with_correct_indices(self):
        party = [3, 5, 7]
        result = distribute_xp(encounter_el=5.0, party_levels=party)
        assert set(result.keys()) == {0, 1, 2}

    def test_high_level_character_less_xp(self):
        # party=[5,5,5,15] → APL=7, level 15 ≥ APL+3 → 0.5× for them
        party = [5, 5, 5, 15]
        result = distribute_xp(encounter_el=5.0, party_levels=party)
        assert result[3] < result[0]

    def test_low_level_character_more_xp(self):
        # party=[1,10,10,10] → APL=7, level 1 ≤ APL-4=3 → 1.5× for them
        party = [1, 10, 10, 10]
        result = distribute_xp(encounter_el=5.0, party_levels=party)
        assert result[0] > result[1]

    def test_empty_party_returns_empty(self):
        result = distribute_xp(encounter_el=5.0, party_levels=[])
        assert result == {}

    def test_all_xp_non_negative(self):
        party = [1, 5, 10, 20]
        result = distribute_xp(encounter_el=5.0, party_levels=party)
        assert all(v >= 0 for v in result.values())

    def test_single_character(self):
        party = [5]
        result = distribute_xp(encounter_el=5.0, party_levels=party)
        assert 0 in result
        assert result[0] == CR_TO_XP[5]
