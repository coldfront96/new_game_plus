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
import logging
import re
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Optional

_log = logging.getLogger(__name__)

from rich.markup import escape
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Input, RichLog, Static

from src.overseer_ui.overseer import OverseerQueue

if TYPE_CHECKING:
    from src.terrain.chunk_manager import ChunkManager
    from src.game.player_controller import PlayerController
    from src.overseer_ui.animation_renderer import AnimationRenderer


# ---------------------------------------------------------------------------
# PH5-001 · UIMode enum + AppStateManager dataclass
# ---------------------------------------------------------------------------

class UIMode(str, Enum):
    """Active screen mode for the multi-screen Textual UI.

    Members:
        OVERWORLD:        Top-down world exploration view.
        TOWN_MERCHANT:    Town merchant shop screen.
        TACTICAL_DUNGEON: Dungeon combat / exploration screen.
    """

    OVERWORLD = "overworld"
    TOWN_MERCHANT = "town_merchant"
    TACTICAL_DUNGEON = "tactical_dungeon"


#: Valid mode transitions: ``{from_mode: {to_mode, ...}}``.
_VALID_TRANSITIONS: dict[UIMode, set[UIMode]] = {
    UIMode.OVERWORLD: {UIMode.TOWN_MERCHANT, UIMode.TACTICAL_DUNGEON},
    UIMode.TOWN_MERCHANT: {UIMode.OVERWORLD},
    UIMode.TACTICAL_DUNGEON: {UIMode.OVERWORLD},
}


@dataclass(slots=True)
class AppStateManager:
    """Thread-safe singleton that tracks the active UI screen and related context.

    Attributes:
        mode:                  Current :class:`UIMode`.
        active_town_id:        ID of the town currently being visited, or ``None``.
        active_dungeon_floor:  Index of the active dungeon floor (0-based).
        transition_lock:       Re-entrant lock protecting all field mutations.
    """

    mode: UIMode = UIMode.OVERWORLD
    active_town_id: str | None = None
    active_dungeon_floor: int = 0
    transition_lock: threading.Lock = field(default_factory=threading.Lock)

    def transition(
        self,
        new_mode: UIMode,
        *,
        town_id: str | None = None,
        dungeon_floor: int = 0,
    ) -> bool:
        """Atomically switch to *new_mode*, updating context fields.

        Acquires :attr:`transition_lock` before mutating any field.

        Args:
            new_mode:      The target :class:`UIMode`.
            town_id:       Town identifier; required when *new_mode* is
                           ``TOWN_MERCHANT``.
            dungeon_floor: Floor index; relevant when *new_mode* is
                           ``TACTICAL_DUNGEON``.

        Returns:
            ``True`` on success.

        Raises:
            ValueError: If the transition from the current mode to *new_mode*
                        is not permitted by :data:`_VALID_TRANSITIONS`.
        """
        with self.transition_lock:
            allowed = _VALID_TRANSITIONS.get(self.mode, set())
            if new_mode not in allowed:
                raise ValueError(
                    f"Invalid transition: {self.mode!r} → {new_mode!r}. "
                    f"Allowed: {allowed!r}"
                )
            self.mode = new_mode
            self.active_town_id = town_id
            self.active_dungeon_floor = dungeon_floor
        return True


#: Module-level singleton consumed by all screen classes.
_app_state = AppStateManager()


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
            _log.debug("OverseerApp viewport render failed: %r", exc)
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


# ---------------------------------------------------------------------------
# PH5-002 · OverworldScreen widget
# ---------------------------------------------------------------------------

class OverworldScreen(Screen):
    """Full-viewport top-down ASCII overworld exploration screen.

    Composes a full-viewport ``Static`` voxel grid (reusing
    :func:`_render_chunk_with_fog`) and a one-line status bar.

    Key bindings:
        Arrow keys / WASD — move the player avatar.
        ``t``             — open NPC dialogue.

    On mount, asserts that ``_app_state.mode`` equals ``UIMode.OVERWORLD``.
    """

    BINDINGS = [
        ("up",    "move_north", "North"),
        ("down",  "move_south", "South"),
        ("right", "move_east",  "East"),
        ("left",  "move_west",  "West"),
        ("w",     "move_north", "North"),
        ("s",     "move_south", "South"),
        ("d",     "move_east",  "East"),
        ("a",     "move_west",  "West"),
        ("t",     "talk",       "Talk"),
        ("ctrl+c", "quit",       "Quit"),
    ]

    CSS = """
    OverworldScreen {
        layout: vertical;
    }
    #ow-viewport {
        height: 1fr;
        border: solid $accent;
    }
    #ow-status {
        height: 1;
        background: $panel;
        color: $text;
    }
    """

    def __init__(
        self,
        chunk_manager: Optional["ChunkManager"] = None,
        player_controller: Optional["PlayerController"] = None,
        combat_registry: Optional[dict] = None,
        world_tick: int = 0,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._chunk_manager = chunk_manager
        self._player_controller = player_controller
        self._combat_registry: dict = combat_registry or {}
        self._world_tick: int = world_tick
        self._cx = 0
        self._cz = 0

    def compose(self) -> ComposeResult:
        yield Static(id="ow-viewport")
        yield Static(
            f"[Overworld] Tick: {self._world_tick}  Pos: (0,0)",
            id="ow-status",
        )

    def on_mount(self) -> None:
        if _app_state.mode != UIMode.OVERWORLD:
            raise RuntimeError(
                f"OverworldScreen mounted with incorrect mode: {_app_state.mode!r}"
            )
        self._refresh_viewport()

    def _refresh_viewport(self) -> None:
        vp = self.query_one("#ow-viewport", Static)
        if self._chunk_manager is None:
            vp.update("[dim]No terrain loaded.[/dim]")
            return
        try:
            ctrl = self._player_controller
            player_pos: Optional[tuple[int, int, int]] = None
            if ctrl is not None:
                entity = self._combat_registry.get(ctrl.entity_id)
                if entity is not None:
                    raw_pos = entity.metadata.get("position")
                    if raw_pos is not None and len(raw_pos) >= 3:
                        player_pos = (int(raw_pos[0]), int(raw_pos[1]), int(raw_pos[2]))
            vp.update(
                _render_chunk_with_fog(
                    self._chunk_manager,
                    self._cx,
                    self._cz,
                    ctrl,
                    player_pos,
                )
            )
            # Update status bar.
            x, z = (player_pos[0], player_pos[2]) if player_pos else (0, 0)
            self.query_one("#ow-status", Static).update(
                f"[Overworld] Tick: {self._world_tick}  Pos: ({x},{z})"
            )
        except Exception as exc:  # noqa: BLE001
            _log.debug("OverworldScreen viewport render failed: %r", exc)
            vp.update(f"[red]Terrain error:[/red] {escape(str(exc))}")

    def _move(self, action: str) -> None:
        """Dispatch a movement action and refresh the viewport."""
        from src.game.player_controller import PlayerAction, dispatch_player_input

        _action_map = {
            "north": PlayerAction.MoveNorth,
            "south": PlayerAction.MoveSouth,
            "east":  PlayerAction.MoveEast,
            "west":  PlayerAction.MoveWest,
        }
        pa = _action_map.get(action)
        if pa is None or self._player_controller is None:
            return
        dispatch_player_input(self._player_controller, pa, self._combat_registry)
        self.call_after_refresh(self._refresh_viewport)

    def action_move_north(self) -> None:
        self._move("north")

    def action_move_south(self) -> None:
        self._move("south")

    def action_move_east(self) -> None:
        self._move("east")

    def action_move_west(self) -> None:
        self._move("west")

    async def action_talk(self) -> None:
        """Stream NPC dialogue for the nearest NPC (delegates to main app)."""
        # Notify the parent app to open dialogue.
        self.app.post_message_no_wait(self.app.OverseerMessage({"cmd": "talk"}))  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# PH5-003 · TownMerchantScreen widget
# ---------------------------------------------------------------------------

class TownMerchantScreen(Screen):
    """Two-column merchant shop screen.

    Left column: scrollable ``DataTable`` of the town's merchant inventory.
    Right column: ``RichLog`` showing party gold and equipped items.

    Key bindings:
        ``b``      — buy highlighted item.
        ``Escape`` — exit to overworld.

    On mount, loads the :class:`~src.world_sim.civilization_builder.TownRecord`
    whose ``town_id`` matches ``_app_state.active_town_id``.
    """

    BINDINGS = [
        ("b",      "buy",       "Buy"),
        ("escape", "exit_town", "Exit"),
        ("ctrl+c", "quit",      "Quit"),
    ]

    CSS = """
    TownMerchantScreen {
        layout: vertical;
    }
    #tm-header {
        height: 1;
        background: $panel;
        text-align: center;
    }
    #tm-main {
        height: 1fr;
        layout: horizontal;
    }
    #tm-inventory {
        width: 2fr;
        border: solid $accent;
    }
    #tm-party {
        width: 1fr;
        border: solid $accent-darken-1;
    }
    """

    def __init__(
        self,
        town_registry: Optional[dict] = None,
        merchant_registry: Optional[dict] = None,
        party_record: Optional[object] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._town_registry: dict = town_registry or {}
        self._merchant_registry: dict = merchant_registry or {}
        self._party_record = party_record
        self._town_record: Optional[object] = None

    def compose(self) -> ComposeResult:
        yield Static("[bold cyan]Town Merchant[/bold cyan]", id="tm-header")
        with Horizontal(id="tm-main"):
            yield DataTable(id="tm-inventory")
            yield RichLog(id="tm-party", highlight=True, markup=True)

    def on_mount(self) -> None:
        # Load the active town.
        town_id = _app_state.active_town_id
        if town_id and town_id in self._town_registry:
            self._town_record = self._town_registry[town_id]

        table = self.query_one("#tm-inventory", DataTable)
        table.add_columns("Name", "Price gp", "Weight lb")

        if self._town_record is not None:
            # Populate inventory from all merchants in the town.
            for mid in getattr(self._town_record, "merchant_ids", []):
                inv_record = self._merchant_registry.get(mid)
                if inv_record is None:
                    continue
                for item in getattr(inv_record, "items", []):
                    table.add_row(
                        getattr(item, "name", str(item)),
                        str(getattr(item, "price_gp", 0)),
                        str(getattr(item, "weight_lb", 0)),
                    )

        # Update party panel.
        self._refresh_party_panel()

    def _refresh_party_panel(self) -> None:
        log = self.query_one("#tm-party", RichLog)
        log.clear()
        if self._party_record is None:
            log.write("[dim]No party loaded.[/dim]")
            return
        gold = getattr(self._party_record, "gold", 0)
        log.write(f"[bold yellow]Gold:[/bold yellow] {gold} gp")
        equipped = getattr(self._party_record, "inventory", [])
        if equipped:
            log.write("[bold]Inventory:[/bold]")
            for it in equipped:
                log.write(f"  • {escape(str(it))}")

    def action_buy(self) -> None:
        """Deduct gold and add the highlighted item to party inventory."""
        table = self.query_one("#tm-inventory", DataTable)
        if table.cursor_row is None or self._party_record is None:
            return
        try:
            row_data = table.get_row_at(table.cursor_row)
        except Exception:  # noqa: BLE001
            return
        if not row_data:
            return
        name = str(row_data[0])
        try:
            price_gp = int(str(row_data[1]))
        except (ValueError, IndexError):
            price_gp = 0

        # Deduct gold, clamped at 0.
        current_gold = getattr(self._party_record, "gold", 0)
        new_gold = max(0, current_gold - price_gp)
        try:
            object.__setattr__(self._party_record, "gold", new_gold)
        except (AttributeError, TypeError):
            try:
                self._party_record.gold = new_gold  # type: ignore[union-attr]
            except Exception:  # noqa: BLE001
                pass

        # Add to inventory.
        inv = getattr(self._party_record, "inventory", None)
        if inv is not None:
            inv.append(name)

        self._refresh_party_panel()

    def action_exit_town(self) -> None:
        """Transition back to OVERWORLD and switch screen."""
        _app_state.transition(UIMode.OVERWORLD)
        self.app.switch_screen("overworld")

    def action_quit(self) -> None:
        self.app.exit()


# ---------------------------------------------------------------------------
# PH5-004 · TacticalDungeonScreen widget
# ---------------------------------------------------------------------------

class TacticalDungeonScreen(Screen):
    """Tactical dungeon combat / exploration screen.

    Renders :class:`~src.terrain.dungeon_carver.DungeonFloor` walls (``#``),
    floors (``.``), and entity tokens as single uppercase letters.

    Key bindings:
        ``f``      — execute a full-attack combat round.
        ``Escape`` — ascend to overworld.

    Floor index is read from ``_app_state.active_dungeon_floor``.
    """

    BINDINGS = [
        ("f",      "full_attack", "Attack"),
        ("escape", "ascend",      "Ascend"),
        ("ctrl+c", "quit",        "Quit"),
    ]

    CSS = """
    TacticalDungeonScreen {
        layout: horizontal;
    }
    #td-grid {
        width: 3fr;
        border: solid $accent;
    }
    #td-log {
        width: 1fr;
        border: solid $accent-darken-1;
    }
    """

    def __init__(
        self,
        dungeon_floors: Optional[list] = None,
        overseer_queue: Optional[OverseerQueue] = None,
        party: Optional[list] = None,
        monster_registry: Optional[dict] = None,
        animation_renderer: Optional["AnimationRenderer"] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._dungeon_floors: list = dungeon_floors or []
        self._overseer_queue = overseer_queue
        self._party: list = party or []
        self._monster_registry: dict = monster_registry or {}
        self._animation_renderer: Optional["AnimationRenderer"] = animation_renderer

    def compose(self) -> ComposeResult:
        yield Static(id="td-grid")
        yield RichLog(id="td-log", highlight=True, markup=True)

    def on_mount(self) -> None:
        floor_idx = _app_state.active_dungeon_floor
        self._render_dungeon_floor(floor_idx)
        log = self.query_one("#td-log", RichLog)
        log.write(f"[bold cyan]Dungeon — Floor {floor_idx}[/bold cyan]")
        log.write("[dim]f = attack  Escape = ascend[/dim]")

    def _render_dungeon_floor(self, floor_index: int) -> None:
        """Render *floor_index* from :attr:`_dungeon_floors` to the grid widget."""
        grid = self.query_one("#td-grid", Static)

        if not self._dungeon_floors or floor_index >= len(self._dungeon_floors):
            grid.update("[dim]No dungeon floor loaded.[/dim]")
            return

        floor = self._dungeon_floors[floor_index]
        # Build a simple ASCII map: chunk-sized grid of '.' (floor) and '#' (wall).
        from src.terrain.chunk import CHUNK_WIDTH, CHUNK_DEPTH

        rows: list[list[str]] = [
            ["#"] * CHUNK_WIDTH for _ in range(CHUNK_DEPTH)
        ]

        # Carve rooms.
        for room in getattr(floor, "rooms", []):
            ox, _oy, oz = room.origin
            for dz in range(room.depth):
                for dx in range(room.width):
                    rx, rz = ox + dx, oz + dz
                    if 0 <= rz < CHUNK_DEPTH and 0 <= rx < CHUNK_WIDTH:
                        rows[rz][rx] = "."

        from rich.text import Text
        out = Text()
        for row in rows:
            out.append("".join(row) + "\n")

        grid.update(out)

    def action_full_attack(self) -> None:
        """Resolve a full-attack combat round and log results.

        Uses :class:`~src.rules_engine.combat.AttackResolver` to resolve one
        attack from the first party member against a random monster.  Damage
        flash VFX is triggered via :attr:`_animation_renderer` when available.
        An audit :class:`~src.agent_orchestration.agent_task.AgentTask` is also
        enqueued for the OverseerQueue log.
        """
        log = self.query_one("#td-log", RichLog)

        if not self._party or not self._monster_registry:
            log.write("[dim]No combatants configured.[/dim]")
            return

        import random as _random
        try:
            from src.rules_engine.combat import AttackResolver
            attacker = self._party[0]
            monster_id, defender = next(iter(self._monster_registry.items()))

            result = AttackResolver.resolve_attack(
                attacker,
                defender,
                damage_dice_count=1,
                damage_dice_sides=8,
                damage_bonus=max(0, (getattr(attacker, "strength", 10) - 10) // 2),
            )

            if result.hit:
                dmg = result.total_damage
                crit_tag = " [bold red](CRIT!)[/bold red]" if result.critical else ""
                log.write(
                    f"[green]{escape(getattr(attacker, 'name', 'Hero'))}[/green] "
                    f"hits [red]{escape(getattr(defender, 'name', 'Monster'))}[/red] "
                    f"for [bold]{dmg}[/bold] damage{crit_tag}"
                )
                if self._animation_renderer is not None:
                    self._animation_renderer.enqueue_damage_flash(
                        position=(0, 0),
                        hp_delta=-dmg,
                        combat_log=log,
                    )
            else:
                log.write(
                    f"[dim]{escape(getattr(attacker, 'name', 'Hero'))} misses "
                    f"{escape(getattr(defender, 'name', 'Monster'))} "
                    f"(roll {result.roll.total} vs AC {result.target_ac}).[/dim]"
                )
        except Exception as exc:  # noqa: BLE001
            log.write(f"[red]Combat error:[/red] {escape(str(exc))}")

        # Audit trail — enqueue after local resolution.
        if self._overseer_queue is not None:
            from src.agent_orchestration.agent_task import AgentTask
            task = AgentTask(
                task_type="combat_round",
                prompt="Full-attack round resolved locally.",
                max_tokens=256,
                priority=5,
            )
            self._overseer_queue.enqueue(task)

    def action_ascend(self) -> None:
        """Transition back to OVERWORLD."""
        _app_state.transition(UIMode.OVERWORLD)
        self.app.switch_screen("overworld")

    def action_quit(self) -> None:
        self.app.exit()
