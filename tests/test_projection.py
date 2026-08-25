"""Tests for the 2D PCA projection behind the illustrative comparison figure.

The projection is the PURE, deterministic data step (no matplotlib): it casts the
run's points to 2D via PCA so the report can draw "before / after grouping". It
must project the chosen space (384-dim embeddings by default, the ~10-dim reduced
vectors optionally), label the "Outros" outliers as -1, expose how lossy the 2D
shadow is (explained variance), and never crash on degenerate input
(CLAUDE.md robustness rule).
"""
from __future__ import annotations

import base64

import pytest

from dynamic_folding.contracts.embedding import EmbeddingRecord
from dynamic_folding.contracts.file_ref import FileRef
from dynamic_folding.contracts.proposal import FolderNode, StructureProposal
from dynamic_folding.contracts.run_result import RunResult
from dynamic_folding.evaluation.projection import project_2d


def _emb(rel: str, vec: list[float]) -> EmbeddingRecord:
    fr = FileRef(path=rel, rel_path=rel, is_dir=False, depth=0, name=rel,
                 ext="txt", size=1, ctime=None, mtime=None)
    return EmbeddingRecord(file=fr, vector=vec, model_id="t", content_hash=rel)


def _run(folders, rels, vecs, *, reduced=None) -> RunResult:
    """Build a RunResult. `vecs` are the embedding vectors and (by default) the
    reduced vectors too; pass reduced=[...] to give the reduced space a different
    geometry than the embeddings."""
    embeddings = [_emb(rel, list(v)) for rel, v in zip(rels, vecs)]
    rv = vecs if reduced is None else reduced
    return RunResult(
        root="r", files=[], extracted=[], preprocessed=[],
        embeddings=embeddings,
        reduced_vectors=[list(v) for v in rv],
        proposal=StructureProposal(root="r", folders=folders, orphans=[], notes=[]),
    )


def _two_group_run(dim: int = 5) -> RunResult:
    """Two separated blobs in `dim`-D, so PCA has real structure to project."""
    folders = [
        FolderNode(name="A", files=["a1", "a2", "a3"]),
        FolderNode(name="B", files=["b1", "b2", "b3"]),
    ]
    rels = ["a1", "a2", "a3", "b1", "b2", "b3"]
    a, b = [0.0] * dim, [10.0] * dim
    jit = lambda base, k: [x + 0.1 * k for x in base]
    vecs = [jit(a, 0), jit(a, 1), jit(a, 2), jit(b, 0), jit(b, 1), jit(b, 2)]
    return _run(folders, rels, vecs)


def test_projects_every_point_to_2d():
    proj = project_2d(_two_group_run())
    assert proj.reason is None
    assert len(proj.coords) == 6
    assert all(len(c) == 2 for c in proj.coords)
    assert len(proj.labels) == 6


def test_deterministic():
    run = _two_group_run()
    a, b = project_2d(run), project_2d(run)
    assert a.coords == b.coords
    assert a.explained_variance == b.explained_variance


def test_outliers_labeled_minus_one_and_counted_nested_flattened():
    folders = [
        FolderNode(name="A", files=["a1", "a2"],
                   subfolders=[FolderNode(name="A_sub", files=["a3"])]),
        FolderNode(name="B", files=["b1", "b2"]),
        FolderNode(name="Outros", display_name="Outros", files=["o1", "o2"]),
    ]
    rels = ["a1", "a2", "a3", "b1", "b2", "o1", "o2"]
    vecs = [[0.0, 0, 0], [0.1, 0, 0], [0.0, 0.1, 0],
            [9.0, 9, 9], [9.1, 9, 9],
            [5.0, 5, 5], [5.1, 5, 5]]
    proj = project_2d(_run(folders, rels, vecs))
    assert len(proj.coords) == 7          # every point projected, outliers included
    assert proj.n_outliers == 2
    assert sorted(set(proj.labels)) == [-1, 0, 1]
    assert proj.labels.count(-1) == 2
    assert set(proj.group_names) == {"A", "B"}
    # nested a3 counts under A, not as its own group
    assert proj.labels[rels.index("a3")] == proj.labels[rels.index("a1")]


def test_space_selects_source_vectors():
    # embeddings (4-D) and reduced (2-D) carry different geometry -> the two
    # projections must differ, proving `space` picks the source.
    folders = [
        FolderNode(name="A", files=["a1", "a2", "a3"]),
        FolderNode(name="B", files=["b1", "b2", "b3"]),
    ]
    rels = ["a1", "a2", "a3", "b1", "b2", "b3"]
    emb = [[0.0, 0, 0, 0], [0.1, 0, 0, 0], [0.0, 0.1, 0, 0],
           [9.0, 9, 9, 9], [9.1, 9, 9, 9], [9.0, 9.1, 9, 9]]
    red = [[0.0, 0.0], [0.0, 0.2], [0.0, 0.4],
           [5.0, 0.0], [5.0, 0.2], [5.0, 0.4]]
    run = _run(folders, rels, emb, reduced=red)
    pe = project_2d(run, space="embeddings")
    pr = project_2d(run, space="reduced")
    assert pe.space == "embeddings"
    assert pr.space == "reduced"
    assert pe.coords != pr.coords


def test_explained_variance_full_when_already_2d():
    # 2-D input projected to 2-D loses nothing -> ~100% variance explained.
    folders = [
        FolderNode(name="A", files=["a1", "a2", "a3"]),
        FolderNode(name="B", files=["b1", "b2", "b3"]),
    ]
    rels = ["a1", "a2", "a3", "b1", "b2", "b3"]
    vecs = [[0.0, 0.0], [1.0, 0.5], [0.2, 0.1], [9.0, 9.0], [9.5, 8.5], [9.1, 9.2]]
    proj = project_2d(_run(folders, rels, vecs))
    assert proj.explained_variance is not None
    assert proj.explained_variance > 0.99


def test_too_few_points_is_undefined_not_crash():
    folders = [FolderNode(name="A", files=["a1"])]
    proj = project_2d(_run(folders, ["a1"], [[1.0, 2.0, 3.0]]))
    assert proj.coords == []
    assert proj.reason is not None


def test_one_dimensional_input_is_undefined_not_crash():
    # Can't form 2 components from 1-D data; must degrade, not raise.
    folders = [
        FolderNode(name="A", files=["a1", "a2"]),
        FolderNode(name="B", files=["b1", "b2"]),
    ]
    rels = ["a1", "a2", "b1", "b2"]
    proj = project_2d(_run(folders, rels, [[0.0], [0.1], [9.0], [9.1]]))
    assert proj.coords == []
    assert proj.reason is not None


def test_zero_variance_points_do_not_crash():
    # Identical points -> degenerate variance; must not raise.
    folders = [
        FolderNode(name="A", files=["a1", "a2"]),
        FolderNode(name="B", files=["b1", "b2"]),
    ]
    rels = ["a1", "a2", "b1", "b2"]
    proj = project_2d(_run(folders, rels, [[1.0, 1.0, 1.0]] * 4))
    assert len(proj.coords) == 4  # no crash; points returned


# --- render_png: the optional matplotlib drawing step ------------------------

def test_render_returns_none_without_matplotlib(monkeypatch):
    # The graceful-skip path: forced even when matplotlib *is* installed, so the
    # behaviour is verified everywhere (the report shows a note on None).
    import dynamic_folding.evaluation.projection as proj_mod
    monkeypatch.setattr(proj_mod, "_load_pyplot", lambda: None)
    assert proj_mod.render_png(project_2d(_two_group_run())) is None


def test_render_returns_none_for_empty_projection():
    # Degenerate projection (no coords) -> nothing to draw, regardless of matplotlib.
    from dynamic_folding.evaluation.projection import render_png
    proj = project_2d(_run([FolderNode(name="A", files=["a1"])], ["a1"], [[1.0, 2.0, 3.0]]))
    assert render_png(proj) is None


def test_render_produces_base64_png():
    pytest.importorskip("matplotlib")
    from dynamic_folding.evaluation.projection import render_png
    b64 = render_png(project_2d(_two_group_run()))
    assert isinstance(b64, str) and b64
    assert base64.b64decode(b64)[:4] == b"\x89PNG"  # PNG magic bytes
