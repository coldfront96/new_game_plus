"""
src/rules_engine/spellcasting.py
---------------------------------
D&D 3.5e Vancian spellcasting engine: spell slots, preparation, and
casting mechanics.

Implements the core 3.5e SRD "fire-and-forget" spellcasting model:

- :class:`SpellSlotManager` — tracks available/expended slots per level.
- :class:`Spellbook` — tracks known/prepared spells.
- :class:`SpellResolver` — computes Spell Save DC and Caster Level.

Memory Optimisation
~~~~~~~~~~~~~~~~~~~
Uses ``@dataclass(slots=True)`` per project standard.

Usage::

    from src.rules_engine.spellcasting import (
        SpellSlotManager, Spellbook, SpellResolver,
    )
    from src.rules_engine.magic import create_default_registry

    registry = create_default_registry()
    slots = SpellSlotManager.for_wizard(level=1, int_mod=3)
    spellbook = Spellbook()
    spellbook.add_known("Magic Missile", spell_level=1)

    resolver = SpellResolver(
        caster_level=1, key_ability_mod=3, spell_registry=registry,
    )
    dc = resolver.spell_save_dc(spell_level=1)  # 10 + 1 + 3 = 14
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from src.rules_engine.magic import Spell, SpellRegistry


# ---------------------------------------------------------------------------
# SRD Spell Slot Tables (3.5e)
# ---------------------------------------------------------------------------

# Wizard base spells per day by class level (index = spell level 0-9).
# From the 3.5e SRD Wizard table.  -1 means "not available at this class level."
_WIZARD_SLOTS: Dict[int, List[int]] = {
    1:  [3, 1, -1, -1, -1, -1, -1, -1, -1, -1],
    2:  [4, 2, -1, -1, -1, -1, -1, -1, -1, -1],
    3:  [4, 2, 1, -1, -1, -1, -1, -1, -1, -1],
    4:  [4, 3, 2, -1, -1, -1, -1, -1, -1, -1],
    5:  [4, 3, 2, 1, -1, -1, -1, -1, -1, -1],
    6:  [4, 3, 3, 2, -1, -1, -1, -1, -1, -1],
    7:  [4, 4, 3, 2, 1, -1, -1, -1, -1, -1],
    8:  [4, 4, 3, 3, 2, -1, -1, -1, -1, -1],
    9:  [4, 4, 4, 3, 2, 1, -1, -1, -1, -1],
    10: [4, 4, 4, 3, 3, 2, -1, -1, -1, -1],
    11: [4, 4, 4, 4, 3, 2, 1, -1, -1, -1],
    12: [4, 4, 4, 4, 3, 3, 2, -1, -1, -1],
    13: [4, 4, 4, 4, 4, 3, 2, 1, -1, -1],
    14: [4, 4, 4, 4, 4, 3, 3, 2, -1, -1],
    15: [4, 4, 4, 4, 4, 4, 3, 2, 1, -1],
    16: [4, 4, 4, 4, 4, 4, 3, 3, 2, -1],
    17: [4, 4, 4, 4, 4, 4, 4, 3, 2, 1],
    18: [4, 4, 4, 4, 4, 4, 4, 3, 3, 2],
    19: [4, 4, 4, 4, 4, 4, 4, 4, 3, 3],
    20: [4, 4, 4, 4, 4, 4, 4, 4, 4, 4],
}

# Sorcerer base spells per day (known casting, no preparation needed).
_SORCERER_SLOTS: Dict[int, List[int]] = {
    1:  [5, 3, -1, -1, -1, -1, -1, -1, -1, -1],
    2:  [6, 4, -1, -1, -1, -1, -1, -1, -1, -1],
    3:  [6, 5, -1, -1, -1, -1, -1, -1, -1, -1],
    4:  [6, 6, 3, -1, -1, -1, -1, -1, -1, -1],
    5:  [6, 6, 4, -1, -1, -1, -1, -1, -1, -1],
    6:  [6, 6, 5, 3, -1, -1, -1, -1, -1, -1],
    7:  [6, 6, 6, 4, -1, -1, -1, -1, -1, -1],
    8:  [6, 6, 6, 5, 3, -1, -1, -1, -1, -1],
    9:  [6, 6, 6, 6, 4, -1, -1, -1, -1, -1],
    10: [6, 6, 6, 6, 5, 3, -1, -1, -1, -1],
    11: [6, 6, 6, 6, 6, 4, -1, -1, -1, -1],
    12: [6, 6, 6, 6, 6, 5, 3, -1, -1, -1],
    13: [6, 6, 6, 6, 6, 6, 4, -1, -1, -1],
    14: [6, 6, 6, 6, 6, 6, 5, 3, -1, -1],
    15: [6, 6, 6, 6, 6, 6, 6, 4, -1, -1],
    16: [6, 6, 6, 6, 6, 6, 6, 5, 3, -1],
    17: [6, 6, 6, 6, 6, 6, 6, 6, 4, -1],
    18: [6, 6, 6, 6, 6, 6, 6, 6, 5, 3],
    19: [6, 6, 6, 6, 6, 6, 6, 6, 6, 4],
    20: [6, 6, 6, 6, 6, 6, 6, 6, 6, 6],
}

# Cleric base spells per day.
_CLERIC_SLOTS: Dict[int, List[int]] = {
    1:  [3, 1, -1, -1, -1, -1, -1, -1, -1, -1],
    2:  [4, 2, -1, -1, -1, -1, -1, -1, -1, -1],
    3:  [4, 2, 1, -1, -1, -1, -1, -1, -1, -1],
    4:  [5, 3, 2, -1, -1, -1, -1, -1, -1, -1],
    5:  [5, 3, 2, 1, -1, -1, -1, -1, -1, -1],
    6:  [5, 3, 3, 2, -1, -1, -1, -1, -1, -1],
    7:  [6, 4, 3, 2, 1, -1, -1, -1, -1, -1],
    8:  [6, 4, 3, 3, 2, -1, -1, -1, -1, -1],
    9:  [6, 4, 4, 3, 2, 1, -1, -1, -1, -1],
    10: [6, 4, 4, 3, 3, 2, -1, -1, -1, -1],
    11: [6, 5, 4, 4, 3, 2, 1, -1, -1, -1],
    12: [6, 5, 4, 4, 3, 3, 2, -1, -1, -1],
    13: [6, 5, 5, 4, 4, 3, 2, 1, -1, -1],
    14: [6, 5, 5, 4, 4, 3, 3, 2, -1, -1],
    15: [6, 5, 5, 5, 4, 4, 3, 2, 1, -1],
    16: [6, 5, 5, 5, 4, 4, 3, 3, 2, -1],
    17: [6, 5, 5, 5, 5, 4, 4, 3, 2, 1],
    18: [6, 5, 5, 5, 5, 4, 4, 3, 3, 2],
    19: [6, 5, 5, 5, 5, 5, 4, 4, 3, 3],
    20: [6, 5, 5, 5, 5, 5, 4, 4, 4, 4],
}

# Bard base spells per day (spontaneous, CHA-based).
# From the 3.5e SRD Bard table. Bards cast up to 6th-level spells.
# Index = spell level (0-6), padded to 10 with -1 for levels 7-9.
_BARD_SLOTS: Dict[int, List[int]] = {
    1:  [2, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    2:  [3, 0, -1, -1, -1, -1, -1, -1, -1, -1],
    3:  [3, 1, -1, -1, -1, -1, -1, -1, -1, -1],
    4:  [3, 2, 0, -1, -1, -1, -1, -1, -1, -1],
    5:  [3, 3, 1, -1, -1, -1, -1, -1, -1, -1],
    6:  [3, 3, 2, -1, -1, -1, -1, -1, -1, -1],
    7:  [3, 3, 2, 0, -1, -1, -1, -1, -1, -1],
    8:  [3, 3, 3, 1, -1, -1, -1, -1, -1, -1],
    9:  [3, 3, 3, 2, -1, -1, -1, -1, -1, -1],
    10: [3, 3, 3, 2, 0, -1, -1, -1, -1, -1],
    11: [3, 3, 3, 3, 1, -1, -1, -1, -1, -1],
    12: [3, 3, 3, 3, 2, -1, -1, -1, -1, -1],
    13: [3, 3, 3, 3, 2, 0, -1, -1, -1, -1],
    14: [4, 3, 3, 3, 3, 1, -1, -1, -1, -1],
    15: [4, 4, 3, 3, 3, 2, -1, -1, -1, -1],
    16: [4, 4, 4, 3, 3, 2, 0, -1, -1, -1],
    17: [4, 4, 4, 4, 3, 3, 1, -1, -1, -1],
    18: [4, 4, 4, 4, 4, 3, 2, -1, -1, -1],
    19: [4, 4, 4, 4, 4, 4, 3, -1, -1, -1],
    20: [4, 4, 4, 4, 4, 4, 4, -1, -1, -1],
}

# Paladin base spells per day (half-caster, WIS-based, levels 1–20, spells 1–4).
# Paladins gain spells at level 4 and cast up to 4th-level spells (3.5e SRD).
# Index = spell level (0-9); index 0 always 0 (Paladins have no 0-level spells).
_PALADIN_SLOTS: Dict[int, List[int]] = {
    1:  [0, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    2:  [0, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    3:  [0, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    4:  [0,  0, -1, -1, -1, -1, -1, -1, -1, -1],
    5:  [0,  0, -1, -1, -1, -1, -1, -1, -1, -1],
    6:  [0,  1, -1, -1, -1, -1, -1, -1, -1, -1],
    7:  [0,  1, -1, -1, -1, -1, -1, -1, -1, -1],
    8:  [0,  1,  0, -1, -1, -1, -1, -1, -1, -1],
    9:  [0,  1,  0, -1, -1, -1, -1, -1, -1, -1],
    10: [0,  1,  1, -1, -1, -1, -1, -1, -1, -1],
    11: [0,  1,  1,  0, -1, -1, -1, -1, -1, -1],
    12: [0,  1,  1,  1, -1, -1, -1, -1, -1, -1],
    13: [0,  1,  1,  1, -1, -1, -1, -1, -1, -1],
    14: [0,  2,  1,  1,  0, -1, -1, -1, -1, -1],
    15: [0,  2,  1,  1,  1, -1, -1, -1, -1, -1],
    16: [0,  2,  2,  1,  1, -1, -1, -1, -1, -1],
    17: [0,  2,  2,  2,  1, -1, -1, -1, -1, -1],
    18: [0,  3,  2,  2,  1, -1, -1, -1, -1, -1],
    19: [0,  3,  3,  3,  2, -1, -1, -1, -1, -1],
    20: [0,  3,  3,  3,  3, -1, -1, -1, -1, -1],
}

# Ranger base spells per day (half-caster, WIS-based, levels 1–20, spells 1–4).
# Rangers gain spells at level 4 and cast up to 4th-level spells (3.5e SRD).
# Index = spell level (0-9); index 0 always 0 (Rangers have no 0-level spells).
_RANGER_SLOTS: Dict[int, List[int]] = {
    1:  [0, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    2:  [0, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    3:  [0, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    4:  [0,  0, -1, -1, -1, -1, -1, -1, -1, -1],
    5:  [0,  0, -1, -1, -1, -1, -1, -1, -1, -1],
    6:  [0,  1, -1, -1, -1, -1, -1, -1, -1, -1],
    7:  [0,  1, -1, -1, -1, -1, -1, -1, -1, -1],
    8:  [0,  1,  0, -1, -1, -1, -1, -1, -1, -1],
    9:  [0,  1,  0, -1, -1, -1, -1, -1, -1, -1],
    10: [0,  1,  1, -1, -1, -1, -1, -1, -1, -1],
    11: [0,  1,  1,  0, -1, -1, -1, -1, -1, -1],
    12: [0,  1,  1,  1, -1, -1, -1, -1, -1, -1],
    13: [0,  1,  1,  1, -1, -1, -1, -1, -1, -1],
    14: [0,  2,  1,  1,  0, -1, -1, -1, -1, -1],
    15: [0,  2,  1,  1,  1, -1, -1, -1, -1, -1],
    16: [0,  2,  2,  1,  1, -1, -1, -1, -1, -1],
    17: [0,  2,  2,  2,  1, -1, -1, -1, -1, -1],
    18: [0,  3,  2,  2,  1, -1, -1, -1, -1, -1],
    19: [0,  3,  3,  3,  2, -1, -1, -1, -1, -1],
    20: [0,  3,  3,  3,  3, -1, -1, -1, -1, -1],
}

# Mapping of caster class to their slot table and key ability.
_CASTER_TABLES: Dict[str, Dict[str, Any]] = {
    "Wizard": {"table": _WIZARD_SLOTS, "key_ability": "intelligence"},
    "Sorcerer": {"table": _SORCERER_SLOTS, "key_ability": "charisma"},
    "Cleric": {"table": _CLERIC_SLOTS, "key_ability": "wisdom"},
    "Druid": {"table": _CLERIC_SLOTS, "key_ability": "wisdom"},
    "Bard": {"table": _BARD_SLOTS, "key_ability": "charisma"},
    "Paladin": {"table": _PALADIN_SLOTS, "key_ability": "wisdom"},
    "Ranger": {"table": _RANGER_SLOTS, "key_ability": "wisdom"},
}


def _bonus_spells_for_level(ability_mod: int, spell_level: int) -> int:
    """Calculate bonus spells per day from a high ability score (3.5e SRD).

    Bonus spells for level N = (ability_mod - N + 1) // 4 + 1 if eligible.
    A caster gets bonus spells only for levels they can already cast.
    No bonus spells for 0-level (cantrips).

    Args:
        ability_mod: The key ability modifier.
        spell_level: The spell level (1–9).

    Returns:
        Number of bonus spell slots for that level (minimum 0).
    """
    if spell_level == 0:
        return 0
    if ability_mod < spell_level:
        return 0
    # SRD formula: bonus spell for level N if ability score >= 10 + 2*N
    # Simplified: bonus = 1 + (mod - spell_level) // 4
    return 1 + (ability_mod - spell_level) // 4


# ---------------------------------------------------------------------------
# SpellSlotManager
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class SpellSlotManager:
    """Manages available and expended spell slots per spell level (0–9).

    Follows the 3.5e Vancian model: slots represent the total number of
    spells that can be cast per day at each level.

    Attributes:
        max_slots:      Maximum slots per level (index 0–9).
        expended_slots: Number of used slots per level.
    """

    max_slots: List[int] = field(default_factory=lambda: [0] * 10)
    expended_slots: List[int] = field(default_factory=lambda: [0] * 10)

    @classmethod
    def for_class(
        cls,
        char_class: str,
        level: int,
        ability_mod: int,
    ) -> "SpellSlotManager":
        """Create a SpellSlotManager for a given caster class, level, and
        key ability modifier.

        Applies bonus spells from high ability scores per 3.5e SRD rules.

        Args:
            char_class: Caster class name (e.g. "Wizard", "Sorcerer").
            level:      Class level (1–20).
            ability_mod: Key ability modifier (INT for Wizard, CHA for Sorcerer).

        Returns:
            A configured :class:`SpellSlotManager`.

        Raises:
            ValueError: If the class is not a recognised caster.
        """
        caster_info = _CASTER_TABLES.get(char_class)
        if caster_info is None:
            raise ValueError(f"'{char_class}' is not a recognised caster class.")

        table = caster_info["table"]
        base_slots = table.get(level, [0] * 10)

        max_slots: List[int] = []
        for spell_level, base in enumerate(base_slots):
            if base < 0:
                max_slots.append(0)
            else:
                bonus = _bonus_spells_for_level(ability_mod, spell_level)
                max_slots.append(base + bonus)

        return cls(max_slots=max_slots, expended_slots=[0] * 10)

    @classmethod
    def for_wizard(cls, level: int, int_mod: int) -> "SpellSlotManager":
        """Convenience factory for Wizard spell slots.

        Args:
            level:   Wizard class level.
            int_mod: Intelligence modifier.

        Returns:
            A :class:`SpellSlotManager` configured for a Wizard.
        """
        return cls.for_class("Wizard", level, int_mod)

    @classmethod
    def for_sorcerer(cls, level: int, cha_mod: int) -> "SpellSlotManager":
        """Convenience factory for Sorcerer spell slots.

        Args:
            level:   Sorcerer class level.
            cha_mod: Charisma modifier.

        Returns:
            A :class:`SpellSlotManager` configured for a Sorcerer.
        """
        return cls.for_class("Sorcerer", level, cha_mod)

    @classmethod
    def for_bard(cls, level: int, cha_mod: int) -> "SpellSlotManager":
        """Convenience factory for Bard spell slots.

        Bards are spontaneous arcane casters using Charisma.

        Args:
            level:   Bard class level (1–20).
            cha_mod: Charisma modifier.

        Returns:
            A :class:`SpellSlotManager` configured for a Bard.
        """
        return cls.for_class("Bard", level, cha_mod)

    def available(self, spell_level: int) -> int:
        """Return the number of remaining (un-expended) slots at a level.

        Args:
            spell_level: Spell level (0–9).

        Returns:
            Remaining slots.
        """
        return max(0, self.max_slots[spell_level] - self.expended_slots[spell_level])

    def expend(self, spell_level: int) -> bool:
        """Expend one slot at the given spell level.

        Args:
            spell_level: Spell level to expend.

        Returns:
            ``True`` if a slot was successfully expended, ``False`` if none
            remain.
        """
        if self.available(spell_level) <= 0:
            return False
        self.expended_slots[spell_level] += 1
        return True

    def rest(self) -> None:
        """Restore all expended slots (long rest / 8 hours of sleep)."""
        self.expended_slots = [0] * 10

    def total_max(self) -> int:
        """Total maximum slots across all levels."""
        return sum(s for s in self.max_slots if s > 0)

    def total_available(self) -> int:
        """Total available slots across all levels."""
        return sum(self.available(i) for i in range(10))


# ---------------------------------------------------------------------------
# Spellbook
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Spellbook:
    """Tracks known and prepared spells for a caster.

    In the 3.5e system:
    - **Wizards** must prepare spells from their spellbook each day.
    - **Sorcerers** know a fixed list and cast spontaneously.
    - **Clerics** have access to their full spell list but must prepare.

    Attributes:
        known_spells:    Set of spell names the caster knows/has in their book.
        prepared_spells: Mapping of spell_level → list of prepared spell names.
    """

    known_spells: Set[str] = field(default_factory=set)
    prepared_spells: Dict[int, List[str]] = field(
        default_factory=lambda: {i: [] for i in range(10)}
    )

    def add_known(self, spell_name: str, spell_level: int) -> None:
        """Add a spell to the known spells list.

        Args:
            spell_name:  Name of the spell.
            spell_level: Level of the spell (for indexing, unused in known set
                         but kept for interface consistency).
        """
        self.known_spells.add(spell_name)

    def remove_known(self, spell_name: str) -> None:
        """Remove a spell from known spells.

        Args:
            spell_name: Name of the spell to remove.
        """
        self.known_spells.discard(spell_name)

    def is_known(self, spell_name: str) -> bool:
        """Check if a spell is known.

        Args:
            spell_name: Name of the spell.

        Returns:
            ``True`` if known.
        """
        return spell_name in self.known_spells

    def prepare(self, spell_name: str, spell_level: int) -> bool:
        """Prepare a known spell into a slot.

        The spell must be known. This does *not* check against slot limits;
        the :class:`SpellSlotManager` handles that constraint.

        Args:
            spell_name:  Name of the spell to prepare.
            spell_level: Spell level to prepare it at.

        Returns:
            ``True`` if successfully prepared, ``False`` if not known.
        """
        if spell_name not in self.known_spells:
            return False
        self.prepared_spells[spell_level].append(spell_name)
        return True

    def unprepare_all(self) -> None:
        """Clear all prepared spells (new day preparation)."""
        self.prepared_spells = {i: [] for i in range(10)}

    def get_prepared(self, spell_level: int) -> List[str]:
        """Get list of spells prepared at a given level.

        Args:
            spell_level: Spell level (0–9).

        Returns:
            List of prepared spell names.
        """
        return list(self.prepared_spells.get(spell_level, []))


# ---------------------------------------------------------------------------
# SpellResolver
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class SpellResolver:
    """Calculates casting mechanics: Save DC and Caster Level.

    Implements 3.5e SRD formulas:
    - **Spell Save DC** = 10 + Spell Level + Key Ability Modifier
    - **Caster Level** = Character level in the casting class

    Attributes:
        caster_level:    The character's level in their casting class.
        key_ability_mod: Modifier of the key casting ability (INT/CHA/WIS).
        spell_registry:  Optional registry for looking up spell data.
    """

    caster_level: int
    key_ability_mod: int
    spell_registry: Optional[SpellRegistry] = field(default=None, repr=False)

    def spell_save_dc(self, spell_level: int) -> int:
        """Calculate the save DC for a spell of a given level.

        Formula (3.5e SRD): ``10 + spell_level + key_ability_mod``

        Args:
            spell_level: The level of the spell being cast.

        Returns:
            The Difficulty Class for the saving throw.
        """
        return 10 + spell_level + self.key_ability_mod

    def get_caster_level(self) -> int:
        """Return the effective caster level.

        In the base case, caster level equals class level. This method
        exists as an extension point for caster level modifiers (feats,
        items, etc.).

        Returns:
            Effective caster level.
        """
        return self.caster_level

    def resolve_spell(
        self,
        spell_name: str,
        target: Any = None,
        caster: Any = None,
    ) -> Optional[Dict[str, Any]]:
        """Resolve a spell's effect by invoking its effect_callback.

        Args:
            spell_name: Name of the spell to resolve.
            target:     Target of the spell (passed to callback).
            caster:     Caster reference (passed to callback).

        Returns:
            Result dictionary from the spell's effect_callback, or ``None``
            if the spell is not found or has no callback.
        """
        if self.spell_registry is None:
            return None
        spell = self.spell_registry.get(spell_name)
        if spell is None or spell.effect_callback is None:
            return None
        return spell.effect_callback(caster, target, self.caster_level)


# ---------------------------------------------------------------------------
# Helper: determine key ability for a class
# ---------------------------------------------------------------------------

def get_key_ability(char_class: str) -> str:
    """Return the key spellcasting ability for a caster class.

    Args:
        char_class: Class name.

    Returns:
        Ability name string ("intelligence", "charisma", "wisdom").

    Raises:
        ValueError: If the class is not a recognised caster.
    """
    caster_info = _CASTER_TABLES.get(char_class)
    if caster_info is None:
        raise ValueError(f"'{char_class}' is not a recognised caster class.")
    return caster_info["key_ability"]


def is_caster_class(char_class: str) -> bool:
    """Check if a class is a recognised caster class.

    Args:
        char_class: Class name.

    Returns:
        ``True`` if the class has spellcasting capability.
    """
    return char_class in _CASTER_TABLES


# ---------------------------------------------------------------------------
# DivineCasterManager
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class DivineCasterManager:
    """Specialized spell slot manager for divine casters (Cleric/Druid).

    Extends the basic :class:`SpellSlotManager` with 3.5e divine-specific
    mechanics:

    - **Spontaneous Casting (Cure)**: A Good or Neutral-aligned Cleric can
      lose any prepared non-domain spell to cast a Cure spell of the same
      level (3.5e SRD p.32).
    - **Wisdom-based bonus slots**: Bonus spells are computed from WIS.

    Attributes:
        slot_manager: The underlying :class:`SpellSlotManager`.
        spellbook:    The :class:`Spellbook` tracking prepared spells.
        alignment:    Cleric alignment ("good", "neutral", or "evil").
        domain_spells: Set of spell names that are domain spells (cannot
                       be spontaneously converted).
    """

    slot_manager: SpellSlotManager
    spellbook: Spellbook
    alignment: str = "good"
    domain_spells: Set[str] = field(default_factory=set)
    _is_druid: bool = field(default=False, repr=False)

    @classmethod
    def for_cleric(
        cls,
        level: int,
        wis_mod: int,
        alignment: str = "good",
    ) -> "DivineCasterManager":
        """Create a DivineCasterManager for a Cleric.

        Args:
            level:     Cleric class level (1–20).
            wis_mod:   Wisdom modifier.
            alignment: "good", "neutral", or "evil".

        Returns:
            A configured :class:`DivineCasterManager`.
        """
        slot_manager = SpellSlotManager.for_class("Cleric", level, wis_mod)
        spellbook = Spellbook()
        return cls(
            slot_manager=slot_manager,
            spellbook=spellbook,
            alignment=alignment,
        )

    @classmethod
    def for_druid(
        cls,
        level: int,
        wis_mod: int,
    ) -> "DivineCasterManager":
        """Create a DivineCasterManager for a Druid.

        Args:
            level:   Druid class level (1–20).
            wis_mod: Wisdom modifier.

        Returns:
            A configured :class:`DivineCasterManager`.
        """
        slot_manager = SpellSlotManager.for_class("Druid", level, wis_mod)
        spellbook = Spellbook()
        return cls(
            slot_manager=slot_manager,
            spellbook=spellbook,
            alignment="neutral",
            _is_druid=True,
        )

    def can_spontaneous_cure(self) -> bool:
        """Whether this caster can spontaneously convert spells to Cure spells.

        Per 3.5e SRD: Good-aligned and Neutral-aligned Clerics can
        spontaneously cast Cure spells. Evil Clerics instead spontaneously
        cast Inflict spells (not yet implemented).

        Returns:
            ``True`` if spontaneous Cure conversion is available.
        """
        return self.alignment in ("good", "neutral")

    def convert_to_cure(self, prepared_spell: str) -> Optional[str]:
        """Spontaneously convert a prepared non-domain spell into a Cure
        spell of the same level (3.5e SRD Spontaneous Casting).

        The prepared spell is consumed (removed from preparation and the
        corresponding slot is expended). The Cure spell name for that level
        is returned.

        Rules enforced:
        - Caster must be Good or Neutral aligned.
        - The spell must be currently prepared.
        - Domain spells cannot be spontaneously converted.
        - The spell must be level 1–9 (cantrips cannot be converted).
        - A slot of the spell's level must be available.

        Args:
            prepared_spell: Name of the prepared spell to sacrifice.

        Returns:
            The name of the Cure spell gained, or ``None`` if conversion
            is not possible.
        """
        from src.rules_engine.magic import CURE_SPELLS

        # Must be eligible for spontaneous cure casting
        if not self.can_spontaneous_cure():
            return None

        # Domain spells cannot be spontaneously converted
        if prepared_spell in self.domain_spells:
            return None

        # Find the spell level from prepared spells
        spell_level: Optional[int] = None
        for level in range(1, 10):
            if prepared_spell in self.spellbook.prepared_spells.get(level, []):
                spell_level = level
                break

        # Spell must be prepared and at level 1+
        if spell_level is None:
            return None

        # Must have a slot available at that level
        if self.slot_manager.available(spell_level) <= 0:
            return None

        # Look up the cure spell for this level
        cure_spell_name = CURE_SPELLS.get(spell_level)
        if cure_spell_name is None:
            return None

        # Consume: expend the slot and remove the prepared spell
        self.slot_manager.expend(spell_level)
        self.spellbook.prepared_spells[spell_level].remove(prepared_spell)

        return cure_spell_name

    def can_spontaneous_summon(self) -> bool:
        """Whether this caster can spontaneously convert spells to Summon
        Nature's Ally spells.

        Per 3.5e SRD: Druids can spontaneously cast Summon Nature's Ally
        spells of the same level as the sacrificed prepared spell.

        Returns:
            ``True`` if this manager was created via :meth:`for_druid`.
        """
        return self._is_druid

    def convert_to_summon_natures_ally(self, prepared_spell: str) -> Optional[str]:
        """Spontaneously convert a prepared non-domain spell into a Summon
        Nature's Ally spell of the same level (3.5e SRD Spontaneous Casting).

        The prepared spell is consumed (removed from preparation and the
        corresponding slot is expended). The Summon Nature's Ally spell name
        for that level is returned.

        Rules enforced:
        - Caster must be a Druid (``can_spontaneous_summon()`` returns True).
        - The spell must be currently prepared.
        - Domain spells cannot be spontaneously converted.
        - The spell must be level 1–9 (cantrips cannot be converted).
        - A slot of the spell's level must be available.

        Args:
            prepared_spell: Name of the prepared spell to sacrifice.

        Returns:
            The name of the Summon Nature's Ally spell gained, or ``None``
            if conversion is not possible.
        """
        from src.rules_engine.magic import SUMMON_NATURES_ALLY_SPELLS

        if not self.can_spontaneous_summon():
            return None

        if prepared_spell in self.domain_spells:
            return None

        spell_level: Optional[int] = None
        for level in range(1, 10):
            if prepared_spell in self.spellbook.prepared_spells.get(level, []):
                spell_level = level
                break

        if spell_level is None:
            return None

        if self.slot_manager.available(spell_level) <= 0:
            return None

        summon_spell_name = SUMMON_NATURES_ALLY_SPELLS.get(spell_level)
        if summon_spell_name is None:
            return None

        self.slot_manager.expend(spell_level)
        self.spellbook.prepared_spells[spell_level].remove(prepared_spell)

        return summon_spell_name

    def prepare_spell(self, spell_name: str, spell_level: int) -> bool:
        """Prepare a spell into the divine caster's daily preparation.

        Divine casters have access to their entire spell list, so this
        does not check the known_spells set. Instead, it adds to known
        and then prepares.

        Args:
            spell_name:  Name of the spell to prepare.
            spell_level: Spell level (0–9).

        Returns:
            ``True`` if successfully prepared.
        """
        # Divine casters know all spells on their list
        self.spellbook.add_known(spell_name, spell_level)
        return self.spellbook.prepare(spell_name, spell_level)

    def cast_spell(self, spell_name: str, spell_level: int) -> bool:
        """Cast a prepared spell, expending the appropriate slot.

        Args:
            spell_name:  Name of the spell to cast.
            spell_level: Spell level of the slot to expend.

        Returns:
            ``True`` if the spell was successfully cast (was prepared and
            a slot was available), ``False`` otherwise.
        """
        if spell_name not in self.spellbook.prepared_spells.get(spell_level, []):
            return False
        if not self.slot_manager.expend(spell_level):
            return False
        self.spellbook.prepared_spells[spell_level].remove(spell_name)
        return True

    def rest(self) -> None:
        """Restore all spell slots and clear prepared spells (new day)."""
        self.slot_manager.rest()
        self.spellbook.unprepare_all()


# ---------------------------------------------------------------------------
# Sorcerer Spells Known Table (3.5e SRD)
# ---------------------------------------------------------------------------

# Maximum number of spells known per spell level by Sorcerer class level.
# Index = spell level (0-9). -1 means not available at that class level.
_SORCERER_SPELLS_KNOWN: Dict[int, List[int]] = {
    1:  [4, 2, -1, -1, -1, -1, -1, -1, -1, -1],
    2:  [5, 2, -1, -1, -1, -1, -1, -1, -1, -1],
    3:  [5, 3, -1, -1, -1, -1, -1, -1, -1, -1],
    4:  [6, 3, 1, -1, -1, -1, -1, -1, -1, -1],
    5:  [6, 4, 2, -1, -1, -1, -1, -1, -1, -1],
    6:  [7, 4, 2, 1, -1, -1, -1, -1, -1, -1],
    7:  [7, 5, 3, 2, -1, -1, -1, -1, -1, -1],
    8:  [8, 5, 3, 2, 1, -1, -1, -1, -1, -1],
    9:  [8, 5, 4, 3, 2, -1, -1, -1, -1, -1],
    10: [9, 5, 4, 3, 2, 1, -1, -1, -1, -1],
    11: [9, 5, 5, 4, 3, 2, -1, -1, -1, -1],
    12: [9, 5, 5, 4, 3, 2, 1, -1, -1, -1],
    13: [9, 5, 5, 4, 4, 3, 2, -1, -1, -1],
    14: [9, 5, 5, 4, 4, 3, 2, 1, -1, -1],
    15: [9, 5, 5, 4, 4, 4, 3, 2, -1, -1],
    16: [9, 5, 5, 4, 4, 4, 3, 2, 1, -1],
    17: [9, 5, 5, 4, 4, 4, 3, 3, 2, -1],
    18: [9, 5, 5, 4, 4, 4, 3, 3, 2, 1],
    19: [9, 5, 5, 4, 4, 4, 3, 3, 3, 2],
    20: [9, 5, 5, 4, 4, 4, 3, 3, 3, 3],
}


# ---------------------------------------------------------------------------
# Bard Spells Known Table (3.5e SRD)
# ---------------------------------------------------------------------------

# Maximum number of spells known per spell level by Bard class level.
# Bards know up to 6th-level spells. Index = spell level (0-6), padded to 10.
_BARD_SPELLS_KNOWN: Dict[int, List[int]] = {
    1:  [4, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    2:  [5, 2, -1, -1, -1, -1, -1, -1, -1, -1],
    3:  [6, 3, -1, -1, -1, -1, -1, -1, -1, -1],
    4:  [6, 3, 2, -1, -1, -1, -1, -1, -1, -1],
    5:  [6, 4, 3, -1, -1, -1, -1, -1, -1, -1],
    6:  [6, 4, 3, -1, -1, -1, -1, -1, -1, -1],
    7:  [6, 4, 4, 2, -1, -1, -1, -1, -1, -1],
    8:  [6, 4, 4, 3, -1, -1, -1, -1, -1, -1],
    9:  [6, 4, 4, 3, -1, -1, -1, -1, -1, -1],
    10: [6, 4, 4, 4, 2, -1, -1, -1, -1, -1],
    11: [6, 4, 4, 4, 3, -1, -1, -1, -1, -1],
    12: [6, 4, 4, 4, 3, -1, -1, -1, -1, -1],
    13: [6, 4, 4, 4, 4, 2, -1, -1, -1, -1],
    14: [6, 4, 4, 4, 4, 3, -1, -1, -1, -1],
    15: [6, 4, 4, 4, 4, 3, -1, -1, -1, -1],
    16: [6, 5, 4, 4, 4, 4, 2, -1, -1, -1],
    17: [6, 5, 5, 4, 4, 4, 3, -1, -1, -1],
    18: [6, 5, 5, 5, 4, 4, 3, -1, -1, -1],
    19: [6, 5, 5, 5, 5, 4, 4, -1, -1, -1],
    20: [6, 5, 5, 5, 5, 5, 4, -1, -1, -1],
}


# ---------------------------------------------------------------------------
# SpellsKnownManager
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class SpellsKnownManager:
    """Tracks the limited list of spells a spontaneous caster (Sorcerer/Bard)
    actually knows.

    Unlike the Wizard's :class:`Spellbook`, a Sorcerer's spells known list is
    strictly limited by class level. Spells known cannot be changed freely —
    they represent innate mastery rather than scholarly study.

    Attributes:
        known_spells: Mapping of spell_level → set of known spell names.
        max_known:    Maximum number of spells known per level (from SRD table).
    """

    known_spells: Dict[int, Set[str]] = field(
        default_factory=lambda: {i: set() for i in range(10)}
    )
    max_known: List[int] = field(default_factory=lambda: [0] * 10)

    @classmethod
    def for_sorcerer(cls, level: int) -> "SpellsKnownManager":
        """Create a SpellsKnownManager for a Sorcerer at the given level.

        Args:
            level: Sorcerer class level (1–20).

        Returns:
            A configured :class:`SpellsKnownManager` with correct caps.
        """
        table = _SORCERER_SPELLS_KNOWN.get(level, [0] * 10)
        max_known = [max(0, v) for v in table]
        return cls(
            known_spells={i: set() for i in range(10)},
            max_known=max_known,
        )

    @classmethod
    def for_bard(cls, level: int) -> "SpellsKnownManager":
        """Create a SpellsKnownManager for a Bard at the given level.

        Args:
            level: Bard class level (1–20).

        Returns:
            A configured :class:`SpellsKnownManager` with correct caps.
        """
        table = _BARD_SPELLS_KNOWN.get(level, [0] * 10)
        max_known = [max(0, v) for v in table]
        return cls(
            known_spells={i: set() for i in range(10)},
            max_known=max_known,
        )

    def can_learn(self, spell_level: int) -> bool:
        """Check if the caster can learn another spell at the given level.

        Args:
            spell_level: Spell level (0–9).

        Returns:
            ``True`` if there is room for another spell at that level.
        """
        if self.max_known[spell_level] <= 0:
            return False
        return len(self.known_spells[spell_level]) < self.max_known[spell_level]

    def learn_spell(self, spell_name: str, spell_level: int) -> bool:
        """Add a spell to the known list at the given level.

        Args:
            spell_name:  Name of the spell to learn.
            spell_level: The spell's level (0–9).

        Returns:
            ``True`` if the spell was successfully learned, ``False`` if
            the spell is already known or the known list is full.
        """
        if spell_name in self.known_spells[spell_level]:
            return False
        if not self.can_learn(spell_level):
            return False
        self.known_spells[spell_level].add(spell_name)
        return True

    def is_known(self, spell_name: str, spell_level: int) -> bool:
        """Check if a spell is known at the given level.

        Args:
            spell_name:  Name of the spell.
            spell_level: The spell's level (0–9).

        Returns:
            ``True`` if the spell is known at that level.
        """
        return spell_name in self.known_spells[spell_level]

    def get_known(self, spell_level: int) -> Set[str]:
        """Return the set of known spells at a given level.

        Args:
            spell_level: Spell level (0–9).

        Returns:
            Set of known spell names.
        """
        return set(self.known_spells[spell_level])

    def total_known(self) -> int:
        """Total number of spells known across all levels."""
        return sum(len(s) for s in self.known_spells.values())


# ---------------------------------------------------------------------------
# SpontaneousCasterManager
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class SpontaneousCasterManager:
    """Specialized slot manager for spontaneous casters (Sorcerer/Bard).

    Unlike Wizards and Clerics who prepare specific spells into slots,
    spontaneous casters can cast *any* spell they know using an available
    slot of the appropriate level. This manager checks the
    :class:`SpellsKnownManager` rather than a "Prepared" list.

    Charisma is the key ability for Sorcerers: bonus spell slots are
    computed from CHA modifier.

    Attributes:
        slot_manager:    The underlying :class:`SpellSlotManager`.
        spells_known:    The :class:`SpellsKnownManager` tracking known spells.
    """

    slot_manager: SpellSlotManager
    spells_known: SpellsKnownManager

    @classmethod
    def for_sorcerer(
        cls,
        level: int,
        cha_mod: int,
    ) -> "SpontaneousCasterManager":
        """Create a SpontaneousCasterManager for a Sorcerer.

        Uses Charisma for bonus spell slots per the 3.5e SRD.

        Args:
            level:   Sorcerer class level (1–20).
            cha_mod: Charisma modifier.

        Returns:
            A configured :class:`SpontaneousCasterManager`.
        """
        slot_manager = SpellSlotManager.for_class("Sorcerer", level, cha_mod)
        spells_known = SpellsKnownManager.for_sorcerer(level)
        return cls(slot_manager=slot_manager, spells_known=spells_known)

    @classmethod
    def for_bard(
        cls,
        level: int,
        cha_mod: int,
    ) -> "SpontaneousCasterManager":
        """Create a SpontaneousCasterManager for a Bard.

        Bards are spontaneous arcane casters using Charisma.
        They cast up to 6th-level spells from a limited known list.

        Args:
            level:   Bard class level (1–20).
            cha_mod: Charisma modifier.

        Returns:
            A configured :class:`SpontaneousCasterManager`.
        """
        slot_manager = SpellSlotManager.for_class("Bard", level, cha_mod)
        spells_known = SpellsKnownManager.for_bard(level)
        return cls(slot_manager=slot_manager, spells_known=spells_known)

    def can_cast(self, spell_name: str, spell_level: int) -> bool:
        """Check if a spell can be cast (is known and a slot is available).

        Args:
            spell_name:  Name of the spell.
            spell_level: Spell level (0–9).

        Returns:
            ``True`` if the spell is known and a slot is available.
        """
        if not self.spells_known.is_known(spell_name, spell_level):
            return False
        return self.slot_manager.available(spell_level) > 0

    def cast_spell(self, spell_name: str, spell_level: int) -> bool:
        """Cast a known spell, expending a slot of the appropriate level.

        Spontaneous casters do not need to prepare spells. They can cast
        any known spell as long as a slot of the correct level remains.

        Args:
            spell_name:  Name of the spell to cast.
            spell_level: Spell level of the slot to expend.

        Returns:
            ``True`` if the spell was successfully cast (known and slot
            available), ``False`` otherwise.
        """
        if not self.spells_known.is_known(spell_name, spell_level):
            return False
        return self.slot_manager.expend(spell_level)

    def rest(self) -> None:
        """Restore all spell slots after a long rest (8 hours).

        Note: Unlike Wizards, Sorcerers do not need to re-prepare spells.
        Their known spells remain unchanged.
        """
        self.slot_manager.rest()

    def available_slots(self, spell_level: int) -> int:
        """Return remaining slots at the given level.

        Args:
            spell_level: Spell level (0–9).

        Returns:
            Number of available slots.
        """
        return self.slot_manager.available(spell_level)

    def learn_spell(self, spell_name: str, spell_level: int) -> bool:
        """Learn a new spell (delegate to SpellsKnownManager).

        Args:
            spell_name:  Name of the spell.
            spell_level: Spell level (0–9).

        Returns:
            ``True`` if successfully learned.
        """
        return self.spells_known.learn_spell(spell_name, spell_level)
