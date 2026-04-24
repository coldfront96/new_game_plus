"""
tests/rules_engine/test_traps.py
----------------------------------
Pytest suite for src/rules_engine/traps.py.

Covers T-004 (TrapBase schema), T-016 (search resolvers), T-017 (disable resolver).
"""

from __future__ import annotations

import pytest

from src.rules_engine.traps import (
    DisableResult,
    ResetType,
    TrapBase,
    TrapType,
    TriggerType,
    find_trap_active,
    resolve_trap_disable,
    resolve_trap_search,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_trap(
    name: str = "Test Trap",
    cr: float = 1.0,
    trap_type: TrapType = TrapType.MECHANICAL,
    trigger: TriggerType = TriggerType.LOCATION,
    reset: ResetType = ResetType.AUTOMATIC,
    search_dc: int = 20,
    disable_dc: int = 20,
) -> TrapBase:
    return TrapBase(
        name=name,
        cr=cr,
        trap_type=trap_type,
        trigger=trigger,
        reset=reset,
        search_dc=search_dc,
        disable_dc=disable_dc,
    )


# ---------------------------------------------------------------------------
# T-004: TrapBase creation and enum values
# ---------------------------------------------------------------------------

class TestTrapBaseCreation:
    def test_basic_instantiation(self):
        trap = _make_trap()
        assert trap.name == "Test Trap"
        assert trap.cr == 1.0
        assert trap.search_dc == 20
        assert trap.disable_dc == 20

    def test_fractional_cr(self):
        trap = _make_trap(cr=0.5)
        assert trap.cr == 0.5

    def test_trap_type_mechanical(self):
        trap = _make_trap(trap_type=TrapType.MECHANICAL)
        assert trap.trap_type == TrapType.MECHANICAL

    def test_trap_type_magic(self):
        trap = _make_trap(trap_type=TrapType.MAGIC)
        assert trap.trap_type == TrapType.MAGIC

    def test_all_trigger_types(self):
        for trigger in TriggerType:
            trap = _make_trap(trigger=trigger)
            assert trap.trigger is trigger

    def test_all_reset_types(self):
        for reset in ResetType:
            trap = _make_trap(reset=reset)
            assert trap.reset is reset

    def test_slots_no_dict(self):
        trap = _make_trap()
        assert not hasattr(trap, "__dict__")

    def test_enum_membership_trap_type(self):
        assert {m.value for m in TrapType} == {"mechanical", "magic"}

    def test_enum_membership_trigger_type(self):
        values = {m.value for m in TriggerType}
        assert values == {"location", "proximity", "touch", "sound", "visual", "timed"}

    def test_enum_membership_reset_type(self):
        values = {m.value for m in ResetType}
        assert values == {"no_reset", "repair", "automatic", "manual"}

    def test_enum_membership_disable_result(self):
        values = {m.value for m in DisableResult}
        assert values == {"disabled", "failed", "triggered"}


# ---------------------------------------------------------------------------
# T-016: resolve_trap_search (passive)
# ---------------------------------------------------------------------------

class TestResolvePassiveSearch:
    def test_passive_exactly_meets_dc(self):
        trap = _make_trap(search_dc=20)
        # 10 + 10 = 20 ≥ 20
        assert resolve_trap_search(trap, searcher_search_modifier=10) is True

    def test_passive_exceeds_dc(self):
        trap = _make_trap(search_dc=15)
        assert resolve_trap_search(trap, searcher_search_modifier=10) is True

    def test_passive_below_dc(self):
        trap = _make_trap(search_dc=25)
        assert resolve_trap_search(trap, searcher_search_modifier=10) is False

    def test_passive_zero_modifier_just_meets(self):
        trap = _make_trap(search_dc=10)
        assert resolve_trap_search(trap, searcher_search_modifier=0) is True

    def test_passive_zero_modifier_misses(self):
        trap = _make_trap(search_dc=11)
        assert resolve_trap_search(trap, searcher_search_modifier=0) is False

    def test_very_high_search_dc(self):
        trap = _make_trap(search_dc=35)
        assert resolve_trap_search(trap, searcher_search_modifier=20) is False

    def test_negative_modifier_fails(self):
        trap = _make_trap(search_dc=15)
        # 10 + (-2) = 8 < 15
        assert resolve_trap_search(trap, searcher_search_modifier=-2) is False


# ---------------------------------------------------------------------------
# T-016: find_trap_active (active roll)
# ---------------------------------------------------------------------------

class TestFindTrapActive:
    def test_active_roll_meets_dc(self):
        trap = _make_trap(search_dc=20)
        assert find_trap_active(trap, active_roll=20) is True

    def test_active_roll_exceeds_dc(self):
        trap = _make_trap(search_dc=15)
        assert find_trap_active(trap, active_roll=22) is True

    def test_active_roll_below_dc(self):
        trap = _make_trap(search_dc=20)
        assert find_trap_active(trap, active_roll=19) is False

    def test_nat_1_fails_high_dc(self):
        trap = _make_trap(search_dc=20)
        assert find_trap_active(trap, active_roll=1) is False

    def test_nat_20_beats_reasonable_dc(self):
        trap = _make_trap(search_dc=20)
        assert find_trap_active(trap, active_roll=20) is True


# ---------------------------------------------------------------------------
# T-017: resolve_trap_disable
# ---------------------------------------------------------------------------

class TestResolveTrapDisable:
    def test_disabled_on_exact_dc(self):
        trap = _make_trap(disable_dc=20)
        assert resolve_trap_disable(trap, disable_roll=20) == DisableResult.DISABLED

    def test_disabled_above_dc(self):
        trap = _make_trap(disable_dc=20)
        assert resolve_trap_disable(trap, disable_roll=25) == DisableResult.DISABLED

    def test_failed_one_below_dc(self):
        trap = _make_trap(disable_dc=20)
        # 19 < 20 and 19 > 20-5=15 → FAILED
        assert resolve_trap_disable(trap, disable_roll=19) == DisableResult.FAILED

    def test_failed_four_below_dc(self):
        trap = _make_trap(disable_dc=20)
        # 16 < 20 and 16 > 15 → FAILED
        assert resolve_trap_disable(trap, disable_roll=16) == DisableResult.FAILED

    def test_triggered_exactly_5_below_dc(self):
        trap = _make_trap(disable_dc=20)
        # 15 ≤ 20-5=15 → TRIGGERED
        assert resolve_trap_disable(trap, disable_roll=15) == DisableResult.TRIGGERED

    def test_triggered_more_than_5_below_dc(self):
        trap = _make_trap(disable_dc=20)
        assert resolve_trap_disable(trap, disable_roll=5) == DisableResult.TRIGGERED

    def test_triggered_roll_of_1(self):
        trap = _make_trap(disable_dc=20)
        assert resolve_trap_disable(trap, disable_roll=1) == DisableResult.TRIGGERED

    def test_high_dc_magic_trap(self):
        trap = _make_trap(trap_type=TrapType.MAGIC, disable_dc=30)
        assert resolve_trap_disable(trap, disable_roll=30) == DisableResult.DISABLED
        assert resolve_trap_disable(trap, disable_roll=27) == DisableResult.FAILED
        assert resolve_trap_disable(trap, disable_roll=25) == DisableResult.TRIGGERED


# ---------------------------------------------------------------------------
# T-040: MechanicalTrap creation
# ---------------------------------------------------------------------------

from src.rules_engine.traps import (
    MechanicalTrap,
    MagicalTrap,
    RoomContents,
    DungeonLevel,
    generate_mechanical_trap,
    generate_magical_trap,
    roll_room_contents,
    generate_dungeon_level,
)

import random


class TestMechanicalTrapCreation:
    def _make(self, **kwargs) -> MechanicalTrap:
        defaults = dict(
            name="Spear Trap",
            cr=1.0,
            trap_type=TrapType.MECHANICAL,
            trigger=TriggerType.LOCATION,
            reset=ResetType.AUTOMATIC,
            search_dc=20,
            disable_dc=20,
            damage_dice="1d8",
            attack_bonus=10,
            save_type=None,
            save_dc=None,
            reflex_negates=False,
        )
        defaults.update(kwargs)
        return MechanicalTrap(**defaults)

    def test_basic_instantiation(self):
        t = self._make()
        assert t.name == "Spear Trap"
        assert t.cr == 1.0
        assert t.damage_dice == "1d8"
        assert t.attack_bonus == 10
        assert t.save_type is None
        assert t.save_dc is None
        assert t.reflex_negates is False

    def test_save_type_reflex(self):
        t = self._make(attack_bonus=None, save_type="Reflex", save_dc=20, reflex_negates=True)
        assert t.save_type == "Reflex"
        assert t.save_dc == 20
        assert t.reflex_negates is True

    def test_slots_no_dict(self):
        t = self._make()
        assert not hasattr(t, "__dict__")

    def test_trap_type_is_mechanical(self):
        t = self._make()
        assert t.trap_type == TrapType.MECHANICAL

    def test_damage_dice_is_str(self):
        t = self._make(damage_dice="2d6+5")
        assert isinstance(t.damage_dice, str)

    def test_fractional_cr(self):
        t = self._make(cr=0.5)
        assert t.cr == 0.5

    def test_none_attack_bonus(self):
        t = self._make(attack_bonus=None)
        assert t.attack_bonus is None

    def test_fort_save_type(self):
        t = self._make(save_type="Fort", save_dc=15)
        assert t.save_type == "Fort"


class TestGenerateMechanicalTrap:
    def test_cr1_returns_mechanical_trap(self):
        rng = random.Random(42)
        t = generate_mechanical_trap(1.0, rng)
        assert isinstance(t, MechanicalTrap)

    def test_cr1_trap_type_mechanical(self):
        rng = random.Random(1)
        t = generate_mechanical_trap(1.0, rng)
        assert t.trap_type == TrapType.MECHANICAL

    def test_cr1_damage_dice_is_str(self):
        rng = random.Random(7)
        t = generate_mechanical_trap(1.0, rng)
        assert isinstance(t.damage_dice, str)
        assert len(t.damage_dice) > 0

    def test_cr1_fields_set(self):
        rng = random.Random(99)
        t = generate_mechanical_trap(1.0, rng)
        assert t.name
        assert t.cr > 0
        assert t.search_dc > 0
        assert t.disable_dc > 0

    def test_cr5_returns_trap(self):
        rng = random.Random(5)
        t = generate_mechanical_trap(5.0, rng)
        assert isinstance(t, MechanicalTrap)

    def test_cr10_returns_trap(self):
        rng = random.Random(10)
        t = generate_mechanical_trap(10.0, rng)
        assert isinstance(t, MechanicalTrap)

    def test_cr_out_of_range_falls_back(self):
        rng = random.Random(0)
        t = generate_mechanical_trap(99.0, rng)
        assert isinstance(t, MechanicalTrap)

    def test_no_rng_still_works(self):
        t = generate_mechanical_trap(2.0)
        assert isinstance(t, MechanicalTrap)

    def test_cr2_within_range(self):
        rng = random.Random(42)
        t = generate_mechanical_trap(2.0, rng)
        assert abs(t.cr - 2.0) <= 1.0

    def test_reflex_negates_is_bool(self):
        rng = random.Random(13)
        t = generate_mechanical_trap(1.0, rng)
        assert isinstance(t.reflex_negates, bool)


# ---------------------------------------------------------------------------
# T-041: MagicalTrap creation
# ---------------------------------------------------------------------------

class TestMagicalTrapCreation:
    def _make(self, **kwargs) -> MagicalTrap:
        defaults = dict(
            name="Fire Trap",
            cr=2.0,
            trap_type=TrapType.MAGIC,
            trigger=TriggerType.TOUCH,
            reset=ResetType.NO_RESET,
            search_dc=26,
            disable_dc=26,
            spell_effect="fire trap",
            caster_level=3,
            save_dc=13,
            aoe="5 ft radius",
        )
        defaults.update(kwargs)
        return MagicalTrap(**defaults)

    def test_basic_instantiation(self):
        t = self._make()
        assert t.name == "Fire Trap"
        assert t.spell_effect == "fire trap"
        assert t.caster_level == 3
        assert t.save_dc == 13
        assert t.aoe == "5 ft radius"

    def test_slots_no_dict(self):
        t = self._make()
        assert not hasattr(t, "__dict__")

    def test_trap_type_is_magic(self):
        t = self._make()
        assert t.trap_type == TrapType.MAGIC

    def test_none_save_dc(self):
        t = self._make(save_dc=None, aoe=None)
        assert t.save_dc is None
        assert t.aoe is None

    def test_caster_level_is_int(self):
        t = self._make()
        assert isinstance(t.caster_level, int)


class TestGenerateMagicalTrap:
    def test_cr1_returns_magical_trap(self):
        rng = random.Random(42)
        t = generate_magical_trap(1.0, rng)
        assert isinstance(t, MagicalTrap)

    def test_cr1_trap_type_magic(self):
        rng = random.Random(1)
        t = generate_magical_trap(1.0, rng)
        assert t.trap_type == TrapType.MAGIC

    def test_cr5_returns_trap(self):
        rng = random.Random(5)
        t = generate_magical_trap(5.0, rng)
        assert isinstance(t, MagicalTrap)

    def test_cr10_returns_trap(self):
        rng = random.Random(10)
        t = generate_magical_trap(10.0, rng)
        assert isinstance(t, MagicalTrap)

    def test_spell_effect_is_str(self):
        rng = random.Random(7)
        t = generate_magical_trap(3.0, rng)
        assert isinstance(t.spell_effect, str)
        assert len(t.spell_effect) > 0

    def test_caster_level_positive(self):
        rng = random.Random(99)
        t = generate_magical_trap(5.0, rng)
        assert t.caster_level > 0

    def test_no_rng_still_works(self):
        t = generate_magical_trap(2.0)
        assert isinstance(t, MagicalTrap)

    def test_cr_out_of_range_falls_back(self):
        rng = random.Random(0)
        t = generate_magical_trap(99.0, rng)
        assert isinstance(t, MagicalTrap)

    def test_cr1_alarm_trap_possible(self):
        # With a seeded rng the only CR-1 template is "Alarm Trap"
        rng = random.Random(42)
        t = generate_magical_trap(1.0, rng)
        assert t.name == "Alarm Trap"

    def test_search_dc_positive(self):
        rng = random.Random(3)
        t = generate_magical_trap(3.0, rng)
        assert t.search_dc > 0


# ---------------------------------------------------------------------------
# T-047: RoomContents creation and roll_room_contents
# ---------------------------------------------------------------------------

class TestRoomContentsCreation:
    def test_all_true(self):
        rc = RoomContents(monster=True, trap=True, treasure=True, empty=False)
        assert rc.monster is True
        assert rc.trap is True
        assert rc.treasure is True
        assert rc.empty is False

    def test_empty_room(self):
        rc = RoomContents(monster=False, trap=False, treasure=False, empty=True)
        assert rc.empty is True

    def test_slots_no_dict(self):
        rc = RoomContents(monster=False, trap=False, treasure=False, empty=True)
        assert not hasattr(rc, "__dict__")


class TestRollRoomContents:
    def test_returns_room_contents(self):
        rng = random.Random(42)
        rc = roll_room_contents(1, rng)
        assert isinstance(rc, RoomContents)

    def test_boolean_fields(self):
        rng = random.Random(1)
        rc = roll_room_contents(1, rng)
        for field in (rc.monster, rc.trap, rc.treasure, rc.empty):
            assert isinstance(field, bool)

    def test_empty_correct_when_nothing_set(self):
        # Force a seed that produces an empty room
        for seed in range(200):
            rng = random.Random(seed)
            rc = roll_room_contents(1, rng)
            if not rc.monster and not rc.trap and not rc.treasure:
                assert rc.empty is True
                break

    def test_deep_levels_higher_monster_rate(self):
        """Level 10 should produce more monsters than level 1 (statistical)."""
        rng1 = random.Random(0)
        rng10 = random.Random(0)
        n = 1000
        low = sum(roll_room_contents(1, rng1).monster for _ in range(n))
        high = sum(roll_room_contents(10, rng10).monster for _ in range(n))
        assert high > low

    def test_no_rng_still_works(self):
        rc = roll_room_contents(1)
        assert isinstance(rc, RoomContents)


# ---------------------------------------------------------------------------
# T-057: DungeonLevel creation and generate_dungeon_level
# ---------------------------------------------------------------------------

class TestDungeonLevelCreation:
    def test_basic_instantiation(self):
        rooms = [RoomContents(monster=False, trap=False, treasure=False, empty=True)]
        dl = DungeonLevel(rooms=rooms)
        assert len(dl.rooms) == 1

    def test_slots_no_dict(self):
        dl = DungeonLevel(rooms=[])
        assert not hasattr(dl, "__dict__")


class TestGenerateDungeonLevel:
    def test_correct_number_of_rooms(self):
        rng = random.Random(42)
        dl = generate_dungeon_level(1, 10, rng)
        assert len(dl.rooms) == 10

    def test_returns_dungeon_level(self):
        rng = random.Random(1)
        dl = generate_dungeon_level(1, 5, rng)
        assert isinstance(dl, DungeonLevel)

    def test_rooms_are_room_contents(self):
        rng = random.Random(7)
        dl = generate_dungeon_level(2, 8, rng)
        for room in dl.rooms:
            assert isinstance(room, RoomContents)

    def test_trap_rooms_not_empty(self):
        rng = random.Random(99)
        dl = generate_dungeon_level(3, 20, rng)
        for room in dl.rooms:
            if room.trap:
                assert room.empty is False

    def test_zero_rooms(self):
        rng = random.Random(0)
        dl = generate_dungeon_level(1, 0, rng)
        assert dl.rooms == []

    def test_no_rng_still_works(self):
        dl = generate_dungeon_level(1, 3)
        assert len(dl.rooms) == 3

    def test_level1_vs_level8_trap_ratio(self):
        """Statistical: level 8 dungeons should have at least as many traps as level 1."""
        n_rooms = 500
        rng1 = random.Random(0)
        rng8 = random.Random(0)
        dl1 = generate_dungeon_level(1, n_rooms, rng1)
        dl8 = generate_dungeon_level(8, n_rooms, rng8)
        traps1 = sum(r.trap for r in dl1.rooms)
        traps8 = sum(r.trap for r in dl8.rooms)
        assert traps8 >= traps1
