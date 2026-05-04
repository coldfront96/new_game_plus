"""
src/game/__main__.py
--------------------
Allow ``python -m new_game_plus`` (and ``python -m src.game``) to launch
the CLI.

Genesis Transition
~~~~~~~~~~~~~~~~~~
If ``data/player.json`` already exists (i.e. the player has completed the
Character Forge), the launcher skips the Forge entirely and runs the
**First Awakening** sequence — initialising the :class:`WorldTick`,
:class:`ChunkManager`, and the Ashen Crossroads starting biome, then
firing the ``PLAYER_AWAKENED`` event to begin the Chronos Engine at
Hour 0, Day 1.

The returned :class:`~src.game.awakening.AwakeningState` is kept in a
module-level variable so Python does not garbage-collect the live
:class:`~src.world_sim.world_tick.WorldState` and
:class:`~src.terrain.chunk_manager.ChunkManager` before the game loop
has a chance to wire them up.

If no player file is found the CLI is launched normally so the player can
run the Character Forge (``python -m src.game new-character``) or any
other subcommand.
"""

from __future__ import annotations

from pathlib import Path

_PLAYER_JSON = Path(__file__).parent.parent.parent / "data" / "player.json"


if __name__ == "__main__":  # pragma: no cover
    if _PLAYER_JSON.exists():
        from src.game.awakening import AwakeningState, run_first_awakening

        def _enter_game_loop(state: AwakeningState) -> int:
            """Hand live engine state to the main game loop.

            This is the integration seam between the First Awakening bootstrap
            and the rendering/tick pipeline.  Receiving ``state`` as a parameter
            (rather than a global) keeps :class:`~src.world_sim.world_tick.WorldState`,
            :class:`~src.terrain.chunk_manager.ChunkManager`, and player data
            alive for the entire call-frame lifetime of this function —
            i.e. the full duration of the game session.

            Replace the body with the real game loop once the rendering engine
            is wired up (Godot GDExtension / Pygame surface hand-off goes here).
            """
            # state owns WorldState + ChunkManager for the session lifetime.
            # Do not reassign or del it before the loop exits.
            _log_main = __import__("logging").getLogger(__name__)
            _log_main.info(
                "Game loop entered — player=%r tick=%d",
                state.player_data.get("name"),
                state.absolute_tick,
            )
            return 0

        awakening_state = run_first_awakening()
        if awakening_state is None:
            raise SystemExit(1)

        raise SystemExit(_enter_game_loop(awakening_state))
    else:
        from src.game.cli import main
        raise SystemExit(main())
