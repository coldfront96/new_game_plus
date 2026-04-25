"""Tests for ``src.rules_engine.srd_loader`` (Task 7)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.rules_engine.srd_loader import (
    DEFAULT_DATA_DIR,
    load_classes,
    load_encounter_tables,
    load_everything,
    load_feats,
    load_gems_art,
    load_magic_items,
    load_monsters,
    load_poisons_diseases,
    load_races,
    load_spells,
)


def test_default_data_dir_exists():
    assert DEFAULT_DATA_DIR.is_dir(), (
        f"data/srd_3.5/ not found at {DEFAULT_DATA_DIR}"
    )


def test_load_spells_contains_magic_missile():
    spells = load_spells()
    names = {s["name"] for s in spells}
    assert "Magic Missile" in names
    # Every spell must have a level field in range 0–9.
    for s in spells:
        assert 0 <= s["level"] <= 9


def test_load_feats_contains_power_attack():
    feats = load_feats()
    names = {f["name"] for f in feats}
    assert "Power Attack" in names
    assert "Improved Initiative" in names


def test_load_races_has_nine_core_races():
    races = load_races()
    names = {r["name"] for r in races}
    assert {"Human", "Elf", "Dwarf", "Halfling", "Gnome",
            "Half-Elf", "Half-Orc"} <= names


def test_load_classes_has_eleven_core_classes():
    classes = load_classes()
    names = {c["name"] for c in classes}
    core = {"Barbarian", "Bard", "Cleric", "Druid", "Fighter",
            "Monk", "Paladin", "Ranger", "Rogue", "Sorcerer", "Wizard"}
    assert core <= names
    for c in classes:
        assert c["bab_progression"] in ("full", "three_quarter", "half")
        assert c["hit_die"] in (4, 6, 8, 10, 12)


def test_load_monsters_non_empty():
    monsters = load_monsters()
    assert len(monsters) > 10
    for m in monsters:
        assert "name" in m and "cr" in m


def test_load_magic_items_contains_belt():
    items = load_magic_items()
    names = {i["name"] for i in items}
    assert any("Belt" in n for n in names)


def test_load_poisons_diseases_schema():
    data = load_poisons_diseases()
    assert "poisons" in data
    assert "diseases" in data
    if data["poisons"]:
        p = data["poisons"][0]
        assert "name" in p and "dc" in p
    if data["diseases"]:
        d = data["diseases"][0]
        assert "name" in d and "dc" in d


def test_load_gems_art_schema():
    data = load_gems_art()
    assert data["gems"]
    assert data["art_objects"]
    gem = data["gems"][0]
    assert {"name", "grade", "base_value_gp"} <= set(gem.keys())


def test_load_encounter_tables_contains_dungeon_forest():
    tables = load_encounter_tables()
    assert "dungeon" in tables
    assert "forest" in tables
    for entry in tables["dungeon"]:
        assert 1 <= entry["d100_low"] <= entry["d100_high"] <= 100


def test_load_everything_returns_all_categories():
    bag = load_everything()
    expected_keys = {
        "spells", "feats", "races", "classes", "monsters",
        "magic_items", "poisons_diseases", "gems_art", "encounter_tables",
    }
    assert set(bag.keys()) == expected_keys


def test_loader_accepts_custom_data_dir(tmp_path: Path):
    # Point at an empty directory: every loader should return a safe empty value
    empty = load_everything(tmp_path)
    assert empty["spells"] == []
    assert empty["feats"] == []
    assert empty["races"] == []
    assert empty["encounter_tables"] == {}
