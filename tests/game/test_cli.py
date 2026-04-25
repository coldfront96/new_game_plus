"""Tests for ``src.game.cli`` (Task 1)."""

from __future__ import annotations

import io
import sys

import pytest

from src.game.cli import build_parser, main


def test_parser_has_three_subcommands():
    parser = build_parser()
    # Find the subparsers action
    actions = [a for a in parser._actions if getattr(a, "choices", None)]
    assert actions, "parser has no subparsers"
    choices = set(actions[0].choices.keys())
    assert {"new-character", "run-encounter", "play"} <= choices


def test_run_encounter_prints_summary(capsys):
    exit_code = main(
        [
            "run-encounter",
            "--apl", "3",
            "--terrain", "dungeon",
            "--difficulty", "average",
            "--seed", "7",
        ]
    )
    captured = capsys.readouterr().out
    assert exit_code == 0
    assert "Encounter (APL 3" in captured
    assert "Target EL" in captured
    assert "Treasure" in captured


def test_no_args_exits_with_error():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_python_dash_m_new_game_plus_has_main():
    # Importing the top-level alias package must not raise.
    import new_game_plus  # noqa: F401
    import new_game_plus.__main__ as m
    assert callable(m.main)
