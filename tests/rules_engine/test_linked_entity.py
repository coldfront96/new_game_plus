"""
tests/rules_engine/test_linked_entity.py
-----------------------------------------
Comprehensive tests for the D&D 3.5e linked entity subsystem.

Covers tasks E-003 through E-057 (Tiers 0-4).
"""

from __future__ import annotations

import random
import pytest

from src.rules_engine.linked_entity import (
    # Schemas
    LinkType,
    MasterMinionLink,
    FamiliarSpecies,
    FamiliarBase,
    AnimalCompanionBase,
    SpecialMountBase,
    # Progression helpers
    familiar_int_score,
    familiar_natural_armor_bonus,
    AnimalCompanionProgression,
    animal_companion_progression,
    SpecialMountProgression,
    paladin_mount_progression,
    # Registries
    FAMILIAR_REGISTRY,
    ANIMAL_COMPANION_REGISTRY,
    PALADIN_MOUNT_REGISTRY,
    # Engines
    FamiliarError,
    acquire_familiar,
    CompanionError,
    acquire_animal_companion,
    MountError,
    summon_special_mount,
    # Turn tracker / share-spells
    MasterMinionTurnTracker,
    ShareResult,
    share_spell,
    empathic_link_message,
    donate_hp,
)
from src.ai_sim.master_minion import resolve_minion_turns


# ===========================================================================
# E-003  MasterMinionLink schema
# ===========================================================================

class TestMasterMinionLink:
    def test_creation(self):
        link = MasterMinionLink(
            master_id="m1", minion_id="f1",
            link_type=LinkType.Familiar,
            share_spells=True, empathic_link=True,
            delivery_touch=True, scry_on_familiar=False,
        )
        assert link.master_id == "m1"
        assert link.link_type is LinkType.Familiar
        assert link.share_spells is True

    def test_link_types(self):
        for lt in LinkType:
            assert isinstance(lt, LinkType)

    def test_slots_no_dict(self):
        link = MasterMinionLink(
            master_id="a", minion_id="b",
            link_type=LinkType.Cohort,
            share_spells=False, empathic_link=False,
            delivery_touch=False, scry_on_familiar=False,
        )
        assert not hasattr(link, "__dict__")


# ===========================================================================
# E-004  FamiliarBase schema
# ===========================================================================

class TestFamiliarBase:
    def test_creation(self):
        fb = FamiliarBase(
            species="Cat", master_class_levels=5,
            natural_armor_bonus=4, int_score=8,
            special_master_bonus="+3 bonus on Move Silently checks",
        )
        assert fb.species == "Cat"
        assert fb.int_score == 8

    def test_slots(self):
        fb = FamiliarBase(
            species="Bat", master_class_levels=1,
            natural_armor_bonus=2, int_score=6,
            special_master_bonus="+3 bonus on Listen checks",
        )
        assert not hasattr(fb, "__dict__")


# ===========================================================================
# E-005  AnimalCompanionBase schema
# ===========================================================================

class TestAnimalCompanionBase:
    def test_creation(self):
        ac = AnimalCompanionBase(
            species="Wolf", base_cr=2.0, effective_druid_level=0,
            bonus_hd=0, natural_armor_adj=0, str_dex_adj=0,
            bonus_tricks=1, link_active=True, share_spells=True,
            evasion=False, devotion=False, multiattack=False,
            improved_evasion=False,
        )
        assert ac.species == "Wolf"
        assert ac.base_cr == 2.0

    def test_slots(self):
        ac = AnimalCompanionBase(
            species="Eagle", base_cr=0.5, effective_druid_level=0,
            bonus_hd=0, natural_armor_adj=0, str_dex_adj=0,
            bonus_tricks=1, link_active=True, share_spells=True,
            evasion=False, devotion=False, multiattack=False,
            improved_evasion=False,
        )
        assert not hasattr(ac, "__dict__")


# ===========================================================================
# E-006  SpecialMountBase schema
# ===========================================================================

class TestSpecialMountBase:
    def test_creation(self):
        sm = SpecialMountBase(
            species="heavy_warhorse", bonus_hd=2, natural_armor_adj=4,
            str_adj=1, int_score=6, empathic_link=True,
            improved_evasion=True, share_spells=True,
            share_saving_throws=True, command=False, spell_resistance=0,
        )
        assert sm.species == "heavy_warhorse"
        assert sm.daily_summons_remaining == 1

    def test_slots(self):
        sm = SpecialMountBase(
            species="warpony", bonus_hd=2, natural_armor_adj=4,
            str_adj=1, int_score=6, empathic_link=True,
            improved_evasion=True, share_spells=True,
            share_saving_throws=True, command=False, spell_resistance=0,
        )
        assert not hasattr(sm, "__dict__")


# ===========================================================================
# E-021  Familiar Intelligence and Natural Armor Progression
# ===========================================================================

class TestFamiliarIntScore:
    @pytest.mark.parametrize("level,expected", [
        (1, 6), (2, 6),
        (3, 7), (4, 7),
        (5, 8), (6, 8),
        (7, 9), (8, 9),
        (9, 10), (10, 10),
        (11, 11), (12, 11),
        (13, 12), (14, 12),
        (15, 13), (16, 13),
        (17, 14), (18, 14),
        (19, 15), (20, 15),
    ])
    def test_int_score_table(self, level, expected):
        assert familiar_int_score(level) == expected

    def test_clamp_low(self):
        assert familiar_int_score(0) == 6

    def test_clamp_high(self):
        assert familiar_int_score(21) == 15


class TestFamiliarNaturalArmor:
    @pytest.mark.parametrize("level,expected", [
        (1, 1), (2, 2), (3, 2), (4, 3), (5, 3),
        (10, 6), (20, 11),
    ])
    def test_na_formula(self, level, expected):
        assert familiar_natural_armor_bonus(level) == expected

    def test_clamp_low(self):
        assert familiar_natural_armor_bonus(0) == 1


# ===========================================================================
# E-022  Animal Companion Progression
# ===========================================================================

class TestAnimalCompanionProgression:
    def test_level_1(self):
        p = animal_companion_progression(1)
        assert p.bonus_hd == 0
        assert p.natural_armor_adj == 0
        assert p.str_dex_adj == 0
        assert p.bonus_tricks == 1
        assert p.link is True
        assert p.share_spells is True
        assert p.evasion is False

    def test_level_2_evasion(self):
        p = animal_companion_progression(2)
        assert p.evasion is True
        assert p.bonus_hd == 0

    def test_level_3(self):
        p = animal_companion_progression(3)
        assert p.bonus_hd == 2
        assert p.natural_armor_adj == 2
        assert p.str_dex_adj == 1
        assert p.bonus_tricks == 2

    def test_level_6_devotion(self):
        p = animal_companion_progression(6)
        assert p.bonus_hd == 4
        assert p.devotion is True

    def test_level_9_multiattack(self):
        p = animal_companion_progression(9)
        assert p.multiattack is True
        assert p.bonus_hd == 6

    def test_level_15_improved_evasion(self):
        p = animal_companion_progression(15)
        assert p.improved_evasion is True
        assert p.bonus_hd == 10

    def test_level_18_max(self):
        p = animal_companion_progression(18)
        assert p.bonus_hd == 12
        assert p.str_dex_adj == 6
        assert p.bonus_tricks == 7

    def test_below_1_returns_level1(self):
        assert animal_companion_progression(0).bonus_hd == 0


# ===========================================================================
# E-023  Paladin Mount Progression
# ===========================================================================

class TestPaladinMountProgression:
    def test_level_5(self):
        p = paladin_mount_progression(5)
        assert p.bonus_hd == 2
        assert p.natural_armor_adj == 4
        assert p.str_adj == 1
        assert p.int_score == 6
        assert p.command is False
        assert p.spell_resistance == 0
        assert p.empathic_link is True
        assert p.improved_evasion is True
        assert p.share_spells is True
        assert p.share_saving_throws is True

    def test_level_8_command(self):
        p = paladin_mount_progression(8)
        assert p.bonus_hd == 4
        assert p.natural_armor_adj == 6
        assert p.str_adj == 2
        assert p.int_score == 7
        assert p.command is True
        assert p.spell_resistance == 0

    def test_level_11_sr(self):
        p = paladin_mount_progression(11)
        assert p.bonus_hd == 6
        assert p.natural_armor_adj == 8
        assert p.str_adj == 3
        assert p.int_score == 8
        assert p.command is True
        assert p.spell_resistance == 16   # 11 + 5

    def test_level_15_sr(self):
        p = paladin_mount_progression(15)
        assert p.bonus_hd == 8
        assert p.str_adj == 4
        assert p.int_score == 9
        assert p.spell_resistance == 20   # 15 + 5

    def test_level_20_sr(self):
        p = paladin_mount_progression(20)
        assert p.spell_resistance == 25   # 20 + 5

    def test_below_5_raises(self):
        with pytest.raises(ValueError):
            paladin_mount_progression(4)


# ===========================================================================
# E-036  Familiar Registry
# ===========================================================================

class TestFamiliarRegistry:
    def test_all_species_present(self):
        for species in FamiliarSpecies:
            assert species in FAMILIAR_REGISTRY

    def test_base_values(self):
        bat = FAMILIAR_REGISTRY[FamiliarSpecies.Bat]
        assert bat.natural_armor_bonus == 2
        assert bat.int_score == 6
        assert "Listen" in bat.special_master_bonus

    def test_rat_fortitude(self):
        rat = FAMILIAR_REGISTRY[FamiliarSpecies.Rat]
        assert "Fortitude" in rat.special_master_bonus

    def test_toad_hp(self):
        toad = FAMILIAR_REGISTRY[FamiliarSpecies.Toad]
        assert "hit points" in toad.special_master_bonus

    def test_raven_speech(self):
        raven = FAMILIAR_REGISTRY[FamiliarSpecies.Raven]
        assert "speech" in raven.special_master_bonus.lower()

    def test_weasel_reflex(self):
        assert "Reflex" in FAMILIAR_REGISTRY[FamiliarSpecies.Weasel].special_master_bonus


# ===========================================================================
# E-037  Animal Companion Registry
# ===========================================================================

class TestAnimalCompanionRegistry:
    def test_standard_species_present(self):
        standard = [
            "Badger", "Camel", "Dire Rat", "Dog", "Riding Dog",
            "Eagle", "Hawk", "Light Horse", "Heavy Horse", "Owl",
            "Pony", "Small Viper Snake", "Medium Viper Snake",
            "Constrictor Snake", "Wolf",
        ]
        for s in standard:
            assert s in ANIMAL_COMPANION_REGISTRY, f"{s!r} missing"

    def test_4th_level_species(self):
        assert "Ape" in ANIMAL_COMPANION_REGISTRY
        assert ANIMAL_COMPANION_REGISTRY["Ape"].effective_druid_level == 3

    def test_7th_level_species(self):
        assert "Brown Bear" in ANIMAL_COMPANION_REGISTRY
        assert ANIMAL_COMPANION_REGISTRY["Brown Bear"].effective_druid_level == 6

    def test_10th_level_species(self):
        assert "Dire Lion" in ANIMAL_COMPANION_REGISTRY
        assert ANIMAL_COMPANION_REGISTRY["Dire Lion"].effective_druid_level == 9

    def test_13th_level_species(self):
        assert "Dire Bear" in ANIMAL_COMPANION_REGISTRY
        assert ANIMAL_COMPANION_REGISTRY["Dire Bear"].effective_druid_level == 12

    def test_16th_level_species(self):
        assert "Purple Worm" in ANIMAL_COMPANION_REGISTRY
        assert ANIMAL_COMPANION_REGISTRY["Purple Worm"].effective_druid_level == 15

    def test_wolf_cr(self):
        assert ANIMAL_COMPANION_REGISTRY["Wolf"].base_cr == 2.0


# ===========================================================================
# E-038  Paladin Mount Registry
# ===========================================================================

class TestPaladinMountRegistry:
    def test_heavy_warhorse_present(self):
        assert "heavy_warhorse" in PALADIN_MOUNT_REGISTRY

    def test_warpony_present(self):
        assert "warpony" in PALADIN_MOUNT_REGISTRY

    def test_base_values(self):
        hw = PALADIN_MOUNT_REGISTRY["heavy_warhorse"]
        assert hw.bonus_hd == 2
        assert hw.natural_armor_adj == 4
        assert hw.str_adj == 1
        assert hw.int_score == 6
        assert hw.empathic_link is True
        assert hw.command is False
        assert hw.spell_resistance == 0


# ===========================================================================
# E-048  Familiar Acquisition Engine
# ===========================================================================

class TestAcquireFamiliar:
    def test_wizard_acquires_familiar(self):
        link, fb = acquire_familiar(
            master_id="wiz1", master_char_class="Wizard",
            master_level=5, master_feats=[],
            species=FamiliarSpecies.Cat, gold_available=1000.0,
        )
        assert link.link_type is LinkType.Familiar
        assert link.master_id == "wiz1"
        assert fb.int_score == familiar_int_score(5)
        assert fb.natural_armor_bonus == familiar_natural_armor_bonus(5)

    def test_sorcerer_acquires_familiar(self):
        link, fb = acquire_familiar(
            master_id="sorc1", master_char_class="Sorcerer",
            master_level=3, master_feats=[],
            species=FamiliarSpecies.Owl, gold_available=500.0,
        )
        assert fb.species == "Owl"

    def test_wrong_class_raises(self):
        with pytest.raises(FamiliarError):
            acquire_familiar(
                master_id="ftr1", master_char_class="Fighter",
                master_level=5, master_feats=[],
                species=FamiliarSpecies.Bat, gold_available=1000.0,
            )

    def test_improved_familiar_feat_allows(self):
        link, fb = acquire_familiar(
            master_id="ftr1", master_char_class="Fighter",
            master_level=5, master_feats=["Improved Familiar"],
            species=FamiliarSpecies.Bat, gold_available=1000.0,
        )
        assert link is not None

    def test_insufficient_gold_raises(self):
        with pytest.raises(FamiliarError):
            acquire_familiar(
                master_id="wiz1", master_char_class="Wizard",
                master_level=10, master_feats=[],
                species=FamiliarSpecies.Cat, gold_available=100.0,
            )

    def test_cost_exact_gold_succeeds(self):
        link, _ = acquire_familiar(
            master_id="wiz1", master_char_class="Wizard",
            master_level=7, master_feats=[],
            species=FamiliarSpecies.Rat, gold_available=700.0,
        )
        assert link is not None

    def test_scry_on_familiar_unlocks_at_13(self):
        _, _ = acquire_familiar(
            master_id="wiz1", master_char_class="Wizard",
            master_level=13, master_feats=[],
            species=FamiliarSpecies.Hawk, gold_available=9999.0,
        )
        # re-acquire to check scry flag
        link, _ = acquire_familiar(
            master_id="wiz2", master_char_class="Wizard",
            master_level=13, master_feats=[],
            species=FamiliarSpecies.Hawk, gold_available=9999.0,
        )
        assert link.scry_on_familiar is True

    def test_scry_on_familiar_false_below_13(self):
        link, _ = acquire_familiar(
            master_id="wiz1", master_char_class="Wizard",
            master_level=5, master_feats=[],
            species=FamiliarSpecies.Cat, gold_available=9999.0,
        )
        assert link.scry_on_familiar is False


# ===========================================================================
# E-049  Animal Companion Acquisition Engine
# ===========================================================================

class TestAcquireAnimalCompanion:
    def test_druid_level_1_wolf(self):
        link, ac = acquire_animal_companion("drd1", 1, "Wolf")
        assert link.link_type is LinkType.AnimalCompanion
        assert ac.species == "Wolf"
        assert ac.bonus_hd == 0       # level 1: no bonus

    def test_druid_level_6_wolf(self):
        _, ac = acquire_animal_companion("drd1", 6, "Wolf")
        # Wolf edl=0, effective druid level = 6-0=6
        prog = animal_companion_progression(6)
        assert ac.bonus_hd == prog.bonus_hd
        assert ac.devotion is True

    def test_unknown_species_raises(self):
        with pytest.raises(CompanionError):
            acquire_animal_companion("drd1", 5, "Dragon")

    def test_level_too_low_for_companion(self):
        with pytest.raises(CompanionError):
            acquire_animal_companion("drd1", 2, "Ape")  # Ape needs edl=3

    def test_exactly_meets_level_requirement(self):
        link, ac = acquire_animal_companion("drd1", 3, "Ape")
        assert ac.species == "Ape"

    def test_high_level_list(self):
        link, ac = acquire_animal_companion("drd1", 15, "Purple Worm")
        assert ac.species == "Purple Worm"

    def test_evasion_at_druid_level_2(self):
        _, ac = acquire_animal_companion("drd1", 2, "Wolf")
        assert ac.evasion is True


# ===========================================================================
# E-050  Paladin Special Mount Summoning Engine
# ===========================================================================

class TestSummonSpecialMount:
    def test_level_5_heavy_warhorse(self):
        link, sm = summon_special_mount("pal1", 5)
        assert link.link_type is LinkType.SpecialMount
        assert sm.species == "heavy_warhorse"
        assert sm.bonus_hd == 2
        assert sm.command is False

    def test_level_8_command(self):
        _, sm = summon_special_mount("pal1", 8)
        assert sm.command is True

    def test_level_11_sr(self):
        _, sm = summon_special_mount("pal1", 11)
        assert sm.spell_resistance == 16

    def test_level_below_5_raises(self):
        with pytest.raises(MountError):
            summon_special_mount("pal1", 4)

    def test_unknown_species_raises(self):
        with pytest.raises(MountError):
            summon_special_mount("pal1", 5, mount_species="unicorn")

    def test_warpony_species(self):
        link, sm = summon_special_mount("pal1", 5, mount_species="warpony")
        assert sm.species == "warpony"

    def test_link_share_spells(self):
        link, _ = summon_special_mount("pal1", 5)
        assert link.share_spells is True


# ===========================================================================
# E-056  MasterMinionTurnTracker
# ===========================================================================

class _FakeRng:
    """Deterministic fake RNG returning a cycling sequence."""
    def __init__(self, values: list[int]):
        self._values = values
        self._idx = 0

    def randint(self, a: int, b: int) -> int:
        val = self._values[self._idx % len(self._values)]
        self._idx += 1
        return val


class TestMasterMinionTurnTracker:
    def _make_link(self, mid="m1", fid="f1") -> MasterMinionLink:
        return MasterMinionLink(
            master_id=mid, minion_id=fid,
            link_type=LinkType.Familiar,
            share_spells=True, empathic_link=True,
            delivery_touch=True, scry_on_familiar=False,
        )

    def test_roll_initiative_records_values(self):
        link = self._make_link()
        tracker = MasterMinionTurnTracker(links=[link], initiative_map={})
        rng = _FakeRng([12, 7])
        master_init, minion_init = tracker.roll_initiative_for_link(link, rng)
        assert master_init == 12
        assert minion_init == 7
        assert tracker.initiative_map["m1"] == 12
        assert tracker.initiative_map["f1"] == 7

    def test_synchronise_actions_adds_master(self):
        link = self._make_link()
        tracker = MasterMinionTurnTracker(links=[link], initiative_map={})
        state = tracker.synchronise_actions({})
        assert "m1" in state["move_action_spent"]

    def test_synchronise_preserves_existing_state(self):
        link = self._make_link()
        tracker = MasterMinionTurnTracker(links=[link], initiative_map={})
        state = tracker.synchronise_actions({"foo": "bar"})
        assert state["foo"] == "bar"

    def test_multiple_links(self):
        links = [self._make_link("m1", "f1"), self._make_link("m2", "f2")]
        tracker = MasterMinionTurnTracker(links=links, initiative_map={})
        rng = _FakeRng([10, 8, 15, 3])
        for link in links:
            tracker.roll_initiative_for_link(link, rng)
        assert tracker.initiative_map["m1"] == 10
        assert tracker.initiative_map["f1"] == 8
        assert tracker.initiative_map["m2"] == 15


# ===========================================================================
# E-057  Share Spells & Empathic Link
# ===========================================================================

class TestShareSpell:
    def _link(self, share_spells=True) -> MasterMinionLink:
        return MasterMinionLink(
            master_id="m1", minion_id="f1",
            link_type=LinkType.Familiar,
            share_spells=share_spells, empathic_link=True,
            delivery_touch=True, scry_on_familiar=False,
        )

    def test_allowed(self):
        result = share_spell(self._link(), "Mage Armor", "Personal", 0.0)
        assert result.allowed is True

    def test_self_range_allowed(self):
        result = share_spell(self._link(), "Shield", "Self", 5.0)
        assert result.allowed is True

    def test_denied_share_spells_false(self):
        result = share_spell(self._link(share_spells=False), "Mage Armor", "Personal", 0.0)
        assert result.allowed is False

    def test_denied_wrong_range(self):
        result = share_spell(self._link(), "Magic Missile", "Close", 5.0)
        assert result.allowed is False

    def test_denied_too_far(self):
        result = share_spell(self._link(), "Mage Armor", "Personal", 10.0)
        assert result.allowed is False

    def test_exactly_5ft_allowed(self):
        result = share_spell(self._link(), "Mage Armor", "Personal", 5.0)
        assert result.allowed is True


class TestEmpathicLink:
    def _link(self, empathic=True) -> MasterMinionLink:
        return MasterMinionLink(
            master_id="m1", minion_id="f1",
            link_type=LinkType.Familiar,
            share_spells=True, empathic_link=empathic,
            delivery_touch=True, scry_on_familiar=False,
        )

    def test_within_range(self):
        msg = empathic_link_message(self._link(), "fear", 0.5)
        assert "fear" in msg
        assert "m1" in msg

    def test_out_of_range(self):
        msg = empathic_link_message(self._link(), "joy", 2.0)
        assert "not transmitted" in msg

    def test_no_link(self):
        msg = empathic_link_message(self._link(empathic=False), "pain", 0.1)
        assert "No empathic link" in msg

    def test_exactly_1_mile_allowed(self):
        msg = empathic_link_message(self._link(), "hunger", 1.0)
        assert "hunger" in msg


class TestDonateHp:
    def _link(self) -> MasterMinionLink:
        return MasterMinionLink(
            master_id="m1", minion_id="f1",
            link_type=LinkType.Familiar,
            share_spells=True, empathic_link=True,
            delivery_touch=True, scry_on_familiar=False,
        )

    def test_normal_transfer(self):
        new_hp, transferred = donate_hp(self._link(), 20, 5)
        assert new_hp == 15
        assert transferred == 5

    def test_transfer_clamped_to_hp(self):
        new_hp, transferred = donate_hp(self._link(), 3, 10)
        assert new_hp == 0
        assert transferred == 3

    def test_zero_transfer(self):
        new_hp, transferred = donate_hp(self._link(), 10, 0)
        assert new_hp == 10
        assert transferred == 0

    def test_negative_delta_raises(self):
        with pytest.raises(ValueError):
            donate_hp(self._link(), 10, -1)


# ===========================================================================
# master_minion.py integration
# ===========================================================================

class TestResolveMinionTurns:
    def _make_tracker(self) -> MasterMinionTurnTracker:
        link = MasterMinionLink(
            master_id="m1", minion_id="f1",
            link_type=LinkType.Familiar,
            share_spells=True, empathic_link=True,
            delivery_touch=True, scry_on_familiar=False,
        )
        return MasterMinionTurnTracker(links=[link], initiative_map={})

    def test_returns_dict_with_initiative(self):
        tracker = self._make_tracker()
        state = resolve_minion_turns(tracker, {}, random)
        assert "initiative_map" in state
        assert "m1" in state["initiative_map"]
        assert "f1" in state["initiative_map"]

    def test_move_action_recorded(self):
        tracker = self._make_tracker()
        state = resolve_minion_turns(tracker, {}, random)
        assert "m1" in state["move_action_spent"]

    def test_existing_state_preserved(self):
        tracker = self._make_tracker()
        state = resolve_minion_turns(tracker, {"round": 1}, random)
        assert state["round"] == 1

    def test_full_integration_all_keys_present(self):
        tracker = self._make_tracker()
        state = resolve_minion_turns(tracker, {"round": 2}, random)
        assert "initiative_map" in state
        assert "move_action_spent" in state
        assert "m1" in state["initiative_map"]
        assert "f1" in state["initiative_map"]
        assert "m1" in state["move_action_spent"]
        assert state["round"] == 2
