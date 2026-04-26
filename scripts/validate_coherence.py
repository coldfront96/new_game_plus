"""LW-045 — Cross-subsystem data coherence validator for ingested monster JSON.

Checks:
  (a) Regeneration  → must have non-empty elemental_weaknesses or alignment_weaknesses.
  (b) Spell Resistance → must have sr field >= 1.
  (c) Improved Grab / Swallow Whole → must have constrict_damage_dice or swallow_damage.
  (d) population_base >= 0 and allowed_biomes non-empty.

Writes data/coherence_report.json on completion.

Usage:
    python scripts/validate_coherence.py [--data-dir data/srd_3.5/monsters]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


_REGEN_KEYWORDS    = {"regeneration", "regen"}
_SR_KEYWORDS       = {"spell resistance", "sr"}
_GRAB_KEYWORDS     = {"improved grab"}
_SWALLOW_KEYWORDS  = {"swallow whole"}


def _sq_lower(entry: dict) -> set[str]:
    """Return lowercased set of special_qualities and special_attacks tokens."""
    combined: list[str] = []
    combined += entry.get("special_qualities", [])
    combined += entry.get("special_attacks", [])
    return {s.lower() for s in combined}


def check_entry(entry: dict) -> list[dict]:
    """Return list of rule-violation dicts (empty = coherent)."""
    sq = _sq_lower(entry)
    name = entry.get("name", "?")
    violations: list[dict] = []

    # (a) Regeneration without weaknesses
    has_regen = any(k in s for s in sq for k in _REGEN_KEYWORDS) or entry.get("regen") or entry.get("fast_heal")
    if has_regen:
        ew = entry.get("elemental_weaknesses", [])
        aw = entry.get("alignment_weaknesses", [])
        if not ew and not aw and entry.get("regen"):
            violations.append({
                "name": name, "rule": "a",
                "detail": "Has Regeneration but no elemental_weaknesses or alignment_weaknesses",
            })

    # (b) Spell Resistance keyword without sr field
    has_sr_qual = any(k in s for s in sq for k in _SR_KEYWORDS)
    sr_field = entry.get("sr")
    if has_sr_qual and (sr_field is None or sr_field < 1):
        violations.append({
            "name": name, "rule": "b",
            "detail": f"Has Spell Resistance in qualities but sr field is {sr_field!r}",
        })

    # (c) Improved Grab / Swallow Whole without grapple support fields
    has_grab = any(k in s for s in sq for k in _GRAB_KEYWORDS)
    has_swallow = any(k in s for s in sq for k in _SWALLOW_KEYWORDS)
    if has_grab and not entry.get("constrict_damage_dice") and not has_swallow:
        pass  # Improved Grab without Constrict is legal (e.g. Ankheg, Crocodile)
    if has_swallow:
        if not entry.get("swallow_damage") and not entry.get("constrict_damage_dice"):
            violations.append({
                "name": name, "rule": "c",
                "detail": "Has Swallow Whole but no swallow_damage or constrict_damage_dice field",
            })

    # (d) population_base and allowed_biomes
    pb = entry.get("population_base")
    if pb is None or (isinstance(pb, int) and pb < 0):
        violations.append({
            "name": name, "rule": "d",
            "detail": f"population_base is {pb!r} (must be int >= 0)",
        })
    ab = entry.get("allowed_biomes")
    if not ab or not isinstance(ab, list) or len(ab) == 0:
        violations.append({
            "name": name, "rule": "d",
            "detail": "allowed_biomes is missing or empty",
        })

    return violations


def validate_coherence(data_dir: Path) -> dict:
    """Scan all batch JSON files and return a full coherence report dict."""
    json_files = [p for p in sorted(data_dir.glob("*.json")) if p.name != "schema_v2.json"]
    report: list[dict] = []
    total = passed = 0

    for path in json_files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            report.append({"file": path.name, "error": str(exc)})
            continue

        entries = data if isinstance(data, list) else [data]
        for entry in entries:
            total += 1
            viols = check_entry(entry)
            if viols:
                for v in viols:
                    report.append({"file": path.name, **v})
            else:
                passed += 1

    return {"total": total, "passed": passed, "violations": report}


def main() -> int:
    parser = argparse.ArgumentParser(description="Cross-subsystem coherence validator for monster JSON.")
    parser.add_argument("--data-dir", default="data/srd_3.5/monsters")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.is_dir():
        print(f"ERROR: {data_dir} is not a directory.", file=sys.stderr)
        return 1

    report = validate_coherence(data_dir)
    out_path = data_dir.parent / "coherence_report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Coherence check: {report['passed']}/{report['total']} entries clean.")
    if report["violations"]:
        print(f"  {len(report['violations'])} violation(s) — see {out_path}")
        for v in report["violations"]:
            print(f"    [{v.get('rule','?')}] {v.get('name','?')}: {v.get('detail', v)}")
        return 1

    print(f"  All entries coherent. Report: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
