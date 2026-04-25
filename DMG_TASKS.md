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

- [ ] Task 1: Scaffold `src/game/` package + `python -m new_game_plus` entry point.
  - Add `src/game/__init__.py`, `src/game/__main__.py`, `src/game/cli.py`.
  - argparse subcommands: `new-character`, `run-encounter`, `play`.
  - Wire into `setup.py` `entry_points` so `new-game-plus` is on PATH.

- [ ] Task 2: Text-mode character-creation wizard.
  - Prompt flow: race → class → ability scores (4d6-drop-lowest **and**
    point-buy) → skills → feats → starting equipment.
  - All choices validated against existing `RaceRegistry`, class definitions,
    `AbilityRegistry`, `SkillSystem`, `FeatEngine`, `EquipmentManager`.
  - Output: a fully-populated `Character35e` instance.

- [ ] Task 3: Party / character persistence.
  - JSON serializer/deserializer for `Character35e` (and dependent state:
    `MagicItemEngine`, `ConditionManager`, `XPManager`).
  - `saves/` directory; `load_party(name)` / `save_party(name, party)`.
  - Round-trip test: save → load → assert equality on AC, HP, saves, slots.

- [ ] Task 4: `TurnController` with initiative + action economy.
  - Roll initiative for all combatants, build turn order.
  - Per-turn loop using existing `ActionTracker` (standard / move / swift /
    full-round / free) with proper reset on new turn.
  - Round counter, condition duration tick, end-of-turn save handling.

- [ ] Task 5: Wire combat event loop through `CombatSystem`.
  - Player input → `AttackIntent` / spell-cast / move / use-item events on
    the existing `EventBus`.
  - Print per-turn results (hit/miss, damage, conditions, death).
  - Detect victory / total-party-defeat / flee and exit cleanly.

- [ ] Task 6: End-to-end party-vs-encounter integration test.
  - Build a 4-character L3 party via Task 2 helpers.
  - Generate an encounter via existing `build_encounter()`.
  - Run full cycle: spell → attack → condition → death → XP award →
    `generate_treasure_hoard()` → loot distribution.
  - Assert the encounter terminates and XP/treasure are sane.

---

## Phase B — Content Externalisation

- [ ] Task 7: Populate `data/srd_3.5/` with JSON + loader.
  - Extract spell definitions from `src/rules_engine/magic.py` to
    `data/srd_3.5/spells/*.json`.
  - Same for feats, races, class progressions, monsters, magic items,
    poisons/diseases, gems/art, encounter tables.
  - Add `src/rules_engine/srd_loader.py` that builds the in-memory registries
    from the JSON at import time.
  - Existing tests must still pass unchanged.

---

## Phase C — Audit & Cleanup

- [ ] Task 8: Audit `DMG_BUILD_SITE.md` Tier 0–3 against shipped modules.
  - Cross-reference each `T-NNN` against `src/rules_engine/*.py`
    (`objects.py`, `traps.py`, `consumables.py`, `item_specials.py`,
    `environment.py`, `encounter_extended.py`, `magic_item_engine.py`).
  - Mark shipped tasks `[x]` in `DMG_BUILD_SITE.md`; produce a residual list
    of any Tier 0–3 tasks that are still actually missing.

---

## Phase D — Agent Layer

- [ ] Task 9: Minimal terminal Overseer UI.
  - Replace `src/overseer_ui/__init__.py` stub with a curses- or
    prompt-toolkit-based approve/reject queue backed by real `AgentTask`
    objects.
  - Persistent session log to `logs/overseer-YYYY-MM-DD.jsonl`.

- [ ] Task 10: Flesh out `src/agent_orchestration/`.
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
