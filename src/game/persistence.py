"""
src/game/persistence.py
-----------------------
JSON persistence for parties and characters (Task 3).

A *party* is simply a list of :class:`~src.rules_engine.character_35e.Character35e`
instances serialised into a single JSON file under ``saves/``.  Each
character record also carries dependent state:

* ``magic_item_engine`` — accumulated magic-item bonuses (list of wondrous
  item registry keys)
* ``conditions`` — active condition list (name, duration, modifiers)
* ``xp`` — :class:`~src.rules_engine.progression.XPManager` state

The public API is :func:`save_party` / :func:`load_party`.  The ``saves/``
directory is resolved relative to the repo root so tests can still run
from any CWD.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from src.rules_engine.character_35e import Character35e
from src.rules_engine.conditions import Condition, ConditionManager
from src.rules_engine.magic_items import (
    MagicItemEngine,
    RING_REGISTRY,
    WONDROUS_ITEM_REGISTRY,
    WondrousItem,
)
from src.rules_engine.progression import XPManager


# Repo root = two levels above this file (src/game/persistence.py → repo/)
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_SAVE_DIR = _REPO_ROOT / "saves"


def save_directory() -> Path:
    """Return (and create if needed) the ``saves/`` directory."""
    _DEFAULT_SAVE_DIR.mkdir(parents=True, exist_ok=True)
    return _DEFAULT_SAVE_DIR


# ---------------------------------------------------------------------------
# MagicItemEngine (de)serialisation — persists the registry keys of all
# currently worn wondrous items / rings.
# ---------------------------------------------------------------------------

def _registry_key_for(item: WondrousItem) -> Optional[str]:
    """Return the registry key for *item*, or None if unknown."""
    for key, reg_item in WONDROUS_ITEM_REGISTRY.items():
        if reg_item is item or reg_item.name == item.name:
            return key
    for key, reg_item in RING_REGISTRY.items():
        if reg_item is item or reg_item.name == item.name:
            return key
    return None


def _serialize_magic_item_engine(
    engine: Optional[MagicItemEngine],
) -> Optional[Dict[str, Any]]:
    if engine is None:
        return None
    keys: List[str] = []
    for item in engine.items:
        key = _registry_key_for(item)
        if key is not None:
            keys.append(key)
    return {"item_keys": keys}


def _deserialize_magic_item_engine(
    data: Optional[Dict[str, Any]],
) -> Optional[MagicItemEngine]:
    if not data:
        return None
    engine = MagicItemEngine()
    for key in data.get("item_keys", []):
        if key in WONDROUS_ITEM_REGISTRY:
            engine.add_item(WONDROUS_ITEM_REGISTRY[key])
        elif key in RING_REGISTRY:
            engine.add_item(RING_REGISTRY[key])
    return engine


# ---------------------------------------------------------------------------
# Conditions
# ---------------------------------------------------------------------------

def _serialize_conditions(
    manager: Optional[ConditionManager],
    character: Character35e,
) -> List[Dict[str, Any]]:
    if manager is None:
        return []
    out: List[Dict[str, Any]] = []
    for cond in manager.get_conditions(character):
        out.append({
            "name": cond.name,
            "duration": cond.duration,
            "stat_modifiers": dict(cond.stat_modifiers),
            "lose_dex_to_ac": cond.lose_dex_to_ac,
            "cannot_act": cond.cannot_act,
        })
    return out


def _deserialize_conditions(records: Iterable[Dict[str, Any]]) -> List[Condition]:
    return [
        Condition(
            name=rec["name"],
            duration=int(rec.get("duration", -1)),
            stat_modifiers=dict(rec.get("stat_modifiers", {})),
            lose_dex_to_ac=bool(rec.get("lose_dex_to_ac", False)),
            cannot_act=bool(rec.get("cannot_act", False)),
        )
        for rec in records
    ]


# ---------------------------------------------------------------------------
# XP manager
# ---------------------------------------------------------------------------

def _serialize_xp(xp_manager: Optional[XPManager]) -> Optional[Dict[str, int]]:
    if xp_manager is None:
        return None
    return {
        "current_xp": xp_manager.current_xp,
        "current_level": xp_manager.current_level,
    }


def _deserialize_xp(data: Optional[Dict[str, Any]]) -> Optional[XPManager]:
    if not data:
        return None
    return XPManager(
        current_xp=int(data.get("current_xp", 0)),
        current_level=int(data.get("current_level", 1)),
    )


# ---------------------------------------------------------------------------
# Character-level
# ---------------------------------------------------------------------------

def serialize_character(
    character: Character35e,
    *,
    conditions: Optional[ConditionManager] = None,
    xp_manager: Optional[XPManager] = None,
) -> Dict[str, Any]:
    """Serialise a character plus associated managers to a JSON-safe dict."""
    return {
        "character": character.to_dict(),
        "magic_item_engine": _serialize_magic_item_engine(character.magic_item_engine),
        "conditions": _serialize_conditions(conditions, character),
        "xp": _serialize_xp(xp_manager),
    }


def deserialize_character(
    record: Dict[str, Any],
    *,
    condition_manager: Optional[ConditionManager] = None,
) -> Character35e:
    """Reconstruct a character from a dict produced by :func:`serialize_character`.

    If *condition_manager* is supplied, stored conditions are re-applied to
    it so the character's condition state round-trips through save/load.
    """
    char_data = record["character"]
    character = Character35e.from_dict(char_data)
    character.magic_item_engine = _deserialize_magic_item_engine(
        record.get("magic_item_engine")
    )
    if condition_manager is not None:
        for cond in _deserialize_conditions(record.get("conditions", [])):
            condition_manager.apply_condition(character, cond)
    character.initialize_spellcasting()
    return character


def xp_manager_from_record(record: Dict[str, Any]) -> Optional[XPManager]:
    """Return the XPManager embedded in *record*, if any."""
    return _deserialize_xp(record.get("xp"))


# ---------------------------------------------------------------------------
# Party-level API
# ---------------------------------------------------------------------------

def _party_path(name: str, directory: Optional[Path] = None) -> Path:
    base = directory if directory is not None else save_directory()
    base.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in name)
    return base / f"{safe}.json"


def save_party(
    name: str,
    party: Iterable[Character35e],
    *,
    directory: Optional[Path] = None,
    conditions: Optional[ConditionManager] = None,
    xp_managers: Optional[Dict[str, XPManager]] = None,
    active_books: Optional[List[str]] = None,
) -> Path:
    """Write *party* to ``<directory or saves/>/<name>.json``.

    Args:
        name:         Party name (used as the file stem).
        party:        Iterable of :class:`Character35e` instances.
        directory:    Override for the destination directory (tests).
        conditions:   Optional :class:`ConditionManager` whose state will be
                      saved alongside each character.
        xp_managers:  Mapping of ``char_id → XPManager`` so each character's
                      XP is round-tripped.
        active_books: List of active supplemental book slugs (PH7).  Saved
                      under ``"active_books"`` and restored on load so the
                      engine can re-invoke ``load_expanded_rules()`` when
                      resuming a session.  Defaults to ``[]``.

    Returns:
        The absolute :class:`~pathlib.Path` that was written.
    """
    path = _party_path(name, directory)
    xp_managers = xp_managers or {}
    records = [
        serialize_character(
            c,
            conditions=conditions,
            xp_manager=xp_managers.get(c.char_id),
        )
        for c in party
    ]
    payload = {"name": name, "party": records, "active_books": active_books or []}
    path.write_text(json.dumps(payload, indent=2))
    return path


def load_party(
    name: str,
    *,
    directory: Optional[Path] = None,
    condition_manager: Optional[ConditionManager] = None,
) -> List[Character35e]:
    """Load a previously saved party.

    Raises:
        FileNotFoundError: If no save file exists for *name*.
    """
    path = _party_path(name, directory)
    if not path.exists():
        raise FileNotFoundError(f"No saved party named {name!r} at {path}")
    payload = json.loads(path.read_text())
    return [
        deserialize_character(rec, condition_manager=condition_manager)
        for rec in payload.get("party", [])
    ]


def load_active_books(
    name: str,
    *,
    directory: Optional[Path] = None,
) -> List[str]:
    """Return the ``active_books`` list from a saved party file.

    Returns an empty list when the save file predates PH7 or the key is absent.

    Args:
        name:      Party name (file stem).
        directory: Override for the save directory (tests).

    Raises:
        FileNotFoundError: If no save file exists for *name*.
    """
    path = _party_path(name, directory)
    if not path.exists():
        raise FileNotFoundError(f"No saved party named {name!r} at {path}")
    payload = json.loads(path.read_text())
    return payload.get("active_books", [])


def load_party_with_state(
    name: str,
    *,
    directory: Optional[Path] = None,
    condition_manager: Optional[ConditionManager] = None,
) -> Dict[str, Any]:
    """Load a party plus its raw record list (for XP / condition recovery).

    Returns a dict with keys ``party`` (list of characters), ``records``
    (list of per-character record dicts matching :func:`serialize_character`),
    and ``active_books`` (list of supplemental book slugs, defaults to ``[]``
    for saves that predate PH7).
    """
    path = _party_path(name, directory)
    if not path.exists():
        raise FileNotFoundError(f"No saved party named {name!r} at {path}")
    payload = json.loads(path.read_text())
    records = payload.get("party", [])
    characters = [
        deserialize_character(rec, condition_manager=condition_manager)
        for rec in records
    ]
    return {
        "party": characters,
        "records": records,
        "name": payload.get("name", name),
        "active_books": payload.get("active_books", []),
    }


def list_saved_parties(directory: Optional[Path] = None) -> List[str]:
    """Return the names of every ``*.json`` file in the save directory."""
    base = directory if directory is not None else save_directory()
    if not base.exists():
        return []
    return sorted(p.stem for p in base.glob("*.json"))
