# AUTHORING_GUIDELINES.md — Content Authoring Guide for AI Agents

> **Audience:** AI agents generating JSON batch files for `data/expanded/`.
> **Purpose:** Ensure every generated entry is mechanically accurate, legally clean,
> and stylistically consistent with the project's High-Fantasy setting.

---

## 1. What Is and Isn't Copyrightable in a TTRPG Context

### Mechanics are not copyrightable

Game rules, procedures, and mathematical stat blocks are **functional** — they
describe how something behaves, not creative expression. The following elements
are uncopyrightable regardless of their source:

- Numerical stats (CR, HD, HP, AC, attack bonus, damage dice, save DCs, speeds)
- Mechanical special-ability structures (e.g. "recharge 5–6 breath weapon dealing
  Xd6 damage in a Y-foot cone, Reflex DC Z for half")
- Action economy descriptions (standard/move/full-round action, immediate reaction)
- Game-system keywords (Fortitude, Reflex, Will, BAB, grapple, trip, etc.)

You may freely derive entries from these mechanical elements regardless of which
publication documented them first.

### Creative expression IS copyrightable

The following elements ARE protected by copyright and/or trademark when they
originate in a WotC publication that is not part of the open SRD:

| Element | Examples |
|---|---|
| Creature names (trademark/PI) | Beholder, Mind Flayer, Displacer Beast, Neogi, Githyanki, Redspawn Arcaniss |
| Flavour text / lore descriptions | Habitat, society, ecology, motivations as written in the source book |
| Artwork descriptions | Visual appearance tied to a specific named creature |
| Setting-specific proper nouns | Named planes, cities, deities, organisations exclusive to WotC settings |

**Rule:** Copy the math; create the expression.

---

## 2. The 90/10 Rule

When generating a batch file, the creatures you will encounter fall into two
categories.

### The 90 % — Public Domain and Open SRD Creatures

The overwhelming majority of fantasy archetypes have existed in mythology,
folklore, or public-domain fiction for centuries and are NOT owned by any game
publisher. These can be digitised with their canonical names intact:

| Category | Examples |
|---|---|
| True Dragons | Red Dragon, Blue Dragon, Green Dragon, Black Dragon, White Dragon |
| Elemental beings | Fire Elemental, Air Elemental, Water Elemental, Earth Elemental |
| Classical undead | Skeleton, Zombie, Vampire, Lich, Ghost, Wight, Wraith |
| Mythological creatures | Griffon, Manticore, Basilisk, Hydra, Medusa, Harpy, Minotaur |
| Giants | Hill Giant, Stone Giant, Frost Giant, Fire Giant, Cloud Giant |
| Fey | Nymph, Dryad, Sylph, Pixie |
| Constructs | Golem (Clay, Stone, Iron) |
| Humanoids | Goblin, Orc, Gnoll, Kobold, Lizardfolk |

For these creatures, generate the JSON entry using the canonical name and
faithful 3.5e stats. No translation required.

### The 10 % — WotC Product Identity Requiring Translation

A minority of creatures were invented by WotC and are designated Product
Identity. When a task spec lists one of these, apply the **Clean-Room
Translation Protocol** (see Section 3) before generating the entry.

Common examples requiring translation:

| WotC PI Name | Archetype to Preserve |
|---|---|
| Beholder | Floating orb aberration with antimagic cone and eye-ray attacks |
| Mind Flayer (Illithid) | Psionic humanoid with tentacle attacks and mind-affecting abilities |
| Displacer Beast | Displacement-field feline predator |
| Neogi | Spider-eel aberration with dominated slave economy |
| Redspawn Arcaniss | Draconic humanoid spellcaster with arcane focus abilities |
| Dracotaur | Dragon-centaur hybrid melee warrior |
| Githyanki / Githzerai | Astral/limbo psionic humanoids |

---

## 3. The Clean-Room Translation Protocol — Step by Step

### Step 1 — Record the pure math

Extract and document only the mechanical stat block:

```
CR, Type/Subtype, Size, HD, HP, Init, Speed
AC breakdown (natural, deflection, dex, etc.)
BAB, Grp
Attack entries (attack bonus, damage dice, crit range, special riders)
Full Attack entries
Space/Reach
Special Attacks (mechanically described — no PI names)
Special Qualities (mechanically described)
Saves (Fort, Ref, Will)
Ability Scores (Str, Dex, Con, Int, Wis, Cha)
Skills (ranks + bonuses)
Feats
Environment / CR / Treasure / Alignment
```

### Step 2 — Discard all protected expression

Delete the following from your working notes before writing the entry:

- The WotC creature name
- Any copied flavour text or physical description from the source book
- Setting-specific lore (named planes, factions, etc.)
- Any artwork or visual description attributable to a specific WotC publication

### Step 3 — Create original expression

Invent a new identity that fits the project's High-Fantasy setting:

- **Name:** Entirely original. Avoid phonetic near-matches to the PI name.
- **Appearance:** Write a fresh physical description. You may keep the same
  *functional* body plan (e.g. "orb-shaped floating creature") but every
  descriptive detail must be your own.
- **Lore:** Write original ecology, habitat, society, and motivations. No
  paraphrase of WotC text.
- **Flavour text:** Original prose only.

### Step 4 — Assemble and tag the JSON entry

Apply the translated name and original lore to the extracted stat block.
Add the following fields to `expanded_metadata`:

```json
"expanded_metadata": {
  "is_expanded": true,
  "source_book": "<source book name>",
  "translated": true,
  "source_archetype": "<creature type, e.g. aberration>"
}
```

Do **not** record the original WotC name in any persisted field.

---

## 4. Worked Example: Dracotaur → Ember-Mane Taurian

### 4.1 Source stat extraction (math only)

```
CR 9 | Dragon (augmented monstrous humanoid) | Large
HD: 10d12+50 | HP: 115 | Init: +0
Speed: 40 ft.
AC: 23 (–1 size, +14 natural) | touch 9 | flat-footed 23
BAB: +10 | Grp: +20
Attack: Greatsword +16 melee (2d6+9/19–20)
  or claw +15 melee (1d8+6)
Full Attack: Greatsword +16/+11 melee (2d6+9/19–20)
  and gore +10 melee (1d8+3);
  or 2 claws +15 melee (1d8+6) and gore +10 (1d8+3) and bite +10 (1d6+3)
Space/Reach: 10 ft./10 ft.
Special Attacks: Breath weapon (30-ft. cone of fire, 6d8, Reflex DC 20 half,
  usable every 1d4 rounds)
Special Qualities: Darkvision 60 ft., low-light vision, immunity to fire,
  paralysis, and sleep; SR 19
Saves: Fort +12, Ref +7, Will +9
Str 23, Dex 10, Con 21, Int 10, Wis 14, Cha 10
Skills: Intimidate +13, Listen +15, Spot +15, Survival +15
Feats: Cleave, Great Cleave, Power Attack, Weapon Focus (greatsword),
  Multiattack
```

### 4.2 Original expression — the Ember-Mane Taurian

**Name:** Ember-Mane Taurian

**Appearance:** A massive creature standing eight feet at the shoulder with
the lower body of a heavily muscled equine and the torso of a draconic
warrior. Its scales shift from deep amber at the haunches to jet-black at
the chest. A mane of perpetually smouldering filaments crowns its angular,
horn-browed head.

**Lore:** Ember-Mane Taurians roam the volcanic steppes of the Cindermarch,
where they serve as self-appointed wardens of ancient flame-shrines. They are
not mindless brutes; each carries a lineage-brand seared into its scales
marking centuries of clan heritage. They despise slavery and will not parley
with those who traffic in it. Their breath is the concentrated heat of a
forge — enough to melt unprotected steel.

### 4.3 Resulting JSON entry (excerpt)

```json
{
  "name": "Ember-Mane Taurian",
  "cr": 9,
  "type": "dragon",
  "subtype": "augmented monstrous humanoid",
  "size": "large",
  "hd": "10d12+50",
  "hp": 115,
  "initiative": 0,
  "speed": {"land": 40},
  "ac": {"total": 23, "touch": 9, "flat_footed": 23,
         "components": {"size": -1, "natural": 14}},
  "bab": 10,
  "grapple": 20,
  "attacks": {
    "standard": [
      {"name": "Greatsword", "bonus": 16, "damage": "2d6+9", "crit": "19-20/x2"}
    ],
    "full": [
      {"name": "Greatsword", "bonus": [16, 11], "damage": "2d6+9", "crit": "19-20/x2"},
      {"name": "Gore", "bonus": 10, "damage": "1d8+3"}
    ]
  },
  "special_attacks": [
    {
      "name": "Breath Weapon",
      "description": "30-ft. cone of fire, 6d8 damage, Reflex DC 20 half, usable every 1d4 rounds."
    }
  ],
  "special_qualities": [
    "Darkvision 60 ft.", "Low-light vision",
    "Immunity to fire, paralysis, and sleep",
    "Spell resistance 19"
  ],
  "saves": {"fort": 12, "ref": 7, "will": 9},
  "ability_scores": {
    "str": 23, "dex": 10, "con": 21, "int": 10, "wis": 14, "cha": 10
  },
  "skills": {
    "Intimidate": 13, "Listen": 15, "Spot": 15, "Survival": 15
  },
  "feats": ["Cleave", "Great Cleave", "Power Attack",
            "Weapon Focus (greatsword)", "Multiattack"],
  "environment": "Volcanic plains and lava fields",
  "treasure": "Standard",
  "alignment": "Chaotic Neutral",
  "source_book": "Draconomicon",
  "is_expanded": true,
  "flavour_text": "The Ember-Mane Taurian does not charge — it arrives.",
  "expanded_metadata": {
    "is_expanded": true,
    "source_book": "Draconomicon",
    "translated": true,
    "source_archetype": "dragon"
  }
}
```

**Observation:** The combat balance is mathematically identical to the source
stat block. The creature name, appearance, lore, and flavour text are 100 %
original. No WotC text was reproduced.

---

## 5. Quality Checklist Before Committing Any Entry

- [ ] No WotC Product Identity name appears in any field.
- [ ] No flavour text or lore is paraphrased from a WotC publication.
- [ ] All numerical stats match the source stat block exactly.
- [ ] `"translated": true` and `"source_archetype"` are set in `expanded_metadata`
      for any translated entry.
- [ ] Original name passes a basic phonetic-distance check against the PI name.
- [ ] Entry validates against `data/expanded/schema_expanded_v1.json`.
- [ ] No name collision with `data/srd_3.5/` or previously committed expanded files.
