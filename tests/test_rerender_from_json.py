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
        f"photo_{tag}_trip_paris_01.jpg",
        f"photo_{tag}_trip_rome_01.jpg",
        f"code_{tag}_project_alpha.py",
        f"code_{tag}_project_beta.py",
    ]:
        _touch(root / n)


_SENSITIVITY = [
    ("clustering", "hdbscan", "min_cluster_size", [2, 3]),
    ("clustering", "kmeans", "top_k", [2, 3]),
]


def _multi(tmp_path: Path):
    from dynamic_folding.evaluation.multicorpus import run_multicorpus_comparison

    dirs = []
    for tag in ["alpha_sub", "beta_sub"]:
        d = tmp_path / tag
        _make_corpus(d, tag)
        dirs.append(d)
    return run_multicorpus_comparison(dirs, sensitivity_studies=_SENSITIVITY), dirs


def test_to_dict_from_dict_round_trips(tmp_path: Path) -> None:
    from dynamic_folding.evaluation.multicorpus import MultiCorpusComparison

    multi, _ = _multi(tmp_path)
    rebuilt = MultiCorpusComparison.from_dict(multi.to_dict())
    # Frozen dataclasses generate __eq__ — the whole tree compares by value.
    assert rebuilt == multi


def test_projection_coords_are_serialized(tmp_path: Path) -> None:
    multi, _ = _multi(tmp_path)
    for item in multi.to_dict()["items"]:
        proj = item["result"]["projection"]
        if proj is not None and proj.get("coords"):
            assert all(len(c) == 2 for c in proj["coords"])  # N x 2, exported (lossless)


def test_render_from_reconstructed_multi(tmp_path: Path) -> None:
    from dynamic_folding.evaluation.multicorpus import MultiCorpusComparison
    from dynamic_folding.evaluation.multicorpus_report import render_multicorpus_html

    multi, _ = _multi(tmp_path)
    rebuilt = MultiCorpusComparison.from_dict(multi.to_dict())
    out = tmp_path / "rerender.html"
    render_multicorpus_html(rebuilt, out)  # figure may degrade (matplotlib) — not required
    html = out.read_text(encoding="utf-8")

    assert "http://" not in html and "https://" not in html
    for m in re.finditer(r"src=['\"]", html):
        assert html[m.end():].startswith("data:")
    assert "Comparação entre os corpus" in html
    assert "Corpus 1" in html and "Corpus 2" in html


def test_cli_from_json_renders_without_pipeline(tmp_path: Path) -> None:
    from dynamic_folding.cli import main

    d1 = tmp_path / "c1"; _make_corpus(d1, "c1")
    d2 = tmp_path / "c2"; _make_corpus(d2, "c2")
    js = tmp_path / "multi.json"
    # Compute once (FakeEmbedder default), write JSON.
    assert main(["compare-multi", str(d1), str(d2), "--json", str(js)]) == 0
    assert js.exists()
    # Re-render from JSON only — no directories, no pipeline.
    out = tmp_path / "rr.html"
    assert main(["compare-multi", "--from-json", str(js), "--html", str(out)]) == 0
    html = out.read_text(encoding="utf-8")
    assert "Corpus 1" in html and "Comparação entre os corpus" in html


def test_cli_rejects_both_paths_and_from_json(tmp_path: Path) -> None:
    from dynamic_folding.cli import main

    d1 = tmp_path / "c1"; _make_corpus(d1, "c1")
    js = tmp_path / "x.json"; js.write_text("{}", encoding="utf-8")
    assert main(["compare-multi", str(d1), "--from-json", str(js)]) == 2
