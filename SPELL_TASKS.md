# D&D 3.5e Spell Registry — Task Tracker

This file tracks the chunked ingestion of SRD spells into the rules engine. Each
phase must pass `pytest tests/rules_engine/test_magic.py` before the next phase
begins. Do not attempt to ingest multiple phases in a single pass — token
truncation risks mechanical impurity.

## Phases

- [x] Phase 1: Wizard/Sorcerer Arcane Spells (Levels 0–3) + Tests.
- [x] Phase 2: Wizard/Sorcerer Arcane Spells (Levels 4–9) + Tests.
- [x] Phase 3: Cleric & Paladin Divine Spells + Tests.
- [x] Phase 4: Druid & Ranger Nature Spells + Tests.
- [x] Phase 5: Bard Arcane Spells + Tests.

## Completion Notes

- **Phase 1** — 32 new spells added (8 × L0–L3 Wizard/Sorcerer): Detect Magic, Ray of Frost,
  Resistance, Mage Hand, Read Magic, Acid Splash, Daze, Light, Charm Person, Color Spray,
  Feather Fall, Grease, Ray of Enfeeblement, True Strike, Cause Fear, Enlarge Person,
  Scorching Ray, Invisibility, Mirror Image, Web, Bull's Strength, Blur, Resist Energy,
  Bear's Endurance, Fireball, Lightning Bolt, Dispel Magic, Haste, Hold Person, Fly, Slow,
  Vampiric Touch. Registry total: 43 spells. 128 tests passing.

- **Phase 2** — 48 new spells added (L4–L9 Wizard/Sorcerer): Dimension Door, Polymorph,
  Greater Invisibility, Ice Storm, Stoneskin, Confusion, Arcane Eye, Black Tentacles,
  Cone of Cold, Telekinesis, Wall of Force, Cloudkill, Dominate Person, Feeblemind,
  Permanency, Sending, Disintegrate, Chain Lightning, Globe of Invulnerability, True Seeing,
  Contingency, Legend Lore, Repulsion, Mislead, Finger of Death, Power Word Blind,
  Spell Turning, Limited Wish, Prismatic Spray, Reverse Gravity, Ethereal Jaunt,
  Mordenkainen's Sword, Power Word Stun, Mind Blank, Prismatic Wall, Maze, Clone,
  Greater Prying Eyes, Sunburst, Polar Ray, Wish, Time Stop, Meteor Swarm,
  Wail of the Banshee, Power Word Kill, Shapechange, Gate, Foresight.
  Registry total: 91 spells. 251 tests passing.

- **Phase 3** — 48 new divine spells added (Cleric L0–L9 and Paladin L1–L4): Guidance, Virtue,
  Inflict Minor Wounds, Detect Undead, Create Water, Purify Food and Drink, Command, Sanctuary,
  Divine Favor, Doom, Entropic Shield, Cure Moderate Wounds, Silence, Spiritual Weapon,
  Consecrate, Aid, Desecrate, Blindness/Deafness, Cure Serious Wounds, Prayer, Cure Critical Wounds,
  Searing Light, Speak with Dead, Inflict Serious Wounds, Divine Power, Freedom of Movement,
  Neutralize Poison, Restoration, Flame Strike, Insect Plague, Righteous Might, Break Enchantment,
  Blade Barrier, Word of Recall, Resurrection, Mass Heal, Detect Evil, Protection from Evil,
  Bless Weapon, Delay Poison, Shield Other, Owl's Wisdom, Daylight, Remove Blindness/Deafness,
  Holy Sword, Mark of Justice, Dispel Evil, Holy Aura.
  Registry total: 139 spells. 324 tests passing.

- **Phase 4** — 48 new nature spells added (Druid L0–L9 and Ranger L1–L4): Flare, Know Direction,
  Cure Minor Wounds, Detect Animals or Plants, Shillelagh, Mending, Entangle, Faerie Fire,
  Longstrider, Speak with Animals, Animal Friendship, Produce Flame, Barkskin, Call Lightning,
  Charm Animal, Warp Wood, Flame Blade, Tree Shape, Contagion, Water Breathing, Poison,
  Spike Growth, Quench, Rusting Grasp, Command Plants, Reincarnate, Repel Vermin, Animal Growth,
  Awaken, Wall of Fire, Call Lightning Storm, Antilife Shell, Liveoak, Control Weather, Earthquake,
  Elemental Swarm, Storm of Vengeance, Alarm, Animal Messenger, Jump, Snare, Pass without Trace,
  Wind Wall, Heal Animal Companion, Remove Disease, Commune with Nature, Tree Stride, Find the Path.
  Registry total: 187 spells. 436 tests passing.

- **Phase 5** — 42 new Bard arcane spells added (L0–L6): Dancing Lights, Lullaby, Message,
  Open/Close, Summon Instrument, Animate Rope, Comprehend Languages, Expeditious Retreat,
  Hypnotism, Tasha's Hideous Laughter, Undetectable Alignment, Ventriloquism, Disguise Self,
  Alter Self, Cat's Grace, Eagle's Splendor, Enthrall, Heroism, Locate Object, Minor Image,
  Misdirection, Whispering Wind, Charm Monster, Clairaudience/Clairvoyance, Gaseous Form,
  Good Hope, Phantom Steed, Scrying, Sculpt Sound, Shout, Zone of Silence, Modify Memory,
  Greater Heroism, Mass Suggestion, Mirage Arcana, Shadow Walk, Song of Discord, Greater Scrying,
  Irresistible Dance, Mass Charm Monster, Sympathetic Vibration, Veil.
  Registry total: 229 spells. 436 tests passing.
