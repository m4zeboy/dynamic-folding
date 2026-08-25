from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Protocol


class ProgressStage(Protocol):
    def advance(self, n: int = 1) -> None: ...


class Progress(Protocol):
    @contextmanager
    def stage(self, name: str, *, total: int | None = None) -> Iterator[ProgressStage]: ...


@dataclass
class _NullStage:
    def advance(self, n: int = 1) -> None:  # pragma: no cover
        return


class NullProgress:
    @contextmanager
    def stage(self, name: str, *, total: int | None = None) -> Iterator[ProgressStage]:  # pragma: no cover
        yield _NullStage()
