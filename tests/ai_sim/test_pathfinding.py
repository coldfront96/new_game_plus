"""
tests/ai_sim/test_pathfinding.py
---------------------------------
Unit tests for src.ai_sim.pathfinding (VoxelPathfinder).
"""

import pytest

from src.ai_sim.pathfinding import PathResult, VoxelPathfinder
from src.core.event_bus import EventBus
from src.terrain.block import Block, Material
from src.terrain.chunk_manager import ChunkManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def bus():
    return EventBus()


@pytest.fixture
def chunk_manager(bus, tmp_path):
    """ChunkManager with flat terrain (surface at y=64, dirt)."""
    cm = ChunkManager(event_bus=bus, cache_size=16, saves_dir=str(tmp_path / "saves"))
    return cm


@pytest.fixture
def pathfinder(chunk_manager):
    return VoxelPathfinder(chunk_manager=chunk_manager)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _set_solid(cm: ChunkManager, x: int, y: int, z: int) -> None:
    """Place a solid stone block at (x, y, z)."""
    cm.set_block_world(x, y, z, Block(block_id=Material.STONE.value, material=Material.STONE))


def _clear_block(cm: ChunkManager, x: int, y: int, z: int) -> None:
    """Remove the block at (x, y, z), making it air."""
    cm.set_block_world(x, y, z, None)


# ---------------------------------------------------------------------------
# Tests — basic pathfinding
# ---------------------------------------------------------------------------

class TestVoxelPathfinderBasic:
    """Tests for basic A* pathfinding functionality."""

    def test_trivial_path_same_position(self, pathfinder):
        """Start == goal should return a single-node path immediately."""
        # Flat terrain: surface at y=64, walkable at y=65
        result = pathfinder.find_path((0, 65, 0), (0, 65, 0))
        assert result.success is True
        assert result.path == [(0, 65, 0)]
        assert result.nodes_explored == 0

    def test_straight_line_path(self, pathfinder, chunk_manager):
        """Pathfind in a straight line along X axis on flat terrain."""
        # Default flat terrain: ground at y=64, walking at y=65
        # y=65 is air (walkable), y=64 is dirt (ground)
        result = pathfinder.find_path((0, 65, 0), (3, 65, 0))
        assert result.success is True
        assert result.path[0] == (0, 65, 0)
        assert result.path[-1] == (3, 65, 0)
        assert len(result.path) >= 2  # At least start and end

    def test_diagonal_path(self, pathfinder):
        """Pathfind diagonally in XZ on flat terrain."""
        result = pathfinder.find_path((0, 65, 0), (2, 65, 2))
        assert result.success is True
        assert result.path[0] == (0, 65, 0)
        assert result.path[-1] == (2, 65, 2)

    def test_no_path_blocked(self, pathfinder, chunk_manager):
        """No path when goal is completely surrounded by solid blocks."""
        # Block all approaches to (5, 65, 0) by filling feet and head level
        for dx in [-1, 0, 1]:
            for dz in [-1, 0, 1]:
                if dx == 0 and dz == 0:
                    continue
                _set_solid(chunk_manager, 5 + dx, 65, 0 + dz)
                _set_solid(chunk_manager, 5 + dx, 66, 0 + dz)
        # Also block directly at feet and head at target (make it unwalkable)
        _set_solid(chunk_manager, 5, 65, 0)

        result = pathfinder.find_path((0, 65, 0), (5, 65, 0))
        assert result.success is False
        assert result.path == []

    def test_unwalkable_start(self, pathfinder, chunk_manager):
        """Return failure if start position is not walkable."""
        # Place a solid block at the start feet position
        _set_solid(chunk_manager, 0, 65, 0)
        result = pathfinder.find_path((0, 65, 0), (3, 65, 0))
        assert result.success is False

    def test_unwalkable_goal(self, pathfinder, chunk_manager):
        """Return failure if goal position is not walkable."""
        # Place a solid block at the goal feet position
        _set_solid(chunk_manager, 3, 65, 0)
        result = pathfinder.find_path((0, 65, 0), (3, 65, 0))
        assert result.success is False


# ---------------------------------------------------------------------------
# Tests — elevation changes
# ---------------------------------------------------------------------------

class TestVoxelPathfinderElevation:
    """Tests for step-up and step-down navigation."""

    def test_step_up_one_block(self, pathfinder, chunk_manager):
        """Entity can step up +1 block when path requires elevation change."""
        # Create a step: place solid at y=65 for x=2 (making ground at 65, walk at 66)
        _set_solid(chunk_manager, 2, 65, 0)
        # Clear above so entity can stand at y=66
        _clear_block(chunk_manager, 2, 66, 0)
        _clear_block(chunk_manager, 2, 67, 0)

        result = pathfinder.find_path((0, 65, 0), (2, 66, 0))
        assert result.success is True
        assert result.path[-1] == (2, 66, 0)

    def test_step_down_one_block(self, pathfinder, chunk_manager):
        """Entity can step down -1 block."""
        # Remove ground at y=64 for x=2 (so ground becomes y=63, walk at y=64)
        _clear_block(chunk_manager, 2, 64, 0)
        # Make sure y=63 is solid (it's stone from generation)
        # Default generation: y=1-59 stone, y=60-64 dirt
        # So clearing y=64 at x=2 makes ground at y=63 (dirt), walk at y=64

        result = pathfinder.find_path((0, 65, 0), (2, 64, 0))
        assert result.success is True
        assert result.path[-1] == (2, 64, 0)

    def test_cannot_step_two_blocks(self, pathfinder, chunk_manager):
        """Entity cannot step up 2 blocks (exceeds max_step=1).

        We create an isolated elevated platform that requires a 2-block
        jump to reach, with walls preventing any approach route.
        """
        # Create a 2-block-high wall at x=1 for all z in [-1, 0, 1]
        for dz in range(-1, 2):
            _set_solid(chunk_manager, 1, 65, dz)
            _set_solid(chunk_manager, 1, 66, dz)

        # Place ground at (2, 66, 0) so walkable at (2, 67, 0) requires
        # a 2-block step from y=65 to y=67
        _set_solid(chunk_manager, 2, 65, 0)
        _set_solid(chunk_manager, 2, 66, 0)
        _clear_block(chunk_manager, 2, 67, 0)
        _clear_block(chunk_manager, 2, 68, 0)

        # Also wall off approaches from the sides at x=2
        for dz in [-1, 1]:
            _set_solid(chunk_manager, 2, 65, dz)
            _set_solid(chunk_manager, 2, 66, dz)
            _set_solid(chunk_manager, 2, 67, dz)
            _set_solid(chunk_manager, 2, 68, dz)
        # Wall off x=3 approach too
        for dz in range(-1, 2):
            _set_solid(chunk_manager, 3, 65, dz)
            _set_solid(chunk_manager, 3, 66, dz)
            _set_solid(chunk_manager, 3, 67, dz)
            _set_solid(chunk_manager, 3, 68, dz)

        # Use a low max_iterations to prevent excessive search on open terrain
        pathfinder.max_iterations = 500
        result = pathfinder.find_path((0, 65, 0), (2, 67, 0))
        assert result.success is False


# ---------------------------------------------------------------------------
# Tests — clearance
# ---------------------------------------------------------------------------

class TestVoxelPathfinderClearance:
    """Tests for 2-block vertical clearance requirement."""

    def test_blocked_at_head_level(self, pathfinder, chunk_manager):
        """Entity cannot pass if head level (y+1) is blocked."""
        # Block head height (y=66) along the path at x=1
        _set_solid(chunk_manager, 1, 66, 0)

        # The entity needs to go through x=1 but head is blocked
        # Build walls around to force through x=1
        _set_solid(chunk_manager, 1, 65, 1)
        _set_solid(chunk_manager, 1, 66, 1)
        _set_solid(chunk_manager, 1, 65, -1)
        _set_solid(chunk_manager, 1, 66, -1)

        result = pathfinder.find_path((0, 65, 0), (2, 65, 0))
        # Should still find a path going around or fail depending on geometry
        # Since we blocked z=-1 and z=1 the path must go through x=1, z=0
        # which has head blocked, so try to check path doesn't include blocked node
        if result.success:
            assert (1, 65, 0) not in result.path

    def test_full_clearance_allows_passage(self, pathfinder, chunk_manager):
        """Entity can pass when both feet and head levels are clear."""
        # Default terrain has air at y=65 and y=66, ground at y=64
        result = pathfinder.find_path((0, 65, 0), (5, 65, 0))
        assert result.success is True


# ---------------------------------------------------------------------------
# Tests — max_distance parameter
# ---------------------------------------------------------------------------

class TestVoxelPathfinderDistance:
    """Tests for the max_distance early-exit parameter."""

    def test_within_max_distance(self, pathfinder):
        """Path is found when goal is within max_distance."""
        result = pathfinder.find_path((0, 65, 0), (2, 65, 0), max_distance=10)
        assert result.success is True

    def test_exceeds_max_distance(self, pathfinder):
        """No search attempted when goal exceeds max_distance."""
        result = pathfinder.find_path((0, 65, 0), (100, 65, 0), max_distance=5)
        assert result.success is False
        assert result.nodes_explored == 0


# ---------------------------------------------------------------------------
# Tests — PathResult dataclass
# ---------------------------------------------------------------------------

class TestPathResult:
    """Tests for PathResult data structure."""

    def test_slots_optimization(self):
        """PathResult uses __slots__ for memory efficiency."""
        assert hasattr(PathResult, "__slots__")

    def test_empty_path_on_failure(self):
        """Failed results have an empty path list."""
        result = PathResult(path=[], success=False, nodes_explored=42)
        assert result.path == []
        assert result.success is False
        assert result.nodes_explored == 42


# ---------------------------------------------------------------------------
# Tests — integration with Character35e voxel_speed
# ---------------------------------------------------------------------------

class TestVoxelSpeedIntegration:
    """Tests confirming the ruleset integration with pathfinding."""

    def test_default_speed_30ft_is_6_blocks(self):
        """Default base_speed of 30ft converts to 6 voxel blocks."""
        from src.rules_engine.character_35e import Character35e

        char = Character35e(name="Test", base_speed=30)
        assert char.voxel_speed == 6

    def test_dwarf_speed_20ft_is_4_blocks(self):
        """Dwarf base_speed of 20ft converts to 4 voxel blocks."""
        from src.rules_engine.character_35e import Character35e

        char = Character35e(name="Dwarf", base_speed=20)
        assert char.voxel_speed == 4

    def test_barbarian_fast_movement_40ft(self):
        """Barbarian fast movement 40ft converts to 8 voxel blocks."""
        from src.rules_engine.character_35e import Character35e

        char = Character35e(name="Barb", char_class="Barbarian", base_speed=40)
        assert char.voxel_speed == 8

    def test_path_length_respects_speed(self, pathfinder):
        """Path found should be traversable within speed budget."""
        from src.rules_engine.character_35e import Character35e

        char = Character35e(name="Walker", base_speed=30)
        result = pathfinder.find_path((0, 65, 0), (3, 65, 0))
        assert result.success is True
        # Path length minus 1 gives number of steps needed
        steps_needed = len(result.path) - 1
        # A character with voxel_speed=6 can traverse this in one move
        assert steps_needed <= char.voxel_speed
