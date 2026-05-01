# PHASE_6_GENESIS_TASKS.md — Genesis & Campaign Matrix

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
| Multi-Screen Textual TUI | `src/overseer_ui/textual_app.py` | ✅ Shipped |
| LLM Context Manager | `src/agent_orchestration/context_manager.py` | ✅ Shipped |
| Chunk Manager | `src/terrain/chunk_manager.py` | ✅ Shipped |
| Chunk Generator | `src/terrain/chunk_generator.py` | ✅ Shipped |
| World Tick Orchestrator | `src/world_sim/world_tick.py` | ✅ Shipped |
| Campaign Session | `src/game/campaign.py` | ✅ Shipped |
| Biome Enums | `src/world_sim/biome.py` | ✅ Shipped |
| Entity Schema | `src/ai_sim/entity.py` | ✅ Shipped |
| SRD Monster Data (446 entries) | `data/srd_3.5/monsters/` | ✅ Shipped |
| Campaign Setup Wizard | `src/overseer_ui/setup_wizard.py` | 🔲 Pending |
| Genesis Protocol | `src/world_sim/genesis.py` | 🔲 Pending |
| World Builder Interface | `src/overseer_ui/world_builder.py` | 🔲 Pending |
| JIT Backstory Memory Hook | `src/agent_orchestration/backstory_loader.py` | 🔲 Pending |
| Campaign Data Directory | `data/campaigns/` | 🔲 Pending |

---

## 1. Scope

Phase 6 builds the player-facing campaign entry layer that sits above the core
simulation. Four subsystems gate access to the existing Phase 5 game loops by
letting the player choose, generate, or hand-craft the world before any
simulation tick executes.

| # | Subsystem | Short Name | New / Modified Modules |
|---|-----------|------------|------------------------|
| A | Campaign Setup Wizard | setup-wizard | `src/overseer_ui/setup_wizard.py` *(new)* |
| B | Genesis Protocol | genesis | `src/world_sim/genesis.py` *(new)* |
| C | World Builder Interface | world-builder | `src/overseer_ui/world_builder.py` *(new)* |
| D | JIT Backstory Memory Hook | jit-backstory | `src/ai_sim/entity.py`, `src/agent_orchestration/context_manager.py` |

---

## 2. Dependency Map

```
Tier 0  ──────────────────────────────────────────────────────────────────
         [PH6-001]  CampaignWizardState dataclass + three UI buttons
         [PH6-003]  fast_forward_simulation() headless tick engine
         [PH6-005]  WorldBuilderState dataclass + ASCII paint grid
         [PH6-008]  Entity.deep_lore_filepath optional field
                │
Tier 1  ────────▼─────────────────────────────────────────────────────────
         [PH6-002]  Premade Modules button → data/campaigns/ → campaign.py   (deps: PH6-001)
         [PH6-004]  True Random Sandbox button → fast_forward_simulation      (deps: PH6-001, PH6-003)
         [PH6-006]  Entity Dropper menu inside World Builder                  (deps: PH6-005)
         [PH6-009]  JIT context_manager dialogue load/clear hook              (deps: PH6-008)
                │
Tier 2  ────────▼─────────────────────────────────────────────────────────
         [PH6-007]  Compile Campaign button → JSON schema write               (deps: PH6-005, PH6-006)
```

---

## 3. Task Tiers

### Tier 0 — Foundation (No Dependencies)

| Task | Title | Subsystem | Requirement | blockedBy | Effort |
|------|-------|-----------|-------------|-----------|--------|
| PH6-001 | CampaignWizardState dataclass + three UI buttons | setup-wizard | Create `src/overseer_ui/setup_wizard.py`. Define `@dataclass(slots=True) CampaignWizardState` with fields: `selected_mode: str \| None = None` and `seed: int \| None = None`. Define `class CampaignWizardScreen(Screen)` using Textual. The screen composes a centered `Vertical` container holding exactly three `Button` widgets: label `[True Random Sandbox]` with `id="btn_sandbox"`, label `[Premade Modules]` with `id="btn_premade"`, and label `[World Builder]` with `id="btn_world_builder"`. Each button's `on_button_pressed` handler writes the corresponding mode string (`"sandbox"`, `"premade"`, `"world_builder"`) into `CampaignWizardState.selected_mode`. A module-level singleton `_wizard_state = CampaignWizardState()` is consumed by all downstream handlers. **Required data structures:** `CampaignWizardState`, `CampaignWizardScreen`. **Target file:** `src/overseer_ui/setup_wizard.py` *(new)*. **Dependencies:** none. | — | S |
| PH6-003 | fast_forward_simulation() headless tick engine | genesis | Create `src/world_sim/genesis.py`. Define `fast_forward_simulation(years: int, seed: int) -> dict` which: (1) instantiates `ChunkManager` from `src/terrain/chunk_manager.py` using `seed` as the RNG seed, with no UI widget attached (strictly headless — no Textual `Screen` import, no `Static` widget, no `AnimationRenderer`); (2) computes `total_ticks = years * 365` and calls the `run_world_tick` loop from `src/world_sim/world_tick.py` exactly `total_ticks` times at maximum CPU speed by passing a `WorldState` constructed with `tick=0` and incrementing it each iteration without any `asyncio.sleep` or frame-rate throttle; (3) captures the final `WorldState` snapshot after all ticks complete; (4) serialises the snapshot into a plain `dict` with keys `seed`, `years_simulated`, `final_tick`, `chunks` (list of serialised `WorldChunk` dicts), and `faction_records` (list of serialised `FactionRecord` dicts from `src/world_sim/factions.py`); (5) returns that dict. Import only `ChunkManager`, `run_world_tick`, `WorldState`, `FactionRecord`, and `random`. **Required data structures:** `ChunkManager` (✅ `src/terrain/chunk_manager.py`), `run_world_tick` + `WorldState` (✅ `src/world_sim/world_tick.py`), `FactionRecord` (✅ `src/world_sim/factions.py`). **Target file:** `src/world_sim/genesis.py` *(new)*. **Dependencies:** none. | — | M |
| PH6-005 | WorldBuilderState dataclass + ASCII paint grid | world-builder | Create `src/overseer_ui/world_builder.py`. Define `@dataclass WorldBuilderState` with fields: `grid: dict[tuple[int, int], str] = field(default_factory=dict)` (mapping `(x, y)` coordinate to a `Biome` enum member name string) and `entity_anchors: dict[tuple[int, int], list[str]] = field(default_factory=dict)` (mapping `(x, y)` to a list of monster ID strings). Define `class WorldBuilderScreen(Screen)` composing a 24-row × 80-column `Static` widget rendered as a 2D ASCII grid where each cell displays the first character of its assigned `Biome` name (e.g. `F` for `FOREST`, `D` for `DESERT`, `.` for unassigned). Implement mouse-driven paint: bind `on_mouse_move` so that when the left mouse button is held, the `(col, row)` coordinate under the cursor is written into `WorldBuilderState.grid` using the currently selected `Biome` enum value. Expose a `set_active_biome(biome_name: str) -> None` method that validates the string against all members of the `Biome` enum in `src/world_sim/biome.py` and stores the active brush. **Required data structures:** `WorldBuilderState`, `WorldBuilderScreen`, `Biome` (✅ `src/world_sim/biome.py`). **Target file:** `src/overseer_ui/world_builder.py` *(new)*. **Dependencies:** none. | — | M |
| PH6-008 | Entity.deep_lore_filepath optional field | jit-backstory | Modify `src/ai_sim/entity.py`. Add the field `deep_lore_filepath: Optional[str] = None` to the `Entity` dataclass immediately after the existing `metadata: dict` field. The field must be typed `Optional[str]` (already imported via `typing`), default to `None`, and point to an absolute or project-relative path of a `.txt` file containing the NPC's deep backstory prose. Do not store raw backstory text in this field or in any other `Entity` field — only the filesystem path is stored. Update `Entity.__repr__` (if one exists) or the existing `__str__` serialisation to include `deep_lore_filepath` in its output only when the value is not `None`. **Required data structures:** `Entity` (✅ `src/ai_sim/entity.py`). **Target file:** `src/ai_sim/entity.py`. **Dependencies:** none. | — | S |

---

### Tier 1 — Integration (Depends on Tier 0)

| Task | Title | Subsystem | Requirement | blockedBy | Effort |
|------|-------|-----------|-------------|-----------|--------|
| PH6-002 | Premade Modules button → data/campaigns/ → campaign.py | setup-wizard | Extend `src/overseer_ui/setup_wizard.py`. Inside the `on_button_pressed` handler for `id="btn_premade"`, implement the following exact logic: (1) scan the `data/campaigns/` directory using `pathlib.Path("data/campaigns").glob("*.json")`; (2) for each discovered `.json` file, call `json.loads(path.read_text())` to deserialise the campaign dict; (3) import `CampaignSession` from `src/game/campaign.py` and construct a `CampaignSession` directly from the deserialised dict, bypassing `ChunkGenerator` entirely — the JSON payload must contain a pre-built `chunks` list that `CampaignSession` accepts directly via its `world_chunks` constructor parameter; (4) store the loaded `CampaignSession` instance in `_wizard_state` and post a `SwitchScreen("overworld")` message to transition into the existing `OverworldScreen`. If `data/campaigns/` does not exist or contains no `.json` files, display a Textual `notify("No premade campaigns found in data/campaigns/", severity="error")` toast and remain on `CampaignWizardScreen`. **Required data structures:** `CampaignWizardState` + `CampaignWizardScreen` (PH6-001), `CampaignSession` (✅ `src/game/campaign.py`). **Target file:** `src/overseer_ui/setup_wizard.py`. **Dependencies:** PH6-001. | PH6-001 | M |
| PH6-004 | True Random Sandbox button → fast_forward_simulation | setup-wizard | Extend `src/overseer_ui/setup_wizard.py`. Inside the `on_button_pressed` handler for `id="btn_sandbox"`, implement the following exact logic: (1) generate `random_seed = random.randint(0, 2**32 - 1)`; (2) store `random_seed` in `_wizard_state.seed`; (3) call `fast_forward_simulation(500, random_seed)` imported from `src/world_sim/genesis.py`, receiving the output `dict`; (4) write the dict as formatted JSON to `data/campaigns/generated_sandbox.json` using `pathlib.Path("data/campaigns/generated_sandbox.json").write_text(json.dumps(result, indent=2))`, creating the `data/campaigns/` directory first if it does not exist (`Path.mkdir(parents=True, exist_ok=True)`); (5) import `CampaignSession` from `src/game/campaign.py`, construct it from the written JSON, store it in `_wizard_state`, and post `SwitchScreen("overworld")` to load the game. **Required data structures:** `CampaignWizardState` + `CampaignWizardScreen` (PH6-001), `fast_forward_simulation` (PH6-003), `CampaignSession` (✅ `src/game/campaign.py`). **Target file:** `src/overseer_ui/setup_wizard.py`. **Dependencies:** PH6-001, PH6-003. | PH6-001, PH6-003 | M |
| PH6-006 | Entity Dropper menu inside World Builder | world-builder | Extend `src/overseer_ui/world_builder.py`. Add a `Select` dropdown widget (Textual `Select`) populated at mount time by scanning `data/srd_3.5/monsters/` with `pathlib.Path("data/srd_3.5/monsters").glob("*.json")`, reading each file, and collecting every monster object's `name` and `id` fields into a list of `(label, value)` tuples. Bind `on_select_changed` to store the currently selected monster ID in a new `WorldBuilderScreen._active_monster_id: str \| None` attribute. Add a secondary mouse click handler `on_click` (distinct from the paint handler): when `_active_monster_id` is not `None` and the right mouse button is pressed, compute the grid `(x, y)` from the click coordinates and call `WorldBuilderState.entity_anchors.setdefault((x, y), []).append(_active_monster_id)`, mathematically anchoring a `SpeciesPopRecord`-compatible monster ID to that chunk coordinate. Render anchored cells with an `@` glyph overlaid on the biome character in the ASCII grid (priority: `@` glyph overrides the biome character when any anchor exists at that cell). **Required data structures:** `WorldBuilderState` + `WorldBuilderScreen` (PH6-005), `SpeciesPopRecord` (✅ `src/world_sim/population.py`). **Target file:** `src/overseer_ui/world_builder.py`. **Dependencies:** PH6-005. | PH6-005 | M |
| PH6-009 | JIT context_manager dialogue load/clear hook | jit-backstory | Extend `src/agent_orchestration/context_manager.py`. Add `load_deep_lore(entity: Entity) -> str \| None` which: (1) checks `entity.deep_lore_filepath is not None`; (2) if truthy, opens the file at that path, reads its full text content, and returns it as a plain string; (3) if falsy or if the file does not exist (catching `FileNotFoundError`), returns `None`. Add `build_dialogue_context(system_prompt: str, user_prompt: str, entity: Entity) -> list[str]` which: (1) calls `load_deep_lore(entity)` to retrieve the optional lore text; (2) if lore text is not `None`, prepends it as an additional system message to the prompt chunks computed by the existing `ContextManager.chunk_prompt` method; (3) returns the final list of chunk strings. Add `clear_dialogue_lore(lore_text: str \| None) -> None` which: (1) if `lore_text` is not `None`, calls `del lore_text` and then `gc.collect()` (import `gc` at the top of the file) to safely evict the lore string from memory immediately after the dialogue concludes, preventing VRAM accumulation across successive conversations; (2) if `lore_text` is `None`, performs no operation. Document in the function docstring that callers must invoke `clear_dialogue_lore` in a `finally` block to guarantee cleanup even if the LLM call raises an exception. **Required data structures:** `Entity` with `deep_lore_filepath` (PH6-008), `ContextManager` (✅ `src/agent_orchestration/context_manager.py`). **Target file:** `src/agent_orchestration/context_manager.py`. **Dependencies:** PH6-008. | PH6-008 | M |

---

### Tier 2 — Capstone (Depends on Tier 1)

| Task | Title | Subsystem | Requirement | blockedBy | Effort |
|------|-------|-----------|-------------|-----------|--------|
| PH6-007 | Compile Campaign button → playable JSON schema | world-builder | Extend `src/overseer_ui/world_builder.py`. Add a `Button` widget with label `[Compile Campaign]` and `id="btn_compile"` to `WorldBuilderScreen`. Inside its `on_button_pressed` handler, implement the following exact serialisation logic: (1) iterate `WorldBuilderState.grid` to produce a `"chunks"` list where each entry is a dict `{"x": x, "y": y, "biome": biome_name, "monster_ids": WorldBuilderState.entity_anchors.get((x, y), [])}` for every `(x, y)` key present in `WorldBuilderState.grid`; (2) build a top-level campaign dict with keys `"source": "world_builder"`, `"seed": None`, `"chunks": <chunks list>`, and `"faction_records": []`; (3) determine the output filename as `f"data/campaigns/custom_{int(time.time())}.json"` (import `time`); (4) write the dict as formatted JSON to that file using `pathlib.Path(filename).write_text(json.dumps(campaign_dict, indent=2))`, creating `data/campaigns/` if necessary; (5) display a Textual `notify(f"Campaign compiled to {filename}", severity="information")` toast. The written JSON must be directly loadable by the `[Premade Modules]` handler in `CampaignWizardScreen` (PH6-002) without any schema conversion. **Required data structures:** `WorldBuilderState` + `WorldBuilderScreen` (PH6-005), entity anchors from `Entity Dropper` (PH6-006). **Target file:** `src/overseer_ui/world_builder.py`. **Dependencies:** PH6-005, PH6-006. | PH6-005, PH6-006 | M |

---

## 4. Effort Summary

| Tier | Task Count | S Tasks | M Tasks | L Tasks | Estimated Total |
|------|-----------|---------|---------|---------|-----------------|
| 0 — Foundation | 4 | 2 | 2 | 0 | ~2 days |
| 1 — Integration | 4 | 0 | 4 | 0 | ~4 days |
| 2 — Capstone | 1 | 0 | 1 | 0 | ~1 day |
| **Total** | **9** | **2** | **7** | **0** | **~7 dev-days** |

> Tier 0 tasks (PH6-001, PH6-003, PH6-005, PH6-008) are fully independent and may be developed in parallel across four engineers.
> Within Tier 1, PH6-002 and PH6-004 share the same target file (`setup_wizard.py`) and must be sequenced; PH6-006 and PH6-009 are mutually independent and can run in parallel.
> PH6-007 is the single capstone task — it must land after PH6-005 and PH6-006 are both stable and tested.
