# EDGE_SYSTEMS_BUILD_SITE.md — Final 3.5e Edge Mechanics Build Plan

## 1. Scope

This document tracks the **final remaining D&D 3.5e mechanics** drawn from the
Player's Handbook (PHB) and Dungeon Master's Guide (DMG) that are not covered by
the previously-shipped phases or by `DMG_BUILD_SITE.md` / `SPELL_TASKS.md`.
These are the "edge" subsystems — the connective tissue between character
sheets, world generation, and the multiverse — that have to land before the
3.5e core can be considered feature-complete.

**Already shipped (out of scope here):**

| Module | File | Status |
|--------|------|--------|
| Environmental Hazards (Falling, Heat/Cold, Starvation, Poison, Disease) | `src/rules_engine/hazards.py` | ✅ Phase 1 |
| Magic Item Engine (Enhancement, Wondrous Items, Rings) | `src/rules_engine/magic_items.py` | ✅ Phase 2 |
| DMG Tier 0–3 (Objects, Traps, Consumables, Item Specials, Treasure, Encounters) | `src/rules_engine/{objects,traps,consumables,item_specials,treasure,encounter}.py` | ✅ DMG Phase 3A–3C |
| Character Core (Abilities, Skills, Feats, Race, Classes, Conditions, Combat) | `src/rules_engine/{abilities,skills,feat_engine,race,progression,conditions,combat}.py` | ✅ PHB Phase 1–2 |
| Spellcasting Engine (Slots, Preparation, Resolution) | `src/rules_engine/{spellcasting,magic}.py` | ✅ PHB Phase 2 |

**Remaining scope — this document:**

| # | Subsystem | Source | Key Chapters / Tables |
|---|-----------|--------|----------------------|
| 1 | **Encumbrance Physics** | PHB | Ch 9 (Carrying Capacity, Table 9-1; Load penalties Table 9-2) |
| 2 | **Linked Entity Orchestration** | PHB | Ch 3 Sorcerer/Wizard (Familiars), Ch 3 Druid (Animal Companion), Ch 3 Paladin (Special Mount) |
| 3 | **Multiclassing Laws** | PHB | Ch 3 "Multiclass Characters" (Favored Class, XP penalty rules) |
| 4 | **Prestige & NPC Classes** | DMG | Ch 4 (5 NPC classes), Ch 5 (Prestige Classes — Assassin, Arcane Archer, Blackguard, et al.) |
| 5 | **Settlement Demographics & Economics** | DMG | Ch 5 (Community size tables, GP Limit, Power Centers, NPC class distribution) |
| 6 | **Planar Physics** | DMG | Ch 5 (Planar traits — Gravity, Time, Magic, Elemental/Energy Dominance, Alignment) |

Each subsystem is broken into **Tier 0 base schemas** through **Tier 5 final
integrators**. Tasks are independently trackable; every `blockedBy` reference
resolves to an earlier task in this document or to a shipped module.

**Format conventions** (mirroring `DMG_BUILD_SITE.md`):

- Task IDs are prefixed `E-` (Edge).
- `Effort` ∈ {S = ≤½ day, M = 1–2 days, L = 3+ days}.
- `Subsystem` slugs: `encumbrance`, `linked-entity`, `multiclassing`,
  `npc-classes`, `prestige-classes`, `settlement`, `planar`.
- All schemas use `dataclasses` with `slots=True`; all enums are `enum.Enum`
  subclasses; all registries are module-level `dict[str, T]`.

---

## 1a. Cross-Reference Audit (2026-04-25)

The following modules in `src/rules_engine/` are the planned destinations for
the work in this document. None of them currently exist in full; partial
scaffolding (where present) is noted.

| Planned Module | Subsystems | Current State |
|----------------|------------|---------------|
| `src/rules_engine/encumbrance.py` | Encumbrance Physics | Not started |
| `src/rules_engine/linked_entity.py` | Familiars, Animal Companions, Special Mounts | Not started |
| `src/rules_engine/multiclass.py` | Multiclass Laws, Favored Class, XP Penalty | Not started |
| `src/rules_engine/npc_classes.py` | Commoner / Expert / Warrior / Adept / Aristocrat | Not started |
| `src/rules_engine/prestige_classes.py` | DMG Prestige Classes + Prerequisite Engine | Not started |
| `src/rules_engine/settlement.py` | Communities, GP Limit, NPC Demographics | Not started |
| `src/rules_engine/planar.py` | Plane registry, planar traits, transition engine | Not started |
| `src/ai_sim/master_minion.py` | Master/Minion turn-tracking integration | Not started |

Existing dependencies that this document **leans on** (must remain stable):

- `src/rules_engine/character_35e.py` — `Character35e` dataclass (used by
  multiclass, encumbrance, linked-entity).
- `src/rules_engine/race.py` — `Race` enum (used by Favored Class lookup).
- `src/rules_engine/abilities.py` — Ability score modifiers (used by
  Carrying Capacity).
- `src/rules_engine/equipment.py` — `Item` dataclass weight field (used by
  Encumbrance aggregator).
- `src/rules_engine/combat.py` — Initiative & turn order (used by
  Master/Minion orchestration).
- `src/rules_engine/spellcasting.py` — Spell slot tracking (used by
  Multiclass Spellcasting and Prestige caster-level continuation).
- `src/rules_engine/magic.py` — Spell resolution (used by Planar magic-trait
  modifier engine).

---
