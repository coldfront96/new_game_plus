# PHASE_7_DATA_GENERATION_TASKS.md — Phase 7: Data Injection (JSON Generation)

## Status Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Complete / Shipped |
| 🔲 | Pending implementation |
| ❌ | Blocked — dependency not yet met |

---

## Infrastructure Status

| Component | Module | Status |
|-----------|--------|--------|
| Expanded Data Root | `data/expanded/` | ✅ Shipped |
| Draconomicon Sub-Directory | `data/expanded/draconomicon/` | ✅ Shipped |
| Monster Manual II Sub-Directory | `data/expanded/monster_manual_2/` | ✅ Shipped |
| Magic Item Compendium Sub-Directory | `data/expanded/magic_item_compendium/` | ✅ Shipped |
| Expanded Schema | `data/expanded/schema_expanded_v1.json` | ✅ Shipped |
| Supplemental Rule Loader | `src/rules_engine/srd_loader.py` — `load_expanded_rules()` | ✅ Shipped |
| Expanded Monster Build Path | `src/rules_engine/srd_loader.py` — `build_monsters_from_srd(expanded=)` | ✅ Shipped |
| Expanded Magic Item Merge | `src/rules_engine/magic_item_engine.py` — `merge_expanded_wondrous()` | ✅ Shipped |
| Multiverse Book Toggles (UI) | `src/overseer_ui/setup_wizard.py` — `CampaignWizardState(active_books)` | ✅ Shipped |
| Active Books Persistence | `src/game/persistence.py` — `save_party(active_books=)` | ✅ Shipped |
| LLM Batch Runner | `scripts/` | 🔲 Pending |
| Batch Merge at Runtime | `src/rules_engine/srd_loader.py` — `load_expanded_rules()` auto-merge | ✅ Shipped |

---

## 1. Scope

Phase 7 Data Injection deploys local LLM batch-generation to physically populate the supplemental
3.5e data directories with JSON content files. All output must comply with
`data/expanded/schema_expanded_v1.json`. To prevent VRAM overflow, each generation run targets a
single small batch file. The `load_expanded_rules()` function in `srd_loader.py` merges all batch
files present in a directory at runtime — no manual merge step is required.

All tasks in this phase write files into the already-shipped directory tree. No source code
modifications are required.

| Tier | Subsystem | Target Directory |
|------|-----------|-----------------|
| 0 | Draconomicon | `data/expanded/draconomicon/` |
| 1 | Monster Manual II | `data/expanded/monster_manual_2/` |
| 2 | Magic Item Compendium | `data/expanded/magic_item_compendium/` |

---

## 2. Dependency Map

```
Tier 0  ─────────────────────────────────────────────────────────────────────
         [PH7D-001]  batch_true_dragons_epic.json
         [PH7D-002]  batch_lesser_dragons.json
         [PH7D-003]  batch_dragon_kin.json

Tier 1  ─────────────────────────────────────────────────────────────────────
         [PH7D-004]  batch_aberrations.json
         [PH7D-005]  batch_constructs.json
         [PH7D-006]  batch_fey_and_giants.json
         [PH7D-007]  batch_undead.json
         [PH7D-008]  batch_beasts_and_vermin.json

Tier 2  ─────────────────────────────────────────────────────────────────────
         [PH7D-009]  batch_wondrous_a_f.json
         [PH7D-010]  batch_wondrous_g_p.json
         [PH7D-011]  batch_wondrous_q_z.json
         [PH7D-012]  batch_weapons_melee.json
         [PH7D-013]  batch_weapons_ranged.json
         [PH7D-014]  batch_armor_and_shields.json
```

All tasks are independent of each other within their tier. Tasks across tiers have no hard
code dependency — any file can be generated in any order. Tier groupings reflect logical
source-book boundaries only.

---

## 3. Task Tiers

### Tier 0 — The Draconomicon (`data/expanded/draconomicon/`)

| Task | Title | Target File | Contents | Status |
|------|-------|-------------|----------|--------|
| PH7D-001 | Generate batch_true_dragons_epic.json | `data/expanded/draconomicon/batch_true_dragons_epic.json` | Advanced age categories (Wyrm, Great Wyrm, Ancient) for Red, Blue, Green, Black, White true dragons. Each entry must include all required schema fields plus `"source_book": "Draconomicon"`. | 🔲 |
| PH7D-002 | Generate batch_lesser_dragons.json | `data/expanded/draconomicon/batch_lesser_dragons.json` | Drakes (Fire Drake, Rime Drake, Sand Drake), Wyverns (standard and advanced), Landwyrms (Forest, Desert, Mountain). Each entry must include `"source_book": "Draconomicon"`. | 🔲 |
| PH7D-003 | Generate batch_dragon_kin.json | `data/expanded/draconomicon/batch_dragon_kin.json` | Dracotaurs, Dragonkin (chromatic variants), Redspawn Arcaniss. Each entry must include `"source_book": "Draconomicon"`. | 🔲 |

---

#### PH7D-001 — batch_true_dragons_epic.json

**Target file:** `data/expanded/draconomicon/batch_true_dragons_epic.json`

**Contents:** Advanced age categories (Wyrm, Great Wyrm, Ancient) for the five chromatic true dragons — Red, Blue, Green, Black, White. Every entry must be a fully self-contained object with no fields left null that the schema marks as required.

**Schema compliance requirements:**
- All entries must validate against `data/expanded/schema_expanded_v1.json`.
- The `"source_book"` field must be set to `"Draconomicon"` on every entry.
- The `"is_expanded"` flag must be `true`.
- Age-category entries for the same species must use a `"name"` field that embeds both species and age category (e.g. `"Red Dragon (Great Wyrm)"`) to avoid collisions with the core SRD entries.

**Generation guidance:** Run the LLM batch-generation script targeting this file in isolation. Keep total token output within the VRAM budget by limiting the batch to a maximum of 15 entries (5 species × 3 age tiers). Validate the file with `python -m json.tool` before committing.

**Status:** 🔲 Pending

---

#### PH7D-002 — batch_lesser_dragons.json

**Target file:** `data/expanded/draconomicon/batch_lesser_dragons.json`

**Contents:** Drakes (Fire Drake, Rime Drake, Sand Drake), Wyverns (standard CR 5 and advanced CR 10 variant), and Landwyrms (Forest, Desert, Mountain).

**Schema compliance requirements:**
- All entries must validate against `data/expanded/schema_expanded_v1.json`.
- The `"source_book"` field must be set to `"Draconomicon"` on every entry.
- The `"is_expanded"` flag must be `true`.
- Lesser dragon entries must not duplicate any name already present in `data/srd_3.5/`.

**Generation guidance:** Target a maximum of 8 entries per batch run to stay within VRAM budget. Validate with `python -m json.tool` before committing.

**Status:** 🔲 Pending

---

#### PH7D-003 — batch_dragon_kin.json

**Target file:** `data/expanded/draconomicon/batch_dragon_kin.json`

**Contents:** Dracotaurs (standard), Dragonkin (chromatic-aligned variants: red-kin, blue-kin, green-kin), Redspawn Arcaniss.

**Schema compliance requirements:**
- All entries must validate against `data/expanded/schema_expanded_v1.json`.
- The `"source_book"` field must be set to `"Draconomicon"` on every entry.
- The `"is_expanded"` flag must be `true`.

**Generation guidance:** Target a maximum of 5 entries per batch run. Validate with `python -m json.tool` before committing.

**Status:** 🔲 Pending

---

### Tier 1 — Monster Manual II (`data/expanded/monster_manual_2/`)

| Task | Title | Target File | Contents | Status |
|------|-------|-------------|----------|--------|
| PH7D-004 | Generate batch_aberrations.json | `data/expanded/monster_manual_2/batch_aberrations.json` | Aboleth variants (Elder Aboleth, Aboleth Mage), Neogi (standard, Great Old Master), Destrachan. Each entry must include `"source_book": "Monster Manual II"`. | 🔲 |
| PH7D-005 | Generate batch_constructs.json | `data/expanded/monster_manual_2/batch_constructs.json` | Clockwork Horrors (Adamantine, Gold, Electrum, Silver, Bronze), advanced Golems (Bone Golem, Flesh Golem variant). Each entry must include `"source_book": "Monster Manual II"`. | 🔲 |
| PH7D-006 | Generate batch_fey_and_giants.json | `data/expanded/monster_manual_2/batch_fey_and_giants.json` | Sylphs, Frost Salamanders, Firbolgs (standard warrior and shaman). Each entry must include `"source_book": "Monster Manual II"`. | 🔲 |
| PH7D-007 | Generate batch_undead.json | `data/expanded/monster_manual_2/batch_undead.json` | Death Knights (generic template), Bone Nagas (standard), Spellstitched undead template examples (Spellstitched Zombie, Spellstitched Skeleton). Each entry must include `"source_book": "Monster Manual II"`. | 🔲 |
| PH7D-008 | Generate batch_beasts_and_vermin.json | `data/expanded/monster_manual_2/batch_beasts_and_vermin.json` | Dire animals (Dire Shark, Dire Eel), Megapede (standard). Each entry must include `"source_book": "Monster Manual II"`. | 🔲 |

---

#### PH7D-004 — batch_aberrations.json

**Target file:** `data/expanded/monster_manual_2/batch_aberrations.json`

**Contents:** Aboleth variants (Elder Aboleth, Aboleth Mage), Neogi (standard worker, Great Old Master), Destrachan.

**Schema compliance requirements:**
- All entries must validate against `data/expanded/schema_expanded_v1.json`.
- The `"source_book"` field must be `"Monster Manual II"` on every entry.
- The `"is_expanded"` flag must be `true`.
- Aberration entries must not duplicate any name already present in `data/srd_3.5/`.

**Generation guidance:** Target a maximum of 5 entries per batch run. Validate with `python -m json.tool` before committing.

**Status:** 🔲 Pending

---

#### PH7D-005 — batch_constructs.json

**Target file:** `data/expanded/monster_manual_2/batch_constructs.json`

**Contents:** Clockwork Horrors (Adamantine Horror CR 10, Gold Horror CR 8, Electrum Horror CR 6, Silver Horror CR 4, Bronze Horror CR 2), Bone Golem (CR 8), Flesh Golem variant (CR 7).

**Schema compliance requirements:**
- All entries must validate against `data/expanded/schema_expanded_v1.json`.
- The `"source_book"` field must be `"Monster Manual II"` on every entry.
- The `"is_expanded"` flag must be `true`.

**Generation guidance:** Target a maximum of 8 entries per batch run. Validate with `python -m json.tool` before committing.

**Status:** 🔲 Pending

---

#### PH7D-006 — batch_fey_and_giants.json

**Target file:** `data/expanded/monster_manual_2/batch_fey_and_giants.json`

**Contents:** Sylphs (standard), Frost Salamanders (standard CR 9), Firbolgs (Firbolg Warrior CR 6, Firbolg Shaman CR 8).

**Schema compliance requirements:**
- All entries must validate against `data/expanded/schema_expanded_v1.json`.
- The `"source_book"` field must be `"Monster Manual II"` on every entry.
- The `"is_expanded"` flag must be `true`.

**Generation guidance:** Target a maximum of 5 entries per batch run. Validate with `python -m json.tool` before committing.

**Status:** 🔲 Pending

---

#### PH7D-007 — batch_undead.json

**Target file:** `data/expanded/monster_manual_2/batch_undead.json`

**Contents:** Death Knight (generic template application, CR 17), Bone Naga (standard CR 8), Spellstitched Zombie (CR 3 template example), Spellstitched Skeleton (CR 2 template example).

**Schema compliance requirements:**
- All entries must validate against `data/expanded/schema_expanded_v1.json`.
- The `"source_book"` field must be `"Monster Manual II"` on every entry.
- The `"is_expanded"` flag must be `true`.
- Template-derived entries must embed the base creature name in a `"tags"` array entry (e.g. `["undead", "template", "spellstitched"]`).

**Generation guidance:** Target a maximum of 5 entries per batch run. Validate with `python -m json.tool` before committing.

**Status:** 🔲 Pending

---

#### PH7D-008 — batch_beasts_and_vermin.json

**Target file:** `data/expanded/monster_manual_2/batch_beasts_and_vermin.json`

**Contents:** Dire Shark (CR 9), Dire Eel (CR 5), Megapede (CR 4).

**Schema compliance requirements:**
- All entries must validate against `data/expanded/schema_expanded_v1.json`.
- The `"source_book"` field must be `"Monster Manual II"` on every entry.
- The `"is_expanded"` flag must be `true`.
- Dire animal entries must not duplicate the Dire Shark or Dire Eel if already present in `data/srd_3.5/` — check for name collisions before committing.

**Generation guidance:** Target a maximum of 3 entries per batch run. Validate with `python -m json.tool` before committing.

**Status:** 🔲 Pending

---

### Tier 2 — Magic Item Compendium (`data/expanded/magic_item_compendium/`)

| Task | Title | Target File | Contents | Status |
|------|-------|-------------|----------|--------|
| PH7D-009 | Generate batch_wondrous_a_f.json | `data/expanded/magic_item_compendium/batch_wondrous_a_f.json` | Wondrous items A–F: Amulets, Belts, Boots, Cloaks, Flasks. Each entry must include `"source_book": "Magic Item Compendium"`. | 🔲 |
| PH7D-010 | Generate batch_wondrous_g_p.json | `data/expanded/magic_item_compendium/batch_wondrous_g_p.json` | Wondrous items G–P: Gauntlets, Gloves, Helms, Mantles, Pearls. Each entry must include `"source_book": "Magic Item Compendium"`. | 🔲 |
| PH7D-011 | Generate batch_wondrous_q_z.json | `data/expanded/magic_item_compendium/batch_wondrous_q_z.json` | Wondrous items Q–Z: Rings, Robes, Scarabs, Vestments. Each entry must include `"source_book": "Magic Item Compendium"`. | 🔲 |
| PH7D-012 | Generate batch_weapons_melee.json | `data/expanded/magic_item_compendium/batch_weapons_melee.json` | Specific named melee weapons: swords, axes, maces. Each entry must include `"source_book": "Magic Item Compendium"`. | 🔲 |
| PH7D-013 | Generate batch_weapons_ranged.json | `data/expanded/magic_item_compendium/batch_weapons_ranged.json` | Specific named ranged weapons: bows, crossbows, throwing weapons. Each entry must include `"source_book": "Magic Item Compendium"`. | 🔲 |
| PH7D-014 | Generate batch_armor_and_shields.json | `data/expanded/magic_item_compendium/batch_armor_and_shields.json` | Specific named armor and shields: plate armors, leather armors, bucklers. Each entry must include `"source_book": "Magic Item Compendium"`. | 🔲 |

---

#### PH7D-009 — batch_wondrous_a_f.json

**Target file:** `data/expanded/magic_item_compendium/batch_wondrous_a_f.json`

**Contents:** Wondrous items with names beginning A–F: representative Amulets (e.g. Amulet of Mighty Fists +1 through +5), Belts (Belt of Battle, Belt of Magnificence), Boots (Boots of Temporal Acceleration, Boots of the Winterlands), Cloaks (Cloak of Charisma +6, Cloak of the Salamander), Flasks (Flask of Curses, Flask of Endless Water).

**Schema compliance requirements:**
- All entries must validate against `data/expanded/schema_expanded_v1.json`.
- The `"source_book"` field must be `"Magic Item Compendium"` on every entry.
- The `"is_expanded"` flag must be `true`.
- Each item must include `"slot"`, `"price_gp"`, `"caster_level"`, and `"aura_school"` fields so `merge_expanded_wondrous()` can construct a `WondrousItem` without falling back to defaults.
- Item names must not duplicate entries already present in `WONDROUS_ITEM_REGISTRY` (check `src/rules_engine/magic_item_engine.py` before committing).

**Generation guidance:** Target a maximum of 12 entries per batch run. Validate with `python -m json.tool` before committing.

**Status:** 🔲 Pending

---

#### PH7D-010 — batch_wondrous_g_p.json

**Target file:** `data/expanded/magic_item_compendium/batch_wondrous_g_p.json`

**Contents:** Wondrous items with names beginning G–P: Gauntlets (Gauntlets of Ogre Power, Gauntlets of the Talon), Gloves (Gloves of Dexterity +6, Gloves of the Balanced Hand), Helms (Helm of Brilliance, Helm of Telepathy), Mantles (Mantle of Spell Resistance, Mantle of the Fiery Spirit), Pearls (Pearl of Power I–IX).

**Schema compliance requirements:**
- All entries must validate against `data/expanded/schema_expanded_v1.json`.
- The `"source_book"` field must be `"Magic Item Compendium"` on every entry.
- The `"is_expanded"` flag must be `true`.
- Each item must include `"slot"`, `"price_gp"`, `"caster_level"`, and `"aura_school"` fields.
- Item names must not duplicate entries already present in `WONDROUS_ITEM_REGISTRY`.

**Generation guidance:** Target a maximum of 12 entries per batch run. Validate with `python -m json.tool` before committing.

**Status:** 🔲 Pending

---

#### PH7D-011 — batch_wondrous_q_z.json

**Target file:** `data/expanded/magic_item_compendium/batch_wondrous_q_z.json`

**Contents:** Wondrous items with names beginning Q–Z: Rings (Ring of Spell Storing, Ring of Evasion, Ring of Regeneration), Robes (Robe of the Archmagi, Robe of Eyes), Scarabs (Scarab of Protection, Scarab of Golembane), Vestments (Vestments of Faith, Vestments of the Avatar).

**Schema compliance requirements:**
- All entries must validate against `data/expanded/schema_expanded_v1.json`.
- The `"source_book"` field must be `"Magic Item Compendium"` on every entry.
- The `"is_expanded"` flag must be `true`.
- Each item must include `"slot"`, `"price_gp"`, `"caster_level"`, and `"aura_school"` fields.
- Item names must not duplicate entries already present in `WONDROUS_ITEM_REGISTRY`.

**Generation guidance:** Target a maximum of 12 entries per batch run. Validate with `python -m json.tool` before committing.

**Status:** 🔲 Pending

---

#### PH7D-012 — batch_weapons_melee.json

**Target file:** `data/expanded/magic_item_compendium/batch_weapons_melee.json`

**Contents:** Specific named melee weapons from the Magic Item Compendium: named swords (Blade of Orc Slaying, Sword of the Planes, Nine Lives Stealer), named axes (Dwarven Thrower as melee variant, Berserking Sword-Axe), named maces (Mace of Smiting, Mace of Terror).

**Schema compliance requirements:**
- All entries must validate against `data/expanded/schema_expanded_v1.json`.
- The `"source_book"` field must be `"Magic Item Compendium"` on every entry.
- The `"is_expanded"` flag must be `true`.
- Each entry must include `"item_type": "weapon"`, `"weapon_category": "melee"`, `"price_gp"`, `"caster_level"`, and `"aura_school"` fields.
- Item names must not duplicate entries already present in the core SRD weapon tables.

**Generation guidance:** Target a maximum of 8 entries per batch run. Validate with `python -m json.tool` before committing.

**Status:** 🔲 Pending

---

#### PH7D-013 — batch_weapons_ranged.json

**Target file:** `data/expanded/magic_item_compendium/batch_weapons_ranged.json`

**Contents:** Specific named ranged weapons from the Magic Item Compendium: named bows (Bow of Songs, Oathbow, Composite Longbow of the Eagle), named crossbows (Crossbow of Speed, Crossbow of Accuracy), named throwing weapons (Returning Dagger of Defending, Javelin of Lightning).

**Schema compliance requirements:**
- All entries must validate against `data/expanded/schema_expanded_v1.json`.
- The `"source_book"` field must be `"Magic Item Compendium"` on every entry.
- The `"is_expanded"` flag must be `true`.
- Each entry must include `"item_type": "weapon"`, `"weapon_category": "ranged"`, `"price_gp"`, `"caster_level"`, and `"aura_school"` fields.
- Item names must not duplicate entries already present in the core SRD weapon tables.

**Generation guidance:** Target a maximum of 8 entries per batch run. Validate with `python -m json.tool` before committing.

**Status:** 🔲 Pending

---

#### PH7D-014 — batch_armor_and_shields.json

**Target file:** `data/expanded/magic_item_compendium/batch_armor_and_shields.json`

**Contents:** Specific named armor and shields from the Magic Item Compendium: plate armors (Armor of Radiance, Demon Armor, Plate Armor of the Deep), leather armors (Leather Armor of Shadow, Dragonskin Armor), bucklers (Animated Buckler, Buckler of Blinding).

**Schema compliance requirements:**
- All entries must validate against `data/expanded/schema_expanded_v1.json`.
- The `"source_book"` field must be `"Magic Item Compendium"` on every entry.
- The `"is_expanded"` flag must be `true`.
- Each entry must include `"item_type": "armor"`, `"armor_category"` (one of `"plate"`, `"leather"`, or `"shield"`), `"price_gp"`, `"caster_level"`, and `"aura_school"` fields.
- Item names must not duplicate entries already present in the core SRD armor tables.

**Generation guidance:** Target a maximum of 8 entries per batch run. Validate with `python -m json.tool` before committing.

**Status:** 🔲 Pending

---

## 4. Common Generation Rules

The following rules apply to every batch file generated in this phase.

1. **Schema validation first.** Every generated JSON file must be validated against
   `data/expanded/schema_expanded_v1.json` before being committed. Use
   `python -m json.tool <file>` for basic syntax checking and the project's schema
   validator if available.

2. **source_book field mandatory.** Every entry must carry the exact canonical
   source book name as its `"source_book"` value:
   - Draconomicon tasks → `"Draconomicon"`
   - Monster Manual II tasks → `"Monster Manual II"`
   - Magic Item Compendium tasks → `"Magic Item Compendium"`

3. **No placeholders.** All numeric fields (`"cr"`, `"hp"`, `"price_gp"`,
   `"caster_level"`, etc.) must be populated with accurate values. Entries
   with `null`, `0`, or `"TBD"` in required fields will be rejected during
   review.

4. **VRAM budget enforcement.** Each batch file must stay within a self-contained
   entry count budget (documented per-task above). Do not merge multiple tasks
   into a single batch file — the file name must match exactly the name specified
   in the task.

5. **Name collision check.** Before committing any file, verify that none of the
   entry `"name"` values duplicate an existing name in `data/srd_3.5/` or in any
   previously committed expanded batch file. The `load_expanded_rules()` runtime
   merge does not deduplicate by name — duplicates will cause double-loading.

6. **is_expanded flag.** Every entry must set `"is_expanded": true` inside the
   `"expanded_metadata"` block to distinguish it from core SRD data at runtime.

> ---
> ### ⚠️ RULE #7 — THE CLEAN-ROOM TRANSLATION PROTOCOL (IP SAFETY) ⚠️
>
> **This rule is mandatory for any batch file targeting a commercial release.**
>
> Not all creatures in the source books are free to reproduce by name. Wizards of the
> Coast designates certain monsters and lore elements as **Product Identity** — these
> names and their associated descriptions, artwork, and story are protected and cannot
> appear in a commercially released product without a licence.
>
> **You CANNOT use the following (non-exhaustive examples):**
> - Monster names that are WotC Product Identity: *Beholder*, *Mind Flayer* (Illithid),
>   *Displacer Beast*, *Neogi*, *Redspawn Arcaniss*, *Githyanki*, *Githzerai*, etc.
> - Specific named spells, artefacts, or lore that appear exclusively in WotC supplements
>   (i.e. are NOT part of the open SRD).
> - Any flavour text, descriptions, or lore copied or closely paraphrased from a WotC
>   publication.
>
> **What you MUST do instead — the Translation Protocol:**
>
> 1. **Extract the pure math.** Pull only the raw 3.5e mechanical stats: CR, HD, HP,
>    AC, attack bonus, damage dice, saves, speed, special abilities (modelled as pure
>    numerical effects). This data is functional/mathematical and is not copyrightable.
>
> 2. **Discard all protected expression.** Do not carry over the creature's WotC name,
>    appearance description, habitat lore, society/culture text, or any flavour field
>    sourced from a WotC publication.
>
> 3. **Wrap in 100 % original expression.** Assign a completely new name and write
>    entirely original lore, description, and flavour text that fits the project's
>    pure High-Fantasy setting. The resulting entry must be legally distinct — a reader
>    familiar with the WotC source material should not be able to identify the original
>    by name or description alone.
>
> 4. **Tag the entry.** Add `"translated": true` and `"source_archetype": "<original
>    creature type>"` (e.g. `"aberration"`) inside the `"expanded_metadata"` block so
>    the runtime loader and future auditors know the entry passed through this protocol.
>    Do **not** record the original WotC name in any persisted field.
>
> **In practice:** If a task spec lists a creature that falls under WotC Product
> Identity (e.g. Neogi, Redspawn Arcaniss), do NOT generate an entry with that name.
> Instead, derive the mechanical stats, invent an original High-Fantasy name and lore,
> and generate the entry under the new identity. See `data/expanded/AUTHORING_GUIDELINES.md`
> for worked examples and the full 90/10 Rule breakdown.
> ---

---

## 5. Effort Summary

| Tier | Task Count | Target Directory | Estimated Entries |
|------|-----------|-----------------|-------------------|
| 0 — Draconomicon | 3 (PH7D-001 – PH7D-003) | `data/expanded/draconomicon/` | ~28 entries |
| 1 — Monster Manual II | 5 (PH7D-004 – PH7D-008) | `data/expanded/monster_manual_2/` | ~26 entries |
| 2 — Magic Item Compendium | 6 (PH7D-009 – PH7D-014) | `data/expanded/magic_item_compendium/` | ~60 entries |
| **Total** | **14** | — | **~114 entries** |

> All tasks within the same tier are independent of each other and may be executed in parallel
> across separate LLM generation sessions, provided each session targets a distinct output file.
> Tasks across tiers have no hard code dependencies; tier ordering reflects source-book grouping
> only.
