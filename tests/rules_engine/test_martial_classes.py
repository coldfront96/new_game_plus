"""
tests/rules_engine/test_martial_classes.py
-------------------------------------------
Unit tests for martial class abilities:

* Rogue Sneak Attack — Level 1 Rogue adds 1d6 to attacks against
  flat-footed targets without Uncanny Dodge.
* Barbarian Rage — RageManager correctly applies bonuses and grants
  temporary HP on activation.
* Monk unarmed damage progression — AttackResolver uses the 3.5e SRD
  Monk unarmed strike table when no weapon dice are supplied.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.rules_engine.abilities import (
    RageManager,
    RageState,
    SneakAttack,
)
from src.rules_engine.character_35e import Character35e, Size
from src.rules_engine.combat import AttackResolver, CombatResult
from src.rules_engine.dice import RollResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def level1_rogue():
    return Character35e(
        name="Shadow",
        char_class="Rogue",
        level=1,
        strength=10,
        dexterity=14,
    )


@pytest.fixture
def level3_rogue():
    return Character35e(
        name="Shadow3",
        char_class="Rogue",
        level=3,
        strength=10,
        dexterity=14,
    )


@pytest.fixture
def flat_footed_target():
    """A Fighter without Uncanny Dodge — eligible for Sneak Attack."""
    return Character35e(
        name="Guard",
        char_class="Fighter",
        level=1,
        strength=10,
        dexterity=10,
    )


@pytest.fixture
def uncanny_dodge_target():
    """A Rogue at level 4 (has Uncanny Dodge) — immune to Sneak Attack."""
    return Character35e(
        name="Veteran",
        char_class="Rogue",
        level=4,
        strength=10,
        dexterity=12,
    )


@pytest.fixture
def level1_barbarian():
    return Character35e(
        name="Grok",
        char_class="Barbarian",
        level=1,
        strength=16,
        constitution=12,
    )


@pytest.fixture
def level4_barbarian():
    return Character35e(
        name="Gorak",
        char_class="Barbarian",
        level=4,
        strength=18,
        constitution=14,
    )


@pytest.fixture
def level1_monk():
    return Character35e(
        name="Kira",
        char_class="Monk",
        level=1,
        strength=12,
        wisdom=14,
    )


@pytest.fixture
def level4_monk():
    return Character35e(
        name="Kira4",
        char_class="Monk",
        level=4,
        strength=12,
        wisdom=14,
    )


# ---------------------------------------------------------------------------
# SneakAttack — dice count
# ---------------------------------------------------------------------------

class TestSneakAttackDiceCount:
    def test_level1_is_1d6(self):
        assert SneakAttack.dice_count(1) == 1

    def test_level2_is_1d6(self):
        assert SneakAttack.dice_count(2) == 1

    def test_level3_is_2d6(self):
        assert SneakAttack.dice_count(3) == 2

    def test_level5_is_3d6(self):
        assert SneakAttack.dice_count(5) == 3

    def test_level20_is_10d6(self):
        assert SneakAttack.dice_count(20) == 10


# ---------------------------------------------------------------------------
# RageState dataclass
# ---------------------------------------------------------------------------

class TestRageState:
    def test_slots_enabled(self):
        assert hasattr(RageState, "__slots__")

    def test_defaults(self):
        state = RageState()
        assert state.active is False
        assert state.str_bonus == 0
        assert state.con_bonus == 0
        assert state.will_bonus == 0
        assert state.ac_penalty == 0
        assert state.temp_hp == 0


# ---------------------------------------------------------------------------
# RageManager — uses per day
# ---------------------------------------------------------------------------

class TestRageManagerUsesPerDay:
    def test_level1_has_1_use(self):
        rm = RageManager.for_barbarian(1)
        assert rm.uses_per_day == 1

    def test_level4_has_2_uses(self):
        rm = RageManager.for_barbarian(4)
        assert rm.uses_per_day == 2

    def test_level8_has_3_uses(self):
        rm = RageManager.for_barbarian(8)
        assert rm.uses_per_day == 3

    def test_level12_has_4_uses(self):
        rm = RageManager.for_barbarian(12)
        assert rm.uses_per_day == 4

    def test_uses_remaining_equals_per_day(self):
        rm = RageManager.for_barbarian(5)
        assert rm.uses_remaining == rm.uses_per_day


# ---------------------------------------------------------------------------
# RageManager — activation
# ---------------------------------------------------------------------------

class TestRageManagerActivation:
    def test_activate_returns_state(self, level1_barbarian):
        rm = RageManager.for_barbarian(1)
        state = rm.activate(level1_barbarian)
        assert state is not None
        assert state.active is True

    def test_activate_str_bonus(self, level1_barbarian):
        rm = RageManager.for_barbarian(1)
        state = rm.activate(level1_barbarian)
        assert state.str_bonus == 4

    def test_activate_con_bonus(self, level1_barbarian):
        rm = RageManager.for_barbarian(1)
        state = rm.activate(level1_barbarian)
        assert state.con_bonus == 4

    def test_activate_will_bonus(self, level1_barbarian):
        rm = RageManager.for_barbarian(1)
        state = rm.activate(level1_barbarian)
        assert state.will_bonus == 2

    def test_activate_ac_penalty(self, level1_barbarian):
        rm = RageManager.for_barbarian(1)
        state = rm.activate(level1_barbarian)
        assert state.ac_penalty == -2

    def test_activate_temp_hp_level1(self, level1_barbarian):
        """Level 1 Barbarian gains 2 temp HP (2 × 1) from Rage."""
        rm = RageManager.for_barbarian(1)
        state = rm.activate(level1_barbarian)
        assert state.temp_hp == 2

    def test_activate_temp_hp_level4(self, level4_barbarian):
        """Level 4 Barbarian gains 8 temp HP (2 × 4) from Rage."""
        rm = RageManager.for_barbarian(4)
        state = rm.activate(level4_barbarian)
        assert state.temp_hp == 8

    def test_activate_decrements_uses(self, level1_barbarian):
        rm = RageManager.for_barbarian(1)
        rm.activate(level1_barbarian)
        assert rm.uses_remaining == 0

    def test_cannot_double_activate(self, level1_barbarian):
        rm = RageManager.for_barbarian(2)
        rm.activate(level1_barbarian)
        result = rm.activate(level1_barbarian)
        assert result is None

    def test_cannot_activate_with_no_uses(self, level1_barbarian):
        rm = RageManager.for_barbarian(1)
        rm.activate(level1_barbarian)
        rm.deactivate()
        result = rm.activate(level1_barbarian)
        assert result is None

    def test_rest_restores_uses(self, level1_barbarian):
        rm = RageManager.for_barbarian(1)
        rm.activate(level1_barbarian)
        rm.deactivate()
        rm.rest()
        assert rm.uses_remaining == rm.uses_per_day

    def test_deactivate_clears_state(self, level1_barbarian):
        rm = RageManager.for_barbarian(1)
        rm.activate(level1_barbarian)
        rm.deactivate()
        assert rm.state.active is False
        assert rm.state.temp_hp == 0
        assert rm.state.str_bonus == 0


# ---------------------------------------------------------------------------
# AttackResolver — Rogue Sneak Attack
# ---------------------------------------------------------------------------

class TestSneakAttack:
    def _make_guaranteed_hit(self, attacker_bonus: int, defender_ac: int):
        """Return a mock RollResult that always hits (raw=20, total beats AC)."""
        return RollResult(raw=20, modifier=attacker_bonus, total=20 + attacker_bonus)

    def test_sneak_attack_added_to_flat_footed_target(
        self, level1_rogue, flat_footed_target
    ):
        """Level 1 Rogue adds ≥1 sneak attack damage to a flat-footed target."""
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg, \
             patch("src.rules_engine.abilities.roll_dice") as mock_sa:
            atk_bonus = level1_rogue.melee_attack
            mock_d20.return_value = RollResult(
                raw=10, modifier=atk_bonus, total=10 + atk_bonus
            )
            mock_dmg.return_value = RollResult(raw=1, modifier=0, total=1)
            mock_sa.return_value = RollResult(raw=4, modifier=0, total=4)

            result = AttackResolver.resolve_attack(
                level1_rogue,
                flat_footed_target,
                target_is_flat_footed=True,
            )

        assert result.hit is True
        assert result.sneak_attack_damage == 4
        assert result.total_damage == 1 + 4  # base + sneak

    def test_sneak_attack_not_applied_without_flat_footed(
        self, level1_rogue, flat_footed_target
    ):
        """Rogue does NOT get Sneak Attack when target is not flat-footed."""
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            atk_bonus = level1_rogue.melee_attack
            mock_d20.return_value = RollResult(
                raw=10, modifier=atk_bonus, total=10 + atk_bonus
            )
            mock_dmg.return_value = RollResult(raw=2, modifier=0, total=2)

            result = AttackResolver.resolve_attack(
                level1_rogue,
                flat_footed_target,
                target_is_flat_footed=False,
            )

        assert result.sneak_attack_damage == 0

    def test_sneak_attack_not_applied_against_uncanny_dodge(
        self, level1_rogue, uncanny_dodge_target
    ):
        """Rogue Sneak Attack is blocked by the target's Uncanny Dodge."""
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            atk_bonus = level1_rogue.melee_attack
            mock_d20.return_value = RollResult(
                raw=10, modifier=atk_bonus, total=10 + atk_bonus
            )
            mock_dmg.return_value = RollResult(raw=2, modifier=0, total=2)

            result = AttackResolver.resolve_attack(
                level1_rogue,
                uncanny_dodge_target,
                target_is_flat_footed=True,
            )

        assert result.sneak_attack_damage == 0

    def test_level3_rogue_rolls_2d6_sneak_attack(
        self, level3_rogue, flat_footed_target
    ):
        """Level 3 Rogue rolls 2d6 Sneak Attack dice."""
        assert SneakAttack.dice_count(3) == 2

        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg, \
             patch("src.rules_engine.abilities.roll_dice") as mock_sa:
            atk_bonus = level3_rogue.melee_attack
            mock_d20.return_value = RollResult(
                raw=10, modifier=atk_bonus, total=10 + atk_bonus
            )
            mock_dmg.return_value = RollResult(raw=1, modifier=0, total=1)
            mock_sa.return_value = RollResult(raw=8, modifier=0, total=8)

            result = AttackResolver.resolve_attack(
                level3_rogue,
                flat_footed_target,
                target_is_flat_footed=True,
            )

        assert result.sneak_attack_damage == 8

    def test_non_rogue_gets_no_sneak_attack(self, flat_footed_target):
        """A Fighter against a flat-footed target gets no Sneak Attack."""
        fighter = Character35e(
            name="Warrior", char_class="Fighter", level=1, strength=14
        )
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            atk_bonus = fighter.melee_attack
            mock_d20.return_value = RollResult(
                raw=10, modifier=atk_bonus, total=10 + atk_bonus
            )
            mock_dmg.return_value = RollResult(raw=3, modifier=2, total=5)

            result = AttackResolver.resolve_attack(
                fighter,
                flat_footed_target,
                target_is_flat_footed=True,
            )

        assert result.sneak_attack_damage == 0


# ---------------------------------------------------------------------------
# AttackResolver — Monk unarmed damage
# ---------------------------------------------------------------------------

class TestMonkUnarmedProgression:
    """Verify AttackResolver uses the 3.5e Monk unarmed strike table."""

    def _resolve_monk_hit(self, monk: Character35e, dummy: Character35e):
        """Helper: force a hit and return the dice (count, sides) used."""
        recorded: list = []

        original_roll_dice = __import__(
            "src.rules_engine.combat", fromlist=["roll_dice"]
        ).roll_dice

        def capturing_roll_dice(count, sides, modifier=0):
            recorded.append((count, sides))
            return original_roll_dice(count, sides, modifier)

        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice", side_effect=capturing_roll_dice):
            atk_bonus = monk.melee_attack
            mock_d20.return_value = RollResult(
                raw=15, modifier=atk_bonus, total=15 + atk_bonus
            )
            AttackResolver.resolve_attack(monk, dummy)

        return recorded[0] if recorded else None

    @pytest.fixture
    def dummy(self):
        return Character35e(name="Dummy", char_class="Fighter", level=1)

    def test_monk_level1_uses_1d6(self, dummy):
        monk = Character35e(name="Kira", char_class="Monk", level=1, strength=10)
        dice = self._resolve_monk_hit(monk, dummy)
        assert dice == (1, 6)

    def test_monk_level3_uses_1d6(self, dummy):
        monk = Character35e(name="Kira", char_class="Monk", level=3, strength=10)
        dice = self._resolve_monk_hit(monk, dummy)
        assert dice == (1, 6)

    def test_monk_level4_uses_1d8(self, dummy):
        monk = Character35e(name="Kira", char_class="Monk", level=4, strength=10)
        dice = self._resolve_monk_hit(monk, dummy)
        assert dice == (1, 8)

    def test_monk_level8_uses_1d10(self, dummy):
        monk = Character35e(name="Kira", char_class="Monk", level=8, strength=10)
        dice = self._resolve_monk_hit(monk, dummy)
        assert dice == (1, 10)

    def test_monk_level12_uses_2d6(self, dummy):
        monk = Character35e(name="Kira", char_class="Monk", level=12, strength=10)
        dice = self._resolve_monk_hit(monk, dummy)
        assert dice == (2, 6)

    def test_monk_level16_uses_2d8(self, dummy):
        monk = Character35e(name="Kira", char_class="Monk", level=16, strength=10)
        dice = self._resolve_monk_hit(monk, dummy)
        assert dice == (2, 8)

    def test_monk_with_weapon_uses_provided_dice(self, dummy):
        """When dice are explicitly provided, do not override with Monk table."""
        monk = Character35e(name="Kira", char_class="Monk", level=1, strength=10)
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            atk_bonus = monk.melee_attack
            mock_d20.return_value = RollResult(
                raw=15, modifier=atk_bonus, total=15 + atk_bonus
            )
            mock_dmg.return_value = RollResult(raw=4, modifier=1, total=5)
            result = AttackResolver.resolve_attack(
                monk, dummy, damage_dice_count=1, damage_dice_sides=4
            )
            # roll_dice should be called with (1, 4, ...) not (1, 6)
            call_args = mock_dmg.call_args
            assert call_args[0][0] == 1
            assert call_args[0][1] == 4


# ---------------------------------------------------------------------------
# Monk AC — Wisdom bonus
# ---------------------------------------------------------------------------

class TestMonkAC:
    def test_monk_adds_wisdom_to_ac(self, level1_monk):
        """Monk with WIS 14 (+2) has AC 10 + 2 = 12 (unarmored)."""
        # WIS 14 → mod +2; AC = 10 + 0 (DEX 10) + 0 (size) + 2 (WIS) = 12
        assert level1_monk.armor_class == 12

    def test_monk_adds_wisdom_to_flat_footed_ac(self, level1_monk):
        """Monk retains WIS bonus to flat-footed AC."""
        assert level1_monk.flat_footed_ac == 12

    def test_non_monk_no_wisdom_bonus(self):
        """Non-Monk with high WIS does NOT add WIS to AC."""
        cleric = Character35e(
            name="Priest", char_class="Cleric", level=1, wisdom=18
        )
        # AC = 10 + 0 (DEX 10) + 0 (size) = 10 (no WIS bonus for Cleric)
        assert cleric.armor_class == 10

    def test_monk_negative_wisdom_not_subtracted(self):
        """Monk with negative WIS modifier does not subtract from AC."""
        monk = Character35e(
            name="Klumsy", char_class="Monk", level=1, wisdom=6
        )
        # WIS 6 → mod -2; only positive WIS adds to AC per SRD
        assert monk.armor_class == 10
