"""
tests/rules_engine/test_progression.py
---------------------------------------
Unit tests for src.rules_engine.progression (XPManager, level_up).
"""

import pytest

from src.core.event_bus import EventBus
from src.rules_engine.character_35e import Character35e
from src.rules_engine.progression import (
    LevelingResult,
    Progression,
    XPManager,
    level_up,
    xp_for_level,
)
from src.ai_sim.systems import ProgressionSystem


# ---------------------------------------------------------------------------
# XP Table Tests
# ---------------------------------------------------------------------------

class TestXPTable:
    """Verify the standard 3.5e XP formula: level × (level - 1) × 500."""

    def test_level_1_requires_0_xp(self):
        assert xp_for_level(1) == 0

    def test_level_2_requires_1000_xp(self):
        assert xp_for_level(2) == 1000

    def test_level_3_requires_3000_xp(self):
        assert xp_for_level(3) == 3000

    def test_level_5_requires_10000_xp(self):
        assert xp_for_level(5) == 10000

    def test_level_10_requires_45000_xp(self):
        assert xp_for_level(10) == 45000

    def test_level_20_requires_190000_xp(self):
        assert xp_for_level(20) == 190000

    def test_level_below_1_returns_0(self):
        assert xp_for_level(0) == 0
        assert xp_for_level(-1) == 0


# ---------------------------------------------------------------------------
# XPManager Tests
# ---------------------------------------------------------------------------

class TestXPManager:
    """Tests for XP tracking and level-up detection."""

    def test_initial_state(self):
        mgr = XPManager()
        assert mgr.current_xp == 0
        assert mgr.current_level == 1

    def test_award_xp_adds_to_total(self):
        mgr = XPManager()
        mgr.award_xp(500)
        assert mgr.current_xp == 500
        mgr.award_xp(300)
        assert mgr.current_xp == 800

    def test_award_xp_ignores_negative(self):
        mgr = XPManager()
        mgr.award_xp(-100)
        assert mgr.current_xp == 0

    def test_award_xp_ignores_zero(self):
        mgr = XPManager()
        mgr.award_xp(0)
        assert mgr.current_xp == 0

    def test_check_level_up_not_ready(self):
        mgr = XPManager()
        mgr.award_xp(500)
        result = mgr.check_level_up()
        assert result.leveled_up is False
        assert result.current_level == 1
        assert result.current_xp == 500
        assert result.xp_needed == 1000

    def test_check_level_up_ready_at_1000_xp(self):
        mgr = XPManager()
        mgr.award_xp(1000)
        result = mgr.check_level_up()
        assert result.leveled_up is True
        assert result.current_level == 1
        assert result.current_xp == 1000
        assert result.xp_needed == 1000

    def test_check_level_up_ready_above_threshold(self):
        mgr = XPManager()
        mgr.award_xp(1500)
        result = mgr.check_level_up()
        assert result.leveled_up is True


# ---------------------------------------------------------------------------
# Dataclass Slots Tests
# ---------------------------------------------------------------------------

class TestDataclassSlots:
    """Ensure memory-efficient slots are enabled."""

    def test_leveling_result_has_slots(self):
        assert hasattr(LevelingResult, "__slots__")

    def test_progression_has_slots(self):
        assert hasattr(Progression, "__slots__")


# ---------------------------------------------------------------------------
# level_up Function Tests
# ---------------------------------------------------------------------------

class TestLevelUp:
    """Tests for the level_up advancement function."""

    def test_level_up_increases_character_level(self):
        char = Character35e(name="Aldric", char_class="Fighter", level=1)
        mgr = XPManager(current_xp=1000, current_level=1)
        level_up(char, mgr)
        assert char.level == 2
        assert mgr.current_level == 2

    def test_level_up_returns_progression_record(self):
        char = Character35e(
            name="Aldric", char_class="Fighter", level=1, constitution=14
        )
        mgr = XPManager(current_xp=1000, current_level=1)
        result = level_up(char, mgr)
        assert isinstance(result, Progression)
        assert result.new_level == 2
        # Fighter HD=10, avg=6, CON mod=+2 → HP gained=8
        assert result.hp_gained == 8
        # Fighter skill points base=2, INT mod=0 → 2
        assert result.skill_points == 2

    def test_level_up_hp_minimum_1(self):
        """A character with very low CON still gains at least 1 HP."""
        char = Character35e(
            name="Weakling", char_class="Wizard", level=1, constitution=3
        )
        mgr = XPManager(current_xp=1000, current_level=1)
        result = level_up(char, mgr)
        # Wizard HD=4, avg=3, CON mod=-4 → max(1, -1) = 1
        assert result.hp_gained == 1

    def test_level_up_skill_points_minimum_1(self):
        """Skill points cannot go below 1 even with INT penalty."""
        char = Character35e(
            name="Dullard", char_class="Fighter", level=1, intelligence=3
        )
        mgr = XPManager(current_xp=1000, current_level=1)
        result = level_up(char, mgr)
        # Fighter base=2, INT mod=-4 → max(1, -2) = 1
        assert result.skill_points == 1

    def test_rogue_gets_more_skill_points(self):
        char = Character35e(
            name="Shadow", char_class="Rogue", level=1, intelligence=14
        )
        mgr = XPManager(current_xp=1000, current_level=1)
        result = level_up(char, mgr)
        # Rogue base=8, INT mod=+2 → 10
        assert result.skill_points == 10


# ---------------------------------------------------------------------------
# Integration: Award 1000 XP to Level 1 → Level 2
# ---------------------------------------------------------------------------

class TestIntegrationLevelUp:
    """Verify that awarding 1,000 XP to a Level 1 character correctly
    triggers a level-up to Level 2.
    """

    def test_1000_xp_triggers_level_up_to_2(self):
        char = Character35e(
            name="Aldric",
            char_class="Fighter",
            level=1,
            strength=16,
            dexterity=13,
            constitution=14,
        )
        mgr = XPManager()
        mgr.award_xp(1000)

        result = mgr.check_level_up()
        assert result.leveled_up is True

        progression = level_up(char, mgr)
        assert char.level == 2
        assert progression.new_level == 2
        assert mgr.current_level == 2

    def test_999_xp_does_not_trigger_level_up(self):
        char = Character35e(name="Aldric", char_class="Fighter", level=1)
        mgr = XPManager()
        mgr.award_xp(999)

        result = mgr.check_level_up()
        assert result.leveled_up is False
        assert char.level == 1


# ---------------------------------------------------------------------------
# ProgressionSystem Tests
# ---------------------------------------------------------------------------

class TestProgressionSystem:
    """Tests for the event-driven ProgressionSystem."""

    def test_combat_result_awards_xp_on_defeat(self):
        bus = EventBus()
        system = ProgressionSystem(bus)
        attacker = Character35e(name="Hero", char_class="Fighter", level=1)
        defender = Character35e(name="Goblin", char_class="Rogue", level=1)
        system.register_character(attacker)

        # Simulate combat_result with defeated=True
        bus.publish("combat_result", {
            "attacker": attacker,
            "defender": defender,
            "defeated": True,
        })

        mgr = system.get_xp_manager(attacker.char_id)
        assert mgr is not None
        assert mgr.current_xp == 300  # CR 1 → 300 XP

    def test_combat_result_no_xp_if_not_defeated(self):
        bus = EventBus()
        system = ProgressionSystem(bus)
        attacker = Character35e(name="Hero", char_class="Fighter", level=1)
        defender = Character35e(name="Goblin", char_class="Rogue", level=1)
        system.register_character(attacker)

        bus.publish("combat_result", {
            "attacker": attacker,
            "defender": defender,
            "defeated": False,
        })

        mgr = system.get_xp_manager(attacker.char_id)
        assert mgr.current_xp == 0

    def test_skill_check_success_awards_xp(self):
        bus = EventBus()
        system = ProgressionSystem(bus)
        char = Character35e(name="Scout", char_class="Ranger", level=1)
        system.register_character(char)

        bus.publish("skill_check_success", {"char_id": char.char_id})

        mgr = system.get_xp_manager(char.char_id)
        assert mgr.current_xp == 50

    def test_combat_xp_triggers_level_up(self):
        """Defeating enough enemies triggers automatic level-up."""
        bus = EventBus()
        system = ProgressionSystem(bus)
        hero = Character35e(name="Hero", char_class="Fighter", level=1)
        system.register_character(hero)

        level_up_events = []
        bus.subscribe("level_up", lambda p: level_up_events.append(p))

        # Award enough combat XP to reach 1000 (CR 1 = 300 XP each)
        # Need 4 defeats: 4 × 300 = 1200 ≥ 1000
        for _ in range(4):
            defender = Character35e(name="Goblin", char_class="Rogue", level=1)
            bus.publish("combat_result", {
                "attacker": hero,
                "defender": defender,
                "defeated": True,
            })

        assert hero.level == 2
        assert len(level_up_events) == 1
        assert level_up_events[0]["new_level"] == 2

    def test_update_is_noop(self):
        """ProgressionSystem.update() does nothing (event-driven)."""
        bus = EventBus()
        system = ProgressionSystem(bus)
        system.update()  # Should not raise
