"""
src/game/player_persistence.py
--------------------------------
Player character persistence for the Ashen Crossroads Character Forge.

Serializes a freshly-created D&D 3.5e character to ``data/player.json``
so the launcher and subsequent game systems can read it back without
requiring the full party-based :mod:`src.game.persistence` infrastructure.

Usage::

    from src.game.player_persistence import save_new_player

    path = save_new_player(character_dict)
    print(f"Character saved to {path}")
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent.parent
_PLAYER_JSON = _REPO_ROOT / "data" / "player.json"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def save_new_player(data: Dict[str, Any]) -> Path:
    """Serialize *data* to ``data/player.json`` and return the file path.

    The ``data`` dict is produced by :meth:`CharacterForgeApp._build_character_dict`
    and follows 3.5e SRD conventions:

    * Six named ability scores (Strength … Charisma) with racial modifiers applied.
    * Derived values: ``hit_points``, ``armor_class``, ``initiative``,
      ``base_attack_bonus``, ``saving_throws``.
    * A ``physical_description`` sub-object structured as "Deep Lore" context
      for the NPC dialogue AI.

    Args:
        data: Fully-constructed character dictionary.

    Returns:
        Absolute :class:`~pathlib.Path` to the saved JSON file.

    Raises:
        OSError: If the file cannot be written (permissions, disk full, etc.).
    """
    _PLAYER_JSON.parent.mkdir(parents=True, exist_ok=True)
    with _PLAYER_JSON.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    return _PLAYER_JSON


def load_player() -> Dict[str, Any]:
    """Load the saved player character from ``data/player.json``.

    Returns:
        The deserialized character dictionary.

    Raises:
        FileNotFoundError: If no player has been created yet.
        json.JSONDecodeError: If the file is corrupt.
    """
    if not _PLAYER_JSON.exists():
        raise FileNotFoundError(
            f"No player file found at {_PLAYER_JSON}. "
            "Run the Character Forge first."
        )
    with _PLAYER_JSON.open(encoding="utf-8") as fh:
        return json.load(fh)


def player_exists() -> bool:
    """Return ``True`` if a saved player file exists."""
    return _PLAYER_JSON.exists()
