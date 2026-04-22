"""
src/rules_engine/character_35e.py
---------------------------------
Base character data class structured around D&D 3.5e SRD rules.

A :class:`Character35e` holds the canonical stat block for any creature
or player character in the 3.5e system.  Ability scores, hit points,
saving throws, base attack bonus, and armour class are all derived from
SRD formulae.

Memory Optimisation
~~~~~~~~~~~~~~~~~~~
Uses ``@dataclass(slots=True)`` to eliminate per-instance ``__dict__``
overhead, critical when the procedural generation layer instantiates
hundreds of NPCs per tick.

Usage::

    from src.rules_engine.character_35e import Character35e, Alignment, Size

    fighter = Character35e(
        name="Aldric",
        char_class="Fighter",
        level=5,
        strength=16,
        dexterity=13,
        constitution=14,
        intelligence=10,
        wisdom=12,
        charisma=8,
    )

    print(fighter)
    print(fighter.strength_mod)   # +3
    print(fighter.hit_points)     # 5d10 + CON-mod × level
    print(fighter.base_attack_bonus)
    print(fighter.armor_class)
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from src.rules_engine.equipment import EquipmentManager
    from src.rules_engine.spellcasting import (
        SpellSlotManager,
        Spellbook,
        SpellsKnownManager,
        SpontaneousCasterManager,
    )


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class Alignment(Enum):
    """The nine D&D 3.5e alignments."""

    LAWFUL_GOOD = "LG"
    NEUTRAL_GOOD = "NG"
    CHAOTIC_GOOD = "CG"
    LAWFUL_NEUTRAL = "LN"
    TRUE_NEUTRAL = "N"
    CHAOTIC_NEUTRAL = "CN"
    LAWFUL_EVIL = "LE"
    NEUTRAL_EVIL = "NE"
    CHAOTIC_EVIL = "CE"


class Size(Enum):
    """Creature size categories from the 3.5e SRD.

    The integer value is the size modifier applied to AC and attack rolls.
    """

    FINE = 8
    DIMINUTIVE = 4
    TINY = 2
    SMALL = 1
    MEDIUM = 0
    LARGE = -1
    HUGE = -2
    GARGANTUAN = -4
    COLOSSAL = -8


# ---------------------------------------------------------------------------
# SRD look-up tables
# ---------------------------------------------------------------------------

# 3.5e SRD armor speed reduction table (medium/heavy armor).
# Maps base speed (ft) → reduced speed (ft) for medium and heavy armor.
_ARMOR_SPEED_TABLE: Dict[int, int] = {
    15: 10,
    20: 15,
    25: 20,
    30: 20,
    35: 25,
    40: 30,
    45: 30,
    50: 35,
    55: 40,
    60: 40,
}


# Hit die by class name (from the 3.5e SRD).
_HIT_DIE: Dict[str, int] = {
    "Barbarian": 12,
    "Bard": 6,
    "Cleric": 8,
    "Druid": 8,
    "Fighter": 10,
    "Monk": 8,
    "Paladin": 10,
    "Ranger": 8,
    "Rogue": 6,
    "Sorcerer": 4,
    "Wizard": 4,
}

# BAB progression type by class: "full", "three_quarter", or "half".
_BAB_PROGRESSION: Dict[str, str] = {
    "Barbarian": "full",
    "Bard": "three_quarter",
    "Cleric": "three_quarter",
    "Druid": "three_quarter",
    "Fighter": "full",
    "Monk": "three_quarter",
    "Paladin": "full",
    "Ranger": "full",
    "Rogue": "three_quarter",
    "Sorcerer": "half",
    "Wizard": "half",
}

# Good saves by class (the rest are poor).
_GOOD_SAVES: Dict[str, List[str]] = {
    "Barbarian": ["fortitude"],
    "Bard": ["reflex", "will"],
    "Cleric": ["fortitude", "will"],
    "Druid": ["fortitude", "will"],
    "Fighter": ["fortitude"],
    "Monk": ["fortitude", "reflex", "will"],
    "Paladin": ["fortitude"],
    "Ranger": ["fortitude", "reflex"],
    "Rogue": ["reflex"],
    "Sorcerer": ["will"],
    "Wizard": ["will"],
}


def _ability_modifier(score: int) -> int:
    """Compute the 3.5e ability modifier: ``(score - 10) // 2``."""
    return (score - 10) // 2


def _bab_for_level(progression: str, level: int) -> int:
    """Return the base attack bonus for a given progression type and level.

    * **Full** (Fighter, etc.): ``+level``
    * **¾** (Cleric, etc.):    ``+level × ¾`` (floored)
    * **½** (Wizard, etc.):    ``+level × ½`` (floored)
    """
    if progression == "full":
        return level
    elif progression == "three_quarter":
        return level * 3 // 4
    else:  # "half"
        return level // 2


def _save_bonus(level: int, is_good: bool) -> int:
    """Compute base save bonus from the SRD progression tables.

    * **Good save**: ``2 + level // 2``
    * **Poor save**: ``level // 3``
    """
    if is_good:
        return 2 + level // 2
    return level // 3


# ---------------------------------------------------------------------------
# Character35e
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Character35e:
    """D&D 3.5e character stat block.

    All derived values (modifiers, HP, BAB, saves, AC) are computed
    from the raw ability scores and class/level using SRD formulae,
    ensuring the game engine never drifts from the official rules.

    Attributes:
        char_id:       Globally unique identifier (UUID4). Auto-generated.
        name:          Character or creature name.
        char_class:    Class name (must match a key in the SRD class tables).
        level:         Character level (1–20 for standard play).
        race:          Race name (e.g. ``"Human"``, ``"Elf"``).
        alignment:     One of the nine 3.5e alignments.
        size:          Creature size category.
        strength:      STR ability score.
        dexterity:     DEX ability score.
        constitution:  CON ability score.
        intelligence:  INT ability score.
        wisdom:        WIS ability score.
        charisma:      CHA ability score.
        base_speed:    Base land speed in feet (default 30 for Medium humanoids).
        equipment:     List of equipment names (simplified).
        feats:         List of feat names.
        skills:        Mapping of skill name → total bonus.
        metadata:      Free-form dictionary for campaign-specific extras.
    """

    name: str
    char_class: str = "Fighter"
    level: int = 1
    char_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    race: str = "Human"
    alignment: Alignment = Alignment.TRUE_NEUTRAL
    size: Size = Size.MEDIUM
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10
    base_speed: int = 30
    equipment: List[str] = field(default_factory=list)
    feats: List[str] = field(default_factory=list)
    skills: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    equipment_manager: Optional["EquipmentManager"] = None
    spell_slot_manager: Optional["SpellSlotManager"] = None
    spellbook: Optional["Spellbook"] = None
    spells_known: Optional["SpellsKnownManager"] = None
    spontaneous_caster: Optional["SpontaneousCasterManager"] = None

    # ------------------------------------------------------------------
    # Ability modifiers (SRD formula: (score - 10) // 2)
    # ------------------------------------------------------------------

    @property
    def strength_mod(self) -> int:
        """Strength modifier."""
        return _ability_modifier(self.strength)

    @property
    def dexterity_mod(self) -> int:
        """Dexterity modifier."""
        return _ability_modifier(self.dexterity)

    @property
    def constitution_mod(self) -> int:
        """Constitution modifier."""
        return _ability_modifier(self.constitution)

    @property
    def intelligence_mod(self) -> int:
        """Intelligence modifier."""
        return _ability_modifier(self.intelligence)

    @property
    def wisdom_mod(self) -> int:
        """Wisdom modifier."""
        return _ability_modifier(self.wisdom)

    @property
    def charisma_mod(self) -> int:
        """Charisma modifier."""
        return _ability_modifier(self.charisma)

    # ------------------------------------------------------------------
    # Movement speed
    # ------------------------------------------------------------------

    @property
    def voxel_speed(self) -> int:
        """Movement speed converted to voxel units (5 ft = 1 block).

        Applies the 3.5e SRD armor speed reduction: medium and heavy armor
        reduce a character's base speed using the standard lookup table
        (e.g. 30 ft → 20 ft in heavy armor).

        Returns:
            Number of blocks the character can traverse per move action.
        """
        speed = self.base_speed
        if self.equipment_manager is not None:
            category = self.equipment_manager.get_armor_category()
            if category in ("medium", "heavy"):
                speed = _ARMOR_SPEED_TABLE.get(speed, max(speed * 2 // 3, 5))
        return speed // 5

    # ------------------------------------------------------------------
    # Hit die & hit points
    # ------------------------------------------------------------------

    @property
    def hit_die(self) -> int:
        """Hit die size for this character's class (e.g. ``10`` for Fighter).

        Falls back to ``8`` for unknown classes.
        """
        return _HIT_DIE.get(self.char_class, 8)

    @property
    def hit_points(self) -> int:
        """Total hit points: ``HD_avg × level + CON-mod × level``.

        Uses the *average* hit die roll ``(HD/2 + 1)`` for deterministic
        stat blocks (standard for NPC generation in the SRD).  A minimum
        of 1 HP per level is enforced.
        """
        avg_roll = self.hit_die // 2 + 1
        hp_per_level = max(1, avg_roll + self.constitution_mod)
        return hp_per_level * self.level

    # ------------------------------------------------------------------
    # Base attack bonus
    # ------------------------------------------------------------------

    @property
    def base_attack_bonus(self) -> int:
        """BAB derived from class progression and level."""
        progression = _BAB_PROGRESSION.get(self.char_class, "three_quarter")
        return _bab_for_level(progression, self.level)

    # ------------------------------------------------------------------
    # Saving throws
    # ------------------------------------------------------------------

    @property
    def fortitude_save(self) -> int:
        """Fortitude save = base + CON modifier."""
        good_saves = _GOOD_SAVES.get(self.char_class, [])
        base = _save_bonus(self.level, "fortitude" in good_saves)
        return base + self.constitution_mod

    @property
    def reflex_save(self) -> int:
        """Reflex save = base + DEX modifier."""
        good_saves = _GOOD_SAVES.get(self.char_class, [])
        base = _save_bonus(self.level, "reflex" in good_saves)
        return base + self.dexterity_mod

    @property
    def will_save(self) -> int:
        """Will save = base + WIS modifier."""
        good_saves = _GOOD_SAVES.get(self.char_class, [])
        base = _save_bonus(self.level, "will" in good_saves)
        return base + self.wisdom_mod

    # ------------------------------------------------------------------
    # Armour class
    # ------------------------------------------------------------------

    @property
    def armor_class(self) -> int:
        """Armour class: ``10 + DEX mod + size modifier + armor bonus + shield bonus + deflection bonus + feat bonus``.

        The Dexterity modifier is capped by the lowest ``max_dex_bonus`` from
        any equipped armor piece, following the 3.5e SRD rule (e.g. Full Plate
        caps DEX bonus at +1).

        Armor bonus and shield bonus are resolved from the
        :class:`EquipmentManager` if one is attached. Deflection bonuses
        (e.g. from divine spells like Shield of Faith) are resolved from
        the character's metadata. Feat bonuses are resolved from the
        :class:`FeatRegistry`.
        """
        from src.rules_engine.feat_engine import FeatRegistry

        dex_mod = self.dexterity_mod
        if self.equipment_manager is not None:
            max_dex = self.equipment_manager.get_min_max_dex_bonus()
            if max_dex is not None:
                dex_mod = min(dex_mod, max_dex)

        ac = 10 + dex_mod + self.size.value
        if self.equipment_manager is not None:
            ac += self.equipment_manager.get_armor_bonus()
            ac += self.equipment_manager.get_shield_bonus()
        # Deflection bonus from divine spells (e.g. Shield of Faith)
        ac += self.metadata.get("deflection_bonus", 0)
        ac += FeatRegistry.get_ac_bonus(self)
        return ac

    @property
    def touch_ac(self) -> int:
        """Touch AC (ignores armour/shield/natural armour)."""
        return 10 + self.dexterity_mod + self.size.value

    @property
    def flat_footed_ac(self) -> int:
        """Flat-footed AC (loses DEX bonus, keeps size modifier)."""
        return 10 + self.size.value

    # ------------------------------------------------------------------
    # Combat
    # ------------------------------------------------------------------

    @property
    def initiative(self) -> int:
        """Initiative modifier: ``DEX mod + feat bonuses``.

        Checks the FeatRegistry for any initiative bonuses granted by
        feats (e.g. Improved Initiative provides +4).
        """
        from src.rules_engine.feat_engine import FeatRegistry

        return self.dexterity_mod + FeatRegistry.get_initiative_bonus(self)

    @property
    def melee_attack(self) -> int:
        """Melee attack bonus: ``BAB + STR mod + size mod + enhancement + feat bonus``."""
        from src.rules_engine.feat_engine import FeatRegistry

        bonus = self.base_attack_bonus + self.strength_mod + self.size.value
        if self.equipment_manager is not None:
            bonus += self.equipment_manager.get_weapon_enhancement_bonus()
        bonus += FeatRegistry.get_attack_bonus(self)
        return bonus

    @property
    def ranged_attack(self) -> int:
        """Ranged attack bonus: ``BAB + DEX mod + size mod + enhancement + feat bonus``."""
        from src.rules_engine.feat_engine import FeatRegistry

        bonus = self.base_attack_bonus + self.dexterity_mod + self.size.value
        if self.equipment_manager is not None:
            bonus += self.equipment_manager.get_weapon_enhancement_bonus()
        bonus += FeatRegistry.get_attack_bonus(self)
        return bonus

    @property
    def grapple(self) -> int:
        """Grapple modifier: ``BAB + STR mod + special_size_mod``.

        Uses the special grapple size modifier (opposite sign of AC size
        modifier).
        """
        return self.base_attack_bonus + self.strength_mod - self.size.value

    # ------------------------------------------------------------------
    # Spellcasting
    # ------------------------------------------------------------------

    def initialize_spellcasting(self) -> None:
        """Initialize spell slot manager and spellbook if this character is
        a caster class (Wizard, Sorcerer, Cleric, Druid).

        This must be called after construction to set up Vancian spellcasting
        components. Does nothing if the character is not a caster class.

        For Sorcerers, sets up a :class:`SpontaneousCasterManager` with
        Charisma-based bonus slots and a :class:`SpellsKnownManager`.
        """
        from src.rules_engine.spellcasting import (
            SpellSlotManager,
            Spellbook,
            SpellsKnownManager,
            SpontaneousCasterManager,
            is_caster_class,
            get_key_ability,
        )

        if not is_caster_class(self.char_class):
            return

        key_ability = get_key_ability(self.char_class)
        ability_mod = _ability_modifier(getattr(self, key_ability))

        self.spell_slot_manager = SpellSlotManager.for_class(
            self.char_class, self.level, ability_mod,
        )

        if self.char_class == "Sorcerer":
            self.spells_known = SpellsKnownManager.for_sorcerer(self.level)
            self.spontaneous_caster = SpontaneousCasterManager.for_sorcerer(
                self.level, ability_mod,
            )
        else:
            self.spellbook = Spellbook()

    @property
    def is_caster(self) -> bool:
        """Whether this character has spellcasting capability."""
        from src.rules_engine.spellcasting import is_caster_class

        return is_caster_class(self.char_class)

    @property
    def caster_level(self) -> int:
        """Caster level (equals class level for single-class casters)."""
        if not self.is_caster:
            return 0
        return self.level

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a plain dictionary (JSON-compatible)."""
        return {
            "char_id": self.char_id,
            "name": self.name,
            "char_class": self.char_class,
            "level": self.level,
            "race": self.race,
            "alignment": self.alignment.value,
            "size": self.size.name,
            "base_speed": self.base_speed,
            "strength": self.strength,
            "dexterity": self.dexterity,
            "constitution": self.constitution,
            "intelligence": self.intelligence,
            "wisdom": self.wisdom,
            "charisma": self.charisma,
            "equipment": self.equipment,
            "feats": self.feats,
            "skills": self.skills,
            "metadata": self.metadata,
            # Derived (read-only, for convenience)
            "hit_points": self.hit_points,
            "base_attack_bonus": self.base_attack_bonus,
            "armor_class": self.armor_class,
            "fortitude_save": self.fortitude_save,
            "reflex_save": self.reflex_save,
            "will_save": self.will_save,
            "voxel_speed": self.voxel_speed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Character35e":
        """Reconstruct from a dictionary produced by :meth:`to_dict`.

        Derived fields (``hit_points``, ``base_attack_bonus``, etc.) are
        ignored — they will be recomputed from the raw ability scores.

        Args:
            data: Dictionary with keys matching :class:`Character35e` fields.

        Returns:
            A new :class:`Character35e` instance.
        """
        return cls(
            char_id=data["char_id"],
            name=data["name"],
            char_class=data.get("char_class", "Fighter"),
            level=data.get("level", 1),
            race=data.get("race", "Human"),
            alignment=Alignment(data["alignment"]) if "alignment" in data else Alignment.TRUE_NEUTRAL,
            size=Size[data["size"]] if "size" in data else Size.MEDIUM,
            base_speed=data.get("base_speed", 30),
            strength=data.get("strength", 10),
            dexterity=data.get("dexterity", 10),
            constitution=data.get("constitution", 10),
            intelligence=data.get("intelligence", 10),
            wisdom=data.get("wisdom", 10),
            charisma=data.get("charisma", 10),
            equipment=data.get("equipment", []),
            feats=data.get("feats", []),
            skills=data.get("skills", {}),
            metadata=data.get("metadata", {}),
        )

    def to_json(self) -> str:
        """Serialise to a JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "Character35e":
        """Deserialise from a JSON string."""
        return cls.from_dict(json.loads(json_str))

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"Character35e(id={self.char_id[:8]}…, name={self.name!r}, "
            f"class={self.char_class}, lvl={self.level}, "
            f"HP={self.hit_points}, AC={self.armor_class}, "
            f"BAB=+{self.base_attack_bonus})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Character35e):
            return NotImplemented
        return self.char_id == other.char_id

    def __hash__(self) -> int:
        return hash(self.char_id)
