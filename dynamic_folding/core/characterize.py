"""Sprint 19: characterize orchestrator.

Runs the three quantitative properties (structure-finding, stability,
performance) on a single corpus and writes a timestamped JSON.

See ADR 0018, SPEC Sprint 19, and docs/learning/01-stability-metric.md.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.metrics import silhouette_score

from dynamic_folding.clustering.random_baseline import cluster_random
from dynamic_folding.contracts.characterization import CharacterizationResult
from dynamic_folding.core.pipeline import resolve_effective_config, run_pipeline
from dynamic_folding.core.registries import CLUSTERERS
from dynamic_folding.core.stability import compute_stability


def _safe_silhouette(vectors: list[list[float]], labels: list[int]) -> float | None:
    if len(vectors) < 2:
        return None
    if len(set(labels)) < 2:
        return None
    try:
        return float(silhouette_score(np.asarray(vectors), labels))
    except Exception:
        return None


def run_characterize(
    root: Path,
    *,
    output_dir: Path = Path("characterization_results"),
    config_path: Path | None = None,
    runs: int = 5,
    perturbation: float = 0.10,
    seed: int = 0,
) -> CharacterizationResult:
    root = Path(root).resolve()

    cfg = resolve_effective_config(root, config_path=config_path)
    cl_cfg = dict(cfg.get("clustering", {}))
    algo = str(cl_cfg.get("algorithm", "kmeans")).strip().lower()

    # (a) Real pipeline run -> embeddings + timings + peak memory.
    result = run_pipeline(root, config_path=config_path)
    vectors = [list(e.vector) for e in result.embeddings]
    n_files = len(vectors)

    # (b) Structure step: silhouette of real clusterer vs. random baseline.
    notes: list[str] = []
    structure: dict = {
        "silhouette_real": None,
        "silhouette_random": None,
        "k": None,
    }
    if n_files >= 2:
        clusterer = CLUSTERERS.create(algo, {})
        labels_real = list(clusterer(vectors, cl_cfg).labels)
        unique_real = sorted(set(labels_real))
        # K = number of non-empty clusters from the real clusterer (>=2 for
        # silhouette to be meaningful). Random baseline uses the same K so the
        # comparison is fair (per ADR 0018 / SPEC Sprint 19).
        k_effective = max(len(unique_real), 2)
        labels_random = cluster_random(vectors, k=k_effective, random_state=seed).labels

        sil_real = _safe_silhouette(vectors, labels_real)
        sil_random = _safe_silhouette(vectors, labels_random)
        structure = {
            "silhouette_real": sil_real,
            "silhouette_random": sil_random,
            "k": k_effective,
        }
    else:
        notes.append("fewer than 2 embeddable files; structure metrics undefined")

    # (c) Stability step.
    stability = compute_stability(
        root,
        runs=runs,
        perturbation=perturbation,
        seed=seed,
        config_path=config_path,
    )

    # (d) Performance.
    performance = {
        "timings": dict(result.timings),
        "peak_memory_mb": result.peak_memory_mb,
    }

    # (e) Corpus metadata.
    corpus_metadata = {
        "n_files": len(result.files),
        "n_embedded": n_files,
        "root": str(root),
    }

    char_result = CharacterizationResult(
        root=str(root),
        corpus_metadata=corpus_metadata,
        config=dict(cfg),
        structure=structure,
        stability=stability,
        performance=performance,
        notes=notes,
    )

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = out / f"characterize_{timestamp}.json"
    out_path.write_text(
        json.dumps(char_result.to_dict(), indent=2, default=str),
        encoding="utf-8",
    )

    return char_result
