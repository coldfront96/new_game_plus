# DMG Ingestion Task Tracker

Tracks progress of implementing D&D 3.5e Dungeon Master's Guide (DMG) core mechanics.

---

- [x] Phase 1: Environmental Hazards (Falling, Heat/Cold, Starvation) & Afflictions (Poisons/Diseases).
  - Implemented `src/rules_engine/hazards.py`: falling damage (1d6/10ft, max 20d6, Jump/Tumble mitigation), HeatDanger, ColdDanger, StarvationTracker (all with escalating Fort DCs), Poison and Disease dataclasses with full two-save sequences, plus registries for 6 SRD poisons and 6 SRD diseases.
  - 66 tests in `tests/rules_engine/test_hazards.py` — all pass. Full suite: 1748 tests pass.

- [x] Phase 2: Magic Item Engine (Enhancement bonuses, Wondrous Items).
  - Implemented `src/rules_engine/magic_items.py`: `MagicItemCategory` enum (10 categories), `BonusType` enum (8 bonus types), `MagicBonus` / `WondrousItem` dataclasses (slots=True), `MagicItemEngine` (add/remove worn items, aggregates non-stacking bonuses), `make_magic_weapon()` / `make_magic_armor()` factory functions (enhancement +1–+5 with SRD price formulae), `WONDROUS_ITEM_REGISTRY` (29 SRD items: belts, gauntlets, gloves, headbands, periapts, cloaks, amulets, resistance cloaks), `RING_REGISTRY` (5 rings of protection).
  - Updated `src/rules_engine/character_35e.py`: added `magic_item_engine` field; ability modifiers, AC (deflection + natural armor), and all three saves now incorporate `MagicItemEngine` bonuses while enforcing non-stacking rules.
  - Updated `src/rules_engine/equipment.py`: `get_armor_bonus()` / `get_shield_bonus()` now include `metadata["enhancement_bonus"]` from magic armour.
  - 113 tests in `tests/rules_engine/test_magic_items.py` — all pass. Full suite: 1861 tests pass.

- [ ] Phase 3: Treasure Hoard Generation Tables.

- [ ] Phase 4: Encounter Calculator (CR, EL, and XP Distribution).
