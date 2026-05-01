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


def _add_ui_parser(subparsers: "argparse._SubParsersAction") -> None:
    parser = subparsers.add_parser(
        "ui",
        help="Launch the Textual TUI Overseer.",
        description=(
            "Open the graphical terminal interface: World viewport, "
            "combat log, and Overseer command bar.  Requires the "
            "'textual' package (pip install textual)."
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="World seed for terrain generation.  Omit to disable the viewport.",
    )
    parser.add_argument(
        "--apl",
        type=int,
        default=3,
        help="Default Average Party Level for 'play' sessions (default 3).",
    )
    parser.add_argument(
        "--terrain",
        default="dungeon",
        help="Default terrain for 'play' sessions (default: dungeon).",
    )
    parser.add_argument(
        "--cache-size",
        type=int,
        default=64,
        help="Chunk cache size for the terrain manager (default 64).",
    )


def _add_level_up_parser(subparsers: "argparse._SubParsersAction") -> None:
    parser = subparsers.add_parser(
        "level-up",
        help="Interactively level up ready characters in a party.",
        description=(
            "Load a saved party, detect which characters have enough XP to "
            "level up, run the interactive level-up wizard for each, and save "
            "the result."
        ),
    )
    parser.add_argument(
        "party",
        nargs="?",
        default="default",
        help="Name of the party to level up (default: 'default').",
    )
    parser.add_argument("--seed", type=int, default=None)


def _add_campaign_parser(subparsers: "argparse._SubParsersAction") -> None:
    parser = subparsers.add_parser(
        "campaign",
        help="Run a multi-quest campaign arc.",
        description=(
            "Load a party, chain multiple quests via CampaignSession, "
            "then save the result.  Each quest generates a settlement "
            "encounter, NPC dialogue, and a combat session."
        ),
    )
    parser.add_argument(
        "party",
        nargs="?",
        default="default",
        help="Party name to load (default: 'default').",
    )
    parser.add_argument(
        "--quests",
        type=int,
        default=3,
        help="Number of quests to run (default 3).",
    )
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument(
        "--difficulty",
        choices=("easy", "average", "challenging", "hard", "overwhelming"),
        default="average",
    )
    parser.add_argument("--terrain", default="dungeon")


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
    _add_ui_parser(subparsers)
    _add_level_up_parser(subparsers)
    _add_campaign_parser(subparsers)
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
    from src.game.persistence import load_party_with_state, save_party, xp_manager_from_record
    from src.game.session import play_session, rest_party
    from src.rules_engine.progression import XPManager

    out = stdout or sys.stdout
    party_name = args.party
    try:
        state = load_party_with_state(party_name)
    except FileNotFoundError as err:
        print(f"error: {err}", file=out)
        return 2

    party = state["party"]
    records = state["records"]

    if not party:
        print(f"error: party '{party_name}' has no characters", file=out)
        return 2

    # Reconstruct XP managers from saved records (create fresh if absent)
    xp_managers: dict = {}
    for char, rec in zip(party, records):
        mgr = xp_manager_from_record(rec)
        if mgr is None:
            mgr = XPManager(current_xp=0, current_level=char.level)
        xp_managers[char.char_id] = mgr

    rng = random.Random(args.seed) if args.seed is not None else random.Random()
    apl = args.apl if args.apl is not None else sum(c.level for c in party) // len(party)

    _difficulty_ladder = ["easy", "average", "challenging", "hard", "overwhelming"]
    difficulty = args.difficulty
    final_outcome = "unknown"

    while True:
        report = play_session(
            party=party,
            apl=apl,
            terrain=args.terrain,
            difficulty=difficulty,
            rng=rng,
            max_rounds=args.max_rounds,
            stdout=out,
        )
        final_outcome = report.outcome
        print(f"\nOutcome: {report.outcome}", file=out)

        # Award XP and check for level-ups
        for char in party:
            xp_gain = report.xp_awarded.get(char.char_id, 0)
            if xp_gain > 0:
                xp_managers[char.char_id].award_xp(xp_gain)
                result = xp_managers[char.char_id].check_level_up()
                if result.leveled_up:
                    print(
                        f"*** {char.name} is ready to level up! "
                        f"Run: new-game-plus level-up {party_name} ***",
                        file=out,
                    )

        # Persist updated party + XP
        save_party(party_name, party, xp_managers=xp_managers)

        # Offer continuation (only when stdin is a real terminal)
        in_stream = stdin or sys.stdin
        if report.outcome != "victory":
            break
        if not getattr(in_stream, "isatty", lambda: False)():
            break
        print("\nPlay another encounter? [y/N]: ", end="", flush=True, file=out)
        answer = in_stream.readline().strip().lower()
        if answer not in ("y", "yes"):
            break

        # Between encounters: long rest + escalating difficulty
        rest_party(party)
        idx = _difficulty_ladder.index(difficulty)
        difficulty = _difficulty_ladder[min(idx + 1, len(_difficulty_ladder) - 1)]
        apl = max(1, sum(c.level for c in party) // len(party))
        print(f"\n--- Party rested. Next encounter: {difficulty} ---\n", file=out)

    return 0 if final_outcome == "victory" else 1


def _cmd_ui(args: argparse.Namespace) -> int:
    try:
        from textual.app import App as _TextualApp  # noqa: F401 — presence check
    except ImportError:
        print(
            "error: 'textual' is not installed.\n"
            "       Run:  pip install textual",
            file=sys.stderr,
        )
        return 1

    from src.overseer_ui.overseer import OverseerQueue
    from src.overseer_ui.textual_app import OverseerApp

    queue = OverseerQueue()

    chunk_manager = None
    if args.seed is not None:
        from src.core.event_bus import EventBus
        from src.terrain.chunk_generator import ChunkGenerator
        from src.terrain.chunk_manager import ChunkManager

        bus = EventBus()
        generator = ChunkGenerator(seed=args.seed)
        chunk_manager = ChunkManager(
            event_bus=bus,
            cache_size=args.cache_size,
            generator=generator,
        )

    app = OverseerApp(
        queue=queue,
        chunk_manager=chunk_manager,
        default_apl=args.apl,
        default_terrain=args.terrain,
    )
    app.run()
    return 0


def _cmd_level_up(
    args: argparse.Namespace,
    *,
    stdin: Optional[TextIO] = None,
    stdout: Optional[TextIO] = None,
) -> int:
    import io
    from src.game.persistence import load_party_with_state, save_party, xp_manager_from_record
    from src.game.wizard import CharacterWizard, run_level_up_flow
    from src.rules_engine.progression import XPManager

    out = stdout or sys.stdout
    in_stream = stdin or sys.stdin
    party_name = args.party
    try:
        state = load_party_with_state(party_name)
    except FileNotFoundError as err:
        print(f"error: {err}", file=out)
        return 2

    party = state["party"]
    records = state["records"]
    if not party:
        print(f"error: party '{party_name}' has no characters", file=out)
        return 2

    xp_managers: dict = {}
    for char, rec in zip(party, records):
        mgr = xp_manager_from_record(rec)
        if mgr is None:
            mgr = XPManager(current_xp=0, current_level=char.level)
        xp_managers[char.char_id] = mgr

    rng = random.Random(args.seed) if args.seed is not None else random.Random()
    wizard = CharacterWizard(stdin=in_stream, stdout=out, rng=rng)
    any_leveled = False
    for char in party:
        mgr = xp_managers[char.char_id]
        prog = run_level_up_flow(char, mgr, wizard)
        if prog is not None:
            any_leveled = True

    if any_leveled:
        save_party(party_name, party, xp_managers=xp_managers)
        print(f"\nParty saved to '{party_name}'.", file=out)
    else:
        print("No characters are ready to level up.", file=out)
    return 0


def _cmd_campaign(
    args: argparse.Namespace,
    *,
    stdin: Optional[TextIO] = None,
    stdout: Optional[TextIO] = None,
) -> int:
    from src.game.campaign import CampaignSession
    from src.game.persistence import load_party, save_party

    out = stdout or sys.stdout
    party_name = args.party
    try:
        party = load_party(party_name)
    except FileNotFoundError as err:
        print(f"error: {err}", file=out)
        return 2

    if not party:
        print(f"error: party '{party_name}' has no characters", file=out)
        return 2

    seed = args.seed if args.seed is not None else random.randint(0, 2 ** 32)
    rng = random.Random(seed)

    camp = CampaignSession(
        party=party,
        world_seed=seed,
        difficulty=args.difficulty,
        terrain=args.terrain,
        stdout=out,
        rng=rng,
    )
    report = camp.run(num_quests=args.quests)
    save_party(party_name, party)
    print(
        f"\nCampaign complete — {report.quests_completed} quests completed, "
        f"{report.quests_failed} failed.  Total XP: {report.total_xp}  "
        f"Gold: {report.total_gp:.0f} gp.",
        file=out,
    )
    return 0 if report.quests_completed > 0 else 1


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
    if args.command == "ui":
        return _cmd_ui(args)
    if args.command == "level-up":
        return _cmd_level_up(args)
    if args.command == "campaign":
        return _cmd_campaign(args)

    parser.print_help()
    return 1
