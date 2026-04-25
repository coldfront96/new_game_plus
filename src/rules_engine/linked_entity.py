"""
src/rules_engine/linked_entity.py
----------------------------------
D&D 3.5e linked entity subsystem — familiars, animal companions, and
paladin special mounts.

Implements tasks E-003 through E-057 (Tiers 0-4):

* Schemas     (E-003 – E-006)
* Progression (E-021 – E-023)
* Registries  (E-036 – E-038)
* Engines     (E-048 – E-050)
* Turn tracker / share-spells (E-056 – E-057)
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


# ---------------------------------------------------------------------------
# E-003  Master/Minion Link Schema
# ---------------------------------------------------------------------------

class LinkType(Enum):
    Familiar = auto()
    AnimalCompanion = auto()
    SpecialMount = auto()
    Cohort = auto()


@dataclass(slots=True)
class MasterMinionLink:
    master_id: str
    minion_id: str
    link_type: LinkType
    share_spells: bool
    empathic_link: bool
    delivery_touch: bool
    scry_on_familiar: bool


# ---------------------------------------------------------------------------
# E-004  Familiar Base Schema
# ---------------------------------------------------------------------------

class FamiliarSpecies(Enum):
    Bat = auto()
    Cat = auto()
    Hawk = auto()
    Lizard = auto()
    Owl = auto()
    Rat = auto()
    Raven = auto()
    Snake_Tiny_Viper = auto()
    Toad = auto()
    Weasel = auto()


@dataclass(slots=True)
class FamiliarBase:
    species: str           # FamiliarSpecies.name
    master_class_levels: int
    natural_armor_bonus: int
    int_score: int
    special_master_bonus: str   # e.g. "+3 to Listen checks"


# ---------------------------------------------------------------------------
# E-005  Animal Companion Base Schema
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class AnimalCompanionBase:
    species: str
    base_cr: float
    effective_druid_level: int   # minimum druid level offset (0 = standard list)
    bonus_hd: int
    natural_armor_adj: int
    str_dex_adj: int
    bonus_tricks: int
    link_active: bool
    share_spells: bool
    evasion: bool
    devotion: bool
    multiattack: bool
    improved_evasion: bool


# ---------------------------------------------------------------------------
# E-006  Paladin Special Mount Base Schema
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class SpecialMountBase:
    species: str                  # "heavy_warhorse" or "warpony"
    bonus_hd: int
    natural_armor_adj: int
    str_adj: int
    int_score: int
    empathic_link: bool
    improved_evasion: bool
    share_spells: bool
    share_saving_throws: bool
    command: bool
    spell_resistance: int
    daily_summons_remaining: int = 1


# ---------------------------------------------------------------------------
# E-021  Familiar Intelligence Progression
# ---------------------------------------------------------------------------

# PHB table: pairs of (min_level, int_score)
_FAMILIAR_INT_TABLE: list[tuple[int, int]] = [
    (1,  6), (3,  7), (5,  8), (7,  9), (9,  10),
    (11, 11), (13, 12), (15, 13), (17, 14), (19, 15),
]


def familiar_int_score(master_class_levels: int) -> int:
    """Return familiar Intelligence score per PHB table.

    Levels 1-2→6, 3-4→7, 5-6→8, 7-8→9, 9-10→10,
    11-12→11, 13-14→12, 15-16→13, 17-18→14, 19-20→15.
    Clamps input to [1, 20].
    """
    lvl = max(1, min(20, master_class_levels))
    result = 6
    for min_lvl, score in _FAMILIAR_INT_TABLE:
        if lvl >= min_lvl:
            result = score
        else:
            break
    return result


def familiar_natural_armor_bonus(master_class_levels: int) -> int:
    """Return natural armor bonus: 1 + (master_class_levels // 2).

    Capped at 11 (level 20 → 11).
    """
    lvl = max(1, min(20, master_class_levels))
    return 1 + (lvl // 2)


# ---------------------------------------------------------------------------
# E-022  Animal Companion Progression Formula
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class AnimalCompanionProgression:
    bonus_hd: int
    natural_armor_adj: int
    str_dex_adj: int
    bonus_tricks: int
    link: bool
    share_spells: bool
    evasion: bool
    devotion: bool
    multiattack: bool
    improved_evasion: bool


# PHB Druid Animal Companion progression table.
# Each row: (min_druid_level, bonus_hd, natural_armor_adj, str_dex_adj, bonus_tricks,
#             link, share_spells, evasion, devotion, multiattack, improved_evasion)
_AC_PROGRESSION: list[tuple[int, int, int, int, int, bool, bool, bool, bool, bool, bool]] = [
    (1,  0,  0, 0, 1, True,  True,  False, False, False, False),
    (2,  0,  0, 0, 1, True,  True,  True,  False, False, False),
    (3,  2,  2, 1, 2, True,  True,  True,  False, False, False),
    (6,  4,  4, 2, 3, True,  True,  True,  True,  False, False),
    (9,  6,  6, 3, 4, True,  True,  True,  True,  True,  False),
    (12, 8,  8, 4, 5, True,  True,  True,  True,  True,  False),
    (15, 10, 10, 5, 6, True,  True,  True,  True,  True,  True),
    (18, 12, 12, 6, 7, True,  True,  True,  True,  True,  True),
]


def animal_companion_progression(druid_level: int) -> AnimalCompanionProgression:
    """Return animal companion progression for given effective druid level.

    Uses PHB Druid Animal Companion table; druid_level < 1 returns level-1 values.
    """
    lvl = max(1, druid_level)
    row = _AC_PROGRESSION[0]
    for entry in _AC_PROGRESSION:
        if lvl >= entry[0]:
            row = entry
        else:
            break
    _, bonus_hd, na_adj, sd_adj, tricks, link, share, evasion, devotion, multi, imp_ev = row
    return AnimalCompanionProgression(
        bonus_hd=bonus_hd,
        natural_armor_adj=na_adj,
        str_dex_adj=sd_adj,
        bonus_tricks=tricks,
        link=link,
        share_spells=share,
        evasion=evasion,
        devotion=devotion,
        multiattack=multi,
        improved_evasion=imp_ev,
    )


# ---------------------------------------------------------------------------
# E-023  Paladin Mount Progression Formula
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class SpecialMountProgression:
    bonus_hd: int
    natural_armor_adj: int
    str_adj: int
    int_score: int
    empathic_link: bool
    improved_evasion: bool
    share_spells: bool
    share_saving_throws: bool
    command: bool
    spell_resistance: int   # 0 if none


# PHB Paladin Special Mount table rows:
# (min_level, bonus_hd, natural_armor_adj, str_adj, int_score, command, sr_offset)
# sr_offset: if > 0, SR = paladin_level + sr_offset  (5 per PHB)
_MOUNT_PROGRESSION: list[tuple[int, int, int, int, int, bool, int]] = [
    (5,  2, 4,  1, 6, False, 0),
    (8,  4, 6,  2, 7, True,  0),
    (11, 6, 8,  3, 8, True,  5),
    (15, 8, 10, 4, 9, True,  5),
]


def paladin_mount_progression(paladin_level: int) -> SpecialMountProgression:
    """Return paladin special mount progression per PHB table.

    Raises ValueError if paladin_level < 5 (mount not yet available).
    """
    if paladin_level < 5:
        raise ValueError(
            f"Paladin level {paladin_level} is too low; special mount requires level 5."
        )
    row = _MOUNT_PROGRESSION[0]
    for entry in _MOUNT_PROGRESSION:
        if paladin_level >= entry[0]:
            row = entry
        else:
            break
    _, bonus_hd, na_adj, str_adj, int_score, command, sr_offset = row
    sr = (paladin_level + sr_offset) if sr_offset else 0
    return SpecialMountProgression(
        bonus_hd=bonus_hd,
        natural_armor_adj=na_adj,
        str_adj=str_adj,
        int_score=int_score,
        empathic_link=True,
        improved_evasion=True,
        share_spells=True,
        share_saving_throws=True,
        command=command,
        spell_resistance=sr,
    )


# ---------------------------------------------------------------------------
# E-036  PHB Familiar Registry
# ---------------------------------------------------------------------------

FAMILIAR_REGISTRY: dict[FamiliarSpecies, FamiliarBase] = {
    FamiliarSpecies.Bat: FamiliarBase(
        species="Bat", master_class_levels=0, natural_armor_bonus=2,
        int_score=6, special_master_bonus="+3 bonus on Listen checks",
    ),
    FamiliarSpecies.Cat: FamiliarBase(
        species="Cat", master_class_levels=0, natural_armor_bonus=2,
        int_score=6, special_master_bonus="+3 bonus on Move Silently checks",
    ),
    FamiliarSpecies.Hawk: FamiliarBase(
        species="Hawk", master_class_levels=0, natural_armor_bonus=2,
        int_score=6, special_master_bonus="+3 bonus on Spot checks in bright light",
    ),
    FamiliarSpecies.Lizard: FamiliarBase(
        species="Lizard", master_class_levels=0, natural_armor_bonus=2,
        int_score=6, special_master_bonus="+3 bonus on Climb checks",
    ),
    FamiliarSpecies.Owl: FamiliarBase(
        species="Owl", master_class_levels=0, natural_armor_bonus=2,
        int_score=6, special_master_bonus="+3 bonus on Spot checks in shadowy illumination",
    ),
    FamiliarSpecies.Rat: FamiliarBase(
        species="Rat", master_class_levels=0, natural_armor_bonus=2,
        int_score=6, special_master_bonus="+2 bonus on Fortitude saves",
    ),
    FamiliarSpecies.Raven: FamiliarBase(
        species="Raven", master_class_levels=0, natural_armor_bonus=2,
        int_score=6, special_master_bonus="Master gains ability of speech",
    ),
    FamiliarSpecies.Snake_Tiny_Viper: FamiliarBase(
        species="Snake_Tiny_Viper", master_class_levels=0, natural_armor_bonus=2,
        int_score=6, special_master_bonus="+3 bonus on Bluff checks",
    ),
    FamiliarSpecies.Toad: FamiliarBase(
        species="Toad", master_class_levels=0, natural_armor_bonus=2,
        int_score=6, special_master_bonus="+3 hit points",
    ),
    FamiliarSpecies.Weasel: FamiliarBase(
        species="Weasel", master_class_levels=0, natural_armor_bonus=2,
        int_score=6, special_master_bonus="+2 bonus on Reflex saves",
    ),
}


# ---------------------------------------------------------------------------
# E-037  Druid Animal Companion Registry
# ---------------------------------------------------------------------------

def _ac(species: str, cr: float, edl: int) -> AnimalCompanionBase:
    """Helper to create an unmodified AnimalCompanionBase registry entry."""
    return AnimalCompanionBase(
        species=species,
        base_cr=cr,
        effective_druid_level=edl,
        bonus_hd=0,
        natural_armor_adj=0,
        str_dex_adj=0,
        bonus_tricks=1,
        link_active=True,
        share_spells=True,
        evasion=False,
        devotion=False,
        multiattack=False,
        improved_evasion=False,
    )


ANIMAL_COMPANION_REGISTRY: dict[str, AnimalCompanionBase] = {
    # Standard list — effective_druid_level = 0
    "Badger":              _ac("Badger",              0.5, 0),
    "Camel":               _ac("Camel",               1.0, 0),
    "Dire Rat":            _ac("Dire Rat",             1/3, 0),
    "Dog":                 _ac("Dog",                  1/3, 0),
    "Riding Dog":          _ac("Riding Dog",           1.0, 0),
    "Eagle":               _ac("Eagle",                0.5, 0),
    "Hawk":                _ac("Hawk",                 1/3, 0),
    "Light Horse":         _ac("Light Horse",          1.0, 0),
    "Heavy Horse":         _ac("Heavy Horse",          2.0, 0),
    "Owl":                 _ac("Owl",                  1/4, 0),
    "Pony":                _ac("Pony",                 0.5, 0),
    "Small Viper Snake":   _ac("Small Viper Snake",    1/3, 0),
    "Medium Viper Snake":  _ac("Medium Viper Snake",   0.5, 0),
    "Constrictor Snake":   _ac("Constrictor Snake",    2.0, 0),
    "Wolf":                _ac("Wolf",                 2.0, 0),
    # 4th-level list — effective_druid_level = 3
    "Ape":                 _ac("Ape",                  2.0, 3),
    "Black Bear":          _ac("Black Bear",           2.0, 3),
    "Bison":               _ac("Bison",                2.0, 3),
    "Boar":                _ac("Boar",                 2.0, 3),
    "Cheetah":             _ac("Cheetah",              2.0, 3),
    "Crocodile":           _ac("Crocodile",            2.0, 3),
    "Dire Badger":         _ac("Dire Badger",          2.0, 3),
    "Dire Bat":            _ac("Dire Bat",             2.0, 3),
    "Dire Weasel":         _ac("Dire Weasel",          2.0, 3),
    "Leopard":             _ac("Leopard",              2.0, 3),
    "Large Viper Snake":   _ac("Large Viper Snake",    2.0, 3),
    "Wolverine":           _ac("Wolverine",            2.0, 3),
    # 7th-level list — effective_druid_level = 6
    "Brown Bear":          _ac("Brown Bear",           4.0, 6),
    "Dire Wolf":           _ac("Dire Wolf",            3.0, 6),
    "Dire Wolverine":      _ac("Dire Wolverine",       4.0, 6),
    "Lion":                _ac("Lion",                 3.0, 6),
    "Rhinoceros":          _ac("Rhinoceros",           4.0, 6),
    "Tiger":               _ac("Tiger",                4.0, 6),
    # 10th-level list — effective_druid_level = 9
    "Dire Ape":            _ac("Dire Ape",             7.0, 9),
    "Dire Boar":           _ac("Dire Boar",            4.0, 9),
    "Dire Lion":           _ac("Dire Lion",            5.0, 9),
    "Giant Constrictor Snake": _ac("Giant Constrictor Snake", 5.0, 9),
    "Megaraptor":          _ac("Megaraptor",           6.0, 9),
    "Polar Bear":          _ac("Polar Bear",           4.0, 9),
    "Elephant":            _ac("Elephant",             7.0, 9),
    "Giant Crocodile":     _ac("Giant Crocodile",      4.0, 9),
    # 13th-level list — effective_druid_level = 12
    "Dire Bear":           _ac("Dire Bear",            7.0, 12),
    "Dire Tiger":          _ac("Dire Tiger",           8.0, 12),
    "Triceratops":         _ac("Triceratops",          9.0, 12),
    "Tyrannosaurus":       _ac("Tyrannosaurus",        8.0, 12),
    # 16th-level list — effective_druid_level = 15
    "Purple Worm":         _ac("Purple Worm",          12.0, 15),
}


# ---------------------------------------------------------------------------
# E-038  Paladin Mount Stat Block Registry
# ---------------------------------------------------------------------------

PALADIN_MOUNT_REGISTRY: dict[str, SpecialMountBase] = {
    "heavy_warhorse": SpecialMountBase(
        species="heavy_warhorse",
        bonus_hd=2, natural_armor_adj=4, str_adj=1, int_score=6,
        empathic_link=True, improved_evasion=True,
        share_spells=True, share_saving_throws=True,
        command=False, spell_resistance=0,
    ),
    "warpony": SpecialMountBase(
        species="warpony",
        bonus_hd=2, natural_armor_adj=4, str_adj=1, int_score=6,
        empathic_link=True, improved_evasion=True,
        share_spells=True, share_saving_throws=True,
        command=False, spell_resistance=0,
    ),
}


# ---------------------------------------------------------------------------
# E-048  Familiar Acquisition Engine
# ---------------------------------------------------------------------------

_FAMILIAR_CASTER_CLASSES = {"Sorcerer", "Wizard", "sorcerer", "wizard"}


class FamiliarError(Exception):
    """Raised when familiar acquisition prerequisites are not met."""


def acquire_familiar(
    master_id: str,
    master_char_class: str,
    master_level: int,
    master_feats: list[str],
    species: FamiliarSpecies,
    gold_available: float,
) -> tuple[MasterMinionLink, FamiliarBase]:
    """Acquire a familiar for a Sorcerer or Wizard (or Improved Familiar holder).

    Gates:
    * caster class must be Sorcerer/Wizard *or* master must have
      'Improved Familiar' feat for non-standard familiars.
    * Cost: 100 gp × master_level.

    Returns:
        (MasterMinionLink, FamiliarBase) with updated int_score and
        natural_armor_bonus reflecting master_level.

    Raises:
        FamiliarError: if prerequisites fail or gold is insufficient.
    """
    is_caster = master_char_class in _FAMILIAR_CASTER_CLASSES
    has_improved = "Improved Familiar" in master_feats

    if not is_caster and not has_improved:
        raise FamiliarError(
            f"Class '{master_char_class}' cannot obtain a familiar "
            "without the Improved Familiar feat."
        )

    if species not in FAMILIAR_REGISTRY:
        raise FamiliarError(f"Species {species!r} not in familiar registry.")

    cost = 100.0 * master_level
    if gold_available < cost:
        raise FamiliarError(
            f"Insufficient gold: need {cost:.1f} gp, have {gold_available:.1f} gp."
        )

    base = FAMILIAR_REGISTRY[species]
    updated = FamiliarBase(
        species=base.species,
        master_class_levels=master_level,
        natural_armor_bonus=familiar_natural_armor_bonus(master_level),
        int_score=familiar_int_score(master_level),
        special_master_bonus=base.special_master_bonus,
    )

    link = MasterMinionLink(
        master_id=master_id,
        minion_id=f"familiar_{base.species.lower()}_{master_id}",
        link_type=LinkType.Familiar,
        share_spells=True,
        empathic_link=True,
        delivery_touch=True,
        scry_on_familiar=master_level >= 13,
    )
    return link, updated


# ---------------------------------------------------------------------------
# E-049  Animal Companion Acquisition Engine
# ---------------------------------------------------------------------------

class CompanionError(Exception):
    """Raised when animal companion acquisition prerequisites are not met."""


def acquire_animal_companion(
    druid_id: str,
    druid_level: int,
    species: str,
) -> tuple[MasterMinionLink, AnimalCompanionBase]:
    """Acquire an animal companion for a druid.

    Validates that druid_level >= companion.effective_druid_level,
    then applies animal_companion_progression using the *effective* druid
    level (druid_level - companion.effective_druid_level).

    Returns:
        (MasterMinionLink, updated AnimalCompanionBase)

    Raises:
        CompanionError: if species not in registry or level insufficient.
    """
    if species not in ANIMAL_COMPANION_REGISTRY:
        raise CompanionError(f"Species '{species}' not in animal companion registry.")

    base = ANIMAL_COMPANION_REGISTRY[species]
    if druid_level < base.effective_druid_level:
        raise CompanionError(
            f"Druid level {druid_level} is too low for '{species}'; "
            f"requires effective druid level {base.effective_druid_level}."
        )

    prog = animal_companion_progression(druid_level - base.effective_druid_level)

    updated = AnimalCompanionBase(
        species=base.species,
        base_cr=base.base_cr,
        effective_druid_level=base.effective_druid_level,
        bonus_hd=prog.bonus_hd,
        natural_armor_adj=prog.natural_armor_adj,
        str_dex_adj=prog.str_dex_adj,
        bonus_tricks=prog.bonus_tricks,
        link_active=prog.link,
        share_spells=prog.share_spells,
        evasion=prog.evasion,
        devotion=prog.devotion,
        multiattack=prog.multiattack,
        improved_evasion=prog.improved_evasion,
    )

    link = MasterMinionLink(
        master_id=druid_id,
        minion_id=f"companion_{species.lower().replace(' ', '_')}_{druid_id}",
        link_type=LinkType.AnimalCompanion,
        share_spells=prog.share_spells,
        empathic_link=prog.link,
        delivery_touch=False,
        scry_on_familiar=False,
    )
    return link, updated


# ---------------------------------------------------------------------------
# E-050  Paladin Special Mount Summoning Engine
# ---------------------------------------------------------------------------

class MountError(Exception):
    """Raised when special mount summoning prerequisites are not met."""


def summon_special_mount(
    paladin_id: str,
    paladin_level: int,
    mount_species: str = "heavy_warhorse",
) -> tuple[MasterMinionLink, SpecialMountBase]:
    """Summon a paladin's special mount.

    Enforces paladin_level >= 5 and applies paladin_mount_progression().

    Returns:
        (MasterMinionLink, updated SpecialMountBase)

    Raises:
        MountError: if paladin_level < 5 or species not in registry.
    """
    if paladin_level < 5:
        raise MountError(
            f"Paladin level {paladin_level} is too low; special mount requires level 5."
        )
    if mount_species not in PALADIN_MOUNT_REGISTRY:
        raise MountError(
            f"Mount species '{mount_species}' not in paladin mount registry."
        )

    try:
        prog = paladin_mount_progression(paladin_level)
    except ValueError as exc:
        raise MountError(str(exc)) from exc

    base = PALADIN_MOUNT_REGISTRY[mount_species]
    updated = SpecialMountBase(
        species=base.species,
        bonus_hd=prog.bonus_hd,
        natural_armor_adj=prog.natural_armor_adj,
        str_adj=prog.str_adj,
        int_score=prog.int_score,
        empathic_link=prog.empathic_link,
        improved_evasion=prog.improved_evasion,
        share_spells=prog.share_spells,
        share_saving_throws=prog.share_saving_throws,
        command=prog.command,
        spell_resistance=prog.spell_resistance,
        daily_summons_remaining=base.daily_summons_remaining,
    )

    link = MasterMinionLink(
        master_id=paladin_id,
        minion_id=f"mount_{mount_species}_{paladin_id}",
        link_type=LinkType.SpecialMount,
        share_spells=prog.share_spells,
        empathic_link=prog.empathic_link,
        delivery_touch=False,
        scry_on_familiar=False,
    )
    return link, updated


# ---------------------------------------------------------------------------
# E-056  Master/Minion Turn Tracker
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class MasterMinionTurnTracker:
    """Tracks initiative and action economy for master/minion pairs."""

    links: list[MasterMinionLink]
    initiative_map: dict[str, int]   # entity_id -> initiative roll

    def roll_initiative_for_link(
        self, link: MasterMinionLink, rng: Any
    ) -> tuple[int, int]:
        """Roll d20 for master and minion independently.

        Args:
            link: The MasterMinionLink to roll for.
            rng:  Object with a ``randint(a, b)`` method (e.g. ``random``).

        Returns:
            (master_initiative, minion_initiative)
        """
        master_init = rng.randint(1, 20)
        minion_init = rng.randint(1, 20)
        self.initiative_map[link.master_id] = master_init
        self.initiative_map[link.minion_id] = minion_init
        return master_init, minion_init

    def synchronise_actions(self, round_state: dict) -> dict:
        """Return updated round_state with command costs noted.

        Commanding a minion costs the master a Move action; this is
        recorded in round_state under the key
        ``"move_action_spent"`` as a set of master IDs.
        """
        updated = dict(round_state)
        spent: set[str] = set(updated.get("move_action_spent", set()))
        for link in self.links:
            spent.add(link.master_id)
        updated["move_action_spent"] = spent
        return updated


# ---------------------------------------------------------------------------
# E-057  Familiar Share Spells & Empathic Link
# ---------------------------------------------------------------------------

_PERSONAL_RANGES = {"Personal", "Self", "personal", "self"}


@dataclass(slots=True)
class ShareResult:
    allowed: bool
    reason: str


def share_spell(
    link: MasterMinionLink,
    spell_name: str,
    spell_range: str,
    distance_ft: float,
) -> ShareResult:
    """Determine whether a spell may be shared with the familiar.

    Conditions (all must hold):
    * link.share_spells is True
    * spell_range is 'Personal' or 'Self'
    * distance_ft <= 5.0

    Returns:
        ShareResult with allowed flag and descriptive reason.
    """
    if not link.share_spells:
        return ShareResult(False, f"Link does not permit share spells for '{spell_name}'.")
    if spell_range not in _PERSONAL_RANGES:
        return ShareResult(
            False,
            f"Spell '{spell_name}' has range '{spell_range}'; only Personal/Self may be shared.",
        )
    if distance_ft > 5.0:
        return ShareResult(
            False,
            f"Familiar is {distance_ft:.1f} ft away; must be within 5 ft to share spells.",
        )
    return ShareResult(True, f"Spell '{spell_name}' shared with familiar successfully.")


def empathic_link_message(
    link: MasterMinionLink,
    sense: str,
    distance_miles: float,
) -> str:
    """Propagate a basic emotion/sense via empathic link.

    The link is active when link.empathic_link is True and
    distance_miles <= 1.0 (one mile per PHB).

    Returns:
        Descriptive string about the transmission result.
    """
    if not link.empathic_link:
        return f"No empathic link exists between {link.master_id} and {link.minion_id}."
    if distance_miles > 1.0:
        return (
            f"Distance {distance_miles:.2f} miles exceeds empathic link range (1 mile); "
            f"sense '{sense}' not transmitted."
        )
    return (
        f"Empathic link active: {link.master_id} transmits '{sense}' "
        f"to {link.minion_id} at {distance_miles:.2f} miles."
    )


def donate_hp(
    link: MasterMinionLink,
    master_current_hp: int,
    hp_delta: int,
) -> tuple[int, int]:
    """Transfer HP from master to minion (touch-spell delivery or HP sharing).

    The master loses hp_delta hit points; the actual amount transferred is
    clamped so master HP cannot go below 0.

    Args:
        link:             The active MasterMinionLink.
        master_current_hp: Master's current HP before transfer.
        hp_delta:         Amount of HP to donate (must be >= 0).

    Returns:
        (master_new_hp, amount_transferred)
    """
    if hp_delta < 0:
        raise ValueError("hp_delta must be non-negative.")
    amount = min(hp_delta, master_current_hp)
    return master_current_hp - amount, amount
