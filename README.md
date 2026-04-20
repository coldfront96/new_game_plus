# New Game Plus — Game & AI Design Document (GDD) v0.2

> **A Hybrid Simulation**: the emergent colony depth of *Dwarf Fortress* meets the voxel destruction of *Minecraft*, the ARPG loot progression of *Lootfiend*, and an autonomous AI-driven open world powered by **D&D 3.5e rules** — all orchestrated by a local multi-agent LLM pipeline running entirely on consumer hardware.

---

## Table of Contents

1. [Vision & Elevator Pitch](#1-vision--elevator-pitch)
2. [Core Gameplay Loop](#2-core-gameplay-loop)
3. [Architectural Pillars](#3-architectural-pillars)
   - [Voxel Terrain Engine](#31-voxel-terrain-engine)
   - [Entity-Component-System (ECS)](#32-entity-component-system-ecs)
   - [Loot & Progression Matrix](#33-loot--progression-matrix)
   - [3.5e Ruleset Engine](#34-35e-ruleset-engine)
   - [Multi-Agent Orchestration Layer](#35-multi-agent-orchestration-layer)
   - [The Overseer Interface](#36-the-overseer-interface)
4. [Autonomous Agent Core Loop](#4-autonomous-agent-core-loop)
5. [Local LLM Integration Strategy](#5-local-llm-integration-strategy)
6. [Repository Structure](#6-repository-structure)
7. [Technical Stack](#7-technical-stack)
8. [Target Hardware & Performance Budget](#8-target-hardware--performance-budget)
9. [Data Models](#9-data-models)
10. [Running the Project Locally](#10-running-the-project-locally)
11. [Running the Multi-Agent System on Ubuntu](#11-running-the-multi-agent-system-on-ubuntu)
12. [Testing](#12-testing)
13. [Roadmap](#13-roadmap)
14. [Contributing](#14-contributing)
15. [License](#15-license)

---

## 1. Vision & Elevator Pitch

**New Game Plus** is a colony-survival-RPG in which you guide an ever-growing band of adventurers through a fully destructible, procedurally generated voxel world. Every colonist is an independently simulated agent with needs, skills, and an inventory of procedurally generated loot. The world reacts — cave-ins, flooding, monster invasions, and economic shifts are all emergent consequences of the simulation running beneath the surface.

**What makes this different:** The game is driven by an **autonomous, offline multi-agent AI pipeline** built on local LLMs (DeepSeek, Llama) that generate dungeons, roll NPC stat blocks, write procedural lore, and even produce engine code — all governed by the **D&D 3.5e System Reference Document** as its canonical ruleset. A human **Overseer** approves, rejects, or tweaks every piece of AI-generated content before it enters the live world.

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

### 3.4 3.5e Ruleset Engine

**Location:** `src/rules_engine/`

The ruleset engine is the **single source of truth** for all game mechanics. It parses structured JSON files from `data/srd_3.5/` at startup and exposes the SRD rules as validated Python objects.

| Component | Responsibility |
|---|---|
| `character_35e.py` | `Character35e` base class — ability scores, HP, BAB, saves, AC (all SRD-derived) |
| `ability_scores.py` | Modifier calculations, generation methods (4d6-drop-lowest, point-buy) |
| `combat.py` | Attack rolls, damage, critical hits, initiative, AoO resolution |
| `skills.py` | Skill check resolution, synergy bonuses, class/cross-class costs |
| `spells.py` | Spell slot management, save DCs, spell resistance |
| `srd_loader.py` | JSON/Markdown parser that hydrates the above from `data/srd_3.5/` files |

**Design Rule:** No game mechanic may be hard-coded. Everything is data-driven from the SRD files, so the engine can be extended to other d20 systems (Pathfinder, 5e) by swapping the data directory.

### 3.5 Multi-Agent Orchestration Layer

**Location:** `src/agent_orchestration/`

The orchestration layer manages a queue of `AgentTask` objects dispatched to local LLM instances.

| Component | Responsibility |
|---|---|
| `agent_task.py` | `AgentTask` data class — prompt, token budget, priority, lifecycle status |
| `scheduler.py` | Priority queue + round-robin dispatcher across available model slots |
| `prompt_builder.py` | Template engine for constructing model prompts with SRD context injection |
| `result_parser.py` | Validates and deserialises structured JSON responses from agents |
| `context_manager.py` | Sliding-window context chunking to stay within VRAM token limits |
| `model_registry.py` | Tracks available local models, their VRAM footprint, and capabilities |

**Agent Dispatch Pipeline:**

```
AgentTask enters priority queue
    ↓
Scheduler picks highest-priority PENDING task
    ↓
PromptBuilder assembles prompt + SRD context (≤ max_tokens)
    ↓
ContextManager chunks if prompt exceeds model window
    ↓
Local LLM processes prompt → returns JSON payload
    ↓
ResultParser validates output against expected schema
    ↓
Task marked COMPLETED (or FAILED → retry / escalate to Overseer)
```

### 3.6 The Overseer Interface

**Location:** `src/overseer_ui/`

The Overseer is the human-in-the-loop control surface. It provides:

| Component | Responsibility |
|---|---|
| `dashboard.py` | Real-time view of the agent task queue, model utilisation, and world state |
| `approval_gate.py` | Review/approve/reject AI-generated content before it enters the live world |
| `parameter_panel.py` | Tune generation parameters (temperature, top-k, token budgets) at runtime |
| `session_log.py` | Persistent audit trail of every AI decision and Overseer override |

**Approval Flow:**

```
AI agent completes task → result queued for Overseer review
    ↓
Overseer inspects generated content (dungeon, NPC, lore, code)
    ↓
APPROVE → content injected into live world / codebase
REJECT  → task re-queued with Overseer's correction notes
EDIT    → Overseer modifies result inline, then approves
```

---

## 4. Autonomous Agent Core Loop

The multi-agent system operates in a continuous cycle that mirrors the game's macro loop but runs asynchronously:

```
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │  AGENT CORE LOOP (runs in background, decoupled from game tick)             │
  │                                                                             │
  │  ① World State Snapshot — serialise current game state to JSON context     │
  │  ② Task Generation — engine identifies gaps (empty dungeons, unnamed NPCs) │
  │  ③ Task Queue — AgentTask objects created with priority + token budget     │
  │  ④ Scheduler Dispatch — tasks routed to available local LLM model slots   │
  │  ⑤ Prompt Assembly — SRD context injected, chunked to fit VRAM budget     │
  │  ⑥ Model Inference — local LLM generates structured JSON response         │
  │  ⑦ Result Validation — output parsed, schema-checked, rule-validated      │
  │  ⑧ Overseer Gate — human reviews, approves/rejects/edits result           │
  │  ⑨ World Integration — approved content merged into live game state        │
  │  ⑩ Audit Log — full trace written to session log                          │
  └─────────────────────────────────────────────────────────────────────────────┘
```

**Key Design Constraints:**

- The agent loop **never blocks** the game simulation tick.
- All inter-module communication is via the `EventBus` (pub/sub) — no direct imports between subsystems.
- Every AI-generated artefact passes through the Overseer approval gate before it affects the live world.
- Tasks that exceed the VRAM token budget are automatically chunked by the `ContextManager`.

---

## 5. Local LLM Integration Strategy

### 5.1 Hardware Envelope

| Resource | Spec | Constraint |
|---|---|---|
| GPU | NVIDIA RTX 4070 Ti Super | **16 GB VRAM — hard cap** |
| System RAM | 64 GB DDR5 | Shared between game sim + model inference |
| OS | Ubuntu Linux 22.04+ | CUDA 12.x + cuDNN required |

### 5.2 Model Selection

| Slot | Model Family | Parameter Size | Quantisation | VRAM Est. |
|---|---|---|---|---|
| **Code Gen** | DeepSeek Coder v2 | 6.7B | GPTQ 4-bit | ~5 GB |
| **World Gen** | Llama 3 | 8B | GGUF Q4_K_M | ~6 GB |
| **Lore / NPC** | Mistral | 7B | AWQ 4-bit | ~5 GB |

> **Rule:** No more than one model loaded at a time to stay under 16 GB. The scheduler swaps models on-demand using a least-recently-used eviction policy.

### 5.3 Context-Window Management

- **Max context per task:** configurable via `AgentTask.max_tokens` (default 2048).
- **SRD injection:** the `PromptBuilder` selects only the SRD excerpts relevant to the task type (e.g. only weapon tables for an item generation task).
- **Prompt chunking:** if the assembled prompt exceeds the model's native context window, the `ContextManager` splits it into sequential chunks with overlap, processes each, and stitches the results.

### 5.4 API Isolation

Each model is wrapped behind a **strict API boundary**:

```python
class LocalModelAPI:
    """Abstract interface — all model backends implement this."""
    def load(self, model_path: str, vram_budget_mb: int) -> None: ...
    def generate(self, prompt: str, max_tokens: int) -> str: ...
    def unload(self) -> None: ...
```

No game code ever calls a model directly. All inference requests flow through `AgentTask → Scheduler → LocalModelAPI`.

---

## 6. Repository Structure

```
new_game_plus/
├── README.md                  ← You are here (GDD + AI Design Doc)
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
│   ├── loot_math/             ← Loot & progression systems
│   │   ├── __init__.py
│   │   ├── item.py
│   │   ├── loot_table.py
│   │   ├── affix_registry.py
│   │   ├── progression.py
│   │   └── item_factory.py
│   │
│   ├── rules_engine/          ← D&D 3.5e SRD ruleset engine
│   │   ├── __init__.py
│   │   ├── character_35e.py   ← Character35e base class (slots=True)
│   │   ├── ability_scores.py
│   │   ├── combat.py
│   │   ├── skills.py
│   │   ├── spells.py
│   │   └── srd_loader.py
│   │
│   ├── agent_orchestration/   ← Multi-agent LLM orchestration layer
│   │   ├── __init__.py
│   │   ├── agent_task.py      ← AgentTask data class (slots=True)
│   │   ├── scheduler.py
│   │   ├── prompt_builder.py
│   │   ├── result_parser.py
│   │   ├── context_manager.py
│   │   └── model_registry.py
│   │
│   └── overseer_ui/           ← Human-in-the-loop Overseer interface
│       ├── __init__.py
│       ├── dashboard.py
│       ├── approval_gate.py
│       ├── parameter_panel.py
│       └── session_log.py
│
├── data/                      ← Static game data (not code)
│   └── srd_3.5/               ← D&D 3.5e SRD structured data (JSON/Markdown)
│       ├── README.md
│       ├── ability_scores.json
│       ├── races.json
│       ├── classes.json
│       ├── skills.json
│       ├── feats.json
│       ├── spells.json
│       ├── equipment.json
│       └── monsters.json
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
    ├── loot_math/
    │   └── test_item.py
    ├── rules_engine/
    │   └── test_character_35e.py
    └── agent_orchestration/
        └── test_agent_task.py
```

---

## 7. Technical Stack

| Layer | Technology | Rationale |
|---|---|---|
| **Language** | Python 3.11+ | Rapid prototyping; easy FFI to C extensions later |
| **Data models** | Python `dataclasses` + `uuid` | Zero-overhead POD structs, engine-agnostic |
| **Memory opt.** | `@dataclass(slots=True)` | Prevents `__dict__` allocation on perf-critical models |
| **Noise generation** | `noise` (Perlin/Simplex) | Battle-tested procedural generation |
| **Pathfinding** | Custom A* on voxel graph | Full control over heuristics and dynamic obstacles |
| **Serialisation** | `msgpack` / `json` | Fast chunk serialisation to disk |
| **Testing** | `pytest` | Lightweight, discoverable unit tests |
| **Local LLM inference** | `llama-cpp-python` / `vllm` | GGUF/GPTQ/AWQ model loading with CUDA acceleration |
| **LLM models** | DeepSeek, Llama, Mistral | Offline, quantised to fit 16 GB VRAM |
| **Prompt management** | Custom template engine | SRD context injection + token-budget chunking |
| **Future rendering** | Godot 4 (GDExtension) or Unity DOTS | Swap rendering backend without touching simulation layer |

---

## 8. Target Hardware & Performance Budget

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

## 9. Data Models

The five foundational data classes are located in:

| Class | File |
|---|---|
| `Block` | `src/terrain/block.py` |
| `Entity` | `src/ai_sim/entity.py` |
| `Item` | `src/loot_math/item.py` |
| `AgentTask` | `src/agent_orchestration/agent_task.py` |
| `Character35e` | `src/rules_engine/character_35e.py` |

> **Memory Optimisation:** `AgentTask` and `Character35e` use `@dataclass(slots=True)` to prevent `__dict__` allocation, reducing per-instance RAM overhead during deep procedural generation ticks.

---

## 10. Running the Project Locally

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

### Quick AI Smoke-Test

```python
from src.agent_orchestration.agent_task import AgentTask, TaskStatus
from src.rules_engine.character_35e import Character35e, Alignment

# Create and process an agent task
task = AgentTask(
    task_type="roll_npc_stats",
    prompt="Generate a level 5 Fighter NPC for a tavern encounter.",
    max_tokens=1024,
    priority=2,
)
print(task)
print(f"VRAM estimate: {task.estimated_vram_mb:.4f} MiB")

# Create a 3.5e character from SRD rules
fighter = Character35e(
    name="Aldric the Bold",
    char_class="Fighter",
    level=5,
    strength=16,
    dexterity=13,
    constitution=14,
    intelligence=10,
    wisdom=12,
    charisma=8,
    alignment=Alignment.LAWFUL_GOOD,
)
print(fighter)
print(f"HP={fighter.hit_points}, BAB=+{fighter.base_attack_bonus}, AC={fighter.armor_class}")
print(f"Fort={fighter.fortitude_save}, Ref={fighter.reflex_save}, Will={fighter.will_save}")
```

---

## 11. Running the Multi-Agent System on Ubuntu

### Prerequisites

- Ubuntu 22.04 LTS or later
- Python 3.11+
- NVIDIA RTX 4070 Ti Super (or equivalent with ≥ 16 GB VRAM)
- CUDA 12.x + cuDNN
- 64 GB system RAM (minimum 32 GB)

### GPU & Driver Setup

```bash
# 1. Verify NVIDIA driver and CUDA are installed
nvidia-smi
nvcc --version

# 2. If not installed, add the NVIDIA CUDA repository
sudo apt update
sudo apt install -y nvidia-driver-535 nvidia-cuda-toolkit

# 3. Reboot and verify
sudo reboot
nvidia-smi  # Should show RTX 4070 Ti Super with 16 GB VRAM
```

### Model Download & Setup

```bash
# 1. Install the model inference backend (example: llama-cpp-python with CUDA)
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121

# 2. Create a local models directory (not tracked by git)
mkdir -p ~/.local/share/new_game_plus/models

# 3. Download quantised models (adjust URLs for your preferred sources)
# Code generation model (~5 GB)
# World generation model (~6 GB)
# Lore generation model (~5 GB)
# Place .gguf / .safetensors files in the models directory
```

### Running the System

```bash
# 1. Clone and install the project
git clone https://github.com/coldfront96/new_game_plus.git
cd new_game_plus
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .

# 2. Verify all tests pass
pytest tests/ -v

# 3. Run the agent orchestration system (future — not yet implemented)
# python -m src.agent_orchestration.scheduler --config config.yaml
```

### VRAM Budget Rules

| Constraint | Value |
|---|---|
| Hard VRAM cap | 16 384 MiB |
| Max models loaded simultaneously | 1 |
| Default token budget per task | 2 048 tokens |
| Model swap strategy | LRU eviction |
| Context chunking threshold | Model's native context window size |

---

## 12. Testing

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

## 13. Roadmap

| Milestone | Description | Status |
|---|---|---|
| **M0 — Foundation** | Repo scaffold, data models, test harness | ✅ Complete |
| **M0.5 — 3.5e + AI Foundation** | Rules engine scaffold, agent orchestration, Overseer UI, SRD data dir | 🟡 In Progress |
| **M1 — Terrain Alpha** | Chunk generation, block CRUD, basic physics | ⬜ Planned |
| **M2 — ECS Alpha** | Entity ticking, needs loop, A* pathfinding | ⬜ Planned |
| **M3 — Loot Alpha** | Item generation pipeline, affix registry | ⬜ Planned |
| **M4 — Rules Engine** | SRD loader, ability scores, combat resolution, skill checks | ⬜ Planned |
| **M5 — Agent Pipeline** | Local LLM scheduler, prompt builder, result parser | ⬜ Planned |
| **M6 — Overseer UI** | Dashboard, approval gate, parameter panel | ⬜ Planned |
| **M7 — Integration** | Colony loop end-to-end, AI-generated content in live world | ⬜ Planned |
| **M8 — Content** | Biomes, classes, enemy types, events | ⬜ Planned |

---

## 14. Contributing

1. Fork the repository and create a feature branch (`git checkout -b feature/my-feature`).
2. Write tests for every new data model or system.
3. Ensure `pytest tests/` passes with zero failures.
4. Open a pull request with a clear description referencing the relevant GDD section.

Code style: [PEP 8](https://peps.python.org/pep-0008/) enforced via `flake8`.

---

## 15. License

This project is licensed under the **MIT License** — see `LICENSE` for details.