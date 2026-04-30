# MONSTER_MANUAL_TASKS.md — SRD 3.5e Monster Manual Implementation Tracker

## Status Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Full stat block implemented (AC, HP dice, speed, attacks + damage, special attacks, special qualities, saves, skills, feats, CR, alignment, advancement, all v2 ecology fields) |
| 🔲 | Stub only — entry exists in `core.json` with name + CR but no full stat block |
| ❌ | Not started — no entry exists at all |

## Infrastructure Status

All 46 Living World / MM Physics tasks (LW-001–LW-046) are **complete** and live in `main`.
See [`LIVING_WORLD_MM_BUILD_SITE.md`](LIVING_WORLD_MM_BUILD_SITE.md) for the full breakdown.

| Subsystem | File(s) | Status |
|-----------|---------|--------|
| Population / Biome / Migration engine | `src/world_sim/` | ✅ |
| Passive effects (Gaze, Aura, Frightful Presence) | `src/rules_engine/mm_passive.py` | ✅ |
| Grapple / Improved Grab / Constrict / Swallow | `src/rules_engine/mm_grapple.py` | ✅ |
| Regeneration / Fast Healing | `src/rules_engine/mm_immortal.py` | ✅ |
| DR / SR engines | `src/rules_engine/mm_metaphysical.py` | ✅ |
| Combat engine wiring | `src/rules_engine/mm_combat_wiring.py` | ✅ |
| Spawn Director integration | `src/world_sim/spawn_director.py` | ✅ |
| JSON schema v2 validator | `data/srd_3.5/monsters/schema_v2.json` | ✅ |
| v1 → v2 migration script | `scripts/migrate_v1_to_v2.py` | ✅ |
| Coherence report | `data/coherence_report.json` | ✅ |
| Regression test suite | `tests/world_sim/test_living_world.py` | ✅ |

---

## Monster Stat Block Progress

### Aberrations

| Monster | CR | Status | Notes |
|---------|----|--------|-------|
| Aboleth | 7 | ✅ | `data/srd_3.5/monsters/batch_a_c.json` |
| Beholder | 13 | ✅ | `data/srd_3.5/monsters/batch_a_c.json` |
| Carrion Crawler | 4 | ✅ | `data/srd_3.5/monsters/batch_aberrations.json` |
| Chuul | 7 | ✅ | `data/srd_3.5/monsters/batch_aberrations.json` |
| Cloaker | 5 | ✅ | `data/srd_3.5/monsters/batch_aberrations.json` |
| Darkmantle | 1 | ✅ | `data/srd_3.5/monsters/batch_d_g.json` |
| Delver | 9 | ✅ | `data/srd_3.5/monsters/batch_aberrations.json` |
| Destrachan | 8 | ✅ | `data/srd_3.5/monsters/batch_aberrations.json` |
| Digester | 6 | ✅ | `data/srd_3.5/monsters/batch_aberrations.json` |
| Ethereal Filcher | 3 | ✅ | `data/srd_3.5/monsters/batch_aberrations.json` |
| Gibbering Mouther | 5 | ✅ | `data/srd_3.5/monsters/batch_aberrations.json` |
| Grick | 3 | ✅ | `data/srd_3.5/monsters/batch_aberrations.json` |
| Mimic | 4 | ✅ | `data/srd_3.5/monsters/batch_aberrations.json` |
| Mind Flayer (Illithid) | 8 | ✅ | `data/srd_3.5/monsters/batch_m_r.json` |
| Otyugh | 4 | ✅ | `data/srd_3.5/monsters/batch_aberrations.json` |
| Roper | 12 | ✅ | `data/srd_3.5/monsters/batch_aberrations.json` |
| Rust Monster | 3 | ✅ | `data/srd_3.5/monsters/batch_m_r.json` |
| Skum | 2 | ✅ | `data/srd_3.5/monsters/batch_aberrations.json` |
| Umber Hulk | 7 | ✅ | `data/srd_3.5/monsters/batch_aberrations.json` |
| Will-o'-Wisp | 6 | ✅ | `data/srd_3.5/monsters/batch_aberrations.json` |

---

### Animals

| Monster | CR | Status | Notes |
|---------|----|--------|-------|
| Ape | 2 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Ape, Dire | 3 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Badger | 1/2 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Badger, Dire | 2 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Bat (swarm) | 2 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Bear, Black | 2 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Bear, Brown (Grizzly) | 4 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Bear, Dire | 7 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Bear, Polar | 4 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Bison | 2 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Boar | 2 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Boar, Dire | 4 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Camel | 1 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Cat | 1/4 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Cheetah | 2 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Crocodile | 2 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Crocodile, Giant | 4 | ✅ | `data/srd_3.5/monsters/batch_a_c.json` |
| Crocodile, Dire | 9 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Dog | 1/3 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Dog, Riding | 1 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Donkey | 1/6 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Eagle | 1/2 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Eagle, Giant | 3 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Elephant | 7 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Frog, Giant | 1 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Hawk | 1/3 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Horse, Heavy | 1 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Horse, Light | 1 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Horse, Warhorse (Heavy) | 2 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Horse, Warhorse (Light) | 1 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Hyena | 1 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Leopard | 2 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Lion | 3 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Lion, Dire | 5 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Mammoth | 8 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Manta Ray | 1/4 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Monkey | 1/6 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Mule | 1/2 | ✅ | `data/srd_3.5/monsters/batch_animals_a_m.json` |
| Octopus | 1 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Octopus, Giant | 8 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Owl | 1/4 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Owl, Giant | 4 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Pony | 1/4 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Porpoise | 1/2 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Rat | 1/4 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Rat, Dire | 1/3 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Raven | 1/6 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Rhinoceros | 4 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Roc | 9 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Shark, Large | 2 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Shark, Huge | 4 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Shark, Dire | 9 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Snake, Constrictor | 2 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Snake, Constrictor (Giant) | 5 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Snake, Viper (Tiny) | 1/3 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Snake, Viper (Small) | 1/2 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Snake, Viper (Medium) | 1 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Snake, Viper (Large) | 2 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Snake, Viper (Huge) | 3 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Snake, Viper (Giant) | 3 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Snow Leopard | 2 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Squid | 1 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Squid, Giant | 9 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Tiger | 4 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Tiger, Dire | 8 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Toad | 1/10 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Weasel | 1/4 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Weasel, Dire | 2 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Whale, Baleen | 6 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Whale, Cachalot | 12 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Whale, Orca | 5 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Wolf | 1 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Wolf, Dire | 3 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Wolverine | 2 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Wolverine, Dire | 4 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |
| Yeti | 3 | ✅ | `data/srd_3.5/monsters/batch_animals_n_z.json` |

---

### Constructs

| Monster | CR | Status | Notes |
|---------|----|--------|-------|
| Animated Object (Tiny) | 1 | ✅ | `data/srd_3.5/monsters/batch_constructs.json` |
| Animated Object (Small) | 2 | ✅ | `data/srd_3.5/monsters/batch_constructs.json` |
| Animated Object (Medium) | 3 | ✅ | `data/srd_3.5/monsters/batch_constructs.json` |
| Animated Object (Large) | 5 | ✅ | `data/srd_3.5/monsters/batch_constructs.json` |
| Animated Object (Huge) | 7 | ✅ | `data/srd_3.5/monsters/batch_constructs.json` |
| Animated Object (Gargantuan) | 10 | ✅ | `data/srd_3.5/monsters/batch_constructs.json` |
| Animated Object (Colossal) | 14 | ✅ | `data/srd_3.5/monsters/batch_constructs.json` |
| Golem, Clay | 10 | ✅ | `data/srd_3.5/monsters/batch_constructs.json` |
| Golem, Flesh | 7 | ✅ | `data/srd_3.5/monsters/batch_constructs.json` |
| Golem, Iron | 13 | ✅ | `data/srd_3.5/monsters/batch_constructs.json` |
| Golem, Stone | 11 | ✅ | `data/srd_3.5/monsters/batch_constructs.json` |
| Homunculus | 1 | ✅ | `data/srd_3.5/monsters/batch_constructs.json` |
| Shield Guardian | 8 | ✅ | `data/srd_3.5/monsters/batch_constructs.json` |

---

### Dragons

> Each colour has 9 age categories (Wyrmling, Very Young, Young, Juvenile, Young Adult, Adult, Mature Adult, Old, Very Old, Ancient, Wyrm, Great Wyrm). Priority order: Young → Adult → Ancient → Wyrm/Great Wyrm.

| Monster | CR (Adult) | Status | Notes |
|---------|-----------|--------|-------|
| Dragon, Black (Wyrmling) | 3 | ✅ | `data/srd_3.5/monsters/batch_dragons_extended.json` |
| Dragon, Black (Young) | 7 | ✅ | `data/srd_3.5/monsters/batch_d_g.json` |
| Dragon, Black (Adult) | 14 | ✅ | `data/srd_3.5/monsters/batch_dragons_extended.json` |
| Dragon, Black (Ancient) | 19 | ✅ | `data/srd_3.5/monsters/batch_dragons_extended.json` |
| Dragon, Black (Great Wyrm) | 22 | ✅ | `data/srd_3.5/monsters/batch_dragons_extended.json` |
| Dragon, Blue (Young) | 9 | ✅ | `data/srd_3.5/monsters/batch_dragons_extended.json` |
| Dragon, Blue (Adult) | 16 | ✅ | `data/srd_3.5/monsters/batch_dragons_extended.json` |
| Dragon, Blue (Ancient) | 21 | ✅ | `data/srd_3.5/monsters/batch_dragons_extended.json` |
| Dragon, Brass (Young) | 8 | ✅ | `data/srd_3.5/monsters/batch_dragons_extended.json` |
| Dragon, Brass (Adult) | 15 | ✅ | `data/srd_3.5/monsters/batch_dragons_extended.json` |
| Dragon, Bronze (Young) | 10 | ✅ | `data/srd_3.5/monsters/batch_dragons_extended.json` |
| Dragon, Bronze (Adult) | 17 | ✅ | `data/srd_3.5/monsters/batch_dragons_extended.json` |
| Dragon, Copper (Young) | 9 | ✅ | `data/srd_3.5/monsters/batch_dragons_extended.json` |
| Dragon, Copper (Adult) | 16 | ✅ | `data/srd_3.5/monsters/batch_dragons_extended.json` |
| Dragon, Gold (Young) | 12 | ✅ | `data/srd_3.5/monsters/batch_dragons_extended.json` |
| Dragon, Gold (Adult) | 19 | ✅ | `data/srd_3.5/monsters/batch_dragons_extended.json` |
| Dragon, Gold (Great Wyrm) | 25 | ✅ | `data/srd_3.5/monsters/batch_dragons_extended.json` |
| Dragon, Green (Young) | 8 | ✅ | `data/srd_3.5/monsters/batch_dragons_extended.json` |
| Dragon, Green (Adult) | 15 | ✅ | `data/srd_3.5/monsters/batch_dragons_extended.json` |
| Dragon, Red (Young) | 10 | ✅ | `data/srd_3.5/monsters/batch_dragons_extended.json` |
| Dragon, Red (Adult) | 17 | ✅ | `data/srd_3.5/monsters/batch_dragons_extended.json` |
| Dragon, Red (Ancient) | 22 | ✅ | `data/srd_3.5/monsters/batch_d_g.json` |
| Dragon, Silver (Young) | 11 | ✅ | `data/srd_3.5/monsters/batch_dragons_extended.json` |
| Dragon, Silver (Adult) | 18 | ✅ | `data/srd_3.5/monsters/batch_dragons_extended.json` |
| Dragon, White (Young) | 5 | ✅ | `data/srd_3.5/monsters/batch_dragons_extended.json` |
| Dragon, White (Adult) | 12 | ✅ | `data/srd_3.5/monsters/batch_dragons_extended.json` |
| Dragon Turtle | 9 | ✅ | `data/srd_3.5/monsters/batch_dragons_extended.json` |
| Pseudodragon | 1 | ✅ | `data/srd_3.5/monsters/batch_dragons_extended.json` |

---

### Elementals

| Monster | CR | Status | Notes |
|---------|----|--------|-------|
| Elemental, Air (Small) | 1 | ✅ | `data/srd_3.5/monsters/batch_elementals.json` |
| Elemental, Air (Medium) | 3 | ✅ | `data/srd_3.5/monsters/batch_elementals.json` |
| Elemental, Air (Large) | 5 | ✅ | `data/srd_3.5/monsters/batch_elementals.json` |
| Elemental, Air (Huge) | 7 | ✅ | `data/srd_3.5/monsters/batch_elementals.json` |
| Elemental, Air (Greater) | 9 | ✅ | `data/srd_3.5/monsters/batch_elementals.json` |
| Elemental, Air (Elder) | 11 | ✅ | `data/srd_3.5/monsters/batch_elementals.json` |
| Elemental, Earth (Small) | 1 | ✅ | `data/srd_3.5/monsters/batch_elementals.json` |
| Elemental, Earth (Medium) | 3 | ✅ | `data/srd_3.5/monsters/batch_elementals.json` |
| Elemental, Earth (Large) | 5 | ✅ | `data/srd_3.5/monsters/batch_elementals.json` |
| Elemental, Earth (Huge) | 7 | ✅ | `data/srd_3.5/monsters/batch_elementals.json` |
| Elemental, Earth (Greater) | 9 | ✅ | `data/srd_3.5/monsters/batch_elementals.json` |
| Elemental, Earth (Elder) | 11 | ✅ | `data/srd_3.5/monsters/batch_elementals.json` |
| Elemental, Fire (Small) | 1 | ✅ | `data/srd_3.5/monsters/batch_elementals.json` |
| Elemental, Fire (Medium) | 3 | ✅ | `data/srd_3.5/monsters/batch_elementals.json` |
| Elemental, Fire (Large) | 5 | ✅ | `data/srd_3.5/monsters/batch_elementals.json` |
| Elemental, Fire (Huge) | 7 | ✅ | `data/srd_3.5/monsters/batch_elementals.json` |
| Elemental, Fire (Greater) | 9 | ✅ | `data/srd_3.5/monsters/batch_elementals.json` |
| Elemental, Fire (Elder) | 11 | ✅ | `data/srd_3.5/monsters/batch_elementals.json` |
| Elemental, Water (Small) | 1 | ✅ | `data/srd_3.5/monsters/batch_elementals.json` |
| Elemental, Water (Medium) | 3 | ✅ | `data/srd_3.5/monsters/batch_elementals.json` |
| Elemental, Water (Large) | 5 | ✅ | `data/srd_3.5/monsters/batch_elementals.json` |
| Elemental, Water (Huge) | 7 | ✅ | `data/srd_3.5/monsters/batch_elementals.json` |
| Elemental, Water (Greater) | 9 | ✅ | `data/srd_3.5/monsters/batch_elementals.json` |
| Elemental, Water (Elder) | 11 | ✅ | `data/srd_3.5/monsters/batch_elementals.json` |
| Mephit, Air | 3 | ✅ | `data/srd_3.5/monsters/batch_elementals.json` |
| Mephit, Dust | 3 | ✅ | `data/srd_3.5/monsters/batch_elementals.json` |
| Mephit, Earth | 3 | ✅ | `data/srd_3.5/monsters/batch_elementals.json` |
| Mephit, Fire | 3 | ✅ | `data/srd_3.5/monsters/batch_elementals.json` |
| Mephit, Ice | 3 | ✅ | `data/srd_3.5/monsters/batch_elementals.json` |
| Mephit, Magma | 4 | ✅ | `data/srd_3.5/monsters/batch_elementals.json` |
| Mephit, Ooze | 3 | ✅ | `data/srd_3.5/monsters/batch_elementals.json` |
| Mephit, Salt | 3 | ✅ | `data/srd_3.5/monsters/batch_elementals.json` |
| Mephit, Steam | 3 | ✅ | `data/srd_3.5/monsters/batch_elementals.json` |
| Mephit, Water | 3 | ✅ | `data/srd_3.5/monsters/batch_elementals.json` |

---

### Fey

| Monster | CR | Status | Notes |
|---------|----|--------|-------|
| Dryad | 3 | ✅ | `data/srd_3.5/monsters/batch_fey.json` |
| Nymph | 7 | ✅ | `data/srd_3.5/monsters/batch_fey.json` |
| Pixie | 4 | ✅ | `data/srd_3.5/monsters/batch_fey.json` |
| Satyr | 4 | ✅ | `data/srd_3.5/monsters/batch_fey.json` |
| Sprite | 1 | ✅ | `data/srd_3.5/monsters/batch_fey.json` |
| Treant | 8 | ✅ | `data/srd_3.5/monsters/batch_s_z.json` |

---

### Giants

| Monster | CR | Status | Notes |
|---------|----|--------|-------|
| Cloud Giant | 11 | ✅ | `data/srd_3.5/monsters/batch_giants.json` |
| Ettin | 6 | ✅ | `data/srd_3.5/monsters/batch_giants.json` |
| Giant, Fire | 10 | ✅ | `data/srd_3.5/monsters/batch_giants.json` |
| Giant, Frost | 9 | ✅ | `data/srd_3.5/monsters/batch_giants.json` |
| Giant, Hill | 7 | ✅ | `data/srd_3.5/monsters/batch_giants.json` |
| Giant, Stone | 8 | ✅ | `data/srd_3.5/monsters/batch_giants.json` |
| Giant, Storm | 13 | ✅ | `data/srd_3.5/monsters/batch_giants.json` |
| Ogre | 3 | ✅ | `data/srd_3.5/monsters/batch_m_r.json` |
| Ogre Mage | 8 | ✅ | `data/srd_3.5/monsters/batch_giants.json` |
| Troll | 5 | ✅ | `data/srd_3.5/monsters/batch_s_z.json` |

---

### Humanoids

| Monster | CR | Status | Notes |
|---------|----|--------|-------|
| Bullywug | 1 | ✅ | `data/srd_3.5/monsters/batch_humanoids_new.json` |
| Drow (Elf, Drow) | 1 | ✅ | `data/srd_3.5/monsters/batch_d_g.json` |
| Duergar | 1 | ✅ | `data/srd_3.5/monsters/batch_humanoids_new.json` |
| Gnoll | 1 | ✅ | `data/srd_3.5/monsters/batch_d_g.json`; also stub in `core.json` |
| Goblin | 1/3 | ✅ | `data/srd_3.5/monsters/batch_humanoids_new.json` |
| Grimlock | 1 | ✅ | `data/srd_3.5/monsters/batch_humanoids_new.json` |
| Hobgoblin | 1/2 | ✅ | `data/srd_3.5/monsters/batch_h_l.json`; also stub in `core.json` |
| Kobold | 1/4 | ✅ | `data/srd_3.5/monsters/batch_h_l.json`; also stub in `core.json` |
| Kuo-Toa | 2 | ✅ | `data/srd_3.5/monsters/batch_humanoids_new.json` |
| Lizardfolk | 1 | ✅ | `data/srd_3.5/monsters/batch_h_l.json`; also stub in `core.json` |
| Locathah | 1 | ✅ | `data/srd_3.5/monsters/batch_humanoids_new.json` |
| Merfolk | 1/2 | ✅ | `data/srd_3.5/monsters/batch_humanoids_new.json` |
| Orc | 1/2 | ✅ | `data/srd_3.5/monsters/batch_m_r.json`; also stub in `core.json` |
| Sahuagin | 2 | ✅ | `data/srd_3.5/monsters/batch_s_z.json` |
| Svirfneblin (Deep Gnome) | 1 | ✅ | `data/srd_3.5/monsters/batch_humanoids_new.json` |
| Troglodyte | 1 | ✅ | `data/srd_3.5/monsters/batch_humanoids_new.json` |
| Yuan-ti Pureblood | 3 | ✅ | `data/srd_3.5/monsters/batch_s_z.json` |
| Yuan-ti Halfblood | 5 | ✅ | `data/srd_3.5/monsters/batch_humanoids_new.json` |
| Yuan-ti Abomination | 7 | ✅ | `data/srd_3.5/monsters/batch_humanoids_new.json` |

---

### Magical Beasts

| Monster | CR | Status | Notes |
|---------|----|--------|-------|
| Basilisk | 5 | ✅ | `data/srd_3.5/monsters/batch_magical_beasts.json` |
| Behir | 8 | ✅ | `data/srd_3.5/monsters/batch_magical_beasts.json` |
| Blink Dog | 2 | ✅ | `data/srd_3.5/monsters/batch_magical_beasts.json` |
| Bulette | 7 | ✅ | `data/srd_3.5/monsters/batch_magical_beasts.json` |
| Chimera | 7 | ✅ | `data/srd_3.5/monsters/batch_a_c.json`; also stub in `core.json` |
| Cockatrice | 3 | ✅ | `data/srd_3.5/monsters/batch_magical_beasts.json` |
| Digester | 6 | ✅ | `data/srd_3.5/monsters/batch_magical_beasts.json` |
| Displacer Beast | 4 | ✅ | `data/srd_3.5/monsters/batch_magical_beasts.json` |
| Ethereal Marauder | 3 | ✅ | `data/srd_3.5/monsters/batch_magical_beasts.json` |
| Girallon | 6 | ✅ | `data/srd_3.5/monsters/batch_magical_beasts.json` |
| Gorgon | 8 | ✅ | `data/srd_3.5/monsters/batch_magical_beasts.json` |
| Griffon | 4 | ✅ | `data/srd_3.5/monsters/batch_magical_beasts.json` |
| Gynosphinx | 8 | ✅ | `data/srd_3.5/monsters/batch_magical_beasts.json` |
| Androsphinx | 12 | ✅ | `data/srd_3.5/monsters/batch_magical_beasts.json` |
| Hippogriff | 2 | ✅ | `data/srd_3.5/monsters/batch_magical_beasts.json` |
| Hydra (5-headed) | 4 | ✅ | `data/srd_3.5/monsters/batch_h_l.json`; also stub in `core.json` |
| Kraken | 20 | ✅ | `data/srd_3.5/monsters/batch_h_l.json` |
| Lamia | 6 | ✅ | `data/srd_3.5/monsters/batch_magical_beasts.json` |
| Manticore | 5 | ✅ | `data/srd_3.5/monsters/batch_magical_beasts.json` |
| Owlbear | 4 | ✅ | `data/srd_3.5/monsters/batch_magical_beasts.json` |
| Pegasus | 3 | ✅ | `data/srd_3.5/monsters/batch_magical_beasts.json` |
| Phase Spider | 5 | ✅ | `data/srd_3.5/monsters/batch_magical_beasts.json` |
| Purple Worm | 12 | ✅ | `data/srd_3.5/monsters/batch_m_r.json` |
| Remorhaz | 7 | ✅ | `data/srd_3.5/monsters/batch_magical_beasts.json` |
| Sea Cat | 4 | ✅ | `data/srd_3.5/monsters/batch_magical_beasts.json` |
| Shocker Lizard | 2 | ✅ | `data/srd_3.5/monsters/batch_magical_beasts.json` |
| Stirge | 1/2 | ✅ | `data/srd_3.5/monsters/batch_magical_beasts.json` |
| Tarrasque | 20 | ✅ | `data/srd_3.5/monsters/batch_s_z.json` |
| Unicorn | 3 | ✅ | `data/srd_3.5/monsters/batch_magical_beasts.json` |
| Winter Wolf | 5 | ✅ | `data/srd_3.5/monsters/batch_magical_beasts.json` |
| Worg | 2 | ✅ | `data/srd_3.5/monsters/batch_magical_beasts.json` |
| Wyvern | 6 | ✅ | `data/srd_3.5/monsters/batch_magical_beasts.json` |

---

### Monstrous Humanoids

| Monster | CR | Status | Notes |
|---------|----|--------|-------|
| Annis (Hag) | 6 | ✅ | `data/srd_3.5/monsters/batch_monstrous_humanoids.json` |
| Bugbear | 2 | ✅ | `data/srd_3.5/monsters/batch_a_c.json` |
| Centaur | 3 | ✅ | `data/srd_3.5/monsters/batch_a_c.json`; also stub in `core.json` |
| Gargoyle | 4 | ✅ | `data/srd_3.5/monsters/batch_monstrous_humanoids.json` |
| Green Hag | 5 | ✅ | `data/srd_3.5/monsters/batch_monstrous_humanoids.json` |
| Harpy | 4 | ✅ | `data/srd_3.5/monsters/batch_h_l.json`; also stub in `core.json` |
| Medusa | 7 | ✅ | `data/srd_3.5/monsters/batch_monstrous_humanoids.json` |
| Minotaur | 4 | ✅ | `data/srd_3.5/monsters/batch_m_r.json` |
| Naga, Dark | 8 | ✅ | `data/srd_3.5/monsters/batch_monstrous_humanoids.json` |
| Naga, Guardian | 10 | ✅ | `data/srd_3.5/monsters/batch_monstrous_humanoids.json` |
| Naga, Spirit | 9 | ✅ | `data/srd_3.5/monsters/batch_monstrous_humanoids.json` |
| Naga, Water | 7 | ✅ | `data/srd_3.5/monsters/batch_monstrous_humanoids.json` |
| Sea Hag | 4 | ✅ | `data/srd_3.5/monsters/batch_monstrous_humanoids.json` |
| Troglodyte | 1 | ✅ | `data/srd_3.5/monsters/batch_monstrous_humanoids.json` |

---

### Oozes

| Monster | CR | Status | Notes |
|---------|----|--------|-------|
| Black Pudding | 7 | ✅ | `data/srd_3.5/monsters/batch_oozes.json` |
| Gelatinous Cube | 3 | ✅ | `data/srd_3.5/monsters/batch_oozes.json` |
| Gray Ooze | 4 | ✅ | `data/srd_3.5/monsters/batch_oozes.json` |
| Ochre Jelly | 5 | ✅ | `data/srd_3.5/monsters/batch_oozes.json` |

---

### Outsiders (Demons)

| Monster | CR | Status | Notes |
|---------|----|--------|-------|
| Babau | 6 | ✅ | `data/srd_3.5/monsters/batch_outsiders_demons.json` |
| Balor | 20 | ✅ | `data/srd_3.5/monsters/batch_outsiders_demons.json` |
| Dretch | 2 | ✅ | `data/srd_3.5/monsters/batch_outsiders_demons.json` |
| Glabrezu | 13 | ✅ | `data/srd_3.5/monsters/batch_outsiders_demons.json` |
| Hezrou | 11 | ✅ | `data/srd_3.5/monsters/batch_outsiders_demons.json` |
| Marilith | 17 | ✅ | `data/srd_3.5/monsters/batch_outsiders_demons.json` |
| Nalfeshnee | 14 | ✅ | `data/srd_3.5/monsters/batch_outsiders_demons.json` |
| Quasit | 2 | ✅ | `data/srd_3.5/monsters/batch_outsiders_demons.json` |
| Succubus | 7 | ✅ | `data/srd_3.5/monsters/batch_outsiders_demons.json` |
| Vrock | 9 | ✅ | `data/srd_3.5/monsters/batch_outsiders_demons.json` |

---

### Outsiders (Devils)

| Monster | CR | Status | Notes |
|---------|----|--------|-------|
| Devil, Barbed (Hamatula) | 11 | ✅ | `data/srd_3.5/monsters/batch_outsiders_devils.json` |
| Devil, Bearded (Barbazu) | 5 | ✅ | `data/srd_3.5/monsters/batch_outsiders_devils.json` |
| Devil, Bone (Osyluth) | 9 | ✅ | `data/srd_3.5/monsters/batch_outsiders_devils.json` |
| Devil, Chain (Kyton) | 6 | ✅ | `data/srd_3.5/monsters/batch_outsiders_devils.json` |
| Devil, Erinyes | 8 | ✅ | `data/srd_3.5/monsters/batch_outsiders_devils.json` |
| Devil, Horned (Cornugon) | 16 | ✅ | `data/srd_3.5/monsters/batch_outsiders_devils.json` |
| Devil, Ice (Gelugon) | 13 | ✅ | `data/srd_3.5/monsters/batch_outsiders_devils.json` |
| Devil, Lemure | 1 | ✅ | `data/srd_3.5/monsters/batch_outsiders_devils.json` |
| Devil, Pit Fiend | 20 | ✅ | `data/srd_3.5/monsters/batch_outsiders_devils.json` |

---

### Outsiders (Celestials / Archons / Azata)

| Monster | CR | Status | Notes |
|---------|----|--------|-------|
| Angel, Astral Deva | 14 | ✅ | `data/srd_3.5/monsters/batch_outsiders_celestials.json` |
| Angel, Planetar | 16 | ✅ | `data/srd_3.5/monsters/batch_outsiders_celestials.json` |
| Angel, Solar | 23 | ✅ | `data/srd_3.5/monsters/batch_outsiders_celestials.json` |
| Archon, Hound | 4 | ✅ | `data/srd_3.5/monsters/batch_outsiders_celestials.json` |
| Archon, Lantern | 2 | ✅ | `data/srd_3.5/monsters/batch_outsiders_celestials.json` |
| Archon, Trumpet | 14 | ✅ | `data/srd_3.5/monsters/batch_outsiders_celestials.json` |
| Azata, Bralani | 6 | ✅ | `data/srd_3.5/monsters/batch_outsiders_celestials.json` |
| Azata, Ghaele | 13 | ✅ | `data/srd_3.5/monsters/batch_outsiders_celestials.json` |

---

### Outsiders (Other)

| Monster | CR | Status | Notes |
|---------|----|--------|-------|
| Djinni | 5 | ✅ | `data/srd_3.5/monsters/batch_outsiders_other.json` |
| Efreeti | 8 | ✅ | `data/srd_3.5/monsters/batch_outsiders_other.json` |
| Formian Worker | 1/2 | ✅ | `data/srd_3.5/monsters/batch_d_g.json` |
| Formian Warrior | 3 | ✅ | `data/srd_3.5/monsters/batch_outsiders_other.json` |
| Formian Taskmaster | 7 | ✅ | `data/srd_3.5/monsters/batch_outsiders_other.json` |
| Formian Myrmarch | 10 | ✅ | `data/srd_3.5/monsters/batch_outsiders_other.json` |
| Formian Queen | 17 | ✅ | `data/srd_3.5/monsters/batch_outsiders_other.json` |
| Hell Hound | 3 | ✅ | `data/srd_3.5/monsters/batch_h_l.json` |
| Inevitable, Kolyarut | 12 | ✅ | `data/srd_3.5/monsters/batch_outsiders_other.json` |
| Inevitable, Marut | 15 | ✅ | `data/srd_3.5/monsters/batch_outsiders_other.json` |
| Inevitable, Zelekhut | 9 | ✅ | `data/srd_3.5/monsters/batch_outsiders_other.json` |
| Jann | 4 | ✅ | `data/srd_3.5/monsters/batch_outsiders_other.json` |
| Marid | 9 | ✅ | `data/srd_3.5/monsters/batch_outsiders_other.json` |
| Night Hag | 9 | ✅ | `data/srd_3.5/monsters/batch_outsiders_other.json` |
| Nightmare | 5 | ✅ | `data/srd_3.5/monsters/batch_outsiders_other.json` |
| Rakshasa | 10 | ✅ | `data/srd_3.5/monsters/batch_m_r.json` |
| Slaad, Red | 7 | ✅ | `data/srd_3.5/monsters/batch_outsiders_other.json` |
| Slaad, Blue | 8 | ✅ | `data/srd_3.5/monsters/batch_outsiders_other.json` |
| Slaad, Green | 9 | ✅ | `data/srd_3.5/monsters/batch_outsiders_other.json` |
| Slaad, Gray | 10 | ✅ | `data/srd_3.5/monsters/batch_outsiders_other.json` |
| Slaad, Death | 13 | ✅ | `data/srd_3.5/monsters/batch_outsiders_other.json` |
| Tojanida (Juvenile) | 3 | ✅ | `data/srd_3.5/monsters/batch_outsiders_other.json` |
| Tojanida (Adult) | 5 | ✅ | `data/srd_3.5/monsters/batch_outsiders_other.json` |
| Tojanida (Elder) | 9 | ✅ | `data/srd_3.5/monsters/batch_outsiders_other.json` |
| Xorn (Minor) | 3 | ✅ | `data/srd_3.5/monsters/batch_outsiders_other.json` |
| Xorn (Average) | 6 | ✅ | `data/srd_3.5/monsters/batch_outsiders_other.json` |
| Xorn (Elder) | 8 | ✅ | `data/srd_3.5/monsters/batch_outsiders_other.json` |

---

### Plants

| Monster | CR | Status | Notes |
|---------|----|--------|-------|
| Assassin Vine | 3 | ✅ | `data/srd_3.5/monsters/batch_plants.json` |
| Phantom Fungus | 2 | ✅ | `data/srd_3.5/monsters/batch_plants.json` |
| Shrieker | 1 | ✅ | `data/srd_3.5/monsters/batch_plants.json` |
| Tendriculos | 6 | ✅ | `data/srd_3.5/monsters/batch_plants.json` |
| Violet Fungus | 3 | ✅ | `data/srd_3.5/monsters/batch_plants.json` |
| Yellow Musk Creeper | 6 | ✅ | `data/srd_3.5/monsters/batch_plants.json` |

---

### Templates

> Templates modify a base creature. Implement as modifier functions / dataclass overlays, not standalone stat blocks.

| Template | Status | Notes |
|----------|--------|-------|
| Celestial Creature | ✅ | `data/srd_3.5/monsters/batch_templates.json` |
| Fiendish Creature | ✅ | `data/srd_3.5/monsters/batch_templates.json` |
| Half-Celestial | ✅ | `data/srd_3.5/monsters/batch_templates.json` |
| Half-Dragon | ✅ | `data/srd_3.5/monsters/batch_templates.json` |
| Half-Fiend | ✅ | `data/srd_3.5/monsters/batch_templates.json` |
| Lich (template) | ✅ | `data/srd_3.5/monsters/batch_templates.json` |
| Lycanthrope — Werebear | ✅ | `data/srd_3.5/monsters/batch_templates.json` |
| Lycanthrope — Wereboar | ✅ | `data/srd_3.5/monsters/batch_templates.json` |
| Lycanthrope — Wererat | ✅ | `data/srd_3.5/monsters/batch_templates.json` |
| Lycanthrope — Weretiger | ✅ | `data/srd_3.5/monsters/batch_templates.json` |
| Lycanthrope — Werewolf | ✅ | `data/srd_3.5/monsters/batch_templates.json` |
| Skeleton (template) | ✅ | `data/srd_3.5/monsters/batch_templates.json` |
| Vampire (template) | ✅ | `data/srd_3.5/monsters/batch_s_z.json` — representative entry |
| Zombie (template) | ✅ | `data/srd_3.5/monsters/batch_s_z.json` — human base |

---

### Undead

| Monster | CR | Status | Notes |
|---------|----|--------|-------|
| Allip | 3 | ✅ | `data/srd_3.5/monsters/batch_undead.json` |
| Bodak | 8 | ✅ | `data/srd_3.5/monsters/batch_undead.json` |
| Devourer | 11 | ✅ | `data/srd_3.5/monsters/batch_undead.json` |
| Ghost (human warrior example) | 5+ | ✅ | `data/srd_3.5/monsters/batch_undead.json` |
| Ghast | 3 | ✅ | `data/srd_3.5/monsters/batch_undead.json` |
| Ghoul | 1 | ✅ | `data/srd_3.5/monsters/batch_undead.json` (was stub in `core.json`) |
| Lich (example) | 11+ | ✅ | `data/srd_3.5/monsters/batch_undead.json` |
| Mohrg | 8 | ✅ | `data/srd_3.5/monsters/batch_undead.json` |
| Mummy | 5 | ✅ | `data/srd_3.5/monsters/batch_undead.json` (was stub in `core.json`) |
| Shadow | 3 | ✅ | `data/srd_3.5/monsters/batch_s_z.json` |
| Specter | 7 | ✅ | `data/srd_3.5/monsters/batch_undead.json` |
| Vampire (example) | 8+ | ✅ | `data/srd_3.5/monsters/batch_s_z.json` |
| Wight | 3 | ✅ | `data/srd_3.5/monsters/batch_undead.json` (was stub in `core.json`) |
| Wraith | 5 | ✅ | `data/srd_3.5/monsters/batch_s_z.json`; also stub in `core.json` |

---

### Vermin

| Monster | CR | Status | Notes |
|---------|----|--------|-------|
| Ant, Giant (Worker) | 1 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` (was stub in `core.json`) |
| Ant, Giant (Soldier) | 2 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Ant, Giant (Queen) | 2 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Bee, Giant | 1 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Beetle, Giant Bombardier | 2 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Beetle, Giant Fire | 1/3 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Centipede, Monstrous (Tiny) | 1/4 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Centipede, Monstrous (Small) | 1/2 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Centipede, Monstrous (Medium) | 1 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Centipede, Monstrous (Large) | 3 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Centipede, Monstrous (Huge) | 6 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Centipede, Monstrous (Gargantuan) | 9 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Centipede, Monstrous (Colossal) | 12 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Leech, Giant | 2 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Scorpion, Giant | 3 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` as Scorpion, Monstrous (Large) (was stub in `core.json`) |
| Scorpion, Monstrous (Tiny) | 1/4 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Scorpion, Monstrous (Small) | 1/2 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Scorpion, Monstrous (Medium) | 1 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Scorpion, Monstrous (Large) | 3 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Scorpion, Monstrous (Huge) | 7 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Scorpion, Monstrous (Gargantuan) | 10 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Scorpion, Monstrous (Colossal) | 12 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Spider, Monstrous (Tiny) | 1/4 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Spider, Monstrous (Small) | 1/2 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Spider, Monstrous (Medium) | 1 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Spider, Monstrous (Large) | 2 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Spider, Monstrous (Huge) | 5 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Spider, Monstrous (Gargantuan) | 8 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Spider, Monstrous (Colossal) | 11 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Spider, Giant | 1 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` (was stub in `core.json`) |
| Wasp, Giant | 3 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |

---

## Summary

| Status | Count |
|--------|-------|
| ✅ Full stat block | ~353 |
| 🔲 Stub only (name + CR) | ~0 |
| ❌ Not started | ~0 |
| **Total SRD entries** | **~353** |

> Count excludes multi-size vermin/elemental variants counted individually and dragon age categories.
> Infrastructure (LW-001–LW-046) is 100% complete — all remaining work is data population.

---

## Recommended Implementation Order

Prioritise by gameplay impact and CR coverage:

### Phase 1 — Complete the stubs (40 entries, high ROI)
Upgrade all 🔲 `core.json` stubs to full stat blocks. These already exist in the data layer and just need stat population. **Most stubs now promoted** — see Phase 2/3 for remaining gaps.

### Phase 2 — Low-CR dungeon staples (❌ not started, CR ≤ 3)
Goblin, Orc (done), Skeleton variants, Zombie variants, Kobold (done), Rat/Dire Rat (done), Spider (Monstrous, various sizes), Centipede (various), Ghoul, Ghast, Stirge, Blink Dog, Shocker Lizard, Pixie, Sprite.

### Phase 3 — Mid-CR monsters (CR 4–10)
Gargoyle, Medusa, Umber Hulk, Displacer Beast, Phase Spider, Basilisk (stub→full), Gelatinous Cube, Gray Ooze, Ochre Jelly, Black Pudding, Annis Hag, Naga variants, Golem (Flesh, Stone, Iron), Demon entry-level (Vrock, Dretch, Quasit), Devil entry-level (Lemure, Bearded, Chain).

### Phase 4 — High-CR boss monsters (CR 11+)
Balor, Pit Fiend, Solar, Planetar, Marut, Lich example, Devourer, Bodak, Slaad variants, Cloud Giant, Storm Giant, Dragon full age progressions.

### Phase 5 — Templates
Implement as modifier overlays: Celestial, Fiendish, Half-Dragon, Half-Fiend, Half-Celestial, Lycanthrope variants.

---

## Completion Notes

### 2026-04-30 — Aberrations, Animals, Constructs, Elementals, Fey, Giants, Humanoids (new), Magical Beasts, Monstrous Humanoids, Oozes, Outsiders (Demons), Outsiders (Devils), Plants batches

**Aberrations batch — `data/srd_3.5/monsters/batch_aberrations.json`** (15 entries)
- Carrion Crawler (CR 4), Chuul (CR 7), Cloaker (CR 5), Delver (CR 9), Destrachan (CR 8),
  Digester/Aberration (CR 6), Ethereal Filcher (CR 3), Gibbering Mouther (CR 5), Grick (CR 3),
  Mimic (CR 4), Otyugh (CR 4), Roper (CR 12), Skum (CR 2), Umber Hulk (CR 7), Will-o'-Wisp (CR 6).
- Promotes Will-o'-Wisp stub from `core.json` to full stat block.

**Animals (A–M) batch — `data/srd_3.5/monsters/batch_animals_a_m.json`** (37 entries)
- Ape, Ape Dire, Badger, Badger Dire, Bat Swarm, Bear (Black/Brown/Dire/Polar), Bison, Boar, Boar Dire,
  Camel, Cat, Cheetah, Crocodile, Crocodile Dire, Dog, Dog Riding, Donkey, Eagle, Eagle Giant,
  Elephant, Frog Giant, Hawk, Horse (Heavy/Light/Warhorse Heavy/Warhorse Light), Hyena,
  Leopard, Lion, Lion Dire, Mammoth, Manta Ray, Monkey, Mule.
- Promotes stubs (Bear Black, Bear Polar, Crocodile, Eagle Giant, Frog Giant, Lion, Lion Dire, Mammoth) to full stat blocks.

**Animals (N–Z) batch — `data/srd_3.5/monsters/batch_animals_n_z.json`** (35 entries)
- Octopus, Octopus Giant, Owl, Owl Giant, Pony, Porpoise, Rat, Rat Dire, Raven, Rhinoceros, Roc,
  Shark (Large/Huge/Dire), Snake Constrictor, Snake Constrictor Giant,
  Snake Viper (Tiny/Small/Medium/Large/Huge/Giant), Snow Leopard, Squid, Squid Giant,
  Tiger, Tiger Dire, Toad, Weasel, Weasel Dire, Whale (Baleen/Cachalot/Orca), Wolf, Wolf Dire,
  Wolverine, Wolverine Dire, Yeti.
- Promotes stubs (Rat Dire, Roc, Snake Viper Giant, Snow Leopard, Wolf, Wolf Dire, Yeti) to full stat blocks.

**Constructs batch — `data/srd_3.5/monsters/batch_constructs.json`** (13 entries)
- Animated Object (Tiny/Small/Medium/Large/Huge/Gargantuan/Colossal),
  Golem (Clay CR 10 / Flesh CR 7 / Iron CR 13 / Stone CR 11), Homunculus (CR 1), Shield Guardian (CR 8).

**Elementals batch — `data/srd_3.5/monsters/batch_elementals.json`** (34 entries)
- Air/Earth/Fire/Water Elementals (Small/Medium/Large/Huge/Greater/Elder) — 24 entries.
- Mephit (Air/Dust/Earth/Fire/Ice/Magma/Ooze/Salt/Steam/Water) — 10 entries.
- Promotes stubs (Mephit Dust, Fire, Ice) to full stat blocks.

**Fey batch — `data/srd_3.5/monsters/batch_fey.json`** (5 entries)
- Dryad (CR 3), Nymph (CR 7), Pixie (CR 4), Satyr (CR 4), Sprite (CR 1).
- Promotes Dryad stub from `core.json` to full stat block.

**Giants batch — `data/srd_3.5/monsters/batch_giants.json`** (8 entries)
- Cloud Giant (CR 11), Ettin (CR 6), Fire Giant (CR 10), Frost Giant (CR 9), Hill Giant (CR 7),
  Ogre Mage (CR 8), Stone Giant (CR 8), Storm Giant (CR 13).
- Promotes stubs (Cloud Giant, Ettin, Frost Giant, Hill Giant, Stone Giant) to full stat blocks.

**Humanoids (new) batch — `data/srd_3.5/monsters/batch_humanoids_new.json`** (11 entries)
- Bullywug (CR 1), Duergar (CR 1), Goblin (CR 1/3), Grimlock (CR 1), Kuo-Toa (CR 2),
  Locathah (CR 1), Merfolk (CR 1/2), Svirfneblin (CR 1), Troglodyte (CR 1),
  Yuan-ti Halfblood (CR 5), Yuan-ti Abomination (CR 7).
- Promotes stubs (Bullywug, Goblin) to full stat blocks.

**Magical Beasts batch — `data/srd_3.5/monsters/batch_magical_beasts.json`** (27 entries)
- Basilisk, Behir, Blink Dog, Bulette, Cockatrice, Digester/Magical Beast, Displacer Beast,
  Ethereal Marauder, Girallon, Gorgon, Griffon, Gynosphinx, Androsphinx, Hippogriff, Lamia,
  Manticore, Owlbear, Pegasus, Phase Spider, Remorhaz, Sea Cat, Shocker Lizard, Stirge,
  Unicorn, Winter Wolf, Worg, Wyvern.
- Promotes stubs (Basilisk, Bulette, Griffon, Androsphinx, Hippogriff, Lamia, Manticore, Owlbear,
  Remorhaz, Winter Wolf, Wyvern) to full stat blocks.

**Monstrous Humanoids batch — `data/srd_3.5/monsters/batch_monstrous_humanoids.json`** (10 entries)
- Annis Hag (CR 6), Gargoyle (CR 4), Green Hag (CR 5), Medusa (CR 7),
  Naga (Dark CR 8 / Guardian CR 10 / Spirit CR 9 / Water CR 7), Sea Hag (CR 4), Troglodyte (CR 1).
- Promotes stubs (Green Hag, Sea Hag) to full stat blocks.

**Oozes batch — `data/srd_3.5/monsters/batch_oozes.json`** (4 entries)
- Black Pudding (CR 7), Gelatinous Cube (CR 3), Gray Ooze (CR 4), Ochre Jelly (CR 5).

**Outsiders (Demons) batch — `data/srd_3.5/monsters/batch_outsiders_demons.json`** (10 entries)
- Babau (CR 6), Balor (CR 20), Dretch (CR 2), Glabrezu (CR 13), Hezrou (CR 11),
  Marilith (CR 17), Nalfeshnee (CR 14), Quasit (CR 2), Succubus (CR 7), Vrock (CR 9).

**Outsiders (Devils) batch — `data/srd_3.5/monsters/batch_outsiders_devils.json`** (9 entries)
- Devil Barbed/Hamatula (CR 11), Devil Bearded/Barbazu (CR 5), Devil Bone/Osyluth (CR 9),
  Devil Chain/Kyton (CR 6), Devil Erinyes (CR 8), Devil Horned/Cornugon (CR 16),
  Devil Ice/Gelugon (CR 13), Devil Lemure (CR 1), Devil Pit Fiend (CR 20).

**Plants batch — `data/srd_3.5/monsters/batch_plants.json`** (6 entries)
- Assassin Vine (CR 3), Phantom Fungus (CR 2), Shrieker (CR 1), Tendriculos (CR 6),
  Violet Fungus (CR 3), Yellow Musk Creeper (CR 6).

---

### 2026-04-30 — Undead batch + Vermin batch

**Undead batch — `data/srd_3.5/monsters/batch_undead.json`** (11 entries)
- Allip (CR 3), Bodak (CR 8), Devourer (CR 11), Ghost / Human Warrior 5 (CR 5),
  Ghast (CR 3), Ghoul (CR 1), Lich / Human Wizard 11 (CR 11), Mohrg (CR 8),
  Mummy (CR 5), Specter (CR 7), Wight (CR 3).
- Promotes 3 stubs from `core.json` (Ghoul, Mummy, Wight) to full stat blocks.
- Full v2 schema compliance: ecology fields, passive_effects for auras/gazes,
  elemental_weaknesses (fire → Mummy), DR (Mummy 5/—, Lich 15/bludgeoning and magic),
  SR (Devourer 21), fast_heal (Mohrg 5).

**Vermin batch — `data/srd_3.5/monsters/batch_vermin.json`** (20 entries)
- Ant, Giant (Worker CR 1 / Soldier CR 2 / Queen CR 2).
- Bee, Giant (CR 1).
- Beetle, Giant Bombardier (CR 2) / Giant Fire (CR 1/3).
- Centipede, Monstrous (Small CR 1/2 / Medium CR 1 / Large CR 3 / Huge CR 6).
- Leech, Giant (CR 2).
- Scorpion, Monstrous (Medium CR 1 / Large CR 3 / Huge CR 7).
- Spider, Monstrous (Small CR 1/2 / Medium CR 1 / Large CR 2 / Huge CR 5) + Giant (CR 1).
- Wasp, Giant (CR 3).
- Promotes 3 stubs from `core.json` (Ant Giant Worker, Scorpion Giant, Spider Giant)
  to full stat blocks.

**Full-suite pass count (post-undead+vermin): 3 406 tests passing (2 pre-existing failures unchanged).**

---

### 2026-04-30 — Outsiders (Celestials, Other), Templates, Dragons (extended), Vermin (missing sizes)

**Outsiders (Celestials/Archons/Azata) — `data/srd_3.5/monsters/batch_outsiders_celestials.json`** (8 entries)
- Angel Astral Deva (CR 14), Angel Planetar (CR 16), Angel Solar (CR 23).
- Archon Hound (CR 4), Archon Lantern (CR 2), Archon Trumpet (CR 14).
- Azata Bralani (CR 6), Azata Ghaele (CR 13).

**Outsiders (Other) — `data/srd_3.5/monsters/batch_outsiders_other.json`** (24 entries)
- Genies: Djinni (CR 5), Efreeti (CR 8), Jann (CR 4), Marid (CR 9).
- Formians: Warrior (CR 3), Taskmaster (CR 7), Myrmarch (CR 10), Queen (CR 17).
- Inevitables: Kolyarut (CR 12), Marut (CR 15), Zelekhut (CR 9).
- Other: Night Hag (CR 9), Nightmare (CR 5).
- Slaadi: Red (CR 7), Blue (CR 8), Green (CR 9), Gray (CR 10), Death (CR 13).
- Tojanida: Juvenile (CR 3), Adult (CR 5), Elder (CR 9).
- Xorn: Minor (CR 3), Average (CR 6), Elder (CR 8).

**Templates — `data/srd_3.5/monsters/batch_templates.json`** (13 entries)
- Skeleton (Human Warrior, CR 1/3 — promotes core.json stub).
- Celestial Creature (Dire Bear example, CR 8; Heavy Horse example, CR 2).
- Fiendish Creature (Giant Constrictor Snake example, CR 6).
- Half-Celestial (Human Paladin 5, CR 7), Half-Dragon (Human Fighter 5, CR 7),
  Half-Fiend (Succubus base, CR 9).
- Lycanthropes: Werewolf (CR 4), Wererat (CR 4), Wereboar (CR 5),
  Weretiger (CR 8), Werebear (CR 8).
- Lich template (overlay/delta descriptor entry).

**Dragons (extended) — `data/srd_3.5/monsters/batch_dragons_extended.json`** (26 entries)
- Black: Wyrmling (CR 3), Adult (CR 14), Ancient (CR 19), Great Wyrm (CR 22).
- Blue: Young (CR 9), Adult (CR 16), Ancient (CR 21).
- Brass: Young (CR 8), Adult (CR 15). Bronze: Young (CR 10), Adult (CR 17).
- Copper: Young (CR 9), Adult (CR 16). Gold: Young (CR 12), Adult (CR 19), Great Wyrm (CR 25).
- Green: Young (CR 8), Adult (CR 15). Red: Young (CR 10), Adult (CR 17).
- Silver: Young (CR 11), Adult (CR 18). White: Young (CR 5), Adult (CR 12).
- Dragon Turtle (CR 9), Pseudodragon (CR 1).
- Promotes 4 stubs (Blue Young, Green Young, Red Young, White Young) to full stat blocks.

**Vermin (missing sizes) — `data/srd_3.5/monsters/batch_vermin.json`** (10 new entries, now 30 total)
- Centipede, Monstrous (Tiny CR 1/4 / Gargantuan CR 9 / Colossal CR 12).
- Scorpion, Monstrous (Tiny CR 1/4 / Small CR 1/2 / Gargantuan CR 10 / Colossal CR 12).
- Spider, Monstrous (Tiny CR 1/4 / Gargantuan CR 8 / Colossal CR 11).

**Full-suite pass count (post all batches): 3 406 tests passing (2 pre-existing failures unchanged).**
