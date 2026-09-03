from __future__ import annotations

import csv
from pathlib import Path

import pytest

from dynamic_folding import cli
from dynamic_folding.contracts.file_ref import FileRef
from dynamic_folding.contracts.proposal import FolderNode, StructureProposal
from dynamic_folding.contracts.run_result import RunResult
from dynamic_folding.evaluation.csv_export import write_external_evaluation_csv
from dynamic_folding.evaluation.external import (
    ExternalEvaluationError,
    evaluate_external,
    read_reference_labels,
)


def _file(rel_path: str) -> FileRef:
    return FileRef(
        path=rel_path,
        rel_path=rel_path,
        is_dir=False,
        depth=0,
        name=rel_path,
        ext="txt",
        size=1,
        ctime=None,
        mtime=None,
    )


def _run(folders: list[FolderNode], *, orphans: list[str] | None = None) -> RunResult:
    paths = ["a1.txt", "a2.txt", "b1.txt", "b2.txt"]
    return RunResult(
        root="corpus",
        files=[_file(path) for path in paths],
        extracted=[],
        preprocessed=[],
        embeddings=[],
        proposal=StructureProposal(
            root="corpus", folders=folders, orphans=orphans or [], notes=[]
        ),
    )


def test_external_metrics_are_perfect_for_same_partition_despite_group_names():
    result = _run(
        [
            FolderNode(name="predicted-one", files=["a1.txt", "a2.txt"]),
            FolderNode(name="predicted-two", files=["b1.txt", "b2.txt"]),
        ]
    )

    score = evaluate_external(
        result,
        {"a1.txt": "human A", "a2.txt": "human A", "b1.txt": "human B", "b2.txt": "human B"},
    )

    assert score.ari == pytest.approx(1.0)
    assert score.nmi == pytest.approx(1.0)
    assert score.ami == pytest.approx(1.0)
    assert score.n_predicted_outros == 0


def test_external_evaluation_flattens_subfolders_and_keeps_outros():
    result = _run(
        [
            FolderNode(
                name="Tema A",
                subfolders=[FolderNode(name="Detalhe", files=["a1.txt", "a2.txt"])],
            ),
            FolderNode(name="Outros", files=["b1.txt"]),
        ],
        orphans=["b2.txt"],
    )

    score = evaluate_external(
        result,
        {"a1.txt": "A", "a2.txt": "A", "b1.txt": "B", "b2.txt": "B"},
    )

    assert score.ari == pytest.approx(1.0)
    assert score.n_predicted_outros == 2
    assert score.predicted_counts == {"Outros": 2, "Tema A": 2}


def test_external_evaluation_rejects_incomplete_or_extra_reference_labels():
    result = _run([FolderNode(name="A", files=["a1.txt", "a2.txt", "b1.txt", "b2.txt"])])

    with pytest.raises(ExternalEvaluationError, match="cover exactly"):
        evaluate_external(result, {"a1.txt": "A", "a2.txt": "A", "b1.txt": "B"})

    with pytest.raises(ExternalEvaluationError, match="cover exactly"):
        evaluate_external(
            result,
            {
                "a1.txt": "A",
                "a2.txt": "A",
                "b1.txt": "B",
                "b2.txt": "B",
                "extra.txt": "B",
            },
        )


def test_external_metrics_detect_a_different_partition_and_ignore_label_row_order():
    result = _run([FolderNode(name="one group", files=["a1.txt", "a2.txt", "b1.txt", "b2.txt"])])

    score = evaluate_external(
        result,
        {"b2.txt": "B", "b1.txt": "B", "a2.txt": "A", "a1.txt": "A"},
    )

    assert score.ari == pytest.approx(0.0)
    assert score.nmi == pytest.approx(0.0)
    assert score.ami == pytest.approx(0.0)


def test_read_reference_labels_accepts_existing_export_shape_and_rejects_duplicates(
    tmp_path: Path,
):
    labels_path = tmp_path / "labels.csv"
    labels_path.write_text(
        "Nome do arquivo;Rótulo\r\na.txt;Tema\r\nb.txt;Outro\r\n",
        encoding="utf-8",
    )
    assert read_reference_labels(labels_path) == {"a.txt": "Tema", "b.txt": "Outro"}

    labels_path.write_text(
        "Arquivo;Rótulo\r\na.txt;Tema\r\na.txt;Outro\r\n", encoding="utf-8"
    )
    with pytest.raises(ExternalEvaluationError, match="duplicate"):
        read_reference_labels(labels_path)


def test_external_evaluation_csv_is_one_flat_summary_row(tmp_path: Path):
    result = _run(
        [
            FolderNode(name="A", files=["a1.txt", "a2.txt"]),
            FolderNode(name="B", files=["b1.txt", "b2.txt"]),
        ]
    )
    score = evaluate_external(
        result, {"a1.txt": "A", "a2.txt": "A", "b1.txt": "B", "b2.txt": "B"}
    )
    output = tmp_path / "external.csv"
    write_external_evaluation_csv(score, output)

    rows = list(csv.DictReader(output.open(encoding="utf-8")))
    assert len(rows) == 1
    assert rows[0]["ari"] == "1.0"
    assert rows[0]["average_method"] == "arithmetic"


def test_external_eval_cli_writes_provenance_json_and_flat_csv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    labels = tmp_path / "labels.csv"
    labels.write_text(
        "Arquivo;Rótulo\n"
        "a1.txt;A\n"
        "a2.txt;A\n"
        "b1.txt;B\n"
        "b2.txt;B\n",
        encoding="utf-8",
    )
    json_output = tmp_path / "result.json"
    csv_output = tmp_path / "result.csv"
    result = _run(
        [
            FolderNode(name="A", files=["a1.txt", "a2.txt"]),
            FolderNode(name="B", files=["b1.txt", "b2.txt"]),
        ]
    )
    monkeypatch.setattr(cli, "_resolve_cli_config_path", lambda _path: None)
    monkeypatch.setattr(cli, "resolve_effective_config", lambda *_args, **_kwargs: {"embedding": {"provider": "fake"}})
    monkeypatch.setattr(cli, "run_pipeline", lambda *_args, **_kwargs: result)

    code = cli.main(
        [
            "external-eval",
            str(corpus),
            "--labels",
            str(labels),
            "--json",
            str(json_output),
            "--csv",
            str(csv_output),
        ]
    )

    assert code == 0
    assert "ARI: +1.000" in capsys.readouterr().out
    assert '"effective_config"' in json_output.read_text(encoding="utf-8")
    assert list(csv.DictReader(csv_output.open(encoding="utf-8")))[0]["ami"] == "1.0"
