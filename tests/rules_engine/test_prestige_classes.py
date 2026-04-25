"""
tests/rules_engine/test_prestige_classes.py
---------------------------------------------
Tests for the prestige classes subsystem (E-010, E-011, E-027, E-041, E-053, E-059).
"""

from __future__ import annotations

import pytest

from src.rules_engine.character_35e import Alignment, Character35e
from src.rules_engine.multiclass import ClassLevel, MulticlassRecord
from src.rules_engine.npc_classes import BABProgression, SaveType
from src.rules_engine.prestige_classes import (
    # E-010
    CasterLevelMode,
    PrestigeClassBase,
    # E-011
    AbilityScoreRequirement,
    AlignmentRequirement,
    BABRequirement,
    ClassFeatureRequirement,
    FeatRequirement,
    PrerequisiteClause,
    RaceRequirement,
    SkillRankRequirement,
    SpellcastingRequirement,
    # E-027
    PrerequisiteResult,
    verify_prerequisites,
    # E-041
    PRESTIGE_CLASS_REGISTRY,
    # E-053
    PrestigeEntryResult,
    advance_prestige,
    attempt_prestige_entry,
    # E-059
    apply_prestige_caster_continuation,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_multiclass_record() -> MulticlassRecord:
    return MulticlassRecord(entries=[], favored_class=None, total_xp=0)


def _character(**kwargs) -> Character35e:
    """Build a minimal Character35e with sane defaults overridden by kwargs."""
    defaults = dict(
        name="Test Character",
        char_class="Fighter",
        level=10,
        race="Human",
        alignment=Alignment.TRUE_NEUTRAL,
        strength=10,
        dexterity=10,
        constitution=10,
        intelligence=10,
        wisdom=10,
        charisma=10,
        feats=[],
        skills={},
        metadata={},
    )
    defaults.update(kwargs)
    return Character35e(**defaults)


# ---------------------------------------------------------------------------
# E-010 — PrestigeClassBase / CasterLevelMode
# ---------------------------------------------------------------------------

class TestPrestigeClassBaseSchema:
    def test_caster_level_mode_values(self):
        assert CasterLevelMode.Full
        assert CasterLevelMode.Partial
        assert CasterLevelMode.None_

    def test_all_16_classes_in_registry(self):
        expected = {
            "Arcane Archer", "Arcane Trickster", "Archmage", "Assassin",
            "Blackguard", "Dragon Disciple", "Duelist", "Dwarven Defender",
            "Eldritch Knight", "Hierophant", "Horizon Walker", "Loremaster",
            "Mystic Theurge", "Red Wizard", "Shadowdancer", "Thaumaturgist",
        }
        assert expected == set(PRESTIGE_CLASS_REGISTRY.keys())

    def test_prestige_class_base_fields(self):
        pc = PRESTIGE_CLASS_REGISTRY["Assassin"]
        assert isinstance(pc, PrestigeClassBase)
        assert isinstance(pc.hit_die, int)
        assert isinstance(pc.bab_progression, BABProgression)
        assert isinstance(pc.good_saves, tuple)
        assert all(isinstance(s, SaveType) for s in pc.good_saves)
        assert isinstance(pc.skill_points_per_level, int)
        assert isinstance(pc.class_skills, tuple)
        assert isinstance(pc.prerequisites, list)
        assert isinstance(pc.caster_level_progression, CasterLevelMode)
        assert isinstance(pc.max_class_level, int)

    def test_max_class_level_defaults(self):
        # Most classes cap at 10
        assert PRESTIGE_CLASS_REGISTRY["Assassin"].max_class_level == 10
        # Some cap at 5
        assert PRESTIGE_CLASS_REGISTRY["Archmage"].max_class_level == 5
        assert PRESTIGE_CLASS_REGISTRY["Hierophant"].max_class_level == 5
        assert PRESTIGE_CLASS_REGISTRY["Thaumaturgist"].max_class_level == 5


# ---------------------------------------------------------------------------
# E-011 — Prerequisite Clause Types
# ---------------------------------------------------------------------------

class TestPrerequisiteClauseTypes:
    def test_base_clause(self):
        c = PrerequisiteClause(description="test")
        assert c.description == "test"

    def test_bab_requirement(self):
        c = BABRequirement(min_bab=6, description="BAB +6")
        assert isinstance(c, PrerequisiteClause)
        assert c.min_bab == 6

    def test_skill_rank_requirement(self):
        c = SkillRankRequirement(skill="Hide", min_ranks=10, description="Hide 10")
        assert c.skill == "Hide"
        assert c.min_ranks == 10

    def test_feat_requirement(self):
        c = FeatRequirement(feat_name="Dodge", description="Dodge")
        assert c.feat_name == "Dodge"

    def test_alignment_requirement(self):
        c = AlignmentRequirement(allowed=("LE", "NE", "CE"), description="Evil")
        assert "LE" in c.allowed

    def test_class_feature_requirement(self):
        c = ClassFeatureRequirement(feature_name="Sneak Attack +2d6")
        assert c.feature_name == "Sneak Attack +2d6"

    def test_race_requirement(self):
        c = RaceRequirement(race="Elf/Half-Elf", description="Elf or half-elf")
        assert c.race == "Elf/Half-Elf"

    def test_spellcasting_requirement(self):
        c = SpellcastingRequirement(min_arcane_level=3)
        assert c.min_arcane_level == 3
        assert c.min_divine_level is None

    def test_ability_score_requirement(self):
        c = AbilityScoreRequirement(ability="intelligence", minimum=13)
        assert c.ability == "intelligence"
        assert c.minimum == 13


# ---------------------------------------------------------------------------
# E-027 — verify_prerequisites
# ---------------------------------------------------------------------------

class TestVerifyPrerequisites:
    def _shadowdancer_char(self) -> Character35e:
        return _character(
            feats=["Dodge", "Mobility", "Combat Reflexes"],
            skills={"Hide": 10, "Move Silently": 8, "Perform": 5},
        )

    def test_all_met(self):
        char = self._shadowdancer_char()
        result = verify_prerequisites(char, PRESTIGE_CLASS_REGISTRY["Shadowdancer"])
        assert result.met is True
        assert result.failed_clauses == []

    def test_failure_missing_feat(self):
        char = _character(
            feats=["Dodge", "Mobility"],  # Missing Combat Reflexes
            skills={"Hide": 10, "Move Silently": 8, "Perform": 5},
        )
        result = verify_prerequisites(char, PRESTIGE_CLASS_REGISTRY["Shadowdancer"])
        assert result.met is False
        feat_names = [
            c.feat_name for c in result.failed_clauses if isinstance(c, FeatRequirement)
        ]
        assert "Combat Reflexes" in feat_names

    def test_failure_insufficient_skill(self):
        char = _character(
            feats=["Dodge", "Mobility", "Combat Reflexes"],
            skills={"Hide": 5, "Move Silently": 8, "Perform": 5},  # Hide too low
        )
        result = verify_prerequisites(char, PRESTIGE_CLASS_REGISTRY["Shadowdancer"])
        assert result.met is False

    def test_bab_check_pass(self):
        # Horizon Walker needs BAB +4 — a level-10 fighter has BAB 10
        char = _character(char_class="Fighter", level=10)
        result = verify_prerequisites(char, PRESTIGE_CLASS_REGISTRY["Horizon Walker"])
        skill_fail = [c for c in result.failed_clauses if isinstance(c, SkillRankRequirement)]
        bab_fail = [c for c in result.failed_clauses if isinstance(c, BABRequirement)]
        assert bab_fail == []

    def test_alignment_check_fail(self):
        char = _character(
            alignment=Alignment.LAWFUL_GOOD,
            feats=["Cleave", "Power Attack"],
            skills={"Hide": 5},
        )
        result = verify_prerequisites(char, PRESTIGE_CLASS_REGISTRY["Blackguard"])
        align_fails = [c for c in result.failed_clauses if isinstance(c, AlignmentRequirement)]
        assert len(align_fails) == 1

    def test_spellcasting_check_pass(self):
        char = _character(
            metadata={"arcane_caster_level": 7},
            feats=["Skill Focus (Spellcraft)"],
            skills={"Spellcraft": 15},
        )
        result = verify_prerequisites(char, PRESTIGE_CLASS_REGISTRY["Archmage"])
        spell_fails = [c for c in result.failed_clauses if isinstance(c, SpellcastingRequirement)]
        assert spell_fails == []

    def test_spellcasting_check_fail(self):
        char = _character(metadata={})
        result = verify_prerequisites(char, PRESTIGE_CLASS_REGISTRY["Archmage"])
        spell_fails = [c for c in result.failed_clauses if isinstance(c, SpellcastingRequirement)]
        assert len(spell_fails) == 1

    def test_race_check_pass(self):
        char = _character(
            race="Dwarf",
            char_class="Fighter",
            level=10,
            feats=["Toughness", "Dodge"],
        )
        result = verify_prerequisites(char, PRESTIGE_CLASS_REGISTRY["Dwarven Defender"])
        race_fails = [c for c in result.failed_clauses if isinstance(c, RaceRequirement)]
        assert race_fails == []

    def test_race_check_fail(self):
        char = _character(
            race="Human",
            char_class="Fighter",
            level=10,
            feats=["Toughness", "Dodge"],
        )
        result = verify_prerequisites(char, PRESTIGE_CLASS_REGISTRY["Dwarven Defender"])
        race_fails = [c for c in result.failed_clauses if isinstance(c, RaceRequirement)]
        assert len(race_fails) == 1

    def test_ability_score_check(self):
        # Duelist requires Int 13
        char = _character(
            char_class="Fighter",
            level=10,
            intelligence=12,  # too low
            feats=["Dodge", "Mobility"],
            skills={"Tumble": 5},
        )
        result = verify_prerequisites(char, PRESTIGE_CLASS_REGISTRY["Duelist"])
        ability_fails = [c for c in result.failed_clauses if isinstance(c, AbilityScoreRequirement)]
        assert len(ability_fails) == 1

    def test_prerequisite_result_summary_on_failure(self):
        char = _character()
        result = verify_prerequisites(char, PRESTIGE_CLASS_REGISTRY["Shadowdancer"])
        assert "Shadowdancer" in result.summary
        assert result.met is False

    def test_prerequisite_result_summary_on_success(self):
        char = _character(
            feats=["Dodge", "Mobility", "Combat Reflexes"],
            skills={"Hide": 10, "Move Silently": 8, "Perform": 5},
        )
        result = verify_prerequisites(char, PRESTIGE_CLASS_REGISTRY["Shadowdancer"])
        assert result.met is True
        assert "Shadowdancer" in result.summary


# ---------------------------------------------------------------------------
# E-041 — Registry spot-checks
# ---------------------------------------------------------------------------

class TestPrestigeClassRegistry:
    def test_arcane_archer_prerequisites(self):
        pc = PRESTIGE_CLASS_REGISTRY["Arcane Archer"]
        feat_names = {c.feat_name for c in pc.prerequisites if isinstance(c, FeatRequirement)}
        assert "Point Blank Shot" in feat_names
        assert "Precise Shot" in feat_names
        bab_reqs = [c for c in pc.prerequisites if isinstance(c, BABRequirement)]
        assert bab_reqs and bab_reqs[0].min_bab == 6

    def test_assassin_hit_die(self):
        assert PRESTIGE_CLASS_REGISTRY["Assassin"].hit_die == 6

    def test_dwarven_defender_hit_die(self):
        assert PRESTIGE_CLASS_REGISTRY["Dwarven Defender"].hit_die == 12

    def test_loremaster_caster_full(self):
        assert PRESTIGE_CLASS_REGISTRY["Loremaster"].caster_level_progression == CasterLevelMode.Full

    def test_shadowdancer_caster_none(self):
        assert PRESTIGE_CLASS_REGISTRY["Shadowdancer"].caster_level_progression == CasterLevelMode.None_

    def test_eldritch_knight_caster_partial(self):
        assert PRESTIGE_CLASS_REGISTRY["Eldritch Knight"].caster_level_progression == CasterLevelMode.Partial

    def test_dragon_disciple_caster_partial(self):
        assert PRESTIGE_CLASS_REGISTRY["Dragon Disciple"].caster_level_progression == CasterLevelMode.Partial

    def test_mystic_theurge_needs_both_arcane_and_divine(self):
        pc = PRESTIGE_CLASS_REGISTRY["Mystic Theurge"]
        spell_reqs = [c for c in pc.prerequisites if isinstance(c, SpellcastingRequirement)]
        has_arcane = any(r.min_arcane_level is not None for r in spell_reqs)
        has_divine = any(r.min_divine_level is not None for r in spell_reqs)
        assert has_arcane and has_divine

    def test_blackguard_requires_evil_alignment(self):
        pc = PRESTIGE_CLASS_REGISTRY["Blackguard"]
        align_reqs = [c for c in pc.prerequisites if isinstance(c, AlignmentRequirement)]
        assert len(align_reqs) == 1
        assert "LE" in align_reqs[0].allowed or "CE" in align_reqs[0].allowed

    def test_red_wizard_requires_human(self):
        pc = PRESTIGE_CLASS_REGISTRY["Red Wizard"]
        race_reqs = [c for c in pc.prerequisites if isinstance(c, RaceRequirement)]
        assert any(r.race == "Human" for r in race_reqs)

    def test_thaumaturgist_requires_augment_summoning(self):
        pc = PRESTIGE_CLASS_REGISTRY["Thaumaturgist"]
        feat_names = {c.feat_name for c in pc.prerequisites if isinstance(c, FeatRequirement)}
        assert "Augment Summoning" in feat_names

    def test_horizon_walker_skill_requirement(self):
        pc = PRESTIGE_CLASS_REGISTRY["Horizon Walker"]
        skill_reqs = [c for c in pc.prerequisites if isinstance(c, SkillRankRequirement)]
        geo_req = next((r for r in skill_reqs if "geography" in r.skill.lower()), None)
        assert geo_req is not None
        assert geo_req.min_ranks == 8

    def test_duelist_requires_int_13(self):
        pc = PRESTIGE_CLASS_REGISTRY["Duelist"]
        ability_reqs = [c for c in pc.prerequisites if isinstance(c, AbilityScoreRequirement)]
        int_req = next((r for r in ability_reqs if r.ability == "intelligence"), None)
        assert int_req is not None
        assert int_req.minimum == 13


# ---------------------------------------------------------------------------
# E-053 — attempt_prestige_entry / advance_prestige
# ---------------------------------------------------------------------------

class TestPrestigeEntry:
    def _full_shadowdancer_char(self) -> Character35e:
        return _character(
            feats=["Dodge", "Mobility", "Combat Reflexes"],
            skills={"Hide": 10, "Move Silently": 8, "Perform": 5},
        )

    def test_successful_entry(self):
        char = self._full_shadowdancer_char()
        record = _make_multiclass_record()
        result = attempt_prestige_entry(char, "Shadowdancer", record)
        assert result.success is True
        assert result.prestige_name == "Shadowdancer"
        assert result.prerequisite_result.met is True
        assert any(e.class_name == "Shadowdancer" for e in record.entries)

    def test_entry_sets_is_prestige_flag(self):
        char = self._full_shadowdancer_char()
        record = _make_multiclass_record()
        attempt_prestige_entry(char, "Shadowdancer", record)
        entry = next(e for e in record.entries if e.class_name == "Shadowdancer")
        assert entry.is_prestige is True

    def test_entry_starts_at_level_1(self):
        char = self._full_shadowdancer_char()
        record = _make_multiclass_record()
        attempt_prestige_entry(char, "Shadowdancer", record)
        entry = next(e for e in record.entries if e.class_name == "Shadowdancer")
        assert entry.level == 1

    def test_failed_entry_does_not_modify_record(self):
        char = _character()  # no feats/skills
        record = _make_multiclass_record()
        result = attempt_prestige_entry(char, "Shadowdancer", record)
        assert result.success is False
        assert len(record.entries) == 0

    def test_unknown_prestige_class(self):
        char = _character()
        record = _make_multiclass_record()
        result = attempt_prestige_entry(char, "Nonexistent Class", record)
        assert result.success is False

    def test_advance_prestige_increments_level(self):
        char = self._full_shadowdancer_char()
        record = _make_multiclass_record()
        attempt_prestige_entry(char, "Shadowdancer", record)
        advance_prestige(record, "Shadowdancer")
        entry = next(e for e in record.entries if e.class_name == "Shadowdancer")
        assert entry.level == 2

    def test_advance_prestige_to_max(self):
        char = self._full_shadowdancer_char()
        record = _make_multiclass_record()
        attempt_prestige_entry(char, "Shadowdancer", record)
        for _ in range(9):  # advance from 1 to 10
            advance_prestige(record, "Shadowdancer")
        entry = next(e for e in record.entries if e.class_name == "Shadowdancer")
        assert entry.level == 10

    def test_advance_prestige_raises_at_max(self):
        char = self._full_shadowdancer_char()
        record = _make_multiclass_record()
        attempt_prestige_entry(char, "Shadowdancer", record)
        for _ in range(9):
            advance_prestige(record, "Shadowdancer")
        with pytest.raises(ValueError, match="maximum level"):
            advance_prestige(record, "Shadowdancer")

    def test_advance_prestige_raises_no_entry(self):
        record = _make_multiclass_record()
        with pytest.raises(ValueError):
            advance_prestige(record, "Shadowdancer")

    def test_advance_prestige_raises_unknown_class(self):
        record = _make_multiclass_record()
        with pytest.raises(ValueError):
            advance_prestige(record, "Bogus Class")

    def test_prestige_entry_result_fields(self):
        char = self._full_shadowdancer_char()
        record = _make_multiclass_record()
        result = attempt_prestige_entry(char, "Shadowdancer", record)
        assert isinstance(result, PrestigeEntryResult)
        assert isinstance(result.prerequisite_result, PrerequisiteResult)
        assert isinstance(result.notes, list)


# ---------------------------------------------------------------------------
# E-059 — apply_prestige_caster_continuation
# ---------------------------------------------------------------------------

class TestCasterContinuation:
    def test_full_progression_increments_arcane(self):
        pc = PRESTIGE_CLASS_REGISTRY["Loremaster"]
        meta = {"arcane_caster_level": 7, "divine_caster_level": 0}
        record = _make_multiclass_record()
        result = apply_prestige_caster_continuation(record, pc, 1, meta)
        assert result["arcane_caster_level"] == 8

    def test_full_progression_increments_divine(self):
        pc = PRESTIGE_CLASS_REGISTRY["Hierophant"]
        meta = {"arcane_caster_level": 0, "divine_caster_level": 7}
        record = _make_multiclass_record()
        result = apply_prestige_caster_continuation(record, pc, 1, meta)
        assert result["divine_caster_level"] == 8

    def test_none_progression_no_change(self):
        pc = PRESTIGE_CLASS_REGISTRY["Shadowdancer"]
        meta = {"arcane_caster_level": 5, "divine_caster_level": 5}
        record = _make_multiclass_record()
        result = apply_prestige_caster_continuation(record, pc, 1, meta)
        assert result["arcane_caster_level"] == 5
        assert result["divine_caster_level"] == 5

    def test_partial_progression_skips_first_level(self):
        pc = PRESTIGE_CLASS_REGISTRY["Eldritch Knight"]
        meta = {"arcane_caster_level": 3, "divine_caster_level": 0}
        record = _make_multiclass_record()
        result = apply_prestige_caster_continuation(record, pc, 1, meta)
        assert result["arcane_caster_level"] == 3  # no advance at level 1

    def test_partial_progression_advances_after_first(self):
        pc = PRESTIGE_CLASS_REGISTRY["Eldritch Knight"]
        meta = {"arcane_caster_level": 3, "divine_caster_level": 0}
        record = _make_multiclass_record()
        result = apply_prestige_caster_continuation(record, pc, 2, meta)
        assert result["arcane_caster_level"] == 4

    def test_returns_updated_dict(self):
        pc = PRESTIGE_CLASS_REGISTRY["Archmage"]
        meta = {"arcane_caster_level": 7}
        record = _make_multiclass_record()
        result = apply_prestige_caster_continuation(record, pc, 1, meta)
        assert result is meta  # same dict mutated and returned
