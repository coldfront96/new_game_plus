"""
src/rules_engine/srd_loader.py
------------------------------
Lightweight JSON loader for the externalised SRD content (Task 7).

The loader walks ``data/srd_3.5/`` and surfaces the structured content
back to the rules engine as plain dicts.  It deliberately does **not**
replace the in-code registries (``RaceRegistry``, ``FEAT_CATALOG``,
``SPELL_REGISTRY``, …) — those remain the single source of truth for
the simulation so existing tests keep passing unchanged.  The JSON
files are the starting point for community edits and a future full
registry-swap.

Expected layout::

    data/srd_3.5/
        spells/
            level_0.json
            level_1.json
            ...
        feats/core.json
        races/core.json
        classes/core.json
        monsters/core.json
        magic_items/wondrous.json
        magic_items/rings.json
        magic_items/potions.json
        poisons_diseases.json
        gems_art.json
        encounter_tables.json

Every loader returns a :class:`list` of dicts (or ``{}`` for
file-not-found) so callers can `if data:` without handling exceptions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


# Resolve the data directory relative to the package root once.
_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parent.parent.parent
DEFAULT_DATA_DIR = _REPO_ROOT / "data" / "srd_3.5"


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _list_json_files(directory: Path) -> List[Path]:
    if not directory.exists():
        return []
    return sorted(directory.glob("*.json"))


def _load_dir_as_list(directory: Path) -> List[Dict[str, Any]]:
    """Merge every ``*.json`` array under *directory* into a single list."""
    out: List[Dict[str, Any]] = []
    for path in _list_json_files(directory):
        data = _read_json(path)
        if isinstance(data, list):
            out.extend(data)
        elif isinstance(data, dict):
            out.append(data)
    return out


# ---------------------------------------------------------------------------
# Public loaders
# ---------------------------------------------------------------------------

def load_spells(data_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Return every spell record merged from ``spells/*.json``."""
    base = (data_dir or DEFAULT_DATA_DIR) / "spells"
    return _load_dir_as_list(base)


def load_feats(data_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Return every feat record under ``feats/*.json``."""
    base = (data_dir or DEFAULT_DATA_DIR) / "feats"
    return _load_dir_as_list(base)


def load_races(data_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Return every race record under ``races/*.json``."""
    base = (data_dir or DEFAULT_DATA_DIR) / "races"
    return _load_dir_as_list(base)


def load_classes(data_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Return every class record under ``classes/*.json``."""
    base = (data_dir or DEFAULT_DATA_DIR) / "classes"
    return _load_dir_as_list(base)


def load_monsters(data_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Return every monster record under ``monsters/*.json``.

    The ``schema_v2.json`` meta-file is excluded automatically.
    """
    base = (data_dir or DEFAULT_DATA_DIR) / "monsters"
    out: List[Dict[str, Any]] = []
    for path in _list_json_files(base):
        if path.name == "schema_v2.json":
            continue
        data = _read_json(path)
        if isinstance(data, list):
            out.extend(data)
        elif isinstance(data, dict):
            out.append(data)
    return out


def load_magic_items(data_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Return every magic item record under ``magic_items/*.json``."""
    base = (data_dir or DEFAULT_DATA_DIR) / "magic_items"
    return _load_dir_as_list(base)


def load_poisons_diseases(
    data_dir: Optional[Path] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Return the combined poisons + diseases payload.

    Layout: ``poisons_diseases.json`` containing
    ``{"poisons": [...], "diseases": [...]}``.
    """
    base = data_dir or DEFAULT_DATA_DIR
    data = _read_json(base / "poisons_diseases.json")
    if not isinstance(data, dict):
        return {"poisons": [], "diseases": []}
    return {
        "poisons": data.get("poisons", []),
        "diseases": data.get("diseases", []),
    }


def load_gems_art(
    data_dir: Optional[Path] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Return gem and art-object tables."""
    base = data_dir or DEFAULT_DATA_DIR
    data = _read_json(base / "gems_art.json")
    if not isinstance(data, dict):
        return {"gems": [], "art_objects": []}
    return {
        "gems": data.get("gems", []),
        "art_objects": data.get("art_objects", []),
    }


def load_encounter_tables(
    data_dir: Optional[Path] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Return terrain → list of encounter entries."""
    base = data_dir or DEFAULT_DATA_DIR
    data = _read_json(base / "encounter_tables.json")
    if not isinstance(data, dict):
        return {}
    return data


def load_expanded_rules(active_books: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """Load supplemental content from ``data/expanded/`` for the requested books.

    Args:
        active_books: List of book slug strings (e.g. ``["draconomicon"]``).
            Only directories whose name appears in this list are loaded.

    Returns:
        A dict keyed by book slug, each value being a list of content dicts
        loaded from all ``*.json`` files inside the matching sub-directory.
        Returns ``{}`` if ``data/expanded/`` does not exist.
    """
    expanded_root = _REPO_ROOT / "data" / "expanded"
    expanded: Dict[str, List[Dict[str, Any]]] = {}
    try:
        for directory in expanded_root.iterdir():
            if not directory.is_dir():
                continue
            if directory.name not in active_books:
                continue
            book_entries: List[Dict[str, Any]] = []
            for json_path in directory.glob("*.json"):
                data = json.loads(json_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    book_entries.extend(data)
                elif isinstance(data, dict):
                    book_entries.append(data)
            expanded[directory.name] = book_entries
    except FileNotFoundError:
        return {}
    return expanded


def load_everything(data_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Return a single dict holding every SRD data category."""
    return {
        "spells": load_spells(data_dir),
        "feats": load_feats(data_dir),
        "races": load_races(data_dir),
        "classes": load_classes(data_dir),
        "monsters": load_monsters(data_dir),
        "magic_items": load_magic_items(data_dir),
        "poisons_diseases": load_poisons_diseases(data_dir),
        "gems_art": load_gems_art(data_dir),
        "encounter_tables": load_encounter_tables(data_dir),
    }
