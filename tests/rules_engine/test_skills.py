"""
tests/rules_engine/test_skills.py
-----------------------------------
Unit tests for src.rules_engine.skills (SkillSystem, SkillCheckResult).
"""

from unittest.mock import patch

import pytest

from src.rules_engine.dice import RollResult
from src.rules_engine.skills import (
    SKILL_DEFINITIONS,
    SkillAbility,
    SkillCheckResult,
    SkillSystem,
)


# ---------------------------------------------------------------------------
# SkillSystem — Rank management
# ---------------------------------------------------------------------------

class TestSkillSystemRanks:
    """Tests for skill rank management."""

    def test_slots_enabled(self):
        assert hasattr(SkillSystem, "__slots__")

    def test_default_rank_is_zero(self):
        ss = SkillSystem()
        assert ss.get_rank("Survival") == 0

    def test_set_and_get_rank(self):
        ss = SkillSystem()
        ss.set_rank("Survival", 5)
        assert ss.get_rank("Survival") == 5

    def test_set_rank_overwrites(self):
        ss = SkillSystem()
        ss.set_rank("Swim", 3)
        ss.set_rank("Swim", 7)
        assert ss.get_rank("Swim") == 7

    def test_negative_rank_raises(self):
        ss = SkillSystem()
        with pytest.raises(ValueError, match="negative"):
            ss.set_rank("Hide", -1)

    def test_rank_exceeds_cap_raises(self):
        ss = SkillSystem(max_rank_cap=10)
        with pytest.raises(ValueError, match="exceeds maximum"):
            ss.set_rank("Hide", 11)

    def test_rank_at_cap_allowed(self):
        ss = SkillSystem(max_rank_cap=10)
        ss.set_rank("Spot", 10)
        assert ss.get_rank("Spot") == 10

    def test_add_ranks_increments(self):
        ss = SkillSystem()
        ss.set_rank("Craft", 3)
        result = ss.add_ranks("Craft", 4)
        assert result == 7
        assert ss.get_rank("Craft") == 7

    def test_add_ranks_from_zero(self):
        ss = SkillSystem()
        result = ss.add_ranks("Listen", 5)
        assert result == 5

    def test_add_ranks_exceeds_cap(self):
        ss = SkillSystem(max_rank_cap=10)
        ss.set_rank("Climb", 8)
        with pytest.raises(ValueError, match="exceed cap"):
            ss.add_ranks("Climb", 5)

    def test_trained_skills_only_nonzero(self):
        ss = SkillSystem()
        ss.set_rank("Search", 3)
        ss.set_rank("Survival", 5)
        ss.set_rank("Hide", 0)
        trained = ss.trained_skills
        assert "Search" in trained
        assert "Survival" in trained
        assert "Hide" not in trained

    def test_multiple_skills_independent(self):
        ss = SkillSystem()
        ss.set_rank("Search", 4)
        ss.set_rank("Spot", 6)
        assert ss.get_rank("Search") == 4
        assert ss.get_rank("Spot") == 6


# ---------------------------------------------------------------------------
# SkillSystem — Check resolution
# ---------------------------------------------------------------------------

class TestSkillSystemCheck:
    """Tests for skill check resolution (d20 + rank + mod vs DC)."""

    def test_check_result_dataclass_has_slots(self):
        assert hasattr(SkillCheckResult, "__slots__")

    def test_successful_check(self):
        ss = SkillSystem()
        ss.set_rank("Survival", 6)
        with patch("src.rules_engine.skills.roll_d20") as mock:
            mock.return_value = RollResult(raw=12, modifier=9, total=21)
            result = ss.check("Survival", ability_modifier=3, dc=15)
        assert result.success is True
        assert result.total == 21
        assert result.margin == 6

    def test_failed_check(self):
        ss = SkillSystem()
        ss.set_rank("Search", 2)
        with patch("src.rules_engine.skills.roll_d20") as mock:
            mock.return_value = RollResult(raw=3, modifier=2, total=5)
            result = ss.check("Search", ability_modifier=0, dc=15)
        assert result.success is False
        assert result.margin == -10

    def test_check_exact_dc(self):
        ss = SkillSystem()
        ss.set_rank("Spot", 5)
        with patch("src.rules_engine.skills.roll_d20") as mock:
            mock.return_value = RollResult(raw=5, modifier=7, total=12)
            result = ss.check("Spot", ability_modifier=2, dc=12)
        assert result.success is True
        assert result.margin == 0

    def test_check_with_misc_modifier(self):
        ss = SkillSystem()
        ss.set_rank("Hide", 4)
        with patch("src.rules_engine.skills.roll_d20") as mock:
            # total_mod = 4 + 3 + 2 = 9
            mock.return_value = RollResult(raw=10, modifier=9, total=19)
            result = ss.check("Hide", ability_modifier=3, dc=20, misc_modifier=2)
        assert result.success is False
        assert result.total == 19

    def test_check_untrained(self):
        ss = SkillSystem()
        with patch("src.rules_engine.skills.roll_d20") as mock:
            mock.return_value = RollResult(raw=18, modifier=2, total=20)
            result = ss.check("Climb", ability_modifier=2, dc=10)
        assert result.success is True

    def test_check_result_fields(self):
        ss = SkillSystem()
        ss.set_rank("Heal", 3)
        with patch("src.rules_engine.skills.roll_d20") as mock:
            mock.return_value = RollResult(raw=14, modifier=5, total=19)
            result = ss.check("Heal", ability_modifier=2, dc=12)
        assert result.skill_name == "Heal"
        assert result.roll.raw == 14
        assert result.dc == 12


# ---------------------------------------------------------------------------
# Skill definitions lookup
# ---------------------------------------------------------------------------

class TestSkillDefinitionsLookup:
    """Tests for get_key_ability and SKILL_DEFINITIONS."""

    def test_survival_key_ability(self):
        ss = SkillSystem()
        assert ss.get_key_ability("Survival") == SkillAbility.WIS

    def test_search_key_ability(self):
        ss = SkillSystem()
        assert ss.get_key_ability("Search") == SkillAbility.INT

    def test_unknown_skill_returns_none(self):
        ss = SkillSystem()
        assert ss.get_key_ability("MadeUpSkill") is None

    def test_all_standard_skills_have_abilities(self):
        for name, ability in SKILL_DEFINITIONS.items():
            assert isinstance(ability, SkillAbility), f"{name} missing ability"
