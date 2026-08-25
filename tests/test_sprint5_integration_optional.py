from __future__ import annotations

import os
from pathlib import Path

import pytest


def _touch(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"x")


def test_integration_sbert_embeddings_smoke(tmp_path: Path) -> None:
    model_path = os.environ.get("DYNAMIC_FOLDING_SBERT_MODEL_PATH")
    if not model_path:
        pytest.skip("Set DYNAMIC_FOLDING_SBERT_MODEL_PATH to run SBERT integration test")

    _touch(tmp_path / "invoice_jan.pdf")
    _touch(tmp_path / "invoice_feb.pdf")

    cfg_path = tmp_path / "cfg.toml"
    cfg_path.write_text(
        """
[scanner]
provider = "fs"
extractor = "basic"
max_depth = 2
max_files = 200
ignore_hidden = true
ignore_globs = [".dynamic-folding/**"]

[preprocess]
provider = "basic"

[embedding]
provider = "sbert"
model_path = """  # keep TOML stable
        + model_path.replace("\\", "\\\\")
        + """
device = "cpu"
normalize = true
cache_db = "cache.sqlite"

[clustering]
algorithm = "kmeans"
top_k = 2
sub_k = 2
random_state = 0

[naming]
provider = "tfidf"
top_terms = 2

[proposal]
provider = "two_level"
""".lstrip(),
        encoding="utf-8",
    )

    from dynamic_folding.core.pipeline import run_pipeline

    r1 = run_pipeline(tmp_path, config_path=cfg_path).to_dict()
    r2 = run_pipeline(tmp_path, config_path=cfg_path).to_dict()

    assert r1["embeddings"], "expected non-empty embeddings"
    assert r1["embeddings"] == r2["embeddings"], "expected stable embeddings across two runs"


def test_integration_ollama_naming_smoke() -> None:
    model = os.environ.get("DYNAMIC_FOLDING_OLLAMA_MODEL")
    if not model:
        pytest.skip("Set DYNAMIC_FOLDING_OLLAMA_MODEL to run Ollama integration test")

    base_url = os.environ.get("DYNAMIC_FOLDING_OLLAMA_BASE_URL", "http://127.0.0.1:11434")

    from dynamic_folding.core.windows import sanitize_windows_folder_name
    from dynamic_folding.naming.ollama import name_cluster_ollama

    texts = [
        "photo trip paris 01",
        "photo trip paris 02",
        "photo trip paris 03",
    ]

    try:
        out = name_cluster_ollama(
            texts,
            {
                "provider": "ollama",
                "base_url": base_url,
                "model": model,
                "timeout_s": 10,
                "top_terms": 2,
            },
        )
    except OSError as e:
        pytest.skip(f"Ollama not reachable at {base_url}: {e}")

    assert out
    assert out == sanitize_windows_folder_name(out)
    assert out.strip() == out
    assert not out.endswith(".")
