# Playability Milestone — Task Tracker

Tracks the work needed to turn the existing 3.5e rules engine into something a
human can actually sit down and play. The rules surface (combat, spells, feats,
classes, hazards, magic items, treasure, encounters) is already complete and
covered by 1900+ tests; what's missing is the runtime driver, content
externalisation, and the autonomous-agent layer.

Tasks are ordered by dependency. Tasks 1–6 are the playability milestone
(2–5 depend on 1; 6 depends on 2–5). Task 7 is parallelisable. Task 8 should
precede any new large rules work. Tasks 9–10 are the agent-layer follow-on.

---

## Phase A — Playable Loop (Text Mode)

- [x] Task 1: Scaffold `src/game/` package + `python -m new_game_plus` entry point.
  - Add `src/game/__init__.py`, `src/game/__main__.py`, `src/game/cli.py`.
  - argparse subcommands: `new-character`, `run-encounter`, `play`.
  - Wire into `setup.py` `entry_points` so `new-game-plus` is on PATH.

- [x] Task 2: Text-mode character-creation wizard.
  - Prompt flow: race → class → ability scores (4d6-drop-lowest **and**
    point-buy) → skills → feats → starting equipment.
  - All choices validated against existing `RaceRegistry`, class definitions,
    `AbilityRegistry`, `SkillSystem`, `FeatEngine`, `EquipmentManager`.
  - Output: a fully-populated `Character35e` instance.

- [x] Task 3: Party / character persistence.
  - JSON serializer/deserializer for `Character35e` (and dependent state:
    `MagicItemEngine`, `ConditionManager`, `XPManager`).
  - `saves/` directory; `load_party(name)` / `save_party(name, party)`.
  - Round-trip test: save → load → assert equality on AC, HP, saves, slots.

- [x] Task 4: `TurnController` with initiative + action economy.
  - Roll initiative for all combatants, build turn order.
  - Per-turn loop using existing `ActionTracker` (standard / move / swift /
    full-round / free) with proper reset on new turn.
  - Round counter, condition duration tick, end-of-turn save handling.

- [x] Task 5: Wire combat event loop through `CombatSystem`.
  - Player input → `AttackIntent` / spell-cast / move / use-item events on
    the existing `EventBus`.
  - Print per-turn results (hit/miss, damage, conditions, death).
  - Detect victory / total-party-defeat / flee and exit cleanly.

- [x] Task 6: End-to-end party-vs-encounter integration test.
  - Build a 4-character L3 party via Task 2 helpers.
  - Generate an encounter via existing `build_encounter()`.
  - Run full cycle: spell → attack → condition → death → XP award →
    `generate_treasure_hoard()` → loot distribution.
  - Assert the encounter terminates and XP/treasure are sane.

---

## Phase B — Content Externalisation

- [x] Task 7: Populate `data/srd_3.5/` with JSON + loader.
  - Extract spell definitions from `src/rules_engine/magic.py` to
    `data/srd_3.5/spells/*.json`.
  - Same for feats, races, class progressions, monsters, magic items,
    poisons/diseases, gems/art, encounter tables.
  - Add `src/rules_engine/srd_loader.py` that builds the in-memory registries
    from the JSON at import time.
  - Existing tests must still pass unchanged.

---

## Phase C — Audit & Cleanup

- [x] Task 8: Audit `DMG_BUILD_SITE.md` Tier 0–3 against shipped modules.
  - Cross-reference each `T-NNN` against `src/rules_engine/*.py`
    (`objects.py`, `traps.py`, `consumables.py`, `item_specials.py`,
    `environment.py`, `encounter_extended.py`, `magic_item_engine.py`).
  - Mark shipped tasks `[x]` in `DMG_BUILD_SITE.md`; produce a residual list
    of any Tier 0–3 tasks that are still actually missing.

---

## Phase D — Agent Layer

- [x] Task 9: Minimal terminal Overseer UI.
  - Replace `src/overseer_ui/__init__.py` stub with a curses- or
    prompt-toolkit-based approve/reject queue backed by real `AgentTask`
    objects.
  - Persistent session log to `logs/overseer-YYYY-MM-DD.jsonl`.

- [x] Task 10: Flesh out `src/agent_orchestration/`.
  - `scheduler.py` — picks the next pending `AgentTask`, respects priority,
    enforces concurrency cap.
  - `prompt_builder.py` — composes prompts from task spec + 3.5e SRD context.
  - `result_parser.py` — validates LLM output against expected schema,
    surfaces parse failures back to the Overseer.
  - Wire to existing `src/ai_sim/llm_bridge.py`.

---

## Completion Notes

(Add a note per task as it lands, mirroring the format of the historical
spell-ingestion notes in `SPELL_TASKS.md`: file paths touched, line counts,
test counts, full-suite pass count.)

### 2026-04-25 — Tasks 1–10 (DMG playability milestone)

**Task 1 — `src/game/` scaffold + entry point**
- Files: `src/game/{__init__.py,__main__.py,cli.py}` (~260 LOC).
- Top-level alias package `new_game_plus/{__init__.py,__main__.py}` so
  `python -m new_game_plus` resolves.
- `setup.py` gains `console_scripts: new-game-plus=src.game.cli:main`.
- Tests: `tests/game/test_cli.py` (4 tests).

**Task 2 — Character creation wizard**
- File: `src/game/wizard.py` (~360 LOC).
- 4d6-drop-lowest + 25-point point-buy with PHB cost table.
- All choices flow through the existing `RaceRegistry`, class lookup tables,
  `SkillSystem`, `FeatRegistry`, and `EquipmentManager` presets.
- Tests: `tests/game/test_wizard.py` (8 tests).

**Task 3 — Party / character persistence**
- File: `src/game/persistence.py` (~280 LOC).
- Round-trips `Character35e` plus `MagicItemEngine` (by registry key),
  `ConditionManager`, and `XPManager` state.
- Tests: `tests/game/test_persistence.py` (7 tests).

**Task 4 — `TurnController`**
- File: `src/game/turn_controller.py` (~190 LOC).
- Initiative rolling with deterministic tie-breaks.
- Reuses `ActionTracker` for action economy; ticks `ConditionManager` at
  end-of-round; emits round/turn events on the `EventBus`.
- Tests: `tests/game/test_turn_controller.py` (7 tests).

**Tasks 5 + 6 — Combat event loop & end-to-end integration test**
- File: `src/game/session.py` (~310 LOC).
- `play_session()` builds monsters from a `build_encounter()` blueprint,
  drives `TurnController`, resolves attacks via `AttackResolver`,
  publishes `attack_resolved` / `combatant_defeated`, and on victory awards
  XP via `distribute_xp()` and rolls loot via `generate_treasure_hoard()`.
- Tests: `tests/game/test_session.py` (7 tests, including a
  4-character L3 party vs. 3 goblins end-to-end run).

**Task 7 — SRD content externalisation**
- New module: `src/rules_engine/srd_loader.py` (~150 LOC).
- One-off dumper `scripts/dump_srd.py` writes 19 JSON files into
  `data/srd_3.5/` (spells × 10 levels, feats, races, classes, monsters,
  magic items × 2, poisons/diseases, gems/art, encounter tables).
- 229 spells, 36 feats, 9 races, 11 classes, 27+ monsters, 50+ wondrous
  items, 5 rings, 12 poisons/diseases, 53 gems, 51 art objects, 8 terrain
  encounter tables surfaced to JSON.
- Tests: `tests/rules_engine/test_srd_loader.py` (12 tests).
- Existing tests untouched and still pass.

**Task 8 — DMG_BUILD_SITE Tier 0–3 audit**
- All 47 Tier 0–3 tasks marked `[x]` (shipped) or `[~]` (shipped with
  fewer entries than the spec target).
- Residual content backlog: T-010 (`ChallengeRating` dataclass wrapper),
  T-034 (gem table 53/60), T-035 (art-object table 51/100).  No
  *functional* Tier 0–3 work is missing.
- Tests: `tests/rules_engine/test_dmg_audit.py` (34 tests pinning each
  task's symbol presence and registry minimum size).

**Task 9 — Terminal Overseer UI**
- Files: `src/overseer_ui/{__init__.py,overseer.py}` (~280 LOC).
- `OverseerQueue` exposes `approve` / `reject` / `edit` / `skip` and
  appends every decision to `logs/overseer-YYYY-MM-DD.jsonl`.
- `OverseerUI` is a stdin/stdout REPL — no curses/prompt-toolkit
  dependency to keep CI footprint minimal.
- Tests: `tests/overseer_ui/test_overseer.py` (13 tests).

**Task 10 — `src/agent_orchestration/` build-out**
- Files: `scheduler.py`, `prompt_builder.py`, `result_parser.py`,
  `task_runner.py` (~720 LOC combined).
- `Scheduler` is a heap-backed priority queue with concurrency cap and
  retry handling.  `PromptBuilder` lazy-loads SRD context via
  `srd_loader` and trims to a token budget.  `ResultParser` extracts
  JSON (with markdown-fence tolerance) and validates per-task schemas.
- `LLMTaskRunner` glues the four together, accepting any sync-or-async
  completion fn so the same code wraps `LLMClient` (real) or test stubs.
- Tests: `tests/agent_orchestration/test_scheduler.py` (8),
  `test_prompt_builder.py` (6), `test_result_parser.py` (8),
  `test_task_runner.py` (6).

**Full-suite pass count (post-task-10): 2 800 tests passing.**
