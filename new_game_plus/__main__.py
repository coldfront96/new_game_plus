"""
new_game_plus/__main__.py
-------------------------
Thin launcher so ``python -m new_game_plus`` drops into the CLI.
"""

from __future__ import annotations

from src.game.cli import main


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
