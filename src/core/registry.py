"""
src/core/registry.py
--------------------
Generic name-based registry used to look up engine objects by string key.

The registry pattern decouples producers from consumers and supports
data-driven configuration (e.g. loading block/item definitions from JSON).

Usage::

    from src.core.registry import Registry

    material_registry: Registry[str] = Registry("materials")
    material_registry.register("stone", "STONE")
    material_registry.register("dirt", "DIRT")

    print(material_registry.get("stone"))  # "STONE"
    print("stone" in material_registry)    # True
"""

from __future__ import annotations

from typing import Dict, Generic, Iterator, Optional, TypeVar

T = TypeVar("T")


class Registry(Generic[T]):
    """Generic name → object registry.

    Attributes:
        name: Human-readable label for this registry (used in error messages).
    """

    def __init__(self, name: str = "registry") -> None:
        self.name = name
        self._entries: Dict[str, T] = {}

    def register(self, key: str, value: T, overwrite: bool = False) -> None:
        """Add *value* under *key*.

        Args:
            key:       String identifier.
            value:     Object to store.
            overwrite: If ``False`` (default) raises :exc:`KeyError` when
                       *key* already exists.

        Raises:
            KeyError: If *key* is already registered and *overwrite* is ``False``.
        """
        if not overwrite and key in self._entries:
            raise KeyError(
                f"Registry '{self.name}': key {key!r} is already registered. "
                "Use overwrite=True to replace."
            )
        self._entries[key] = value

    def get(self, key: str) -> Optional[T]:
        """Return the value for *key*, or ``None`` if not found."""
        return self._entries.get(key)

    def require(self, key: str) -> T:
        """Return the value for *key*, raising :exc:`KeyError` if absent.

        Args:
            key: String identifier.

        Raises:
            KeyError: If *key* is not registered.
        """
        if key not in self._entries:
            raise KeyError(
                f"Registry '{self.name}': key {key!r} is not registered."
            )
        return self._entries[key]

    def unregister(self, key: str) -> Optional[T]:
        """Remove and return the value for *key* (returns ``None`` if absent)."""
        return self._entries.pop(key, None)

    def keys(self) -> Iterator[str]:
        """Iterate over all registered keys."""
        return iter(self._entries.keys())

    def values(self) -> Iterator[T]:
        """Iterate over all registered values."""
        return iter(self._entries.values())

    def __contains__(self, key: str) -> bool:
        return key in self._entries

    def __len__(self) -> int:
        return len(self._entries)

    def __repr__(self) -> str:
        return f"Registry({self.name!r}, {len(self)} entries)"
