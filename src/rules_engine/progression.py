"""
src/rules_engine/progression.py
-------------------------------
D&D 3.5e Experience Point (XP) and Levelling Engine.

Implements XP tracking, level-up detection, and character advancement
using the standard 3.5e XP table: ``Level × (Level - 1) × 500``.

The :class:`XPManager` tracks an entity's current XP and determines
when a level-up is available.  The :func:`level_up` function advances
a :class:`~src.rules_engine.character_35e.Character35e` by one level,
applying hit point and skill point gains per SRD rules.

Usage::

    from src.rules_engine.progression import XPManager, level_up

    xp_mgr = XPManager()
    xp_mgr.award_xp(1000)
    result = xp_mgr.check_level_up()
    if result.leveled_up:
        level_up(character)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from src.rules_engine.character_35e import Character35e, _HIT_DIE


# ---------------------------------------------------------------------------
# SRD Skill Points per level by class
# ---------------------------------------------------------------------------

_SKILL_POINTS_PER_LEVEL: Dict[str, int] = {
    "Barbarian": 4,
    "Bard": 6,
    "Cleric": 2,
    "Druid": 4,
    "Fighter": 2,
    "Monk": 4,
    "Paladin": 2,
    "Ranger": 6,
    "Rogue": 8,
    "Sorcerer": 2,
    "Wizard": 2,
}


# ---------------------------------------------------------------------------
# XP Table (3.5e SRD)
# ---------------------------------------------------------------------------

def xp_for_level(level: int) -> int:
    """Return the total XP required to reach the given level.

    Uses the standard 3.5e formula: ``level × (level - 1) × 500``.

    Args:
        level: The target level (must be ≥ 1).

    Returns:
        Total XP required.  Level 1 requires 0 XP.
    """
    if level < 1:
        return 0
    return level * (level - 1) * 500


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class LevelingResult:
    """Outcome of a level-up check.

    Attributes:
        leveled_up:     ``True`` if the entity has enough XP to level up.
        current_level:  The entity's current level.
        current_xp:     The entity's current XP total.
        xp_needed:      XP required for the next level.
    """

    leveled_up: bool
    current_level: int
    current_xp: int
    xp_needed: int


@dataclass(slots=True)
class Progression:
    """Record of a level-up advancement.

    Attributes:
        new_level:        The new level after advancement.
        hp_gained:        Hit points gained from this level.
        skill_points:     Skill points awarded for this level.
    """

    new_level: int
    hp_gained: int
    skill_points: int


# ---------------------------------------------------------------------------
# XPManager
# ---------------------------------------------------------------------------

class XPManager:
    """Tracks experience points and determines level-up eligibility.

    Attributes:
        current_xp:    Total XP accumulated.
        current_level: The entity's current character level.
    """

    def __init__(self, current_xp: int = 0, current_level: int = 1) -> None:
        self.current_xp = current_xp
        self.current_level = current_level

    def award_xp(self, amount: int) -> None:
        """Add XP to the manager's total.

        Args:
            amount: Non-negative XP to award.
        """
        if amount > 0:
            self.current_xp += amount

    def check_level_up(self) -> LevelingResult:
        """Check whether current XP meets or exceeds the next level threshold.

        Returns:
            A :class:`LevelingResult` describing the current state.
        """
        next_level = self.current_level + 1
        xp_needed = xp_for_level(next_level)
        leveled_up = self.current_xp >= xp_needed
        return LevelingResult(
            leveled_up=leveled_up,
            current_level=self.current_level,
            current_xp=self.current_xp,
            xp_needed=xp_needed,
        )


# ---------------------------------------------------------------------------
# Level-up function
# ---------------------------------------------------------------------------

def level_up(character: Character35e, xp_manager: XPManager) -> Progression:
    """Advance a character by one level, applying SRD advancement rules.

    * Increases the character's level by 1.
    * Calculates HP gained: average hit die roll ``(HD/2 + 1)`` + CON modifier
      (minimum 1 HP).
    * Awards skill points: class base + INT modifier (minimum 1).
    * Syncs the :class:`XPManager` level.

    Args:
        character:  The :class:`Character35e` to advance.
        xp_manager: The :class:`XPManager` tracking the entity's XP.

    Returns:
        A :class:`Progression` record of the advancement.
    """
    # Advance the level
    character.level += 1
    xp_manager.current_level = character.level

    # Calculate HP gained for the new level
    hit_die = _HIT_DIE.get(character.char_class, 8)
    avg_roll = hit_die // 2 + 1
    hp_gained = max(1, avg_roll + character.constitution_mod)

    # Calculate skill points for the new level (SRD: class base + INT mod, min 1)
    base_skill_points = _SKILL_POINTS_PER_LEVEL.get(character.char_class, 2)
    skill_points = max(1, base_skill_points + character.intelligence_mod)

    return Progression(
        new_level=character.level,
        hp_gained=hp_gained,
        skill_points=skill_points,
    )
