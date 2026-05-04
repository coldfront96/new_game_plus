"""
src/game/game_world_screen.py
------------------------------
AdventureScreen — the Textual terminal UI for the active game world
(Interaction Loop, Path 1).

Replaces the raw ``input()`` loop with a persistent Textual Screen so the
Master App window never closes between the Character Forge and actual play.

Layout
~~~~~~
* **RichLog** (main area, ``height: 1fr``) — atmospheric awakening text,
  room descriptions, and command echoes with Rich markup.
* **Status bar** (one line) — player name, HP, AC, and in-world time.
* **Input** (bottom, ``height: 3``) — the player types commands here.

Command routing
~~~~~~~~~~~~~~~
All typed commands are forwarded to
:class:`~src.game.player_controller.CommandProcessor`, which implements the
``look`` and ``examine`` verbs (Path 1) and returns Rich-markup strings to
be written to the log.

``GameWorldScreen`` is kept as a backward-compatible alias.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, RichLog, Static

from src.game.player_controller import CommandProcessor, _QUIT_SENTINEL


class AdventureScreen(Screen):
    """Active game-world screen — RichLog display + command Input.

    Typed commands are echoed to the log and forwarded to
    :class:`~src.game.player_controller.CommandProcessor`.

    Args:
        awakening_state: The :class:`~src.game.awakening.AwakeningState`
            produced by :func:`~src.game.awakening.run_first_awakening`.
        char_dict: The fully-resolved character dict from the Character Forge.
    """

    TITLE = "ASHEN CROSSROADS  ·  The World Awaits"

    CSS = """
    AdventureScreen {
        background: #0d0d0d;
    }
    #world-log {
        height: 1fr;
        border: solid #3d2b15;
        background: #0a0a0a;
        padding: 0 1;
        scrollbar-color: #3d2b15;
        scrollbar-background: #0a0a0a;
    }
    #status-bar {
        height: 1;
        background: #1c0f00;
        color: #7a5a30;
        padding: 0 1;
        text-style: bold;
    }
    #world-input {
        height: 3;
        background: #141414;
        border: solid #3d2b15;
        color: #e8d5a0;
    }
    #world-input:focus {
        border: solid #c89b5f;
    }
    """

    BINDINGS = [("ctrl+q", "quit_game", "Quit")]

    def __init__(
        self,
        awakening_state: Any,
        char_dict: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__()
        self._state     = awakening_state
        self._char_dict = char_dict or {}
        self._processor = CommandProcessor(awakening_state.origin_room, self._char_dict)

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        yield RichLog(id="world-log", highlight=True, markup=True, wrap=True)

        player_name = self._char_dict.get("name", "Traveller")
        hp          = self._char_dict.get("hit_points", "?")
        ac          = self._char_dict.get("armor_class", "?")
        bab         = self._char_dict.get("base_attack_bonus", 0)
        yield Static(
            f" {player_name}  ·  HP {hp}  ·  AC {ac}  ·  BAB +{bab}"
            "  ·  Hour 0, Day 1  ·  Ashen Crossroads",
            id="status-bar",
        )

        yield Input(placeholder="> enter command…", id="world-input")
        yield Footer()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        """Display the First Awakening text and print the initial look."""
        log    = self.query_one("#world-log", RichLog)
        border = "[bold #c89b5f]" + ("=" * 72) + "[/bold #c89b5f]"

        log.write(border)
        log.write("[bold #c89b5f]  ASHEN CROSSROADS  —  FIRST AWAKENING[/bold #c89b5f]")
        log.write(border)
        log.write("")

        # Print full awakening description via CommandProcessor look.
        for line in self._processor.process("look"):
            log.write(line)

        log.write("")
        log.write(border)
        log.write("")
        log.write(
            "Type [bold #c89b5f]help[/bold #c89b5f] to see available commands."
        )
        log.write("")

        self.query_one("#world-input", Input).focus()

    # ------------------------------------------------------------------
    # Input handling
    # ------------------------------------------------------------------

    def on_input_submitted(self, event: Input.Submitted) -> None:
        raw = event.value.strip()
        if not raw:
            return

        log = self.query_one("#world-log", RichLog)
        log.write(f"\n[bold #c89b5f]>[/bold #c89b5f] {raw}")

        for line in self._processor.process(raw):
            if line == _QUIT_SENTINEL:
                self.app.exit()
                return
            log.write(line)

        event.input.clear()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_quit_game(self) -> None:
        self.app.exit()


# Backward-compatible alias — existing code importing GameWorldScreen
# continues to work without modification.
GameWorldScreen = AdventureScreen
