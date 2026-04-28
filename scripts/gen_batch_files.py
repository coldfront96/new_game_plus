import json, os

OUT = "/home/runner/work/new_game_plus/new_game_plus/data/srd_3.5/monsters"

# ─────────────────────────────────────────────────────────────
# CONSTRUCTS
# ─────────────────────────────────────────────────────────────
constructs = [
  {
    "name": "Animated Object, Tiny",
    "cr": 1, "size": "Tiny", "type": "Construct", "subtype": None,
    "hit_dice": "1d10", "hp_avg": 5, "initiative": 2,
    "speed": {"land": 40},
    "armor_class": {"total": 14, "touch": 14, "flat_footed": 12,
                    "components": "+2 Dex, +2 size"},
    "base_attack": 0, "grapple": -8,
    "attacks": [{"name": "Slam", "attack_bonus": "+2", "damage": "1d3", "damage_type": "Bludgeoning"}],
    "special_attacks": [],
    "special_qualities": ["Darkvision 60 ft.", "Low-Light Vision", "Construct Traits", "Hardness 5"],
    "saves": {"fort": 0, "ref": 2, "will": -5},
    "abilities": {"str": 6, "dex": 14, "con": None, "int": None, "wis": 1, "cha": 1},
    "skills": {}, "feats": [], "alignment": "Always Neutral",
    "advancement": "None (created by magic, varies by size)",
    "dr": None, "sr": None, "regen": None, "fast_heal": None,
    "elemental_weaknesses": [], "alignment_weaknesses": [], "passive_effects": [],
    "population_base": 0, "allowed_biomes": ["Any_Ruin"], "primary_biome": "Any_Ruin",
    "ecology_notes": "Tiny animated objects serve as minor guardians or servants, brought to life by Animate Objects. Their small size and hardness make them difficult to destroy outright."
  },
  {
    "name": "Animated Object, Small",
    "cr": 2, "size": "Small", "type": "Construct", "subtype": None,
    "hit_dice": "2d10", "hp_avg": 11, "initiative": 1,
    "speed": {"land": 40},
    "armor_class": {"total": 14, "touch": 12, "flat_footed": 13,
                    "components": "+1 Dex, +1 size, +2 natural"},
    "base_attack": 1, "grapple": -3,
    "attacks": [{"name": "Slam", "attack_bonus": "+1", "damage": "1d4+1", "damage_type": "Bludgeoning"}],
    "special_attacks": [],
    "special_qualities": ["Darkvision 60 ft.", "Low-Light Vision", "Construct Traits", "Hardness 5"],
    "saves": {"fort": 0, "ref": 1, "will": -5},
    "abilities": {"str": 12, "dex": 12, "con": None, "int": None, "wis": 1, "cha": 1},
    "skills": {}, "feats": [], "alignment": "Always Neutral",
    "advancement": "None (created by magic, varies by size)",
    "dr": None, "sr": None, "regen": None, "fast_heal": None,
    "elemental_weaknesses": [], "alignment_weaknesses": [], "passive_effects": [],
    "population_base": 0, "allowed_biomes": ["Any_Ruin"], "primary_biome": "Any_Ruin",
    "ecology_notes": "Small animated objects are common magical sentinels in ancient vaults and wizard towers, activated to defend against intruders."
  },
  {
    "name": "Animated Object, Medium",
    "cr": 3, "size": "Medium", "type": "Construct", "subtype": None,
    "hit_dice": "4d10", "hp_avg": 22, "initiative": 0,
    "speed": {"land": 30},
    "armor_class": {"total": 14, "touch": 10, "flat_footed": 14,
                    "components": "+4 natural"},
    "base_attack": 3, "grapple": 4,
    "attacks": [{"name": "Slam", "attack_bonus": "+4", "damage": "1d6+2", "damage_type": "Bludgeoning"}],
    "special_attacks": [],
    "special_qualities": ["Darkvision 60 ft.", "Low-Light Vision", "Construct Traits", "Hardness 5"],
    "saves": {"fort": 1, "ref": 1, "will": -4},
    "abilities": {"str": 14, "dex": 10, "con": None, "int": None, "wis": 1, "cha": 1},
    "skills": {}, "feats": [], "alignment": "Always Neutral",
    "advancement": "None (created by magic, varies by size)",
    "dr": None, "sr": None, "regen": None, "fast_heal": None,
    "elemental_weaknesses": [], "alignment_weaknesses": [], "passive_effects": [],
    "population_base": 0, "allowed_biomes": ["Any_Ruin"], "primary_biome": "Any_Ruin",
    "ecology_notes": "Medium animated objects are versatile guardian constructs, often taking the form of furniture, statues, or tools in ruin complexes."
  },
  {
    "name": "Animated Object, Large",
    "cr": 5, "size": "Large", "type": "Construct", "subtype": None,
    "hit_dice": "8d10", "hp_avg": 44, "initiative": -1,
    "speed": {"land": 20},
    "armor_class": {"total": 13, "touch": 8, "flat_footed": 13,
                    "components": "+5 natural, -1 size, -1 Dex"},
    "base_attack": 6, "grapple": 14,
    "attacks": [
      {"name": "Slam", "attack_bonus": "+9", "damage": "1d8+7", "damage_type": "Bludgeoning"},
      {"name": "Slam", "attack_bonus": "+9", "damage": "1d8+7", "damage_type": "Bludgeoning"}
    ],
    "special_attacks": [],
    "special_qualities": ["Darkvision 60 ft.", "Low-Light Vision", "Construct Traits", "Hardness 5"],
    "saves": {"fort": 2, "ref": 1, "will": -3},
    "abilities": {"str": 24, "dex": 8, "con": None, "int": None, "wis": 1, "cha": 1},
    "skills": {}, "feats": [], "alignment": "Always Neutral",
    "advancement": "None (created by magic, varies by size)",
    "dr": None, "sr": None, "regen": None, "fast_heal": None,
    "elemental_weaknesses": [], "alignment_weaknesses": [], "passive_effects": [],
    "population_base": 0, "allowed_biomes": ["Any_Ruin"], "primary_biome": "Any_Ruin",
    "ecology_notes": "Large animated objects guard the halls of mighty spellcasters, their bulk and dual slam attacks making them formidable defenders of arcane vaults."
  },
  {
    "name": "Animated Object, Huge",
    "cr": 7, "size": "Huge", "type": "Construct", "subtype": None,
    "hit_dice": "16d10", "hp_avg": 88, "initiative": -2,
    "speed": {"land": 20},
    "armor_class": {"total": 11, "touch": 6, "flat_footed": 11,
                    "components": "+7 natural, -2 size, -2 Dex"},
    "base_attack": 12, "grapple": 26,
    "attacks": [
      {"name": "Slam", "attack_bonus": "+17", "damage": "2d6+11", "damage_type": "Bludgeoning"},
      {"name": "Slam", "attack_bonus": "+17", "damage": "2d6+11", "damage_type": "Bludgeoning"}
    ],
    "special_attacks": [],
    "special_qualities": ["Darkvision 60 ft.", "Low-Light Vision", "Construct Traits", "Hardness 5"],
    "saves": {"fort": 5, "ref": 3, "will": -2},
    "abilities": {"str": 32, "dex": 6, "con": None, "int": None, "wis": 1, "cha": 1},
    "skills": {}, "feats": [], "alignment": "Always Neutral",
    "advancement": "None (created by magic, varies by size)",
    "dr": None, "sr": None, "regen": None, "fast_heal": None,
    "elemental_weaknesses": [], "alignment_weaknesses": [], "passive_effects": [],
    "population_base": 0, "allowed_biomes": ["Any_Ruin"], "primary_biome": "Any_Ruin",
    "ecology_notes": "Huge animated objects are colossal magical sentinels capable of devastating whole groups of adventurers. Only powerful casters can create and control them."
  },
  {
    "name": "Animated Object, Gargantuan",
    "cr": 10, "size": "Gargantuan", "type": "Construct", "subtype": None,
    "hit_dice": "24d10", "hp_avg": 132, "initiative": -2,
    "speed": {"land": 20},
    "armor_class": {"total": 8, "touch": 4, "flat_footed": 8,
                    "components": "+8 natural, -4 size, -2 Dex"},
    "base_attack": 18, "grapple": 37,
    "attacks": [
      {"name": "Slam", "attack_bonus": "+26", "damage": "2d8+15", "damage_type": "Bludgeoning"},
      {"name": "Slam", "attack_bonus": "+26", "damage": "2d8+15", "damage_type": "Bludgeoning"}
    ],
    "special_attacks": [],
    "special_qualities": ["Darkvision 60 ft.", "Low-Light Vision", "Construct Traits", "Hardness 5"],
    "saves": {"fort": 8, "ref": 6, "will": 0},
    "abilities": {"str": 40, "dex": 6, "con": None, "int": None, "wis": 1, "cha": 1},
    "skills": {}, "feats": [], "alignment": "Always Neutral",
    "advancement": "None (created by magic, varies by size)",
    "dr": None, "sr": None, "regen": None, "fast_heal": None,
    "elemental_weaknesses": [], "alignment_weaknesses": [], "passive_effects": [],
    "population_base": 0, "allowed_biomes": ["Any_Ruin"], "primary_biome": "Any_Ruin",
    "ecology_notes": "Gargantuan animated objects are among the most powerful magical constructs, typically animating massive statues or siege equipment in ancient strongholds."
  },
  {
    "name": "Animated Object, Colossal",
    "cr": 14, "size": "Colossal", "type": "Construct", "subtype": None,
    "hit_dice": "32d10", "hp_avg": 176, "initiative": -2,
    "speed": {"land": 20},
    "armor_class": {"total": 3, "touch": 0, "flat_footed": 3,
                    "components": "+9 natural, -8 size, -2 Dex"},
    "base_attack": 24, "grapple": 49,
    "attacks": [
      {"name": "Slam", "attack_bonus": "+34", "damage": "4d6+19", "damage_type": "Bludgeoning"},
      {"name": "Slam", "attack_bonus": "+34", "damage": "4d6+19", "damage_type": "Bludgeoning"}
    ],
    "special_attacks": [],
    "special_qualities": ["Darkvision 60 ft.", "Low-Light Vision", "Construct Traits", "Hardness 5"],
    "saves": {"fort": 10, "ref": 8, "will": 2},
    "abilities": {"str": 48, "dex": 6, "con": None, "int": None, "wis": 1, "cha": 1},
    "skills": {}, "feats": [], "alignment": "Always Neutral",
    "advancement": "None (created by magic, varies by size)",
    "dr": None, "sr": None, "regen": None, "fast_heal": None,
    "elemental_weaknesses": [], "alignment_weaknesses": [], "passive_effects": [],
    "population_base": 0, "allowed_biomes": ["Any_Ruin"], "primary_biome": "Any_Ruin",
    "ecology_notes": "Colossal animated objects are legendary magical constructs of world-shaking power. Their creation requires epic-level magic and is incredibly rare."
  },
  {
    "name": "Golem, Clay",
    "cr": 10, "size": "Large", "type": "Construct", "subtype": None,
    "hit_dice": "11d10+30", "hp_avg": 90, "initiative": -1,
    "speed": {"land": 20},
    "armor_class": {"total": 22, "touch": 8, "flat_footed": 22,
                    "components": "+14 natural, -1 size, -1 Dex"},
    "base_attack": 8, "grapple": 20,
    "attacks": [
      {"name": "Slam", "attack_bonus": "+15", "damage": "2d10+9", "damage_type": "Bludgeoning"},
      {"name": "Slam", "attack_bonus": "+15", "damage": "2d10+9", "damage_type": "Bludgeoning"}
    ],
    "special_attacks": [
      "Berserk (uncontrolled rampage when damaged; DC 19 Will to control)",
      "Cursed Wound (wounds cannot heal naturally; DC 26 Remove Curse to lift)"
    ],
    "special_qualities": [
      "Construct Traits",
      "Darkvision 60 ft.",
      "DR 10/Adamantine",
      "Magic Immunity (immune to all spells except as noted)",
      "Immunity to Normal Healing (only Mending or spells targeted at constructs heal it)"
    ],
    "saves": {"fort": 3, "ref": 2, "will": 3},
    "abilities": {"str": 29, "dex": 9, "con": None, "int": None, "wis": 11, "cha": 1},
    "skills": {}, "feats": ["Power Attack", "Cleave"],
    "alignment": "Always Neutral",
    "advancement": "None",
    "dr": "10/Adamantine", "sr": None, "regen": None, "fast_heal": None,
    "elemental_weaknesses": [], "alignment_weaknesses": [], "passive_effects": [],
    "population_base": 0, "allowed_biomes": ["Any_Ruin"], "primary_biome": "Any_Ruin",
    "ecology_notes": "Clay golems are powerful guardian constructs crafted from sacred clay. Their cursed wound ability makes them particularly feared, as wounds from their slams resist all natural healing."
  },
  {
    "name": "Golem, Flesh",
    "cr": 7, "size": "Large", "type": "Construct", "subtype": None,
    "hit_dice": "9d10+20", "hp_avg": 69, "initiative": -1,
    "speed": {"land": 30},
    "armor_class": {"total": 15, "touch": 8, "flat_footed": 15,
                    "components": "+7 natural, -1 size, -1 Dex"},
    "base_attack": 6, "grapple": 15,
    "attacks": [
      {"name": "Slam", "attack_bonus": "+10", "damage": "2d8+5", "damage_type": "Bludgeoning"},
      {"name": "Slam", "attack_bonus": "+10", "damage": "2d8+5", "damage_type": "Bludgeoning"}
    ],
    "special_attacks": [
      "Berserk (uncontrolled rampage when damaged; DC 17 Will to control)"
    ],
    "special_qualities": [
      "Construct Traits",
      "Darkvision 60 ft.",
      "DR 5/Adamantine",
      "Immunity to Magic (fire slows it, cold negates berserk temporarily)",
      "Low-Light Vision"
    ],
    "saves": {"fort": 3, "ref": 2, "will": 2},
    "abilities": {"str": 21, "dex": 9, "con": None, "int": None, "wis": 11, "cha": 1},
    "skills": {}, "feats": ["Power Attack", "Cleave", "Improved Sunder"],
    "alignment": "Always Neutral",
    "advancement": "None",
    "dr": "5/Adamantine", "sr": None, "regen": None, "fast_heal": None,
    "elemental_weaknesses": [], "alignment_weaknesses": [], "passive_effects": [],
    "population_base": 0, "allowed_biomes": ["Any_Ruin"], "primary_biome": "Any_Ruin",
    "ecology_notes": "Flesh golems are grotesque constructs assembled from corpse parts, animated by powerful magic. They are susceptible to fire and electricity affects their behavior."
  },
  {
    "name": "Golem, Iron",
    "cr": 13, "size": "Large", "type": "Construct", "subtype": None,
    "hit_dice": "18d10+30", "hp_avg": 129, "initiative": -1,
    "speed": {"land": 20},
    "armor_class": {"total": 30, "touch": 9, "flat_footed": 30,
                    "components": "+22 natural, -1 size, -1 Dex"},
    "base_attack": 13, "grapple": 25,
    "attacks": [
      {"name": "Slam", "attack_bonus": "+20", "damage": "2d10+11", "damage_type": "Bludgeoning"},
      {"name": "Slam", "attack_bonus": "+20", "damage": "2d10+11", "damage_type": "Bludgeoning"}
    ],
    "special_attacks": [
      "Breath Weapon (10-ft. radius poison gas cloud, DC 19 Fort, 1d4 Con + 1d4 Con secondary; usable every 1d4+1 rounds)"
    ],
    "special_qualities": [
      "Construct Traits",
      "Darkvision 60 ft.",
      "DR 15/Adamantine",
      "Immunity to Magic (rusting attacks slow it; electricity heals it)",
      "Low-Light Vision"
    ],
    "saves": {"fort": 6, "ref": 5, "will": 6},
    "abilities": {"str": 33, "dex": 9, "con": None, "int": None, "wis": 11, "cha": 1},
    "skills": {}, "feats": ["Power Attack", "Cleave", "Great Cleave", "Improved Sunder", "Improved Bull Rush"],
    "alignment": "Always Neutral",
    "advancement": "None",
    "dr": "15/Adamantine", "sr": None, "regen": None, "fast_heal": None,
    "elemental_weaknesses": [], "alignment_weaknesses": [], "passive_effects": [],
    "population_base": 0, "allowed_biomes": ["Any_Ruin"], "primary_biome": "Any_Ruin",
    "ecology_notes": "Iron golems are nearly indestructible constructs forged from pure iron. Only adamantine weapons can harm them, and their poison breath weapon makes them deadly even at range."
  },
  {
    "name": "Golem, Stone",
    "cr": 11, "size": "Large", "type": "Construct", "subtype": None,
    "hit_dice": "14d10+30", "hp_avg": 107, "initiative": -1,
    "speed": {"land": 20},
    "armor_class": {"total": 26, "touch": 8, "flat_footed": 26,
                    "components": "+18 natural, -1 size, -1 Dex"},
    "base_attack": 10, "grapple": 22,
    "attacks": [
      {"name": "Slam", "attack_bonus": "+17", "damage": "2d10+9", "damage_type": "Bludgeoning"},
      {"name": "Slam", "attack_bonus": "+17", "damage": "2d10+9", "damage_type": "Bludgeoning"}
    ],
    "special_attacks": [
      "Slow (DC 17 Will, target is slowed for 2d6 rounds; area 10-ft. radius)"
    ],
    "special_qualities": [
      "Construct Traits",
      "Darkvision 60 ft.",
      "DR 10/Adamantine",
      "Immunity to Magic (haste counters slow; acid deals normal damage; other spells require DC 19 Fort or be affected)",
      "Low-Light Vision"
    ],
    "saves": {"fort": 4, "ref": 3, "will": 4},
    "abilities": {"str": 29, "dex": 9, "con": None, "int": None, "wis": 11, "cha": 1},
    "skills": {}, "feats": ["Power Attack", "Cleave", "Great Cleave", "Improved Sunder"],
    "alignment": "Always Neutral",
    "advancement": "None",
    "dr": "10/Adamantine", "sr": None, "regen": None, "fast_heal": None,
    "elemental_weaknesses": [], "alignment_weaknesses": [], "passive_effects": [],
    "population_base": 0, "allowed_biomes": ["Any_Ruin"], "primary_biome": "Any_Ruin",
    "ecology_notes": "Stone golems are enduring magical constructs, carved from solid rock and animated for permanent guardianship. Their slow ability can quickly turn an encounter against unprepared adventurers."
  },
  {
    "name": "Homunculus",
    "cr": 1, "size": "Tiny", "type": "Construct", "subtype": None,
    "hit_dice": "2d10", "hp_avg": 11, "initiative": 2,
    "speed": {"land": 20, "fly": 50},
    "armor_class": {"total": 14, "touch": 14, "flat_footed": 12,
                    "components": "+2 Dex, +2 size"},
    "base_attack": 1, "grapple": -7,
    "attacks": [
      {"name": "Bite", "attack_bonus": "+2", "damage": "1d4-1 plus poison", "damage_type": "Piercing"}
    ],
    "special_attacks": [
      "Poison (DC 13 Fort, 1d4 Str primary and secondary)"
    ],
    "special_qualities": [
      "Construct Traits",
      "Darkvision 60 ft.",
      "Empathic Link with master (1 mile range)",
      "Low-Light Vision"
    ],
    "saves": {"fort": 0, "ref": 2, "will": 1},
    "abilities": {"str": 8, "dex": 15, "con": None, "int": 10, "wis": 12, "cha": 7},
    "skills": {"Hide": 14, "Listen": 4, "Spot": 4},
    "feats": ["Lightning Reflexes"],
    "alignment": "Always Neutral",
    "advancement": "None",
    "dr": None, "sr": None, "regen": None, "fast_heal": None,
    "elemental_weaknesses": [], "alignment_weaknesses": [], "passive_effects": [],
    "population_base": 0, "allowed_biomes": ["Any_Ruin"], "primary_biome": "Any_Ruin",
    "ecology_notes": "A homunculus is a tiny familiar-like construct created by a wizard from his own blood. It shares an empathic link with its creator and serves as a loyal spy and scout."
  },
  {
    "name": "Shield Guardian",
    "cr": 8, "size": "Large", "type": "Construct", "subtype": None,
    "hit_dice": "15d10+20", "hp_avg": 102, "initiative": 0,
    "speed": {"land": 30},
    "armor_class": {"total": 24, "touch": 9, "flat_footed": 24,
                    "components": "+15 natural, -1 size"},
    "base_attack": 11, "grapple": 20,
    "attacks": [
      {"name": "Slam", "attack_bonus": "+15", "damage": "1d6+5", "damage_type": "Bludgeoning"},
      {"name": "Slam", "attack_bonus": "+10", "damage": "1d6+5", "damage_type": "Bludgeoning"}
    ],
    "special_attacks": [
      "Find Master (telepathic bond; can locate master anywhere on same plane)",
      "Guard (first 2d6 damage dealt to master per round is redirected to guardian)"
    ],
    "special_qualities": [
      "Construct Traits",
      "Darkvision 60 ft.",
      "Fast Healing 2",
      "Shield Other (50% damage redirect from master to guardian)",
      "Spell Storing (can store one spell of 4th level or lower cast into it)"
    ],
    "saves": {"fort": 5, "ref": 5, "will": 5},
    "abilities": {"str": 21, "dex": 10, "con": None, "int": None, "wis": 10, "cha": 1},
    "skills": {}, "feats": ["Power Attack", "Improved Bull Rush", "Improved Sunder"],
    "alignment": "Always Neutral",
    "advancement": "16-21 HD (Large); 22-45 HD (Huge)",
    "dr": None, "sr": None, "regen": None, "fast_heal": 2,
    "elemental_weaknesses": [], "alignment_weaknesses": [], "passive_effects": [],
    "population_base": 0, "allowed_biomes": ["Any_Ruin"], "primary_biome": "Any_Ruin",
    "ecology_notes": "Shield guardians are powerful constructs bound to a magical amulet and programmed to protect their master. They intercept attacks and heal rapidly, making them prized bodyguards for wealthy spellcasters."
  }
]

# ─────────────────────────────────────────────────────────────
# ELEMENTALS
# ─────────────────────────────────────────────────────────────
def el(name, cr, size, subtype, hd, hp, init, spd, ac_t, ac_touch, ac_ff, ac_comp,
       bab, grapple, attacks, sa, sq, fort, ref, will,
       str_, dex, con, int_, wis, cha, feats, elem_weak, biomes, primary, pop,
       dr=None, sr=None, fast_heal=None, adv=None, skills=None, notes=""):
    return {
        "name": name, "cr": cr, "size": size, "type": "Elemental", "subtype": subtype,
        "hit_dice": hd, "hp_avg": hp, "initiative": init, "speed": spd,
        "armor_class": {"total": ac_t, "touch": ac_touch, "flat_footed": ac_ff, "components": ac_comp},
        "base_attack": bab, "grapple": grapple, "attacks": attacks,
        "special_attacks": sa, "special_qualities": sq,
        "saves": {"fort": fort, "ref": ref, "will": will},
        "abilities": {"str": str_, "dex": dex, "con": con, "int": int_, "wis": wis, "cha": cha},
        "skills": skills or {}, "feats": feats, "alignment": "Always Neutral",
        "advancement": adv, "dr": dr, "sr": sr, "regen": None, "fast_heal": fast_heal,
        "elemental_weaknesses": elem_weak, "alignment_weaknesses": [], "passive_effects": [],
        "population_base": pop, "allowed_biomes": biomes, "primary_biome": primary,
        "ecology_notes": notes
    }

AIR_SQ = ["Air Mastery (+1 attack and damage when airborne foe is also airborne)", "Elemental Traits", "Darkvision 60 ft."]
EARTH_SQ = ["Earth Mastery (+1 attack and damage when both combatants on ground)", "Elemental Traits", "Darkvision 60 ft."]
FIRE_SQ = ["Fire Mastery (as air mastery but near open flame)", "Elemental Traits", "Darkvision 60 ft.", "Immunity to Fire", "Vulnerability to Cold"]
WATER_SQ = ["Water Mastery (+1 attack and damage when both in water)", "Elemental Traits", "Darkvision 60 ft.", "Immunity to Cold", "Drench (extinguish non-magical flames on contact)"]

AIR_BIOMES = ["Any"]
EARTH_BIOMES = ["Mountain", "Underground"]
FIRE_BIOMES = ["Warm_Desert", "Warm_Plain"]
WATER_BIOMES = ["Temperate_Aquatic", "Warm_Aquatic", "Cold_Aquatic"]

elementals = [
  # ---- AIR ----
  el("Small Air Elemental", 1, "Small", "Air", "2d8", 9, 7,
     {"fly": 100},
     17, 14, 14, "+3 Dex, +3 natural, +1 size",
     1, -3,
     [{"name": "Slam", "attack_bonus": "+4", "damage": "1d4", "damage_type": "Bludgeoning"}],
     ["Whirlwind (DC 11 Ref, 5-ft. tall, 1d4 damage, lasts 1d4+1 rounds)"],
     AIR_SQ,
     0, 5, 0, 10, 17, 10, 4, 11, 11,
     ["Flyby Attack", "Improved Initiative"], [], AIR_BIOMES, "Any", 40,
     notes="Small air elementals drift on currents of wind, lashing out with blasts of compressed air. Their whirlwind form can engulf and toss smaller creatures."),

  el("Medium Air Elemental", 3, "Medium", "Air", "4d8", 18, 9,
     {"fly": 100},
     17, 15, 12, "+5 Dex, +2 natural",
     3, 3,
     [{"name": "Slam", "attack_bonus": "+8", "damage": "1d6+2", "damage_type": "Bludgeoning"}],
     ["Whirlwind (DC 13 Ref, 5-10 ft. tall, 2d6 damage)"],
     AIR_SQ,
     1, 9, 1, 14, 21, 10, 4, 11, 11,
     ["Dodge", "Flyby Attack", "Improved Initiative", "Weapon Finesse"], [], AIR_BIOMES, "Any", 30,
     notes="Medium air elementals are mobile and difficult to hit, darting through combat and using their whirlwind to scatter opponents."),

  el("Large Air Elemental", 5, "Large", "Air", "8d8", 36, 11,
     {"fly": 100},
     20, 16, 13, "+6 Dex, +5 natural, -1 size",
     6, 11,
     [{"name": "Slam", "attack_bonus": "+12/+7", "damage": "1d8+4", "damage_type": "Bludgeoning"}],
     ["Whirlwind (DC 16 Ref, 10-15 ft. tall, 2d8 damage)"],
     AIR_SQ,
     2, 12, 2, 18, 23, 10, 6, 11, 11,
     ["Dodge", "Flyby Attack", "Improved Initiative", "Weapon Finesse"], [], AIR_BIOMES, "Any", 20,
     notes="Large air elementals command significant volumes of air, their whirlwinds capable of engulfing Medium creatures and flinging them aside."),

  el("Huge Air Elemental", 7, "Huge", "Air", "16d8", 72, 13,
     {"fly": 100},
     21, 16, 12, "+6 Dex, +7 natural, -2 size",
     12, 22,
     [{"name": "Slam", "attack_bonus": "+18/+13", "damage": "2d8+6", "damage_type": "Bludgeoning"}],
     ["Whirlwind (DC 20 Ref, 10-20 ft. tall, 2d8 damage)"],
     AIR_SQ,
     5, 16, 5, 22, 23, 10, 6, 11, 11,
     ["Combat Reflexes", "Dodge", "Flyby Attack", "Improved Initiative", "Weapon Finesse"], [], AIR_BIOMES, "Any", 15,
     notes="Huge air elementals are living cyclones, their passage heralded by howling winds and debris. Their whirlwinds can menace entire adventuring parties."),

  el("Greater Air Elemental", 9, "Huge", "Air", "21d8", 94, 14,
     {"fly": 100},
     27, 17, 18, "+7 Dex, +12 natural, -2 size",
     15, 27,
     [{"name": "Slam", "attack_bonus": "+22/+17/+12", "damage": "2d8+8", "damage_type": "Bludgeoning"}],
     ["Whirlwind (DC 24 Ref, 10-20 ft. tall, 2d8 damage)"],
     AIR_SQ,
     7, 19, 7, 26, 25, 10, 6, 11, 11,
     ["Combat Reflexes", "Dodge", "Flyby Attack", "Improved Initiative", "Iron Will", "Weapon Finesse"], [], AIR_BIOMES, "Any", 10,
     notes="Greater air elementals are ancient tempestuous entities, manifesting as towering pillars of raging wind capable of tearing apart stone structures."),

  el("Elder Air Elemental", 11, "Huge", "Air", "24d8", 108, 15,
     {"fly": 100},
     31, 18, 23, "+8 Dex, +15 natural, -2 size",
     18, 31,
     [{"name": "Slam", "attack_bonus": "+26/+21/+16/+11", "damage": "2d8+10", "damage_type": "Bludgeoning"}],
     ["Whirlwind (DC 27 Ref, 10-20 ft. tall, 2d8 damage)"],
     AIR_SQ,
     8, 22, 8, 30, 27, 10, 8, 11, 11,
     ["Alertness", "Combat Reflexes", "Dodge", "Flyby Attack", "Improved Initiative", "Iron Will", "Weapon Finesse"], [], AIR_BIOMES, "Any", 5,
     notes="Elder air elementals are the oldest and most powerful of their kind, living hurricanes whose very presence distorts weather patterns across hundreds of miles."),

  # ---- EARTH ----
  el("Small Earth Elemental", 1, "Small", "Earth", "2d8+2", 11, -1,
     {"land": 20, "burrow": 20},
     17, 10, 17, "-1 Dex, +7 natural, +1 size",
     1, -1,
     [{"name": "Slam", "attack_bonus": "+3", "damage": "1d6+4", "damage_type": "Bludgeoning"}],
     ["Push (on hit, Str check DC 13 or be pushed 5 ft.)"],
     EARTH_SQ,
     4, -1, 0, 17, 8, 13, 4, 11, 11,
     ["Power Attack"], [], EARTH_BIOMES, "Mountain", 40,
     notes="Small earth elementals burst from rocky ground to attack, using their surprising strength to shove opponents aside before retreating underground."),

  el("Medium Earth Elemental", 3, "Medium", "Earth", "4d8+12", 30, -1,
     {"land": 20, "burrow": 20},
     17, 9, 17, "-1 Dex, +8 natural",
     3, 8,
     [{"name": "Slam", "attack_bonus": "+8", "damage": "1d8+7", "damage_type": "Bludgeoning"}],
     ["Push (Str check DC 16 or be pushed 5 ft.)"],
     EARTH_SQ,
     7, 0, 1, 21, 8, 17, 4, 11, 11,
     ["Cleave", "Power Attack"], [], EARTH_BIOMES, "Mountain", 30,
     notes="Medium earth elementals are patient hunters, lying dormant within stone until prey walks near. Their great strength allows them to cleave through multiple foes."),

  el("Large Earth Elemental", 5, "Large", "Earth", "8d8+32", 68, -1,
     {"land": 20, "burrow": 20},
     18, 8, 18, "-1 Dex, +10 natural, -1 size",
     6, 15,
     [{"name": "Slam", "attack_bonus": "+11/+6", "damage": "2d8+8", "damage_type": "Bludgeoning"}],
     ["Push (Str check DC 19 or be pushed 5 ft.)"],
     EARTH_SQ,
     10, 1, 2, 25, 8, 19, 6, 11, 11,
     ["Cleave", "Great Cleave", "Power Attack"], [], EARTH_BIOMES, "Mountain", 20,
     notes="Large earth elementals can move through solid rock as easily as water, making them formidable ambush predators in cavern environments."),

  el("Huge Earth Elemental", 7, "Huge", "Earth", "16d8+80", 152, -1,
     {"land": 20, "burrow": 20},
     18, 7, 18, "-1 Dex, +11 natural, -2 size",
     12, 25,
     [{"name": "Slam", "attack_bonus": "+20/+15", "damage": "2d10+11", "damage_type": "Bludgeoning"}],
     ["Push (Str check DC 25 or be pushed 10 ft.)"],
     EARTH_SQ,
     15, 4, 5, 33, 8, 21, 8, 11, 11,
     ["Cleave", "Great Cleave", "Improved Sunder", "Power Attack"], [], EARTH_BIOMES, "Mountain", 15,
     notes="Huge earth elementals reshape the battlefield, smashing through walls and floors. Their push ability can send even armored warriors flying."),

  el("Greater Earth Elemental", 9, "Huge", "Earth", "21d8+105", 199, -1,
     {"land": 20, "burrow": 20},
     23, 7, 23, "-1 Dex, +16 natural, -2 size",
     15, 31,
     [{"name": "Slam", "attack_bonus": "+26/+21/+16", "damage": "2d10+13", "damage_type": "Bludgeoning"}],
     ["Push (Str check DC 29 or be pushed 10 ft.)"],
     EARTH_SQ,
     18, 6, 7, 37, 8, 21, 8, 11, 11,
     ["Cleave", "Great Cleave", "Improved Bull Rush", "Improved Sunder", "Power Attack"], [], EARTH_BIOMES, "Mountain", 10,
     notes="Greater earth elementals are ancient forces of geological power, able to trigger minor earthquakes with their movement and topple stone fortifications."),

  el("Elder Earth Elemental", 11, "Huge", "Earth", "24d8+120", 228, -1,
     {"land": 20, "burrow": 20},
     26, 7, 26, "-1 Dex, +19 natural, -2 size",
     18, 35,
     [{"name": "Slam", "attack_bonus": "+30/+25/+20/+15", "damage": "2d10+15", "damage_type": "Bludgeoning"}],
     ["Push (Str check DC 32 or be pushed 10 ft.)"],
     EARTH_SQ,
     20, 7, 8, 41, 8, 21, 10, 11, 11,
     ["Cleave", "Great Cleave", "Improved Bull Rush", "Improved Sunder", "Iron Will", "Power Attack"], [], EARTH_BIOMES, "Mountain", 5,
     notes="Elder earth elementals are mountains given life, primordial entities of immeasurable strength whose movements cause avalanches and reshape terrain."),

  # ---- FIRE ----
  el("Small Fire Elemental", 1, "Small", "Fire", "2d8", 9, 5,
     {"land": 50},
     15, 14, 12, "+3 Dex, +1 natural, +1 size",
     1, -3,
     [{"name": "Slam", "attack_bonus": "+4", "damage": "1d4 plus 1d4 fire", "damage_type": "Bludgeoning + Fire"}],
     ["Burn (DC 11 Ref or catch fire, taking 1d4 fire damage/round until extinguished)"],
     FIRE_SQ,
     0, 5, 0, 10, 17, 10, 4, 11, 11,
     ["Improved Initiative", "Weapon Finesse"], ["Cold"], FIRE_BIOMES, "Warm_Desert", 40,
     notes="Small fire elementals are sparks of living flame, dancing through combustible environments and setting fires wherever they go. They avoid cold and water."),

  el("Medium Fire Elemental", 3, "Medium", "Fire", "4d8", 18, 9,
     {"land": 50},
     16, 15, 11, "+5 Dex, +1 natural",
     3, 3,
     [{"name": "Slam", "attack_bonus": "+8", "damage": "1d6+1 plus 1d6 fire", "damage_type": "Bludgeoning + Fire"}],
     ["Burn (DC 13 Ref or catch fire, 1d6 fire damage/round)"],
     FIRE_SQ,
     1, 9, 1, 12, 21, 10, 4, 11, 11,
     ["Dodge", "Improved Initiative", "Mobility", "Weapon Finesse"], ["Cold"], FIRE_BIOMES, "Warm_Desert", 30,
     notes="Medium fire elementals are roving columns of living fire, capable of igniting entire structures in moments. They pursue fleeing prey with relentless speed."),

  el("Large Fire Elemental", 5, "Large", "Fire", "8d8", 36, 11,
     {"land": 50},
     18, 16, 11, "+6 Dex, +3 natural, -1 size",
     6, 11,
     [{"name": "Slam", "attack_bonus": "+12/+7", "damage": "1d8+4 plus 1d8 fire", "damage_type": "Bludgeoning + Fire"}],
     ["Burn (DC 16 Ref or catch fire, 1d8 fire damage/round)"],
     FIRE_SQ,
     2, 12, 2, 18, 23, 10, 6, 11, 11,
     ["Dodge", "Improved Initiative", "Mobility", "Weapon Finesse"], ["Cold"], FIRE_BIOMES, "Warm_Desert", 20,
     notes="Large fire elementals are devastating infernos in living form, capable of reducing entire villages to ash in minutes and melting through iron doors."),

  el("Huge Fire Elemental", 7, "Huge", "Fire", "16d8", 72, 13,
     {"land": 50},
     19, 16, 10, "+6 Dex, +5 natural, -2 size",
     12, 22,
     [{"name": "Slam", "attack_bonus": "+18/+13", "damage": "2d8+6 plus 2d8 fire", "damage_type": "Bludgeoning + Fire"}],
     ["Burn (DC 20 Ref or catch fire, 2d8 fire damage/round)"],
     FIRE_SQ,
     5, 16, 5, 22, 23, 10, 6, 11, 11,
     ["Combat Reflexes", "Dodge", "Improved Initiative", "Mobility", "Weapon Finesse"], ["Cold"], FIRE_BIOMES, "Warm_Desert", 15,
     notes="Huge fire elementals are massive conflagrations with a personality, drawn to destroy and consume. Their passage leaves scorched wastelands in their wake."),

  el("Greater Fire Elemental", 9, "Huge", "Fire", "21d8", 94, 14,
     {"land": 60},
     25, 17, 16, "+7 Dex, +10 natural, -2 size",
     15, 27,
     [{"name": "Slam", "attack_bonus": "+22/+17/+12", "damage": "2d8+8 plus 2d8 fire", "damage_type": "Bludgeoning + Fire"}],
     ["Burn (DC 24 Ref or catch fire, 2d8 fire damage/round)"],
     FIRE_SQ,
     7, 19, 7, 26, 25, 10, 6, 11, 11,
     ["Combat Reflexes", "Dodge", "Improved Initiative", "Iron Will", "Mobility", "Weapon Finesse"], ["Cold"], FIRE_BIOMES, "Warm_Desert", 10,
     notes="Greater fire elementals are ancient pillars of living fire whose temperature exceeds the surface of suns. They leave glass where they walk."),

  el("Elder Fire Elemental", 11, "Huge", "Fire", "24d8", 108, 15,
     {"land": 60},
     29, 18, 21, "+8 Dex, +13 natural, -2 size",
     18, 31,
     [{"name": "Slam", "attack_bonus": "+26/+21/+16/+11", "damage": "2d8+10 plus 2d8 fire", "damage_type": "Bludgeoning + Fire"}],
     ["Burn (DC 27 Ref or catch fire, 2d8 fire damage/round)"],
     FIRE_SQ,
     8, 22, 8, 30, 27, 10, 8, 11, 11,
     ["Alertness", "Combat Reflexes", "Dodge", "Improved Initiative", "Iron Will", "Mobility", "Weapon Finesse"], ["Cold"], FIRE_BIOMES, "Warm_Desert", 5,
     notes="Elder fire elementals are the embodiment of primal flame, entities older than civilization whose very presence can set the sky ablaze."),

  # ---- WATER ----
  el("Small Water Elemental", 1, "Small", "Water", "2d8+2", 11, 0,
     {"land": 20, "swim": 90},
     17, 11, 17, "+5 natural, +1 size",
     1, -1,
     [{"name": "Slam", "attack_bonus": "+4", "damage": "1d6+4", "damage_type": "Bludgeoning"}],
     ["Drench (extinguish non-magical fires on contact)", "Water Mastery (+1 attack and damage when both in water)"],
     WATER_SQ,
     4, 0, 0, 16, 10, 13, 4, 11, 11,
     ["Power Attack"], [], WATER_BIOMES, "Temperate_Aquatic", 40,
     notes="Small water elementals are mobile waves of living water, prowling coastlines and rivers. They douse flames and overwhelm swimmers with their powerful slams."),

  el("Medium Water Elemental", 3, "Medium", "Water", "4d8+12", 30, 1,
     {"land": 20, "swim": 90},
     19, 11, 18, "+1 Dex, +8 natural",
     3, 8,
     [{"name": "Slam", "attack_bonus": "+8", "damage": "1d8+7", "damage_type": "Bludgeoning"}],
     ["Drench", "Water Mastery"],
     WATER_SQ,
     7, 2, 1, 20, 12, 17, 4, 11, 11,
     ["Cleave", "Power Attack"], [], WATER_BIOMES, "Temperate_Aquatic", 30,
     notes="Medium water elementals are aquatic terrors that drag prey beneath the surface. On land they are slower, but their slam attacks remain devastating."),

  el("Large Water Elemental", 5, "Large", "Water", "8d8+32", 68, 2,
     {"land": 20, "swim": 90},
     21, 11, 19, "+2 Dex, +10 natural, -1 size",
     6, 15,
     [{"name": "Slam", "attack_bonus": "+11/+6", "damage": "2d8+8", "damage_type": "Bludgeoning"}],
     ["Drench", "Water Mastery"],
     WATER_SQ,
     10, 4, 2, 26, 14, 19, 6, 11, 11,
     ["Cleave", "Great Cleave", "Power Attack"], [], WATER_BIOMES, "Temperate_Aquatic", 20,
     notes="Large water elementals can overwhelm entire ships, capsizing vessels and drowning crews. They are near-unstoppable in aquatic environments."),

  el("Huge Water Elemental", 7, "Huge", "Water", "16d8+80", 152, 2,
     {"land": 20, "swim": 90},
     22, 10, 20, "+2 Dex, +12 natural, -2 size",
     12, 25,
     [{"name": "Slam", "attack_bonus": "+20/+15", "damage": "2d10+11", "damage_type": "Bludgeoning"}],
     ["Drench", "Water Mastery"],
     WATER_SQ,
     15, 7, 5, 32, 14, 21, 8, 11, 11,
     ["Cleave", "Great Cleave", "Improved Sunder", "Power Attack"], [], WATER_BIOMES, "Temperate_Aquatic", 15,
     notes="Huge water elementals are tsunamis given consciousness, capable of flooding coastal towns and shattering harbor fortifications."),

  el("Greater Water Elemental", 9, "Huge", "Water", "21d8+105", 199, 2,
     {"land": 20, "swim": 90},
     26, 10, 24, "+2 Dex, +16 natural, -2 size",
     15, 31,
     [{"name": "Slam", "attack_bonus": "+26/+21/+16", "damage": "2d10+13", "damage_type": "Bludgeoning"}],
     ["Drench", "Water Mastery"],
     WATER_SQ,
     18, 9, 7, 36, 14, 21, 8, 11, 11,
     ["Cleave", "Great Cleave", "Improved Bull Rush", "Improved Sunder", "Power Attack"], [], WATER_BIOMES, "Temperate_Aquatic", 10,
     notes="Greater water elementals are the spirits of great oceans and deep rivers, their power sufficient to shatter stone seawalls and flood entire valleys."),

  el("Elder Water Elemental", 11, "Huge", "Water", "24d8+120", 228, 2,
     {"land": 20, "swim": 90},
     30, 10, 28, "+2 Dex, +20 natural, -2 size",
     18, 35,
     [{"name": "Slam", "attack_bonus": "+30/+25/+20/+15", "damage": "2d10+15", "damage_type": "Bludgeoning"}],
     ["Drench", "Water Mastery"],
     WATER_SQ,
     20, 10, 8, 40, 14, 21, 10, 11, 11,
     ["Cleave", "Great Cleave", "Improved Bull Rush", "Improved Sunder", "Iron Will", "Power Attack"], [], WATER_BIOMES, "Temperate_Aquatic", 5,
     notes="Elder water elementals are primordial ocean entities that have existed since the seas first formed. Their wrath can raise tidal waves that drown whole coastlines."),

  # ---- MEPHITS ----
  {
    "name": "Mephit, Air",
    "cr": 3, "size": "Small", "type": "Outsider", "subtype": "Air",
    "hit_dice": "3d8", "hp_avg": 13, "initiative": 7,
    "speed": {"land": 30, "fly": 40},
    "armor_class": {"total": 17, "touch": 14, "flat_footed": 14,
                    "components": "+3 Dex, +3 natural, +1 size"},
    "base_attack": 2, "grapple": -2,
    "attacks": [
      {"name": "Claw", "attack_bonus": "+5", "damage": "1d3", "damage_type": "Slashing"},
      {"name": "Claw", "attack_bonus": "+5", "damage": "1d3", "damage_type": "Slashing"}
    ],
    "special_attacks": [
      "Breath Weapon (cone 15 ft., DC 12 Fort, 1d8 choking gust; recharge 1d4 rounds)",
      "Spell-Like Abilities (blur 1/day, wind wall 1/day; CL 6th)"
    ],
    "special_qualities": [
      "Darkvision 60 ft.",
      "DR 5/Magic",
      "Elemental Traits",
      "Fast Healing 2 (in windy conditions or on Elemental Plane of Air)",
      "Summon Mephit (15% chance, 1 mephit of same type)"
    ],
    "saves": {"fort": 3, "ref": 5, "will": 3},
    "abilities": {"str": 10, "dex": 17, "con": 10, "int": 6, "wis": 11, "cha": 15},
    "skills": {"Bluff": 8, "Diplomacy": 2, "Hide": 12, "Listen": 6, "Move Silently": 8, "Spot": 6},
    "feats": ["Improved Initiative", "Toughness"],
    "alignment": "Always Neutral",
    "advancement": "None",
    "dr": "5/Magic", "sr": None, "regen": None, "fast_heal": 2,
    "elemental_weaknesses": [], "alignment_weaknesses": [], "passive_effects": [],
    "population_base": 10, "allowed_biomes": ["Any"], "primary_biome": "Any",
    "ecology_notes": "Air mephits are mischievous minor elementals that delight in pranks and chaos. They serve more powerful air creatures as scouts and messengers."
  },
  {
    "name": "Mephit, Dust",
    "cr": 3, "size": "Small", "type": "Outsider", "subtype": "Air",
    "hit_dice": "3d8", "hp_avg": 13, "initiative": 7,
    "speed": {"land": 30, "fly": 40},
    "armor_class": {"total": 17, "touch": 14, "flat_footed": 14,
                    "components": "+3 Dex, +3 natural, +1 size"},
    "base_attack": 2, "grapple": -2,
    "attacks": [
      {"name": "Claw", "attack_bonus": "+5", "damage": "1d3", "damage_type": "Slashing"},
      {"name": "Claw", "attack_bonus": "+5", "damage": "1d3", "damage_type": "Slashing"}
    ],
    "special_attacks": [
      "Breath Weapon (cone 10 ft., DC 12 Ref or blinded 3 rounds; recharge 1d4 rounds)",
      "Spell-Like Abilities (blur 1/day, wind wall 1/day; CL 6th)"
    ],
    "special_qualities": [
      "Darkvision 60 ft.",
      "DR 5/Magic",
      "Elemental Traits",
      "Fast Healing 2 (in arid environments)",
      "Summon Mephit (15% chance, 1 mephit of same type)"
    ],
    "saves": {"fort": 3, "ref": 5, "will": 3},
    "abilities": {"str": 10, "dex": 17, "con": 10, "int": 6, "wis": 11, "cha": 15},
    "skills": {"Bluff": 8, "Diplomacy": 2, "Hide": 12, "Listen": 6, "Move Silently": 8, "Spot": 6},
    "feats": ["Improved Initiative", "Toughness"],
    "alignment": "Always Neutral",
    "advancement": "None",
    "dr": "5/Magic", "sr": None, "regen": None, "fast_heal": 2,
    "elemental_weaknesses": [], "alignment_weaknesses": [], "passive_effects": [],
    "population_base": 10, "allowed_biomes": ["Warm_Desert", "Temperate_Desert"], "primary_biome": "Warm_Desert",
    "ecology_notes": "Dust mephits are creatures of arid, windswept places, their blinding breath weapon making them effective ambushers in desert ruins and dry canyons."
  },
  {
    "name": "Mephit, Earth",
    "cr": 3, "size": "Small", "type": "Outsider", "subtype": "Earth",
    "hit_dice": "3d8+3", "hp_avg": 16, "initiative": 0,
    "speed": {"land": 30, "fly": 40},
    "armor_class": {"total": 16, "touch": 11, "flat_footed": 16,
                    "components": "+4 natural, +1 size"},
    "base_attack": 2, "grapple": -2,
    "attacks": [
      {"name": "Claw", "attack_bonus": "+4", "damage": "1d3+2", "damage_type": "Slashing"},
      {"name": "Claw", "attack_bonus": "+4", "damage": "1d3+2", "damage_type": "Slashing"}
    ],
    "special_attacks": [
      "Breath Weapon (cone 15 ft., DC 12 Ref, 1d8 jagged rock shards; recharge 1d4 rounds)",
      "Spell-Like Abilities (soften earth and stone 1/day, stinking cloud 1/day; CL 6th)"
    ],
    "special_qualities": [
      "Darkvision 60 ft.",
      "DR 5/Magic",
      "Elemental Traits",
      "Fast Healing 2 (underground or on Elemental Plane of Earth)",
      "Summon Mephit (15% chance, 1 mephit of same type)"
    ],
    "saves": {"fort": 4, "ref": 3, "will": 3},
    "abilities": {"str": 17, "dex": 10, "con": 13, "int": 6, "wis": 11, "cha": 15},
    "skills": {"Bluff": 7, "Diplomacy": 2, "Hide": 9, "Listen": 6, "Move Silently": 6, "Spot": 6},
    "feats": ["Power Attack", "Toughness"],
    "alignment": "Always Neutral",
    "advancement": "None",
    "dr": "5/Magic", "sr": None, "regen": None, "fast_heal": 2,
    "elemental_weaknesses": [], "alignment_weaknesses": [], "passive_effects": [],
    "population_base": 10, "allowed_biomes": ["Mountain", "Underground"], "primary_biome": "Mountain",
    "ecology_notes": "Earth mephits are squat, heavy-limbed creatures that haunt mines and caverns. Their stone-sharp breath makes them dangerous despite their small stature."
  },
  {
    "name": "Mephit, Fire",
    "cr": 3, "size": "Small", "type": "Outsider", "subtype": "Fire",
    "hit_dice": "3d8", "hp_avg": 13, "initiative": 7,
    "speed": {"land": 30, "fly": 40},
    "armor_class": {"total": 16, "touch": 14, "flat_footed": 13,
                    "components": "+3 Dex, +2 natural, +1 size"},
    "base_attack": 2, "grapple": -2,
    "attacks": [
      {"name": "Claw", "attack_bonus": "+5", "damage": "1d3 plus 1d4 fire", "damage_type": "Slashing + Fire"},
      {"name": "Claw", "attack_bonus": "+5", "damage": "1d3 plus 1d4 fire", "damage_type": "Slashing + Fire"}
    ],
    "special_attacks": [
      "Breath Weapon (cone 10 ft., DC 12 Ref, 1d8 fire damage; recharge 1d4 rounds)",
      "Spell-Like Abilities (scorching ray 1/day, heat metal 1/day; CL 6th)"
    ],
    "special_qualities": [
      "Darkvision 60 ft.",
      "DR 5/Magic",
      "Elemental Traits",
      "Fast Healing 2 (near open flames or on Elemental Plane of Fire)",
      "Immunity to Fire",
      "Summon Mephit (15% chance, 1 mephit of same type)"
    ],
    "saves": {"fort": 3, "ref": 5, "will": 3},
    "abilities": {"str": 10, "dex": 17, "con": 10, "int": 6, "wis": 11, "cha": 15},
    "skills": {"Bluff": 8, "Diplomacy": 2, "Hide": 12, "Listen": 6, "Move Silently": 8, "Spot": 6},
    "feats": ["Improved Initiative", "Toughness"],
    "alignment": "Always Neutral",
    "advancement": "None",
    "dr": "5/Magic", "sr": None, "regen": None, "fast_heal": 2,
    "elemental_weaknesses": ["Cold"], "alignment_weaknesses": [], "passive_effects": [],
    "population_base": 10, "allowed_biomes": ["Warm_Desert", "Warm_Plain"], "primary_biome": "Warm_Desert",
    "ecology_notes": "Fire mephits are cruel and boastful creatures that delight in setting things ablaze. Their fiery claws and breath weapon make them dangerous out of proportion to their size."
  },
  {
    "name": "Mephit, Ice",
    "cr": 3, "size": "Small", "type": "Outsider", "subtype": "Cold",
    "hit_dice": "3d8", "hp_avg": 13, "initiative": 7,
    "speed": {"land": 30, "fly": 40},
    "armor_class": {"total": 16, "touch": 14, "flat_footed": 13,
                    "components": "+3 Dex, +2 natural, +1 size"},
    "base_attack": 2, "grapple": -2,
    "attacks": [
      {"name": "Claw", "attack_bonus": "+5", "damage": "1d3 plus 1d4 cold", "damage_type": "Slashing + Cold"},
      {"name": "Claw", "attack_bonus": "+5", "damage": "1d3 plus 1d4 cold", "damage_type": "Slashing + Cold"}
    ],
    "special_attacks": [
      "Breath Weapon (cone 10 ft., DC 12 Ref, 1d4 cold plus ice shard piercing; recharge 1d4 rounds)",
      "Spell-Like Abilities (chill metal 1/day, ice storm 1/day; CL 6th)"
    ],
    "special_qualities": [
      "Darkvision 60 ft.",
      "DR 5/Magic",
      "Elemental Traits",
      "Fast Healing 2 (in cold environments or on Elemental Plane of Ice)",
      "Immunity to Cold",
      "Summon Mephit (15% chance, 1 mephit of same type)"
    ],
    "saves": {"fort": 3, "ref": 5, "will": 3},
    "abilities": {"str": 10, "dex": 17, "con": 10, "int": 6, "wis": 11, "cha": 15},
    "skills": {"Bluff": 8, "Diplomacy": 2, "Hide": 12, "Listen": 6, "Move Silently": 8, "Spot": 6},
    "feats": ["Improved Initiative", "Toughness"],
    "alignment": "Always Neutral",
    "advancement": "None",
    "dr": "5/Magic", "sr": None, "regen": None, "fast_heal": 2,
    "elemental_weaknesses": ["Fire"], "alignment_weaknesses": [], "passive_effects": [],
    "population_base": 10, "allowed_biomes": ["Arctic", "Cold_Plain"], "primary_biome": "Arctic",
    "ecology_notes": "Ice mephits are spiteful creatures of frost and frozen air, native to the border between the Elemental Planes of Air and Water. They inhabit glacial caves and frozen tundras."
  },
  {
    "name": "Mephit, Magma",
    "cr": 4, "size": "Small", "type": "Outsider", "subtype": "Fire, Earth",
    "hit_dice": "4d8+4", "hp_avg": 22, "initiative": 0,
    "speed": {"land": 30, "fly": 40},
    "armor_class": {"total": 17, "touch": 11, "flat_footed": 17,
                    "components": "+5 natural, +1 size"},
    "base_attack": 3, "grapple": -1,
    "attacks": [
      {"name": "Claw", "attack_bonus": "+4", "damage": "1d3+1 plus 1d4 fire", "damage_type": "Slashing + Fire"},
      {"name": "Claw", "attack_bonus": "+4", "damage": "1d3+1 plus 1d4 fire", "damage_type": "Slashing + Fire"}
    ],
    "special_attacks": [
      "Breath Weapon (cone 10 ft., DC 13 Ref, 1d4 fire from lava splash; recharge 1d4 rounds)",
      "Spell-Like Abilities (acid splash 3/day, produce flame 1/day; CL 6th)"
    ],
    "special_qualities": [
      "Darkvision 60 ft.",
      "DR 5/Magic",
      "Elemental Traits",
      "Fast Healing 2 (near lava or magma)",
      "Immunity to Fire",
      "Summon Mephit (15% chance, 1 mephit of same type)"
    ],
    "saves": {"fort": 5, "ref": 3, "will": 4},
    "abilities": {"str": 13, "dex": 10, "con": 13, "int": 6, "wis": 11, "cha": 15},
    "skills": {"Bluff": 7, "Diplomacy": 2, "Hide": 8, "Listen": 5, "Move Silently": 6, "Spot": 5},
    "feats": ["Power Attack", "Toughness"],
    "alignment": "Always Neutral",
    "advancement": "None",
    "dr": "5/Magic", "sr": None, "regen": None, "fast_heal": 2,
    "elemental_weaknesses": ["Cold"], "alignment_weaknesses": [], "passive_effects": [],
    "population_base": 5, "allowed_biomes": ["Mountain", "Underground"], "primary_biome": "Mountain",
    "ecology_notes": "Magma mephits dwell near volcanic vents and lava flows, creatures born from the border between Earth and Fire planes. Their superheated claws can melt stone over time."
  },
  {
    "name": "Mephit, Ooze",
    "cr": 3, "size": "Small", "type": "Outsider", "subtype": "Water, Earth",
    "hit_dice": "3d8+3", "hp_avg": 16, "initiative": 0,
    "speed": {"land": 30, "fly": 40},
    "armor_class": {"total": 16, "touch": 11, "flat_footed": 16,
                    "components": "+4 natural, +1 size"},
    "base_attack": 2, "grapple": -2,
    "attacks": [
      {"name": "Claw", "attack_bonus": "+4", "damage": "1d3+2", "damage_type": "Slashing"},
      {"name": "Claw", "attack_bonus": "+4", "damage": "1d3+2", "damage_type": "Slashing"}
    ],
    "special_attacks": [
      "Breath Weapon (cone 10 ft., DC 12 Ref, 1d4 acid; recharge 1d4 rounds)",
      "Spell-Like Abilities (acid splash 3/day, stinking cloud 1/day; CL 6th)"
    ],
    "special_qualities": [
      "Darkvision 60 ft.",
      "DR 5/Magic",
      "Elemental Traits",
      "Fast Healing 2 (in swampy or muddy environments)",
      "Summon Mephit (15% chance, 1 mephit of same type)"
    ],
    "saves": {"fort": 4, "ref": 3, "will": 3},
    "abilities": {"str": 14, "dex": 10, "con": 13, "int": 6, "wis": 11, "cha": 15},
    "skills": {"Bluff": 7, "Diplomacy": 2, "Hide": 8, "Listen": 5, "Move Silently": 6, "Spot": 5},
    "feats": ["Power Attack", "Toughness"],
    "alignment": "Always Neutral",
    "advancement": "None",
    "dr": "5/Magic", "sr": None, "regen": None, "fast_heal": 2,
    "elemental_weaknesses": [], "alignment_weaknesses": [], "passive_effects": [],
    "population_base": 10, "allowed_biomes": ["Temperate_Swamp", "Warm_Swamp"], "primary_biome": "Temperate_Swamp",
    "ecology_notes": "Ooze mephits are creatures of muddy, stagnant water from the border of the Earth and Water planes. They inhabit swamps and bogs, smelling of rot and corrosion."
  },
  {
    "name": "Mephit, Salt",
    "cr": 3, "size": "Small", "type": "Outsider", "subtype": "Earth",
    "hit_dice": "3d8", "hp_avg": 13, "initiative": 7,
    "speed": {"land": 30, "fly": 40},
    "armor_class": {"total": 17, "touch": 14, "flat_footed": 14,
                    "components": "+3 Dex, +3 natural, +1 size"},
    "base_attack": 2, "grapple": -2,
    "attacks": [
      {"name": "Claw", "attack_bonus": "+5", "damage": "1d3", "damage_type": "Slashing"},
      {"name": "Claw", "attack_bonus": "+5", "damage": "1d3", "damage_type": "Slashing"}
    ],
    "special_attacks": [
      "Breath Weapon (cone 10 ft., DC 12 Fort, 1d8 dehydration damage plus Fatigue; recharge 1d4 rounds)",
      "Spell-Like Abilities (glitterdust 1/day, parching touch 1/day; CL 6th)"
    ],
    "special_qualities": [
      "Darkvision 60 ft.",
      "DR 5/Magic",
      "Elemental Traits",
      "Fast Healing 2 (in arid or salty environments)",
      "Summon Mephit (15% chance, 1 mephit of same type)"
    ],
    "saves": {"fort": 3, "ref": 5, "will": 3},
    "abilities": {"str": 10, "dex": 17, "con": 10, "int": 6, "wis": 11, "cha": 15},
    "skills": {"Bluff": 8, "Diplomacy": 2, "Hide": 12, "Listen": 6, "Move Silently": 8, "Spot": 6},
    "feats": ["Improved Initiative", "Toughness"],
    "alignment": "Always Neutral",
    "advancement": "None",
    "dr": "5/Magic", "sr": None, "regen": None, "fast_heal": 2,
    "elemental_weaknesses": ["Water"], "alignment_weaknesses": [], "passive_effects": [],
    "population_base": 10, "allowed_biomes": ["Temperate_Desert", "Warm_Desert"], "primary_biome": "Warm_Desert",
    "ecology_notes": "Salt mephits are parched, crystalline creatures from arid borderlands. Their dehydrating breath weapon is particularly lethal in desert environments where water is already scarce."
  },
  {
    "name": "Mephit, Steam",
    "cr": 3, "size": "Small", "type": "Outsider", "subtype": "Fire, Water",
    "hit_dice": "3d8", "hp_avg": 13, "initiative": 7,
    "speed": {"land": 30, "fly": 40},
    "armor_class": {"total": 17, "touch": 14, "flat_footed": 14,
                    "components": "+3 Dex, +3 natural, +1 size"},
    "base_attack": 2, "grapple": -2,
    "attacks": [
      {"name": "Claw", "attack_bonus": "+5", "damage": "1d3", "damage_type": "Slashing"},
      {"name": "Claw", "attack_bonus": "+5", "damage": "1d3", "damage_type": "Slashing"}
    ],
    "special_attacks": [
      "Breath Weapon (cone 10 ft., DC 12 Fort, 1d4 fire plus 1d4 scalding steam; recharge 1d4 rounds)",
      "Spell-Like Abilities (blur 1/day, pyrotechnics 1/day; CL 6th)"
    ],
    "special_qualities": [
      "Darkvision 60 ft.",
      "DR 5/Magic",
      "Elemental Traits",
      "Fast Healing 2 (near steam vents or boiling water)",
      "Immunity to Fire",
      "Summon Mephit (15% chance, 1 mephit of same type)"
    ],
    "saves": {"fort": 3, "ref": 5, "will": 3},
    "abilities": {"str": 10, "dex": 17, "con": 10, "int": 6, "wis": 11, "cha": 15},
    "skills": {"Bluff": 8, "Diplomacy": 2, "Hide": 12, "Listen": 6, "Move Silently": 8, "Spot": 6},
    "feats": ["Improved Initiative", "Toughness"],
    "alignment": "Always Neutral",
    "advancement": "None",
    "dr": "5/Magic", "sr": None, "regen": None, "fast_heal": 2,
    "elemental_weaknesses": [], "alignment_weaknesses": [], "passive_effects": [],
    "population_base": 10, "allowed_biomes": ["Warm_Aquatic", "Temperate_Aquatic"], "primary_biome": "Warm_Aquatic",
    "ecology_notes": "Steam mephits haunt volcanic hot springs and geothermal vents, born where fire meets water. Their scalding breath makes them deadly in enclosed spaces."
  },
  {
    "name": "Mephit, Water",
    "cr": 3, "size": "Small", "type": "Outsider", "subtype": "Water",
    "hit_dice": "3d8", "hp_avg": 13, "initiative": 7,
    "speed": {"land": 30, "fly": 40},
    "armor_class": {"total": 17, "touch": 14, "flat_footed": 14,
                    "components": "+3 Dex, +3 natural, +1 size"},
    "base_attack": 2, "grapple": -2,
    "attacks": [
      {"name": "Claw", "attack_bonus": "+5", "damage": "1d3", "damage_type": "Slashing"},
      {"name": "Claw", "attack_bonus": "+5", "damage": "1d3", "damage_type": "Slashing"}
    ],
    "special_attacks": [
      "Breath Weapon (cone 10 ft., DC 12 Fort, 1d8 acid from briny spit; recharge 1d4 rounds)",
      "Spell-Like Abilities (acid arrow 2/day, stinking cloud 1/day; CL 6th)"
    ],
    "special_qualities": [
      "Darkvision 60 ft.",
      "DR 5/Magic",
      "Elemental Traits",
      "Fast Healing 2 (in or near water)",
      "Immunity to Cold",
      "Summon Mephit (15% chance, 1 mephit of same type)"
    ],
    "saves": {"fort": 3, "ref": 5, "will": 3},
    "abilities": {"str": 10, "dex": 17, "con": 10, "int": 6, "wis": 11, "cha": 15},
    "skills": {"Bluff": 8, "Diplomacy": 2, "Hide": 12, "Listen": 6, "Move Silently": 8, "Spot": 6},
    "feats": ["Improved Initiative", "Toughness"],
    "alignment": "Always Neutral",
    "advancement": "None",
    "dr": "5/Magic", "sr": None, "regen": None, "fast_heal": 2,
    "elemental_weaknesses": ["Fire"], "alignment_weaknesses": [], "passive_effects": [],
    "population_base": 10, "allowed_biomes": ["Temperate_Aquatic", "Warm_Aquatic"], "primary_biome": "Temperate_Aquatic",
    "ecology_notes": "Water mephits dwell near coasts, rivers, and bogs. They are obnoxious and vain, collecting shiny objects and lording over smaller aquatic creatures."
  }
]

# ─────────────────────────────────────────────────────────────
# GIANTS
# ─────────────────────────────────────────────────────────────
giants = [
  {
    "name": "Cloud Giant",
    "cr": 11, "size": "Huge", "type": "Giant", "subtype": None,
    "hit_dice": "17d8+102", "hp_avg": 178, "initiative": 1,
    "speed": {"land": 50},
    "armor_class": {"total": 25, "touch": 9, "flat_footed": 24,
                    "components": "+1 Dex, +16 natural, -2 size"},
    "base_attack": 12, "grapple": 30,
    "attacks": [
      {"name": "Morningstar", "attack_bonus": "+22/+17/+12", "damage": "4d6+18", "damage_type": "Bludgeoning + Piercing"}
    ],
    "special_attacks": [
      "Oversized Weapon (wields Huge morningstar two-handed)",
      "Rock Throwing (range increment 140 ft., 2d8+12 damage)"
    ],
    "special_qualities": [
      "Low-Light Vision",
      "Rock Catching",
      "Scent",
      "Spell-Like Abilities (levitate 3/day, obscuring mist 2/day, fog cloud 1/day, solid fog 1/day; CL 15th)"
    ],
    "saves": {"fort": 16, "ref": 6, "will": 7},
    "abilities": {"str": 35, "dex": 13, "con": 23, "int": 12, "wis": 16, "cha": 13},
    "skills": {"Climb": 22, "Listen": 22, "Perform (harp)": 11, "Sense Motive": 13, "Spot": 22},
    "feats": ["Alertness", "Awesome Blow", "Combat Reflexes", "Improved Bull Rush", "Iron Will", "Power Attack"],
    "alignment": "Usually Neutral Good or Neutral Evil",
    "advancement": "18-34 HD (Huge); 35-51 HD (Gargantuan)",
    "dr": None, "sr": None, "regen": None, "fast_heal": None,
    "elemental_weaknesses": [], "alignment_weaknesses": [], "passive_effects": [],
    "population_base": 10, "allowed_biomes": ["Mountain", "Cold_Plain"], "primary_biome": "Mountain",
    "ecology_notes": "Cloud giants dwell in mountaintop castles or grand structures in the clouds. Their alignment varies widely; Good cloud giants are reclusive and artistic while Evil ones raid lowland settlements."
  },
  {
    "name": "Ettin",
    "cr": 6, "size": "Large", "type": "Giant", "subtype": None,
    "hit_dice": "10d8+20", "hp_avg": 65, "initiative": 3,
    "speed": {"land": 30},
    "armor_class": {"total": 18, "touch": 9, "flat_footed": 16,
                    "components": "-1 Dex, +9 natural, -1 size"},
    "base_attack": 7, "grapple": 17,
    "attacks": [
      {"name": "Morningstar (right)", "attack_bonus": "+12/+7", "damage": "2d6+6", "damage_type": "Bludgeoning + Piercing"},
      {"name": "Morningstar (left)", "attack_bonus": "+12/+7", "damage": "2d6+3", "damage_type": "Bludgeoning + Piercing"}
    ],
    "special_attacks": [
      "Superior Two-Weapon Fighting (no attack or damage penalty for fighting with two weapons)"
    ],
    "special_qualities": [
      "Low-Light Vision",
      "Two Heads (immune to flanking; +2 to Listen, Spot, and Search checks)"
    ],
    "saves": {"fort": 9, "ref": 3, "will": 3},
    "abilities": {"str": 23, "dex": 8, "con": 15, "int": 6, "wis": 10, "cha": 11},
    "skills": {"Listen": 10, "Search": 1, "Spot": 10},
    "feats": ["Alertness", "Improved Initiative", "Iron Will", "Power Attack"],
    "alignment": "Usually Chaotic Evil",
    "advancement": "11-15 HD (Large); 16-30 HD (Huge)",
    "dr": None, "sr": None, "regen": None, "fast_heal": None,
    "elemental_weaknesses": [], "alignment_weaknesses": [], "passive_effects": [],
    "population_base": 20, "allowed_biomes": ["Cold_Plain", "Mountain"], "primary_biome": "Cold_Plain",
    "ecology_notes": "Ettins are two-headed giants notorious for their constant arguments between heads and their brutal raiding. Their two heads grant them remarkable vigilance, making them nearly impossible to surprise."
  },
  {
    "name": "Fire Giant",
    "cr": 10, "size": "Large", "type": "Giant", "subtype": None,
    "hit_dice": "15d8+75", "hp_avg": 142, "initiative": -1,
    "speed": {"land": 30},
    "armor_class": {"total": 23, "touch": 8, "flat_footed": 23,
                    "components": "-1 Dex, +12 natural, -1 size, +3 armor"},
    "base_attack": 11, "grapple": 23,
    "attacks": [
      {"name": "Greatsword", "attack_bonus": "+19/+14/+9", "damage": "3d6+15", "damage_type": "Slashing"}
    ],
    "special_attacks": [
      "Rock Throwing (range increment 120 ft., 2d6+10 damage)"
    ],
    "special_qualities": [
      "Low-Light Vision",
      "Rock Catching",
      "Immunity to Fire"
    ],
    "saves": {"fort": 14, "ref": 4, "will": 5},
    "abilities": {"str": 31, "dex": 9, "con": 21, "int": 10, "wis": 11, "cha": 11},
    "skills": {"Climb": 13, "Craft (weaponsmithing)": 10, "Intimidate": 11, "Listen": 11, "Spot": 11},
    "feats": ["Cleave", "Great Cleave", "Improved Sunder", "Power Attack", "Weapon Focus (greatsword)"],
    "alignment": "Usually Lawful Evil",
    "advancement": "16-22 HD (Large); 23-45 HD (Huge)",
    "dr": None, "sr": None, "regen": None, "fast_heal": None,
    "elemental_weaknesses": ["Cold"], "alignment_weaknesses": [], "passive_effects": [],
    "population_base": 15, "allowed_biomes": ["Mountain", "Warm_Desert"], "primary_biome": "Mountain",
    "ecology_notes": "Fire giants are militaristic giants that dwell in volcanic mountains and forge powerful weapons. Their disciplined society contrasts sharply with most giant-kin, and their smithcraft is legendary."
  },
  {
    "name": "Frost Giant",
    "cr": 9, "size": "Large", "type": "Giant", "subtype": None,
    "hit_dice": "14d8+56", "hp_avg": 119, "initiative": -1,
    "speed": {"land": 40},
    "armor_class": {"total": 21, "touch": 8, "flat_footed": 21,
                    "components": "-1 Dex, -1 size, +13 natural"},
    "base_attack": 10, "grapple": 22,
    "attacks": [
      {"name": "Greataxe", "attack_bonus": "+17/+12", "damage": "3d6+13", "damage_type": "Slashing"}
    ],
    "special_attacks": [
      "Rock Throwing (range increment 120 ft., 2d6+9 damage)"
    ],
    "special_qualities": [
      "Low-Light Vision",
      "Rock Catching",
      "Immunity to Cold"
    ],
    "saves": {"fort": 13, "ref": 3, "will": 4},
    "abilities": {"str": 29, "dex": 9, "con": 19, "int": 10, "wis": 11, "cha": 11},
    "skills": {"Climb": 11, "Intimidate": 11, "Listen": 11, "Spot": 11},
    "feats": ["Cleave", "Great Cleave", "Improved Sunder", "Power Attack"],
    "alignment": "Usually Chaotic Evil",
    "advancement": "15-21 HD (Large); 22-42 HD (Huge)",
    "dr": None, "sr": None, "regen": None, "fast_heal": None,
    "elemental_weaknesses": ["Fire"], "alignment_weaknesses": [], "passive_effects": [],
    "population_base": 15, "allowed_biomes": ["Arctic", "Cold_Plain", "Mountain"], "primary_biome": "Arctic",
    "ecology_notes": "Frost giants are raiders from arctic wastes, their immunity to cold allowing them to thrive where others perish. They organize into war-bands and serve powerful ice giants or dragon overlords."
  },
  {
    "name": "Hill Giant",
    "cr": 7, "size": "Large", "type": "Giant", "subtype": None,
    "hit_dice": "12d8+48", "hp_avg": 102, "initiative": -1,
    "speed": {"land": 30},
    "armor_class": {"total": 20, "touch": 7, "flat_footed": 20,
                    "components": "-1 Dex, -1 size, +9 natural, +3 hide armor"},
    "base_attack": 9, "grapple": 19,
    "attacks": [
      {"name": "Greatclub", "attack_bonus": "+14/+9", "damage": "2d8+10", "damage_type": "Bludgeoning"}
    ],
    "special_attacks": [
      "Rock Throwing (range increment 120 ft., 2d6+7 damage)"
    ],
    "special_qualities": [
      "Low-Light Vision",
      "Rock Catching"
    ],
    "saves": {"fort": 12, "ref": 3, "will": 3},
    "abilities": {"str": 25, "dex": 8, "con": 19, "int": 6, "wis": 10, "cha": 7},
    "skills": {"Climb": 11, "Intimidate": 7, "Listen": 7, "Spot": 7},
    "feats": ["Cleave", "Improved Bull Rush", "Power Attack", "Weapon Focus (greatclub)"],
    "alignment": "Usually Chaotic Evil",
    "advancement": "13-18 HD (Large); 19-36 HD (Huge)",
    "dr": None, "sr": None, "regen": None, "fast_heal": None,
    "elemental_weaknesses": [], "alignment_weaknesses": [], "passive_effects": [],
    "population_base": 30, "allowed_biomes": ["Temperate_Plain", "Mountain", "Cold_Plain"], "primary_biome": "Temperate_Plain",
    "ecology_notes": "Hill giants are the most common and least intelligent of giantkind, living in rough-hewn caves and raiding nearby settlements for food. They are bullied by higher giants but bully everything smaller."
  },
  {
    "name": "Ogre Mage",
    "cr": 8, "size": "Large", "type": "Giant", "subtype": None,
    "hit_dice": "5d8+15", "hp_avg": 37, "initiative": 4,
    "speed": {"land": 40, "fly": 60},
    "armor_class": {"total": 18, "touch": 13, "flat_footed": 14,
                    "components": "+4 Dex, -1 size, +5 natural"},
    "base_attack": 3, "grapple": 12,
    "attacks": [
      {"name": "Greatsword", "attack_bonus": "+7", "damage": "3d6+7", "damage_type": "Slashing"}
    ],
    "special_attacks": [
      "Spell-Like Abilities (at will: darkness, invisibility; 1/day: charm person DC 14, cone of cold DC 18, gaseous form, polymorph, sleep DC 14; CL 9th)"
    ],
    "special_qualities": [
      "Change Shape (any Small, Medium, or Large humanoid; as alter self)",
      "Flight",
      "Low-Light Vision",
      "Regeneration 5 (fire and acid deal normal damage)"
    ],
    "saves": {"fort": 7, "ref": 5, "will": 3},
    "abilities": {"str": 21, "dex": 19, "con": 17, "int": 14, "wis": 14, "cha": 17},
    "skills": {"Concentration": 11, "Listen": 12, "Sense Motive": 12, "Spellcraft": 10, "Spot": 12},
    "feats": ["Combat Expertise", "Improved Initiative"],
    "alignment": "Usually Lawful Evil",
    "advancement": "6-10 HD (Large); 11-15 HD (Huge)",
    "dr": None, "sr": None, "regen": 5, "fast_heal": None,
    "elemental_weaknesses": [], "alignment_weaknesses": [], "passive_effects": [],
    "population_base": 10, "allowed_biomes": ["Mountain", "Temperate_Forest"], "primary_biome": "Mountain",
    "ecology_notes": "Ogre mages are rare and intelligent oni-like giants with potent magical abilities. They use their shape-changing and spells to manipulate lesser creatures, sometimes ruling humanoid or ogre tribes from the shadows."
  },
  {
    "name": "Stone Giant",
    "cr": 8, "size": "Large", "type": "Giant", "subtype": None,
    "hit_dice": "14d8+42", "hp_avg": 105, "initiative": 2,
    "speed": {"land": 40},
    "armor_class": {"total": 25, "touch": 11, "flat_footed": 23,
                    "components": "+2 Dex, -1 size, +14 natural"},
    "base_attack": 10, "grapple": 20,
    "attacks": [
      {"name": "Greatclub", "attack_bonus": "+16/+11", "damage": "2d8+12", "damage_type": "Bludgeoning"}
    ],
    "special_attacks": [
      "Rock Throwing (range increment 180 ft., 2d8+9 damage)"
    ],
    "special_qualities": [
      "Low-Light Vision",
      "Rock Catching"
    ],
    "saves": {"fort": 12, "ref": 6, "will": 5},
    "abilities": {"str": 27, "dex": 15, "con": 17, "int": 10, "wis": 12, "cha": 11},
    "skills": {"Climb": 14, "Hide": 6, "Jump": 14, "Listen": 10, "Spot": 10},
    "feats": ["Combat Reflexes", "Far Shot", "Point Blank Shot", "Power Attack", "Precise Shot"],
    "alignment": "Usually Neutral",
    "advancement": "15-21 HD (Large); 22-42 HD (Huge)",
    "dr": None, "sr": None, "regen": None, "fast_heal": None,
    "elemental_weaknesses": [], "alignment_weaknesses": [], "passive_effects": [],
    "population_base": 15, "allowed_biomes": ["Mountain"], "primary_biome": "Mountain",
    "ecology_notes": "Stone giants are reclusive mountain dwellers who prefer to be left alone. They are master rock-throwers and use their natural camouflage to avoid conflict, though they defend their territory ferociously."
  },
  {
    "name": "Storm Giant",
    "cr": 13, "size": "Huge", "type": "Giant", "subtype": None,
    "hit_dice": "19d8+133", "hp_avg": 218, "initiative": 2,
    "speed": {"land": 50, "swim": 40},
    "armor_class": {"total": 26, "touch": 11, "flat_footed": 24,
                    "components": "+2 Dex, +16 natural, -2 size"},
    "base_attack": 14, "grapple": 33,
    "attacks": [
      {"name": "Greatsword", "attack_bonus": "+25/+20/+15/+10", "damage": "4d6+19", "damage_type": "Slashing"}
    ],
    "special_attacks": [
      "Rock Throwing (range increment 200 ft., 2d8+13 damage)",
      "Spell-Like Abilities (call lightning 1/day DC 23, chain lightning 1/day DC 24, control weather 1/day, freedom of movement 1/day, levitate at will; CL 15th)"
    ],
    "special_qualities": [
      "Low-Light Vision",
      "Rock Catching",
      "Immunity to Electricity",
      "Water Breathing",
      "Waterwalk (at will)"
    ],
    "saves": {"fort": 18, "ref": 8, "will": 9},
    "abilities": {"str": 39, "dex": 14, "con": 25, "int": 16, "wis": 20, "cha": 15},
    "skills": {"Climb": 26, "Concentration": 20, "Listen": 22, "Perform (stringed instruments)": 12,
               "Sense Motive": 20, "Spot": 22},
    "feats": ["Awesome Blow", "Cleave", "Combat Reflexes", "Improved Bull Rush", "Iron Will", "Power Attack"],
    "alignment": "Usually Chaotic Good",
    "advancement": "20-29 HD (Huge); 30-57 HD (Gargantuan)",
    "dr": None, "sr": None, "regen": None, "fast_heal": None,
    "elemental_weaknesses": [], "alignment_weaknesses": [], "passive_effects": [],
    "population_base": 5, "allowed_biomes": ["Mountain", "Cold_Aquatic"], "primary_biome": "Mountain",
    "ecology_notes": "Storm giants are the mightiest of the true giants, dwelling atop the highest peaks or beneath the deepest seas. They are generally benevolent and wise, serving as mediators among giantkind."
  }
]

# ─── Write files ───
with open(os.path.join(OUT, "batch_constructs.json"), "w") as f:
    json.dump(constructs, f, indent=2)
print(f"batch_constructs.json: {len(constructs)} entries")

with open(os.path.join(OUT, "batch_elementals.json"), "w") as f:
    json.dump(elementals, f, indent=2)
print(f"batch_elementals.json: {len(elementals)} entries")

with open(os.path.join(OUT, "batch_giants.json"), "w") as f:
    json.dump(giants, f, indent=2)
print(f"batch_giants.json: {len(giants)} entries")

print("Done.")
