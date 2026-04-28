# Edge Systems — Task Tracker

67 tasks from `EDGE_SYSTEMS_BUILD_SITE.md`. Ordered by dependency then priority:
encumbrance + NPC classes first, then settlements, linked entities, multiclassing,
prestige classes, and finally the planar track (longest chain).

Effort: S = ≤½ day, M = 1–2 days, L = 3+ days.

---

## Phase E-A — Tier 0 Base Schemas (15 tasks, all S-effort, no dependencies)

Land all 15 in one pass before any Tier 1 work begins.

- [ ] **E-001** (S) — `LoadCategory` & `LiftCategory` enums + `weight_lb: float` on `Item` — `src/rules_engine/encumbrance.py`, `src/rules_engine/equipment.py`
- [ ] **E-002** (S) — `CarryingCapacityRow` dataclass (`strength`, `light_max_lb`, `medium_max_lb`, `heavy_max_lb`; STR 1–29 rows + ×4 rule stub) — `src/rules_engine/encumbrance.py`
- [ ] **E-003** (S) — `MasterMinionLink` dataclass + `LinkType` enum (Familiar / AnimalCompanion / SpecialMount / Cohort) — `src/rules_engine/linked_entity.py`
- [ ] **E-004** (S) — `FamiliarBase` dataclass + `FamiliarSpecies` enum (10 PHB familiars) — `src/rules_engine/linked_entity.py`
- [ ] **E-005** (S) — `AnimalCompanionBase` dataclass (bonus HD, NA adj, STR/DEX adj, bonus tricks, link flags) — `src/rules_engine/linked_entity.py`
- [ ] **E-006** (S) — `SpecialMountBase` dataclass (heavy warhorse / warpony; bonus HD, NA adj, STR adj, Int score, daily summon counter) — `src/rules_engine/linked_entity.py`
- [ ] **E-007** (S) — `ClassLevel` dataclass + `MulticlassRecord` container — `src/rules_engine/multiclass.py`
- [ ] **E-008** (S) — `FavoredClassPolicy` enum (Fixed / HighestLevel / Any) + `RaceFavoredClass` dataclass — `src/rules_engine/multiclass.py`
- [ ] **E-009** (S) — `NPCClassName` enum (Commoner / Expert / Warrior / Adept / Aristocrat) + `NPCClassBase` dataclass — `src/rules_engine/npc_classes.py`
- [ ] **E-010** (S) — `PrestigeClassBase` dataclass + `CasterLevelMode` enum (Full / Partial / None) — `src/rules_engine/prestige_classes.py`
- [ ] **E-011** (S) — `PrerequisiteClause` sealed-union: 8 subtypes (BABRequirement, SkillRankRequirement, FeatRequirement, AlignmentRequirement, ClassFeatureRequirement, RaceRequirement, SpellcastingRequirement, AbilityScoreRequirement) — `src/rules_engine/prestige_classes.py`
- [ ] **E-012** (S) — `CommunitySize` enum (Thorp → Metropolis) + `CommunityBase` dataclass — `src/rules_engine/settlement.py`
- [ ] **E-013** (S) — `DemographicsRow` dataclass + `NPC_CLASS_DISTRIBUTION_PCT` dict — `src/rules_engine/settlement.py`
- [ ] **E-014** (S) — Planar trait enums: `GravityTrait`, `TimeTrait`, `AlignmentTrait`, `MagicTrait`, `ElementalDominance`, `EnergyDominance`, `PlaneCategory` — `src/rules_engine/planar.py`
- [ ] **E-015** (S) — `PlaneBase` dataclass (name, category, gravity, time, realm size, morphic, elemental, energy, alignment, magic, connecting planes) — `src/rules_engine/planar.py`

---

## Phase E-B — Encumbrance Spine (8 tasks; blockedBy E-001, E-002)

Closes the unlimited-carry-weight gap. `EncumbranceState` feeds planar gravity and combat integration.

- [ ] **E-016** (S) — `total_carried_weight(character) -> float` + `coin_weight(coins) -> float` (50 coins = 1 lb) — `src/rules_engine/encumbrance.py` — *blockedBy E-001*
- [ ] **E-017** (M) — `carrying_capacity(strength, size, quadruped) -> CarryingCapacityRow` — PHB Table 9-1 STR 1–29; ×4 per +10 STR for STR 30+; size multipliers (Tiny ×½ → Colossal ×16); quadruped ×1.5 — `src/rules_engine/encumbrance.py` — *blockedBy E-002*
- [ ] **E-018** (S) — `resolve_load_category(weight_lb, capacity) -> LoadCategory` — Light / Medium / Heavy / Overload — `src/rules_engine/encumbrance.py` — *blockedBy E-001, E-002*
- [ ] **E-019** (M) — `LoadPenalties` dataclass + `apply_load_penalties(load) -> LoadPenalties` — max Dex cap, ACP, speed table per PHB Table 9-2; Heavy run ×3 not ×4 — `src/rules_engine/encumbrance.py` — *blockedBy E-018*
- [ ] **E-020** (S) — `voxel_speed_from_feet(speed_ft, voxel_ft=5) -> int` + `apply_load_to_voxel_speed()` — no double-apply with armor speed penalty — `src/rules_engine/encumbrance.py` — *blockedBy E-019*
- [ ] **E-034** (L) — `EQUIPMENT_WEIGHT_REGISTRY: dict[str, float]` — 180+ PHB Ch 7 items: weapons (Table 7-4), armor (Table 7-5), gear (Table 7-8), mounts/vehicles (Table 7-7); size-variant multipliers — `src/rules_engine/encumbrance.py` — *blockedBy E-016*
- [ ] **E-035** (M) — `CARRYING_CAPACITY_TABLE: dict[int, CarryingCapacityRow]` — explicit STR 1–29 from PHB Table 9-1; ×4 function for STR 30+ — `src/rules_engine/encumbrance.py` — *blockedBy E-017*
- [ ] **E-047** (M) — `compute_encumbrance_state(character) -> EncumbranceState` — immutable snapshot: total weight, capacity, load, penalties, effective speed ft + voxel, combined ACP (load stacks with armor ACP; speed does NOT double-apply) — `src/rules_engine/encumbrance.py` — *blockedBy E-016, E-017, E-018, E-019, E-020, E-034*

---

## Phase E-C — NPC Classes (3 tasks; blockedBy E-009)

Prerequisite for the settlement generator.

- [ ] **E-026** (M) — `npc_class_progression(klass, level) -> NPCProgression` — BAB: Commoner/Expert/Adept/Aristocrat poor (`level//2`), Warrior full (`level`); saves per DMG Ch 4 — `src/rules_engine/npc_classes.py` — *blockedBy E-009*
- [ ] **E-040** (M) — `NPC_CLASS_REGISTRY: dict[NPCClassName, NPCClassBase]` — 5 DMG NPC classes: Commoner (d4, all-poor saves, 2 sp), Expert (d6, good Will, 6 sp, 10 chosen skills), Warrior (d8, full BAB, good Fort), Adept (d6, good Will, divine casting), Aristocrat (d8, good Will, social skills) — `src/rules_engine/npc_classes.py` — *blockedBy E-026*
- [ ] **E-052** (M) — `generate_npc(klass, level, rng) -> NPCStats` — equipment from DMG Table 4-23 CR gp budget; applies `NPC_CLASS_DISTRIBUTION_PCT` weights when called from settlement generator — `src/rules_engine/npc_classes.py` — *blockedBy E-040, E-026*

---

## Phase E-D — Settlement Track (7 tasks; blockedBy Phase E-C + E-012, E-013)

Highest-impact world feature: towns, demographics, economics, shopping.

- [ ] **E-028** (S) — `gp_limit_for(size) -> int` + `community_total_assets(size, population) -> int` — DMG Table 5-2 (Thorp 40 gp → Metropolis 100 000 gp); total assets = `gp_limit/2 × (population/10)` — `src/rules_engine/settlement.py` — *blockedBy E-012*
- [ ] **E-029** (M) — `highest_level_npc_class(size, klass, rng) -> int` + `population_class_roster()` — DMG p. 139 d4+size-modifier algorithm; level-doubling per lower level; population cap per class — `src/rules_engine/settlement.py` — *blockedBy E-013, E-026*
- [ ] **E-042** (M) — `COMMUNITY_REGISTRY: dict[CommunitySize, CommunityBase]` — 8 sizes from DMG Table 5-2 with population ranges, GP limits, power-center count ranges, mixed-alignment flags — `src/rules_engine/settlement.py` — *blockedBy E-028*
- [ ] **E-043** (S) — `POWER_CENTER_REGISTRY` + `PowerCenterType` enum (Conventional / Nonstandard / Magical) + d100 weighted table (01–60 Conventional, 61–90 Nonstandard, 91–100 Magical) — `src/rules_engine/settlement.py` — *blockedBy E-042*
- [ ] **E-054** (L) — `generate_settlement(size, rng) -> Settlement` — population roll, assets, power centers, NPC level-distribution roster, PC class roster, `AuthorityFigure` — `src/rules_engine/settlement.py` — *blockedBy E-029, E-042, E-043, E-052*
- [ ] **E-060** (L) — `available_magic_items(settlement, rng) -> AvailableInventory` — minor 75% if ≤ GP limit; medium % = `(gp_limit/price)×100` capped 75; major only if `gp_limit ≥ price` — `src/rules_engine/settlement.py` — *blockedBy E-054, E-028*
- [ ] **E-066** (M) — `shop(character, settlement, item_name) -> ShopResult` — GP limit check → magic-item roster → mundane PHB Ch 7 → Expert craftsman availability → asset depletion tally — `src/rules_engine/settlement.py` — *blockedBy E-054, E-060*

---

## Phase E-E — Linked Entities: Familiars, Animal Companions, Special Mounts (11 tasks; blockedBy E-003–E-006)

Run the three acquisition sub-chains in parallel, converge at E-056.

- [ ] **E-021** (S) — `familiar_int_score(master_levels) -> int` + `familiar_natural_armor_bonus()` — PHB table: levels 1–2 → Int 6 through 19–20 → Int 15; NA = `1 + (master_levels // 2)` — `src/rules_engine/linked_entity.py` — *blockedBy E-004*
- [ ] **E-022** (M) — `animal_companion_progression(druid_level) -> AnimalCompanionProgression` — PHB druid table: +2HD/+2NA/+1STR-DEX/+1trick every 3 levels; Evasion lvl 2, Devotion lvl 6, Multiattack lvl 9, Improved Evasion lvl 15; alternative-list level offsets — `src/rules_engine/linked_entity.py` — *blockedBy E-005*
- [ ] **E-023** (M) — `paladin_mount_progression(paladin_level) -> SpecialMountProgression` — PHB paladin 2-level bands; SR = paladin level+5 at lvl 11; 1/day summon limit — `src/rules_engine/linked_entity.py` — *blockedBy E-006*
- [ ] **E-036** (M) — `FAMILIAR_REGISTRY: dict[FamiliarSpecies, FamiliarBase]` — 10 PHB familiars with master bonuses (Bat +3 Listen, Cat +3 Move Silently, Hawk +3 Spot bright, Lizard +3 Climb, Owl +3 Spot shadowy, Rat +2 Fort, Raven Speech, Tiny Viper +3 Bluff, Toad +3 hp, Weasel +2 Ref) — `src/rules_engine/linked_entity.py` — *blockedBy E-021*
- [ ] **E-037** (L) — `ANIMAL_COMPANION_REGISTRY` — full PHB druid companion lists: standard list + 4th-level (−3 eff. level: Ape, Black Bear, Bison, Boar, Cheetah, Crocodile, Dire Badger/Bat/Weasel, Leopard, Large Viper, Wolverine) + 7th/10th/13th/16th-level lists — `src/rules_engine/linked_entity.py` — *blockedBy E-022*
- [ ] **E-038** (S) — `PALADIN_MOUNT_REGISTRY` — Heavy Warhorse + Warpony base stat blocks with per-band progression deltas; `intelligence_at_level` table — `src/rules_engine/linked_entity.py` — *blockedBy E-023*
- [ ] **E-048** (M) — `acquire_familiar(master, species) -> MasterMinionLink` — Sorcerer/Wizard class gate; Improved Familiar feat for non-standard species; 100 gp × master-class-level cost; raises `FamiliarError` on prereq failure — `src/rules_engine/linked_entity.py` — *blockedBy E-003, E-004, E-021, E-036*
- [ ] **E-049** (M) — `acquire_animal_companion(druid, species) -> MasterMinionLink` — druid-level ≥ required; `animal_companion_progression(druid_level − offset)` for current bonuses; 24-hour ritual; replace-companion flow — `src/rules_engine/linked_entity.py` — *blockedBy E-003, E-005, E-022, E-037*
- [ ] **E-050** (M) — `summon_special_mount(paladin) -> MasterMinionLink` — 1/day (resets on long rest); 2-hour summon duration + banishment refractory; mount death → 30-day cooldown + −1 level — `src/rules_engine/linked_entity.py` — *blockedBy E-003, E-006, E-023, E-038*
- [ ] **E-056** (L) — `MasterMinionTurnTracker` — minions roll initiative independently; "command minion" costs master Move action; familiar must be within 5 ft at cast time for share-spells — `src/ai_sim/master_minion.py` — *blockedBy E-003, E-048, E-049, E-050*
- [ ] **E-057** (M) — `share_spell(master, link, spell)` + `empathic_link_message()` + `donate_hp()` — Personal/Self range gate; 5-ft proximity check at moment of casting; 1-mile empathic range — `src/rules_engine/linked_entity.py` — *blockedBy E-048, E-056*

---

## Phase E-F — Multiclassing + Prestige Classes (10 tasks; blockedBy E-007, E-008, E-010, E-011)

Land multiclassing first (E-024 → E-025 → E-039 → E-051 → E-058), then prestige (E-027 → E-041 → E-053 → E-059), then unified level-up (E-065).

- [ ] **E-024** (M) — `multiclass_xp_penalty_pct(record, race) -> float` — 20% per level-gap ≥2; ignores favored class and prestige classes; Human/Half-Elf HighestLevel exemption — `src/rules_engine/multiclass.py` — *blockedBy E-007, E-008*
- [ ] **E-025** (S) — `favored_class_for(race, record) -> str` — HighestLevel: highest-level entry (first on tie); Fixed: registered class name — `src/rules_engine/multiclass.py` — *blockedBy E-008*
- [ ] **E-039** (S) — `FAVORED_CLASS_REGISTRY: dict[Race, RaceFavoredClass]` — Human/Half-Elf → HighestLevel; Dwarf → Fighter; Elf → Wizard; Gnome → Bard; Half-Orc → Barbarian; Halfling → Rogue — `src/rules_engine/multiclass.py` — *blockedBy E-025*
- [ ] **E-051** (L) — `build_multiclass_stats(record) -> MulticlassStats` — total BAB (sum per-class); per-save stacking (good-save +2 base applied once per save category); total HD — `src/rules_engine/multiclass.py` — *blockedBy E-007, E-024, E-039*
- [ ] **E-027** (L) — `verify_prerequisites(character, prestige_class) -> PrerequisiteResult` — dispatches all 8 `PrerequisiteClause` subtypes; returns `met: bool` + `failed_clauses` list — `src/rules_engine/prestige_classes.py` — *blockedBy E-010, E-011*
- [ ] **E-041** (L) — `PRESTIGE_CLASS_REGISTRY: dict[str, PrestigeClassBase]` — 16 DMG Ch 5 prestige classes (Arcane Archer, Arcane Trickster, Archmage, Assassin, Blackguard, Dragon Disciple, Duelist, Dwarven Defender, Eldritch Knight, Hierophant, Horizon Walker, Loremaster, Mystic Theurge, Red Wizard, Shadowdancer, Thaumaturgist) with full prerequisite chains + `CasterLevelMode` flags — `src/rules_engine/prestige_classes.py` — *blockedBy E-010, E-011, E-027*
- [ ] **E-053** (L) — `attempt_prestige_entry(character, prestige_name)` + `advance_prestige(character, prestige_name)` — prereq check → `ClassLevel(is_prestige=True)` registration; BAB/save/feature deltas; `max_class_level` cap — `src/rules_engine/prestige_classes.py` — *blockedBy E-027, E-041, E-051*
- [ ] **E-058** (M) — `multiclass_caster_levels(character) -> dict[str, int]` — per-class independent CL tracking; `combined_caster_level(character, mode)` for prestige continuation — `src/rules_engine/multiclass.py` — *blockedBy E-051, E-007*
- [ ] **E-059** (L) — `apply_prestige_caster_continuation(character, prestige_class, level_gained)` — Full (Mystic Theurge: advances both arcane + divine CL); Partial (Eldritch Knight: skips 1st level); Archmage slot-sacrifice rule — `src/rules_engine/prestige_classes.py` — *blockedBy E-053, E-058*
- [ ] **E-065** (L) — `level_up(character, klass) -> LevelUpReport` — prestige path: verify prereqs → advance → caster continuation; standard path: increment level → recompute XP penalty → update favored class → rebuild multiclass stats → update spell slots — `src/rules_engine/multiclass.py` — *blockedBy E-024, E-025, E-051, E-053, E-058, E-059*

---

## Phase E-G — Planar Track (10 tasks; blockedBy E-014, E-015 — do last)

Trait resolvers (E-030–E-033) and plane registries (E-044–E-046) can each run in parallel, then converge at E-055.

- [ ] **E-030** (M) — `apply_gravity_trait(trait, action) -> ActionContext` — Heavy: ×1.5 effective weight; Light: ½ weight +1 atk/STR/DEX ×2 jump 1d6/20ft fall; None: Balance DC 16 to move; Subjective: Wisdom DC 16 first time — `src/rules_engine/planar.py` — *blockedBy E-014*
- [ ] **E-031** (M) — `apply_time_trait(trait, hours) -> TimeDilationResult` — Flowing: fixed ratio; Erratic: d% ratio per visit; Timeless: aging/hunger/durations suspended; Fort DC 25 vs catastrophic ageing on exit — `src/rules_engine/planar.py` — *blockedBy E-014*
- [ ] **E-032** (M) — `apply_magic_trait(trait, school, descriptors) -> MagicTraitResult` — Enhanced: +1 CL for matching school; Impeded: Spellcraft DC 20+spell_level or fail; Dead: all spells fail; Wild: roll wild-magic table; Limited: listed schools only — `src/rules_engine/planar.py` — *blockedBy E-014*
- [ ] **E-033** (M) — `apply_elemental_dominance()` + `apply_energy_dominance()` — Fire: 3d10/round; Positive minor: fast healing 2; Positive major: Fort DC 20 or explode; Negative minor: Fort DC 25 or 1d6 neg levels/round; Negative major: dust on failed save — `src/rules_engine/planar.py` — *blockedBy E-014*
- [ ] **E-044** (M) — `INNER_PLANE_REGISTRY: dict[str, PlaneBase]` — 6 inner planes (Elemental Air/Earth/Fire/Water + Positive/Negative Energy) with full trait sets per DMG Ch 5 — `src/rules_engine/planar.py` — *blockedBy E-015*
- [ ] **E-045** (L) — `OUTER_PLANE_REGISTRY: dict[str, PlaneBase]` — 17 Great Wheel outer planes with alignment + magic + time + gravity traits per DMG Ch 5; cell-by-cell diff against source required — `src/rules_engine/planar.py` — *blockedBy E-015*
- [ ] **E-046** (M) — `TRANSITIVE_PLANE_REGISTRY: dict[str, PlaneBase]` — Astral (Subjective Directional gravity, Timeless, Enhanced divinations), Ethereal (Border vs Deep sub-regions), Plane of Shadow (Enhanced shadow, Impeded light), Plane of Mirrors — `src/rules_engine/planar.py` — *blockedBy E-015*
- [ ] **E-055** (L) — `transition_plane(traveler, from_plane, to_plane) -> PlanarTransitionResult` — connectivity check; encumbrance recompute under new gravity; temporal reset; magic-school suppression flags; persists `current_plane_id` on character — `src/rules_engine/planar.py` — *blockedBy E-030, E-031, E-032, E-033, E-044, E-045, E-046, E-047*
- [ ] **E-061** (L) — `resolve_spell_in_plane(spell, caster, plane) -> SpellResolutionResult` — folds `apply_magic_trait()` + elemental-dominance descriptor scaling into `magic.cast()`; CL deltas, save DC deltas, wild-surge dispatch — `src/rules_engine/planar.py` — *blockedBy E-032, E-033, E-055*
- [ ] **E-062** (M) — `adapt_encounter_for_plane(blueprint, plane, rng) -> EncounterBlueprint` — remaps creature lists to plane-appropriate types; injects environmental hazards into encounter setup — `src/rules_engine/planar.py` — *blockedBy E-055, E-061*

---

## Phase E-H — Final Integrators (4 tasks; all tracks must be complete)

- [ ] **E-063** (M) — `apply_encumbrance_to_combat_state(character, combat_state) -> CombatState` — updates AC max-Dex cap; ACP on Climb/Jump/Swim/Tumble/Hide/Move Silently; voxel-grid speed; Overload = stationary — `src/rules_engine/encumbrance.py` — *blockedBy E-047, E-020*
- [ ] **E-064** (L) — `simulate_round_with_links(party, links, encounter, rng) -> RoundReport` — masters + minions on independent initiative slots; familiar share-spell + empathic-link actions; "command minion" costs master Move; master takes 1 hp per 5 hp dealt to familiar — `src/ai_sim/master_minion.py` — *blockedBy E-056, E-057, E-063*
- [ ] **E-065** (see Phase E-F) — unified level-up integrator; listed here as convergence point for multiclass + prestige tracks
- [ ] **E-067** (L) — `run_planar_excursion(party, itinerary, rng) -> ExcursionReport` — per-plane loop: `transition_plane()` → gravity encumbrance recompute → `adapt_encounter_for_plane()` → `resolve_spell_in_plane()` → `apply_time_trait()` accumulation; report: prime-material time elapsed, XP earned, catastrophic-ageing Fort saves — `src/rules_engine/planar.py` — *blockedBy E-055, E-061, E-062, E-063*
