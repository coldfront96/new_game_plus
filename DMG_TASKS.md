#	Subsystem	Short Name	Target Modules
A	Trophic Level & Caloric Engine	Food Web	src/world_sim/food_web.py
B	Geomorphic Entity Interaction	Lair Carver	src/terrain/chunk_generator.py, src/world_sim/lairs.py
C	Sociopolitical Entity Grouping	Factions	src/world_sim/factions.py
D	Context-Aware Intelligence	Spellcaster AI	src/ai_sim/behavior.py
📋 Tier 1: The Bio-Mechanical Foundation (Core Logic)
Task	Title	Subsystem	Requirement	Effort
EM-001	Trophic Level Assignment	food-web	Add trophic_level (Apex/Predator/Prey/Producer) and diet_tags to species JSON schema; link to SpeciesPopRecord.	S
EM-002	Caloric Demand Formula	food-web	Function calculate_chunk_starvation(): If Predator population > (Prey population * constant), trigger population delta.	M
EM-003	Lair Metadata Integration	lair-carver	Add lair_type (Burrow/Cave/Hive/Fortress) to monster stat blocks in batches A–Z.	S
EM-004	Entity Faction Tags	factions	Dataclass FactionRecord: name: str, alignment: Alignment, hostile_to: list[str]; assign Orcs/Goblins to default warbands.	S
📋 Tier 2: The Physical Transformation (Voxel Interaction)
Task	Title	Subsystem	Requirement	Effort
EM-005	Voxel Carving API	lair-carver	Update ChunkGenerator to accept LairRecord and carve specific voxel patterns (e.g., a 10x10 hole for a Dragon).	L
EM-006	Migration War Trigger	factions	Function resolve_migration_conflict(): When two hostile populations inhabit the same chunk, calculate math-based casualties instead of growth.	M
EM-007	Resource Depletion	food-web	High population of "Prey" (Herbivores) now mathematically degrades the Biome quality of a chunk over time.	M
📋 Tier 3: The Cognitive Layer (DeepSeek Integration)
Task	Title	Subsystem	Requirement	Effort
EM-008	Daily Spell Loadout	caster-ai	SpellcasterAI.prepare_daily(): Pings local LLM to choose spells from data/srd_3.5/spells/ based on current chunk environment.	M
EM-009	Faction Lore Generator	factions	Use LLMBridge to forge a name and history for a population that crosses a specific growth threshold (e.g., "The Blood-Axe Tribe").	M
🚀
