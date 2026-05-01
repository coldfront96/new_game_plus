# PHASE_5_GRAND_UNIFICATION_TASKS.md — Grand Unification & Atmosphere

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
| Textual TUI (single-screen) | `src/overseer_ui/textual_app.py` | ✅ Shipped |
| Fog-of-War / Vision radius | `src/game/player_controller.py` | ✅ Shipped |
| World Tick Orchestrator | `src/world_sim/world_tick.py` | ✅ Shipped |
| Civilization Builder / Towns | `src/world_sim/civilization_builder.py` | ✅ Shipped |
| Dungeon Floor Generator | `src/terrain/dungeon_carver.py` | ✅ Shipped |
| Party Manager | `src/game/party_manager.py` | ✅ Shipped |
| Campaign Session | `src/game/campaign.py` | ✅ Shipped |
| UI State Machine | `src/overseer_ui/textual_app.py` (extended) | 🔲 Pending |
| Chronos & Weather Module | `src/world_sim/chronos.py` | 🔲 Pending |
| Vision Attenuation | `src/rules_engine/vision.py` | 🔲 Pending |
| Terminal VFX Renderer | `src/overseer_ui/animation_renderer.py` | 🔲 Pending |

---

## 1. Scope

Phase 5 unifies all previously shipped simulation modules into a single,
cohesive Textual multi-screen experience and injects environmental physics
plus ASCII visual effects. The three subsystems are:

| # | Subsystem | Short Name | New / Modified Modules |
|---|-----------|------------|------------------------|
| A | Unified UI State Machine | ui-state | `src/overseer_ui/textual_app.py` |
| B | Chronos & Atmos | chronos-atmos | `src/world_sim/chronos.py` *(new)*, `src/rules_engine/vision.py` *(new)*, `src/world_sim/world_tick.py` |
| C | Terminal VFX | terminal-vfx | `src/overseer_ui/animation_renderer.py` *(new)*, `src/overseer_ui/textual_app.py` |

---

## 2. Dependency Map

```
Tier 0  ──────────────────────────────────────────────────────────────────
         [PH5-001]  UIMode enum + AppStateManager dataclass
         [PH5-006]  WorldClock + ChronosRecord dataclass
         [PH5-010]  AnimationRenderer base + async VFX queue
                │
Tier 1  ────────▼─────────────────────────────────────────────────────────
         [PH5-002]  OverworldScreen widget           (deps: PH5-001)
         [PH5-003]  TownMerchantScreen widget         (deps: PH5-001)
         [PH5-004]  TacticalDungeonScreen widget      (deps: PH5-001)
         [PH5-007]  Night vision radius attenuation   (deps: PH5-006)
         [PH5-008]  WeatherState + procedural weather (deps: PH5-006)
         [PH5-011]  Lightning Bolt Z-line VFX         (deps: PH5-010)
         [PH5-012]  Damage flash VFX                  (deps: PH5-010)
                │
Tier 2  ────────▼─────────────────────────────────────────────────────────
         [PH5-005]  Mathematical transition triggers  (deps: PH5-002, PH5-003, PH5-004)
         [PH5-009]  Weather debuff integration        (deps: PH5-007, PH5-008)
         [PH5-013]  Rain particle VFX integration     (deps: PH5-008, PH5-011, PH5-012)
```

---

## 3. Task Tiers

### Tier 0 — Foundation (No Dependencies)

| Task | Title | Subsystem | Requirement | blockedBy | Effort |
|------|-------|-----------|-------------|-----------|--------|
| PH5-001 | UIMode enum + AppStateManager dataclass | ui-state | Add `UIMode(str, Enum)` with members `OVERWORLD`, `TOWN_MERCHANT`, `TACTICAL_DUNGEON` to `src/overseer_ui/textual_app.py`. Add `@dataclass(slots=True) AppStateManager` with fields: `mode: UIMode = UIMode.OVERWORLD`, `active_town_id: str \| None = None`, `active_dungeon_floor: int = 0`, `transition_lock: threading.Lock = field(default_factory=threading.Lock)`. Add `AppStateManager.transition(new_mode, *, town_id=None, dungeon_floor=0) -> bool` that acquires the lock, validates the transition (raises `ValueError` for invalid mode), updates fields atomically, releases the lock, and returns `True`. Expose a module-level singleton `_app_state = AppStateManager()` consumed by all screen classes. **Required data structures:** `UIMode`, `AppStateManager`. **Target file:** `src/overseer_ui/textual_app.py`. **Dependencies:** none. | — | S |
| PH5-006 | WorldClock + ChronosRecord dataclass | chronos-atmos | Create `src/world_sim/chronos.py`. Define `TICKS_PER_HOUR: int = 60`, `HOURS_PER_DAY: int = 24`, `DAY_START_HOUR: int = 6`, `NIGHT_START_HOUR: int = 20`. Define `@dataclass(slots=True) ChronosRecord` with fields: `tick: int`, `hour: int` (0–23, computed as `(tick // TICKS_PER_HOUR) % HOURS_PER_DAY`), `is_day: bool` (True when `DAY_START_HOUR <= hour < NIGHT_START_HOUR`), `weather: str` (`"clear"` default), `rain_intensity: float` (0.0–1.0), `temperature_c: float`. Define `advance_chronos(record: ChronosRecord, ticks: int = 1) -> ChronosRecord` that returns a new `ChronosRecord` with updated `tick`, recomputed `hour` and `is_day`, and unchanged weather. Define `chronos_from_world_tick(world_tick: int) -> ChronosRecord` as the canonical constructor. **Required data structures:** `ChronosRecord`, `TICKS_PER_HOUR`, `HOURS_PER_DAY`. **Target file:** `src/world_sim/chronos.py` *(new)*. **Dependencies:** none. | — | S |
| PH5-010 | AnimationRenderer base + async VFX queue | terminal-vfx | Create `src/overseer_ui/animation_renderer.py`. Define `@dataclass(slots=True) VFXEvent` with fields: `event_type: str` (e.g. `"lightning_bolt"`, `"damage_flash"`, `"rain_particle"`), `origin: tuple[int, int]`, `target: tuple[int, int] \| None`, `duration_ms: int`, `payload: dict`. Define `class AnimationRenderer` with: `_queue: asyncio.Queue[VFXEvent]` (maxsize=128), `_grid_widget: Static` (injected reference to the Textual voxel grid), `running: bool = False`. Add `enqueue(event: VFXEvent) -> None` (non-blocking `put_nowait`; drops oldest on full). Add `async def run_loop(self) -> None` that sets `running=True` and awaits events from the queue in a `while self.running` loop, dispatching to the appropriate private `_render_*` coroutine. Add `async def stop(self) -> None` that sets `running=False` and drains the queue. The `run_loop` must **never** block the main physics thread — all rendering is done via `asyncio.sleep(0)` yields between frames. **Required data structures:** `VFXEvent`, `AnimationRenderer`. **Target file:** `src/overseer_ui/animation_renderer.py` *(new)*. **Dependencies:** none. | — | M |

---

### Tier 1 — Core Screens & Physics (Depends on Tier 0)

| Task | Title | Subsystem | Requirement | blockedBy | Effort |
|------|-------|-----------|-------------|-----------|--------|
| PH5-002 | OverworldScreen widget | ui-state | Add `class OverworldScreen(Screen)` to `src/overseer_ui/textual_app.py`. The screen composes a full-viewport `Static` voxel grid (reuses `_render_chunk_with_fog` from the existing app) and a one-line status bar showing `[Overworld] Tick: {tick}  Pos: ({x},{y})`. Bind arrow keys and WASD to `action_move_{direction}` which call `PlayerController.dispatch_player_input` and update the voxel grid via `call_after_refresh`. Bind `t` to the existing `action_talk` NPC dialogue flow. On mount, read `_app_state.mode` and assert it equals `UIMode.OVERWORLD`; raise `RuntimeError` otherwise. **Required data structures:** `AppStateManager` (PH5-001), `PlayerController` (✅ `src/game/player_controller.py`). **Target file:** `src/overseer_ui/textual_app.py`. **Dependencies:** PH5-001. | PH5-001 | M |
| PH5-003 | TownMerchantScreen widget | ui-state | Add `class TownMerchantScreen(Screen)` to `src/overseer_ui/textual_app.py`. The screen composes a two-column `Horizontal` layout: left column shows the town's `MerchantInventoryRecord.items` as a scrollable `DataTable` (columns: Name, Price gp, Weight lb); right column shows party gold and equipped items via a `RichLog`. Bind `b` to `action_buy` which reads the highlighted `DataTable` row, deducts party gold (`party_record.gold -= item.price_gp`, clamped ≥ 0), and appends the item to `party_record.inventory`. Bind `Escape` to `action_exit_town` which calls `_app_state.transition(UIMode.OVERWORLD)` and `app.switch_screen("overworld")`. On mount, load the `TownRecord` whose `town_id == _app_state.active_town_id` from `CivilizationBuilder.generate_towns` cache. **Required data structures:** `AppStateManager` (PH5-001), `TownRecord`, `MerchantInventoryRecord` (✅ `src/world_sim/civilization_builder.py`). **Target file:** `src/overseer_ui/textual_app.py`. **Dependencies:** PH5-001. | PH5-001 | M |
| PH5-004 | TacticalDungeonScreen widget | ui-state | Add `class TacticalDungeonScreen(Screen)` to `src/overseer_ui/textual_app.py`. The screen composes a main `Static` voxel grid rendered from `DungeonFloor.grid` (from `src/terrain/dungeon_carver.py`) with walls as `#`, floors as `.`, and entity tokens as single uppercase letters. A sidebar `RichLog` shows the combat log from `session.play_session` events forwarded via `OverseerQueue`. Bind `f` to `action_full_attack` which enqueues a combat round via `OverseerQueue.put` and awaits the result. Bind `Escape` to `action_ascend` which calls `_app_state.transition(UIMode.OVERWORLD)` and `app.switch_screen("overworld")`. Floor index is read from `_app_state.active_dungeon_floor`. **Required data structures:** `AppStateManager` (PH5-001), `DungeonFloor` (✅ `src/terrain/dungeon_carver.py`), `OverseerQueue` (✅ `src/overseer_ui/overseer.py`). **Target file:** `src/overseer_ui/textual_app.py`. **Dependencies:** PH5-001. | PH5-001 | M |
| PH5-007 | Night vision radius attenuation | chronos-atmos | Create `src/rules_engine/vision.py`. Define constants `BASE_VISION_RADIUS: int = 8` and `NIGHT_VISION_RADIUS: int = 3`. Define `@dataclass(slots=True) VisionState` with fields: `radius: int`, `has_light_source: bool`, `low_light_vision: bool`, `darkvision_ft: int`. Define `calculate_vision_radius(chronos: ChronosRecord, character_metadata: dict, *, base_radius: int = BASE_VISION_RADIUS) -> int` implementing the following formula exactly: (1) start with `r = base_radius`; (2) if `chronos.is_day`, return `r` unchanged; (3) if `character_metadata.get("darkvision_ft", 0) > 0`, return `r` unchanged (darkvision ignores night); (4) if `character_metadata.get("has_light_source", False)`, return `r` unchanged (torch radius equals base); (5) otherwise return `NIGHT_VISION_RADIUS` — the mathematical shrink. Define `build_vision_state(chronos: ChronosRecord, character_metadata: dict) -> VisionState` that calls `calculate_vision_radius` and constructs the `VisionState`. This function must be called by `PlayerController.dispatch_player_input` in `src/game/player_controller.py` (pass result's `radius` as the `vision_radius` parameter of `calculate_visible_voxels`). **Required data structures:** `ChronosRecord` (PH5-006), `VisionState`. **Target file:** `src/rules_engine/vision.py` *(new)*. **Dependencies:** PH5-006. | PH5-006 | M |
| PH5-008 | WeatherState + procedural weather engine | chronos-atmos | Extend `src/world_sim/chronos.py`. Define `WeatherType(str, Enum)` with members `CLEAR = "clear"`, `RAIN = "rain"`, `STORM = "storm"`. Define `@dataclass(slots=True) WeatherState` with fields: `weather_type: WeatherType`, `intensity: float` (0.0–1.0), `rain_particles: list[tuple[int,int]]` (current particle coordinates in the viewport grid), `wind_speed_ms: float`. Define `generate_weather(rng, *, terrain_biome: str = "temperate") -> WeatherState` which: rolls `rng.random()` against a biome probability table (`"desert"`: 5 % rain, `"temperate"`: 25 % rain, `"swamp"`: 45 % rain, default: 20 % rain); if above threshold returns `CLEAR`; otherwise rolls `intensity = rng.uniform(0.3, 1.0)`; if `intensity >= 0.8` sets `STORM` else `RAIN`; populates `rain_particles` with `int(intensity * 20)` random `(row, col)` tuples in a 24×80 viewport. Define `tick_weather(state: WeatherState, rng) -> WeatherState` that shifts each particle one row down (wrapping at row 24) and rolls a 2 % chance per tick to regenerate weather. Integrate into `advance_chronos`: accept optional `rng` and `biome` parameters; if `rng` is not `None`, call `tick_weather` to advance particle positions. **Required data structures:** `WeatherType`, `WeatherState`, `ChronosRecord` (PH5-006). **Target file:** `src/world_sim/chronos.py`. **Dependencies:** PH5-006. | PH5-006 | M |
| PH5-011 | Lightning Bolt Z-line VFX | terminal-vfx | Add `async def _render_lightning_bolt(self, event: VFXEvent) -> None` to `AnimationRenderer` in `src/overseer_ui/animation_renderer.py`. Given `event.origin = (r0, c0)` and `event.target = (r1, c1)`, compute the jagged Z-line path: (1) draw a horizontal segment from `c0` to `c1` at row `r0`; (2) draw a diagonal segment from `(r0, c1)` to `(r1, c0)` stepping one row per column; (3) draw a horizontal segment from `c0` to `c1` at row `r1`. For each coordinate in the path, call `self._grid_widget.update()` with a Rich `Text` object overlaying a yellow `⚡` glyph at that cell position; await `asyncio.sleep(0.03)` between each glyph to produce a frame-by-frame draw effect. After `event.duration_ms` milliseconds, restore original cell content by calling `self._grid_widget.refresh()`. Expose a public helper `enqueue_lightning_bolt(origin, target, duration_ms=400) -> None` that constructs and enqueues the `VFXEvent`. **Required data structures:** `VFXEvent` (PH5-010), `AnimationRenderer` (PH5-010). **Target file:** `src/overseer_ui/animation_renderer.py`. **Dependencies:** PH5-010. | PH5-010 | S |
| PH5-012 | Damage flash VFX | terminal-vfx | Add `async def _render_damage_flash(self, event: VFXEvent) -> None` to `AnimationRenderer` in `src/overseer_ui/animation_renderer.py`. Given `event.origin = (row, col)` (the voxel coordinate of the damaged entity), render a Rich `Text` segment with `style="on red"` at that cell for `event.duration_ms` milliseconds (default 200 ms), then restore the cell to its previous content. Implement the flash via two `asyncio.sleep` calls: one to hold the red frame, one after restoration. The HP delta is read from `event.payload["hp_delta"]` (negative int) and printed to the combat `RichLog` as `"[-{abs(hp_delta)} HP]"` in red after the flash completes. Expose `enqueue_damage_flash(position: tuple[int,int], hp_delta: int, duration_ms: int = 200) -> None`. Wire this into `TacticalDungeonScreen.action_full_attack` (PH5-004): for each `CombatResult` with `damage_dealt > 0`, call `enqueue_damage_flash`. **Required data structures:** `VFXEvent` (PH5-010), `AnimationRenderer` (PH5-010), `CombatResult` (✅ `src/rules_engine/combat.py`). **Target file:** `src/overseer_ui/animation_renderer.py`. **Dependencies:** PH5-010. | PH5-010 | S |

---

### Tier 2 — Integration (Depends on Tier 1)

| Task | Title | Subsystem | Requirement | blockedBy | Effort |
|------|-------|-----------|-------------|-----------|--------|
| PH5-005 | Mathematical transition triggers | ui-state | Extend `PlayerController.dispatch_player_input` in `src/game/player_controller.py` with a post-move coordinate check. After updating `player_entity.position`, call `_resolve_screen_transition(new_pos, world_state) -> UIMode \| None` (new private function). This function: (1) queries `CivilizationBuilder`'s town list and checks if `new_pos` matches any `TownRecord.voxel_position` (exact coordinate equality); if matched, calls `_app_state.transition(UIMode.TOWN_MERCHANT, town_id=town.town_id)` and returns `UIMode.TOWN_MERCHANT`; (2) queries loaded dungeon chunks and checks if `new_pos` matches any `DungeonFloor`'s entry coordinate; if matched, calls `_app_state.transition(UIMode.TACTICAL_DUNGEON, dungeon_floor=floor_index)` and returns `UIMode.TACTICAL_DUNGEON`; (3) returns `None` if no transition. The caller in `dispatch_player_input` inspects the return value; if not `None`, it posts a `SwitchScreen` message to the Textual app via `OverseerQueue.put({"cmd": "switch_screen", "mode": new_mode.value})`. Add `_cmd_switch_screen` handler in `OverseerUI.on_overseer_message` that reads the mode and calls `self.app.switch_screen(...)`. **Required data structures:** `UIMode` + `AppStateManager` (PH5-001), `OverworldScreen` (PH5-002), `TownMerchantScreen` (PH5-003), `TacticalDungeonScreen` (PH5-004), `TownRecord` (✅), `DungeonFloor` (✅). **Target file:** `src/game/player_controller.py`, `src/overseer_ui/textual_app.py`. **Dependencies:** PH5-002, PH5-003, PH5-004. | PH5-002, PH5-003, PH5-004 | L |
| PH5-009 | Weather debuff integration | chronos-atmos | Add `apply_weather_debuffs(character_metadata: dict, weather: WeatherState) -> dict` to `src/world_sim/chronos.py`. The function: (1) computes `speed_multiplier = 1.0 - (weather.intensity * 0.4)` when `weather.weather_type in (RAIN, STORM)`, else `1.0`; (2) writes `character_metadata["weather_speed_multiplier"] = speed_multiplier` (float); (3) if `weather.weather_type == STORM`: also writes `character_metadata["weather_attack_penalty"] = -2`; (4) iterates `character_metadata.get("active_fire_effects", [])` (list of effect IDs) and removes any whose `element == "fire"` — fire-based effects are extinguished by STORM-intensity rain (simulating dousing); (5) returns the mutated dict. Integrate into `run_world_tick` in `src/world_sim/world_tick.py`: after `world_state.tick` is updated, call `apply_weather_debuffs` on each `WorldChunk.entity_metadata` dict using the chunk's current `WeatherState` (stored as `world_chunk.weather_state`, a new optional field on `WorldChunk`). Extend `PlayerController.dispatch_player_input` to read `character_metadata["weather_speed_multiplier"]` and apply it as a multiplier to the movement point budget before deducting voxel movement cost. **Required data structures:** `WeatherState` (PH5-008), `VisionState` (PH5-007), `WorldState` (✅ `src/world_sim/world_tick.py`). **Target files:** `src/world_sim/chronos.py`, `src/world_sim/world_tick.py`, `src/game/player_controller.py`. **Dependencies:** PH5-007, PH5-008. | PH5-007, PH5-008 | M |
| PH5-013 | Rain particle VFX integration | terminal-vfx | Add `async def _render_rain_particles(self, event: VFXEvent) -> None` to `AnimationRenderer` in `src/overseer_ui/animation_renderer.py`. Read `event.payload["particles"]` (list of `[row, col]` pairs from `WeatherState.rain_particles`). For each particle coordinate, overlay a cyan `~` glyph (Rich `Text`, `style="cyan"`) on the voxel grid widget. Draw all particles in a single `_grid_widget.update()` call by composing a full-grid `Text` object with particle glyphs injected at their positions (preserving existing terrain glyphs for non-particle cells). Await `asyncio.sleep(1 / 10)` (10 FPS rain tick) and re-render with shifted particle positions from `event.payload["next_particles"]`. The rain loop runs continuously while `WeatherState.weather_type in (RAIN, STORM)`; it terminates when `AnimationRenderer.stop()` is called or the weather clears. Expose `enqueue_rain_update(particles: list[tuple[int,int]], next_particles: list[tuple[int,int]]) -> None`. Wire this into `OverworldScreen` (PH5-002): after each `advance_chronos` call in the world-tick callback, if weather is RAIN or STORM call `enqueue_rain_update` with current and next-frame particles. **Required data structures:** `VFXEvent` (PH5-010), `AnimationRenderer` (PH5-010), `WeatherState` (PH5-008). **Target file:** `src/overseer_ui/animation_renderer.py`. **Dependencies:** PH5-008, PH5-011, PH5-012. | PH5-008, PH5-011, PH5-012 | M |

---

## 4. Effort Summary

| Tier | Task Count | S Tasks | M Tasks | L Tasks | Estimated Total |
|------|-----------|---------|---------|---------|-----------------|
| 0 — Foundation | 3 | 2 | 1 | 0 | ~2 days |
| 1 — Core Screens & Physics | 8 | 2 | 6 | 0 | ~6 days |
| 2 — Integration | 3 | 0 | 2 | 1 | ~4 days |
| **Total** | **13** | **4** | **9** | **1** | **~12 dev-days** |

> Tier 0 tasks (PH5-001, PH5-006, PH5-010) are fully independent and may be developed in parallel across three engineers.
> Tier 1 tasks within a subsystem are also mutually independent: PH5-002/003/004 can run in parallel; PH5-007/008 can run in parallel; PH5-011/012 can run in parallel.
> PH5-005 is the single critical-path integration task — it must land after all three Tier 1 screens are stable.
> PH5-013 is the visual capstone and depends on the weather engine (PH5-008) being complete and tested first.
