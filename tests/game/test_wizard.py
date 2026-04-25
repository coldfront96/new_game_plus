"""Tests for ``src.game.wizard`` (Task 2 — character creation wizard)."""

from __future__ import annotations

import io
import random

import pytest

from src.game.wizard import (
    CharacterWizard,
    SUPPORTED_CLASSES,
    point_buy_cost,
    point_buy_total,
    roll_4d6_drop_lowest,
    validate_point_buy,
)
from src.rules_engine.character_35e import Character35e
from src.rules_engine.race import RaceRegistry


def _script(*lines: str) -> io.StringIO:
    """Return a StringIO that yields each prompt answer in order."""
    return io.StringIO("\n".join(lines) + "\n")


def _blank_out() -> io.StringIO:
    return io.StringIO()


def test_roll_4d6_drop_lowest_range():
    rng = random.Random(1)
    for _ in range(200):
        score = roll_4d6_drop_lowest(rng)
        # Three d6 sum — min 3, max 18
        assert 3 <= score <= 18


def test_point_buy_cost_table():
    # SRD PHB p.169 reference values
    assert point_buy_cost(8) == 0
    assert point_buy_cost(10) == 2
    assert point_buy_cost(15) == 8
    assert point_buy_cost(18) == 16


def test_point_buy_cost_out_of_range():
    with pytest.raises(ValueError):
        point_buy_cost(7)
    with pytest.raises(ValueError):
        point_buy_cost(19)


def test_point_buy_total_and_validate():
    scores = [15, 14, 13, 12, 10, 8]  # canonical 25-point array
    assert point_buy_total(scores) == 25
    validate_point_buy(scores, budget=25)
    with pytest.raises(ValueError):
        validate_point_buy([18, 18, 18, 18, 18, 18], budget=25)


def test_wizard_full_flow_with_rolled_scores():
    # Script (one line per prompt):
    #   name, race (1 = Dwarf — first alpha-sorted), class (5 = Fighter),
    #   then 6 score assignments (always pick the first remaining), then
    #   skills ("done"), then feats — default to (skip) × 2 (Fighter=2 feats).
    # Race list is sorted alphabetically, so index 1 selects "Dwarf".
    # class index 5 from SUPPORTED_CLASSES = "Fighter".
    script = _script(
        "Thoric",      # name
        "1",           # race 1 = Dwarf (first in sorted list)
        "5",           # class 5 = Fighter
        # ability-score assignments (6 prompts)
        "1", "1", "1", "1", "1", "1",
        # skills — the "done" option is the last entry
        "",            # take default (= "done" entry) to exit skills
        "",            # fallback for any extra prompt
    )
    wizard = CharacterWizard(
        stdin=script,
        stdout=_blank_out(),
        rng=random.Random(42),
    )
    char = wizard.run(name=None, method="4d6")
    assert isinstance(char, Character35e)
    assert char.name == "Thoric"
    assert char.race in RaceRegistry.all_names()
    assert char.char_class in SUPPORTED_CLASSES
    # All six ability scores are set within reasonable range.
    for ability in ("strength", "dexterity", "constitution",
                    "intelligence", "wisdom", "charisma"):
        val = getattr(char, ability)
        assert 3 <= val <= 18
    # Starting equipment is non-empty for a Fighter.
    if char.char_class == "Fighter":
        assert char.equipment  # e.g. Longsword, Chain Shirt …


def test_wizard_point_buy_enforces_budget():
    # Try to overspend: all 18s on point-buy.
    script = _script(
        "Grim",  # name
        "1",     # race
        "5",     # class — Fighter
        # Six attempts at 18 each → over budget → wizard re-prompts the full set.
        "18", "18", "18", "18", "18", "18",
        # On second attempt use a legal 25-point spread.
        "15", "14", "13", "12", "10", "8",
        "",   # skills → done
    )
    wizard = CharacterWizard(
        stdin=script,
        stdout=_blank_out(),
        rng=random.Random(0),
    )
    char = wizard.run(method="point-buy", point_buy_budget=25)
    # The legal spread wins out.
    scores = sorted([char.strength, char.dexterity, char.constitution,
                     char.intelligence, char.wisdom, char.charisma])
    assert scores == [8, 10, 12, 13, 14, 15]


def test_wizard_paladin_default_alignment():
    # Paladin (index 7 in SUPPORTED_CLASSES → "Paladin")
    script = _script(
        "Astra",
        "1",     # race
        str(SUPPORTED_CLASSES.index("Paladin") + 1),  # class
        "1", "1", "1", "1", "1", "1",
        "",   # skills done
    )
    wizard = CharacterWizard(
        stdin=script,
        stdout=_blank_out(),
        rng=random.Random(1),
    )
    char = wizard.run(method="4d6")
    assert char.char_class == "Paladin"
    # Paladins must be Lawful Good by SRD rules — wizard's default handles that
    char.validate_alignment()


def test_wizard_respects_race_size():
    # Halflings are Small — pick them and check size was set correctly.
    races_sorted = RaceRegistry.all_names()
    halfling_idx = races_sorted.index("Halfling") + 1
    script = _script(
        "Bandit",
        str(halfling_idx),
        str(SUPPORTED_CLASSES.index("Rogue") + 1),
        "1", "1", "1", "1", "1", "1",
        "",  # skills done
    )
    wizard = CharacterWizard(stdin=script, stdout=_blank_out(),
                             rng=random.Random(9))
    char = wizard.run(method="4d6")
    assert char.race == "Halfling"
    assert char.size.name == "SMALL"
