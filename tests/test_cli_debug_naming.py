from __future__ import annotations

import os
import re
from pathlib import Path


def test_resolve_naming_debug_path_flag_off_no_op(monkeypatch) -> None:
    """Flag off → returns None and does not touch the env var."""
    from dynamic_folding.cli import _resolve_naming_debug_path

    monkeypatch.delenv("DYNAMIC_FOLDING_NAMING_DEBUG_PATH", raising=False)
    result = _resolve_naming_debug_path(False)

    assert result is None
    assert "DYNAMIC_FOLDING_NAMING_DEBUG_PATH" not in os.environ


def test_resolve_naming_debug_path_flag_on_sets_env_with_timestamped_path(
    monkeypatch, tmp_path: Path
) -> None:
    """Flag on, no env var → generates timestamped path in CWD and sets env var."""
    from dynamic_folding.cli import _resolve_naming_debug_path

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DYNAMIC_FOLDING_NAMING_DEBUG_PATH", raising=False)

    result = _resolve_naming_debug_path(True)

    assert result is not None
    # Path is under the new CWD.
    assert str(tmp_path) in result
    # Filename matches naming_debug_YYYYMMDD_HHMMSS.jsonl.
    assert re.search(r"naming_debug_\d{8}_\d{6}\.jsonl$", result) is not None
    # Env var got set to the same path so the namer picks it up.
    assert os.environ["DYNAMIC_FOLDING_NAMING_DEBUG_PATH"] == result


def test_resolve_naming_debug_path_flag_on_respects_existing_env(monkeypatch) -> None:
    """Pre-existing env var beats the flag (explicit user intent wins)."""
    from dynamic_folding.cli import _resolve_naming_debug_path

    explicit = "/explicit/user/path.jsonl"
    monkeypatch.setenv("DYNAMIC_FOLDING_NAMING_DEBUG_PATH", explicit)

    result = _resolve_naming_debug_path(True)

    # Helper signals "no override happened" by returning None.
    assert result is None
    # Env var is unchanged.
    assert os.environ["DYNAMIC_FOLDING_NAMING_DEBUG_PATH"] == explicit
