# ADR 0040: The Reducer Enters the Sensitivity Study, Lightly (amends ADR 0038)

Date: 2026-06-20

## Status

Accepted. **Amends [ADR 0038](0038-bounded-empirical-justification-default-clusterer.md)
Decision item 1** ("the reducer (UMAP) and other stages stay descriptive background") on
one narrow axis. Everything else in ADR 0038 / ADR 0018 is unchanged.

## Context

The orientadora's feedback on the first comparison report asked to **lightly expand the
hyperparameter sensitivity** and to **discuss the UMAP reducer's hyperparameters**
(`n_components`, `n_neighbors`, `min_dist`) and **decide whether any enter the sensitivity
study** — explicitly revisiting ADR 0038's "reducer stays background" boundary.

ADR 0038 item 1 scoped sensitivity to the **clustering algorithm's** hyperparameters and
kept the reducer descriptive-only. The author reads "lightly" as leaning **more toward
k-means than a heavy UMAP study**, and chose (option B) to admit a single reducer knob.

## Decision

1. **The reducer enters the sensitivity study with one knob: `n_components`** (swept
   5 / 10 / 15 / 20), with the clusterer **pinned to the default (hdbscan)** as a fixed
   backdrop. Framed as **ADR 0018 property #3** (responsiveness / provenance), *not*
   optimization — same honest reading as the clustering sweeps: a silhouette that responds
   to the knob shows the reducer **matters**, never that a value is "best".

2. **`n_neighbors` and `min_dist` stay out of the sweep — discussed in prose only** (why
   they are held fixed, plus the honest caveat that they could move results; e.g. the
   default `n_neighbors=15` ≈ 28% of a ~54-file corpus is an untested small-n regime — a
   stated limitation, not a tuned choice).

3. **k-means carries the heavier clustering sweep** (`top_k` widened to 2..15), honoring
   the author's "lean toward k-means". hdbscan's `min_cluster_size` sweep is unchanged.

4. The machinery gains a **`stage`** dimension on each sensitivity study
   (`"clustering"` | `"reducer"`) so the override targets the right config section; no
   product-contract change (the reducer config already existed).

## Rationale

- **Honest engagement with the feedback.** "Decide whether they enter" includes deciding
  that two of three (`n_neighbors`, `min_dist`) **do not** — discussed, not swept — which
  is what keeps the expansion *light*.
- **One reducer knob as provenance** shows the reducer is not inert (it changes
  #groups / coverage / silhouette across `n_components`) without claiming an optimal
  projection — consistent with 0038's provenance-not-optimization stance.
- **Pinning the clusterer** to the default keeps the reducer sweep interpretable against a
  fixed backdrop.

## Consequences

### Positive
- The "reducer out of scope" gap is closed with **bounded provenance**; the report now
  shows the reducer responds to its main knob (`n_components=10` reproduces the default
  pipeline's numbers exactly — a consistency check).

### Negative / owned limitations
- Still **one knob, n=1, exploratory** — illustrative, not a reducer optimization study.
- `n_neighbors` / `min_dist` appropriateness in the small-n regime remains a **stated,
  untested limitation**.

### Scope / process
- `dynamic_folding/evaluation/comparison.py` sensitivity studies gain a `stage` field;
  `compare` text + HTML render the reducer study; `docs/SPEC.md` and
  `docs/learning/02-experimental-scope.md` updated. Tests in `tests/test_comparison*.py`
  cover the reducer-stage plumbing.

## References

- [ADR 0038](0038-bounded-empirical-justification-default-clusterer.md) — the scope this
  narrowly amends (reducer was "descriptive background").
- [ADR 0009](0009-dimensionality-reduction-stage.md) — the UMAP reducer and its hyperparameters.
- [ADR 0018](0018-empirical-characterization-no-ground-truth.md) — sensitivity = property
  #3 (responsiveness), the frame this uses.
- `docs/learning/02-experimental-scope.md` — the chapter roadmap (updated).
