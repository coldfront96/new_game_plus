"""EM-003 — Lair Metadata Integration (Lair Carver subsystem)."""
from __future__ import annotations

import enum
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# EM-003 · LairType and LairRecord
# ---------------------------------------------------------------------------

class LairType(enum.Enum):
    """Classification of monster lair architecture."""
    Burrow   = "Burrow"
    Cave     = "Cave"
    Hive     = "Hive"
    Fortress = "Fortress"


@dataclass(slots=True)
class LairRecord:
    """Describes a monster lair that can be carved into a terrain chunk.

    Attributes:
        lair_id:      Unique identifier for this lair instance.
        monster_name: Name of the primary occupant (e.g. "Dragon").
        lair_type:    Architectural category of the lair.
        chunk_id:     The world chunk this lair occupies.
        width:        X-extent of the carved cavity (blocks).
        depth:        Z-extent of the carved cavity (blocks).
        height:       Y-extent of the carved cavity (blocks).
    """
    lair_id:      str
    monster_name: str
    lair_type:    LairType
    chunk_id:     str
    width:        int
    depth:        int
    height:       int
