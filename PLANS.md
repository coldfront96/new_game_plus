# Project Alignment Plan

This document captures the work needed to align the repository's
documentation and source-level descriptions with the authoritative
project definition for **New Game Plus**.

---

## 1. Authoritative Project Definition

**Project Title:** New Game Plus

**Core Objective:** Develop a high-fidelity, original game engine and
simulation built strictly on **Dungeons & Dragons 3.5e SRD** mechanics.
This is a standalone title focusing on **autonomous AI agency** within
a deep, procedural voxel world.

### Technical Landscape & Stack

- **Engine Philosophy:** A custom Python-based engine designed for
  high-performance Windows systems (Target: RTX 4070 Ti Super, 64 GB
  RAM).
- **Architecture:** Event-driven Entity Component System (ECS) with a
  heavy emphasis on memory efficiency. Every data model (`Block`,
  `Entity`, `Item`, etc.) uses `@dataclass(slots=True)` to handle
  millions of instances within the 64 GB RAM budget.
- **Rules Engine:** Strict adherence to the 3.5e ruleset, where
  mechanics like BAB, AC, saving throws, and skill checks serve as the
  "physical laws" of the simulation.
- **World Generation:** Procedural voxel terrain featuring geological
  strata (Stone, Dirt, Grass) and stratified ore distribution (Iron,
  Gold, etc.) generated via Simplex/Perlin noise.
- **AI Integration:** Designed to interface with local/offline LLMs
  (e.g. DeepSeek, Llama) to act as autonomous agents that perform
  world-building, coding, and in-game decision-making.

### Current Project Structure

- `src/rules_engine/` — 3.5e character math, dice systems, combat resolvers.
- `src/terrain/` — Voxel chunk management, block definitions, procedural heightmap generation.
- `src/ai_sim/` — Event-driven systems for combat, mining, needs (hunger/rest), physics (gravity), 3D A* pathfinding.
- `src/core/` — Event bus for decoupled system communication, mathematical utilities.

### Visual & Mechanical Goals

Simulation logic is in Python; the long-term goal is visual fidelity
comparable to modern high-end titles (such as Baldur's Gate 3) through
a GPU-accelerated rendering pipeline that visualises the complex
underlying 3.5e data.

### Guiding Instruction

Treat this as a professional software architecture project. Use the
existing 3.5e SRD data and the ECS framework as the foundation for all
future code generation. **Avoid** referencing other "hybrid" game
titles; focus on the unique constraints of this custom engine.

---

## 2. Gap Analysis — What Currently Conflicts With the Definition

| File | Issue |
|---|---|
| `README.md` | Framed as a "hybrid" of Dwarf Fortress × Minecraft × Lootfiend; target OS listed as Ubuntu; subtitle is "colony-survival RPG"; comparison tables reference other game titles. |
| `setup.py` (line 16) | Package `description` reads *"Hybrid colony-simulation RPG engine — Dwarf Fortress × Minecraft × Lootfiend"*. |
| `src/overseer_ui/__init__.py` | Docstring OK in spirit but can be sharpened to reflect the autonomous-AI-agency framing. |
| `src/ai_sim/entity.py` | Module docstring uses `colonist` as the canonical example — should be `agent` / `NPC` / `character` to match the autonomous-AI-agency framing. |
| `src/ai_sim/components.py` | `NeedType` and `Needs` docstrings describe "colonist basic needs"; `Stats` docstring references "colonist or creature". |
| `src/loot_math/item.py` (line 182) | `level_requirement` docstring says "Minimum colonist level". |
| Tests (`tests/ai_sim/test_entity.py`, etc.) | Use the literal tag string `"colonist"` — arbitrary test fixtures, can remain or be updated for internal consistency. |

No source logic needs to change. All changes are documentation /
docstring / package-metadata alignment. The `Overseer` module remains
valid: it is an approval gate for LLM-generated artefacts, which fits
the autonomous-AI-agency model.

---

## 3. Execution Plan — Parts

| Part | Action | Target | Scope |
|------|--------|--------|-------|
| A | Rewrite `README.md` | `README.md` | Drop hybrid framing, remove DF/Minecraft/Lootfiend comparison tables, set Windows as primary target, add BG3-fidelity rendering goal, restructure pillars around the 3.5e-as-physics philosophy. |
| B | Update package description | `setup.py` | Replace line 16 `description=` string with a 3.5e-SRD-focused summary. |
| C | Refresh Overseer module docstring | `src/overseer_ui/__init__.py` | Reframe as "human approval gate for autonomous LLM agents operating under 3.5e rules." |
| D | Replace "colonist" → "agent / NPC / character" | `src/ai_sim/entity.py` | Docstring only; variable names in examples stay generic. |
| E | Same replacement in Needs/Stats docstrings | `src/ai_sim/components.py` | Docstring only. |
| F | "colonist level" → "character level" | `src/loot_math/item.py:182` | Docstring only. |
| G | Run `pytest tests/ -v` | — | Confirm no regression; these are doc-only changes. |
| H | Commit + push | branch `claude/explore-new-repo-ahk5V` | Single commit with a clear alignment message. |

---

## 4. Out of Scope (For Now)

- Renaming any source identifiers, tests, or tag literals (e.g. the
  `"colonist"` string tag in `tests/ai_sim/test_entity.py`).
- Rewriting the D&D 3.5e SRD data under `data/srd_3.5/` — separate
  content-population milestone (M0.5).
- Implementing the GPU-accelerated rendering pipeline (future
  milestone, not part of doc alignment).
- Changing the agent orchestration / Overseer module surface area.

---

## 5. README Rewrite — Draft Outline

The rewritten `README.md` should follow this structure:

1. **Title & Pitch** — *"A high-fidelity, original game engine and
   simulation built strictly on D&D 3.5e SRD mechanics, focused on
   autonomous AI agency within a deep, procedural voxel world."*
2. **Core Objective** — verbatim from the authoritative definition.
3. **Design Philosophy** — 3.5e rules as the physical laws of the
   simulation; no hard-coded mechanics.
4. **Architectural Pillars**
   - 3.5e Ruleset Engine (primary)
   - Voxel Terrain Engine
   - Event-Driven ECS Simulation
   - Autonomous LLM Agent Layer
   - Overseer Approval Interface
5. **Target Hardware & Performance Budget** — Windows, RTX 4070 Ti
   Super (16 GB VRAM), 64 GB RAM. Remove Ubuntu-primary framing.
6. **Visual Fidelity Goal** — GPU-accelerated pipeline, BG3-comparable.
7. **Repository Structure** — mirror the actual `src/` tree.
8. **Data Models** — `Block`, `Entity`, `Item`, `AgentTask`,
   `Character35e`, all `slots=True`.
9. **Running the Project Locally** — Windows-first, Linux-compatible.
10. **Testing** — `pytest`.
11. **Roadmap** — M0 through M8, re-framed around the 3.5e engine.
12. **Contributing** / **License**.

Remove entirely: any comparison table to *Dwarf Fortress*, *Minecraft*,
or *Lootfiend*; "colony-survival RPG" phrasing; the Ubuntu-first
install section (keep Linux as a secondary note).

---

## 6. Acceptance Criteria

- No file in the repository contains the strings `Dwarf Fortress`,
  `Minecraft`, `Lootfiend`, or `hybrid` in any descriptive (non-code)
  context.
- `README.md` opens with the authoritative project definition.
- `setup.py` package `description` reflects the 3.5e-SRD focus.
- All docstrings referencing "colonist" as the canonical entity have
  been updated to `agent` / `NPC` / `character`.
- `pytest tests/` still passes with zero failures.
- Changes land on branch `claude/explore-new-repo-ahk5V` in a single
  cohesive commit.
