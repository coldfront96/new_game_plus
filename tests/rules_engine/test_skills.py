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
    SKILL_SYNERGIES,
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


# ---------------------------------------------------------------------------
# Skill Synergy Tests
# ---------------------------------------------------------------------------

class TestSkillSynergies:
    """Tests for 3.5e Skill Synergy system (SKILL_SYNERGIES table + get_synergy_bonus)."""

    def test_skill_synergies_is_dict(self):
        assert isinstance(SKILL_SYNERGIES, dict)
        assert len(SKILL_SYNERGIES) > 0

    def test_tumble_grants_balance_and_jump(self):
        assert "Balance" in SKILL_SYNERGIES["Tumble"]
        assert "Jump" in SKILL_SYNERGIES["Tumble"]

    def test_bluff_grants_diplomacy(self):
        assert "Diplomacy" in SKILL_SYNERGIES["Bluff"]

    def test_bluff_grants_intimidate(self):
        assert "Intimidate" in SKILL_SYNERGIES["Bluff"]

    def test_jump_grants_tumble(self):
        assert "Tumble" in SKILL_SYNERGIES["Jump"]

    def test_use_rope_grants_escape_artist(self):
        assert "Escape Artist" in SKILL_SYNERGIES["Use Rope"]

    # get_synergy_bonus ---------------------------------------------------

    def test_no_synergy_when_ranks_below_5(self):
        ss = SkillSystem()
        ss.set_rank("Tumble", 4)
        assert ss.get_synergy_bonus("Balance") == 0

    def test_synergy_bonus_2_when_5_ranks(self):
        ss = SkillSystem()
        ss.set_rank("Tumble", 5)
        assert ss.get_synergy_bonus("Balance") == 2

    def test_synergy_bonus_2_when_more_than_5_ranks(self):
        ss = SkillSystem()
        ss.set_rank("Tumble", 10)
        assert ss.get_synergy_bonus("Balance") == 2

    def test_no_synergy_for_unrelated_skill(self):
        ss = SkillSystem()
        ss.set_rank("Tumble", 10)
        assert ss.get_synergy_bonus("Diplomacy") == 0

    def test_multiple_synergy_sources_stack(self):
        """Bluff (5 ranks) and Decipher Script (5 ranks) both synergize with Use Magic Device."""
        ss = SkillSystem()
        ss.set_rank("Bluff", 5)
        ss.set_rank("Decipher Script", 5)
        # Bluff → Diplomacy/Intimidate/SoH/Disguise; Decipher Script → UMD; Spellcraft → UMD
        # UMD benefits from Decipher Script and Spellcraft
        ss.set_rank("Spellcraft", 5)
        bonus = ss.get_synergy_bonus("Use Magic Device")
        assert bonus == 4  # +2 from Decipher Script + +2 from Spellcraft

    def test_tumble_synergy_jump(self):
        ss = SkillSystem()
        ss.set_rank("Tumble", 5)
        assert ss.get_synergy_bonus("Jump") == 2

    def test_bluff_synergy_diplomacy(self):
        ss = SkillSystem()
        ss.set_rank("Bluff", 5)
        assert ss.get_synergy_bonus("Diplomacy") == 2

    # check() with synergy -------------------------------------------------

    def test_check_includes_synergy_by_default(self):
        """check() should automatically add synergy bonus."""
        ss = SkillSystem()
        ss.set_rank("Tumble", 5)   # grants +2 to Balance
        ss.set_rank("Balance", 3)

        with patch("src.rules_engine.skills.roll_d20") as mock:
            # total_modifier = 3 (rank) + 1 (ability) + 2 (synergy) = 6
            mock.return_value = RollResult(raw=10, modifier=6, total=16)
            result = ss.check("Balance", ability_modifier=1, dc=15)

        assert result.success is True

    def test_check_can_disable_synergy(self):
        """check() with include_synergy=False should ignore synergy bonuses."""
        ss = SkillSystem()
        ss.set_rank("Tumble", 5)
        ss.set_rank("Balance", 3)

        with patch("src.rules_engine.skills.roll_d20") as mock:
            # total_modifier = 3 (rank) + 1 (ability) + 0 (no synergy) = 4
            mock.return_value = RollResult(raw=10, modifier=4, total=14)
            result = ss.check("Balance", ability_modifier=1, dc=15, include_synergy=False)

        assert result.success is False

    def test_check_synergy_only_from_this_skill_system(self):
        """Synergy is based on ranks in this SkillSystem, not global state."""
        ss1 = SkillSystem()
        ss2 = SkillSystem()
        ss2.set_rank("Tumble", 5)

        # ss1 has no Tumble ranks
        assert ss1.get_synergy_bonus("Balance") == 0
        assert ss2.get_synergy_bonus("Balance") == 2
