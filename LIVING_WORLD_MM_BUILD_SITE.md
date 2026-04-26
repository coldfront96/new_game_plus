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
