from __future__ import annotations

import re
from pathlib import Path


def _touch(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"x")


def _make_corpus(root: Path, tag: str) -> None:
    for n in [
        f"invoice_{tag}_2023_jan.pdf",
        f"invoice_{tag}_2023_feb.pdf",
        f"invoice_{tag}_2024_jan.pdf",
        f"photo_{tag}_trip_paris_01.jpg",
        f"photo_{tag}_trip_paris_02.jpg",
        f"photo_{tag}_trip_rome_01.jpg",
        f"code_{tag}_project_alpha.py",
        f"code_{tag}_project_beta.py",
        f"code_{tag}_project_gamma.py",
    ]:
        _touch(root / n)


_SENSITIVITY_STUDIES = [
    ("clustering", "hdbscan", "min_cluster_size", [2, 3]),
    ("clustering", "kmeans", "top_k", [2, 3]),
    ("clustering", "agglomerative_tree", "min_cluster_size", [2, 3]),
]


def _multi(tmp_path: Path):
    from dynamic_folding.evaluation.multicorpus import run_multicorpus_comparison

    dirs = []
    for i, tag in enumerate(["alpha_subdir", "beta_subdir", "gamma_subdir"]):
        d = tmp_path / tag
        _make_corpus(d, tag)
        dirs.append(d)

    return run_multicorpus_comparison(
        dirs,
        sensitivity_studies=_SENSITIVITY_STUDIES,
    ), dirs


def test_run_multicorpus_comparison_returns_three_labeled_entries(tmp_path: Path) -> None:
    multi, dirs = _multi(tmp_path)

    assert len(multi.items) == 3
    labels = [label for label, _ in multi.items]
    assert labels == ["Corpus 1", "Corpus 2", "Corpus 3"]

    # Anonymization: the ComparisonResult.root itself must carry the label,
    # not the real path (so downstream sections never see the real dir name).
    for label, res in multi.items:
        assert res.root == label


def test_multicorpus_html_is_self_contained(tmp_path: Path) -> None:
    from dynamic_folding.evaluation.multicorpus_report import render_multicorpus_html

    multi, dirs = _multi(tmp_path)
    out = tmp_path / "multi.html"
    render_multicorpus_html(multi, out)

    assert out.exists()
    html = out.read_text(encoding="utf-8")

    assert "http://" not in html
    assert "https://" not in html
    for m in re.finditer(r"src=['\"]", html):
        assert html[m.end():].startswith("data:"), "non-inline src reference"
    assert 'href="' not in html


def test_multicorpus_html_anonymizes_real_dir_names(tmp_path: Path) -> None:
    from dynamic_folding.evaluation.multicorpus_report import render_multicorpus_html

    multi, dirs = _multi(tmp_path)
    out = tmp_path / "multi.html"
    render_multicorpus_html(multi, out)
    html = out.read_text(encoding="utf-8")

    for d in dirs:
        assert d.name not in html
        assert str(d) not in html

    assert "Corpus 1" in html
    assert "Corpus 2" in html
    assert "Corpus 3" in html


def test_multicorpus_html_has_aggregate_section(tmp_path: Path) -> None:
    from dynamic_folding.evaluation.multicorpus_report import render_multicorpus_html

    multi, dirs = _multi(tmp_path)
    out = tmp_path / "multi.html"
    render_multicorpus_html(multi, out)
    html = out.read_text(encoding="utf-8")

    assert "Comparação entre os corpus" in html
    for label in ("Corpus 1", "Corpus 2", "Corpus 3"):
        assert label in html
    for algo in ("hdbscan", "kmeans", "agglomerative_tree"):
        assert algo in html
    assert "silhueta" in html.lower()
    assert "dbcv" in html.lower()
    assert "estrutural" in html.lower()
    # A prosa (leitura transversal + limitações) é autoral e já foi escrita —
    # o relatório não deve mais conter nenhum placeholder de "a escrever".
    assert "[A ESCREVER PELO AUTOR" not in html


def test_multicorpus_html_has_per_corpus_blocks(tmp_path: Path) -> None:
    from dynamic_folding.evaluation.multicorpus_report import render_multicorpus_html

    multi, dirs = _multi(tmp_path)
    out = tmp_path / "multi.html"
    render_multicorpus_html(multi, out)
    html = out.read_text(encoding="utf-8")

    # Slimmed structure (ADR 0045 amended — "médio: dedup só do idêntico"):
    # matrices + reducer stay per-corpus (3x, different data), but the figure and
    # the provenance are deduplicated to a single shared instance.
    assert html.count("Matrizes por algoritmo") == 3
    assert "min_cluster_size" in html
    assert html.count("Figura ilustrativa") == 1
    assert html.count("Procedência e configuração efetiva") == 1


def test_multicorpus_html_does_not_inherit_n1_prose(tmp_path: Path) -> None:
    from dynamic_folding.evaluation.multicorpus_report import render_multicorpus_html

    multi, dirs = _multi(tmp_path)
    out = tmp_path / "multi.html"
    render_multicorpus_html(multi, out)
    html = out.read_text(encoding="utf-8")

    assert "n=1" not in html
