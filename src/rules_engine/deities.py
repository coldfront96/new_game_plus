"""
src/rules_engine/deities.py
----------------------------
D&D 3.5e Deity and Domain Engine for the New Game Plus engine.

Implements canonical SRD deities, their alignments, portfolios, and
favored weapons.  Also implements Cleric Domains with their domain
spell lists and granted powers, following the D&D 3.5e SRD.

Usage::

    from src.rules_engine.deities import DeityRegistry, DomainRegistry

    pelor = DeityRegistry.get("Pelor")
    print(pelor.alignment)          # "NG"
    print(pelor.favored_weapon)     # "Heavy Mace"

    healing = DomainRegistry.get("Healing")
    print(healing.domain_spells)    # {1: "Cure Light Wounds", ...}
    print(healing.granted_power)    # "Casts healing spells at +1 caster level"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


# ---------------------------------------------------------------------------
# Domain dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Domain:
    """A Cleric domain granting bonus spells and a special granted power.

    Attributes:
        name:           Domain name (e.g. ``"Healing"``).
        domain_spells:  Mapping of spell level (1–9) to spell name.
        granted_power:  Text description of the domain's granted power.
        power_callback: Optional callable implementing the granted power;
                        called with (character, level) and returns a dict
                        of effect parameters.
    """

    name: str
    domain_spells: Dict[int, str]
    granted_power: str
    power_callback: Optional[Callable] = field(default=None, compare=False)


# ---------------------------------------------------------------------------
# Domain registry
# ---------------------------------------------------------------------------

class DomainRegistry:
    """Registry of canonical 3.5e SRD Cleric domains.

    Use :meth:`get` to retrieve a domain by name.  Use :meth:`all_names` to
    enumerate available domains.
    """

    _domains: Dict[str, Domain] = {}
    _built: bool = False

    @classmethod
    def _build(cls) -> None:
        """Populate the registry with canonical SRD domains."""
        if cls._built:
            return

        def _healing_power(character: object, level: int) -> Dict:
            return {
                "caster_level_bonus": 1,
                "applies_to": "healing spells",
                "description": "Cast healing spells at +1 caster level.",
            }

        def _protection_power(character: object, level: int) -> Dict:
            return {
                "resistance_bonus": 1,
                "applies_to": "saving throws",
                "description": "+1 resistance bonus on saving throws.",
            }

        def _strength_power(character: object, level: int) -> Dict:
            return {
                "str_bonus": level,
                "duration_rounds": 1,
                "uses_per_day": 1,
                "description": f"Add {level} to STR for 1 round, 1/day.",
            }

        def _war_power(character: object, level: int) -> Dict:
            return {
                "proficiency": "deity_favored_weapon",
                "weapon_focus": True,
                "description": "Free Martial Weapon Proficiency and Weapon Focus in deity's favored weapon.",
            }

        def _destruction_power(character: object, level: int) -> Dict:
            return {
                "smite_bonus_damage": level,
                "uses_per_day": 1,
                "description": f"Smite: +{level} damage on one melee attack, 1/day.",
            }

        def _death_power(character: object, level: int) -> Dict:
            return {
                "death_touch": True,
                "uses_per_day": 1,
                "description": "Death Touch: once/day, melee touch attack that deals 1d6/level damage.",
            }

        def _luck_power(character: object, level: int) -> Dict:
            return {
                "reroll": True,
                "uses_per_day": 1,
                "description": "Reroll any one roll per day; keep the second result.",
            }

        def _trickery_power(character: object, level: int) -> Dict:
            return {
                "bonus_class_skills": ["Bluff", "Disguise", "Hide"],
                "description": "Bluff, Disguise, and Hide become Cleric class skills.",
            }

        def _knowledge_power(character: object, level: int) -> Dict:
            return {
                "bonus_class_skills": "all_knowledge",
                "divination_caster_level_bonus": 1,
                "description": "All Knowledge skills are class skills; cast divinations at +1 CL.",
            }

        def _travel_power(character: object, level: int) -> Dict:
            return {
                "freedom_of_movement_rounds": level,
                "uses_per_day": 1,
                "description": f"Freedom of Movement for {level} rounds/day (1 round at a time).",
            }

        domains = [
            Domain(
                name="Healing",
                domain_spells={
                    1: "Cure Light Wounds",
                    2: "Cure Moderate Wounds",
                    3: "Cure Serious Wounds",
                    4: "Cure Critical Wounds",
                    5: "Heal",
                    6: "Heal",
                    7: "Regenerate",
                    8: "Mass Cure Critical Wounds",
                    9: "Mass Heal",
                },
                granted_power="Casts healing spells at +1 caster level.",
                power_callback=_healing_power,
            ),
            Domain(
                name="Protection",
                domain_spells={
                    1: "Sanctuary",
                    2: "Shield Other",
                    3: "Protection from Energy",
                    4: "Spell Immunity",
                    5: "Spell Resistance",
                    6: "Antimagic Field",
                    7: "Repulsion",
                    8: "Mind Blank",
                    9: "Prismatic Sphere",
                },
                granted_power=(
                    "Generate a protective ward granting a +1 resistance bonus on "
                    "one saving throw as a standard action, 1/day per cleric level."
                ),
                power_callback=_protection_power,
            ),
            Domain(
                name="Strength",
                domain_spells={
                    1: "Enlarge Person",
                    2: "Bull's Strength",
                    3: "Magic Vestment",
                    4: "Spell Immunity",
                    5: "Righteous Might",
                    6: "Stoneskin",
                    7: "Grasping Hand",
                    8: "Clenched Fist",
                    9: "Crushing Hand",
                },
                granted_power="Add cleric level as an enhancement bonus to STR for 1 round, 1/day.",
                power_callback=_strength_power,
            ),
            Domain(
                name="War",
                domain_spells={
                    1: "Magic Weapon",
                    2: "Spiritual Weapon",
                    3: "Magic Vestment",
                    4: "Divine Power",
                    5: "Flame Strike",
                    6: "Blade Barrier",
                    7: "Power Word Blind",
                    8: "Power Word Stun",
                    9: "Power Word Kill",
                },
                granted_power=(
                    "Free Martial Weapon Proficiency and Weapon Focus feats for "
                    "the deity's favored weapon."
                ),
                power_callback=_war_power,
            ),
            Domain(
                name="Destruction",
                domain_spells={
                    1: "Inflict Light Wounds",
                    2: "Shatter",
                    3: "Contagion",
                    4: "Inflict Critical Wounds",
                    5: "Mass Inflict Light Wounds",
                    6: "Harm",
                    7: "Disintegrate",
                    8: "Earthquake",
                    9: "Implosion",
                },
                granted_power="Smite: +cleric level damage on one melee attack, 1/day.",
                power_callback=_destruction_power,
            ),
            Domain(
                name="Death",
                domain_spells={
                    1: "Cause Fear",
                    2: "Death Knell",
                    3: "Animate Dead",
                    4: "Death Ward",
                    5: "Slay Living",
                    6: "Create Undead",
                    7: "Destruction",
                    8: "Create Greater Undead",
                    9: "Wail of the Banshee",
                },
                granted_power="Death Touch: once/day melee touch that deals 1d6/level damage.",
                power_callback=_death_power,
            ),
            Domain(
                name="Luck",
                domain_spells={
                    1: "Entropic Shield",
                    2: "Aid",
                    3: "Protection from Energy",
                    4: "Freedom of Movement",
                    5: "Break Enchantment",
                    6: "Mislead",
                    7: "Spell Turning",
                    8: "Moment of Prescience",
                    9: "Miracle",
                },
                granted_power="Reroll any one die roll per day; keep the second result.",
                power_callback=_luck_power,
            ),
            Domain(
                name="Trickery",
                domain_spells={
                    1: "Disguise Self",
                    2: "Invisibility",
                    3: "Nondetection",
                    4: "Confusion",
                    5: "False Vision",
                    6: "Mislead",
                    7: "Screen",
                    8: "Polymorph Any Object",
                    9: "Time Stop",
                },
                granted_power="Bluff, Disguise, and Hide become Cleric class skills.",
                power_callback=_trickery_power,
            ),
            Domain(
                name="Knowledge",
                domain_spells={
                    1: "Detect Secret Doors",
                    2: "Detect Thoughts",
                    3: "Clairvoyance",
                    4: "Divination",
                    5: "True Seeing",
                    6: "Find the Path",
                    7: "Legend Lore",
                    8: "Discern Location",
                    9: "Foresight",
                },
                granted_power="All Knowledge skills are class skills; cast divinations at +1 CL.",
                power_callback=_knowledge_power,
            ),
            Domain(
                name="Travel",
                domain_spells={
                    1: "Longstrider",
                    2: "Locate Object",
                    3: "Fly",
                    4: "Dimension Door",
                    5: "Teleport",
                    6: "Find the Path",
                    7: "Teleport, Greater",
                    8: "Phase Door",
                    9: "Astral Projection",
                },
                granted_power="Freedom of Movement for 1 round/cleric level per day (as free action).",
                power_callback=_travel_power,
            ),
        ]

        for domain in domains:
            cls._domains[domain.name] = domain
        cls._built = True

    @classmethod
    def get(cls, name: str) -> Domain:
        """Return the :class:`Domain` with the given name.

        Args:
            name: Domain name (e.g. ``"Healing"``).

        Returns:
            The matching :class:`Domain`.

        Raises:
            KeyError: If no domain with that name is registered.
        """
        cls._build()
        if name not in cls._domains:
            raise KeyError(f"Unknown domain: {name!r}")
        return cls._domains[name]

    @classmethod
    def all_names(cls) -> List[str]:
        """Return a sorted list of all registered domain names."""
        cls._build()
        return sorted(cls._domains)

    @classmethod
    def all(cls) -> List[Domain]:
        """Return all registered domains (sorted by name)."""
        cls._build()
        return [cls._domains[n] for n in sorted(cls._domains)]


# ---------------------------------------------------------------------------
# Deity dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Deity:
    """A deity definition following the 3.5e SRD.

    Attributes:
        name:           Deity name (e.g. ``"Pelor"``).
        alignment:      Two-letter alignment code (e.g. ``"NG"``).
        portfolio:      List of domains/themes this deity governs.
        domains:        List of domain names available to Clerics of this deity.
        favored_weapon: Name of the deity's favored weapon.
        description:    Short lore description.
    """

    name: str
    alignment: str
    portfolio: List[str]
    domains: List[str]
    favored_weapon: str
    description: str = ""


# ---------------------------------------------------------------------------
# Deity registry
# ---------------------------------------------------------------------------

class DeityRegistry:
    """Registry of canonical 3.5e SRD deities.

    Use :meth:`get` to retrieve a deity by name.  Use :meth:`all_names` to
    enumerate available deities.
    """

    _deities: Dict[str, Deity] = {}
    _built: bool = False

    @classmethod
    def _build(cls) -> None:
        """Populate the registry with canonical SRD deities."""
        if cls._built:
            return

        deities = [
            Deity(
                name="Pelor",
                alignment="NG",
                portfolio=["Sun", "Light", "Strength", "Healing"],
                domains=["Good", "Healing", "Strength", "Sun"],
                favored_weapon="Heavy Mace",
                description="God of the Sun and healer of the afflicted.",
            ),
            Deity(
                name="Heironeous",
                alignment="LG",
                portfolio=["Chivalry", "Honor", "Justice", "War"],
                domains=["Good", "Healing", "Law", "War"],
                favored_weapon="Longsword",
                description="The Invincible; god of chivalry and valor.",
            ),
            Deity(
                name="Moradin",
                alignment="LG",
                portfolio=["Dwarves", "Creation", "Smithing", "Protection"],
                domains=["Earth", "Good", "Law", "Protection"],
                favored_weapon="Warhammer",
                description="Soul Forger; god of dwarves and creation.",
            ),
            Deity(
                name="Corellon Larethian",
                alignment="CG",
                portfolio=["Elves", "Magic", "Music", "War"],
                domains=["Chaos", "Good", "Protection", "War"],
                favored_weapon="Longsword",
                description="Creator of the elves; patron of art and magic.",
            ),
            Deity(
                name="Yondalla",
                alignment="LG",
                portfolio=["Halflings", "Protection", "Fertility"],
                domains=["Good", "Halfling", "Law", "Protection"],
                favored_weapon="Short Sword",
                description="Provider and protector; goddess of halflings.",
            ),
            Deity(
                name="Boccob",
                alignment="N",
                portfolio=["Magic", "Arcane Knowledge", "Balance", "Foresight"],
                domains=["Knowledge", "Magic", "Trickery"],
                favored_weapon="Quarterstaff",
                description="The Uncaring; god of magic and arcane knowledge.",
            ),
            Deity(
                name="Obad-Hai",
                alignment="N",
                portfolio=["Nature", "Wildlands", "Freedom", "Hunting"],
                domains=["Air", "Animal", "Earth", "Fire", "Plant", "Water"],
                favored_weapon="Quarterstaff",
                description="Master of nature, patron of druids.",
            ),
            Deity(
                name="Fharlanghn",
                alignment="N",
                portfolio=["Horizons", "Travel", "Roads", "Distance"],
                domains=["Luck", "Protection", "Travel"],
                favored_weapon="Quarterstaff",
                description="Dweller on the Horizon; god of travel.",
            ),
            Deity(
                name="Hextor",
                alignment="LE",
                portfolio=["War", "Discord", "Massacres", "Tyranny"],
                domains=["Destruction", "Evil", "Law", "War"],
                favored_weapon="Heavy Flail",
                description="Herald of Hell; god of war and tyranny.",
            ),
            Deity(
                name="Nerull",
                alignment="NE",
                portfolio=["Death", "Darkness", "Murder", "Underworld"],
                domains=["Death", "Evil", "Trickery"],
                favored_weapon="Scythe",
                description="The Reaper; god of death and the underworld.",
            ),
            Deity(
                name="Vecna",
                alignment="NE",
                portfolio=["Destructive Secrets", "Intrigue", "Magic", "Undead"],
                domains=["Death", "Evil", "Knowledge", "Magic"],
                favored_weapon="Dagger",
                description="The Whispered One; god of destructive secrets.",
            ),
            Deity(
                name="Erythnul",
                alignment="CE",
                portfolio=["Hate", "Envy", "Malice", "Panic", "Ugliness", "Slaughter"],
                domains=["Chaos", "Evil", "Trickery", "War"],
                favored_weapon="Morningstar",
                description="The Many; god of slaughter and strife.",
            ),
        ]

        for deity in deities:
            cls._deities[deity.name] = deity
        cls._built = True

    @classmethod
    def get(cls, name: str) -> Deity:
        """Return the :class:`Deity` with the given name.

        Args:
            name: Deity name (e.g. ``"Pelor"``).

        Returns:
            The matching :class:`Deity`.

        Raises:
            KeyError: If no deity with that name is registered.
        """
        cls._build()
        if name not in cls._deities:
            raise KeyError(f"Unknown deity: {name!r}")
        return cls._deities[name]

    @classmethod
    def all_names(cls) -> List[str]:
        """Return a sorted list of all registered deity names."""
        cls._build()
        return sorted(cls._deities)

    @classmethod
    def all(cls) -> List[Deity]:
        """Return all registered deities (sorted by name)."""
        cls._build()
        return [cls._deities[n] for n in sorted(cls._deities)]
