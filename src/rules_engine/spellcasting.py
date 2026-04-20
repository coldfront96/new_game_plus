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

# Mapping of caster class to their slot table and key ability.
_CASTER_TABLES: Dict[str, Dict[str, Any]] = {
    "Wizard": {"table": _WIZARD_SLOTS, "key_ability": "intelligence"},
    "Sorcerer": {"table": _SORCERER_SLOTS, "key_ability": "charisma"},
    "Cleric": {"table": _CLERIC_SLOTS, "key_ability": "wisdom"},
    "Druid": {"table": _CLERIC_SLOTS, "key_ability": "wisdom"},
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
