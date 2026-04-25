"""
new_game_plus
-------------
Top-level alias package that re-exports :mod:`src.game` so ``python -m
new_game_plus`` maps to the CLI entry point.  All real code lives under
``src/``.
"""

from src.game import cli  # noqa: F401

__all__ = ["cli"]
