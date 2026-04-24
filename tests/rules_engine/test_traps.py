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
