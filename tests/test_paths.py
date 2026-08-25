from __future__ import annotations

import os
from pathlib import Path


def test_default_cache_path_prefers_localappdata(monkeypatch) -> None:
    from dynamic_folding.core.paths import default_cache_db_path

    monkeypatch.setenv("LOCALAPPDATA", str(Path("C:/Users/x/AppData/Local")))
    p = default_cache_db_path()
    assert str(p).lower().endswith(str(Path("DynamicFolding") / "cache.sqlite").lower())


def test_default_cache_path_falls_back_to_home(monkeypatch) -> None:
    from dynamic_folding.core.paths import default_cache_db_path

    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    p = default_cache_db_path()
    assert "cache.sqlite" in str(p)
