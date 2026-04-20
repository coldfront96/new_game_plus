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
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Optional

from src.ai_sim.components import Health
from src.core.event_bus import EventBus
from src.loot_math.item import Item, ItemType
from src.rules_engine.character_35e import Character35e
from src.rules_engine.combat import AttackResolver, CombatResult
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
        """Resolve all pending attack intents and publish results."""
        intents = list(self._pending)
        self._pending.clear()

        for intent in intents:
            # Determine weapon damage dice overrides
            dmg_count = 0
            dmg_sides = 0
            dmg_bonus = 0
            if intent.weapon and intent.weapon.item_type == ItemType.WEAPON:
                dmg_bonus = int(intent.weapon.effective_damage)

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
        """Resolve all pending mine intents and publish results."""
        intents = list(self._pending)
        self._pending.clear()

        for intent in intents:
            damage = self.calculate_mining_damage(
                intent.character, intent.tool
            )
            remaining = intent.block.mine(damage)
            result = MineResult(
                damage_dealt=damage,
                remaining_durability=remaining,
                block_destroyed=intent.block.is_destroyed(),
            )
            self._event_bus.publish("mine_result", result)

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
        self._pending_positions: List[tuple] = []
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
