"""
src/game/__main__.py
--------------------
Allow ``python -m new_game_plus`` (and ``python -m src.game``) to launch
the CLI.  The heavy lifting lives in :mod:`src.game.cli`.
"""

from __future__ import annotations

from src.game.cli import main


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
