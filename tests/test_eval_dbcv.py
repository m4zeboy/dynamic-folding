"""Proof that the DBCV tool computes the right thing (no SBERT needed).

DBCV is the density lens (opposite bias to silhouette): it rewards dense, connected
clusters of any shape, scored on the REDUCED vectors the clustering used
(result.reduced_vectors). The "Outros" bucket is fed as noise (-1) and counted.

Key fixture is the opposite-bias one: two elongated (non-convex) clusters that the
density lens likes but the convex silhouette does not.
"""
from __future__ import annotations

from dynamic_folding.contracts.embedding import EmbeddingRecord
from dynamic_folding.contracts.file_ref import FileRef
from dynamic_folding.contracts.proposal import FolderNode, StructureProposal
from dynamic_folding.contracts.run_result import RunResult
from dynamic_folding.evaluation.dbcv import dbcv_of_run
from dynamic_folding.evaluation.silhouette import silhouette_of_run


def _emb(rel: str, vec: list[float]) -> EmbeddingRecord:
    fr = FileRef(path=rel, rel_path=rel, is_dir=False, depth=0, name=rel,
                 ext="txt", size=1, ctime=None, mtime=None)
    return EmbeddingRecord(file=fr, vector=vec, model_id="t", content_hash=rel)


def _run(folders, rels, vecs, *, reduced=None) -> RunResult:
    """Build a RunResult. `vecs` are the reduced vectors DBCV scores (and, by
    default, the embedding vectors too, so silhouette can be read on the same
    geometry). Pass reduced=[] to simulate a run without reduced vectors."""
    embeddings = [_emb(rel, list(v)) for rel, v in zip(rels, vecs)]
    rv = vecs if reduced is None else reduced
    return RunResult(
        root="r", files=[], extracted=[], preprocessed=[],
        embeddings=embeddings,
        reduced_vectors=[list(v) for v in rv],
        proposal=StructureProposal(root="r", folders=folders, orphans=[], notes=[]),
    )


def test_separated_dense_blobs_score_positive():
    folders = [
        FolderNode(name="A", files=["a1.txt", "a2.txt", "a3.txt", "a4.txt", "a5.txt"]),
        FolderNode(name="B", files=["b1.txt", "b2.txt", "b3.txt", "b4.txt", "b5.txt"]),
    ]
    rels = ["a1.txt", "a2.txt", "a3.txt", "a4.txt", "a5.txt",
            "b1.txt", "b2.txt", "b3.txt", "b4.txt", "b5.txt"]
    vecs = [
        [10.0, 0.0], [10.1, 0.0], [9.9, 0.1], [10.0, 0.2], [10.2, 0.1],
        [0.0, 10.0], [0.1, 10.0], [0.0, 9.9], [0.2, 10.1], [0.1, 9.8],
    ]
    res = dbcv_of_run(_run(folders, rels, vecs))
    assert res.n_groups == 2
    assert res.n_files_scored == 10
    assert res.n_outliers == 0
    assert res.score is not None
    assert res.score > 0.5  # dense, well separated -> high DBCV


def test_opposite_bias_dbcv_rewards_elongated_clusters_silhouette_does_not():
    # Two parallel dense lines: elongated (non-convex-friendly). The density lens
    # likes them (dense, connected, separated by a gap); the convex silhouette,
    # which assumes round blobs, scores them much lower. This is the opposite bias.
    n = 12
    a_rels = [f"a{i}" for i in range(n)]
    b_rels = [f"b{i}" for i in range(n)]
    a_vecs = [[float(i), 0.0] for i in range(n)]
    b_vecs = [[float(i), 3.0] for i in range(n)]
    folders = [FolderNode(name="A", files=a_rels), FolderNode(name="B", files=b_rels)]
    run = _run(folders, a_rels + b_rels, a_vecs + b_vecs)
    d = dbcv_of_run(run)
    s = silhouette_of_run(run)
    assert d.score is not None and s.score is not None
    assert d.score > 0
    assert d.score > s.score  # DBCV rewards what silhouette penalizes


def test_single_group_is_undefined():
    folders = [FolderNode(name="A", files=["a1.txt", "a2.txt", "a3.txt"])]
    rels = ["a1.txt", "a2.txt", "a3.txt"]
    vecs = [[1.0, 0.0], [1.1, 0.0], [0.9, 0.1]]
    res = dbcv_of_run(_run(folders, rels, vecs))
    assert res.score is None
    assert res.n_groups == 1
    assert res.reason is not None


def test_missing_reduced_vectors_is_undefined():
    folders = [
        FolderNode(name="A", files=["a1.txt", "a2.txt", "a3.txt"]),
        FolderNode(name="B", files=["b1.txt", "b2.txt", "b3.txt"]),
    ]
    rels = ["a1.txt", "a2.txt", "a3.txt", "b1.txt", "b2.txt", "b3.txt"]
    vecs = [[10.0, 0.0], [10.1, 0.0], [9.9, 0.1], [0.0, 10.0], [0.0, 10.1], [0.1, 9.9]]
    res = dbcv_of_run(_run(folders, rels, vecs, reduced=[]))
    assert res.score is None
    assert res.reason is not None


def test_degenerate_partition_does_not_crash():
    # A singleton cluster gives validity_index no internal MST to build; the tool
    # must return None + reason, never raise (CLAUDE.md robustness rule).
    folders = [
        FolderNode(name="A", files=["a1.txt"]),
        FolderNode(name="B", files=["b1.txt", "b2.txt", "b3.txt"]),
    ]
    rels = ["a1.txt", "b1.txt", "b2.txt", "b3.txt"]
    vecs = [[10.0, 0.0], [0.0, 10.0], [0.0, 10.1], [0.1, 9.9]]
    res = dbcv_of_run(_run(folders, rels, vecs))
    assert res.score is None
    assert res.reason is not None


def test_deterministic():
    folders = [
        FolderNode(name="A", files=["a1.txt", "a2.txt", "a3.txt", "a4.txt"]),
        FolderNode(name="B", files=["b1.txt", "b2.txt", "b3.txt", "b4.txt"]),
    ]
    rels = ["a1.txt", "a2.txt", "a3.txt", "a4.txt", "b1.txt", "b2.txt", "b3.txt", "b4.txt"]
    vecs = [
        [10.0, 0.0], [10.1, 0.0], [9.9, 0.1], [10.0, 0.2],
        [0.0, 10.0], [0.1, 10.0], [0.0, 9.9], [0.2, 10.1],
    ]
    run = _run(folders, rels, vecs)
    assert dbcv_of_run(run).score == dbcv_of_run(run).score


def test_outros_fed_as_noise_and_counted_with_per_group():
    folders = [
        FolderNode(name="A", files=["a1.txt", "a2.txt"],
                   subfolders=[FolderNode(name="A_sub", files=["a3.txt"])]),
        FolderNode(name="B", files=["b1.txt", "b2.txt", "b3.txt"]),
        FolderNode(name="Outros", display_name="Outros", files=["o1.txt", "o2.txt"]),
    ]
    rels = ["a1.txt", "a2.txt", "a3.txt", "b1.txt", "b2.txt", "b3.txt", "o1.txt", "o2.txt"]
    vecs = [
        [10.0, 0.0], [10.1, 0.0], [9.9, 0.1],
        [0.0, 10.0], [0.0, 10.1], [0.1, 9.9],
        [5.0, 5.0], [5.1, 5.1],
    ]
    res = dbcv_of_run(_run(folders, rels, vecs))
    assert res.n_outliers == 2       # Outros fed as noise, counted not scored
    assert res.n_files_scored == 6   # a3 (nested) counts under A
    assert res.score is not None
    by_name = {g.name: g for g in res.per_group}
    assert set(by_name) == {"A", "B"}
    assert by_name["A"].n_files == 3  # nested a3 flattened under A
