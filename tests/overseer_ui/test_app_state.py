"""Tests for PH5-001 · PH5-005 — UIMode enum + AppStateManager + screen transitions."""
from __future__ import annotations

import threading
import pytest

from src.overseer_ui.textual_app import (
    UIMode,
    AppStateManager,
)


# ---------------------------------------------------------------------------
# PH5-001 · UIMode
# ---------------------------------------------------------------------------

class TestUIMode:
    def test_members(self):
        assert UIMode.OVERWORLD == "overworld"
        assert UIMode.TOWN_MERCHANT == "town_merchant"
        assert UIMode.TACTICAL_DUNGEON == "tactical_dungeon"

    def test_is_str(self):
        assert isinstance(UIMode.OVERWORLD, str)

    def test_is_enum(self):
        import enum
        assert isinstance(UIMode.OVERWORLD, enum.Enum)


# ---------------------------------------------------------------------------
# PH5-001 · AppStateManager
# ---------------------------------------------------------------------------

class TestAppStateManager:
    def _fresh(self) -> AppStateManager:
        return AppStateManager()

    def test_default_mode(self):
        m = self._fresh()
        assert m.mode == UIMode.OVERWORLD

    def test_default_active_town_id_is_none(self):
        m = self._fresh()
        assert m.active_town_id is None

    def test_default_dungeon_floor(self):
        m = self._fresh()
        assert m.active_dungeon_floor == 0

    def test_has_lock(self):
        m = self._fresh()
        assert isinstance(m.transition_lock, type(threading.Lock()))

    def test_slots_no_dict(self):
        m = self._fresh()
        assert not hasattr(m, "__dict__")

    # ------------------------------------------------------------------
    # transition() — valid transitions
    # ------------------------------------------------------------------

    def test_transition_overworld_to_town(self):
        m = self._fresh()
        result = m.transition(UIMode.TOWN_MERCHANT, town_id="town_abc")
        assert result is True
        assert m.mode == UIMode.TOWN_MERCHANT
        assert m.active_town_id == "town_abc"

    def test_transition_overworld_to_dungeon(self):
        m = self._fresh()
        result = m.transition(UIMode.TACTICAL_DUNGEON, dungeon_floor=2)
        assert result is True
        assert m.mode == UIMode.TACTICAL_DUNGEON
        assert m.active_dungeon_floor == 2

    def test_transition_town_back_to_overworld(self):
        m = self._fresh()
        m.transition(UIMode.TOWN_MERCHANT, town_id="t1")
        m.transition(UIMode.OVERWORLD)
        assert m.mode == UIMode.OVERWORLD

    def test_transition_dungeon_back_to_overworld(self):
        m = self._fresh()
        m.transition(UIMode.TACTICAL_DUNGEON, dungeon_floor=1)
        m.transition(UIMode.OVERWORLD)
        assert m.mode == UIMode.OVERWORLD

    # ------------------------------------------------------------------
    # transition() — invalid transitions raise ValueError
    # ------------------------------------------------------------------

    def test_invalid_transition_town_to_dungeon_raises(self):
        m = self._fresh()
        m.transition(UIMode.TOWN_MERCHANT, town_id="t1")
        with pytest.raises(ValueError):
            m.transition(UIMode.TACTICAL_DUNGEON)

    def test_invalid_transition_dungeon_to_town_raises(self):
        m = self._fresh()
        m.transition(UIMode.TACTICAL_DUNGEON)
        with pytest.raises(ValueError):
            m.transition(UIMode.TOWN_MERCHANT)

    def test_invalid_transition_overworld_to_overworld_raises(self):
        m = self._fresh()
        with pytest.raises(ValueError):
            m.transition(UIMode.OVERWORLD)

    # ------------------------------------------------------------------
    # Thread safety — concurrent transition calls
    # ------------------------------------------------------------------

    def test_concurrent_transitions_do_not_corrupt_state(self):
        m = self._fresh()
        errors: list[Exception] = []

        def _cycle():
            try:
                for _ in range(50):
                    try:
                        m.transition(UIMode.TOWN_MERCHANT, town_id="t")
                    except ValueError:
                        pass
                    try:
                        m.transition(UIMode.OVERWORLD)
                    except ValueError:
                        pass
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=_cycle) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread errors: {errors}"
        # Mode must be one of the valid values.
        assert m.mode in set(UIMode)


# ---------------------------------------------------------------------------
# PH5-005 · _resolve_screen_transition
# ---------------------------------------------------------------------------

class TestResolveScreenTransition:
    """Tests for the _resolve_screen_transition private helper."""

    def _fresh_manager(self) -> AppStateManager:
        """Return a fresh AppStateManager in OVERWORLD mode."""
        return AppStateManager()

    def test_no_world_state_towns_returns_none(self):
        from src.game.player_controller import _resolve_screen_transition
        # Minimal world state with no towns or dungeon floors.
        class _WS:
            towns = []
            dungeon_floors = []

        # Reset _app_state to OVERWORLD before test.
        from src.overseer_ui.textual_app import _app_state, UIMode, _VALID_TRANSITIONS
        # Force mode to OVERWORLD.
        with _app_state.transition_lock:
            _app_state.mode = UIMode.OVERWORLD

        result = _resolve_screen_transition((5, 64, 5), _WS())
        assert result is None

    def test_returns_none_for_non_matching_position(self):
        from src.game.player_controller import _resolve_screen_transition

        class _MockTown:
            town_id = "t1"
            voxel_position = (0, 64, 0)

        class _WS:
            towns = [_MockTown()]
            dungeon_floors = []

        from src.overseer_ui.textual_app import _app_state, UIMode
        with _app_state.transition_lock:
            _app_state.mode = UIMode.OVERWORLD

        result = _resolve_screen_transition((99, 64, 99), _WS())
        assert result is None

    def test_returns_town_merchant_on_town_match(self):
        from src.game.player_controller import _resolve_screen_transition

        class _MockTown:
            town_id = "town_xyz"
            voxel_position = (10, 64, 10)

        class _WS:
            towns = [_MockTown()]
            dungeon_floors = []

        from src.overseer_ui.textual_app import _app_state, UIMode
        with _app_state.transition_lock:
            _app_state.mode = UIMode.OVERWORLD

        result = _resolve_screen_transition((10, 64, 10), _WS())
        assert result == UIMode.TOWN_MERCHANT.value

    def test_returns_tactical_dungeon_on_floor_match(self):
        from src.game.player_controller import _resolve_screen_transition

        class _MockFloor:
            entry_voxel = (20, 64, 20)

        class _WS:
            towns = []
            dungeon_floors = [_MockFloor()]

        from src.overseer_ui.textual_app import _app_state, UIMode
        with _app_state.transition_lock:
            _app_state.mode = UIMode.OVERWORLD

        result = _resolve_screen_transition((20, 64, 20), _WS())
        assert result == UIMode.TACTICAL_DUNGEON.value
