"""Sprint 19: Stability characterization (pair-co-occurrence under input perturbation).

Implements the "fast smart way": run scan->extract->preprocess->embed ONCE
on the full corpus, then for each stability run sample at the embedding
level (drop a random fraction of vectors) and re-cluster only.

Justification: extraction and embedding are deterministic by design, so
re-running them adds no new instability. The clusterer is the only source
of variance, which is exactly the property characterized here.

See ADR 0018 and SPEC Sprint 19.
"""
from __future__ import annotations

import itertools
from pathlib import Path

import numpy as np

from dynamic_folding.contracts.stability import StabilityReport
from dynamic_folding.core.pipeline import resolve_effective_config, run_pipeline
from dynamic_folding.core.registries import CLUSTERERS


def compute_stability(
    root: Path,
    *,
    runs: int,
    perturbation: float,
    seed: int,
    config_path: Path | None = None,
) -> StabilityReport:
    root = Path(root).resolve()

    if runs < 2:
        return StabilityReport(
            root=str(root),
            runs=runs,
            perturbation=perturbation,
            seed=seed,
            pair_co_occurrence=1.0,
            evaluable_pairs=0,
            notes=["stability requires runs>=2; returning trivial 1.0"],
        )

    cfg = resolve_effective_config(root, config_path=config_path)
    cl_cfg = dict(cfg.get("clustering", {}))
    algo = str(cl_cfg.get("algorithm", "kmeans")).strip().lower()

    result = run_pipeline(root, config_path=config_path)
    vectors = [list(e.vector) for e in result.embeddings]
    paths = [e.file.rel_path for e in result.embeddings]
    n_files = len(paths)

    if n_files < 2:
        return StabilityReport(
            root=str(root),
            runs=runs,
            perturbation=perturbation,
            seed=seed,
            pair_co_occurrence=1.0,
            evaluable_pairs=0,
            notes=["fewer than 2 embeddable files; pair-co-occurrence undefined"],
        )

    clusterer = CLUSTERERS.create(algo, {})

    per_run_labels: list[dict[str, int]] = []
    for i in range(runs):
        rng = np.random.default_rng(seed + i)
        keep_mask = rng.random(n_files) >= perturbation
        kept_idx = [j for j, keep in enumerate(keep_mask) if keep]
        kept_vecs = [vectors[j] for j in kept_idx]
        kept_paths = [paths[j] for j in kept_idx]
        if not kept_vecs:
            per_run_labels.append({})
            continue
        labels = clusterer(kept_vecs, cl_cfg).labels
        per_run_labels.append(dict(zip(kept_paths, labels)))

    survivor_sets = [set(d.keys()) for d in per_run_labels]
    survivors = sorted(set.intersection(*survivor_sets)) if survivor_sets else []

    if len(survivors) < 2:
        return StabilityReport(
            root=str(root),
            runs=runs,
            perturbation=perturbation,
            seed=seed,
            pair_co_occurrence=1.0,
            evaluable_pairs=0,
            notes=["too few all-runs survivors; perturbation may be too high for corpus size"],
        )

    # Per-pair stability: 1 - 4*p*(1-p), where p = fraction of runs the pair
    # is co-clustered. Yields 1 when the pair is consistently grouped (always
    # same or always apart) and 0 when the decision is a coin flip.
    # See docs/learning/01-stability-metric.md for the rationale.
    total = 0.0
    pair_count = 0
    for a, b in itertools.combinations(survivors, 2):
        agree = sum(1 for d in per_run_labels if d[a] == d[b])
        p = agree / runs
        total += 1.0 - 4.0 * p * (1.0 - p)
        pair_count += 1

    return StabilityReport(
        root=str(root),
        runs=runs,
        perturbation=perturbation,
        seed=seed,
        pair_co_occurrence=total / pair_count,
        evaluable_pairs=pair_count,
        notes=[],
    )
