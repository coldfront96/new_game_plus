"""
src/rules_engine/conditions.py
------------------------------
D&D 3.5e SRD Condition Tracking System.

Conditions modify a character's stat block for a set duration (measured in
ticks). Each condition carries a dictionary of ``stat_modifiers`` that
downstream systems use to adjust AC, attack rolls, and other derived values.

Conditions are applied and removed via :class:`~src.core.event_bus.EventBus`
events (``"condition_applied"``, ``"condition_expired"``).

Usage::

    from src.rules_engine.conditions import Condition, ConditionManager, BLINDED

    manager = ConditionManager()
    manager.apply_condition(character, BLINDED, duration=5)
    ac = manager.get_effective_ac(character)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.core.event_bus import EventBus
from src.rules_engine.character_35e import Character35e


# ---------------------------------------------------------------------------
# Condition data model
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Condition:
    """A single condition applied to a character.

    Attributes:
        name:            The condition name (e.g. ``"Blinded"``).
        duration:        Remaining duration in ticks (``-1`` = permanent until
                         explicitly removed).
        stat_modifiers:  Dictionary of modifier keys to integer values.
                         Keys follow the pattern ``"<stat>:<type>"`` where
                         stat is the affected value and type describes the
                         modifier category.
        lose_dex_to_ac:  If ``True``, the character loses their Dexterity
                         bonus to AC while this condition is active.
        cannot_act:      If ``True``, the character cannot take actions.
    """

    name: str
    duration: int = -1
    stat_modifiers: Dict[str, int] = field(default_factory=dict)
    lose_dex_to_ac: bool = False
    cannot_act: bool = False


# ---------------------------------------------------------------------------
# Predefined 3.5e SRD conditions
# ---------------------------------------------------------------------------

def create_blinded(duration: int = -1) -> Condition:
    """Create a Blinded condition per the 3.5e SRD.

    Effects:
    - -2 penalty to AC.
    - Loses Dexterity bonus to AC.
    - -2 penalty to melee attack rolls (opponents have total concealment).
    """
    return Condition(
        name="Blinded",
        duration=duration,
        stat_modifiers={"ac": -2, "melee_attack": -2},
        lose_dex_to_ac=True,
        cannot_act=False,
    )


def create_stunned(duration: int = -1) -> Condition:
    """Create a Stunned condition per the 3.5e SRD.

    Effects:
    - Cannot act (loses actions).
    - -2 penalty to AC.
    - Loses Dexterity bonus to AC.
    """
    return Condition(
        name="Stunned",
        duration=duration,
        stat_modifiers={"ac": -2},
        lose_dex_to_ac=True,
        cannot_act=True,
    )


def create_prone(duration: int = -1) -> Condition:
    """Create a Prone condition per the 3.5e SRD.

    Effects:
    - -4 penalty on melee attack rolls.
    - +4 bonus to AC against ranged attacks.
    - -4 penalty to AC against melee attacks.
    """
    return Condition(
        name="Prone",
        duration=duration,
        stat_modifiers={
            "melee_attack": -4,
            "ac_vs_ranged": 4,
            "ac_vs_melee": -4,
        },
        lose_dex_to_ac=False,
        cannot_act=False,
    )


# ---------------------------------------------------------------------------
# ConditionManager
# ---------------------------------------------------------------------------

class ConditionManager:
    """Manages active conditions on characters.

    Tracks which conditions are currently applied to each character and
    provides methods to compute effective stat modifications. Publishes
    events on the EventBus when conditions are applied or expire.

    Args:
        event_bus: Optional :class:`EventBus` for publishing condition events.
    """

    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self._event_bus = event_bus
        # Mapping of character ID → list of active Condition instances
        self._conditions: Dict[str, List[Condition]] = {}

    def apply_condition(
        self,
        character: Character35e,
        condition: Condition,
    ) -> None:
        """Apply a condition to a character.

        If the character already has a condition with the same name, the
        existing one is replaced (per 3.5e SRD: conditions don't stack
        with themselves).

        Args:
            character: The target character.
            condition: The condition to apply.
        """
        char_id = character.char_id
        if char_id not in self._conditions:
            self._conditions[char_id] = []

        # Remove existing condition of the same name (no stacking)
        self._conditions[char_id] = [
            c for c in self._conditions[char_id] if c.name != condition.name
        ]
        self._conditions[char_id].append(condition)

        if self._event_bus is not None:
            self._event_bus.publish("condition_applied", {
                "char_id": char_id,
                "condition": condition.name,
                "duration": condition.duration,
            })

    def remove_condition(self, character: Character35e, name: str) -> bool:
        """Remove a named condition from a character.

        Args:
            character: The target character.
            name:      The condition name to remove.

        Returns:
            ``True`` if the condition was found and removed; ``False``
            otherwise.
        """
        char_id = character.char_id
        conditions = self._conditions.get(char_id, [])
        original_len = len(conditions)
        self._conditions[char_id] = [c for c in conditions if c.name != name]
        removed = len(self._conditions[char_id]) < original_len

        if removed and self._event_bus is not None:
            self._event_bus.publish("condition_expired", {
                "char_id": char_id,
                "condition": name,
            })

        return removed

    def get_conditions(self, character: Character35e) -> List[Condition]:
        """Return a list of active conditions on the character.

        Args:
            character: The character to query.

        Returns:
            List of active :class:`Condition` instances (may be empty).
        """
        return list(self._conditions.get(character.char_id, []))

    def has_condition(self, character: Character35e, name: str) -> bool:
        """Check if a character has a specific active condition.

        Args:
            character: The character to query.
            name:      The condition name to check.

        Returns:
            ``True`` if the condition is active.
        """
        return any(
            c.name == name
            for c in self._conditions.get(character.char_id, [])
        )

    def tick(self) -> List[Dict[str, Any]]:
        """Advance all condition durations by one tick.

        Conditions with ``duration == 0`` after decrement are expired
        and removed. Conditions with ``duration == -1`` (permanent) are
        not decremented.

        Returns:
            List of expired condition event dicts (char_id, condition name).
        """
        expired_events: List[Dict[str, Any]] = []

        for char_id in list(self._conditions.keys()):
            remaining: List[Condition] = []
            for condition in self._conditions[char_id]:
                if condition.duration == -1:
                    # Permanent — never expires on its own
                    remaining.append(condition)
                elif condition.duration > 1:
                    condition.duration -= 1
                    remaining.append(condition)
                else:
                    # duration <= 1 → expires this tick
                    expired_events.append({
                        "char_id": char_id,
                        "condition": condition.name,
                    })
                    if self._event_bus is not None:
                        self._event_bus.publish("condition_expired", {
                            "char_id": char_id,
                            "condition": condition.name,
                        })

            self._conditions[char_id] = remaining

        return expired_events

    # ------------------------------------------------------------------
    # Effective stat helpers
    # ------------------------------------------------------------------

    def loses_dex_to_ac(self, character: Character35e) -> bool:
        """Check if a character currently loses Dex bonus to AC.

        Returns:
            ``True`` if any active condition strips the Dex bonus.
        """
        return any(
            c.lose_dex_to_ac
            for c in self._conditions.get(character.char_id, [])
        )

    def cannot_act(self, character: Character35e) -> bool:
        """Check if a character is prevented from acting.

        Returns:
            ``True`` if any active condition prevents actions.
        """
        return any(
            c.cannot_act
            for c in self._conditions.get(character.char_id, [])
        )

    def get_ac_modifier(self, character: Character35e) -> int:
        """Compute the total AC modifier from all active conditions.

        This returns the sum of all ``"ac"`` modifiers. Does NOT account
        for loss of Dex bonus (that is handled separately).

        Args:
            character: The character to compute modifiers for.

        Returns:
            Total AC adjustment (negative = penalty).
        """
        total = 0
        for condition in self._conditions.get(character.char_id, []):
            total += condition.stat_modifiers.get("ac", 0)
        return total

    def get_melee_attack_modifier(self, character: Character35e) -> int:
        """Compute the total melee attack modifier from conditions.

        Args:
            character: The character to compute modifiers for.

        Returns:
            Total melee attack adjustment.
        """
        total = 0
        for condition in self._conditions.get(character.char_id, []):
            total += condition.stat_modifiers.get("melee_attack", 0)
        return total

    def get_effective_ac(self, character: Character35e) -> int:
        """Compute the effective AC considering all active conditions.

        Accounts for:
        - Loss of Dexterity bonus to AC (uses flat-footed base).
        - Flat AC modifiers from conditions.

        Args:
            character: The character to compute effective AC for.

        Returns:
            The adjusted AC value.
        """
        if self.loses_dex_to_ac(character):
            # Use flat-footed AC (no Dex bonus) as the base
            base_ac = character.flat_footed_ac
        else:
            base_ac = character.armor_class

        return base_ac + self.get_ac_modifier(character)
