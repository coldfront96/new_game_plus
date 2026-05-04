"""
src/game/master_app.py
-----------------------
MasterApp — the single, persistent Textual application that unifies
the Character Forge and Game World under one window.

Screen stack (push order)
~~~~~~~~~~~~~~~~~~~~~~~~~~
  MainMenuScreen
    → DifficultySelectorScreen
      → CharacterForgeScreen
        → GameWorldScreen

Because all transitions use ``push_screen`` / ``pop_screen`` the OS window
never closes between the Pygame door slam and the end of a play session.

Usage (standalone — for development or the window wrapper)::

    python -m src.game.master_app

Or import :func:`create_app` and call ``.run()``::

    from src.game.master_app import MasterApp
    MasterApp().run()
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Optional, Tuple

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_REPO_ROOT   = Path(__file__).parent.parent.parent
_PLAYER_JSON = _REPO_ROOT / "data" / "player.json"

_DIFFICULTIES: dict[str, Tuple[int, int, bool]] = {
    "Easy":          (35, 45, False),
    "Medium":        (25, 35, False),
    "Hard":          (20, 30, False),
    "The Iron Path": (20, 30, True),
}

# ---------------------------------------------------------------------------
# Shared CSS injected at App level — applies to every Screen
# ---------------------------------------------------------------------------

_SHARED_CSS = """
/* Common button hover / disabled states */
Button:hover {
    text-style: bold;
}
"""


# ===========================================================================
# Screen: Main Menu
# ===========================================================================


class MainMenuScreen(Screen):
    """Entry screen — Continue / New Game / Settings."""

    TITLE = "ASHEN CROSSROADS  ·  Main Menu"

    CSS = """
    MainMenuScreen {
        background: #0d0d0d;
        align: center middle;
    }
    #menu-container {
        width: 50;
        border: solid #3d2b15;
        padding: 1 2;
    }
    #menu-title {
        height: 1;
        background: #1c0f00;
        color: #c89b5f;
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    .menu-btn {
        width: 100%;
        margin-bottom: 1;
        background: #1c0800;
        color: #e8d5a0;
        border: solid #3d2b15;
    }
    .menu-btn:hover {
        background: #3d2b15;
        color: #c89b5f;
    }
    .menu-btn:disabled {
        color: #3d2b15;
        background: #0a0a0a;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Vertical(id="menu-container"):
            yield Static("⚡  ECHOES OF THE INFINITE", id="menu-title")
            continue_disabled = not _PLAYER_JSON.exists()
            yield Button(
                "▶  Continue",
                id="btn-continue",
                classes="menu-btn",
                disabled=continue_disabled,
            )
            yield Button("✦  New Game",  id="btn-new-game", classes="menu-btn")
            yield Button("⚙  Settings",  id="btn-settings", classes="menu-btn", disabled=True)
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-continue":
            # Future: load existing save, skip forge, push GameWorldScreen.
            # For now exit cleanly — the continue path is Phase 8.
            self.app.exit()
        elif event.button.id == "btn-new-game":
            self.app.push_screen(DifficultySelectorScreen())


# ===========================================================================
# Screen: Difficulty Selector
# ===========================================================================


class DifficultySelectorScreen(Screen):
    """Choose difficulty tier before entering the Character Forge."""

    TITLE = "ASHEN CROSSROADS  ·  Choose Your Trial"

    CSS = """
    DifficultySelectorScreen {
        background: #0d0d0d;
        align: center middle;
    }
    #diff-container {
        width: 60;
        border: solid #3d2b15;
        padding: 1 2;
    }
    #diff-title {
        height: 1;
        background: #1c0f00;
        color: #c89b5f;
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    #diff-subtitle {
        color: #7a5a30;
        margin-bottom: 1;
        text-align: center;
    }
    .diff-btn {
        width: 100%;
        margin-bottom: 1;
        background: #1c0800;
        color: #e8d5a0;
        border: solid #3d2b15;
    }
    .diff-btn:hover {
        background: #3d2b15;
        color: #c89b5f;
    }
    #btn-iron-path {
        color: #ff6b6b;
        border: solid #8b0000;
    }
    #btn-iron-path:hover {
        background: #8b0000;
        color: #fff;
    }
    #btn-back {
        width: 100%;
        background: #0a0a0a;
        color: #7a5a30;
        border: solid #3d2b15;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Vertical(id="diff-container"):
            yield Static("⚔  SELECT YOUR TRIAL", id="diff-title")
            yield Static(
                "Your chosen trial determines the size of your Awakening Pool.",
                id="diff-subtitle",
            )
            yield Button("☀  Easy          [Pool: 35–45]",               id="btn-easy",      classes="diff-btn")
            yield Button("⚖  Medium        [Pool: 25–35]",               id="btn-medium",    classes="diff-btn")
            yield Button("💀 Hard          [Pool: 20–30]",               id="btn-hard",      classes="diff-btn")
            yield Button("🩸 The Iron Path [Pool: 20–30 + Permadeath]",  id="btn-iron-path", classes="diff-btn")
            yield Button("← Back",                                        id="btn-back")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
            return

        difficulty_map = {
            "btn-easy":      "Easy",
            "btn-medium":    "Medium",
            "btn-hard":      "Hard",
            "btn-iron-path": "The Iron Path",
        }
        if event.button.id in difficulty_map:
            diff_name = difficulty_map[event.button.id]
            pool_min, pool_max, permadeath = _DIFFICULTIES[diff_name]
            pool_size = random.randint(pool_min, pool_max)

            from src.game.character_forge import CharacterForgeScreen
            self.app.push_screen(
                CharacterForgeScreen(
                    difficulty=diff_name,
                    pool_size=pool_size,
                    permadeath=permadeath,
                )
            )


# ===========================================================================
# Master App
# ===========================================================================


class MasterApp(App):
    """Single persistent Textual application for Echoes of the Infinite.

    Starts on :class:`MainMenuScreen` and manages all subsequent screen
    transitions internally — the window never closes mid-session.
    """

    TITLE    = "Echoes of the Infinite"
    CSS      = _SHARED_CSS

    def on_mount(self) -> None:
        self.push_screen(MainMenuScreen())


# ---------------------------------------------------------------------------
# Module entry point (development / textual serve)
# ---------------------------------------------------------------------------


def create_app() -> MasterApp:
    """Factory used by ``textual serve`` and the window wrapper."""
    return MasterApp()


if __name__ == "__main__":
    MasterApp().run()
