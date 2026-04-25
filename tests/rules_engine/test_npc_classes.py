"""
tests/rules_engine/test_npc_classes.py
----------------------------------------
Comprehensive tests for the NPC classes subsystem (E-009, E-026, E-040, E-052).
"""

from __future__ import annotations

import math
import random
import pytest

from src.rules_engine.npc_classes import (
    BABProgression,
    NPCClassBase,
    NPCClassName,
    NPCProgression,
    NPCStats,
    NPC_CLASS_DISTRIBUTION_PCT,
    NPC_CLASS_REGISTRY,
    SaveType,
    generate_npc,
    npc_class_progression,
)


# ---------------------------------------------------------------------------
# E-009 — Schema integrity
# ---------------------------------------------------------------------------

class TestNPCClassBaseSchema:
    def test_all_npc_classes_in_registry(self):
        for member in NPCClassName:
            assert member in NPC_CLASS_REGISTRY

    def test_npc_class_base_fields(self):
        base = NPC_CLASS_REGISTRY[NPCClassName.Commoner]
        assert isinstance(base, NPCClassBase)
        assert isinstance(base.name, NPCClassName)
        assert isinstance(base.hit_die, int)
        assert isinstance(base.bab_progression, BABProgression)
        assert isinstance(base.good_saves, tuple)
        assert isinstance(base.skill_points_per_level, int)
        assert isinstance(base.class_skills, tuple)

    def test_bab_progression_values(self):
        assert BABProgression.Full.value == "full"
        assert BABProgression.ThreeQuarters.value == "3/4"
        assert BABProgression.Half.value == "1/2"

    def test_save_type_values(self):
        assert SaveType.Fort.value == "fort"
        assert SaveType.Ref.value == "ref"
        assert SaveType.Will.value == "will"


# ---------------------------------------------------------------------------
# E-040 — Registry correctness
# ---------------------------------------------------------------------------

class TestNPCClassRegistry:
    def test_commoner(self):
        c = NPC_CLASS_REGISTRY[NPCClassName.Commoner]
        assert c.hit_die == 4
        assert c.bab_progression == BABProgression.Half
        assert c.good_saves == ()
        assert c.skill_points_per_level == 2
        assert "Climb" in c.class_skills
        assert "Craft" in c.class_skills

    def test_expert(self):
        e = NPC_CLASS_REGISTRY[NPCClassName.Expert]
        assert e.hit_die == 6
        assert e.bab_progression == BABProgression.ThreeQuarters
        assert SaveType.Will in e.good_saves
        assert e.skill_points_per_level == 6
        assert "Appraise" in e.class_skills

    def test_warrior(self):
        w = NPC_CLASS_REGISTRY[NPCClassName.Warrior]
        assert w.hit_die == 8
        assert w.bab_progression == BABProgression.Full
        assert SaveType.Fort in w.good_saves
        assert w.skill_points_per_level == 2
        assert "Intimidate" in w.class_skills

    def test_adept(self):
        a = NPC_CLASS_REGISTRY[NPCClassName.Adept]
        assert a.hit_die == 6
        assert a.bab_progression == BABProgression.Half
        assert SaveType.Will in a.good_saves
        assert a.skill_points_per_level == 2
        assert "Spellcraft" in a.class_skills

    def test_aristocrat(self):
        ar = NPC_CLASS_REGISTRY[NPCClassName.Aristocrat]
        assert ar.hit_die == 8
        assert ar.bab_progression == BABProgression.ThreeQuarters
        assert SaveType.Will in ar.good_saves
        assert ar.skill_points_per_level == 4
        assert "Diplomacy" in ar.class_skills

    def test_distribution_sums_to_one(self):
        total = sum(NPC_CLASS_DISTRIBUTION_PCT.values())
        assert abs(total - 1.0) < 1e-9

    def test_distribution_covers_all_classes(self):
        for member in NPCClassName:
            assert member in NPC_CLASS_DISTRIBUTION_PCT

    def test_commoner_is_most_common(self):
        pct = NPC_CLASS_DISTRIBUTION_PCT
        assert pct[NPCClassName.Commoner] > max(
            v for k, v in pct.items() if k != NPCClassName.Commoner
        )


# ---------------------------------------------------------------------------
# E-026 — Progression formula
# ---------------------------------------------------------------------------

class TestNPCClassProgression:
    # BAB checks
    @pytest.mark.parametrize("level,expected_bab", [
        (1, 0), (2, 1), (4, 2), (6, 3), (10, 5),
    ])
    def test_commoner_bab_half(self, level, expected_bab):
        prog = npc_class_progression(NPCClassName.Commoner, level)
        assert prog.bab == expected_bab

    @pytest.mark.parametrize("level,expected_bab", [
        (1, 0), (2, 1), (4, 3), (8, 6), (12, 9),
    ])
    def test_expert_bab_three_quarters(self, level, expected_bab):
        prog = npc_class_progression(NPCClassName.Expert, level)
        assert prog.bab == expected_bab

    @pytest.mark.parametrize("level,expected_bab", [
        (1, 1), (2, 2), (5, 5), (10, 10),
    ])
    def test_warrior_bab_full(self, level, expected_bab):
        prog = npc_class_progression(NPCClassName.Warrior, level)
        assert prog.bab == expected_bab

    @pytest.mark.parametrize("level,expected_bab", [
        (1, 0), (4, 2), (8, 4),
    ])
    def test_adept_bab_half(self, level, expected_bab):
        prog = npc_class_progression(NPCClassName.Adept, level)
        assert prog.bab == expected_bab

    @pytest.mark.parametrize("level,expected_bab", [
        (1, 0), (4, 3), (8, 6),
    ])
    def test_aristocrat_bab_three_quarters(self, level, expected_bab):
        prog = npc_class_progression(NPCClassName.Aristocrat, level)
        assert prog.bab == expected_bab

    # Save checks — commoner all poor
    @pytest.mark.parametrize("level", [1, 4, 8, 12])
    def test_commoner_all_poor_saves(self, level):
        prog = npc_class_progression(NPCClassName.Commoner, level)
        assert prog.fort == level // 3
        assert prog.ref  == level // 3
        assert prog.will == level // 3

    # Save checks — warrior good Fort
    @pytest.mark.parametrize("level", [1, 4, 8])
    def test_warrior_good_fort_poor_others(self, level):
        prog = npc_class_progression(NPCClassName.Warrior, level)
        assert prog.fort == 2 + level // 2
        assert prog.ref  == level // 3
        assert prog.will == level // 3

    # Save checks — expert good Will
    @pytest.mark.parametrize("level", [1, 4, 8])
    def test_expert_good_will_poor_others(self, level):
        prog = npc_class_progression(NPCClassName.Expert, level)
        assert prog.fort == level // 3
        assert prog.ref  == level // 3
        assert prog.will == 2 + level // 2

    # Save checks — adept good Will
    def test_adept_good_will(self):
        prog = npc_class_progression(NPCClassName.Adept, 6)
        assert prog.will == 2 + 6 // 2  # 5
        assert prog.fort == 6 // 3       # 2

    # Save checks — aristocrat good Will
    def test_aristocrat_good_will(self):
        prog = npc_class_progression(NPCClassName.Aristocrat, 6)
        assert prog.will == 2 + 6 // 2  # 5
        assert prog.fort == 6 // 3       # 2

    def test_hit_dice_total_equals_level(self):
        for klass in NPCClassName:
            for lv in (1, 5, 10):
                prog = npc_class_progression(klass, lv)
                assert prog.hit_dice_total == lv

    def test_returns_npc_progression(self):
        prog = npc_class_progression(NPCClassName.Warrior, 3)
        assert isinstance(prog, NPCProgression)

    def test_class_features_are_list(self):
        for klass in NPCClassName:
            prog = npc_class_progression(klass, 1)
            assert isinstance(prog.class_features, list)

    def test_invalid_level_raises(self):
        with pytest.raises(ValueError):
            npc_class_progression(NPCClassName.Commoner, 0)


# ---------------------------------------------------------------------------
# E-052 — NPC generator
# ---------------------------------------------------------------------------

class TestGenerateNPC:
    def test_returns_npcstats(self):
        npc = generate_npc(NPCClassName.Warrior, 5)
        assert isinstance(npc, NPCStats)

    def test_klass_and_level_stored(self):
        npc = generate_npc(NPCClassName.Expert, 3)
        assert npc.klass == NPCClassName.Expert
        assert npc.level == 3

    # BAB / saves come from progression
    def test_warrior_level5_bab(self):
        npc = generate_npc(NPCClassName.Warrior, 5)
        assert npc.bab == 5

    def test_commoner_level1_all_poor_saves(self):
        npc = generate_npc(NPCClassName.Commoner, 1)
        assert npc.fort == 0
        assert npc.ref  == 0
        assert npc.will == 0

    # HP — deterministic
    def test_commoner_level1_hp_deterministic(self):
        # First level: max HD = 4
        npc = generate_npc(NPCClassName.Commoner, 1)
        assert npc.hp == 4

    def test_commoner_level2_hp_deterministic(self):
        # Level 2: 4 (max) + 3 (avg d4 rounded up)
        npc = generate_npc(NPCClassName.Commoner, 2)
        assert npc.hp == 4 + 3  # 7

    def test_warrior_level3_hp_deterministic(self):
        # d8: max=8, avg=5
        npc = generate_npc(NPCClassName.Warrior, 3)
        assert npc.hp == 8 + 2 * 5  # 18

    def test_hp_with_rng(self):
        rng = random.Random(42)
        npc = generate_npc(NPCClassName.Warrior, 5, rng=rng)
        # First level is max (8), remaining 4 are random 1-8
        assert npc.hp >= 8 + 4       # minimum possible after max first
        assert npc.hp <= 8 + 4 * 8  # maximum possible

    # Equipment gp budget
    def test_gp_budget_formula(self):
        for level in (1, 5, 10):
            npc = generate_npc(NPCClassName.Expert, level)
            assert npc.equipment_gp_budget == level * level * 150

    # AC
    def test_ac_at_least_ten(self):
        for klass in NPCClassName:
            npc = generate_npc(klass, 1)
            assert npc.ac >= 10

    def test_ac_level1_commoner_low_budget(self):
        # 1^2 * 150 = 150 gp → armor_bonus 4 → AC 14
        npc = generate_npc(NPCClassName.Commoner, 1)
        assert npc.ac == 14

    def test_ac_level10_has_better_armor(self):
        # 100 * 150 = 15000 gp → full plate bonus 8 → AC 18
        npc = generate_npc(NPCClassName.Commoner, 10)
        assert npc.ac == 18

    # Skills
    def test_skills_is_dict(self):
        npc = generate_npc(NPCClassName.Expert, 3)
        assert isinstance(npc.skills, dict)

    def test_total_skill_ranks_correct(self):
        for klass in NPCClassName:
            base = NPC_CLASS_REGISTRY[klass]
            lv = 4
            npc = generate_npc(klass, lv)
            expected_total = lv * base.skill_points_per_level
            assert sum(npc.skills.values()) == expected_total

    def test_skills_only_class_skills(self):
        npc = generate_npc(NPCClassName.Warrior, 4)
        base = NPC_CLASS_REGISTRY[NPCClassName.Warrior]
        for skill in npc.skills:
            assert skill in base.class_skills

    # Feats
    def test_feats_is_list(self):
        npc = generate_npc(NPCClassName.Commoner, 1)
        assert isinstance(npc.feats, list)

    @pytest.mark.parametrize("level,expected_feats", [
        (1, 1),   # level 1 → 1 feat
        (2, 1),   # level 2 → still 1
        (3, 2),   # level 3 → 2 feats
        (5, 2),   # level 5 → 2
        (6, 3),   # level 6 → 3
        (9, 4),   # level 9 → 4
        (12, 5),  # level 12 → 5
    ])
    def test_feat_count_by_level(self, level, expected_feats):
        npc = generate_npc(NPCClassName.Commoner, level)
        assert len(npc.feats) == expected_feats

    def test_feat_names(self):
        npc = generate_npc(NPCClassName.Commoner, 6)
        assert npc.feats == ["Feat 1", "Feat 2", "Feat 3"]

    # Invalid level
    def test_invalid_level_raises(self):
        with pytest.raises(ValueError):
            generate_npc(NPCClassName.Commoner, 0)

    # Deterministic rng=None produces same result
    def test_deterministic_no_rng(self):
        npc1 = generate_npc(NPCClassName.Adept, 7)
        npc2 = generate_npc(NPCClassName.Adept, 7)
        assert npc1.hp == npc2.hp
        assert npc1.skills == npc2.skills
        assert npc1.feats == npc2.feats

    # All classes generate without error across common levels
    @pytest.mark.parametrize("klass", list(NPCClassName))
    @pytest.mark.parametrize("level", [1, 5, 10, 20])
    def test_all_classes_all_levels(self, klass, level):
        npc = generate_npc(klass, level)
        assert npc.level == level
        assert npc.hp > 0
        assert npc.ac >= 10
