"""Tests for EM-003 · EM-005 — lairs module and carve_lair API."""
from __future__ import annotations

import pytest

from src.world_sim.lairs import LairType, LairRecord
from src.terrain.chunk_generator import ChunkGenerator, carve_lair
from src.terrain.chunk import Chunk, CHUNK_WIDTH, CHUNK_DEPTH, CHUNK_HEIGHT


# ---------------------------------------------------------------------------
# EM-003 · LairType enum
# ---------------------------------------------------------------------------

class TestLairType:
    def test_all_members_exist(self):
        assert LairType.Burrow.value   == "Burrow"
        assert LairType.Cave.value     == "Cave"
        assert LairType.Hive.value     == "Hive"
        assert LairType.Fortress.value == "Fortress"

    def test_four_members(self):
        assert len(LairType) == 4


# ---------------------------------------------------------------------------
# EM-003 · LairRecord dataclass
# ---------------------------------------------------------------------------

class TestLairRecord:
    def test_creation(self):
        lr = LairRecord(
            lair_id="lair_001",
            monster_name="Dragon",
            lair_type=LairType.Cave,
            chunk_id="chunk_0_0",
            width=10,
            depth=10,
            height=5,
        )
        assert lr.lair_id      == "lair_001"
        assert lr.monster_name == "Dragon"
        assert lr.lair_type    == LairType.Cave
        assert lr.chunk_id     == "chunk_0_0"
        assert lr.width        == 10
        assert lr.depth        == 10
        assert lr.height       == 5

    def test_slots_no_dict(self):
        lr = LairRecord("x", "Orc", LairType.Fortress, "c", 5, 5, 3)
        assert not hasattr(lr, "__dict__")

    def test_burrow_type(self):
        lr = LairRecord("b", "Badger", LairType.Burrow, "c", 3, 3, 2)
        assert lr.lair_type == LairType.Burrow

    def test_hive_type(self):
        lr = LairRecord("h", "Formian", LairType.Hive, "c", 8, 8, 4)
        assert lr.lair_type == LairType.Hive


# ---------------------------------------------------------------------------
# EM-005 · carve_lair function
# ---------------------------------------------------------------------------

class TestCarveLair:
    def _gen_chunk(self, seed: int = 42) -> Chunk:
        return ChunkGenerator(seed=seed).generate_chunk(0, 0)

    def _lair(self, width=4, depth=4, height=3) -> LairRecord:
        return LairRecord("lair1", "Dragon", LairType.Cave, "c0", width, depth, height)

    def test_carve_creates_air_in_cavity(self):
        chunk = self._gen_chunk()
        lair = self._lair(width=4, depth=4, height=3)
        carve_lair(chunk, lair)

        # Center of chunk
        cx, cz = CHUNK_WIDTH // 2, CHUNK_DEPTH // 2
        half_w, half_d = lair.width // 2, lair.depth // 2
        x = cx - half_w + 1
        z = cz - half_d + 1
        # y_top is BASE_HEIGHT - 1 = 63
        y = 63
        block = chunk.get_block(x, y, z)
        assert block is None, "Carved region should be air (None)"

    def test_carve_returns_same_chunk(self):
        chunk = self._gen_chunk()
        lair = self._lair()
        result = carve_lair(chunk, lair)
        assert result is chunk

    def test_carve_marks_chunk_dirty(self):
        chunk = self._gen_chunk()
        chunk.dirty = False
        lair = self._lair()
        carve_lair(chunk, lair)
        assert chunk.dirty is True

    def test_oversized_lair_clamped(self):
        """Lair larger than chunk dimensions should not raise IndexError."""
        chunk = self._gen_chunk()
        lair = LairRecord("big", "Tarrasque", LairType.Cave, "c0", 100, 100, 200)
        carve_lair(chunk, lair)   # must not raise

    def test_generate_chunk_with_lair(self):
        """ChunkGenerator.generate_chunk_with_lair carves lair into generated chunk."""
        gen = ChunkGenerator(seed=7)
        lair = self._lair(width=6, depth=6, height=4)
        chunk = gen.generate_chunk_with_lair(0, 0, lair)
        # Verify cavity at chunk center
        cx, cz = CHUNK_WIDTH // 2, CHUNK_DEPTH // 2
        block = chunk.get_block(cx, 63, cz)
        assert block is None
