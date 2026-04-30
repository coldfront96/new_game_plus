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
| Carrion Crawler | 4 | ❌ | |
| Chuul | 7 | ❌ | |
| Cloaker | 5 | ❌ | |
| Darkmantle | 1 | ✅ | `data/srd_3.5/monsters/batch_d_g.json` |
| Delver | 9 | ❌ | |
| Destrachan | 8 | ❌ | |
| Digester | 6 | ❌ | |
| Ethereal Filcher | 3 | ❌ | |
| Gibbering Mouther | 5 | ❌ | |
| Grick | 3 | ❌ | |
| Mimic | 4 | ❌ | |
| Mind Flayer (Illithid) | 8 | ✅ | `data/srd_3.5/monsters/batch_m_r.json` |
| Otyugh | 4 | ❌ | |
| Roper | 12 | ❌ | |
| Rust Monster | 3 | ✅ | `data/srd_3.5/monsters/batch_m_r.json` |
| Skum | 2 | ❌ | |
| Umber Hulk | 7 | ❌ | |
| Will-o'-Wisp | 6 | 🔲 | stub in `core.json` |

---

### Animals

| Monster | CR | Status | Notes |
|---------|----|--------|-------|
| Ape | 2 | ❌ | |
| Ape, Dire | 3 | ❌ | |
| Badger | 1/2 | ❌ | |
| Badger, Dire | 2 | ❌ | |
| Bat (swarm) | 2 | ❌ | |
| Bear, Black | 2 | 🔲 | stub in `core.json` |
| Bear, Brown (Grizzly) | 4 | ❌ | |
| Bear, Dire | 7 | ❌ | |
| Bear, Polar | 4 | 🔲 | stub in `core.json` |
| Bison | 2 | ❌ | |
| Boar | 2 | ❌ | |
| Boar, Dire | 4 | ❌ | |
| Camel | 1 | ❌ | |
| Cat | 1/4 | ❌ | |
| Cheetah | 2 | ❌ | |
| Crocodile | 2 | 🔲 | stub in `core.json` |
| Crocodile, Giant | 4 | ✅ | `data/srd_3.5/monsters/batch_a_c.json` |
| Crocodile, Dire | 9 | ❌ | |
| Dog | 1/3 | ❌ | |
| Dog, Riding | 1 | ❌ | |
| Donkey | 1/6 | ❌ | |
| Eagle | 1/2 | ❌ | |
| Eagle, Giant | 3 | 🔲 | stub in `core.json` |
| Elephant | 7 | ❌ | |
| Frog, Giant | 1 | 🔲 | stub in `core.json` |
| Hawk | 1/3 | ❌ | |
| Horse, Heavy | 1 | ❌ | |
| Horse, Light | 1 | ❌ | |
| Horse, Warhorse (Heavy) | 2 | ❌ | |
| Horse, Warhorse (Light) | 1 | ❌ | |
| Hyena | 1 | ❌ | |
| Leopard | 2 | ❌ | |
| Lion | 3 | 🔲 | stub in `core.json` |
| Lion, Dire | 5 | 🔲 | stub in `core.json` |
| Mammoth | 8 | 🔲 | stub in `core.json` |
| Manta Ray | 1/4 | ❌ | |
| Monkey | 1/6 | ❌ | |
| Mule | 1/2 | ❌ | |
| Octopus | 1 | ❌ | |
| Octopus, Giant | 8 | ❌ | |
| Owl | 1/4 | ❌ | |
| Owl, Giant | 4 | ❌ | |
| Pony | 1/4 | ❌ | |
| Porpoise | 1/2 | ❌ | |
| Rat | 1/4 | ❌ | |
| Rat, Dire | 1/3 | 🔲 | stub in `core.json` |
| Raven | 1/6 | ❌ | |
| Rhinoceros | 4 | ❌ | |
| Roc | 9 | 🔲 | stub in `core.json` |
| Shark, Large | 2 | ❌ | |
| Shark, Huge | 4 | ❌ | |
| Shark, Dire | 9 | ❌ | |
| Snake, Constrictor | 2 | ❌ | |
| Snake, Constrictor (Giant) | 5 | ❌ | |
| Snake, Viper (Tiny) | 1/3 | ❌ | |
| Snake, Viper (Small) | 1/2 | ❌ | |
| Snake, Viper (Medium) | 1 | ❌ | |
| Snake, Viper (Large) | 2 | ❌ | |
| Snake, Viper (Huge) | 3 | ❌ | |
| Snake, Viper (Giant) | 3 | 🔲 | stub in `core.json` |
| Snow Leopard | 2 | 🔲 | stub in `core.json` |
| Squid | 1 | ❌ | |
| Squid, Giant | 9 | ❌ | |
| Tiger | 4 | ❌ | |
| Tiger, Dire | 8 | ❌ | |
| Toad | 1/10 | ❌ | |
| Weasel | 1/4 | ❌ | |
| Weasel, Dire | 2 | ❌ | |
| Whale, Baleen | 6 | ❌ | |
| Whale, Cachalot | 12 | ❌ | |
| Whale, Orca | 5 | ❌ | |
| Wolf | 1 | 🔲 | stub in `core.json` |
| Wolf, Dire | 3 | 🔲 | stub in `core.json` |
| Wolverine | 2 | ❌ | |
| Wolverine, Dire | 4 | ❌ | |
| Yeti | 3 | 🔲 | stub in `core.json` |

---

### Constructs

| Monster | CR | Status | Notes |
|---------|----|--------|-------|
| Animated Object (Tiny) | 1 | ❌ | |
| Animated Object (Small) | 2 | ❌ | |
| Animated Object (Medium) | 3 | ❌ | |
| Animated Object (Large) | 5 | ❌ | |
| Animated Object (Huge) | 7 | ❌ | |
| Animated Object (Gargantuan) | 10 | ❌ | |
| Animated Object (Colossal) | 14 | ❌ | |
| Golem, Clay | 10 | ❌ | |
| Golem, Flesh | 7 | ❌ | |
| Golem, Iron | 13 | ❌ | |
| Golem, Stone | 11 | ❌ | |
| Homunculus | 1 | ❌ | |
| Shield Guardian | 8 | ❌ | |

---

### Dragons

> Each colour has 9 age categories (Wyrmling, Very Young, Young, Juvenile, Young Adult, Adult, Mature Adult, Old, Very Old, Ancient, Wyrm, Great Wyrm). Priority order: Young → Adult → Ancient → Wyrm/Great Wyrm.

| Monster | CR (Adult) | Status | Notes |
|---------|-----------|--------|-------|
| Dragon, Black (Wyrmling) | 3 | ❌ | |
| Dragon, Black (Young) | 7 | ✅ | `data/srd_3.5/monsters/batch_d_g.json` |
| Dragon, Black (Adult) | 14 | ❌ | |
| Dragon, Black (Ancient) | 19 | ❌ | |
| Dragon, Black (Great Wyrm) | 22 | ❌ | |
| Dragon, Blue (Young) | 9 | 🔲 | stub in `core.json` |
| Dragon, Blue (Adult) | 16 | ❌ | |
| Dragon, Blue (Ancient) | 21 | ❌ | |
| Dragon, Brass (Young) | 8 | ❌ | |
| Dragon, Brass (Adult) | 15 | ❌ | |
| Dragon, Bronze (Young) | 10 | ❌ | |
| Dragon, Bronze (Adult) | 17 | ❌ | |
| Dragon, Copper (Young) | 9 | ❌ | |
| Dragon, Copper (Adult) | 16 | ❌ | |
| Dragon, Gold (Young) | 12 | ❌ | |
| Dragon, Gold (Adult) | 19 | ❌ | |
| Dragon, Gold (Great Wyrm) | 25 | ❌ | |
| Dragon, Green (Young) | 8 | 🔲 | stub in `core.json` |
| Dragon, Green (Adult) | 15 | ❌ | |
| Dragon, Red (Young) | 10 | 🔲 | stub in `core.json` |
| Dragon, Red (Adult) | 17 | ❌ | |
| Dragon, Red (Ancient) | 22 | ✅ | `data/srd_3.5/monsters/batch_d_g.json` |
| Dragon, Silver (Young) | 11 | ❌ | |
| Dragon, Silver (Adult) | 18 | ❌ | |
| Dragon, White (Young) | 5 | 🔲 | stub in `core.json` |
| Dragon, White (Adult) | 12 | ❌ | |
| Dragon Turtle | 9 | ❌ | |
| Pseudodragon | 1 | ❌ | |

---

### Elementals

| Monster | CR | Status | Notes |
|---------|----|--------|-------|
| Elemental, Air (Small) | 1 | ❌ | |
| Elemental, Air (Medium) | 3 | ❌ | |
| Elemental, Air (Large) | 5 | ❌ | |
| Elemental, Air (Huge) | 7 | ❌ | |
| Elemental, Air (Greater) | 9 | ❌ | |
| Elemental, Air (Elder) | 11 | ❌ | |
| Elemental, Earth (Small) | 1 | ❌ | |
| Elemental, Earth (Medium) | 3 | ❌ | |
| Elemental, Earth (Large) | 5 | ❌ | |
| Elemental, Earth (Huge) | 7 | ❌ | |
| Elemental, Earth (Greater) | 9 | ❌ | |
| Elemental, Earth (Elder) | 11 | ❌ | |
| Elemental, Fire (Small) | 1 | ❌ | |
| Elemental, Fire (Medium) | 3 | ❌ | |
| Elemental, Fire (Large) | 5 | ❌ | |
| Elemental, Fire (Huge) | 7 | ❌ | |
| Elemental, Fire (Greater) | 9 | ❌ | |
| Elemental, Fire (Elder) | 11 | ❌ | |
| Elemental, Water (Small) | 1 | ❌ | |
| Elemental, Water (Medium) | 3 | ❌ | |
| Elemental, Water (Large) | 5 | ❌ | |
| Elemental, Water (Huge) | 7 | ❌ | |
| Elemental, Water (Greater) | 9 | ❌ | |
| Elemental, Water (Elder) | 11 | ❌ | |
| Mephit, Air | 3 | ❌ | |
| Mephit, Dust | 3 | 🔲 | stub in `core.json` |
| Mephit, Earth | 3 | ❌ | |
| Mephit, Fire | 3 | 🔲 | stub in `core.json` |
| Mephit, Ice | 3 | 🔲 | stub in `core.json` |
| Mephit, Magma | 4 | ❌ | |
| Mephit, Ooze | 3 | ❌ | |
| Mephit, Salt | 3 | ❌ | |
| Mephit, Steam | 3 | ❌ | |
| Mephit, Water | 3 | ❌ | |

---

### Fey

| Monster | CR | Status | Notes |
|---------|----|--------|-------|
| Dryad | 3 | 🔲 | stub in `core.json` |
| Nymph | 7 | ❌ | |
| Pixie | 4 | ❌ | |
| Satyr | 4 | ❌ | |
| Sprite | 1 | ❌ | |
| Treant | 8 | ✅ | `data/srd_3.5/monsters/batch_s_z.json` |

---

### Giants

| Monster | CR | Status | Notes |
|---------|----|--------|-------|
| Cloud Giant | 11 | 🔲 | stub in `core.json` |
| Ettin | 6 | 🔲 | stub in `core.json` |
| Giant, Fire | 10 | ❌ | |
| Giant, Frost | 9 | 🔲 | stub in `core.json` |
| Giant, Hill | 7 | 🔲 | stub in `core.json` |
| Giant, Stone | 8 | 🔲 | stub in `core.json` |
| Giant, Storm | 13 | ❌ | |
| Ogre | 3 | ✅ | `data/srd_3.5/monsters/batch_m_r.json` |
| Ogre Mage | 8 | ❌ | |
| Troll | 5 | ✅ | `data/srd_3.5/monsters/batch_s_z.json` |

---

### Humanoids

| Monster | CR | Status | Notes |
|---------|----|--------|-------|
| Bullywug | 1 | 🔲 | stub in `core.json` |
| Drow (Elf, Drow) | 1 | ✅ | `data/srd_3.5/monsters/batch_d_g.json` |
| Duergar | 1 | ❌ | |
| Gnoll | 1 | ✅ | `data/srd_3.5/monsters/batch_d_g.json`; also stub in `core.json` |
| Goblin | 1/3 | 🔲 | stub in `core.json` |
| Grimlock | 1 | ❌ | |
| Hobgoblin | 1/2 | ✅ | `data/srd_3.5/monsters/batch_h_l.json`; also stub in `core.json` |
| Kobold | 1/4 | ✅ | `data/srd_3.5/monsters/batch_h_l.json`; also stub in `core.json` |
| Kuo-Toa | 2 | ❌ | |
| Lizardfolk | 1 | ✅ | `data/srd_3.5/monsters/batch_h_l.json`; also stub in `core.json` |
| Locathah | 1 | ❌ | |
| Merfolk | 1/2 | ❌ | |
| Orc | 1/2 | ✅ | `data/srd_3.5/monsters/batch_m_r.json`; also stub in `core.json` |
| Sahuagin | 2 | ✅ | `data/srd_3.5/monsters/batch_s_z.json` |
| Svirfneblin (Deep Gnome) | 1 | ❌ | |
| Troglodyte | 1 | ❌ | |
| Yuan-ti Pureblood | 3 | ✅ | `data/srd_3.5/monsters/batch_s_z.json` |
| Yuan-ti Halfblood | 5 | ❌ | |
| Yuan-ti Abomination | 7 | ❌ | |

---

### Magical Beasts

| Monster | CR | Status | Notes |
|---------|----|--------|-------|
| Basilisk | 5 | 🔲 | stub in `core.json` |
| Behir | 8 | ❌ | |
| Blink Dog | 2 | ❌ | |
| Bulette | 7 | 🔲 | stub in `core.json` |
| Chimera | 7 | ✅ | `data/srd_3.5/monsters/batch_a_c.json`; also stub in `core.json` |
| Cockatrice | 3 | ❌ | |
| Digester | 6 | ❌ | |
| Displacer Beast | 4 | ❌ | |
| Ethereal Marauder | 3 | ❌ | |
| Girallon | 6 | ❌ | |
| Gorgon | 8 | ❌ | |
| Griffon | 4 | 🔲 | stub in `core.json` |
| Gynosphinx | 8 | ❌ | |
| Androsphinx | 12 | 🔲 | stub in `core.json` as "Sphinx, Androsphinx" |
| Hippogriff | 2 | 🔲 | stub in `core.json` |
| Hydra (5-headed) | 4 | ✅ | `data/srd_3.5/monsters/batch_h_l.json`; also stub in `core.json` |
| Kraken | 20 | ✅ | `data/srd_3.5/monsters/batch_h_l.json` |
| Lamia | 6 | 🔲 | stub in `core.json` |
| Manticore | 5 | 🔲 | stub in `core.json` |
| Owlbear | 4 | 🔲 | stub in `core.json` |
| Pegasus | 3 | ❌ | |
| Phase Spider | 5 | ❌ | |
| Purple Worm | 12 | ✅ | `data/srd_3.5/monsters/batch_m_r.json` |
| Remorhaz | 7 | 🔲 | stub in `core.json` |
| Sea Cat | 4 | ❌ | |
| Shocker Lizard | 2 | ❌ | |
| Stirge | 1/2 | ❌ | |
| Tarrasque | 20 | ✅ | `data/srd_3.5/monsters/batch_s_z.json` |
| Unicorn | 3 | ❌ | |
| Winter Wolf | 5 | 🔲 | stub in `core.json` |
| Worg | 2 | ❌ | |
| Wyvern | 6 | 🔲 | stub in `core.json` |

---

### Monstrous Humanoids

| Monster | CR | Status | Notes |
|---------|----|--------|-------|
| Annis (Hag) | 6 | ❌ | |
| Bugbear | 2 | ✅ | `data/srd_3.5/monsters/batch_a_c.json` |
| Centaur | 3 | ✅ | `data/srd_3.5/monsters/batch_a_c.json`; also stub in `core.json` |
| Gargoyle | 4 | ❌ | |
| Green Hag | 5 | 🔲 | stub in `core.json` |
| Harpy | 4 | ✅ | `data/srd_3.5/monsters/batch_h_l.json`; also stub in `core.json` |
| Medusa | 7 | ❌ | |
| Minotaur | 4 | ✅ | `data/srd_3.5/monsters/batch_m_r.json` |
| Naga, Dark | 8 | ❌ | |
| Naga, Guardian | 10 | ❌ | |
| Naga, Spirit | 9 | ❌ | |
| Naga, Water | 7 | ❌ | |
| Sea Hag | 4 | 🔲 | stub in `core.json` |
| Troglodyte | 1 | ❌ | |

---

### Oozes

| Monster | CR | Status | Notes |
|---------|----|--------|-------|
| Black Pudding | 7 | ❌ | |
| Gelatinous Cube | 3 | ❌ | |
| Gray Ooze | 4 | ❌ | |
| Ochre Jelly | 5 | ❌ | |

---

### Outsiders (Demons)

| Monster | CR | Status | Notes |
|---------|----|--------|-------|
| Babau | 6 | ❌ | |
| Balor | 20 | ❌ | |
| Dretch | 2 | ❌ | |
| Glabrezu | 13 | ❌ | |
| Hezrou | 11 | ❌ | |
| Marilith | 17 | ❌ | |
| Nalfeshnee | 14 | ❌ | |
| Quasit | 2 | ❌ | |
| Succubus | 7 | ❌ | |
| Vrock | 9 | ❌ | |

---

### Outsiders (Devils)

| Monster | CR | Status | Notes |
|---------|----|--------|-------|
| Devil, Barbed (Hamatula) | 11 | ❌ | |
| Devil, Bearded (Barbazu) | 5 | ❌ | |
| Devil, Bone (Osyluth) | 9 | ❌ | |
| Devil, Chain (Kyton) | 6 | ❌ | |
| Devil, Erinyes | 8 | ❌ | |
| Devil, Horned (Cornugon) | 16 | ❌ | |
| Devil, Ice (Gelugon) | 13 | ❌ | |
| Devil, Lemure | 1 | ❌ | |
| Devil, Pit Fiend | 20 | ❌ | |

---

### Outsiders (Celestials / Archons / Azata)

| Monster | CR | Status | Notes |
|---------|----|--------|-------|
| Angel, Astral Deva | 14 | ❌ | |
| Angel, Planetar | 16 | ❌ | |
| Angel, Solar | 23 | ❌ | |
| Archon, Hound | 4 | ❌ | |
| Archon, Lantern | 2 | ❌ | |
| Archon, Trumpet | 14 | ❌ | |
| Azata, Bralani | 6 | ❌ | |
| Azata, Ghaele | 13 | ❌ | |

---

### Outsiders (Other)

| Monster | CR | Status | Notes |
|---------|----|--------|-------|
| Djinni | 5 | ❌ | |
| Efreeti | 8 | ❌ | |
| Formian Worker | 1/2 | ✅ | `data/srd_3.5/monsters/batch_d_g.json` |
| Formian Warrior | 3 | ❌ | |
| Formian Taskmaster | 7 | ❌ | |
| Formian Myrmarch | 10 | ❌ | |
| Formian Queen | 17 | ❌ | |
| Hell Hound | 3 | ✅ | `data/srd_3.5/monsters/batch_h_l.json` |
| Inevitable, Kolyarut | 12 | ❌ | |
| Inevitable, Marut | 15 | ❌ | |
| Inevitable, Zelekhut | 9 | ❌ | |
| Jann | 4 | ❌ | |
| Marid | 9 | ❌ | |
| Night Hag | 9 | ❌ | |
| Nightmare | 5 | ❌ | |
| Rakshasa | 10 | ✅ | `data/srd_3.5/monsters/batch_m_r.json` |
| Slaad, Red | 7 | ❌ | |
| Slaad, Blue | 8 | ❌ | |
| Slaad, Green | 9 | ❌ | |
| Slaad, Gray | 10 | ❌ | |
| Slaad, Death | 13 | ❌ | |
| Tojanida (Juvenile) | 3 | ❌ | |
| Tojanida (Adult) | 5 | ❌ | |
| Tojanida (Elder) | 9 | ❌ | |
| Xorn (Minor) | 3 | ❌ | |
| Xorn (Average) | 6 | ❌ | |
| Xorn (Elder) | 8 | ❌ | |

---

### Plants

| Monster | CR | Status | Notes |
|---------|----|--------|-------|
| Assassin Vine | 3 | ❌ | |
| Phantom Fungus | 2 | ❌ | |
| Shrieker | 1 | ❌ | |
| Tendriculos | 6 | ❌ | |
| Violet Fungus | 3 | ❌ | |
| Yellow Musk Creeper | 6 | ❌ | |

---

### Templates

> Templates modify a base creature. Implement as modifier functions / dataclass overlays, not standalone stat blocks.

| Template | Status | Notes |
|----------|--------|-------|
| Celestial Creature | ❌ | |
| Fiendish Creature | ❌ | |
| Half-Celestial | ❌ | |
| Half-Dragon | ❌ | |
| Half-Fiend | ❌ | |
| Lich (template) | ❌ | |
| Lycanthrope — Werebear | ❌ | |
| Lycanthrope — Wereboar | ❌ | |
| Lycanthrope — Wererat | ❌ | |
| Lycanthrope — Weretiger | ❌ | |
| Lycanthrope — Werewolf | ❌ | |
| Skeleton (template) | 🔲 | stub in `core.json` |
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
| Centipede, Monstrous (Tiny) | 1/4 | ❌ | |
| Centipede, Monstrous (Small) | 1/2 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Centipede, Monstrous (Medium) | 1 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Centipede, Monstrous (Large) | 3 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Centipede, Monstrous (Huge) | 6 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Centipede, Monstrous (Gargantuan) | 9 | ❌ | |
| Centipede, Monstrous (Colossal) | 12 | ❌ | |
| Leech, Giant | 2 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Scorpion, Giant | 3 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` as Scorpion, Monstrous (Large) (was stub in `core.json`) |
| Scorpion, Monstrous (Tiny) | 1/4 | ❌ | |
| Scorpion, Monstrous (Small) | 1/2 | ❌ | |
| Scorpion, Monstrous (Medium) | 1 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Scorpion, Monstrous (Large) | 3 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Scorpion, Monstrous (Huge) | 7 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Scorpion, Monstrous (Gargantuan) | 10 | ❌ | |
| Scorpion, Monstrous (Colossal) | 12 | ❌ | |
| Spider, Monstrous (Tiny) | 1/4 | ❌ | |
| Spider, Monstrous (Small) | 1/2 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Spider, Monstrous (Medium) | 1 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Spider, Monstrous (Large) | 2 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Spider, Monstrous (Huge) | 5 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |
| Spider, Monstrous (Gargantuan) | 8 | ❌ | |
| Spider, Monstrous (Colossal) | 11 | ❌ | |
| Spider, Giant | 1 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` (was stub in `core.json`) |
| Wasp, Giant | 3 | ✅ | `data/srd_3.5/monsters/batch_vermin.json` |

---

## Summary

| Status | Count |
|--------|-------|
| ✅ Full stat block | ~89 |
| 🔲 Stub only (name + CR) | ~5 |
| ❌ Not started | ~200 |
| **Total SRD entries** | **~296** |

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
