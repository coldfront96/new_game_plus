# D&D 3.5e SRD Data

This directory contains structured data files parsed from the
[D&D 3.5e System Reference Document](https://www.d20srd.org/).

## Planned Data Files

| File | Contents |
|---|---|
| `ability_scores.json` | The six core ability scores, modifiers table, and generation rules |
| `races.json` | Playable races — ability adjustments, size, speed, racial traits |
| `classes.json` | Base classes — hit dice, BAB progression, saves, class features |
| `skills.json` | Skill list — key ability, trained-only flag, armour check penalty |
| `feats.json` | Feat definitions — prerequisites, benefits, special rules |
| `spells.json` | Spell compendium — school, level lists, components, range, duration |
| `equipment.json` | Weapons, armour, and adventuring gear — cost, weight, stats |
| `monsters.json` | Monster stat blocks — CR, type, HD, abilities, special attacks |

All files use a flat JSON array of objects so the rules engine can
index them at startup with minimal parsing overhead.
