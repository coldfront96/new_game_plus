# PHASE_6_GENESIS_TASKS.md — Genesis & Campaign Matrix

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
| Multi-Screen Textual TUI | `src/overseer_ui/textual_app.py` | ✅ Shipped |
| LLM Context Manager | `src/agent_orchestration/context_manager.py` | ✅ Shipped |
| Chunk Manager | `src/terrain/chunk_manager.py` | ✅ Shipped |
| Chunk Generator | `src/terrain/chunk_generator.py` | ✅ Shipped |
| World Tick Orchestrator | `src/world_sim/world_tick.py` | ✅ Shipped |
| Campaign Session | `src/game/campaign.py` | ✅ Shipped |
| Biome Enums | `src/world_sim/biome.py` | ✅ Shipped |
| Entity Schema | `src/ai_sim/entity.py` | ✅ Shipped |
| SRD Monster Data (446 entries) | `data/srd_3.5/monsters/` | ✅ Shipped |
| Campaign Setup Wizard | `src/overseer_ui/setup_wizard.py` | ✅ Complete |
| Genesis Protocol | `src/world_sim/genesis.py` | ✅ Complete |
| World Builder Interface | `src/overseer_ui/world_builder.py` | ✅ Complete |
| JIT Backstory Memory Hook | `src/agent_orchestration/backstory_loader.py` | ✅ Complete |
| Campaign Data Directory | `data/campaigns/` | ✅ Complete |

---

## 1. Scope

Phase 6 builds the player-facing campaign entry layer that sits above the core
simulation. Four subsystems gate access to the existing Phase 5 game loops by
letting the player choose, generate, or hand-craft the world before any
simulation tick executes.

| # | Subsystem | Short Name | New / Modified Modules |
|---|-----------|------------|------------------------|
| A | Campaign Setup Wizard | setup-wizard | `src/overseer_ui/setup_wizard.py` *(new)* |
| B | Genesis Protocol | genesis | `src/world_sim/genesis.py` *(new)* |
| C | World Builder Interface | world-builder | `src/overseer_ui/world_builder.py` *(new)* |
| D | JIT Backstory Memory Hook | jit-backstory | `src/ai_sim/entity.py`, `src/agent_orchestration/context_manager.py` |

---

## 2. Dependency Map

```
Tier 0  ──────────────────────────────────────────────────────────────────
         [PH6-001]  CampaignWizardState dataclass + three UI buttons
         [PH6-003]  fast_forward_simulation() headless tick engine
         [PH6-005]  WorldBuilderState dataclass + ASCII paint grid
         [PH6-008]  Entity.deep_lore_filepath optional field
                │
Tier 1  ────────▼─────────────────────────────────────────────────────────
         [PH6-002]  Premade Modules button → data/campaigns/ → campaign.py   (deps: PH6-001)
         [PH6-004]  True Random Sandbox button → fast_forward_simulation      (deps: PH6-001, PH6-003)
         [PH6-006]  Entity Dropper menu inside World Builder                  (deps: PH6-005)
         [PH6-009]  JIT context_manager dialogue load/clear hook              (deps: PH6-008)
                │
Tier 2  ────────▼─────────────────────────────────────────────────────────
         [PH6-007]  Compile Campaign button → JSON schema write               (deps: PH6-005, PH6-006)
```

---

## 3. Task Tiers

### Tier 0 — Foundation (No Dependencies)

| Task | Title | Subsystem | Status |
|------|-------|-----------|--------|
| PH6-001 | CampaignWizardState dataclass + three UI buttons | setup-wizard | ✅ Complete |
| PH6-003 | fast_forward_simulation() headless tick engine | genesis | ✅ Complete |
| PH6-005 | WorldBuilderState dataclass + ASCII paint grid | world-builder | ✅ Complete |
| PH6-008 | Entity.deep_lore_filepath optional field | jit-backstory | ✅ Complete |

---

### Tier 1 — Integration (Depends on Tier 0)

| Task | Title | Subsystem | Status |
|------|-------|-----------|--------|
| PH6-002 | Premade Modules button → data/campaigns/ → campaign.py | setup-wizard | ✅ Complete |
| PH6-004 | True Random Sandbox button → fast_forward_simulation | setup-wizard | ✅ Complete |
| PH6-006 | Entity Dropper menu inside World Builder | world-builder | ✅ Complete |
| PH6-009 | JIT context_manager dialogue load/clear hook | jit-backstory | ✅ Complete |

---

### Tier 2 — Capstone (Depends on Tier 1)

| Task | Title | Subsystem | Status |
|------|-------|-----------|--------|
| PH6-007 | Compile Campaign button → playable JSON schema | world-builder | ✅ Complete |

---

## 4. Effort Summary

| Tier | Task Count | S Tasks | M Tasks | L Tasks | Estimated Total |
|------|-----------|---------|---------|---------|-----------------|
| 0 — Foundation | 4 | 2 | 2 | 0 | ~2 days |
| 1 — Integration | 4 | 0 | 4 | 0 | ~4 days |
| 2 — Capstone | 1 | 0 | 1 | 0 | ~1 day |
| **Total** | **9** | **2** | **7** | **0** | **~7 dev-days** |

> Tier 0 tasks (PH6-001, PH6-003, PH6-005, PH6-008) are fully independent and may be developed in parallel across four engineers.
> Within Tier 1, PH6-002 and PH6-004 share the same target file (`setup_wizard.py`) and must be sequenced; PH6-006 and PH6-009 are mutually independent and can run in parallel.
> PH6-007 is the single capstone task — it must land after PH6-005 and PH6-006 are both stable and tested.
