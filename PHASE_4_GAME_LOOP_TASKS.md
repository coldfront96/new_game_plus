# PHASE_4_GAME_LOOP_TASKS.md — Full Game Loop & Character Advancement

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
| Character Creation Wizard | `src/game/wizard.py` | ✅ Shipped |
| Party Save / Load | `src/game/persistence.py` | ✅ Shipped |
| Play Session (combat loop) | `src/game/session.py` | ✅ Shipped |
| Turn Controller + Initiative | `src/game/turn_controller.py` | ✅ Shipped |
| XP Manager + level_up() | `src/rules_engine/progression.py` | ✅ Shipped |
| Feat Engine (prereqs + effects) | `src/rules_engine/feat_engine.py` | ✅ Shipped |
| CLI entry point | `src/game/cli.py` | ✅ Shipped |
| Campaign Session | `src/game/campaign.py` | ✅ Shipped |
| SRD Monster data (446 entries) | `data/srd_3.5/monsters/` | ✅ Shipped |
| Extended FEAT_CATALOG | `src/rules_engine/feat_engine.py` | ✅ Shipped |
| SRD Monster Stat Block Loader | `src/game/session.py` | ✅ Shipped |
| Iterative Full-Attack Action | `src/rules_engine/combat.py` | ✅ Shipped |
| Long Rest / Rest Party | `src/game/session.py` | ✅ Shipped |
| Post-Session XP Persistence | `src/game/cli.py` | ✅ Shipped |
| Level-Up Interactive Wizard | `src/game/wizard.py` | ✅ Shipped |
| Campaign CLI Subcommand | `src/game/cli.py` | ✅ Shipped |

---

## 1. Scope

Phase 4 closes the gap between the individually-complete subsystems and a
fully playable, persistent game loop. The three subsystems are:

| # | Subsystem | Short Name | New / Modified Modules |
|---|-----------|------------|------------------------|
| A | SRD Fidelity | SRD-Fidelity | `src/rules_engine/feat_engine.py`, `src/rules_engine/character_35e.py`, `src/rules_engine/combat.py`, `src/game/session.py` |
| B | Persistence & Progression | Persist-Progress | `src/game/persistence.py`, `src/game/wizard.py`, `src/game/cli.py` |
| C | Campaign Loop | Campaign-Loop | `src/game/cli.py`, `src/game/session.py` |

---

## 2. Dependency Map

```
Tier 0  ──────────────────────────────────────────────────────────────────
         [PH4-001]  Extended FEAT_CATALOG (25+ SRD feats)
         [PH4-002]  natural_armor_bonus metadata in character_35e.armor_class
                │
Tier 1  ────────▼─────────────────────────────────────────────────────────
         [PH4-003]  SRD Monster stat-block loader
         [PH4-004]  Iterative full-attack in combat.py
         [PH4-005]  rest_party() long-rest function
                │
Tier 2  ────────▼─────────────────────────────────────────────────────────
         [PH4-006]  Post-session XP persistence + save
         [PH4-007]  Level-up interactive wizard
                │
Tier 3  ────────▼─────────────────────────────────────────────────────────
         [PH4-008]  Campaign CLI subcommand + play-loop continuation
```

---

## 3. Task Tiers

### Tier 0 — SRD Fidelity Base (No Dependencies)

| Task | Title | Subsystem | Requirement | blockedBy | Effort |
|------|-------|-----------|-------------|-----------|--------|
| PH4-001 | Extended FEAT_CATALOG | srd-fidelity | Add 25+ missing SRD feats to `FEAT_CATALOG` in `src/rules_engine/feat_engine.py`: **Two-Weapon Fighting family** (TWF: DEX 15 prereq, ITWF: TWF+BAB+6, GTWF: ITWF+BAB+11); **Archery chain** (Point Blank Shot: none, Rapid Shot: PBS+DEX13, Precise Shot: PBS, Far Shot: PBS, Shot on the Run: PBS+Dodge+Mobility+BAB+4); **Unarmed chain** (Improved Unarmed Strike: none, Stunning Fist: IUS+DEX13+WIS13+BAB+8, Deflect Arrows: IUS+DEX13); **Combat chain** (Combat Expertise: INT13, Whirlwind Attack: DEX13+INT13+Dodge+Mobility+Spring Attack+BAB+4); **General** (Alertness: none, Endurance: none, Diehard: Endurance, Run: none, Blind-Fight: none, Track: none); **Spellcaster** (Spell Focus: none, Greater Spell Focus: Spell Focus, Spell Penetration: none, Greater Spell Penetration: Spell Penetration, Augment Summoning: Spell Focus+Conjuration, Natural Spell: WIS13+wildshape, Extra Turning: ability to turn); **Mounted** (Mounted Combat: Ride 1 rank, Ride-By Attack: Mounted Combat). Expand `FeatRegistry._ATTACK_BONUSES`, `_DAMAGE_BONUSES`, `_AC_BONUSES`, `_INITIATIVE_BONUSES`, `_FORTITUDE_BONUSES`, `_REFLEX_BONUSES`, `_WILL_BONUSES`, `_HP_BONUSES` maps to cover the new feats. Add `FeatRegistry.get_spell_dc_bonus(character, school) -> int` and `FeatRegistry.get_caster_level_bonus(character) -> int` for spell feat effects. **Target files:** `src/rules_engine/feat_engine.py`. | — | M |
| PH4-002 | natural_armor_bonus metadata support | srd-fidelity | Add one line to `Character35e.armor_class` property: `ac += self.metadata.get("natural_armor_bonus", 0)` inserted after the equipment armor/shield additions and before the magic-item deflection block. This unlocks accurate SRD monster AC without requiring an `EquipmentManager`. **Target file:** `src/rules_engine/character_35e.py`. | — | S |

---

### Tier 1 — Core Mechanics (Depends on Tier 0)

| Task | Title | Subsystem | Requirement | blockedBy | Effort |
|------|-------|-----------|-------------|-----------|--------|
| PH4-003 | SRD Monster Stat-Block Loader | srd-fidelity | Function `build_monsters_from_srd(blueprint: EncounterBlueprint, rng: random.Random) -> List[Character35e]` in `src/game/session.py`. Loads all monster JSON via `srd_loader.load_monsters()` (cached in a module-level `_MONSTER_INDEX: dict[str, dict]` keyed by lowercased name). For each `(name, count, cr)` in `blueprint.monsters`: look up the SRD entry by normalized name (strip special characters, lowercase); if found, construct `Character35e` with SRD ability scores, set `metadata["current_hp"] = entry["hp_avg"]`, set `metadata["natural_armor_bonus"]` = `entry["armor_class"]["total"] − (10 + dex_mod + size.value)` (clamped ≥ 0), and set `metadata["cr"] = cr`; if not found, fall back to the existing Fighter-approximation path. Set `metadata["side"] = "enemy"` on all monsters. Replace the call to `build_monsters_from_blueprint` in `play_session` with `build_monsters_from_srd`. The old function is kept but marked deprecated. **Target file:** `src/game/session.py`. **Input deps:** PH4-002, `srd_loader.load_monsters()` (✅), `EncounterBlueprint` (✅). | PH4-002 | M |
| PH4-004 | Iterative Full-Attack Action | srd-fidelity | Add parameter `iterative_penalty: int = 0` to `AttackResolver.resolve_attack()` in `src/rules_engine/combat.py`; apply it as `attack_bonus -= iterative_penalty` immediately after computing `attack_bonus`. Add class-method `AttackResolver.resolve_full_attack(attacker, target, *, rng, damage_dice_count, damage_dice_sides, power_attack) -> list[CombatResult]` that: computes `n_attacks = max(1, (attacker.base_attack_bonus + 4) // 5)` (capped at 4); iterates `penalty = 0, 5, 10, 15`; calls `resolve_attack(..., iterative_penalty=penalty)` for each; stops iterating if the target drops to 0 or fewer `current_hp`. Update `session.py`'s `_attack_action` callback to use `resolve_full_attack` and apply damage from each result in order. **Target files:** `src/rules_engine/combat.py`, `src/game/session.py`. | — | M |
| PH4-005 | Long Rest / rest_party() | campaign-loop | Function `long_rest(character: Character35e) -> int` in `src/game/session.py`: calls `character.spell_slot_manager.rest()` if the slot manager exists; restores `metadata["current_hp"]` by `character.level` HP (natural healing per SRD), clamped to `character.hit_points` maximum; returns HP restored. Function `rest_party(party: Sequence[Character35e]) -> dict[str, int]` that calls `long_rest` on each member and returns a mapping of `char_id → hp_restored`. **Target file:** `src/game/session.py`. | — | S |

---

### Tier 2 — Persistence & Progression (Depends on Tier 1)

| Task | Title | Subsystem | Requirement | blockedBy | Effort |
|------|-------|-----------|-------------|-----------|--------|
| PH4-006 | Post-Session XP Persistence | persist-progress | Modify `_cmd_play` in `src/game/cli.py`: after `play_session()` returns, (1) load or create an `XPManager` per character (key: `char_id`; create at `current_level=character.level` if no saved state); (2) for each character in the party call `xp_manager.award_xp(report.xp_awarded.get(character.char_id, 0))`; (3) call `save_party(party_name, party, xp_managers=xp_managers)` to persist the updated XP; (4) for each character check `xp_manager.check_level_up().leveled_up` and if `True` print `"*** {name} is ready to level up! Run: new-game-plus level-up {party} ***"`. **Target file:** `src/game/cli.py`. **Input deps:** `XPManager` (✅ `src/rules_engine/progression.py`), `save_party` (✅ `src/game/persistence.py`). | PH4-005 | S |
| PH4-007 | Level-Up Interactive Wizard | persist-progress | Function `run_level_up_flow(character: Character35e, xp_manager: XPManager, wizard: CharacterWizard) -> Progression \| None` in `src/game/wizard.py`: checks `xp_manager.check_level_up().leveled_up`; if False returns `None`; otherwise calls `level_up(character, xp_manager)` (from `src/rules_engine/progression.py`) to advance the level; prints HP gained; calls `prompt_skills()` with `available=progression.skill_points` (add this `available` parameter to skip the `× 4` first-level multiplier and instead use the passed-in budget directly); determines feat slots gained: `+1` at every level divisible by 3, `+1` for Fighter at every even level (SRD Fighter bonus feat table); calls `prompt_feats()` for the total new slots; adds feats via `FeatRegistry.add_feat`; returns the `Progression` record. Add a new CLI subcommand `level-up` to `src/game/cli.py` that loads a party, creates `XPManager` instances from saved `xp` records, iterates characters calling `run_level_up_flow`, and saves the updated party. **Target files:** `src/game/wizard.py`, `src/game/cli.py`. **Input deps:** `level_up` (✅ `src/rules_engine/progression.py`), PH4-006. | PH4-006 | M |

---

### Tier 3 — Campaign Loop Integration (Depends on Tier 2)

| Task | Title | Subsystem | Requirement | blockedBy | Effort |
|------|-------|-----------|-------------|-----------|--------|
| PH4-008 | Campaign CLI Subcommand + Play Continuation | campaign-loop | (A) Add `campaign` subcommand to `src/game/cli.py`: loads the party by name, instantiates `CampaignSession(party=party, world_seed=seed, difficulty=difficulty, terrain=terrain, stdout=stdout)`, calls `camp.run(num_quests=args.quests)`, calls `save_party` with updated state, prints a summary. Args: `party` (positional, default `"default"`), `--quests` (int, default 3), `--seed`, `--difficulty`, `--terrain`. (B) Extend the `play` subcommand: after `play_session()` returns a victory, prompt `"Play another encounter? [y/N]:"` (only if `stdin` is a tty); if yes, call `rest_party(party)` (PH4-005), then re-run `play_session` with the same party, incrementing difficulty by one tier after each win (easy → average → challenging → hard → overwhelming → stays at overwhelming). Save after every encounter. **Target file:** `src/game/cli.py`. **Input deps:** `CampaignSession` (✅ `src/game/campaign.py`), `rest_party` (PH4-005), `save_party` (✅). | PH4-007 | M |

---

## 4. Effort Summary

| Tier | Task Count | S Tasks | M Tasks | L Tasks | Estimated Total |
|------|-----------|---------|---------|---------|-----------------|
| 0 — Base | 2 | 1 | 1 | 0 | ~1.5 days |
| 1 — Core | 3 | 1 | 2 | 0 | ~3 days |
| 2 — Persistence | 2 | 1 | 1 | 0 | ~2 days |
| 3 — Campaign | 1 | 0 | 1 | 0 | ~2 days |
| **Total** | **8** | **3** | **5** | **0** | **~8.5 dev-days** |

> Subsystems A Tier 0 (PH4-001, PH4-002) have no dependencies and ship first.
> PH4-003, PH4-004, PH4-005 are fully independent of each other and may run in parallel.
> PH4-008 is the final integration task — it depends on the full persistence stack being stable.
