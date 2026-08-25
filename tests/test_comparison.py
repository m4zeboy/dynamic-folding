from __future__ import annotations

from pathlib import Path


def _touch(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"x")


def _make_corpus(tmp_path: Path) -> None:
    # Three filename-themed groups so kmeans (k=top_k) has structure to find.
    for n in [
        "invoice_2023_jan.pdf",
        "invoice_2023_feb.pdf",
        "invoice_2024_jan.pdf",
        "photo_trip_paris_01.jpg",
        "photo_trip_paris_02.jpg",
        "photo_trip_rome_01.jpg",
        "code_project_alpha.py",
        "code_project_beta.py",
        "code_project_gamma.py",
    ]:
        _touch(tmp_path / n)


# Small per-algorithm knob sweeps that stay valid on the 9-file fixture.
_STUDIES = [
    ("clustering", "hdbscan", "min_cluster_size", [2, 3, 4]),
    ("clustering", "kmeans", "top_k", [2, 3]),
    ("reducer", "hdbscan", "n_components", [2, 3]),
]


def test_run_comparison_shape(tmp_path: Path) -> None:
    from dynamic_folding.evaluation.comparison import (
        COMPARISON_ALGORITHMS,
        run_comparison,
    )

    _make_corpus(tmp_path)
    res = run_comparison(tmp_path, sensitivity_studies=_STUDIES)

    # All three candidate algorithms ran, in a stable order.
    assert [a.algorithm for a in res.algorithms] == list(COMPARISON_ALGORITHMS)

    for a in res.algorithms:
        # Structural descriptors are always present (these are what compare).
        assert isinstance(a.n_groups, int)
        assert isinstance(a.n_files_scored, int)
        assert isinstance(a.n_outliers, int)
        assert a.n_total == a.n_files_scored + a.n_outliers
        # Silhouette is a per-algorithm descriptor: float, or None when degenerate.
        assert a.score is None or isinstance(a.score, float)
        # DBCV is the second-lens descriptor: float, or None when degenerate.
        assert a.dbcv_score is None or isinstance(a.dbcv_score, float)
        # Provenance reflects the truth: this algorithm + the naming-agnostic namer.
        assert a.effective_config["clustering"]["algorithm"] == a.algorithm
        assert a.effective_config["naming"]["provider"] == "tfidf"

    # One sensitivity study per requested (stage, algorithm, parameter), in order.
    assert [(s.stage, s.algorithm, s.parameter) for s in res.sensitivities] == [
        ("clustering", "hdbscan", "min_cluster_size"),
        ("clustering", "kmeans", "top_k"),
        ("reducer", "hdbscan", "n_components"),
    ]
    hdb, km, red = res.sensitivities
    assert [r.value for r in hdb.rows] == [2, 3, 4]
    assert [r.value for r in km.rows] == [2, 3]
    assert [r.value for r in red.rows] == [2, 3]
    for study in res.sensitivities:
        for r in study.rows:
            assert r.score is None or isinstance(r.score, float)
            assert r.n_total == r.n_files_scored + r.n_outliers
            if study.stage == "reducer":
                assert r.dbcv_score is None  # no DBCV in the reducer sweep (space varies)
            else:
                assert r.dbcv_score is None or isinstance(r.dbcv_score, float)
    # kmeans assigns every file (no outlier bucket): coverage is full, K groups.
    for r in km.rows:
        assert r.n_outliers == 0
        assert r.n_groups == r.value


def test_run_comparison_populates_projection(tmp_path: Path) -> None:
    from dynamic_folding.evaluation.comparison import run_comparison

    _make_corpus(tmp_path)
    res = run_comparison(tmp_path, sensitivity_studies=_STUDIES)

    # The illustrative figure's data comes from the default (hdbscan) run, in the
    # 384-dim embedding space — pure data, computed regardless of matplotlib.
    assert res.projection is not None
    assert res.projection.space == "embeddings"
    if res.projection.coords:  # defined unless the tiny corpus degenerates
        assert len(res.projection.coords) == res.n_files
        assert len(res.projection.labels) == res.n_files


def test_comparison_is_deterministic(tmp_path: Path) -> None:
    from dynamic_folding.evaluation.comparison import run_comparison

    _make_corpus(tmp_path)
    a = run_comparison(tmp_path, sensitivity_studies=_STUDIES)
    b = run_comparison(tmp_path, sensitivity_studies=_STUDIES)

    def _key(res):
        algo = [
            (x.algorithm, x.score, x.dbcv_score, x.n_groups, x.n_outliers, x.n_files_scored)
            for x in res.algorithms
        ]
        sens = [
            (s.stage, s.algorithm, s.parameter, r.value, r.score, r.dbcv_score, r.n_groups, r.n_outliers)
            for s in res.sensitivities
            for r in s.rows
        ]
        return algo + sens

    assert _key(a) == _key(b)


def test_format_comparison_text_does_not_rank_silhouette(tmp_path: Path) -> None:
    from dynamic_folding.evaluation.comparison import (
        format_comparison_text,
        run_comparison,
    )

    _make_corpus(tmp_path)
    txt = format_comparison_text(run_comparison(tmp_path, sensitivity_studies=_STUDIES))

    assert "hdbscan" in txt and "kmeans" in txt and "agglomerative_tree" in txt
    # Both lenses appear; silhouette is framed as a per-algorithm descriptor, not a ranking.
    assert "descritor" in txt.lower()
    assert "dbcv" in txt.lower()
    # The structural descriptors are present (they do the comparing).
    assert "cobertura" in txt.lower()
    # All sensitivity studies are rendered (knob names + the reducer stage appear).
    assert "min_cluster_size" in txt and "top_k" in txt
    assert "n_components" in txt and "redutor" in txt.lower()
