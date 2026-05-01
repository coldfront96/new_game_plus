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
            quest_id=str(uuid.uuid4()),
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
