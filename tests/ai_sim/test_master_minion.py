"""
tests/ai_sim/test_master_minion.py
-----------------------------------
Unit tests for the master/minion combined initiative simulator (E-064).

Covers:
  * RoundReport dataclass fields
  * simulate_round_with_links: initiative map, move-action spend, damage propagation,
    share-spell results, empathic-link messages
"""

from __future__ import annotations

import random as _random
from dataclasses import dataclass
from typing import Any

import pytest

from src.ai_sim.master_minion import RoundReport, simulate_round_with_links
from src.rules_engine.linked_entity import LinkType, MasterMinionLink


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@dataclass
class _Char:
    """Minimal character stand-in for E-064 tests."""
    char_id: str
    dexterity_mod: int = 0
    metadata: dict = None
    current_hp: int = 100

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


def _make_link(
    master_id: str,
    minion_id: str,
    link_type: LinkType = LinkType.Familiar,
    share_spells: bool = True,
    empathic_link: bool = True,
) -> MasterMinionLink:
    return MasterMinionLink(
        master_id=master_id,
        minion_id=minion_id,
        link_type=link_type,
        share_spells=share_spells,
        empathic_link=empathic_link,
        delivery_touch=False,
        scry_on_familiar=False,
    )


class _DetRng:
    """Deterministic RNG for testing: always returns a fixed value."""
    def __init__(self, value: int = 10):
        self._value = value

    def randint(self, a: int, b: int) -> int:
        return self._value


# ---------------------------------------------------------------------------
# TestRoundReport
# ---------------------------------------------------------------------------

class TestRoundReport:
    """RoundReport dataclass is properly initialised."""

    def test_default_fields(self):
        rr = RoundReport()
        assert rr.initiative_order == []
        assert rr.initiative_map == {}
        assert rr.move_actions_spent == set()
        assert rr.damage_propagated == {}
        assert rr.share_spell_results == []
        assert rr.empathic_messages == []
        assert rr.notes == []

    def test_is_dataclass(self):
        from dataclasses import is_dataclass
        assert is_dataclass(RoundReport)


# ---------------------------------------------------------------------------
# TestSimulateRoundWithLinks
# ---------------------------------------------------------------------------

class TestSimulateRoundWithLinks:
    """E-064: simulate_round_with_links basic contract."""

    def test_returns_round_report(self):
        master = _Char("wizard1")
        link = _make_link("wizard1", "familiar1")
        report = simulate_round_with_links([master], [link], None, _DetRng(10))
        assert isinstance(report, RoundReport)

    def test_initiative_map_contains_master_and_minion(self):
        master = _Char("wizard1", dexterity_mod=2)
        link = _make_link("wizard1", "familiar1")
        report = simulate_round_with_links([master], [link], None, _DetRng(10))
        assert "wizard1" in report.initiative_map
        assert "familiar1" in report.initiative_map

    def test_initiative_order_is_sorted_descending(self):
        master = _Char("w1")
        link = _make_link("w1", "f1")
        report = simulate_round_with_links([master], [link], None, _random)
        rolls = [report.initiative_map[eid] for eid in report.initiative_order]
        assert rolls == sorted(rolls, reverse=True)

    def test_move_action_spent_for_master(self):
        master = _Char("wizard1")
        link = _make_link("wizard1", "familiar1")
        report = simulate_round_with_links([master], [link], None, _DetRng(10))
        assert "wizard1" in report.move_actions_spent

    def test_multiple_links_all_masters_spend_move(self):
        m1 = _Char("w1")
        m2 = _Char("w2")
        links = [_make_link("w1", "f1"), _make_link("w2", "f2")]
        report = simulate_round_with_links([m1, m2], links, None, _DetRng(8))
        assert "w1" in report.move_actions_spent
        assert "w2" in report.move_actions_spent

    def test_no_links_empty_move_actions(self):
        master = _Char("w1")
        report = simulate_round_with_links([master], [], None, _DetRng(10))
        assert report.move_actions_spent == set()

    def test_damage_propagation_five_hp_to_familiar(self):
        master = _Char("wizard1", current_hp=30)
        master.metadata["familiar_damage_taken"] = 5
        link = _make_link("wizard1", "familiar1")
        report = simulate_round_with_links([master], [link], None, _DetRng(10))
        # 5 hp to familiar → 1 hp lost by master
        assert report.damage_propagated.get("wizard1") == 1
        assert master.current_hp == 29

    def test_damage_propagation_ten_hp_to_familiar(self):
        master = _Char("wizard1", current_hp=30)
        master.metadata["familiar_damage_taken"] = 10
        link = _make_link("wizard1", "familiar1")
        report = simulate_round_with_links([master], [link], None, _DetRng(10))
        assert report.damage_propagated.get("wizard1") == 2
        assert master.current_hp == 28

    def test_damage_propagation_less_than_five_no_hp_loss(self):
        master = _Char("wizard1", current_hp=30)
        master.metadata["familiar_damage_taken"] = 4
        link = _make_link("wizard1", "familiar1")
        report = simulate_round_with_links([master], [link], None, _DetRng(10))
        assert report.damage_propagated.get("wizard1") is None
        assert master.current_hp == 30

    def test_familiar_damage_cleared_after_round(self):
        master = _Char("wizard1")
        master.metadata["familiar_damage_taken"] = 10
        link = _make_link("wizard1", "familiar1")
        simulate_round_with_links([master], [link], None, _DetRng(10))
        assert master.metadata["familiar_damage_taken"] == 0

    def test_share_spell_result_logged(self):
        master = _Char("wizard1")
        master.metadata["pending_share_spell"] = {
            "name": "Mage Armor", "range": "Personal", "distance_ft": 0.0
        }
        link = _make_link("wizard1", "familiar1", share_spells=True)
        report = simulate_round_with_links([master], [link], None, _DetRng(10))
        assert len(report.share_spell_results) == 1
        assert "Mage Armor" in report.share_spell_results[0]

    def test_share_spell_fails_if_too_far(self):
        master = _Char("wizard1")
        master.metadata["pending_share_spell"] = {
            "name": "Mage Armor", "range": "Personal", "distance_ft": 10.0
        }
        link = _make_link("wizard1", "familiar1", share_spells=True)
        report = simulate_round_with_links([master], [link], None, _DetRng(10))
        assert any("10.0 ft" in r for r in report.share_spell_results)

    def test_empathic_link_message_logged(self):
        master = _Char("wizard1")
        master.metadata["empathic_sense"] = "fear"
        master.metadata["familiar_distance_miles"] = 0.5
        link = _make_link("wizard1", "familiar1", empathic_link=True)
        report = simulate_round_with_links([master], [link], None, _DetRng(10))
        assert len(report.empathic_messages) == 1
        assert "fear" in report.empathic_messages[0]

    def test_no_pending_spell_no_share_spell_result(self):
        master = _Char("wizard1")
        link = _make_link("wizard1", "familiar1", share_spells=True)
        report = simulate_round_with_links([master], [link], None, _DetRng(10))
        assert report.share_spell_results == []

    def test_no_empathic_sense_no_message(self):
        master = _Char("wizard1")
        link = _make_link("wizard1", "familiar1", empathic_link=True)
        report = simulate_round_with_links([master], [link], None, _DetRng(10))
        assert report.empathic_messages == []

    def test_missing_master_logged_in_notes(self):
        """If master is not in party, a note is logged."""
        link = _make_link("ghost_master", "familiar1")
        report = simulate_round_with_links([], [link], None, _DetRng(10))
        assert any("ghost_master" in n for n in report.notes)

    def test_animal_companion_link_move_action_spent(self):
        druid = _Char("druid1")
        link = _make_link("druid1", "companion1", link_type=LinkType.AnimalCompanion)
        report = simulate_round_with_links([druid], [link], None, _DetRng(10))
        assert "druid1" in report.move_actions_spent
