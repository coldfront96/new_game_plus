"""Tests for ``src.game.session`` (Task 5 + Task 6 — combat loop & e2e)."""

from __future__ import annotations

import io
import random

import pytest

from src.game.session import (
    apply_damage,
    build_monsters_from_blueprint,
    current_hp,
    is_alive,
    play_session,
)
from src.rules_engine.character_35e import Alignment, Character35e, Size
from src.rules_engine.encounter_extended import (
    EncounterBlueprint,
    EncounterDifficulty,
    build_encounter,
)


def _party(count: int = 4, level: int = 3) -> list[Character35e]:
    party = []
    for i in range(count):
        if i == 0:
            c = Character35e(
                name=f"Fighter-{i}",
                char_class="Fighter",
                level=level,
                strength=16,
                constitution=14,
                dexterity=13,
            )
        elif i == 1:
            c = Character35e(
                name=f"Cleric-{i}",
                char_class="Cleric",
                level=level,
                strength=14,
                constitution=14,
                wisdom=16,
            )
            c.initialize_spellcasting()
        elif i == 2:
            c = Character35e(
                name=f"Rogue-{i}",
                char_class="Rogue",
                level=level,
                strength=12,
                dexterity=16,
                constitution=12,
            )
        else:
            c = Character35e(
                name=f"Wizard-{i}",
                char_class="Wizard",
                level=level,
                intelligence=17,
                constitution=12,
                dexterity=14,
            )
            c.initialize_spellcasting()
        party.append(c)
    return party


def test_current_hp_initialises_from_hit_points():
    c = Character35e(name="X", char_class="Fighter", level=3,
                     constitution=14)
    assert current_hp(c) == c.hit_points


def test_apply_damage_reduces_current_hp():
    c = Character35e(name="X", char_class="Fighter", level=1, constitution=14)
    max_hp = c.hit_points
    apply_damage(c, 3)
    assert current_hp(c) == max_hp - 3
    assert is_alive(c) is True


def test_apply_damage_kills_at_zero_or_below():
    c = Character35e(name="X", char_class="Fighter", level=1, constitution=10)
    apply_damage(c, 999)
    assert current_hp(c) <= 0
    assert is_alive(c) is False


def test_build_monsters_from_blueprint_respects_counts():
    rng = random.Random(3)
    blueprint = build_encounter(
        apl=2,
        difficulty=EncounterDifficulty.AVERAGE,
        terrain="dungeon",
        rng=rng,
    )
    total = sum(count for _, count, _ in blueprint.monsters)
    monsters = build_monsters_from_blueprint(blueprint)
    assert len(monsters) == total
    for mon in monsters:
        assert mon.metadata.get("side") == "enemy"


def test_play_session_against_trivial_encounter_ends_in_victory():
    party = _party(level=5)
    # Hand-craft a pushover blueprint: one CR 1/3 goblin.
    blueprint = EncounterBlueprint(
        target_el=1.0,
        actual_el=1.0,
        monsters=[("Goblin", 1, 0.33)],
        difficulty=EncounterDifficulty.EASY,
        terrain="dungeon",
    )
    out = io.StringIO()
    report = play_session(
        party,
        apl=5,
        terrain="dungeon",
        difficulty="easy",
        rng=random.Random(0),
        max_rounds=30,
        stdout=out,
        blueprint=blueprint,
    )
    assert report.outcome == "victory"
    assert report.rounds >= 1
    assert report.xp_awarded  # XP distributed
    assert report.treasure is not None
    assert all(c.char_id in report.xp_awarded for c in party)
    # Log captured something.
    assert len(report.log) > 0
    assert "Encounter" in out.getvalue()


def test_play_session_against_overwhelming_encounter_can_result_in_defeat():
    # Level-1 party vs a CR-10 solo monster.  With sufficient rounds the
    # party should eventually fall (the test only asserts the loop
    # terminates cleanly with a reported outcome).
    party = _party(count=2, level=1)
    blueprint = EncounterBlueprint(
        target_el=10.0,
        actual_el=10.0,
        monsters=[("Dragon", 1, 10.0)],
        difficulty=EncounterDifficulty.OVERWHELMING,
        terrain="dungeon",
    )
    report = play_session(
        party,
        apl=1,
        terrain="dungeon",
        difficulty="overwhelming",
        rng=random.Random(7),
        max_rounds=50,
        stdout=io.StringIO(),
        blueprint=blueprint,
    )
    assert report.outcome in {"victory", "defeat", "mutual", "stalemate"}
    assert report.rounds <= 50


def test_end_to_end_party_vs_encounter(tmp_path):
    """Task 6 — full cycle: party build → encounter → combat → XP+treasure.

    Uses fixed RNG seeds so the assertion values are reproducible.
    """
    rng = random.Random(12345)
    party = _party(count=4, level=3)
    # Craft a winnable encounter: three CR 1/3 goblins.
    blueprint = EncounterBlueprint(
        target_el=3.0,
        actual_el=2.0,
        monsters=[("Goblin", 3, 0.33)],
        difficulty=EncounterDifficulty.AVERAGE,
        terrain="dungeon",
    )
    report = play_session(
        party,
        apl=3,
        terrain="dungeon",
        difficulty="average",
        rng=rng,
        max_rounds=40,
        stdout=io.StringIO(),
        blueprint=blueprint,
    )
    assert report.outcome in {"victory", "mutual"}
    # Every PC had an XP awarded (only populated on victory)
    if report.outcome == "victory":
        assert len(report.xp_awarded) == 4
        # XP amount sane for EL 2 @ party of 4 = 300 base / 4 = 75 (roughly).
        for amount in report.xp_awarded.values():
            assert amount >= 0
            assert amount < 10_000  # sanity
        assert report.treasure is not None
        assert report.treasure.total_value_gp >= 0

    # Survivors + casualties partition the party.
    names_split = {c.name for c in report.survivors} | {
        c.name for c in report.casualties
    }
    assert names_split == {c.name for c in party}
