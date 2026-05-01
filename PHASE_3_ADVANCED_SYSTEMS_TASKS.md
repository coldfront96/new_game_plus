# PHASE_3_ADVANCED_SYSTEMS_TASKS.md — Advanced Systems & Dungeoneering Build Plan

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
| ChunkGenerator (surface terrain) | `src/terrain/chunk_generator.py` | ✅ Shipped |
| Lair Carver (`carve_lair`) | `src/terrain/chunk_generator.py` | ✅ Shipped |
| Block / Material enum | `src/terrain/block.py` | ✅ Shipped |
| Chunk dataclass | `src/terrain/chunk.py` | ✅ Shipped |
| ChunkManager | `src/terrain/chunk_manager.py` | ✅ Shipped |
| Trap Engine | `src/rules_engine/traps.py` | ✅ Shipped |
| Treasure Engine | `src/rules_engine/treasure.py` | ✅ Shipped |
| Combat Engine & Conditions | `src/rules_engine/combat.py`, `src/rules_engine/conditions.py` | ✅ Shipped |
| Character Sheet (3.5e) | `src/rules_engine/character_35e.py` | ✅ Shipped |
| Faction Mechanics | `src/world_sim/factions.py` | ✅ Shipped |
| Anomaly Records | `src/world_sim/anomaly.py` | ✅ Shipped |
| Tactical AI Evaluator | `src/ai_sim/tactics.py` | ✅ Shipped |
| LLM Bridge (async inference client) | `src/ai_sim/llm_bridge.py` | ✅ Shipped |
| Mythos Forge (artifact generator) | `src/rules_engine/mythos_forge.py` | ✅ Shipped |
| Quest Journal & Generator | `src/game/quest.py` | ✅ Shipped |
| Campaign Session | `src/game/campaign.py` | ✅ Shipped |
| Player Controller & Fog of War | `src/game/player_controller.py` | ✅ Shipped |
| Textual UI (Dialogue Panel, FoW renderer) | `src/overseer_ui/textual_app.py` | ✅ Shipped |
| Dungeon Carver | `src/terrain/dungeon_carver.py` | 🔲 Phase 3 target |
| Party Manager | `src/game/party_manager.py` | 🔲 Phase 3 target |
| Mythos ↔ Campaign/Quest wiring | `src/rules_engine/mythos_forge.py` (extension) | 🔲 Phase 3 target |

---

## 1. Scope

This document is the authoritative project-management plan for the three
interdependent subsystems that form **Phase 3: Advanced Systems & Dungeoneering**
of New Game Plus:

| # | Subsystem | Short Name | New / Modified Modules |
|---|-----------|------------|------------------------|
| A | Subterranean Architecture | Dungeon-Carver | `src/terrain/dungeon_carver.py` |
| B | Tactical Party System | Party-Manager | `src/game/party_manager.py` |
| C | Mythos Integration | Mythos-Wire | `src/rules_engine/mythos_forge.py` (extended), `src/game/campaign.py`, `src/game/quest.py` |

**Format conventions (matching existing build docs):**

- Task IDs are prefixed `PH3-` (Phase 3).
- `Effort` ∈ {S = ≤½ day, M = 1–2 days, L = 3+ days}.
- `blockedBy` references resolve to an earlier `PH3-` task or a shipped module marked ✅.
- All new schemas use `dataclasses` with `slots=True`; all enums are `enum.Enum` subclasses.

---

## 2. Dependency Map

```
Tier 0  ──────────────────────────────────────────────────────────────────
         [PH3-001]  DungeonFloor schema & negative-Z constants
         [PH3-005]  PartyRecord schema & ControlMode enum
         [PH3-010]  MythosThresholdRecord schema
                │
Tier 1  ────────▼─────────────────────────────────────────────────────────
         [PH3-002]  Multi-floor room & hallway carver
         [PH3-006]  Party formation API
         [PH3-007]  Autonomous companion turn router
         [PH3-011]  Faction / chunk danger evaluator
                │
Tier 2  ────────▼─────────────────────────────────────────────────────────
         [PH3-003]  Trap & treasure voxel spawner
         [PH3-008]  Manual companion turn router
         [PH3-009]  Party combat round dispatcher
         [PH3-012]  Forge trigger → artifact generator
                │
Tier 3  ────────▼─────────────────────────────────────────────────────────
         [PH3-004]  ChunkGenerator negative-Z integration hook
         [PH3-013]  Artifact quest objective injector
```

**External dependencies this document leans on (must remain stable):**

| Dependency | File | Used By |
|------------|------|---------|
| `Chunk` dataclass | `src/terrain/chunk.py` | PH3-001, PH3-002, PH3-003, PH3-004 |
| `Block` / `Material` enum | `src/terrain/block.py` | PH3-002, PH3-003 |
| `ChunkGenerator` | `src/terrain/chunk_generator.py` | PH3-004 |
| `AnomalyRecord` | `src/world_sim/anomaly.py` | PH3-002, PH3-004 |
| `TrapBase` / `MechanicalTrap` / `MagicalTrap` | `src/rules_engine/traps.py` | PH3-003 |
| `TreasureHoard` / `generate_treasure_hoard` | `src/rules_engine/treasure.py` | PH3-003 |
| `CombatEntity` dataclass | `src/rules_engine/combat.py` | PH3-005, PH3-006, PH3-007, PH3-008, PH3-009 |
| `Character35e` | `src/rules_engine/character_35e.py` | PH3-005, PH3-007, PH3-008, PH3-009 |
| `TacticalEvaluator` | `src/ai_sim/tactics.py` | PH3-007 |
| `LLMClient` / `query_model_async` | `src/ai_sim/llm_bridge.py` | PH3-007, PH3-012 |
| `PlayerController` | `src/game/player_controller.py` | PH3-008 |
| `FactionRecord` / `DEFAULT_FACTIONS` | `src/world_sim/factions.py` | PH3-011 |
| `ProceduralArtifactGenerator` / `Artifact` | `src/rules_engine/mythos_forge.py` | PH3-012, PH3-013 |
| `Quest` / `QuestGenerator` / `QuestJournal` | `src/game/quest.py` | PH3-013 |
| `CampaignSession` | `src/game/campaign.py` | PH3-011, PH3-012, PH3-013 |

---

## 3. Task Tiers

### Tier 0 — Base Schemas & Configuration (No Dependencies)

| Task | Title | Subsystem | Requirement | blockedBy | Effort |
|------|-------|-----------|-------------|-----------|--------|
| PH3-001 | DungeonFloor Schema | dungeon-carver | New module `src/terrain/dungeon_carver.py`. Dataclass `DungeonFloor` (slots=True): `floor_index: int` (0 = first basement level, 1 = second, etc.), `z_offset: int` (negative Y in voxel space; `floor_index * FLOOR_DEPTH_VOXELS` where `FLOOR_DEPTH_VOXELS: int = 16`), `rooms: list[DungeonRoom]`, `hallways: list[DungeonHallway]`, `anchor_chunk_id: str`. Dataclass `DungeonRoom` (slots=True): `room_id: str`, `origin: tuple[int, int, int]` (voxel XYZ, Z is negative), `width: int`, `depth: int`, `height: int` (ceiling clearance in voxels, default 4). Dataclass `DungeonHallway` (slots=True): `hall_id: str`, `start_voxel: tuple[int, int, int]`, `end_voxel: tuple[int, int, int]`, `width: int` (default 2). Module-level constant `MAX_DUNGEON_FLOORS: int = 5`. All IDs are deterministic UUIDs derived from `anchor_chunk_id + floor_index + room_index` to guarantee cross-session reproducibility. **Target file:** `src/terrain/dungeon_carver.py`. **Deps:** `Chunk` (✅ `src/terrain/chunk.py`) | — | S |
| PH3-005 | PartyRecord Schema & ControlMode Enum | party-manager | New module `src/game/party_manager.py`. Enum `ControlMode` (values: `AUTONOMOUS`, `MANUAL`). Dataclass `CompanionSlot` (slots=True): `slot_index: int` (0–2; slot 0 is reserved for the human player's entity), `entity_id: str`, `character_id: str`, `control_mode: ControlMode` (default `ControlMode.AUTONOMOUS`). Dataclass `PartyRecord` (slots=True): `party_id: str`, `leader_entity_id: str` (the human player's `CombatEntity` id), `slots: list[CompanionSlot]` (max length 3 companions, enforced at insertion); a party therefore holds at most 4 combatants total (1 leader + 3 companions). Validation rule: `party_id` is a deterministic UUID of `leader_entity_id + world_seed`; adding a fifth member raises `PartyFullError(RuntimeError)`. **Target file:** `src/game/party_manager.py`. **Deps:** `CombatEntity` (✅ `src/rules_engine/combat.py`), `Character35e` (✅ `src/rules_engine/character_35e.py`) | — | S |
| PH3-010 | MythosThresholdRecord Schema | mythos-wire | Dataclass `MythosThresholdRecord` (slots=True): `record_id: str`, `faction_name: str \| None` (set if triggered by faction growth), `chunk_id: str \| None` (set if triggered by chunk danger level), `trigger_value: float` (the growth rate or danger score that crossed the threshold), `threshold_cutoff: float` (the configured ceiling; default `FACTION_GROWTH_THRESHOLD = 2.5` for factions, `CHUNK_DANGER_THRESHOLD = 8.0` for chunks), `triggered_at_tick: int`, `artifact_id: str \| None` (populated by PH3-012 after the forge runs). Module-level constants: `FACTION_GROWTH_THRESHOLD: float = 2.5` (ratio of hostile faction population vs. opposing faction population across shared chunks); `CHUNK_DANGER_THRESHOLD: float = 8.0` (sum of encounter-level ratings for all lairs in a single chunk, per `src/rules_engine/encounter.py`). **Target file:** `src/rules_engine/mythos_forge.py` (extend existing module). **Deps:** `ProceduralArtifactGenerator` (✅ `src/rules_engine/mythos_forge.py`), `FactionRecord` (✅ `src/world_sim/factions.py`) | — | S |

---

### Tier 1 — Core Mechanics (Depends on Tier 0)

| Task | Title | Subsystem | Requirement | blockedBy | Effort |
|------|-------|-----------|-------------|-----------|--------|
| PH3-002 | Multi-Floor Room & Hallway Carver | dungeon-carver | Function `carve_dungeon(chunk: Chunk, num_floors: int, anchor_chunk_id: str, anomaly: AnomalyRecord \| None, rng: random.Random) -> list[DungeonFloor]`; for each floor index `f` in `range(num_floors)`: compute `z_base = -(f + 1) * FLOOR_DEPTH_VOXELS`; place 2–6 `DungeonRoom` objects at randomised XY positions within the chunk's XZ footprint, constraining rooms to non-overlapping bounding boxes (collision check: AABB overlap test); connect rooms with rectilinear `DungeonHallway` segments (L-shaped corridors: horizontal segment first, then vertical); write `Material.AIR` to every voxel inside each room and hallway bounding box in `chunk.voxels`; line room walls and ceilings with `Material.STONE`; stamp a `Material.OBSIDIAN` floor at the lowest voxel row of each room; if `anomaly` is not `None` and `anomaly.chunk_id == anchor_chunk_id`, bias room placement beneath the anomaly's surface XZ coordinates (±4 voxels). Returns the list of `DungeonFloor` objects describing the carved layout. **Target file:** `src/terrain/dungeon_carver.py`. **Deps:** PH3-001, `Chunk` (✅), `Block`/`Material` (✅), `AnomalyRecord` (✅ `src/world_sim/anomaly.py`) | PH3-001 | M |
| PH3-006 | Party Formation API | party-manager | Function `create_party(leader_entity_id: str, world_seed: int) -> PartyRecord`; constructs an empty `PartyRecord` with the leader set and an empty `slots` list. Function `add_companion(party: PartyRecord, entity_id: str, character_id: str, control_mode: ControlMode = ControlMode.AUTONOMOUS) -> PartyRecord`; appends a `CompanionSlot` to `party.slots` or raises `PartyFullError` if `len(party.slots) >= 3`. Function `remove_companion(party: PartyRecord, entity_id: str) -> PartyRecord`; removes the slot whose `entity_id` matches, or raises `KeyError` if not found. Function `set_control_mode(party: PartyRecord, entity_id: str, mode: ControlMode) -> PartyRecord`; mutates the matching slot's `control_mode` field. All functions return the mutated `PartyRecord` (in-place mutation; the return is a convenience reference). **Target file:** `src/game/party_manager.py`. **Deps:** PH3-005 | PH3-005 | S |
| PH3-007 | Autonomous Companion Turn Router | party-manager | Function `route_autonomous_turn(slot: CompanionSlot, party: PartyRecord, encounter_entities: list[CombatEntity], character_registry: dict[str, Character35e], rng: random.Random, llm_client: LLMClient \| None = None) -> TacticalDecision \| None`; asserts `slot.control_mode == ControlMode.AUTONOMOUS` (raises `ValueError` otherwise); retrieves the companion's `Character35e` from `character_registry[slot.character_id]`; identifies hostile targets as all `CombatEntity` objects in `encounter_entities` whose faction is not in the companion's faction list (faction determined via `character.metadata.get("faction", None)`); constructs a `TacticalEvaluator` (from `src/ai_sim/tactics.py`) with the companion entity, character, visible hostiles, and equipped weapon; calls `evaluator.evaluate()` to obtain a `TacticalDecision`; if `llm_client` is provided, additionally calls `llm_client.query_model_async` with a compact gambit prompt (entity name, HP, AC, hostile count) to obtain a preferred spell or ability override and applies it if the response parses cleanly; returns the final `TacticalDecision` (or `None` if no valid targets). **Target file:** `src/game/party_manager.py`. **Deps:** PH3-005, PH3-006, `TacticalEvaluator` (✅ `src/ai_sim/tactics.py`), `LLMClient` (✅ `src/ai_sim/llm_bridge.py`), `CombatEntity` (✅), `Character35e` (✅) | PH3-005, PH3-006 | M |
| PH3-011 | Faction / Chunk Danger Evaluator | mythos-wire | Function `evaluate_mythos_threshold(faction_registry: dict[str, FactionRecord], population_ledger: PopulationLedger, chunk_danger_map: dict[str, float], current_tick: int) -> list[MythosThresholdRecord]`; scans all factions: for each pair of mutually hostile factions sharing at least one chunk (per `population_ledger`), compute `growth_ratio = hostile_population / opposing_population` (skip if opposing is 0); if `growth_ratio >= FACTION_GROWTH_THRESHOLD` and no existing `MythosThresholdRecord` covers this faction pair at the same tick, emit a `MythosThresholdRecord` with `faction_name = hostile_faction.name`; scans `chunk_danger_map` (keys = chunk IDs, values = summed encounter-level ratings from `src/rules_engine/encounter.py:calculate_el`): if any chunk's danger value `>= CHUNK_DANGER_THRESHOLD`, emit a `MythosThresholdRecord` with `chunk_id = chunk_id`; returns the list of newly triggered records (may be empty). `chunk_danger_map` is computed externally by summing `calculate_el` across all lairs in a chunk. **Target file:** `src/rules_engine/mythos_forge.py`. **Deps:** PH3-010, `FactionRecord` (✅), `PopulationLedger` (✅ `src/world_sim/population.py`), `calculate_el` (✅ `src/rules_engine/encounter.py`) | PH3-010 | M |

---

### Tier 2 — Spawners, Routers & Forge Triggers (Depends on Tier 1)

| Task | Title | Subsystem | Requirement | blockedBy | Effort |
|------|-------|-----------|-------------|-----------|--------|
| PH3-003 | Trap & Treasure Voxel Spawner | dungeon-carver | Dataclass `DungeonSpawnManifest` (slots=True): `floor_index: int`, `room_id: str`, `trap_voxels: dict[tuple[int, int, int], TrapBase]` (voxel coord → trap object), `treasure_voxels: dict[tuple[int, int, int], TreasureHoard]` (voxel coord → hoard). Function `populate_dungeon_floor(floor: DungeonFloor, party_level: int, rng: random.Random) -> DungeonSpawnManifest`; for each `DungeonRoom` in `floor.rooms`: roll a trap presence check (1-in-3 chance per room using SRD dungeon-dressing rules); if triggered, select a trap type via `generate_mechanical_trap(rng)` or `generate_magical_trap(rng)` (from `src/rules_engine/traps.py`) based on a 70/30 split; place the trap at a random non-doorway voxel within the room's floor plane; roll a treasure presence check (1-in-2 chance per room); if triggered, call `generate_treasure_hoard(cr=party_level, rng=rng)` (from `src/rules_engine/treasure.py`) and place the hoard at a room corner voxel; returns the `DungeonSpawnManifest` linking every spawned object to its exact voxel coordinate. The manifest is the sole lookup table the game loop uses to resolve trap triggers and loot interactions — no scanning of the voxel grid is required at runtime. **Target file:** `src/terrain/dungeon_carver.py`. **Deps:** PH3-002, `TrapBase`/`MechanicalTrap`/`MagicalTrap`/`generate_mechanical_trap`/`generate_magical_trap` (✅ `src/rules_engine/traps.py`), `TreasureHoard`/`generate_treasure_hoard` (✅ `src/rules_engine/treasure.py`) | PH3-002 | M |
| PH3-008 | Manual Companion Turn Router | party-manager | Function `route_manual_turn(slot: CompanionSlot, controller: PlayerController, combat_registry: dict[str, CombatEntity]) -> PlayerAction`; asserts `slot.control_mode == ControlMode.MANUAL` (raises `ValueError` otherwise); re-uses `PlayerController.dispatch_player_input` semantics but targets the companion's `CombatEntity` instead of the leader's; the Textual UI must display a secondary command prompt labelled `"[{companion_name}] >"` when a manual companion's turn is active, blocking the leader's input until the companion's action is submitted; accepted commands mirror the existing `PlayerAction` enum (N/S/E/W/U/D/Wait/Interact) plus two combat-specific extensions: `Attack` (targets nearest hostile by voxel distance) and `Cast` (opens a spell selection sub-menu listing prepared spells from `Character35e.spellcasting`); the function returns the resolved `PlayerAction` for logging in the turn controller. **Target file:** `src/game/party_manager.py`. **Deps:** PH3-005, PH3-006, `PlayerController`/`PlayerAction`/`dispatch_player_input` (✅ `src/game/player_controller.py`), `CombatEntity` (✅) | PH3-005, PH3-006 | M |
| PH3-009 | Party Combat Round Dispatcher | party-manager | Function `dispatch_party_round(party: PartyRecord, encounter_entities: list[CombatEntity], character_registry: dict[str, Character35e], controller: PlayerController, rng: random.Random, llm_client: LLMClient \| None = None) -> list[TacticalDecision \| PlayerAction]`; iterates `party.slots` in initiative order (using each entity's initiative score from `character_registry`); for each slot: if `slot.control_mode == ControlMode.AUTONOMOUS` call `route_autonomous_turn` (PH3-007); if `slot.control_mode == ControlMode.MANUAL` call `route_manual_turn` (PH3-008); prepend the leader's action (always manual, resolved via `controller`) to the result list; returns the ordered list of decisions/actions for the turn controller to execute sequentially. The dispatcher does not apply damage or movement — it only resolves intent; the existing `AttackResolver` and `dispatch_player_input` apply the physical consequences. **Target file:** `src/game/party_manager.py`. **Deps:** PH3-007, PH3-008, `simulate_round_with_links` (✅ `src/ai_sim/master_minion.py`) for optional familiar/linked-entity propagation | PH3-007, PH3-008 | M |
| PH3-012 | Forge Trigger → Artifact Generator | mythos-wire | Async function `trigger_forge_on_threshold(threshold: MythosThresholdRecord, forge: ProceduralArtifactGenerator, campaign: CampaignSession, rng: random.Random) -> Artifact`; receives a `MythosThresholdRecord` that crossed the cutoff; determines artifact tier: if `threshold.trigger_value / threshold.threshold_cutoff >= 2.0` → `"major"`; else → `"standard"`; calls `forge.generate_artifact(tier=tier)` (async, awaited) to produce a named `Artifact` with DMG-pricing and LLM-generated lore; persists the artifact via `forge`'s existing `data/generated_artifacts.json` store; writes `threshold.artifact_id = artifact.artifact_id` (mutates the record in-place); emits a structured log entry via Python `logging` at level `WARNING`: `"MYTHOS FORGE: {faction_or_chunk} breached threshold. Artifact forged: {artifact.lore_name} ({artifact.artifact_id})"`. Returns the `Artifact` for immediate handoff to PH3-013. **Target file:** `src/rules_engine/mythos_forge.py`. **Deps:** PH3-011, `ProceduralArtifactGenerator`/`Artifact` (✅ `src/rules_engine/mythos_forge.py`), `CampaignSession` (✅ `src/game/campaign.py`) | PH3-011 | M |

---

### Tier 3 — Integration Hooks (Depends on Tier 2)

| Task | Title | Subsystem | Requirement | blockedBy | Effort |
|------|-------|-----------|-------------|-----------|--------|
| PH3-004 | ChunkGenerator Negative-Z Integration Hook | dungeon-carver | Extend `ChunkGenerator.generate_chunk` to accept an optional parameter `dungeon_floors: list[DungeonFloor] \| None = None`; if provided, after the standard surface generation loop, call `_apply_dungeon_floors(chunk, dungeon_floors)` which iterates each `DungeonFloor` and each `DungeonRoom`/`DungeonHallway` within it, zeroing out the corresponding voxels (setting `Material.AIR`) in `chunk.voxels` at the correct negative-Z offset; add a complementary factory function `ChunkGenerator.generate_chunk_with_dungeon(cx: int, cz: int, num_floors: int, anomaly: AnomalyRecord \| None, rng: random.Random) -> tuple[Chunk, list[DungeonFloor], list[DungeonSpawnManifest]]` that: (1) calls `generate_chunk` for surface terrain; (2) calls `carve_dungeon` (PH3-002) to produce floors; (3) calls `populate_dungeon_floor` (PH3-003) for each floor; (4) calls `_apply_dungeon_floors` to write the carve into the chunk; (5) returns all three artifacts as a tuple. This is the single public API surface the `ChunkManager` calls when loading a chunk that qualifies for dungeon generation (qualifier: `anomaly is not None and anomaly.current_biome in RUIN_BIOMES` where `RUIN_BIOMES = {Biome.RUIN, Biome.UNDERDARK}`). **Target file:** `src/terrain/chunk_generator.py` (extend) and `src/terrain/dungeon_carver.py`. **Deps:** PH3-003, `ChunkGenerator` (✅), `AnomalyRecord` (✅), `Biome` (✅ `src/world_sim/biome.py`) | PH3-003 | L |
| PH3-013 | Artifact Quest Objective Injector | mythos-wire | Function `inject_artifact_quest(artifact: Artifact, threshold: MythosThresholdRecord, journal: QuestJournal, world_seed: int) -> Quest`; constructs a new `Quest` object (using `QuestGenerator`'s existing dataclass schema from `src/game/quest.py`) with: `quest_id` = deterministic UUID of `artifact.artifact_id + world_seed`; `title` = `"Retrieve the {artifact.lore_name}"`; `description` = the artifact's LLM-generated lore excerpt (first 280 characters of `artifact.lore_text`) suffixed with the triggering context (e.g. `"The {faction_name} has grown beyond reckoning — only this relic can turn the tide."`); `objective` = `f"Locate and recover artifact {artifact.artifact_id} from the world."`; `reward_gp` = `int(artifact.properties.calculated_price_gp * 0.1)` (10 % of artifact market value, as a finder's fee); `status` = `QuestStatus.ACTIVE`; adds the quest to `journal` via `journal.add(quest)`; wires the quest into the active `CampaignSession` by appending it to `campaign.quest_journal` (the campaign exposes its `QuestJournal` as a public attribute). Returns the created `Quest`. This task completes the Mythos feedback loop: threshold breach → forge artifact → live quest objective. **Target file:** `src/game/quest.py` (extend) and `src/rules_engine/mythos_forge.py`. **Deps:** PH3-012, `Quest`/`QuestJournal`/`QuestStatus` (✅ `src/game/quest.py`), `CampaignSession` (✅ `src/game/campaign.py`) | PH3-012 | S |

---

## 4. Effort Summary

| Tier | Task Count | S Tasks | M Tasks | L Tasks | Estimated Total |
|------|-----------|---------|---------|---------|-----------------|
| 0 — Base Schemas | 3 | 3 | 0 | 0 | ~1.5 days |
| 1 — Core Mechanics | 4 | 1 | 3 | 0 | ~5 days |
| 2 — Spawners & Routers | 4 | 0 | 4 | 0 | ~7 days |
| 3 — Integration Hooks | 2 | 1 | 0 | 1 | ~4 days |
| **Total** | **13** | **5** | **7** | **1** | **~17.5 dev-days** |

> Subsystem A Tier 0–1 (PH3-001–PH3-002), Subsystem B Tier 0–1 (PH3-005–PH3-007),
> and Subsystem C Tier 0–1 (PH3-010–PH3-011) are fully independent and may be
> started in parallel from day one.
> PH3-004 (ChunkGenerator negative-Z integration) is the sole L-effort task and
> is the last to complete in Subsystem A — it depends on both the carver (PH3-002)
> and the spawner (PH3-003) being stable.
> PH3-013 (Artifact quest injector) closes the Mythos feedback loop and should be
> the final task merged, as it depends on both PH3-012 (forge trigger) and the
> stable `QuestJournal` / `CampaignSession` contracts from Phase 2.
