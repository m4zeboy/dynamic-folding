# ADR 0041: Comparison Report — Per-Algorithm Matrices, No Elected Execution (refines ADR 0038/0039/0040)

Date: 2026-06-20

## Status

Accepted. Refines the comparison report's **presentation** (ADR 0038's artifact; ADR 0039
DBCV; ADR 0040 reducer sweep). No product-contract change beyond an additive field on the
internal `SensitivityRow` eval DTO.

## Context

The first comparison report presented, per algorithm, a **single elected execution** (the
product default config) for the structural + silhouette + DBCV descriptors, plus a separate
sensitivity section. Reviewing it, the author raised three points:

1. The DBCV table showed only `algorithm | DBCV` — no groups/outliers/coverage/config.
2. The sensitivity reported only silhouette, not DBCV.
3. **The deeper one:** electing one execution per algorithm (e.g. kmeans at `top_k=3`)
   embeds an *arbitrary* hyperparameter choice — "how do I justify k=3?" The answer is you
   can't; k=3 is just the default. Electing it for the headline is the same unjustified
   election that **outcome-independence** (ADR 0038) rejects for algorithms.

## Decision

1. **Replace the elected per-algorithm metric sections with per-algorithm matrices.** Each
   clustering algorithm gets one matrix: rows = the **knob sweep** (the executions), columns
   = `grupos · outliers · cobertura · silhueta · DBCV`. The product default is **one row,
   marked "(padrão)"** — honest provenance, explicitly *not* "the comparison point". This is
   outcome-independence applied to **hyperparameters**: show the variation, never elect one.
2. **DBCV gains full context** (a column in the matrix, beside the structural descriptors)
   and **appears across the sweep** — resolving points 1 and 2.
3. **DBCV is comparable only down the clustering matrices** (fixed 10-dim space). The
   **reducer sweep (`n_components`) is a separate table with NO DBCV column** — its space
   changes per row, so a DBCV column there would compare different metric spaces (ADR 0039/0040).
4. **What survives the dissolve:** the config-**independent** structural contrast (kmeans
   makes no outliers; hdbscan models noise → `Outros`; hdbscan/agglomerative infer K) stays
   as prose. The random floor (piso) is computed/shown for **each algorithm's default row**
   (provenance anchor). hdbscan and agglomerative_tree share the `min_cluster_size` axis, but
   the knob plays **different roles** (density core vs tree-cut threshold) → loose alignment,
   not a controlled comparison (stated, not oversold).
5. **The 1D-sweep caveat is explicit:** each matrix varies one knob with everything else
   (other knobs, the embedder) at defaults — the committed "tiny fraction of a continuous
   space" limitation. "Don't elect" is *not* "we covered the space".

## Rationale

- "Show the variation, don't elect" is the only honest answer to "justify k=3", and it is
  outcome-independence (ADR 0038) extended from algorithms to hyperparameters.
- The matrix **unifies** the comparison and the sensitivity: the old elected sections were
  just the default row of the sweep — redundant.

## Consequences

### Positive
- No arbitrary elected execution; every metric shown across the variation; DBCV contextualized.

### Negative / owned limitations
- Matrices have **different x-axes** (different knobs) → no single side-by-side cross-algorithm
  table; the cross-algorithm reading is the config-independent structural contrast (prose) +
  reading the matrices together. Still **n=1**.

### Scope / process
- **Prose migration (writing pact):** the dissolved sections' authored prose (the "descrição
  não ranking" callout, the piso paragraph, the sensitivity reasoning) relocates to the
  matrices' intro — **authored by the user** in the writing phase (placeholders mark it; the
  prior text is preserved in git history). The tool scaffolds; the author writes.
- Code: `comparison_report.py` (`_section_matrices`, `_matrix_for`, `_section_reducer`;
  dissolved `_section_per_algorithm` / `_section_dbcv` / `_section_sensitivity`);
  `SensitivityRow` gains `dbcv_score`/`dbcv_reason`; `comparison.py` adds an
  `agglomerative_tree` clustering sweep. `docs/SPEC.md` updated. Tests in `tests/test_comparison*.py`.

## References

- [ADR 0038](0038-bounded-empirical-justification-default-clusterer.md) — outcome-independence; the artifact.
- [ADR 0039](0039-dbcv-second-lens-reduced-space.md) — DBCV (the matrix column); reduced-space space caveat.
- [ADR 0040](0040-reducer-enters-sensitivity-lightly.md) — the reducer sweep (separate table).
- [ADR 0032](0032-html-report-v1-sereno.md) — the V1 Sereno report design reused.
- `docs/learning/02-experimental-scope.md` — the chapter roadmap.
