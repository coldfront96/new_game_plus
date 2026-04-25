"""Tests for ``src.game.persistence`` (Task 3 — save/load round-trip)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.game.persistence import (
    deserialize_character,
    list_saved_parties,
    load_party,
    load_party_with_state,
    save_party,
    serialize_character,
    xp_manager_from_record,
)
from src.rules_engine.character_35e import Alignment, Character35e, Size
from src.rules_engine.conditions import (
    ConditionManager,
    create_blinded,
    create_prone,
)
from src.rules_engine.magic_items import (
    WONDROUS_ITEM_REGISTRY,
    MagicItemEngine,
)
from src.rules_engine.progression import XPManager


def _make_fighter() -> Character35e:
    c = Character35e(
        name="Aldric",
        char_class="Fighter",
        level=5,
        race="Human",
        alignment=Alignment.LAWFUL_GOOD,
        size=Size.MEDIUM,
        strength=16,
        dexterity=13,
        constitution=14,
        intelligence=10,
        wisdom=12,
        charisma=8,
    )
    return c


def _make_wizard() -> Character35e:
    c = Character35e(
        name="Vex",
        char_class="Wizard",
        level=3,
        race="Elf",
        intelligence=17,
    )
    c.initialize_spellcasting()
    return c


def test_save_and_load_party_round_trip(tmp_path: Path):
    party = [_make_fighter(), _make_wizard()]
    save_party("test_party", party, directory=tmp_path)

    loaded = load_party("test_party", directory=tmp_path)
    assert len(loaded) == 2
    loaded_by_name = {c.name: c for c in loaded}

    original_fighter = party[0]
    restored_fighter = loaded_by_name["Aldric"]

    # AC / HP / saves must match after round-trip.
    assert restored_fighter.armor_class == original_fighter.armor_class
    assert restored_fighter.hit_points == original_fighter.hit_points
    assert restored_fighter.fortitude_save == original_fighter.fortitude_save
    assert restored_fighter.reflex_save == original_fighter.reflex_save
    assert restored_fighter.will_save == original_fighter.will_save
    assert restored_fighter.char_id == original_fighter.char_id

    # Wizard spell-slot manager must be reinstated.
    restored_wizard = loaded_by_name["Vex"]
    assert restored_wizard.is_caster
    assert restored_wizard.spell_slot_manager is not None


def test_save_preserves_magic_item_bonuses(tmp_path: Path):
    fighter = _make_fighter()
    engine = MagicItemEngine()
    engine.add_item(WONDROUS_ITEM_REGISTRY["belt_of_giant_strength_4"])
    engine.add_item(WONDROUS_ITEM_REGISTRY["cloak_of_resistance_2"])
    fighter.magic_item_engine = engine
    original_str_mod = fighter.strength_mod
    original_fort = fighter.fortitude_save

    save_party("magic_test", [fighter], directory=tmp_path)
    loaded = load_party("magic_test", directory=tmp_path)[0]

    assert loaded.magic_item_engine is not None
    assert loaded.strength_mod == original_str_mod
    assert loaded.fortitude_save == original_fort


def test_save_preserves_conditions(tmp_path: Path):
    fighter = _make_fighter()
    cm = ConditionManager()
    cm.apply_condition(fighter, create_blinded(duration=5))
    cm.apply_condition(fighter, create_prone(duration=2))

    save_party(
        "cond_test",
        [fighter],
        directory=tmp_path,
        conditions=cm,
    )

    new_cm = ConditionManager()
    loaded = load_party(
        "cond_test",
        directory=tmp_path,
        condition_manager=new_cm,
    )[0]
    active = new_cm.get_conditions(loaded)
    assert {c.name for c in active} == {"Blinded", "Prone"}


def test_save_preserves_xp(tmp_path: Path):
    fighter = _make_fighter()
    xp = XPManager(current_xp=7500, current_level=5)
    save_party(
        "xp_test",
        [fighter],
        directory=tmp_path,
        xp_managers={fighter.char_id: xp},
    )
    state = load_party_with_state("xp_test", directory=tmp_path)
    assert len(state["party"]) == 1
    recovered = xp_manager_from_record(state["records"][0])
    assert recovered is not None
    assert recovered.current_xp == 7500
    assert recovered.current_level == 5


def test_list_saved_parties(tmp_path: Path):
    save_party("alpha", [_make_fighter()], directory=tmp_path)
    save_party("beta", [_make_wizard()], directory=tmp_path)
    names = list_saved_parties(directory=tmp_path)
    assert names == ["alpha", "beta"]


def test_load_missing_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_party("nope", directory=tmp_path)


def test_serialize_is_json_safe(tmp_path: Path):
    fighter = _make_fighter()
    record = serialize_character(fighter)
    # Dumping to JSON must not raise.
    blob = json.dumps(record)
    round_tripped = deserialize_character(json.loads(blob))
    assert round_tripped.hit_points == fighter.hit_points
