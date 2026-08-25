from __future__ import annotations

import json
from pathlib import Path


def test_fake_embedder_is_deterministic() -> None:
    from dynamic_folding.embedding.fake import FakeEmbedder

    e = FakeEmbedder(dim=8)
    v1 = e.embed_text("hello")
    v2 = e.embed_text("hello")
    v3 = e.embed_text("hello!")

    assert v1 == v2
    assert v1 != v3
    assert len(v1) == 8


def test_sqlite_cache_roundtrip(tmp_path: Path) -> None:
    from dynamic_folding.cache.sqlite_cache import EmbeddingCache

    db = tmp_path / "cache.sqlite"
    cache = EmbeddingCache(db)

    key = "rel/file.txt"
    model_id = "fake:v1"
    content_hash = "abc"
    vector = [0.1, 0.2, 0.3]

    assert cache.get(key, model_id=model_id, content_hash=content_hash) is None
    cache.put(key, model_id=model_id, content_hash=content_hash, vector=vector, text="some text")
    got_vec, got_text = cache.get(key, model_id=model_id, content_hash=content_hash)
    assert got_vec == vector
    assert got_text == "some text"
    # Different hash misses
    assert cache.get(key, model_id=model_id, content_hash="def") is None


def test_pipeline_produces_embeddings_when_enabled(tmp_path: Path) -> None:
    # This test is intentionally higher-level: it validates the contracts
    # and that caching is wired, without requiring a real ML model.
    from dynamic_folding.core.pipeline import run_pipeline

    (tmp_path / "a.txt").write_text("x", encoding="utf-8")

    r1 = run_pipeline(tmp_path)
    d1 = r1.to_dict()

    assert "embeddings" in d1
    assert isinstance(d1["embeddings"], list)

    # Second run should keep the same embeddings deterministically.
    r2 = run_pipeline(tmp_path)
    d2 = r2.to_dict()

    assert json.dumps(d1["embeddings"], sort_keys=True) == json.dumps(d2["embeddings"], sort_keys=True)
