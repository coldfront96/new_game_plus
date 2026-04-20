"""
src/rules_engine/spellcasting.py
---------------------------------
Vancian spellcasting engine for D&D 3.5e Wizards.

Implements the "prepare-then-cast" model:
    1. A :class:`Spellbook` holds all spells the Wizard has learned.
    2. A :class:`SpellSlotManager` tracks daily spell slots (0–9) including
       bonus slots from Intelligence.
    3. A :class:`SpellResolver` computes Spell Save DCs.

Memory Optimisation
~~~~~~~~~~~~~~~~~~~
Uses ``@dataclass(slots=True)`` for all structures to eliminate
per-instance ``__dict__`` overhead.

Usage::

    from src.rules_engine.magic import DEFAULT_SPELL_REGISTRY
    from src.rules_engine.spellcasting import (
        Spellbook, SpellSlotManager, SpellResolver,
    )

    book = Spellbook()
    book.learn_spell(DEFAULT_SPELL_REGISTRY.get("Magic Missile"))

    slots = SpellSlotManager(caster_level=1, intelligence=16)
    slots.prepare_spell(DEFAULT_SPELL_REGISTRY.get("Magic Missile"), level=1)
    slots.expend_slot(1)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.rules_engine.magic import Spell


# ---------------------------------------------------------------------------
# 3.5e Wizard Spell Slots Per Day (SRD Table 3-17)
# Key: caster_level, Value: list of slots per spell level [0, 1, 2, ..., 9]
# A value of None means the wizard cannot cast spells of that level yet.
# ---------------------------------------------------------------------------

_WIZARD_SLOTS_PER_DAY: Dict[int, List[Optional[int]]] = {
    1:  [3, 1, None, None, None, None, None, None, None, None],
    2:  [4, 2, None, None, None, None, None, None, None, None],
    3:  [4, 2, 1,    None, None, None, None, None, None, None],
    4:  [4, 3, 2,    None, None, None, None, None, None, None],
    5:  [4, 3, 2,    1,    None, None, None, None, None, None],
    6:  [4, 3, 3,    2,    None, None, None, None, None, None],
    7:  [4, 4, 3,    2,    1,    None, None, None, None, None],
    8:  [4, 4, 3,    3,    2,    None, None, None, None, None],
    9:  [4, 4, 4,    3,    2,    1,    None, None, None, None],
    10: [4, 4, 4,    3,    3,    2,    None, None, None, None],
    11: [4, 4, 4,    4,    3,    2,    1,    None, None, None],
    12: [4, 4, 4,    4,    3,    3,    2,    None, None, None],
    13: [4, 4, 4,    4,    4,    3,    2,    1,    None, None],
    14: [4, 4, 4,    4,    4,    3,    3,    2,    None, None],
    15: [4, 4, 4,    4,    4,    4,    3,    2,    1,    None],
    16: [4, 4, 4,    4,    4,    4,    3,    3,    2,    None],
    17: [4, 4, 4,    4,    4,    4,    4,    3,    2,    1],
    18: [4, 4, 4,    4,    4,    4,    4,    3,    3,    2],
    19: [4, 4, 4,    4,    4,    4,    4,    4,    3,    3],
    20: [4, 4, 4,    4,    4,    4,    4,    4,    4,    4],
}


def _ability_modifier(score: int) -> int:
    """Compute the 3.5e ability modifier: ``(score - 10) // 2``."""
    return (score - 10) // 2


def _bonus_spells_for_level(intelligence: int, spell_level: int) -> int:
    """Calculate bonus spell slots for a given spell level from Intelligence.

    Per the 3.5e SRD:
    - Bonus spells are granted for spell levels 1–9 only (not cantrips).
    - A caster must have an Intelligence score of at least 10 + spell_level
      to cast spells of that level at all.
    - Bonus slots = (int_modifier - spell_level + 1) // 4 + 1 when
      int_modifier >= spell_level.

    Simplified SRD table formula:
    - Bonus spells for level N = (ability_modifier - N) // 4 + 1
      (only if ability_modifier >= N, and N >= 1)

    Args:
        intelligence: The caster's Intelligence score.
        spell_level:  The spell level to compute bonus slots for (1–9).

    Returns:
        Number of bonus spell slots (0 if not eligible).
    """
    if spell_level < 1:
        return 0  # No bonus cantrips

    int_mod = _ability_modifier(intelligence)

    # Must have sufficient Intelligence to cast spells of this level
    if intelligence < 10 + spell_level:
        return 0

    # Must have modifier >= spell_level for any bonus
    if int_mod < spell_level:
        return 0

    return (int_mod - spell_level) // 4 + 1


# ---------------------------------------------------------------------------
# Spellbook
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Spellbook:
    """A Wizard's spellbook containing all known (learned) spells.

    In 3.5e, a Wizard starts with all 0-level spells and a number of
    1st-level spells equal to 3 + Intelligence modifier. Additional spells
    are gained by leveling up or copying from scrolls/other spellbooks.

    Attributes:
        known_spells: Dictionary mapping spell level to list of known spells.
    """

    known_spells: Dict[int, List[Spell]] = field(default_factory=lambda: {i: [] for i in range(10)})

    def learn_spell(self, spell: Spell) -> bool:
        """Add a spell to the spellbook.

        Args:
            spell: The Spell to learn.

        Returns:
            True if the spell was added, False if already known.
        """
        if spell in self.known_spells[spell.level]:
            return False
        self.known_spells[spell.level].append(spell)
        return True

    def knows_spell(self, spell: Spell) -> bool:
        """Check if a spell is in the spellbook."""
        return spell in self.known_spells[spell.level]

    def get_spells_by_level(self, level: int) -> List[Spell]:
        """Get all known spells of a given level."""
        return list(self.known_spells.get(level, []))

    def all_known(self) -> List[Spell]:
        """Return a flat list of all known spells."""
        result: List[Spell] = []
        for level_spells in self.known_spells.values():
            result.extend(level_spells)
        return result

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a dictionary."""
        return {
            "known_spells": {
                str(level): [s.name for s in spells]
                for level, spells in self.known_spells.items()
                if spells
            }
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], spell_registry: Any) -> "Spellbook":
        """Reconstruct from a dictionary produced by :meth:`to_dict`.

        Args:
            data:            Dictionary with known_spells mapping.
            spell_registry:  A SpellRegistry to look up spell objects by name.

        Returns:
            A new Spellbook instance.
        """
        book = cls()
        known = data.get("known_spells", {})
        for level_str, spell_names in known.items():
            for name in spell_names:
                spell = spell_registry.get(name)
                if spell is not None:
                    book.learn_spell(spell)
        return book


# ---------------------------------------------------------------------------
# SpellSlotManager
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class SpellSlotManager:
    """Manages daily spell slots for a 3.5e Wizard.

    Calculates total available slots (base + bonus from Intelligence)
    and tracks preparation/expenditure of slots throughout the adventuring
    day.

    Attributes:
        caster_level:    The Wizard's caster level (1–20).
        intelligence:    The Wizard's Intelligence score.
        total_slots:     Total available slots per level (base + bonus).
        remaining_slots: Slots still available to cast today.
        prepared_spells: Spells prepared in each slot level.
    """

    caster_level: int
    intelligence: int
    total_slots: Dict[int, int] = field(default_factory=dict)
    remaining_slots: Dict[int, int] = field(default_factory=dict)
    prepared_spells: Dict[int, List[Spell]] = field(default_factory=lambda: {i: [] for i in range(10)})

    def __post_init__(self) -> None:
        """Calculate total slots from caster level and Intelligence."""
        if not self.total_slots:
            self._calculate_slots()

    def _calculate_slots(self) -> None:
        """Compute total spell slots = base + bonus from Intelligence."""
        capped_level = min(max(self.caster_level, 1), 20)
        base_slots = _WIZARD_SLOTS_PER_DAY[capped_level]

        self.total_slots = {}
        self.remaining_slots = {}

        for spell_level in range(10):
            base = base_slots[spell_level]
            if base is None:
                # Wizard cannot cast this level yet
                continue
            bonus = _bonus_spells_for_level(self.intelligence, spell_level)
            total = base + bonus
            self.total_slots[spell_level] = total
            self.remaining_slots[spell_level] = total

    def get_total_slots(self, level: int) -> int:
        """Get the total number of slots for a spell level.

        Returns 0 if the wizard cannot cast spells of that level.
        """
        return self.total_slots.get(level, 0)

    def get_remaining_slots(self, level: int) -> int:
        """Get remaining available slots for a spell level."""
        return self.remaining_slots.get(level, 0)

    def prepare_spell(self, spell: Spell, level: int) -> bool:
        """Prepare a spell in a slot of the given level.

        In 3.5e, a Wizard can prepare a lower-level spell in a higher
        slot but cannot exceed the slot total for that level.

        Args:
            spell: The Spell to prepare.
            level: The slot level to prepare it in.

        Returns:
            True if preparation succeeded, False if no slots available.
        """
        if level not in self.total_slots:
            return False

        current_prepared = len(self.prepared_spells.get(level, []))
        if current_prepared >= self.total_slots[level]:
            return False

        if level not in self.prepared_spells:
            self.prepared_spells[level] = []
        self.prepared_spells[level].append(spell)
        return True

    def expend_slot(self, level: int) -> bool:
        """Expend one spell slot of the given level.

        Args:
            level: The spell level slot to expend.

        Returns:
            True if a slot was expended, False if none remaining.
        """
        if self.remaining_slots.get(level, 0) <= 0:
            return False
        self.remaining_slots[level] -= 1
        return True

    def rest(self) -> None:
        """Reset all slots to full (simulates 8-hour rest and re-preparation)."""
        for level in self.total_slots:
            self.remaining_slots[level] = self.total_slots[level]
        self.prepared_spells = {i: [] for i in range(10)}

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a dictionary."""
        return {
            "caster_level": self.caster_level,
            "intelligence": self.intelligence,
            "total_slots": {str(k): v for k, v in self.total_slots.items()},
            "remaining_slots": {str(k): v for k, v in self.remaining_slots.items()},
            "prepared_spells": {
                str(level): [s.name for s in spells]
                for level, spells in self.prepared_spells.items()
                if spells
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SpellSlotManager":
        """Reconstruct from a dictionary produced by :meth:`to_dict`.

        Note: prepared_spells will be empty after deserialization;
        they must be re-prepared after rest.
        """
        mgr = cls(
            caster_level=data["caster_level"],
            intelligence=data["intelligence"],
        )
        # Restore remaining slots from saved state
        remaining = data.get("remaining_slots", {})
        for level_str, count in remaining.items():
            level = int(level_str)
            if level in mgr.remaining_slots:
                mgr.remaining_slots[level] = count
        return mgr


# ---------------------------------------------------------------------------
# SpellResolver
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class SpellResolver:
    """Resolves spell mechanics: DCs, caster level checks, etc.

    Per the 3.5e SRD:
    - Spell Save DC = 10 + Spell Level + Intelligence Modifier

    Attributes:
        intelligence: The caster's Intelligence score.
        caster_level: The caster's level (for caster level checks).
    """

    intelligence: int
    caster_level: int = 1

    @property
    def intelligence_mod(self) -> int:
        """Intelligence modifier."""
        return _ability_modifier(self.intelligence)

    def spell_save_dc(self, spell_level: int) -> int:
        """Calculate the Spell Save DC for a given spell level.

        Formula (3.5e SRD): DC = 10 + Spell Level + Int Modifier

        Args:
            spell_level: The level of the spell being cast (0–9).

        Returns:
            The save DC.
        """
        return 10 + spell_level + self.intelligence_mod

    def caster_level_check(self, dc: int, roll: int) -> bool:
        """Perform a caster level check.

        Formula: d20 + caster_level >= DC

        Args:
            dc:   The difficulty class to beat.
            roll: The d20 roll result.

        Returns:
            True if the check succeeds.
        """
        return roll + self.caster_level >= dc
