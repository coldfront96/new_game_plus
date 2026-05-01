"""Tests for PH2-010 · PH2-011 · PH2-012 · PH2-014 — player_controller module."""
from __future__ import annotations

import math
import pytest

from src.game.player_controller import (
    PlayerAction,
    PlayerController,
    calculate_visible_voxels,
    calculate_visible_voxels_at,
    dispatch_player_input,
    update_loaded_chunks,
    _chunk_id_is_numeric,
)
from src.rules_engine.character_35e import Character35e


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entity(name: str = "Hero", position: list[int] | None = None) -> Character35e:
    entity = Character35e(name=name, char_class="Fighter", level=1)
    if position is not None:
        entity.metadata["position"] = list(position)
    else:
        entity.metadata["position"] = [0, 64, 0]
    return entity


def _make_controller(
    chunk_id: str = "0_0",
    vision_radius: int = 4,
    entity_id: str = "hero_1",
) -> PlayerController:
    return PlayerController(
        player_id="player_1",
        entity_id=entity_id,
        chunk_id=chunk_id,
        vision_radius=vision_radius,
    )


# ---------------------------------------------------------------------------
# PH2-010 · PlayerController / PlayerAction
# ---------------------------------------------------------------------------

class TestPlayerController:
    def test_creation(self):
        ctrl = PlayerController(
            player_id="p1",
            entity_id="e1",
            chunk_id="0_0",
            vision_radius=8,
        )
        assert ctrl.player_id == "p1"
        assert ctrl.entity_id == "e1"
        assert ctrl.chunk_id == "0_0"
        assert ctrl.vision_radius == 8
        assert ctrl.fog_revealed == set()

    def test_slots_no_dict(self):
        ctrl = PlayerController("p", "e", "0_0")
        assert not hasattr(ctrl, "__dict__")

    def test_default_vision_radius(self):
        ctrl = PlayerController("p", "e", "0_0")
        assert ctrl.vision_radius == 8

    def test_fog_revealed_is_set(self):
        ctrl = PlayerController("p", "e", "0_0")
        assert isinstance(ctrl.fog_revealed, set)

    def test_player_action_values(self):
        actions = {a.value for a in PlayerAction}
        assert "move_north" in actions
        assert "move_south" in actions
        assert "move_east" in actions
        assert "move_west" in actions
        assert "move_up" in actions
        assert "move_down" in actions
        assert "wait" in actions
        assert "interact" in actions


# ---------------------------------------------------------------------------
# PH2-011 · dispatch_player_input
# ---------------------------------------------------------------------------

class TestDispatchPlayerInput:
    def _registry(self, entity: Character35e) -> dict[str, Character35e]:
        return {entity.char_id: entity}

    def test_move_north_decreases_z(self):
        entity = _make_entity(position=[0, 64, 5])
        ctrl = _make_controller(entity_id=entity.char_id)
        dispatch_player_input(ctrl, PlayerAction.MoveNorth, {entity.char_id: entity})
        assert entity.metadata["position"][2] == 4

    def test_move_south_increases_z(self):
        entity = _make_entity(position=[0, 64, 0])
        ctrl = _make_controller(entity_id=entity.char_id)
        dispatch_player_input(ctrl, PlayerAction.MoveSouth, {entity.char_id: entity})
        assert entity.metadata["position"][2] == 1

    def test_move_east_increases_x(self):
        entity = _make_entity(position=[0, 64, 0])
        ctrl = _make_controller(entity_id=entity.char_id)
        dispatch_player_input(ctrl, PlayerAction.MoveEast, {entity.char_id: entity})
        assert entity.metadata["position"][0] == 1

    def test_move_west_decreases_x(self):
        entity = _make_entity(position=[3, 64, 0])
        ctrl = _make_controller(entity_id=entity.char_id)
        dispatch_player_input(ctrl, PlayerAction.MoveWest, {entity.char_id: entity})
        assert entity.metadata["position"][0] == 2

    def test_move_up_increases_y(self):
        entity = _make_entity(position=[0, 64, 0])
        ctrl = _make_controller(entity_id=entity.char_id)
        dispatch_player_input(ctrl, PlayerAction.MoveUp, {entity.char_id: entity})
        assert entity.metadata["position"][1] == 65

    def test_move_down_decreases_y(self):
        entity = _make_entity(position=[0, 64, 0])
        ctrl = _make_controller(entity_id=entity.char_id)
        dispatch_player_input(ctrl, PlayerAction.MoveDown, {entity.char_id: entity})
        assert entity.metadata["position"][1] == 63

    def test_wait_does_not_move(self):
        entity = _make_entity(position=[5, 64, 5])
        ctrl = _make_controller(entity_id=entity.char_id)
        dispatch_player_input(ctrl, PlayerAction.Wait, {entity.char_id: entity})
        assert entity.metadata["position"] == [5, 64, 5]

    def test_interact_is_noop(self):
        entity = _make_entity(position=[5, 64, 5])
        ctrl = _make_controller(entity_id=entity.char_id)
        dispatch_player_input(ctrl, PlayerAction.Interact, {entity.char_id: entity})
        assert entity.metadata["position"] == [5, 64, 5]

    def test_returns_controller(self):
        entity = _make_entity(position=[0, 64, 0])
        ctrl = _make_controller(entity_id=entity.char_id)
        result = dispatch_player_input(ctrl, PlayerAction.MoveEast, {entity.char_id: entity})
        assert result is ctrl

    def test_chunk_id_updates_on_boundary_cross(self):
        from src.terrain.chunk import CHUNK_WIDTH
        # Start at x = CHUNK_WIDTH - 1 (last voxel of chunk 0).
        entity = _make_entity(position=[CHUNK_WIDTH - 1, 64, 0])
        ctrl = _make_controller(entity_id=entity.char_id, chunk_id="0_0")
        dispatch_player_input(ctrl, PlayerAction.MoveEast, {entity.char_id: entity})
        # Now at CHUNK_WIDTH → chunk 1.
        assert ctrl.chunk_id == "1_0"

    def test_unknown_entity_does_not_crash(self):
        ctrl = _make_controller(entity_id="missing")
        result = dispatch_player_input(ctrl, PlayerAction.MoveNorth, {})
        assert result is ctrl


# ---------------------------------------------------------------------------
# PH2-012 · calculate_visible_voxels / calculate_visible_voxels_at
# ---------------------------------------------------------------------------

class TestCalculateVisibleVoxels:
    def _voxels_sphere(self, centre=(0, 64, 0), r=10) -> set[tuple[int, int, int]]:
        """Generate a sphere of voxels."""
        cx, cy, cz = centre
        return {
            (cx + dx, cy + dy, cz + dz)
            for dx in range(-r, r + 1)
            for dy in range(-r, r + 1)
            for dz in range(-r, r + 1)
        }

    def test_visible_within_radius(self):
        ctrl = _make_controller(vision_radius=3)
        player_pos = (0, 64, 0)
        chunk_voxels = self._voxels_sphere(player_pos, r=10)
        visible, hidden = calculate_visible_voxels_at(ctrl, chunk_voxels, player_pos)
        # All voxels within radius 3 should be visible.
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                for dz in range(-3, 4):
                    if dx*dx + dy*dy + dz*dz <= 9:
                        v = (player_pos[0]+dx, player_pos[1]+dy, player_pos[2]+dz)
                        if v in chunk_voxels:
                            assert v in visible

    def test_hidden_is_complement(self):
        ctrl = _make_controller(vision_radius=2)
        player_pos = (0, 64, 0)
        chunk_voxels = self._voxels_sphere(player_pos, r=5)
        visible, hidden = calculate_visible_voxels_at(ctrl, chunk_voxels, player_pos)
        assert visible | hidden == chunk_voxels
        assert visible & hidden == set()

    def test_fog_revealed_grows_monotonically(self):
        ctrl = _make_controller(vision_radius=2)
        chunk_voxels = self._voxels_sphere((0, 64, 0), r=5)
        visible1, _ = calculate_visible_voxels_at(ctrl, chunk_voxels, (0, 64, 0))
        revealed_after_first = frozenset(ctrl.fog_revealed)
        # Move and recalculate.
        visible2, _ = calculate_visible_voxels_at(ctrl, chunk_voxels, (3, 64, 0))
        # fog_revealed should be a superset of the first reveal.
        assert ctrl.fog_revealed >= revealed_after_first

    def test_empty_chunk_voxels(self):
        ctrl = _make_controller(vision_radius=4)
        visible, hidden = calculate_visible_voxels_at(ctrl, set(), (0, 64, 0))
        assert visible == set()
        assert hidden == set()

    def test_vision_radius_zero_reveals_only_player_voxel(self):
        ctrl = _make_controller(vision_radius=0)
        player_pos = (0, 64, 0)
        chunk_voxels = {player_pos, (1, 64, 0), (0, 64, 1)}
        visible, hidden = calculate_visible_voxels_at(ctrl, chunk_voxels, player_pos)
        assert visible == {player_pos}
        assert (1, 64, 0) in hidden

    def test_default_calculate_visible_voxels(self):
        ctrl = _make_controller(vision_radius=2)
        chunk_voxels = {(0, 64, 0), (10, 64, 10), (0, 64, 1)}
        # Should not crash.
        visible, hidden = calculate_visible_voxels(ctrl, chunk_voxels)
        assert isinstance(visible, set)
        assert isinstance(hidden, set)


# ---------------------------------------------------------------------------
# Helper: _chunk_id_is_numeric
# ---------------------------------------------------------------------------

class TestChunkIdIsNumeric:
    def test_valid(self):
        assert _chunk_id_is_numeric("0_0") is True
        assert _chunk_id_is_numeric("-1_3") is True
        assert _chunk_id_is_numeric("10_20") is True

    def test_invalid(self):
        assert _chunk_id_is_numeric("chunk_A") is False
        assert _chunk_id_is_numeric("abc") is False
        assert _chunk_id_is_numeric("") is False
        assert _chunk_id_is_numeric("1_2_3") is False


# ---------------------------------------------------------------------------
# PH2-014 · update_loaded_chunks
# ---------------------------------------------------------------------------

class TestUpdateLoadedChunks:
    def _make_chunk_manager(self):
        from src.core.event_bus import EventBus
        from src.terrain.chunk_manager import ChunkManager
        import tempfile, os
        tmpdir = tempfile.mkdtemp()
        return ChunkManager(event_bus=EventBus(), cache_size=64, saves_dir=tmpdir)

    def test_loads_nearby_chunks(self):
        mgr = self._make_chunk_manager()
        ctrl = _make_controller(chunk_id="0_0")
        newly_loaded, newly_unloaded = update_loaded_chunks(ctrl, mgr, load_radius=1)
        assert len(newly_loaded) > 0
        # Should have loaded (0,0) and its neighbours.
        assert "0_0" in newly_loaded or (0, 0) in mgr._cache

    def test_unloads_distant_chunks(self):
        mgr = self._make_chunk_manager()
        # Manually load a distant chunk.
        mgr.load_chunk(100, 100)
        ctrl = _make_controller(chunk_id="0_0")
        _, newly_unloaded = update_loaded_chunks(ctrl, mgr, load_radius=1)
        assert "100_100" in newly_unloaded

    def test_returns_tuple_of_lists(self):
        mgr = self._make_chunk_manager()
        ctrl = _make_controller(chunk_id="0_0")
        result = update_loaded_chunks(ctrl, mgr, load_radius=0)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], list)
        assert isinstance(result[1], list)

    def test_non_numeric_chunk_id_fallback(self):
        mgr = self._make_chunk_manager()
        ctrl = _make_controller(chunk_id="chunk_alpha")
        # Should not crash; may load nothing but returns valid lists.
        newly_loaded, newly_unloaded = update_loaded_chunks(ctrl, mgr, load_radius=1)
        assert isinstance(newly_loaded, list)

    def test_world_chunks_adjacency_routing(self):
        from src.world_sim.population import WorldChunk
        from src.world_sim.biome import Biome
        # Build a simple linear chain: A → B → C.
        chunks = [
            WorldChunk("A", Biome.Temperate_Plain, ("B",), {}, {}),
            WorldChunk("B", Biome.Temperate_Plain, ("A", "C"), {}, {}),
            WorldChunk("C", Biome.Temperate_Plain, ("B",), {}, {}),
        ]
        mgr = self._make_chunk_manager()
        ctrl = PlayerController("p", "e", "A")
        # With non-numeric chunk_ids and world_chunks provided, adjacency BFS is used.
        newly_loaded, newly_unloaded = update_loaded_chunks(
            ctrl, mgr, load_radius=1, world_chunks=chunks
        )
        # The function should not crash; chunk_ids are non-numeric so no loads happen.
        assert isinstance(newly_loaded, list)
        assert isinstance(newly_unloaded, list)
