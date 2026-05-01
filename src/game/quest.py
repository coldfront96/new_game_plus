"""
src/game/quest.py
------------------
Quest generation and journal for New Game Plus.

Generates context-driven quests from the world simulation layer — faction
hostilities, lair records, and settlement power centres — so every quest
has a grounded in-world reason to exist.

Key types
~~~~~~~~~
* :class:`Quest`          — a single quest with objective, reward, and status.
* :class:`QuestGenerator` — builds quests from factions, lairs, and settlements.
* :class:`QuestJournal`   — per-party tracker; serialises to a plain dict.

Usage::

    from src.game.quest import QuestGenerator, QuestJournal
    from src.world_sim.factions import FactionRecord
    from src.world_sim.lairs import LairRecord, LairType

    factions = [
        FactionRecord(name="Goblin Warband", alignment="CE", hostile_to=["Human Settlement"]),
        FactionRecord(name="Human Settlement", alignment="LG", hostile_to=[]),
    ]
    lairs = [
        LairRecord("lair-001", "Goblin", LairType.Cave, "chunk-0", 8, 8, 4),
    ]
    quest = QuestGenerator.generate(factions=factions, lairs=lairs)
    journal = QuestJournal()
    journal.add(quest)
    print(journal.active())
"""

from __future__ import annotations

import random
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Sequence


# ---------------------------------------------------------------------------
# Quest status
# ---------------------------------------------------------------------------

class QuestStatus(Enum):
    ACTIVE    = "active"
    COMPLETED = "completed"
    FAILED    = "failed"


# ---------------------------------------------------------------------------
# Quest
# ---------------------------------------------------------------------------

@dataclass
class Quest:
    """A single adventure quest.

    Attributes:
        quest_id:        Unique identifier.
        title:           Short quest title.
        description:     Full flavour/objectives description.
        giver_name:      NPC who issued the quest.
        faction_id:      Faction that benefits from quest completion.
        target_monster:  Primary monster type the party must defeat.
        target_lair_id:  Lair the party must clear (may be empty string).
        encounter_level: EL for the generated encounter.
        reward_gp:       Gold piece reward on completion.
        reward_xp:       Bonus XP awarded per party member.
        status:          Current quest status.
        notes:           Freeform notes added during play.
    """

    quest_id:       str
    title:          str
    description:    str
    giver_name:     str = "Unknown"
    faction_id:     str = ""
    target_monster: str = "monsters"
    target_lair_id: str = ""
    encounter_level: int = 3
    reward_gp:      int = 0
    reward_xp:      int = 0
    status:         QuestStatus = QuestStatus.ACTIVE
    notes:          List[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def complete(self) -> None:
        """Mark this quest as completed."""
        self.status = QuestStatus.COMPLETED

    def fail(self) -> None:
        """Mark this quest as failed."""
        self.status = QuestStatus.FAILED

    def add_note(self, note: str) -> None:
        """Append a freeform progress note."""
        self.notes.append(note)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Quest":
        data = dict(data)
        data["status"] = QuestStatus(data.get("status", "active"))
        return cls(**data)


# ---------------------------------------------------------------------------
# Quest narrative fragments
# ---------------------------------------------------------------------------

_QUEST_TITLES: List[str] = [
    "Clear the {lair_type} of {monster}s",
    "The {monster} Menace",
    "Trouble at the {lair_type}",
    "Drive Out the {monster}s",
    "The {faction} Threat",
    "Bounty: {monster} Pack",
    "Defend {settlement} from {monster}s",
    "The Raid on {lair_type}",
]

_QUEST_DESCRIPTIONS: List[str] = [
    (
        "{faction} raiders have been striking our outlying farms. "
        "We believe their lair is the {lair_type} to the {direction}. "
        "Clear it out and we'll make it worth your while — {gp} gold pieces."
    ),
    (
        "A pack of {monster}s has nested in the {lair_type} nearby. "
        "They've been preying on travellers and livestock for weeks. "
        "Slay their leader and bring proof. Reward: {gp} gp."
    ),
    (
        "Scouts from the {faction} faction have been spotted near {settlement}. "
        "We need someone to drive them back before they grow bolder. "
        "The {lair_type} is their staging ground. {gp} gold awaits the brave."
    ),
    (
        "Ever since the {monster}s moved into the old {lair_type}, "
        "the road has been impassable. Merchants are losing their livelihoods. "
        "Clear the way and {settlement} will reward you handsomely ({gp} gp)."
    ),
]

_DIRECTIONS: List[str] = ["north", "south", "east", "west", "northeast", "southwest"]

_GIVERS: List[str] = [
    "the Mayor", "the Sheriff", "the Guild Master", "Captain Aldren",
    "Elder Vasha", "the Temple Warden", "Merchant Corvin", "Lady Serath",
]


# ---------------------------------------------------------------------------
# QuestGenerator
# ---------------------------------------------------------------------------

class QuestGenerator:
    """Builds :class:`Quest` objects from world-simulation data.

    All generation is deterministic when a seeded RNG is provided.
    """

    @classmethod
    def generate(
        cls,
        *,
        factions: Sequence[Any] = (),
        lairs: Sequence[Any] = (),
        settlement_name: str = "the village",
        party_level: int = 3,
        rng: Optional[random.Random] = None,
    ) -> Quest:
        """Generate a single quest appropriate for the given world context.

        Args:
            factions:        List of :class:`~src.world_sim.factions.FactionRecord`.
            lairs:           List of :class:`~src.world_sim.lairs.LairRecord`.
            settlement_name: Name of the settlement issuing the quest.
            party_level:     Average party level (used to scale EL and reward).
            rng:             RNG for determinism.

        Returns:
            A fully populated :class:`Quest`.
        """
        rng = rng or random.Random()

        # --- Pick a hostile faction if available ---
        hostile = [
            f for f in factions
            if getattr(f, "hostile_to", [])
        ]
        faction = rng.choice(hostile) if hostile else None
        faction_name = getattr(faction, "name", "Unknown Raiders")
        monster_name = faction_name.split()[0] if faction_name else "monster"

        # --- Pick a lair if available ---
        lair = rng.choice(lairs) if lairs else None
        lair_type = "cave"
        lair_id = ""
        if lair is not None:
            lair_type = str(getattr(lair, "lair_type", "cave")).lower().split(".")[-1]
            lair_id = str(getattr(lair, "lair_id", ""))
            monster_name = getattr(lair, "monster_name", monster_name)

        # --- Scale reward ---
        el = max(1, party_level)
        reward_gp = int(el * 100 * (rng.uniform(0.8, 1.2)))
        reward_xp = int(el * 50 * (rng.uniform(0.8, 1.2)))

        # --- Build narrative ---
        direction = rng.choice(_DIRECTIONS)
        giver = rng.choice(_GIVERS)

        title_template = rng.choice(_QUEST_TITLES)
        title = (
            title_template
            .replace("{lair_type}", lair_type.capitalize())
            .replace("{monster}", monster_name)
            .replace("{faction}", faction_name)
            .replace("{settlement}", settlement_name)
        )

        desc_template = rng.choice(_QUEST_DESCRIPTIONS)
        description = (
            desc_template
            .replace("{faction}", faction_name)
            .replace("{lair_type}", lair_type)
            .replace("{monster}", monster_name)
            .replace("{direction}", direction)
            .replace("{settlement}", settlement_name)
            .replace("{gp}", str(reward_gp))
        )

        return Quest(
            quest_id=f"q-{rng.getrandbits(64):016x}",
            title=title,
            description=description,
            giver_name=giver,
            faction_id=faction_name,
            target_monster=monster_name,
            target_lair_id=lair_id,
            encounter_level=el,
            reward_gp=reward_gp,
            reward_xp=reward_xp,
        )

    @classmethod
    def generate_batch(
        cls,
        count: int = 3,
        **kwargs: Any,
    ) -> List[Quest]:
        """Generate *count* quests with the same world context."""
        rng: random.Random = kwargs.pop("rng", random.Random())
        return [cls.generate(rng=rng, **kwargs) for _ in range(count)]


# ---------------------------------------------------------------------------
# QuestJournal
# ---------------------------------------------------------------------------

class QuestJournal:
    """Per-party journal that tracks active and completed quests.

    Serialises to a plain list of dicts for JSON persistence.
    """

    def __init__(self) -> None:
        self._quests: Dict[str, Quest] = {}

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add(self, quest: Quest) -> None:
        """Add a quest to the journal."""
        self._quests[quest.quest_id] = quest

    def get(self, quest_id: str) -> Optional[Quest]:
        """Return the quest with *quest_id*, or ``None``."""
        return self._quests.get(quest_id)

    def complete(self, quest_id: str) -> bool:
        """Mark *quest_id* as completed. Returns ``False`` if not found."""
        quest = self._quests.get(quest_id)
        if quest is None:
            return False
        quest.complete()
        return True

    def fail(self, quest_id: str) -> bool:
        """Mark *quest_id* as failed. Returns ``False`` if not found."""
        quest = self._quests.get(quest_id)
        if quest is None:
            return False
        quest.fail()
        return True

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def active(self) -> List[Quest]:
        """Return all quests with ACTIVE status."""
        return [q for q in self._quests.values() if q.status == QuestStatus.ACTIVE]

    def completed(self) -> List[Quest]:
        """Return all completed quests."""
        return [q for q in self._quests.values() if q.status == QuestStatus.COMPLETED]

    def all_quests(self) -> List[Quest]:
        """Return every quest in the journal."""
        return list(self._quests.values())

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def to_list(self) -> List[Dict[str, Any]]:
        """Serialise to a JSON-compatible list of dicts."""
        return [q.to_dict() for q in self._quests.values()]

    @classmethod
    def from_list(cls, records: List[Dict[str, Any]]) -> "QuestJournal":
        """Reconstruct a :class:`QuestJournal` from serialised records."""
        journal = cls()
        for rec in records:
            journal.add(Quest.from_dict(rec))
        return journal


# ---------------------------------------------------------------------------
# PH3-013 — Artifact Quest Objective Injector
# ---------------------------------------------------------------------------

def inject_artifact_quest(
    artifact: Any,
    threshold: Any,
    journal: "QuestJournal",
    world_seed: int,
    campaign: Any = None,
) -> Quest:
    """Create a quest tied to a freshly forged Mythos artifact and add it to *journal*.

    The quest directs the party to locate and recover the artifact, with a
    description derived from the artifact's lore text and the triggering world
    context (faction growth or chunk danger).

    Quest properties:
        * ``quest_id``:   Deterministic UUID from ``artifact.artifact_id + str(world_seed)``.
        * ``title``:      ``"Retrieve the {artifact.lore_name}"``.
        * ``description``: First :data:`_LORE_EXCERPT_MAX_CHARS` chars of artifact lore + triggering context suffix.
        * ``objective``:  ``"Locate and recover artifact {artifact.artifact_id} from the world."``.
        * ``reward_gp``:  10 % of artifact market value (finder's fee).
        * ``status``:     :attr:`~QuestStatus.ACTIVE`.

    The quest is appended to *journal* via :meth:`QuestJournal.add` and, when
    *campaign* is provided, also to ``campaign.journal``.

    Args:
        artifact:   A :class:`~src.rules_engine.mythos_forge.GeneratedArtifact`.
        threshold:  A :class:`~src.rules_engine.mythos_forge.MythosThresholdRecord`.
        journal:    The active :class:`QuestJournal` for the party.
        world_seed: Integer world seed used for UUID derivation.
        campaign:   Optional active :class:`~src.game.campaign.CampaignSession`;
                    when provided, the quest is also added to ``campaign.journal``.

    Returns:
        The created :class:`Quest`.
    """
    import uuid as _uuid

    # Maximum characters of artifact lore included in the quest description.
    _LORE_EXCERPT_MAX_CHARS = 280

    # Deterministic quest_id
    quest_id = str(_uuid.uuid5(_uuid.NAMESPACE_DNS, f"{artifact.artifact_id}{world_seed}"))

    title = f"Retrieve the {artifact.lore_name}"

    # Description: first _LORE_EXCERPT_MAX_CHARS chars of lore + triggering context
    lore_excerpt = (artifact.lore_history or "")[:_LORE_EXCERPT_MAX_CHARS]
    faction_name = getattr(threshold, "faction_name", None)
    chunk_id = getattr(threshold, "chunk_id", None)
    if faction_name:
        context_suffix = (
            f"The {faction_name} has grown beyond reckoning — only this relic can turn the tide."
        )
    else:
        context_suffix = (
            f"A darkness stirs in chunk {chunk_id} — only this relic can restore balance."
        )
    description = f"{lore_excerpt} {context_suffix}".strip()

    objective = f"Locate and recover artifact {artifact.artifact_id} from the world."

    # Reward: 10 % of artifact market value
    price_gp = getattr(getattr(artifact, "properties", None), "calculated_price_gp", 0)
    reward_gp = int(price_gp * 0.1)

    quest = Quest(
        quest_id=quest_id,
        title=title,
        description=description,
        giver_name="The Mythos Oracle",
        faction_id="",
        target_monster="",
        target_lair_id="",
        encounter_level=1,
        reward_gp=reward_gp,
        reward_xp=0,
        status=QuestStatus.ACTIVE,
    )
    quest.add_note(objective)

    journal.add(quest)

    # Wire into campaign journal if provided
    if campaign is not None:
        camp_journal = getattr(campaign, "journal", None)
        if camp_journal is not None and camp_journal is not journal:
            camp_journal.add(quest)

    return quest
