"""
scripts/dump_srd.py
-------------------
One-off tool that walks the in-code registries in ``src/rules_engine/``
and writes their contents into ``data/srd_3.5/`` as JSON.

Run with ``python scripts/dump_srd.py`` (from the repo root).

The resulting files are consumed by :mod:`src.rules_engine.srd_loader`.
Because the in-code registries remain the single source of truth for
the simulation, this dumper is idempotent: re-running it simply
overwrites the JSON payload.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.rules_engine.character_35e import _BAB_PROGRESSION, _GOOD_SAVES, _HIT_DIE
from src.rules_engine.encounter_extended import ENCOUNTER_TABLES
from src.rules_engine.feat_engine import FEAT_CATALOG
from src.rules_engine.hazards import DISEASE_REGISTRY, POISON_REGISTRY
from src.rules_engine.magic import create_default_registry
from src.rules_engine.magic_items import RING_REGISTRY, WONDROUS_ITEM_REGISTRY
from src.rules_engine.race import RaceRegistry
from src.rules_engine.treasure import ART_OBJECT_TABLE, GEM_TABLE


DATA = Path(__file__).resolve().parent.parent / "data" / "srd_3.5"


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=False)
    print(f"  wrote {path.relative_to(DATA.parent.parent)}  "
          f"({len(json.dumps(payload))} bytes)")


# ---------------------------------------------------------------------------
# Dumpers
# ---------------------------------------------------------------------------

def dump_spells() -> None:
    registry = create_default_registry()
    all_spells = []
    for level in range(10):
        all_spells.extend(registry.get_by_level(level))
    by_level: dict[int, list[dict]] = {i: [] for i in range(10)}
    for spell in sorted(all_spells, key=lambda s: (s.level, s.name)):
        by_level[spell.level].append({
            "name": spell.name,
            "level": spell.level,
            "school": spell.school.value,
            "components": [c.value for c in spell.components],
            "range": spell.range,
            "duration": spell.duration,
            "subschool": spell.subschool,
            "descriptor": list(spell.descriptor),
            "description": spell.description,
        })
    for level, entries in by_level.items():
        if not entries:
            continue
        _write(DATA / "spells" / f"level_{level}.json", entries)


def dump_feats() -> None:
    entries = [
        {
            "name": feat.name,
            "description": feat.description,
            "prerequisites": feat.prerequisites,
            "bonus_type": feat.bonus_type.name,
        }
        for feat in sorted(FEAT_CATALOG.values(), key=lambda f: f.name)
    ]
    _write(DATA / "feats" / "core.json", entries)


def dump_races() -> None:
    entries = []
    for name in RaceRegistry.all_names():
        race = RaceRegistry.get(name)
        entries.append({
            "name": race.name,
            "stat_modifiers": dict(race.stat_modifiers),
            "special_abilities": list(race.special_abilities),
            "base_speed": race.base_speed,
            "size": race.size,
        })
    _write(DATA / "races" / "core.json", entries)


def dump_classes() -> None:
    """Emit the class progression tables (HD, BAB, good saves)."""
    entries = []
    for cls_name in sorted(_HIT_DIE.keys()):
        entries.append({
            "name": cls_name,
            "hit_die": _HIT_DIE[cls_name],
            "bab_progression": _BAB_PROGRESSION.get(cls_name, "three_quarter"),
            "good_saves": list(_GOOD_SAVES.get(cls_name, [])),
        })
    _write(DATA / "classes" / "core.json", entries)


def dump_magic_items() -> None:
    def _serialize_wondrous(item) -> dict:
        return {
            "name": item.name,
            "category": item.category.value,
            "slot": item.slot,
            "caster_level": item.caster_level,
            "price_gp": item.price_gp,
            "weight_lb": item.weight_lb,
            "bonuses": [
                {
                    "bonus_type": b.bonus_type.value,
                    "stat": b.stat,
                    "value": b.value,
                }
                for b in item.bonuses
            ],
            "aura": item.aura,
            "description": item.description,
        }

    wondrous_entries = [
        _serialize_wondrous(v) for _, v in sorted(WONDROUS_ITEM_REGISTRY.items())
    ]
    ring_entries = [
        _serialize_wondrous(v) for _, v in sorted(RING_REGISTRY.items())
    ]
    _write(DATA / "magic_items" / "wondrous.json", wondrous_entries)
    _write(DATA / "magic_items" / "rings.json", ring_entries)


def dump_monsters() -> None:
    """Emit the monster entries referenced by the encounter tables.

    Since there's no full bestiary registry yet, we dump the unique
    (name, cr) pairs from the encounter tables as a placeholder.
    """
    seen: dict[str, float] = {}
    for table in ENCOUNTER_TABLES.values():
        for entry in table:
            if entry.monster_name not in seen:
                seen[entry.monster_name] = entry.cr
    entries = [
        {"name": name, "cr": cr}
        for name, cr in sorted(seen.items())
    ]
    _write(DATA / "monsters" / "core.json", entries)


def dump_poisons_diseases() -> None:
    poisons = []
    for name, p in sorted(POISON_REGISTRY.items()):
        poisons.append({
            "name": p.name,
            "dc": p.dc,
            "initial_effect": p.initial_effect,
            "secondary_effect": p.secondary_effect,
            "initial_ability_dmg": dict(p.initial_ability_dmg),
            "secondary_ability_dmg": dict(p.secondary_ability_dmg),
            "secondary_delay_minutes": p.secondary_delay_minutes,
            "delivery": p.delivery,
            "price_gp": p.price_gp,
        })
    diseases = []
    for name, d in sorted(DISEASE_REGISTRY.items()):
        diseases.append({
            "name": d.name,
            "dc": d.dc,
            "incubation_days": d.incubation_days,
            "effect": d.effect,
            "ability_dmg": dict(d.ability_dmg),
            "disease_type": d.disease_type.name,
        })
    _write(
        DATA / "poisons_diseases.json",
        {"poisons": poisons, "diseases": diseases},
    )


def dump_gems_art() -> None:
    gems = [
        {
            "name": g.name,
            "grade": g.grade.value,
            "base_value_gp": g.base_value_gp,
            "value_range_gp": list(g.value_range_gp),
        }
        for g in GEM_TABLE
    ]
    art = [
        {
            "name": a.name,
            "category": a.category.value,
            "value_gp": a.value_gp,
        }
        for a in ART_OBJECT_TABLE
    ]
    _write(
        DATA / "gems_art.json",
        {"gems": gems, "art_objects": art},
    )


def dump_encounter_tables() -> None:
    payload = {}
    for terrain, entries in ENCOUNTER_TABLES.items():
        payload[terrain] = [
            {
                "d100_low": e.d100_low,
                "d100_high": e.d100_high,
                "monster_name": e.monster_name,
                "number_appearing": e.number_appearing,
                "cr": e.cr,
            }
            for e in entries
        ]
    _write(DATA / "encounter_tables.json", payload)


def main() -> None:
    print(f"Writing SRD JSON to {DATA}")
    dump_spells()
    dump_feats()
    dump_races()
    dump_classes()
    dump_magic_items()
    dump_monsters()
    dump_poisons_diseases()
    dump_gems_art()
    dump_encounter_tables()
    print("Done.")


if __name__ == "__main__":
    main()
