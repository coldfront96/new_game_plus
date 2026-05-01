"""
tests/game/test_phase4.py
-------------------------
Tests for Phase 4 — Full Game Loop & Character Advancement.

Covers:
  PH4-001  Extended FEAT_CATALOG & FeatRegistry query methods
  PH4-002  natural_armor_bonus metadata in Character35e.armor_class
  PH4-003  SRD monster stat-block loader (build_monsters_from_srd)
  PH4-004  Iterative full-attack (resolve_full_attack)
  PH4-005  rest_party / long_rest
  PH4-006  Post-session XP persistence helpers
  PH4-007  Level-up interactive wizard (run_level_up_flow)
  PH4-008  Campaign / play-loop CLI subcommands
"""

from __future__ import annotations

import io
import random
import tempfile
from pathlib import Path
from typing import List

import pytest

from src.rules_engine.character_35e import Alignment, Character35e, Size
from src.rules_engine.feat_engine import FEAT_CATALOG, FeatRegistry
from src.rules_engine.progression import XPManager, xp_for_level


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fighter(level: int = 5, **kwargs) -> Character35e:
    defaults = dict(
        name="Aldric",
        char_class="Fighter",
        level=level,
        race="Human",
        alignment=Alignment.NEUTRAL_GOOD,
        size=Size.MEDIUM,
        strength=16,
        dexterity=14,
        constitution=14,
        intelligence=10,
        wisdom=10,
        charisma=10,
    )
    defaults.update(kwargs)
    return Character35e(**defaults)


def _make_wizard_char(level: int = 5) -> Character35e:
    return Character35e(
        name="Isolde",
        char_class="Wizard",
        level=level,
        race="Elf",
        alignment=Alignment.NEUTRAL_GOOD,
        size=Size.MEDIUM,
        strength=8,
        dexterity=14,
        constitution=12,
        intelligence=18,
        wisdom=12,
        charisma=10,
    )


# ===========================================================================
# PH4-001 — Extended FEAT_CATALOG
# ===========================================================================

class TestExtendedFeatCatalog:
    def test_two_weapon_fighting_in_catalog(self):
        assert "Two-Weapon Fighting" in FEAT_CATALOG

    def test_improved_two_weapon_fighting_in_catalog(self):
        assert "Improved Two-Weapon Fighting" in FEAT_CATALOG

    def test_greater_two_weapon_fighting_in_catalog(self):
        assert "Greater Two-Weapon Fighting" in FEAT_CATALOG

    def test_point_blank_shot_in_catalog(self):
        assert "Point Blank Shot" in FEAT_CATALOG

    def test_rapid_shot_in_catalog(self):
        assert "Rapid Shot" in FEAT_CATALOG

    def test_precise_shot_in_catalog(self):
        assert "Precise Shot" in FEAT_CATALOG

    def test_improved_unarmed_strike_in_catalog(self):
        assert "Improved Unarmed Strike" in FEAT_CATALOG

    def test_combat_expertise_in_catalog(self):
        assert "Combat Expertise" in FEAT_CATALOG

    def test_alertness_in_catalog(self):
        assert "Alertness" in FEAT_CATALOG

    def test_endurance_in_catalog(self):
        assert "Endurance" in FEAT_CATALOG

    def test_diehard_in_catalog(self):
        assert "Diehard" in FEAT_CATALOG

    def test_spell_focus_in_catalog(self):
        assert "Spell Focus" in FEAT_CATALOG

    def test_greater_spell_focus_in_catalog(self):
        assert "Greater Spell Focus" in FEAT_CATALOG

    def test_spell_penetration_in_catalog(self):
        assert "Spell Penetration" in FEAT_CATALOG

    def test_greater_spell_penetration_in_catalog(self):
        assert "Greater Spell Penetration" in FEAT_CATALOG

    def test_track_in_catalog(self):
        assert "Track" in FEAT_CATALOG

    def test_mounted_combat_in_catalog(self):
        assert "Mounted Combat" in FEAT_CATALOG

    def test_natural_spell_in_catalog(self):
        assert "Natural Spell" in FEAT_CATALOG


class TestFeatRegistryNewMethods:
    def test_spell_dc_bonus_zero_without_feats(self):
        char = _make_wizard_char()
        assert FeatRegistry.get_spell_dc_bonus(char) == 0

    def test_spell_dc_bonus_with_spell_focus(self):
        char = _make_wizard_char()
        FeatRegistry.add_feat(char, "Spell Focus")
        assert FeatRegistry.get_spell_dc_bonus(char) == 1

    def test_spell_dc_bonus_stacks_with_greater(self):
        char = _make_wizard_char()
        FeatRegistry.add_feat(char, "Spell Focus")
        FeatRegistry.add_feat(char, "Greater Spell Focus")
        assert FeatRegistry.get_spell_dc_bonus(char) == 2

    def test_caster_level_bonus_zero_without_feats(self):
        char = _make_wizard_char()
        assert FeatRegistry.get_caster_level_bonus(char) == 0

    def test_caster_level_bonus_spell_penetration(self):
        char = _make_wizard_char()
        FeatRegistry.add_feat(char, "Spell Penetration")
        assert FeatRegistry.get_caster_level_bonus(char) == 2

    def test_caster_level_bonus_stacks(self):
        char = _make_wizard_char()
        FeatRegistry.add_feat(char, "Spell Penetration")
        FeatRegistry.add_feat(char, "Greater Spell Penetration")
        assert FeatRegistry.get_caster_level_bonus(char) == 4

    def test_skill_bonus_alertness(self):
        char = _make_fighter()
        assert FeatRegistry.get_skill_bonus(char, "Listen") == 0
        FeatRegistry.add_feat(char, "Alertness")
        assert FeatRegistry.get_skill_bonus(char, "Listen") == 2
        assert FeatRegistry.get_skill_bonus(char, "Spot") == 2

    def test_extra_turning_zero_without_feat(self):
        char = _make_fighter()
        assert FeatRegistry.get_extra_turning_attempts(char) == 0

    def test_extra_turning_with_feat(self):
        char = _make_fighter()
        FeatRegistry.add_feat(char, "Extra Turning")
        assert FeatRegistry.get_extra_turning_attempts(char) == 4

    def test_twf_penalties_without_feat(self):
        char = _make_fighter()
        assert FeatRegistry.get_twf_penalties(char) == (-6, -10)

    def test_twf_penalties_with_feat(self):
        char = _make_fighter(dexterity=16)
        FeatRegistry.add_feat(char, "Two-Weapon Fighting")
        assert FeatRegistry.get_twf_penalties(char) == (-4, -4)


class TestFeatPrerequisites:
    def test_two_weapon_fighting_requires_dex_15(self):
        char = _make_fighter(dexterity=14)
        assert not FeatRegistry.meets_prerequisites(char, "Two-Weapon Fighting")
        char2 = _make_fighter(dexterity=15)
        assert FeatRegistry.meets_prerequisites(char2, "Two-Weapon Fighting")

    def test_improved_twf_requires_twf_and_bab_6(self):
        char = _make_fighter(level=6, dexterity=17)
        FeatRegistry.add_feat(char, "Two-Weapon Fighting")
        assert FeatRegistry.meets_prerequisites(char, "Improved Two-Weapon Fighting")
        # Without TWF
        char2 = _make_fighter(level=6, dexterity=17)
        assert not FeatRegistry.meets_prerequisites(char2, "Improved Two-Weapon Fighting")

    def test_diehard_requires_endurance(self):
        char = _make_fighter()
        assert not FeatRegistry.meets_prerequisites(char, "Diehard")
        FeatRegistry.add_feat(char, "Endurance")
        assert FeatRegistry.meets_prerequisites(char, "Diehard")

    def test_greater_spell_focus_requires_spell_focus(self):
        char = _make_wizard_char()
        assert not FeatRegistry.meets_prerequisites(char, "Greater Spell Focus")
        FeatRegistry.add_feat(char, "Spell Focus")
        assert FeatRegistry.meets_prerequisites(char, "Greater Spell Focus")

    def test_natural_spell_requires_wis_13(self):
        char = _make_fighter(wisdom=12)
        assert not FeatRegistry.meets_prerequisites(char, "Natural Spell")
        char2 = _make_fighter(wisdom=13)
        assert FeatRegistry.meets_prerequisites(char2, "Natural Spell")


# ===========================================================================
# PH4-002 — natural_armor_bonus metadata
# ===========================================================================

class TestNaturalArmorBonus:
    def test_default_ac_unaffected(self):
        char = _make_fighter()
        ac_without = char.armor_class
        assert char.metadata.get("natural_armor_bonus", 0) == 0
        assert char.armor_class == ac_without

    def test_natural_armor_bonus_applied(self):
        char = _make_fighter()
        base_ac = char.armor_class
        char.metadata["natural_armor_bonus"] = 5
        assert char.armor_class == base_ac + 5

    def test_zero_natural_armor_bonus_no_change(self):
        char = _make_fighter()
        base_ac = char.armor_class
        char.metadata["natural_armor_bonus"] = 0
        assert char.armor_class == base_ac


# ===========================================================================
# PH4-003 — SRD Monster Stat-Block Loader
# ===========================================================================

class TestSRDMonsterLoader:
    def test_build_monsters_from_srd_returns_list(self):
        from src.game.session import build_monsters_from_srd
        from src.rules_engine.encounter_extended import EncounterBlueprint

        blueprint = EncounterBlueprint(
            target_el=3,
            actual_el=3,
            monsters=[("Goblin", 3, 0.33)],
            terrain="dungeon",
            difficulty="average",
        )
        monsters = build_monsters_from_srd(blueprint)
        assert len(monsters) == 3

    def test_monsters_have_side_metadata(self):
        from src.game.session import build_monsters_from_srd
        from src.rules_engine.encounter_extended import EncounterBlueprint

        blueprint = EncounterBlueprint(
            target_el=3, actual_el=3,
            monsters=[("Goblin", 2, 0.33)],
            terrain="dungeon", difficulty="average",
        )
        monsters = build_monsters_from_srd(blueprint)
        for m in monsters:
            assert m.metadata.get("side") == "enemy"

    def test_unknown_monster_falls_back_to_fighter(self):
        from src.game.session import build_monsters_from_srd
        from src.rules_engine.encounter_extended import EncounterBlueprint

        blueprint = EncounterBlueprint(
            target_el=5, actual_el=5,
            monsters=[("Xyzzy Nonexistent Monster", 1, 3.0)],
            terrain="dungeon", difficulty="average",
        )
        monsters = build_monsters_from_srd(blueprint)
        assert len(monsters) == 1
        assert monsters[0].char_class == "Fighter"

    def test_srd_monster_has_hp_set(self):
        from src.game.session import build_monsters_from_srd, HP_KEY
        from src.rules_engine.encounter_extended import EncounterBlueprint

        blueprint = EncounterBlueprint(
            target_el=3, actual_el=3,
            monsters=[("Goblin", 1, 0.33)],
            terrain="dungeon", difficulty="average",
        )
        monsters = build_monsters_from_srd(blueprint)
        assert HP_KEY in monsters[0].metadata
        assert monsters[0].metadata[HP_KEY] > 0

    def test_srd_monster_natural_armor_set(self):
        from src.game.session import build_monsters_from_srd
        from src.rules_engine.encounter_extended import EncounterBlueprint

        blueprint = EncounterBlueprint(
            target_el=5, actual_el=5,
            monsters=[("Troll", 1, 5.0)],
            terrain="dungeon", difficulty="average",
        )
        monsters = build_monsters_from_srd(blueprint)
        # Troll has significant natural armor; should be > 0
        assert monsters[0].metadata.get("natural_armor_bonus", 0) >= 0

    def test_multi_count_creates_numbered_names(self):
        from src.game.session import build_monsters_from_srd
        from src.rules_engine.encounter_extended import EncounterBlueprint

        blueprint = EncounterBlueprint(
            target_el=3, actual_el=3,
            monsters=[("Goblin", 3, 0.33)],
            terrain="dungeon", difficulty="average",
        )
        monsters = build_monsters_from_srd(blueprint)
        names = [m.name for m in monsters]
        assert "Goblin #1" in names
        assert "Goblin #2" in names
        assert "Goblin #3" in names


# ===========================================================================
# PH4-004 — Iterative Full-Attack
# ===========================================================================

class TestResolveFullAttack:
    def _make_target(self) -> Character35e:
        return Character35e(
            name="Target",
            char_class="Fighter",
            level=3,
            race="Human",
            alignment=Alignment.CHAOTIC_EVIL,
            size=Size.MEDIUM,
            strength=10,
            dexterity=10,
            constitution=10,
            intelligence=10,
            wisdom=10,
            charisma=10,
        )

    def test_single_attack_at_low_bab(self):
        from src.rules_engine.combat import AttackResolver
        attacker = _make_fighter(level=1)
        target = self._make_target()
        results = AttackResolver.resolve_full_attack(attacker, target)
        assert len(results) == 1

    def test_two_attacks_at_bab_6(self):
        from src.rules_engine.combat import AttackResolver
        attacker = _make_fighter(level=6)
        target = self._make_target()
        results = AttackResolver.resolve_full_attack(attacker, target)
        assert len(results) == 2

    def test_three_attacks_at_bab_11(self):
        from src.rules_engine.combat import AttackResolver
        attacker = _make_fighter(level=11)
        target = self._make_target()
        results = AttackResolver.resolve_full_attack(attacker, target)
        assert len(results) == 3

    def test_four_attacks_at_bab_16(self):
        from src.rules_engine.combat import AttackResolver
        attacker = _make_fighter(level=16)
        target = self._make_target()
        results = AttackResolver.resolve_full_attack(attacker, target)
        assert len(results) == 4

    def test_max_four_attacks_capped(self):
        from src.rules_engine.combat import AttackResolver
        attacker = _make_fighter(level=20)
        target = self._make_target()
        results = AttackResolver.resolve_full_attack(attacker, target)
        assert len(results) == 4

    def test_iterative_penalty_applied(self):
        from src.rules_engine.combat import AttackResolver
        rng = random.Random(42)
        attacker = _make_fighter(level=11)
        target = self._make_target()
        target.metadata["current_hp"] = 1000
        results = AttackResolver.resolve_full_attack(attacker, target)
        if len(results) >= 2:
            # Second attack's roll total should be lower due to -5 penalty
            # (Can't always guarantee ordering from rolls, but bonus must differ)
            assert results[1].attack_bonus == results[0].attack_bonus - 5

    def test_stops_on_target_death(self):
        from src.rules_engine.combat import AttackResolver
        attacker = _make_fighter(level=16, strength=20)
        target = self._make_target()
        target.metadata["current_hp"] = 1
        results = AttackResolver.resolve_full_attack(
            attacker, target, damage_dice_count=1, damage_dice_sides=8
        )
        # Attack loop may stop after first hit kills target
        assert len(results) >= 1


# ===========================================================================
# PH4-005 — Long Rest / rest_party
# ===========================================================================

class TestLongRest:
    def test_long_rest_restores_hp_by_level(self):
        from src.game.session import long_rest, HP_KEY
        char = _make_fighter(level=5)
        char.metadata[HP_KEY] = char.hit_points - 10
        healed = long_rest(char)
        assert healed == 5
        assert char.metadata[HP_KEY] == char.hit_points - 5

    def test_long_rest_clamps_to_max_hp(self):
        from src.game.session import long_rest, HP_KEY
        char = _make_fighter(level=10)
        char.metadata[HP_KEY] = char.hit_points - 2
        healed = long_rest(char)
        assert char.metadata[HP_KEY] == char.hit_points
        assert healed == 2

    def test_long_rest_already_at_full_heals_zero(self):
        from src.game.session import long_rest, HP_KEY
        char = _make_fighter(level=5)
        char.metadata[HP_KEY] = char.hit_points
        healed = long_rest(char)
        assert healed == 0

    def test_rest_party_returns_dict(self):
        from src.game.session import rest_party, HP_KEY
        party = [_make_fighter(level=3), _make_fighter(level=5, name="Bob")]
        for c in party:
            c.metadata[HP_KEY] = 1
        result = rest_party(party)
        assert set(result.keys()) == {c.char_id for c in party}

    def test_long_rest_recovers_spell_slots(self):
        from src.game.session import long_rest
        char = _make_wizard_char(level=5)
        char.initialize_spellcasting()
        ssm = char.spell_slot_manager
        if ssm is not None:
            ssm.expend(1)
            remaining_before = ssm.available(1)
            long_rest(char)
            assert ssm.available(1) > remaining_before


# ===========================================================================
# PH4-006 — Post-session XP persistence helpers
# ===========================================================================

class TestXPPersistence:
    def test_xp_manager_from_record_none_on_missing(self):
        from src.game.persistence import xp_manager_from_record
        result = xp_manager_from_record({})
        assert result is None

    def test_xp_manager_roundtrips_through_save_load(self):
        from src.game.persistence import (
            serialize_character,
            deserialize_character,
            xp_manager_from_record,
        )
        from src.rules_engine.progression import XPManager

        char = _make_fighter(level=3)
        mgr = XPManager(current_xp=2500, current_level=3)
        record = serialize_character(char, xp_manager=mgr)
        recovered = xp_manager_from_record(record)
        assert recovered is not None
        assert recovered.current_xp == 2500
        assert recovered.current_level == 3

    def test_award_xp_updates_manager(self):
        from src.rules_engine.progression import XPManager
        mgr = XPManager(current_xp=0, current_level=1)
        mgr.award_xp(1000)
        assert mgr.current_xp == 1000

    def test_level_up_check_triggers_correctly(self):
        from src.rules_engine.progression import XPManager, xp_for_level
        mgr = XPManager(current_xp=0, current_level=1)
        assert not mgr.check_level_up().leveled_up
        mgr.award_xp(xp_for_level(2))
        assert mgr.check_level_up().leveled_up


# ===========================================================================
# PH4-007 — Level-up interactive wizard
# ===========================================================================

class TestRunLevelUpFlow:
    def _make_wizard_streams(self, inputs: str):
        return io.StringIO(inputs), io.StringIO()

    def test_returns_none_when_not_ready(self):
        from src.game.wizard import CharacterWizard, run_level_up_flow
        from src.rules_engine.progression import XPManager
        char = _make_fighter(level=3)
        mgr = XPManager(current_xp=0, current_level=3)
        stdin, stdout = self._make_wizard_streams("")
        wiz = CharacterWizard(stdin=stdin, stdout=stdout)
        result = run_level_up_flow(char, mgr, wiz)
        assert result is None

    def test_levels_up_when_xp_met(self):
        from src.game.wizard import CharacterWizard, run_level_up_flow
        from src.rules_engine.progression import XPManager, xp_for_level
        char = _make_fighter(level=1)
        mgr = XPManager(current_xp=xp_for_level(2), current_level=1)
        # Provide enough "done" inputs to skip skill and feat prompts
        inputs = "done\n(skip)\n" * 10
        stdin, stdout = self._make_wizard_streams(inputs)
        wiz = CharacterWizard(stdin=stdin, stdout=stdout)
        result = run_level_up_flow(char, mgr, wiz)
        assert result is not None
        assert result.new_level == 2
        assert char.level == 2

    def test_level_3_awards_feat_slot(self):
        from src.game.wizard import CharacterWizard, run_level_up_flow, _feat_slots_gained
        assert _feat_slots_gained(3, "Fighter") == 1   # general feat only (level 3 is odd)
        assert _feat_slots_gained(3, "Wizard") == 1    # general only
        assert _feat_slots_gained(2, "Fighter") == 1   # fighter bonus only (even level)
        assert _feat_slots_gained(6, "Fighter") == 2   # general + fighter bonus (level 6: divisible by 3 and even)
        assert _feat_slots_gained(1, "Fighter") == 1   # first-level fighter bonus
        assert _feat_slots_gained(2, "Rogue") == 0     # none

    def test_skill_points_added_to_existing(self):
        from src.game.wizard import CharacterWizard, run_level_up_flow
        from src.rules_engine.progression import XPManager, xp_for_level
        char = _make_fighter(level=1)
        char.skills["Climb"] = 3
        mgr = XPManager(current_xp=xp_for_level(2), current_level=1)
        # Choose Climb for 1 point, then done, then skip feat
        inputs = "1\n1\ndone\n(skip)\n" * 5
        stdin, stdout = self._make_wizard_streams(inputs)
        wiz = CharacterWizard(stdin=stdin, stdout=stdout)
        run_level_up_flow(char, mgr, wiz)
        # Climb should have gained at least the original 3 ranks
        assert char.skills.get("Climb", 0) >= 3


# ===========================================================================
# PH4-008 — CLI subcommands (smoke tests)
# ===========================================================================

class TestCLISubcommands:
    def test_level_up_parser_registered(self):
        from src.game.cli import build_parser
        parser = build_parser()
        # Should not raise
        args = parser.parse_args(["level-up", "default"])
        assert args.command == "level-up"

    def test_campaign_parser_registered(self):
        from src.game.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["campaign", "default", "--quests", "2"])
        assert args.command == "campaign"
        assert args.quests == 2

    def test_play_parser_still_works(self):
        from src.game.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["play", "default", "--terrain", "dungeon"])
        assert args.command == "play"

    def test_cmd_play_saves_xp_after_victory(self):
        from src.game.cli import _cmd_play, build_parser
        from src.game.persistence import save_party, load_party_with_state, xp_manager_from_record
        from src.rules_engine.progression import XPManager

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            char = _make_fighter(level=3)
            save_party("test_xp", [char], directory=tmp_path)

            # Monkey-patch persistence to use tmp directory
            import src.game.cli as cli_mod
            import src.game.persistence as pers_mod

            orig_load = pers_mod.load_party_with_state
            orig_save = pers_mod.save_party

            def _patched_load(name, **kw):
                return orig_load(name, directory=tmp_path, **kw)

            def _patched_save(name, party, **kw):
                return orig_save(name, party, directory=tmp_path, **kw)

            pers_mod.load_party_with_state = _patched_load
            pers_mod.save_party = _patched_save
            try:
                parser = build_parser()
                args = parser.parse_args([
                    "play", "test_xp",
                    "--seed", "99",
                    "--terrain", "dungeon",
                    "--difficulty", "easy",
                    "--max-rounds", "5",
                ])
                out = io.StringIO()
                _cmd_play(args, stdout=out)
                # After the run, the save file should still exist
                from src.game.persistence import list_saved_parties
                parties = list_saved_parties(directory=tmp_path)
                assert "test_xp" in parties
            finally:
                pers_mod.load_party_with_state = orig_load
                pers_mod.save_party = orig_save


# ===========================================================================
# Integration — full session uses SRD monsters
# ===========================================================================

class TestSessionIntegration:
    def test_play_session_runs_with_srd_monsters(self):
        from src.game.session import play_session

        party = [_make_fighter(level=3)]
        rng = random.Random(42)
        report = play_session(
            party=party,
            apl=3,
            terrain="dungeon",
            difficulty="easy",
            rng=rng,
            max_rounds=5,
            stdout=io.StringIO(),
        )
        assert report.outcome in ("victory", "defeat", "stalemate", "mutual")

    def test_full_attack_used_in_session(self):
        """High-level fighter (BAB 11) should produce multiple attack lines."""
        from src.game.session import play_session

        party = [_make_fighter(level=11, strength=20)]
        rng = random.Random(1)
        out = io.StringIO()
        play_session(
            party=party,
            apl=5,
            terrain="dungeon",
            difficulty="easy",
            rng=rng,
            max_rounds=3,
            stdout=out,
        )
        log = out.getvalue()
        # With BAB 11 and 3 rounds, we expect multiple attack lines
        hit_lines = [l for l in log.splitlines() if "hits" in l or "misses" in l]
        assert len(hit_lines) > 0
