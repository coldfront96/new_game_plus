# LIVING_WORLD_MM_BUILD_SITE.md — Persistent Ecology & Monster Manual Build Plan

## 1. Scope

This document is the authoritative project-management plan for three
interdependent subsystems that together form the **Living World** layer of
New Game Plus:

| # | Subsystem | Short Name | New Modules |
|---|-----------|------------|-------------|
| A | Persistent Ecology & Population Engine | World Sim | `src/world_sim/population.py`, `src/world_sim/biome.py`, `src/world_sim/migration.py`, `src/world_sim/anomaly.py`, `src/world_sim/world_tick.py` |
| B | Universal Monster Rules Engine | MM Physics | `src/rules_engine/mm_passive.py`, `src/rules_engine/mm_grapple.py`, `src/rules_engine/mm_immortal.py`, `src/rules_engine/mm_metaphysical.py` |
| C | Monster Manual Data Ingestion Pipeline | MM Ingest | `data/srd_3.5/monsters/` JSON files, `scripts/migrate_v1_to_v2.py` |

**Already shipped (out of scope here):**

| Module | File | Status |
|--------|------|--------|
| LLM Bridge (async inference client) | `src/ai_sim/llm_bridge.py` | ✅ Shipped |
| Combat Engine & Conditions | `src/rules_engine/combat.py`, `src/rules_engine/conditions.py` | ✅ Shipped |
| Character Sheet (3.5e) | `src/rules_engine/character_35e.py` | ✅ Shipped |
| Spell Resolution | `src/rules_engine/spellcasting.py`, `src/rules_engine/magic.py` | ✅ Shipped |
| Planar Physics | `src/rules_engine/planar.py` | ✅ Shipped |
| Feats Engine | `src/rules_engine/feat_engine.py` | ✅ Shipped |
| Monster JSON stubs (name + cr only) | `data/srd_3.5/monsters/core.json` (67 entries) | ✅ Partial — schema upgrade required |

---

## 1a. Dependency Map

The three subsystems have a strict build order. Nothing in MM Physics or MM
Ingest can be integrated until the Ecology foundation schemas exist.

```
Tier 0  ──────────────────────────────────────────────────────────────────
         [LW-001..LW-006]  Ecology base schemas
         [LW-007..LW-010]  MM Physics base schemas
         [LW-011]          JSON schema v2 addendum spec
                │
Tier 1  ────────▼─────────────────────────────────────────────────────────
         [LW-012..LW-016]  Population init, biome gate, anomaly roll
         [LW-017..LW-020]  Passive lethality, grapple init, heal tick, SR pre-roll
                │
Tier 2  ────────▼─────────────────────────────────────────────────────────
         [LW-021..LW-025]  Migration graph, pressure calc, vector gen/apply, LLM hook
         [LW-026..LW-028]  Gaze resolution, constrict/swallow, DR engine
         [LW-029..LW-030]  JSON schema validator, regen weakness suppression
                │
Tier 3  ────────▼─────────────────────────────────────────────────────────
         [LW-031..LW-032]  Aura processor, grapple escape logic
         [LW-033..LW-034]  Healing precedence, SR interaction rules
         [LW-035..LW-036]  Extinction broadcaster, world tick orchestrator
                │
Tier 4  ────────▼─────────────────────────────────────────────────────────
         [LW-037]          JSON v2 migration script
         [LW-038..LW-042]  SRD ingest batches A–C, D–G, H–L, M–R, S–Z
                │
Tier 5  ────────▼─────────────────────────────────────────────────────────
         [LW-043..LW-044]  Spawn director integration, combat engine wiring
         [LW-045..LW-046]  Coherence validation, regression test suite
```

**External dependencies this document leans on (must remain stable):**

| Dependency | File | Used By |
|------------|------|---------|
| `LLMClient.query_model_async` | `src/ai_sim/llm_bridge.py` | LW-025 Anomaly Lore Hook |
| `CombatEntity` dataclass | `src/rules_engine/combat.py` | LW-017, LW-018, LW-019, LW-020 |
| `Character35e` dataclass | `src/rules_engine/character_35e.py` | LW-027, LW-034 |
| `SpellRecord` & `SpellSchool` | `src/rules_engine/spellcasting.py` | LW-034 |
| `DamageType` enum | `src/rules_engine/combat.py` | LW-028, LW-030 |
| `SaveType` enum | `src/rules_engine/conditions.py` | LW-007, LW-017 |
| `SizeCategory` enum | `src/rules_engine/character_35e.py` | LW-018, LW-027 |
| `EventBus` | `src/core/` | LW-035 Extinction Broadcaster |

**Format conventions (matching existing build docs):**

- Task IDs are prefixed `LW-` (Living World).
- `Effort` ∈ {S = ≤½ day, M = 1–2 days, L = 3+ days}.
- `blockedBy` references resolve to an earlier `LW-` task or a shipped module marked ✅.
- All new schemas use `dataclasses` with `slots=True`; all enums are `enum.Enum` subclasses.

---

## 2. Task Tiers

### Tier 0 — Base Schemas & Enums (No Dependencies)

| Task | Title | Subsystem | Requirement | blockedBy | Effort |
|------|-------|-----------|-------------|-----------|--------|
| LW-001 | Species Population Record Schema | ecology-pop | Dataclass `SpeciesPopRecord` (slots=True): `species_id: str`, `global_count: int`, `local_counts: dict[str, int]` (chunk_id → count), `is_extinct: bool`; a species whose `global_count` reaches 0 is immediately flagged `is_extinct = True`; no respawn logic exists — extinction is permanent and the record becomes read-only | — | S |
| LW-002 | Biome Enum | ecology-biome | Enum `Biome` covering all 3.5e biomes: Cold/Temperate/Warm × Forest/Hill/Plain/Desert/Aquatic/Swamp/Mountain + special entries `Underground`, `Underdark`, `Arctic`, `Any_Urban`, `Any_Ruin`, `Astral`, `Ethereal`, `Positive_Energy`, `Negative_Energy`, `Elemental_Air`, `Elemental_Earth`, `Elemental_Fire`, `Elemental_Water`, `Outer_Plane`; sentinel value `Any` for non-biome-restricted creatures | — | S |
| LW-003 | Species Biome Binding Schema | ecology-biome | Dataclass `SpeciesBiomeBinding` (slots=True): `species_id: str`, `primary_biomes: tuple[Biome, ...]`, `tolerated_biomes: tuple[Biome, ...]`, `forbidden_biomes: tuple[Biome, ...]`; if a world instance contains no chunk whose `biome` is in `primary_biomes`, the species' `global_count` is set to 0 at world-generation time; tolerated biomes allow survival but halve birth rate | — | S |
| LW-004 | World Chunk Schema | ecology-pop | Dataclass `WorldChunk` (slots=True): `chunk_id: str`, `biome: Biome`, `adjacent_chunks: tuple[str, ...]`, `local_populations: dict[str, int]` (species_id → count), `carrying_capacity: dict[str, int]` (species_id → max sustainable); dataclass `WorldGenerationSeed` (slots=True): `seed: int`, `biome_distribution: dict[Biome, float]` (fraction of total chunks assigned per biome, must sum to 1.0) | — | S |
| LW-005 | Migration Vector Schema | ecology-migration | Dataclass `MigrationVector` (slots=True): `species_id: str`, `source_chunk_id: str`, `target_chunk_id: str`, `migrating_count: int`, `scheduled_tick: int`, `cause: MigrationCause`; enum `MigrationCause` (PopulationPressure / BiomeRestored / PredatorFlight / DroughtFamine / AnomalyFlight); vectors are immutable once created — cancel by filtering, never mutating | — | S |
| LW-006 | Anomaly Placement Record Schema | ecology-lore | Dataclass `AnomalyRecord` (slots=True): `anomaly_id: str`, `entity_id: str`, `species_id: str`, `chunk_id: str`, `native_biome: Biome`, `current_biome: Biome`, `anomaly_roll: float`, `world_tick: int`, `lore_text: str \| None`; `lore_text` is `None` until the LLMBridge async call resolves; record is persisted to world-state store immediately on creation so the anomaly is tracked even before lore is generated | — | S |
| LW-007 | Gaze / Aura Passive Effect Schema | mm-passive | Dataclass `PassiveEffect` (slots=True): `effect_type: PassiveEffectType`, `range_ft: int`, `save_type: SaveType \| None`, `save_dc: int`, `effect_on_fail: str`, `effect_on_pass: str \| None`, `suppress_conditions: tuple[str, ...]` (condition names that negate this effect); enum `PassiveEffectType` (Gaze / Aura / Frightful_Presence / Stench / Spores / Death_Throes); Gaze requires line-of-sight; Aura is omnidirectional within range | — | S |
| LW-008 | Grapple State Schema | mm-grapple | Dataclass `GrappleState` (slots=True): `grapple_id: str`, `grappler_id: str`, `grappled_id: str`, `initiated_tick: int`, `swallow_depth: int` (0 = not swallowed, 1 = inside stomach), `constrict_damage_dice: str \| None`, `improved_grab_active: bool`, `pin_active: bool`; enum `GrappleOutcome` (Grappled / Pinned / Swallowed / Escaped / GrapplerDead); `GrappleState` is nullified on any `Escaped` or `GrapplerDead` outcome | — | S |
| LW-009 | Regeneration & Fast Healing Tracker Schema | mm-immortal | Dataclass `RegenerationRecord` (slots=True): `entity_id: str`, `regen_hp_per_round: int`, `fast_heal_hp_per_round: int`, `elemental_weaknesses: tuple[str, ...]` (DamageType names), `alignment_weaknesses: tuple[str, ...]` (e.g. `"Good"`, `"Evil"`, `"Silver"`), `suppressed_until_tick: int`; Regeneration is suppressed for the full round in which a listed weakness damage type is received; Fast Healing is never suppressed and does not interact with weaknesses | — | S |
| LW-010 | Damage Reduction & Spell Resistance Schema | mm-metaphysical | Dataclass `DRRecord` (slots=True): `entity_id: str`, `dr_amount: int`, `bypass_conjunction: DRConjunction`, `bypass_materials: tuple[str, ...]`; enum `DRConjunction` (And / Or) — And requires ALL listed materials simultaneously (e.g. `10/Cold Iron and Magic`), Or requires any single material; dataclass `SRRecord` (slots=True): `entity_id: str`, `sr_value: int`, `voluntarily_suppressed: bool`; both records are keyed per-entity in module-level registries | — | S |
| LW-011 | Monster JSON Schema v2 Addendum | data-schema | Specification of four new required fields added to every SRD monster JSON entry: `population_base: int` (world-generation starting count; 0 = unique singleton, never auto-spawned); `allowed_biomes: list[str]` (each string must resolve to a `Biome` enum name or the sentinel `"Any"`); `primary_biome: str` (dominant biome, must also appear in `allowed_biomes`); `ecology_notes: str \| None` (free-text field passed verbatim to the LLM in anomaly lore prompts); all existing v1 fields remain unchanged and backward-compatible | — | S |

---

### Tier 1 — Core Mechanics (Depends on Tier 0)

| Task | Title | Subsystem | Requirement | blockedBy | Effort |
|------|-------|-----------|-------------|-----------|--------|
| LW-012 | Global Population Initializer | ecology-pop | Function `initialize_world_populations(world_chunks: list[WorldChunk], species_registry: dict[str, SpeciesBiomeBinding], seed: WorldGenerationSeed) -> dict[str, SpeciesPopRecord]`; distributes each species' `population_base` across biome-matching chunks proportionally to chunk count; species with zero matching primary-biome chunks receive `global_count = 0, is_extinct = True` immediately; writes result to a `PopulationLedger` (module-level `dict[str, SpeciesPopRecord]`); logs each zeroed species to a DM-readable init report | LW-001, LW-004 | M |
| LW-013 | Biome Strictness Check | ecology-biome | Function `apply_biome_strictness(binding: SpeciesBiomeBinding, world_biomes: set[Biome]) -> bool`; returns `True` if the intersection of `binding.primary_biomes` and `world_biomes` is non-empty; returns `False` (triggering a population zero-out in the `PopulationLedger`) otherwise; runs once at world-generation time before any other spawn logic; result is cached per species per world instance | LW-002, LW-003 | S |
| LW-014 | Local Population Delta Application | ecology-pop | Function `apply_population_delta(ledger: PopulationLedger, species_id: str, chunk_id: str, delta: int) -> SpeciesPopRecord`; adds `delta` (positive = birth/migration in, negative = kill/migration out) to `local_counts[chunk_id]`; clamps result to ≥ 0; recalculates `global_count` as the sum of all local counts; if `global_count` reaches 0, sets `is_extinct = True` permanently — this transition is a one-way gate with no undo path; raises `SpeciesExtinctError` if called on an already-extinct species | LW-012 | S |
| LW-015 | Spawn Director Biome Gate | ecology-biome | Function `can_spawn_in_chunk(species_id: str, chunk: WorldChunk, ledger: PopulationLedger, bindings: dict[str, SpeciesBiomeBinding]) -> bool`; returns `False` on any of: species is extinct; chunk biome not in species `primary_biomes + tolerated_biomes`; chunk biome is in `forbidden_biomes`; local population for species in this chunk is already at carrying capacity; this is the **single authoritative entry point** for all spawn decisions — no other code may bypass it | LW-013, LW-014 | S |
| LW-016 | Anomaly Roll Resolver | ecology-lore | Function `resolve_anomaly_roll(rng, binding: SpeciesBiomeBinding, chunk: WorldChunk, threshold: float = 0.005) -> AnomalyRecord \| None`; draws a float in [0, 1); if result < threshold AND chunk.biome not in species `primary_biomes + tolerated_biomes`, creates and returns an `AnomalyRecord` (lore_text=None); anomaly spawn bypasses `can_spawn_in_chunk` exactly once; the normal gate result is irrelevant for anomaly placements; `threshold` is configurable per world-generation settings | LW-006, LW-015 | M |
| LW-017 | Passive Lethality Evaluator | mm-passive | Function `evaluate_passive_effects(source: CombatEntity, observers: list[CombatEntity], tick: int) -> list[EffectApplication]`; iterates all `PassiveEffect` entries on `source`; for each: performs range check (Euclidean distance ≤ `range_ft / 5` in voxels); for Gaze effects enforces line-of-sight check and observer gaze-aversion state; rolls saving throw if `save_type` is not None; records outcome in `EffectApplication` dataclass (`target_id`, `effect_type`, `saved: bool`, `tick`); returns complete list for combat-log consumption | LW-007 | M |
| LW-018 | Improved Grab Initiator | mm-grapple | Function `attempt_improved_grab(attacker: CombatEntity, target: CombatEntity, hit_confirmed: bool, tick: int) -> GrappleState \| None`; only fires if `attacker` has the Improved Grab feat and `hit_confirmed` is True on a natural attack; initiates opposed grapple check: `1d20 + BAB + STR_mod + size_mod` (attacker) vs `1d20 + BAB + STR_mod + size_mod` (target); on attacker win, creates and returns a `GrappleState`; does NOT provoke an attack of opportunity from the target (core Improved Grab rule); on failure returns `None` | LW-008 | M |
| LW-019 | Fast Healing Tick Processor | mm-immortal | Function `process_healing_tick(entity: CombatEntity, record: RegenerationRecord, damage_log: DamageLog, tick: int) -> int`; Fast Healing path: adds `fast_heal_hp_per_round` unconditionally, capped at entity max HP; does not restore missing limbs or ability damage; Regeneration path: checks `damage_log` for the current round — if any entry's `damage_type` name appears in `record.elemental_weaknesses` or `record.alignment_weaknesses`, sets `record.suppressed_until_tick = tick + 1` and skips regen; otherwise restores `regen_hp_per_round`; returns net HP restored this tick | LW-009 | M |
| LW-020 | Spell Resistance Pre-Roll | mm-metaphysical | Function `check_spell_resistance(caster: CombatEntity, target: CombatEntity, sr_record: SRRecord) -> SRResult`; dataclass `SRResult` (slots=True): `penetrated: bool`, `roll: int`, `caster_level: int`, `sr_value: int`; if `sr_record.voluntarily_suppressed` is True, sets `penetrated = True` without rolling; otherwise rolls `1d20 + caster.caster_level` and compares to `sr_record.sr_value`; result is appended to the combat audit trail before any spell effect is applied | LW-010 | S |

---

### Tier 2 — Registries & Intermediate Generators (Depends on Tier 1)

| Task | Title | Subsystem | Requirement | blockedBy | Effort |
|------|-------|-----------|-------------|-----------|--------|
| LW-021 | Chunk Adjacency Graph | ecology-migration | Class `ChunkAdjacencyGraph`; built from `WorldChunk.adjacent_chunks` tuples at world-load time; exposes `get_neighbors(chunk_id: str) -> list[WorldChunk]` and `biome_reachable_in_steps(chunk_id: str, target_biome: Biome, max_steps: int) -> list[str]` (BFS up to `max_steps`); used by the migration engine to find valid destination chunks without traversing the full world graph at every tick | LW-004, LW-005 | M |
| LW-022 | Migration Pressure Calculator | ecology-migration | Function `calculate_migration_pressure(species_id: str, chunk: WorldChunk, ledger: PopulationLedger) -> float`; computes `local_count / carrying_capacity` ratio; pressure > 1.0 indicates overpopulation and triggers outward migration; pressure < 0.2 in an adjacent compatible chunk indicates underpopulation and pulls inward migration; returns a signed float (positive = push from this chunk, negative = pull toward this chunk); used as the sole criterion by the vector generator | LW-014, LW-021 | M |
| LW-023 | Migration Vector Generator | ecology-migration | Function `generate_migration_vectors(species_id: str, world: list[WorldChunk], ledger: PopulationLedger, current_tick: int, rng) -> list[MigrationVector]`; for each chunk where pressure > 1.0: selects the lowest-pressure adjacent chunk whose biome is in species `primary_biomes + tolerated_biomes`; sets `migrating_count = ceil(pressure_excess * 0.1 * local_pop)`; schedules vector `1d4` ticks forward; skips species if `is_extinct`; returns all generated vectors for this tick without applying them | LW-022 | M |
| LW-024 | Migration Vector Applier | ecology-migration | Function `apply_migration_vectors(vectors: list[MigrationVector], ledger: PopulationLedger, current_tick: int) -> PopulationLedger`; filters to vectors whose `scheduled_tick <= current_tick`; for each: verifies source chunk still has sufficient population (skip silently if source count dropped below `migrating_count` since vector was created); calls `apply_population_delta(ledger, species_id, source_chunk_id, -migrating_count)` then `apply_population_delta(ledger, species_id, target_chunk_id, +migrating_count)`; logs each completed migration event | LW-014, LW-023 | S |
| LW-025 | LLMBridge Anomaly Lore Hook | ecology-lore | Async function `request_anomaly_lore(anomaly: AnomalyRecord, llm_client: LLMClient, species_notes: str \| None) -> AnomalyRecord`; builds a prompt containing: species name, native biome, current biome, world seed, current world tick, and any `ecology_notes` from the monster's JSON entry; dispatches to `LLMClient.query_model_async(system_prompt, prompt)`; on completion writes the response string to `anomaly.lore_text` and persists the updated record to the world-state store; fires-and-forgets from the main simulation thread — world tick and combat continue unblocked while lore generates | LW-006, LW-016 | M |
| LW-026 | Gaze Attack Full Resolver | mm-passive | Function `resolve_gaze_attack(gazer: CombatEntity, target: CombatEntity, effect: PassiveEffect, aversion_state: GazeAversionState, tick: int) -> EffectApplication`; enum `GazeAversionState` (Looking / Averting / ClosedEyes / Mirror); Looking: target must save each round; Averting: 50% chance each round the gaze misses entirely, target takes −2 penalty to attacks on gazer; ClosedEyes: target immune to gaze but gains 50% miss chance on all attacks; Mirror: gazer must save against own gaze (SR does not apply to self-reflection); result feeds into `evaluate_passive_effects` pipeline | LW-017 | M |
| LW-027 | Constrict & Swallow Whole Processor | mm-grapple | Function `process_grapple_round(state: GrappleState, attacker: CombatEntity, target: CombatEntity, tick: int) -> GrappleState`; each round of maintained grapple: rolls to maintain (opposed grapple check); on success if `constrict_damage_dice` is set, auto-deals constrict damage (no attack roll needed); Swallow Whole attempt: if `state.pin_active` and attacker size ≥ Large and target is at least 2 size categories smaller, may attempt swallow — sets `swallow_depth = 1` on success; swallowed target takes per-round acid + bludgeoning damage per SRD; escape path: deal damage equal to ¼ swallower's max HP from inside | LW-018 | L |
| LW-028 | DR Resolution Engine | mm-metaphysical | Function `apply_damage_reduction(raw_damage: int, weapon_properties: tuple[str, ...], dr_record: DRRecord) -> int`; `weapon_properties` is a tuple of material/alignment/enhancement strings present on the attacking weapon (e.g. `("Silver", "Magic", "+3")`); And-conjunction: all entries in `dr_record.bypass_materials` must appear in `weapon_properties` to bypass; Or-conjunction: any single match is sufficient; spell damage with descriptor `"no_physical_component"` bypasses DR entirely regardless of conjunction; returns post-DR damage, minimum 0; pure energy damage (fire, cold, acid, etc.) also bypasses DR | LW-010 | M |
| LW-029 | Monster JSON Schema v2 Validator | data-schema | Pydantic model `MonsterSchemaV2` extending the existing v1 model; validates: `population_base: int` (≥ 0); `allowed_biomes: list[str]` (each element must resolve to a valid `Biome` enum name or the string `"Any"`); `primary_biome: str` (must also appear in `allowed_biomes`); `ecology_notes: str \| None`; migration utility `validate_all_monsters(data_dir: Path) -> ValidationReport` scans all JSON files under `data/srd_3.5/monsters/` and reports per-entry pass/fail; `ValidationReport` dataclass: `total: int`, `passed: int`, `failed: list[tuple[str, str]]` (filename, error message) | LW-011 | M |
| LW-030 | Regeneration Weakness Suppression | mm-immortal | Function `apply_regeneration_weakness_check(record: RegenerationRecord, damage_event: DamageEvent, tick: int) -> RegenerationRecord`; `DamageEvent` dataclass: `damage_type: str`, `amount: int`, `tick: int`; if `damage_event.damage_type` matches any entry in `record.elemental_weaknesses` or `record.alignment_weaknesses`: sets `record.suppressed_until_tick = tick + 1`; critically, lethal damage from a weakness source is **not** converted to nonlethal (unlike normal Regeneration behavior) and is applied directly to the HP pool; logs the suppression event to the combat audit trail | LW-019 | S |

---

### Tier 3 — Advanced Physics & Orchestration (Depends on Tier 2)

| Task | Title | Subsystem | Requirement | blockedBy | Effort |
|------|-------|-----------|-------------|-----------|--------|
| LW-031 | Aura Passive Effect Processor | mm-passive | Function `process_aura_effects(source: CombatEntity, combat_state: CombatState, tick: int) -> list[EffectApplication]`; handles distinct sub-types: **Frightful Presence** — Will save DC = `10 + ½ source.HD + CHA_mod`; fail = Shaken if target HD ≤ source HD, Panicked if target HD < ½ source HD; immunity granted after one successful save vs same creature per encounter; **Stench** — Fort save; fail = Sickened for 10 rounds; **Positive/Negative Energy Aura** — affects undead or living in range respectively; does not double-apply to a target that already received the same effect this tick from `evaluate_passive_effects` (tick-stamp deduplication) | LW-026 | M |
| LW-032 | Complex Grapple Escape Logic | mm-grapple | Function `attempt_escape_grapple(state: GrappleState, escapee: CombatEntity, method: EscapeMethod, tick: int) -> GrappleOutcome`; enum `EscapeMethod` (Grapple_Check / Escape_Artist / Teleport / Dimensional_Shift); Grapple_Check: opposed `1d20 + grapple_bonus` check; Escape_Artist: escapee's Escape Artist skill rank + DEX_mod vs grappler's grapple bonus; Teleport / Dimensional_Shift: automatic escape, costs a standard action, removes `GrappleState` entirely; while `swallow_depth == 1`: only internal damage route (see LW-027) or Teleport/Dimensional_Shift are valid — Grapple_Check and Escape_Artist cannot be used from inside a swallower; returns nullified `GrappleState` on any successful escape | LW-027 | M |
| LW-033 | Fast Healing vs Regeneration Precedence Resolver | mm-immortal | Function `resolve_healing_precedence(entity: CombatEntity, record: RegenerationRecord, tick: int) -> HealingResult`; dataclass `HealingResult` (slots=True): `hp_restored: int`, `source: HealingSource`, `regen_was_suppressed: bool`; enum `HealingSource` (Regeneration / FastHealing / Both — Both is invalid per RAW); per 3.5e rules, Regeneration supersedes Fast Healing on the same entity — they do not stack; if `record.suppressed_until_tick > tick` (Regeneration suppressed this round), Fast Healing activates instead and `regen_was_suppressed = True`; if both regen and fast heal are present and regen is active, only regen fires; result logged to combat audit trail | LW-019, LW-030 | S |
| LW-034 | Spell Resistance Interaction Rules | mm-metaphysical | Function `apply_sr_interaction_rules(spell: SpellRecord, caster: CombatEntity, target: CombatEntity, sr_record: SRRecord) -> SRResult`; extends LW-020 with the full 3.5e SR exception table: SR does **not** apply to spells with the `SR: No` tag; SR does not apply to supernatural abilities (non-spell effects); SR does not apply to natural breath weapons; area spells check SR individually per target in the area; harmless spells still check SR if the target is hostile and did not voluntarily lower SR; touch spells check SR at the moment of contact, not at cast time; SR does not protect against `[Force]` descriptor spells that explicitly state they bypass SR; returns amended `SRResult` with `exception_applied: str \| None` field | LW-020, LW-028 | M |
| LW-035 | Biome Extinction Event Broadcaster | ecology-pop | Function `broadcast_extinction(species_id: str, ledger: PopulationLedger, event_bus: EventBus, tick: int) -> ExtinctionEvent`; fired exactly once when `SpeciesPopRecord.global_count` transitions to 0; dataclass `ExtinctionEvent` (slots=True): `species_id: str`, `last_known_chunk: str`, `world_tick: int`, `cause: ExtinctionCause`; enum `ExtinctionCause` (PlayerKills / MigrationCollapse / BiomeLoss / StarvationCycle / WorldGenZeroed); event is **idempotent** — publishing a second extinction event for the same species_id raises `AlreadyExtinctError`; once fired, the species_id is locked out of `apply_population_delta` entirely | LW-014 | S |
| LW-036 | World Tick Orchestrator | ecology-pop | Function `run_world_tick(world_state: WorldState, tick: int, rng, llm_client: LLMClient) -> WorldState`; canonical sequence for each world tick: (1) process births via biome-capacity birth-rate formula for each non-extinct species; (2) call `generate_migration_vectors` for all species; (3) call `apply_migration_vectors` for all due vectors; (4) check all species for `global_count == 0` — call `broadcast_extinction` for any newly zeroed; (5) for each spawn event this tick, call `resolve_anomaly_roll` — if an `AnomalyRecord` is returned, fire `request_anomaly_lore` as a non-blocking async task; returns updated `WorldState`; must complete steps 1–4 synchronously before returning | LW-024, LW-025, LW-035 | L |

---

### Tier 4 — Data Ingestion Batches (Depends on Tier 2 schema validator)

> Each batch is independent of the others and may be worked in parallel once LW-037 is complete.
> Batching by alphabetic range prevents token-truncation during ingestion sessions.

| Task | Title | Subsystem | Requirement | blockedBy | Effort |
|------|-------|-----------|-------------|-----------|--------|
| LW-037 | JSON v2 Migration Script | data-schema | Script `scripts/migrate_v1_to_v2.py`; reads all JSON files under `data/srd_3.5/monsters/`; for each monster entry missing any v2 field: inserts `population_base: 100`, `allowed_biomes: ["Any"]`, `primary_biome: "Any"`, `ecology_notes: null` as safe defaults; validates every modified entry against `MonsterSchemaV2`; supports `--dry-run` flag (prints unified diff without writing); writes `data/migration_v2_report.json` listing every modified entry, its old keys, and its new keys; exits non-zero if any entry fails validation after migration | LW-029 | M |
| LW-038 | SRD Batch Ingest A–C | data-ingest | Populate `data/srd_3.5/monsters/` JSON entries for SRD 3.5e monsters **Aboleth through Crocodile, Giant**; every entry must carry the full stat block (AC, HP dice, speed, attacks with damage, special attacks, special qualities, saves, skills, feats, CR, alignment, advancement) plus all v2 ecology fields; representative ecology values: Aboleth (`population_base: 30`, `allowed_biomes: ["Underground", "Underdark", "Aquatic"]`); Ankheg (`population_base: 200`, `allowed_biomes: ["Temperate_Plain", "Temperate_Hill"]`); Beholder (`population_base: 50`, `allowed_biomes: ["Underdark"]`); Bugbear (`population_base: 2000`, `allowed_biomes: ["Temperate_Forest", "Underground"]`); Centaur (`population_base: 400`, `allowed_biomes: ["Temperate_Forest", "Temperate_Plain"]`); each batch file validated against `MonsterSchemaV2` before commit | LW-037 | L |
| LW-039 | SRD Batch Ingest D–G | data-ingest | Populate JSON entries for **Darkmantle through Gynosphinx**; ecology highlights: Drow (`population_base: 5000`, `allowed_biomes: ["Underdark"]`, `primary_biome: "Underdark"`); Dragon entries split by age category with descending `population_base` — Wyrmling: 30, Young: 15, Adult: 5, Ancient: 1, Great Wyrm: 0 (unique singleton); each dragon entry's `allowed_biomes` matches its colour/type (e.g. White Dragon = `["Cold_Mountain", "Arctic"]`, Red Dragon = `["Warm_Mountain"]`); Formians encoded as colony population model — `population_base` = estimated colony count × average colony size (Worker: `population_base: 50000`, Taskmaster: `population_base: 500`, Queen: `population_base: 20`); Gnoll (`population_base: 3000`, `allowed_biomes: ["Warm_Plain", "Warm_Hill"]`) | LW-037 | L |
| LW-040 | SRD Batch Ingest H–L | data-ingest | Populate JSON entries for **Harpy through Lizardfolk**; ecology highlights: Harpy (`population_base: 150`, `allowed_biomes: ["Temperate_Hill", "Temperate_Mountain"]`); Hell Hound (`population_base: 300`, `allowed_biomes: ["Outer_Plane", "Elemental_Fire"]`); Hippogriff (`population_base: 500`, `allowed_biomes: ["Temperate_Hill", "Temperate_Mountain"]`); Hobgoblin (`population_base: 8000`, `allowed_biomes: ["Temperate_Hill", "Temperate_Plain", "Underground"]`); Hydra entries include `mm-immortal` compatible fields: each head tracked separately, `regen_hp_per_round` encodes the regrowth rule (2 heads regrow per severed head unless cauterised); Kobold (`population_base: 10000`, `allowed_biomes: ["Underground", "Temperate_Hill"]`); Kraken (`population_base: 5`, `allowed_biomes: ["Aquatic"]`); Lizardfolk (`population_base: 1500`, `allowed_biomes: ["Warm_Swamp", "Warm_Aquatic"]`) | LW-037 | L |
| LW-041 | SRD Batch Ingest M–R | data-ingest | Populate JSON entries for **Manticore through Rust Monster**; ecology highlights: Mind Flayer (`population_base: 200`, `allowed_biomes: ["Underdark"]`); Minotaur (`population_base: 300`, `allowed_biomes: ["Underground", "Any_Ruin"]`); Nymph (`population_base: 100`, `allowed_biomes: ["Temperate_Forest", "Temperate_Aquatic"]`); Ogre (`population_base: 1000`, `allowed_biomes: ["Cold_Hill", "Temperate_Hill", "Temperate_Mountain"]`); Ogre Mage (`population_base: 80`, `allowed_biomes: ["Cold_Mountain", "Cold_Hill"]`); Orc (`population_base: 15000`, `allowed_biomes: ["Temperate_Hill", "Temperate_Plain", "Underground"]`); Purple Worm (`population_base: 40`, `allowed_biomes: ["Underground"]`); Rakshasa (`population_base: 30`, `allowed_biomes: ["Warm_Plain", "Warm_Forest", "Any_Urban"]`); Rust Monster (`population_base: 200`, `allowed_biomes: ["Underground"]`) | LW-037 | L |
| LW-042 | SRD Batch Ingest S–Z | data-ingest | Populate JSON entries for **Sahuagin through Zombie**; ecology highlights: Sahuagin (`population_base: 3000`, `allowed_biomes: ["Aquatic"]`); Shadow (`population_base: 500`, `allowed_biomes: ["Any_Ruin", "Underground", "Any_Urban"]`); Succubus (`population_base: 100`, `allowed_biomes: ["Outer_Plane"]`); Tarrasque (`population_base: 1`, `allowed_biomes: ["Any"]`, `primary_biome: "Any"`, `ecology_notes: "Unique entity — only one exists in the world at any time; population_base of 1 is an absolute cap enforced at world generation"`); Treant (`population_base: 500`, `allowed_biomes: ["Temperate_Forest"]`); Troll (`population_base: 300`, `allowed_biomes: ["Cold_Mountain", "Cold_Hill", "Temperate_Swamp"]`); Vampire (`population_base: 50`, `allowed_biomes: ["Any_Urban", "Any_Ruin"]`, `ecology_notes: "Population represents active vampires; does not count spawn under their control"`); Wight (`population_base: 200`, `allowed_biomes: ["Any_Ruin", "Underground"]`); Wraith (`population_base: 150`, `allowed_biomes: ["Any_Ruin"]`); Yuan-ti (`population_base: 300`, `allowed_biomes: ["Warm_Forest", "Warm_Plain"]`); Zombie template entries set `population_base: 0` (raised, not naturally occurring) | LW-037 | L |

---

### Tier 5 — Full Integration & Validation (Depends on Tiers 3 & 4)

| Task | Title | Subsystem | Requirement | blockedBy | Effort |
|------|-------|-----------|-------------|-----------|--------|
| LW-043 | Spawn Director Full Integration | ecology-pop | Update `SpawnDirector` class (wherever currently defined) to consult the `PopulationLedger` on every spawn request; integration sequence: (1) call `can_spawn_in_chunk` gate — return `SpawnResult.Blocked_Biome` or `SpawnResult.Extinct` if gate fails; (2) if gate passes, call `apply_population_delta(ledger, species_id, chunk_id, -1)` to decrement world population; (3) call `resolve_anomaly_roll` for this spawn event — if an `AnomalyRecord` is returned, fire `request_anomaly_lore` as a non-blocking async task and proceed with spawn; (4) on entity death, call `apply_population_delta(ledger, species_id, chunk_id, +0)` — kills are already accounted for at spawn-decrement; permanent death calls `apply_population_delta` with `delta=-1` against the current global ledger; `SpawnResult` enum: Spawned / Blocked_Biome / Extinct / CapacityFull / AnomalySpawned | LW-036, LW-016 | L |
| LW-044 | MM Physics Combat Engine Wiring | mm-passive | Wire all MM Physics subsystems into the existing `CombatEngine` turn loop; integration points: **Start of entity turn** — call `process_aura_effects` for each entity with an Aura `PassiveEffect`; **After attack resolution** — if attacker has Improved Grab feat and hit landed on natural attack, call `attempt_improved_grab`; if attack is a spell, call `apply_sr_interaction_rules` before applying damage; **Damage application** — call `apply_damage_reduction` for all physical damage; **End of round** — call `process_healing_tick` with `resolve_healing_precedence` for every entity with a `RegenerationRecord`; **On entity death** — fire `apply_population_delta` via the SpawnDirector integration (LW-043) to decrement species world count by 1 | LW-031, LW-032, LW-033, LW-034 | L |
| LW-045 | Ecology × Physics Data Coherence Validator | data-ingest | Validation pass over all ingested JSON entries (runs after LW-038–LW-042 complete); checks: (a) every monster with `Regeneration` in `special_qualities` must have non-empty `elemental_weaknesses` or `alignment_weaknesses` in its `mm-immortal` fields; (b) every monster with `Spell Resistance` in `special_qualities` must have an `sr_value: int` field ≥ 1; (c) every monster with `Improved Grab` or `Swallow Whole` in `special_attacks` must have corresponding grapple fields (`constrict_damage_dice`, swallow damage expression); (d) every monster must have `population_base ≥ 0` and at least one entry in `allowed_biomes`; outputs `data/coherence_report.json` with per-entry pass/fail and the specific failing rule | LW-038, LW-039, LW-040, LW-041, LW-042 | M |
| LW-046 | Living World Regression Test Suite | ecology-pop | Integration test battery in `tests/world_sim/test_living_world.py`; minimum six scenarios: **(1) Biome-zeroed at init** — world generated with no Underdark chunk → Drow `global_count` is 0, `is_extinct` is True before first tick; **(2) Extinction via kills** — spawn a local Troll population of 1, kill it via `apply_population_delta(-1)` → `broadcast_extinction` fires, `AlreadyExtinctError` raised on second broadcast, `apply_population_delta` raises `SpeciesExtinctError` on any further call; **(3) Migration repopulation** — overpopulated Cold_Hill chunk with Trolls, adjacent empty Cold_Mountain chunk — after one tick cycle a `MigrationVector` is generated and applied, target chunk count > 0; **(4) Anomaly lore async** — mock `LLMClient`, trigger anomaly roll for Tarrasque in a Temperate_Forest chunk → `AnomalyRecord` created with `lore_text=None`, async task resolves and `lore_text` is populated; **(5) DR + SR combat** — Beholder with DR 10/Magic and SR 27 receives a non-magical arrow (reduced by 10) and a Magic Missile (SR checked, on failure spell does 0 damage); **(6) Troll Regeneration suppression** — Troll receives fire damage on tick N, Regeneration suppressed for tick N, Fast Healing does not activate same tick per LW-033 precedence rule | LW-043, LW-044, LW-045 | L |

---

## 3. Effort Summary

| Tier | Task Count | S Tasks | M Tasks | L Tasks | Estimated Total |
|------|-----------|---------|---------|---------|-----------------|
| 0 — Base Schemas | 11 | 11 | 0 | 0 | ~5 days |
| 1 — Core Mechanics | 9 | 3 | 5 | 1 | ~12 days |
| 2 — Registries & Generators | 10 | 2 | 7 | 1 | ~14 days |
| 3 — Advanced Physics | 6 | 1 | 4 | 1 | ~9 days |
| 4 — Data Ingestion | 7 | 0 | 1 | 6 | ~14 days |
| 5 — Integration & Validation | 4 | 0 | 1 | 3 | ~8 days |
| **Total** | **47** | **17** | **18** | **12** | **~62 dev-days** |

> Tier 4 batches (LW-038–LW-042) are data-entry work and can be parallelised across contributors.
> Tier 0–1 must be complete before any Tier 2+ implementation begins.
> Tier 5 cannot begin until all Tier 4 batches are validated by LW-045.

