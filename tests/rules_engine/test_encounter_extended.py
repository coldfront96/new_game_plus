"""
tests/rules_engine/test_encounter_extended.py
----------------------------------------------
Tests for T-045, T-052, T-056 (encounter_extended.py).
"""
from __future__ import annotations

import random
import pytest

from src.rules_engine.encounter_extended import (
    EncounterEntry,
    ENCOUNTER_TABLES,
    EncounterDifficulty,
    EncounterBlueprint,
    EncounterReport,
    build_encounter,
    run_encounter,
    _parse_dice_avg,
    _roll_encounter_table,
)
from src.rules_engine.environment import TerrainType


# ---------------------------------------------------------------------------
# EncounterEntry creation
# ---------------------------------------------------------------------------

class TestEncounterEntry:
    def test_basic_creation(self):
        e = EncounterEntry(1, 10, "Goblin", "2d4", 0.33)
        assert e.d100_low == 1
        assert e.d100_high == 10
        assert e.monster_name == "Goblin"
        assert e.number_appearing == "2d4"
        assert e.cr == 0.33

    def test_high_cr(self):
        e = EncounterEntry(93, 100, "Dragon", "1", 15.0)
        assert e.cr == 15.0

    def test_number_appearing_range(self):
        e = EncounterEntry(1, 10, "Wolf", "1d6+2", 1.0)
        assert "d" in e.number_appearing


# ---------------------------------------------------------------------------
# ENCOUNTER_TABLES structure
# ---------------------------------------------------------------------------

EXPECTED_TERRAINS = [
    "dungeon", "forest", "plains", "desert",
    "hills", "mountains", "marsh", "arctic",
]


class TestEncounterTables:
    def test_all_eight_terrain_keys_present(self):
        for terrain in EXPECTED_TERRAINS:
            assert terrain in ENCOUNTER_TABLES, f"Missing terrain: {terrain}"

    def test_each_table_has_11_entries(self):
        for terrain in EXPECTED_TERRAINS:
            assert len(ENCOUNTER_TABLES[terrain]) == 11, (
                f"{terrain} table has {len(ENCOUNTER_TABLES[terrain])} entries, expected 11"
            )

    def test_entries_are_encounter_entry_instances(self):
        for terrain in EXPECTED_TERRAINS:
            for entry in ENCOUNTER_TABLES[terrain]:
                assert isinstance(entry, EncounterEntry)

    def test_d100_ranges_are_valid(self):
        for terrain in EXPECTED_TERRAINS:
            for entry in ENCOUNTER_TABLES[terrain]:
                assert 1 <= entry.d100_low <= 100
                assert 1 <= entry.d100_high <= 100
                assert entry.d100_low <= entry.d100_high

    def test_last_entry_ends_at_100(self):
        for terrain in EXPECTED_TERRAINS:
            assert ENCOUNTER_TABLES[terrain][-1].d100_high == 100

    def test_first_entry_starts_at_1(self):
        for terrain in EXPECTED_TERRAINS:
            assert ENCOUNTER_TABLES[terrain][0].d100_low == 1

    def test_all_entries_have_positive_cr(self):
        for terrain in EXPECTED_TERRAINS:
            for entry in ENCOUNTER_TABLES[terrain]:
                assert entry.cr > 0

    def test_dungeon_contains_dire_rat(self):
        names = [e.monster_name for e in ENCOUNTER_TABLES["dungeon"]]
        assert "Dire Rat" in names

    def test_forest_contains_green_dragon(self):
        names = [e.monster_name for e in ENCOUNTER_TABLES["forest"]]
        assert any("Dragon" in n for n in names)

    def test_arctic_contains_frost_giant(self):
        names = [e.monster_name for e in ENCOUNTER_TABLES["arctic"]]
        assert "Frost Giant" in names


# ---------------------------------------------------------------------------
# _parse_dice_avg
# ---------------------------------------------------------------------------

class TestParseDiceAvg:
    def test_simple_die(self):
        assert _parse_dice_avg("1d4") == 2

    def test_multiple_dice(self):
        assert _parse_dice_avg("2d6") == 7

    def test_plain_integer(self):
        assert _parse_dice_avg("1") == 1

    def test_plain_integer_large(self):
        assert _parse_dice_avg("3") == 3

    def test_with_modifier_ignored(self):
        # "1d6+1" — modifier stripped, avg of 1d6 = 3
        result = _parse_dice_avg("1d6+1")
        assert result >= 1

    def test_minimum_one(self):
        assert _parse_dice_avg("0") >= 1

    def test_d4_two_dice(self):
        assert _parse_dice_avg("2d4") == 5


# ---------------------------------------------------------------------------
# _roll_encounter_table
# ---------------------------------------------------------------------------

class TestRollEncounterTable:
    def test_returns_entry_for_valid_terrain(self):
        rng = random.Random(42)
        entry = _roll_encounter_table("dungeon", rng)
        assert entry is not None
        assert isinstance(entry, EncounterEntry)

    def test_returns_none_for_unknown_terrain(self):
        rng = random.Random(42)
        entry = _roll_encounter_table("atlantis", rng)
        assert entry is None

    def test_all_terrains_return_entry(self):
        rng = random.Random(0)
        for terrain in EXPECTED_TERRAINS:
            entry = _roll_encounter_table(terrain, rng)
            assert entry is not None


# ---------------------------------------------------------------------------
# EncounterDifficulty enum
# ---------------------------------------------------------------------------

class TestEncounterDifficulty:
    def test_all_five_values(self):
        assert EncounterDifficulty.EASY.value == "easy"
        assert EncounterDifficulty.AVERAGE.value == "average"
        assert EncounterDifficulty.CHALLENGING.value == "challenging"
        assert EncounterDifficulty.HARD.value == "hard"
        assert EncounterDifficulty.OVERWHELMING.value == "overwhelming"

    def test_enum_count(self):
        assert len(EncounterDifficulty) == 5


# ---------------------------------------------------------------------------
# build_encounter
# ---------------------------------------------------------------------------

class TestBuildEncounter:
    def _rng(self, seed=1):
        return random.Random(seed)

    def test_returns_blueprint(self):
        bp = build_encounter(5, EncounterDifficulty.AVERAGE, "dungeon", self._rng())
        assert isinstance(bp, EncounterBlueprint)

    def test_blueprint_has_target_el(self):
        bp = build_encounter(5, EncounterDifficulty.AVERAGE, "dungeon", self._rng())
        assert bp.target_el == 5.0

    def test_easy_target_el(self):
        bp = build_encounter(5, EncounterDifficulty.EASY, "dungeon", self._rng())
        assert bp.target_el == 3.0

    def test_hard_target_el(self):
        bp = build_encounter(5, EncounterDifficulty.HARD, "dungeon", self._rng())
        assert bp.target_el == 7.0

    def test_overwhelming_target_el(self):
        bp = build_encounter(5, EncounterDifficulty.OVERWHELMING, "dungeon", self._rng())
        assert bp.target_el == 9.0

    def test_actual_el_is_positive(self):
        bp = build_encounter(5, EncounterDifficulty.AVERAGE, "forest", self._rng())
        assert bp.actual_el > 0

    def test_monsters_list_not_empty(self):
        bp = build_encounter(5, EncounterDifficulty.AVERAGE, "plains", self._rng())
        assert len(bp.monsters) > 0

    def test_monster_tuple_structure(self):
        bp = build_encounter(5, EncounterDifficulty.AVERAGE, "dungeon", self._rng())
        name, count, cr = bp.monsters[0]
        assert isinstance(name, str)
        assert isinstance(count, int)
        assert count >= 1
        assert isinstance(cr, float)

    def test_difficulty_stored_in_blueprint(self):
        bp = build_encounter(5, EncounterDifficulty.HARD, "hills", self._rng())
        assert bp.difficulty == EncounterDifficulty.HARD

    def test_terrain_stored_in_blueprint(self):
        bp = build_encounter(5, EncounterDifficulty.AVERAGE, "arctic", self._rng())
        assert bp.terrain == "arctic"

    def test_terrain_type_enum_accepted(self):
        bp = build_encounter(5, EncounterDifficulty.AVERAGE, TerrainType.FOREST, self._rng())
        assert bp.terrain == "forest"

    def test_unknown_terrain_falls_back_to_dungeon(self):
        bp = build_encounter(5, EncounterDifficulty.AVERAGE, "atlantis", self._rng())
        assert bp.terrain == "dungeon"

    def test_apl_1_minimum_el(self):
        bp = build_encounter(1, EncounterDifficulty.EASY, "dungeon", self._rng())
        assert bp.target_el >= 0.5

    def test_challenging_offset(self):
        bp = build_encounter(5, EncounterDifficulty.CHALLENGING, "marsh", self._rng())
        assert bp.target_el == 6.0

    def test_all_terrains_work(self):
        rng = self._rng(99)
        for terrain in EXPECTED_TERRAINS:
            bp = build_encounter(5, EncounterDifficulty.AVERAGE, terrain, rng)
            assert isinstance(bp, EncounterBlueprint)

    def test_easy_target_el_lower_than_overwhelming(self):
        """Easy difficulty produces a lower target EL than overwhelming."""
        rng = random.Random(42)
        easy_bp = build_encounter(8, EncounterDifficulty.EASY, "dungeon", rng)
        rng = random.Random(42)
        over_bp = build_encounter(8, EncounterDifficulty.OVERWHELMING, "dungeon", rng)
        assert easy_bp.target_el < over_bp.target_el


# ---------------------------------------------------------------------------
# run_encounter / EncounterReport
# ---------------------------------------------------------------------------

class TestRunEncounter:
    def _rng(self, seed=7):
        return random.Random(seed)

    def test_returns_encounter_report(self):
        report = run_encounter([5, 5, 5, 5], 5, "dungeon", EncounterDifficulty.AVERAGE, self._rng())
        assert isinstance(report, EncounterReport)

    def test_report_has_blueprint(self):
        report = run_encounter([5, 5, 5, 5], 5, "dungeon", EncounterDifficulty.AVERAGE, self._rng())
        assert isinstance(report.blueprint, EncounterBlueprint)

    def test_xp_per_character_is_dict(self):
        report = run_encounter([5, 5, 5, 5], 5, "dungeon", EncounterDifficulty.AVERAGE, self._rng())
        assert isinstance(report.xp_per_character, dict)

    def test_xp_dict_has_4_entries_for_4_party(self):
        report = run_encounter([5, 5, 5, 5], 5, "dungeon", EncounterDifficulty.AVERAGE, self._rng())
        assert len(report.xp_per_character) == 4

    def test_xp_dict_has_3_entries_for_3_party(self):
        report = run_encounter([4, 5, 6], 5, "forest", EncounterDifficulty.HARD, self._rng())
        assert len(report.xp_per_character) == 3

    def test_xp_dict_keys_are_character_strings(self):
        report = run_encounter([5, 5], 5, "plains", EncounterDifficulty.EASY, self._rng())
        assert "character_1" in report.xp_per_character
        assert "character_2" in report.xp_per_character

    def test_xp_values_are_non_negative(self):
        report = run_encounter([5, 5, 5, 5], 5, "dungeon", EncounterDifficulty.AVERAGE, self._rng())
        for xp in report.xp_per_character.values():
            assert xp >= 0

    def test_treasure_type_is_string(self):
        report = run_encounter([5, 5, 5, 5], 5, "dungeon", EncounterDifficulty.AVERAGE, self._rng())
        assert isinstance(report.treasure_type, str)
        assert len(report.treasure_type) > 0

    def test_weather_description_is_string(self):
        report = run_encounter([5, 5, 5, 5], 5, "dungeon", EncounterDifficulty.AVERAGE, self._rng())
        assert isinstance(report.weather_description, str)

    def test_terrain_type_enum_accepted(self):
        report = run_encounter([5, 5, 5, 5], 5, TerrainType.ARCTIC, EncounterDifficulty.HARD, self._rng())
        assert isinstance(report, EncounterReport)

    def test_single_character_party(self):
        report = run_encounter([10], 10, "mountains", EncounterDifficulty.AVERAGE, self._rng())
        assert len(report.xp_per_character) == 1

    def test_six_character_party(self):
        report = run_encounter([5] * 6, 5, "marsh", EncounterDifficulty.CHALLENGING, self._rng())
        assert len(report.xp_per_character) == 6

    def test_blueprint_terrain_matches_input(self):
        report = run_encounter([5, 5, 5, 5], 5, "hills", EncounterDifficulty.AVERAGE, self._rng())
        assert report.blueprint.terrain == "hills"
