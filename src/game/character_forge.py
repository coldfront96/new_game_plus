"""
src/game/character_forge.py
----------------------------
Ashen Crossroads — Character Forge
===================================
Textual-based terminal UI for D&D 3.5e character creation.

The forge maps player selections to SRD data from ``data/srd_3.5/`` and
writes a fully-resolved ``data/player.json`` via
:func:`~src.game.player_persistence.save_new_player` when the AWAKEN button
is confirmed.

Screens
~~~~~~~
* :class:`CharacterForgeApp` — single-screen multi-panel character builder.

Launch::

    python -m src.game.character_forge

Or call :func:`main` from the launcher after the Pygame intro sequence.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from rich.console import Console

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Label, Select, Static

# ---------------------------------------------------------------------------
# SRD data loading
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent.parent
_SRD_ROOT = _REPO_ROOT / "data" / "srd_3.5"

with (_SRD_ROOT / "races" / "core.json").open(encoding="utf-8") as _fh:
    _RACES: list[dict] = json.load(_fh)

with (_SRD_ROOT / "classes" / "core.json").open(encoding="utf-8") as _fh:
    _CLASSES: list[dict] = json.load(_fh)

_RACE_MAP: dict[str, dict] = {r["name"]: r for r in _RACES}
_CLASS_MAP: dict[str, dict] = {c["name"]: c for c in _CLASSES}

# ---------------------------------------------------------------------------
# Keepsake lookup table
# ---------------------------------------------------------------------------

_KEEPSAKES: dict[str, dict[str, Any]] = {
    "Crimson Medallion": {
        "description": "A blood-red medallion worn by the dying. Pulses faintly with residual life.",
        "effect": "max_hp_bonus",
        "value": 2,
        "lore": "Said to carry the last heartbeat of its original owner.",
    },
    "Ashen Token": {
        "description": "Ash compressed into a coin shape from a fallen champion's pyre.",
        "effect": "all_saves_bonus",
        "value": 1,
        "lore": "Heroes who carried this never broke under pressure.",
    },
    "Iron Signet": {
        "description": "A heavy iron signet ring engraved with a half-erased crest.",
        "effect": "ac_bonus",
        "value": 1,
        "lore": "The house it represents has long since crumbled to ruin.",
    },
    "Scholar's Compass": {
        "description": "A brass compass that spins freely — it points toward hidden truths, not north.",
        "effect": "all_skills_bonus",
        "value": 1,
        "lore": "Belonged to a cartographer who mapped the unmappable.",
    },
    "Wanderer's Mark": {
        "description": "A tattoo of the open road branded on the inside of your wrist at birth.",
        "effect": "speed_bonus",
        "value": 5,
        "lore": "Those who bear it cannot be lost — only delayed.",
    },
    "Ember Shard": {
        "description": "A crystallized shard of flame from the First Forge of Creation.",
        "effect": "fire_damage_bonus",
        "value": 1,
        "lore": "Still warm to the touch, even in the deepest winter.",
    },
    "None": {
        "description": "You carry nothing of sentimental value. Only scars remain.",
        "effect": None,
        "value": 0,
        "lore": "Some say the heaviest burdens are invisible.",
    },
}

# ---------------------------------------------------------------------------
# UI constants
# ---------------------------------------------------------------------------

_ABILITY_LABELS = ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]
_ABILITY_ABBR   = ["STR",      "DEX",       "CON",         "INT",         "WIS",    "CHA"]
_BUILDS = ["Towering", "Broad", "Athletic", "Lean", "Slight", "Gaunt"]

# Mapping from display label to JSON key used in race stat_modifiers
_ABILITY_KEY: dict[str, str] = {
    "Strength":     "strength",
    "Dexterity":    "dexterity",
    "Constitution": "constitution",
    "Intelligence": "intelligence",
    "Wisdom":       "wisdom",
    "Charisma":     "charisma",
}

_STAT_MIN = 8
_STAT_MAX = 20
_STAT_BASE = 10

# ---------------------------------------------------------------------------
# D&D 3.5e stat helpers
# ---------------------------------------------------------------------------

def _mod(score: int) -> int:
    """Return the 3.5e ability modifier for *score*."""
    return (score - 10) // 2


def _bab_at_1(progression: str) -> int:
    """Return Base Attack Bonus at level 1 for the given BAB progression."""
    return {"full": 1, "three_quarter": 0, "half": 0}.get(progression, 0)


def _good_save_base() -> int:
    """Good save base value at level 1 (SRD: 2 + level // 2)."""
    return 2  # level 1: 2 + 0 = 2


def _poor_save_base() -> int:
    """Poor save base value at level 1 (SRD: level // 3)."""
    return 0  # level 1: 0


# ---------------------------------------------------------------------------
# Character Forge App
# ---------------------------------------------------------------------------

class CharacterForgeApp(App[Optional[Dict[str, Any]]]):
    """Ashen Crossroads — Character Forge terminal UI.

    Three-panel layout:
    * **Identity** (left) — Name, Ancestry, Vocation, Keepsake.
    * **Ability Scores** (centre) — Point Buy System with [+]/[−] buttons.
    * **Mortal Coil** (right) — Physical description for Deep Lore AI context.

    The AWAKEN button validates all fields, derives 3.5e stats, calls
    :func:`~src.game.player_persistence.save_new_player`, then exits the app,
    returning the character dict to the caller.

    Args:
        pool_size: Number of points available to spend above the base of 10.
        difficulty: Display name of the chosen difficulty tier.
        permadeath: Whether Iron Path permadeath is active.
    """

    TITLE     = "ASHEN CROSSROADS  ·  Character Forge"
    SUB_TITLE = "Inscribe your legend upon the Mortal Coil"

    CSS = """
    Screen {
        background: #0d0d0d;
    }

    /* ── Three-panel body ── */
    #forge-body {
        height: 1fr;
        layout: horizontal;
    }

    .panel {
        border: solid #3d2b15;
        padding: 0 1;
    }

    .panel-title {
        height: 1;
        background: #1c0f00;
        color: #c89b5f;
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }

    .field-label {
        color: #7a5a30;
        height: 1;
        margin-top: 1;
    }

    /* ── Inputs & Selects ── */
    Input {
        background: #141414;
        border: solid #3d2b15;
        color: #e8d5a0;
    }
    Input:focus {
        border: solid #c89b5f;
    }

    Select {
        background: #141414;
        border: solid #3d2b15;
        color: #e8d5a0;
    }
    Select:focus {
        border: solid #c89b5f;
    }
    SelectOverlay {
        background: #1c1000;
    }

    /* ── Panel widths ── */
    #identity-panel {
        width: 32;
    }
    #scores-panel {
        width: 42;
    }
    #lore-panel {
        width: 1fr;
    }

    /* ── Pool display ── */
    #pool-display {
        height: 3;
        color: #c89b5f;
        text-align: center;
        text-style: bold;
        content-align: center middle;
        margin-bottom: 1;
    }
    #pool-display.pool-zero {
        color: #50c878;
    }
    #pool-display.pool-negative {
        color: #ff6b6b;
    }

    /* ── Score rows ── */
    .score-row {
        height: 3;
        layout: horizontal;
        margin-bottom: 0;
    }
    .score-label {
        width: 5;
        height: 3;
        color: #c89b5f;
        text-style: bold;
        content-align: left middle;
    }
    .score-value {
        width: 4;
        height: 3;
        color: #e8d5a0;
        text-align: center;
        content-align: center middle;
        text-style: bold;
    }
    .score-btn {
        width: 3;
        height: 3;
        min-width: 3;
        background: #1c0800;
        color: #c89b5f;
        border: solid #3d2b15;
    }
    .score-btn:hover {
        background: #3d2b15;
    }
    .score-mod {
        width: 5;
        height: 3;
        color: #7a5a30;
        content-align: left middle;
        padding-left: 1;
    }
    .score-racial {
        width: 4;
        height: 3;
        content-align: left middle;
    }

    /* ── Bottom bar ── */
    #bottom-bar {
        height: 5;
        layout: horizontal;
        padding: 1 2;
        background: #0a0a0a;
        border-top: solid #3d2b15;
    }
    #status-container {
        width: 3fr;
        height: 3;
        color: #7a5a30;
        content-align: left middle;
        padding: 0 1;
    }
    #awaken-btn {
        width: 26;
        height: 3;
        background: #1c0800;
        color: #c89b5f;
        border: solid #c89b5f;
        text-style: bold;
    }
    #awaken-btn:hover {
        background: #c89b5f;
        color: #0d0d0d;
    }
    """

    def __init__(
        self,
        *,
        pool_size: int = 25,
        difficulty: str = "Medium",
        permadeath: bool = False,
    ) -> None:
        super().__init__()
        self._pool_size = pool_size
        self._difficulty = difficulty
        self._permadeath = permadeath
        # Track mutable scores; start every stat at the base value
        self._scores: dict[str, int] = {ab: _STAT_BASE for ab in _ABILITY_LABELS}
        self._pool_remaining: int = pool_size
        # Racial modifiers for the currently selected ancestry (stat key → int)
        self._racial_mods: dict[str, int] = {}

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Horizontal(id="forge-body"):

            # ── Identity Panel ──────────────────────────────────────────
            with Vertical(id="identity-panel", classes="panel"):
                yield Static("⚔  IDENTITY", classes="panel-title")

                yield Label("Character Name", classes="field-label")
                yield Input(placeholder="Enter name…", id="input-name")

                yield Label("Ancestry  (Lineage)", classes="field-label")
                yield Select(
                    [(r["name"], r["name"]) for r in _RACES],
                    prompt="Choose ancestry…",
                    id="select-ancestry",
                )

                yield Label("Vocation  (Class)", classes="field-label")
                yield Select(
                    [(c["name"], c["name"]) for c in _CLASSES],
                    prompt="Choose vocation…",
                    id="select-vocation",
                )

                yield Label("Keepsake  (optional)", classes="field-label")
                yield Select(
                    [(k, k) for k in _KEEPSAKES],
                    prompt="Choose keepsake…",
                    id="select-keepsake",
                )

            # ── Ability Scores Panel ────────────────────────────────────
            with Vertical(id="scores-panel", classes="panel"):
                yield Static("🎲  ABILITY SCORES", classes="panel-title")
                diff_label = self._difficulty
                if self._permadeath:
                    diff_label += "  [bold red]☠ PERMADEATH[/bold red]"
                yield Static(
                    f"[dim]Point Buy — Difficulty: [/dim][bold]{diff_label}[/bold]\n"
                    f"[dim]Base: 10 each  ·  Min: {_STAT_MIN}  ·  Use all points to Awaken.[/dim]",
                    markup=True,
                )
                yield Static(
                    self._pool_label(),
                    id="pool-display",
                    markup=True,
                )
                for abbr, ability in zip(_ABILITY_ABBR, _ABILITY_LABELS):
                    with Horizontal(classes="score-row"):
                        yield Static(abbr, classes="score-label")
                        yield Button("−", id=f"btn-minus-{abbr.lower()}", classes="score-btn")
                        yield Static(
                            str(_STAT_BASE),
                            id=f"score-val-{abbr.lower()}",
                            classes="score-value",
                        )
                        yield Button("+", id=f"btn-plus-{abbr.lower()}",  classes="score-btn")
                        yield Static(
                            self._mod_label(_STAT_BASE),
                            id=f"score-mod-{abbr.lower()}",
                            classes="score-mod",
                        )
                        yield Static(
                            "",
                            id=f"score-racial-{abbr.lower()}",
                            classes="score-racial",
                            markup=True,
                        )

            # ── Mortal Coil Panel ───────────────────────────────────────
            with Vertical(id="lore-panel", classes="panel"):
                yield Static("📜  MORTAL COIL", classes="panel-title")
                yield Static(
                    '[dim italic]"What manner of creature stumbled\n'
                    ' through the veil into the Crossroads?"[/dim italic]',
                    markup=True,
                )

                yield Label("Age  (years)", classes="field-label")
                yield Input(placeholder="e.g. 24", id="input-age")

                yield Label("Build", classes="field-label")
                yield Select(
                    [(b, b) for b in _BUILDS],
                    prompt="Choose build…",
                    id="select-build",
                )

                yield Label("Eye Aspect", classes="field-label")
                yield Input(
                    placeholder="e.g. Storm-grey, hollow",
                    id="input-eye-aspect",
                )

                yield Label("Distinguishing Marks", classes="field-label")
                yield Input(
                    placeholder="e.g. Scar across left jaw",
                    id="input-marks",
                )

        # ── Bottom bar ──────────────────────────────────────────────────
        with Horizontal(id="bottom-bar"):
            yield Static(
                "[ Awaiting inscription… ]",
                id="status-container",
            )
            yield Button("⚡  AWAKEN  ⚡", id="awaken-btn", variant="default", disabled=True)

        yield Footer()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _pool_label(self) -> str:
        remaining = self._pool_remaining
        if remaining == 0:
            return f"[bold green]Pool: {remaining} remaining — Ready to Awaken![/bold green]"
        elif remaining < 0:
            return f"[bold red]Pool: {remaining} remaining — Over budget![/bold red]"
        else:
            return f"Pool: [bold]{remaining}[/bold] points remaining"

    @staticmethod
    def _mod_label(score: int) -> str:
        mod = _mod(score)
        sign = "+" if mod >= 0 else ""
        return f"({sign}{mod})"

    def _refresh_pool_display(self) -> None:
        pool_widget = self.query_one("#pool-display", Static)
        pool_widget.update(self._pool_label())
        # Update AWAKEN button disabled state
        awaken_btn = self.query_one("#awaken-btn", Button)
        awaken_btn.disabled = (self._pool_remaining != 0)

    def _refresh_score_row(self, ability: str, abbr: str) -> None:
        pb_score = self._scores[ability]  # base 10 + point-buy
        racial = self._racial_mods.get(_ABILITY_KEY[ability], 0)
        total = pb_score + racial

        self.query_one(f"#score-val-{abbr.lower()}", Static).update(str(pb_score))
        self.query_one(f"#score-mod-{abbr.lower()}", Static).update(self._mod_label(total))

        racial_widget = self.query_one(f"#score-racial-{abbr.lower()}", Static)
        if racial > 0:
            racial_widget.update(f"[bold #c89b5f]+{racial}[/bold #c89b5f]")
        elif racial < 0:
            racial_widget.update(f"[bold red]{racial}[/bold red]")
        else:
            racial_widget.update("")

    def _refresh_all_score_rows(self) -> None:
        """Refresh every ability score row (e.g. after ancestry change)."""
        for abbr, ability in zip(_ABILITY_ABBR, _ABILITY_LABELS):
            self._refresh_score_row(ability, abbr)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""

        # ── Score [+] / [−] buttons ────────────────────────────────────
        for abbr, ability in zip(_ABILITY_ABBR, _ABILITY_LABELS):
            if btn_id == f"btn-plus-{abbr.lower()}":
                if self._pool_remaining > 0 and self._scores[ability] < _STAT_MAX:
                    self._scores[ability] += 1
                    self._pool_remaining -= 1
                    self._refresh_score_row(ability, abbr)
                    self._refresh_pool_display()
                return
            if btn_id == f"btn-minus-{abbr.lower()}":
                if self._scores[ability] > _STAT_MIN:
                    self._scores[ability] -= 1
                    self._pool_remaining += 1
                    self._refresh_score_row(ability, abbr)
                    self._refresh_pool_display()
                return

        if btn_id == "awaken-btn":
            self._attempt_awaken()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "select-ancestry":
            if event.value is Select.BLANK:
                self._racial_mods = {}
            else:
                race_data = _RACE_MAP.get(str(event.value), {})
                self._racial_mods = race_data.get("stat_modifiers", {})
            self._refresh_all_score_rows()

    # ------------------------------------------------------------------
    # Validation & character construction
    # ------------------------------------------------------------------

    def _attempt_awaken(self) -> None:
        """Validate, build character dict, persist, and exit the app."""
        status = self.query_one("#status-container", Static)

        # ── Mandatory identity fields ──────────────────────────────────
        name = self.query_one("#input-name", Input).value.strip()
        ancestry_val = self.query_one("#select-ancestry", Select).value
        vocation_val = self.query_one("#select-vocation", Select).value

        if not name:
            status.update(
                "[bold red]✗  A name must be inscribed upon the Mortal Coil.[/bold red]"
            )
            return
        if ancestry_val is Select.BLANK:
            status.update(
                "[bold red]✗  Choose an Ancestry — your Lineage shapes your flesh.[/bold red]"
            )
            return
        if vocation_val is Select.BLANK:
            status.update(
                "[bold red]✗  Choose a Vocation — your calling echoes through the Crossroads.[/bold red]"
            )
            return

        # ── Pool validation ────────────────────────────────────────────
        if self._pool_remaining != 0:
            status.update(
                "[bold red]✗  All points must be spent before you can Awaken.[/bold red]"
            )
            return

        # ── Read scores from internal state ───────────────────────────
        scores: dict[str, int] = dict(self._scores)

        # ── Optional Mortal Coil fields ────────────────────────────────
        keepsake_val = self.query_one("#select-keepsake", Select).value
        age_raw      = self.query_one("#input-age", Input).value.strip()
        build_val    = self.query_one("#select-build", Select).value
        eye_aspect   = self.query_one("#input-eye-aspect", Input).value.strip()
        marks        = self.query_one("#input-marks", Input).value.strip()

        try:
            age = int(age_raw) if age_raw else 0
        except ValueError:
            age = 0

        keepsake_name = (
            str(keepsake_val) if keepsake_val is not Select.BLANK else "None"
        )
        build = str(build_val) if build_val is not Select.BLANK else "Unknown"

        # ── Build & persist ────────────────────────────────────────────
        status.update("[yellow]⚙  Inscribing soul upon the Mortal Coil…[/yellow]")

        char_dict = self._build_character_dict(
            name=name,
            ancestry=str(ancestry_val),
            vocation=str(vocation_val),
            keepsake=keepsake_name,
            scores=scores,
            age=age,
            build=build,
            eye_aspect=eye_aspect or "Undisclosed",
            marks=marks or "None noted",
        )

        try:
            from src.game.player_persistence import save_new_player
            save_new_player(char_dict)
        except Exception as exc:  # noqa: BLE001
            status.update(f"[bold red]✗  Persistence error: {exc}[/bold red]")
            return

        # Hand control back to the launcher.
        self.exit(result=char_dict)

    # ------------------------------------------------------------------
    # 3.5e character construction
    # ------------------------------------------------------------------

    def _build_character_dict(
        self,
        *,
        name: str,
        ancestry: str,
        vocation: str,
        keepsake: str,
        scores: dict[str, int],
        age: int,
        build: str,
        eye_aspect: str,
        marks: str,
    ) -> dict[str, Any]:
        """Derive all 3.5e stats and return a serialisable character dict."""

        race_data    = _RACE_MAP.get(ancestry, {})
        class_data   = _CLASS_MAP.get(vocation, {})
        keepsake_data = _KEEPSAKES.get(keepsake, _KEEPSAKES["None"])

        # ── Apply racial ability modifiers ─────────────────────────────
        racial_mods: dict[str, int] = race_data.get("stat_modifiers", {})
        final_scores: dict[str, int] = {
            ab: scores[ab] + racial_mods.get(_ABILITY_KEY[ab], 0)
            for ab in _ABILITY_LABELS
        }

        str_score = final_scores["Strength"]
        dex_score = final_scores["Dexterity"]
        con_score = final_scores["Constitution"]
        int_score = final_scores["Intelligence"]
        wis_score = final_scores["Wisdom"]
        cha_score = final_scores["Charisma"]

        con_mod = _mod(con_score)
        dex_mod = _mod(dex_score)
        wis_mod = _mod(wis_score)

        # ── Class-derived values ───────────────────────────────────────
        hit_die   = class_data.get("hit_die", 6)
        bab_prog  = class_data.get("bab_progression", "half")
        good_saves: list[str] = class_data.get("good_saves", [])

        # Level 1: maximum HD + CON modifier
        hp_base = hit_die + con_mod
        hp_bonus = keepsake_data["value"] if keepsake_data["effect"] == "max_hp_bonus" else 0
        hp = max(1, hp_base + hp_bonus)

        ac_bonus = keepsake_data["value"] if keepsake_data["effect"] == "ac_bonus"      else 0
        ac       = 10 + dex_mod + ac_bonus

        saves_bonus = keepsake_data["value"] if keepsake_data["effect"] == "all_saves_bonus" else 0

        fort   = (_good_save_base() if "fortitude" in good_saves else _poor_save_base()) + con_mod + saves_bonus
        reflex = (_good_save_base() if "reflex"    in good_saves else _poor_save_base()) + dex_mod + saves_bonus
        will   = (_good_save_base() if "will"      in good_saves else _poor_save_base()) + wis_mod + saves_bonus

        speed_bonus = keepsake_data["value"] if keepsake_data["effect"] == "speed_bonus" else 0
        base_speed  = race_data.get("base_speed", 30) + speed_bonus

        # ── Mortal Coil / Deep Lore context ───────────────────────────
        # Formatted so it can be injected verbatim as NPC dialogue AI context.
        deep_lore = (
            f"{name} is a {age}-year-old {ancestry} of {build.lower()} build. "
            f"Their eyes are {eye_aspect.lower()}. "
            f"Notable distinguishing marks: {marks}. "
            f"Vocation: {vocation}."
        )
        physical_description: dict[str, Any] = {
            "name":               name,
            "age":                age,
            "build":              build,
            "eye_aspect":         eye_aspect,
            "distinguishing_marks": marks,
            "deep_lore_context":  deep_lore,
        }

        # ── Final character dict (3.5e SRD layout) ────────────────────
        return {
            "version":    "3.5e-srd",
            "name":       name,
            "race":       ancestry,
            "char_class": vocation,
            "level":      1,

            # ── Difficulty / run metadata ──────────────────────────────
            "difficulty":        self._difficulty,
            "permadeath_status": self._permadeath,
            "starting_pool":     self._pool_size,

            # ── Physical description (Deep Lore for NPC dialogue AI) ──
            "physical_description": physical_description,

            # ── Six ability scores (post racial adjustment) ────────────
            "ability_scores": {
                "Strength":     str_score,
                "Dexterity":    dex_score,
                "Constitution": con_score,
                "Intelligence": int_score,
                "Wisdom":       wis_score,
                "Charisma":     cha_score,
            },
            "ability_modifiers": {
                "Strength":     _mod(str_score),
                "Dexterity":    dex_mod,
                "Constitution": con_mod,
                "Intelligence": _mod(int_score),
                "Wisdom":       wis_mod,
                "Charisma":     _mod(cha_score),
            },

            # ── Pre-racial base scores (audit trail) ──────────────────
            "base_ability_scores": dict(scores),
            "racial_modifiers":    racial_mods,
            "racial_traits":       race_data.get("special_abilities", []),
            "size":                race_data.get("size", "Medium"),

            # ── Core combat stats ──────────────────────────────────────
            "hit_die":          hit_die,
            "hit_points":       hp,
            "armor_class":      ac,
            "initiative":       dex_mod,
            "base_attack_bonus": _bab_at_1(bab_prog),
            "bab_progression":  bab_prog,
            "saving_throws": {
                "fortitude": fort,
                "reflex":    reflex,
                "will":      will,
            },
            "good_saves": good_saves,
            "speed":      base_speed,

            # ── Keepsake ───────────────────────────────────────────────
            "keepsake": {
                "name":        keepsake,
                "description": keepsake_data["description"],
                "lore":        keepsake_data.get("lore", ""),
                "effect":      keepsake_data["effect"],
                "value":       keepsake_data["value"],
            },

            # ── Starting state ─────────────────────────────────────────
            "inventory":        [],
            "gold":             0,
            "experience_points": 0,
            "conditions":       [],
        }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(
    pool_size: int = 25,
    difficulty: str = "Medium",
    permadeath: bool = False,
) -> None:
    """Launch the Character Forge and print a confirmation on exit."""
    app = CharacterForgeApp(
        pool_size=pool_size,
        difficulty=difficulty,
        permadeath=permadeath,
    )
    result = app.run()

    if result is not None:
        console = Console()
        console.print(
            f"\n[bold #c89b5f]⚡  {result['name']} awakens from the Ashen Crossroads.[/bold #c89b5f]"
        )
        console.print(
            f"   [dim]{result['race']} {result['char_class']}  ·  "
            f"HP {result['hit_points']}  ·  "
            f"AC {result['armor_class']}  ·  "
            f"BAB +{result['base_attack_bonus']}[/dim]"
        )
        console.print(
            f"   [dim]Saved → data/player.json[/dim]\n"
        )
    else:
        Console().print("\n[dim]Character Forge closed without saving.[/dim]\n")


if __name__ == "__main__":
    main()
