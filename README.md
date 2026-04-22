# New Game Plus

> **A high-fidelity, original game engine and simulation built strictly on D&D 3.5e SRD mechanics, focused on autonomous AI agency within a deep, procedural voxel world.**

---

## Table of Contents

1. [Core Objective](#1-core-objective)
2. [Design Philosophy](#2-design-philosophy)
3. [Architectural Pillars](#3-architectural-pillars)
   - [3.5e Ruleset Engine](#31-35e-ruleset-engine)
   - [Voxel Terrain Engine](#32-voxel-terrain-engine)
   - [Event-Driven ECS Simulation](#33-event-driven-ecs-simulation)
   - [Autonomous LLM Agent Layer](#34-autonomous-llm-agent-layer)
   - [Overseer Approval Interface](#35-overseer-approval-interface)
4. [Autonomous Agent Core Loop](#4-autonomous-agent-core-loop)
5. [Local LLM Integration Strategy](#5-local-llm-integration-strategy)
6. [Repository Structure](#6-repository-structure)
7. [Technical Stack](#7-technical-stack)
8. [Target Hardware & Performance Budget](#8-target-hardware--performance-budget)
9. [Visual Fidelity Goal](#9-visual-fidelity-goal)
10. [Data Models](#10-data-models)
11. [Running the Project Locally](#11-running-the-project-locally)
12. [Testing](#12-testing)
13. [Roadmap](#13-roadmap)
14. [Contributing](#14-contributing)
15. [License](#15-license)

---

## 1. Core Objective

Develop a high-fidelity, original game engine and simulation built strictly on **Dungeons & Dragons 3.5e SRD** mechanics. This is a standalone title focusing on **autonomous AI agency** within a deep, procedural voxel world.

Every NPC, creature, and character is an independently simulated agent governed by the full 3.5e ruleset — ability scores, BAB, AC, saving throws, spell slots, and skills all enforced by the engine as inviolable physical laws.

---

## 2. Design Philosophy

The D&D 3.5e SRD is the **single source of truth** for all game mechanics, functioning as the physical laws of the simulation rather than arbitrary designer choices. No mechanic may be hard-coded outside the SRD data files; the engine enforces rules purely by reading from `data/srd_3.5/`.

**Key principles:**

- **3.5e rules as physics** — BAB, AC, saving throws, and skill checks govern agent behaviour exactly as specified in the SRD.
- **Autonomous agency** — Local LLM agents make in-world decisions, generate content, and write engine code without constant human direction.
- **Memory efficiency first** — Every data model (`Block`, `Entity`, `Item`, `AgentTask`, `Character35e`) uses `@dataclass(slots=True)` to handle millions of instances within the 64 GB RAM budget.
- **Event-driven ECS** — All inter-system communication flows through the `EventBus`; no system imports another directly.

---

## 3. Architectural Pillars

### 3.1 3.5e Ruleset Engine

**Location:** `src/rules_engine/`

The ruleset engine is the core of the simulation. It parses structured JSON files from `data/srd_3.5/` at startup and exposes SRD rules as validated Python objects.

| Component | Responsibility |
|---|---|
| `character_35e.py` | `Character35e` base class — ability scores, HP, BAB, saves, AC (all SRD-derived) |
| `ability_scores.py` | Modifier calculations, generation methods (4d6-drop-lowest, point-buy) |
| `combat.py` | Attack rolls, damage, critical hits, initiative, AoO resolution |
| `skills.py` | Skill check resolution, synergy bonuses, class/cross-class costs |
| `spellcasting.py` | Spell slot management, Vancian/spontaneous casting, save DCs |
| `magic.py` | Spell definitions and SpellRegistry |
| `equipment.py` | Equipment slots, armour check penalties, ASF, max dex bonus |
| `conditions.py` | SRD conditions (Blinded, Stunned, Prone) with duration tracking |
| `srd_loader.py` | JSON/Markdown parser that hydrates the above from `data/srd_3.5/` |

**Design Rule:** No game mechanic may be hard-coded. Everything is data-driven from the SRD files.

### 3.2 Voxel Terrain Engine

**Location:** `src/terrain/`

| Component | Responsibility |
|---|---|
| `chunk_manager.py` | Loads/unloads 16×16×256 chunks relative to active entities; LRU cache |
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

### 3.3 Event-Driven ECS Simulation

**Location:** `src/ai_sim/`

| Component | Responsibility |
|---|---|
| `entity.py` | `Entity` base class — UUID, components dict, tag set |
| `components.py` | Pure data bags: `Position`, `Health`, `Needs`, `Inventory`, `Stats` |
| `systems.py` | Stateless processors: `NeedsSystem`, `PathfindingSystem`, `CombatSystem`, `MagicSystem`, `AoOSystem` |
| `state_machine.py` | Hierarchical FSM driving agent behaviour |
| `job_scheduler.py` | Priority queue matching agents to pending jobs |
| `pathfinding.py` | 3D A* over voxel graph with dynamic obstacle updates |

All systems communicate exclusively through the `EventBus` (pub/sub) defined in `src/core/`.

### 3.4 Autonomous LLM Agent Layer

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

### 3.5 Overseer Approval Interface

**Location:** `src/overseer_ui/`

The Overseer is the human-in-the-loop approval gate for all LLM-generated artefacts entering the live simulation. It ensures every autonomous agent decision is reviewed before affecting the world.

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
| OS | Windows (primary); Linux compatible | CUDA 12.x + cuDNN required |

### 5.2 Model Selection

| Slot | Model Family | Parameter Size | Quantisation | VRAM Est. |
|---|---|---|---|---|
| **Code Gen** | DeepSeek Coder v2 | 6.7B | GPTQ 4-bit | ~5 GB |
| **World Gen** | Llama 3 | 8B | GGUF Q4_K_M | ~6 GB |
| **Lore / NPC** | Mistral | 7B | AWQ 4-bit | ~5 GB |

> **Rule:** No more than one model loaded at a time to stay under 16 GB. The scheduler swaps models on-demand using a least-recently-used eviction policy.

### 5.3 Context-Window Management

- **Max context per task:** configurable via `AgentTask.max_tokens` (default 2048).
- **SRD injection:** the `PromptBuilder` selects only the SRD excerpts relevant to the task type.
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
├── README.md                  ← Project overview and architecture
├── PLANS.md                   ← Alignment plan and execution checklist
├── setup.py                   ← Package metadata
├── .gitignore
│
├── src/                       ← All game source code
│   ├── __init__.py
│   ├── core/                  ← Shared utilities (event bus, math helpers)
│   │   ├── __init__.py
│   │   ├── event_bus.py
│   │   ├── engine.py
│   │   └── math_utils.py
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
│   │   ├── spellcasting.py
│   │   ├── magic.py
│   │   ├── equipment.py
│   │   ├── conditions.py
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
└── tests/                     ← Automated test suite (pytest)
    ├── __init__.py
    ├── core/
    ├── terrain/
    ├── ai_sim/
    ├── loot_math/
    ├── rules_engine/
    └── agent_orchestration/
```

---

## 7. Technical Stack

| Layer | Technology | Rationale |
|---|---|---|
| **Language** | Python 3.11+ | Rapid prototyping; easy FFI to C extensions later |
| **Data models** | Python `dataclasses` + `uuid` | Zero-overhead POD structs, engine-agnostic |
| **Memory opt.** | `@dataclass(slots=True)` | Prevents `__dict__` allocation on perf-critical models |
| **Noise generation** | `opensimplex` (Simplex) | Battle-tested procedural generation |
| **Pathfinding** | Custom 3D A* on voxel graph | Full control over heuristics and dynamic obstacles |
| **Serialisation** | `msgpack` / `json` | Fast chunk serialisation to disk |
| **Testing** | `pytest` | Lightweight, discoverable unit tests |
| **Local LLM inference** | `llama-cpp-python` / `vllm` | GGUF/GPTQ/AWQ model loading with CUDA acceleration |
| **LLM models** | DeepSeek, Llama, Mistral | Offline, quantised to fit 16 GB VRAM |
| **Future rendering** | GPU-accelerated pipeline (Godot 4 / Unity DOTS) | Swap rendering backend without touching simulation layer |

---

## 8. Target Hardware & Performance Budget

**Primary platform: Windows** (Linux compatible)

| Resource | Target Spec | Budget |
|---|---|---|
| GPU | NVIDIA RTX 4070 Ti Super (16 GB VRAM) | Full GPU-driven chunk mesh upload |
| System RAM | 64 GB DDR5 | Up to 4 096 active chunks in LRU cache |
| Storage | NVMe SSD | < 5 ms chunk load from disk |
| CPU | High-end desktop (≥ 8 cores) | 500 simultaneous entity ticks at 20 TPS |

**Performance Rules:**

- All simulation systems must be **O(n)** or better per tick.
- Chunk generation runs in a **background thread pool**; never blocks the main tick loop.
- The ECS forbids global state — systems operate on component arrays only.
- Loot generation must complete in **< 1 ms** per item.

---

## 9. Visual Fidelity Goal

The simulation logic is implemented in Python; the long-term rendering goal is visual fidelity comparable to modern high-end titles (such as Baldur's Gate 3) through a **GPU-accelerated rendering pipeline** that visualises the complex underlying 3.5e data.

The rendering backend is designed to be swappable (Godot 4 GDExtension or Unity DOTS) without touching the simulation layer.

---

## 10. Data Models

All foundational data classes use `@dataclass(slots=True)` to minimise per-instance RAM overhead.

| Class | File | Notes |
|---|---|---|
| `Block` | `src/terrain/block.py` | Voxel block with material, durability, light emission |
| `Entity` | `src/ai_sim/entity.py` | UUID + component dict + tag set |
| `Item` | `src/loot_math/item.py` | Procedural prefix/suffix item with SRD stats |
| `AgentTask` | `src/agent_orchestration/agent_task.py` | LLM task with priority and token budget |
| `Character35e` | `src/rules_engine/character_35e.py` | Full 3.5e character: BAB, AC, saves, spell slots |

---

## 11. Running the Project Locally

### Prerequisites

- Python 3.11 or later
- `pip` (comes with Python)
- `git`

### Setup (Windows — primary)

```powershell
# 1. Clone the repository
git clone https://github.com/coldfront96/new_game_plus.git
cd new_game_plus

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate

# 3. Install in editable mode
pip install -e .

# 4. Verify the installation by running the test suite
pytest tests/ -v
```

### Setup (Linux — compatible)

```bash
git clone https://github.com/coldfront96/new_game_plus.git
cd new_game_plus
python -m venv .venv
source .venv/bin/activate
pip install -e .
pytest tests/ -v
```

### Quick Smoke-Test

```python
from src.terrain.block import Block, Material
from src.ai_sim.entity import Entity
from src.loot_math.item import Item, Rarity

stone = Block(block_id=1, material=Material.STONE, durability=100)
agent = Entity(name="Aldric")
sword = Item(name="Iron Sword", rarity=Rarity.COMMON, base_damage=12)

print(stone)
print(agent)
print(sword)
```

### Quick 3.5e Character Smoke-Test

```python
from src.agent_orchestration.agent_task import AgentTask, TaskStatus
from src.rules_engine.character_35e import Character35e, Alignment

task = AgentTask(
    task_type="roll_npc_stats",
    prompt="Generate a level 5 Fighter NPC for a tavern encounter.",
    max_tokens=1024,
    priority=2,
)
print(task)

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

## 12. Testing

```bash
# Run all tests
pytest tests/ -v

# Run only rules engine tests
pytest tests/rules_engine/ -v

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
| **M2 — ECS Alpha** | Entity ticking, needs loop, 3D A* pathfinding | ⬜ Planned |
| **M3 — Loot Alpha** | Item generation pipeline, affix registry | ⬜ Planned |
| **M4 — Rules Engine** | SRD loader, ability scores, combat resolution, skill checks | ⬜ Planned |
| **M5 — Agent Pipeline** | Local LLM scheduler, prompt builder, result parser | ⬜ Planned |
| **M6 — Overseer UI** | Dashboard, approval gate, parameter panel | ⬜ Planned |
| **M7 — Integration** | Full agent loop end-to-end, AI-generated content in live world | ⬜ Planned |
| **M8 — Content** | Biomes, character classes, enemy types, world events | ⬜ Planned |

---

## 14. Contributing

1. Fork the repository and create a feature branch (`git checkout -b feature/my-feature`).
2. Write tests for every new data model or system.
3. Ensure `pytest tests/` passes with zero failures.
4. Open a pull request with a clear description referencing the relevant GDD section.

Code style: [PEP 8](https://peps.python.org/pep-0008/).

---

## 15. License

This project is licensed under the **MIT License** — see `LICENSE` for details.