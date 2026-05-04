"""
tests/game/test_character_forge_racial.py
------------------------------------------
Tests for the visual racial modifier system added to CharacterForgeApp
(Phase 'Ashen Crossroads' transition, Feature: Visual Racial Modifiers).

Covers:
  CF-001  _ABILITY_KEY maps every display label to the correct JSON key
  CF-002  _RACE_MAP contains all races from core.json
  CF-003  Racial modifiers are extracted correctly from the race data
  CF-004  Total score (base + point-buy + racial) is computed correctly
  CF-005  _build_character_dict uses racial mods from _ABILITY_KEY
  CF-006  run_first_awakening returns AwakeningState (state persistence)
  CF-007  run_first_awakening returns None when player.json is missing
"""

from __future__ import annotations

import io
import json
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pytest

from src.game.character_forge import (
    CharacterForgeApp,
    _ABILITY_KEY,
    _ABILITY_LABELS,
    _RACE_MAP,
    _STAT_BASE,
    _mod,
)


# ---------------------------------------------------------------------------
# CF-001  _ABILITY_KEY completeness
# ---------------------------------------------------------------------------

class TestAbilityKeyMapping:
    def test_all_labels_present(self):
        for label in _ABILITY_LABELS:
            assert label in _ABILITY_KEY, f"{label} missing from _ABILITY_KEY"

    def test_values_are_lowercase_strings(self):
        for label, key in _ABILITY_KEY.items():
            assert isinstance(key, str)
            assert key == key.lower(), f"Key for {label} must be lowercase: {key!r}"

    def test_correct_mappings(self):
        expected = {
            "Strength":     "strength",
            "Dexterity":    "dexterity",
            "Constitution": "constitution",
            "Intelligence": "intelligence",
            "Wisdom":       "wisdom",
            "Charisma":     "charisma",
        }
        assert _ABILITY_KEY == expected


# ---------------------------------------------------------------------------
# CF-002  Race map population
# ---------------------------------------------------------------------------

class TestRaceMap:
    def test_all_standard_races_present(self):
        for race in ("Dwarf", "Elf", "Gnome", "Half-Elf", "Half-Orc", "Halfling", "Human", "Orc"):
            assert race in _RACE_MAP, f"{race} missing from _RACE_MAP"

    def test_each_race_has_stat_modifiers_key(self):
        for name, data in _RACE_MAP.items():
            assert "stat_modifiers" in data, f"{name} missing 'stat_modifiers'"


# ---------------------------------------------------------------------------
# CF-003  Racial modifier extraction
# ---------------------------------------------------------------------------

class TestRacialModifierExtraction:
    def test_dwarf_mods(self):
        mods = _RACE_MAP["Dwarf"]["stat_modifiers"]
        assert mods.get("constitution") == 2
        assert mods.get("charisma") == -2

    def test_elf_mods(self):
        mods = _RACE_MAP["Elf"]["stat_modifiers"]
        assert mods.get("dexterity") == 2
        assert mods.get("constitution") == -2

    def test_human_has_no_mods(self):
        assert _RACE_MAP["Human"]["stat_modifiers"] == {}

    def test_half_elf_has_no_mods(self):
        assert _RACE_MAP["Half-Elf"]["stat_modifiers"] == {}

    def test_orc_mods(self):
        mods = _RACE_MAP["Orc"]["stat_modifiers"]
        assert mods.get("strength") == 4
        assert mods.get("intelligence") == -2
        assert mods.get("wisdom") == -2
        assert mods.get("charisma") == -2


# ---------------------------------------------------------------------------
# CF-004  Total score calculation (base + point-buy + racial)
# ---------------------------------------------------------------------------

class TestTotalScoreCalculation:
    """Verify that total = base10 + point_buy_adjustment + racial_mod."""

    def _total(self, pb_score: int, racial: int) -> int:
        return pb_score + racial

    def test_dwarf_constitution_total(self):
        # Starting score 10, no point-buy, Dwarf +2 CON
        pb = _STAT_BASE  # 10
        racial = _RACE_MAP["Dwarf"]["stat_modifiers"].get("constitution", 0)
        total = self._total(pb, racial)
        assert total == 12
        assert _mod(total) == 1  # (12-10)//2 = 1

    def test_elf_constitution_penalty(self):
        pb = _STAT_BASE  # 10
        racial = _RACE_MAP["Elf"]["stat_modifiers"].get("constitution", 0)
        total = self._total(pb, racial)
        assert total == 8
        assert _mod(total) == -1  # (8-10)//2 = -1

    def test_human_no_change(self):
        pb = 14  # after spending 4 pool points
        racial = _RACE_MAP["Human"]["stat_modifiers"].get("strength", 0)
        assert self._total(pb, racial) == 14

    def test_point_buy_plus_racial(self):
        pb = 12  # base 10 + 2 spent
        racial = _RACE_MAP["Dwarf"]["stat_modifiers"].get("constitution", 0)  # +2
        total = self._total(pb, racial)
        assert total == 14
        assert _mod(total) == 2  # (14-10)//2 = 2


# ---------------------------------------------------------------------------
# CF-005  _build_character_dict applies racial mods via _ABILITY_KEY
# ---------------------------------------------------------------------------

class TestBuildCharacterDict:
    """Integration test: _build_character_dict uses _ABILITY_KEY correctly."""

    def _make_app(self) -> CharacterForgeApp:
        return CharacterForgeApp.__new__(CharacterForgeApp)

    def _scores(self, override: Dict[str, int] | None = None) -> Dict[str, int]:
        base = {ab: _STAT_BASE for ab in _ABILITY_LABELS}
        if override:
            base.update(override)
        return base

    def test_dwarf_constitution_boosted(self):
        app = self._make_app()
        app._difficulty = "Medium"
        app._permadeath = False
        app._pool_size = 25
        result = app._build_character_dict(
            name="Thorin",
            ancestry="Dwarf",
            vocation="Fighter",
            keepsake="None",
            scores=self._scores(),
            age=40,
            build="Broad",
            eye_aspect="Steel-grey",
            marks="Battle scar",
        )
        assert result["ability_scores"]["Constitution"] == 12  # 10 + 2
        assert result["ability_scores"]["Charisma"] == 8       # 10 - 2
        assert result["racial_modifiers"] == {"constitution": 2, "charisma": -2}

    def test_elf_dex_and_con(self):
        app = self._make_app()
        app._difficulty = "Medium"
        app._permadeath = False
        app._pool_size = 25
        result = app._build_character_dict(
            name="Aelindra",
            ancestry="Elf",
            vocation="Wizard",
            keepsake="None",
            scores=self._scores(),
            age=120,
            build="Slight",
            eye_aspect="Silver",
            marks="None noted",
        )
        assert result["ability_scores"]["Dexterity"] == 12   # 10 + 2
        assert result["ability_scores"]["Constitution"] == 8  # 10 - 2

    def test_human_no_change(self):
        app = self._make_app()
        app._difficulty = "Medium"
        app._permadeath = False
        app._pool_size = 25
        result = app._build_character_dict(
            name="Marcus",
            ancestry="Human",
            vocation="Fighter",
            keepsake="None",
            scores=self._scores(),
            age=25,
            build="Athletic",
            eye_aspect="Brown",
            marks="None noted",
        )
        for ab in _ABILITY_LABELS:
            assert result["ability_scores"][ab] == _STAT_BASE

    def test_base_scores_preserved_in_audit_trail(self):
        app = self._make_app()
        app._difficulty = "Medium"
        app._permadeath = False
        app._pool_size = 25
        scores = self._scores({"Strength": 14})
        result = app._build_character_dict(
            name="Groak",
            ancestry="Half-Orc",
            vocation="Barbarian",
            keepsake="None",
            scores=scores,
            age=22,
            build="Towering",
            eye_aspect="Red",
            marks="War paint",
        )
        # audit trail preserves pre-racial values
        assert result["base_ability_scores"]["Strength"] == 14
        # final score includes Half-Orc +2 STR
        assert result["ability_scores"]["Strength"] == 16


# ---------------------------------------------------------------------------
# CF-006/007  AwakeningState return from run_first_awakening
# ---------------------------------------------------------------------------

class TestRunFirstAwakening:
    """run_first_awakening should return Optional[AwakeningState]."""

    def _minimal_player(self, tmp_path: Path) -> Path:
        player = {
            "name": "Ash",
            "race": "Human",
            "char_class": "Fighter",
            "physical_description": {
                "eye_aspect": "grey",
                "build": "lean",
                "distinguishing_marks": "none",
            },
        }
        p = tmp_path / "player.json"
        p.write_text(json.dumps(player), encoding="utf-8")
        return p

    def test_returns_none_when_no_player_file(self, tmp_path):
        from src.game.awakening import run_first_awakening

        missing = tmp_path / "nonexistent.json"
        result = run_first_awakening(player_json_path=missing, stream=io.StringIO())
        assert result is None

    def test_returns_awakening_state_on_success(self, tmp_path):
        from src.game.awakening import run_first_awakening, AwakeningState

        path = self._minimal_player(tmp_path)
        result = run_first_awakening(
            player_json_path=path,
            stream=io.StringIO(),
            seed=42,
        )
        assert result is not None
        assert isinstance(result, AwakeningState)
        assert result.player_data["name"] == "Ash"
        assert result.absolute_tick == 0

    def test_awakening_state_holds_world_state(self, tmp_path):
        from src.game.awakening import run_first_awakening

        path = self._minimal_player(tmp_path)
        result = run_first_awakening(
            player_json_path=path,
            stream=io.StringIO(),
            seed=0,
        )
        assert result is not None
        assert result.world_state is not None

    def test_awakening_state_has_origin_room(self, tmp_path):
        from src.game.awakening import run_first_awakening, SafeZoneRoom

        path = self._minimal_player(tmp_path)
        result = run_first_awakening(
            player_json_path=path,
            stream=io.StringIO(),
            seed=7,
        )
        assert result is not None
        assert isinstance(result.origin_room, SafeZoneRoom)
        assert result.origin_room.world_x == 0
        assert result.origin_room.world_y == 64
        assert result.origin_room.world_z == 0
