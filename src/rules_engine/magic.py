"""
src/rules_engine/magic.py
--------------------------
Foundational spell definitions and registry for D&D 3.5e Wizardry.

Provides the :class:`Spell` dataclass representing a canonical spell entry
and the :class:`SpellRegistry` for fast lookups by name or level.

Memory Optimisation
~~~~~~~~~~~~~~~~~~~
Uses ``@dataclass(slots=True)`` to eliminate per-instance ``__dict__``
overhead, supporting hundreds of spell definitions in the 64GB RAM
environment without excessive memory usage.

Usage::

    from src.rules_engine.magic import Spell, SpellRegistry

    registry = SpellRegistry()
    mm = registry.get("Magic Missile")
    print(mm.level, mm.school)  # 1, "Evocation"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


# ---------------------------------------------------------------------------
# Spell Schools (3.5e SRD)
# ---------------------------------------------------------------------------

SPELL_SCHOOLS = frozenset({
    "Abjuration",
    "Conjuration",
    "Divination",
    "Enchantment",
    "Evocation",
    "Illusion",
    "Necromancy",
    "Transmutation",
    "Universal",
})


# ---------------------------------------------------------------------------
# Spell Dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Spell:
    """A canonical D&D 3.5e spell definition.

    Attributes:
        name:             Spell name (e.g. "Magic Missile").
        level:            Spell level for Wizards (0–9).
        school:           School of magic (e.g. "Evocation").
        components:       List of component types ("V", "S", "M", "F", "XP").
        range:            Range descriptor (e.g. "Medium (100 ft. + 10 ft./level)").
        duration:         Duration descriptor (e.g. "Instantaneous").
        description:      Brief rules text description.
        effect_callback:  Placeholder callable for resolving spell effects.
    """

    name: str
    level: int
    school: str
    components: List[str] = field(default_factory=list)
    range: str = "Close (25 ft. + 5 ft./2 levels)"
    duration: str = "Instantaneous"
    description: str = ""
    effect_callback: Optional[Callable[..., Any]] = None

    def __post_init__(self) -> None:
        """Validate spell school against SRD schools."""
        if self.school not in SPELL_SCHOOLS:
            raise ValueError(
                f"Invalid spell school '{self.school}'. "
                f"Must be one of: {sorted(SPELL_SCHOOLS)}"
            )
        if not 0 <= self.level <= 9:
            raise ValueError(
                f"Spell level must be 0–9, got {self.level}."
            )


# ---------------------------------------------------------------------------
# SpellRegistry
# ---------------------------------------------------------------------------

class SpellRegistry:
    """High-performance registry for canonical spell definitions.

    Provides O(1) lookups by spell name and O(1) lookups by level via
    pre-built index dictionaries.  Optimised for the 64GB RAM environment
    where thousands of spells may be registered simultaneously.

    Usage::

        registry = SpellRegistry()
        registry.register(my_spell)
        result = registry.get("Magic Missile")
        level_1_spells = registry.get_by_level(1)
    """

    __slots__ = ("_by_name", "_by_level")

    def __init__(self) -> None:
        self._by_name: Dict[str, Spell] = {}
        self._by_level: Dict[int, List[Spell]] = {i: [] for i in range(10)}

    def register(self, spell: Spell) -> None:
        """Register a spell in the registry.

        Args:
            spell: The Spell to register.

        Raises:
            ValueError: If a spell with the same name is already registered.
        """
        if spell.name in self._by_name:
            raise ValueError(f"Spell '{spell.name}' is already registered.")
        self._by_name[spell.name] = spell
        self._by_level[spell.level].append(spell)

    def get(self, name: str) -> Optional[Spell]:
        """Retrieve a spell by name. Returns None if not found."""
        return self._by_name.get(name)

    def get_by_level(self, level: int) -> List[Spell]:
        """Retrieve all registered spells of a given level.

        Args:
            level: Spell level (0–9).

        Returns:
            List of spells at that level (may be empty).
        """
        return list(self._by_level.get(level, []))

    def all_spells(self) -> List[Spell]:
        """Return all registered spells."""
        return list(self._by_name.values())

    def __len__(self) -> int:
        return len(self._by_name)

    def __contains__(self, name: str) -> bool:
        return name in self._by_name


# ---------------------------------------------------------------------------
# Default Wizard Spells (SRD)
# ---------------------------------------------------------------------------

def _create_default_spells() -> SpellRegistry:
    """Create and populate a SpellRegistry with the initial SRD Wizard spells."""
    registry = SpellRegistry()

    magic_missile = Spell(
        name="Magic Missile",
        level=1,
        school="Evocation",
        components=["V", "S"],
        range="Medium (100 ft. + 10 ft./level)",
        duration="Instantaneous",
        description=(
            "A missile of magical energy darts forth from your fingertip and "
            "strikes its target, dealing 1d4+1 points of force damage. For "
            "every two caster levels beyond 1st, you gain an additional missile."
        ),
    )

    mage_armor = Spell(
        name="Mage Armor",
        level=1,
        school="Conjuration",
        components=["V", "S", "F"],
        range="Touch",
        duration="1 hour/level",
        description=(
            "An invisible but tangible field of force surrounds the subject "
            "of a mage armor spell, providing a +4 armor bonus to AC. Unlike "
            "mundane armor, mage armor entails no armor check penalty, arcane "
            "spell failure chance, or speed reduction."
        ),
    )

    registry.register(magic_missile)
    registry.register(mage_armor)

    return registry


# Module-level default registry instance
DEFAULT_SPELL_REGISTRY: SpellRegistry = _create_default_spells()
