"""Run the pipeline N times on one corpus, recording cluster membership + the
name each run gave it, to see how LLM (Ollama) naming varies run to run.

Clustering is deterministic (fixed seeds) — only the naming stage should
differ between runs. This script does not touch any existing/frozen
`external_evaluation_results/*.json`; it writes new, separate artifacts.

Usage:
  uv run python evaluation/collect_naming_variants.py <corpus_dir> \\
      --labels <labels.csv> --runs 3 --label "Corpus 1" \\
      --out-dir external_evaluation_results/naming_variants

Writes one JSON per run: <out-dir>/<slug>_run{i}.json.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from dynamic_folding.core.pipeline import run_pipeline
from dynamic_folding.evaluation.external import (
    _predicted_labels,
    evaluate_external,
    read_reference_labels,
)


def _slugify(label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
    return slug or "corpus"


def collect(
    corpus: Path,
    labels_path: Path,
    runs: int,
    label: str,
    config_path: Path | None,
    out_dir: Path,
) -> None:
    reference = read_reference_labels(labels_path)
    slug = _slugify(label)
    out_dir.mkdir(parents=True, exist_ok=True)

    for i in range(1, runs + 1):
        result = run_pipeline(corpus, config_path=config_path)
        evaluation = evaluate_external(result, reference)
        predicted = _predicted_labels(result)

        groups: dict[str, list[str]] = {}
        for rel_path, name in predicted.items():
            if name == "Outros":
                continue
            groups.setdefault(name, []).append(rel_path)
        for paths in groups.values():
            paths.sort()

        payload = {
            "label": label,
            "run": i,
            "groups": groups,
            "external_evaluation": {
                "ari": evaluation.ari,
                "nmi": evaluation.nmi,
                "ami": evaluation.ami,
                "n_files": evaluation.n_files,
            },
        }
        out_path = out_dir / f"{slug}_run{i}.json"
        out_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(
            f"[{label}] run {i}/{runs}: "
            f"ari={evaluation.ari:.3f} nmi={evaluation.nmi:.3f} ami={evaluation.ami:.3f} "
            f"groups={len(groups)} -> {out_path}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", help="path to the corpus directory")
    parser.add_argument("--labels", required=True, help="reference labels CSV")
    parser.add_argument("--runs", type=int, default=3, help="number of repeat runs")
    parser.add_argument("--label", default=None, help='e.g. "Corpus 1" (default: dir name)')
    parser.add_argument("--config", default=None, help="config TOML path (default: tool default)")
    parser.add_argument(
        "--out-dir",
        default="external_evaluation_results/naming_variants",
        help="where to write the per-run JSON files",
    )
    args = parser.parse_args()

    corpus = Path(args.corpus).resolve()
    collect(
        corpus=corpus,
        labels_path=Path(args.labels),
        runs=args.runs,
        label=args.label or corpus.name,
        config_path=Path(args.config) if args.config else None,
        out_dir=Path(args.out_dir),
    )


if __name__ == "__main__":
    main()
