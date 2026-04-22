"""
src/rules_engine/skills.py
---------------------------
D&D 3.5e Skill System for the New Game Plus engine.

Implements skill ranks, ability modifiers, and the standard skill check
mechanic: ``d20 + skill_rank + ability_modifier vs. DC``.

Also implements 3.5e Skill Synergies: when a character has 5 or more ranks
in certain skills, related skills gain a +2 competence bonus.

Standard 3.5e skills tracked include Search, Survival, Craft, Listen,
Spot, Heal, Hide, Move Silently, and others from the SRD.

Usage::

    from src.rules_engine.skills import SkillSystem, SkillCheckResult

    skills = SkillSystem()
    skills.set_rank("Survival", 5)
    result = skills.check("Survival", wisdom_mod=2, dc=15)
    print(result.success)  # True if d20 + 5 + 2 >= 15
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from src.rules_engine.dice import RollResult, roll_d20


# ---------------------------------------------------------------------------
# Skill definitions (3.5e SRD standard skills with key abilities)
# ---------------------------------------------------------------------------

class SkillAbility(Enum):
    """The ability score associated with each skill (3.5e SRD)."""

    STR = "strength"
    DEX = "dexterity"
    CON = "constitution"
    INT = "intelligence"
    WIS = "wisdom"
    CHA = "charisma"


# ---------------------------------------------------------------------------
# Skill Synergy table (3.5e SRD p. 65)
# Key: skill with 5+ ranks → Value: list of skills that receive +2 bonus
# ---------------------------------------------------------------------------

SKILL_SYNERGIES: Dict[str, List[str]] = {
    "Bluff":          ["Diplomacy", "Intimidate", "Sleight of Hand", "Disguise"],
    "Decipher Script": ["Use Magic Device"],
    "Escape Artist":  ["Use Rope"],
    "Handle Animal":  ["Ride"],
    "Jump":           ["Tumble"],
    "Knowledge":      ["Bardic Knowledge"],  # Knowledge (any) synergy with Bardic Knowledge
    "Spellcraft":     ["Use Magic Device"],
    "Survival":       ["Knowledge", "Survival"],  # Survival → Knowledge (Nature) tracked via Knowledge
    "Tumble":         ["Balance", "Jump"],
    "Use Magic Device": ["Spellcraft"],
    "Use Rope":       ["Climb", "Escape Artist"],
}

# Survival specifically grants +2 to Knowledge checks related to nature; we
# use the skill name "Knowledge" as a proxy here. The engine consumer is
# responsible for narrowing to the appropriate Knowledge sub-type if needed.


SKILL_DEFINITIONS: Dict[str, SkillAbility] = {
    "Appraise": SkillAbility.INT,
    "Balance": SkillAbility.DEX,
    "Bluff": SkillAbility.CHA,
    "Climb": SkillAbility.STR,
    "Concentration": SkillAbility.CON,
    "Craft": SkillAbility.INT,
    "Decipher Script": SkillAbility.INT,
    "Diplomacy": SkillAbility.CHA,
    "Disable Device": SkillAbility.INT,
    "Disguise": SkillAbility.CHA,
    "Escape Artist": SkillAbility.DEX,
    "Forgery": SkillAbility.INT,
    "Gather Information": SkillAbility.CHA,
    "Handle Animal": SkillAbility.CHA,
    "Heal": SkillAbility.WIS,
    "Hide": SkillAbility.DEX,
    "Intimidate": SkillAbility.CHA,
    "Jump": SkillAbility.STR,
    "Knowledge": SkillAbility.INT,
    "Listen": SkillAbility.WIS,
    "Move Silently": SkillAbility.DEX,
    "Open Lock": SkillAbility.DEX,
    "Perform": SkillAbility.CHA,
    "Profession": SkillAbility.WIS,
    "Ride": SkillAbility.DEX,
    "Search": SkillAbility.INT,
    "Sense Motive": SkillAbility.WIS,
    "Sleight of Hand": SkillAbility.DEX,
    "Spellcraft": SkillAbility.INT,
    "Spot": SkillAbility.WIS,
    "Survival": SkillAbility.WIS,
    "Swim": SkillAbility.STR,
    "Tumble": SkillAbility.DEX,
    "Use Magic Device": SkillAbility.CHA,
    "Use Rope": SkillAbility.DEX,
}


# ---------------------------------------------------------------------------
# SkillCheckResult
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class SkillCheckResult:
    """Outcome of a single skill check.

    Attributes:
        skill_name:     The skill being checked.
        roll:           The d20 :class:`RollResult` (raw die + total modifier).
        total:          Final check value (d20 + rank + ability_mod + misc).
        dc:             The Difficulty Class the check was made against.
        success:        ``True`` if total >= dc.
        margin:         How much the check beat (positive) or missed (negative) the DC.
    """

    skill_name: str
    roll: RollResult
    total: int
    dc: int
    success: bool
    margin: int


# ---------------------------------------------------------------------------
# SkillSystem
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class SkillSystem:
    """Tracks skill ranks and resolves 3.5e skill checks.

    Each entity/character can have one SkillSystem that records their
    invested ranks per skill.  Skill checks follow the standard formula:

        ``d20 + skill_rank + ability_modifier + misc_modifier >= DC``

    Attributes:
        ranks: Mapping of skill name → invested ranks.
        max_rank_cap: Maximum ranks allowed per skill (level + 3 for class
                      skills in 3.5e). Defaults to 23 (level 20 cap).
    """

    ranks: Dict[str, int] = field(default_factory=dict)
    max_rank_cap: int = 23

    def set_rank(self, skill_name: str, rank: int) -> None:
        """Set the rank for a skill.

        Args:
            skill_name: Name of the skill (should match a SKILL_DEFINITIONS key).
            rank: Number of ranks invested (0 to max_rank_cap).

        Raises:
            ValueError: If rank is negative or exceeds max_rank_cap.
        """
        if rank < 0:
            raise ValueError(f"Skill rank cannot be negative, got {rank}")
        if rank > self.max_rank_cap:
            raise ValueError(
                f"Skill rank {rank} exceeds maximum cap {self.max_rank_cap}"
            )
        self.ranks[skill_name] = rank

    def get_rank(self, skill_name: str) -> int:
        """Return the current rank for a skill (0 if untrained).

        Args:
            skill_name: Name of the skill.

        Returns:
            Integer rank value.
        """
        return self.ranks.get(skill_name, 0)

    def add_ranks(self, skill_name: str, points: int) -> int:
        """Add skill points to a skill, respecting the rank cap.

        Args:
            skill_name: Name of the skill.
            points: Number of ranks to add (must be positive).

        Returns:
            The new total rank.

        Raises:
            ValueError: If points is negative or would exceed the cap.
        """
        if points < 0:
            raise ValueError(f"Points to add must be non-negative, got {points}")
        current = self.get_rank(skill_name)
        new_rank = current + points
        if new_rank > self.max_rank_cap:
            raise ValueError(
                f"Adding {points} to {skill_name} (current {current}) "
                f"would exceed cap {self.max_rank_cap}"
            )
        self.ranks[skill_name] = new_rank
        return new_rank

    def get_synergy_bonus(self, skill_name: str) -> int:
        """Return the total synergy bonus for *skill_name* from the 3.5e SRD
        synergy table.

        For each source skill that grants a bonus to *skill_name*, if this
        SkillSystem has 5 or more ranks in that source skill, a +2 competence
        bonus is added (bonuses from multiple sources stack).

        Args:
            skill_name: The target skill being checked for synergy bonuses.

        Returns:
            Total synergy bonus as a non-negative integer.
        """
        bonus = 0
        for source_skill, benefiting_skills in SKILL_SYNERGIES.items():
            if skill_name in benefiting_skills and self.get_rank(source_skill) >= 5:
                bonus += 2
        return bonus

    def check(
        self,
        skill_name: str,
        ability_modifier: int = 0,
        dc: int = 10,
        misc_modifier: int = 0,
        armor_check_penalty: int = 0,
        include_synergy: bool = True,
    ) -> SkillCheckResult:
        """Resolve a skill check against a Difficulty Class.

        Formula: ``d20 + rank + ability_modifier + misc_modifier + synergy_bonus
        - armor_check_penalty`` vs DC.

        The *armor_check_penalty* is subtracted only for skills whose key
        ability is Strength or Dexterity (per the 3.5e SRD).  For all other
        skills the penalty is ignored.

        Synergy bonuses (3.5e SRD p. 65) are automatically applied when
        *include_synergy* is ``True`` (the default): if the character has 5 or
        more ranks in qualifying source skills, a +2 competence bonus is added
        to this check.

        Args:
            skill_name:          Name of the skill being checked.
            ability_modifier:    The relevant ability modifier (e.g. WIS mod
                                 for Survival).
            dc:                  Difficulty Class to beat (default 10).
            misc_modifier:       Any additional circumstance or synergy bonuses.
            armor_check_penalty: The total Armor Check Penalty from equipped
                                 gear (non-negative integer; applied as a
                                 penalty to STR- and DEX-based skills only).
            include_synergy:     Whether to automatically apply synergy bonuses
                                 from the SKILL_SYNERGIES table (default True).

        Returns:
            A :class:`SkillCheckResult` with the full outcome.
        """
        rank = self.get_rank(skill_name)

        # Apply ACP only to STR- and DEX-based skills (3.5e SRD rule)
        key_ability = self.get_key_ability(skill_name)
        acp_penalty = 0
        if armor_check_penalty > 0 and key_ability in (
            SkillAbility.STR, SkillAbility.DEX
        ):
            acp_penalty = armor_check_penalty

        synergy_bonus = self.get_synergy_bonus(skill_name) if include_synergy else 0

        total_modifier = rank + ability_modifier + misc_modifier + synergy_bonus - acp_penalty
        roll = roll_d20(modifier=total_modifier)
        total = roll.total
        success = total >= dc
        margin = total - dc

        return SkillCheckResult(
            skill_name=skill_name,
            roll=roll,
            total=total,
            dc=dc,
            success=success,
            margin=margin,
        )

    def get_key_ability(self, skill_name: str) -> Optional[SkillAbility]:
        """Return the key ability for a known 3.5e skill.

        Args:
            skill_name: Name of the skill.

        Returns:
            The :class:`SkillAbility` enum, or ``None`` if the skill is
            not in the standard SRD list.
        """
        return SKILL_DEFINITIONS.get(skill_name)

    @property
    def trained_skills(self) -> Dict[str, int]:
        """Return a dictionary of all skills with ranks > 0."""
        return {k: v for k, v in self.ranks.items() if v > 0}
