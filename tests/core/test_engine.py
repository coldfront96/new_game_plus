"""
tests/core/test_engine.py
--------------------------
Unit tests for the SimulationEngine in src.core.engine.
"""

import pytest

from src.ai_sim.components import Inventory, Position
from src.ai_sim.entity import Entity
from src.ai_sim.systems import (
    HarvestingSystem,
    InteractionSystem,
    InventorySystem,
    MineIntent,
    System,
)
from src.core.engine import SimulationEngine
from src.core.event_bus import EventBus
from src.loot_math.item import Item, ItemType, Rarity
from src.rules_engine.character_35e import Character35e
from src.terrain.block import Block, Material
from src.terrain.chunk_manager import ChunkManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def bus():
    return EventBus()


@pytest.fixture
def chunk_manager(bus):
    return ChunkManager(event_bus=bus, cache_size=4)


@pytest.fixture
def engine(bus, chunk_manager):
    return SimulationEngine(event_bus=bus, chunk_manager=chunk_manager)


@pytest.fixture
def fighter():
    return Character35e(
        name="Aldric",
        char_class="Fighter",
        level=5,
        strength=16,
        dexterity=13,
        constitution=14,
    )


# ---------------------------------------------------------------------------
# SimulationEngine: Basic Tests
# ---------------------------------------------------------------------------

class TestSimulationEngineBasic:
    """Test basic engine creation and system management."""

    def test_engine_creation(self, engine, bus, chunk_manager):
        """Engine should initialise with the provided event_bus and chunk_manager."""
        assert engine.event_bus is bus
        assert engine.chunk_manager is chunk_manager
        assert engine.entities == []
        assert engine.systems == []

    def test_register_system(self, engine):
        """Registering a system should add it to the systems list."""

        class DummySystem(System):
            def update(self):
                pass

        sys = DummySystem()
        engine.register_system(sys, priority=100)
        assert sys in engine.systems

    def test_unregister_system(self, engine):
        """Unregistering a system should remove it."""

        class DummySystem(System):
            def update(self):
                pass

        sys = DummySystem()
        engine.register_system(sys, priority=100)
        assert engine.unregister_system(sys) is True
        assert sys not in engine.systems

    def test_unregister_nonexistent_system(self, engine):
        """Unregistering a system that was never registered returns False."""

        class DummySystem(System):
            def update(self):
                pass

        assert engine.unregister_system(DummySystem()) is False

    def test_add_entity(self, engine):
        """Entities can be added to the simulation."""
        entity = Entity(name="Test")
        engine.add_entity(entity)
        assert entity in engine.entities

    def test_remove_entity(self, engine):
        """Entities can be removed from the simulation."""
        entity = Entity(name="Test")
        engine.add_entity(entity)
        assert engine.remove_entity(entity) is True
        assert entity not in engine.entities

    def test_remove_nonexistent_entity(self, engine):
        """Removing a non-existent entity returns False."""
        entity = Entity(name="Ghost")
        assert engine.remove_entity(entity) is False


# ---------------------------------------------------------------------------
# SimulationEngine: Tick & Priority Order
# ---------------------------------------------------------------------------

class TestSimulationEngineTick:
    """Test the tick method and system update ordering."""

    def test_tick_calls_update_on_all_systems(self, engine):
        """A single tick should invoke update() on every registered system."""
        call_log = []

        class TrackingSystemA(System):
            def update(self):
                call_log.append("A")

        class TrackingSystemB(System):
            def update(self):
                call_log.append("B")

        engine.register_system(TrackingSystemA(), priority=100)
        engine.register_system(TrackingSystemB(), priority=200)
        engine.tick(delta_time=1.0)

        assert call_log == ["A", "B"]

    def test_tick_respects_priority_order(self, engine):
        """Systems must update in ascending priority order."""
        call_log = []

        class PhysicsStub(System):
            def update(self):
                call_log.append("Physics")

        class BehaviorStub(System):
            def update(self):
                call_log.append("Behavior")

        class MovementStub(System):
            def update(self):
                call_log.append("Movement")

        class InteractionStub(System):
            def update(self):
                call_log.append("Interaction")

        # Register out of order to verify sorting
        engine.register_system(InteractionStub(), priority=400)
        engine.register_system(PhysicsStub(), priority=100)
        engine.register_system(MovementStub(), priority=300)
        engine.register_system(BehaviorStub(), priority=200)

        engine.tick(delta_time=1.0)

        assert call_log == ["Physics", "Behavior", "Movement", "Interaction"]

    def test_tick_publishes_events(self, engine, bus):
        """Tick should publish tick_start and tick_end events."""
        events_received = []

        bus.subscribe("tick_start", lambda p: events_received.append(("start", p)))
        bus.subscribe("tick_end", lambda p: events_received.append(("end", p)))

        engine.tick(delta_time=0.5)

        assert len(events_received) == 2
        assert events_received[0][0] == "start"
        assert events_received[0][1]["delta_time"] == 0.5
        assert events_received[1][0] == "end"

    def test_tick_cleans_inactive_entities(self, engine):
        """Inactive entities should be removed after a tick."""
        entity = Entity(name="Doomed")
        engine.add_entity(entity)
        entity.destroy()  # marks as inactive

        engine.tick(delta_time=1.0)

        assert entity not in engine.entities


# ---------------------------------------------------------------------------
# Full Loop Integration: Mine → Harvest → Pickup
# ---------------------------------------------------------------------------

class TestFullGameplayLoop:
    """Integration tests for the Action → Harvest → Grow loop."""

    def test_mine_block_spawns_item(self, bus, chunk_manager, fighter):
        """Breaking a block via InteractionSystem should spawn an item entity."""
        entities = []
        interaction = InteractionSystem(event_bus=bus)
        harvesting = HarvestingSystem(event_bus=bus, entities=entities)

        engine = SimulationEngine(
            event_bus=bus, chunk_manager=chunk_manager, entities=entities
        )
        engine.register_system(interaction, priority=400)
        engine.register_system(harvesting, priority=500)

        # Create a weak block that will be destroyed in one hit
        block = Block(block_id=1, material=Material.DIRT, durability=1)

        # Publish mine intent
        bus.publish("mine_intent", MineIntent(
            character=fighter,
            block=block,
            tool=None,
        ))

        # Run one tick — interaction resolves, harvesting spawns item
        engine.tick(delta_time=1.0)

        # The block should be destroyed
        assert block.is_destroyed()

        # An item entity should have been spawned
        item_entities = [e for e in entities if e.has_tag("item")]
        assert len(item_entities) == 1
        assert item_entities[0].get_component(Item) is not None
        assert item_entities[0].get_component(Item).name == "Dirt"

    def test_item_pickup_on_overlap(self, bus, chunk_manager, fighter):
        """An entity with Inventory should pick up overlapping item entities."""
        entities = []

        # Create a collector entity at (5, 64, 5)
        collector = Entity(name="Collector")
        collector.add_component(Position(x=5.0, y=64.0, z=5.0))
        collector.add_component(Inventory(capacity=10))
        entities.append(collector)

        # Create an item entity at the same position
        item_entity = Entity(name="drop_stone")
        item_entity.add_tag("item")
        item_entity.add_component(Position(x=5.0, y=64.0, z=5.0))
        item_entity.add_component(Item(
            name="Stone",
            item_type=ItemType.MATERIAL,
            rarity=Rarity.COMMON,
            base_damage=0,
        ))
        entities.append(item_entity)

        inventory_sys = InventorySystem(event_bus=bus, entities=entities)
        engine = SimulationEngine(
            event_bus=bus, chunk_manager=chunk_manager, entities=entities
        )
        engine.register_system(inventory_sys, priority=500)

        # Record pickup events
        pickups = []
        bus.subscribe("item_picked_up", lambda p: pickups.append(p))

        engine.tick(delta_time=1.0)

        # The item should have been picked up
        assert len(pickups) == 1
        assert pickups[0]["collector_id"] == collector.entity_id
        assert pickups[0]["item_name"] == "Stone"

        # Item entity should be destroyed (removed after cleanup)
        assert not item_entity.is_active

        # Collector's inventory should contain the item
        inv = collector.get_component(Inventory)
        assert inv.used_slots == 1

    def test_full_loop_mine_harvest_pickup(self, bus, chunk_manager, fighter):
        """Full loop: mine a block → item spawns → collector picks it up."""
        entities = []

        # Collector near the mining location
        collector = Entity(name="Miner")
        collector.add_component(Position(x=0.0, y=0.0, z=0.0))
        collector.add_component(Inventory(capacity=10))
        entities.append(collector)

        interaction = InteractionSystem(event_bus=bus)
        harvesting = HarvestingSystem(event_bus=bus, entities=entities)
        inventory_sys = InventorySystem(
            event_bus=bus, entities=entities, pickup_radius=2.0
        )

        engine = SimulationEngine(
            event_bus=bus, chunk_manager=chunk_manager, entities=entities
        )
        engine.register_system(interaction, priority=400)
        engine.register_system(harvesting, priority=500)
        engine.register_system(inventory_sys, priority=600)

        # Create a block that will be destroyed
        block = Block(block_id=1, material=Material.DIRT, durability=1)

        # Mine it
        bus.publish("mine_intent", MineIntent(
            character=fighter,
            block=block,
            tool=None,
        ))

        # First tick: interaction breaks block, harvesting spawns item
        engine.tick(delta_time=1.0)

        # Second tick: inventory system picks up the item
        engine.tick(delta_time=1.0)

        # Verify the full loop
        inv = collector.get_component(Inventory)
        assert inv.used_slots == 1
        assert inv.items[0].name == "Dirt"
