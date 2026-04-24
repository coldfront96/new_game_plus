"""
tests/rules_engine/test_consumables.py
----------------------------------------
Comprehensive tests for src/rules_engine/consumables.py.
Covers T-005 dataclasses, T-018–T-021 price formulae, and T-027–T-031 registries.
"""

from __future__ import annotations

import math
import pytest

from src.rules_engine.consumables import (
    PotionBase, ScrollBase, WandBase, RodBase, StaffBase,
    potion_market_price, scroll_market_price, wand_market_price,
    rod_market_price, staff_market_price,
    POTION_REGISTRY, SCROLL_REGISTRY, WAND_REGISTRY,
    ROD_REGISTRY, STAFF_REGISTRY,
)


# ===========================================================================
# T-005: Dataclass creation
# ===========================================================================

class TestPotionBase:
    def test_fields_stored_correctly(self):
        p = PotionBase(
            name="Cure Light Wounds",
            spell_name="Cure Light Wounds",
            caster_level=1,
            spell_level=1,
            market_price_gp=50,
        )
        assert p.name == "Cure Light Wounds"
        assert p.spell_name == "Cure Light Wounds"
        assert p.caster_level == 1
        assert p.spell_level == 1
        assert p.market_price_gp == 50

    def test_different_values(self):
        p = PotionBase("Blur", "Blur", 3, 2, 300)
        assert p.caster_level == 3
        assert p.spell_level == 2
        assert p.market_price_gp == 300


class TestScrollBase:
    def test_arcane_scroll(self):
        s = ScrollBase("Scroll of Fireball (Arcane)", "Fireball", 5, 3, True, 375)
        assert s.arcane is True
        assert s.spell_level == 3
        assert s.caster_level == 5
        assert s.market_price_gp == 375

    def test_divine_scroll(self):
        s = ScrollBase("Scroll of Cure Light Wounds (Divine)", "Cure Light Wounds", 1, 1, False, 25)
        assert s.arcane is False
        assert s.market_price_gp == 25


class TestWandBase:
    def test_charges_max_stored(self):
        w = WandBase("Wand of Magic Missile", "Magic Missile", 1, 1, 50, 750)
        assert w.charges_max == 50
        assert w.market_price_gp == 750

    def test_higher_level_wand(self):
        w = WandBase("Wand of Fireball", "Fireball", 5, 3, 50, 11_250)
        assert w.spell_level == 3
        assert w.caster_level == 5


class TestRodBase:
    def test_no_charges(self):
        r = RodBase("Immovable Rod", 0, 5_000)
        assert r.charges_max == 0
        assert r.market_price_gp == 5_000

    def test_with_charges(self):
        r = RodBase("Rod of Absorption", 50, 50_000)
        assert r.charges_max == 50


class TestStaffBase:
    def test_charges_always_50(self):
        s = StaffBase("Staff of Fire", 50, 17_750)
        assert s.charges_max == 50
        assert s.market_price_gp == 17_750


# ===========================================================================
# T-018: potion_market_price
# ===========================================================================

class TestPotionMarketPrice:
    def test_level_0_cl1(self):
        assert potion_market_price(0, 1) == 25

    def test_level_0_cl3(self):
        assert potion_market_price(0, 3) == 75

    def test_level_1_cl1(self):
        assert potion_market_price(1, 1) == 50

    def test_level_2_cl3(self):
        assert potion_market_price(2, 3) == 300

    def test_level_3_cl5(self):
        assert potion_market_price(3, 5) == 750

    def test_level_4_cl7(self):
        assert potion_market_price(4, 7) == 1_400

    def test_formula_general(self):
        for sl in range(1, 5):
            for cl in range(1, 10):
                assert potion_market_price(sl, cl) == sl * cl * 50


# ===========================================================================
# T-019: scroll_market_price
# ===========================================================================

class TestScrollMarketPrice:
    def test_level_0_cl1(self):
        assert scroll_market_price(0, 1) == math.ceil(1 * 12.5)  # 13

    def test_level_0_cl2(self):
        assert scroll_market_price(0, 2) == math.ceil(2 * 12.5)  # 25

    def test_level_1_cl1(self):
        assert scroll_market_price(1, 1) == 25

    def test_level_2_cl3(self):
        assert scroll_market_price(2, 3) == 150

    def test_level_3_cl5(self):
        assert scroll_market_price(3, 5) == 375

    def test_level_4_cl7(self):
        assert scroll_market_price(4, 7) == 700

    def test_arcane_divine_same_price(self):
        assert scroll_market_price(3, 5, arcane=True) == scroll_market_price(3, 5, arcane=False)

    def test_level_6_cl11(self):
        assert scroll_market_price(6, 11) == 6 * 11 * 25  # 1650

    def test_formula_general(self):
        for sl in range(1, 7):
            for cl in range(1, 12):
                assert scroll_market_price(sl, cl) == sl * cl * 25


# ===========================================================================
# T-020: wand_market_price
# ===========================================================================

class TestWandMarketPrice:
    def test_level_0_cl1_minimum(self):
        assert wand_market_price(0, 1) == 375

    def test_level_0_cl2(self):
        assert wand_market_price(0, 2) == 750

    def test_level_0_minimum_enforced(self):
        # Even cl=0 would give 0 but minimum is 375
        assert wand_market_price(0, 0) == 375

    def test_level_1_cl1(self):
        assert wand_market_price(1, 1) == 750

    def test_level_2_cl3(self):
        assert wand_market_price(2, 3) == 4_500

    def test_level_3_cl5(self):
        assert wand_market_price(3, 5) == 11_250

    def test_level_4_cl7(self):
        assert wand_market_price(4, 7) == 21_000

    def test_formula_general(self):
        for sl in range(1, 5):
            for cl in range(1, 10):
                assert wand_market_price(sl, cl) == sl * cl * 750


# ===========================================================================
# T-021: rod_market_price and staff_market_price
# ===========================================================================

class TestRodMarketPrice:
    def test_returns_stored_price(self):
        r = RodBase("Test Rod", 0, 42_000)
        assert rod_market_price(r) == 42_000

    def test_immovable_rod(self):
        r = RodBase("Immovable Rod", 0, 5_000)
        assert rod_market_price(r) == 5_000

    def test_expensive_rod(self):
        r = RodBase("Rod of Alertness", 0, 85_000)
        assert rod_market_price(r) == 85_000


class TestStaffMarketPrice:
    def test_primary_only(self):
        assert staff_market_price(3, 5, []) == 3 * 5 * 900  # 13_500

    def test_primary_plus_secondaries(self):
        primary = 3 * 5 * 900
        secondaries = [500, 1_000]
        assert staff_market_price(3, 5, [500, 1_000]) == primary + 1_500

    def test_zero_secondaries_list(self):
        assert staff_market_price(1, 1, []) == 900


# ===========================================================================
# T-027: POTION_REGISTRY
# ===========================================================================

class TestPotionRegistry:
    _EXPECTED = [
        ("Cure Light Wounds",         1, 1,  50),
        ("Cure Moderate Wounds",      2, 3, 300),
        ("Cure Serious Wounds",        3, 5, 750),
        ("Bull's Strength",            2, 3, 300),
        ("Cat's Grace",                2, 3, 300),
        ("Bear's Endurance",           2, 3, 300),
        ("Eagle's Splendor",           2, 3, 300),
        ("Fox's Cunning",              2, 3, 300),
        ("Owl's Wisdom",               2, 3, 300),
        ("Barkskin",                   2, 3, 300),
        ("Darkvision",                 2, 3, 300),
        ("Hide from Undead",           1, 1,  50),
        ("Jump",                       1, 1,  50),
        ("Neutralize Poison",          4, 7, 1_400),
        ("Remove Blindness/Deafness",  3, 5, 750),
        ("Remove Curse",               3, 5, 750),
        ("Remove Disease",             3, 5, 750),
        ("Remove Fear",                1, 1,  50),
        ("Resist Energy",              2, 3, 300),
        ("Spider Climb",               2, 3, 300),
        ("Water Breathing",            3, 5, 750),
        ("Blur",                       2, 3, 300),
        ("Endure Elements",            1, 1,  50),
        ("Gaseous Form",               3, 5, 750),
        ("Invisibility",               2, 3, 300),
        ("Levitate",                   2, 3, 300),
        ("Mage Armor",                 1, 1,  50),
        ("Magic Fang",                 1, 1,  50),
        ("Nondetection",               3, 5, 750),
        ("Protection from Arrows",     2, 3, 300),
        ("Shield of Faith",            1, 1,  50),
    ]

    def test_registry_has_31_potions(self):
        assert len(POTION_REGISTRY) == 31

    def test_all_expected_potions_present(self):
        for name, sl, cl, price in self._EXPECTED:
            assert name in POTION_REGISTRY, f"Missing: {name}"

    def test_spell_levels_correct(self):
        for name, sl, cl, price in self._EXPECTED:
            assert POTION_REGISTRY[name].spell_level == sl

    def test_caster_levels_correct(self):
        for name, sl, cl, price in self._EXPECTED:
            assert POTION_REGISTRY[name].caster_level == cl

    def test_market_prices_correct(self):
        for name, sl, cl, price in self._EXPECTED:
            assert POTION_REGISTRY[name].market_price_gp == price

    def test_all_are_potion_base_instances(self):
        for p in POTION_REGISTRY.values():
            assert isinstance(p, PotionBase)

    def test_names_match_keys(self):
        for key, p in POTION_REGISTRY.items():
            assert key == p.name


# ===========================================================================
# T-028: SCROLL_REGISTRY
# ===========================================================================

class TestScrollRegistry:
    def test_registry_has_at_least_40_scrolls(self):
        assert len(SCROLL_REGISTRY) >= 40

    def test_arcane_scrolls_flagged_correctly(self):
        arcane_names = [
            "Scroll of Detect Magic (Arcane)",
            "Scroll of Fireball (Arcane)",
            "Scroll of Stoneskin (Arcane)",
        ]
        for name in arcane_names:
            assert name in SCROLL_REGISTRY
            assert SCROLL_REGISTRY[name].arcane is True

    def test_divine_scrolls_flagged_correctly(self):
        divine_names = [
            "Scroll of Cure Light Wounds (Divine)",
            "Scroll of Heal (Divine)",
            "Scroll of Raise Dead (Divine)",
        ]
        for name in divine_names:
            assert name in SCROLL_REGISTRY
            assert SCROLL_REGISTRY[name].arcane is False

    def test_level_0_arcane_price(self):
        s = SCROLL_REGISTRY["Scroll of Detect Magic (Arcane)"]
        assert s.market_price_gp == math.ceil(1 * 12.5)  # 13

    def test_level_1_arcane_price(self):
        s = SCROLL_REGISTRY["Scroll of Magic Missile (Arcane)"]
        assert s.market_price_gp == 25

    def test_level_3_arcane_price(self):
        s = SCROLL_REGISTRY["Scroll of Fireball (Arcane)"]
        assert s.market_price_gp == 375

    def test_level_1_divine_price(self):
        s = SCROLL_REGISTRY["Scroll of Cure Light Wounds (Divine)"]
        assert s.market_price_gp == 25

    def test_level_6_divine_price(self):
        s = SCROLL_REGISTRY["Scroll of Heal (Divine)"]
        assert s.market_price_gp == 6 * 11 * 25  # 1650

    def test_all_are_scroll_base_instances(self):
        for s in SCROLL_REGISTRY.values():
            assert isinstance(s, ScrollBase)

    def test_names_match_keys(self):
        for key, s in SCROLL_REGISTRY.items():
            assert key == s.name

    def test_25_arcane_scrolls(self):
        arcane = [s for s in SCROLL_REGISTRY.values() if s.arcane]
        assert len(arcane) == 25

    def test_16_divine_scrolls(self):
        divine = [s for s in SCROLL_REGISTRY.values() if not s.arcane]
        assert len(divine) == 16


# ===========================================================================
# T-029: WAND_REGISTRY
# ===========================================================================

class TestWandRegistry:
    def test_registry_has_25_wands(self):
        assert len(WAND_REGISTRY) == 25

    def test_all_charges_max_50(self):
        for w in WAND_REGISTRY.values():
            assert w.charges_max == 50

    def test_cure_light_wounds_wand_price(self):
        w = WAND_REGISTRY["Wand of Cure Light Wounds"]
        assert w.market_price_gp == 750
        assert w.spell_level == 1
        assert w.caster_level == 1

    def test_fireball_wand_price(self):
        w = WAND_REGISTRY["Wand of Fireball"]
        assert w.market_price_gp == 11_250
        assert w.spell_level == 3
        assert w.caster_level == 5

    def test_enervation_wand_price(self):
        w = WAND_REGISTRY["Wand of Enervation"]
        assert w.market_price_gp == wand_market_price(4, 7)  # 21_000

    def test_all_expected_wands_present(self):
        expected = [
            "Wand of Cure Light Wounds", "Wand of Fireball", "Wand of Lightning Bolt",
            "Wand of Magic Missile", "Wand of Charm Person", "Wand of Hold Person",
            "Wand of Invisibility", "Wand of Knock", "Wand of Web",
            "Wand of Dispel Magic", "Wand of Bear's Endurance", "Wand of Bull's Strength",
            "Wand of Cat's Grace", "Wand of Eagle's Splendor", "Wand of Enervation",
            "Wand of Fear", "Wand of Fly", "Wand of Haste", "Wand of Ice Storm",
            "Wand of Inflict Light Wounds", "Wand of Melf's Acid Arrow",
            "Wand of Neutralize Poison", "Wand of Slow", "Wand of Suggestion",
            "Wand of Summon Monster III",
        ]
        for name in expected:
            assert name in WAND_REGISTRY

    def test_all_are_wand_base_instances(self):
        for w in WAND_REGISTRY.values():
            assert isinstance(w, WandBase)

    def test_names_match_keys(self):
        for key, w in WAND_REGISTRY.items():
            assert key == w.name


# ===========================================================================
# T-030: ROD_REGISTRY
# ===========================================================================

class TestRodRegistry:
    def test_registry_has_20_rods(self):
        assert len(ROD_REGISTRY) == 20

    def test_known_prices(self):
        expected = {
            "Rod of Absorption":                    50_000,
            "Rod of Alertness":                     85_000,
            "Rod of Cancellation":                  11_000,
            "Rod of Enemy Detection":               23_500,
            "Rod of Flailing":                       2_000,
            "Rod of Flame Extinguishing":           15_000,
            "Rod of Lordly Might":                  70_000,
            "Rod of Metal and Mineral Detection":   10_500,
            "Rod of Negation":                      37_000,
            "Rod of Python":                        13_000,
            "Rod of Rulership":                     60_000,
            "Rod of Security":                      61_000,
            "Rod of Smiting":                        4_000,
            "Rod of Splendor":                      25_000,
            "Rod of Thunder and Lightning":         33_000,
            "Rod of the Viper":                     19_000,
            "Rod of Viscid Globs":                  60_000,
            "Rod of Withering":                     25_000,
            "Rod of Wonder":                        12_000,
            "Immovable Rod":                         5_000,
        }
        for name, price in expected.items():
            assert name in ROD_REGISTRY, f"Missing rod: {name}"
            assert ROD_REGISTRY[name].market_price_gp == price

    def test_all_are_rod_base_instances(self):
        for r in ROD_REGISTRY.values():
            assert isinstance(r, RodBase)

    def test_names_match_keys(self):
        for key, r in ROD_REGISTRY.items():
            assert key == r.name

    def test_rod_market_price_function(self):
        for r in ROD_REGISTRY.values():
            assert rod_market_price(r) == r.market_price_gp


# ===========================================================================
# T-031: STAFF_REGISTRY
# ===========================================================================

class TestStaffRegistry:
    def test_registry_has_at_least_17_staffs(self):
        assert len(STAFF_REGISTRY) >= 17

    def test_registry_has_20_staffs(self):
        assert len(STAFF_REGISTRY) == 20

    def test_all_charges_max_50(self):
        for s in STAFF_REGISTRY.values():
            assert s.charges_max == 50

    def test_known_prices(self):
        expected = {
            "Staff of Abjuration":          65_000,
            "Staff of Charming":            16_500,
            "Staff of Conjuration":         65_000,
            "Staff of Defense":             58_250,
            "Staff of Divination":          65_000,
            "Staff of Earth and Stone":     80_500,
            "Staff of Evocation":           65_000,
            "Staff of Fire":                17_750,
            "Staff of Frost":               41_400,
            "Staff of Healing":             27_750,
            "Staff of Illumination":        48_250,
            "Staff of Illusion":            65_000,
            "Staff of Life":               109_400,
            "Staff of Necromancy":          65_000,
            "Staff of Passage":            206_900,
            "Staff of Power":              211_000,
            "Staff of Size Alteration":     29_000,
            "Staff of Swarming Insects":    24_750,
            "Staff of Transmutation":       65_000,
            "Staff of Woodlands":          101_250,
        }
        for name, price in expected.items():
            assert name in STAFF_REGISTRY, f"Missing staff: {name}"
            assert STAFF_REGISTRY[name].market_price_gp == price

    def test_all_are_staff_base_instances(self):
        for s in STAFF_REGISTRY.values():
            assert isinstance(s, StaffBase)

    def test_names_match_keys(self):
        for key, s in STAFF_REGISTRY.items():
            assert key == s.name
