"""
src/rules_engine/prestige_classes.py
--------------------------------------
D&D 3.5e Prestige Classes subsystem.

Implements:
    E-010 — PrestigeClassBase schema / CasterLevelMode enum
    E-011 — PrerequisiteClause hierarchy (8 subtypes)
    E-027 — verify_prerequisites / PrerequisiteResult
    E-041 — PRESTIGE_CLASS_REGISTRY (all 16 DMG prestige classes)
    E-053 — attempt_prestige_entry / advance_prestige / PrestigeEntryResult
    E-059 — apply_prestige_caster_continuation

DMG reference: Dungeon Master's Guide, Chapter 2 (Prestige Classes).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

from src.rules_engine.npc_classes import BABProgression, SaveType
from src.rules_engine.multiclass import ClassLevel, MulticlassRecord


# ---------------------------------------------------------------------------
# E-010 — Prestige Class Base Schema
# ---------------------------------------------------------------------------

class CasterLevelMode(Enum):
    """How a prestige class advances spellcasting."""
    Full = auto()      # gains caster level every level (Archmage, Loremaster)
    Partial = auto()   # gains caster level on most but not first level (Eldritch Knight)
    None_ = auto()     # no spellcasting advancement (Dwarven Defender, Duelist)


# ---------------------------------------------------------------------------
# E-011 — Prerequisite Clause Schema
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class PrerequisiteClause:
    """Base class for prerequisite clauses."""
    description: str = ""


@dataclass
class BABRequirement(PrerequisiteClause):
    min_bab: int = 0


@dataclass
class SkillRankRequirement(PrerequisiteClause):
    skill: str = ""
    min_ranks: int = 0


@dataclass
class FeatRequirement(PrerequisiteClause):
    feat_name: str = ""


@dataclass
class AlignmentRequirement(PrerequisiteClause):
    allowed: tuple = ()


@dataclass
class ClassFeatureRequirement(PrerequisiteClause):
    feature_name: str = ""


@dataclass
class RaceRequirement(PrerequisiteClause):
    race: str = ""


@dataclass
class SpellcastingRequirement(PrerequisiteClause):
    min_arcane_level: Optional[int] = None
    min_divine_level: Optional[int] = None


@dataclass
class AbilityScoreRequirement(PrerequisiteClause):
    ability: str = ""
    minimum: int = 0


# ---------------------------------------------------------------------------
# E-010 (continued) — PrestigeClassBase dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class PrestigeClassBase:
    name: str
    hit_die: int
    bab_progression: BABProgression
    good_saves: tuple[SaveType, ...]
    skill_points_per_level: int
    class_skills: tuple[str, ...]
    prerequisites: list
    caster_level_progression: CasterLevelMode
    max_class_level: int = 10


# ---------------------------------------------------------------------------
# E-027 — Prerequisite Verification Engine
# ---------------------------------------------------------------------------

@dataclass
class PrerequisiteResult:
    met: bool
    failed_clauses: list[PrerequisiteClause]
    summary: str


def _check_clause(character, clause: PrerequisiteClause) -> bool:
    """Return True if the character meets this single prerequisite clause."""

    if isinstance(clause, BABRequirement):
        bab = getattr(character, "base_attack_bonus", 0)
        return bab >= clause.min_bab

    if isinstance(clause, SkillRankRequirement):
        skills = getattr(character, "skills", {})
        ranks = skills.get(clause.skill, 0)
        return ranks >= clause.min_ranks

    if isinstance(clause, FeatRequirement):
        feats = getattr(character, "feats", [])
        return clause.feat_name in feats

    if isinstance(clause, AlignmentRequirement):
        alignment = getattr(character, "alignment", None)
        if alignment is None:
            return False
        alignment_val = alignment.value if hasattr(alignment, "value") else str(alignment)
        allowed_vals = {
            (a.value if hasattr(a, "value") else str(a)) for a in clause.allowed
        }
        return alignment_val in allowed_vals

    if isinstance(clause, ClassFeatureRequirement):
        metadata = getattr(character, "metadata", {})
        features = metadata.get("class_features", [])
        return clause.feature_name in features

    if isinstance(clause, RaceRequirement):
        race = getattr(character, "race", "")
        allowed_races = [r.strip() for r in clause.race.split("/")]
        return race in allowed_races

    if isinstance(clause, SpellcastingRequirement):
        metadata = getattr(character, "metadata", {})
        if clause.min_arcane_level is not None:
            arcane = metadata.get("arcane_caster_level", 0)
            if arcane < clause.min_arcane_level:
                return False
        if clause.min_divine_level is not None:
            divine = metadata.get("divine_caster_level", 0)
            if divine < clause.min_divine_level:
                return False
        return True

    if isinstance(clause, AbilityScoreRequirement):
        score = getattr(character, clause.ability, 0)
        return score >= clause.minimum

    return True


def verify_prerequisites(character, prestige_class: PrestigeClassBase) -> PrerequisiteResult:
    """Iterates prerequisites, checks each against character.

    Returns PrerequisiteResult with met=True if all clauses pass.
    """
    failed: list[PrerequisiteClause] = []
    for clause in prestige_class.prerequisites:
        if not _check_clause(character, clause):
            failed.append(clause)

    met = len(failed) == 0
    if met:
        summary = f"All prerequisites met for {prestige_class.name}."
    else:
        descs = [c.description or repr(c) for c in failed]
        summary = f"Failed {len(failed)} prerequisite(s) for {prestige_class.name}: {'; '.join(descs)}"

    return PrerequisiteResult(met=met, failed_clauses=failed, summary=summary)


# ---------------------------------------------------------------------------
# E-041 — DMG Prestige Class Registry (all 16 classes)
# ---------------------------------------------------------------------------

PRESTIGE_CLASS_REGISTRY: dict[str, PrestigeClassBase] = {

    "Arcane Archer": PrestigeClassBase(
        name="Arcane Archer",
        hit_die=8,
        bab_progression=BABProgression.Full,
        good_saves=(SaveType.Fort, SaveType.Ref),
        skill_points_per_level=4,
        class_skills=("Hide", "Listen", "Move Silently", "Ride", "Spot", "Survival", "Use Rope"),
        prerequisites=[
            RaceRequirement(race="Elf/Half-Elf", description="Must be an elf or half-elf"),
            BABRequirement(min_bab=6, description="BAB +6"),
            FeatRequirement(feat_name="Point Blank Shot", description="Point Blank Shot feat"),
            FeatRequirement(feat_name="Precise Shot", description="Precise Shot feat"),
            SpellcastingRequirement(min_arcane_level=1, description="Able to cast 1st-level arcane spells"),
        ],
        caster_level_progression=CasterLevelMode.None_,
        max_class_level=10,
    ),

    "Arcane Trickster": PrestigeClassBase(
        name="Arcane Trickster",
        hit_die=4,
        bab_progression=BABProgression.Half,
        good_saves=(SaveType.Ref, SaveType.Will),
        skill_points_per_level=4,
        class_skills=(
            "Appraise", "Balance", "Bluff", "Climb", "Craft", "Decipher Script",
            "Disable Device", "Disguise", "Escape Artist", "Gather Information",
            "Hide", "Jump", "Knowledge (arcana)", "Listen", "Move Silently",
            "Open Lock", "Profession", "Search", "Sense Motive", "Sleight of Hand",
            "Speak Language", "Spot", "Swim", "Tumble", "Use Rope",
        ),
        prerequisites=[
            AlignmentRequirement(
                allowed=("CG", "CN", "CE", "NG", "NE", "N"),
                description="Non-Lawful Good alignment",
            ),
            SpellcastingRequirement(min_arcane_level=3, description="Able to cast 3rd-level arcane spells"),
            ClassFeatureRequirement(feature_name="Sneak Attack +2d6", description="Sneak Attack +2d6"),
            SkillRankRequirement(skill="Disable Device", min_ranks=7, description="Disable Device 7 ranks"),
            SkillRankRequirement(skill="Escape Artist", min_ranks=7, description="Escape Artist 7 ranks"),
        ],
        caster_level_progression=CasterLevelMode.Full,
        max_class_level=10,
    ),

    "Archmage": PrestigeClassBase(
        name="Archmage",
        hit_die=4,
        bab_progression=BABProgression.Half,
        good_saves=(SaveType.Will,),
        skill_points_per_level=2,
        class_skills=("Concentration", "Craft", "Knowledge (arcana)", "Knowledge (history)",
                       "Knowledge (planes)", "Profession", "Search", "Spellcraft"),
        prerequisites=[
            SpellcastingRequirement(min_arcane_level=7, description="Able to cast 7th-level arcane spells"),
            FeatRequirement(feat_name="Skill Focus (Spellcraft)", description="Skill Focus (Spellcraft) feat"),
            SkillRankRequirement(skill="Spellcraft", min_ranks=15, description="Spellcraft 15 ranks"),
            ClassFeatureRequirement(
                feature_name="Arcane school 5th-level spells",
                description="Ability to cast 5th-level spells from two different arcane schools",
            ),
        ],
        caster_level_progression=CasterLevelMode.Full,
        max_class_level=5,
    ),

    "Assassin": PrestigeClassBase(
        name="Assassin",
        hit_die=6,
        bab_progression=BABProgression.ThreeQuarters,
        good_saves=(SaveType.Ref,),
        skill_points_per_level=4,
        class_skills=(
            "Balance", "Bluff", "Climb", "Craft", "Decipher Script", "Disable Device",
            "Disguise", "Escape Artist", "Forgery", "Gather Information", "Hide",
            "Intimidate", "Jump", "Listen", "Move Silently", "Open Lock", "Search",
            "Sense Motive", "Sleight of Hand", "Spot", "Swim", "Tumble", "Use Magic Device",
            "Use Rope",
        ),
        prerequisites=[
            AlignmentRequirement(
                allowed=("LE", "NE", "CE", "LN", "CN", "N"),
                description="Non-Good alignment",
            ),
            SkillRankRequirement(skill="Hide", min_ranks=8, description="Hide 8 ranks"),
            SkillRankRequirement(skill="Move Silently", min_ranks=8, description="Move Silently 8 ranks"),
        ],
        caster_level_progression=CasterLevelMode.None_,
        max_class_level=10,
    ),

    "Blackguard": PrestigeClassBase(
        name="Blackguard",
        hit_die=10,
        bab_progression=BABProgression.Full,
        good_saves=(SaveType.Fort,),
        skill_points_per_level=2,
        class_skills=("Concentration", "Craft", "Diplomacy", "Handle Animal",
                       "Heal", "Hide", "Intimidate", "Knowledge (religion)", "Profession", "Ride"),
        prerequisites=[
            AlignmentRequirement(
                allowed=("LE", "NE", "CE"),
                description="Evil alignment",
            ),
            BABRequirement(min_bab=6, description="BAB +6"),
            FeatRequirement(feat_name="Cleave", description="Cleave feat"),
            FeatRequirement(feat_name="Power Attack", description="Power Attack feat"),
            SkillRankRequirement(skill="Hide", min_ranks=5, description="Hide 5 ranks"),
        ],
        caster_level_progression=CasterLevelMode.None_,
        max_class_level=10,
    ),

    "Dragon Disciple": PrestigeClassBase(
        name="Dragon Disciple",
        hit_die=8,
        bab_progression=BABProgression.ThreeQuarters,
        good_saves=(SaveType.Fort, SaveType.Will),
        skill_points_per_level=2,
        class_skills=("Concentration", "Craft", "Diplomacy", "Escape Artist",
                       "Gather Information", "Knowledge (arcana)", "Listen", "Profession",
                       "Search", "Speak Language", "Spellcraft", "Spot"),
        prerequisites=[
            AlignmentRequirement(
                allowed=("CG", "CN", "CE", "NG", "NE", "N"),
                description="Non-Lawful alignment",
            ),
            SpellcastingRequirement(min_arcane_level=1, description="Able to cast arcane spells (no preparation)"),
        ],
        caster_level_progression=CasterLevelMode.Partial,
        max_class_level=10,
    ),

    "Duelist": PrestigeClassBase(
        name="Duelist",
        hit_die=10,
        bab_progression=BABProgression.Full,
        good_saves=(SaveType.Ref,),
        skill_points_per_level=4,
        class_skills=("Balance", "Bluff", "Escape Artist", "Jump", "Listen",
                       "Perform", "Sense Motive", "Spot", "Tumble"),
        prerequisites=[
            BABRequirement(min_bab=6, description="BAB +6"),
            FeatRequirement(feat_name="Dodge", description="Dodge feat"),
            FeatRequirement(feat_name="Mobility", description="Mobility feat"),
            SkillRankRequirement(skill="Tumble", min_ranks=5, description="Tumble 5 ranks"),
            AbilityScoreRequirement(ability="intelligence", minimum=13, description="Intelligence 13+"),
        ],
        caster_level_progression=CasterLevelMode.None_,
        max_class_level=10,
    ),

    "Dwarven Defender": PrestigeClassBase(
        name="Dwarven Defender",
        hit_die=12,
        bab_progression=BABProgression.Full,
        good_saves=(SaveType.Fort,),
        skill_points_per_level=2,
        class_skills=("Craft", "Listen", "Sense Motive", "Spot"),
        prerequisites=[
            RaceRequirement(race="Dwarf", description="Must be a dwarf"),
            BABRequirement(min_bab=7, description="BAB +7"),
            FeatRequirement(feat_name="Toughness", description="Toughness feat"),
            FeatRequirement(feat_name="Dodge", description="Dodge or Mobility or Combat Reflexes"),
        ],
        caster_level_progression=CasterLevelMode.None_,
        max_class_level=10,
    ),

    "Eldritch Knight": PrestigeClassBase(
        name="Eldritch Knight",
        hit_die=6,
        bab_progression=BABProgression.Full,
        good_saves=(SaveType.Fort,),
        skill_points_per_level=2,
        class_skills=("Concentration", "Craft", "Decipher Script", "Jump",
                       "Knowledge (arcana)", "Knowledge (nobility and royalty)",
                       "Ride", "Sense Motive", "Spellcraft", "Swim"),
        prerequisites=[
            SpellcastingRequirement(min_arcane_level=3, description="Able to cast 3rd-level arcane spells"),
            BABRequirement(min_bab=3, description="BAB +3 (proficiency with all martial weapons)"),
            ClassFeatureRequirement(
                feature_name="Martial Weapon Proficiency",
                description="Proficiency with all martial weapons",
            ),
        ],
        caster_level_progression=CasterLevelMode.Partial,
        max_class_level=10,
    ),

    "Hierophant": PrestigeClassBase(
        name="Hierophant",
        hit_die=8,
        bab_progression=BABProgression.ThreeQuarters,
        good_saves=(SaveType.Fort, SaveType.Ref, SaveType.Will),
        skill_points_per_level=2,
        class_skills=("Concentration", "Craft", "Diplomacy", "Heal",
                       "Knowledge (arcana)", "Knowledge (history)", "Knowledge (religion)",
                       "Knowledge (planes)", "Profession", "Spellcraft"),
        prerequisites=[
            SpellcastingRequirement(min_divine_level=7, description="Able to cast 7th-level divine spells"),
            SkillRankRequirement(skill="Spellcraft", min_ranks=15, description="Spellcraft 15 ranks"),
        ],
        caster_level_progression=CasterLevelMode.Full,
        max_class_level=5,
    ),

    "Horizon Walker": PrestigeClassBase(
        name="Horizon Walker",
        hit_die=8,
        bab_progression=BABProgression.Full,
        good_saves=(SaveType.Fort,),
        skill_points_per_level=4,
        class_skills=("Balance", "Climb", "Diplomacy", "Handle Animal",
                       "Hide", "Jump", "Knowledge (geography)", "Listen",
                       "Move Silently", "Profession", "Ride", "Speak Language",
                       "Spot", "Survival", "Swim", "Use Rope"),
        prerequisites=[
            BABRequirement(min_bab=4, description="BAB +4"),
            SkillRankRequirement(
                skill="Knowledge (geography)", min_ranks=8, description="Knowledge (geography) 8 ranks"
            ),
        ],
        caster_level_progression=CasterLevelMode.None_,
        max_class_level=10,
    ),

    "Loremaster": PrestigeClassBase(
        name="Loremaster",
        hit_die=4,
        bab_progression=BABProgression.Half,
        good_saves=(SaveType.Will,),
        skill_points_per_level=4,
        class_skills=("Appraise", "Concentration", "Craft", "Decipher Script",
                       "Gather Information", "Handle Animal", "Heal",
                       "Knowledge (all)", "Perform", "Profession", "Search",
                       "Speak Language", "Spellcraft", "Use Magic Device"),
        prerequisites=[
            SpellcastingRequirement(min_arcane_level=7, description="Able to cast 7th-level arcane spells"),
            ClassFeatureRequirement(
                feature_name="Metamagic feat",
                description="Any metamagic feat",
            ),
            ClassFeatureRequirement(
                feature_name="Item creation feat",
                description="Any item creation feat",
            ),
            SkillRankRequirement(skill="Spellcraft", min_ranks=10, description="Spellcraft 10 ranks"),
            SkillRankRequirement(
                skill="Knowledge (any)", min_ranks=10, description="Knowledge (any) 10 ranks"
            ),
        ],
        caster_level_progression=CasterLevelMode.Full,
        max_class_level=10,
    ),

    "Mystic Theurge": PrestigeClassBase(
        name="Mystic Theurge",
        hit_die=4,
        bab_progression=BABProgression.Half,
        good_saves=(SaveType.Will,),
        skill_points_per_level=2,
        class_skills=("Concentration", "Craft", "Knowledge (arcana)",
                       "Knowledge (religion)", "Profession", "Sense Motive", "Spellcraft"),
        prerequisites=[
            SpellcastingRequirement(min_arcane_level=2, description="Able to cast 2nd-level arcane spells"),
            SpellcastingRequirement(min_divine_level=2, description="Able to cast 2nd-level divine spells"),
            SkillRankRequirement(skill="Spellcraft", min_ranks=6, description="Spellcraft 6 ranks"),
            SkillRankRequirement(
                skill="Knowledge (arcana)", min_ranks=6, description="Knowledge (arcana) 6 ranks"
            ),
        ],
        caster_level_progression=CasterLevelMode.Full,
        max_class_level=10,
    ),

    "Red Wizard": PrestigeClassBase(
        name="Red Wizard",
        hit_die=4,
        bab_progression=BABProgression.Half,
        good_saves=(SaveType.Will,),
        skill_points_per_level=2,
        class_skills=("Concentration", "Craft", "Knowledge (arcana)", "Profession", "Spellcraft"),
        prerequisites=[
            RaceRequirement(race="Human", description="Must be human"),
            ClassFeatureRequirement(feature_name="Wizard", description="Wizard class levels"),
            ClassFeatureRequirement(
                feature_name="Spell school specialization",
                description="Specialization in a chosen school of magic",
            ),
            ClassFeatureRequirement(
                feature_name="Metamagic feat 1",
                description="Any three metamagic feats",
            ),
            SkillRankRequirement(skill="Spellcraft", min_ranks=7, description="Spellcraft 7 ranks"),
        ],
        caster_level_progression=CasterLevelMode.Full,
        max_class_level=10,
    ),

    "Shadowdancer": PrestigeClassBase(
        name="Shadowdancer",
        hit_die=8,
        bab_progression=BABProgression.ThreeQuarters,
        good_saves=(SaveType.Ref,),
        skill_points_per_level=6,
        class_skills=("Balance", "Bluff", "Decipher Script", "Diplomacy",
                       "Disguise", "Escape Artist", "Hide", "Jump",
                       "Listen", "Move Silently", "Perform", "Search",
                       "Sleight of Hand", "Spot", "Tumble", "Use Rope"),
        prerequisites=[
            SkillRankRequirement(skill="Hide", min_ranks=10, description="Hide 10 ranks"),
            SkillRankRequirement(skill="Move Silently", min_ranks=8, description="Move Silently 8 ranks"),
            SkillRankRequirement(skill="Perform", min_ranks=5, description="Perform (Dance) 5 ranks"),
            FeatRequirement(feat_name="Dodge", description="Dodge feat"),
            FeatRequirement(feat_name="Mobility", description="Mobility feat"),
            FeatRequirement(feat_name="Combat Reflexes", description="Combat Reflexes feat"),
        ],
        caster_level_progression=CasterLevelMode.None_,
        max_class_level=10,
    ),

    "Thaumaturgist": PrestigeClassBase(
        name="Thaumaturgist",
        hit_die=4,
        bab_progression=BABProgression.Half,
        good_saves=(SaveType.Will,),
        skill_points_per_level=2,
        class_skills=("Concentration", "Craft", "Diplomacy", "Knowledge (planes)",
                       "Knowledge (religion)", "Profession", "Sense Motive", "Spellcraft"),
        prerequisites=[
            SpellcastingRequirement(min_divine_level=3, description="Able to cast 3rd-level divine spells"),
            FeatRequirement(feat_name="Augment Summoning", description="Augment Summoning feat"),
        ],
        caster_level_progression=CasterLevelMode.Full,
        max_class_level=5,
    ),
}


# ---------------------------------------------------------------------------
# E-053 — Prestige Class Entry Validator + Progression
# ---------------------------------------------------------------------------

@dataclass
class PrestigeEntryResult:
    success: bool
    prestige_name: str
    prerequisite_result: PrerequisiteResult
    notes: list[str] = field(default_factory=list)


def attempt_prestige_entry(
    character,
    prestige_name: str,
    multiclass_record: MulticlassRecord,
) -> PrestigeEntryResult:
    """Chains verify_prerequisites() -> if success, registers ClassLevel in record.

    Prestige classes are XP-penalty exempt (is_prestige=True).
    Returns PrestigeEntryResult.
    """
    notes: list[str] = []

    if prestige_name not in PRESTIGE_CLASS_REGISTRY:
        prereq_result = PrerequisiteResult(
            met=False,
            failed_clauses=[],
            summary=f"'{prestige_name}' is not a recognised prestige class.",
        )
        return PrestigeEntryResult(
            success=False,
            prestige_name=prestige_name,
            prerequisite_result=prereq_result,
            notes=[f"Unknown prestige class: {prestige_name}"],
        )

    prestige_class = PRESTIGE_CLASS_REGISTRY[prestige_name]
    prereq_result = verify_prerequisites(character, prestige_class)

    if not prereq_result.met:
        return PrestigeEntryResult(
            success=False,
            prestige_name=prestige_name,
            prerequisite_result=prereq_result,
            notes=[prereq_result.summary],
        )

    # Check if character already has levels in this prestige class
    existing = next(
        (e for e in multiclass_record.entries if e.class_name == prestige_name), None
    )
    if existing is not None:
        notes.append(f"Already entered {prestige_name}; level incremented via advance_prestige().")
    else:
        multiclass_record.entries.append(
            ClassLevel(class_name=prestige_name, level=1, is_prestige=True)
        )
        notes.append(f"Entered prestige class {prestige_name} at level 1.")

    return PrestigeEntryResult(
        success=True,
        prestige_name=prestige_name,
        prerequisite_result=prereq_result,
        notes=notes,
    )


def advance_prestige(multiclass_record: MulticlassRecord, prestige_name: str) -> None:
    """Increments prestige class level in record up to max_class_level.

    Raises ValueError if prestige_name not in PRESTIGE_CLASS_REGISTRY or at max level.
    """
    if prestige_name not in PRESTIGE_CLASS_REGISTRY:
        raise ValueError(f"'{prestige_name}' is not a recognised prestige class.")

    prestige_class = PRESTIGE_CLASS_REGISTRY[prestige_name]
    entry = next(
        (e for e in multiclass_record.entries if e.class_name == prestige_name), None
    )

    if entry is None:
        raise ValueError(
            f"Character has no levels in '{prestige_name}'. "
            "Call attempt_prestige_entry() first."
        )

    if entry.level >= prestige_class.max_class_level:
        raise ValueError(
            f"'{prestige_name}' is already at maximum level ({prestige_class.max_class_level})."
        )

    # ClassLevel is a slots dataclass; mutate via object.__setattr__
    object.__setattr__(entry, "level", entry.level + 1)


# ---------------------------------------------------------------------------
# E-059 — Prestige Class Caster-Level Continuation
# ---------------------------------------------------------------------------

def apply_prestige_caster_continuation(
    multiclass_record: MulticlassRecord,
    prestige_class: PrestigeClassBase,
    prestige_level_gained: int,
    caster_metadata: dict,
) -> dict:
    """Advance caster level based on the prestige class's CasterLevelMode.

    For Full progression: increment each level.
    For Partial: increment on all levels except the 1st.
    For None_: no change.

    caster_metadata keys: "arcane_caster_level", "divine_caster_level".
    Returns updated caster_metadata (a copy is NOT made; mutates and returns).
    """
    mode = prestige_class.caster_level_progression

    if mode == CasterLevelMode.None_:
        return caster_metadata

    should_advance = mode == CasterLevelMode.Full or (
        mode == CasterLevelMode.Partial and prestige_level_gained > 1
    )

    if not should_advance:
        return caster_metadata

    # Determine which pool to advance based on which key is non-zero (arcane takes priority).
    arcane = caster_metadata.get("arcane_caster_level", 0)
    divine = caster_metadata.get("divine_caster_level", 0)

    if arcane > 0 or divine == 0:
        caster_metadata["arcane_caster_level"] = arcane + 1
    else:
        caster_metadata["divine_caster_level"] = divine + 1

    return caster_metadata
