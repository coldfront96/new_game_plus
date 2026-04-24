# DMG Ingestion Task Tracker

Tracks progress of implementing D&D 3.5e Dungeon Master's Guide (DMG) core mechanics.

---

- [x] Phase 1: Environmental Hazards (Falling, Heat/Cold, Starvation) & Afflictions (Poisons/Diseases).
  - Implemented `src/rules_engine/hazards.py`: falling damage (1d6/10ft, max 20d6, Jump/Tumble mitigation), HeatDanger, ColdDanger, StarvationTracker (all with escalating Fort DCs), Poison and Disease dataclasses with full two-save sequences, plus registries for 6 SRD poisons and 6 SRD diseases.
  - 66 tests in `tests/rules_engine/test_hazards.py` — all pass. Full suite: 1748 tests pass.

- [ ] Phase 2: Magic Item Engine (Enhancement bonuses, Wondrous Items).

- [ ] Phase 3: Treasure Hoard Generation Tables.

- [ ] Phase 4: Encounter Calculator (CR, EL, and XP Distribution).
