"""
src/overseer_ui/textual_app.py
------------------------------
Textual TUI for the New Game Plus Overseer.

Cross-platform replacement for the raw stdin/stdout OverseerUI loop.
Provides three panels wired to the existing OverseerQueue and ChunkManager:

* Panel 1 — The World:   top-down ASCII/voxel view of the current terrain chunk.
* Panel 2 — The Log:     scrolling Rich combat log (initiative, attacks, XP).
* Panel 3 — Command bar: typed commands proxied to OverseerQueue or play_session.

Launch via ``python -m new_game_plus ui`` (see src/game/cli.py).
"""

from __future__ import annotations

import json
import re
import threading
from typing import TYPE_CHECKING, Optional

from rich.markup import escape
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, RichLog, Static

from src.overseer_ui.overseer import OverseerQueue

if TYPE_CHECKING:
    from src.terrain.chunk_manager import ChunkManager


# ---------------------------------------------------------------------------
# Terrain glyph table  (Material.name → (char, Rich style))
# ---------------------------------------------------------------------------

_GLYPH: dict[str, tuple[str, str]] = {
    "AIR":           (" ", ""),
    "DIRT":          (".", "yellow"),
    "STONE":         ("#", "bright_black"),
    "SAND":          (",", "dark_khaki"),
    "GRAVEL":        (":", "grey50"),
    "WOOD":          ("T", "orange3"),
    "LEAVES":        ("*", "green3"),
    "WATER":         ("~", "blue"),
    "LAVA":          ("!", "red"),
    "IRON_ORE":      ("i", "steel_blue"),
    "GOLD_ORE":      ("g", "gold1"),
    "DIAMOND_ORE":   ("d", "cyan"),
    "OBSIDIAN":      ("X", "purple"),
    "GLASS":         ("o", "bright_white"),
    "CRAFTED_WOOD":  ("w", "dark_orange"),
    "CRAFTED_STONE": ("%", "grey62"),
}

# Scan down from this y-level to find the surface block in each column.
_SCAN_TOP = 100


def _render_chunk(manager: "ChunkManager", cx: int, cz: int) -> Text:
    """Return a Rich Text top-down ASCII view of chunk (cx, cz)."""
    from src.terrain.chunk import CHUNK_DEPTH, CHUNK_WIDTH

    chunk = manager.load_chunk(cx, cz)
    out = Text()
    for z in range(CHUNK_DEPTH):
        for x in range(CHUNK_WIDTH):
            block = None
            for y in range(_SCAN_TOP, -1, -1):
                b = chunk.get_block(x, y, z)
                if b is not None:
                    block = b
                    break
            if block is None:
                out.append(" ")
            else:
                char, style = _GLYPH.get(block.material.name, ("?", "white"))
                out.append(char, style=style or None)
        out.append("\n")
    return out


# ---------------------------------------------------------------------------
# OverseerApp
# ---------------------------------------------------------------------------


class OverseerApp(App[None]):
    """Three-panel Textual Overseer TUI."""

    TITLE = "New Game Plus — Overseer"
    SUB_TITLE = "a[pprove]  r[eject]  e <json>  s[kip]  l[ist]  play  q[uit]"

    CSS = """
    Screen {
        layout: vertical;
    }

    #main {
        height: 1fr;
        layout: horizontal;
    }

    #world-panel {
        width: 3fr;
        border: solid $accent;
        padding: 0 1;
    }

    #world-title {
        height: 1;
        text-align: center;
        color: $accent-lighten-1;
    }

    #viewport {
        height: 1fr;
    }

    #log {
        width: 2fr;
        border: solid $accent;
    }

    #cmd-input {
        height: 3;
    }
    """

    BINDINGS = [("ctrl+c", "quit", "Quit")]

    def __init__(
        self,
        queue: OverseerQueue,
        chunk_manager: Optional["ChunkManager"] = None,
        default_apl: int = 3,
        default_terrain: str = "dungeon",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.queue = queue
        self.chunk_manager = chunk_manager
        self.default_apl = default_apl
        self.default_terrain = default_terrain
        self._cx = 0
        self._cz = 0

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main"):
            with Vertical(id="world-panel"):
                yield Static("[b cyan]The World[/b cyan]", id="world-title")
                yield Static(id="viewport")
            yield RichLog(id="log", highlight=True, markup=True)
        yield Input(
            placeholder=(
                "Commands: a  r  e <json>  s  l  "
                "play [--apl N --terrain X --party NAME]  "
                "chunk <cx> <cz>  q"
            ),
            id="cmd-input",
        )
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_viewport()
        log = self.query_one("#log", RichLog)
        log.write("[bold green]=== New Game Plus — Overseer TUI ===[/bold green]")
        log.write(
            "[cyan]a[/cyan]pprove  [red]r[/red]eject  "
            "[yellow]e[/yellow] <json>  skip  list  "
            "[green]play[/green]  chunk <cx> <cz>  quit"
        )
        log.write("")
        self._display_pending()

    # ------------------------------------------------------------------
    # Panel 1 — viewport
    # ------------------------------------------------------------------

    def _refresh_viewport(self) -> None:
        vp = self.query_one("#viewport", Static)
        if self.chunk_manager is None:
            vp.update(
                "[dim]No terrain loaded.\n"
                "Pass [cyan]--seed N[/cyan] to the [green]ui[/green] "
                "subcommand to enable world view.[/dim]"
            )
            return
        try:
            vp.update(_render_chunk(self.chunk_manager, self._cx, self._cz))
        except Exception as exc:  # noqa: BLE001
            vp.update(f"[red]Terrain error:[/red] {escape(str(exc))}")

    # ------------------------------------------------------------------
    # Panel 2 — task display helpers
    # ------------------------------------------------------------------

    def _display_pending(self) -> None:
        log = self.query_one("#log", RichLog)
        task = self.queue.peek()
        if task is None:
            log.write("[dim](queue empty — enqueue tasks to begin)[/dim]")
            return
        result_line = (
            f"\n  result:   [dim]{escape(json.dumps(task.result)[:200])}[/dim]"
            if task.result
            else ""
        )
        log.write(
            f"\n[bold]── Next task  ({len(self.queue)} pending) ──[/bold]\n"
            f"  id:       [cyan]{task.task_id}[/cyan]\n"
            f"  type:     [yellow]{escape(task.task_type)}[/yellow]\n"
            f"  priority: {task.priority}\n"
            f"  status:   [green]{task.status.name}[/green]\n"
            f"  prompt:   {escape(task.prompt[:120])}"
            + result_line
        )

    # ------------------------------------------------------------------
    # Panel 3 — command dispatch
    # ------------------------------------------------------------------

    def on_input_submitted(self, event: Input.Submitted) -> None:
        raw = event.value.strip()
        event.input.clear()
        if not raw:
            return
        log = self.query_one("#log", RichLog)
        log.write(f"[dim]> {escape(raw)}[/dim]")
        cmd, _, tail = raw.partition(" ")
        cmd = cmd.lower()

        if cmd in ("q", "quit", "exit"):
            self.exit()

        elif cmd in ("l", "list"):
            tasks = self.queue.pending()
            log.write(f"[bold]Pending: {len(tasks)}[/bold]")
            for i, t in enumerate(tasks, 1):
                log.write(
                    f"  {i}. [[{t.priority}]] "
                    f"[yellow]{escape(t.task_type)}[/yellow] "
                    f"{t.task_id[:8]}… {t.status.name}"
                )

        elif cmd in ("a", "approve"):
            self._queue_op("approve", tail)

        elif cmd in ("r", "reject"):
            self._queue_op("reject", tail)

        elif cmd in ("s", "skip"):
            self._queue_op("skip", tail)

        elif cmd in ("e", "edit"):
            if not self.queue:
                log.write("[dim](queue empty)[/dim]")
                return
            try:
                result = json.loads(tail) if tail else {}
            except json.JSONDecodeError as err:
                log.write(f"[red]! invalid JSON:[/red] {escape(str(err))}")
                return
            task = self.queue.edit(result=result)
            log.write(f"[yellow]✎ edited + approved[/yellow] {task.task_id[:8]}…")
            self._display_pending()

        elif cmd == "chunk":
            parts = tail.split()
            if len(parts) >= 2:
                try:
                    self._cx, self._cz = int(parts[0]), int(parts[1])
                    log.write(
                        f"[cyan]Viewing chunk ({self._cx}, {self._cz})[/cyan]"
                    )
                    self._refresh_viewport()
                except ValueError:
                    log.write("[red]Usage: chunk <cx> <cz>[/red]")
            else:
                log.write(
                    f"[dim]Current chunk: ({self._cx}, {self._cz})[/dim]"
                )

        elif cmd == "play":
            self._start_play_session(tail)

        else:
            log.write(f"[dim]? unknown command: {escape(repr(cmd))}[/dim]")

    def _queue_op(self, op: str, note: str) -> None:
        """Proxy approve / reject / skip to OverseerQueue."""
        log = self.query_one("#log", RichLog)
        if not self.queue:
            log.write("[dim](queue empty)[/dim]")
            return
        if op == "approve":
            task = self.queue.approve(note=note)
            log.write(f"[green]✓ approved[/green] {task.task_id[:8]}…")
        elif op == "reject":
            task = self.queue.reject(note=note)
            log.write(f"[red]✗ rejected[/red] {task.task_id[:8]}…")
        elif op == "skip":
            task = self.queue.skip(note=note)
            log.write(f"[dim]… deferred {task.task_id[:8]}…[/dim]")
        self._display_pending()

    # ------------------------------------------------------------------
    # play subcommand — runs play_session in a daemon thread and streams
    # each combat log line back to Panel 2 via call_from_thread.
    # ------------------------------------------------------------------

    def _start_play_session(self, args_str: str) -> None:
        log = self.query_one("#log", RichLog)

        m_apl   = re.search(r"--apl\s+(\d+)",       args_str)
        m_ter   = re.search(r"--terrain\s+(\S+)",    args_str)
        m_diff  = re.search(r"--difficulty\s+(\S+)", args_str)
        m_seed  = re.search(r"--seed\s+(\d+)",       args_str)
        m_party = re.search(r"--party\s+(\S+)",      args_str)

        apl        = int(m_apl.group(1))  if m_apl   else self.default_apl
        terrain    = m_ter.group(1)        if m_ter   else self.default_terrain
        difficulty = m_diff.group(1)       if m_diff  else "average"
        seed_val   = int(m_seed.group(1)) if m_seed  else None
        party_name = m_party.group(1)      if m_party else None

        log.write(
            f"[cyan]── play  apl={apl}  terrain={terrain}  "
            f"diff={difficulty} ──[/cyan]"
        )

        app_ref = self

        def _post(markup: str) -> None:
            """Schedule a log.write on the main thread."""
            app_ref.call_from_thread(
                lambda s=markup: app_ref.query_one("#log", RichLog).write(s)
            )

        def _run() -> None:
            import random

            from src.game.session import play_session

            rng = random.Random(seed_val)

            if party_name:
                try:
                    from src.game.persistence import load_party
                    party = load_party(party_name)
                except FileNotFoundError:
                    _post(f"[red]Party '{escape(party_name)}' not found.[/red]")
                    return
            else:
                from src.rules_engine.character_35e import (
                    Alignment,
                    Character35e,
                    Size,
                )
                party = [
                    Character35e(
                        name=f"Hero {i + 1}",
                        char_class="Fighter",
                        level=apl,
                        race="Human",
                        alignment=Alignment.NEUTRAL_GOOD,
                        size=Size.MEDIUM,
                        strength=16,
                        dexterity=14,
                        constitution=14,
                        intelligence=10,
                        wisdom=10,
                        charisma=10,
                    )
                    for i in range(4)
                ]

            # Relay: play_session writes plain text → escape → post to log.
            class _Relay:
                def write(self, text: str) -> int:
                    for line in text.splitlines():
                        if line:
                            _post(escape(line))
                    return len(text)

                def flush(self) -> None:
                    pass

            try:
                report = play_session(
                    party=party,
                    apl=apl,
                    terrain=terrain,
                    difficulty=difficulty,
                    rng=rng,
                    stdout=_Relay(),
                )
                color = "green" if report.outcome == "victory" else "red"
                _post(
                    f"[{color}]── Outcome: {report.outcome}  "
                    f"(round {report.rounds}) ──[/{color}]"
                )
            except Exception as exc:  # noqa: BLE001
                _post(f"[red]Session error:[/red] {escape(str(exc))}")

        threading.Thread(target=_run, daemon=True).start()
