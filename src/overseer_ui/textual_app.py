"""
src/overseer_ui/textual_app.py
------------------------------
Textual TUI for the New Game Plus Overseer.

Cross-platform replacement for the raw stdin/stdout OverseerUI loop.
Provides three panels wired to the existing OverseerQueue and ChunkManager:

* Panel 1 — The World:   top-down ASCII/voxel view of the current terrain chunk.
* Panel 2 — The Log:     scrolling Rich combat log (initiative, attacks, XP).
* Panel 3 — Command bar: typed commands proxied to OverseerQueue or play_session.

Phase 2 additions
~~~~~~~~~~~~~~~~~
* :class:`DialogueLine` / :class:`DialoguePanel` — NPC streaming dialogue panel
  (PH2-006).
* Fog-of-War aware viewport rendering via
  :func:`~src.game.player_controller.calculate_visible_voxels_at` (PH2-013).
* ``t`` key binding wires :func:`~src.ai_sim.llm_bridge.generate_npc_dialogue`
  into the async Textual event loop (PH2-009).

Launch via ``python -m new_game_plus ui`` (see src/game/cli.py).
"""

from __future__ import annotations

import asyncio
import json
import re
import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from rich.markup import escape
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, RichLog, Static

from src.overseer_ui.overseer import OverseerQueue

if TYPE_CHECKING:
    from src.terrain.chunk_manager import ChunkManager
    from src.game.player_controller import PlayerController


# ---------------------------------------------------------------------------
# PH2-006 · DialogueLine / DialoguePanel (NPC streaming dialogue)
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class DialogueLine:
    """A single line of NPC dialogue with speaker metadata.

    Attributes:
        speaker_id:   Entity ID of the speaking NPC.
        speaker_name: Human-readable NPC name shown in the panel header.
        text:         The dialogue token or partial text chunk.
        tick:         World tick at which this line was produced.
    """

    speaker_id: str
    speaker_name: str
    text: str
    tick: int


class DialoguePanel:
    """Thin wrapper around a Textual :class:`~textual.widgets.RichLog` widget.

    Occupies a fixed sidebar column in the Textual layout and never blocks the
    main world view.  Streaming tokens are pushed as partial :class:`DialogueLine`
    updates until the generation completes.

    Args:
        log_widget: The :class:`~textual.widgets.RichLog` that backs the panel.
    """

    def __init__(self, log_widget: RichLog) -> None:
        self._log = log_widget
        self._active_speaker: str | None = None

    def push_line(self, line: DialogueLine) -> None:
        """Append a formatted :class:`DialogueLine` to the panel.

        The speaker's name is shown as a coloured prefix on the first token of
        each turn; subsequent partial tokens in the same turn are appended
        without a prefix to create a streaming-text effect.

        Args:
            line: The dialogue line to display.
        """
        if line.speaker_id != self._active_speaker:
            self._active_speaker = line.speaker_id
            self._log.write(
                f"[bold cyan]{escape(line.speaker_name)}[/bold cyan] "
                f"[dim](tick {line.tick})[/dim]"
            )
        self._log.write(escape(line.text), markup=False)

    def clear(self) -> None:
        """Clear all dialogue history from the panel."""
        self._log.clear()
        self._active_speaker = None


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


def _render_chunk_with_fog(
    manager: "ChunkManager",
    cx: int,
    cz: int,
    controller: "Optional[PlayerController]",
    player_world_pos: "Optional[tuple[int, int, int]]",
) -> Text:
    """Return a Fog-of-War aware ASCII top-down view of chunk (cx, cz).

    PH2-013 — Rendering rules:
    * **Unknown** (never revealed): solid ``█`` (default dim style).
    * **Remembered** (revealed but not currently visible): glyph at half
      brightness (``dim italic``).
    * **Visible** (currently within vision radius): glyph at full brightness.

    The visible set is calculated once per call via
    :func:`~src.game.player_controller.calculate_visible_voxels_at`.

    Args:
        manager:          Terrain chunk manager.
        cx:               Chunk X coordinate.
        cz:               Chunk Z coordinate.
        controller:       Optional player controller; if ``None`` renders without FoW.
        player_world_pos: Player's ``(world_x, world_y, world_z)`` voxel position.

    Returns:
        A :class:`rich.text.Text` object ready for the Textual viewport widget.
    """
    from src.terrain.chunk import CHUNK_DEPTH, CHUNK_WIDTH, CHUNK_HEIGHT

    chunk = manager.load_chunk(cx, cz)
    out = Text()

    if controller is None or player_world_pos is None:
        # Fall back to plain render.
        return _render_chunk(manager, cx, cz)

    from src.game.player_controller import calculate_visible_voxels_at

    # Build the set of voxels in this chunk (surface layer only for FoW).
    chunk_voxels: set[tuple[int, int, int]] = set()
    x_offset = cx * CHUNK_WIDTH
    z_offset = cz * CHUNK_DEPTH
    for zl in range(CHUNK_DEPTH):
        for xl in range(CHUNK_WIDTH):
            for yl in range(_SCAN_TOP, -1, -1):
                if chunk.get_block(xl, yl, zl) is not None:
                    chunk_voxels.add((x_offset + xl, yl, z_offset + zl))
                    break

    visible, _ = calculate_visible_voxels_at(controller, chunk_voxels, player_world_pos)
    revealed = controller.fog_revealed

    for zl in range(CHUNK_DEPTH):
        for xl in range(CHUNK_WIDTH):
            # Find surface block and its world voxel.
            block = None
            yl_surface = 0
            for yl in range(_SCAN_TOP, -1, -1):
                b = chunk.get_block(xl, yl, zl)
                if b is not None:
                    block = b
                    yl_surface = yl
                    break

            world_voxel = (x_offset + xl, yl_surface, z_offset + zl)

            if world_voxel in visible:
                # Fully visible — render normally.
                if block is None:
                    out.append(" ")
                else:
                    char, style = _GLYPH.get(block.material.name, ("?", "white"))
                    out.append(char, style=style or None)
            elif world_voxel in revealed:
                # Previously revealed, now out of sight — dim italic.
                if block is None:
                    out.append("░", style="dim italic")
                else:
                    char, _ = _GLYPH.get(block.material.name, ("?", ""))
                    out.append(char, style="dim italic")
            else:
                # Never seen — fully hidden.
                out.append("█", style="dim")
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

    #dialogue-panel {
        width: 1fr;
        border: solid $accent-darken-1;
        display: none;
    }

    #dialogue-header {
        height: 1;
        text-align: center;
        color: $accent-darken-1;
    }

    #cmd-input {
        height: 3;
    }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("t", "talk", "Talk"),
    ]

    def __init__(
        self,
        queue: OverseerQueue,
        chunk_manager: Optional["ChunkManager"] = None,
        default_apl: int = 3,
        default_terrain: str = "dungeon",
        player_controller: "Optional[PlayerController]" = None,
        combat_registry: "Optional[dict]" = None,
        faction_registry: "Optional[dict]" = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.queue = queue
        self.chunk_manager = chunk_manager
        self.default_apl = default_apl
        self.default_terrain = default_terrain
        self._cx = 0
        self._cz = 0
        # PH2 additions.
        self._player_controller: Optional["PlayerController"] = player_controller
        self._combat_registry: dict = combat_registry or {}
        self._faction_registry: dict = faction_registry or {}
        self._dialogue_panel: Optional[DialoguePanel] = None
        self._streaming_task: Optional[asyncio.Task] = None  # type: ignore[type-arg]
        self._world_tick: int = 0

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main"):
            with Vertical(id="world-panel"):
                yield Static("[b cyan]The World[/b cyan]", id="world-title")
                yield Static(id="viewport")
            yield RichLog(id="log", highlight=True, markup=True)
            with Vertical(id="dialogue-panel"):
                yield Static("[b]NPC Dialogue[/b]", id="dialogue-header")
                yield RichLog(id="dialogue-log", highlight=False, markup=True)
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
        # Initialise DialoguePanel (PH2-006).
        dialogue_log = self.query_one("#dialogue-log", RichLog)
        self._dialogue_panel = DialoguePanel(dialogue_log)
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
    # Panel 1 — viewport (PH2-013: Fog-of-War aware rendering)
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
            # PH2-013: use FoW renderer when a player controller is present.
            if self._player_controller is not None:
                ctrl = self._player_controller
                entity = self._combat_registry.get(ctrl.entity_id)
                player_pos: Optional[tuple[int, int, int]] = None
                if entity is not None:
                    raw_pos = entity.metadata.get("position")
                    if raw_pos is not None and len(raw_pos) >= 3:
                        player_pos = (int(raw_pos[0]), int(raw_pos[1]), int(raw_pos[2]))
                vp.update(
                    _render_chunk_with_fog(
                        self.chunk_manager,
                        self._cx,
                        self._cz,
                        ctrl,
                        player_pos,
                    )
                )
            else:
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

    # PH2-009 · Dialogue Streaming Integration
    async def action_talk(self) -> None:
        """Handle the ``t`` key: stream NPC dialogue for the nearest adjacent NPC.

        Spawns an :class:`asyncio.Task` that consumes
        :func:`~src.ai_sim.llm_bridge.generate_npc_dialogue` and pushes each
        token to the :class:`DialoguePanel` via Textual's async facilities.
        The main UI is never blocked during streaming.
        """
        if self._player_controller is None or not self._combat_registry:
            return

        ctrl = self._player_controller
        # Find the first entity in the registry that is not the player.
        npc_id = next(
            (eid for eid in self._combat_registry if eid != ctrl.entity_id),
            None,
        )
        if npc_id is None:
            return

        npc_entity = self._combat_registry[npc_id]
        npc_name = npc_entity.name

        # Show dialogue panel and update header.
        dialogue_panel_widget = self.query_one("#dialogue-panel")
        dialogue_panel_widget.display = True
        header = self.query_one("#dialogue-header", Static)
        header.update(f"[bold cyan]{escape(npc_name)} — speaking…[/bold cyan]")

        panel = self._dialogue_panel
        if panel is None:
            return

        # Cancel any ongoing stream.
        if self._streaming_task is not None and not self._streaming_task.done():
            self._streaming_task.cancel()

        from src.ai_sim.llm_bridge import generate_npc_dialogue

        async def _stream() -> None:
            try:
                async for token in generate_npc_dialogue(
                    entity_id=npc_id,
                    player_prompt="Hello, what can you tell me about this place?",
                    combat_registry=self._combat_registry,
                    faction_registry=self._faction_registry,
                ):
                    line = DialogueLine(
                        speaker_id=npc_id,
                        speaker_name=npc_name,
                        text=token,
                        tick=self._world_tick,
                    )
                    panel.push_line(line)
            finally:
                # Revert header to idle state.
                self.call_from_thread(
                    lambda: header.update(f"[bold]NPC Dialogue[/bold]")
                )

        self._streaming_task = asyncio.create_task(_stream())

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
