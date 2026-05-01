# NEXT_STEPS_TASKS.md — Post-Phase-4 Implementation Backlog

## Status Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Complete / Shipped |
| 🔲 | Pending implementation |
| 🚧 | In progress |
| ❌ | Blocked |

---

## 1 · Vision State Wiring  `src/game/player_controller.py`

**Gap:** `build_vision_state()` exists in `src/rules_engine/vision.py` and correctly
computes night/darkvision/light-source attenuation, but `dispatch_player_input` never
calls it — `controller.vision_radius` is always the constructor default (8) regardless
of time of day or character senses.

| Task | Module | Status | Requirement |
|------|--------|--------|-------------|
| VIS-001 | `src/game/player_controller.py` | ✅ | Add optional `chronos: ChronosRecord \| None` and `character_metadata: dict \| None` parameters to `dispatch_player_input`. After each successful move, call `build_vision_state(chronos, char_meta)` and assign `controller.vision_radius = vision_state.radius`. Skip if either arg is `None` (backwards-compatible default). |

---

## 2 · Metamagic Feat Wiring  `src/rules_engine/spell_effects.py`, `feat_engine.py`

**Gap:** `Empower Spell` and `Maximize Spell` are in `FEAT_CATALOG` with the comment
*"effect resolved in spellcasting"*, but `SpellDispatcher.dispatch()` never checks
for them. `Quicken Spell` is absent from the catalog entirely.

| Task | Module | Status | Requirement |
|------|--------|--------|-------------|
| MM-001 | `src/rules_engine/feat_engine.py` | ✅ | Add `Quicken Spell` to `FEAT_CATALOG` (desc: *"A quickened spell is cast as a swift action. Uses a slot 4 levels higher."*) and `_PREREQUISITES` (no prerequisites). |
| MM-002 | `src/rules_engine/spell_effects.py` | ✅ | Add `metamagic_flags: frozenset[str] \| None = None` parameter to `SpellDispatcher.dispatch()`. Pass it to `_resolve_effect()`. In `_resolve_effect()`, after computing `rolled` damage/healing: if `"Maximize Spell" in flags` replace all dice rolls with their maximum values; if `"Empower Spell" in flags` multiply the final numeric result by 1.5 (round down). Both can stack (maximize first, then empower). |
| MM-003 | `src/rules_engine/spell_effects.py` | ✅ | Add `SpellDispatcher.get_active_metamagic(caster) -> frozenset[str]` that reads `caster.feats` and returns all metamagic feat names present. Callers can pass this directly to `dispatch()`. |

---

## 3 · Crafting Pipeline  `src/rules_engine/crafting.py` *(new)*

**Gap:** `Brew Potion` and `Craft Wondrous Item` are cataloged feats but there is no
code that actually crafts items. No `CraftingSystem` class or module exists.

| Task | Module | Status | Requirement |
|------|--------|--------|-------------|
| CRF-001 | `src/rules_engine/crafting.py` | ✅ | Define `@dataclass CraftingResult` with fields: `success: bool`, `item_name: str`, `gp_cost: int`, `xp_cost: int`, `days: int`, `failure_reason: str`. |
| CRF-002 | `src/rules_engine/crafting.py` | ✅ | Implement `brew_potion(caster, spell_name, caster_level, registry, party_gold) -> CraftingResult`. Prereqs: caster has `"Brew Potion"` feat; caster_level ≥ 3; spell is in registry and level ≤ 3. GP cost = spell_level × caster_level × 25 (half market). XP cost = GP_cost // 25. Time: 1 day. Returns success if `party_gold >= gp_cost`. |
| CRF-003 | `src/rules_engine/crafting.py` | ✅ | Implement `craft_wondrous_item(caster, item_name, market_price_gp, caster_level, party_gold) -> CraftingResult`. Prereqs: caster has `"Craft Wondrous Item"` feat; caster_level ≥ 3. GP cost = market_price_gp // 2. XP cost = GP_cost // 25. Time = ceil(GP_cost / 1000) days. |
| CRF-004 | `src/rules_engine/crafting.py` | ✅ | Add module-level `CRAFT_DC_TABLE: dict[str, int]` mapping item category → Spellcraft DC. Default DC = 5 + (spell_level × 2). Expose `check_craft_dc(caster, dc, rng) -> bool` using `caster.metadata.get("spellcraft_ranks", 0) + INT_mod + d20`. |

---

## 4 · LLM Fallback in MythosForge  `src/rules_engine/mythos_forge.py`

**Gap:** When the LLM server is unavailable (network error, no Ollama running),
`LLMClient._post()` returns an empty string. `ProceduralArtifactGenerator` receives
`""` and stores it as the artifact's lore — producing a nameless, story-less relic.

| Task | Module | Status | Requirement |
|------|--------|--------|-------------|
| MF-001 | `src/rules_engine/mythos_forge.py` | ✅ | Add `_FALLBACK_PREFIXES: list[str]` and `_FALLBACK_SUFFIXES: list[str]` tables (10 entries each — mythological adjectives and weapon/armour nouns). |
| MF-002 | `src/rules_engine/mythos_forge.py` | ✅ | Add `_generate_fallback_lore(artifact_type, tier, properties, rng) -> tuple[str, str]` that returns `(lore_name, backstory)` by sampling `PREFIX + " " + NOUN` and a template backstory string that incorporates `tier` and `artifact_type`. |
| MF-003 | `src/rules_engine/mythos_forge.py` | ✅ | In `ProceduralArtifactGenerator._attach_lore()` (or wherever the LLM result is applied): if the returned string is empty or whitespace-only, call `_generate_fallback_lore()` instead. Log a `_forge_log.warning` noting the fallback. |

---

## 5 · TacticalDungeonScreen Combat Execution  `src/overseer_ui/textual_app.py`

**Gap:** `TacticalDungeonScreen.action_full_attack` only enqueues an `AgentTask` and
prints *"Combat round queued."* — it never actually resolves a combat round or shows
damage numbers. The `AnimationRenderer` with `enqueue_damage_flash` is never called.

| Task | Module | Status | Requirement |
|------|--------|--------|-------------|
| TD-001 | `src/overseer_ui/textual_app.py` | ✅ | Add `party: list \| None`, `monster_registry: dict \| None`, and `animation_renderer: AnimationRenderer \| None` parameters to `TacticalDungeonScreen.__init__`. |
| TD-002 | `src/overseer_ui/textual_app.py` | ✅ | In `action_full_attack`: if `party` and `monster_registry` are available, import `src.rules_engine.combat.resolve_attack_roll` and resolve one attack from party[0] against a random monster. Display result in `td-log`. If `damage_dealt > 0` and `animation_renderer` is set, call `animation_renderer.enqueue_damage_flash((0, 0), -damage_dealt)`. |
| TD-003 | `src/overseer_ui/textual_app.py` | ✅ | Still enqueue the `AgentTask` for the OverseerQueue audit trail, but only *after* the local combat round is resolved. |

---

## 6 · Error Handling Improvements

**Gap:** Eight-plus silent `except ... pass` blocks swallow real errors in production
paths. At minimum every caught exception should be logged at DEBUG level.

| Task | Module | Status | File:Line | Fix |
|------|--------|--------|-----------|-----|
| ERR-001 | `src/world_sim/world_tick.py` | ✅ | `_trigger_anomaly_lore_tasks`: `except RuntimeError: pass` → log at DEBUG. |
| ERR-002 | `src/world_sim/world_tick.py` | ✅ | `_apply_weather_debuffs`: `except Exception: pass` → log at DEBUG with chunk id. |
| ERR-003 | `src/game/player_controller.py` | ✅ | `dispatch_player_input` screen-transition block: `except Exception: pass` → log at DEBUG. |
| ERR-004 | `src/game/player_controller.py` | ✅ | `_resolve_screen_transition` town/dungeon blocks: broad `except (ValueError, Exception): pass` → split into specific ValueError (log WARNING) and generic (log DEBUG). |
| ERR-005 | `src/overseer_ui/animation_renderer.py` | ✅ | `_render_damage_flash` combat_log write: `except Exception: pass` → log at DEBUG. |
| ERR-006 | `src/overseer_ui/textual_app.py` | ✅ | `_refresh_viewport` and `_render_dungeon_floor`: `except Exception: pass` inner blocks → log at DEBUG. |

---

## 7 · Performance Profiling Instrumentation

**Gap:** No timing data exists for the two heaviest operations: chunk generation and
3D A* pathfinding. Without measurements, we cannot know if these will hold up at
simulation scale.

| Task | Module | Status | Requirement |
|------|--------|--------|-------------|
| PERF-001 | `src/terrain/chunk_generator.py` | ✅ | Wrap the body of the main generation function with `t0 = time.perf_counter()` / `_log.debug("chunk gen %.3f s", time.perf_counter() - t0)`. |
| PERF-002 | `src/ai_sim/pathfinding.py` | ✅ | Wrap A* search loop with `perf_counter` timing. Log path length and elapsed time at DEBUG. |

---

## Dependency Order

```
ERR-001..006  (independent, no deps)
PERF-001..002 (independent, no deps)
VIS-001       (depends on vision.py ✅)
MM-001        → MM-002 → MM-003
CRF-001       → CRF-002 → CRF-003 → CRF-004
MF-001        → MF-002 → MF-003
TD-001        → TD-002 → TD-003
```

---

## Effort Summary

| Group | Tasks | Estimated |
|-------|-------|-----------|
| Vision wiring | 1 | 1 hr |
| Metamagic | 3 | 2 hr |
| Crafting | 4 | 3 hr |
| Mythos fallback | 3 | 1 hr |
| Tactical combat | 3 | 2 hr |
| Error handling | 6 | 1 hr |
| Perf profiling | 2 | 30 min |
| **Total** | **22** | **~10 hr** |
