"""
src/overseer_ui/world_builder.py
---------------------------------
PH6-005 · PH6-006 · PH6-007 — World Builder Interface (Textual TUI).

Provides :class:`WorldBuilderScreen`, a mouse-driven ASCII paint canvas that
lets the player:

* **Paint biomes** onto a 24 × 80 grid by holding the left mouse button.
* **Drop entities** (SRD monsters) onto grid cells with the right mouse button.
* **Compile** the painted world into a ``data/campaigns/custom_<timestamp>.json``
  file that the :class:`~src.overseer_ui.setup_wizard.CampaignWizardScreen`
  ``[Premade Modules]`` handler can load directly.

Usage::

    from src.overseer_ui.world_builder import WorldBuilderScreen
    # Push onto a running Textual App:
    app.push_screen(WorldBuilderScreen())
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Select, Static

from src.world_sim.biome import Biome

# ---------------------------------------------------------------------------
# PH6-005 · WorldBuilderState dataclass
# ---------------------------------------------------------------------------

_CAMPAIGNS_DIR = Path("data/campaigns")
_MONSTERS_DIR  = Path("data/srd_3.5/monsters")

# Grid dimensions
_GRID_ROWS = 24
_GRID_COLS = 80


@dataclass
class WorldBuilderState:
    """Mutable state for the ASCII world-paint canvas.

    Attributes:
        grid:            Mapping of ``(x, y)`` grid coordinate to a
                         :class:`~src.world_sim.biome.Biome` member *name*
                         string (e.g. ``"Temperate_Forest"``).
        entity_anchors:  Mapping of ``(x, y)`` to a list of monster-ID
                         strings anchored at that cell.
    """

    grid: dict[tuple[int, int], str] = field(default_factory=dict)
    entity_anchors: dict[tuple[int, int], list[str]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# PH6-005 · WorldBuilderScreen
# ---------------------------------------------------------------------------

# First-character glyph for each Biome name
_BIOME_GLYPH: dict[str, str] = {b.name: b.name[0].upper() for b in Biome}


class WorldBuilderScreen(Screen):
    """ASCII paint canvas for world creation.

    The screen contains:

    * A 24 × 80 ``Static`` widget showing the current biome grid.
    * A ``Select`` dropdown for choosing the active biome brush.
    * A ``Select`` dropdown for choosing the active monster to drop.
    * A ``[Compile Campaign]`` button that serialises the world to JSON.
    """

    CSS = """
    WorldBuilderScreen {
        layout: vertical;
    }
    #grid-display {
        height: 26;
        border: round $accent;
        overflow: hidden;
    }
    #controls {
        layout: horizontal;
        height: 5;
    }
    #biome-select {
        width: 1fr;
    }
    #monster-select {
        width: 1fr;
    }
    #btn_compile {
        width: 22;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._state = WorldBuilderState()
        self._active_biome: str = Biome.Temperate_Forest.name
        self._active_monster_id: Optional[str] = None
        self._mouse_held: bool = False

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        from textual.containers import Horizontal

        yield Static(self._render_grid(), id="grid-display")

        with Horizontal(id="controls"):
            yield Select(
                options=[(b.name, b.name) for b in Biome],
                value=self._active_biome,
                id="biome-select",
            )
            yield Select(
                options=self._load_monster_options(),
                prompt="-- select monster --",
                id="monster-select",
            )
            yield Button("[Compile Campaign]", id="btn_compile")

    def on_mount(self) -> None:
        """Refresh the grid display after mounting."""
        self._refresh_grid()

    # ------------------------------------------------------------------
    # PH6-005 · Biome selection
    # ------------------------------------------------------------------

    def set_active_biome(self, biome_name: str) -> None:
        """Validate *biome_name* against the Biome enum and store as active brush.

        Args:
            biome_name: Must be an exact member name of
                        :class:`~src.world_sim.biome.Biome`.

        Raises:
            ValueError: If *biome_name* is not a valid Biome member name.
        """
        if biome_name not in {b.name for b in Biome}:
            raise ValueError(
                f"{biome_name!r} is not a valid Biome name. "
                f"Valid names: {sorted(b.name for b in Biome)}"
            )
        self._active_biome = biome_name

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle changes to both Select widgets."""
        if event.select.id == "biome-select":
            if event.value and event.value is not Select.BLANK:
                try:
                    self.set_active_biome(str(event.value))
                except ValueError:
                    pass
        elif event.select.id == "monster-select":
            # PH6-006: store the currently selected monster ID
            if event.value and event.value is not Select.BLANK:
                self._active_monster_id = str(event.value)
            else:
                self._active_monster_id = None

    # ------------------------------------------------------------------
    # PH6-005 · Mouse paint (left button)
    # ------------------------------------------------------------------

    def on_mouse_move(self, event) -> None:
        """Paint the active biome onto the grid when left mouse is held."""
        if not getattr(event, "button", 0) == 1 and not self._mouse_held:
            return
        x, y = _event_to_grid(event)
        if _in_grid(x, y):
            self._state.grid[(x, y)] = self._active_biome
            self._refresh_grid()

    def on_mouse_down(self, event) -> None:
        """Begin paint stroke or drop an entity."""
        if event.button == 1:
            # Left click: paint biome
            self._mouse_held = True
            x, y = _event_to_grid(event)
            if _in_grid(x, y):
                self._state.grid[(x, y)] = self._active_biome
                self._refresh_grid()
        elif event.button == 3:
            # PH6-006: Right click: anchor monster
            if self._active_monster_id is not None:
                x, y = _event_to_grid(event)
                if _in_grid(x, y):
                    self._state.entity_anchors.setdefault((x, y), []).append(
                        self._active_monster_id
                    )
                    self._refresh_grid()

    def on_mouse_up(self, event) -> None:
        """End left-button paint stroke."""
        if event.button == 1:
            self._mouse_held = False

    # ------------------------------------------------------------------
    # PH6-007 · Compile Campaign button
    # ------------------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle compile button click."""
        if event.button.id == "btn_compile":
            self._compile_campaign()

    def _compile_campaign(self) -> None:
        """Serialise the painted world to a campaign JSON file.

        The output file is loadable by the
        :class:`~src.overseer_ui.setup_wizard.CampaignWizardScreen`
        ``[Premade Modules]`` handler without any schema conversion.
        """
        filename = compile_campaign_to_file(self._state)
        self.app.notify(
            f"Campaign compiled to {filename}",
            severity="information",
        )

    # ------------------------------------------------------------------
    # PH6-006 · Monster options loader
    # ------------------------------------------------------------------

    def _load_monster_options(self) -> list[tuple[str, str]]:
        """Scan ``data/srd_3.5/monsters/`` and return ``(label, value)`` pairs.

        Uses the monster ``name`` field as both the label and as the value
        (monster ID), since the SRD monster JSON files do not contain a
        separate ``id`` field.

        Returns:
            List of ``(name, name)`` tuples, one per unique monster entry.
        """
        options: list[tuple[str, str]] = []
        if not _MONSTERS_DIR.exists():
            return options

        seen: set[str] = set()
        for json_file in sorted(_MONSTERS_DIR.glob("*.json")):
            try:
                entries = json.loads(json_file.read_text())
                if not isinstance(entries, list):
                    continue
                for entry in entries:
                    name = entry.get("name") or entry.get("id")
                    if name and name not in seen:
                        seen.add(name)
                        options.append((name, name))
            except (json.JSONDecodeError, OSError):
                continue

        return options

    # ------------------------------------------------------------------
    # Internal render helpers
    # ------------------------------------------------------------------

    def _render_grid(self) -> str:
        """Render the 24 × 80 ASCII grid as a single string."""
        lines: list[str] = []
        for row in range(_GRID_ROWS):
            row_chars: list[str] = []
            for col in range(_GRID_COLS):
                cell = (col, row)
                if cell in self._state.entity_anchors and self._state.entity_anchors[cell]:
                    # PH6-006: @ glyph overrides biome when any anchor exists
                    row_chars.append("@")
                elif cell in self._state.grid:
                    biome_name = self._state.grid[cell]
                    row_chars.append(_BIOME_GLYPH.get(biome_name, "."))
                else:
                    row_chars.append(".")
            lines.append("".join(row_chars))
        return "\n".join(lines)

    def _refresh_grid(self) -> None:
        """Update the grid Static widget with the current state."""
        try:
            grid_widget = self.query_one("#grid-display", Static)
            grid_widget.update(self._render_grid())
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def compile_campaign_to_file(
    state: WorldBuilderState,
    *,
    output_dir: Optional[Path] = None,
) -> str:
    """Serialise *state* to a timestamped campaign JSON file.

    This is the pure-data extraction of
    :meth:`WorldBuilderScreen._compile_campaign`, callable without a running
    Textual app for easy unit-testing.

    Args:
        state:      The :class:`WorldBuilderState` to serialise.
        output_dir: Directory to write the file to.  Defaults to
                    ``data/campaigns/``.

    Returns:
        The absolute path of the written JSON file as a string.
    """
    out_dir = output_dir if output_dir is not None else _CAMPAIGNS_DIR
    chunks_list = []
    for (x, y), biome_name in state.grid.items():
        chunks_list.append({
            "x": x,
            "y": y,
            "biome": biome_name,
            "monster_ids": state.entity_anchors.get((x, y), []),
        })

    campaign_dict = {
        "source": "world_builder",
        "seed": None,
        "chunks": chunks_list,
        "faction_records": [],
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    filename = str(out_dir / f"custom_{int(time.time())}.json")
    Path(filename).write_text(json.dumps(campaign_dict, indent=2))
    return filename

def _event_to_grid(event) -> tuple[int, int]:
    """Convert a mouse event to grid (col, row) coordinates."""
    x = max(0, int(getattr(event, "x", 0)))
    y = max(0, int(getattr(event, "y", 0)))
    return x, y


def _in_grid(x: int, y: int) -> bool:
    """Return True if (x, y) is within the 80 × 24 grid bounds."""
    return 0 <= x < _GRID_COLS and 0 <= y < _GRID_ROWS
