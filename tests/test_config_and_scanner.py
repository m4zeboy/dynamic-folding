from __future__ import annotations

from pathlib import Path

import pytest


def _touch(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"x")


def test_load_default_config() -> None:
    from dynamic_folding.core.config import load_config

    cfg = load_config()
    assert cfg["scanner"]["max_depth"] == 2
    assert cfg["scanner"]["max_files"] == 200
    assert cfg["scanner"]["ignore_hidden"] is True


def test_scan_respects_max_depth(tmp_path: Path) -> None:
    from dynamic_folding.scanner.fs_scanner import scan

    # depth 0
    _touch(tmp_path / "a.txt")
    # depth 1
    _touch(tmp_path / "lvl1" / "b.txt")
    # depth 2
    _touch(tmp_path / "lvl1" / "lvl2" / "c.txt")
    # depth 3 (must be ignored)
    _touch(tmp_path / "lvl1" / "lvl2" / "lvl3" / "d.txt")

    out = scan(tmp_path, max_depth=2, max_files=200, ignore_hidden=False, ignore_globs=[])
    rels = {f.rel_path for f in out if not f.is_dir}

    assert "a.txt" in rels
    assert (Path("lvl1") / "b.txt").as_posix() in rels
    assert (Path("lvl1") / "lvl2" / "c.txt").as_posix() in rels
    assert (Path("lvl1") / "lvl2" / "lvl3" / "d.txt").as_posix() not in rels


def test_scan_respects_max_files(tmp_path: Path) -> None:
    from dynamic_folding.scanner.fs_scanner import scan

    for i in range(10):
        _touch(tmp_path / f"f{i}.txt")

    out = scan(tmp_path, max_depth=2, max_files=5, ignore_hidden=False, ignore_globs=[])
    files = [f for f in out if (not f.is_dir and f.depth >= 0)]
    assert len(files) == 5


def test_scan_is_deterministic_order(tmp_path: Path) -> None:
    from dynamic_folding.scanner.fs_scanner import scan

    _touch(tmp_path / "b.txt")
    _touch(tmp_path / "a.txt")
    _touch(tmp_path / "c.txt")

    out1 = scan(tmp_path, max_depth=2, max_files=200, ignore_hidden=False, ignore_globs=[])
    out2 = scan(tmp_path, max_depth=2, max_files=200, ignore_hidden=False, ignore_globs=[])

    rel1 = [f.rel_path for f in out1 if not f.is_dir]
    rel2 = [f.rel_path for f in out2 if not f.is_dir]
    assert rel1 == rel2
    assert rel1 == sorted(rel1, key=str.casefold)


@pytest.mark.parametrize(
    "path",
    [
        ".hidden.txt",
        (Path(".hidden") / "x.txt").as_posix(),
    ],
)
def test_ignore_hidden(tmp_path: Path, path: str) -> None:
    from dynamic_folding.scanner.fs_scanner import scan

    _touch(tmp_path / path)
    out = scan(tmp_path, max_depth=2, max_files=200, ignore_hidden=True, ignore_globs=[])
    rels = {f.rel_path for f in out if not f.is_dir}
    assert path not in rels


def test_scan_ignores_dynamic_folding_cache_dir(tmp_path: Path) -> None:
    from dynamic_folding.scanner.fs_scanner import scan

    _touch(tmp_path / ".dynamic-folding" / "cache.sqlite")
    out = scan(tmp_path, max_depth=2, max_files=200, ignore_hidden=False, ignore_globs=[".dynamic-folding/**"])
    rels = {f.rel_path for f in out if not f.is_dir}
    assert (Path(".dynamic-folding") / "cache.sqlite").as_posix() not in rels


def test_scan_ignores_thumbs_db_by_default_like_patterns(tmp_path: Path) -> None:
    from dynamic_folding.scanner.fs_scanner import scan

    _touch(tmp_path / "Thumbs.db")
    out = scan(
        tmp_path,
        max_depth=2,
        max_files=200,
        ignore_hidden=False,
        ignore_globs=["Thumbs.db"],
    )
    rels = {f.rel_path for f in out if not f.is_dir}
    assert "Thumbs.db" not in rels


def test_scan_does_not_crash_on_unreadable_dir(tmp_path: Path, monkeypatch) -> None:
    import os

    from dynamic_folding.scanner.fs_scanner import scan

    (tmp_path / "ok").mkdir()

    real_scandir = os.scandir

    def bad_scandir(path):
        if str(path).endswith("ok"):
            raise PermissionError("nope")
        return real_scandir(path)

    monkeypatch.setattr(os, "scandir", bad_scandir)

    out = scan(tmp_path, max_depth=2, max_files=200, ignore_hidden=False, ignore_globs=[])
    assert isinstance(out, list)


def test_scan_does_not_descend_into_symlink_dirs(tmp_path: Path, monkeypatch) -> None:
    import os

    from dynamic_folding.scanner.fs_scanner import scan

    # Setup: root has one entry that pretends to be a symlink directory.
    (tmp_path / "real").mkdir()
    (tmp_path / "real" / "x.txt").write_bytes(b"x")

    real_scandir = os.scandir

    class Wrapper:
        def __init__(self, e):
            self._e = e
            self.name = e.name
            self.path = e.path

        def is_symlink(self):
            return self.name == "real"

        def is_dir(self, follow_symlinks=False):
            return self._e.is_dir(follow_symlinks=follow_symlinks)

        def is_file(self, follow_symlinks=False):
            return self._e.is_file(follow_symlinks=follow_symlinks)

        def stat(self, follow_symlinks=False):
            return self._e.stat(follow_symlinks=follow_symlinks)

    def wrapped_scandir(path):
        return [Wrapper(e) for e in real_scandir(path)]

    monkeypatch.setattr(os, "scandir", wrapped_scandir)

    out = scan(tmp_path, max_depth=2, max_files=200, ignore_hidden=False, ignore_globs=[])
    rels = {f.rel_path for f in out if not f.is_dir}

    # If we descend into the symlink dir, we'd see real/x.txt.
    assert "real/x.txt" not in rels
