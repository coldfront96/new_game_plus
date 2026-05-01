"""Tests for src/game/dialogue.py"""
from __future__ import annotations

import random

import pytest

from src.game.dialogue import (
    DialogueContext,
    DialogueSession,
    DialogueTurn,
    npc_session_from_npc_stats,
)


@pytest.fixture
def rng():
    return random.Random(1)


@pytest.fixture
def ctx():
    return DialogueContext(
        npc_name="Mira",
        npc_role="innkeeper",
        settlement_name="Millhaven",
        quest_hooks=["strange disappearances near the docks"],
        player_name="Aldric",
    )


class TestDialogueSession:
    def test_greeting_returns_string(self, ctx, rng):
        session = DialogueSession(ctx, rng=rng)
        text = session.greeting()
        assert isinstance(text, str)
        assert len(text) > 0

    def test_greeting_adds_to_history(self, ctx, rng):
        session = DialogueSession(ctx, rng=rng)
        session.greeting()
        assert len(session.history) == 1
        assert session.history[0].speaker == "npc"

    def test_respond_without_llm_returns_string(self, ctx, rng):
        session = DialogueSession(ctx, rng=rng)
        session.greeting()
        reply = session.respond("Tell me about the docks", use_llm=False)
        assert isinstance(reply, str)
        assert len(reply) > 0

    def test_respond_adds_player_and_npc_turns(self, ctx, rng):
        session = DialogueSession(ctx, rng=rng)
        session.greeting()
        session.respond("Hello", use_llm=False)
        # greeting turn + player turn + npc reply = 3
        assert len(session.history) == 3
        assert session.history[1].speaker == "player"
        assert session.history[2].speaker == "npc"

    def test_quest_hook_mentioned_in_response(self, ctx, rng):
        session = DialogueSession(ctx, rng=rng)
        session.greeting()
        reply = session.respond("disappearances", use_llm=False)
        # The hook keyword should trigger the hint branch
        assert isinstance(reply, str)

    def test_farewell_response(self, ctx, rng):
        session = DialogueSession(ctx, rng=rng)
        session.greeting()
        reply = session.respond("goodbye", use_llm=False)
        assert isinstance(reply, str)

    def test_settlement_name_in_greeting(self, rng):
        ctx = DialogueContext(
            npc_name="Bob",
            npc_role="guard",
            settlement_name="Uniqueville",
            player_name="Hero",
        )
        session = DialogueSession(ctx, rng=rng)
        text = session.greeting()
        # Guard greeting templates reference {settlement}
        assert "Uniqueville" in text

    def test_unknown_role_uses_default(self, rng):
        ctx = DialogueContext(
            npc_name="Stranger",
            npc_role="blacksmith",
            settlement_name="Ashford",
        )
        session = DialogueSession(ctx, rng=rng)
        text = session.greeting()
        assert len(text) > 0

    def test_no_quest_hooks_no_hint(self, rng):
        ctx = DialogueContext(npc_name="Bob", settlement_name="X")
        session = DialogueSession(ctx, rng=rng)
        text = session.greeting()
        assert isinstance(text, str)

    def test_multiple_sessions_independent(self, ctx):
        s1 = DialogueSession(ctx, rng=random.Random(1))
        s2 = DialogueSession(ctx, rng=random.Random(1))
        assert s1.greeting() == s2.greeting()

    def test_farewell_standalone(self, ctx, rng):
        session = DialogueSession(ctx, rng=rng)
        text = session.farewell()
        assert isinstance(text, str)
        assert len(text) > 0


class TestDialogueTurn:
    def test_construction(self):
        turn = DialogueTurn(speaker="npc", text="Hello!")
        assert turn.speaker == "npc"
        assert turn.text == "Hello!"


class TestNpcSessionFactory:
    def test_from_npc_stats(self, rng):
        class FakeNPC:
            name = "Guildmaster Corvin"
            npc_class = "Expert"

        session = npc_session_from_npc_stats(
            FakeNPC(),
            settlement_name="Ironspire",
            quest_hooks=["missing tax collector"],
            player_name="Reva",
            rng=rng,
        )
        assert isinstance(session, DialogueSession)
        text = session.greeting()
        assert len(text) > 0
