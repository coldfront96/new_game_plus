"""
tests/terrain/test_chunk_manager.py
-----------------------------------
Unit tests for the ChunkManager and Chunk classes.

Verifies:
- Chunks load and generate correctly
- LRU eviction works without memory leaks
- Chunks save/load to disk correctly
- Block access via world coordinates
- Event publishing on chunk lifecycle
- PhysicsSystem gravity integration
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from src.core.event_bus import EventBus
from src.terrain.block import Block, Material
from src.terrain.chunk import Chunk, CHUNK_WIDTH, CHUNK_HEIGHT, CHUNK_DEPTH
from src.terrain.chunk_manager import ChunkManager


# ---------------------------------------------------------------------------
# Chunk tests
# ---------------------------------------------------------------------------


class TestChunk:
    """Tests for the Chunk data structure."""

    def test_chunk_creation(self) -> None:
        """A new chunk is created with correct dimensions."""
        chunk = Chunk(cx=0, cz=0)
        assert chunk.cx == 0
        assert chunk.cz == 0
        assert chunk.dirty is False

    def test_get_block_default_none(self) -> None:
        """All blocks default to None (air)."""
        chunk = Chunk(cx=0, cz=0)
        assert chunk.get_block(0, 0, 0) is None
        assert chunk.get_block(15, 255, 15) is None

    def test_set_and_get_block(self) -> None:
        """Setting a block and retrieving it returns the same block."""
        chunk = Chunk(cx=1, cz=2)
        stone = Block(block_id=2, material=Material.STONE)
        chunk.set_block(5, 64, 5, stone)
        result = chunk.get_block(5, 64, 5)
        assert result is stone

    def test_set_block_marks_dirty(self) -> None:
        """Setting a block marks the chunk as dirty."""
        chunk = Chunk(cx=0, cz=0)
        assert chunk.dirty is False
        chunk.set_block(0, 0, 0, Block(block_id=1, material=Material.DIRT))
        assert chunk.dirty is True

    def test_set_block_to_none_clears(self) -> None:
        """Setting a block to None clears it."""
        chunk = Chunk(cx=0, cz=0)
        chunk.set_block(3, 10, 3, Block(block_id=2, material=Material.STONE))
        chunk.set_block(3, 10, 3, None)
        assert chunk.get_block(3, 10, 3) is None

    def test_out_of_range_x(self) -> None:
        """Accessing x outside [0, 15] raises IndexError."""
        chunk = Chunk(cx=0, cz=0)
        with pytest.raises(IndexError):
            chunk.get_block(16, 0, 0)
        with pytest.raises(IndexError):
            chunk.get_block(-1, 0, 0)

    def test_out_of_range_y(self) -> None:
        """Accessing y outside [0, 255] raises IndexError."""
        chunk = Chunk(cx=0, cz=0)
        with pytest.raises(IndexError):
            chunk.get_block(0, 256, 0)
        with pytest.raises(IndexError):
            chunk.get_block(0, -1, 0)

    def test_out_of_range_z(self) -> None:
        """Accessing z outside [0, 15] raises IndexError."""
        chunk = Chunk(cx=0, cz=0)
        with pytest.raises(IndexError):
            chunk.get_block(0, 0, 16)
        with pytest.raises(IndexError):
            chunk.get_block(0, 0, -1)

    def test_serialisation_roundtrip(self) -> None:
        """Serialising and deserialising preserves chunk data."""
        chunk = Chunk(cx=3, cz=7)
        chunk.set_block(1, 1, 1, Block(block_id=2, material=Material.STONE))
        chunk.set_block(2, 2, 2, Block(block_id=7, material=Material.WATER))

        data = chunk.to_dict()
        restored = Chunk.from_dict(data)

        assert restored.cx == 3
        assert restored.cz == 7
        b1 = restored.get_block(1, 1, 1)
        assert b1 is not None
        assert b1.material == Material.STONE
        b2 = restored.get_block(2, 2, 2)
        assert b2 is not None
        assert b2.material == Material.WATER

    def test_json_roundtrip(self) -> None:
        """JSON serialisation round-trip preserves data."""
        chunk = Chunk(cx=1, cz=1)
        chunk.set_block(0, 0, 0, Block(block_id=3, material=Material.SAND))
        json_str = chunk.to_json()
        restored = Chunk.from_json(json_str)
        b = restored.get_block(0, 0, 0)
        assert b is not None
        assert b.material == Material.SAND


# ---------------------------------------------------------------------------
# ChunkManager tests
# ---------------------------------------------------------------------------


class TestChunkManager:
    """Tests for the ChunkManager LRU cache and persistence."""

    @pytest.fixture
    def tmp_saves(self, tmp_path: Path) -> str:
        """Provide a temporary saves directory."""
        saves = tmp_path / "saves"
        saves.mkdir()
        return str(saves)

    @pytest.fixture
    def bus(self) -> EventBus:
        """Provide a fresh EventBus."""
        return EventBus()

    @pytest.fixture
    def manager(self, bus: EventBus, tmp_saves: str) -> ChunkManager:
        """Provide a ChunkManager with small cache for testing."""
        return ChunkManager(event_bus=bus, cache_size=4, saves_dir=tmp_saves)

    def test_load_generates_chunk(self, manager: ChunkManager) -> None:
        """Loading a chunk that doesn't exist on disk generates it."""
        chunk = manager.load_chunk(0, 0)
        assert isinstance(chunk, Chunk)
        assert chunk.cx == 0
        assert chunk.cz == 0

    def test_load_returns_cached(self, manager: ChunkManager) -> None:
        """Loading the same chunk twice returns the same object."""
        chunk1 = manager.load_chunk(0, 0)
        chunk2 = manager.load_chunk(0, 0)
        assert chunk1 is chunk2

    def test_cache_count(self, manager: ChunkManager) -> None:
        """loaded_count reflects cache state."""
        assert manager.loaded_count == 0
        manager.load_chunk(0, 0)
        assert manager.loaded_count == 1
        manager.load_chunk(1, 0)
        assert manager.loaded_count == 2

    def test_lru_eviction(self, manager: ChunkManager) -> None:
        """Loading more chunks than cache_size evicts the LRU chunk."""
        # Fill cache (size=4)
        manager.load_chunk(0, 0)
        manager.load_chunk(1, 0)
        manager.load_chunk(2, 0)
        manager.load_chunk(3, 0)
        assert manager.loaded_count == 4

        # Loading a 5th chunk should evict the LRU (0, 0)
        manager.load_chunk(4, 0)
        assert manager.loaded_count == 4

    def test_lru_eviction_order(self, manager: ChunkManager) -> None:
        """Accessing a chunk moves it to most-recently-used position."""
        manager.load_chunk(0, 0)
        manager.load_chunk(1, 0)
        manager.load_chunk(2, 0)
        manager.load_chunk(3, 0)

        # Access chunk (0,0) to make it MRU
        manager.load_chunk(0, 0)

        # Load a new chunk — should evict (1,0) not (0,0)
        manager.load_chunk(4, 0)
        assert manager.loaded_count == 4

        # (0,0) should still be cached (accessing it works from cache)
        chunk = manager.load_chunk(0, 0)
        assert chunk.cx == 0

    def test_unload_saves_dirty_chunk(
        self, manager: ChunkManager, tmp_saves: str
    ) -> None:
        """Unloading a dirty chunk saves it to disk."""
        chunk = manager.load_chunk(5, 5)
        chunk.set_block(0, 0, 0, Block(block_id=1, material=Material.DIRT))
        assert chunk.dirty is True

        manager.unload_chunk(5, 5)
        assert manager.loaded_count == 0

        # File should exist on disk
        path = Path(tmp_saves) / "chunk_5_5.json"
        assert path.exists()

    def test_unload_returns_false_for_missing(self, manager: ChunkManager) -> None:
        """Unloading a chunk not in cache returns False."""
        assert manager.unload_chunk(99, 99) is False

    def test_load_from_disk(
        self, manager: ChunkManager, tmp_saves: str
    ) -> None:
        """A chunk saved to disk can be loaded back."""
        # Load, modify, and unload
        chunk = manager.load_chunk(7, 7)
        sand = Block(block_id=3, material=Material.SAND)
        chunk.set_block(4, 100, 4, sand)
        manager.unload_chunk(7, 7)

        # Load again — should come from disk
        chunk2 = manager.load_chunk(7, 7)
        b = chunk2.get_block(4, 100, 4)
        assert b is not None
        assert b.material == Material.SAND

    def test_no_memory_leak_on_eviction(self, bus: EventBus, tmp_saves: str) -> None:
        """Evicting chunks doesn't leak references — cache stays bounded."""
        manager = ChunkManager(event_bus=bus, cache_size=2, saves_dir=tmp_saves)

        # Load many chunks; only 2 should remain in memory
        for i in range(100):
            manager.load_chunk(i, 0)

        assert manager.loaded_count == 2

    def test_events_published_on_load(self, manager: ChunkManager, bus: EventBus) -> None:
        """Loading a chunk publishes 'chunk_loaded' event."""
        events = []
        bus.subscribe("chunk_loaded", lambda p: events.append(p))

        manager.load_chunk(10, 10)
        assert len(events) == 1
        assert events[0] == {"cx": 10, "cz": 10}

    def test_events_published_on_unload(self, manager: ChunkManager, bus: EventBus) -> None:
        """Unloading a chunk publishes 'chunk_unloaded' event."""
        events = []
        bus.subscribe("chunk_unloaded", lambda p: events.append(p))

        manager.load_chunk(10, 10)
        manager.unload_chunk(10, 10)
        assert len(events) == 1
        assert events[0] == {"cx": 10, "cz": 10}

    def test_get_block_world(self, manager: ChunkManager) -> None:
        """get_block_world uses math_utils to convert world coords."""
        chunk = manager.load_chunk(0, 0)
        stone = Block(block_id=2, material=Material.STONE)
        chunk.set_block(5, 64, 5, stone)

        result = manager.get_block_world(5, 64, 5)
        assert result is stone

    def test_set_block_world(self, manager: ChunkManager) -> None:
        """set_block_world places blocks using world coords."""
        dirt = Block(block_id=1, material=Material.DIRT)
        manager.set_block_world(20, 64, 20, dirt)

        # World (20, 64, 20) is chunk (1, 1), local (4, 64, 4)
        result = manager.get_block_world(20, 64, 20)
        assert result is dirt

    def test_set_block_world_publishes_event(
        self, manager: ChunkManager, bus: EventBus
    ) -> None:
        """set_block_world publishes a 'block_modified' event."""
        events = []
        bus.subscribe("block_modified", lambda p: events.append(p))

        dirt = Block(block_id=1, material=Material.DIRT)
        manager.set_block_world(0, 64, 0, dirt)
        assert len(events) == 1
        assert events[0]["world_x"] == 0
        assert events[0]["world_y"] == 64
        assert events[0]["world_z"] == 0

    def test_generated_chunk_has_terrain(self, manager: ChunkManager) -> None:
        """Generated chunks have basic terrain layers."""
        chunk = manager.load_chunk(0, 0)
        # y=0 should be OBSIDIAN (bedrock)
        b0 = chunk.get_block(0, 0, 0)
        assert b0 is not None
        assert b0.material == Material.OBSIDIAN

        # y=30 should be STONE
        b30 = chunk.get_block(0, 30, 0)
        assert b30 is not None
        assert b30.material == Material.STONE

        # y=62 should be DIRT
        b62 = chunk.get_block(0, 62, 0)
        assert b62 is not None
        assert b62.material == Material.DIRT

        # y=100 should be None (air)
        b100 = chunk.get_block(0, 100, 0)
        assert b100 is None


# ---------------------------------------------------------------------------
# PhysicsSystem integration tests
# ---------------------------------------------------------------------------


class TestPhysicsSystem:
    """Integration tests for the PhysicsSystem gravity and structural logic."""

    @pytest.fixture
    def tmp_saves(self, tmp_path: Path) -> str:
        saves = tmp_path / "saves"
        saves.mkdir()
        return str(saves)

    @pytest.fixture
    def bus(self) -> EventBus:
        return EventBus()

    @pytest.fixture
    def manager(self, bus: EventBus, tmp_saves: str) -> ChunkManager:
        return ChunkManager(event_bus=bus, cache_size=8, saves_dir=tmp_saves)

    @pytest.fixture
    def physics(self, bus: EventBus, manager: ChunkManager):
        from src.ai_sim.systems import PhysicsSystem
        return PhysicsSystem(event_bus=bus, chunk_manager=manager)

    def test_sand_falls_to_empty_space(
        self, bus: EventBus, manager: ChunkManager, physics
    ) -> None:
        """A SAND block above air should fall down."""
        # Clear the column — set block at y=10, air below
        for y in range(0, 256):
            manager.set_block_world(0, y, 0, None)

        # Place solid ground at y=0
        manager.set_block_world(0, 0, 0, Block(block_id=13, material=Material.OBSIDIAN))
        # Place sand at y=5
        sand = Block(block_id=3, material=Material.SAND)
        manager.set_block_world(0, 5, 0, sand)

        # Trigger physics by publishing block_broken below sand
        bus.publish("block_broken", {"world_x": 0, "world_y": 4, "world_z": 0})
        physics.update()

        # Sand should have fallen to y=1 (above obsidian)
        result = manager.get_block_world(0, 1, 0)
        assert result is not None
        assert result.material == Material.SAND

        # y=5 should now be empty
        assert manager.get_block_world(0, 5, 0) is None

    def test_gravel_falls(
        self, bus: EventBus, manager: ChunkManager, physics
    ) -> None:
        """GRAVEL blocks are also affected by gravity."""
        for y in range(0, 256):
            manager.set_block_world(0, y, 0, None)

        manager.set_block_world(0, 0, 0, Block(block_id=13, material=Material.OBSIDIAN))
        gravel = Block(block_id=4, material=Material.GRAVEL)
        manager.set_block_world(0, 3, 0, gravel)

        bus.publish("block_broken", {"world_x": 0, "world_y": 2, "world_z": 0})
        physics.update()

        result = manager.get_block_world(0, 1, 0)
        assert result is not None
        assert result.material == Material.GRAVEL

    def test_fluid_falls(
        self, bus: EventBus, manager: ChunkManager, physics
    ) -> None:
        """Fluid blocks (WATER) should fall through empty space."""
        for y in range(0, 256):
            manager.set_block_world(0, y, 0, None)

        manager.set_block_world(0, 0, 0, Block(block_id=13, material=Material.OBSIDIAN))
        water = Block(block_id=7, material=Material.WATER)
        manager.set_block_world(0, 4, 0, water)

        bus.publish("block_broken", {"world_x": 0, "world_y": 3, "world_z": 0})
        physics.update()

        result = manager.get_block_world(0, 1, 0)
        assert result is not None
        assert result.material == Material.WATER

    def test_stone_does_not_fall(
        self, bus: EventBus, manager: ChunkManager, physics
    ) -> None:
        """STONE blocks should NOT be affected by gravity."""
        for y in range(0, 256):
            manager.set_block_world(0, y, 0, None)

        stone = Block(block_id=2, material=Material.STONE)
        manager.set_block_world(0, 5, 0, stone)

        bus.publish("block_broken", {"world_x": 0, "world_y": 4, "world_z": 0})
        physics.update()

        # Stone should stay at y=5
        result = manager.get_block_world(0, 5, 0)
        assert result is not None
        assert result.material == Material.STONE

    def test_block_fell_event_published(
        self, bus: EventBus, manager: ChunkManager, physics
    ) -> None:
        """When a block falls, a 'block_fell' event is published."""
        events = []
        bus.subscribe("block_fell", lambda p: events.append(p))

        for y in range(0, 256):
            manager.set_block_world(0, y, 0, None)

        manager.set_block_world(0, 0, 0, Block(block_id=13, material=Material.OBSIDIAN))
        manager.set_block_world(0, 5, 0, Block(block_id=3, material=Material.SAND))

        bus.publish("block_broken", {"world_x": 0, "world_y": 4, "world_z": 0})
        physics.update()

        assert len(events) == 1
        assert events[0]["from_y"] == 5
        assert events[0]["to_y"] == 1
        assert events[0]["material"] == "SAND"
