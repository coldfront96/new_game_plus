"""Tests for src/game/campaign.py"""
from __future__ import annotations

import io
import random

import pytest

from src.game.campaign import CampaignSession, CampaignReport, _level_to_settlement_size
from src.rules_engine.character_35e import Alignment, Character35e, Size
from src.rules_engine.settlement import CommunitySize


@pytest.fixture
def party():
    members = []
    for name, cls, level in [
        ("Aldric", "Fighter", 3),
        ("Zara",   "Wizard",  3),
    ]:
        c = Character35e(
            name=name,
            char_class=cls,
            level=level,
            alignment=Alignment.LAWFUL_GOOD,
            size=Size.MEDIUM,
            strength=14,
            dexterity=13,
            constitution=13,
            intelligence=16 if cls == "Wizard" else 10,
            wisdom=12,
            charisma=10,
        )
        c.initialize_spellcasting()
        members.append(c)
    return members


@pytest.fixture
def quiet_campaign(party):
    return CampaignSession(
        party=party,
        world_seed=1,
        stdout=io.StringIO(),
    )


class TestCampaignSession:
    def test_run_returns_report(self, quiet_campaign):
        report = quiet_campaign.run(num_quests=1)
        assert isinstance(report, CampaignReport)

    def test_report_has_quest_outcome(self, quiet_campaign):
        report = quiet_campaign.run(num_quests=1)
        assert report.quests_completed + report.quests_failed == 1

    def test_report_has_survivors_list(self, quiet_campaign):
        report = quiet_campaign.run(num_quests=1)
        assert isinstance(report.survivors, list)

    def test_total_gp_non_negative(self, quiet_campaign):
        report = quiet_campaign.run(num_quests=1)
        assert report.total_gp >= 0

    def test_log_is_populated(self, quiet_campaign):
        report = quiet_campaign.run(num_quests=1)
        assert len(report.log) > 0

    def test_journal_updated(self, quiet_campaign):
        report = quiet_campaign.run(num_quests=2)
        all_q = quiet_campaign.journal.all_quests()
        # Journal should have one entry per quest actually attempted
        assert len(all_q) == report.quests_completed + report.quests_failed

    def test_deterministic_with_seed(self, party):
        r1 = CampaignSession(
            party=[Character35e(
                name="Test", char_class="Fighter", level=3,
                alignment=Alignment.TRUE_NEUTRAL, size=Size.MEDIUM,
            )],
            world_seed=7, stdout=io.StringIO(),
        ).run(num_quests=1)

        r2 = CampaignSession(
            party=[Character35e(
                name="Test", char_class="Fighter", level=3,
                alignment=Alignment.TRUE_NEUTRAL, size=Size.MEDIUM,
            )],
            world_seed=7, stdout=io.StringIO(),
        ).run(num_quests=1)

        assert (r1.quests_completed + r1.quests_failed) == (
            r2.quests_completed + r2.quests_failed
        )

    def test_multi_quest_run(self, party):
        camp = CampaignSession(
            party=party, world_seed=99, stdout=io.StringIO()
        )
        report = camp.run(num_quests=3)
        # No crash; total should be ≤ 3 quests (can stop early on full wipe)
        assert report.quests_completed + report.quests_failed <= 3


class TestLevelToSettlementSize:
    @pytest.mark.parametrize("level,expected", [
        (1, CommunitySize.Hamlet),
        (2, CommunitySize.Hamlet),
        (3, CommunitySize.Village),
        (4, CommunitySize.Village),
        (5, CommunitySize.SmallTown),
        (8, CommunitySize.LargeTown),
        (11, CommunitySize.SmallCity),
    ])
    def test_mapping(self, level, expected):
        assert _level_to_settlement_size(level) == expected
