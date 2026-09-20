from __future__ import annotations

from pathlib import Path
from typing import Any

import tomllib

from dynamic_folding.core.config_utils import deep_merge


def get_system_defaults() -> dict[str, Any]:
    """
    Return hardcoded zero-deps defaults — a complete, valid config.

    These describe the deterministic, no-extra-deps stack: fake embedder,
    identity reducer, kmeans clustering, tfidf naming. Anything richer
    (sbert, ollama, hdbscan) is opted into via a config preset such as
    config/default.toml or config/sbert_ollama_llama3_1.toml.
    """
    return {
        "scanner": {
            "provider": "fs",
            "extractor": "basic",
            "max_depth": 2,
            "max_files": 200,
            "snippet_size": 4096,
            "ignore_hidden": True,
            "ignore_globs": [],
        },
        "preprocess": {
            "provider": "basic",
            "template": "{stem} ext:{ext} path:{rel_path}",
        },
        "embedding": {
            "provider": "fake",
            "batch_size": 32,
            "normalize": True,
            "cache_db": "__default__",
        },
        "reducer": {
            "provider": "identity",
            "n_components": 10,
            "n_neighbors": 15,
            "random_state": 0,
        },
        "clustering": {
            "algorithm": "kmeans",
            "top_k": 3,
            "sub_k": 2,
            "min_cluster_size": 4,
            "random_state": 0,
        },
        "naming": {
            "provider": "tfidf",
            "top_terms": 2,
        },
        "proposal": {
            "provider": "two_level",
            "max_levels": 2,
            "outliers_folder": "Outros",
            # Naming strategy (ADR 0037). System default keeps the stable
            # per-node labeling so the zero-deps/test stack is unchanged;
            # config/default.toml opts into "bottom_up" for real runs.
            "naming_direction": "per_node",
        },
        "ui": {
            "use_emojis": True,
        },
        "report": {
            "enabled": False,
            "output_path": "__default__",
            "auto_open": False,
        },
    }


def project_default_config_path() -> Path:
    """Path to the project's user-facing default config (config/default.toml)."""
    return Path(__file__).resolve().parents[2] / "config" / "default.toml"


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """
    Load and resolve configuration: System Defaults -> User Config (if provided).

    Note: the project's `config/default.toml` is NOT auto-merged here. It is the
    CLI's responsibility to pass it as `config_path` when no user override is
    given. This keeps test runs that call `run_pipeline()` directly on the
    deterministic, zero-deps system defaults (fake embedder + tfidf namer).
    """
    cfg = get_system_defaults()

    if config_path and config_path.exists():
        with open(config_path, "rb") as f:
            cfg = deep_merge(cfg, tomllib.load(f))

    return cfg
