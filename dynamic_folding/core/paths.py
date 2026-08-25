from __future__ import annotations

import os
from pathlib import Path


def default_cache_db_path() -> Path:
    """Default cache location.

    Windows-first: prefer LOCALAPPDATA.
    Fallback to user home if LOCALAPPDATA is missing.
    """

    lad = os.environ.get("LOCALAPPDATA")
    if lad:
        return (Path(lad) / "DynamicFolding" / "cache.sqlite").resolve()
    return (Path.home() / ".dynamic-folding" / "cache.sqlite").resolve()


def default_reports_dir() -> Path:
    """Default location for generated HTML reports.

    Windows: %LOCALAPPDATA%/DynamicFolding/reports/
    Elsewhere: ~/.dynamic-folding/reports/
    """
    lad = os.environ.get("LOCALAPPDATA")
    if lad:
        return (Path(lad) / "DynamicFolding" / "reports").resolve()
    return (Path.home() / ".dynamic-folding" / "reports").resolve()


def default_sbert_models_dir() -> Path:
    """Default location for locally saved SBERT models.

    Mirrors the cache_db convention: %LOCALAPPDATA%/DynamicFolding/models/
    on Windows, ~/.dynamic-folding/models/ elsewhere. The pipeline auto-
    discovers a model from this directory when no env var or config path
    is set; the `setup-sbert` command saves models here by default.
    """
    lad = os.environ.get("LOCALAPPDATA")
    if lad:
        return (Path(lad) / "DynamicFolding" / "models").resolve()
    return (Path.home() / ".dynamic-folding" / "models").resolve()
