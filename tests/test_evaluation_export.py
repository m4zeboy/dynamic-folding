"""to_dict()/CSV export for the evaluation metrics (Silhouette, DBCV, compare).

Covers: fields present in to_dict(), determinism, and the score-is-None case
(reason present, serialization doesn't blow up).
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from dynamic_folding.contracts.embedding import EmbeddingRecord
from dynamic_folding.contracts.file_ref import FileRef
from dynamic_folding.contracts.proposal import FolderNode, StructureProposal
from dynamic_folding.contracts.run_result import RunResult
from dynamic_folding.evaluation.csv_export import (
    write_comparison_csv,
    write_silhouette_csv,
)
from dynamic_folding.evaluation.silhouette import (
    silhouette_baseline_of_run,
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


def _separated_groups_run() -> RunResult:
    folders = [
        FolderNode(name="A", files=["a1.txt", "a2.txt", "a3.txt"]),
        FolderNode(name="B", files=["b1.txt", "b2.txt", "b3.txt"]),
    ]
    embeddings = [
        _emb("a1.txt", [10.0, 0.0]), _emb("a2.txt", [10.1, 0.0]), _emb("a3.txt", [9.9, 0.1]),
        _emb("b1.txt", [0.0, 10.0]), _emb("b2.txt", [0.0, 10.1]), _emb("b3.txt", [0.1, 9.9]),
    ]
    return _run(folders, embeddings)


def _single_group_run() -> RunResult:
    folders = [FolderNode(name="A", files=["a1.txt", "a2.txt"])]
    embeddings = [_emb("a1.txt", [1.0, 0.0]), _emb("a2.txt", [1.1, 0.0])]
    return _run(folders, embeddings)


def test_silhouette_to_dict_has_expected_shape():
    base = silhouette_baseline_of_run(_separated_groups_run(), n_permutations=5)
    d = base.to_dict()
    assert d["real"]["score"] == base.real.score
    assert d["baseline_mean"] == base.baseline_mean
    assert d["gap"] == base.gap
    assert len(d["real"]["per_group"]) == 2
    assert {g["name"] for g in d["real"]["per_group"]} == {"A", "B"}
    # Round-trips through json without error.
    json.dumps(d)


def test_silhouette_to_dict_none_score_has_reason():
    base = silhouette_baseline_of_run(_single_group_run())
    d = base.to_dict()
    assert d["real"]["score"] is None
    assert d["real"]["reason"]
    assert d["baseline_mean"] is None
    json.dumps(d)  # doesn't blow up on None fields


def test_silhouette_to_dict_is_deterministic():
    run = _separated_groups_run()
    d1 = silhouette_baseline_of_run(run, n_permutations=5, random_state=0).to_dict()
    d2 = silhouette_baseline_of_run(run, n_permutations=5, random_state=0).to_dict()
    assert d1 == d2


def test_write_silhouette_csv(tmp_path: Path):
    base = silhouette_baseline_of_run(_separated_groups_run(), n_permutations=5)
    out = tmp_path / "sil.csv"
    write_silhouette_csv(base, out)

    text = out.read_text()
    rows = list(csv.reader(text.splitlines()))
    assert rows[0] == ["name", "score", "n_files"]
    group_names = {r[0] for r in rows[1:3]}
    assert group_names == {"A", "B"}
    # Summary block after the blank-line separator.
    assert ["metric", "value"] in rows


def test_run_comparison_to_dict_and_csv(tmp_path: Path):
    from dynamic_folding.evaluation.comparison import run_comparison

    for n in ["invoice_a.pdf", "invoice_b.pdf", "photo_a.jpg", "photo_b.jpg"]:
        p = tmp_path / n
        p.write_bytes(b"x")

    studies = [("clustering", "hdbscan", "min_cluster_size", [2, 3])]
    res = run_comparison(tmp_path, sensitivity_studies=studies)

    d = res.to_dict()
    assert [a["algorithm"] for a in d["algorithms"]] == [a.algorithm for a in res.algorithms]
    json.dumps(d)  # round-trips

    out = tmp_path / "cmp.csv"
    write_comparison_csv(res, out)
    rows = list(csv.DictReader(out.read_text().splitlines()))
    assert [r["algorithm"] for r in rows] == [a.algorithm for a in res.algorithms]
