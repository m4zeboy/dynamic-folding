"""
Shared pytest configuration.

Goal: tests must never touch the user's global embedding cache or any other
machine-level state. The pipeline resolves `cache_db = "__default__"` to
`%LOCALAPPDATA%/DynamicFolding/cache.sqlite`. We redirect LOCALAPPDATA (and
HOME, as a fallback) into a session-scoped temp directory that lives OUTSIDE
any test's `tmp_path`, so it never appears as a scannable input.
"""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def _df_cache_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("dynamic_folding_cache")


@pytest.fixture(autouse=True)
def _isolate_dynamic_folding_cache(
    _df_cache_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(_df_cache_root))
    monkeypatch.setenv("HOME", str(_df_cache_root))


@pytest.fixture
def make_file_ref():
    """Factory that builds a FileRef the way the real scanner does.

    Crucially, the extension is BARE and lowercased (no leading dot), matching
    ``fs_scanner.scan()``'s ``p.suffix.lower().lstrip(".")``. Hand-built test
    fixtures that used a dotted ext (e.g. ``ext=".pdf"``) silently masked the
    Sprint-7 extractor dispatch bug for years (ADR 0036). New tests should build
    file refs through this factory so production's bare-ext contract is exercised
    and that trap cannot return.
    """
    from pathlib import Path as _Path

    from dynamic_folding.contracts.file_ref import FileRef

    def _make(path, *, rel_path=None, depth=0, size=1, ctime=None, mtime=None):
        p = _Path(path)
        return FileRef(
            path=str(path),
            rel_path=rel_path if rel_path is not None else p.name,
            is_dir=False,
            depth=depth,
            name=p.name,
            ext=p.suffix.lower().lstrip("."),
            size=size,
            ctime=ctime,
            mtime=mtime,
        )

    return _make
