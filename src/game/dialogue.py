"""
src/game/dialogue.py
---------------------
NPC dialogue system.

Drives a conversation with a settlement NPC either via the LLM bridge
(:class:`~src.ai_sim.llm_bridge.LLMClient`) or via a bank of
deterministic scripted fallbacks when no local model is available.

Key types
~~~~~~~~~
* :class:`DialogueTurn` — a single speaker/text exchange.
* :class:`DialogueContext` — everything the NPC "knows" going into the
  conversation (settlement, role, faction, current quests).
* :class:`DialogueSession` — drives the conversation; collects turns and
  exposes them as a plain list for the CLI / TUI.

Usage::

    from src.game.dialogue import DialogueSession, DialogueContext

    ctx = DialogueContext(
        npc_name="Mira",
        npc_role="innkeeper",
        settlement_name="Millhaven",
        faction_name="Merchant Guild",
        quest_hooks=["strange disappearances in the warehouse district"],
    )
    session = DialogueSession(ctx)
    print(session.greeting())
    reply = session.respond("Do you know anything about the missing sailors?")
    print(reply)
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class DialogueTurn:
    """One exchange in a conversation.

    Attributes:
        speaker:  ``"npc"`` or ``"player"``.
        text:     The spoken text.
    """

    speaker: str
    text: str


@dataclass
class DialogueContext:
    """Everything an NPC "knows" going into a conversation.

    Attributes:
        npc_name:        The NPC's given name.
        npc_role:        Role in the settlement (e.g. ``"innkeeper"``).
        settlement_name: Name of the settlement.
        faction_name:    Faction the NPC is affiliated with, if any.
        quest_hooks:     Short descriptive hooks the NPC can mention.
        player_name:     Player character's name (for personalisation).
    """

    npc_name: str
    npc_role: str = "townsperson"
    settlement_name: str = "the village"
    faction_name: str = ""
    quest_hooks: List[str] = field(default_factory=list)
    player_name: str = "adventurer"


# ---------------------------------------------------------------------------
# Scripted fallback lines keyed by NPC role
# ---------------------------------------------------------------------------

_GREETINGS: dict = {
    "innkeeper": [
        "Welcome to the {settlement}! Find yourself a seat — the stew's still warm.",
        "Ah, a traveller! We don't get many through here these days. Glad you made it safely.",
        "The {settlement} Inn is open to all who can pay. What'll it be?",
    ],
    "merchant": [
        "Finest goods this side of the Thornwood — and the prices prove it!",
        "Welcome, friend. I deal in quality wares. Have a look around.",
        "Ah, a new face! Perhaps you're looking to buy — or maybe sell?",
    ],
    "guard": [
        "Halt. State your business in {settlement}.",
        "Move along, unless you've got business with the watch.",
        "Keep your weapons sheathed and there'll be no trouble.",
    ],
    "priest": [
        "Peace be upon you, traveller. The temple is open to all who seek guidance.",
        "May the light protect you on your journey. How can I help?",
        "Welcome, friend. Have you come for healing, or spiritual counsel?",
    ],
    "noble": [
        "I don't usually receive unannounced visitors, but I'll make an exception.",
        "You look like someone who gets things done. I may have a proposition for you.",
        "My name carries weight in this region. I trust yours does too?",
    ],
    "default": [
        "Greetings, stranger. You're not from around here, are you?",
        "Well met, traveller. {settlement} doesn't see many outsiders.",
        "Hello there. Can I help you with something?",
    ],
}

_QUEST_HOOK_INTROS: List[str] = [
    "Between you and me, there's been some trouble lately. {hook}",
    "I probably shouldn't say this to a stranger, but {hook}.",
    "If you're looking for work, you might want to know: {hook}.",
    "Word is — and don't quote me on this — {hook}.",
]

_GENERIC_RESPONSES: dict = {
    "farewell": [
        "Safe travels, {player}.",
        "Watch your back out there.",
        "Come back if you need anything.",
        "May fortune favour you on the road.",
    ],
    "unknown": [
        "I'm afraid I don't know much about that.",
        "You'd be better off asking someone else.",
        "That's beyond what I can help with, I'm sorry.",
        "I haven't heard anything about that, no.",
    ],
    "agree": [
        "Aye, that's right.",
        "Indeed — you've heard it correctly.",
        "Couldn't agree more.",
    ],
}


def _pick(options: List[str], rng: random.Random) -> str:
    return rng.choice(options)


def _format(template: str, ctx: DialogueContext) -> str:
    return (
        template
        .replace("{settlement}", ctx.settlement_name)
        .replace("{player}", ctx.player_name)
        .replace("{npc}", ctx.npc_name)
        .replace("{faction}", ctx.faction_name or "the guild")
    )


# ---------------------------------------------------------------------------
# Async LLM helper (optional — used when a local model is reachable)
# ---------------------------------------------------------------------------

async def _llm_generate(
    ctx: DialogueContext,
    history: List[DialogueTurn],
    player_input: str,
    *,
    model: str = "mistral",
    base_url: str = "http://localhost:11434",
) -> str:
    """Try to generate a reply via the local LLM bridge. Returns ``""`` on failure."""
    try:
        from src.ai_sim.llm_bridge import LLMClient

        system = (
            f"You are {ctx.npc_name}, a {ctx.npc_role} in {ctx.settlement_name}. "
            f"Speak in character — one or two sentences, colloquial fantasy tone. "
        )
        if ctx.faction_name:
            system += f"You are affiliated with {ctx.faction_name}. "
        if ctx.quest_hooks:
            system += (
                "You know about the following local troubles and may hint at them: "
                + "; ".join(ctx.quest_hooks) + ". "
            )

        # Build a minimal conversation history string
        history_text = "\n".join(
            f"{t.speaker.upper()}: {t.text}" for t in history[-6:]
        )
        user_msg = f"{history_text}\nPLAYER: {player_input}\n{ctx.npc_name.upper()}:"

        client = LLMClient(base_url=base_url, model=model)
        reply = await client.query_text(system, user_msg)
        return reply.strip()
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# DialogueSession
# ---------------------------------------------------------------------------

class DialogueSession:
    """Drives a conversation with an NPC.

    Tries the LLM bridge first; falls back to scripted responses when no
    local model is reachable.  All turns are stored in :attr:`history`.

    Args:
        context: Contextual information about this NPC.
        rng:     Random source for scripted line selection.
    """

    def __init__(
        self,
        context: DialogueContext,
        rng: Optional[random.Random] = None,
    ) -> None:
        self.context = context
        self._rng = rng or random.Random()
        self.history: List[DialogueTurn] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def greeting(self) -> str:
        """Generate the NPC's opening greeting line."""
        role = self.context.npc_role.lower()
        options = _GREETINGS.get(role, _GREETINGS["default"])
        text = _format(_pick(options, self._rng), self.context)
        # Append a quest hook hint roughly 50% of the time if hooks exist
        if self.context.quest_hooks and self._rng.random() < 0.5:
            hook = self._rng.choice(self.context.quest_hooks)
            intro = _pick(_QUEST_HOOK_INTROS, self._rng)
            hint = _format(intro.replace("{hook}", hook), self.context)
            text = f"{text} {hint}"
        turn = DialogueTurn(speaker="npc", text=text)
        self.history.append(turn)
        return text

    def respond(self, player_input: str, *, use_llm: bool = True) -> str:
        """Generate the NPC's response to *player_input*.

        Attempts the LLM bridge when *use_llm* is ``True``; falls back to
        the scripted response bank on any failure.

        Args:
            player_input: What the player said.
            use_llm:      Whether to attempt an LLM-generated response.

        Returns:
            The NPC's reply text.
        """
        self.history.append(DialogueTurn(speaker="player", text=player_input))

        reply = ""
        if use_llm:
            import asyncio
            try:
                reply = asyncio.run(
                    _llm_generate(
                        self.context,
                        self.history,
                        player_input,
                    )
                )
            except Exception:
                reply = ""

        if not reply:
            reply = self._scripted_response(player_input)

        turn = DialogueTurn(speaker="npc", text=reply)
        self.history.append(turn)
        return reply

    def farewell(self) -> str:
        """Generate a farewell line."""
        text = _format(
            _pick(_GENERIC_RESPONSES["farewell"], self._rng),
            self.context,
        )
        self.history.append(DialogueTurn(speaker="npc", text=text))
        return text

    # ------------------------------------------------------------------
    # Scripted fallback
    # ------------------------------------------------------------------

    def _scripted_response(self, player_input: str) -> str:
        lower = player_input.lower()

        # Keyword matching for quest hooks
        for hook in self.context.quest_hooks:
            hook_words = set(hook.lower().split())
            if any(w in lower for w in hook_words if len(w) > 4):
                intro = _pick(_QUEST_HOOK_INTROS, self._rng)
                return _format(
                    intro.replace("{hook}", hook),
                    self.context,
                )

        # Farewell detection
        if any(w in lower for w in ("bye", "farewell", "goodbye", "leave")):
            return self.farewell()

        # Generic fallback
        return _format(
            _pick(_GENERIC_RESPONSES["unknown"], self._rng),
            self.context,
        )


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------

def npc_session_from_npc_stats(
    npc_stats: object,
    settlement_name: str = "the village",
    quest_hooks: Optional[List[str]] = None,
    player_name: str = "adventurer",
    rng: Optional[random.Random] = None,
) -> DialogueSession:
    """Build a :class:`DialogueSession` from an :class:`~src.rules_engine.npc_classes.NPCStats`.

    Args:
        npc_stats:       An NPCStats-compatible object with ``name`` and
                         ``npc_class`` attributes.
        settlement_name: Name of the settlement the NPC inhabits.
        quest_hooks:     Optional list of quest hook strings.
        player_name:     The player character's name.
        rng:             RNG for scripted line selection.

    Returns:
        A ready-to-use :class:`DialogueSession`.
    """
    name = getattr(npc_stats, "name", "Townsperson")
    role = str(getattr(npc_stats, "npc_class", "default")).lower()
    ctx = DialogueContext(
        npc_name=name,
        npc_role=role,
        settlement_name=settlement_name,
        quest_hooks=list(quest_hooks or []),
        player_name=player_name,
    )
    return DialogueSession(ctx, rng=rng)
