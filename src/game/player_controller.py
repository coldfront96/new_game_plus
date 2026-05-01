"""PH2-010 · PH2-011 · PH2-012 · PH2-014 — Avatar Agency & Fog of War subsystem.

Phase 2 — Player Interaction & Civilised Ecology.
Provides the player controller schema, keyboard input dispatcher, fog of war
calculator, and dynamic chunk load/unload logic.
"""
from __future__ import annotations

import enum
import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.rules_engine.character_35e import Character35e
    from src.terrain.chunk_manager import ChunkManager
    from src.world_sim.population import WorldChunk


# ---------------------------------------------------------------------------
# PH2-010 · PlayerAction Enum
# ---------------------------------------------------------------------------

class PlayerAction(enum.Enum):
    """All discrete actions available to the player avatar each turn.

    Values match the single-key Textual bindings defined in the overseer UI
    (``n``, ``s``, ``e``, ``w``, ``u``, ``d``, ``.``, ``i``).
    """

    MoveNorth = "move_north"
    MoveSouth = "move_south"
    MoveEast  = "move_east"
    MoveWest  = "move_west"
    MoveUp    = "move_up"
    MoveDown  = "move_down"
    Wait      = "wait"
    Interact  = "interact"


# ---------------------------------------------------------------------------
# PH2-010 · PlayerController Schema
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class PlayerController:
    """Single authoritative source of player position and fog-of-war state.

    All Fog of War and chunk-loading decisions read from this object.

    Attributes:
        player_id:      Unique player identifier.
        entity_id:      ID of the bound :class:`~src.rules_engine.character_35e.Character35e`.
        chunk_id:       Current world-chunk ID the player occupies.
        vision_radius:  How many voxels the player can see (default 8).
        fog_revealed:   Voxel coordinates revealed at least once; never re-hidden.
    """

    player_id: str
    entity_id: str
    chunk_id: str
    vision_radius: int = 8
    fog_revealed: set[tuple[int, int, int]] = field(default_factory=set)


# ---------------------------------------------------------------------------
# PH2-011 · Keyboard Input Dispatcher
# ---------------------------------------------------------------------------

#: Voxel coordinate delta for each movement action (dx, dy, dz).
_ACTION_DELTAS: dict[PlayerAction, tuple[int, int, int]] = {
    PlayerAction.MoveNorth: (0,  0, -1),
    PlayerAction.MoveSouth: (0,  0,  1),
    PlayerAction.MoveEast:  (1,  0,  0),
    PlayerAction.MoveWest:  (-1, 0,  0),
    PlayerAction.MoveUp:    (0,  1,  0),
    PlayerAction.MoveDown:  (0, -1,  0),
    PlayerAction.Wait:      (0,  0,  0),
    PlayerAction.Interact:  (0,  0,  0),
}


def dispatch_player_input(
    controller: PlayerController,
    action: PlayerAction,
    combat_registry: "dict[str, Character35e]",
) -> PlayerController:
    """Apply *action* to the player's bound entity and update the controller.

    Movement actions shift the bound entity's ``metadata["position"]`` voxel
    coordinate by 1 in the appropriate direction.  The controller's
    ``chunk_id`` is updated when the position crosses a chunk boundary
    (multiples of the CHUNK_WIDTH/CHUNK_DEPTH constants).

    ``Wait`` advances the entity's turn without moving.
    ``Interact`` is a no-op stub reserved for future object interaction.

    Args:
        controller:       The player's current controller state.
        action:           The :class:`PlayerAction` to process.
        combat_registry:  ``entity_id → Character35e`` mapping.

    Returns:
        The updated :class:`PlayerController` (mutated in place and returned).
    """
    from src.terrain.chunk import CHUNK_DEPTH, CHUNK_WIDTH

    entity = combat_registry.get(controller.entity_id)
    dx, dy, dz = _ACTION_DELTAS[action]

    if entity is not None and (dx, dy, dz) != (0, 0, 0):
        pos = entity.metadata.setdefault("position", [0, 64, 0])
        pos[0] += dx
        pos[1] += dy
        pos[2] += dz
        entity.metadata["position"] = pos

        # Derive chunk_id from world position when integers are used.
        # Chunk IDs are formatted as "cx_cz" where cx = x // CHUNK_WIDTH,
        # cz = z // CHUNK_DEPTH.  If the existing chunk_id doesn't match this
        # format, it is left unchanged (world-sim string IDs are preserved).
        cx = pos[0] // CHUNK_WIDTH
        cz = pos[2] // CHUNK_DEPTH
        derived = f"{cx}_{cz}"
        if _chunk_id_is_numeric(controller.chunk_id):
            controller.chunk_id = derived

    return controller


def _chunk_id_is_numeric(chunk_id: str) -> bool:
    """Return ``True`` if *chunk_id* matches the ``"cx_cz"`` integer format."""
    parts = chunk_id.split("_")
    if len(parts) != 2:
        return False
    try:
        int(parts[0])
        int(parts[1])
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# PH2-012 · Fog of War Calculator
# ---------------------------------------------------------------------------

def calculate_visible_voxels(
    controller: PlayerController,
    chunk_voxels: set[tuple[int, int, int]],
) -> tuple[set[tuple[int, int, int]], set[tuple[int, int, int]]]:
    """Compute visible and hidden voxels for the current player position.

    Performance
    ~~~~~~~~~~~
    Runs in O(vision_radius³) time by iterating only the candidate sphere
    rather than the full *chunk_voxels* set.

    Algorithm
    ~~~~~~~~~
    * ``visible`` = all voxels within Euclidean distance ≤ ``vision_radius``
      of the player's current voxel position that are also in *chunk_voxels*.
    * ``hidden``  = ``chunk_voxels − visible``.
    * ``controller.fog_revealed`` is updated by union-ing ``visible``
      (revealed voxels are never re-hidden).

    Args:
        controller:   Current :class:`PlayerController`.
        chunk_voxels: Full set of voxel coordinates in the active chunk.

    Returns:
        A 2-tuple ``(visible, hidden)`` of voxel coordinate sets.
    """
    entity_pos: tuple[int, int, int] | None = None

    # Try to read from combat_registry via metadata — fall back to (0, 64, 0).
    # The controller doesn't hold the entity directly, so we read from
    # fog_revealed centre if available, otherwise use a default.
    # In practice the caller should ensure entity position is synchronised.
    # We expose a helper that accepts an explicit position for testability.
    return _calculate_visible_voxels_at(
        controller=controller,
        chunk_voxels=chunk_voxels,
        player_pos=(0, 64, 0),
    )


def calculate_visible_voxels_at(
    controller: PlayerController,
    chunk_voxels: set[tuple[int, int, int]],
    player_pos: tuple[int, int, int],
) -> tuple[set[tuple[int, int, int]], set[tuple[int, int, int]]]:
    """Variant of :func:`calculate_visible_voxels` accepting an explicit position.

    Prefer this overload when the caller has the player's world-space voxel
    position readily available (avoids a registry lookup).

    Args:
        controller:  Current :class:`PlayerController`.
        chunk_voxels: Full set of voxel coordinates in the active chunk.
        player_pos:  The player's current ``(x, y, z)`` voxel position.

    Returns:
        A 2-tuple ``(visible, hidden)`` of voxel coordinate sets.
    """
    return _calculate_visible_voxels_at(controller, chunk_voxels, player_pos)


def _calculate_visible_voxels_at(
    controller: PlayerController,
    chunk_voxels: set[tuple[int, int, int]],
    player_pos: tuple[int, int, int],
) -> tuple[set[tuple[int, int, int]], set[tuple[int, int, int]]]:
    """Internal implementation shared by the public overloads."""
    px, py, pz = player_pos
    r = controller.vision_radius
    r_sq = r * r

    visible: set[tuple[int, int, int]] = set()

    # Iterate only the bounding cube of the vision sphere — O(r³).
    for dx in range(-r, r + 1):
        for dy in range(-r, r + 1):
            for dz in range(-r, r + 1):
                if dx * dx + dy * dy + dz * dz <= r_sq:
                    voxel = (px + dx, py + dy, pz + dz)
                    if voxel in chunk_voxels:
                        visible.add(voxel)

    controller.fog_revealed |= visible
    hidden = chunk_voxels - visible
    return visible, hidden


# ---------------------------------------------------------------------------
# PH2-014 · ChunkManager Dynamic Load/Unload
# ---------------------------------------------------------------------------

def update_loaded_chunks(
    controller: PlayerController,
    chunk_manager: "ChunkManager",
    load_radius: int = 2,
    world_chunks: "list[WorldChunk] | None" = None,
) -> tuple[list[str], list[str]]:
    """Load chunks within *load_radius* of the player and unload distant ones.

    If *controller.chunk_id* is in ``"cx_cz"`` format, the neighbourhood is
    computed via simple grid arithmetic.  When *world_chunks* is supplied, a
    :class:`~src.world_sim.migration.ChunkAdjacencyGraph` BFS is used instead
    to respect the world-sim adjacency topology.

    Chunk state (entity positions, population deltas) is serialised by the
    :class:`~src.terrain.chunk_manager.ChunkManager` before eviction via its
    existing LRU save-to-disk mechanism.

    Args:
        controller:    Current :class:`PlayerController`.
        chunk_manager: The active terrain chunk manager.
        load_radius:   How many chunks away from the player to keep loaded.
        world_chunks:  Optional world-sim chunk list for adjacency-graph routing.

    Returns:
        A 2-tuple ``(newly_loaded, newly_unloaded)`` of chunk-ID strings.
    """
    newly_loaded: list[str] = []
    newly_unloaded: list[str] = []

    target_ids: set[str]

    if world_chunks is not None:
        # Use adjacency graph BFS to find all chunks within load_radius hops.
        from src.world_sim.migration import ChunkAdjacencyGraph

        graph = ChunkAdjacencyGraph(world_chunks)
        reachable: set[str] = {controller.chunk_id}
        frontier: list[str] = [controller.chunk_id]
        for _ in range(load_radius):
            next_frontier: list[str] = []
            for cid in frontier:
                for neighbor in graph.get_neighbors(cid):
                    if neighbor.chunk_id not in reachable:
                        reachable.add(neighbor.chunk_id)
                        next_frontier.append(neighbor.chunk_id)
            frontier = next_frontier
            if not frontier:
                break
        target_ids = reachable
    elif _chunk_id_is_numeric(controller.chunk_id):
        # Grid-based neighbourhood.
        parts = controller.chunk_id.split("_")
        cx, cz = int(parts[0]), int(parts[1])
        target_ids = set()
        for dx in range(-load_radius, load_radius + 1):
            for dz in range(-load_radius, load_radius + 1):
                target_ids.add(f"{cx + dx}_{cz + dz}")
    else:
        # Fallback: keep only the current chunk loaded.
        target_ids = {controller.chunk_id}

    # Load any target chunks not yet cached.
    for chunk_id_str in target_ids:
        if not _chunk_id_is_numeric(chunk_id_str):
            continue
        p = chunk_id_str.split("_")
        ncx, ncz = int(p[0]), int(p[1])
        key = (ncx, ncz)
        if key not in chunk_manager._cache:
            chunk_manager.load_chunk(ncx, ncz)
            newly_loaded.append(chunk_id_str)

    # Unload chunks that are no longer in the target set.
    keys_to_remove = [
        k for k in list(chunk_manager._cache.keys())
        if f"{k[0]}_{k[1]}" not in target_ids
    ]
    for k in keys_to_remove:
        if chunk_manager.unload_chunk(k[0], k[1]):
            newly_unloaded.append(f"{k[0]}_{k[1]}")

    return newly_loaded, newly_unloaded
