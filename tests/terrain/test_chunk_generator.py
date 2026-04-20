"""
tests/terrain/test_chunk_generator.py
--------------------------------------
Unit tests for the ChunkGenerator procedural terrain module.

Verifies:
- Deterministic generation given a seed
- Correct stratification (bedrock, stone, dirt, grass)
- Ore distribution within expected depth ranges
- Heightmap produces valid surface levels
- Memory optimization via @dataclass(slots=True)
"""

from __future__ import annotations

import pytest

from src.terrain.block import Block, Material
from src.terrain.chunk import Chunk, CHUNK_WIDTH, CHUNK_DEPTH, CHUNK_HEIGHT
from src.terrain.chunk_generator import (
    ChunkGenerator,
    BASE_HEIGHT,
    HEIGHT_AMPLITUDE,
    DIRT_LAYER_DEPTH,
    IRON_ORE_MIN_Y,
    IRON_ORE_MAX_Y,
    GOLD_ORE_MIN_Y,
    GOLD_ORE_MAX_Y,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def generator() -> ChunkGenerator:
    """Provide a ChunkGenerator with a fixed seed."""
    return ChunkGenerator(seed=12345)


# ---------------------------------------------------------------------------
# Basic generation tests
# ---------------------------------------------------------------------------


class TestChunkGeneratorBasic:
    """Tests for basic ChunkGenerator functionality."""

    def test_slots_enabled(self) -> None:
        """ChunkGenerator uses __slots__ for memory efficiency."""
        assert hasattr(ChunkGenerator, "__slots__")

    def test_returns_chunk(self, generator: ChunkGenerator) -> None:
        """generate_chunk returns a Chunk instance."""
        chunk = generator.generate_chunk(0, 0)
        assert isinstance(chunk, Chunk)

    def test_chunk_coordinates(self, generator: ChunkGenerator) -> None:
        """Generated chunk has the correct cx, cz coordinates."""
        chunk = generator.generate_chunk(3, 7)
        assert chunk.cx == 3
        assert chunk.cz == 7

    def test_chunk_not_dirty(self, generator: ChunkGenerator) -> None:
        """Freshly generated chunk is not marked dirty."""
        chunk = generator.generate_chunk(0, 0)
        assert chunk.dirty is False

    def test_deterministic_generation(self) -> None:
        """Same seed produces identical chunks."""
        gen1 = ChunkGenerator(seed=42)
        gen2 = ChunkGenerator(seed=42)
        chunk1 = gen1.generate_chunk(5, 5)
        chunk2 = gen2.generate_chunk(5, 5)

        for x in range(CHUNK_WIDTH):
            for z in range(CHUNK_DEPTH):
                for y in range(CHUNK_HEIGHT):
                    b1 = chunk1.get_block(x, y, z)
                    b2 = chunk2.get_block(x, y, z)
                    if b1 is None:
                        assert b2 is None
                    else:
                        assert b2 is not None
                        assert b1.material == b2.material

    def test_different_seeds_differ(self) -> None:
        """Different seeds produce different terrain."""
        gen1 = ChunkGenerator(seed=1)
        gen2 = ChunkGenerator(seed=9999)
        chunk1 = gen1.generate_chunk(0, 0)
        chunk2 = gen2.generate_chunk(0, 0)

        # Check a sample of blocks — at least some should differ
        differences = 0
        for x in range(CHUNK_WIDTH):
            for z in range(CHUNK_DEPTH):
                b1 = chunk1.get_block(x, 64, z)
                b2 = chunk2.get_block(x, 64, z)
                m1 = b1.material if b1 else None
                m2 = b2.material if b2 else None
                if m1 != m2:
                    differences += 1

        assert differences > 0


# ---------------------------------------------------------------------------
# Stratification tests
# ---------------------------------------------------------------------------


class TestStratification:
    """Tests for terrain layer ordering."""

    def test_bedrock_at_y0(self, generator: ChunkGenerator) -> None:
        """Y=0 is always bedrock (OBSIDIAN)."""
        chunk = generator.generate_chunk(0, 0)
        for x in range(CHUNK_WIDTH):
            for z in range(CHUNK_DEPTH):
                block = chunk.get_block(x, 0, z)
                assert block is not None
                assert block.material == Material.OBSIDIAN

    def test_stone_below_dirt(self, generator: ChunkGenerator) -> None:
        """Stone appears below the dirt layers."""
        chunk = generator.generate_chunk(0, 0)
        # Check center column
        block_at_5 = chunk.get_block(8, 5, 8)
        assert block_at_5 is not None
        assert block_at_5.material in (
            Material.STONE, Material.IRON_ORE, Material.GOLD_ORE
        )

    def test_dirt_layers_present(self, generator: ChunkGenerator) -> None:
        """Each column has dirt layers below the surface."""
        chunk = generator.generate_chunk(0, 0)
        # Find the surface for a given column and verify dirt below it
        x, z = 8, 8
        surface_y = None
        for y in range(CHUNK_HEIGHT - 1, 0, -1):
            block = chunk.get_block(x, y, z)
            if block is not None:
                surface_y = y
                break

        assert surface_y is not None
        # Surface should be grass (DIRT with metadata)
        surface_block = chunk.get_block(x, surface_y, z)
        assert surface_block.material == Material.DIRT
        assert surface_block.metadata.get("grass") is True

        # Below surface should be plain dirt (no grass metadata)
        if surface_y > 1:
            dirt_block = chunk.get_block(x, surface_y - 1, z)
            assert dirt_block is not None
            assert dirt_block.material == Material.DIRT
            assert "grass" not in dirt_block.metadata

    def test_grass_metadata_on_surface(self, generator: ChunkGenerator) -> None:
        """The top block of each column has grass metadata."""
        chunk = generator.generate_chunk(2, 3)
        # Check multiple columns
        for x in [0, 7, 15]:
            for z in [0, 7, 15]:
                surface_y = None
                for y in range(CHUNK_HEIGHT - 1, 0, -1):
                    block = chunk.get_block(x, y, z)
                    if block is not None:
                        surface_y = y
                        break
                assert surface_y is not None
                block = chunk.get_block(x, surface_y, z)
                assert block.material == Material.DIRT
                assert block.metadata.get("grass") is True

    def test_air_above_surface(self, generator: ChunkGenerator) -> None:
        """Blocks above the surface are None (air)."""
        chunk = generator.generate_chunk(0, 0)
        # High Y values should be air
        for x in range(CHUNK_WIDTH):
            for z in range(CHUNK_DEPTH):
                block = chunk.get_block(x, CHUNK_HEIGHT - 1, z)
                assert block is None


# ---------------------------------------------------------------------------
# Heightmap tests
# ---------------------------------------------------------------------------


class TestHeightmap:
    """Tests for noise-based heightmap generation."""

    def test_surface_within_expected_range(self, generator: ChunkGenerator) -> None:
        """Surface levels stay within base ± amplitude."""
        chunk = generator.generate_chunk(0, 0)
        min_expected = max(1, BASE_HEIGHT - HEIGHT_AMPLITUDE)
        max_expected = min(CHUNK_HEIGHT - 1, BASE_HEIGHT + HEIGHT_AMPLITUDE)

        for x in range(CHUNK_WIDTH):
            for z in range(CHUNK_DEPTH):
                surface_y = None
                for y in range(CHUNK_HEIGHT - 1, 0, -1):
                    block = chunk.get_block(x, y, z)
                    if block is not None:
                        surface_y = y
                        break
                assert surface_y is not None
                assert min_expected <= surface_y <= max_expected, (
                    f"Surface at ({x},{z}) is {surface_y}, "
                    f"expected [{min_expected}, {max_expected}]"
                )

    def test_surface_varies_across_chunk(self, generator: ChunkGenerator) -> None:
        """Surface level is not perfectly flat (noise introduces variation)."""
        chunk = generator.generate_chunk(0, 0)
        surfaces = set()
        for x in range(CHUNK_WIDTH):
            for z in range(CHUNK_DEPTH):
                for y in range(CHUNK_HEIGHT - 1, 0, -1):
                    block = chunk.get_block(x, y, z)
                    if block is not None:
                        surfaces.add(y)
                        break

        # With 16x16 columns and noise, there should be multiple heights
        assert len(surfaces) > 1


# ---------------------------------------------------------------------------
# Ore distribution tests
# ---------------------------------------------------------------------------


class TestOreDistribution:
    """Tests for ore placement within the terrain."""

    def test_ores_present_in_stone_layers(self) -> None:
        """Ore blocks appear somewhere in the generated terrain."""
        # Use a generator and check multiple chunks to find ores
        gen = ChunkGenerator(seed=7777)
        found_iron = False
        found_gold = False

        for cx in range(4):
            for cz in range(4):
                chunk = gen.generate_chunk(cx, cz)
                for x in range(CHUNK_WIDTH):
                    for z in range(CHUNK_DEPTH):
                        for y in range(1, 55):
                            block = chunk.get_block(x, y, z)
                            if block is not None:
                                if block.material == Material.IRON_ORE:
                                    found_iron = True
                                elif block.material == Material.GOLD_ORE:
                                    found_gold = True
                            if found_iron and found_gold:
                                return

        assert found_iron, "No IRON_ORE found in generated terrain"
        assert found_gold, "No GOLD_ORE found in generated terrain"

    def test_iron_ore_within_depth_range(self) -> None:
        """IRON_ORE only appears within its defined depth range."""
        gen = ChunkGenerator(seed=42)
        chunk = gen.generate_chunk(0, 0)

        for x in range(CHUNK_WIDTH):
            for z in range(CHUNK_DEPTH):
                for y in range(CHUNK_HEIGHT):
                    block = chunk.get_block(x, y, z)
                    if block is not None and block.material == Material.IRON_ORE:
                        assert IRON_ORE_MIN_Y <= y <= IRON_ORE_MAX_Y, (
                            f"IRON_ORE at y={y} outside range "
                            f"[{IRON_ORE_MIN_Y}, {IRON_ORE_MAX_Y}]"
                        )

    def test_gold_ore_within_depth_range(self) -> None:
        """GOLD_ORE only appears within its defined depth range."""
        gen = ChunkGenerator(seed=42)
        chunk = gen.generate_chunk(0, 0)

        for x in range(CHUNK_WIDTH):
            for z in range(CHUNK_DEPTH):
                for y in range(CHUNK_HEIGHT):
                    block = chunk.get_block(x, y, z)
                    if block is not None and block.material == Material.GOLD_ORE:
                        assert GOLD_ORE_MIN_Y <= y <= GOLD_ORE_MAX_Y, (
                            f"GOLD_ORE at y={y} outside range "
                            f"[{GOLD_ORE_MIN_Y}, {GOLD_ORE_MAX_Y}]"
                        )

    def test_no_ore_in_dirt_or_surface(self) -> None:
        """Ores should never replace dirt or grass layers."""
        gen = ChunkGenerator(seed=42)
        chunk = gen.generate_chunk(0, 0)

        for x in range(CHUNK_WIDTH):
            for z in range(CHUNK_DEPTH):
                # Find surface
                surface_y = None
                for y in range(CHUNK_HEIGHT - 1, 0, -1):
                    block = chunk.get_block(x, y, z)
                    if block is not None:
                        surface_y = y
                        break
                if surface_y is None:
                    continue

                # Check top DIRT_LAYER_DEPTH layers are not ore
                for y in range(
                    max(1, surface_y - DIRT_LAYER_DEPTH + 1), surface_y + 1
                ):
                    block = chunk.get_block(x, y, z)
                    if block is not None:
                        assert block.material not in (
                            Material.IRON_ORE, Material.GOLD_ORE
                        ), f"Ore found at y={y} in dirt/grass layer"


# ---------------------------------------------------------------------------
# Integration with ChunkManager
# ---------------------------------------------------------------------------


class TestChunkManagerIntegration:
    """Tests that ChunkManager correctly delegates to ChunkGenerator."""

    @pytest.fixture
    def tmp_saves(self, tmp_path) -> str:
        saves = tmp_path / "saves"
        saves.mkdir()
        return str(saves)

    @pytest.fixture
    def bus(self):
        from src.core.event_bus import EventBus
        return EventBus()

    def test_manager_uses_generator(self, bus, tmp_saves) -> None:
        """ChunkManager delegates to ChunkGenerator when provided."""
        from src.terrain.chunk_manager import ChunkManager

        gen = ChunkGenerator(seed=42)
        manager = ChunkManager(
            event_bus=bus, cache_size=4, saves_dir=tmp_saves, generator=gen
        )
        chunk = manager.load_chunk(0, 0)

        # Should have noise-based terrain (bedrock at y=0)
        assert chunk.get_block(0, 0, 0).material == Material.OBSIDIAN
        # Surface should have grass metadata somewhere
        found_grass = False
        for y in range(CHUNK_HEIGHT - 1, 0, -1):
            block = chunk.get_block(8, y, 8)
            if block is not None:
                if block.metadata.get("grass"):
                    found_grass = True
                break
        assert found_grass

    def test_manager_without_generator_uses_default(self, bus, tmp_saves) -> None:
        """ChunkManager without generator uses flat terrain fallback."""
        from src.terrain.chunk_manager import ChunkManager

        manager = ChunkManager(
            event_bus=bus, cache_size=4, saves_dir=tmp_saves
        )
        chunk = manager.load_chunk(0, 0)

        # Default flat terrain: y=62 should be DIRT
        block = chunk.get_block(0, 62, 0)
        assert block is not None
        assert block.material == Material.DIRT
