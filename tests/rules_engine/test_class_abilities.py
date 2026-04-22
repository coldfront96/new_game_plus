"""
tests/rules_engine/test_class_abilities.py
-------------------------------------------
Unit tests for the remaining core class abilities:

* Turn Undead (Cleric)          — TurnUndeadManager
* Wild Shape (Druid)            — WildShapeManager / WildShapeForm / WildShapeState
* Smite Evil (Paladin)          — SmiteEvilManager / SmiteEvilResult
* Lay on Hands (Paladin)        — LayOnHandsManager
* Favored Enemy (Ranger)        — FavoredEnemyManager / FavoredEnemyEntry
* Combat integration            — smite_evil_* and favored_enemy_* params in
                                  AttackResolver.resolve_attack
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.rules_engine.abilities import (
    FavoredEnemyEntry,
    FavoredEnemyManager,
    LayOnHandsManager,
    SmiteEvilManager,
    SmiteEvilResult,
    TurnUndeadManager,
    TurnUndeadResult,
    WildShapeForm,
    WildShapeManager,
    WildShapeState,
)
from src.rules_engine.character_35e import Character35e, Size
from src.rules_engine.combat import AttackResolver, CombatResult
from src.rules_engine.dice import RollResult


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def level5_cleric():
    return Character35e(
        name="Jozan",
        char_class="Cleric",
        level=5,
        charisma=14,  # +2 mod
    )


@pytest.fixture
def level5_druid():
    return Character35e(
        name="Shii",
        char_class="Druid",
        level=5,
        strength=10,
        dexterity=12,
        constitution=10,
        size=Size.MEDIUM,
    )


@pytest.fixture
def bear_form():
    """Brown Bear: Large, STR 27, DEX 13, CON 19, natural armor +7."""
    return WildShapeForm(
        name="Brown Bear",
        size="LARGE",
        strength=27,
        dexterity=13,
        constitution=19,
        natural_armor=7,
    )


@pytest.fixture
def wolf_form():
    """Wolf: Medium, STR 13, DEX 15, CON 15, natural armor +2."""
    return WildShapeForm(
        name="Wolf",
        size="MEDIUM",
        strength=13,
        dexterity=15,
        constitution=15,
        natural_armor=2,
    )


@pytest.fixture
def level5_paladin():
    return Character35e(
        name="Pelor",
        char_class="Paladin",
        level=5,
        charisma=16,  # +3 mod
    )


@pytest.fixture
def level1_ranger():
    return Character35e(
        name="Drizzt",
        char_class="Ranger",
        level=1,
        strength=14,
    )


@pytest.fixture
def dummy_target():
    return Character35e(
        name="Dummy",
        char_class="Fighter",
        level=1,
        strength=10,
        dexterity=10,
    )


# ===========================================================================
# TurnUndeadManager
# ===========================================================================

class TestTurnUndeadManagerSlots:
    def test_has_slots(self):
        assert hasattr(TurnUndeadManager, "__slots__")

    def test_result_has_slots(self):
        assert hasattr(TurnUndeadResult, "__slots__")


class TestTurnUndeadManagerUsesPerDay:
    def test_cha_mod_0_gives_3_uses(self):
        mgr = TurnUndeadManager.for_cleric(level=1, cha_mod=0)
        assert mgr.uses_per_day == 3

    def test_cha_mod_positive_adds_to_uses(self):
        mgr = TurnUndeadManager.for_cleric(level=5, cha_mod=2)
        assert mgr.uses_per_day == 5

    def test_cha_mod_negative_reduces_uses(self):
        mgr = TurnUndeadManager.for_cleric(level=1, cha_mod=-1)
        assert mgr.uses_per_day == 2

    def test_uses_remaining_initialized_to_uses_per_day(self):
        mgr = TurnUndeadManager.for_cleric(level=3, cha_mod=1)
        assert mgr.uses_remaining == mgr.uses_per_day

    def test_cleric_level_stored(self):
        mgr = TurnUndeadManager.for_cleric(level=7, cha_mod=2)
        assert mgr.cleric_level == 7


class TestTurnUndeadManagerCanTurn:
    def test_can_turn_when_uses_remain(self):
        mgr = TurnUndeadManager.for_cleric(level=1, cha_mod=0)
        assert mgr.can_turn() is True

    def test_cannot_turn_when_no_uses(self):
        mgr = TurnUndeadManager.for_cleric(level=1, cha_mod=-3)
        assert mgr.uses_per_day == 0
        assert mgr.can_turn() is False

    def test_attempt_turn_returns_none_when_exhausted(self):
        mgr = TurnUndeadManager.for_cleric(level=1, cha_mod=0)
        for _ in range(3):
            mgr.attempt_turn()
        assert mgr.attempt_turn() is None


class TestTurnUndeadManagerAttempt:
    def test_attempt_decrements_uses(self):
        mgr = TurnUndeadManager.for_cleric(level=5, cha_mod=2)
        mgr.attempt_turn()
        assert mgr.uses_remaining == mgr.uses_per_day - 1

    def test_attempt_returns_result(self):
        mgr = TurnUndeadManager.for_cleric(level=5, cha_mod=2)
        result = mgr.attempt_turn()
        assert isinstance(result, TurnUndeadResult)

    def test_result_check_roll_has_cha_mod(self):
        """The check RollResult modifier must equal the CHA mod."""
        mgr = TurnUndeadManager.for_cleric(level=5, cha_mod=2)
        result = mgr.attempt_turn()
        assert result.check_roll.modifier == 2

    def test_result_damage_roll_modifier_equals_level_plus_cha(self):
        """Turning damage modifier = cleric level + CHA mod."""
        mgr = TurnUndeadManager.for_cleric(level=5, cha_mod=2)
        result = mgr.attempt_turn()
        assert result.damage_roll.modifier == 7  # 5 + 2

    def test_rest_restores_uses(self):
        mgr = TurnUndeadManager.for_cleric(level=3, cha_mod=1)
        mgr.attempt_turn()
        mgr.rest()
        assert mgr.uses_remaining == mgr.uses_per_day


class TestTurnUndeadHDTable:
    """Verify the turning check → max HD mapping per 3.5e SRD."""

    def _hd(self, cleric_level: int, check_total: int) -> int:
        mgr = TurnUndeadManager.for_cleric(level=cleric_level, cha_mod=0)
        return mgr._hd_from_check(check_total)

    # Level 5 Cleric; check result maps to cleric_level ± offset.
    def test_check_leq_0_gives_level_minus_4(self):
        assert self._hd(5, 0) == 1   # 5 - 4

    def test_check_neg_gives_level_minus_4(self):
        assert self._hd(5, -5) == 1  # 5 - 4

    def test_check_1_to_3_gives_level_minus_3(self):
        assert self._hd(5, 2) == 2   # 5 - 3

    def test_check_4_to_6_gives_level_minus_2(self):
        assert self._hd(5, 5) == 3   # 5 - 2

    def test_check_7_to_9_gives_level_minus_1(self):
        assert self._hd(5, 9) == 4   # 5 - 1

    def test_check_10_to_12_gives_level(self):
        assert self._hd(5, 11) == 5  # 5

    def test_check_13_to_15_gives_level_plus_1(self):
        assert self._hd(5, 14) == 6  # 5 + 1

    def test_check_16_to_18_gives_level_plus_2(self):
        assert self._hd(5, 17) == 7  # 5 + 2

    def test_check_19_to_21_gives_level_plus_3(self):
        assert self._hd(5, 20) == 8  # 5 + 3

    def test_check_geq_22_gives_level_plus_4(self):
        assert self._hd(5, 22) == 9  # 5 + 4

    def test_check_very_high_gives_level_plus_4(self):
        assert self._hd(10, 30) == 14  # 10 + 4


# ===========================================================================
# WildShapeManager
# ===========================================================================

class TestWildShapeSlots:
    def test_manager_has_slots(self):
        assert hasattr(WildShapeManager, "__slots__")

    def test_state_has_slots(self):
        assert hasattr(WildShapeState, "__slots__")

    def test_form_has_slots(self):
        assert hasattr(WildShapeForm, "__slots__")


class TestWildShapeUsesPerDay:
    @pytest.mark.parametrize("level,expected", [
        (1, 0), (4, 0),    # no wild shape before level 5
        (5, 1), (6, 2), (7, 3), (8, 3), (9, 3),
        (10, 4), (14, 4),
        (15, 5), (17, 5),
        (18, 6), (20, 6),
    ])
    def test_uses_from_level(self, level, expected):
        mgr = WildShapeManager.for_druid(level)
        assert mgr.uses_per_day == expected

    def test_uses_remaining_equals_per_day(self):
        mgr = WildShapeManager.for_druid(5)
        assert mgr.uses_remaining == mgr.uses_per_day


class TestWildShapeActivation:
    def test_can_shape_with_uses(self, level5_druid, wolf_form):
        mgr = WildShapeManager.for_druid(5)
        assert mgr.can_shape() is True

    def test_cannot_shape_at_level_4(self):
        mgr = WildShapeManager.for_druid(4)
        assert mgr.can_shape() is False

    def test_shift_returns_state(self, level5_druid, wolf_form):
        mgr = WildShapeManager.for_druid(5)
        state = mgr.shift(level5_druid, wolf_form)
        assert state is not None
        assert state.active is True

    def test_shift_decrements_uses(self, level5_druid, wolf_form):
        mgr = WildShapeManager.for_druid(5)
        mgr.shift(level5_druid, wolf_form)
        assert mgr.uses_remaining == 0

    def test_shift_applies_str(self, level5_druid, wolf_form):
        mgr = WildShapeManager.for_druid(5)
        mgr.shift(level5_druid, wolf_form)
        assert level5_druid.strength == wolf_form.strength

    def test_shift_applies_dex(self, level5_druid, wolf_form):
        mgr = WildShapeManager.for_druid(5)
        mgr.shift(level5_druid, wolf_form)
        assert level5_druid.dexterity == wolf_form.dexterity

    def test_shift_applies_con(self, level5_druid, wolf_form):
        mgr = WildShapeManager.for_druid(5)
        mgr.shift(level5_druid, wolf_form)
        assert level5_druid.constitution == wolf_form.constitution

    def test_shift_applies_size(self, level5_druid, bear_form):
        mgr = WildShapeManager.for_druid(6)
        mgr.shift(level5_druid, bear_form)
        assert level5_druid.size == Size.LARGE

    def test_shift_stores_natural_armor_bonus(self, level5_druid, bear_form):
        mgr = WildShapeManager.for_druid(6)
        state = mgr.shift(level5_druid, bear_form)
        assert state.natural_armor_bonus == bear_form.natural_armor

    def test_shift_stores_original_str(self, level5_druid, wolf_form):
        original_str = level5_druid.strength
        mgr = WildShapeManager.for_druid(5)
        state = mgr.shift(level5_druid, wolf_form)
        assert state.original_str == original_str

    def test_shift_stores_original_size_name(self, level5_druid, bear_form):
        mgr = WildShapeManager.for_druid(6)
        state = mgr.shift(level5_druid, bear_form)
        assert state.original_size_name == "MEDIUM"

    def test_cannot_shift_when_already_active(self, level5_druid, wolf_form, bear_form):
        mgr = WildShapeManager.for_druid(6)
        mgr.shift(level5_druid, wolf_form)
        result = mgr.shift(level5_druid, bear_form)
        assert result is None

    def test_shift_returns_none_no_uses(self, level5_druid, wolf_form):
        mgr = WildShapeManager.for_druid(5)
        mgr.shift(level5_druid, wolf_form)
        mgr.revert(level5_druid)
        result = mgr.shift(level5_druid, wolf_form)
        assert result is None


class TestWildShapeRevert:
    def test_revert_restores_str(self, level5_druid, wolf_form):
        original = level5_druid.strength
        mgr = WildShapeManager.for_druid(5)
        mgr.shift(level5_druid, wolf_form)
        mgr.revert(level5_druid)
        assert level5_druid.strength == original

    def test_revert_restores_dex(self, level5_druid, wolf_form):
        original = level5_druid.dexterity
        mgr = WildShapeManager.for_druid(5)
        mgr.shift(level5_druid, wolf_form)
        mgr.revert(level5_druid)
        assert level5_druid.dexterity == original

    def test_revert_restores_con(self, level5_druid, wolf_form):
        original = level5_druid.constitution
        mgr = WildShapeManager.for_druid(5)
        mgr.shift(level5_druid, wolf_form)
        mgr.revert(level5_druid)
        assert level5_druid.constitution == original

    def test_revert_restores_size(self, level5_druid, bear_form):
        original_size = level5_druid.size
        mgr = WildShapeManager.for_druid(6)
        mgr.shift(level5_druid, bear_form)
        mgr.revert(level5_druid)
        assert level5_druid.size == original_size

    def test_revert_clears_state(self, level5_druid, wolf_form):
        mgr = WildShapeManager.for_druid(5)
        mgr.shift(level5_druid, wolf_form)
        mgr.revert(level5_druid)
        assert mgr.state.active is False
        assert mgr.state.natural_armor_bonus == 0

    def test_revert_when_not_active_is_noop(self, level5_druid):
        mgr = WildShapeManager.for_druid(5)
        original_str = level5_druid.strength
        mgr.revert(level5_druid)  # should not raise
        assert level5_druid.strength == original_str

    def test_rest_restores_uses(self, level5_druid, wolf_form):
        mgr = WildShapeManager.for_druid(5)
        mgr.shift(level5_druid, wolf_form)
        mgr.revert(level5_druid)
        mgr.rest()
        assert mgr.uses_remaining == mgr.uses_per_day


# ===========================================================================
# SmiteEvilManager
# ===========================================================================

class TestSmiteEvilSlots:
    def test_manager_has_slots(self):
        assert hasattr(SmiteEvilManager, "__slots__")

    def test_result_has_slots(self):
        assert hasattr(SmiteEvilResult, "__slots__")


class TestSmiteEvilUsesPerDay:
    @pytest.mark.parametrize("level,expected", [
        (1, 1), (4, 1),
        (5, 2), (9, 2),
        (10, 3), (14, 3),
        (15, 4), (19, 4),
        (20, 5),
    ])
    def test_uses_from_level(self, level, expected):
        mgr = SmiteEvilManager.for_paladin(level=level, cha_mod=3)
        assert mgr.uses_per_day == expected

    def test_uses_remaining_initialized(self):
        mgr = SmiteEvilManager.for_paladin(level=5, cha_mod=2)
        assert mgr.uses_remaining == mgr.uses_per_day


class TestSmiteEvilActivation:
    def test_can_smite_with_uses(self):
        mgr = SmiteEvilManager.for_paladin(level=1, cha_mod=3)
        assert mgr.can_smite() is True

    def test_activate_returns_result(self):
        mgr = SmiteEvilManager.for_paladin(level=5, cha_mod=3)
        result = mgr.activate()
        assert isinstance(result, SmiteEvilResult)

    def test_attack_bonus_equals_cha_mod(self):
        mgr = SmiteEvilManager.for_paladin(level=5, cha_mod=3)
        result = mgr.activate()
        assert result.attack_bonus == 3

    def test_damage_bonus_equals_paladin_level(self):
        mgr = SmiteEvilManager.for_paladin(level=8, cha_mod=2)
        result = mgr.activate()
        assert result.damage_bonus == 8

    def test_activate_decrements_uses(self):
        mgr = SmiteEvilManager.for_paladin(level=1, cha_mod=2)
        mgr.activate()
        assert mgr.uses_remaining == 0

    def test_activate_returns_none_when_exhausted(self):
        mgr = SmiteEvilManager.for_paladin(level=1, cha_mod=2)
        mgr.activate()
        result = mgr.activate()
        assert result is None

    def test_rest_restores_uses(self):
        mgr = SmiteEvilManager.for_paladin(level=5, cha_mod=3)
        mgr.activate()
        mgr.rest()
        assert mgr.uses_remaining == mgr.uses_per_day

    def test_negative_cha_mod_stored_as_negative_attack_bonus(self):
        mgr = SmiteEvilManager.for_paladin(level=1, cha_mod=-1)
        result = mgr.activate()
        assert result.attack_bonus == -1


# ===========================================================================
# LayOnHandsManager
# ===========================================================================

class TestLayOnHandsSlots:
    def test_has_slots(self):
        assert hasattr(LayOnHandsManager, "__slots__")


class TestLayOnHandsPool:
    def test_pool_equals_level_times_cha_mod(self):
        mgr = LayOnHandsManager.for_paladin(level=5, cha_mod=3)
        assert mgr.pool_max == 15

    def test_zero_cha_mod_gives_zero_pool(self):
        mgr = LayOnHandsManager.for_paladin(level=5, cha_mod=0)
        assert mgr.pool_max == 0

    def test_negative_cha_mod_clamped_to_zero(self):
        mgr = LayOnHandsManager.for_paladin(level=5, cha_mod=-2)
        assert mgr.pool_max == 0

    def test_pool_remaining_initialized_to_pool_max(self):
        mgr = LayOnHandsManager.for_paladin(level=10, cha_mod=4)
        assert mgr.pool_remaining == mgr.pool_max


class TestLayOnHandsHeal:
    def test_can_heal_when_pool_available(self):
        mgr = LayOnHandsManager.for_paladin(level=5, cha_mod=3)
        assert mgr.can_heal(5) is True

    def test_cannot_heal_when_pool_empty(self):
        mgr = LayOnHandsManager.for_paladin(level=1, cha_mod=0)
        assert mgr.can_heal(1) is False

    def test_heal_returns_amount(self):
        mgr = LayOnHandsManager.for_paladin(level=5, cha_mod=3)
        healed = mgr.heal(10)
        assert healed == 10

    def test_heal_reduces_pool(self):
        mgr = LayOnHandsManager.for_paladin(level=5, cha_mod=3)
        mgr.heal(10)
        assert mgr.pool_remaining == 5

    def test_heal_cannot_overdraw_pool(self):
        mgr = LayOnHandsManager.for_paladin(level=5, cha_mod=3)
        healed = mgr.heal(100)
        assert healed == 15
        assert mgr.pool_remaining == 0

    def test_rest_restores_pool(self):
        mgr = LayOnHandsManager.for_paladin(level=5, cha_mod=3)
        mgr.heal(10)
        mgr.rest()
        assert mgr.pool_remaining == mgr.pool_max


# ===========================================================================
# FavoredEnemyManager
# ===========================================================================

class TestFavoredEnemySlots:
    def test_manager_has_slots(self):
        assert hasattr(FavoredEnemyManager, "__slots__")

    def test_entry_has_slots(self):
        assert hasattr(FavoredEnemyEntry, "__slots__")


class TestFavoredEnemyBonuses:
    @pytest.mark.parametrize("level,expected_bonus", [
        (1, 2),
        (2, 2),
        (4, 2),
        (5, 4),  # 2nd enemy added → primary goes to +4
        (10, 6), # 3rd enemy added → primary at +6
        (15, 8),
        (20, 10),
    ])
    def test_primary_enemy_bonus_at_level(self, level, expected_bonus):
        mgr = FavoredEnemyManager.for_ranger(
            level=level,
            enemy_types=["Undead", "Humanoid", "Dragon", "Aberration", "Outsider"],
        )
        assert mgr.get_bonus("Undead") == expected_bonus

    def test_second_enemy_bonus_at_level5(self):
        mgr = FavoredEnemyManager.for_ranger(
            level=5,
            enemy_types=["Undead", "Humanoid"],
        )
        assert mgr.get_bonus("Humanoid") == 2

    def test_third_enemy_bonus_at_level10(self):
        mgr = FavoredEnemyManager.for_ranger(
            level=10,
            enemy_types=["Undead", "Humanoid", "Dragon"],
        )
        assert mgr.get_bonus("Dragon") == 2
        assert mgr.get_bonus("Humanoid") == 4
        assert mgr.get_bonus("Undead") == 6

    def test_non_favored_enemy_returns_zero(self):
        mgr = FavoredEnemyManager.for_ranger(level=1, enemy_types=["Undead"])
        assert mgr.get_bonus("Dragon") == 0

    def test_lookup_is_case_insensitive(self):
        mgr = FavoredEnemyManager.for_ranger(level=1, enemy_types=["Undead"])
        assert mgr.get_bonus("undead") == 2
        assert mgr.get_bonus("UNDEAD") == 2

    def test_skill_bonus_delegates_to_get_bonus(self):
        mgr = FavoredEnemyManager.for_ranger(level=1, enemy_types=["Undead"])
        assert mgr.skill_bonus("Undead") == mgr.get_bonus("Undead")

    def test_damage_bonus_delegates_to_get_bonus(self):
        mgr = FavoredEnemyManager.for_ranger(level=1, enemy_types=["Undead"])
        assert mgr.damage_bonus("Undead") == mgr.get_bonus("Undead")

    def test_more_types_provided_than_slots_uses_only_available_slots(self):
        """Ranger level 1 has 1 slot; only the first enemy type is used."""
        mgr = FavoredEnemyManager.for_ranger(
            level=1,
            enemy_types=["Undead", "Humanoid"],
        )
        assert len(mgr.enemies) == 1
        assert mgr.enemies[0].creature_type == "Undead"


# ===========================================================================
# Combat integration — Smite Evil
# ===========================================================================

class TestSmiteEvilCombatIntegration:
    """Verify smite_evil_attack_bonus and smite_evil_damage_bonus params."""

    def _make_hit_roll(self, attack_bonus: int) -> RollResult:
        return RollResult(raw=10, modifier=attack_bonus, total=10 + attack_bonus)

    def test_smite_evil_attack_bonus_added_to_attack_bonus(
        self, level5_paladin, dummy_target
    ):
        """The smite attack bonus must appear in CombatResult.attack_bonus."""
        cha_mod = level5_paladin.charisma_mod  # +3
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            base_attack = level5_paladin.melee_attack
            mock_d20.return_value = self._make_hit_roll(base_attack + cha_mod)
            mock_dmg.return_value = RollResult(raw=5, modifier=0, total=5)

            result = AttackResolver.resolve_attack(
                level5_paladin,
                dummy_target,
                smite_evil_attack_bonus=cha_mod,
            )

        assert result.attack_bonus == base_attack + cha_mod

    def test_smite_evil_damage_bonus_added_to_total_damage(
        self, level5_paladin, dummy_target
    ):
        """Smite damage bonus (Paladin level) must be reflected in total_damage
        and stored in CombatResult.smite_evil_damage."""
        paladin_level = level5_paladin.level  # 5
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            base_attack = level5_paladin.melee_attack
            mock_d20.return_value = self._make_hit_roll(base_attack)
            mock_dmg.return_value = RollResult(raw=4, modifier=0, total=4)

            result = AttackResolver.resolve_attack(
                level5_paladin,
                dummy_target,
                smite_evil_damage_bonus=paladin_level,
            )

        assert result.smite_evil_damage == paladin_level
        assert result.total_damage >= 4 + paladin_level

    def test_no_smite_bonuses_by_default(self, level5_paladin, dummy_target):
        """Without smite params the smite_evil_damage field is 0."""
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            atk = level5_paladin.melee_attack
            mock_d20.return_value = self._make_hit_roll(atk)
            mock_dmg.return_value = RollResult(raw=3, modifier=0, total=3)
            result = AttackResolver.resolve_attack(level5_paladin, dummy_target)

        assert result.smite_evil_damage == 0


# ===========================================================================
# Combat integration — Favored Enemy
# ===========================================================================

class TestFavoredEnemyCombatIntegration:
    """Verify favored_enemy_damage_bonus param in resolve_attack."""

    def test_favored_enemy_bonus_added_to_total_damage(
        self, level1_ranger, dummy_target
    ):
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            atk = level1_ranger.melee_attack
            mock_d20.return_value = RollResult(raw=10, modifier=atk, total=10 + atk)
            mock_dmg.return_value = RollResult(raw=3, modifier=2, total=5)

            result = AttackResolver.resolve_attack(
                level1_ranger,
                dummy_target,
                favored_enemy_damage_bonus=2,
            )

        assert result.favored_enemy_damage == 2
        assert result.total_damage >= 5 + 2

    def test_favored_enemy_zero_by_default(self, level1_ranger, dummy_target):
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            atk = level1_ranger.melee_attack
            mock_d20.return_value = RollResult(raw=10, modifier=atk, total=10 + atk)
            mock_dmg.return_value = RollResult(raw=3, modifier=2, total=5)
            result = AttackResolver.resolve_attack(level1_ranger, dummy_target)

        assert result.favored_enemy_damage == 0

    def test_combined_smite_and_favored_enemy(self, dummy_target):
        """Both bonuses can apply simultaneously (different features)."""
        paladin_ranger = Character35e(
            name="Hybrid", char_class="Paladin", level=5,
            strength=14, charisma=16,
        )
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            atk = paladin_ranger.melee_attack
            mock_d20.return_value = RollResult(raw=10, modifier=atk, total=10 + atk)
            mock_dmg.return_value = RollResult(raw=2, modifier=2, total=4)

            result = AttackResolver.resolve_attack(
                paladin_ranger,
                dummy_target,
                smite_evil_damage_bonus=5,
                favored_enemy_damage_bonus=2,
            )

        assert result.smite_evil_damage == 5
        assert result.favored_enemy_damage == 2
        assert result.total_damage >= 4 + 5 + 2


# ===========================================================================
# CombatResult new fields
# ===========================================================================

class TestCombatResultNewFields:
    def test_smite_evil_damage_defaults_to_zero(self):
        result = CombatResult(
            hit=True,
            roll=RollResult(raw=15, modifier=5, total=20),
            attack_bonus=5,
            target_ac=10,
            damage_roll=RollResult(raw=4, modifier=2, total=6),
            total_damage=6,
            critical=False,
        )
        assert result.smite_evil_damage == 0

    def test_favored_enemy_damage_defaults_to_zero(self):
        result = CombatResult(
            hit=True,
            roll=RollResult(raw=15, modifier=5, total=20),
            attack_bonus=5,
            target_ac=10,
            damage_roll=RollResult(raw=4, modifier=2, total=6),
            total_damage=6,
            critical=False,
        )
        assert result.favored_enemy_damage == 0
