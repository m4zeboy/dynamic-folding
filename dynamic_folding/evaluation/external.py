"""External clustering evaluation against a human reference partition.

The reference labels describe one human organization of a corpus.  They are a
comparison target for that corpus, not an assertion of universal correctness.
The proposed hierarchy is deliberately flattened at its top level so it can be
compared to the flat reference partition.
"""
from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from sklearn.metrics import (
    adjusted_mutual_info_score,
    adjusted_rand_score,
    normalized_mutual_info_score,
)

from dynamic_folding.contracts.proposal import FolderNode
from dynamic_folding.contracts.run_result import RunResult

_OUTROS = "Outros"
_AVERAGE_METHOD = "arithmetic"


class ExternalEvaluationError(ValueError):
    """The reference partition cannot be compared fairly to this run."""


@dataclass(frozen=True)
class ExternalEvaluationResult:
    """Agreement of one proposal with one complete human reference partition."""

    ari: float
    nmi: float
    ami: float
    n_files: int
    n_reference_classes: int
    n_predicted_groups: int
    n_predicted_outros: int
    reference_counts: dict[str, int]
    predicted_counts: dict[str, int]
    average_method: str = _AVERAGE_METHOD

    def to_dict(self) -> dict:
        return {
            "ari": self.ari,
            "nmi": self.nmi,
            "ami": self.ami,
            "n_files": self.n_files,
            "n_reference_classes": self.n_reference_classes,
            "n_predicted_groups": self.n_predicted_groups,
            "n_predicted_outros": self.n_predicted_outros,
            "reference_counts": dict(self.reference_counts),
            "predicted_counts": dict(self.predicted_counts),
            "average_method": self.average_method,
        }


def read_reference_labels(path: str | Path) -> dict[str, str]:
    """Read the project's two-column, semicolon-separated human label export.

    The first two columns are intentionally used by position: the existing
    exports use both ``Arquivo`` and ``Nome do arquivo`` for the path header,
    while their data shape is the same.  Reading with ``utf-8-sig`` also makes
    a spreadsheet-added UTF-8 BOM harmless.
    """
    label_path = Path(path)
    try:
        with label_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle, delimiter=";")
            header = next(reader, None)
            if header is None or len(header) < 2:
                raise ExternalEvaluationError(
                    f"{label_path}: expected a header and two semicolon-separated columns"
                )

            labels: dict[str, str] = {}
            for line_number, row in enumerate(reader, start=2):
                if len(row) < 2:
                    raise ExternalEvaluationError(
                        f"{label_path}:{line_number}: expected file path and reference label"
                    )
                rel_path, reference = row[0].strip(), row[1].strip()
                if not rel_path or not reference:
                    raise ExternalEvaluationError(
                        f"{label_path}:{line_number}: file path and reference label are required"
                    )
                if rel_path in labels:
                    raise ExternalEvaluationError(
                        f"{label_path}:{line_number}: duplicate file path {rel_path!r}"
                    )
                labels[rel_path] = reference
    except OSError as exc:
        raise ExternalEvaluationError(f"could not read {label_path}: {exc}") from exc

    if not labels:
        raise ExternalEvaluationError(f"{label_path}: no reference labels found")
    return labels


def _all_files(folder: FolderNode) -> list[str]:
    paths = list(folder.files)
    for child in folder.subfolders:
        paths.extend(_all_files(child))
    return paths


def _predicted_labels(result: RunResult) -> dict[str, str]:
    """Flatten the proposal to one predicted top-level label per file.

    ``Outros`` and proposal orphans are kept in the comparison.  A file not
    placed under a top-level folder is consequently treated as ``Outros``
    instead of disappearing from the denominator.
    """
    labels: dict[str, str] = {}
    for folder in result.proposal.folders:
        group_name = folder.display_name or folder.name
        for rel_path in _all_files(folder):
            if rel_path in labels:
                raise ExternalEvaluationError(
                    f"proposal assigns {rel_path!r} to more than one top-level folder"
                )
            labels[rel_path] = group_name
    for rel_path in result.proposal.orphans:
        if rel_path in labels:
            raise ExternalEvaluationError(
                f"proposal assigns {rel_path!r} both to a folder and to orphans"
            )
        labels[rel_path] = _OUTROS
    return labels


def _describe_difference(expected: set[str], actual: set[str]) -> str:
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    pieces: list[str] = []
    if missing:
        pieces.append(f"missing labels for {missing[:3]!r}")
    if unexpected:
        pieces.append(f"labels without scanned files {unexpected[:3]!r}")
    return "; ".join(pieces)


def evaluate_external(
    result: RunResult, reference_labels: dict[str, str],
) -> ExternalEvaluationResult:
    """Score one complete run against its complete human reference partition."""
    file_paths = [file_ref.rel_path for file_ref in result.files if not file_ref.is_dir]
    if len(file_paths) != len(set(file_paths)):
        raise ExternalEvaluationError("scanner returned duplicate relative paths")
    if not file_paths:
        raise ExternalEvaluationError("cannot evaluate an empty corpus")

    expected = set(file_paths)
    actual = set(reference_labels)
    if expected != actual:
        raise ExternalEvaluationError(
            "reference labels must cover exactly the scanned files: "
            + _describe_difference(expected, actual)
        )

    predicted_by_path = _predicted_labels(result)
    unexpected_predictions = set(predicted_by_path) - expected
    if unexpected_predictions:
        raise ExternalEvaluationError(
            "proposal contains files outside the scanned corpus: "
            f"{sorted(unexpected_predictions)[:3]!r}"
        )

    reference = [reference_labels[path] for path in file_paths]
    predicted = [predicted_by_path.get(path, _OUTROS) for path in file_paths]
    reference_counts = dict(sorted(Counter(reference).items()))
    predicted_counts = dict(sorted(Counter(predicted).items()))

    return ExternalEvaluationResult(
        ari=float(adjusted_rand_score(reference, predicted)),
        nmi=float(
            normalized_mutual_info_score(
                reference, predicted, average_method=_AVERAGE_METHOD
            )
        ),
        ami=float(
            adjusted_mutual_info_score(
                reference, predicted, average_method=_AVERAGE_METHOD
            )
        ),
        n_files=len(file_paths),
        n_reference_classes=len(reference_counts),
        n_predicted_groups=len(predicted_counts),
        n_predicted_outros=predicted_counts.get(_OUTROS, 0),
        reference_counts=reference_counts,
        predicted_counts=predicted_counts,
    )


def format_external_evaluation(result: ExternalEvaluationResult) -> str:
    """Compact, human-readable result for the CLI."""
    return "\n".join(
        [
            "Avaliação externa (referência humana)",
            f"  ARI: {result.ari:+.3f}",
            f"  NMI: {result.nmi:+.3f}",
            f"  AMI (ANMI): {result.ami:+.3f}",
            (
                f"  arquivos: {result.n_files} | classes de referência: "
                f"{result.n_reference_classes} | grupos previstos: "
                f"{result.n_predicted_groups} | em Outros: {result.n_predicted_outros}"
            ),
        ]
    )
