"""
src/game/game_world_screen.py
------------------------------
GameWorldScreen — the Textual terminal UI for the active game world.

Replaces the raw ``input()`` loop with a persistent Textual Screen so the
Master App window never closes between the Character Forge and actual play.

Layout
~~~~~~
* **RichLog** (main area) — atmospheric awakening text, room descriptions,
  and command echoes with Rich markup.
* **Status bar** (one line) — player name, HP, AC, and in-world time.
* **Input** (bottom) — the player types commands here (``look``, ``examine``,
  ``north``, ``inventory``, ``quit``, …).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, RichLog, Static


class GameWorldScreen(Screen):
    """Active game-world screen — RichLog display + command Input.

    Args:
        awakening_state: The :class:`~src.game.awakening.AwakeningState`
            produced by :func:`~src.game.awakening.run_first_awakening`.
        char_dict: The fully-resolved character dict from
            :meth:`~src.game.character_forge.CharacterForgeScreen._build_character_dict`.
    """

    TITLE = "ASHEN CROSSROADS  ·  The World Awaits"

    CSS = """
    GameWorldScreen {
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
        self._state = awakening_state
        self._char_dict = char_dict or {}

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        yield RichLog(id="world-log", highlight=True, markup=True, wrap=True)

        player_name = self._char_dict.get("name", "Traveller")
        hp = self._char_dict.get("hit_points", "?")
        ac = self._char_dict.get("armor_class", "?")
        bab = self._char_dict.get("base_attack_bonus", 0)
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
        """Display the First Awakening text when the screen appears."""
        log = self.query_one("#world-log", RichLog)
        border = "[bold #c89b5f]" + ("=" * 72) + "[/bold #c89b5f]"

        log.write(border)
        log.write("[bold #c89b5f]  ASHEN CROSSROADS  —  FIRST AWAKENING[/bold #c89b5f]")
        log.write(border)
        log.write("")

        for paragraph in self._state.origin_room.description.split("\n\n"):
            log.write(paragraph.strip())
            log.write("")

        if self._state.origin_room.features:
            log.write(
                f"[dim]  [ Features: {', '.join(self._state.origin_room.features)} ][/dim]"
            )
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
        self._process_command(raw.lower(), log)
        event.input.clear()

    def _process_command(self, command: str, log: RichLog) -> None:
        if command in ("help", "?", "h"):
            log.write(
                "Commands:  [bold]look[/bold]  [bold]examine[/bold]  "
                "[bold]examine <target>[/bold]  [bold]inventory[/bold]  "
                "[bold]north[/bold] / [bold]south[/bold] / [bold]east[/bold] / [bold]west[/bold]  "
                "[bold]quit[/bold]"
            )

        elif command in ("look", "l"):
            log.write(self._state.origin_room.description)

        elif command.startswith("examine"):
            target = command[len("examine"):].strip() or "room"
            self._examine(target, log)

        elif command in ("inventory", "i", "inv"):
            self._show_inventory(log)

        elif command in (
            "north", "n", "south", "s",
            "east",  "e", "west",  "w",
            "up",    "u", "down",  "d",
        ):
            log.write(
                "[dim italic]The passage is sealed."
                " The Crossroads will not release you yet.[/dim italic]"
            )

        elif command in ("quit", "exit", "q"):
            self.app.exit()

        else:
            log.write(
                f"[dim italic]The word '{command}' dissolves"
                " into the ash-laden air.[/dim italic]"
            )

    # ------------------------------------------------------------------
    # Sub-commands
    # ------------------------------------------------------------------

    def _examine(self, target: str, log: RichLog) -> None:
        if target in ("room", "area", "surroundings", "around", "chamber"):
            features = self._state.origin_room.features
            if features:
                log.write(
                    f"[dim]You study the chamber carefully."
                    f" You notice: {', '.join(features)}.[/dim]"
                )
            else:
                log.write(
                    "[dim]You study the chamber. Crumbling stone. Ash. Silence."
                    " Nothing more.[/dim]"
                )
        elif target in ("door", "vault", "iron door", "iron vault"):
            log.write(
                "[dim]The iron vault door is etched with runes that shift when you"
                " stare too long. It is sealed.[/dim]"
            )
        elif target in ("columns", "pillars", "carvings", "runes"):
            log.write(
                "[dim]The carvings are worn almost smooth."
                " Faces, perhaps. Or warnings.[/dim]"
            )
        elif target in ("floor", "flagstone", "ash", "dust"):
            log.write(
                "[dim]The flagstone floor is cold underfoot, worn smooth by"
                " countless ages. A thin layer of ash coats everything.[/dim]"
            )
        else:
            log.write(
                f"[dim italic]You see no '{target}' here worth examining.[/dim italic]"
            )

    def _show_inventory(self, log: RichLog) -> None:
        keepsake = self._char_dict.get("keepsake", {})
        items: list = self._char_dict.get("inventory", [])

        if keepsake.get("name") and keepsake["name"] != "None":
            log.write(
                f"[bold #c89b5f]Keepsake:[/bold #c89b5f] {keepsake['name']}"
                f" — {keepsake.get('description', '')}"
            )
        if items:
            log.write("[bold]Inventory:[/bold]")
            for item in items:
                log.write(f"  · {item}")
        elif not (keepsake.get("name") and keepsake["name"] != "None"):
            log.write(
                "[dim]You carry nothing."
                " Only scars and the weight of forgotten years.[/dim]"
            )
        else:
            log.write("[dim]Beyond your keepsake, your pockets are empty.[/dim]")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_quit_game(self) -> None:
        self.app.exit()
