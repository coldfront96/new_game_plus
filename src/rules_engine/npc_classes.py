"""
src/rules_engine/npc_classes.py
--------------------------------
D&D 3.5e NPC Classes subsystem.

Implements:
    E-009 — NPCClassName / BABProgression / SaveType / NPCClassBase schema
    E-026 — NPCProgression / npc_class_progression
    E-040 — NPC_CLASS_REGISTRY / NPC_CLASS_DISTRIBUTION_PCT
    E-052 — NPCStats / generate_npc

DMG reference: Dungeon Master's Guide, Chapter 4 (NPC Classes).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

from src.rules_engine.multiclass import _bab_full, _bab_three_quarters, _bab_half, _save_good, _save_poor


# ---------------------------------------------------------------------------
# E-009 — NPC Class Base Schema
# ---------------------------------------------------------------------------

class NPCClassName(Enum):
    Commoner = auto()
    Expert = auto()
    Warrior = auto()
    Adept = auto()
    Aristocrat = auto()


class BABProgression(Enum):
    """Attack bonus progression rates."""
    Full = "full"               # BAB = level
    ThreeQuarters = "3/4"      # BAB = (level*3)//4
    Half = "1/2"               # BAB = level // 2


class SaveType(Enum):
    """Saving throw identifiers used to mark which saves have good progression.

    Good-save formula: 2 + level // 2
    Poor-save formula: level // 3
    """
    Fort = "fort"
    Ref  = "ref"
    Will = "will"


@dataclass(slots=True)
class NPCClassBase:
    name: NPCClassName
    hit_die: int
    bab_progression: BABProgression
    good_saves: tuple[SaveType, ...]   # which save types are "good"
    skill_points_per_level: int
    class_skills: tuple[str, ...]


# ---------------------------------------------------------------------------
# E-040 — NPC Class Registry
# ---------------------------------------------------------------------------

NPC_CLASS_REGISTRY: dict[NPCClassName, NPCClassBase] = {
    NPCClassName.Commoner: NPCClassBase(
        name=NPCClassName.Commoner,
        hit_die=4,
        bab_progression=BABProgression.Half,
        good_saves=(),  # all poor
        skill_points_per_level=2,
        class_skills=(
            "Climb", "Craft", "Handle Animal", "Jump", "Listen",
            "Profession", "Ride", "Spot", "Swim", "Use Rope",
        ),
    ),
    NPCClassName.Expert: NPCClassBase(
        name=NPCClassName.Expert,
        hit_die=6,
        bab_progression=BABProgression.ThreeQuarters,
        good_saves=(SaveType.Will,),
        skill_points_per_level=6,
        class_skills=(
            "Appraise", "Craft", "Decipher Script", "Disable Device",
            "Forgery", "Gather Information", "Handle Animal", "Heal",
            "Knowledge", "Perform", "Profession", "Ride", "Search",
            "Sense Motive", "Sleight of Hand", "Speak Language",
            "Spellcraft", "Survival", "Swim", "Use Rope",
        ),
    ),
    NPCClassName.Warrior: NPCClassBase(
        name=NPCClassName.Warrior,
        hit_die=8,
        bab_progression=BABProgression.Full,
        good_saves=(SaveType.Fort,),
        skill_points_per_level=2,
        class_skills=("Climb", "Handle Animal", "Intimidate", "Jump", "Ride", "Swim"),
    ),
    NPCClassName.Adept: NPCClassBase(
        name=NPCClassName.Adept,
        hit_die=6,
        bab_progression=BABProgression.Half,
        good_saves=(SaveType.Will,),
        skill_points_per_level=2,
        class_skills=(
            "Concentration", "Craft", "Handle Animal", "Heal",
            "Knowledge (arcana)", "Knowledge (nature)", "Profession",
            "Spellcraft", "Survival",
        ),
    ),
    NPCClassName.Aristocrat: NPCClassBase(
        name=NPCClassName.Aristocrat,
        hit_die=8,
        bab_progression=BABProgression.ThreeQuarters,
        good_saves=(SaveType.Will,),
        skill_points_per_level=4,
        class_skills=(
            "Appraise", "Bluff", "Diplomacy", "Disguise", "Forgery",
            "Gather Information", "Handle Animal", "Intimidate",
            "Knowledge (history)", "Knowledge (local)", "Knowledge (nobility)",
            "Listen", "Perform", "Ride", "Sense Motive", "Spot", "Swim",
        ),
    ),
}

NPC_CLASS_DISTRIBUTION_PCT: dict[NPCClassName, float] = {
    NPCClassName.Commoner:   0.75,
    NPCClassName.Expert:     0.12,
    NPCClassName.Warrior:    0.08,
    NPCClassName.Adept:      0.03,
    NPCClassName.Aristocrat: 0.02,
}


# ---------------------------------------------------------------------------
# E-026 — NPC Class Advancement Formula
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class NPCProgression:
    bab: int
    fort: int
    ref: int
    will: int
    hit_dice_total: int   # number of HD (= level)
    class_features: list[str]


_BAB_FN = {
    BABProgression.Full:          _bab_full,
    BABProgression.ThreeQuarters: _bab_three_quarters,
    BABProgression.Half:          _bab_half,
}

_CLASS_FEATURES: dict[NPCClassName, list[str]] = {
    NPCClassName.Commoner:   [],
    NPCClassName.Expert:     ["Expert Skills"],
    NPCClassName.Warrior:    ["Bonus Feat (1st level)"],
    NPCClassName.Adept:      ["Spells", "Summon Familiar"],
    NPCClassName.Aristocrat: ["Bonus Languages"],
}


def npc_class_progression(klass: NPCClassName, level: int) -> NPCProgression:
    """Compute NPC class stats at *level*.

    BAB progressions (DMG Ch 4):
      Commoner/Adept — half (level//2)
      Expert/Aristocrat — three-quarters ((level*3)//4)
      Warrior — full (level)

    Save formulas:
      Good save = 2 + level//2
      Poor save = level//3
    """
    if level < 1:
        raise ValueError(f"level must be >= 1, got {level}")

    klass_base = NPC_CLASS_REGISTRY[klass]
    bab = _BAB_FN[klass_base.bab_progression](level)

    good = klass_base.good_saves

    fort = _save_good(level) if SaveType.Fort in good else _save_poor(level)
    ref  = _save_good(level) if SaveType.Ref  in good else _save_poor(level)
    will = _save_good(level) if SaveType.Will in good else _save_poor(level)

    return NPCProgression(
        bab=bab,
        fort=fort,
        ref=ref,
        will=will,
        hit_dice_total=level,
        class_features=list(_CLASS_FEATURES.get(klass, [])),
    )


# ---------------------------------------------------------------------------
# E-052 — NPC Stat Block Generator
# ---------------------------------------------------------------------------

# Average HD roll rounded up: (hd + 1) // 2
_AVG_HP: dict[int, int] = {4: 3, 6: 4, 8: 5, 10: 6, 12: 7}

# Rough armor bonus from available gp (very simple estimate)
def _armor_bonus_from_budget(gp: int) -> int:
    """Return a simple AC armor bonus estimate based on gp budget."""
    if gp >= 1_500:   # Full Plate or better
        return 8
    if gp >= 100:     # Chain Shirt (100 gp, +4 AC) or better
        return 4
    if gp >= 50:      # Scale Mail (~50 gp, +4) or similar
        return 3
    if gp >= 5:       # Padded / Leather
        return 1
    return 0


@dataclass(slots=True)
class NPCStats:
    klass: NPCClassName
    level: int
    bab: int
    fort: int
    ref: int
    will: int
    hp: int
    ac: int                    # 10 + armor bonus
    equipment_gp_budget: int   # DMG Table 4-23 approximation
    skills: dict[str, int]     # skill_name -> total ranks
    feats: list[str]


def generate_npc(klass: NPCClassName, level: int, rng=None) -> NPCStats:
    """Generate a complete NPC stat block.

    HP:
      Deterministic (rng=None): average HD rounded up per level
                                (d4→3, d6→4, d8→5).
      With rng: sum of individual die rolls per level.
      First level is always maximum HD.

    AC:
      10 + rough armor bonus derived from gp budget.

    Equipment gp budget:
      level² × 150 gp (DMG Table 4-23 approximation).

    Skills:
      Total ranks = level × skill_points_per_level, distributed evenly
      across class skills (remainder skills get one extra rank).

    Feats:
      One feat at 1st level, then one additional feat every 3 levels
      (levels 1, 3, 6, 9 …).  Named "Feat 1", "Feat 2", etc.
    """
    if level < 1:
        raise ValueError(f"level must be >= 1, got {level}")

    prog = npc_class_progression(klass, level)
    klass_base = NPC_CLASS_REGISTRY[klass]
    hd = klass_base.hit_die

    # --- HP ---
    if rng is None:
        avg = _AVG_HP.get(hd, (hd + 1) // 2)
        hp = hd + (level - 1) * avg  # first level max, rest average
    else:
        hp = hd  # first level max
        for _ in range(level - 1):
            hp += rng.randint(1, hd)

    # --- Equipment budget & AC ---
    gp_budget = level * level * 150
    armor_bonus = _armor_bonus_from_budget(gp_budget)
    ac = 10 + armor_bonus

    # --- Skills ---
    class_skills = list(klass_base.class_skills)
    total_ranks = level * klass_base.skill_points_per_level
    skills: dict[str, int] = {}
    if class_skills:
        base_ranks, extras = divmod(total_ranks, len(class_skills))
        for i, skill in enumerate(class_skills):
            skills[skill] = base_ranks + (1 if i < extras else 0)
    else:
        skills = {}

    # --- Feats ---
    # Level 1 plus every 3rd level: 1, 3, 6, 9, 12, 15, 18
    feat_levels = [1] + [lvl for lvl in range(3, level + 1, 3)]
    num_feats = len([fl for fl in feat_levels if fl <= level])
    feats = [f"Feat {i + 1}" for i in range(num_feats)]

    return NPCStats(
        klass=klass,
        level=level,
        bab=prog.bab,
        fort=prog.fort,
        ref=prog.ref,
        will=prog.will,
        hp=hp,
        ac=ac,
        equipment_gp_budget=gp_budget,
        skills=skills,
        feats=feats,
    )
