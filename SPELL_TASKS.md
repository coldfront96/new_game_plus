# D&D 3.5e Spell Registry — Task Tracker

This file tracks the chunked ingestion of SRD spells into the rules engine. Each
phase must pass `pytest tests/rules_engine/test_magic.py` before the next phase
begins. Do not attempt to ingest multiple phases in a single pass — token
truncation risks mechanical impurity.

## Phases

- [ ] Phase 1: Wizard/Sorcerer Arcane Spells (Levels 0–3) + Tests.
- [ ] Phase 2: Wizard/Sorcerer Arcane Spells (Levels 4–9) + Tests.
- [ ] Phase 3: Cleric & Paladin Divine Spells + Tests.
- [ ] Phase 4: Druid & Ranger Nature Spells + Tests.
- [ ] Phase 5: Bard Arcane Spells + Tests.

## Completion Notes

_(Populated as each phase is checked off — include spell count and any deviations.)_
