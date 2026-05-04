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

If no player file is found the CLI is launched normally so the player can
run the Character Forge (``python -m src.game new-character``) or any
other subcommand.
"""

from __future__ import annotations

from pathlib import Path

_PLAYER_JSON = Path(__file__).parent.parent.parent / "data" / "player.json"


if __name__ == "__main__":  # pragma: no cover
    if _PLAYER_JSON.exists():
        from src.game.awakening import run_first_awakening
        raise SystemExit(run_first_awakening())
    else:
        from src.game.cli import main
        raise SystemExit(main())
