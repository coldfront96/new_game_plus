"""Tests for Phase 3: Dungeon Carver subsystem (PH3-001 · PH3-002 · PH3-003)."""
from __future__ import annotations

import random

import pytest

from src.terrain.chunk import Chunk
from src.terrain.block import Material
from src.terrain.dungeon_carver import (
    FLOOR_DEPTH_VOXELS,
    MAX_DUNGEON_FLOORS,
    DungeonFloor,
    DungeonRoom,
    DungeonHallway,
    DungeonSpawnManifest,
    carve_dungeon,
    populate_dungeon_floor,
    _det_uuid,
    _rooms_overlap,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_chunk() -> Chunk:
    from src.terrain.chunk_generator import ChunkGenerator
    gen = ChunkGenerator(seed=42)
    return gen.generate_chunk(cx=0, cz=0)


# ---------------------------------------------------------------------------
# PH3-001 — DungeonFloor schema
# ---------------------------------------------------------------------------

class TestDungeonFloorSchema:
    def test_constants(self):
        assert FLOOR_DEPTH_VOXELS == 16
        assert MAX_DUNGEON_FLOORS == 5

    def test_dungeon_room_defaults(self):
        room = DungeonRoom(
            room_id="r1",
            origin=(0, -16, 0),
            width=4,
            depth=4,
        )
        assert room.height == 4

    def test_dungeon_hallway_defaults(self):
        hall = DungeonHallway(
            hall_id="h1",
            start_voxel=(2, -16, 2),
            end_voxel=(8, -16, 8),
        )
        assert hall.width == 2

    def test_dungeon_floor_fields(self):
        room = DungeonRoom("r1", (0, -16, 0), 4, 4)
        hall = DungeonHallway("h1", (2, -16, 2), (8, -16, 8))
        floor = DungeonFloor(
            floor_index=0,
            z_offset=-FLOOR_DEPTH_VOXELS,
            rooms=[room],
            hallways=[hall],
            anchor_chunk_id="0,0",
        )
        assert floor.floor_index == 0
        assert floor.z_offset == -FLOOR_DEPTH_VOXELS
        assert len(floor.rooms) == 1
        assert len(floor.hallways) == 1
        assert floor.anchor_chunk_id == "0,0"

    def test_det_uuid_deterministic(self):
        a = _det_uuid("chunk0:0:1")
        b = _det_uuid("chunk0:0:1")
        assert a == b

    def test_det_uuid_distinct(self):
        a = _det_uuid("chunk0:0:0")
        b = _det_uuid("chunk0:0:1")
        assert a != b


# ---------------------------------------------------------------------------
# PH3-001 — AABB overlap
# ---------------------------------------------------------------------------

class TestRoomsOverlap:
    def _room(self, x, z, w, d):
        return DungeonRoom("r", (x, -16, z), w, d)

    def test_no_overlap(self):
        a = self._room(0, 0, 4, 4)
        b = self._room(5, 5, 4, 4)
        assert not _rooms_overlap(a, b)

    def test_overlap(self):
        a = self._room(0, 0, 4, 4)
        b = self._room(2, 2, 4, 4)
        assert _rooms_overlap(a, b)

    def test_adjacent_no_overlap(self):
        a = self._room(0, 0, 4, 4)
        b = self._room(4, 0, 4, 4)
        assert not _rooms_overlap(a, b)


# ---------------------------------------------------------------------------
# PH3-002 — carve_dungeon
# ---------------------------------------------------------------------------

class TestCarveDungeon:
    def test_returns_correct_floor_count(self):
        chunk = _make_chunk()
        rng = random.Random(1)
        floors = carve_dungeon(chunk, num_floors=3, anchor_chunk_id="0,0", anomaly=None, rng=rng)
        assert len(floors) == 3

    def test_floor_indices_sequential(self):
        chunk = _make_chunk()
        rng = random.Random(2)
        floors = carve_dungeon(chunk, num_floors=3, anchor_chunk_id="0,0", anomaly=None, rng=rng)
        for i, floor in enumerate(floors):
            assert floor.floor_index == i

    def test_z_offset_negative(self):
        chunk = _make_chunk()
        rng = random.Random(3)
        floors = carve_dungeon(chunk, num_floors=2, anchor_chunk_id="0,0", anomaly=None, rng=rng)
        for floor in floors:
            assert floor.z_offset < 0

    def test_z_offset_formula(self):
        chunk = _make_chunk()
        rng = random.Random(4)
        floors = carve_dungeon(chunk, num_floors=3, anchor_chunk_id="0,0", anomaly=None, rng=rng)
        for f, floor in enumerate(floors):
            expected = -(f + 1) * FLOOR_DEPTH_VOXELS
            assert floor.z_offset == expected

    def test_anchor_chunk_id_propagated(self):
        chunk = _make_chunk()
        rng = random.Random(5)
        floors = carve_dungeon(chunk, num_floors=2, anchor_chunk_id="3,7", anomaly=None, rng=rng)
        for floor in floors:
            assert floor.anchor_chunk_id == "3,7"

    def test_rooms_placed(self):
        chunk = _make_chunk()
        rng = random.Random(6)
        floors = carve_dungeon(chunk, num_floors=1, anchor_chunk_id="0,0", anomaly=None, rng=rng)
        assert len(floors[0].rooms) >= 2

    def test_room_ids_deterministic(self):
        rng1 = random.Random(42)
        rng2 = random.Random(42)
        c1 = _make_chunk()
        c2 = _make_chunk()
        floors1 = carve_dungeon(c1, num_floors=1, anchor_chunk_id="0,0", anomaly=None, rng=rng1)
        floors2 = carve_dungeon(c2, num_floors=1, anchor_chunk_id="0,0", anomaly=None, rng=rng2)
        ids1 = [r.room_id for r in floors1[0].rooms]
        ids2 = [r.room_id for r in floors2[0].rooms]
        assert ids1 == ids2

    def test_hallways_connect_rooms(self):
        chunk = _make_chunk()
        rng = random.Random(7)
        floors = carve_dungeon(chunk, num_floors=1, anchor_chunk_id="0,0", anomaly=None, rng=rng)
        floor = floors[0]
        # Hallways count should be rooms - 1
        assert len(floor.hallways) == len(floor.rooms) - 1

    def test_voxels_carved_to_air(self):
        chunk = _make_chunk()
        rng = random.Random(8)
        floors = carve_dungeon(chunk, num_floors=1, anchor_chunk_id="0,0", anomaly=None, rng=rng)
        # Check that at least some interior voxels were carved to None (air)
        floor = floors[0]
        found_air = False
        for room in floor.rooms:
            rx, ry_neg, rz = room.origin
            from src.terrain.dungeon_carver import _SURFACE_Y
            y_top = _SURFACE_Y + ry_neg
            y_bot = max(1, y_top - room.height + 1)
            for x in range(rx, rx + room.width):
                for z in range(rz, rz + room.depth):
                    for y in range(y_bot + 1, y_top):
                        if chunk.get_block(x, y, z) is None:
                            found_air = True
        assert found_air

    def test_max_dungeon_floors_capped(self):
        chunk = _make_chunk()
        rng = random.Random(9)
        floors = carve_dungeon(chunk, num_floors=100, anchor_chunk_id="0,0", anomaly=None, rng=rng)
        assert len(floors) <= MAX_DUNGEON_FLOORS

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
        chunk = _make_chunk()
        rng = random.Random(10)
        floors = carve_dungeon(chunk, num_floors=2, anchor_chunk_id="0,0", anomaly=anomaly, rng=rng)
        assert len(floors) == 2


# ---------------------------------------------------------------------------
# PH3-003 — DungeonSpawnManifest schema
# ---------------------------------------------------------------------------

class TestDungeonSpawnManifest:
    def test_dataclass_fields(self):
        manifest = DungeonSpawnManifest(
            floor_index=0,
            room_id="r1",
            trap_voxels={},
            treasure_voxels={},
        )
        assert manifest.floor_index == 0
        assert manifest.room_id == "r1"
        assert isinstance(manifest.trap_voxels, dict)
        assert isinstance(manifest.treasure_voxels, dict)


class TestPopulateDungeonFloor:
    def _make_floor(self, rng: random.Random) -> DungeonFloor:
        chunk = _make_chunk()
        floors = carve_dungeon(chunk, num_floors=1, anchor_chunk_id="0,0", anomaly=None, rng=rng)
        return floors[0]

    def test_returns_manifest(self):
        rng = random.Random(11)
        floor = self._make_floor(rng)
        manifest = populate_dungeon_floor(floor, party_level=5, rng=rng)
        assert isinstance(manifest, DungeonSpawnManifest)

    def test_manifest_floor_index_matches(self):
        rng = random.Random(12)
        floor = self._make_floor(rng)
        manifest = populate_dungeon_floor(floor, party_level=3, rng=rng)
        assert manifest.floor_index == floor.floor_index

    def test_voxel_keys_are_tuples(self):
        rng = random.Random(13)
        floor = self._make_floor(rng)
        manifest = populate_dungeon_floor(floor, party_level=5, rng=rng)
        for key in manifest.trap_voxels:
            assert isinstance(key, tuple) and len(key) == 3
        for key in manifest.treasure_voxels:
            assert isinstance(key, tuple) and len(key) == 3

    def test_traps_are_valid_objects(self):
        from src.rules_engine.traps import MechanicalTrap, MagicalTrap
        rng = random.Random(14)
        # Run several seeds to reliably get a trap (1/3 chance per room)
        found = False
        for seed in range(100):
            rng = random.Random(seed)
            floor = self._make_floor(rng)
            manifest = populate_dungeon_floor(floor, party_level=5, rng=rng)
            if manifest.trap_voxels:
                for trap in manifest.trap_voxels.values():
                    assert isinstance(trap, (MechanicalTrap, MagicalTrap))
                found = True
                break
        assert found, "Expected at least one floor with a trap in 100 attempts"

    def test_treasure_are_valid_hoards(self):
        from src.rules_engine.treasure import TreasureHoard
        found = False
        for seed in range(100):
            rng = random.Random(seed)
            floor = self._make_floor(rng)
            manifest = populate_dungeon_floor(floor, party_level=5, rng=rng)
            if manifest.treasure_voxels:
                for hoard in manifest.treasure_voxels.values():
                    assert isinstance(hoard, TreasureHoard)
                found = True
                break
        assert found, "Expected at least one floor with treasure in 100 attempts"

    def test_trap_and_treasure_not_same_voxel(self):
        for seed in range(200):
            rng = random.Random(seed)
            floor = self._make_floor(rng)
            manifest = populate_dungeon_floor(floor, party_level=5, rng=rng)
            overlap = set(manifest.trap_voxels) & set(manifest.treasure_voxels)
            assert not overlap, f"Trap and treasure share voxels: {overlap}"
