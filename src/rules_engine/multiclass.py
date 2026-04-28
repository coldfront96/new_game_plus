"""
src/rules_engine/multiclass.py
-------------------------------
D&D 3.5e Multiclassing subsystem.

Implements:
    E-007 — ClassLevel / MulticlassRecord schema
    E-008 — FavoredClassPolicy / RaceFavoredClass
    E-024 — multiclass_xp_penalty_pct
    E-025 — favored_class_for
    E-039 — FAVORED_CLASS_REGISTRY
    E-051 — MulticlassStats / build_multiclass_stats
    E-058 — multiclass_caster_levels / combined_caster_level / CombineMode
    E-065 — LevelUpReport / level_up_standard (stub for prestige integration)

PHB reference: Player's Handbook, Chapter 3 (Classes), Multiclass Characters.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


# ---------------------------------------------------------------------------
# E-007 — Multiclass Class-Level Entry Schema
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ClassLevel:
    """One entry in a character's multiclass record."""

    class_name: str
    level: int
    is_prestige: bool = False


@dataclass(slots=True)
class MulticlassRecord:
    """Full multiclass record for a character."""

    entries: list[ClassLevel]
    favored_class: Optional[str]      # None = not yet determined
    total_xp: int = 0
    current_xp_penalty_pct: float = 0.0


# ---------------------------------------------------------------------------
# E-008 — Favored Class Policy Enum
# ---------------------------------------------------------------------------

class FavoredClassPolicy(Enum):
    Fixed = auto()          # Dwarf→Fighter, Elf→Wizard, etc.
    HighestLevel = auto()   # Human, Half-Elf → whichever class has highest level
    Any = auto()            # special cases


@dataclass(slots=True)
class RaceFavoredClass:
    """Favored class definition for a race."""

    race_name: str                   # matches Race.name
    policy: FavoredClassPolicy
    class_name: Optional[str]        # None when policy is HighestLevel or Any


# ---------------------------------------------------------------------------
# E-039 — Race Favored Class Registry
# ---------------------------------------------------------------------------

FAVORED_CLASS_REGISTRY: dict[str, RaceFavoredClass] = {
    "Human": RaceFavoredClass(
        race_name="Human", policy=FavoredClassPolicy.HighestLevel, class_name=None
    ),
    "Half-Elf": RaceFavoredClass(
        race_name="Half-Elf", policy=FavoredClassPolicy.HighestLevel, class_name=None
    ),
    "Dwarf": RaceFavoredClass(
        race_name="Dwarf", policy=FavoredClassPolicy.Fixed, class_name="Fighter"
    ),
    "Elf": RaceFavoredClass(
        race_name="Elf", policy=FavoredClassPolicy.Fixed, class_name="Wizard"
    ),
    "Gnome": RaceFavoredClass(
        race_name="Gnome", policy=FavoredClassPolicy.Fixed, class_name="Bard"
    ),
    "Half-Orc": RaceFavoredClass(
        race_name="Half-Orc", policy=FavoredClassPolicy.Fixed, class_name="Barbarian"
    ),
    "Halfling": RaceFavoredClass(
        race_name="Halfling", policy=FavoredClassPolicy.Fixed, class_name="Rogue"
    ),
}


# ---------------------------------------------------------------------------
# E-025 — Favored Class Lookup by Race
# ---------------------------------------------------------------------------

def favored_class_for(race_name: str, record: MulticlassRecord) -> Optional[str]:
    """Return the favored class name for *race_name* given the current *record*.

    HighestLevel policy: returns the non-prestige entry with the highest level
    (first one wins on a tie). Fixed policy: returns the registered class_name.
    Returns ``None`` if the race is not in the registry or has no class entries.
    """
    entry = FAVORED_CLASS_REGISTRY.get(race_name)
    if entry is None:
        return None

    if entry.policy == FavoredClassPolicy.Fixed:
        return entry.class_name

    if entry.policy == FavoredClassPolicy.HighestLevel:
        non_prestige = [e for e in record.entries if not e.is_prestige]
        if not non_prestige:
            return None
        return max(non_prestige, key=lambda e: e.level).class_name

    # FavoredClassPolicy.Any — no exclusions
    return None


# ---------------------------------------------------------------------------
# E-024 — Multiclass XP Penalty Calculator
# ---------------------------------------------------------------------------

def multiclass_xp_penalty_pct(record: MulticlassRecord, race_name: str) -> float:
    """Compute the PHB Ch 3 multiclass XP penalty percentage.

    1. Determine the favored class via :func:`favored_class_for`.
    2. Filter out prestige classes and the favored class from the check.
    3. If ≤ 1 remaining class, return 0.0.
    4. If max(level) − min(level) ≥ 2 across remaining classes, return 20.0.
    5. Otherwise return 0.0.
    """
    favored = favored_class_for(race_name, record)

    relevant = [
        e for e in record.entries
        if not e.is_prestige and e.class_name != favored
    ]

    if len(relevant) <= 1:
        return 0.0

    levels = [e.level for e in relevant]
    if max(levels) - min(levels) >= 2:
        return 20.0
    return 0.0


# ---------------------------------------------------------------------------
# E-051 — Multiclass Character Stat Builder
# ---------------------------------------------------------------------------

# BAB progressions
def _bab_full(level: int) -> int:
    return level


def _bab_three_quarters(level: int) -> int:
    return (level * 3) // 4


def _bab_half(level: int) -> int:
    return level // 2


# Save progressions (per-class contribution before stacking bonus)
def _save_good(level: int) -> int:
    return 2 + level // 2


def _save_poor(level: int) -> int:
    return level // 3


# Incremental good-save contribution for subsequent classes (no +2 bonus)
def _save_good_no_bonus(level: int) -> int:
    return level // 2


_BAB_FN = {
    "full": _bab_full,
    "three_quarters": _bab_three_quarters,
    "half": _bab_half,
}

_CLASS_STATS: dict[str, dict] = {
    "Barbarian":  {"bab": "full",           "fort": "good", "ref": "poor", "will": "poor", "hd": 12},
    "Bard":       {"bab": "three_quarters", "fort": "poor", "ref": "good", "will": "good", "hd": 6},
    "Cleric":     {"bab": "three_quarters", "fort": "good", "ref": "poor", "will": "good", "hd": 8},
    "Druid":      {"bab": "three_quarters", "fort": "good", "ref": "poor", "will": "good", "hd": 8},
    "Fighter":    {"bab": "full",           "fort": "good", "ref": "poor", "will": "poor", "hd": 10},
    "Monk":       {"bab": "three_quarters", "fort": "good", "ref": "good", "will": "good", "hd": 8},
    "Paladin":    {"bab": "full",           "fort": "good", "ref": "poor", "will": "poor", "hd": 10},
    "Ranger":     {"bab": "full",           "fort": "good", "ref": "good", "will": "poor", "hd": 8},
    "Rogue":      {"bab": "three_quarters", "fort": "poor", "ref": "good", "will": "poor", "hd": 6},
    "Sorcerer":   {"bab": "half",           "fort": "poor", "ref": "poor", "will": "good", "hd": 4},
    "Wizard":     {"bab": "half",           "fort": "poor", "ref": "poor", "will": "good", "hd": 4},
    # NPC classes
    "Commoner":   {"bab": "half",           "fort": "poor", "ref": "poor", "will": "poor", "hd": 4},
    "Expert":     {"bab": "three_quarters", "fort": "poor", "ref": "poor", "will": "good", "hd": 6},
    "Warrior":    {"bab": "full",           "fort": "good", "ref": "poor", "will": "poor", "hd": 8},
    "Adept":      {"bab": "half",           "fort": "poor", "ref": "poor", "will": "good", "hd": 6},
    "Aristocrat": {"bab": "three_quarters", "fort": "poor", "ref": "poor", "will": "good", "hd": 8},
}


@dataclass(slots=True)
class MulticlassStats:
    """Computed combat statistics for a multiclass character."""

    total_bab: int
    fort_save: int
    ref_save: int
    will_save: int
    total_hd: int
    hp_pool: int   # sum of average HD per level (max for very first HD)


def build_multiclass_stats(record: MulticlassRecord, con_modifier: int = 0) -> MulticlassStats:
    """Build combined multiclass stats per PHB Ch 3.

    BAB: sum of per-class BAB at each class level.
    Saves: sum per-class with the one-time +2 base bonus only for the first
           class that has "good" in each save category.
    HD/hp_pool: first level overall is maximum HD; all subsequent levels use
                average (rounded up), i.e. ``(hd + 1) // 2``.
    """
    total_bab = 0
    fort = 0
    ref = 0
    will = 0
    total_hd = 0
    hp_pool = 0

    # Track whether the +2 one-time bonus has been granted per save category.
    fort_bonus_given = False
    ref_bonus_given = False
    will_bonus_given = False

    # Determine which class entry represents level 1 overall (first HD is max).
    # We treat the entry with the highest contribution as "primary" only for HP;
    # in practice the first entry in the list is level 1 if the character was
    # built sequentially. We handle it simply: total first level = max HD.
    first_level_applied = False

    for entry in record.entries:
        stats = _CLASS_STATS.get(entry.class_name)
        if stats is None:
            continue  # unknown / prestige class — caller handles separately

        hd = stats["hd"]
        lv = entry.level

        # BAB
        total_bab += _BAB_FN[stats["bab"]](lv)

        # Saves — apply one-time +2 bonus for first good-save class
        if stats["fort"] == "good":
            if not fort_bonus_given:
                fort += _save_good(lv)
                fort_bonus_given = True
            else:
                fort += _save_good_no_bonus(lv)
        else:
            fort += _save_poor(lv)

        if stats["ref"] == "good":
            if not ref_bonus_given:
                ref += _save_good(lv)
                ref_bonus_given = True
            else:
                ref += _save_good_no_bonus(lv)
        else:
            ref += _save_poor(lv)

        if stats["will"] == "good":
            if not will_bonus_given:
                will += _save_good(lv)
                will_bonus_given = True
            else:
                will += _save_good_no_bonus(lv)
        else:
            will += _save_poor(lv)

        # HD and HP
        total_hd += hd * lv
        avg = (hd + 1) // 2  # average rounded up

        for level_index in range(lv):
            if not first_level_applied:
                # Very first character level: maximum HD + CON mod
                hp_pool += hd + con_modifier
                first_level_applied = True
            else:
                hp_pool += avg + con_modifier

    return MulticlassStats(
        total_bab=total_bab,
        fort_save=fort,
        ref_save=ref,
        will_save=will,
        total_hd=total_hd,
        hp_pool=hp_pool,
    )


# ---------------------------------------------------------------------------
# E-058 — Multiclass Spellcasting Adjudicator
# ---------------------------------------------------------------------------

class CombineMode(Enum):
    """How to combine caster levels for special cases."""

    Sum = auto()       # add all caster levels
    Max = auto()       # take highest
    Prestige = auto()  # prestige continuation (handled by prestige_classes.py)


# Classes that cast spells and their caster-level formula.
# Paladin/Ranger start at class level 4 (CL = class_level - 3).
_SPELLCASTING_CLASSES: dict[str, str] = {
    "Bard":     "full",
    "Cleric":   "full",
    "Druid":    "full",
    "Sorcerer": "full",
    "Wizard":   "full",
    "Adept":    "full",
    "Paladin":  "paladin_ranger",
    "Ranger":   "paladin_ranger",
}


def _caster_level_for(class_name: str, class_level: int) -> int:
    """Return the effective caster level for *class_name* at *class_level*."""
    formula = _SPELLCASTING_CLASSES.get(class_name)
    if formula is None:
        return 0
    if formula == "paladin_ranger":
        cl = class_level - 3
        return cl if cl > 0 else 0
    return class_level  # "full"


def multiclass_caster_levels(char_class_levels: list[ClassLevel]) -> dict[str, int]:
    """Return mapping of class_name → caster_level for spellcasting classes.

    Non-spellcasting classes are omitted. Each spellcasting class tracks its
    own CL independently per PHB Ch 3.
    """
    result: dict[str, int] = {}
    for entry in char_class_levels:
        cl = _caster_level_for(entry.class_name, entry.level)
        if cl > 0:
            result[entry.class_name] = cl
    return result


def combined_caster_level(
    char_class_levels: list[ClassLevel],
    mode: CombineMode = CombineMode.Max,
) -> int:
    """Combine caster levels across all spellcasting classes per *mode*.

    Used for prestige class CL continuation and other special cases.
    Returns 0 if the character has no spellcasting classes.
    """
    cls_map = multiclass_caster_levels(char_class_levels)
    if not cls_map:
        return 0
    levels = list(cls_map.values())
    if mode == CombineMode.Sum:
        return sum(levels)
    if mode == CombineMode.Max:
        return max(levels)
    # CombineMode.Prestige — handled externally; return Max as sensible default
    return max(levels)


# ---------------------------------------------------------------------------
# E-065 — Unified Multiclass + Prestige Progression (stub)
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class LevelUpReport:
    """Summary of stat changes gained when levelling up one class."""

    class_name: str
    new_level: int
    bab_delta: int
    fort_delta: int
    ref_delta: int
    will_delta: int
    hp_gained: int
    xp_penalty_pct: float
    notes: list[str]


def level_up_standard(
    record: MulticlassRecord,
    class_name: str,
    race_name: str,
    con_modifier: int = 0,
    rng=None,
) -> LevelUpReport:
    """Increment *class_name* in *record* by 1, recompute XP penalty.

    If *class_name* is not present in *record.entries* it is added at level 1.
    *rng*, if provided, must have a ``randint(a, b)`` method (inclusive); when
    ``None`` the average HD value is used instead.

    Returns a :class:`LevelUpReport` describing the changes.

    .. note::
        Prestige-class integration (E-053) is handled by ``prestige_classes.py``.
        This function is intentionally limited to standard (non-prestige) classes.
    """
    stats_before = build_multiclass_stats(record, con_modifier)

    # Find or create the class entry
    entry = next((e for e in record.entries if e.class_name == class_name), None)
    if entry is None:
        entry = ClassLevel(class_name=class_name, level=0)
        record.entries.append(entry)

    # Increment level (slots=True means we must mutate via object attribute)
    object.__setattr__(entry, "level", entry.level + 1)
    new_level = entry.level

    stats_after = build_multiclass_stats(record, con_modifier)

    # Compute HP gained for this single level
    class_stats = _CLASS_STATS.get(class_name)
    hd = class_stats["hd"] if class_stats else 6  # fallback

    total_levels_after = sum(e.level for e in record.entries)
    if total_levels_after == 1:
        # Very first level: max HD
        hp_gained = hd + con_modifier
    elif rng is not None:
        hp_gained = rng.randint(1, hd) + con_modifier
    else:
        hp_gained = (hd + 1) // 2 + con_modifier  # average, rounded up

    # Recompute XP penalty
    penalty = multiclass_xp_penalty_pct(record, race_name)
    object.__setattr__(record, "current_xp_penalty_pct", penalty)

    notes: list[str] = []
    if penalty > 0.0:
        notes.append(f"{penalty:.0f}% XP penalty applies")

    return LevelUpReport(
        class_name=class_name,
        new_level=new_level,
        bab_delta=stats_after.total_bab - stats_before.total_bab,
        fort_delta=stats_after.fort_save - stats_before.fort_save,
        ref_delta=stats_after.ref_save - stats_before.ref_save,
        will_delta=stats_after.will_save - stats_before.will_save,
        hp_gained=hp_gained,
        xp_penalty_pct=penalty,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# E-065 — Unified Multiclass + Prestige Progression
# ---------------------------------------------------------------------------

def level_up(
    record: MulticlassRecord,
    klass: str,
    race_name: str,
    character=None,
    con_modifier: int = 0,
    rng=None,
) -> LevelUpReport:
    """Unified level-up for standard classes and prestige classes.

    Decision tree:
    * If *klass* is in ``PRESTIGE_CLASS_REGISTRY``:
        1. Verify prerequisites via ``attempt_prestige_entry`` (or
           ``advance_prestige`` if already entered).
        2. Apply BAB/save deltas via the prestige class's progression data.
        3. Apply caster-level continuation via
           ``apply_prestige_caster_continuation``.
        4. Prestige levels are **exempt** from the XP penalty (``is_prestige``
           flag).
    * Otherwise delegates to :func:`level_up_standard`.

    Args:
        record:        The character's :class:`MulticlassRecord`; mutated
                       in-place.
        klass:         Class name to advance (standard or prestige).
        race_name:     Race name used for favored-class XP-penalty logic.
        character:     Optional ``Character35e`` instance; required for
                       prerequisite verification when entering a prestige
                       class for the first time.  May be ``None`` if the
                       prestige class is already recorded in *record*.
        con_modifier:  CON modifier added to each HP roll.
        rng:           Object with ``randint(a, b)`` method; when ``None``
                       average HD is used.

    Returns:
        A :class:`LevelUpReport` describing the stat changes.

    Raises:
        ValueError: If *klass* is a prestige class and prerequisites are
                    not met, or the class is already at ``max_class_level``.
    """
    from src.rules_engine.prestige_classes import (
        PRESTIGE_CLASS_REGISTRY,
        attempt_prestige_entry,
        advance_prestige,
        apply_prestige_caster_continuation,
        CasterLevelMode,
    )
    from src.rules_engine.npc_classes import BABProgression

    if klass not in PRESTIGE_CLASS_REGISTRY:
        # Standard (non-prestige) path
        return level_up_standard(record, klass, race_name, con_modifier, rng)

    # ---- Prestige path ----
    pc = PRESTIGE_CLASS_REGISTRY[klass]

    # Determine if this is a first-time entry or an advancement
    existing = next((e for e in record.entries if e.class_name == klass), None)

    stats_before = build_multiclass_stats(record, con_modifier)

    if existing is None:
        # First entry: validate prerequisites
        entry_result = attempt_prestige_entry(character, klass, record)
        if not entry_result.success:
            raise ValueError(
                f"Prerequisites not met for '{klass}': "
                + entry_result.prerequisite_result.summary
            )
        new_level = 1
    else:
        # Already entered: just advance
        advance_prestige(record, klass)
        existing_after = next(e for e in record.entries if e.class_name == klass)
        new_level = existing_after.level

    stats_after = build_multiclass_stats(record, con_modifier)

    # HP gained: use average (or roll)
    hd = pc.hit_die
    total_levels_after = sum(e.level for e in record.entries)
    if total_levels_after == 1:
        hp_gained = hd + con_modifier
    elif rng is not None:
        hp_gained = rng.randint(1, hd) + con_modifier
    else:
        hp_gained = (hd + 1) // 2 + con_modifier

    # Caster-level continuation
    caster_meta = {
        "arcane_caster_level": sum(
            e.level for e in record.entries
            if e.class_name in ("Wizard", "Sorcerer", "Bard")
        ),
        "divine_caster_level": sum(
            e.level for e in record.entries
            if e.class_name in ("Cleric", "Druid", "Paladin", "Ranger", "Adept")
        ),
    }
    apply_prestige_caster_continuation(record, pc, new_level, caster_meta)

    # Prestige classes are always penalty-exempt
    penalty = multiclass_xp_penalty_pct(record, race_name)
    object.__setattr__(record, "current_xp_penalty_pct", penalty)

    notes: list[str] = [f"Entered/advanced prestige class '{klass}' to level {new_level}."]
    if pc.caster_level_progression != CasterLevelMode.None_:
        notes.append(f"Caster-level continuation applied ({pc.caster_level_progression.name}).")

    return LevelUpReport(
        class_name=klass,
        new_level=new_level,
        bab_delta=stats_after.total_bab - stats_before.total_bab,
        fort_delta=stats_after.fort_save - stats_before.fort_save,
        ref_delta=stats_after.ref_save - stats_before.ref_save,
        will_delta=stats_after.will_save - stats_before.will_save,
        hp_gained=hp_gained,
        xp_penalty_pct=penalty,
        notes=notes,
    )
