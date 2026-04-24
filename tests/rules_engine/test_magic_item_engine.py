"""
tests/rules_engine/test_magic_item_engine.py
---------------------------------------------
Tests for T-049, T-050, T-051, T-058 (magic_item_engine.py).
"""
from __future__ import annotations

import random
import pytest

from src.rules_engine.magic_item_engine import (
    MagicItemCategory,
    roll_magic_item_type,
    roll_magic_item,
    UMDResult,
    check_use_magic_device,
    magic_item_save_dc,
    IdentificationMethod,
    IdentificationResult,
    identify_magic_item,
)
from src.rules_engine.consumables import (
    POTION_REGISTRY, SCROLL_REGISTRY, WAND_REGISTRY, ROD_REGISTRY, STAFF_REGISTRY,
    PotionBase, ScrollBase, WandBase, RodBase, StaffBase,
)


# ---------------------------------------------------------------------------
# MagicItemCategory enum
# ---------------------------------------------------------------------------

class TestMagicItemCategory:
    def test_armor(self):
        assert MagicItemCategory.ARMOR.value == "armor"

    def test_weapon(self):
        assert MagicItemCategory.WEAPON.value == "weapon"

    def test_potion(self):
        assert MagicItemCategory.POTION.value == "potion"

    def test_ring(self):
        assert MagicItemCategory.RING.value == "ring"

    def test_rod(self):
        assert MagicItemCategory.ROD.value == "rod"

    def test_scroll(self):
        assert MagicItemCategory.SCROLL.value == "scroll"

    def test_staff(self):
        assert MagicItemCategory.STAFF.value == "staff"

    def test_wand(self):
        assert MagicItemCategory.WAND.value == "wand"

    def test_wondrous(self):
        assert MagicItemCategory.WONDROUS.value == "wondrous"

    def test_enum_has_nine_values(self):
        assert len(MagicItemCategory) == 9


# ---------------------------------------------------------------------------
# roll_magic_item_type
# ---------------------------------------------------------------------------

class TestRollMagicItemType:
    def test_returns_magic_item_category(self):
        rng = random.Random(1)
        result = roll_magic_item_type(rng)
        assert isinstance(result, MagicItemCategory)

    def test_no_rng_provided(self):
        result = roll_magic_item_type()
        assert isinstance(result, MagicItemCategory)

    def test_seeded_rng_deterministic(self):
        r1 = roll_magic_item_type(random.Random(42))
        r2 = roll_magic_item_type(random.Random(42))
        assert r1 == r2

    def test_distribution_all_categories_appear(self):
        """Over 900 rolls all 9 categories must appear at least once."""
        rng = random.Random(0)
        seen = set()
        for _ in range(900):
            seen.add(roll_magic_item_type(rng))
        assert seen == set(MagicItemCategory)

    def test_potion_most_common(self):
        """Potions cover 28% of the table, should dominate large sample."""
        rng = random.Random(12345)
        counts = {cat: 0 for cat in MagicItemCategory}
        for _ in range(1000):
            counts[roll_magic_item_type(rng)] += 1
        assert counts[MagicItemCategory.POTION] > counts[MagicItemCategory.ARMOR]


# ---------------------------------------------------------------------------
# roll_magic_item
# ---------------------------------------------------------------------------

class TestRollMagicItem:
    def test_potion_category_returns_potion(self):
        rng = random.Random(1)
        result = roll_magic_item(MagicItemCategory.POTION, rng)
        assert result["category"] == MagicItemCategory.POTION
        assert isinstance(result["item"], PotionBase)

    def test_scroll_category_returns_scroll(self):
        rng = random.Random(2)
        result = roll_magic_item(MagicItemCategory.SCROLL, rng)
        assert isinstance(result["item"], ScrollBase)

    def test_wand_category_returns_wand(self):
        rng = random.Random(3)
        result = roll_magic_item(MagicItemCategory.WAND, rng)
        assert isinstance(result["item"], WandBase)

    def test_rod_category_returns_rod(self):
        rng = random.Random(4)
        result = roll_magic_item(MagicItemCategory.ROD, rng)
        assert isinstance(result["item"], RodBase)

    def test_staff_category_returns_staff(self):
        rng = random.Random(5)
        result = roll_magic_item(MagicItemCategory.STAFF, rng)
        assert isinstance(result["item"], StaffBase)

    def test_armor_returns_placeholder(self):
        rng = random.Random(6)
        result = roll_magic_item(MagicItemCategory.ARMOR, rng)
        assert result["category"] == MagicItemCategory.ARMOR
        assert result["item"] is None

    def test_weapon_returns_placeholder(self):
        rng = random.Random(7)
        result = roll_magic_item(MagicItemCategory.WEAPON, rng)
        assert result["item"] is None

    def test_result_has_name_key(self):
        rng = random.Random(8)
        result = roll_magic_item(MagicItemCategory.POTION, rng)
        assert "name" in result
        assert isinstance(result["name"], str)

    def test_result_has_category_key(self):
        rng = random.Random(9)
        result = roll_magic_item(MagicItemCategory.SCROLL, rng)
        assert result["category"] == MagicItemCategory.SCROLL

    def test_all_categories_execute_without_error(self):
        rng = random.Random(99)
        for cat in MagicItemCategory:
            result = roll_magic_item(cat, rng)
            assert "category" in result


# ---------------------------------------------------------------------------
# UMDResult
# ---------------------------------------------------------------------------

class TestUMDResult:
    def test_success_true(self):
        r = UMDResult(success=True, roll=20, dc=15)
        assert r.success is True

    def test_success_false(self):
        r = UMDResult(success=False, roll=5, dc=20)
        assert r.success is False

    def test_roll_stored(self):
        r = UMDResult(success=True, roll=18, dc=15)
        assert r.roll == 18

    def test_dc_stored(self):
        r = UMDResult(success=False, roll=10, dc=25)
        assert r.dc == 25

    def test_repr(self):
        r = UMDResult(success=True, roll=20, dc=0)
        assert "UMDResult" in repr(r)


# ---------------------------------------------------------------------------
# check_use_magic_device
# ---------------------------------------------------------------------------

class TestCheckUseMagicDevice:
    def _potion(self):
        return POTION_REGISTRY[next(iter(POTION_REGISTRY))]

    def _scroll(self, spell_level=1):
        return next(s for s in SCROLL_REGISTRY.values() if s.spell_level == spell_level)

    def _wand(self):
        return WAND_REGISTRY[next(iter(WAND_REGISTRY))]

    def _staff(self):
        return STAFF_REGISTRY[next(iter(STAFF_REGISTRY))]

    def test_potion_always_succeeds(self):
        potion = self._potion()
        for seed in range(20):
            result = check_use_magic_device(potion, 0, random.Random(seed))
            assert result.success is True

    def test_potion_dc_is_zero(self):
        potion = self._potion()
        result = check_use_magic_device(potion, 0, random.Random(1))
        assert result.dc == 0

    def test_scroll_dc_equals_20_plus_spell_level(self):
        scroll = self._scroll(spell_level=1)
        result = check_use_magic_device(scroll, 100, random.Random(1))
        assert result.dc == 21

    def test_scroll_level_3_dc_is_23(self):
        scroll = next(s for s in SCROLL_REGISTRY.values() if s.spell_level == 3)
        result = check_use_magic_device(scroll, 100, random.Random(1))
        assert result.dc == 23

    def test_wand_dc_is_20(self):
        wand = self._wand()
        result = check_use_magic_device(wand, 100, random.Random(1))
        assert result.dc == 20

    def test_staff_dc_is_20(self):
        staff = self._staff()
        result = check_use_magic_device(staff, 100, random.Random(1))
        assert result.dc == 20

    def test_high_modifier_succeeds(self):
        wand = self._wand()
        result = check_use_magic_device(wand, 100, random.Random(1))
        assert result.success is True

    def test_negative_modifier_may_fail(self):
        """With -100 modifier, wand activation must fail."""
        wand = self._wand()
        result = check_use_magic_device(wand, -100, random.Random(1))
        assert result.success is False

    def test_returns_umd_result(self):
        wand = self._wand()
        result = check_use_magic_device(wand, 0, random.Random(1))
        assert isinstance(result, UMDResult)


# ---------------------------------------------------------------------------
# magic_item_save_dc
# ---------------------------------------------------------------------------

class TestMagicItemSaveDC:
    def test_potion_returns_none(self):
        potion = POTION_REGISTRY[next(iter(POTION_REGISTRY))]
        assert magic_item_save_dc(potion) is None

    def test_scroll_returns_none(self):
        scroll = SCROLL_REGISTRY[next(iter(SCROLL_REGISTRY))]
        assert magic_item_save_dc(scroll) is None

    def test_rod_returns_none(self):
        rod = ROD_REGISTRY[next(iter(ROD_REGISTRY))]
        assert magic_item_save_dc(rod) is None

    def test_wand_formula(self):
        wand = WAND_REGISTRY[next(iter(WAND_REGISTRY))]
        expected = 10 + (wand.caster_level // 2)
        assert magic_item_save_dc(wand) == expected

    def test_wand_cl_1_gives_10(self):
        wand = next(w for w in WAND_REGISTRY.values() if w.caster_level == 1)
        assert magic_item_save_dc(wand) == 10

    def test_wand_returns_integer(self):
        wand = WAND_REGISTRY[next(iter(WAND_REGISTRY))]
        result = magic_item_save_dc(wand)
        assert isinstance(result, int)

    def test_staff_returns_integer(self):
        staff = STAFF_REGISTRY[next(iter(STAFF_REGISTRY))]
        result = magic_item_save_dc(staff)
        # StaffBase has no caster_level so uses default 1 → 10 + (1//2) = 10
        assert isinstance(result, int)


# ---------------------------------------------------------------------------
# IdentificationMethod enum
# ---------------------------------------------------------------------------

class TestIdentificationMethod:
    def test_spellcraft(self):
        assert IdentificationMethod.SPELLCRAFT.value == "spellcraft"

    def test_detect_magic(self):
        assert IdentificationMethod.DETECT_MAGIC.value == "detect_magic"

    def test_identify(self):
        assert IdentificationMethod.IDENTIFY.value == "identify"

    def test_analyze_dweomer(self):
        assert IdentificationMethod.ANALYZE_DWEOMER.value == "analyze_dweomer"

    def test_enum_count(self):
        assert len(IdentificationMethod) == 4


# ---------------------------------------------------------------------------
# IdentificationResult
# ---------------------------------------------------------------------------

class TestIdentificationResult:
    def test_creation_identified(self):
        r = IdentificationResult(identified=True, aura_school="evocation", full_name="Wand of Fire")
        assert r.identified is True

    def test_creation_not_identified(self):
        r = IdentificationResult(identified=False, aura_school="evocation", full_name=None)
        assert r.full_name is None

    def test_aura_school_stored(self):
        r = IdentificationResult(identified=True, aura_school="transmutation", full_name="Staff")
        assert r.aura_school == "transmutation"


# ---------------------------------------------------------------------------
# identify_magic_item
# ---------------------------------------------------------------------------

class TestIdentifyMagicItem:
    def _wand(self):
        return "Wand of Magic Missiles", WAND_REGISTRY[next(iter(WAND_REGISTRY))]

    def _potion(self):
        k = next(iter(POTION_REGISTRY))
        return k, POTION_REGISTRY[k]

    def _scroll(self):
        k = next(iter(SCROLL_REGISTRY))
        return k, SCROLL_REGISTRY[k]

    def _staff(self):
        k = next(iter(STAFF_REGISTRY))
        return k, STAFF_REGISTRY[k]

    def test_analyze_dweomer_always_identified(self):
        name, wand = self._wand()
        result = identify_magic_item(name, wand, IdentificationMethod.ANALYZE_DWEOMER)
        assert result.identified is True
        assert result.full_name == name

    def test_analyze_dweomer_potion(self):
        name, potion = self._potion()
        result = identify_magic_item(name, potion, IdentificationMethod.ANALYZE_DWEOMER)
        assert result.identified is True

    def test_identify_spell_always_succeeds(self):
        name, wand = self._wand()
        result = identify_magic_item(name, wand, IdentificationMethod.IDENTIFY)
        assert result.identified is True
        assert result.full_name == name

    def test_identify_sets_aura_school(self):
        name, wand = self._wand()
        result = identify_magic_item(name, wand, IdentificationMethod.IDENTIFY)
        assert result.aura_school is not None

    def test_detect_magic_not_identified(self):
        name, wand = self._wand()
        result = identify_magic_item(name, wand, IdentificationMethod.DETECT_MAGIC)
        assert result.identified is False

    def test_detect_magic_returns_aura_school(self):
        name, wand = self._wand()
        result = identify_magic_item(name, wand, IdentificationMethod.DETECT_MAGIC)
        assert result.aura_school is not None

    def test_detect_magic_full_name_is_none(self):
        name, wand = self._wand()
        result = identify_magic_item(name, wand, IdentificationMethod.DETECT_MAGIC)
        assert result.full_name is None

    def test_spellcraft_high_modifier_identifies(self):
        name, wand = self._wand()
        result = identify_magic_item(
            name, wand, IdentificationMethod.SPELLCRAFT,
            spellcraft_modifier=100, rng=random.Random(1)
        )
        assert result.identified is True
        assert result.full_name == name

    def test_spellcraft_low_modifier_fails(self):
        name, wand = self._wand()
        result = identify_magic_item(
            name, wand, IdentificationMethod.SPELLCRAFT,
            spellcraft_modifier=-100, rng=random.Random(1)
        )
        assert result.identified is False
        assert result.full_name is None

    def test_spellcraft_low_modifier_still_has_aura(self):
        name, wand = self._wand()
        result = identify_magic_item(
            name, wand, IdentificationMethod.SPELLCRAFT,
            spellcraft_modifier=-100, rng=random.Random(1)
        )
        assert result.aura_school is not None

    def test_potion_aura_is_conjuration(self):
        name, potion = self._potion()
        result = identify_magic_item(name, potion, IdentificationMethod.IDENTIFY)
        assert result.aura_school == "conjuration"

    def test_scroll_aura_is_universal(self):
        name, scroll = self._scroll()
        result = identify_magic_item(name, scroll, IdentificationMethod.IDENTIFY)
        assert result.aura_school == "universal"

    def test_wand_aura_is_evocation(self):
        name, wand = self._wand()
        result = identify_magic_item(name, wand, IdentificationMethod.IDENTIFY)
        assert result.aura_school == "evocation"

    def test_staff_aura_is_transmutation(self):
        name, staff = self._staff()
        result = identify_magic_item(name, staff, IdentificationMethod.IDENTIFY)
        assert result.aura_school == "transmutation"

    def test_returns_identification_result(self):
        name, wand = self._wand()
        result = identify_magic_item(name, wand, IdentificationMethod.IDENTIFY)
        assert isinstance(result, IdentificationResult)
