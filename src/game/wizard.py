"""
src/game/wizard.py
------------------
Interactive text-mode character-creation wizard (Task 2).

Drives the user through a conversational flow:

    1. Race            → :class:`~src.rules_engine.race.RaceRegistry`
    2. Class           → (3.5e SRD core 11)
    3. Ability scores  → 4d6-drop-lowest **or** point-buy
    4. Skills          → :class:`~src.rules_engine.skills.SkillSystem`
    5. Feats           → :class:`~src.rules_engine.feat_engine.FeatRegistry`
    6. Starting equipment (simple presets per class)

The wizard returns a fully-populated :class:`~src.rules_engine.character_35e.Character35e`.
All prompts accept a numeric index matching a displayed list; invalid input
re-prompts instead of raising so the wizard can be driven by both interactive
terminals and scripted test fixtures.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, TextIO, Tuple

from src.rules_engine.character_35e import Alignment, Character35e, Size
from src.rules_engine.feat_engine import FEAT_CATALOG, FeatRegistry
from src.rules_engine.progression import Progression, XPManager, level_up
from src.rules_engine.race import RaceRegistry
from src.rules_engine.skills import SKILL_DEFINITIONS


# ---------------------------------------------------------------------------
# Supported classes and starting equipment
# ---------------------------------------------------------------------------

# The 11 core classes from the 3.5e SRD.
SUPPORTED_CLASSES: Tuple[str, ...] = (
    "Barbarian",
    "Bard",
    "Cleric",
    "Druid",
    "Fighter",
    "Monk",
    "Paladin",
    "Ranger",
    "Rogue",
    "Sorcerer",
    "Wizard",
)


# SRD 3.5 point-buy cost table (PHB p.169).  Scores 8–18.
_POINT_BUY_COST: Dict[int, int] = {
    8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5,
    14: 6, 15: 8, 16: 10, 17: 13, 18: 16,
}
_POINT_BUY_MIN = 8
_POINT_BUY_MAX = 18


_STARTING_EQUIPMENT: Dict[str, Tuple[str, ...]] = {
    "Barbarian": ("Greataxe", "Hide Armor", "Backpack", "Waterskin"),
    "Bard": ("Rapier", "Leather Armor", "Lute", "Backpack"),
    "Cleric": ("Heavy Mace", "Chain Shirt", "Holy Symbol", "Backpack"),
    "Druid": ("Scimitar", "Leather Armor", "Holly Sprig", "Backpack"),
    "Fighter": ("Longsword", "Chain Shirt", "Heavy Shield", "Backpack"),
    "Monk": ("Quarterstaff", "Sling", "Backpack", "Waterskin"),
    "Paladin": ("Longsword", "Chain Shirt", "Heavy Shield", "Holy Symbol"),
    "Ranger": ("Longsword", "Longbow", "Studded Leather Armor", "Quiver"),
    "Rogue": ("Rapier", "Leather Armor", "Thieves' Tools", "Backpack"),
    "Sorcerer": ("Quarterstaff", "Dagger", "Spell Component Pouch", "Backpack"),
    "Wizard": ("Quarterstaff", "Spellbook", "Spell Component Pouch", "Backpack"),
}


_CLASS_SKILL_POINTS_L1: Dict[str, int] = {
    "Barbarian": 4,
    "Bard": 6,
    "Cleric": 2,
    "Druid": 4,
    "Fighter": 2,
    "Monk": 4,
    "Paladin": 2,
    "Ranger": 6,
    "Rogue": 8,
    "Sorcerer": 2,
    "Wizard": 2,
}


# ---------------------------------------------------------------------------
# Ability-score generation helpers
# ---------------------------------------------------------------------------

def roll_4d6_drop_lowest(rng: random.Random) -> int:
    """Roll 4d6 and drop the lowest die (classic ability-score generation)."""
    rolls = sorted(rng.randint(1, 6) for _ in range(4))
    return sum(rolls[1:])


def roll_ability_scores(rng: random.Random) -> List[int]:
    """Return a list of six scores generated via 4d6-drop-lowest."""
    return [roll_4d6_drop_lowest(rng) for _ in range(6)]


def point_buy_cost(score: int) -> int:
    """Return the point-buy cost for a target ability score.

    Raises:
        ValueError: If *score* is outside the 8–18 SRD range.
    """
    if score not in _POINT_BUY_COST:
        raise ValueError(
            f"Point-buy score must be between {_POINT_BUY_MIN} and "
            f"{_POINT_BUY_MAX}; got {score}."
        )
    return _POINT_BUY_COST[score]


def point_buy_total(scores: Sequence[int]) -> int:
    """Return the total point-buy cost for six ability scores."""
    if len(scores) != 6:
        raise ValueError(f"Expected 6 scores, got {len(scores)}.")
    return sum(point_buy_cost(s) for s in scores)


def validate_point_buy(scores: Sequence[int], budget: int) -> None:
    """Validate that *scores* fits within *budget*.

    Raises:
        ValueError: If the total cost exceeds the budget or any score is
            outside the allowed range.
    """
    total = point_buy_total(scores)
    if total > budget:
        raise ValueError(
            f"Point-buy overspent: {total} points used, budget is {budget}."
        )


# ---------------------------------------------------------------------------
# CharacterWizard
# ---------------------------------------------------------------------------

_ABILITY_LABELS: Tuple[str, ...] = (
    "strength",
    "dexterity",
    "constitution",
    "intelligence",
    "wisdom",
    "charisma",
)


@dataclass
class CharacterWizard:
    """Drive the character-creation flow against a pair of text streams.

    The streams default to ``sys.stdin`` / ``sys.stdout`` so the wizard
    works in a real terminal, but tests (and scripted demos) can inject
    ``io.StringIO`` instances to drive it programmatically.

    Attributes:
        stdin:  Input stream for user prompts.
        stdout: Output stream for prompts and feedback.
        rng:    Random source for 4d6-drop-lowest.
    """

    stdin: TextIO
    stdout: TextIO
    rng: random.Random = field(default_factory=random.Random)

    # ------------------------------------------------------------------
    # Low-level I/O
    # ------------------------------------------------------------------

    def _print(self, msg: str = "") -> None:
        print(msg, file=self.stdout)

    def _readline(self) -> str:
        line = self.stdin.readline()
        if line == "":
            return ""
        return line.rstrip("\n")

    def _prompt_choice(
        self,
        prompt: str,
        options: Sequence[str],
        *,
        default: Optional[int] = None,
    ) -> int:
        """Prompt the user to choose one of *options* by 1-based index.

        Returns the 0-based index of the selected option.
        """
        self._print(prompt)
        for i, opt in enumerate(options, start=1):
            self._print(f"  {i}. {opt}")
        while True:
            suffix = f" [{default}]" if default is not None else ""
            self._print(f"Enter choice 1-{len(options)}{suffix}:")
            raw = self._readline().strip()
            if not raw and default is not None:
                return default - 1
            try:
                choice = int(raw)
            except ValueError:
                self._print(f"  '{raw}' is not a number; try again.")
                continue
            if 1 <= choice <= len(options):
                return choice - 1
            self._print(f"  {choice} is out of range; try again.")

    def _prompt_int(
        self,
        prompt: str,
        *,
        default: Optional[int] = None,
        minimum: Optional[int] = None,
        maximum: Optional[int] = None,
    ) -> int:
        while True:
            suffix = f" [{default}]" if default is not None else ""
            self._print(f"{prompt}{suffix}")
            raw = self._readline().strip()
            if not raw and default is not None:
                return default
            try:
                value = int(raw)
            except ValueError:
                self._print(f"  '{raw}' is not a number; try again.")
                continue
            if minimum is not None and value < minimum:
                self._print(f"  must be ≥ {minimum}; try again.")
                continue
            if maximum is not None and value > maximum:
                self._print(f"  must be ≤ {maximum}; try again.")
                continue
            return value

    def _prompt_str(
        self,
        prompt: str,
        *,
        default: Optional[str] = None,
    ) -> str:
        while True:
            suffix = f" [{default}]" if default else ""
            self._print(f"{prompt}{suffix}")
            raw = self._readline().strip()
            if raw:
                return raw
            if default:
                return default
            self._print("  a value is required; try again.")

    # ------------------------------------------------------------------
    # Individual prompt stages
    # ------------------------------------------------------------------

    def prompt_name(self, default: Optional[str] = None) -> str:
        return self._prompt_str("Character name?", default=default)

    def prompt_race(self) -> str:
        names = RaceRegistry.all_names()
        idx = self._prompt_choice("Choose a race:", names, default=1)
        return names[idx]

    def prompt_class(self) -> str:
        idx = self._prompt_choice(
            "Choose a class:", SUPPORTED_CLASSES, default=1,
        )
        return SUPPORTED_CLASSES[idx]

    def prompt_ability_scores(
        self,
        method: str = "4d6",
        point_buy_budget: int = 25,
    ) -> Dict[str, int]:
        """Generate and assign six ability scores.

        Method ``"4d6"`` rolls six times, then lets the user pick which
        score goes to which ability.  Method ``"point-buy"`` prompts the
        user to type a value per ability and validates the total cost
        against *point_buy_budget*.
        """
        if method == "4d6":
            pool = roll_ability_scores(self.rng)
            self._print(f"Rolled scores: {pool}")
            assigned: Dict[str, int] = {}
            remaining = list(pool)
            for ability in _ABILITY_LABELS:
                self._print(f"Assign a score to {ability.upper()}.")
                idx = self._prompt_choice(
                    f"Remaining: {remaining}",
                    [str(v) for v in remaining],
                    default=1,
                )
                assigned[ability] = remaining.pop(idx)
            return assigned

        if method == "point-buy":
            self._print(
                f"Point-buy budget: {point_buy_budget} points. "
                f"Valid score range: {_POINT_BUY_MIN}–{_POINT_BUY_MAX}."
            )
            assigned = {}
            while True:
                for ability in _ABILITY_LABELS:
                    assigned[ability] = self._prompt_int(
                        f"Score for {ability.upper()} "
                        f"({_POINT_BUY_MIN}–{_POINT_BUY_MAX})?",
                        default=10,
                        minimum=_POINT_BUY_MIN,
                        maximum=_POINT_BUY_MAX,
                    )
                try:
                    validate_point_buy(list(assigned.values()), point_buy_budget)
                except ValueError as err:
                    self._print(f"  {err}  Try again.")
                    continue
                return assigned

        raise ValueError(f"Unknown ability-score method: {method!r}")

    def prompt_skills(
        self,
        char_class: str,
        intelligence_mod: int,
        *,
        available: Optional[int] = None,
    ) -> Dict[str, int]:
        """Distribute skill points.

        At level 1 the pool is ``(base + INT) × 4``.  For subsequent levels
        pass *available* directly to skip the first-level quadrupling.
        """
        if available is None:
            base = _CLASS_SKILL_POINTS_L1.get(char_class, 2)
            total = max(1, base + intelligence_mod) * 4
        else:
            total = available
        ranks: Dict[str, int] = {}
        skill_names = sorted(SKILL_DEFINITIONS.keys())
        self._print(
            f"You have {total} skill points to spend across {len(skill_names)} skills."
        )
        remaining = total
        while remaining > 0:
            self._print(f"Remaining points: {remaining}")
            idx = self._prompt_choice(
                "Pick a skill to assign ranks to (or choose 'done').",
                skill_names + ["done"],
                default=len(skill_names) + 1,
            )
            if idx == len(skill_names):
                break
            skill = skill_names[idx]
            max_ranks = min(remaining, remaining)
            amount = self._prompt_int(
                f"Ranks in {skill} (0–{max_ranks})?",
                default=0,
                minimum=0,
                maximum=max_ranks,
            )
            if amount == 0:
                continue
            ranks[skill] = ranks.get(skill, 0) + amount
            remaining -= amount
        return ranks

    def prompt_feats(
        self,
        character: Character35e,
        *,
        num_feats: Optional[int] = None,
    ) -> List[str]:
        """Ask the user to pick feats.

        *num_feats* overrides the slot count derived from race/class (used
        during level-up where the slot count is pre-calculated by the caller).
        """
        if num_feats is not None:
            slots = num_feats
        else:
            slots = 1
            if character.race == "Human":
                slots += 1
            if character.char_class == "Fighter":
                slots += 1
        eligible = [
            name for name in sorted(FEAT_CATALOG.keys())
            if FeatRegistry.meets_prerequisites(character, name)
        ]
        chosen: List[str] = []
        for i in range(slots):
            options = [n for n in eligible if n not in chosen] + ["(skip)"]
            idx = self._prompt_choice(
                f"Choose feat #{i + 1} of {slots}:",
                options,
                default=len(options),
            )
            if idx == len(options) - 1:
                break
            chosen.append(options[idx])
            # Prerequisites might change once a feat is added; refresh list
            eligible = [
                name for name in sorted(FEAT_CATALOG.keys())
                if FeatRegistry.meets_prerequisites(character, name)
                or name in chosen
            ]
        return chosen

    # ------------------------------------------------------------------
    # Top-level flow
    # ------------------------------------------------------------------

    def run(
        self,
        *,
        name: Optional[str] = None,
        method: str = "4d6",
        point_buy_budget: int = 25,
    ) -> Character35e:
        """Execute the full wizard and return the constructed character."""
        self._print("=== New Game Plus — Character Creation ===")
        char_name = name or self.prompt_name()
        race_name = self.prompt_race()
        char_class = self.prompt_class()
        scores = self.prompt_ability_scores(
            method=method,
            point_buy_budget=point_buy_budget,
        )

        race = RaceRegistry.get(race_name)
        size = Size[race.size.upper()] if race.size.upper() in Size.__members__ else Size.MEDIUM

        # Preliminary character so skills + feats can consult derived stats
        character = Character35e(
            name=char_name,
            char_class=char_class,
            level=1,
            race=race_name,
            alignment=_default_alignment(char_class),
            size=size,
            strength=scores["strength"],
            dexterity=scores["dexterity"],
            constitution=scores["constitution"],
            intelligence=scores["intelligence"],
            wisdom=scores["wisdom"],
            charisma=scores["charisma"],
            base_speed=race.base_speed,
        )

        character.skills = self.prompt_skills(
            char_class=char_class,
            intelligence_mod=character.intelligence_mod,
        )
        for feat in self.prompt_feats(character):
            FeatRegistry.add_feat(character, feat)

        character.equipment = list(_STARTING_EQUIPMENT.get(char_class, ()))

        # Initialize spellcasting slots if applicable.
        character.initialize_spellcasting()

        self._print("")
        self._print(f"Created: {character!r}")
        return character


def _default_alignment(char_class: str) -> Alignment:
    """Return a class-appropriate default alignment."""
    if char_class == "Paladin":
        return Alignment.LAWFUL_GOOD
    if char_class == "Monk":
        return Alignment.LAWFUL_NEUTRAL
    if char_class == "Barbarian":
        return Alignment.CHAOTIC_NEUTRAL
    return Alignment.NEUTRAL_GOOD


def _feat_slots_gained(new_level: int, char_class: str) -> int:
    """Return the number of feat slots gained at *new_level*.

    General rule: +1 feat at every level divisible by 3 (levels 3, 6, 9, …).
    Fighter bonus rule: +1 extra feat at level 1 and every even level
    (1, 2, 4, 6, 8, …) for Fighters.
    """
    slots = 1 if new_level % 3 == 0 else 0
    if char_class == "Fighter":
        if new_level == 1 or new_level % 2 == 0:
            slots += 1
    return slots


def run_level_up_flow(
    character: Character35e,
    xp_manager: XPManager,
    wizard: CharacterWizard,
) -> Optional[Progression]:
    """Check for and interactively run a level-up for *character*.

    If *character* does not yet have enough XP to level, returns ``None``
    without printing anything.  Otherwise advances the character by one
    level, presents the HP and skill point gain, prompts the player to
    distribute new skill ranks and pick any new feats, then returns the
    :class:`~src.rules_engine.progression.Progression` record.

    Args:
        character:   The character to potentially level up.
        xp_manager:  The :class:`XPManager` tracking the character's XP.
        wizard:      A :class:`CharacterWizard` used for interactive prompts.

    Returns:
        :class:`Progression` if a level-up occurred, ``None`` otherwise.
    """
    check = xp_manager.check_level_up()
    if not check.leveled_up:
        return None

    progression = level_up(character, xp_manager)
    wizard._print(
        f"\n{'=' * 50}\n"
        f"*** {character.name} reached level {progression.new_level}! ***\n"
        f"  HP gained  : +{progression.hp_gained}\n"
        f"  Skill pts  : {progression.skill_points}\n"
        f"{'=' * 50}"
    )

    # Distribute new skill ranks (add to existing ranks)
    new_ranks = wizard.prompt_skills(
        character.char_class,
        character.intelligence_mod,
        available=progression.skill_points,
    )
    for skill, amount in new_ranks.items():
        character.skills[skill] = character.skills.get(skill, 0) + amount

    # Feat slots
    feat_slots = _feat_slots_gained(progression.new_level, character.char_class)
    if feat_slots > 0:
        wizard._print(f"  You gain {feat_slots} feat slot(s).")
        new_feats = wizard.prompt_feats(character, num_feats=feat_slots)
        for feat_name in new_feats:
            FeatRegistry.add_feat(character, feat_name)

    wizard._print(
        f"Level-up complete. {character.name} is now level {character.level}."
    )
    return progression
