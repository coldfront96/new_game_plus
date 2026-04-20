"""
src/ai_sim/pathfinding.py
--------------------------
A* pathfinding optimized for 3D voxel grids in the New Game Plus engine.

The :class:`VoxelPathfinder` navigates entities through the game world by
interfacing with the :class:`~src.terrain.chunk_manager.ChunkManager` to
verify walkability based on ``is_solid`` properties.

Navigation Rules:
    * Entities require **2 blocks** of vertical clearance (head + body).
    * Entities can navigate elevation changes of **±1 block** (step up/down).
    * Diagonal movement in XZ is permitted (8-connected horizontal).
    * Solid blocks are impassable; only air (None) or non-solid blocks
      allow entity passage.

Usage::

    from src.ai_sim.pathfinding import VoxelPathfinder
    from src.terrain.chunk_manager import ChunkManager
    from src.core.event_bus import EventBus

    bus = EventBus()
    cm = ChunkManager(event_bus=bus)
    pathfinder = VoxelPathfinder(chunk_manager=cm)

    path = pathfinder.find_path(start=(0, 65, 0), goal=(5, 65, 3))
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from src.terrain.chunk_manager import ChunkManager


# Type alias for 3D integer coordinates
Coord3 = Tuple[int, int, int]

# Maximum number of nodes to expand before giving up (prevents runaway searches)
_MAX_ITERATIONS: int = 10_000

# Height clearance required for entity passage (body + head)
_ENTITY_HEIGHT: int = 2

# Maximum step height for elevation changes
_MAX_STEP: int = 1

# 8-connected horizontal neighbours (dx, dz)
_HORIZONTAL_NEIGHBOURS: List[Tuple[int, int]] = [
    (1, 0), (-1, 0), (0, 1), (0, -1),
    (1, 1), (1, -1), (-1, 1), (-1, -1),
]


@dataclass(slots=True)
class PathNode:
    """A* search node for priority queue ordering.

    Attributes:
        f_score:  Estimated total cost (g + h).
        g_score:  Actual cost from start to this node.
        position: The 3D voxel coordinate of this node.
        parent:   The parent node's coordinate for path reconstruction.
    """

    f_score: float
    g_score: float
    position: Coord3
    parent: Optional[Coord3] = None

    def __lt__(self, other: "PathNode") -> bool:
        return self.f_score < other.f_score


@dataclass(slots=True)
class PathResult:
    """Result of a pathfinding query.

    Attributes:
        path:       Ordered list of (x, y, z) voxel coordinates from start
                    to goal (inclusive). Empty if no path found.
        success:    ``True`` if a valid path was found.
        nodes_explored: Number of nodes expanded during the search.
    """

    path: List[Coord3]
    success: bool
    nodes_explored: int


@dataclass(slots=True)
class VoxelPathfinder:
    """A* pathfinder for 3D voxel navigation.

    Interfaces with the :class:`ChunkManager` to query block solidity and
    computes walkable paths respecting elevation rules and clearance.

    Attributes:
        chunk_manager:  The chunk manager providing world block data.
        max_iterations: Maximum nodes to expand before aborting.
    """

    chunk_manager: ChunkManager
    max_iterations: int = _MAX_ITERATIONS

    def find_path(
        self,
        start: Coord3,
        goal: Coord3,
        max_distance: Optional[int] = None,
    ) -> PathResult:
        """Find a path from *start* to *goal* using A*.

        Args:
            start: Starting (x, y, z) voxel coordinate (entity feet position).
            goal:  Target (x, y, z) voxel coordinate.
            max_distance: Optional maximum Manhattan distance to search. If the
                          goal is further away, the search is skipped.

        Returns:
            A :class:`PathResult` with the path and metadata.
        """
        if start == goal:
            return PathResult(path=[start], success=True, nodes_explored=0)

        # Early reject if goal is clearly unreachable
        if max_distance is not None:
            dist = abs(goal[0] - start[0]) + abs(goal[1] - start[1]) + abs(goal[2] - start[2])
            if dist > max_distance:
                return PathResult(path=[], success=False, nodes_explored=0)

        # Validate start and goal are walkable
        if not self._is_walkable(start):
            return PathResult(path=[], success=False, nodes_explored=0)
        if not self._is_walkable(goal):
            return PathResult(path=[], success=False, nodes_explored=0)

        # A* search
        open_heap: List[PathNode] = []
        start_node = PathNode(
            f_score=self._heuristic(start, goal),
            g_score=0.0,
            position=start,
            parent=None,
        )
        heapq.heappush(open_heap, start_node)

        # g_scores and parent tracking
        g_scores: Dict[Coord3, float] = {start: 0.0}
        came_from: Dict[Coord3, Optional[Coord3]] = {start: None}
        closed: set = set()
        nodes_explored = 0

        while open_heap and nodes_explored < self.max_iterations:
            current = heapq.heappop(open_heap)
            pos = current.position

            if pos in closed:
                continue
            closed.add(pos)
            nodes_explored += 1

            # Goal reached
            if pos == goal:
                path = self._reconstruct_path(came_from, goal)
                return PathResult(path=path, success=True, nodes_explored=nodes_explored)

            # Expand neighbours
            for neighbour, move_cost in self._get_neighbours(pos):
                if neighbour in closed:
                    continue

                tentative_g = g_scores[pos] + move_cost

                if tentative_g < g_scores.get(neighbour, math.inf):
                    g_scores[neighbour] = tentative_g
                    came_from[neighbour] = pos
                    f_score = tentative_g + self._heuristic(neighbour, goal)
                    heapq.heappush(
                        open_heap,
                        PathNode(
                            f_score=f_score,
                            g_score=tentative_g,
                            position=neighbour,
                            parent=pos,
                        ),
                    )

        # No path found within iteration budget
        return PathResult(path=[], success=False, nodes_explored=nodes_explored)

    def _is_walkable(self, pos: Coord3) -> bool:
        """Check if an entity can stand at *pos* (feet position).

        Requirements:
            1. The block at feet level (pos.y) must be non-solid (air/passable).
            2. The block at head level (pos.y + 1) must be non-solid.
            3. The block beneath (pos.y - 1) must be solid (ground support).
        """
        x, y, z = pos
        # Must have ground support beneath feet
        if y <= 0:
            return False
        ground = self.chunk_manager.get_block_world(x, y - 1, z)
        if ground is None or not ground.is_solid:
            return False
        # Feet position must be passable (air or non-solid)
        feet_block = self.chunk_manager.get_block_world(x, y, z)
        if feet_block is not None and feet_block.is_solid:
            return False
        # Head position must be passable
        head_block = self.chunk_manager.get_block_world(x, y + 1, z)
        if head_block is not None and head_block.is_solid:
            return False
        return True

    def _get_neighbours(self, pos: Coord3) -> List[Tuple[Coord3, float]]:
        """Generate valid walkable neighbours from *pos*.

        Considers 8-connected horizontal movement at the same elevation,
        plus step-up (+1) and step-down (-1) for each horizontal direction.

        Returns:
            List of (neighbour_coord, movement_cost) tuples.
        """
        x, y, z = pos
        neighbours: List[Tuple[Coord3, float]] = []

        for dx, dz in _HORIZONTAL_NEIGHBOURS:
            nx, nz = x + dx, z + dz
            is_diagonal = dx != 0 and dz != 0
            base_cost = 1.414 if is_diagonal else 1.0

            # Same-level movement
            candidate = (nx, y, nz)
            if self._is_walkable(candidate):
                neighbours.append((candidate, base_cost))
                continue

            # Step up (+1): can we stand one block higher?
            step_up = (nx, y + 1, nz)
            if y + 1 <= 254 and self._is_walkable(step_up):
                # Must also check that the space above current pos is clear
                # for the step-up transition (entity needs clearance at y+2)
                above_head = self.chunk_manager.get_block_world(x, y + 2, z)
                if above_head is None or not above_head.is_solid:
                    neighbours.append((step_up, base_cost + 0.5))
                    continue

            # Step down (-1): can we stand one block lower?
            step_down = (nx, y - 1, nz)
            if y - 1 > 0 and self._is_walkable(step_down):
                neighbours.append((step_down, base_cost + 0.5))

        return neighbours

    @staticmethod
    def _heuristic(a: Coord3, b: Coord3) -> float:
        """Octile distance heuristic for 3D grid (admissible for A*).

        Uses the 3D extension of the octile distance which accounts for
        diagonal movement being sqrt(2) cost.
        """
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        dz = abs(a[2] - b[2])
        # Sort so that the smallest is used for diagonal steps
        dmin = min(dx, dz)
        dmax = max(dx, dz)
        return dmin * 1.414 + (dmax - dmin) + dy

    @staticmethod
    def _reconstruct_path(
        came_from: Dict[Coord3, Optional[Coord3]], goal: Coord3
    ) -> List[Coord3]:
        """Trace back from goal to start using the came_from map."""
        path: List[Coord3] = []
        current: Optional[Coord3] = goal
        while current is not None:
            path.append(current)
            current = came_from[current]
        path.reverse()
        return path
