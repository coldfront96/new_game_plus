# PHASE_2_INTERACTION_TASKS.md — Player Interaction & Civilized Ecology Build Plan

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
| Monster Manual Physics | `src/rules_engine/mm_passive.py`, `mm_grapple.py`, `mm_immortal.py`, `mm_metaphysical.py` | ✅ Shipped |
| Food Web Engine | `src/world_sim/food_web.py` | ✅ Shipped |
| Lair Carving | `src/world_sim/lairs.py`, `src/terrain/chunk_generator.py` | ✅ Shipped |
| Faction Mechanics | `src/world_sim/factions.py` | ✅ Shipped |
| Population Ledger & World Tick | `src/world_sim/population.py`, `src/world_sim/world_tick.py` | ✅ Shipped |
| Biome & Migration Engine | `src/world_sim/biome.py`, `src/world_sim/migration.py` | ✅ Shipped |
| Chunk Manager | `src/terrain/chunk_manager.py` | ✅ Shipped |
| LLM Bridge (async inference client) | `src/ai_sim/llm_bridge.py` | ✅ Shipped |
| Combat Engine & Conditions | `src/rules_engine/combat.py`, `src/rules_engine/conditions.py` | ✅ Shipped |
| Character Sheet (3.5e) | `src/rules_engine/character_35e.py` | ✅ Shipped |
| Civilization Builder | `src/world_sim/civilization_builder.py` | ✅ Shipped |
| NPC Dialogue System | `src/ai_sim/llm_bridge.py` (extension) | ✅ Shipped |
| Player Controller | `src/game/player_controller.py` | ✅ Shipped |

---

## 1. Scope

This document is the authoritative project-management plan for the three
interdependent subsystems that form **Phase 2: Player Interaction & Civilized
Ecology** of New Game Plus:

| # | Subsystem | Short Name | New / Modified Modules |
|---|-----------|------------|------------------------|
| A | Civilization & Economy | Civ-Economy | `src/world_sim/civilization_builder.py` |
| B | Real-Time NPC Dialogue | NPC-Dialogue | `src/ai_sim/llm_bridge.py` (extended), Textual UI dialogue panel |
| C | Avatar Agency & Fog of War | Avatar-FoW | `src/game/player_controller.py` |

**Format conventions (matching existing build docs):**

- Task IDs are prefixed `PH2-` (Phase 2).
- `Effort` ∈ {S = ≤½ day, M = 1–2 days, L = 3+ days}.
- `blockedBy` references resolve to an earlier `PH2-` task or a shipped module marked ✅.
- All new schemas use `dataclasses` with `slots=True`; all enums are `enum.Enum` subclasses.

---

## 2. Dependency Map

```
Tier 0  ──────────────────────────────────────────────────────────────────
         [PH2-001..PH2-002]  Civ-Economy base schemas & biome classifier
         [PH2-006]           NPC Dialogue Panel widget schema
         [PH2-010]           PlayerController schema
                │
Tier 1  ────────▼─────────────────────────────────────────────────────────
         [PH2-003]           Procedural town generator
         [PH2-004]           MerchantInventoryRecord schema
         [PH2-007]           NPC context snapshot builder
         [PH2-011]           Keyboard input dispatcher
                │
Tier 2  ────────▼─────────────────────────────────────────────────────────
         [PH2-005]           Population-linked inventory calculator
         [PH2-008]           async generate_npc_dialogue()
         [PH2-012]           Fog of War calculator
                │
Tier 3  ────────▼─────────────────────────────────────────────────────────
         [PH2-009]           Dialogue streaming integration
         [PH2-013]           Fog of War UI renderer
         [PH2-014]           ChunkManager dynamic load/unload
```

**External dependencies this document leans on (must remain stable):**

| Dependency | File | Used By |
|------------|------|---------|
| `SpeciesPopRecord` dataclass | `src/world_sim/population.py` | PH2-005 |
| `PopulationLedger` | `src/world_sim/population.py` | PH2-005 |
| `WorldChunk` dataclass | `src/world_sim/population.py` | PH2-003, PH2-014 |
| `Biome` enum | `src/world_sim/biome.py` | PH2-002, PH2-003 |
| `FactionRecord` / `DEFAULT_FACTIONS` | `src/world_sim/factions.py` | PH2-003, PH2-007 |
| `CombatEntity` dataclass | `src/rules_engine/combat.py` | PH2-007, PH2-008, PH2-010, PH2-011 |
| `LLMClient.query_model_async` | `src/ai_sim/llm_bridge.py` | PH2-008 |
| `ChunkManager` | `src/terrain/chunk_manager.py` | PH2-014 |

---

## 3. Task Tiers

### Tier 0 — Base Schemas & Configuration (No Dependencies)

| Task | Title | Subsystem | Requirement | blockedBy | Effort |
|------|-------|-----------|-------------|-----------|--------|
| PH2-001 | TownRecord Schema | civ-economy | Dataclass `TownRecord` (slots=True): `town_id: str`, `name: str`, `chunk_id: str`, `biome: Biome`, `faction_name: str \| None`, `population_count: int`, `merchant_ids: list[str]`; towns are generated at world-init and stored in a module-level `TownRegistry` (`dict[str, TownRecord]`); a `town_id` is derived from a deterministic hash of `chunk_id + seed` to guarantee reproducibility | — | S |
| PH2-002 | Safe Biome Classifier | civ-economy | Function `is_safe_biome(biome: Biome) -> bool`; returns `True` for biomes suitable for permanent settlement: `Temperate_Plain`, `Temperate_Forest`, `Temperate_Hill`, `Warm_Plain`, `Warm_Forest`, `Any_Urban`; returns `False` for hostile, transient, or planar biomes (e.g. `Underdark`, `Elemental_*`, `Outer_Plane`, `Arctic`, `Negative_Energy`); used as the sole gate in the town placement loop — no chunk whose biome returns `False` may host a town; **target file:** `src/world_sim/civilization_builder.py` | — | S |
| PH2-006 | DialoguePanel Widget Schema | npc-dialogue | Dataclass `DialogueLine` (slots=True): `speaker_id: str`, `speaker_name: str`, `text: str`, `tick: int`; class `DialoguePanel` wrapping a Textual `RichLog` widget; exposes `push_line(line: DialogueLine) -> None` (appends formatted text) and `clear() -> None`; the panel occupies a fixed sidebar column in the Textual layout and never blocks the main world view; streaming tokens are pushed as partial `DialogueLine` updates until the generation completes; **target file:** Textual UI module (overseer UI layer) | — | S |
| PH2-010 | PlayerController Schema | avatar-fow | Dataclass `PlayerController` (slots=True): `player_id: str`, `entity_id: str` (bound `CombatEntity` id), `chunk_id: str`, `vision_radius: int` (in voxels; default 8), `fog_revealed: set[tuple[int, int, int]]` (voxel coords visible at least once); enum `PlayerAction` (MoveNorth / MoveSouth / MoveEast / MoveWest / MoveUp / MoveDown / Wait / Interact); the controller is the single authoritative source of player position — all Fog of War and chunk-loading decisions read from it; **target file:** `src/game/player_controller.py` | — | S |

---

### Tier 1 — Core Mechanics (Depends on Tier 0)

| Task | Title | Subsystem | Requirement | blockedBy | Effort |
|------|-------|-----------|-------------|-----------|--------|
| PH2-003 | Procedural Town Generator | civ-economy | Function `generate_towns(world_chunks: list[WorldChunk], faction_registry: dict[str, FactionRecord], seed: int, max_towns_per_biome: int = 3) -> TownRegistry`; iterates all chunks; for each chunk whose biome passes `is_safe_biome`: rolls a placement chance (deterministic from `seed + chunk_id` hash); if placed, creates a `TownRecord` assigning the nearest matching `FactionRecord` by alignment affinity (Lawful factions prefer `Any_Urban`, Neutral factions prefer plains/forest); a single chunk may host at most one town; returns the complete `TownRegistry`; **target file:** `src/world_sim/civilization_builder.py`; **input deps:** `WorldChunk` (✅ `src/world_sim/population.py`), `Biome` (✅ `src/world_sim/biome.py`), `FactionRecord` (✅ `src/world_sim/factions.py`), PH2-001, PH2-002 | PH2-001, PH2-002 | M |
| PH2-004 | MerchantInventoryRecord Schema | civ-economy | Dataclass `MerchantInventoryRecord` (slots=True): `merchant_id: str`, `town_id: str`, `stock: dict[str, int]` (item_name → quantity); dataclass `InventoryItem` (slots=True): `item_name: str`, `base_price_gp: int`, `category: ItemCategory`; enum `ItemCategory` (RawMaterial / Weapon / Armour / Provision / Alchemical / Misc); the `stock` dict is populated by the inventory calculator (PH2-005) and re-evaluated each world tick; merchants are keyed by `merchant_id` in a module-level `MerchantRegistry`; **target file:** `src/world_sim/civilization_builder.py` | PH2-001 | S |
| PH2-007 | NPC Context Snapshot Builder | npc-dialogue | Function `build_npc_context(entity_id: str, combat_registry: dict[str, CombatEntity], faction_registry: dict[str, FactionRecord]) -> dict[str, Any]`; constructs a serialisable snapshot containing: entity name, HP (current and max), AC, BAB, all active conditions, faction name and alignment, hostile faction names, and the entity's chunk_id; this snapshot is the sole data passed to the LLM prompt builder in PH2-008 — the LLM cannot receive raw stat-block objects; raises `EntityNotFoundError` if `entity_id` is absent from `combat_registry`; **target file:** `src/ai_sim/llm_bridge.py`; **input deps:** `CombatEntity` (✅ `src/rules_engine/combat.py`), `FactionRecord` (✅ `src/world_sim/factions.py`) | PH2-006 | S |
| PH2-011 | Keyboard Input Dispatcher | avatar-fow | Function `dispatch_player_input(controller: PlayerController, action: PlayerAction, combat_registry: dict[str, CombatEntity]) -> PlayerController`; maps each `PlayerAction` to a voxel-coordinate delta and applies it to the bound `CombatEntity`'s position via the existing combat movement rules; `MoveNorth/South/East/West` shift the XY voxel coordinate by 1; `MoveUp/Down` shift the Z coordinate by 1; `Wait` advances the entity's turn without moving; `Interact` is a no-op stub reserved for future object interaction; the Textual UI key bindings (`n`, `s`, `e`, `w`, `u`, `d`, `.`, `i`) must call this function and re-render the viewport on each invocation; **target file:** `src/game/player_controller.py`; **input deps:** `CombatEntity` (✅ `src/rules_engine/combat.py`), PH2-010 | PH2-010 | M |

---

### Tier 2 — Generators & Live Systems (Depends on Tier 1)

| Task | Title | Subsystem | Requirement | blockedBy | Effort |
|------|-------|-----------|-------------|-----------|--------|
| PH2-005 | Population-Linked Inventory Calculator | civ-economy | Function `calculate_merchant_inventory(town: TownRecord, ledger: PopulationLedger, species_registry: dict[str, SpeciesPopRecord], item_table: dict[str, InventoryItem]) -> MerchantInventoryRecord`; for each species whose chunk matches `town.chunk_id`: reads `local_counts[chunk_id]`; maps species to item categories using a `SPECIES_TO_LOOT` table (e.g. `"deer"` → `("Leather", "Raw Meat")`, `"wolf"` → `("Wolf Pelt", "Bone")`); stock quantity = `floor(local_count * drop_rate_coefficient)` where `drop_rate_coefficient` is a per-item constant (e.g. 0.1 for common materials); stock is clamped to `[0, 99]`; re-evaluated every world tick — high prey density directly inflates leather/meat stock, predator dominance inflates exotic components; **target file:** `src/world_sim/civilization_builder.py`; **input deps:** `SpeciesPopRecord` / `PopulationLedger` (✅ `src/world_sim/population.py`), PH2-003, PH2-004 | PH2-003, PH2-004 | M |
| PH2-008 | Async NPC Dialogue Generator | npc-dialogue | Async function `generate_npc_dialogue(entity_id: str, player_prompt: str, combat_registry: dict[str, CombatEntity], faction_registry: dict[str, FactionRecord], api_url: str = "http://localhost:11434/api/generate", model: str = "llama3") -> AsyncIterator[str]`; calls `build_npc_context` (PH2-007) to obtain the entity snapshot; constructs a system prompt of the form: `"You are {name}, a {alignment} {faction} NPC. HP: {hp}/{max_hp}. AC: {ac}. Hostile to: {hostile_factions}. Stay in character."`; POSTs a streaming JSON request to `api_url` with `{"model": model, "prompt": ..., "stream": true}`; yields each decoded `response` token from the NDJSON stream as it arrives; on HTTP error or connection refused, yields a single fallback line: `"[{name} says nothing.]"`; the caller must consume the async iterator and push each token to `DialoguePanel.push_line`; **target file:** `src/ai_sim/llm_bridge.py`; **input deps:** `LLMClient` / `CognitiveState` (✅ `src/ai_sim/llm_bridge.py`), PH2-007 | PH2-007 | M |
| PH2-012 | Fog of War Calculator | avatar-fow | Function `calculate_visible_voxels(controller: PlayerController, chunk_voxels: set[tuple[int, int, int]]) -> tuple[set[tuple[int, int, int]], set[tuple[int, int, int]]]`; returns a 2-tuple: `(visible, hidden)` where `visible` = all voxel coords whose Euclidean distance from the player's current voxel is ≤ `controller.vision_radius`; `hidden` = `chunk_voxels - visible`; updates `controller.fog_revealed` by union-ing the `visible` set (revealed coords are never re-hidden); the UI renders `hidden` voxels as `"░"` characters regardless of their true tile content; the calculation must run in O(vision_radius³) time and must not iterate the full world chunk set; **target file:** `src/game/player_controller.py`; **input deps:** PH2-010, PH2-011 | PH2-010, PH2-011 | M |

---

### Tier 3 — Integration & Rendering (Depends on Tier 2)

| Task | Title | Subsystem | Requirement | blockedBy | Effort |
|------|-------|-----------|-------------|-----------|--------|
| PH2-009 | Dialogue Streaming Integration | npc-dialogue | Wire `generate_npc_dialogue` (PH2-008) into the Textual UI event loop; on player pressing the `t` (talk) key while adjacent to an NPC entity, spawn an `asyncio.Task` that consumes the `AsyncIterator[str]` from PH2-008 and calls `DialoguePanel.push_line` for each token; the main UI must not block during streaming — use `asyncio.create_task` and Textual's `call_from_thread` or `post_message` mechanism; the Dialogue Panel header must display the NPC's name while a response is streaming and revert to idle state on completion or error; **target file:** Textual UI module (overseer UI layer); **input deps:** PH2-006, PH2-008 | PH2-006, PH2-008 | S |
| PH2-013 | Fog of War UI Renderer | avatar-fow | Update the Textual voxel viewport widget to consume the `(visible, hidden)` output of `calculate_visible_voxels` (PH2-012) on every render frame; hidden voxels must be drawn as `"░"` in a dimmed colour style (`dim` Rich style); previously-revealed but currently-not-visible voxels (`fog_revealed - visible`) must be drawn at half brightness (`dim italic`); fully unknown voxels (never in `fog_revealed`) are drawn as solid `"█"`; the viewport must call `calculate_visible_voxels` once per player action, not once per frame, to avoid redundant recalculation; **target file:** Textual UI module (overseer UI layer); **input deps:** PH2-010, PH2-012 | PH2-010, PH2-012 | S |
| PH2-014 | ChunkManager Dynamic Load/Unload | avatar-fow | Function `update_loaded_chunks(controller: PlayerController, chunk_manager: ChunkManager, load_radius: int = 2) -> tuple[list[str], list[str]]`; returns `(newly_loaded, newly_unloaded)` chunk ID lists; computes the set of chunk IDs within `load_radius` chunks of `controller.chunk_id` using `ChunkAdjacencyGraph.biome_reachable_in_steps` (already implemented in LW-021); loads any chunk in the computed set that is not currently active in `ChunkManager`; unloads any chunk currently active in `ChunkManager` that falls outside the set; must be called by `dispatch_player_input` (PH2-011) whenever the player crosses a chunk boundary (i.e. when `controller.chunk_id` changes); chunk state (entity positions, population deltas) must be serialised to the persistence layer before unloading via `session.py`; **target file:** `src/game/player_controller.py`; **input deps:** `ChunkManager` (✅ `src/terrain/chunk_manager.py`), PH2-011, PH2-012 | PH2-011, PH2-012 | L |

---

## 4. Effort Summary

| Tier | Task Count | S Tasks | M Tasks | L Tasks | Estimated Total |
|------|-----------|---------|---------|---------|-----------------|
| 0 — Base Schemas | 4 | 4 | 0 | 0 | ~2 days |
| 1 — Core Mechanics | 4 | 2 | 2 | 0 | ~4 days |
| 2 — Generators & Live Systems | 3 | 0 | 3 | 0 | ~5 days |
| 3 — Integration & Rendering | 3 | 2 | 0 | 1 | ~4 days |
| **Total** | **14** | **8** | **5** | **1** | **~15 dev-days** |

> Subsystem A (PH2-001–PH2-005) and Subsystem C Tier 0–1 (PH2-010–PH2-011) are fully independent
> and may be started in parallel from day one.
> Subsystem B (PH2-006–PH2-009) depends only on shipped LLM infrastructure and may also begin immediately.
> PH2-014 (ChunkManager dynamic loading) is the sole L-effort task and is the last to complete.
