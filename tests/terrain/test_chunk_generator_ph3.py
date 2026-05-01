"""Tests for Phase 3: ChunkGenerator negative-Z dungeon integration (PH3-004)."""
from __future__ import annotations

import random

import pytest

from src.terrain.chunk_generator import ChunkGenerator, _apply_dungeon_floors
from src.terrain.chunk import Chunk
from src.terrain.dungeon_carver import DungeonFloor, DungeonRoom, DungeonHallway


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _gen(seed: int = 42) -> ChunkGenerator:
    return ChunkGenerator(seed=seed)


def _simple_floor(floor_index: int = 0) -> DungeonFloor:
    """Create a minimal DungeonFloor with one room and no hallways."""
    from src.terrain.dungeon_carver import FLOOR_DEPTH_VOXELS, _SURFACE_Y
    z_base = -(floor_index + 1) * FLOOR_DEPTH_VOXELS
    room = DungeonRoom(
        room_id=f"r-{floor_index}",
        origin=(4, z_base, 4),
        width=4,
        depth=4,
    )
    return DungeonFloor(
        floor_index=floor_index,
        z_offset=z_base,
        rooms=[room],
        hallways=[],
        anchor_chunk_id="0,0",
    )


# ---------------------------------------------------------------------------
# PH3-004 — generate_chunk signature backward compatibility
# ---------------------------------------------------------------------------

class TestGenerateChunkBackwardCompat:
    def test_no_dungeon_floors_works_as_before(self):
        gen = _gen()
        chunk = gen.generate_chunk(0, 0)
        assert isinstance(chunk, Chunk)

    def test_none_dungeon_floors_works(self):
        gen = _gen()
        chunk = gen.generate_chunk(0, 0, dungeon_floors=None)
        assert isinstance(chunk, Chunk)


# ---------------------------------------------------------------------------
# PH3-004 — generate_chunk with dungeon_floors
# ---------------------------------------------------------------------------

class TestGenerateChunkWithDungeonFloors:
    def test_accepts_dungeon_floors_list(self):
        gen = _gen()
        floor = _simple_floor(0)
        chunk = gen.generate_chunk(0, 0, dungeon_floors=[floor])
        assert isinstance(chunk, Chunk)

    def test_voxels_cleared_by_dungeon_floor(self):
        from src.terrain.dungeon_carver import _SURFACE_Y, FLOOR_DEPTH_VOXELS
        gen = _gen()
        floor_index = 0
        floor = _simple_floor(floor_index)
        chunk = gen.generate_chunk(0, 0, dungeon_floors=[floor])

        room = floor.rooms[0]
        rx, ry_neg, rz = room.origin
        y_top = _SURFACE_Y + ry_neg
        y_bot = max(1, y_top - room.height + 1)

        # At least some interior voxels should be air
        found_air = False
        for x in range(rx, rx + room.width):
            for z in range(rz, rz + room.depth):
                for y in range(y_bot + 1, y_top):
                    if chunk.get_block(x, y, z) is None:
                        found_air = True
        assert found_air

    def test_chunk_not_dirty(self):
        gen = _gen()
        chunk = gen.generate_chunk(0, 0, dungeon_floors=[_simple_floor()])
        assert not chunk.dirty


# ---------------------------------------------------------------------------
# PH3-004 — generate_chunk_with_dungeon
# ---------------------------------------------------------------------------

class TestGenerateChunkWithDungeon:
    def test_returns_three_tuple(self):
        gen = _gen()
        result = gen.generate_chunk_with_dungeon(0, 0, num_floors=2, anomaly=None, rng=random.Random(42))
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_returns_chunk(self):
        gen = _gen()
        chunk, floors, manifests = gen.generate_chunk_with_dungeon(
            0, 0, num_floors=2, anomaly=None, rng=random.Random(1)
        )
        assert isinstance(chunk, Chunk)

    def test_floors_count(self):
        gen = _gen()
        _, floors, _ = gen.generate_chunk_with_dungeon(
            0, 0, num_floors=3, anomaly=None, rng=random.Random(2)
        )
        assert len(floors) == 3

    def test_manifests_count_matches_floors(self):
        gen = _gen()
        _, floors, manifests = gen.generate_chunk_with_dungeon(
            0, 0, num_floors=3, anomaly=None, rng=random.Random(3)
        )
        assert len(manifests) == len(floors)

    def test_deterministic_with_same_seed(self):
        gen1 = _gen(seed=99)
        gen2 = _gen(seed=99)
        _, floors1, _ = gen1.generate_chunk_with_dungeon(
            0, 0, num_floors=2, anomaly=None, rng=random.Random(7)
        )
        _, floors2, _ = gen2.generate_chunk_with_dungeon(
            0, 0, num_floors=2, anomaly=None, rng=random.Random(7)
        )
        ids1 = [r.room_id for f in floors1 for r in f.rooms]
        ids2 = [r.room_id for f in floors2 for r in f.rooms]
        assert ids1 == ids2

    def test_anomaly_does_not_crash(self):
        from src.world_sim.anomaly import AnomalyRecord
        from src.world_sim.biome import Biome
        anomaly = AnomalyRecord(
            anomaly_id="a1",
            entity_id="e1",
            species_id="goblin",
            chunk_id="0,0",
            native_biome=Biome.Temperate_Forest,
            current_biome=Biome.Any_Ruin,
            anomaly_roll=0.001,
            world_tick=1,
            lore_text=None,
        )
        gen = _gen()
        chunk, floors, manifests = gen.generate_chunk_with_dungeon(
            0, 0, num_floors=2, anomaly=anomaly, rng=random.Random(42)
        )
        assert isinstance(chunk, Chunk)

    def test_floor_rooms_present(self):
        gen = _gen()
        _, floors, _ = gen.generate_chunk_with_dungeon(
            0, 0, num_floors=1, anomaly=None, rng=random.Random(42)
        )
        assert all(len(f.rooms) >= 1 for f in floors)


# ---------------------------------------------------------------------------
# PH3-004 — _apply_dungeon_floors
# ---------------------------------------------------------------------------

class TestApplyDungeonFloors:
    def test_clears_room_interior_voxels(self):
        from src.terrain.dungeon_carver import _SURFACE_Y
        gen = _gen()
        chunk = gen.generate_chunk(0, 0)
        floor = _simple_floor(0)
        _apply_dungeon_floors(chunk, [floor])

        room = floor.rooms[0]
        rx, ry_neg, rz = room.origin
        y_top = _SURFACE_Y + ry_neg
        y_bot = max(1, y_top - room.height + 1)

        found_air = False
        for x in range(rx, rx + room.width):
            for z in range(rz, rz + room.depth):
                for y in range(y_bot + 1, y_top):
                    if chunk.get_block(x, y, z) is None:
                        found_air = True
        assert found_air

    def test_bedrock_untouched(self):
        gen = _gen()
        chunk = gen.generate_chunk(0, 0)
        floor = _simple_floor(0)
        _apply_dungeon_floors(chunk, [floor])
        # Y=0 should still be bedrock (OBSIDIAN)
        from src.terrain.block import Material
        block = chunk.get_block(0, 0, 0)
        assert block is not None
        assert block.material == Material.OBSIDIAN
