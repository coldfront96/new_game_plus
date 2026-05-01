"""
src/ai_sim/entity.py
--------------------
Base Entity class for the New Game Plus ECS simulation layer.

An Entity is a lightweight identity container — a UUID plus a dictionary of
attached Components and a set of string tags. All game logic lives in Systems
that query entities by component type; the Entity itself carries no behaviour.

Usage::

    from src.ai_sim.entity import Entity

    agent = Entity(name="Aldric")
    agent.add_tag("npc")
    agent.add_tag("warrior")

    # Attach plain-data component objects
    from src.ai_sim.components import Position, Health
    agent.add_component(Position(x=10, y=64, z=10))
    agent.add_component(Health(current=100, maximum=100))

    print(agent)
    pos = agent.get_component(Position)
    print(pos.x, pos.y, pos.z)  # 10 64 10

    agent.remove_tag("warrior")
    print(agent.has_tag("warrior"))  # False
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional, Type, TypeVar

T = TypeVar("T")


@dataclass
class Entity:
    """Lightweight identity node in the ECS simulation.

    Attributes:
        entity_id: Globally unique identifier (UUID4). Auto-generated if
                   not supplied.
        name:      Human-readable label (e.g. agent name or creature type).
        is_active: When ``False`` the entity is ignored by all Systems and
                   scheduled for removal at the end of the current tick.
        tags:      Unordered set of string labels used for fast category
                   queries (e.g. ``"npc"``, ``"hostile"``, ``"on_fire"``).
        _components: Internal mapping of ``type → component instance``.
                     Consumers should use :meth:`add_component`,
                     :meth:`get_component`, and :meth:`remove_component`.
    """

    name: str
    entity_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    is_active: bool = True
    tags: set = field(default_factory=set)
    _components: dict = field(default_factory=dict, repr=False)
    metadata: dict = field(default_factory=dict, repr=False)
    deep_lore_filepath: Optional[str] = None

    # ------------------------------------------------------------------
    # Component management
    # ------------------------------------------------------------------

    def add_component(self, component: Any) -> "Entity":
        """Attach a component to this entity.

        Only one component per type is allowed. Replaces any existing
        component of the same type.

        Args:
            component: Any object to use as a component.  Conventionally
                       these are plain dataclass instances from
                       :mod:`src.ai_sim.components`.

        Returns:
            ``self``, enabling fluent chaining.
        """
        self._components[type(component)] = component
        return self

    def get_component(self, component_type: Type[T]) -> Optional[T]:
        """Retrieve the component of the given type, or ``None``.

        Args:
            component_type: The exact class of the component to look up.

        Returns:
            The attached component instance, or ``None`` if not present.
        """
        return self._components.get(component_type)

    def has_component(self, component_type: type) -> bool:
        """Return ``True`` if a component of *component_type* is attached."""
        return component_type in self._components

    def remove_component(self, component_type: type) -> Optional[Any]:
        """Detach and return the component of the given type.

        Args:
            component_type: The class of the component to remove.

        Returns:
            The removed component, or ``None`` if it was not present.
        """
        return self._components.pop(component_type, None)

    @property
    def components(self) -> dict:
        """Read-only view of all attached components keyed by type."""
        return dict(self._components)

    # ------------------------------------------------------------------
    # Tag management
    # ------------------------------------------------------------------

    def add_tag(self, tag: str) -> "Entity":
        """Add *tag* to this entity's tag set.

        Args:
            tag: Non-empty string label.

        Returns:
            ``self``, enabling fluent chaining.
        """
        if not tag:
            raise ValueError("tag must be a non-empty string")
        self.tags.add(tag)
        return self

    def remove_tag(self, tag: str) -> bool:
        """Remove *tag* if present.

        Args:
            tag: The tag to remove.

        Returns:
            ``True`` if the tag was present and removed; ``False`` otherwise.
        """
        if tag in self.tags:
            self.tags.discard(tag)
            return True
        return False

    def has_tag(self, tag: str) -> bool:
        """Return ``True`` if *tag* is in this entity's tag set."""
        return tag in self.tags

    def has_all_tags(self, *tags: str) -> bool:
        """Return ``True`` if *all* of the provided tags are present."""
        return all(t in self.tags for t in tags)

    def has_any_tag(self, *tags: str) -> bool:
        """Return ``True`` if *at least one* of the provided tags is present."""
        return any(t in self.tags for t in tags)

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    def destroy(self) -> None:
        """Mark this entity as inactive so Systems skip it next tick.

        The entity is not removed immediately — the World's cleanup pass
        will collect all inactive entities at the end of the tick.
        """
        self.is_active = False

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise to a plain dictionary (JSON-compatible meta-data only).

        Note:
            Component instances are **not** included in this representation
            because component serialisation is the responsibility of each
            component class. The dict contains only identity and tag data.
            ``deep_lore_filepath`` is included only when it is not ``None``.
        """
        d = {
            "entity_id": self.entity_id,
            "name": self.name,
            "is_active": self.is_active,
            "tags": sorted(self.tags),
            "component_types": [t.__name__ for t in self._components],
        }
        if self.deep_lore_filepath is not None:
            d["deep_lore_filepath"] = self.deep_lore_filepath
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "Entity":
        """Reconstruct an :class:`Entity` from a :meth:`to_dict` snapshot.

        Components are **not** restored here; callers must re-attach them
        separately after calling this method.

        Args:
            data: Dictionary produced by :meth:`to_dict`.

        Returns:
            A new :class:`Entity` instance (without components).
        """
        entity = cls(
            name=data["name"],
            entity_id=data["entity_id"],
            is_active=data.get("is_active", True),
        )
        entity.tags = set(data.get("tags", []))
        if data.get("deep_lore_filepath") is not None:
            entity.deep_lore_filepath = data["deep_lore_filepath"]
        return entity

    def to_json(self) -> str:
        """Serialise identity metadata to a JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "Entity":
        """Deserialise from a JSON string produced by :meth:`to_json`."""
        return cls.from_dict(json.loads(json_str))

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        n_components = len(self._components)
        tag_str = ", ".join(sorted(self.tags)) if self.tags else "—"
        return (
            f"Entity(id={self.entity_id[:8]}…, name={self.name!r}, "
            f"active={self.is_active}, tags=[{tag_str}], "
            f"components={n_components})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return NotImplemented
        return self.entity_id == other.entity_id

    def __hash__(self) -> int:
        return hash(self.entity_id)
