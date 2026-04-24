"""
tests/rules_engine/test_hazards.py
-----------------------------------
Pytest test suite for the D&D 3.5e DMG hazards & afflictions engine.

Covers:
- Falling damage (deterministic bounds, skill-check mitigation, edge cases)
- Heat and Cold danger (save pass/fail logic, DC escalation)
- Starvation & thirst tracking
- Poison initial/secondary save sequence
- Disease infection/daily save sequence
- Registry completeness
"""

from __future__ import annotations

import random
from unittest.mock import patch

import pytest

from src.rules_engine.hazards import (
    # Falling
    FallResult,
    calculate_falling_damage,
    # Heat
    ColdDanger,
    ColdExposureResult,
    ColdLevel,
    # Cold
    HeatDanger,
    HeatExposureResult,
    HeatLevel,
    # Starvation
    StarvationTracker,
    # Afflictions
    AfflictionPhase,
    AfflictionResult,
    Poison,
    Disease,
    DiseaseType,
    # Registries
    DISEASE_REGISTRY,
    POISON_REGISTRY,
)


# ===========================================================================
# Falling Damage
# ===========================================================================

class TestFallingDamage:
    """Falling damage per DMG p.302: 1d6 per 10 ft, max 20d6."""

    def test_zero_distance_returns_zero_damage(self):
        result = calculate_falling_damage(0)
        assert result.damage == 0
        assert result.dice_rolled == 0

    def test_negative_distance_returns_zero_damage(self):
        result = calculate_falling_damage(-10)
        assert result.damage == 0

    def test_less_than_10ft_returns_zero_damage(self):
        result = calculate_falling_damage(9)
        assert result.damage == 0
        assert result.dice_rolled == 0

    def test_exactly_10ft_rolls_one_d6(self):
        result = calculate_falling_damage(10)
        assert result.dice_rolled == 1
        assert 1 <= result.damage <= 6

    def test_40ft_rolls_four_d6(self):
        result = calculate_falling_damage(40)
        assert result.dice_rolled == 4
        assert 4 <= result.damage <= 24

    def test_200ft_caps_at_20d6(self):
        result = calculate_falling_damage(200)
        assert result.dice_rolled == 20
        assert 20 <= result.damage <= 120

    def test_cap_applies_beyond_200ft(self):
        result = calculate_falling_damage(500)
        assert result.dice_rolled == 20

    def test_jump_check_success_mitigates(self):
        """Successful Jump (DC 15) reduces fall by 10 ft."""
        with patch("src.rules_engine.hazards._roll_dice") as mock_roll:
            mock_roll.return_value = 15
            # 30 ft with Jump → treated as 20 ft (2d6)
            result = calculate_falling_damage(30, jump_check=15)
        assert result.dice_rolled == 2
        assert result.skill_check_used == "Jump"

    def test_jump_check_failure_no_mitigation(self):
        """Failed Jump (DC 15) provides no mitigation."""
        with patch("src.rules_engine.hazards._roll_dice") as mock_roll:
            mock_roll.return_value = 15
            result = calculate_falling_damage(30, jump_check=14)
        assert result.dice_rolled == 3  # 30 ft → 3d6, no reduction
        assert result.skill_check_used is None

    def test_tumble_check_success_mitigates(self):
        """Successful Tumble (DC 15) reduces fall by 10 ft."""
        with patch("src.rules_engine.hazards._roll_dice") as mock_roll:
            mock_roll.return_value = 15
            result = calculate_falling_damage(30, tumble_check=15)
        assert result.dice_rolled == 2
        assert result.skill_check_used == "Tumble"

    def test_jump_and_tumble_stack(self):
        """Both Jump and Tumble reduce by 10 ft each (20 ft total)."""
        with patch("src.rules_engine.hazards._roll_dice") as mock_roll:
            mock_roll.return_value = 10
            # 40 ft → Jump + Tumble → 20 ft → 2d6
            result = calculate_falling_damage(40, jump_check=15, tumble_check=15)
        assert result.dice_rolled == 2
        assert "Jump" in result.skill_check_used
        assert "Tumble" in result.skill_check_used

    def test_mitigation_cannot_reduce_below_zero_distance(self):
        """Skill mitigation cannot make effective distance negative."""
        result = calculate_falling_damage(10, jump_check=15, tumble_check=15)
        assert result.damage == 0
        assert result.dice_rolled == 0

    def test_fall_result_is_dataclass_with_expected_fields(self):
        result = calculate_falling_damage(20)
        assert hasattr(result, "distance_ft")
        assert hasattr(result, "dice_rolled")
        assert hasattr(result, "raw_roll")
        assert hasattr(result, "mitigation")
        assert hasattr(result, "damage")
        assert hasattr(result, "skill_check_used")
        assert result.distance_ft == 20

    def test_damage_within_dice_range(self):
        """Damage is always within valid dice range for any distance."""
        for distance in [10, 50, 100, 200]:
            result = calculate_falling_damage(distance)
            expected_dice = min(20, distance // 10)
            assert result.damage <= expected_dice * 6
            if expected_dice > 0:
                assert result.damage >= expected_dice


# ===========================================================================
# Heat Danger
# ===========================================================================

class TestHeatDanger:
    """Heat exposure per DMG p.303-304."""

    def test_failed_save_deals_nonlethal_damage(self):
        danger = HeatDanger(level=HeatLevel.WARM)
        with patch("src.rules_engine.hazards._d20", return_value=1), \
             patch("src.rules_engine.hazards._roll_dice", return_value=3):
            result = danger.expose(fort_bonus=0)
        assert not result.save_succeeded
        assert result.nonlethal_damage == 3

    def test_passed_save_deals_no_damage(self):
        danger = HeatDanger(level=HeatLevel.WARM)
        with patch("src.rules_engine.hazards._d20", return_value=20):
            result = danger.expose(fort_bonus=5)
        assert result.save_succeeded
        assert result.nonlethal_damage == 0

    def test_dc_escalates_after_failed_saves(self):
        danger = HeatDanger(level=HeatLevel.WARM)
        assert danger.current_dc == 15
        with patch("src.rules_engine.hazards._d20", return_value=1), \
             patch("src.rules_engine.hazards._roll_dice", return_value=2):
            danger.expose(fort_bonus=0)
        assert danger.current_dc == 16

    def test_extreme_heat_deals_lethal_damage_on_failure(self):
        danger = HeatDanger(level=HeatLevel.EXTREME)
        with patch("src.rules_engine.hazards._d20", return_value=1), \
             patch("src.rules_engine.hazards._roll_dice", return_value=4):
            result = danger.expose(fort_bonus=0)
        assert result.lethal_damage == 1
        assert result.nonlethal_damage == 4

    def test_warm_heat_no_lethal_damage(self):
        danger = HeatDanger(level=HeatLevel.WARM)
        with patch("src.rules_engine.hazards._d20", return_value=1), \
             patch("src.rules_engine.hazards._roll_dice", return_value=2):
            result = danger.expose(fort_bonus=0)
        assert result.lethal_damage == 0

    def test_cumulative_nonlethal_accumulates(self):
        danger = HeatDanger(level=HeatLevel.SEVERE)
        with patch("src.rules_engine.hazards._d20", return_value=1), \
             patch("src.rules_engine.hazards._roll_dice", return_value=2):
            danger.expose(fort_bonus=0)
            danger.expose(fort_bonus=0)
        assert danger.cumulative_nonlethal >= 2

    def test_result_has_correct_level(self):
        danger = HeatDanger(level=HeatLevel.SEVERE)
        with patch("src.rules_engine.hazards._d20", return_value=20):
            result = danger.expose(fort_bonus=0)
        assert result.level is HeatLevel.SEVERE

    def test_fort_bonus_affects_save(self):
        """A high enough Fort bonus should always pass DC 15."""
        danger = HeatDanger(level=HeatLevel.WARM)
        with patch("src.rules_engine.hazards._d20", return_value=1):
            # 1 + 15 = 16 >= 15 → pass
            result = danger.expose(fort_bonus=14)
        assert result.save_succeeded


# ===========================================================================
# Cold Danger
# ===========================================================================

class TestColdDanger:
    """Cold exposure per DMG p.302-303."""

    def test_failed_save_deals_nonlethal_d6(self):
        danger = ColdDanger(level=ColdLevel.COLD)
        with patch("src.rules_engine.hazards._d20", return_value=1), \
             patch("src.rules_engine.hazards._roll_dice", return_value=5):
            result = danger.expose(fort_bonus=0)
        assert not result.save_succeeded
        assert result.nonlethal_damage == 5

    def test_passed_save_deals_no_damage(self):
        danger = ColdDanger(level=ColdLevel.COLD)
        with patch("src.rules_engine.hazards._d20", return_value=20):
            result = danger.expose(fort_bonus=0)
        assert result.save_succeeded
        assert result.nonlethal_damage == 0

    def test_extreme_cold_lethal_on_failure(self):
        danger = ColdDanger(level=ColdLevel.EXTREME)
        with patch("src.rules_engine.hazards._d20", return_value=1), \
             patch("src.rules_engine.hazards._roll_dice", return_value=3):
            result = danger.expose(fort_bonus=0)
        assert result.lethal_damage == 1

    def test_dc_escalates(self):
        danger = ColdDanger(level=ColdLevel.SEVERE)
        assert danger.current_dc == 15
        with patch("src.rules_engine.hazards._d20", return_value=1), \
             patch("src.rules_engine.hazards._roll_dice", return_value=2):
            danger.expose(fort_bonus=0)
        assert danger.current_dc == 16

    def test_cumulative_nonlethal_tracked(self):
        danger = ColdDanger(level=ColdLevel.COLD)
        with patch("src.rules_engine.hazards._d20", return_value=1), \
             patch("src.rules_engine.hazards._roll_dice", return_value=4):
            danger.expose(fort_bonus=0)
            danger.expose(fort_bonus=0)
        assert danger.cumulative_nonlethal >= 2


# ===========================================================================
# Starvation & Thirst
# ===========================================================================

class TestStarvationTracker:
    """Starvation and dehydration per DMG p.304."""

    def test_water_grace_period(self):
        tracker = StarvationTracker(constitution_mod=2)
        assert tracker.water_grace_hours == 26

    def test_water_grace_minimum_is_one(self):
        tracker = StarvationTracker(constitution_mod=-5)
        assert tracker.water_grace_hours >= 1

    def test_food_grace_always_3_days(self):
        tracker = StarvationTracker(constitution_mod=3)
        assert tracker.food_grace_days == 3

    def test_no_check_during_water_grace(self):
        tracker = StarvationTracker(constitution_mod=0)
        # First 24 hours are safe
        for _ in range(24):
            result = tracker.advance_hour(fort_bonus=0)
        assert result is None  # last hour still within grace

    def test_check_after_water_grace(self):
        tracker = StarvationTracker(constitution_mod=0)
        # Exhaust grace period
        for _ in range(tracker.water_grace_hours):
            tracker.advance_hour(fort_bonus=99)
        # Next hour should trigger a check
        with patch("src.rules_engine.hazards._d20", return_value=1):
            result = tracker.advance_hour(fort_bonus=0)
        assert result is not None and result >= 0

    def test_no_check_during_food_grace(self):
        tracker = StarvationTracker(constitution_mod=0)
        for _ in range(3):
            result = tracker.advance_day(fort_bonus=0)
        assert result is None

    def test_check_after_food_grace(self):
        tracker = StarvationTracker(constitution_mod=0)
        for _ in range(tracker.food_grace_days):
            tracker.advance_day(fort_bonus=99)
        with patch("src.rules_engine.hazards._d20", return_value=1):
            result = tracker.advance_day(fort_bonus=0)
        assert result is not None and result >= 0

    def test_eat_resets_starvation(self):
        tracker = StarvationTracker(constitution_mod=0)
        tracker.days_without_food = 10
        tracker.eat()
        assert tracker.days_without_food == 0

    def test_drink_resets_dehydration(self):
        tracker = StarvationTracker(constitution_mod=0)
        tracker.hours_without_water = 50
        tracker.drink()
        assert tracker.hours_without_water == 0

    def test_failed_food_save_accumulates_nonlethal(self):
        tracker = StarvationTracker(constitution_mod=0)
        for _ in range(tracker.food_grace_days):
            tracker.advance_day(fort_bonus=99)
        with patch("src.rules_engine.hazards._d20", return_value=1), \
             patch("src.rules_engine.hazards._roll_dice", return_value=4):
            tracker.advance_day(fort_bonus=0)
        assert tracker.cumulative_nonlethal == 4

    def test_dc_escalates_on_food_failure(self):
        tracker = StarvationTracker(constitution_mod=0)
        for _ in range(tracker.food_grace_days):
            tracker.advance_day(fort_bonus=99)
        initial_dc = 10
        with patch("src.rules_engine.hazards._d20", return_value=1), \
             patch("src.rules_engine.hazards._roll_dice", return_value=3):
            tracker.advance_day(fort_bonus=0)
        # Next failed save DC should be 11
        with patch("src.rules_engine.hazards._d20", return_value=1), \
             patch("src.rules_engine.hazards._roll_dice", return_value=3):
            result = tracker.advance_day(fort_bonus=0)
        assert tracker._food_failed_saves == 2


# ===========================================================================
# Poison
# ===========================================================================

class TestPoison:
    """Poison sequence per DMG p.297-298."""

    def test_black_adder_venom_in_registry(self):
        assert "black_adder_venom" in POISON_REGISTRY

    def test_large_scorpion_in_registry(self):
        assert "large_scorpion_venom" in POISON_REGISTRY

    def test_wyvern_poison_in_registry(self):
        assert "wyvern_poison" in POISON_REGISTRY

    def test_initial_save_success_no_effect(self):
        poison = POISON_REGISTRY["black_adder_venom"]
        with patch("src.rules_engine.hazards._d20", return_value=20):
            result = poison.apply_initial(fort_bonus=0)
        assert result.save_succeeded
        assert result.effect == "No effect"
        assert result.ability_damage == {}

    def test_initial_save_failure_applies_effect(self):
        poison = POISON_REGISTRY["black_adder_venom"]
        with patch("src.rules_engine.hazards._d20", return_value=1):
            result = poison.apply_initial(fort_bonus=0)
        assert not result.save_succeeded
        assert result.effect != "No effect"
        assert result.phase is AfflictionPhase.INITIAL

    def test_secondary_save_success_no_effect(self):
        poison = POISON_REGISTRY["black_adder_venom"]
        with patch("src.rules_engine.hazards._d20", return_value=20):
            result = poison.apply_secondary(fort_bonus=0)
        assert result.save_succeeded
        assert result.phase is AfflictionPhase.SECONDARY

    def test_secondary_save_failure_applies_effect(self):
        poison = POISON_REGISTRY["wyvern_poison"]
        with patch("src.rules_engine.hazards._d20", return_value=1):
            result = poison.apply_secondary(fort_bonus=0)
        assert not result.save_succeeded
        assert "CON" in result.ability_damage

    def test_poison_dc_enforced(self):
        """Wyvern poison DC 17: roll of 16 + 0 bonus should fail."""
        poison = POISON_REGISTRY["wyvern_poison"]
        with patch("src.rules_engine.hazards._d20", return_value=16):
            result = poison.apply_initial(fort_bonus=0)
        assert not result.save_succeeded

    def test_poison_dc_pass_at_exactly_dc(self):
        """Roll equal to DC is a success."""
        poison = POISON_REGISTRY["wyvern_poison"]  # DC 17
        with patch("src.rules_engine.hazards._d20", return_value=17):
            result = poison.apply_initial(fort_bonus=0)
        assert result.save_succeeded

    def test_fort_roll_stored_in_result(self):
        poison = POISON_REGISTRY["black_adder_venom"]
        with patch("src.rules_engine.hazards._d20", return_value=10):
            result = poison.apply_initial(fort_bonus=3)
        assert result.fort_roll == 13
        assert result.fort_dc == 11

    def test_ability_damage_present_on_failure(self):
        poison = POISON_REGISTRY["large_scorpion_venom"]
        with patch("src.rules_engine.hazards._d20", return_value=1):
            result = poison.apply_initial(fort_bonus=0)
        assert "STR" in result.ability_damage

    def test_all_registry_poisons_have_required_fields(self):
        for key, poison in POISON_REGISTRY.items():
            assert isinstance(poison.name, str), f"{key}: missing name"
            assert isinstance(poison.dc, int), f"{key}: missing dc"
            assert poison.dc > 0, f"{key}: dc must be positive"
            assert isinstance(poison.delivery, str), f"{key}: missing delivery"


# ===========================================================================
# Disease
# ===========================================================================

class TestDisease:
    """Disease sequence per DMG p.292-293."""

    def test_mummy_rot_in_registry(self):
        assert "mummy_rot" in DISEASE_REGISTRY

    def test_filth_fever_in_registry(self):
        assert "filth_fever" in DISEASE_REGISTRY

    def test_infection_save_success_no_infection(self):
        disease = DISEASE_REGISTRY["mummy_rot"]
        with patch("src.rules_engine.hazards._d20", return_value=20):
            result = disease.roll_infection(fort_bonus=0)
        assert result.save_succeeded
        assert result.effect == "No infection"

    def test_infection_save_failure_infects(self):
        disease = DISEASE_REGISTRY["mummy_rot"]
        with patch("src.rules_engine.hazards._d20", return_value=1):
            result = disease.roll_infection(fort_bonus=0)
        assert not result.save_succeeded
        assert "Mummy Rot" in result.effect

    def test_daily_save_success_no_damage(self):
        disease = DISEASE_REGISTRY["filth_fever"]
        with patch("src.rules_engine.hazards._d20", return_value=20):
            result = disease.roll_daily_save(fort_bonus=0)
        assert result.save_succeeded
        assert result.ability_damage == {}

    def test_daily_save_failure_applies_damage(self):
        disease = DISEASE_REGISTRY["filth_fever"]
        with patch("src.rules_engine.hazards._d20", return_value=1):
            result = disease.roll_daily_save(fort_bonus=0)
        assert not result.save_succeeded
        assert len(result.ability_damage) > 0

    def test_mummy_rot_damages_con_and_cha(self):
        disease = DISEASE_REGISTRY["mummy_rot"]
        with patch("src.rules_engine.hazards._d20", return_value=1):
            result = disease.roll_daily_save(fort_bonus=0)
        assert "CON" in result.ability_damage
        assert "CHA" in result.ability_damage

    def test_disease_phase_is_secondary_for_daily(self):
        disease = DISEASE_REGISTRY["cackle_fever"]
        with patch("src.rules_engine.hazards._d20", return_value=1):
            result = disease.roll_daily_save(fort_bonus=0)
        assert result.phase is AfflictionPhase.SECONDARY

    def test_disease_phase_is_initial_for_infection(self):
        disease = DISEASE_REGISTRY["red_ache"]
        with patch("src.rules_engine.hazards._d20", return_value=1):
            result = disease.roll_infection(fort_bonus=0)
        assert result.phase is AfflictionPhase.INITIAL

    def test_incubation_days_correct_for_red_ache(self):
        disease = DISEASE_REGISTRY["red_ache"]
        assert disease.incubation_days == 3

    def test_mummy_rot_is_contact(self):
        assert DISEASE_REGISTRY["mummy_rot"].disease_type is DiseaseType.CONTACT

    def test_cackle_fever_is_inhaled(self):
        assert DISEASE_REGISTRY["cackle_fever"].disease_type is DiseaseType.INHALED

    def test_all_registry_diseases_have_required_fields(self):
        for key, disease in DISEASE_REGISTRY.items():
            assert isinstance(disease.name, str), f"{key}: missing name"
            assert isinstance(disease.dc, int), f"{key}: dc must be int"
            assert disease.dc > 0, f"{key}: dc must be positive"
            assert disease.incubation_days >= 1, f"{key}: incubation must be ≥ 1"

    def test_daily_save_at_exact_dc_succeeds(self):
        disease = DISEASE_REGISTRY["filth_fever"]  # DC 12
        with patch("src.rules_engine.hazards._d20", return_value=12):
            result = disease.roll_daily_save(fort_bonus=0)
        assert result.save_succeeded

    def test_fort_roll_stored_in_result(self):
        disease = DISEASE_REGISTRY["shakes"]
        with patch("src.rules_engine.hazards._d20", return_value=8):
            result = disease.roll_daily_save(fort_bonus=4)
        assert result.fort_roll == 12
        assert result.fort_dc == 13


# ===========================================================================
# AfflictionResult dataclass
# ===========================================================================

class TestAfflictionResult:
    """Verify AfflictionResult slots/fields."""

    def test_affliction_result_fields(self):
        result = AfflictionResult(
            phase=AfflictionPhase.INITIAL,
            fort_dc=15,
            fort_roll=10,
            save_succeeded=False,
            effect="1d6 CON",
            ability_damage={"CON": 2},
        )
        assert result.phase is AfflictionPhase.INITIAL
        assert result.fort_dc == 15
        assert result.fort_roll == 10
        assert not result.save_succeeded
        assert result.effect == "1d6 CON"
        assert result.ability_damage == {"CON": 2}
