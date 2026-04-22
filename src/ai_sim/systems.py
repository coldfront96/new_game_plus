"""
src/ai_sim/systems.py
---------------------
ECS Systems that drive combat and world-interaction logic.

Systems subscribe to events on the :class:`~src.core.event_bus.EventBus`
and process them each tick.  They read/write ECS components on
:class:`~src.ai_sim.entity.Entity` instances but contain no persistent
state of their own beyond the event queue.

Systems
~~~~~~~
* :class:`CombatSystem` — listens for ``"attack_intent"`` events and
  resolves attacks between two :class:`Character35e` stat blocks.
* :class:`InteractionSystem` — listens for ``"mine_intent"`` events and
  applies mining damage to a :class:`Block` based on the character's
  Strength modifier and any equipped :class:`Item`.
* :class:`BehaviorSystem` — updates entity FSMs each tick, driving
  AI decisions based on needs and skill checks.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.ai_sim.behavior import BehaviorFSM, BehaviorState, EntityTask, TaskType
from src.ai_sim.components import Health, Inventory, Needs, Position
from src.ai_sim.entity import Entity
from src.core.event_bus import EventBus
from src.loot_math.item import Item, ItemType, Rarity
from src.rules_engine.character_35e import Character35e
from src.rules_engine.combat import AttackResolver, CombatResult
from src.rules_engine.conditions import ConditionManager
from src.rules_engine.equipment import EquipmentManager
from src.rules_engine.magic import SpellComponent, SpellRegistry
from src.rules_engine.progression import XPManager, level_up
from src.rules_engine.skills import SkillSystem
from src.terrain.block import Block


# ---------------------------------------------------------------------------
# System base class
# ---------------------------------------------------------------------------

class System(ABC):
    """Abstract base for all ECS systems.

    Subclasses must implement :meth:`update` which is called once per
    simulation tick by the engine loop.
    """

    @abstractmethod
    def update(self) -> None:
        """Process pending work for the current tick."""


# ---------------------------------------------------------------------------
# Event payload dataclasses
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class AttackIntent:
    """Payload published on the ``"attack_intent"`` event channel.

    Attributes:
        attacker:   The attacking character's stat block.
        defender:   The defending character's stat block.
        use_ranged: ``True`` for a ranged attack; ``False`` for melee.
        weapon:     Optional equipped weapon :class:`Item` (overrides
                    unarmed damage dice).
    """

    attacker: Character35e
    defender: Character35e
    use_ranged: bool = False
    weapon: Optional[Item] = None


@dataclass(slots=True)
class MineIntent:
    """Payload published on the ``"mine_intent"`` event channel.

    Attributes:
        character: The character performing the mining action.
        block:     The target :class:`Block` to mine.
        tool:      Optional equipped tool/weapon :class:`Item`.
    """

    character: Character35e
    block: Block
    tool: Optional[Item] = None


# ---------------------------------------------------------------------------
# CombatSystem
# ---------------------------------------------------------------------------

class CombatSystem(System):
    """Processes ``"attack_intent"`` events and resolves D&D 3.5e attacks.

    Each tick, all queued :class:`AttackIntent` payloads are resolved
    via :class:`AttackResolver` and the results are published back on
    the ``"combat_result"`` channel.

    Args:
        event_bus: The :class:`EventBus` instance to subscribe/publish on.
    """

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._pending: List[AttackIntent] = []
        self._event_bus.subscribe("attack_intent", self._on_attack_intent)

    def _on_attack_intent(self, payload: Any) -> None:
        """Buffer incoming attack intents for processing on the next tick."""
        if isinstance(payload, AttackIntent):
            self._pending.append(payload)

    def update(self) -> None:
        """Resolve all pending attack intents and publish results.

        If the attacker has an :class:`EquipmentManager` attached and no
        explicit weapon was provided in the intent, the system automatically
        pulls weapon damage dice and enhancement bonuses from the equipped
        MAIN_HAND weapon.
        """
        intents = list(self._pending)
        self._pending.clear()

        for intent in intents:
            # Determine weapon damage dice overrides
            dmg_count = 0
            dmg_sides = 0
            dmg_bonus = 0

            # Try to pull weapon from EquipmentManager if not explicitly set
            weapon = intent.weapon
            if weapon is None and intent.attacker.equipment_manager is not None:
                weapon = intent.attacker.equipment_manager.get_weapon()

            if weapon and weapon.item_type == ItemType.WEAPON:
                # Pull damage dice from weapon metadata (3.5e style)
                dmg_count = int(weapon.metadata.get("damage_dice_count", 0))
                dmg_sides = int(weapon.metadata.get("damage_dice_sides", 0))
                # Enhancement bonus adds to damage
                dmg_bonus = int(weapon.metadata.get("enhancement_bonus", 0))
                # Fall back to effective_damage if no dice metadata
                if dmg_count == 0 or dmg_sides == 0:
                    dmg_bonus += int(weapon.effective_damage)

            result = AttackResolver.resolve_attack(
                attacker=intent.attacker,
                defender=intent.defender,
                use_ranged=intent.use_ranged,
                damage_dice_count=dmg_count,
                damage_dice_sides=dmg_sides,
                damage_bonus=dmg_bonus,
            )

            self._event_bus.publish("combat_result", result)

    @property
    def pending_count(self) -> int:
        """Number of unprocessed attack intents."""
        return len(self._pending)


# ---------------------------------------------------------------------------
# InteractionSystem
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class MineResult:
    """Outcome of a single mining action.

    Attributes:
        damage_dealt:       Raw mining damage applied to the block.
        remaining_durability: Block durability after the hit.
        block_destroyed:    ``True`` if the block was destroyed by this hit.
    """

    damage_dealt: int
    remaining_durability: int
    block_destroyed: bool


class InteractionSystem(System):
    """Processes ``"mine_intent"`` events — characters mining blocks.

    Mining damage is ``base_mining + STR modifier + tool_bonus``, where:

    * ``base_mining`` is a fixed value of ``5`` (unarmed / bare-handed).
    * ``STR modifier`` is the 3.5e ability modifier from the character.
    * ``tool_bonus`` is the tool's ``effective_damage`` if a TOOL or WEAPON
      item is provided.

    Args:
        event_bus: The :class:`EventBus` instance to subscribe/publish on.
    """

    BASE_MINING_DAMAGE: int = 5

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._pending: List[MineIntent] = []
        self._event_bus.subscribe("mine_intent", self._on_mine_intent)

    def _on_mine_intent(self, payload: Any) -> None:
        """Buffer incoming mine intents for processing on the next tick."""
        if isinstance(payload, MineIntent):
            self._pending.append(payload)

    @classmethod
    def calculate_mining_damage(
        cls,
        character: Character35e,
        tool: Optional[Item] = None,
    ) -> int:
        """Compute the total mining damage a character deals.

        Args:
            character: The character performing the action.
            tool:      Optional tool or weapon item.

        Returns:
            Non-negative mining damage value (minimum 1).
        """
        damage = cls.BASE_MINING_DAMAGE + character.strength_mod

        if tool and tool.item_type in (ItemType.TOOL, ItemType.WEAPON):
            damage += int(tool.effective_damage)

        return max(1, damage)

    def update(self) -> None:
        """Resolve all pending mine intents and publish results.

        When a block is destroyed, a ``"block_broken"`` event is also
        published so that downstream systems (Physics, Harvesting) can react.
        """
        intents = list(self._pending)
        self._pending.clear()

        for intent in intents:
            damage = self.calculate_mining_damage(
                intent.character, intent.tool
            )
            remaining = intent.block.mine(damage)
            destroyed = intent.block.is_destroyed()
            result = MineResult(
                damage_dealt=damage,
                remaining_durability=remaining,
                block_destroyed=destroyed,
            )
            self._event_bus.publish("mine_result", result)

            if destroyed:
                self._event_bus.publish("block_broken", {
                    "material": intent.block.material.name,
                    "block": intent.block,
                    "character": intent.character,
                })

    @property
    def pending_count(self) -> int:
        """Number of unprocessed mine intents."""
        return len(self._pending)


# ---------------------------------------------------------------------------
# PhysicsSystem
# ---------------------------------------------------------------------------

# Materials subject to gravity (falling behaviour)
_GRAVITY_MATERIALS = frozenset({"SAND", "GRAVEL"})


class PhysicsSystem(System):
    """Processes block physics: gravity for fluids/loose materials and
    structural support checks after block removal.

    Gravity Logic:
        If a block has the ``is_fluid`` property **or** its material is
        SAND or GRAVEL, and the block directly beneath it is AIR (None),
        the block falls to the lowest available empty position.

    Structural Check:
        When a ``"block_broken"`` event is received the system queues a
        check on the six adjacent blocks.  Any adjacent block that is a
        gravity-affected material and no longer supported will fall.

    Args:
        event_bus:      The :class:`EventBus` to subscribe/publish on.
        chunk_manager:  The :class:`~src.terrain.chunk_manager.ChunkManager`
                        used to read/write blocks in the world.
    """

    def __init__(self, event_bus: "EventBus", chunk_manager: Any) -> None:
        self._event_bus = event_bus
        self._chunk_manager = chunk_manager
        self._pending_positions: List[Tuple[int, int, int]] = []
        self._event_bus.subscribe("block_broken", self._on_block_broken)
        self._event_bus.subscribe("block_modified", self._on_block_modified)

    def _on_block_broken(self, payload: Any) -> None:
        """When a block is broken, queue structural checks on its neighbours."""
        if not isinstance(payload, dict):
            return
        wx = payload.get("world_x")
        wy = payload.get("world_y")
        wz = payload.get("world_z")
        if wx is None or wy is None or wz is None:
            return
        # Queue the six adjacent positions for structural check
        for dx, dy, dz in [(1, 0, 0), (-1, 0, 0),
                           (0, 1, 0), (0, -1, 0),
                           (0, 0, 1), (0, 0, -1)]:
            nx, ny, nz = wx + dx, wy + dy, wz + dz
            if 0 <= ny < 256:
                self._pending_positions.append((nx, ny, nz))

    def _on_block_modified(self, payload: Any) -> None:
        """When a block is modified, check above it for falling blocks."""
        if not isinstance(payload, dict):
            return
        wx = payload.get("world_x")
        wy = payload.get("world_y")
        wz = payload.get("world_z")
        if wx is None or wy is None or wz is None:
            return
        # Check the block directly above the modified position
        if wy + 1 < 256:
            self._pending_positions.append((wx, wy + 1, wz))

    def update(self) -> None:
        """Process all pending gravity and structural checks."""
        positions = list(self._pending_positions)
        self._pending_positions.clear()

        # De-duplicate positions
        seen = set()
        for pos in positions:
            if pos not in seen:
                seen.add(pos)
                self._process_gravity(pos[0], pos[1], pos[2])

    def _should_fall(self, block: "Block") -> bool:
        """Determine whether a block is subject to gravity."""
        if block.is_fluid:
            return True
        if block.material.name in _GRAVITY_MATERIALS:
            return True
        return False

    def _process_gravity(self, wx: int, wy: int, wz: int) -> None:
        """Check if the block at (wx, wy, wz) should fall, and drop it."""
        block = self._chunk_manager.get_block_world(wx, wy, wz)
        if block is None:
            return
        if not self._should_fall(block):
            return

        # Find lowest empty space beneath
        target_y = wy
        for y in range(wy - 1, -1, -1):
            below = self._chunk_manager.get_block_world(wx, y, wz)
            if below is None:
                target_y = y
            else:
                break

        if target_y == wy:
            # No space to fall
            return

        # Move the block down
        self._chunk_manager.set_block_world(wx, wy, wz, None)
        self._chunk_manager.set_block_world(wx, target_y, wz, block)

        self._event_bus.publish("block_fell", {
            "world_x": wx,
            "from_y": wy,
            "to_y": target_y,
            "world_z": wz,
            "material": block.material.name,
        })

    @property
    def pending_count(self) -> int:
        """Number of unprocessed positions to check."""
        return len(self._pending_positions)


# ---------------------------------------------------------------------------
# MovementSystem
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class MoveIntent:
    """Payload published on the ``"move_intent"`` event channel.

    Attributes:
        entity:    The entity to move.
        character: The entity's 3.5e stat block (provides voxel_speed).
        path:      Ordered list of (x, y, z) waypoints to follow.
    """

    entity: Entity
    character: Character35e
    path: List[Tuple[int, int, int]]


class MovementSystem(System):
    """Processes ``"move_intent"`` events — spatial updates for entities.

    Each tick, entities advance along their assigned path by a number of
    steps equal to their 3.5e ``voxel_speed`` (base_speed // 5). The
    entity's :class:`Position` component is updated to the new location.

    When an entity reaches its destination, a ``"move_complete"`` event
    is published.

    Args:
        event_bus: The :class:`EventBus` instance to subscribe/publish on.
    """

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._pending: List[MoveIntent] = []
        self._event_bus.subscribe("move_intent", self._on_move_intent)

    def _on_move_intent(self, payload: Any) -> None:
        """Buffer incoming move intents for processing on the next tick."""
        if isinstance(payload, MoveIntent):
            self._pending.append(payload)

    def update(self) -> None:
        """Advance all pending entities along their paths."""
        intents = list(self._pending)
        self._pending.clear()

        for intent in intents:
            self._process_movement(intent)

    def _process_movement(self, intent: MoveIntent) -> None:
        """Move an entity along its path up to voxel_speed steps."""
        entity = intent.entity
        character = intent.character
        path = intent.path

        if not path:
            return

        pos = entity.get_component(Position)
        if pos is None:
            return

        steps = character.voxel_speed
        steps_taken = 0
        last_index = 0

        for i, waypoint in enumerate(path):
            if steps_taken >= steps:
                break
            # Skip waypoints that match the entity's current position
            if (float(waypoint[0]) == pos.x and float(waypoint[1]) == pos.y
                    and float(waypoint[2]) == pos.z):
                last_index = i
                continue
            pos.x = float(waypoint[0])
            pos.y = float(waypoint[1])
            pos.z = float(waypoint[2])
            steps_taken += 1
            last_index = i

        remaining_path = path[last_index + 1:]

        if not remaining_path:
            # Entity reached destination
            self._event_bus.publish("move_complete", {
                "entity_id": entity.entity_id,
                "position": (pos.x, pos.y, pos.z),
            })
        else:
            # Re-queue for the next tick with the remaining path
            self._pending.append(MoveIntent(
                entity=entity,
                character=character,
                path=remaining_path,
            ))

    @property
    def pending_count(self) -> int:
        """Number of unprocessed move intents."""
        return len(self._pending)


# ---------------------------------------------------------------------------
# NeedsSystem
# ---------------------------------------------------------------------------

class NeedsSystem(System):
    """Manages temporal decay of :class:`Needs` components on entities.

    Each tick, all registered entities with a :class:`Needs` component
    have their needs decayed by the configured ``delta_time``. When any
    need drops to a critical threshold (≤ 10), a ``"need_critical"``
    event is published.

    Args:
        event_bus:  The :class:`EventBus` instance to publish events on.
        entities:   List of entities whose needs should be updated.
        delta_time: Simulated seconds per tick (default 1.0).
    """

    CRITICAL_THRESHOLD: float = 10.0

    def __init__(
        self,
        event_bus: EventBus,
        entities: Optional[List[Entity]] = None,
        delta_time: float = 1.0,
    ) -> None:
        self._event_bus = event_bus
        self._entities: List[Entity] = entities if entities is not None else []
        self._delta_time = delta_time

    def add_entity(self, entity: Entity) -> None:
        """Register an entity for needs processing."""
        if entity not in self._entities:
            self._entities.append(entity)

    def remove_entity(self, entity: Entity) -> None:
        """Unregister an entity from needs processing."""
        if entity in self._entities:
            self._entities.remove(entity)

    def update(self) -> None:
        """Decay all registered entities' needs and check for critical state."""
        for entity in self._entities:
            if not entity.is_active:
                continue

            needs = entity.get_component(Needs)
            if needs is None:
                continue

            needs.tick(self._delta_time)

            # Check for critical needs
            for need_name in ("hunger", "rest", "safety", "social", "purpose"):
                value = getattr(needs, need_name)
                if value <= self.CRITICAL_THRESHOLD:
                    self._event_bus.publish("need_critical", {
                        "entity_id": entity.entity_id,
                        "need": need_name,
                        "value": value,
                    })

    @property
    def entity_count(self) -> int:
        """Number of entities registered for needs processing."""
        return len(self._entities)


# ---------------------------------------------------------------------------
# BehaviorSystem
# ---------------------------------------------------------------------------

# Hunger threshold below which an entity should forage
_HUNGER_THRESHOLD: float = 30.0

# Default DC for foraging (Survival check)
_FORAGE_DC: int = 15


@dataclass(slots=True)
class EntityBehaviorEntry:
    """Associates an entity with its behavior FSM, skill system, and character.

    Attributes:
        entity:       The ECS entity.
        fsm:          The entity's behavioral state machine.
        skill_system: The entity's 3.5e skill ranks.
        character:    The entity's D&D 3.5e stat block.
    """

    entity: Entity
    fsm: BehaviorFSM
    skill_system: SkillSystem
    character: Character35e


class BehaviorSystem(System):
    """Updates entity FSMs each simulation tick, driving AI decisions.

    Logic per tick:
        1. If entity is IDLE and hunger is low → assign a FORAGE task
           (requires a Survival skill check).
        2. If SEARCH_FOR_TASK → look for nearest food source and transition
           to MOVE_TO_TARGET.
        3. If MOVE_TO_TARGET → publish a move_intent event and wait for
           arrival (transition to PERFORM_ACTION when at target).
        4. If PERFORM_ACTION → perform the skill check and complete the task.

    Args:
        event_bus:      The :class:`EventBus` to publish movement/action events.
        chunk_manager:  Optional chunk manager for pathfinding integration.
    """

    def __init__(
        self,
        event_bus: EventBus,
        chunk_manager: Any = None,
        food_sources: Optional[list] = None,
    ) -> None:
        self._event_bus = event_bus
        self._chunk_manager = chunk_manager
        self._entries: List[EntityBehaviorEntry] = []
        self._food_sources: list = food_sources if food_sources is not None else []
        self._event_bus.subscribe("move_complete", self._on_move_complete)

    def register_entity(
        self,
        entity: Entity,
        fsm: BehaviorFSM,
        skill_system: SkillSystem,
        character: Character35e,
    ) -> None:
        """Register an entity for behavior processing.

        Args:
            entity:       The ECS entity.
            fsm:          The entity's FSM instance.
            skill_system: The entity's skill system.
            character:    The entity's 3.5e character stat block.
        """
        self._entries.append(
            EntityBehaviorEntry(
                entity=entity,
                fsm=fsm,
                skill_system=skill_system,
                character=character,
            )
        )

    def add_food_source(self, position: Tuple[int, int, int]) -> None:
        """Register a food source location in the world.

        Args:
            position: (x, y, z) world coordinate of the food source.
        """
        self._food_sources.append(position)

    def _on_move_complete(self, payload: Any) -> None:
        """Handle move_complete events — transition entities to PERFORM_ACTION."""
        if not isinstance(payload, dict):
            return
        entity_id = payload.get("entity_id")
        for entry in self._entries:
            if entry.entity.entity_id == entity_id:
                if entry.fsm.state == BehaviorState.MOVE_TO_TARGET:
                    entry.fsm.transition(BehaviorState.PERFORM_ACTION)
                break

    def update(self) -> None:
        """Process all registered entities' behavioral logic for one tick."""
        for entry in self._entries:
            if not entry.entity.is_active:
                continue
            entry.fsm.tick()
            self._process_entity(entry)

    def _process_entity(self, entry: EntityBehaviorEntry) -> None:
        """Run FSM logic for a single entity."""
        state = entry.fsm.state

        if state == BehaviorState.IDLE:
            self._handle_idle(entry)
        elif state == BehaviorState.SEARCH_FOR_TASK:
            self._handle_search(entry)
        elif state == BehaviorState.MOVE_TO_TARGET:
            self._handle_move(entry)
        elif state == BehaviorState.PERFORM_ACTION:
            self._handle_action(entry)

    def _handle_idle(self, entry: EntityBehaviorEntry) -> None:
        """Check if the entity has a critical need and assign a task."""
        needs = entry.entity.get_component(Needs)
        if needs is None:
            return

        # If hunger is low, forage
        if needs.hunger <= _HUNGER_THRESHOLD:
            task = EntityTask(
                task_type=TaskType.FORAGE,
                skill_name="Survival",
                dc=_FORAGE_DC,
            )
            entry.fsm.assign_task(task)

    def _handle_search(self, entry: EntityBehaviorEntry) -> None:
        """Find the nearest food source and set it as the target."""
        if not self._food_sources:
            # No food sources available — go back to idle
            entry.fsm.transition(BehaviorState.IDLE)
            return

        pos = entry.entity.get_component(Position)
        if pos is None:
            entry.fsm.transition(BehaviorState.IDLE)
            return

        # Find nearest food source
        entity_pos = (int(pos.x), int(pos.y), int(pos.z))
        nearest = min(
            self._food_sources,
            key=lambda f: (
                abs(f[0] - entity_pos[0])
                + abs(f[1] - entity_pos[1])
                + abs(f[2] - entity_pos[2])
            ),
        )

        entry.fsm.current_task.target_position = nearest
        entry.fsm.transition(BehaviorState.MOVE_TO_TARGET)

        # Publish move intent so the MovementSystem can handle pathfinding
        self._event_bus.publish("behavior_move_request", {
            "entity_id": entry.entity.entity_id,
            "target": nearest,
        })

    def _handle_move(self, entry: EntityBehaviorEntry) -> None:
        """Wait for move_complete event (handled by _on_move_complete).

        If the entity has been in this state too long, abort.
        """
        if entry.fsm.ticks_in_state > 100:
            # Timeout — go back to idle
            entry.fsm.transition(BehaviorState.IDLE)

    def _handle_action(self, entry: EntityBehaviorEntry) -> None:
        """Perform the task action (skill check) and complete."""
        task = entry.fsm.current_task

        if task.task_type == TaskType.FORAGE and task.skill_name:
            # Perform Survival skill check
            ability = entry.skill_system.get_key_ability(task.skill_name)
            ability_mod = 0
            if ability is not None:
                ability_mod = (
                    getattr(entry.character, f"{ability.value}_mod", 0)
                )

            result = entry.skill_system.check(
                skill_name=task.skill_name,
                ability_modifier=ability_mod,
                dc=task.dc,
            )

            self._event_bus.publish("skill_check_result", {
                "entity_id": entry.entity.entity_id,
                "skill": task.skill_name,
                "success": result.success,
                "total": result.total,
                "dc": task.dc,
            })

            if result.success:
                # Successful forage — restore some hunger
                needs = entry.entity.get_component(Needs)
                if needs is not None:
                    needs.hunger = min(100.0, needs.hunger + 30.0)

        entry.fsm.complete_task()

    @property
    def entity_count(self) -> int:
        """Number of entities registered for behavior processing."""
        return len(self._entries)


# ---------------------------------------------------------------------------
# ProgressionSystem
# ---------------------------------------------------------------------------

# CR-to-XP award table (simplified 3.5e SRD CR awards for a single character)
_CR_XP_AWARD: Dict[int, int] = {
    1: 300,
    2: 600,
    3: 900,
    4: 1200,
    5: 1500,
    6: 1800,
    7: 2100,
    8: 2400,
    9: 2700,
    10: 3000,
    11: 3300,
    12: 3600,
    13: 3900,
    14: 4200,
    15: 4500,
    16: 4800,
    17: 5100,
    18: 5400,
    19: 5700,
    20: 6000,
}


def _xp_for_cr(cr: int) -> int:
    """Return the XP award for defeating a creature of the given CR.

    Uses the look-up table for CR 1–20; for CRs outside that range,
    uses ``cr × 300`` as a linear approximation.

    Args:
        cr: Challenge Rating of the defeated creature.

    Returns:
        XP to award the victor.
    """
    return _CR_XP_AWARD.get(cr, cr * 300)


class ProgressionSystem(System):
    """Listens for ``"combat_result"`` and ``"skill_check_success"`` events
    to award XP and trigger level-ups automatically.

    When a ``"combat_result"`` event indicates a defender was defeated
    (total_damage dealt, with optional ``defeated`` flag in payload), XP
    is awarded to the attacker based on the defender's Challenge Rating.

    When a ``"skill_check_success"`` event fires, a small fixed XP
    reward is granted.

    Args:
        event_bus: The :class:`EventBus` instance to subscribe/publish on.
    """

    # Fixed XP reward for a successful skill check
    SKILL_CHECK_XP: int = 50

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._xp_managers: Dict[str, XPManager] = {}
        self._characters: Dict[str, Character35e] = {}
        self._event_bus.subscribe("combat_result", self._on_combat_result)
        self._event_bus.subscribe("skill_check_success", self._on_skill_check_success)

    def register_character(
        self, character: Character35e, xp_manager: Optional[XPManager] = None
    ) -> None:
        """Register a character for XP tracking.

        Args:
            character:  The character to track.
            xp_manager: Optional pre-existing XPManager.  If ``None``, a new
                        one is created at level/xp 0 matching the character.
        """
        if xp_manager is None:
            xp_manager = XPManager(current_xp=0, current_level=character.level)
        self._xp_managers[character.char_id] = xp_manager
        self._characters[character.char_id] = character

    def get_xp_manager(self, char_id: str) -> Optional[XPManager]:
        """Retrieve the XPManager for a character by ID."""
        return self._xp_managers.get(char_id)

    def _on_combat_result(self, payload: Any) -> None:
        """Handle combat_result events — award XP if defender is defeated."""
        if not isinstance(payload, dict):
            return

        defeated = payload.get("defeated", False)
        if not defeated:
            return

        attacker = payload.get("attacker")
        defender = payload.get("defender")
        if attacker is None or defender is None:
            return

        attacker_id = attacker.char_id if isinstance(attacker, Character35e) else None
        if attacker_id is None or attacker_id not in self._xp_managers:
            return

        # Determine CR from defender's level (monsters use level as CR proxy)
        cr = defender.level if isinstance(defender, Character35e) else 1
        xp_award = _xp_for_cr(cr)

        xp_mgr = self._xp_managers[attacker_id]
        xp_mgr.award_xp(xp_award)
        self._event_bus.publish("xp_awarded", {
            "char_id": attacker_id,
            "amount": xp_award,
            "source": "combat",
        })

        self._try_level_up(attacker_id)

    def _on_skill_check_success(self, payload: Any) -> None:
        """Handle skill_check_success events — award fixed XP."""
        if not isinstance(payload, dict):
            return

        char_id = payload.get("char_id")
        if char_id is None or char_id not in self._xp_managers:
            return

        xp_mgr = self._xp_managers[char_id]
        xp_mgr.award_xp(self.SKILL_CHECK_XP)
        self._event_bus.publish("xp_awarded", {
            "char_id": char_id,
            "amount": self.SKILL_CHECK_XP,
            "source": "skill_check",
        })

        self._try_level_up(char_id)

    def _try_level_up(self, char_id: str) -> None:
        """Check and apply level-up if XP threshold is met."""
        xp_mgr = self._xp_managers.get(char_id)
        character = self._characters.get(char_id)
        if xp_mgr is None or character is None:
            return

        result = xp_mgr.check_level_up()
        if result.leveled_up:
            progression = level_up(character, xp_mgr)
            self._event_bus.publish("level_up", {
                "char_id": char_id,
                "new_level": progression.new_level,
                "hp_gained": progression.hp_gained,
                "skill_points": progression.skill_points,
            })

    def update(self) -> None:
        """No-op for ProgressionSystem — events are processed immediately."""


# ---------------------------------------------------------------------------
# HarvestingSystem
# ---------------------------------------------------------------------------

class HarvestingSystem(System):
    """Listens for ``"block_broken"`` events and spawns item entities.

    When a block is destroyed, the system creates a new :class:`Entity` with
    a :class:`Position` component at the broken block's location and an
    :class:`Item` component matching the block's material type.

    The spawned entity is tagged ``"item"`` so that other systems
    (e.g. :class:`InventorySystem`) can locate it for pickup.

    Args:
        event_bus:  The :class:`EventBus` to subscribe/publish on.
        entities:   The shared entity list (typically ``SimulationEngine.entities``).
    """

    def __init__(self, event_bus: EventBus, entities: Optional[List[Entity]] = None) -> None:
        self._event_bus = event_bus
        self._entities: List[Entity] = entities if entities is not None else []
        self._pending: List[Dict[str, Any]] = []
        self._event_bus.subscribe("block_broken", self._on_block_broken)

    def _on_block_broken(self, payload: Any) -> None:
        """Buffer block_broken events for processing on the next tick."""
        if isinstance(payload, dict):
            self._pending.append(payload)

    def update(self) -> None:
        """Spawn item entities for all blocks broken this tick."""
        events = list(self._pending)
        self._pending.clear()

        for event in events:
            material_name = event.get("material")
            if material_name is None:
                continue

            # Create item matching the block material
            item = Item(
                name=material_name.replace("_", " ").title(),
                item_type=ItemType.MATERIAL,
                rarity=Rarity.COMMON,
                base_damage=0,
            )

            # Create the item entity
            item_entity = Entity(name=f"drop_{material_name.lower()}")
            item_entity.add_component(item)
            item_entity.add_tag("item")

            # Place at block position if available, else origin
            world_x = event.get("world_x", 0)
            world_y = event.get("world_y", 0)
            world_z = event.get("world_z", 0)
            item_entity.add_component(Position(
                x=float(world_x),
                y=float(world_y),
                z=float(world_z),
            ))

            self._entities.append(item_entity)
            self._event_bus.publish("item_spawned", {
                "entity_id": item_entity.entity_id,
                "material": material_name,
                "position": (world_x, world_y, world_z),
            })

    @property
    def pending_count(self) -> int:
        """Number of unprocessed block_broken events."""
        return len(self._pending)


# ---------------------------------------------------------------------------
# InventorySystem
# ---------------------------------------------------------------------------

class InventorySystem(System):
    """Handles automatic item pickup when entity positions overlap.

    Each tick, this system checks all entities that have both a
    :class:`Position` and an :class:`~src.ai_sim.components.Inventory`
    component against all entities tagged ``"item"``. If their positions
    are within range (Manhattan distance), the item is added to the
    entity's inventory and the item entity is destroyed.

    Args:
        event_bus:      The :class:`EventBus` to publish pickup events on.
        entities:       The shared entity list.
        pickup_radius:  Maximum Manhattan distance (in voxel units) for a
                        pickup to trigger. Default is 1.5 blocks.
    """

    def __init__(
        self,
        event_bus: EventBus,
        entities: Optional[List[Entity]] = None,
        pickup_radius: float = 1.5,
    ) -> None:
        self._event_bus = event_bus
        self._entities: List[Entity] = entities if entities is not None else []
        self._pickup_radius = pickup_radius

    def update(self) -> None:
        """Check for overlapping item entities and perform pickups."""
        # Separate items and collectors
        items: List[Entity] = []
        collectors: List[Entity] = []

        for entity in self._entities:
            if not entity.is_active:
                continue
            if entity.has_tag("item") and entity.has_component(Position):
                items.append(entity)
            elif (entity.has_component(Inventory)
                  and entity.has_component(Position)):
                collectors.append(entity)

        # For each collector, check proximity to item entities
        for collector in collectors:
            col_pos = collector.get_component(Position)
            inventory = collector.get_component(Inventory)
            if col_pos is None or inventory is None:
                continue
            if inventory.is_full:
                continue

            for item_entity in items:
                if not item_entity.is_active:
                    continue
                item_pos = item_entity.get_component(Position)
                if item_pos is None:
                    continue

                # Distance check (Manhattan distance for performance)
                dx = abs(col_pos.x - item_pos.x)
                dy = abs(col_pos.y - item_pos.y)
                dz = abs(col_pos.z - item_pos.z)
                distance = dx + dy + dz

                if distance <= self._pickup_radius:
                    # Retrieve the Item component from the item entity
                    item_component = item_entity.get_component(Item)
                    if item_component is None:
                        continue

                    if inventory.add_item(item_component):
                        item_entity.destroy()
                        self._event_bus.publish("item_picked_up", {
                            "collector_id": collector.entity_id,
                            "item_entity_id": item_entity.entity_id,
                            "item_name": item_component.name,
                        })


# ---------------------------------------------------------------------------
# ConditionSystem
# ---------------------------------------------------------------------------

class ConditionSystem(System):
    """Manages condition durations each tick, removing expired conditions.

    Each tick, all tracked conditions have their duration decremented.
    When a condition's duration reaches zero it is removed and a
    ``"condition_expired"`` event is published.

    Args:
        event_bus:          The :class:`EventBus` instance to publish events on.
        condition_manager:  The :class:`ConditionManager` that holds active
                            conditions for all characters.
    """

    def __init__(
        self,
        event_bus: EventBus,
        condition_manager: Optional[ConditionManager] = None,
    ) -> None:
        self._event_bus = event_bus
        self._condition_manager = (
            condition_manager
            if condition_manager is not None
            else ConditionManager(event_bus)
        )

    @property
    def condition_manager(self) -> ConditionManager:
        """Access the underlying condition manager."""
        return self._condition_manager

    def update(self) -> None:
        """Tick all condition durations and remove expired ones."""
        self._condition_manager.tick()


# ---------------------------------------------------------------------------
# AoOSystem (Attack of Opportunity)
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ThreatEntry:
    """Tracks an entity that threatens adjacent voxels.

    Attributes:
        entity:    The threatening entity.
        character: The entity's 3.5e stat block.
        position:  The entity's current position.
    """

    entity: Entity
    character: Character35e
    position: Tuple[int, int, int]


class AoOSystem(System):
    """Detects movement out of threatened voxels and triggers Attacks of Opportunity.

    Per the 3.5e SRD, moving out of a threatened square (adjacent voxel)
    without using a Withdraw action provokes an Attack of Opportunity from
    the threatening creature.

    The system tracks entity positions and, when a ``"move_complete"`` event
    fires, checks whether the entity moved out of any threatened voxel
    without a matching ``"withdraw_action"`` event. If so, an
    ``"attack_intent"`` event is published for the threatening entity.

    Args:
        event_bus: The :class:`EventBus` to subscribe/publish on.
    """

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._threats: List[ThreatEntry] = []
        self._pending_aoo: List[AttackIntent] = []
        self._withdrawing: set = set()  # entity IDs that used Withdraw
        self._previous_positions: Dict[str, Tuple[int, int, int]] = {}

        self._event_bus.subscribe("withdraw_action", self._on_withdraw)
        self._event_bus.subscribe("entity_moved", self._on_entity_moved)

    def register_threat(
        self,
        entity: Entity,
        character: Character35e,
        position: Tuple[int, int, int],
    ) -> None:
        """Register an entity as threatening adjacent voxels.

        Args:
            entity:    The threatening entity.
            character: The entity's character stat block.
            position:  The entity's voxel position (x, y, z).
        """
        self._threats.append(ThreatEntry(
            entity=entity,
            character=character,
            position=position,
        ))
        self._previous_positions[entity.entity_id] = position

    def update_threat_position(
        self,
        entity_id: str,
        new_position: Tuple[int, int, int],
    ) -> None:
        """Update the recorded position of a threatening entity.

        Args:
            entity_id:    The entity's unique ID.
            new_position: The new voxel position (x, y, z).
        """
        for threat in self._threats:
            if threat.entity.entity_id == entity_id:
                threat.position = new_position
                break

    def _on_withdraw(self, payload: Any) -> None:
        """Mark an entity as using the Withdraw action (no AoO provoked)."""
        if isinstance(payload, dict):
            entity_id = payload.get("entity_id")
            if entity_id:
                self._withdrawing.add(entity_id)

    def _on_entity_moved(self, payload: Any) -> None:
        """Check if a moving entity leaves a threatened voxel.

        Payload expected keys:
            - entity_id: The moving entity's ID.
            - character: The moving entity's Character35e stat block.
            - from_position: Previous (x, y, z) tuple.
            - to_position: New (x, y, z) tuple.
        """
        if not isinstance(payload, dict):
            return

        entity_id = payload.get("entity_id")
        mover_character = payload.get("character")
        from_pos = payload.get("from_position")
        to_pos = payload.get("to_position")

        if entity_id is None or from_pos is None or to_pos is None:
            return
        if mover_character is None:
            return

        # If entity used Withdraw, no AoO
        if entity_id in self._withdrawing:
            return

        # Check all threats: was the mover adjacent to any threat at from_pos?
        for threat in self._threats:
            if threat.entity.entity_id == entity_id:
                continue  # Can't threaten yourself
            if not threat.entity.is_active:
                continue

            # Check adjacency (Chebyshev distance ≤ 1 = adjacent in 3D)
            if self._is_adjacent(from_pos, threat.position):
                # Entity was in a threatened voxel and moved out
                if not self._is_adjacent(to_pos, threat.position):
                    # Provokes AoO
                    self._pending_aoo.append(AttackIntent(
                        attacker=threat.character,
                        defender=mover_character,
                        use_ranged=False,
                    ))

    @staticmethod
    def _is_adjacent(
        pos_a: Tuple[int, int, int],
        pos_b: Tuple[int, int, int],
    ) -> bool:
        """Check if two positions are adjacent (Chebyshev distance ≤ 1).

        Args:
            pos_a: First position (x, y, z).
            pos_b: Second position (x, y, z).

        Returns:
            ``True`` if the positions are adjacent or the same.
        """
        dx = abs(pos_a[0] - pos_b[0])
        dy = abs(pos_a[1] - pos_b[1])
        dz = abs(pos_a[2] - pos_b[2])
        return max(dx, dy, dz) <= 1

    def update(self) -> None:
        """Publish any pending Attacks of Opportunity as attack_intent events."""
        intents = list(self._pending_aoo)
        self._pending_aoo.clear()
        # Clear withdraw flags at end of tick
        self._withdrawing.clear()

        for intent in intents:
            self._event_bus.publish("attack_intent", intent)

    @property
    def pending_count(self) -> int:
        """Number of pending AoO intents."""
        return len(self._pending_aoo)


# ---------------------------------------------------------------------------
# SpellIntent
# ---------------------------------------------------------------------------

# Arcane caster classes (3.5e SRD): spells require somatic component ASF check.
_ARCANE_CASTER_CLASSES = frozenset({"Wizard", "Sorcerer", "Bard"})


@dataclass(slots=True)
class SpellIntent:
    """Payload published on the ``"spell_intent"`` event channel.

    Attributes:
        caster:     The casting character's stat block.
        spell_name: Name of the spell to cast (must exist in ``spell_registry``).
        spell_level: Spell level of the slot to expend.
        target:     Optional target character (for targeted spells).
    """

    caster: Character35e
    spell_name: str
    spell_level: int
    target: Optional[Character35e] = None


# ---------------------------------------------------------------------------
# MagicSystem
# ---------------------------------------------------------------------------

class MagicSystem(System):
    """Processes ``"spell_intent"`` events and resolves D&D 3.5e spellcasting.

    Before resolving an arcane spell with a somatic component the system
    rolls a d100. If the result is less than or equal to the caster's total
    Arcane Spell Failure chance (from equipped armor), the spell fails and
    the slot is still expended (3.5e SRD p.124).

    Events published:
    - ``"spell_cast"``  — a spell was resolved successfully.
    - ``"spell_failed"`` — ASF caused the spell to fizzle.

    Args:
        event_bus:      Shared :class:`EventBus`.
        spell_registry: Registry of known spell definitions.
    """

    def __init__(
        self,
        event_bus: EventBus,
        spell_registry: SpellRegistry,
    ) -> None:
        self._event_bus = event_bus
        self._spell_registry = spell_registry
        self._pending: List[SpellIntent] = []
        event_bus.subscribe("spell_intent", self._on_spell_intent)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _on_spell_intent(self, payload: SpellIntent) -> None:
        """Queue a spell intent for resolution during update()."""
        self._pending.append(payload)

    @staticmethod
    def _roll_d100() -> int:
        """Roll a d100 (1–100 inclusive)."""
        import random
        return random.randint(1, 100)

    def _compute_asf(self, caster: Character35e) -> int:
        """Return total ASF % for *caster* from their equipped armor."""
        if caster.equipment_manager is None:
            return 0
        return caster.equipment_manager.get_total_asf()

    def _is_arcane(self, caster: Character35e) -> bool:
        """Return True if *caster* is an arcane spellcaster."""
        return caster.char_class in _ARCANE_CASTER_CLASSES

    def _has_somatic(self, spell_name: str) -> bool:
        """Return True if the named spell has a somatic component."""
        spell = self._spell_registry.get(spell_name)
        if spell is None:
            return False
        return SpellComponent.SOMATIC in spell.components

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(self, intent: SpellIntent) -> Dict[str, Any]:
        """Resolve a single spell intent, applying ASF if applicable.

        Args:
            intent: The :class:`SpellIntent` to resolve.

        Returns:
            A result dict with keys:
            - ``"success"`` (bool): Whether the spell fired.
            - ``"asf_roll"`` (int | None): The d100 roll, or ``None`` if no
              ASF check was performed.
            - ``"asf_chance"`` (int): The caster's total ASF percentage.
            - ``"effect"`` (dict | None): The spell effect dict, or ``None``.
        """
        asf_roll: Optional[int] = None
        asf_chance = 0
        effect = None

        # ASF check: arcane spells with somatic components only
        if self._is_arcane(intent.caster) and self._has_somatic(intent.spell_name):
            asf_chance = self._compute_asf(intent.caster)
            if asf_chance > 0:
                asf_roll = self._roll_d100()
                if asf_roll <= asf_chance:
                    # Spell fails; publish failure event
                    result: Dict[str, Any] = {
                        "success": False,
                        "asf_roll": asf_roll,
                        "asf_chance": asf_chance,
                        "effect": None,
                    }
                    self._event_bus.publish("spell_failed", {
                        "caster_name": intent.caster.name,
                        "spell_name": intent.spell_name,
                        "asf_roll": asf_roll,
                        "asf_chance": asf_chance,
                    })
                    return result

        # Resolve the spell effect
        spell = self._spell_registry.get(intent.spell_name)
        if spell is not None and spell.effect_callback is not None:
            effect = spell.effect_callback(
                intent.caster, intent.target, intent.caster.caster_level
            )

        result = {
            "success": True,
            "asf_roll": asf_roll,
            "asf_chance": asf_chance,
            "effect": effect,
        }
        self._event_bus.publish("spell_cast", {
            "caster_name": intent.caster.name,
            "spell_name": intent.spell_name,
            "effect": effect,
        })
        return result

    def update(self) -> None:
        """Resolve all pending spell intents for this tick."""
        intents = list(self._pending)
        self._pending.clear()
        for intent in intents:
            self.resolve(intent)

    @property
    def pending_count(self) -> int:
        """Number of pending spell intents."""
        return len(self._pending)


# ---------------------------------------------------------------------------
# VisionSystem
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class VisibilityResult:
    """Result of a visibility check between two entities.

    Attributes:
        visible:      ``True`` if the observer can perceive the target.
        light_level:  The :class:`~src.terrain.lighting.LightLevel` at the
                      target's position.
        distance_ft:  Euclidean distance between observer and target in feet
                      (1 voxel = 5 ft).
        in_range:     ``True`` if the target is within the observer's vision
                      range.
        concealment:  Concealment miss-chance percentage (0, 20, or 50).
    """

    visible: bool
    light_level: Any
    distance_ft: float
    in_range: bool
    concealment: int


class VisionSystem(System):
    """Determines visibility between entity pairs based on distance and lighting.

    Per the 3.5e SRD:
    - An entity can see another if it is within its vision range **and** the
      target is not in Total Concealment the observer cannot pierce (Darkness
      without Darkvision).
    - Low-Light Vision doubles light-source radii.
    - Darkvision treats Darkness as Bright within 60 ft.

    Args:
        light_system: The :class:`~src.terrain.lighting.LightSystem` providing
                      voxel light levels.
    """

    # 1 voxel = 5 feet (standard 3.5e grid scale)
    VOXELS_TO_FEET: float = 5.0

    def __init__(self, light_system: Any) -> None:
        self._light_system = light_system

    def check_visibility(
        self,
        observer_entity: Entity,
        target_entity: Entity,
    ) -> VisibilityResult:
        """Determine whether *observer_entity* can see *target_entity*.

        Requires both entities to have :class:`~src.ai_sim.components.Position`
        and :class:`~src.ai_sim.components.Vision` components attached.

        Args:
            observer_entity: The entity doing the looking.
            target_entity:   The entity being looked at.

        Returns:
            A :class:`VisibilityResult` describing the outcome.
        """
        import math
        from src.ai_sim.components import Vision, VisionType
        from src.terrain.lighting import LightLevel

        # --- Positions -------------------------------------------------------
        obs_pos: Optional[Position] = observer_entity.get_component(Position)
        tgt_pos: Optional[Position] = target_entity.get_component(Position)

        if obs_pos is None or tgt_pos is None:
            return VisibilityResult(
                visible=False,
                light_level=None,
                distance_ft=0.0,
                in_range=False,
                concealment=100,
            )

        dx = obs_pos.x - tgt_pos.x
        dy = obs_pos.y - tgt_pos.y
        dz = obs_pos.z - tgt_pos.z
        distance_voxels = math.sqrt(dx * dx + dy * dy + dz * dz)
        distance_ft = distance_voxels * self.VOXELS_TO_FEET

        # --- Observer vision -------------------------------------------------
        obs_vision: Optional[Vision] = observer_entity.get_component(Vision)
        vision_type = obs_vision.vision_type if obs_vision is not None else VisionType.NORMAL
        vision_range_ft = obs_vision.range_ft if obs_vision is not None else 60.0

        in_range = distance_ft <= vision_range_ft

        # --- Light level at target -------------------------------------------
        if vision_type == VisionType.LOW_LIGHT_VISION:
            raw_level = self._light_system.get_light_level_for_vision(
                tgt_pos.x, tgt_pos.y, tgt_pos.z, "Low-Light Vision"
            )
        else:
            raw_level = self._light_system.get_light_level(
                tgt_pos.x, tgt_pos.y, tgt_pos.z
            )

        # --- Darkvision override ---------------------------------------------
        effective_level = raw_level
        if vision_type == VisionType.DARKVISION and raw_level == LightLevel.DARKNESS:
            darkvision_range_ft = obs_vision.range_ft if obs_vision is not None else 60.0
            if distance_ft <= darkvision_range_ft:
                effective_level = LightLevel.BRIGHT

        # --- Concealment & visibility ----------------------------------------
        if effective_level == LightLevel.BRIGHT:
            concealment = 0
        elif effective_level == LightLevel.DIM:
            concealment = 20
        else:
            concealment = 50

        # Entity is visible if in range AND not in impenetrable darkness
        visible = in_range and concealment < 100

        return VisibilityResult(
            visible=visible,
            light_level=effective_level,
            distance_ft=distance_ft,
            in_range=in_range,
            concealment=concealment,
        )

    def update(self) -> None:
        """VisionSystem has no per-tick work; visibility is queried on demand."""
