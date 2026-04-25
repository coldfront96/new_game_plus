"""Tests for ``src.agent_orchestration.result_parser`` (Task 10)."""

from __future__ import annotations

import json

import pytest

from src.agent_orchestration import ResultParser, TaskType


@pytest.fixture
def parser() -> ResultParser:
    return ResultParser()


def test_plain_json_passes_schema(parser: ResultParser):
    payload = json.dumps({
        "name": "Aldric", "char_class": "Fighter", "level": 5,
        "strength": 16, "dexterity": 13, "constitution": 14,
        "intelligence": 10, "wisdom": 12, "charisma": 8,
    })
    result = parser.parse(payload, TaskType.ROLL_NPC_STATS.value)
    assert result.ok
    assert result.data["name"] == "Aldric"


def test_fenced_json_is_extracted(parser: ResultParser):
    payload = (
        "Here you go!\n\n```json\n"
        '{"name": "X", "char_class": "Wizard", "level": 3,'
        ' "strength": 8, "dexterity": 14, "constitution": 12,'
        ' "intelligence": 18, "wisdom": 13, "charisma": 10}\n'
        "```\nEnjoy."
    )
    result = parser.parse(payload, TaskType.ROLL_NPC_STATS.value)
    assert result.ok
    assert result.data["intelligence"] == 18


def test_missing_required_field_fails(parser: ResultParser):
    payload = json.dumps({"name": "X"})  # missing many fields
    result = parser.parse(payload, TaskType.ROLL_NPC_STATS.value)
    assert not result.ok
    assert "missing" in result.error


def test_wrong_type_fails(parser: ResultParser):
    payload = json.dumps({
        "name": "X", "char_class": "Wizard", "level": "five",  # str instead of int
        "strength": 8, "dexterity": 14, "constitution": 12,
        "intelligence": 18, "wisdom": 13, "charisma": 10,
    })
    result = parser.parse(payload, TaskType.ROLL_NPC_STATS.value)
    assert not result.ok
    assert "level" in result.error


def test_no_json_returns_failure(parser: ResultParser):
    result = parser.parse("Sorry, no JSON here.", TaskType.ROLL_NPC_STATS.value)
    assert not result.ok
    assert "did not contain a JSON" in result.error


def test_unknown_task_type_accepts_any_dict(parser: ResultParser):
    result = parser.parse('{"foo": 1}', "novel-task")
    assert result.ok
    assert result.data == {"foo": 1}


def test_register_custom_schema(parser: ResultParser):
    parser.register_schema(
        "novel-task",
        {"foo": int, "?bar": str},
    )
    bad = parser.parse('{"foo": "not-int"}', "novel-task")
    assert not bad.ok
    good = parser.parse('{"foo": 42, "bar": "x"}', "novel-task")
    assert good.ok


def test_list_payload_wrapped_into_items(parser: ResultParser):
    result = parser.parse("[1, 2, 3]", "anything")
    assert result.ok
    assert result.data == {"items": [1, 2, 3]}
