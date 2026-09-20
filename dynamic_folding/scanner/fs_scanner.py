from __future__ import annotations

import fnmatch
import os
from collections.abc import Iterable
from pathlib import Path

from dynamic_folding.contracts.file_ref import FileRef


def _is_hidden(rel: str) -> bool:
    # Cross-platform-ish hidden rule for MVP: any path segment starting with '.'
    parts = Path(rel).parts
    return any(p.startswith(".") for p in parts)


def _matches_any_glob(rel_posix: str, globs: Iterable[str]) -> bool:
    for g in globs:
        # Use a simple, predictable glob matcher over POSIX paths.
        if fnmatch.fnmatch(rel_posix, g):
            return True
        # If the pattern has no separators, match against the basename too.
        if "/" not in g and fnmatch.fnmatch(Path(rel_posix).name, g):
            return True
    return False


def scan(
    root: Path,
    *,
    max_depth: int,
    max_files: int,
    ignore_hidden: bool,
    ignore_globs: list[str],
) -> list[FileRef]:
    """Scan directory contents up to a maximum depth.

    Returns a deterministic, sorted list of FileRef entries.
    Directories are included to enable future grouping decisions, but tests
    currently focus on file discovery.
    """

    root = root.resolve()
    out: list[FileRef] = []
    file_count = 0

    # BFS-style traversal, deterministic by sorting directory entries.
    # Depth definition (MVP): number of directory levels from root.
    # - file at root => depth 0
    # - file under root/level1 => depth 1
    # - file under root/level1/level2 => depth 2
    queue: list[tuple[Path, int]] = [(root, 0)]

    while queue:
        cur, dir_depth = queue.pop(0)
        try:
            entries = list(os.scandir(cur))
        except OSError:
            # Ignore unreadable directories in MVP.
            continue

        # Deterministic ordering
        entries.sort(key=lambda e: e.name.casefold())

        for e in entries:
            p = Path(e.path)
            rel_posix = p.relative_to(root).as_posix()

            if ignore_hidden and _is_hidden(rel_posix):
                continue
            if ignore_globs and _matches_any_glob(rel_posix, ignore_globs):
                continue

            is_dir = e.is_dir(follow_symlinks=False)
            is_file = e.is_file(follow_symlinks=False)

            # Do not descend into symlink/junction dirs (avoid loops / escape).
            try:
                is_link = bool(getattr(e, "is_symlink")())
            except Exception:
                is_link = False
            if is_dir and is_link:
                continue

            # Enforce depth using directory-depth semantics.
            entry_depth = (dir_depth + 1) if is_dir else dir_depth
            if entry_depth > max_depth:
                continue

            st = None
            try:
                st = e.stat(follow_symlinks=False)
            except OSError:
                st = None

            ext = ""
            if not is_dir:
                ext = p.suffix.lower().lstrip(".")

            out.append(
                FileRef(
                    path=str(p.resolve()),
                    # Contract: rel_path always uses POSIX separators.
                    rel_path=rel_posix,
                    is_dir=is_dir,
                    depth=entry_depth,
                    name=e.name,
                    ext=ext,
                    size=(None if is_dir or st is None else int(st.st_size)),
                    ctime=(None if st is None else float(getattr(st, "st_ctime", 0.0))),
                    mtime=(None if st is None else float(getattr(st, "st_mtime", 0.0))),
                )
            )

            if is_file:
                file_count += 1
                if file_count >= max_files:
                    # Only cap by file count; keep behavior simple.
                    break

            if is_dir:
                # Only descend if the directory itself is within depth.
                queue.append((p, entry_depth))

        if file_count >= max_files:
            break

    # Deterministic final order: files/dirs mixed but stable by rel_path.
    out.sort(key=lambda fr: fr.rel_path.casefold())
    return out
