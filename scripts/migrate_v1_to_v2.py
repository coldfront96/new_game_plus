"""LW-037 — Migrate SRD monster JSON files from schema v1 (name+cr) to schema v2.

Usage:
    python scripts/migrate_v1_to_v2.py [--data-dir data/srd_3.5/monsters] [--dry-run]

V2 safe defaults applied to any entry missing a v2 field:
    population_base: 100
    allowed_biomes:  ["Any"]
    primary_biome:   "Any"
    ecology_notes:   null
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.validate_monsters import validate_monster_entry  # noqa: E402

_V2_DEFAULTS: dict = {
    "population_base": 100,
    "allowed_biomes":  ["Any"],
    "primary_biome":   "Any",
    "ecology_notes":   None,
}


def migrate_entry(entry: dict) -> tuple[dict, list[str]]:
    """Add missing v2 fields with safe defaults. Returns (updated_entry, added_fields)."""
    added: list[str] = []
    for key, default in _V2_DEFAULTS.items():
        if key not in entry:
            entry[key] = default
            added.append(key)
    return entry, added


def migrate_file(path: Path, dry_run: bool = False) -> dict:
    """Migrate a single JSON file; return a report dict."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    entries = raw if isinstance(raw, list) else [raw]
    is_list = isinstance(raw, list)

    modified_entries: list[dict] = []
    file_report: list[dict] = []

    for entry in entries:
        original_keys = list(entry.keys())
        updated, added = migrate_entry(dict(entry))
        errs = validate_monster_entry(updated, source=path.name)
        file_report.append({
            "name": updated.get("name", "?"),
            "added_fields": added,
            "validation_errors": errs,
        })
        modified_entries.append(updated)

    if not dry_run:
        out = modified_entries if is_list else modified_entries[0]
        path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    return {"file": path.name, "entries": file_report}


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate SRD monster JSON files to schema v2.")
    parser.add_argument("--data-dir", default="data/srd_3.5/monsters")
    parser.add_argument("--dry-run", action="store_true", help="Print diffs without writing")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.is_dir():
        print(f"ERROR: {data_dir} is not a directory.", file=sys.stderr)
        return 1

    json_files = [p for p in sorted(data_dir.glob("*.json")) if p.name != "schema_v2.json"]
    if not json_files:
        print("No JSON files to migrate.")
        return 0

    all_reports: list[dict] = []
    validation_failures = 0

    for path in json_files:
        report = migrate_file(path, dry_run=args.dry_run)
        all_reports.append(report)
        for entry in report["entries"]:
            if entry["validation_errors"]:
                validation_failures += len(entry["validation_errors"])
                for err in entry["validation_errors"]:
                    print(f"  VALIDATION ERROR: {err}", file=sys.stderr)
            elif entry["added_fields"]:
                prefix = "[dry-run] " if args.dry_run else ""
                print(f"  {prefix}Migrated '{entry['name']}': added {entry['added_fields']}")

    # Write migration report
    report_path = data_dir.parent / "migration_v2_report.json"
    if not args.dry_run:
        report_path.write_text(json.dumps(all_reports, indent=2), encoding="utf-8")
        print(f"\nMigration report written to {report_path}")

    if validation_failures:
        print(f"\nERROR: {validation_failures} validation failure(s) after migration.", file=sys.stderr)
        return 1

    print(f"\nMigration {'(dry-run) ' if args.dry_run else ''}complete — {len(json_files)} file(s) processed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
