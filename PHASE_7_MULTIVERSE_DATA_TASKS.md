# PHASE_7_MULTIVERSE_DATA_TASKS.md — Multiverse Expansion (Tier 1 — Data Injection)

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
| Campaign Setup Wizard | `src/overseer_ui/setup_wizard.py` | ✅ Shipped |
| Genesis Protocol | `src/world_sim/genesis.py` | ✅ Shipped |
| World Builder Interface | `src/overseer_ui/world_builder.py` | ✅ Shipped |
| SRD Monster Data (446 entries) | `data/srd_3.5/monsters/` | ✅ Shipped |
| SRD Core Schema | `data/srd_3.5/` | ✅ Shipped |
| SRD Loader | `src/rules_engine/srd_loader.py` | ✅ Shipped |
| Magic Item Engine | `src/rules_engine/magic_item_engine.py` | ✅ Shipped |
| Game Persistence | `src/game/persistence.py` | ✅ Shipped |
| Expanded Data Root | `data/expanded/` | 🔲 Pending |
| Expanded Sub-Directories | `data/expanded/draconomicon/`, `data/expanded/monster_manual_2/`, `data/expanded/magic_item_compendium/` | 🔲 Pending |
| Expanded Schema | `data/expanded/schema_expanded_v1.json` | 🔲 Pending |
| Supplemental Rule Loader | `src/rules_engine/srd_loader.py` — `load_expanded_rules()` | 🔲 Pending |
| Expanded Monster Build Path | `src/rules_engine/srd_loader.py` — `build_monsters_from_srd()` | 🔲 Pending |
| Expanded Magic Item Merge | `src/rules_engine/magic_item_engine.py` | 🔲 Pending |
| Multiverse Book Toggles (UI) | `src/overseer_ui/setup_wizard.py` — `CampaignWizardState` | 🔲 Pending |
| Expanded Loader UI Wiring | `src/overseer_ui/setup_wizard.py` — button handlers | 🔲 Pending |
| Active Books Persistence | `src/game/persistence.py` — `save_party()` | 🔲 Pending |

---

## 1. Scope

Phase 7 Tier 1 architects the physical directory structures, JSON schema extensions, loader
overrides, and UI toggles required to ingest supplemental 3.5e rulebooks (Draconomicon,
Monster Manual II, Magic Item Compendium) as pure data injections. No changes are made to
the core action economy math. All new content is additive and gated behind explicit player
opt-in checkboxes in the Campaign Setup Wizard.

| # | Subsystem | Short Name | New / Modified Modules |
|---|-----------|------------|------------------------|
| A | Expanded Directory Architecture | expanded-dirs | `data/expanded/` *(new tree)*, `data/expanded/schema_expanded_v1.json` *(new)* |
| B | Supplemental Loader | srd-loader | `src/rules_engine/srd_loader.py` *(modified)*, `src/rules_engine/magic_item_engine.py` *(modified)* |
| C | Multiverse Setup UI | multiverse-ui | `src/overseer_ui/setup_wizard.py` *(modified)*, `src/game/persistence.py` *(modified)* |

---

## 2. Dependency Map

```
Tier 0  ──────────────────────────────────────────────────────────────────
         [PH7-001]  data/expanded/ directory tree (3 sub-directories)
         [PH7-002]  schema_expanded_v1.json safe extension schema
                │
Tier 1  ────────▼─────────────────────────────────────────────────────────
         [PH7-003]  load_expanded_rules(active_books) in srd_loader.py     (deps: PH7-001, PH7-002)
         [PH7-006]  CampaignWizardState Checkbox list for available books   (deps: PH7-001)
                │
Tier 2  ────────▼─────────────────────────────────────────────────────────
         [PH7-004]  build_monsters_from_srd() expanded dict check           (deps: PH7-003)
         [PH7-005]  magic_item_engine.py wondrous.json merge                (deps: PH7-001, PH7-003)
         [PH7-007]  Button handlers pass checkbox booleans → load_expanded_rules() (deps: PH7-003, PH7-006)
                │
Tier 3  ────────▼─────────────────────────────────────────────────────────
         [PH7-008]  persistence.py writes active_books into save file       (deps: PH7-007)
```

---

## 3. Task Tiers

### Tier 0 — Foundation (No Dependencies)

| Task | Title | Subsystem | Requirement | blockedBy | Effort |
|------|-------|-----------|-------------|-----------|--------|
| PH7-001 | Create data/expanded/ directory tree | expanded-dirs | Create the root directory `data/expanded/`. Inside it, create exactly three strictly named sub-directories: `data/expanded/draconomicon/`, `data/expanded/monster_manual_2/`, and `data/expanded/magic_item_compendium/`. Each sub-directory must contain a `.gitkeep` file so the empty directories are tracked by version control. No content JSON files are placed in these directories during this task — they are data-injection targets for future content authors. **Required data structures:** none. **Target files:** `data/expanded/draconomicon/.gitkeep`, `data/expanded/monster_manual_2/.gitkeep`, `data/expanded/magic_item_compendium/.gitkeep` *(all new)*. **Dependencies:** none. | — | S |
| PH7-002 | Create schema_expanded_v1.json | expanded-dirs | Create `data/expanded/schema_expanded_v1.json`. The schema must define a JSON Schema (draft-07) `object` that safely extends the core SRD monster and item object shape with the following additional optional metadata properties: `"source_book"` (type `string`, description: the canonical rulebook name this entry originates from, e.g. `"Draconomicon"`), `"source_page"` (type `integer`, description: the page number within that rulebook), `"is_expanded"` (type `boolean`, default `true`, description: flag distinguishing supplemental entries from core SRD entries), and `"tags"` (type `array` of `string`, description: freeform classification tags such as `["dragon", "undead"]`). All four properties must be declared under `"additionalProperties": false` within a nested `"expanded_metadata"` sub-object so they cannot collide with any existing core SRD field. The schema must include a `"$comment"` root key reading `"Expanded metadata block — append-only, never modify core SRD fields"` and a `"$schema"` key pointing to `"http://json-schema.org/draft-07/schema#"`. The resulting schema must be loadable and validated without errors by `src/game/session.py` at startup. **Required data structures:** none. **Target file:** `data/expanded/schema_expanded_v1.json` *(new)*. **Dependencies:** none. | — | S |

---

### Tier 1 — Integration (Depends on Tier 0)

| Task | Title | Subsystem | Requirement | blockedBy | Effort |
|------|-------|-----------|-------------|-----------|--------|
| PH7-003 | load_expanded_rules() in srd_loader.py | srd-loader | Modify `src/rules_engine/srd_loader.py`. Add a new module-level function `load_expanded_rules(active_books: list[str]) -> dict` that: (1) initialises an empty `expanded: dict[str, list[dict]]` accumulator keyed by book slug; (2) iterates `pathlib.Path("data/expanded").iterdir()` to discover all direct child directories; (3) for each discovered directory, checks whether `directory.name` is present in the `active_books` list — if not present, skips the directory entirely without raising; (4) for each matching directory, calls `Path(directory).glob("*.json")` and reads each JSON file with `json.loads(path.read_text())`; (5) extends `expanded[directory.name]` with all loaded dicts; (6) returns the fully populated `expanded` dict. The function must not raise if `data/expanded/` does not exist — catch `FileNotFoundError` and return an empty dict. Import only `pathlib.Path`, `json`, and nothing from the Textual stack. **Required data structures:** `data/expanded/` tree (PH7-001), `schema_expanded_v1.json` (PH7-002). **Target file:** `src/rules_engine/srd_loader.py`. **Dependencies:** PH7-001, PH7-002. | PH7-001, PH7-002 | M |
| PH7-006 | CampaignWizardState Checkbox list for available books | multiverse-ui | Modify `src/overseer_ui/setup_wizard.py`. Extend the `CampaignWizardState` dataclass with a new field `active_books: list[str] = field(default_factory=list)`. Inside `CampaignWizardScreen`, below the existing three `Button` widgets (`btn_sandbox`, `btn_premade`, `btn_world_builder`), compose a Textual `SelectionList` (or equivalent `Checkbox` group) containing exactly three entries: label `"Load Draconomicon"` bound to the slug value `"draconomicon"`, label `"Load Monster Manual II"` bound to the slug value `"monster_manual_2"`, and label `"Load Magic Item Compendium"` bound to the slug value `"magic_item_compendium"`. All three entries must be unchecked by default. Bind the `on_selection_list_selected_changed` (or equivalent `on_checkbox_changed`) handler so that toggling any entry adds or removes the corresponding slug string from `_wizard_state.active_books`. The underlying slug strings (`"draconomicon"`, `"monster_manual_2"`, `"magic_item_compendium"`) must exactly match the sub-directory names created in PH7-001. **Required data structures:** `CampaignWizardState` + `CampaignWizardScreen` (✅ `src/overseer_ui/setup_wizard.py`). **Target file:** `src/overseer_ui/setup_wizard.py`. **Dependencies:** PH7-001. | PH7-001 | M |

---

### Tier 2 — Integration (Depends on Tier 1)

| Task | Title | Subsystem | Requirement | blockedBy | Effort |
|------|-------|-----------|-------------|-----------|--------|
| PH7-004 | build_monsters_from_srd() expanded dict check | srd-loader | Modify `src/rules_engine/srd_loader.py`. Update the existing `build_monsters_from_srd()` function to accept an optional parameter `expanded: dict \| None = None` (default `None`). When `expanded` is not `None` and is non-empty, iterate its values (each a `list[dict]`) and attempt to construct a monster object from each dict before falling back to the existing Fighter-approximation path: specifically, if the dict contains the minimum required fields (`"name"`, `"cr"`, `"hp"`), build the monster directly from those fields; otherwise fall through to the Fighter-approximation path unchanged. The expanded monsters must be appended to the same return collection as core SRD monsters so the caller receives a single unified list. The function signature change must remain backwards-compatible: all existing callers that omit the `expanded` parameter must produce identical output to the pre-PH7 behaviour. The new monsters are dropped into the physical voxel grid through the same code path used for SRD monsters — no new grid-insertion logic is required. **Required data structures:** `load_expanded_rules()` (PH7-003). **Target file:** `src/rules_engine/srd_loader.py`. **Dependencies:** PH7-003. | PH7-003 | M |
| PH7-005 | magic_item_engine.py wondrous.json merge | srd-loader | Modify `src/rules_engine/magic_item_engine.py`. Add a new function `merge_expanded_wondrous(expanded: dict) -> None` that: (1) checks whether the key `"magic_item_compendium"` is present in the `expanded` dict (returned by `load_expanded_rules()`); (2) if present, iterates through the list of item dicts stored at `expanded["magic_item_compendium"]`; (3) for each item dict, reads the item's `"name"` field and constructs a `WondrousItem` dataclass instance using the existing `WondrousItem` fields (`name`, `slot`, `weight`, `price_gp`, `caster_level`, `aura_school`), mapping any missing optional fields to their dataclass defaults; (4) appends the newly constructed `WondrousItem` to the module-level `WONDROUS_ITEM_REGISTRY` list; (5) deduplicates `WONDROUS_ITEM_REGISTRY` in-place by `name` after the merge (last writer wins on duplicates, preserving the expanded book's version when names collide). The function must be safe to call multiple times — duplicate entries from repeated calls must not accumulate. The procedural merchant loot tables that already read from `WONDROUS_ITEM_REGISTRY` will automatically reflect the merged items without further modification. **Required data structures:** `WondrousItem` + `WONDROUS_ITEM_REGISTRY` (✅ `src/rules_engine/magic_item_engine.py`), `load_expanded_rules()` (PH7-003), `data/expanded/magic_item_compendium/wondrous.json` (PH7-001). **Target file:** `src/rules_engine/magic_item_engine.py`. **Dependencies:** PH7-001, PH7-003. | PH7-001, PH7-003 | M |
| PH7-007 | Wire checkbox booleans into load_expanded_rules() | multiverse-ui | Modify `src/overseer_ui/setup_wizard.py`. Update the `on_button_pressed` handlers for both `id="btn_sandbox"` and `id="btn_world_builder"` so that, immediately after the button press is detected and before calling `fast_forward_simulation()` or switching to `WorldBuilderScreen`, each handler reads `_wizard_state.active_books` and passes it directly into `load_expanded_rules(_wizard_state.active_books)` imported from `src/rules_engine/srd_loader.py`. The returned `expanded` dict must be stored in `_wizard_state` (add a new field `expanded_data: dict = field(default_factory=dict)` to `CampaignWizardState`) so downstream systems can access it without re-loading. Pass the `expanded` dict into `build_monsters_from_srd(expanded=_wizard_state.expanded_data)` and call `merge_expanded_wondrous(_wizard_state.expanded_data)` before the session begins. The `id="btn_premade"` handler must also honour `_wizard_state.active_books` in the same way — load expanded rules and merge wondrous items before constructing the `CampaignSession`. **Required data structures:** `CampaignWizardState` with `active_books` (PH7-006), `load_expanded_rules()` (PH7-003), `build_monsters_from_srd()` (PH7-004), `merge_expanded_wondrous()` (PH7-005). **Target file:** `src/overseer_ui/setup_wizard.py`. **Dependencies:** PH7-003, PH7-006. | PH7-003, PH7-006 | M |

---

### Tier 3 — Capstone (Depends on Tier 2)

| Task | Title | Subsystem | Requirement | blockedBy | Effort |
|------|-------|-----------|-------------|-----------|--------|
| PH7-008 | persistence.py writes active_books into save file | multiverse-ui | Modify `src/game/persistence.py`. Update `save_party()` (and any campaign-state serialisation function) to include the `active_books` list in the save payload: (1) accept an `active_books: list[str]` parameter (default `[]` for backwards compatibility with callers that predate PH7); (2) write the list under the key `"active_books"` in the top-level save dict before serialising to disk with `json.dumps`; (3) update the corresponding load path (e.g. `load_party()` or equivalent deserialisation function) to read `save_data.get("active_books", [])` and return it as part of the restored state, so the engine can call `load_expanded_rules(active_books)` again when resuming a session. The change must be backwards-compatible: save files that do not contain an `"active_books"` key must deserialise cleanly with `active_books = []`, which results in the vanilla SRD-only experience. No existing tests for `persistence.py` may be removed or modified — only extend the serialisation schema. **Required data structures:** `save_party()` + `load_party()` (✅ `src/game/persistence.py`), `active_books` list (PH7-007). **Target file:** `src/game/persistence.py`. **Dependencies:** PH7-007. | PH7-007 | M |

---

## 4. Effort Summary

| Tier | Task Count | S Tasks | M Tasks | L Tasks | Estimated Total |
|------|-----------|---------|---------|---------|-----------------|
| 0 — Foundation | 2 | 2 | 0 | 0 | ~1 day |
| 1 — Integration | 2 | 0 | 2 | 0 | ~2 days |
| 2 — Integration | 3 | 0 | 3 | 0 | ~3 days |
| 3 — Capstone | 1 | 0 | 1 | 0 | ~1 day |
| **Total** | **8** | **2** | **6** | **0** | **~7 dev-days** |

> Tier 0 tasks (PH7-001, PH7-002) are fully independent and may be developed in parallel.
> Within Tier 1, PH7-003 and PH7-006 share no common target file and can run in parallel; PH7-006 only requires PH7-001 while PH7-003 requires both PH7-001 and PH7-002.
> Within Tier 2, PH7-004 and PH7-005 are independent of each other and can run in parallel once PH7-003 is stable; PH7-007 must wait for both PH7-003 and PH7-006.
> PH7-008 is the single capstone task and must land after PH7-007 is fully tested.
