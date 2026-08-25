"""Proof that the Silhouette tool computes the right thing (no SBERT needed).

Hand-built RunResults with known geometry: two well-separated groups score high,
a single group is undefined, the hierarchy is flattened to the top level, and the
"Outros" bucket is skipped.
"""
from __future__ import annotations

from dynamic_folding.contracts.embedding import EmbeddingRecord
from dynamic_folding.contracts.file_ref import FileRef
from dynamic_folding.contracts.proposal import FolderNode, StructureProposal
from dynamic_folding.contracts.run_result import RunResult
from dynamic_folding.evaluation.silhouette import (
    silhouette_baseline_of_run,
    silhouette_of_run,
)


def _emb(rel: str, vec: list[float]) -> EmbeddingRecord:
    fr = FileRef(path=rel, rel_path=rel, is_dir=False, depth=0, name=rel,
                 ext="txt", size=1, ctime=None, mtime=None)
    return EmbeddingRecord(file=fr, vector=vec, model_id="t", content_hash=rel)


def _run(folders: list[FolderNode], embeddings: list[EmbeddingRecord]) -> RunResult:
    return RunResult(
        root="r", files=[], extracted=[], preprocessed=[],
        embeddings=embeddings,
        proposal=StructureProposal(root="r", folders=folders, orphans=[], notes=[]),
    )


def test_separated_groups_score_high_skip_outros_flatten_hierarchy():
    # Group A (one file nested in a subfolder) near [10, 0]; Group B near [0, 10].
    folders = [
        FolderNode(name="A", files=["a1.txt", "a2.txt"],
                   subfolders=[FolderNode(name="A_sub", files=["a3.txt"])]),
        FolderNode(name="B", files=["b1.txt", "b2.txt", "b3.txt"]),
        FolderNode(name="Outros", display_name="Outros", files=["o1.txt", "o2.txt"]),
    ]
    embeddings = [
        _emb("a1.txt", [10.0, 0.0]), _emb("a2.txt", [10.1, 0.0]), _emb("a3.txt", [9.9, 0.1]),
        _emb("b1.txt", [0.0, 10.0]), _emb("b2.txt", [0.0, 10.1]), _emb("b3.txt", [0.1, 9.9]),
        _emb("o1.txt", [5.0, 5.0]), _emb("o2.txt", [5.1, 5.1]),
    ]
    res = silhouette_of_run(_run(folders, embeddings))
    assert res.n_groups == 2
    assert res.n_files_scored == 6  # a3 (nested) counts under A; o1/o2 skipped
    assert res.n_outliers == 2
    assert res.score is not None
    assert res.score > 0.5  # two tight, far-apart groups


def test_single_group_is_undefined():
    folders = [FolderNode(name="A", files=["a1.txt", "a2.txt", "a3.txt"])]
    embeddings = [
        _emb("a1.txt", [1.0, 0.0]), _emb("a2.txt", [1.1, 0.0]), _emb("a3.txt", [0.9, 0.1])
    ]
    res = silhouette_of_run(_run(folders, embeddings))
    assert res.score is None
    assert res.n_groups == 1
    assert res.reason is not None


def test_baseline_floor_far_below_real_for_separated_groups():
    # Three tight groups, far apart: the real grouping scores high, but shuffling
    # which file goes where (keeping the same 5/5/5 sizes) should score near zero.
    folders = [
        FolderNode(name="A", files=["a1.txt", "a2.txt", "a3.txt", "a4.txt", "a5.txt"]),
        FolderNode(name="B", files=["b1.txt", "b2.txt", "b3.txt", "b4.txt", "b5.txt"]),
        FolderNode(name="C", files=["c1.txt", "c2.txt", "c3.txt", "c4.txt", "c5.txt"]),
    ]
    embeddings = [
        _emb("a1.txt", [10.0, 0.0]), _emb("a2.txt", [10.1, 0.0]), _emb("a3.txt", [9.9, 0.1]),
        _emb("a4.txt", [10.0, 0.2]), _emb("a5.txt", [10.2, 0.1]),
        _emb("b1.txt", [0.0, 10.0]), _emb("b2.txt", [0.1, 10.0]), _emb("b3.txt", [0.0, 9.9]),
        _emb("b4.txt", [0.2, 10.1]), _emb("b5.txt", [0.1, 9.8]),
        _emb("c1.txt", [-10.0, -10.0]), _emb("c2.txt", [-10.1, -10.0]), _emb("c3.txt", [-9.9, -9.9]),
        _emb("c4.txt", [-10.0, -10.2]), _emb("c5.txt", [-10.2, -9.8]),
    ]
    base = silhouette_baseline_of_run(_run(folders, embeddings), n_permutations=100)
    assert base.real.score is not None and base.real.score > 0.5
    assert base.baseline_mean is not None
    assert base.baseline_mean < 0.15  # random membership ~ no structure
    assert base.gap is not None and base.gap > 0.4  # real sits well above the floor


def test_baseline_is_deterministic():
    folders = [
        FolderNode(name="A", files=["a1.txt", "a2.txt", "a3.txt"]),
        FolderNode(name="B", files=["b1.txt", "b2.txt", "b3.txt"]),
    ]
    embeddings = [
        _emb("a1.txt", [10.0, 0.0]), _emb("a2.txt", [10.1, 0.0]), _emb("a3.txt", [9.9, 0.1]),
        _emb("b1.txt", [0.0, 10.0]), _emb("b2.txt", [0.0, 10.1]), _emb("b3.txt", [0.1, 9.9]),
    ]
    run = _run(folders, embeddings)
    one = silhouette_baseline_of_run(run, n_permutations=100, random_state=0)
    two = silhouette_baseline_of_run(run, n_permutations=100, random_state=0)
    assert one.baseline_mean == two.baseline_mean
    assert one.baseline_std == two.baseline_std


def test_baseline_undefined_when_silhouette_undefined():
    folders = [FolderNode(name="A", files=["a1.txt", "a2.txt", "a3.txt"])]
    embeddings = [
        _emb("a1.txt", [1.0, 0.0]), _emb("a2.txt", [1.1, 0.0]), _emb("a3.txt", [0.9, 0.1])
    ]
    base = silhouette_baseline_of_run(_run(folders, embeddings))
    assert base.real.score is None
    assert base.baseline_mean is None
    assert base.gap is None
    assert base.reason is not None
    assert base.n_permutations == 0


def test_per_group_scores_named_and_counted():
    # Group A has a nested file (a3) that must count under A at the top level.
    folders = [
        FolderNode(name="A", files=["a1.txt", "a2.txt"],
                   subfolders=[FolderNode(name="A_sub", files=["a3.txt"])]),
        FolderNode(name="B", files=["b1.txt", "b2.txt", "b3.txt"]),
    ]
    embeddings = [
        _emb("a1.txt", [10.0, 0.0]), _emb("a2.txt", [10.1, 0.0]), _emb("a3.txt", [9.9, 0.1]),
        _emb("b1.txt", [0.0, 10.0]), _emb("b2.txt", [0.0, 10.1]), _emb("b3.txt", [0.1, 9.9]),
    ]
    res = silhouette_of_run(_run(folders, embeddings))
    assert res.score is not None
    by_name = {g.name: g for g in res.per_group}
    assert set(by_name) == {"A", "B"}
    assert by_name["A"].n_files == 3  # a3 (nested) counts under A
    assert by_name["B"].n_files == 3
    assert by_name["A"].score > 0.5 and by_name["B"].score > 0.5


def test_per_group_empty_when_undefined():
    folders = [FolderNode(name="A", files=["a1.txt", "a2.txt", "a3.txt"])]
    embeddings = [
        _emb("a1.txt", [1.0, 0.0]), _emb("a2.txt", [1.1, 0.0]), _emb("a3.txt", [0.9, 0.1])
    ]
    res = silhouette_of_run(_run(folders, embeddings))
    assert res.score is None
    assert res.per_group == []
