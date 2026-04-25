"""
src/game/cli.py
---------------
Text-mode command-line interface for New Game Plus.

Subcommands
~~~~~~~~~~~
``new-character``
    Launch the interactive character-creation wizard (:mod:`src.game.wizard`)
    and save the result to ``saves/``.

``run-encounter``
    Generate a random encounter for a given APL / terrain / difficulty and
    print a summary (monsters, EL, XP award, treasure letter).

``play``
    Run the main play loop: load a party, roll initiative, resolve combat
    until the encounter terminates.

The CLI keeps all orchestration logic out of the rules engine; it only
wires together the existing registries and managers.
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path
from typing import List, Optional, Sequence, TextIO


def _add_new_character_parser(subparsers: "argparse._SubParsersAction") -> None:
    parser = subparsers.add_parser(
        "new-character",
        help="Interactive character-creation wizard.",
        description=(
            "Walk through race → class → ability scores → skills → feats → "
            "starting equipment and save the resulting Character35e to disk."
        ),
    )
    parser.add_argument(
        "--name",
        type=str,
        default=None,
        help="Character name (prompted if omitted).",
    )
    parser.add_argument(
        "--method",
        choices=("4d6", "point-buy"),
        default="4d6",
        help="Ability-score generation method (default: 4d6-drop-lowest).",
    )
    parser.add_argument(
        "--point-buy-budget",
        type=int,
        default=25,
        help="Point-buy budget when --method=point-buy (default 25).",
    )
    parser.add_argument(
        "--save-as",
        type=str,
        default=None,
        help="Party name to save the character under (default: character name).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for deterministic ability rolls (debugging).",
    )


def _add_run_encounter_parser(subparsers: "argparse._SubParsersAction") -> None:
    parser = subparsers.add_parser(
        "run-encounter",
        help="Generate and print a random encounter.",
        description=(
            "Build an encounter via rules_engine.build_encounter() and print "
            "the blueprint, per-character XP, and treasure letter."
        ),
    )
    parser.add_argument("--apl", type=int, default=3, help="Average Party Level.")
    parser.add_argument(
        "--party-size", type=int, default=4, help="Number of PCs (default 4)."
    )
    parser.add_argument(
        "--terrain",
        default="dungeon",
        help="Terrain key (dungeon, forest, plains, desert, hills, mountains, marsh, arctic).",
    )
    parser.add_argument(
        "--difficulty",
        choices=("easy", "average", "challenging", "hard", "overwhelming"),
        default="average",
    )
    parser.add_argument("--seed", type=int, default=None)


def _add_play_parser(subparsers: "argparse._SubParsersAction") -> None:
    parser = subparsers.add_parser(
        "play",
        help="Run a full play session (initiative + combat).",
        description=(
            "Load a saved party, roll initiative, drive the turn controller "
            "through the encounter, and report the outcome."
        ),
    )
    parser.add_argument(
        "party",
        nargs="?",
        default="default",
        help="Name of the party to load (default: 'default').",
    )
    parser.add_argument("--apl", type=int, default=None)
    parser.add_argument("--terrain", default="dungeon")
    parser.add_argument(
        "--difficulty",
        choices=("easy", "average", "challenging", "hard", "overwhelming"),
        default="average",
    )
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=20,
        help="Safety cap on combat rounds (default 20).",
    )


def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level ``argparse`` parser."""
    parser = argparse.ArgumentParser(
        prog="new-game-plus",
        description="New Game Plus — D&D 3.5e engine + simulation CLI.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_new_character_parser(subparsers)
    _add_run_encounter_parser(subparsers)
    _add_play_parser(subparsers)
    return parser


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def _cmd_new_character(
    args: argparse.Namespace,
    *,
    stdin: Optional[TextIO] = None,
    stdout: Optional[TextIO] = None,
) -> int:
    from src.game.wizard import CharacterWizard

    rng = random.Random(args.seed) if args.seed is not None else random.Random()
    wizard = CharacterWizard(
        stdin=stdin or sys.stdin,
        stdout=stdout or sys.stdout,
        rng=rng,
    )
    character = wizard.run(
        name=args.name,
        method=args.method,
        point_buy_budget=args.point_buy_budget,
    )

    from src.game.persistence import save_party
    party_name = args.save_as or character.name
    path = save_party(party_name, [character])
    print(f"\nSaved {character.name!r} to {path}", file=stdout or sys.stdout)
    return 0


def _cmd_run_encounter(
    args: argparse.Namespace,
    *,
    stdout: Optional[TextIO] = None,
) -> int:
    from src.rules_engine.encounter_extended import (
        EncounterDifficulty,
        build_encounter,
    )
    from src.rules_engine.encounter import distribute_xp
    from src.rules_engine.treasure import _cr_to_treasure_letter

    out = stdout or sys.stdout
    rng = random.Random(args.seed) if args.seed is not None else random.Random()
    difficulty = EncounterDifficulty(args.difficulty)

    blueprint = build_encounter(args.apl, difficulty, args.terrain, rng)
    party_levels = [args.apl] * args.party_size
    xp = distribute_xp(blueprint.actual_el, party_levels)
    treasure_letter = _cr_to_treasure_letter(blueprint.actual_el)

    print("=" * 60, file=out)
    print(f"Encounter (APL {args.apl}, {args.difficulty}, {args.terrain})", file=out)
    print("=" * 60, file=out)
    print(f"Target EL : {blueprint.target_el}", file=out)
    print(f"Actual EL : {blueprint.actual_el}", file=out)
    print("Monsters  :", file=out)
    for name, count, cr in blueprint.monsters:
        print(f"  - {count:>2}× {name} (CR {cr})", file=out)
    print("XP award  :", file=out)
    for idx, amount in xp.items():
        print(f"  PC #{idx + 1}: {amount} XP", file=out)
    print(f"Treasure  : Type {treasure_letter}", file=out)
    return 0


def _cmd_play(
    args: argparse.Namespace,
    *,
    stdin: Optional[TextIO] = None,
    stdout: Optional[TextIO] = None,
) -> int:
    from src.game.persistence import load_party
    from src.game.session import play_session

    out = stdout or sys.stdout
    try:
        party = load_party(args.party)
    except FileNotFoundError as err:
        print(f"error: {err}", file=out)
        return 2

    if not party:
        print(f"error: party '{args.party}' has no characters", file=out)
        return 2

    rng = random.Random(args.seed) if args.seed is not None else random.Random()
    apl = args.apl if args.apl is not None else sum(c.level for c in party) // len(party)

    report = play_session(
        party=party,
        apl=apl,
        terrain=args.terrain,
        difficulty=args.difficulty,
        rng=rng,
        max_rounds=args.max_rounds,
        stdout=out,
    )
    print(f"\nOutcome: {report.outcome}", file=out)
    return 0 if report.outcome == "victory" else 1


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: Optional[Sequence[str]] = None) -> int:
    """Module entry point.  Returns a shell-style exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "new-character":
        return _cmd_new_character(args)
    if args.command == "run-encounter":
        return _cmd_run_encounter(args)
    if args.command == "play":
        return _cmd_play(args)

    parser.print_help()
    return 1
