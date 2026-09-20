from __future__ import annotations

from pathlib import Path


def _touch(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"x")


def _make_corpus(tmp_path: Path) -> None:
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


def _result(tmp_path: Path):
    from dynamic_folding.evaluation.comparison import run_comparison

    return run_comparison(
        tmp_path,
        sensitivity_studies=[
            ("clustering", "hdbscan", "min_cluster_size", [2, 3]),
            ("clustering", "kmeans", "top_k", [2, 3]),
            ("clustering", "agglomerative_tree", "min_cluster_size", [2, 3]),
            ("reducer", "hdbscan", "n_components", [2, 3]),
        ],
    )


def test_report_is_self_contained(tmp_path: Path) -> None:
    from dynamic_folding.evaluation.comparison_report import render_comparison_html

    _make_corpus(tmp_path)
    out = tmp_path / "cmp.html"
    render_comparison_html(_result(tmp_path), out)

    assert out.exists()
    html = out.read_text(encoding="utf-8")
    # Offline / self-contained: no network references. Any src must be an inline
    # data: URI (e.g. the base64 figure under .[viz]), never a network/file ref.
    import re

    assert "http://" not in html
    assert "https://" not in html
    for m in re.finditer(r"src=['\"]", html):
        assert html[m.end():].startswith("data:"), "non-inline src reference"
    assert 'href="' not in html


def test_report_has_illustrative_figure_section(tmp_path: Path) -> None:
    from dynamic_folding.evaluation.comparison_report import render_comparison_html

    _make_corpus(tmp_path)
    out = tmp_path / "cmp.html"
    render_comparison_html(_result(tmp_path), out)
    html = out.read_text(encoding="utf-8")

    # The illustrative figure section exists; its caption is left as the user's prose.
    assert "Figura ilustrativa" in html
    assert "distribuição dos pontos" in html  # the authored caption is in place

    # Loud-not-silent: without matplotlib the report says how to enable the figure,
    # instead of dropping it silently.
    import importlib.util
    if importlib.util.find_spec("matplotlib") is None:
        assert ".[viz]" in html


def test_report_content_and_framing(tmp_path: Path) -> None:
    from dynamic_folding.evaluation.comparison_report import render_comparison_html

    _make_corpus(tmp_path)
    out = tmp_path / "cmp.html"
    render_comparison_html(_result(tmp_path), out)
    html = out.read_text(encoding="utf-8")

    # PT-BR + the honest framing.
    assert "Comparação de algoritmos" in html
    # descriptor-not-ranking framing (the matrices intro, in the user's words)
    assert "não como um ranking" in html.lower()
    assert "estrutural" in html.lower()  # structural descriptors do the comparing

    # All three algorithms and both sensitivity knobs are rendered.
    for a in ("hdbscan", "kmeans", "agglomerative_tree"):
        assert a in html
    assert "min_cluster_size" in html
    assert "top_k" in html
    # Reducer enters the sensitivity lightly (n_components); second lens (DBCV) present.
    assert "n_components" in html and "redutor" in html.lower()
    assert "dbcv" in html.lower()
    # New structure: per-algorithm matrices (no single elected execution) + reducer apart.
    assert "Matrizes por algoritmo" in html
    assert "Sensibilidade do redutor" in html

    # Provenance: naming-agnostic determinism note is present.
    assert "naming-agnostic" in html.lower() or "tfidf" in html
