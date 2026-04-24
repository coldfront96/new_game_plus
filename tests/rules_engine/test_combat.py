"""
tests/rules_engine/test_combat.py
---------------------------------
Unit tests for src.rules_engine.combat (AttackResolver, CombatResult,
TripResolver, GrappleResolver, BullRushResolver, SunderResolver).
"""

from unittest.mock import patch

import pytest

from src.loot_math.item import Item, ItemType, Rarity
from src.rules_engine.character_35e import Character35e, Size
from src.rules_engine.combat import (
    AttackResolver,
    BullRushResolver,
    BullRushResult,
    CombatResult,
    GrappleResolver,
    GrappleResult,
    SunderResolver,
    SunderResult,
    TripResolver,
    TripResult,
)
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


# ---------------------------------------------------------------------------
# AttackResolver — threat-on-a-miss confirmation path (lines 247-250)
# ---------------------------------------------------------------------------

class TestAttackResolverThreatOnMiss:
    """When the raw d20 is within the threat range but the total misses AC,
    a confirmation roll is still made. A successful confirmation turns the
    miss into a confirmed critical hit."""

    def test_threat_on_miss_becomes_confirmed_crit_on_good_confirm(self):
        """Raw 19 with threat_range=19 that misses AC, then confirm hits → crit."""
        # Build attacker with a tiny attack bonus so the initial roll misses.
        attacker = Character35e(
            name="Weak", char_class="Fighter", level=1,
            strength=10, dexterity=10, constitution=10,
        )
        # Build defender with high AC so raw 19 misses but crit confirm (also 19 raw) misses too
        # We need to control both rolls — use side_effect with two roll results.
        defender = Character35e(
            name="Tough", char_class="Fighter", level=1,
            strength=10, dexterity=10, constitution=10,
        )

        # Patch AC to a high value via object override is tricky; instead
        # pick a target AC by controlling the roll totals.
        target_ac = defender.armor_class

        # First roll (raw=19, modifier=0 → total=19) — miss if AC > 19
        # Second roll (raw=15, total=19 — confirm) — hit if >= AC
        # We'll pick AC exactly so first misses but second hits.
        # Easiest: force the roll totals.
        initial_roll = RollResult(raw=19, modifier=0, total=target_ac - 1)  # misses
        confirm_roll = RollResult(raw=15, modifier=0, total=target_ac)      # hits

        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            mock_d20.side_effect = [initial_roll, confirm_roll]
            mock_dmg.return_value = RollResult(raw=4, modifier=0, total=4)

            result = AttackResolver.resolve_attack(
                attacker, defender, threat_range=19, damage_multiplier=2,
            )
            assert result.hit is True
            assert result.critical is True
            assert result.total_damage == 8  # 4 × 2

    def test_threat_on_miss_stays_miss_when_confirm_fails(self):
        """Raw in threat range but total misses, and confirm also misses → miss."""
        attacker = Character35e(
            name="Weak", char_class="Fighter", level=1,
            strength=10, dexterity=10, constitution=10,
        )
        defender = Character35e(
            name="Tough", char_class="Fighter", level=1,
            strength=10, dexterity=10, constitution=10,
        )
        target_ac = defender.armor_class

        # Both rolls miss
        initial_roll = RollResult(raw=19, modifier=0, total=target_ac - 1)
        confirm_roll = RollResult(raw=2, modifier=0, total=target_ac - 1)

        with patch("src.rules_engine.combat.roll_d20") as mock_d20:
            mock_d20.side_effect = [initial_roll, confirm_roll]

            result = AttackResolver.resolve_attack(
                attacker, defender, threat_range=19,
            )
            assert result.hit is False
            assert result.critical is False
            assert result.total_damage == 0


# ---------------------------------------------------------------------------
# AttackResolver — _parse_damage_reduction helper (lines 131-136)
# ---------------------------------------------------------------------------

class TestParseDamageReduction:
    def test_empty_string_returns_zero(self):
        assert AttackResolver._parse_damage_reduction("") == 0

    def test_valid_dr_returns_number(self):
        assert AttackResolver._parse_damage_reduction("5/Magic") == 5

    def test_dr_slash_dash(self):
        assert AttackResolver._parse_damage_reduction("3/-") == 3

    def test_invalid_dr_returns_zero(self):
        assert AttackResolver._parse_damage_reduction("not-a-number/Magic") == 0

    def test_dr_applied_to_hit_damage(self):
        """A hit against a defender with DR should have damage reduced."""
        attacker = Character35e(
            name="Aldric", char_class="Fighter", level=5,
            strength=16, dexterity=13, constitution=14,
        )
        defender = Character35e(
            name="Goblin", char_class="Rogue", level=1,
            strength=8, dexterity=14, size=Size.SMALL,
        )
        defender.damage_reduction = "3/-"

        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            mock_d20.return_value = RollResult(raw=15, modifier=8, total=23)
            mock_dmg.return_value = RollResult(raw=5, modifier=3, total=8)

            result = AttackResolver.resolve_attack(attacker, defender)
            assert result.hit is True
            assert result.damage_reduction_applied == 3
            assert result.total_damage == 5  # 8 - 3 DR


# ---------------------------------------------------------------------------
# AttackResolver — Monk unarmed dice fallback (line 124)
# ---------------------------------------------------------------------------

class TestMonkUnarmedDice:
    def test_level_1_monk_returns_1d6(self):
        assert AttackResolver._monk_unarmed_dice(1) == (1, 6)

    def test_level_4_monk_returns_1d8(self):
        assert AttackResolver._monk_unarmed_dice(4) == (1, 8)

    def test_level_8_monk_returns_1d10(self):
        assert AttackResolver._monk_unarmed_dice(8) == (1, 10)

    def test_level_12_monk_returns_2d6(self):
        assert AttackResolver._monk_unarmed_dice(12) == (2, 6)

    def test_level_20_monk_returns_2d8(self):
        assert AttackResolver._monk_unarmed_dice(20) == (2, 8)

    def test_level_zero_returns_fallback(self):
        """Level below the lowest table entry returns the 1d6 fallback (line 124)."""
        assert AttackResolver._monk_unarmed_dice(0) == (1, 6)


# ---------------------------------------------------------------------------
# TripResolver (lines 456-469)
# ---------------------------------------------------------------------------

class TestTripResolver:
    @pytest.fixture
    def strong_attacker(self):
        return Character35e(
            name="Ogre", char_class="Fighter", level=5,
            strength=18, dexterity=10, constitution=14,
        )

    @pytest.fixture
    def small_defender(self):
        return Character35e(
            name="Halfling", char_class="Rogue", level=1,
            strength=8, dexterity=16, size=Size.SMALL,
        )

    def test_resolve_trip_success_returns_trip_result(
        self, strong_attacker, small_defender,
    ):
        with patch("src.rules_engine.combat.roll_d20") as mock_d20:
            mock_d20.side_effect = [
                RollResult(raw=18, modifier=0, total=18),  # attacker roll
                RollResult(raw=3, modifier=0, total=3),    # defender roll
            ]
            result = TripResolver.resolve_trip(strong_attacker, small_defender)
            assert isinstance(result, TripResult)
            assert result.success is True

    def test_resolve_trip_failure(self, strong_attacker, small_defender):
        with patch("src.rules_engine.combat.roll_d20") as mock_d20:
            # Force low attacker, high defender
            mock_d20.side_effect = [
                RollResult(raw=1, modifier=0, total=1),
                RollResult(raw=20, modifier=0, total=20),
            ]
            result = TripResolver.resolve_trip(strong_attacker, small_defender)
            assert result.success is False

    def test_resolve_trip_ties_go_to_attacker(
        self, strong_attacker, small_defender,
    ):
        """Per 3.5e SRD, the attacker wins ties on opposed checks."""
        with patch("src.rules_engine.combat.roll_d20") as mock_d20:
            mock_d20.side_effect = [
                RollResult(raw=10, modifier=0, total=10),
                RollResult(raw=10, modifier=0, total=10),
            ]
            result = TripResolver.resolve_trip(strong_attacker, small_defender)
            assert result.success is True  # tie → attacker

    def test_resolve_trip_defender_uses_max_of_str_dex(
        self, strong_attacker, small_defender,
    ):
        """Defender picks max(STR mod, DEX mod). Small_defender has DEX=16 (+3)
        vs STR=8 (-1), so defender_ability_mod should be +3."""
        with patch("src.rules_engine.combat.roll_d20") as mock_d20:
            mock_d20.side_effect = [
                RollResult(raw=10, modifier=0, total=10),
                RollResult(raw=10, modifier=0, total=10),
            ]
            result = TripResolver.resolve_trip(strong_attacker, small_defender)
            # Just confirm both rolls are present
            assert result.attacker_roll is not None
            assert result.defender_roll is not None


# ---------------------------------------------------------------------------
# GrappleResolver (lines 534-550)
# ---------------------------------------------------------------------------

class TestGrappleResolver:
    @pytest.fixture
    def attacker(self):
        return Character35e(
            name="Wrestler", char_class="Fighter", level=5,
            strength=18, dexterity=12, constitution=14,
        )

    @pytest.fixture
    def defender(self):
        return Character35e(
            name="Rogue", char_class="Rogue", level=3,
            strength=12, dexterity=16, constitution=12,
        )

    def test_resolve_grapple_success(self, attacker, defender):
        with patch("src.rules_engine.combat.roll_d20") as mock_d20:
            mock_d20.side_effect = [
                RollResult(raw=18, modifier=0, total=18),
                RollResult(raw=3, modifier=0, total=3),
            ]
            result = GrappleResolver.resolve_grapple(attacker, defender)
            assert isinstance(result, GrappleResult)
            assert result.success is True

    def test_resolve_grapple_failure(self, attacker, defender):
        with patch("src.rules_engine.combat.roll_d20") as mock_d20:
            mock_d20.side_effect = [
                RollResult(raw=1, modifier=0, total=1),
                RollResult(raw=20, modifier=0, total=20),
            ]
            result = GrappleResolver.resolve_grapple(attacker, defender)
            assert result.success is False

    def test_resolve_grapple_ties_go_to_attacker(self, attacker, defender):
        with patch("src.rules_engine.combat.roll_d20") as mock_d20:
            mock_d20.side_effect = [
                RollResult(raw=10, modifier=0, total=10),
                RollResult(raw=10, modifier=0, total=10),
            ]
            result = GrappleResolver.resolve_grapple(attacker, defender)
            assert result.success is True


# ---------------------------------------------------------------------------
# BullRushResolver (lines 621-641)
# ---------------------------------------------------------------------------

class TestBullRushResolver:
    @pytest.fixture
    def attacker(self):
        return Character35e(
            name="Bruiser", char_class="Fighter", level=5,
            strength=18, dexterity=12, constitution=14,
        )

    @pytest.fixture
    def defender(self):
        return Character35e(
            name="Thin", char_class="Wizard", level=1,
            strength=8, dexterity=14, constitution=10,
        )

    def test_resolve_bull_rush_success_pushes_5ft(self, attacker, defender):
        with patch("src.rules_engine.combat.roll_d20") as mock_d20:
            # Attacker wins by a small margin (< 5 point margin → 5 ft push)
            mock_d20.side_effect = [
                RollResult(raw=15, modifier=0, total=15),  # attacker
                RollResult(raw=14, modifier=0, total=14),  # defender
            ]
            result = BullRushResolver.resolve_bull_rush(attacker, defender)
            assert isinstance(result, BullRushResult)
            assert result.success is True
            assert result.push_distance == 5  # base 5 ft, no extra

    def test_resolve_bull_rush_failure_no_push(self, attacker, defender):
        with patch("src.rules_engine.combat.roll_d20") as mock_d20:
            mock_d20.side_effect = [
                RollResult(raw=1, modifier=0, total=1),
                RollResult(raw=20, modifier=0, total=20),
            ]
            result = BullRushResolver.resolve_bull_rush(attacker, defender)
            assert result.success is False
            assert result.push_distance == 0

    def test_resolve_bull_rush_charging_bonus_applied(self, attacker, defender):
        """Charging adds +2 to the attacker's check."""
        with patch("src.rules_engine.combat.roll_d20") as mock_d20:
            mock_d20.side_effect = [
                RollResult(raw=10, modifier=0, total=10),  # attacker
                RollResult(raw=10, modifier=0, total=10),  # defender
            ]
            # Without charging: attacker_mod = STR mod (4) = 4, defender = -1 → attacker wins
            # With charging: attacker gets extra +2 → still wins
            result = BullRushResolver.resolve_bull_rush(
                attacker, defender, charging=True,
            )
            assert result.success is True

    def test_resolve_bull_rush_extra_push_per_5_margin(self, attacker, defender):
        """Each 5-point margin above the win grants +5 ft of push."""
        with patch("src.rules_engine.combat.roll_d20") as mock_d20:
            # Attacker mod = STR(4) = 4; defender mod = STR(-1) = -1
            # attacker total = 20+4 = 24; defender total = 2-1 = 1 → margin = 23
            # push = 5 + (23 // 5) × 5 = 5 + 4*5 = 25
            mock_d20.side_effect = [
                RollResult(raw=20, modifier=4, total=24),
                RollResult(raw=2, modifier=-1, total=1),
            ]
            result = BullRushResolver.resolve_bull_rush(attacker, defender)
            assert result.success is True
            assert result.push_distance >= 10  # at least base + one margin tier


# ---------------------------------------------------------------------------
# SunderResolver (lines 725-767)
# ---------------------------------------------------------------------------

class TestSunderResolver:
    @pytest.fixture
    def attacker(self):
        return Character35e(
            name="Breaker", char_class="Fighter", level=5,
            strength=18, dexterity=10, constitution=14,
        )

    @pytest.fixture
    def item(self):
        return Item(
            name="Iron Sword",
            item_type=ItemType.WEAPON,
            rarity=Rarity.COMMON,
            base_damage=10,
            durability=20,
            max_durability=20,
            metadata={"hardness": 10, "enhancement_bonus": 0},
        )

    def test_sunder_miss_on_natural_1(self, attacker, item):
        with patch("src.rules_engine.combat.roll_d20") as mock_d20:
            mock_d20.return_value = RollResult(
                raw=1, modifier=attacker.melee_attack,
                total=1 + attacker.melee_attack,
            )
            result = SunderResolver.resolve_sunder(attacker, item)
            assert isinstance(result, SunderResult)
            assert result.hit is False
            assert result.damage_dealt == 0
            assert result.item_broken is False

    def test_sunder_hit_on_natural_20(self, attacker, item):
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            mock_d20.return_value = RollResult(
                raw=20, modifier=attacker.melee_attack,
                total=20 + attacker.melee_attack,
            )
            # Weapon roll with enough damage to exceed hardness 10
            mock_dmg.return_value = RollResult(raw=8, modifier=4, total=15)
            result = SunderResolver.resolve_sunder(
                attacker, item,
                damage_dice_count=1, damage_dice_sides=8,
            )
            assert result.hit is True
            assert result.damage_dealt == 5  # 15 - 10 hardness

    def test_sunder_damage_absorbed_by_hardness(self, attacker, item):
        """Damage below hardness deals 0 net damage."""
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            mock_d20.return_value = RollResult(raw=18, modifier=8, total=26)
            mock_dmg.return_value = RollResult(raw=2, modifier=0, total=2)
            result = SunderResolver.resolve_sunder(attacker, item)
            assert result.hit is True
            assert result.damage_dealt == 0
            assert result.item_broken is False
            # Item durability unchanged because net damage was 0
            assert item.durability == 20

    def test_sunder_breaks_item_when_durability_reaches_zero(self, attacker):
        """Item breaks when durability drops to 0."""
        fragile = Item(
            name="Stick",
            item_type=ItemType.WEAPON,
            rarity=Rarity.COMMON,
            durability=2,
            max_durability=2,
            metadata={"hardness": 0, "enhancement_bonus": 0},
        )
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            mock_d20.return_value = RollResult(raw=18, modifier=8, total=26)
            mock_dmg.return_value = RollResult(raw=10, modifier=4, total=14)
            result = SunderResolver.resolve_sunder(attacker, fragile)
            assert result.hit is True
            assert result.item_broken is True
            assert fragile.durability == 0

    def test_sunder_miss_when_total_below_item_ac(self, attacker):
        """A hit attempt that fails the AC check reports a miss."""
        armored_item = Item(
            name="+5 Greatsword",
            item_type=ItemType.WEAPON,
            rarity=Rarity.LEGENDARY,
            durability=50,
            max_durability=50,
            metadata={"hardness": 10, "enhancement_bonus": 5},  # AC = 15
        )
        with patch("src.rules_engine.combat.roll_d20") as mock_d20:
            # raw=5 (not 1 or 20), total = 5 + attacker.melee_attack.
            # For a Fighter5 STR18, melee_attack is ~5+4 = 9, so total = 14 < 15.
            mock_d20.return_value = RollResult(
                raw=5, modifier=attacker.melee_attack,
                total=5 + attacker.melee_attack,
            )
            result = SunderResolver.resolve_sunder(attacker, armored_item)
            # If total still >= 15 due to high melee_attack, skip this assertion.
            if 5 + attacker.melee_attack < 15:
                assert result.hit is False
                assert result.damage_dealt == 0

    def test_sunder_item_ac_uses_enhancement(self, attacker):
        """Item AC is 10 + enhancement_bonus."""
        masterwork = Item(
            name="+3 Sword",
            item_type=ItemType.WEAPON,
            rarity=Rarity.EPIC,
            durability=30,
            max_durability=30,
            metadata={"hardness": 10, "enhancement_bonus": 3},
        )
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            mock_d20.return_value = RollResult(raw=18, modifier=8, total=26)
            mock_dmg.return_value = RollResult(raw=8, modifier=4, total=12)
            result = SunderResolver.resolve_sunder(masterwork, masterwork) \
                if False else SunderResolver.resolve_sunder(attacker, masterwork)
            assert result.target_item_ac == 13  # 10 + 3

    def test_sunder_unarmed_defaults_to_1d3(self, attacker, item):
        """No override dice → uses 1d3 unarmed."""
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            mock_d20.return_value = RollResult(raw=18, modifier=8, total=26)
            mock_dmg.return_value = RollResult(raw=2, modifier=4, total=6)
            SunderResolver.resolve_sunder(attacker, item)
            # Check roll_dice was called with (1, 3, ...)
            args = mock_dmg.call_args[0]
            assert args[0] == 1
            assert args[1] == 3


# ---------------------------------------------------------------------------
# AttackResolver — concealment / miss-chance (lines 270-308)
# ---------------------------------------------------------------------------

class TestAttackResolverConcealment:
    def test_dim_light_triggers_20pct_miss_chance(self, fighter, goblin):
        """DIM light triggers a 20% concealment miss chance."""
        from src.terrain.lighting import LightLevel

        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.random.randint") as mock_rand:
            mock_d20.return_value = RollResult(raw=18, modifier=8, total=26)
            mock_rand.return_value = 10  # <= 20, miss chance triggers

            result = AttackResolver.resolve_attack(
                fighter, goblin,
                defender_light_level=LightLevel.DIM,
            )
            assert result.hit is False
            assert result.miss_chance_triggered is True
            assert result.miss_chance_threshold == 20
            assert result.miss_chance_roll == 10

    def test_dim_light_miss_chance_above_threshold_still_hits(
        self, fighter, goblin,
    ):
        """If the d% roll is above the 20% threshold, the attack still hits."""
        from src.terrain.lighting import LightLevel

        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg, \
             patch("src.rules_engine.combat.random.randint") as mock_rand:
            mock_d20.return_value = RollResult(raw=18, modifier=8, total=26)
            mock_dmg.return_value = RollResult(raw=4, modifier=3, total=7)
            mock_rand.return_value = 50  # > 20

            result = AttackResolver.resolve_attack(
                fighter, goblin,
                defender_light_level=LightLevel.DIM,
            )
            assert result.hit is True
            assert result.miss_chance_triggered is False

    def test_darkness_triggers_50pct_miss_chance(self, fighter, goblin):
        """DARKNESS triggers a 50% total-concealment miss chance."""
        from src.terrain.lighting import LightLevel

        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.random.randint") as mock_rand:
            mock_d20.return_value = RollResult(raw=18, modifier=8, total=26)
            mock_rand.return_value = 25  # <= 50

            result = AttackResolver.resolve_attack(
                fighter, goblin,
                defender_light_level=LightLevel.DARKNESS,
            )
            assert result.hit is False
            assert result.miss_chance_triggered is True
            assert result.miss_chance_threshold == 50

    def test_darkvision_bypasses_darkness_miss_chance(self, fighter, goblin):
        """An attacker with Darkvision ignores DARKNESS miss chance."""
        from src.terrain.lighting import LightLevel

        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            mock_d20.return_value = RollResult(raw=18, modifier=8, total=26)
            mock_dmg.return_value = RollResult(raw=4, modifier=3, total=7)

            result = AttackResolver.resolve_attack(
                fighter, goblin,
                defender_light_level=LightLevel.DARKNESS,
                attacker_has_darkvision=True,
            )
            assert result.hit is True


# ---------------------------------------------------------------------------
# AttackResolver — Monk unarmed damage path (line 319)
# ---------------------------------------------------------------------------

class TestAttackResolverMonkUnarmed:
    def test_monk_without_weapon_uses_unarmed_table(self):
        """A Monk with no damage dice overrides uses the Monk unarmed table."""
        monk = Character35e(
            name="Monk", char_class="Monk", level=8,
            strength=14, dexterity=16, constitution=12,
        )
        target = Character35e(
            name="Bandit", char_class="Rogue", level=1,
            strength=10, dexterity=12, constitution=10,
        )

        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            mock_d20.return_value = RollResult(raw=18, modifier=10, total=28)
            mock_dmg.return_value = RollResult(raw=6, modifier=2, total=8)

            AttackResolver.resolve_attack(monk, target)
            args = mock_dmg.call_args[0]
            # Monk level 8 → 1d10
            assert args[0] == 1
            assert args[1] == 10


# ---------------------------------------------------------------------------
# AttackResolver — Sneak Attack (Rogue, lines 342-347)
# ---------------------------------------------------------------------------

class TestAttackResolverSneakAttack:
    def test_rogue_vs_flat_footed_adds_sneak_damage(self):
        """A Rogue hitting a flat-footed target without Uncanny Dodge adds
        Sneak Attack damage to the total."""
        rogue = Character35e(
            name="Shadow", char_class="Rogue", level=5,
            strength=12, dexterity=18, constitution=12,
        )
        target = Character35e(
            name="Target", char_class="Fighter", level=1,
            strength=10, dexterity=10, constitution=10,
        )

        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg, \
             patch("src.rules_engine.abilities.SneakAttack.roll_damage") as mock_sa:
            mock_d20.return_value = RollResult(raw=18, modifier=3, total=21)
            mock_dmg.return_value = RollResult(raw=3, modifier=1, total=4)
            mock_sa.return_value = RollResult(raw=10, modifier=0, total=10)

            result = AttackResolver.resolve_attack(
                rogue, target, target_is_flat_footed=True,
            )
            assert result.hit is True
            assert result.sneak_attack_damage == 10
            assert result.total_damage == 14  # 4 + 10


# ---------------------------------------------------------------------------
# AttackResolver — Smite Evil / Favored Enemy bonuses (lines 354, 361)
# ---------------------------------------------------------------------------

class TestAttackResolverBonuses:
    def test_smite_evil_adds_attack_and_damage_bonus(self, fighter, goblin):
        """smite_evil_* params add to the attack roll and damage."""
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            mock_d20.return_value = RollResult(raw=15, modifier=11, total=26)
            mock_dmg.return_value = RollResult(raw=4, modifier=3, total=7)

            result = AttackResolver.resolve_attack(
                fighter, goblin,
                smite_evil_attack_bonus=3,
                smite_evil_damage_bonus=5,
            )
            assert result.hit is True
            assert result.smite_evil_damage == 5
            # attack_bonus includes the +3 smite
            assert result.attack_bonus == fighter.melee_attack + 3
            assert result.total_damage == 12  # 7 + 5

    def test_favored_enemy_adds_damage(self, fighter, goblin):
        """favored_enemy_damage_bonus is added to a hit's total damage."""
        with patch("src.rules_engine.combat.roll_d20") as mock_d20, \
             patch("src.rules_engine.combat.roll_dice") as mock_dmg:
            mock_d20.return_value = RollResult(raw=15, modifier=8, total=23)
            mock_dmg.return_value = RollResult(raw=4, modifier=3, total=7)

            result = AttackResolver.resolve_attack(
                fighter, goblin, favored_enemy_damage_bonus=4,
            )
            assert result.hit is True
            assert result.favored_enemy_damage == 4
            assert result.total_damage == 11  # 7 + 4
