"""Tests for src/game/quest.py"""
from __future__ import annotations

import random

import pytest

from src.game.quest import Quest, QuestGenerator, QuestJournal, QuestStatus
from src.world_sim.factions import FactionRecord
from src.world_sim.lairs import LairRecord, LairType


@pytest.fixture
def rng():
    return random.Random(42)


@pytest.fixture
def factions():
    return [
        FactionRecord(name="Goblin Warband", alignment="CE", hostile_to=["Human Settlement"]),
        FactionRecord(name="Human Settlement", alignment="LG", hostile_to=[]),
    ]


@pytest.fixture
def lairs():
    return [
        LairRecord(
            lair_id="lair-001",
            monster_name="Goblin",
            lair_type=LairType.Cave,
            chunk_id="chunk-0",
            width=8, depth=8, height=4,
        )
    ]


class TestQuestGenerator:
    def test_generates_quest(self, rng, factions, lairs):
        quest = QuestGenerator.generate(
            factions=factions, lairs=lairs, rng=rng
        )
        assert isinstance(quest, Quest)

    def test_quest_has_non_empty_title(self, rng, factions, lairs):
        quest = QuestGenerator.generate(
            factions=factions, lairs=lairs, rng=rng
        )
        assert len(quest.title) > 0

    def test_quest_has_description(self, rng, factions, lairs):
        quest = QuestGenerator.generate(
            factions=factions, lairs=lairs, rng=rng
        )
        assert len(quest.description) > 0

    def test_quest_reward_scales_with_level(self, factions, lairs):
        q_low = QuestGenerator.generate(
            factions=factions, lairs=lairs, party_level=1, rng=random.Random(1)
        )
        q_high = QuestGenerator.generate(
            factions=factions, lairs=lairs, party_level=10, rng=random.Random(1)
        )
        assert q_high.reward_gp > q_low.reward_gp

    def test_quest_active_by_default(self, rng, factions, lairs):
        quest = QuestGenerator.generate(factions=factions, lairs=lairs, rng=rng)
        assert quest.status == QuestStatus.ACTIVE

    def test_no_factions_no_crash(self, rng):
        quest = QuestGenerator.generate(rng=rng)
        assert isinstance(quest, Quest)

    def test_no_lairs_no_crash(self, rng, factions):
        quest = QuestGenerator.generate(factions=factions, rng=rng)
        assert isinstance(quest, Quest)

    def test_generate_batch(self, rng, factions, lairs):
        quests = QuestGenerator.generate_batch(
            3, factions=factions, lairs=lairs, rng=rng
        )
        assert len(quests) == 3
        ids = {q.quest_id for q in quests}
        assert len(ids) == 3  # all unique IDs

    def test_deterministic_with_same_seed(self, factions, lairs):
        q1 = QuestGenerator.generate(
            factions=factions, lairs=lairs, rng=random.Random(99)
        )
        q2 = QuestGenerator.generate(
            factions=factions, lairs=lairs, rng=random.Random(99)
        )
        assert q1.title == q2.title
        assert q1.description == q2.description


class TestQuest:
    def test_complete(self):
        q = QuestGenerator.generate(rng=random.Random(1))
        q.complete()
        assert q.status == QuestStatus.COMPLETED

    def test_fail(self):
        q = QuestGenerator.generate(rng=random.Random(1))
        q.fail()
        assert q.status == QuestStatus.FAILED

    def test_add_note(self):
        q = QuestGenerator.generate(rng=random.Random(1))
        q.add_note("Found the lair entrance.")
        assert "Found the lair entrance." in q.notes

    def test_serialise_roundtrip(self):
        q = QuestGenerator.generate(rng=random.Random(1))
        q.complete()
        d = q.to_dict()
        restored = Quest.from_dict(d)
        assert restored.quest_id == q.quest_id
        assert restored.status == QuestStatus.COMPLETED
        assert restored.title == q.title


class TestQuestJournal:
    def test_add_and_active(self, rng, factions, lairs):
        journal = QuestJournal()
        q = QuestGenerator.generate(factions=factions, lairs=lairs, rng=rng)
        journal.add(q)
        assert len(journal.active()) == 1

    def test_complete_quest(self, rng):
        journal = QuestJournal()
        q = QuestGenerator.generate(rng=rng)
        journal.add(q)
        result = journal.complete(q.quest_id)
        assert result is True
        assert len(journal.active()) == 0
        assert len(journal.completed()) == 1

    def test_fail_quest(self, rng):
        journal = QuestJournal()
        q = QuestGenerator.generate(rng=rng)
        journal.add(q)
        journal.fail(q.quest_id)
        assert q.status == QuestStatus.FAILED

    def test_complete_unknown_returns_false(self):
        journal = QuestJournal()
        assert journal.complete("nonexistent-id") is False

    def test_get_quest(self, rng):
        journal = QuestJournal()
        q = QuestGenerator.generate(rng=rng)
        journal.add(q)
        fetched = journal.get(q.quest_id)
        assert fetched is q

    def test_all_quests(self, rng):
        journal = QuestJournal()
        for _ in range(3):
            journal.add(QuestGenerator.generate(rng=rng))
        assert len(journal.all_quests()) == 3

    def test_serialise_roundtrip(self, rng):
        journal = QuestJournal()
        for _ in range(2):
            journal.add(QuestGenerator.generate(rng=rng))
        records = journal.to_list()
        restored = QuestJournal.from_list(records)
        assert len(restored.all_quests()) == 2

    def test_multiple_states(self, rng):
        journal = QuestJournal()
        q1 = QuestGenerator.generate(rng=rng)
        q2 = QuestGenerator.generate(rng=rng)
        q3 = QuestGenerator.generate(rng=rng)
        journal.add(q1)
        journal.add(q2)
        journal.add(q3)
        journal.complete(q1.quest_id)
        journal.fail(q2.quest_id)
        assert len(journal.active()) == 1
        assert len(journal.completed()) == 1
        assert len(journal.all_quests()) == 3
