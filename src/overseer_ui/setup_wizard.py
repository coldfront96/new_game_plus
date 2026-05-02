"""
src/overseer_ui/setup_wizard.py
--------------------------------
PH6-001 · PH6-002 · PH6-004 — Campaign Setup Wizard (Textual TUI).

Provides the entry-point screen that lets the player choose how to begin a
campaign:

* **True Random Sandbox** — generates a 500-year headless world history, saves
  the result to ``data/campaigns/generated_sandbox.json``, then loads it as a
  :class:`~src.game.campaign.CampaignSession`.
* **Premade Modules** — scans ``data/campaigns/`` for pre-built ``.json`` files
  and loads the first one found.
* **World Builder** — switches to :class:`~src.overseer_ui.world_builder.WorldBuilderScreen`.

Usage::

    from src.overseer_ui.setup_wizard import CampaignWizardScreen, _wizard_state

    # Mount in a Textual App
    app.push_screen(CampaignWizardScreen())

    # After user interaction, read result:
    print(_wizard_state.selected_mode)   # "sandbox" | "premade" | "world_builder"
    print(_wizard_state.seed)            # int seed when sandbox mode was chosen
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Static

# ---------------------------------------------------------------------------
# PH6-001 · CampaignWizardState dataclass
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class CampaignWizardState:
    """Mutable state produced by the :class:`CampaignWizardScreen`.

    Attributes:
        selected_mode:    One of ``"sandbox"``, ``"premade"``, or
                          ``"world_builder"``; ``None`` until the player clicks.
        seed:             Random seed chosen for sandbox generation; ``None``
                          until sandbox mode is selected.
        campaign_session: The loaded :class:`~src.game.campaign.CampaignSession`
                          instance, if one has been created.
    """

    selected_mode: Optional[str] = None
    seed: Optional[int] = None
    campaign_session: Optional[object] = None


#: Module-level singleton consumed by all downstream handlers.
_wizard_state: CampaignWizardState = CampaignWizardState()


# ---------------------------------------------------------------------------
# PH6-001 · CampaignWizardScreen
# ---------------------------------------------------------------------------

_CAMPAIGNS_DIR = Path("data/campaigns")


class CampaignWizardScreen(Screen):
    """Textual screen that presents three campaign-start options.

    Three :class:`~textual.widgets.Button` widgets are rendered inside a
    centred ``Vertical`` container:

    * ``[True Random Sandbox]`` — id ``btn_sandbox``
    * ``[Premade Modules]``      — id ``btn_premade``
    * ``[World Builder]``        — id ``btn_world_builder``
    """

    CSS = """
    CampaignWizardScreen {
        align: center middle;
    }
    #wizard-container {
        width: 44;
        height: auto;
        padding: 1 2;
        border: round $accent;
    }
    #wizard-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    Button {
        width: 100%;
        margin-bottom: 1;
    }
    """

    def compose(self) -> ComposeResult:
        from textual.containers import Vertical

        with Vertical(id="wizard-container"):
            yield Static("⚔  New Game Plus  ⚔", id="wizard-title")
            yield Button("[True Random Sandbox]", id="btn_sandbox")
            yield Button("[Premade Modules]", id="btn_premade")
            yield Button("[World Builder]", id="btn_world_builder")

    # ------------------------------------------------------------------
    # PH6-001 · Button handlers
    # ------------------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Dispatch to the appropriate handler based on button id."""
        btn_id = event.button.id
        if btn_id == "btn_sandbox":
            _wizard_state.selected_mode = "sandbox"
            self._handle_sandbox()
        elif btn_id == "btn_premade":
            _wizard_state.selected_mode = "premade"
            self._handle_premade()
        elif btn_id == "btn_world_builder":
            _wizard_state.selected_mode = "world_builder"
            self._handle_world_builder()

    # ------------------------------------------------------------------
    # PH6-004 · True Random Sandbox
    # ------------------------------------------------------------------

    def _handle_sandbox(self) -> None:
        """Generate a 500-year world and load it as a CampaignSession.

        1. Generate a random seed.
        2. Run ``fast_forward_simulation(500, seed)``.
        3. Write the result to ``data/campaigns/generated_sandbox.json``.
        4. Construct a ``CampaignSession`` and switch to the overworld screen.
        """
        from src.world_sim.genesis import fast_forward_simulation
        from src.game.campaign import CampaignSession

        random_seed = random.randint(0, 2**32 - 1)
        _wizard_state.seed = random_seed

        try:
            result = fast_forward_simulation(500, random_seed)

            _CAMPAIGNS_DIR.mkdir(parents=True, exist_ok=True)
            out_path = _CAMPAIGNS_DIR / "generated_sandbox.json"
            out_path.write_text(json.dumps(result, indent=2))

            session = _load_campaign_from_dict(result)
            _wizard_state.campaign_session = session

            self.app.switch_screen("overworld")
        except Exception:
            self.app.notify(
                "Sandbox generation failed — check logs.",
                severity="error",
            )

    # ------------------------------------------------------------------
    # PH6-002 · Premade Modules
    # ------------------------------------------------------------------

    def _handle_premade(self) -> None:
        """Load the first available premade campaign JSON.

        Scans ``data/campaigns/`` for ``.json`` files.  Constructs a
        ``CampaignSession`` from the first file found and switches to the
        overworld screen.
        """
        if not _CAMPAIGNS_DIR.exists():
            self.app.notify(
                "No premade campaigns found in data/campaigns/",
                severity="error",
            )
            return

        json_files = list(_CAMPAIGNS_DIR.glob("*.json"))
        if not json_files:
            self.app.notify(
                "No premade campaigns found in data/campaigns/",
                severity="error",
            )
            return

        try:
            campaign_dict = json.loads(json_files[0].read_text())
            session = _load_campaign_from_dict(campaign_dict)
            _wizard_state.campaign_session = session
            self.app.switch_screen("overworld")
        except Exception:
            self.app.notify(
                "Failed to load premade campaign — check logs.",
                severity="error",
            )

    # ------------------------------------------------------------------
    # World Builder redirect
    # ------------------------------------------------------------------

    def _handle_world_builder(self) -> None:
        """Switch to the WorldBuilderScreen."""
        try:
            from src.overseer_ui.world_builder import WorldBuilderScreen

            self.app.push_screen(WorldBuilderScreen())
        except Exception:
            self.app.notify("World Builder unavailable.", severity="error")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_campaign_from_dict(campaign_dict: dict) -> object:
    """Construct a CampaignSession from a campaign dict.

    The ``CampaignSession`` constructor accepts keyword arguments; the
    campaign dict is passed directly.  If the dict contains a ``"chunks"``
    key, it is forwarded as ``world_chunks``.

    Args:
        campaign_dict: Deserialised campaign JSON (from genesis or saved file).

    Returns:
        A :class:`~src.game.campaign.CampaignSession` instance.
    """
    from src.game.campaign import CampaignSession

    # CampaignSession requires at least a party list; for world-generated
    # campaigns the party is empty until the player configures characters.
    return CampaignSession(
        party=[],
        world_seed=campaign_dict.get("seed"),
    )
