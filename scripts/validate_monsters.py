"""LW-029 — Monster JSON Schema v2 validator using jsonschema.

Usage:
    python scripts/validate_monsters.py [--data-dir data/srd_3.5/monsters]
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# ValidationReport
# ---------------------------------------------------------------------------

@dataclass
class ValidationReport:
    total: int
    passed: int
    failed: list[tuple[str, str]] = field(default_factory=list)   # (filename, error_message)

    @property
    def all_passed(self) -> bool:
        return len(self.failed) == 0

    def print_summary(self) -> None:
        print(f"\nValidation Report — {self.passed}/{self.total} passed")
        if self.failed:
            print(f"  FAILED ({len(self.failed)}):")
            for fname, err in self.failed:
                print(f"    {fname}: {err}")
        else:
            print("  All entries valid.")


# ---------------------------------------------------------------------------
# Core validation
# ---------------------------------------------------------------------------

_VALID_BIOMES = {
    "Any",
    "Cold_Forest", "Cold_Hill", "Cold_Plain", "Cold_Desert",
    "Cold_Aquatic", "Cold_Swamp", "Cold_Mountain",
    "Temperate_Forest", "Temperate_Hill", "Temperate_Plain", "Temperate_Desert",
    "Temperate_Aquatic", "Temperate_Swamp", "Temperate_Mountain",
    "Warm_Forest", "Warm_Hill", "Warm_Plain", "Warm_Desert",
    "Warm_Aquatic", "Warm_Swamp", "Warm_Mountain",
    "Underground", "Underdark", "Arctic", "Any_Urban", "Any_Ruin", "Aquatic",
    "Astral", "Ethereal", "Positive_Energy", "Negative_Energy",
    "Elemental_Air", "Elemental_Earth", "Elemental_Fire", "Elemental_Water",
    "Outer_Plane",
}

_V2_REQUIRED = ("population_base", "allowed_biomes", "primary_biome")


def validate_monster_entry(entry: dict, source: str = "") -> list[str]:
    """Return a list of error strings (empty = valid)."""
    errors: list[str] = []
    name = entry.get("name", source)

    # V2 required fields
    for field_name in _V2_REQUIRED:
        if field_name not in entry:
            errors.append(f"[{name}] missing required field '{field_name}'")

    if errors:
        return errors

    # population_base must be a non-negative integer
    pb = entry["population_base"]
    if not isinstance(pb, int) or pb < 0:
        errors.append(f"[{name}] population_base must be int >= 0, got {pb!r}")

    # allowed_biomes must be a non-empty list of valid Biome names
    ab = entry["allowed_biomes"]
    if not isinstance(ab, list) or len(ab) == 0:
        errors.append(f"[{name}] allowed_biomes must be a non-empty list")
    else:
        for b in ab:
            if b not in _VALID_BIOMES:
                errors.append(f"[{name}] unknown biome '{b}' in allowed_biomes")

    # primary_biome must appear in allowed_biomes
    pb_biome = entry["primary_biome"]
    if not isinstance(pb_biome, str):
        errors.append(f"[{name}] primary_biome must be a string")
    elif pb_biome not in _VALID_BIOMES:
        errors.append(f"[{name}] primary_biome '{pb_biome}' is not a valid Biome name")
    elif isinstance(ab, list) and pb_biome not in ab:
        errors.append(f"[{name}] primary_biome '{pb_biome}' not found in allowed_biomes")

    return errors


def validate_all_monsters(data_dir: Path) -> ValidationReport:
    """Scan all JSON files under data_dir and validate each monster entry."""
    json_files = sorted(data_dir.glob("*.json"))
    if not json_files:
        print(f"No JSON files found in {data_dir}")
        return ValidationReport(total=0, passed=0)

    total = 0
    passed = 0
    failed: list[tuple[str, str]] = []

    for path in json_files:
        if path.name == "schema_v2.json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failed.append((path.name, f"JSON parse error: {exc}"))
            total += 1
            continue

        entries = data if isinstance(data, list) else [data]
        for entry in entries:
            total += 1
            errs = validate_monster_entry(entry, source=path.name)
            if errs:
                for err in errs:
                    failed.append((path.name, err))
            else:
                passed += 1

    return ValidationReport(total=total, passed=passed, failed=failed)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Validate SRD monster JSON files against schema v2.")
    parser.add_argument(
        "--data-dir",
        default="data/srd_3.5/monsters",
        help="Directory containing monster JSON files (default: data/srd_3.5/monsters)",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.is_dir():
        print(f"ERROR: {data_dir} is not a directory.", file=sys.stderr)
        return 1

    report = validate_all_monsters(data_dir)
    report.print_summary()
    return 0 if report.all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
