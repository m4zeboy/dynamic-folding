"""Orchestrate the single-corpus comparison (``comparison.py::run_comparison``)
over several corpora, for a single side-by-side report (ADR 0045).

This is assembly, not new measurement: each corpus gets its own
``run_comparison`` call, then the results are anonymized (the real directory
is replaced by a stable "Corpus N" label) and collected in order. The mapping
from label back to the real path is intentionally NOT part of the returned
DTO — it must stay out of the HTML (see ``multicorpus_report.py``); callers
that need it (e.g. the CLI) keep their own zip of ``paths`` with the result.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

from dynamic_folding.evaluation.comparison import ComparisonResult, run_comparison


@dataclasses.dataclass(frozen=True)
class MultiCorpusComparison:
    # (label, anonymized ComparisonResult) in argument order — Corpus 1, 2, 3, ...
    items: list[tuple[str, ComparisonResult]]
    version: str

    def to_dict(self) -> dict:
        return {
            "items": [
                {"label": label, "result": res.to_dict()} for label, res in self.items
            ],
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MultiCorpusComparison":
        """Rebuild from a to_dict() payload — lets the report be re-rendered from a
        saved JSON without re-running the pipeline (compare-multi --from-json)."""
        from dynamic_folding.evaluation.comparison import comparison_result_from_dict

        return cls(
            items=[
                (item["label"], comparison_result_from_dict(item["result"]))
                for item in d.get("items", [])
            ],
            version=d.get("version", ""),
        )


def run_multicorpus_comparison(
    corpus_dirs: list[Path | str],
    *,
    config_path: Path | None = None,
    sensitivity_studies: list[tuple[str, str, str, list[int]]] | None = None,
    labels: list[str] | None = None,
) -> MultiCorpusComparison:
    """Run ``run_comparison`` once per corpus (in the given order) and anonymize.

    ``labels`` overrides the default "Corpus N" naming (rare; must be the same
    length as ``corpus_dirs`` if given). Real paths never enter the returned
    DTO's ``ComparisonResult.root`` — it is replaced by the label.
    """
    from dynamic_folding import __version__

    if labels is not None and len(labels) != len(corpus_dirs):
        raise ValueError("labels must have the same length as corpus_dirs")

    items: list[tuple[str, ComparisonResult]] = []
    for i, corpus_dir in enumerate(corpus_dirs):
        label = labels[i] if labels is not None else f"Corpus {i + 1}"
        res = run_comparison(
            corpus_dir,
            config_path=config_path,
            sensitivity_studies=sensitivity_studies,
        )
        res_anon = dataclasses.replace(res, root=label)
        items.append((label, res_anon))

    return MultiCorpusComparison(items=items, version=__version__)
