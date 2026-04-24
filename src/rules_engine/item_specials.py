"""
src/rules_engine/item_specials.py
----------------------------------
D&D 3.5e DMG Magic Item Special Abilities and Artifacts.

Implements:
- ArmorSpecialAbility / WeaponSpecialAbility schemas (T-006, T-007)
- ArtifactEntry schema (T-011)
- validate_armor_ability_stack / validate_weapon_ability_stack (T-025, T-026)
- ARMOR_SPECIAL_ABILITY_REGISTRY (T-032)
- WEAPON_SPECIAL_ABILITY_REGISTRY (T-033)
- generate_magic_armor / generate_magic_weapon (T-042, T-043)
- ARTIFACT_REGISTRY with 13 Minor + 13 Major Artifacts (T-044)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# T-006: ArmorSpecialAbility schema
# ---------------------------------------------------------------------------

class ArmorAbilityType(Enum):
    ENHANCEMENT = "enhancement"
    SPECIAL = "special"


@dataclass(slots=True)
class ArmorSpecialAbility:
    name: str
    bonus_equivalent: int       # equivalent enhancement bonus cost
    aura: str                   # e.g. "faint abjuration"
    cl: int                     # caster level required
    prerequisites: list[str]    # prerequisite spells/feats
    market_price_gp: int | None  # None if bonus-equivalent only
    ability_type: ArmorAbilityType = ArmorAbilityType.SPECIAL


# ---------------------------------------------------------------------------
# T-007: WeaponSpecialAbility schema
# ---------------------------------------------------------------------------

class WeaponAbilityType(Enum):
    ENHANCEMENT = "enhancement"
    SPECIAL = "special"


@dataclass(slots=True)
class WeaponSpecialAbility:
    name: str
    bonus_equivalent: int
    aura: str
    cl: int
    prerequisites: list[str]
    market_price_gp: int | None
    melee_only: bool = False
    ranged_only: bool = False
    ability_type: WeaponAbilityType = WeaponAbilityType.SPECIAL


# ---------------------------------------------------------------------------
# T-011: ArtifactEntry schema
# ---------------------------------------------------------------------------

class ArtifactType(Enum):
    MINOR = "minor"
    MAJOR = "major"


@dataclass(slots=True)
class ArtifactEntry:
    name: str
    artifact_type: ArtifactType
    powers: list[str]
    drawbacks: list[str]
    lore: str
    market_price_gp: None = None  # always None (priceless)


# ---------------------------------------------------------------------------
# T-025: validate_armor_ability_stack
# ---------------------------------------------------------------------------

class MagicItemError(Exception):
    pass


def validate_armor_ability_stack(base_bonus: int, abilities: list[ArmorSpecialAbility]) -> bool:
    """Total effective bonus (base + sum of bonus_equivalent) must not exceed +10."""
    total = base_bonus + sum(a.bonus_equivalent for a in abilities)
    if total > 10:
        raise MagicItemError(f"Total armor bonus {total} exceeds +10 cap")
    return True


# ---------------------------------------------------------------------------
# T-026: validate_weapon_ability_stack
# ---------------------------------------------------------------------------

def validate_weapon_ability_stack(base_bonus: int, abilities: list[WeaponSpecialAbility], ranged: bool = False) -> bool:
    """Same +10 cap; ranged weapons exclude melee_only abilities."""
    valid_abilities = [a for a in abilities if not (ranged and a.melee_only)]
    total = base_bonus + sum(a.bonus_equivalent for a in valid_abilities)
    if total > 10:
        raise MagicItemError(f"Total weapon bonus {total} exceeds +10 cap")
    return True


# ---------------------------------------------------------------------------
# T-032: ARMOR_SPECIAL_ABILITY_REGISTRY
# ---------------------------------------------------------------------------

ARMOR_SPECIAL_ABILITY_REGISTRY: dict[str, ArmorSpecialAbility] = {
    "Glamered": ArmorSpecialAbility(name="Glamered", bonus_equivalent=1, aura="faint illusion", cl=5, prerequisites=["disguise self"], market_price_gp=None),
    "Fortification, Light": ArmorSpecialAbility(name="Fortification, Light", bonus_equivalent=1, aura="strong abjuration", cl=13, prerequisites=["limited wish"], market_price_gp=None),
    "Fortification, Moderate": ArmorSpecialAbility(name="Fortification, Moderate", bonus_equivalent=3, aura="strong abjuration", cl=13, prerequisites=["limited wish"], market_price_gp=None),
    "Fortification, Heavy": ArmorSpecialAbility(name="Fortification, Heavy", bonus_equivalent=5, aura="strong abjuration", cl=13, prerequisites=["limited wish"], market_price_gp=None),
    "Invulnerability": ArmorSpecialAbility(name="Invulnerability", bonus_equivalent=3, aura="strong abjuration and evocation", cl=18, prerequisites=["invulnerability"], market_price_gp=None),
    "Reflecting": ArmorSpecialAbility(name="Reflecting", bonus_equivalent=5, aura="strong abjuration", cl=14, prerequisites=["spell turning"], market_price_gp=None),
    "Shadow": ArmorSpecialAbility(name="Shadow", bonus_equivalent=1, aura="faint illusion", cl=5, prerequisites=["invisibility"], market_price_gp=None),
    "Silent Moves": ArmorSpecialAbility(name="Silent Moves", bonus_equivalent=1, aura="faint transmutation", cl=5, prerequisites=["silence"], market_price_gp=None),
    "Slick": ArmorSpecialAbility(name="Slick", bonus_equivalent=1, aura="faint conjuration", cl=4, prerequisites=["grease"], market_price_gp=None),
    "Spell Resistance 13": ArmorSpecialAbility(name="Spell Resistance 13", bonus_equivalent=2, aura="strong abjuration", cl=15, prerequisites=["spell resistance"], market_price_gp=None),
    "Spell Resistance 15": ArmorSpecialAbility(name="Spell Resistance 15", bonus_equivalent=3, aura="strong abjuration", cl=15, prerequisites=["spell resistance"], market_price_gp=None),
    "Spell Resistance 17": ArmorSpecialAbility(name="Spell Resistance 17", bonus_equivalent=4, aura="strong abjuration", cl=15, prerequisites=["spell resistance"], market_price_gp=None),
    "Spell Resistance 19": ArmorSpecialAbility(name="Spell Resistance 19", bonus_equivalent=5, aura="strong abjuration", cl=15, prerequisites=["spell resistance"], market_price_gp=None),
    "Etherealness": ArmorSpecialAbility(name="Etherealness", bonus_equivalent=6, aura="strong transmutation", cl=13, prerequisites=["ethereal jaunt"], market_price_gp=None),
    "Undead Controlling": ArmorSpecialAbility(name="Undead Controlling", bonus_equivalent=9, aura="strong necromancy", cl=13, prerequisites=["control undead", "create undead"], market_price_gp=None),
    "Wild": ArmorSpecialAbility(name="Wild", bonus_equivalent=3, aura="moderate transmutation", cl=9, prerequisites=["baleful polymorph"], market_price_gp=None),
}


# ---------------------------------------------------------------------------
# T-033: WEAPON_SPECIAL_ABILITY_REGISTRY
# ---------------------------------------------------------------------------

WEAPON_SPECIAL_ABILITY_REGISTRY: dict[str, WeaponSpecialAbility] = {
    "Bane": WeaponSpecialAbility(name="Bane", bonus_equivalent=1, aura="faint conjuration", cl=8, prerequisites=["summon monster I"], market_price_gp=None),
    "Defending": WeaponSpecialAbility(name="Defending", bonus_equivalent=1, aura="faint abjuration", cl=8, prerequisites=["shield or shield of faith"], market_price_gp=None),
    "Disruption": WeaponSpecialAbility(name="Disruption", bonus_equivalent=2, aura="strong conjuration", cl=14, prerequisites=["heal"], market_price_gp=None, melee_only=True),
    "Distance": WeaponSpecialAbility(name="Distance", bonus_equivalent=1, aura="faint divination", cl=6, prerequisites=["clairaudience/clairvoyance"], market_price_gp=None, ranged_only=True),
    "Flaming": WeaponSpecialAbility(name="Flaming", bonus_equivalent=1, aura="faint evocation", cl=10, prerequisites=["flame blade, flame strike, or fireball"], market_price_gp=None),
    "Flaming Burst": WeaponSpecialAbility(name="Flaming Burst", bonus_equivalent=2, aura="moderate evocation", cl=12, prerequisites=["flame blade, flame strike, or fireball"], market_price_gp=None),
    "Frost": WeaponSpecialAbility(name="Frost", bonus_equivalent=1, aura="faint evocation", cl=8, prerequisites=["chill metal or ice storm"], market_price_gp=None),
    "Holy": WeaponSpecialAbility(name="Holy", bonus_equivalent=2, aura="moderate evocation", cl=7, prerequisites=["holy smite", "must be good"], market_price_gp=None),
    "Icy Burst": WeaponSpecialAbility(name="Icy Burst", bonus_equivalent=2, aura="moderate evocation", cl=10, prerequisites=["chill metal or ice storm"], market_price_gp=None),
    "Keen": WeaponSpecialAbility(name="Keen", bonus_equivalent=1, aura="faint transmutation", cl=10, prerequisites=["keen edge"], market_price_gp=None, melee_only=True),
    "Ki Focus": WeaponSpecialAbility(name="Ki Focus", bonus_equivalent=2, aura="moderate transmutation", cl=8, prerequisites=["creator must be a monk"], market_price_gp=None, melee_only=True),
    "Lawful": WeaponSpecialAbility(name="Lawful", bonus_equivalent=2, aura="moderate evocation", cl=7, prerequisites=["order's wrath", "must be lawful"], market_price_gp=None),
    "Merciful": WeaponSpecialAbility(name="Merciful", bonus_equivalent=1, aura="faint conjuration", cl=5, prerequisites=["cure light wounds"], market_price_gp=None),
    "Mighty Cleaving": WeaponSpecialAbility(name="Mighty Cleaving", bonus_equivalent=1, aura="faint evocation", cl=8, prerequisites=["cleave"], market_price_gp=None, melee_only=True),
    "Returning": WeaponSpecialAbility(name="Returning", bonus_equivalent=1, aura="faint transmutation", cl=7, prerequisites=["telekinesis"], market_price_gp=None),
    "Seeking": WeaponSpecialAbility(name="Seeking", bonus_equivalent=1, aura="moderate divination", cl=12, prerequisites=["true seeing"], market_price_gp=None, ranged_only=True),
    "Shock": WeaponSpecialAbility(name="Shock", bonus_equivalent=1, aura="faint evocation", cl=8, prerequisites=["call lightning or lightning bolt"], market_price_gp=None),
    "Shocking Burst": WeaponSpecialAbility(name="Shocking Burst", bonus_equivalent=2, aura="moderate evocation", cl=10, prerequisites=["call lightning or lightning bolt"], market_price_gp=None),
    "Speed": WeaponSpecialAbility(name="Speed", bonus_equivalent=3, aura="moderate transmutation", cl=7, prerequisites=["haste"], market_price_gp=None),
    "Spell Storing": WeaponSpecialAbility(name="Spell Storing", bonus_equivalent=1, aura="strong (no school)", cl=12, prerequisites=["creator must be a spellcaster"], market_price_gp=None),
    "Thundering": WeaponSpecialAbility(name="Thundering", bonus_equivalent=1, aura="faint necromancy", cl=5, prerequisites=["blindness/deafness"], market_price_gp=None),
    "Throwing": WeaponSpecialAbility(name="Throwing", bonus_equivalent=1, aura="faint transmutation", cl=5, prerequisites=["magic stone"], market_price_gp=None, melee_only=True),
    "Unholy": WeaponSpecialAbility(name="Unholy", bonus_equivalent=2, aura="moderate evocation", cl=7, prerequisites=["unholy blight", "must be evil"], market_price_gp=None),
    "Vicious": WeaponSpecialAbility(name="Vicious", bonus_equivalent=1, aura="moderate necromancy", cl=9, prerequisites=["enervation"], market_price_gp=None),
    "Vorpal": WeaponSpecialAbility(name="Vorpal", bonus_equivalent=5, aura="strong necromancy and transmutation", cl=18, prerequisites=["circle of death", "keen edge"], market_price_gp=None, melee_only=True),
    "Wounding": WeaponSpecialAbility(name="Wounding", bonus_equivalent=2, aura="moderate evocation", cl=10, prerequisites=["mage's sword"], market_price_gp=None),
    "Anarchic": WeaponSpecialAbility(name="Anarchic", bonus_equivalent=2, aura="moderate evocation", cl=7, prerequisites=["chaos hammer", "must be chaotic"], market_price_gp=None),
    "Axiomatic": WeaponSpecialAbility(name="Axiomatic", bonus_equivalent=2, aura="moderate evocation", cl=7, prerequisites=["order's wrath", "must be lawful"], market_price_gp=None),
}


# ---------------------------------------------------------------------------
# T-042: generate_magic_armor
# ---------------------------------------------------------------------------

def generate_magic_armor(
    base_armor_name: str,
    base_armor_cost_gp: int,
    enhancement: int,
    special_ability_names: list[str],
    rng=None,
) -> dict:
    """Returns dict with name, enhancement, special_abilities, market_price_gp, description."""
    abilities = [ARMOR_SPECIAL_ABILITY_REGISTRY[n] for n in special_ability_names]
    validate_armor_ability_stack(enhancement, abilities)
    price = base_armor_cost_gp + (enhancement ** 2) * 1000 + sum(
        (a.bonus_equivalent ** 2) * 1000 for a in abilities
    )
    return {
        "name": f"+{enhancement} {base_armor_name}" + (f" of {', '.join(special_ability_names)}" if special_ability_names else ""),
        "enhancement": enhancement,
        "special_abilities": special_ability_names,
        "market_price_gp": price,
        "base_armor": base_armor_name,
    }


# ---------------------------------------------------------------------------
# T-043: generate_magic_weapon
# ---------------------------------------------------------------------------

def generate_magic_weapon(
    base_weapon_name: str,
    base_weapon_cost_gp: int,
    enhancement: int,
    special_ability_names: list[str],
    ranged: bool = False,
    rng=None,
) -> dict:
    """Returns dict with name, enhancement, special_abilities, market_price_gp."""
    abilities = [WEAPON_SPECIAL_ABILITY_REGISTRY[n] for n in special_ability_names]
    validate_weapon_ability_stack(enhancement, abilities, ranged=ranged)
    price = base_weapon_cost_gp + (enhancement ** 2) * 2000 + sum(
        (a.bonus_equivalent ** 2) * 2000 for a in abilities
    )
    return {
        "name": f"+{enhancement} {base_weapon_name}" + (f" of {', '.join(special_ability_names)}" if special_ability_names else ""),
        "enhancement": enhancement,
        "special_abilities": special_ability_names,
        "market_price_gp": price,
        "base_weapon": base_weapon_name,
        "ranged": ranged,
    }


# ---------------------------------------------------------------------------
# T-044: ARTIFACT_REGISTRY — 13 Minor + 13 Major Artifacts
# ---------------------------------------------------------------------------

ARTIFACT_REGISTRY: dict[str, ArtifactEntry] = {
    # Minor Artifacts
    "Bag of Tricks (Rust)": ArtifactEntry(
        name="Bag of Tricks (Rust)",
        artifact_type=ArtifactType.MINOR,
        powers=["Produces a random animal 3/day", "Animals serve for 10 minutes"],
        drawbacks=["Animals disappear if bag is turned inside out"],
        lore="A small brown bag that produces animals from its depths.",
    ),
    "Candle of Invocation": ArtifactEntry(
        name="Candle of Invocation",
        artifact_type=ArtifactType.MINOR,
        powers=["Gate spell 1/day", "+2 caster level for aligned casters", "Commune 1/day"],
        drawbacks=["Destroyed after 4 hours of use", "Only works for matching alignment"],
        lore="A thin taper that glows with divine light.",
    ),
    "Crystal Ball": ArtifactEntry(
        name="Crystal Ball",
        artifact_type=ArtifactType.MINOR,
        powers=["Scrying at will", "Clairvoyance/clairaudience"],
        drawbacks=["Target may detect scrying"],
        lore="A perfect sphere of flawless crystal.",
    ),
    "Deck of Many Things": ArtifactEntry(
        name="Deck of Many Things",
        artifact_type=ArtifactType.MINOR,
        powers=["Draw cards for random powerful effects", "Wish, level gain, alignment change, etc."],
        drawbacks=["Catastrophic results possible (imprisonment, death)", "Unpredictable"],
        lore="A deck of twenty-two cards that reshape destiny.",
    ),
    "Figurines of Wondrous Power": ArtifactEntry(
        name="Figurines of Wondrous Power",
        artifact_type=ArtifactType.MINOR,
        powers=["Animates into creature for 6 hours/day", "Serves as mount or companion"],
        drawbacks=["Destroyed if killed while animated"],
        lore="Small statuettes that transform into real creatures.",
    ),
    "Horn of Valhalla": ArtifactEntry(
        name="Horn of Valhalla",
        artifact_type=ArtifactType.MINOR,
        powers=["Summons 2d4+2 barbarians 1/7 days"],
        drawbacks=["Must be proficient with all martial weapons to blow silver horn"],
        lore="A bronze horn engraved with Norse runes.",
    ),
    "Horseshoes of the Zephyr": ArtifactEntry(
        name="Horseshoes of the Zephyr",
        artifact_type=ArtifactType.MINOR,
        powers=["Horse can walk on air", "Leaves no tracks", "+10 ft speed"],
        drawbacks=["Only works on horses"],
        lore="Four shoes of mithral engraved with cloud patterns.",
    ),
    "Instant Fortress": ArtifactEntry(
        name="Instant Fortress",
        artifact_type=ArtifactType.MINOR,
        powers=["Becomes 20-ft cube tower on command", "Arrow slits, battlements, iron door"],
        drawbacks=["Creatures inside when dismissed are teleported outside"],
        lore="A small adamantine cube that unfolds into a tower.",
    ),
    "Iron Flask": ArtifactEntry(
        name="Iron Flask",
        artifact_type=ArtifactType.MINOR,
        powers=["Captures outsiders (DC 19 Will)", "Contained creature serves when released"],
        drawbacks=["50% chance captured creature attacks when released"],
        lore="A flask of iron with a brass stopper etched with sigils.",
    ),
    "Necklace of Prayer Beads": ArtifactEntry(
        name="Necklace of Prayer Beads",
        artifact_type=ArtifactType.MINOR,
        powers=["Beads grant spells: Bless, Cure Serious Wounds, Wind Walk, etc."],
        drawbacks=["Only divine spellcasters benefit"],
        lore="A string of beads made from sacred wood.",
    ),
    "Pearl of Power": ArtifactEntry(
        name="Pearl of Power",
        artifact_type=ArtifactType.MINOR,
        powers=["Recall one expended spell slot 1/day"],
        drawbacks=["Only works for arcane spellcasters"],
        lore="A perfect white pearl that pulses with magical energy.",
    ),
    "Portable Hole": ArtifactEntry(
        name="Portable Hole",
        artifact_type=ArtifactType.MINOR,
        powers=["Creates extradimensional space 6 ft diameter, 10 ft deep"],
        drawbacks=["Placing bag of holding inside causes planar rift"],
        lore="A circle of black cloth that opens into an extradimensional space.",
    ),
    "Rope of Entanglement": ArtifactEntry(
        name="Rope of Entanglement",
        artifact_type=ArtifactType.MINOR,
        powers=["Entangles target (DC 20 Reflex) at command", "Can bind up to 8 Medium creatures"],
        drawbacks=["Severable (AC 22, 22 HP, hardness 10)"],
        lore="A supple rope that moves on its own.",
    ),
    "Sphere of Annihilation": ArtifactEntry(
        name="Sphere of Annihilation",
        artifact_type=ArtifactType.MAJOR,
        powers=["2-ft globe of nothingness destroys all matter", "Controlled by Concentration check"],
        drawbacks=["If control is lost, moves randomly", "Contact with gate spell is catastrophic"],
        lore="A 2-foot globe of utter blackness.",
    ),
    "Staff of the Magi": ArtifactEntry(
        name="Staff of the Magi",
        artifact_type=ArtifactType.MAJOR,
        powers=["50 charges, multiple powerful spells", "Absorbs spells, retributive strike"],
        drawbacks=["Retributive strike may kill wielder and all nearby"],
        lore="A black staff engraved with arcane symbols.",
    ),
    # Additional major artifacts
    "Axe of the Dwarvish Lords": ArtifactEntry(
        name="Axe of the Dwarvish Lords",
        artifact_type=ArtifactType.MAJOR,
        powers=["+6 dwarven waraxe", "Grants dwarven racial traits", "Locate veins of metal"],
        drawbacks=["Non-dwarves suffer -2 to all saves while wielding"],
        lore="The axe crafted by the first dwarf king.",
    ),
    "Codex of the Infinite Planes": ArtifactEntry(
        name="Codex of the Infinite Planes",
        artifact_type=ArtifactType.MAJOR,
        powers=["Gate, plane shift, etherealness at will", "Read for 1d4 hours: powerful knowledge"],
        drawbacks=["Reading for 24+ hours: gate opens randomly", "Drives readers mad"],
        lore="A massive tome of infinite planar secrets.",
    ),
    "Eye of Vecna": ArtifactEntry(
        name="Eye of Vecna",
        artifact_type=ArtifactType.MAJOR,
        powers=["True seeing, clairvoyance", "Finger of death 1/day", "Power word blind at will"],
        drawbacks=["Must remove own eye to use", "Vecna can see through it"],
        lore="The eye of the undead archlich Vecna.",
    ),
    "Hand of Vecna": ArtifactEntry(
        name="Hand of Vecna",
        artifact_type=ArtifactType.MAJOR,
        powers=["Strength 26", "Cold touch 1d6 cold", "Detect magic at will"],
        drawbacks=["Must sever own hand to attach", "Vecna may take control"],
        lore="The mummified hand of the undead archlich Vecna.",
    ),
    "Philosopher's Stone": ArtifactEntry(
        name="Philosopher's Stone",
        artifact_type=ArtifactType.MAJOR,
        powers=["Transmute base metals to silver/gold", "Create true resurrection oil"],
        drawbacks=["Destroyed in creating resurrection oil"],
        lore="A lump of blackish stone with strange markings.",
    ),
    "Sword of Kas": ArtifactEntry(
        name="Sword of Kas",
        artifact_type=ArtifactType.MAJOR,
        powers=["+6 longsword", "Vorpal", "Unholy, wounding", "Sentient: INT 15, WIS 13, CHA 16"],
        drawbacks=["Seeks to destroy Hand of Vecna", "Chaotic evil alignment required"],
        lore="The blade once wielded by Vecna's lieutenant.",
    ),
    "Talisman of Pure Good": ArtifactEntry(
        name="Talisman of Pure Good",
        artifact_type=ArtifactType.MAJOR,
        powers=["Grants true resurrection 1/day to good clerics", "Destroys evil clerics on touch (DC 18 Reflex)"],
        drawbacks=["Only good divine spellcasters can use", "6 charges total, then plain lead"],
        lore="A golden talisman inscribed with a sunburst.",
    ),
    "Talisman of Ultimate Evil": ArtifactEntry(
        name="Talisman of Ultimate Evil",
        artifact_type=ArtifactType.MAJOR,
        powers=["Grants gate to evil outsiders 1/day", "Destroys good clerics on touch (DC 18 Reflex)"],
        drawbacks=["Only evil divine spellcasters can use", "6 charges, then plain iron"],
        lore="A black iron talisman engraved with a skull.",
    ),
    "Talisman of the Sphere": ArtifactEntry(
        name="Talisman of the Sphere",
        artifact_type=ArtifactType.MAJOR,
        powers=["+10 to checks to control sphere of annihilation", "Control from up to 30 ft away"],
        drawbacks=["Worthless without Sphere of Annihilation"],
        lore="A small iron loop etched with arcane marks.",
    ),
    "Orbs of Dragonkind": ArtifactEntry(
        name="Orbs of Dragonkind",
        artifact_type=ArtifactType.MAJOR,
        powers=["Command specific dragon type", "Drain life force of dominated dragon", "Locate dragons 1/day"],
        drawbacks=["Dominated dragon may break free (Will DC 25)", "Destroys itself if all dragons of type killed"],
        lore="Nine crystal orbs, each attuned to a different dragon type.",
    ),
    "Cup and Talisman of Al'Akbar": ArtifactEntry(
        name="Cup and Talisman of Al'Akbar",
        artifact_type=ArtifactType.MAJOR,
        powers=["Cure disease and poison at will", "Restoration 3/day", "Neutralize poison at will"],
        drawbacks=["Only good clerics can use", "Slowly converted to lawful good"],
        lore="A plain wooden cup and golden talisman of the Prophet Al'Akbar.",
    ),
}
