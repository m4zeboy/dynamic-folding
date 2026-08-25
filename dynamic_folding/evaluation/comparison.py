"""Compare clustering algorithms on one corpus + first hyperparameter
sensitivity cuts — the first empirical pass of thesis Chapter 4.

Honesty constraints baked in (ADR 0038; docs/learning/02-experimental-scope.md):

- **Silhouette is a PER-ALGORITHM descriptor, never a cross-algorithm ranking.**
  The algorithms differ in number of groups, coverage and outlier handling, so
  each one's silhouette is measured over a *different* set of files and the
  numbers are not comparable. The cross-algorithm comparison rests on the
  **structural descriptors** (n_groups, n_outliers, coverage).
- **Naming-agnostic.** Naming sets display labels only — never cluster
  membership — so we force the deterministic, offline ``tfidf`` namer. This keeps
  the comparison reproducible and offline without changing any number.
- **Faithful provenance.** Every run records the exact effective config that
  produced it (the applied overrides included).
- **Robust.** A run that raises does not abort the comparison; it becomes a row
  with ``score=None`` and a reason.

Two lenses now (silhouette + DBCV) on one corpus (n=1): exploratory, no verdict. The
report presents each algorithm as a matrix (knob sweep x all metrics; no elected
execution — ADR 0041). A controlled geometric comparison (common file set + matched K)
is a possible next pass.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dynamic_folding.core.pipeline import resolve_effective_config, run_pipeline
from dynamic_folding.evaluation.dbcv import dbcv_of_run
from dynamic_folding.evaluation.projection import Projection2D, project_2d
from dynamic_folding.evaluation.silhouette import (
    silhouette_baseline_of_run,
    silhouette_of_run,
)

# The candidate algorithms, in a stable order for reproducible tables. The
# ``random`` clusterer is a baseline, not a candidate, so it is excluded.
COMPARISON_ALGORITHMS: tuple[str, ...] = ("hdbscan", "kmeans", "agglomerative_tree")

# Sensitivity cuts: one knob at a time (ADR 0018 property #3 — responsiveness, not
# optimization). EACH clustering algorithm gets a sweep, so the report shows the full
# variation per algorithm (a matrix) instead of one elected execution: hdbscan and
# agglomerative_tree both expose ``min_cluster_size`` (different roles — density core vs
# tree-cut threshold — so it is loose alignment, not a controlled comparison); kmeans has
# a fixed K, swept as ``top_k`` over a wider range (the lighter algorithm carries the
# heavier sweep). The reducer enters lightly — a single knob, ``n_components`` — clusterer
# pinned to the default (ADR 0040 amends 0038's "reducer stays background"); n_neighbors
# and min_dist are discussed in prose only. Each entry:
# (stage, algorithm, config-key, values); stage in {"clustering", "reducer"}.
DEFAULT_SENSITIVITY_STUDIES: tuple[tuple[str, str, str, tuple[int, ...]], ...] = (
    ("clustering", "hdbscan", "min_cluster_size", (2, 3, 4, 5, 6, 7, 8)),
    ("clustering", "kmeans", "top_k", (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15)),
    ("clustering", "agglomerative_tree", "min_cluster_size", (2, 3, 4, 5, 6, 7, 8)),
    ("reducer", "hdbscan", "n_components", (5, 10, 15, 20)),
)


@dataclass(frozen=True)
class AlgorithmResult:
    algorithm: str
    # Per-algorithm descriptor (None when the partition is degenerate / failed).
    score: float | None
    baseline_mean: float | None
    baseline_std: float | None
    gap: float | None
    # DBCV — the second lens (density bias), scored in the reduced clustering space.
    # A SEPARATE, non-comparable descriptor: different space AND bias than silhouette
    # (read asymmetrically — it is the most charitable setting for HDBSCAN; see ADR 0039).
    dbcv_score: float | None
    dbcv_reason: str | None
    # Structural descriptors — these are what compare across algorithms.
    n_groups: int
    n_files_scored: int
    n_outliers: int
    n_total: int
    group_sizes: list[int]
    reason: str | None
    effective_config: dict  # exact clustering/naming/embedding/reducer used

    def to_dict(self) -> dict:
        return {
            "algorithm": self.algorithm,
            "score": self.score,
            "baseline_mean": self.baseline_mean,
            "baseline_std": self.baseline_std,
            "gap": self.gap,
            "dbcv_score": self.dbcv_score,
            "dbcv_reason": self.dbcv_reason,
            "n_groups": self.n_groups,
            "n_files_scored": self.n_files_scored,
            "n_outliers": self.n_outliers,
            "n_total": self.n_total,
            "group_sizes": self.group_sizes,
            "reason": self.reason,
            "effective_config": self.effective_config,
        }


@dataclass(frozen=True)
class SensitivityRow:
    value: int  # the knob value under test
    score: float | None
    n_groups: int
    n_files_scored: int
    n_outliers: int
    n_total: int
    reason: str | None
    # Second lens — populated only for clustering sweeps (the reduced space is fixed there,
    # so DBCV is comparable down the column). None for reducer sweeps, whose space changes
    # per row (a DBCV column there would compare different metric spaces). See ADR 0039/0040.
    dbcv_score: float | None = None
    dbcv_reason: str | None = None

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "score": self.score,
            "n_groups": self.n_groups,
            "n_files_scored": self.n_files_scored,
            "n_outliers": self.n_outliers,
            "n_total": self.n_total,
            "reason": self.reason,
            "dbcv_score": self.dbcv_score,
            "dbcv_reason": self.dbcv_reason,
        }


@dataclass(frozen=True)
class SensitivityStudy:
    algorithm: str  # the clusterer in effect (varied for clustering studies; pinned for reducer studies)
    parameter: str  # the config key varied (e.g. min_cluster_size, top_k, n_components)
    rows: list[SensitivityRow]
    stage: str = "clustering"  # which config section `parameter` lives in: "clustering" or "reducer"

    def to_dict(self) -> dict:
        return {
            "algorithm": self.algorithm,
            "parameter": self.parameter,
            "stage": self.stage,
            "rows": [r.to_dict() for r in self.rows],
        }


@dataclass(frozen=True)
class ComparisonResult:
    root: str
    n_files: int
    algorithms: list[AlgorithmResult]
    sensitivities: list[SensitivityStudy]
    base_config_source: str
    version: str
    # Illustrative figure data: the default run's points projected to 2D (ADR 0042).
    # None if the projection failed; a local DTO field, so docs/CONTRACTS.md is unchanged.
    projection: Projection2D | None = None

    def to_dict(self) -> dict:
        return {
            "root": self.root,
            "n_files": self.n_files,
            "algorithms": [a.to_dict() for a in self.algorithms],
            "sensitivities": [s.to_dict() for s in self.sensitivities],
            "base_config_source": self.base_config_source,
            "version": self.version,
            # Coords ARE included (lossless): so the report can be re-rendered from
            # this JSON without re-running the pipeline (compare-multi --from-json).
            "projection": (
                None
                if self.projection is None
                else {
                    "coords": self.projection.coords,
                    "labels": self.projection.labels,
                    "group_names": self.projection.group_names,
                    "space": self.projection.space,
                    "explained_variance": self.projection.explained_variance,
                    "n_outliers": self.projection.n_outliers,
                    "reason": self.projection.reason,
                }
            ),
        }


def _curate_config(eff: dict) -> dict:
    """The subset of the effective config that actually shaped the numbers.

    Faithful to what ran (no generic 'config/default.toml' reference): the
    clustering knobs, the naming provider, the embedding identity, the reducer.
    """
    emb = eff.get("embedding", {})
    return {
        "clustering": dict(eff.get("clustering", {})),
        "naming": {"provider": str(eff.get("naming", {}).get("provider", ""))},
        "embedding": {
            "provider": str(emb.get("provider", "")),
            "model_path": emb.get("model_path"),
        },
        "reducer": dict(eff.get("reducer", {})),
    }


def _overrides(
    algorithm: str, *, stage: str = "clustering",
    parameter: str | None = None, value: int | None = None,
) -> dict:
    """Config overrides for one run: pick the algorithm, force the offline
    naming-agnostic namer, and (optionally) set the knob under test. ``stage`` says
    which config section the knob lives in — a clustering key, or a reducer key (with
    the clusterer pinned to ``algorithm`` so the reducer sweep has a fixed backdrop).
    """
    clustering: dict = {"algorithm": algorithm}
    overrides: dict = {"clustering": clustering, "naming": {"provider": "tfidf"}}
    if parameter is not None and value is not None:
        if stage == "reducer":
            overrides["reducer"] = {parameter: int(value)}
        else:
            clustering[parameter] = int(value)
    return overrides


def _measure_one(
    root: Path, *, config_path: Path | None, algorithm: str
) -> AlgorithmResult:
    overrides = _overrides(algorithm)
    try:
        result = run_pipeline(root, config_path=config_path, overrides=overrides)
        base = silhouette_baseline_of_run(result)
        sil = base.real
        dbcv = dbcv_of_run(result)
        eff = resolve_effective_config(root, config_path=config_path, overrides=overrides)
        return AlgorithmResult(
            algorithm=algorithm,
            score=sil.score,
            baseline_mean=base.baseline_mean,
            baseline_std=base.baseline_std,
            gap=base.gap,
            dbcv_score=dbcv.score,
            dbcv_reason=dbcv.reason,
            n_groups=sil.n_groups,
            n_files_scored=sil.n_files_scored,
            n_outliers=sil.n_outliers,
            n_total=sil.n_files_scored + sil.n_outliers,
            group_sizes=[g.n_files for g in sil.per_group],
            reason=sil.reason,
            effective_config=_curate_config(eff),
        )
    except Exception as exc:  # a broken algorithm must not abort the comparison
        return AlgorithmResult(
            algorithm=algorithm,
            score=None,
            baseline_mean=None,
            baseline_std=None,
            gap=None,
            dbcv_score=None,
            dbcv_reason=f"run failed: {exc}",
            n_groups=0,
            n_files_scored=0,
            n_outliers=0,
            n_total=0,
            group_sizes=[],
            reason=f"run failed: {exc}",
            effective_config={},
        )


def _measure_sensitivity_row(
    root: Path, *, config_path: Path | None, stage: str, algorithm: str, parameter: str, value: int
) -> SensitivityRow:
    overrides = _overrides(algorithm, stage=stage, parameter=parameter, value=value)
    try:
        result = run_pipeline(root, config_path=config_path, overrides=overrides)
        sil = silhouette_of_run(result)
        # DBCV only for clustering sweeps: there the reduced space is fixed (comparable down
        # the column). The reducer sweep changes the space per row, so it gets no DBCV.
        dbcv = dbcv_of_run(result) if stage == "clustering" else None
        return SensitivityRow(
            value=value,
            score=sil.score,
            n_groups=sil.n_groups,
            n_files_scored=sil.n_files_scored,
            n_outliers=sil.n_outliers,
            n_total=sil.n_files_scored + sil.n_outliers,
            reason=sil.reason,
            dbcv_score=dbcv.score if dbcv else None,
            dbcv_reason=dbcv.reason if dbcv else None,
        )
    except Exception as exc:
        return SensitivityRow(
            value=value,
            score=None,
            n_groups=0,
            n_files_scored=0,
            n_outliers=0,
            n_total=0,
            reason=f"run failed: {exc}",
        )


# The illustrative figure shows ONLY the default algorithm (ADR 0042): three
# colourings side by side would invite a visual verdict, against outcome-independence.
_FIGURE_ALGORITHM = "hdbscan"


def _measure_projection(root: Path, *, config_path: Path | None) -> Projection2D | None:
    """2D projection of the default run's points, for the illustrative figure.

    A dedicated run of the default algorithm (cheap — the embeddings are cached),
    projected in the 384-dim embedding space. Failure yields None (the report shows a
    visible note), never aborting the comparison.
    """
    try:
        result = run_pipeline(
            root, config_path=config_path, overrides=_overrides(_FIGURE_ALGORITHM)
        )
        return project_2d(result)
    except Exception:
        return None


def run_comparison(
    root: Path | str,
    *,
    config_path: Path | None = None,
    sensitivity_studies: list[tuple[str, str, str, list[int]]] | None = None,
) -> ComparisonResult:
    """Run the first comparison pass: each algorithm + per-algorithm knob sweeps.

    Deterministic and offline (naming forced to ``tfidf``). The embedding cache
    makes the repeated pipeline runs cheap (only reducer+clustering+proposal
    re-run per variant).
    """
    from dynamic_folding import __version__

    root = Path(root).resolve()
    studies_spec = sensitivity_studies if sensitivity_studies is not None else [
        (stage, algo, param, list(values))
        for stage, algo, param, values in DEFAULT_SENSITIVITY_STUDIES
    ]

    algorithms = [
        _measure_one(root, config_path=config_path, algorithm=algo)
        for algo in COMPARISON_ALGORITHMS
    ]

    sensitivities = [
        SensitivityStudy(
            algorithm=algo,
            parameter=param,
            stage=stage,
            rows=[
                _measure_sensitivity_row(
                    root, config_path=config_path, stage=stage, algorithm=algo,
                    parameter=param, value=v,
                )
                for v in values
            ],
        )
        for stage, algo, param, values in studies_spec
    ]

    # Every run embeds the same files, so any successful run's total is the
    # corpus size; fall back to 0 if all failed.
    n_files = next((a.n_total for a in algorithms if a.n_total), 0)
    projection = _measure_projection(root, config_path=config_path)

    return ComparisonResult(
        root=str(root),
        n_files=n_files,
        algorithms=algorithms,
        sensitivities=sensitivities,
        base_config_source=str(config_path) if config_path else "(system defaults)",
        version=__version__,
        projection=projection,
    )


# ---------------------------------------------------------------------------
# Text rendering (verify the numbers before any HTML)
# ---------------------------------------------------------------------------

def _coverage(scored: int, total: int) -> str:
    if total <= 0:
        return "0/0"
    return f"{scored}/{total} ({round(100 * scored / total)}%)"


def _fmt_score(score: float | None, reason: str | None) -> str:
    if score is None:
        return f"n/a ({reason or 'indefinida'})"
    return f"{score:+.3f}"


def format_comparison_text(res: ComparisonResult) -> str:
    lines: list[str] = []
    lines.append(
        f"Comparação de algoritmos em {res.root}  ({res.n_files} arquivos)  —  v{res.version}"
    )
    lines.append(
        f"Config base: {res.base_config_source}  |  nomeação: tfidf "
        f"(naming-agnostic, determinística)"
    )
    lines.append("")
    lines.append(
        "A silhueta abaixo é um DESCRITOR por algoritmo (cada um medido sobre um"
    )
    lines.append(
        "conjunto de arquivos diferente) — NÃO um ranking. Quem compara os"
    )
    lines.append("algoritmos são os descritores estruturais.")
    lines.append("")

    # --- Structural comparison (this is the cross-algorithm comparison) ---
    lines.append("Estrutural (compara os algoritmos):")
    lines.append(f"  {'algoritmo':<20}{'grupos':>8}{'outliers':>10}{'cobertura':>16}")
    for a in res.algorithms:
        lines.append(
            f"  {a.algorithm:<20}{a.n_groups:>8}{a.n_outliers:>10}"
            f"{_coverage(a.n_files_scored, a.n_total):>16}"
        )
    lines.append("")

    # --- Per-algorithm silhouette descriptor (NOT to be compared row-to-row) ---
    lines.append("Silhueta por algoritmo (descritor; não comparar entre linhas):")
    for a in res.algorithms:
        base = ""
        if a.score is not None and a.baseline_mean is not None:
            base = (
                f"  [piso aleatório {a.baseline_mean:+.3f} ± {a.baseline_std:.3f}; "
                f"gap {a.gap:+.3f}]"
            )
        lines.append(
            f"  {a.algorithm:<20}{_fmt_score(a.score, a.reason)}"
            f"  sobre {a.n_files_scored} arquivos, {a.n_groups} grupos{base}"
        )

    # --- DBCV: second lens (density bias), scored in the reduced space (descriptor) ---
    lines.append("")
    lines.append("DBCV por algoritmo (2ª lente, densidade, espaço reduzido; descritor):")
    for a in res.algorithms:
        lines.append(f"  {a.algorithm:<20}{_fmt_score(a.dbcv_score, a.dbcv_reason)}")

    # --- Sensitivity studies (one lens: responsiveness to the knob, not 'better') ---
    for study in res.sensitivities:
        lines.append("")
        subject = (
            f"redutor {study.parameter} (clusterer {study.algorithm})"
            if study.stage == "reducer"
            else f"{study.algorithm}, {study.parameter}"
        )
        lines.append(
            f"Sensibilidade — {subject} "
            f"(1 lente: responde ao knob, não significa 'melhor'):"
        )
        lines.append(
            f"  {study.parameter:>16}{'silhueta':>12}{'grupos':>8}"
            f"{'outliers':>10}{'cobertura':>16}"
        )
        for r in study.rows:
            score = _fmt_score(r.score, r.reason) if r.score is not None else "n/a"
            lines.append(
                f"  {r.value:>16}{score:>12}{r.n_groups:>8}{r.n_outliers:>10}"
                f"{_coverage(r.n_files_scored, r.n_total):>16}"
            )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Reconstruction from a serialized to_dict() — for compare-multi --from-json
# (re-render the report without re-running the pipeline).
# ---------------------------------------------------------------------------

def algorithm_result_from_dict(d: dict) -> AlgorithmResult:
    return AlgorithmResult(
        algorithm=d["algorithm"],
        score=d.get("score"),
        baseline_mean=d.get("baseline_mean"),
        baseline_std=d.get("baseline_std"),
        gap=d.get("gap"),
        dbcv_score=d.get("dbcv_score"),
        dbcv_reason=d.get("dbcv_reason"),
        n_groups=int(d.get("n_groups", 0)),
        n_files_scored=int(d.get("n_files_scored", 0)),
        n_outliers=int(d.get("n_outliers", 0)),
        n_total=int(d.get("n_total", 0)),
        group_sizes=list(d.get("group_sizes", [])),
        reason=d.get("reason"),
        effective_config=dict(d.get("effective_config", {})),
    )


def sensitivity_row_from_dict(d: dict) -> SensitivityRow:
    return SensitivityRow(
        value=d["value"],
        score=d.get("score"),
        n_groups=int(d.get("n_groups", 0)),
        n_files_scored=int(d.get("n_files_scored", 0)),
        n_outliers=int(d.get("n_outliers", 0)),
        n_total=int(d.get("n_total", 0)),
        reason=d.get("reason"),
        dbcv_score=d.get("dbcv_score"),
        dbcv_reason=d.get("dbcv_reason"),
    )


def sensitivity_study_from_dict(d: dict) -> SensitivityStudy:
    return SensitivityStudy(
        algorithm=d["algorithm"],
        parameter=d["parameter"],
        rows=[sensitivity_row_from_dict(r) for r in d.get("rows", [])],
        stage=d.get("stage", "clustering"),
    )


def comparison_result_from_dict(d: dict) -> ComparisonResult:
    from dynamic_folding.evaluation.projection import Projection2D

    proj = d.get("projection")
    return ComparisonResult(
        root=d["root"],
        n_files=int(d.get("n_files", 0)),
        algorithms=[algorithm_result_from_dict(a) for a in d.get("algorithms", [])],
        sensitivities=[sensitivity_study_from_dict(s) for s in d.get("sensitivities", [])],
        base_config_source=d.get("base_config_source", ""),
        version=d.get("version", ""),
        projection=None if proj is None else Projection2D.from_dict(proj),
    )
