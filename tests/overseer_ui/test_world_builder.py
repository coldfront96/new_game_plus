"""
tests/overseer_ui/test_world_builder.py
-----------------------------------------
Unit tests for PH6-005 · PH6-006 · PH6-007 — WorldBuilderState and
WorldBuilderScreen (non-UI logic only — no Textual app pilot needed).
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.overseer_ui.world_builder import (
    WorldBuilderState,
    WorldBuilderScreen,
    compile_campaign_to_file,
    _in_grid,
    _event_to_grid,
    _GRID_COLS,
    _GRID_ROWS,
)


# ---------------------------------------------------------------------------
# PH6-005 · WorldBuilderState
# ---------------------------------------------------------------------------

class TestWorldBuilderState:
    def test_default_grid_empty(self):
        s = WorldBuilderState()
        assert s.grid == {}

    def test_default_entity_anchors_empty(self):
        s = WorldBuilderState()
        assert s.entity_anchors == {}

    def test_paint_cell(self):
        s = WorldBuilderState()
        s.grid[(0, 0)] = "Temperate_Forest"
        assert s.grid[(0, 0)] == "Temperate_Forest"

    def test_anchor_entity(self):
        s = WorldBuilderState()
        s.entity_anchors.setdefault((5, 5), []).append("wolf")
        assert "wolf" in s.entity_anchors[(5, 5)]

    def test_multiple_anchors_at_same_cell(self):
        s = WorldBuilderState()
        s.entity_anchors.setdefault((1, 1), []).append("wolf")
        s.entity_anchors.setdefault((1, 1), []).append("goblin")
        assert len(s.entity_anchors[(1, 1)]) == 2


# ---------------------------------------------------------------------------
# PH6-005 · set_active_biome
# ---------------------------------------------------------------------------

class TestSetActiveBiome:
    def _screen(self) -> WorldBuilderScreen:
        return WorldBuilderScreen.__new__(WorldBuilderScreen)

    def setup_method(self):
        from src.overseer_ui.world_builder import WorldBuilderScreen
        from src.world_sim.biome import Biome
        screen = WorldBuilderScreen.__new__(WorldBuilderScreen)
        screen._active_biome = Biome.Temperate_Forest.name
        screen._state = WorldBuilderState()
        self._screen_obj = screen

    def test_valid_biome_sets_active(self):
        self._screen_obj.set_active_biome("Cold_Mountain")
        assert self._screen_obj._active_biome == "Cold_Mountain"

    def test_invalid_biome_raises_value_error(self):
        with pytest.raises(ValueError):
            self._screen_obj.set_active_biome("NotABiome")

    def test_any_biome_is_valid(self):
        self._screen_obj.set_active_biome("Any")
        assert self._screen_obj._active_biome == "Any"


# ---------------------------------------------------------------------------
# _in_grid helper
# ---------------------------------------------------------------------------

class TestInGrid:
    def test_origin_in_grid(self):
        assert _in_grid(0, 0) is True

    def test_max_valid(self):
        assert _in_grid(_GRID_COLS - 1, _GRID_ROWS - 1) is True

    def test_col_out_of_bounds(self):
        assert _in_grid(_GRID_COLS, 0) is False

    def test_row_out_of_bounds(self):
        assert _in_grid(0, _GRID_ROWS) is False

    def test_negative_x(self):
        assert _in_grid(-1, 0) is False

    def test_negative_y(self):
        assert _in_grid(0, -1) is False


# ---------------------------------------------------------------------------
# Grid render
# ---------------------------------------------------------------------------

class TestGridRender:
    def _make_screen(self):
        screen = WorldBuilderScreen.__new__(WorldBuilderScreen)
        screen._state = WorldBuilderState()
        screen._active_biome = "Temperate_Forest"
        screen._active_monster_id = None
        screen._mouse_held = False
        return screen

    def test_render_empty_grid_is_all_dots(self):
        screen = self._make_screen()
        rendered = screen._render_grid()
        lines = rendered.split("\n")
        assert len(lines) == _GRID_ROWS
        assert all(ch == "." for line in lines for ch in line)

    def test_render_painted_cell_shows_biome_glyph(self):
        screen = self._make_screen()
        screen._state.grid[(0, 0)] = "Temperate_Forest"
        rendered = screen._render_grid()
        first_line = rendered.split("\n")[0]
        # T for Temperate_Forest
        assert first_line[0] == "T"

    def test_render_anchored_cell_shows_at_sign(self):
        screen = self._make_screen()
        screen._state.entity_anchors[(0, 0)] = ["wolf"]
        rendered = screen._render_grid()
        first_line = rendered.split("\n")[0]
        assert first_line[0] == "@"

    def test_render_anchor_overrides_biome_glyph(self):
        screen = self._make_screen()
        screen._state.grid[(2, 3)] = "Cold_Forest"
        screen._state.entity_anchors[(2, 3)] = ["goblin"]
        rendered = screen._render_grid()
        line = rendered.split("\n")[3]
        assert line[2] == "@"


# ---------------------------------------------------------------------------
# Compile Campaign serialisation (PH6-007)
# ---------------------------------------------------------------------------

class TestCompileCampaign:
    def _make_state(self):
        state = WorldBuilderState()
        state.grid[(0, 0)] = "Temperate_Forest"
        state.grid[(1, 0)] = "Cold_Mountain"
        state.entity_anchors[(0, 0)] = ["wolf"]
        return state

    def test_compile_writes_valid_json(self, tmp_path):
        state = self._make_state()
        filename = compile_campaign_to_file(state, output_dir=tmp_path)

        data = json.loads(Path(filename).read_text())
        assert data["source"] == "world_builder"
        assert data["seed"] is None
        assert isinstance(data["chunks"], list)
        assert isinstance(data["faction_records"], list)

    def test_compile_chunks_include_monster_ids(self, tmp_path):
        state = self._make_state()
        filename = compile_campaign_to_file(state, output_dir=tmp_path)

        data = json.loads(Path(filename).read_text())
        cell_00 = next(c for c in data["chunks"] if c["x"] == 0 and c["y"] == 0)
        assert "wolf" in cell_00["monster_ids"]

    def test_compile_campaign_creates_dir_if_missing(self, tmp_path):
        nested = tmp_path / "missing" / "subdir"
        state = self._make_state()
        compile_campaign_to_file(state, output_dir=nested)
        assert nested.exists()

    def test_compile_returns_filename_string(self, tmp_path):
        state = self._make_state()
        filename = compile_campaign_to_file(state, output_dir=tmp_path)
        assert isinstance(filename, str)
        assert Path(filename).exists()

    def test_empty_state_produces_empty_chunks(self, tmp_path):
        state = WorldBuilderState()
        filename = compile_campaign_to_file(state, output_dir=tmp_path)
        data = json.loads(Path(filename).read_text())
        assert data["chunks"] == []
