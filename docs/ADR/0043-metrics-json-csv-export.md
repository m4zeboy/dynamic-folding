# ADR 0043: JSON/CSV export for evaluation metrics

## Status
Accepted

## Context
`silhouette` and `compare` only exposed their metrics as stdout text or, for
`compare`, an optional self-contained HTML report (`--html`) — built for the
author to read visually, not for a third party to consume the numbers
programmatically. The thesis advisor plans to run the tool on her own dataset
and will want the quantitative metrics (Silhouette, DBCV), which today are
only readable by opening the HTML report or scraping the terminal text.

## Decision
- Add `--json <path>` and `--csv <path>` to both `silhouette` and `compare`,
  **additive** like the existing `compare --html`: they write a file as a side
  effect and never suppress the existing stdout text. This keeps the flags
  composable (`--html out.html --json out.json --csv out.csv` in one run) and
  matches the one precedent already in the CLI, rather than introducing the
  `run --json` boolean-replaces-stdout convention for a second time.
- Serialize via hand-written `to_dict()` methods on the evaluation dataclasses
  (`SilhouetteResult`, `SilhouetteBaselineResult`, `GroupSilhouette`,
  `DBCVResult`, `GroupDBCV`, `AlgorithmResult`, `SensitivityRow`,
  `SensitivityStudy`, `ComparisonResult`), matching the existing convention in
  `dynamic_folding/contracts/run_result.py::RunResult.to_dict` (no
  `dataclasses.asdict()` anywhere in the project).
- `ComparisonResult.to_dict()` drops the `projection`'s raw 2D coordinate
  array — that data exists only to draw the illustrative figure (ADR 0042)
  and would inflate the export with numbers nobody asked to read; the
  projection's metadata (space, explained variance, n_outliers, reason) is
  kept.
- New module `dynamic_folding/evaluation/csv_export.py` (stdlib `csv`, no new
  dependency — there was no CSV precedent anywhere in the project). CSV rows:
  one row per algorithm for `compare` (the structural + silhouette + DBCV
  descriptors that already read as a flat table); one row per top-level group
  for `silhouette`, followed by a differently-shaped `metric,value` summary
  block for the overall score/baseline/gap, since those don't fit the
  per-group columns.

## Consequences
- Nested/variable-shaped fields (`group_sizes`, `effective_config`) are
  JSON-only; CSV stays a flat table on purpose.
- No new CLI convention conflict: a future export flag should default to
  "additive, writes a file" unless there's a specific reason to replace
  stdout (as `run --json` does).
