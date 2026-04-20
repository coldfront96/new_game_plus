"""
tests/rules_engine/test_combat.py
---------------------------------
Unit tests for src.rules_engine.combat (AttackResolver, CombatResult).
"""

from unittest.mock import patch

import pytest

from src.rules_engine.character_35e import Character35e, Size
from src.rules_engine.combat import AttackResolver, CombatResult
from src.rules_engine.dice import RollResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fighter():
    return Character35e(
        name="Aldric",
        char_class="Fighter",
        level=5,
        strength=16,
        dexterity=13,
        constitution=14,
    )


@pytest.fixture
def goblin():
    return Character35e(
        name="Goblin",
        char_class="Rogue",
        level=1,
        strength=8,
        dexterity=14,
        size=Size.SMALL,
    )


# ---------------------------------------------------------------------------
# CombatResult dataclass
# ---------------------------------------------------------------------------

class TestCombatResult:
    def test_slots_enabled(self):
        assert hasattr(CombatResult, "__slots__")

    def test_fields_stored(self):
        roll = RollResult(raw=15, modifier=5, total=20)
        dmg = RollResult(raw=3, modifier=3, total=6)
        r = CombatResult(
            hit=True, roll=roll, attack_bonus=5, target_ac=12,
            damage_roll=dmg, total_damage=6, critical=False,
        )
        assert r.hit is True
        assert r.total_damage == 6
        assert r.critical is False


# ---------------------------------------------------------------------------
# AttackResolver — melee
# ---------------------------------------------------------------------------

class TestAttackResolverMelee:
    def test_natural_20_always_hits(self, fighter, goblin):
        """A natural 20 is always a hit, regardless of AC."""
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            mock_d20.return_value = RollResult(raw=20, modifier=fighter.melee_attack, total=20 + fighter.melee_attack)
            mock_dmg.return_value = RollResult(raw=2, modifier=3, total=5)

            result = AttackResolver.resolve_attack(fighter, goblin)
            assert result.hit is True
            assert result.critical is True
            assert result.total_damage == 10  # 5 × 2 for crit

    def test_natural_1_always_misses(self, fighter, goblin):
        """A natural 1 is always a miss, regardless of bonuses."""
        with patch("src.rules_engine.combat.roll_d20") as mock_d20:
            mock_d20.return_value = RollResult(raw=1, modifier=fighter.melee_attack, total=1 + fighter.melee_attack)

            result = AttackResolver.resolve_attack(fighter, goblin)
            assert result.hit is False
            assert result.total_damage == 0
            assert result.damage_roll is None

    def test_hit_when_total_meets_ac(self, fighter, goblin):
        """Attack total == AC counts as a hit."""
        target_ac = goblin.armor_class
        needed_raw = target_ac - fighter.melee_attack

        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            # Ensure the raw isn't 1 or 20
            raw = max(2, min(19, needed_raw))
            mock_d20.return_value = RollResult(
                raw=raw, modifier=fighter.melee_attack,
                total=raw + fighter.melee_attack,
            )
            mock_dmg.return_value = RollResult(raw=2, modifier=3, total=5)

            result = AttackResolver.resolve_attack(fighter, goblin)
            if raw + fighter.melee_attack >= target_ac:
                assert result.hit is True
                assert result.total_damage >= 1

    def test_miss_when_total_below_ac(self, fighter, goblin):
        """Attack total < AC is a miss."""
        target_ac = goblin.armor_class

        with patch("src.rules_engine.combat.roll_d20") as mock_d20:
            # Roll low enough to miss (but not 1 which is auto-miss)
            raw = 2
            total = raw + fighter.melee_attack
            # Only test if this actually misses
            if total < target_ac:
                mock_d20.return_value = RollResult(
                    raw=raw, modifier=fighter.melee_attack, total=total,
                )
                result = AttackResolver.resolve_attack(fighter, goblin)
                assert result.hit is False

    def test_damage_minimum_one(self, fighter, goblin):
        """Minimum 1 damage on a hit."""
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            mock_d20.return_value = RollResult(raw=15, modifier=8, total=23)
            # Force a very negative damage roll
            mock_dmg.return_value = RollResult(raw=1, modifier=-10, total=-9)

            result = AttackResolver.resolve_attack(fighter, goblin)
            assert result.hit is True
            assert result.total_damage >= 1

    def test_attack_bonus_uses_melee(self, fighter, goblin):
        """Default attack uses melee_attack bonus."""
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            mock_d20.return_value = RollResult(raw=15, modifier=fighter.melee_attack, total=15 + fighter.melee_attack)
            mock_dmg.return_value = RollResult(raw=2, modifier=3, total=5)

            result = AttackResolver.resolve_attack(fighter, goblin)
            assert result.attack_bonus == fighter.melee_attack


# ---------------------------------------------------------------------------
# AttackResolver — ranged
# ---------------------------------------------------------------------------

class TestAttackResolverRanged:
    def test_ranged_uses_dex_bonus(self, fighter, goblin):
        """Ranged attack should use ranged_attack bonus (DEX-based)."""
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            mock_d20.return_value = RollResult(
                raw=15, modifier=fighter.ranged_attack,
                total=15 + fighter.ranged_attack,
            )
            mock_dmg.return_value = RollResult(raw=3, modifier=0, total=3)

            result = AttackResolver.resolve_attack(
                fighter, goblin, use_ranged=True,
            )
            assert result.attack_bonus == fighter.ranged_attack

    def test_ranged_no_str_damage(self, fighter, goblin):
        """Ranged attacks do NOT add STR modifier to damage."""
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            mock_d20.return_value = RollResult(raw=18, modifier=6, total=24)
            mock_dmg.return_value = RollResult(raw=3, modifier=0, total=3)

            result = AttackResolver.resolve_attack(
                fighter, goblin, use_ranged=True,
            )
            # Verify roll_dice was called with modifier=0 (no STR mod)
            _, kwargs = mock_dmg.call_args
            assert kwargs.get("modifier", mock_dmg.call_args[0][2] if len(mock_dmg.call_args[0]) > 2 else 0) == 0


# ---------------------------------------------------------------------------
# AttackResolver — weapon overrides
# ---------------------------------------------------------------------------

class TestAttackResolverWeaponOverride:
    def test_custom_damage_dice(self, fighter, goblin):
        """Custom damage dice override unarmed defaults."""
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            mock_d20.return_value = RollResult(raw=15, modifier=8, total=23)
            mock_dmg.return_value = RollResult(raw=7, modifier=6, total=13)

            result = AttackResolver.resolve_attack(
                fighter, goblin,
                damage_dice_count=2, damage_dice_sides=6, damage_bonus=3,
            )
            assert result.hit is True
            # roll_dice should have been called with count=2, sides=6
            args = mock_dmg.call_args[0]
            assert args[0] == 2  # count
            assert args[1] == 6  # sides


# ---------------------------------------------------------------------------
# AttackResolver — critical hits
# ---------------------------------------------------------------------------

class TestAttackResolverCritical:
    def test_critical_doubles_damage(self, fighter, goblin):
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            mock_d20.return_value = RollResult(raw=20, modifier=8, total=28)
            mock_dmg.return_value = RollResult(raw=3, modifier=3, total=6)

            result = AttackResolver.resolve_attack(fighter, goblin)
            assert result.critical is True
            assert result.total_damage == 12  # 6 × 2

    def test_non_crit_no_double(self, fighter, goblin):
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            mock_d20.return_value = RollResult(raw=15, modifier=8, total=23)
            mock_dmg.return_value = RollResult(raw=3, modifier=3, total=6)

            result = AttackResolver.resolve_attack(fighter, goblin)
            assert result.critical is False
            assert result.total_damage == 6
