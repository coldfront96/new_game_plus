"""
tests/overseer_ui/test_setup_wizard.py
---------------------------------------
Unit tests for PH6-001 · PH6-002 · PH6-004 — CampaignWizardState and
CampaignWizardScreen.
"""
from __future__ import annotations

import pytest

from src.overseer_ui.setup_wizard import (
    CampaignWizardState,
    _load_campaign_from_dict,
    _wizard_state,
)


# ---------------------------------------------------------------------------
# PH6-001 · CampaignWizardState
# ---------------------------------------------------------------------------

class TestCampaignWizardState:
    def test_default_selected_mode_is_none(self):
        s = CampaignWizardState()
        assert s.selected_mode is None

    def test_default_seed_is_none(self):
        s = CampaignWizardState()
        assert s.seed is None

    def test_default_campaign_session_is_none(self):
        s = CampaignWizardState()
        assert s.campaign_session is None

    def test_set_selected_mode(self):
        s = CampaignWizardState()
        s.selected_mode = "sandbox"
        assert s.selected_mode == "sandbox"

    def test_set_seed(self):
        s = CampaignWizardState()
        s.seed = 42
        assert s.seed == 42

    def test_has_slots(self):
        s = CampaignWizardState()
        assert not hasattr(s, "__dict__")

    def test_valid_modes(self):
        for mode in ("sandbox", "premade", "world_builder"):
            s = CampaignWizardState()
            s.selected_mode = mode
            assert s.selected_mode == mode


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

class TestWizardStateSingleton:
    def test_singleton_exists(self):
        assert _wizard_state is not None

    def test_singleton_is_campaign_wizard_state(self):
        assert isinstance(_wizard_state, CampaignWizardState)


# ---------------------------------------------------------------------------
# _load_campaign_from_dict helper
# ---------------------------------------------------------------------------

class TestLoadCampaignFromDict:
    def test_returns_campaign_session(self):
        from src.game.campaign import CampaignSession
        result = _load_campaign_from_dict({"seed": 99})
        assert isinstance(result, CampaignSession)

    def test_accepts_none_seed(self):
        from src.game.campaign import CampaignSession
        result = _load_campaign_from_dict({})
        assert isinstance(result, CampaignSession)

    def test_accepts_chunks_key(self):
        from src.game.campaign import CampaignSession
        result = _load_campaign_from_dict({"seed": 1, "chunks": [], "faction_records": []})
        assert isinstance(result, CampaignSession)
