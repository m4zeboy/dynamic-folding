from __future__ import annotations

from pathlib import Path

import pytest


def _base_cfg() -> dict:
    return {
        "scanner": {"provider": "fs", "extractor": "basic", "max_depth": 2, "max_files": 200},
        "preprocess": {"provider": "basic"},
        "embedding": {"provider": "fake", "cache_db": "__default__", "fake_dim": 8},
        "proposal": {"provider": "two_level"},
    }


def test_validate_config_requires_embedding_model_path_for_sbert(monkeypatch, tmp_path: Path) -> None:
    from dynamic_folding.core import registries
    from dynamic_folding.core.validate_config import ConfigError, validate_config

    # Ensure provider is known so this test targets the new Sprint 5 validation.
    factories = dict(registries.EMBEDDERS._factories)
    factories["sbert"] = lambda _cfg: (lambda _docs, _cfg2: [])
    monkeypatch.setattr(registries.EMBEDDERS, "_factories", factories)

    cfg = _base_cfg()
    cfg["embedding"] = {
        "provider": "sbert",
        "cache_db": "__default__",
        # model_path intentionally missing
    }

    with pytest.raises(ConfigError) as e:
        validate_config(cfg)
    msg = str(e.value).lower()
    assert "embedding" in msg
    assert ("model_path" in msg) or ("sentence-transformers" in msg)


def test_validate_config_requires_naming_model_for_ollama(monkeypatch) -> None:
    from dynamic_folding.core import registries
    from dynamic_folding.core.validate_config import ConfigError, validate_config

    # Future-proof: once validate_config starts checking naming.provider, it should
    # allow known providers and then validate required keys.
    factories = dict(registries.NAMERS._factories)
    factories["ollama"] = lambda _cfg: (lambda _texts, _cfg2: "x")
    monkeypatch.setattr(registries.NAMERS, "_factories", factories)

    cfg = _base_cfg()
    cfg["naming"] = {
        "provider": "ollama",
        "base_url": "http://127.0.0.1:11434",
        # model intentionally missing
    }

    with pytest.raises(ConfigError) as e:
        validate_config(cfg)
    assert "naming" in str(e.value).lower()
    assert "model" in str(e.value).lower()


def test_validate_config_rejects_non_loopback_ollama_base_url(monkeypatch) -> None:
    from dynamic_folding.core import registries
    from dynamic_folding.core.validate_config import ConfigError, validate_config

    factories = dict(registries.NAMERS._factories)
    factories["ollama"] = lambda _cfg: (lambda _texts, _cfg2: "x")
    monkeypatch.setattr(registries.NAMERS, "_factories", factories)

    cfg = _base_cfg()
    cfg["naming"] = {
        "provider": "ollama",
        "model": "llama3",
        "base_url": "http://192.168.1.50:11434",
    }

    with pytest.raises(ConfigError) as e:
        validate_config(cfg)
    msg = str(e.value).lower()
    assert "base_url" in msg or "url" in msg
    assert "loopback" in msg or "localhost" in msg or "127.0.0.1" in msg


def test_ollama_namer_falls_back_to_tfidf_when_unreachable(monkeypatch) -> None:
    """Unit-level fallback behavior; must not require Ollama running."""

    from dynamic_folding.naming.tfidf import name_cluster as tfidf_name_cluster

    texts = [
        "invoice invoice invoice report",
        "invoice report february",
        "invoice report january",
    ]
    expected = tfidf_name_cluster(texts, top_terms=2)

    # Simulate local HTTP failure at the client layer.
    import urllib.request

    def _boom(*_a, **_kw):
        raise OSError("connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)

    from dynamic_folding.naming.ollama import name_cluster_ollama

    got = name_cluster_ollama(
        texts,
        {
            "provider": "ollama",
            "base_url": "http://127.0.0.1:11434",
            "model": "llama3",
            "timeout_s": 0.01,
            "top_terms": 2,
        },
    )
    assert got == expected
