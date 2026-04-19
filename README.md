# New Game Plus — Game Design Document (GDD) v0.1

> **A Hybrid Simulation**: the emergent colony depth of *Dwarf Fortress* meets the voxel destruction of *Minecraft* and the ARPG loot progression of *Lootfiend*.

---

## Table of Contents

1. [Vision & Elevator Pitch](#1-vision--elevator-pitch)
2. [Core Gameplay Loop](#2-core-gameplay-loop)
3. [Architectural Pillars](#3-architectural-pillars)
   - [Voxel Terrain Engine](#31-voxel-terrain-engine)
   - [Entity-Component-System (ECS)](#32-entity-component-system-ecs)
   - [Loot & Progression Matrix](#33-loot--progression-matrix)
4. [Repository Structure](#4-repository-structure)
5. [Technical Stack](#5-technical-stack)
6. [Target Hardware & Performance Budget](#6-target-hardware--performance-budget)
7. [Data Models](#7-data-models)
8. [Running the Project Locally](#8-running-the-project-locally)
9. [Testing](#9-testing)
10. [Roadmap](#10-roadmap)
11. [Contributing](#11-contributing)
12. [License](#12-license)

---

## 1. Vision & Elevator Pitch

**New Game Plus** is a colony-survival-RPG in which you guide an ever-growing band of adventurers through a fully destructible, procedurally generated voxel world. Every colonist is an independently simulated agent with needs, skills, and an inventory of procedurally generated loot. The world reacts — cave-ins, flooding, monster invasions, and economic shifts are all emergent consequences of the simulation running beneath the surface.

**Key differentiators:**

| Feature | Inspiration | Our Twist |
|---|---|---|
| Fully destructible voxel world | Minecraft | 3D noise layers + geological strata |
| Colony AI with needs & jobs | Dwarf Fortress | ECS-driven state machines, 500+ simultaneous agents |
| ARPG loot & class progression | Lootfiend | Procedural prefix/suffix item generation, stat scaling per class |

---

## 2. Core Gameplay Loop

```
  ┌─────────────────────────────────────────────────────────────────────────┐
  │  MACRO LOOP (each in-game day)                                          │
  │                                                                         │
  │  ① Colonists wake → evaluate Needs (hunger, rest, safety, purpose)     │
  │  ② AI Task Scheduler assigns Jobs from the Job Queue                   │
  │  ③ Colonists execute Jobs (mine, build, craft, fight, rest, trade)     │
  │  ④ Voxel world updates (block changes, physics, light propagation)     │
  │  ⑤ Loot drops / crafting resolves → Progression Matrix updates stats  │
  │  ⑥ World events fire (raids, floods, discoveries) based on sim state   │
  │  ⑦ Player reviews colony state, adjusts priorities, sets new goals     │
  └─────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Colonist Lifecycle

1. **Spawn** — Colonists arrive with a randomly rolled class, base stats, and a starter item.
2. **Needs Loop** — A continuous priority queue manages: `Hunger → Rest → Safety → Social → Purpose`.
3. **Job Queue** — The player designates zones and tasks; the AI scheduler assigns work tokens.
4. **Combat** — Triggered by proximity to hostile entities; resolves via stat comparison + RNG.
5. **Levelling** — XP from jobs and kills feeds the Progression Matrix, unlocking class perks.
6. **Death / Legacy** — Colonists can die permanently; their loot persists in the world.

### 2.2 World Lifecycle

1. **Chunk Generation** — 16×16×256 voxel chunks generated on demand using 3D Perlin/Simplex noise.
2. **Geological Layers** — Surface biome → Stone → Ore veins → Deep caverns → Magma layer.
3. **Dynamic Events** — Collapses, water flow, fire spread, and seasonal changes alter the world.
4. **Player Influence** — Mining, construction, farming, and magic reshape chunk data in real time.

---

## 3. Architectural Pillars

### 3.1 Voxel Terrain Engine

**Location:** `src/terrain/`

| Component | Responsibility |
|---|---|
| `chunk_manager.py` | Loads/unloads chunks relative to active entities; LRU cache |
| `chunk_generator.py` | Procedural generation via 3D Simplex noise; geological strata |
| `block.py` | `Block` data class — id, material, durability, light emission |
| `physics_engine.py` | Gravity, fluid simulation, structural integrity checks |
| `light_engine.py` | Ray-cast sky light + point-light flood-fill |

**Chunk Lifecycle:**

```
Request chunk (x, z)
    ↓
Cache hit? → Deserialise from disk → Return
    ↓ (miss)
Generate heightmap with Simplex noise
    ↓
Apply geological layers (ore, cave carving)
    ↓
Serialise to disk + add to LRU cache → Return
```

### 3.2 Entity-Component-System (ECS)

**Location:** `src/ai_sim/`

| Component | Responsibility |
|---|---|
| `entity.py` | `Entity` base class — UUID, components dict, tag set |
| `components.py` | Pure data bags: `Position`, `Health`, `Needs`, `Inventory`, `Stats` |
| `systems.py` | Stateless processors: `NeedsSystem`, `PathfindingSystem`, `CombatSystem` |
| `state_machine.py` | Hierarchical FSM driving colonist behaviour |
| `job_scheduler.py` | Priority queue matching colonists to pending jobs |
| `pathfinding.py` | A* over voxel graph with dynamic obstacle updates |

**Entity State Machine (top-level states):**

```
IDLE ──► NEEDS_CRITICAL ──► SEEK_RESOURCE
  │                               │
  ▼                               ▼
ASSIGNED_JOB ◄───────────── RESOURCE_FOUND
  │
  ▼
EXECUTING_JOB ──► COMBAT (if threatened)
  │
  ▼
JOB_COMPLETE ──► IDLE
```

### 3.3 Loot & Progression Matrix

**Location:** `src/loot_math/`

| Component | Responsibility |
|---|---|
| `item.py` | `Item` base class — rarity, prefix, suffix, base stats |
| `loot_table.py` | Weighted RNG tables per biome/enemy/chest tier |
| `affix_registry.py` | All valid prefix/suffix modifiers and their stat formulae |
| `progression.py` | XP curves, class stat scaling, perk trees |
| `item_factory.py` | Composes full `Item` instances from loot tables + affixes |

**Item Generation Pipeline:**

```
Roll base item type (weapon/armour/trinket)
    ↓
Determine rarity (Common → Uncommon → Rare → Legendary) via weighted RNG
    ↓
Select 0–2 prefixes + 0–2 suffixes from AffixRegistry
    ↓
Scale all stats by: base_value × rarity_multiplier × player_level_factor
    ↓
Return fully constructed Item instance
```

---

## 4. Repository Structure

```
new_game_plus/
├── README.md                  ← You are here (GDD)
├── requirements.txt           ← Python runtime dependencies
├── setup.py                   ← Package metadata
├── .gitignore
│
├── src/                       ← All game source code
│   ├── __init__.py
│   ├── core/                  ← Shared utilities (logging, events, math helpers)
│   │   ├── __init__.py
│   │   ├── event_bus.py
│   │   ├── math_utils.py
│   │   └── registry.py
│   │
│   ├── terrain/               ← Voxel terrain engine
│   │   ├── __init__.py
│   │   ├── block.py
│   │   ├── chunk_manager.py
│   │   ├── chunk_generator.py
│   │   ├── physics_engine.py
│   │   └── light_engine.py
│   │
│   ├── ai_sim/                ← ECS + AI simulation layer
│   │   ├── __init__.py
│   │   ├── entity.py
│   │   ├── components.py
│   │   ├── systems.py
│   │   ├── state_machine.py
│   │   ├── job_scheduler.py
│   │   └── pathfinding.py
│   │
│   └── loot_math/             ← Loot & progression systems
│       ├── __init__.py
│       ├── item.py
│       ├── loot_table.py
│       ├── affix_registry.py
│       ├── progression.py
│       └── item_factory.py
│
├── assets/                    ← Raw game assets (not processed by engine at runtime)
│   ├── textures/              ← Block & entity sprite sheets
│   ├── sounds/                ← SFX / ambient audio
│   └── models/                ← 3D mesh sources
│
├── docs/                      ← Extended documentation
│   ├── gdd/                   ← Detailed GDD chapters
│   └── api/                   ← Auto-generated API reference
│
└── tests/                     ← Automated test suite (pytest)
    ├── __init__.py
    ├── core/
    ├── terrain/
    │   └── test_block.py
    ├── ai_sim/
    │   └── test_entity.py
    └── loot_math/
        └── test_item.py
```

---

## 5. Technical Stack

| Layer | Technology | Rationale |
|---|---|---|
| **Language** | Python 3.11+ | Rapid prototyping; easy FFI to C extensions later |
| **Data models** | Python `dataclasses` + `uuid` | Zero-overhead POD structs, engine-agnostic |
| **Noise generation** | `noise` (Perlin/Simplex) | Battle-tested procedural generation |
| **Pathfinding** | Custom A* on voxel graph | Full control over heuristics and dynamic obstacles |
| **Serialisation** | `msgpack` / `json` | Fast chunk serialisation to disk |
| **Testing** | `pytest` | Lightweight, discoverable unit tests |
| **Future rendering** | Godot 4 (GDExtension) or Unity DOTS | Swap rendering backend without touching simulation layer |

---

## 6. Target Hardware & Performance Budget

| Resource | Target Spec | Budget |
|---|---|---|
| GPU | NVIDIA RTX 4070 Ti Super (16 GB VRAM) | Full GPU-driven chunk mesh upload |
| System RAM | 64 GB | Up to 4 096 active chunks in LRU cache |
| Storage | NVMe SSD | < 5 ms chunk load from disk |
| CPU | High-end desktop (≥ 8 cores) | 500 simultaneous entity ticks at 20 TPS |

**Performance Rules:**

- All simulation systems must be **O(n)** or better per tick.
- Chunk generation runs in a **background thread pool**; never blocks the main tick loop.
- The ECS forbids global state — systems operate on component arrays only.
- Loot generation must complete in **< 1 ms** per item.

---

## 7. Data Models

The three foundational data classes are located in:

| Class | File |
|---|---|
| `Block` | `src/terrain/block.py` |
| `Entity` | `src/ai_sim/entity.py` |
| `Item` | `src/loot_math/item.py` |

See each file for full docstrings and usage examples.

---

## 8. Running the Project Locally

### Prerequisites

- Python 3.11 or later
- `pip` (comes with Python)
- `git`

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/coldfront96/new_game_plus.git
cd new_game_plus

# 2. Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows PowerShell

# 3. Install runtime and development dependencies
pip install -r requirements.txt

# 4. Verify the installation by running the test suite
pytest tests/ -v
```

### Quick Smoke-Test

```python
from src.terrain.block import Block, Material
from src.ai_sim.entity import Entity
from src.loot_math.item import Item, Rarity

stone = Block(block_id=1, material=Material.STONE, durability=100)
colonist = Entity(name="Aldric")
sword = Item(name="Iron Sword", rarity=Rarity.COMMON, base_damage=12)

print(stone)
print(colonist)
print(sword)
```

---

## 9. Testing

```bash
# Run all tests
pytest tests/ -v

# Run only terrain tests
pytest tests/terrain/ -v

# Run with coverage report
pytest tests/ --cov=src --cov-report=term-missing
```

Tests live in `tests/` mirroring the `src/` module layout. Each module must maintain ≥ 80 % line coverage before merging to `main`.

---

## 10. Roadmap

| Milestone | Description | Status |
|---|---|---|
| **M0 — Foundation** | Repo scaffold, data models, test harness | 🟡 In Progress |
| **M1 — Terrain Alpha** | Chunk generation, block CRUD, basic physics | ⬜ Planned |
| **M2 — ECS Alpha** | Entity ticking, needs loop, A* pathfinding | ⬜ Planned |
| **M3 — Loot Alpha** | Item generation pipeline, affix registry | ⬜ Planned |
| **M4 — Integration** | Colony loop end-to-end, basic rendering hook | ⬜ Planned |
| **M5 — Content** | Biomes, classes, enemy types, events | ⬜ Planned |

---

## 11. Contributing

1. Fork the repository and create a feature branch (`git checkout -b feature/my-feature`).
2. Write tests for every new data model or system.
3. Ensure `pytest tests/` passes with zero failures.
4. Open a pull request with a clear description referencing the relevant GDD section.

Code style: [PEP 8](https://peps.python.org/pep-0008/) enforced via `flake8`.

---

## 12. License

This project is licensed under the **MIT License** — see `LICENSE` for details.