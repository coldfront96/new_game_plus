"""
src/agent_orchestration/result_parser.py
----------------------------------------
Validate LLM responses against expected schemas (Task 10).

The :class:`ResultParser` does three things:

1. Extract a JSON object from the model's raw text (LLMs often wrap
   responses in markdown fences or chatty preamble; we tolerate both).
2. Validate the parsed dict against a per-task-type schema (a tiny,
   dependency-free schema is built into this module to keep the package
   import cost low).
3. Surface the result as a :class:`ParseResult` so callers can decide
   whether to mark the task ``COMPLETED`` or re-queue it via the
   :class:`Scheduler`.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple, Union

from src.agent_orchestration.agent_task import TaskType


# ---------------------------------------------------------------------------
# Schema description
# ---------------------------------------------------------------------------

# A schema is a mapping ``field_name → spec`` where *spec* is one of:
#   * a Python type (``str``, ``int``, ``float``, ``bool``, ``list``, ``dict``)
#   * a tuple of accepted types
#   * a callable ``value -> bool`` (returns True if value is acceptable)
#
# Optional fields may be marked by prefixing the field name with ``?``.

SchemaSpec = Mapping[str, Any]


_DEFAULT_SCHEMAS: Dict[str, SchemaSpec] = {
    TaskType.ROLL_NPC_STATS.value: {
        "name": str,
        "char_class": str,
        "level": int,
        "strength": int,
        "dexterity": int,
        "constitution": int,
        "intelligence": int,
        "wisdom": int,
        "charisma": int,
        "?race": str,
        "?alignment": str,
    },
    TaskType.GENERATE_ENCOUNTER.value: {
        "monsters": list,
        "?terrain": str,
        "?difficulty": str,
        "?cr": (int, float),
    },
    TaskType.GENERATE_DUNGEON.value: {
        "rooms": list,
        "?theme": str,
    },
    TaskType.GENERATE_ITEM.value: {
        "name": str,
        "?slot": str,
        "?aura": str,
        "?price_gp": (int, float),
        "?bonuses": list,
    },
    TaskType.WRITE_LORE.value: {
        "title": str,
        "body": str,
    },
    TaskType.CODE_GENERATION.value: {
        "language": str,
        "code": str,
    },
}


# ---------------------------------------------------------------------------
# Errors / results
# ---------------------------------------------------------------------------

class SchemaError(Exception):
    """Raised when a parsed dict does not satisfy the requested schema."""


@dataclass
class ParseResult:
    """Outcome of parsing a single LLM response.

    Attributes:
        ok:         Whether parsing succeeded and the schema validated.
        data:       The validated payload (``None`` when ``ok`` is False).
        error:      Human-readable error message on failure.
        raw_text:   The original model response (kept for audit logs).
    """

    ok: bool
    data: Optional[Dict[str, Any]] = None
    error: str = ""
    raw_text: str = ""


# ---------------------------------------------------------------------------
# JSON extraction
# ---------------------------------------------------------------------------

_JSON_FENCE_RE = re.compile(
    r"```(?:json)?\s*(?P<body>\{.*?\}|\[.*?\])\s*```",
    re.DOTALL | re.IGNORECASE,
)
_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(text: str) -> Optional[Any]:
    """Pull the first JSON object/array out of *text*, tolerating fences."""
    if not text:
        return None
    text = text.strip()

    # Plain JSON?
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Markdown-fenced JSON?
    fence = _JSON_FENCE_RE.search(text)
    if fence:
        try:
            return json.loads(fence.group("body"))
        except json.JSONDecodeError:
            pass

    # First { ... } block?
    match = _JSON_OBJECT_RE.search(text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

def _validate_field(name: str, value: Any, spec: Any) -> Optional[str]:
    if callable(spec) and not isinstance(spec, type) and not isinstance(spec, tuple):
        if not spec(value):
            return f"field {name!r} failed callable spec"
        return None
    if isinstance(spec, tuple):
        if not isinstance(value, spec):
            return f"field {name!r} should be one of {spec}, got {type(value).__name__}"
        return None
    if isinstance(spec, type):
        if not isinstance(value, spec):
            return f"field {name!r} should be {spec.__name__}, got {type(value).__name__}"
        return None
    return f"field {name!r} has unrecognised spec: {spec!r}"


def _validate_dict(payload: Mapping[str, Any], schema: SchemaSpec) -> List[str]:
    errors: List[str] = []
    if not isinstance(payload, Mapping):
        return [f"expected dict, got {type(payload).__name__}"]
    for raw_key, spec in schema.items():
        optional = raw_key.startswith("?")
        key = raw_key[1:] if optional else raw_key
        if key not in payload:
            if optional:
                continue
            errors.append(f"missing required field {key!r}")
            continue
        err = _validate_field(key, payload[key], spec)
        if err:
            errors.append(err)
    return errors


# ---------------------------------------------------------------------------
# ResultParser
# ---------------------------------------------------------------------------

@dataclass
class ResultParser:
    """Parses LLM responses against per-task schemas.

    Attributes:
        schemas: Mapping of task_type → schema spec.  Initialised with
                 :data:`_DEFAULT_SCHEMAS`; callers may extend this in
                 place to add custom task types.
    """

    schemas: Dict[str, SchemaSpec] = field(
        default_factory=lambda: dict(_DEFAULT_SCHEMAS)
    )

    def register_schema(self, task_type: str, schema: SchemaSpec) -> None:
        """Register or override the schema for *task_type*."""
        self.schemas[task_type] = schema

    def parse(self, raw_text: str, task_type: str) -> ParseResult:
        """Extract JSON from *raw_text* and validate it for *task_type*.

        Returns a :class:`ParseResult`.  Never raises — failures are
        surfaced as ``ok=False`` so the orchestration layer can mark the
        task ``FAILED`` (with retries) instead of crashing the loop.
        """
        data = _extract_json(raw_text)
        if data is None:
            return ParseResult(
                ok=False,
                error="response did not contain a JSON object",
                raw_text=raw_text,
            )
        if not isinstance(data, dict):
            # Lists are allowed but most schemas expect dicts; wrap into
            # an envelope so the schema check has something to inspect.
            data = {"items": data}

        schema = self.schemas.get(task_type)
        if schema is None:
            # Unknown task type — accept any dict.
            return ParseResult(ok=True, data=data, raw_text=raw_text)

        errors = _validate_dict(data, schema)
        if errors:
            return ParseResult(
                ok=False,
                data=data,
                error="; ".join(errors),
                raw_text=raw_text,
            )
        return ParseResult(ok=True, data=data, raw_text=raw_text)
