"""
tests/rules_engine/test_multiclass.py
--------------------------------------
Comprehensive tests for src.rules_engine.multiclass.

Covers:
    E-007 — ClassLevel / MulticlassRecord
    E-008 — FavoredClassPolicy / RaceFavoredClass
    E-024 — multiclass_xp_penalty_pct
    E-025 — favored_class_for
    E-039 — FAVORED_CLASS_REGISTRY
    E-051 — build_multiclass_stats / MulticlassStats
    E-058 — multiclass_caster_levels / combined_caster_level / CombineMode
    E-065 — level_up_standard / LevelUpReport
"""

import pytest

from src.rules_engine.multiclass import (
    ClassLevel,
    CombineMode,
    FavoredClassPolicy,
    FAVORED_CLASS_REGISTRY,
    LevelUpReport,
    MulticlassRecord,
    MulticlassStats,
    RaceFavoredClass,
    build_multiclass_stats,
    combined_caster_level,
    favored_class_for,
    level_up_standard,
    multiclass_caster_levels,
    multiclass_xp_penalty_pct,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _record(*pairs, favored=None, **kwargs):
    """Build a MulticlassRecord from (class_name, level) pairs."""
    entries = [ClassLevel(class_name=c, level=lv) for c, lv in pairs]
    return MulticlassRecord(entries=entries, favored_class=favored, **kwargs)


def _prestige_record(*pairs, prestige_pairs=(), favored=None):
    """Build a record mixing normal and prestige class entries."""
    entries = [ClassLevel(class_name=c, level=lv) for c, lv in pairs]
    entries += [ClassLevel(class_name=c, level=lv, is_prestige=True) for c, lv in prestige_pairs]
    return MulticlassRecord(entries=entries, favored_class=favored)


# ---------------------------------------------------------------------------
# E-007 — ClassLevel / MulticlassRecord
# ---------------------------------------------------------------------------

class TestClassLevel:
    def test_defaults(self):
        cl = ClassLevel(class_name="Fighter", level=3)
        assert cl.class_name == "Fighter"
        assert cl.level == 3
        assert cl.is_prestige is False

    def test_prestige_flag(self):
        cl = ClassLevel(class_name="Arcane Trickster", level=5, is_prestige=True)
        assert cl.is_prestige is True

    def test_slots(self):
        cl = ClassLevel(class_name="Rogue", level=1)
        with pytest.raises(AttributeError):
            cl.nonexistent = True  # type: ignore[attr-defined]


class TestMulticlassRecord:
    def test_basic_construction(self):
        r = _record(("Fighter", 4), ("Wizard", 2), favored="Fighter")
        assert len(r.entries) == 2
        assert r.favored_class == "Fighter"
        assert r.total_xp == 0
        assert r.current_xp_penalty_pct == 0.0

    def test_slots(self):
        r = _record(("Rogue", 3))
        with pytest.raises(AttributeError):
            r.nonexistent = True  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# E-008 — FavoredClassPolicy / RaceFavoredClass
# ---------------------------------------------------------------------------

class TestFavoredClassPolicy:
    def test_enum_members(self):
        assert FavoredClassPolicy.Fixed
        assert FavoredClassPolicy.HighestLevel
        assert FavoredClassPolicy.Any
        assert len(FavoredClassPolicy) == 3

    def test_race_favored_class_slots(self):
        rfc = RaceFavoredClass(
            race_name="Elf", policy=FavoredClassPolicy.Fixed, class_name="Wizard"
        )
        with pytest.raises(AttributeError):
            rfc.nonexistent = True  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# E-039 — FAVORED_CLASS_REGISTRY
# ---------------------------------------------------------------------------

class TestFavoredClassRegistry:
    def test_all_core_races_present(self):
        expected = {"Human", "Half-Elf", "Dwarf", "Elf", "Gnome", "Half-Orc", "Halfling"}
        assert set(FAVORED_CLASS_REGISTRY.keys()) == expected

    def test_fixed_entries(self):
        assert FAVORED_CLASS_REGISTRY["Dwarf"].class_name == "Fighter"
        assert FAVORED_CLASS_REGISTRY["Elf"].class_name == "Wizard"
        assert FAVORED_CLASS_REGISTRY["Gnome"].class_name == "Bard"
        assert FAVORED_CLASS_REGISTRY["Half-Orc"].class_name == "Barbarian"
        assert FAVORED_CLASS_REGISTRY["Halfling"].class_name == "Rogue"

    def test_highest_level_entries(self):
        assert FAVORED_CLASS_REGISTRY["Human"].policy == FavoredClassPolicy.HighestLevel
        assert FAVORED_CLASS_REGISTRY["Human"].class_name is None
        assert FAVORED_CLASS_REGISTRY["Half-Elf"].policy == FavoredClassPolicy.HighestLevel

    def test_fixed_policy_for_dwarf(self):
        assert FAVORED_CLASS_REGISTRY["Dwarf"].policy == FavoredClassPolicy.Fixed


# ---------------------------------------------------------------------------
# E-025 — favored_class_for
# ---------------------------------------------------------------------------

class TestFavoredClassFor:
    def test_fixed_race_returns_fixed_class(self):
        r = _record(("Fighter", 5), ("Wizard", 3))
        assert favored_class_for("Dwarf", r) == "Fighter"

    def test_highest_level_human(self):
        r = _record(("Rogue", 6), ("Fighter", 4))
        assert favored_class_for("Human", r) == "Rogue"

    def test_highest_level_half_elf(self):
        r = _record(("Wizard", 3), ("Cleric", 5))
        assert favored_class_for("Half-Elf", r) == "Cleric"

    def test_highest_level_tie_returns_first(self):
        r = _record(("Wizard", 4), ("Sorcerer", 4))
        # First listed wins on tie
        assert favored_class_for("Human", r) == "Wizard"

    def test_unknown_race_returns_none(self):
        r = _record(("Fighter", 5))
        assert favored_class_for("Tiefling", r) == None

    def test_highest_level_ignores_prestige(self):
        r = _prestige_record(("Wizard", 3), prestige_pairs=(("Arcane Trickster", 10),))
        # Arcane Trickster is prestige so should be ignored; Wizard is highest non-prestige
        assert favored_class_for("Human", r) == "Wizard"

    def test_empty_entries_returns_none(self):
        r = MulticlassRecord(entries=[], favored_class=None)
        assert favored_class_for("Human", r) == None


# ---------------------------------------------------------------------------
# E-024 — multiclass_xp_penalty_pct
# ---------------------------------------------------------------------------

class TestMulticlassXpPenalty:
    def test_single_class_no_penalty(self):
        r = _record(("Fighter", 5))
        assert multiclass_xp_penalty_pct(r, "Dwarf") == 0.0

    def test_two_classes_within_one_level_no_penalty(self):
        r = _record(("Fighter", 4), ("Wizard", 3))
        assert multiclass_xp_penalty_pct(r, "Human") == 0.0

    def test_two_classes_equal_level_no_penalty(self):
        r = _record(("Fighter", 4), ("Wizard", 4))
        assert multiclass_xp_penalty_pct(r, "Human") == 0.0

    def test_two_classes_differ_by_two_penalty(self):
        # Use Half-Orc (favored=Barbarian) so Fighter and Wizard both stay in check
        r = _record(("Fighter", 5), ("Wizard", 3))
        assert multiclass_xp_penalty_pct(r, "Half-Orc") == 20.0

    def test_favored_class_excluded_dwarf(self):
        # Dwarf favored = Fighter; Fighter 8, Rogue 5 → diff=3 but Fighter excluded
        r = _record(("Fighter", 8), ("Rogue", 5))
        # Only Rogue remains after excluding Fighter → ≤1 class → 0%
        assert multiclass_xp_penalty_pct(r, "Dwarf") == 0.0

    def test_favored_class_excluded_with_third_class(self):
        # Dwarf: Fighter excluded; Rogue 5, Cleric 3 → diff=2 → 20%
        r = _record(("Fighter", 8), ("Rogue", 5), ("Cleric", 3))
        assert multiclass_xp_penalty_pct(r, "Dwarf") == 20.0

    def test_prestige_class_excluded(self):
        # Prestige class levels are ignored
        r = _prestige_record(("Fighter", 6), ("Rogue", 5), prestige_pairs=(("Shadowdancer", 3),))
        # Fighter 6, Rogue 5 → diff=1 → no penalty for Human
        assert multiclass_xp_penalty_pct(r, "Human") == 0.0

    def test_prestige_only_no_penalty(self):
        r = _prestige_record(prestige_pairs=(("Shadowdancer", 5),))
        assert multiclass_xp_penalty_pct(r, "Human") == 0.0

    def test_human_highest_level_excluded(self):
        # Human: highest level class is favored; Rogue 7, Fighter 5, Wizard 4
        # Favored = Rogue (highest); remaining = Fighter 5, Wizard 4 → diff=1 → 0%
        r = _record(("Rogue", 7), ("Fighter", 5), ("Wizard", 4))
        assert multiclass_xp_penalty_pct(r, "Human") == 0.0

    def test_human_penalty_when_not_favored_differ(self):
        # Human: Rogue 7 is favored; Fighter 5, Wizard 2 → diff=3 → 20%
        r = _record(("Rogue", 7), ("Fighter", 5), ("Wizard", 2))
        assert multiclass_xp_penalty_pct(r, "Human") == 20.0

    def test_unknown_race_uses_no_favored(self):
        # Unknown race: no favored class excluded; Fighter 5, Rogue 3 → diff=2 → 20%
        r = _record(("Fighter", 5), ("Rogue", 3))
        assert multiclass_xp_penalty_pct(r, "Tiefling") == 20.0


# ---------------------------------------------------------------------------
# E-051 — build_multiclass_stats / MulticlassStats
# ---------------------------------------------------------------------------

class TestBuildMulticlassStats:
    def test_single_fighter_5(self):
        r = _record(("Fighter", 5))
        s = build_multiclass_stats(r)
        # Fighter: full BAB → 5
        assert s.total_bab == 5
        # Fort good: 2 + 5//2 = 4; Ref poor: 5//3=1; Will poor: 5//3=1
        assert s.fort_save == 4
        assert s.ref_save == 1
        assert s.will_save == 1
        # HD: 10 * 5 = 50
        assert s.total_hd == 50

    def test_single_wizard_4(self):
        r = _record(("Wizard", 4))
        s = build_multiclass_stats(r)
        # half BAB: 4//2=2
        assert s.total_bab == 2
        # Fort poor: 4//3=1; Ref poor: 4//3=1; Will good: 2+4//2=4
        assert s.fort_save == 1
        assert s.ref_save == 1
        assert s.will_save == 4

    def test_fighter_wizard_multiclass(self):
        # Fighter 4, Wizard 2 multiclass
        r = _record(("Fighter", 4), ("Wizard", 2))
        s = build_multiclass_stats(r)
        # BAB: fighter full(4)=4 + wizard half(2)=1 → 5
        assert s.total_bab == 5
        # Fort: fighter good first (2+4//2=4) + wizard poor (2//3=0) → 4
        assert s.fort_save == 4
        # Ref: fighter poor (4//3=1) + wizard poor (2//3=0) → 1
        assert s.ref_save == 1
        # Will: fighter poor (4//3=1) + wizard good first (2+2//2=3) → 4
        assert s.will_save == 4

    def test_good_save_no_double_bonus(self):
        # Two classes both with good Fort: Fighter and Cleric
        r = _record(("Fighter", 4), ("Cleric", 4))
        s = build_multiclass_stats(r)
        # Fighter fort (first): 2 + 4//2 = 4
        # Cleric fort (second, no +2): 4//2 = 2
        # Total fort = 6
        assert s.fort_save == 6
        # Will: Fighter poor (4//3=1) + Cleric good first? Fighter came first
        # Fighter has poor will → Cleric gets the +2 bonus
        # Will = 1 + (2 + 4//2) = 1 + 4 = 5
        assert s.will_save == 5

    def test_hp_pool_first_level_max(self):
        # Fighter 1: first level always max HD (10)
        r = _record(("Fighter", 1))
        s = build_multiclass_stats(r, con_modifier=0)
        assert s.hp_pool == 10

    def test_hp_pool_con_modifier(self):
        # Fighter 1 with CON+2: first level = 10+2=12
        r = _record(("Fighter", 1))
        s = build_multiclass_stats(r, con_modifier=2)
        assert s.hp_pool == 12

    def test_hp_pool_multiclass(self):
        # Fighter 2, Wizard 1 (Fighter first in list = primary)
        # Fighter lv1: max=10, lv2: avg (10+1)//2=5
        # Wizard lv1: avg (4+1)//2=2
        # Total: 10+5+2 = 17
        r = _record(("Fighter", 2), ("Wizard", 1))
        s = build_multiclass_stats(r, con_modifier=0)
        assert s.hp_pool == 17

    def test_total_hd_accumulates(self):
        r = _record(("Rogue", 3), ("Barbarian", 2))
        s = build_multiclass_stats(r)
        # Rogue hd=6, Barbarian hd=12
        assert s.total_hd == 6 * 3 + 12 * 2

    def test_stats_returns_multiclass_stats(self):
        r = _record(("Monk", 5))
        s = build_multiclass_stats(r)
        assert isinstance(s, MulticlassStats)

    def test_unknown_class_ignored(self):
        r = _record(("Fighter", 3), ("UnknownPrestige", 2))
        # Should not raise; unknown class is skipped
        s = build_multiclass_stats(r)
        assert s.total_bab == 3  # only Fighter contributes

    def test_ranger_bab_full(self):
        r = _record(("Ranger", 6))
        s = build_multiclass_stats(r)
        assert s.total_bab == 6

    def test_bard_three_quarters_bab(self):
        r = _record(("Bard", 8))
        s = build_multiclass_stats(r)
        assert s.total_bab == (8 * 3) // 4  # 6

    def test_sorcerer_half_bab(self):
        r = _record(("Sorcerer", 10))
        s = build_multiclass_stats(r)
        assert s.total_bab == 5

    def test_npc_warrior_stats(self):
        r = _record(("Warrior", 4))
        s = build_multiclass_stats(r)
        assert s.total_bab == 4
        assert s.fort_save == 2 + 4 // 2

    def test_three_class_multiclass(self):
        # Fighter 3 / Rogue 3 / Wizard 3
        r = _record(("Fighter", 3), ("Rogue", 3), ("Wizard", 3))
        s = build_multiclass_stats(r)
        # BAB: full(3)+3q(3)+half(3) = 3+2+1 = 6
        assert s.total_bab == 6


# ---------------------------------------------------------------------------
# E-058 — multiclass_caster_levels / combined_caster_level
# ---------------------------------------------------------------------------

class TestMulticlassCasterLevels:
    def test_wizard_only(self):
        entries = [ClassLevel("Wizard", 5)]
        assert multiclass_caster_levels(entries) == {"Wizard": 5}

    def test_non_caster_excluded(self):
        entries = [ClassLevel("Fighter", 5)]
        assert multiclass_caster_levels(entries) == {}

    def test_mixed_classes(self):
        entries = [ClassLevel("Fighter", 4), ClassLevel("Wizard", 3)]
        result = multiclass_caster_levels(entries)
        assert "Fighter" not in result
        assert result["Wizard"] == 3

    def test_paladin_starts_at_4(self):
        # Paladin level 3 → no spells yet
        assert multiclass_caster_levels([ClassLevel("Paladin", 3)]) == {}

    def test_paladin_level_4(self):
        # Paladin level 4 → CL = 4-3 = 1
        assert multiclass_caster_levels([ClassLevel("Paladin", 4)]) == {"Paladin": 1}

    def test_paladin_level_7(self):
        assert multiclass_caster_levels([ClassLevel("Paladin", 7)]) == {"Paladin": 4}

    def test_ranger_same_as_paladin(self):
        assert multiclass_caster_levels([ClassLevel("Ranger", 4)]) == {"Ranger": 1}
        assert multiclass_caster_levels([ClassLevel("Ranger", 3)]) == {}

    def test_bard_cleric_both_included(self):
        entries = [ClassLevel("Bard", 4), ClassLevel("Cleric", 3)]
        result = multiclass_caster_levels(entries)
        assert result == {"Bard": 4, "Cleric": 3}

    def test_adept_is_spellcaster(self):
        entries = [ClassLevel("Adept", 5)]
        assert multiclass_caster_levels(entries) == {"Adept": 5}

    def test_druid_included(self):
        entries = [ClassLevel("Druid", 6)]
        assert multiclass_caster_levels(entries) == {"Druid": 6}


class TestCombinedCasterLevel:
    def test_max_mode(self):
        entries = [ClassLevel("Wizard", 5), ClassLevel("Sorcerer", 3)]
        assert combined_caster_level(entries, CombineMode.Max) == 5

    def test_sum_mode(self):
        entries = [ClassLevel("Wizard", 5), ClassLevel("Sorcerer", 3)]
        assert combined_caster_level(entries, CombineMode.Sum) == 8

    def test_no_casters_returns_zero(self):
        entries = [ClassLevel("Fighter", 10), ClassLevel("Barbarian", 5)]
        assert combined_caster_level(entries) == 0

    def test_default_mode_is_max(self):
        entries = [ClassLevel("Cleric", 7), ClassLevel("Druid", 4)]
        assert combined_caster_level(entries) == 7

    def test_prestige_mode_returns_max(self):
        entries = [ClassLevel("Wizard", 5), ClassLevel("Bard", 3)]
        assert combined_caster_level(entries, CombineMode.Prestige) == 5

    def test_single_caster(self):
        entries = [ClassLevel("Sorcerer", 8)]
        assert combined_caster_level(entries) == 8


# ---------------------------------------------------------------------------
# E-065 — level_up_standard / LevelUpReport
# ---------------------------------------------------------------------------

class TestLevelUpStandard:
    def test_adds_new_class(self):
        r = _record(("Fighter", 3))
        report = level_up_standard(r, "Rogue", "Human")
        assert any(e.class_name == "Rogue" and e.level == 1 for e in r.entries)
        assert report.class_name == "Rogue"
        assert report.new_level == 1

    def test_increments_existing_class(self):
        r = _record(("Fighter", 3))
        level_up_standard(r, "Fighter", "Dwarf")
        fighter = next(e for e in r.entries if e.class_name == "Fighter")
        assert fighter.level == 4

    def test_returns_level_up_report(self):
        r = _record(("Wizard", 2))
        report = level_up_standard(r, "Wizard", "Elf")
        assert isinstance(report, LevelUpReport)

    def test_bab_delta_fighter(self):
        # Fighter goes from 3 to 4: full BAB → delta=1
        r = _record(("Fighter", 3))
        report = level_up_standard(r, "Fighter", "Dwarf")
        assert report.bab_delta == 1

    def test_xp_penalty_updated(self):
        # Dwarf: favored=Fighter; Fighter 4, Rogue 2 → diff=2 → 20%
        r = _record(("Fighter", 4), ("Rogue", 2))
        report = level_up_standard(r, "Rogue", "Dwarf")
        # After: Rogue 3, Fighter 4 → diff=1 → 0% (since 4-3=1 < 2)
        assert report.xp_penalty_pct == 0.0
        assert r.current_xp_penalty_pct == 0.0

    def test_xp_penalty_note(self):
        # Half-Orc: favored=Barbarian; Fighter 5, Rogue 3 → diff=2 → 20%
        r = _record(("Fighter", 5), ("Rogue", 3))
        report = level_up_standard(r, "Rogue", "Half-Orc")
        # Fighter 5, Rogue 4 → diff=1 → 0% … use Fighter level up instead
        # Use pre-existing diff of 2 by building Fighter 5 Rogue 3 and leveling Rogue
        # Actually: after level up Rogue 3→4: Fighter 5, Rogue 4 → diff=1 → 0%
        # Better: start Fighter 5, Rogue 2, level Rogue to 3 → diff=2 → 20%
        r2 = _record(("Fighter", 5), ("Rogue", 2))
        report2 = level_up_standard(r2, "Rogue", "Half-Orc")
        assert report2.xp_penalty_pct == 20.0
        assert any("20%" in n for n in report2.notes)

    def test_hp_gained_average_no_rng(self):
        # Rogue level 2: hd=6, avg=(6+1)//2=3
        r = _record(("Rogue", 1))
        report = level_up_standard(r, "Rogue", "Halfling", con_modifier=0)
        assert report.hp_gained == 3  # average rounding up

    def test_hp_gained_with_con_modifier(self):
        r = _record(("Fighter", 1))
        report = level_up_standard(r, "Fighter", "Dwarf", con_modifier=2)
        assert report.hp_gained == (10 + 1) // 2 + 2  # avg Fighter d10 + CON

    def test_hp_gained_with_rng(self):
        class FakeRng:
            def randint(self, a, b):
                return b  # always max

        r = _record(("Fighter", 1))
        report = level_up_standard(r, "Fighter", "Dwarf", rng=FakeRng())
        assert report.hp_gained == 10  # max d10

    def test_first_level_overall_max_hp(self):
        # Fresh character: single level, first level gets max HD
        r = MulticlassRecord(entries=[], favored_class=None)
        report = level_up_standard(r, "Barbarian", "Half-Orc", con_modifier=0)
        assert report.hp_gained == 12  # Barbarian d12 max

    def test_level_up_report_has_deltas(self):
        r = _record(("Cleric", 2))
        report = level_up_standard(r, "Cleric", "Human")
        # BAB delta: 3/4 prog: (3*3)//4 - (2*3)//4 = 2 - 1 = 1
        assert report.bab_delta >= 0
        assert report.fort_delta >= 0

    def test_record_penalty_stored(self):
        # Elf: favored=Wizard; Fighter 5, Rogue 2 → diff=3 → after Rogue→3: diff=2 → 20%
        r = _record(("Fighter", 5), ("Rogue", 2))
        level_up_standard(r, "Rogue", "Elf")
        assert r.current_xp_penalty_pct == 20.0

    def test_no_penalty_for_single_class(self):
        r = _record(("Paladin", 5))
        report = level_up_standard(r, "Paladin", "Human")
        assert report.xp_penalty_pct == 0.0
        assert report.notes == []
