"""
src/game/campaign.py
---------------------
Top-level campaign loop for New Game Plus.

A :class:`CampaignSession` orchestrates the full game experience by
chaining the subsystems that previously only existed in isolation:

1. **Arrive** — generate a settlement and meet an NPC via the dialogue system.
2. **Accept quest** — QuestGenerator builds a context-driven objective.
3. **Adventure** — run the encounter with full spellcasting via play_session.
4. **Return** — award gold/XP, tick the world, persist the party.

Usage::

    from src.game.campaign import CampaignSession
    from src.rules_engine.character_35e import Alignment, Character35e

    party = [Character35e(name="Aldric", char_class="Fighter", level=3, ...)]
    camp = CampaignSession(party=party, world_seed=42)
    camp.run(num_quests=3)
"""

from __future__ import annotations

import random
import sys
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, TextIO

from src.game.dialogue import DialogueContext, DialogueSession
from src.game.quest import Quest, QuestGenerator, QuestJournal
from src.game.session import SessionReport, play_session
from src.rules_engine.character_35e import Character35e
from src.rules_engine.encounter_extended import EncounterDifficulty
from src.rules_engine.settlement import CommunitySize, generate_settlement


# ---------------------------------------------------------------------------
# CampaignReport
# ---------------------------------------------------------------------------

@dataclass
class CampaignReport:
    """Summary of a completed campaign arc.

    Attributes:
        quests_completed: Number of quests the party successfully finished.
        quests_failed:    Number of quests that ended in party defeat.
        total_xp:         XP awarded to the party across all sessions.
        total_gp:         Gold pieces accumulated (quest rewards + treasure).
        survivors:        Party members still alive at the end.
        log:              Full chronological narrative log.
    """

    quests_completed: int = 0
    quests_failed: int = 0
    total_xp: int = 0
    total_gp: float = 0.0
    survivors: List[Character35e] = dc_field(default_factory=list)
    log: List[str] = dc_field(default_factory=list)


# ---------------------------------------------------------------------------
# CampaignSession
# ---------------------------------------------------------------------------

class CampaignSession:
    """Drives a series of quests from a shared settlement hub.

    Args:
        party:       Pre-built list of player :class:`Character35e`.
        world_seed:  Seed for world generation (terrain, settlements, etc.).
        difficulty:  Default encounter difficulty (affects EL scaling).
        terrain:     Default terrain key.
        stdout:      Output stream for narrative text.
        rng:         RNG for determinism (seeded from *world_seed* if omitted).
    """

    def __init__(
        self,
        party: Sequence[Character35e],
        *,
        world_seed: Optional[int] = None,
        difficulty: str = "average",
        terrain: str = "dungeon",
        stdout: Optional[TextIO] = None,
        rng: Optional[random.Random] = None,
    ) -> None:
        self.party: List[Character35e] = list(party)
        self._difficulty = difficulty
        self._terrain = terrain
        self._out = stdout or sys.stdout
        self._rng = rng or random.Random(world_seed)
        self.journal = QuestJournal()
        self._xp_totals: Dict[str, int] = {c.char_id: 0 for c in party}
        self._gp_total: float = 0.0
        self._collected_log: List[str] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, num_quests: int = 3) -> CampaignReport:
        """Run *num_quests* adventure arcs from start to finish.

        Each arc follows: settlement visit → quest accept → combat → reward.

        Args:
            num_quests: Number of quests to attempt.

        Returns:
            A :class:`CampaignReport` summarising the campaign.
        """
        report = CampaignReport()

        for quest_num in range(1, num_quests + 1):
            self._log(f"\n{'='*60}")
            self._log(f"  QUEST {quest_num} of {num_quests}")
            self._log(f"{'='*60}")

            quest = self._enter_settlement(quest_num)
            success = self._run_quest(quest)

            if success:
                report.quests_completed += 1
                self.journal.complete(quest.quest_id)
                self._award_quest_reward(quest, report)
                self._log(
                    f"\n[QUEST COMPLETE] {quest.title}\n"
                    f"  +{quest.reward_gp} gp  |  +{quest.reward_xp} XP each"
                )
            else:
                report.quests_failed += 1
                self.journal.fail(quest.quest_id)
                self._log(f"\n[QUEST FAILED]  {quest.title}")
                # If the whole party was wiped, stop the campaign
                if not self.party:
                    self._log("\nThe party has been defeated. Campaign ends.")
                    break

        report.total_xp = sum(self._xp_totals.values())
        report.total_gp = self._gp_total
        report.survivors = list(self.party)
        report.log = self._collected_log
        return report

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _log(self, msg: str) -> None:
        self._collected_log.append(msg)
        print(msg, file=self._out)

    def _enter_settlement(self, quest_num: int) -> Quest:
        """Generate a settlement, run the NPC dialogue, and return a quest."""
        # Pick a settlement size that scales with the party's average level
        apl = self._avg_party_level()
        size = _level_to_settlement_size(apl)
        settlement = generate_settlement(size, rng=self._rng)

        settlement_name = _settlement_name(self._rng)
        self._log(f"\n-- Arriving at {settlement_name} (pop. {settlement.population}) --")

        # Generate quests from any available world-sim data
        quest = QuestGenerator.generate(
            settlement_name=settlement_name,
            party_level=apl,
            rng=self._rng,
        )
        self.journal.add(quest)

        # Open a brief dialogue with the quest giver
        ctx = DialogueContext(
            npc_name=quest.giver_name,
            npc_role=_random_giver_role(self._rng),
            settlement_name=settlement_name,
            quest_hooks=[quest.description[:80]],
            player_name=self.party[0].name if self.party else "adventurer",
        )
        dialogue = DialogueSession(ctx, rng=self._rng)
        greeting = dialogue.greeting()
        self._log(f"\n{quest.giver_name}: \"{greeting}\"")
        self._log(f"\n[QUEST OFFERED]  {quest.title}")
        self._log(f"  {quest.description}")
        self._log(f"  Reward: {quest.reward_gp} gp + {quest.reward_xp} XP/member")

        return quest

    def _run_quest(self, quest: Quest) -> bool:
        """Run the combat encounter for *quest*. Returns True on victory."""
        apl = self._avg_party_level()
        self._log(f"\n-- Heading to {quest.target_lair_id or 'the lair'}... --")

        report: SessionReport = play_session(
            party=self.party,
            apl=apl,
            terrain=self._terrain,
            difficulty=self._difficulty,
            rng=self._rng,
            stdout=self._out,
        )

        # Accumulate session XP
        for char_id, xp in report.xp_awarded.items():
            self._xp_totals[char_id] = self._xp_totals.get(char_id, 0) + xp

        # Accumulate treasure
        if report.treasure is not None:
            self._gp_total += report.treasure.total_value_gp

        # Remove casualties from the active party
        self.party = [c for c in self.party if c in report.survivors]

        return report.outcome == "victory"

    def _award_quest_reward(self, quest: Quest, report: CampaignReport) -> None:
        """Apply the gold reward and bonus XP from a completed quest."""
        self._gp_total += quest.reward_gp
        for char in self.party:
            self._xp_totals[char.char_id] = (
                self._xp_totals.get(char.char_id, 0) + quest.reward_xp
            )

    def _avg_party_level(self) -> int:
        if not self.party:
            return 1
        return max(1, sum(c.level for c in self.party) // len(self.party))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SETTLEMENT_NAMES: List[str] = [
    "Millhaven", "Thornwick", "Ashford", "Cresthollow", "Dunmere",
    "Ravensgate", "Coldwater", "Ironspire", "Shadowfen", "Goldmist",
    "Westbridge", "Embervale", "Stormkeep", "Dawnharbour", "Greymantle",
]

_GIVER_ROLES: List[str] = [
    "mayor", "guard", "priest", "merchant", "noble", "innkeeper",
]


def _settlement_name(rng: random.Random) -> str:
    return rng.choice(_SETTLEMENT_NAMES)


def _random_giver_role(rng: random.Random) -> str:
    return rng.choice(_GIVER_ROLES)


def _level_to_settlement_size(apl: int) -> CommunitySize:
    """Map average party level to an appropriate settlement size."""
    if apl <= 2:
        return CommunitySize.Hamlet
    if apl <= 4:
        return CommunitySize.Village
    if apl <= 7:
        return CommunitySize.SmallTown
    if apl <= 10:
        return CommunitySize.LargeTown
    return CommunitySize.SmallCity
