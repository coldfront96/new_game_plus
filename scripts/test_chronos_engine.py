#!/usr/bin/env python3
"""Chronos Engine verification script.

Verifies that firing 14,400 COMBAT_ROUND_END events (14,400 rounds × 6 s/round
= 86,400 s) advances the world clock by exactly 24 in-game hours.

Run from the repository root::

    python scripts/test_chronos_engine.py

Expected output::

    [PASS] 14,400 rounds → absolute_tick == 86,400 s
    [PASS] 14,400 rounds → 24 hours crossed (TIME_TICK hour events)
    [PASS] 14,400 rounds → 1 day crossed  (TIME_TICK day events)
    [PASS] engine.game_time.total_days == 1
    [PASS] Serialise / restore round-trip preserves absolute_tick
    All assertions passed.
"""

from __future__ import annotations

import sys
import os

# Ensure the repository root is on sys.path so imports resolve correctly when
# the script is run from any working directory.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from src.core.event_bus import EventBus
from src.world_sim.chronos import (
    ChronosEngine,
    EVENT_COMBAT_ROUND_END,
    EVENT_TIME_TICK,
    SECONDS_PER_ROUND,
    SECONDS_PER_DAY,
    HOURS_PER_GAME_DAY,
)

ROUNDS = 14_400


def _fail(msg: str) -> None:
    print(f"[FAIL] {msg}", file=sys.stderr)
    sys.exit(1)


def _ok(msg: str) -> None:
    print(f"[PASS] {msg}")


def main() -> None:
    bus = EventBus()
    engine = ChronosEngine(initial_tick=0)
    engine.attach(bus)

    # Track TIME_TICK events emitted by the engine.
    hour_ticks: list[dict] = []
    day_ticks: list[dict] = []

    def _capture_time_tick(payload: dict) -> None:
        if payload["type"] == "hour":
            hour_ticks.append(payload)
        elif payload["type"] == "day":
            day_ticks.append(payload)

    bus.subscribe(EVENT_TIME_TICK, _capture_time_tick)

    # Fire 14,400 COMBAT_ROUND_END events (one per round).
    for _ in range(ROUNDS):
        bus.publish(EVENT_COMBAT_ROUND_END, {})

    # ── Assertion 1: absolute_tick must equal ROUNDS × 6 ────────────────────
    expected_seconds = ROUNDS * SECONDS_PER_ROUND  # 86,400
    if engine.game_time.absolute_tick != expected_seconds:
        _fail(
            f"absolute_tick == {engine.game_time.absolute_tick}, "
            f"expected {expected_seconds}"
        )
    _ok(
        f"{ROUNDS:,} rounds → absolute_tick == {expected_seconds:,} s"
    )

    # ── Assertion 2: exactly 24 hour-boundary TIME_TICK events ──────────────
    if len(hour_ticks) != HOURS_PER_GAME_DAY:
        _fail(
            f"TIME_TICK hour events: got {len(hour_ticks)}, "
            f"expected {HOURS_PER_GAME_DAY}"
        )
    _ok(
        f"{ROUNDS:,} rounds → {HOURS_PER_GAME_DAY} hours crossed "
        f"(TIME_TICK hour events)"
    )

    # ── Assertion 3: exactly 1 day-boundary TIME_TICK event ─────────────────
    if len(day_ticks) != 1:
        _fail(
            f"TIME_TICK day events: got {len(day_ticks)}, expected 1"
        )
    _ok(f"{ROUNDS:,} rounds → 1 day crossed  (TIME_TICK day events)")

    # ── Assertion 4: total_days property ────────────────────────────────────
    if engine.game_time.total_days != 1:
        _fail(
            f"engine.game_time.total_days == {engine.game_time.total_days}, "
            f"expected 1"
        )
    _ok("engine.game_time.total_days == 1")

    # ── Assertion 5: serialise / restore round-trip ──────────────────────────
    snapshot = engine.to_dict()
    restored = ChronosEngine.from_dict(snapshot)
    if restored.game_time.absolute_tick != engine.game_time.absolute_tick:
        _fail(
            f"Round-trip absolute_tick mismatch: "
            f"{restored.game_time.absolute_tick} != {engine.game_time.absolute_tick}"
        )
    _ok("Serialise / restore round-trip preserves absolute_tick")

    print("\nAll assertions passed.")


if __name__ == "__main__":
    main()
