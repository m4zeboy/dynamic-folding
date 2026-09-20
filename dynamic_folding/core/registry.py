from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar


T = TypeVar("T")


@dataclass
class Registry(Generic[T]):
    name: str

    def __post_init__(self) -> None:
        self._factories: dict[str, Callable[[dict], T]] = {}

    def register(self, key: str, factory: Callable[[dict], T]) -> None:
        self._factories[key] = factory

    def keys(self) -> list[str]:
        return sorted(self._factories.keys(), key=str.casefold)

    def create(self, key: str, config: dict) -> T:
        try:
            fn = self._factories[key]
        except KeyError as e:
            raise KeyError(f"Unknown {self.name} plugin '{key}'. Available: {self.keys()}") from e
        return fn(config)
