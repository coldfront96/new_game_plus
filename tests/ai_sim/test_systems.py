"""
tests/ai_sim/test_systems.py
-----------------------------
Unit tests for src.ai_sim.systems (CombatSystem, InteractionSystem).
"""

from unittest.mock import patch

import pytest

from src.ai_sim.systems import (
    AttackIntent,
    CombatSystem,
    InteractionSystem,
    MineIntent,
    MineResult,
    System,
)
from src.core.event_bus import EventBus
from src.loot_math.item import Item, ItemType, Rarity
from src.rules_engine.character_35e import Character35e, Size
from src.rules_engine.combat import CombatResult
from src.rules_engine.dice import RollResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def bus():
    return EventBus()


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


@pytest.fixture
def goblin():
    return Character35e(
        name="Goblin",
        char_class="Rogue",
        level=1,
        strength=8,
        dexterity=14,
        size=Size.SMALL,
    )


# ---------------------------------------------------------------------------
# System base class
# ---------------------------------------------------------------------------

class TestSystemABC:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            System()

    def test_subclass_must_implement_update(self):
        class Incomplete(System):
            pass

        with pytest.raises(TypeError):
            Incomplete()

    def test_concrete_subclass_works(self):
        class Concrete(System):
            def update(self):
                pass

        s = Concrete()
        s.update()  # no error


# ---------------------------------------------------------------------------
# AttackIntent dataclass
# ---------------------------------------------------------------------------

class TestAttackIntent:
    def test_slots_enabled(self):
        assert hasattr(AttackIntent, "__slots__")

    def test_fields(self, fighter, goblin):
        intent = AttackIntent(attacker=fighter, defender=goblin)
        assert intent.attacker is fighter
        assert intent.defender is goblin
        assert intent.use_ranged is False
        assert intent.weapon is None


# ---------------------------------------------------------------------------
# MineIntent dataclass
# ---------------------------------------------------------------------------

class TestMineIntent:
    def test_slots_enabled(self):
        assert hasattr(MineIntent, "__slots__")

    def test_fields(self, fighter):
        from src.terrain.block import Block, Material
        block = Block(block_id=1, material=Material.STONE)
        intent = MineIntent(character=fighter, block=block)
        assert intent.character is fighter
        assert intent.block is block
        assert intent.tool is None


# ---------------------------------------------------------------------------
# MineResult dataclass
# ---------------------------------------------------------------------------

class TestMineResult:
    def test_slots_enabled(self):
        assert hasattr(MineResult, "__slots__")

    def test_fields(self):
        r = MineResult(damage_dealt=10, remaining_durability=90, block_destroyed=False)
        assert r.damage_dealt == 10
        assert r.remaining_durability == 90
        assert r.block_destroyed is False


# ---------------------------------------------------------------------------
# CombatSystem
# ---------------------------------------------------------------------------

class TestCombatSystem:
    def test_subscribes_to_attack_intent(self, bus):
        system = CombatSystem(bus)
        assert system.pending_count == 0

    def test_buffers_intent_on_publish(self, bus, fighter, goblin):
        system = CombatSystem(bus)
        intent = AttackIntent(attacker=fighter, defender=goblin)
        bus.publish("attack_intent", intent)
        assert system.pending_count == 1

    def test_ignores_non_intent_payloads(self, bus):
        system = CombatSystem(bus)
        bus.publish("attack_intent", {"not": "an intent"})
        assert system.pending_count == 0

    def test_update_clears_pending(self, bus, fighter, goblin):
        system = CombatSystem(bus)
        intent = AttackIntent(attacker=fighter, defender=goblin)
        bus.publish("attack_intent", intent)
        assert system.pending_count == 1
        system.update()
        assert system.pending_count == 0

    def test_update_publishes_combat_result(self, bus, fighter, goblin):
        system = CombatSystem(bus)
        results = []
        bus.subscribe("combat_result", lambda r: results.append(r))

        intent = AttackIntent(attacker=fighter, defender=goblin)
        bus.publish("attack_intent", intent)
        system.update()

        assert len(results) == 1
        assert isinstance(results[0], CombatResult)

    def test_multiple_intents_processed(self, bus, fighter, goblin):
        system = CombatSystem(bus)
        results = []
        bus.subscribe("combat_result", lambda r: results.append(r))

        for _ in range(3):
            bus.publish("attack_intent", AttackIntent(attacker=fighter, defender=goblin))
        system.update()

        assert len(results) == 3

    def test_weapon_adds_damage_bonus(self, bus, fighter, goblin):
        system = CombatSystem(bus)
        results = []
        bus.subscribe("combat_result", lambda r: results.append(r))

        sword = Item(name="Longsword", item_type=ItemType.WEAPON, rarity=Rarity.COMMON, base_damage=8)
        intent = AttackIntent(attacker=fighter, defender=goblin, weapon=sword)
        bus.publish("attack_intent", intent)

        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            mock_d20.return_value = RollResult(raw=18, modifier=8, total=26)
            mock_dmg.return_value = RollResult(raw=3, modifier=11, total=14)
            system.update()

        assert len(results) == 1


# ---------------------------------------------------------------------------
# InteractionSystem — mining damage calculation
# ---------------------------------------------------------------------------

class TestInteractionSystemDamage:
    def test_base_damage_with_str(self, fighter):
        """Mining damage = 5 (base) + STR mod."""
        dmg = InteractionSystem.calculate_mining_damage(fighter)
        # STR 16 → mod +3, so 5 + 3 = 8
        assert dmg == 8

    def test_low_str_minimum_one(self):
        """Very low STR should still yield at least 1 damage."""
        weakling = Character35e(name="Weakling", strength=1)
        dmg = InteractionSystem.calculate_mining_damage(weakling)
        # STR 1 → mod -5, base 5 + (-5) = 0 → clamped to 1
        assert dmg == 1

    def test_tool_adds_damage(self, fighter):
        pick = Item(name="Iron Pick", item_type=ItemType.TOOL, rarity=Rarity.COMMON, base_damage=10)
        dmg = InteractionSystem.calculate_mining_damage(fighter, tool=pick)
        # 5 (base) + 3 (STR) + 10 (tool) = 18
        assert dmg == 18

    def test_weapon_also_works_as_tool(self, fighter):
        sword = Item(name="Sword", item_type=ItemType.WEAPON, rarity=Rarity.COMMON, base_damage=8)
        dmg = InteractionSystem.calculate_mining_damage(fighter, tool=sword)
        # 5 + 3 + 8 = 16
        assert dmg == 16

    def test_non_tool_item_ignored(self, fighter):
        trinket = Item(name="Ring", item_type=ItemType.TRINKET, rarity=Rarity.COMMON)
        dmg = InteractionSystem.calculate_mining_damage(fighter, tool=trinket)
        # 5 + 3 = 8  (trinket ignored)
        assert dmg == 8

    def test_rare_tool_bonus(self, fighter):
        """Rarity stat multiplier should affect tool damage."""
        pick = Item(name="Rare Pick", item_type=ItemType.TOOL, rarity=Rarity.RARE, base_damage=10)
        dmg = InteractionSystem.calculate_mining_damage(fighter, tool=pick)
        # effective_damage = 10 * 1.35 = 13.5 → int = 13
        # 5 + 3 + 13 = 21
        assert dmg == 21


# ---------------------------------------------------------------------------
# InteractionSystem — event processing
# ---------------------------------------------------------------------------

class TestInteractionSystemEvents:
    def test_subscribes_to_mine_intent(self, bus):
        system = InteractionSystem(bus)
        assert system.pending_count == 0

    def test_buffers_mine_intent(self, bus, fighter):
        from src.terrain.block import Block, Material
        system = InteractionSystem(bus)
        block = Block(block_id=1, material=Material.STONE)
        bus.publish("mine_intent", MineIntent(character=fighter, block=block))
        assert system.pending_count == 1

    def test_ignores_non_intent_payloads(self, bus):
        system = InteractionSystem(bus)
        bus.publish("mine_intent", "garbage")
        assert system.pending_count == 0

    def test_update_clears_pending(self, bus, fighter):
        from src.terrain.block import Block, Material
        system = InteractionSystem(bus)
        block = Block(block_id=1, material=Material.STONE)
        bus.publish("mine_intent", MineIntent(character=fighter, block=block))
        system.update()
        assert system.pending_count == 0

    def test_update_publishes_mine_result(self, bus, fighter):
        from src.terrain.block import Block, Material
        system = InteractionSystem(bus)
        results = []
        bus.subscribe("mine_result", lambda r: results.append(r))

        block = Block(block_id=1, material=Material.STONE)
        bus.publish("mine_intent", MineIntent(character=fighter, block=block))
        system.update()

        assert len(results) == 1
        assert isinstance(results[0], MineResult)

    def test_mining_reduces_block_durability(self, bus, fighter):
        from src.terrain.block import Block, Material
        system = InteractionSystem(bus)
        results = []
        bus.subscribe("mine_result", lambda r: results.append(r))

        block = Block(block_id=1, material=Material.DIRT)  # durability 30
        bus.publish("mine_intent", MineIntent(character=fighter, block=block))
        system.update()

        r = results[0]
        expected_dmg = InteractionSystem.calculate_mining_damage(fighter)
        assert r.damage_dealt == expected_dmg
        assert r.remaining_durability == 30 - expected_dmg

    def test_block_destroyed_on_zero_durability(self, bus, fighter):
        from src.terrain.block import Block, Material
        system = InteractionSystem(bus)
        results = []
        bus.subscribe("mine_result", lambda r: results.append(r))

        # Leaves have 5 durability; fighter deals 8 damage → destroyed
        block = Block(block_id=1, material=Material.LEAVES)
        bus.publish("mine_intent", MineIntent(character=fighter, block=block))
        system.update()

        assert results[0].block_destroyed is True
        assert results[0].remaining_durability == 0

    def test_tool_increases_mining_damage(self, bus, fighter):
        from src.terrain.block import Block, Material
        system = InteractionSystem(bus)
        results = []
        bus.subscribe("mine_result", lambda r: results.append(r))

        pick = Item(name="Pick", item_type=ItemType.TOOL, rarity=Rarity.COMMON, base_damage=10)
        block = Block(block_id=1, material=Material.STONE)  # 100 durability
        bus.publish("mine_intent", MineIntent(character=fighter, block=block, tool=pick))
        system.update()

        expected_dmg = InteractionSystem.calculate_mining_damage(fighter, tool=pick)
        assert results[0].damage_dealt == expected_dmg
