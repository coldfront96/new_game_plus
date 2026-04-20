"""
src/core/engine.py
------------------
Central simulation engine for New Game Plus.

The :class:`SimulationEngine` owns the core subsystems (ChunkManager,
entity list, active Systems) and orchestrates the main game loop via
its :meth:`tick` method.

Systems are updated each tick in a fixed priority order:

    Physics → Behavior → Movement → Interaction

This ensures deterministic simulation regardless of registration order.

Usage::

    from src.core.engine import SimulationEngine
    from src.core.event_bus import EventBus
    from src.terrain.chunk_manager import ChunkManager

    bus = EventBus()
    cm = ChunkManager(event_bus=bus)
    engine = SimulationEngine(event_bus=bus, chunk_manager=cm)
    engine.register_system(my_system, priority=200)
    engine.tick(delta_time=1.0)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Tuple

from src.ai_sim.entity import Entity
from src.core.event_bus import EventBus


@dataclass(slots=True)
class SimulationEngine:
    """Manages the main simulation loop and all active ECS systems.

    Systems are stored with a numeric priority — lower values update first.
    Recommended priority bands:

        100  Physics
        200  Behavior
        300  Movement
        400  Interaction
        500  Harvesting / Inventory
        600  Progression / UI

    Attributes:
        event_bus:     Shared event bus for inter-system communication.
        chunk_manager: Terrain chunk manager instance.
        entities:      Global list of active entities in the simulation.
    """

    event_bus: EventBus
    chunk_manager: Any  # ChunkManager (avoid circular import at type level)
    entities: List[Entity] = field(default_factory=list)
    _systems: List[Tuple[int, Any]] = field(default_factory=list)

    # ------------------------------------------------------------------
    # System management
    # ------------------------------------------------------------------

    def register_system(self, system: Any, priority: int = 500) -> None:
        """Register a system with the given priority (lower runs first).

        Args:
            system:   Any object implementing an ``update()`` method.
            priority: Numeric priority. Lower values are updated earlier.
        """
        self._systems.append((priority, system))
        self._systems.sort(key=lambda entry: entry[0])

    def unregister_system(self, system: Any) -> bool:
        """Remove a previously registered system.

        Returns:
            ``True`` if the system was found and removed; ``False`` otherwise.
        """
        for i, (_, s) in enumerate(self._systems):
            if s is system:
                self._systems.pop(i)
                return True
        return False

    @property
    def systems(self) -> List[Any]:
        """Return the list of registered systems in priority order."""
        return [s for _, s in self._systems]

    # ------------------------------------------------------------------
    # Entity management
    # ------------------------------------------------------------------

    def add_entity(self, entity: Entity) -> None:
        """Add an entity to the simulation."""
        self.entities.append(entity)

    def remove_entity(self, entity: Entity) -> bool:
        """Remove an entity from the simulation.

        Returns:
            ``True`` if the entity was found and removed; ``False`` otherwise.
        """
        if entity in self.entities:
            self.entities.remove(entity)
            return True
        return False

    # ------------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------------

    def tick(self, delta_time: float = 1.0) -> None:
        """Advance the simulation by one tick.

        Publishes a ``"tick_start"`` event before updating systems and a
        ``"tick_end"`` event after all systems have been processed.

        Args:
            delta_time: Elapsed game-time seconds since last tick.
        """
        self.event_bus.publish("tick_start", {"delta_time": delta_time})

        for _priority, system in self._systems:
            system.update()

        # Cleanup: remove inactive entities
        self.entities = [e for e in self.entities if e.is_active]

        self.event_bus.publish("tick_end", {"delta_time": delta_time})
