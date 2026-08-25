# ADR 0038: Bounded Empirical Justification of the Default Clusterer (amends ADR 0018)

Date: 2026-06-14

## Status

Accepted. **Amends [ADR 0018](0018-empirical-characterization-no-ground-truth.md)**
on two axes (comparative scope; corpora count), detailed below. ADR 0018 remains in
force in everything else — no ground truth, no ARI/NMI/self-labeled corpus, internal
metrics characterize rather than certify. ADR 0006 (HDBSCAN integration) is unchanged.

**Refined by [ADR 0039](0039-dbcv-second-lens-reduced-space.md)** — implements the DBCV
second lens (scored in the reduced space, noise-fed) and adds `RunResult.reduced_vectors`
(contract v2).

**Amended by [ADR 0040](0040-reducer-enters-sensitivity-lightly.md)** — the reducer enters
the sensitivity study lightly (one knob, `n_components`), revisiting Decision item 1's
"reducer stays background".

## Context

ADR 0018 framed thesis Chapter 4 as **descriptive characterization without ground
truth**, computed across **3–4 corpora**, and warned that internal metrics
(silhouette) measure cohesion — not correctness or usefulness — so they cannot be
used over a grid search to "validate" a configuration.

Since then, Chapter 4 was **restarted from scratch**: one metric at a time, measuring
what the tool actually ships (the real proposal's labels + the raw 384-dim
embeddings), not a re-clustering of raw vectors. The silhouette metric, a random
baseline, and a per-group breakdown are built and merged (PR #61); the reasoning is
in `docs/learning/05-silhouette-metric.md`. The roadmap for the chapter is
`docs/learning/02-experimental-scope.md`.

Two pressures motivate a **bounded** expansion of 0018's scope:

1. The clustering algorithm (HDBSCAN) was adopted on intuition (ADR 0006) and has
   **never been compared** to kmeans/agglomerative; its **hyperparameters were never
   varied**. Leaving the chapter's central strategic choice unjustified is a thesis
   gap the student wants to close.
2. The restarted work, in practice, uses a **single corpus** (the user's Downloads
   folder — the deliberately messy real-world case), not 3–4.

The tension this ADR must resolve: comparing algorithms with internal metrics risks
re-importing exactly what 0018 rejected ("the best-scoring algorithm wins"). The
resolution is to keep the epistemic claim narrow — *provenance and honest trade-off
characterization*, never *certification of optimality*.

## Decision

1. **Expand the scope from "descriptive, not comparative" to "descriptive + bounded
   empirical justification"** of the default's strategic choices: the **clustering
   algorithm** and its **hyperparameters**. The reducer (UMAP) and other stages stay
   descriptive background. (Amends 0018's descriptive-only framing.)

2. **The justification is provenance + honest trade-off characterization — not
   optimization, not validation.**
   - The **primary** justification of the default is **design-fit** (HDBSCAN models
     noise → the `Outros` bucket; arbitrary cluster shapes; no preset K; matches
     messy real input) — independent of any metric.
   - Internal metrics **characterize trade-offs**; they do **not** certify
     correctness (0018's principle, preserved). **No single number crowns a winner.**
   - **Outcome-independence is binding**: every claim must read as clean and honest
     *regardless of which algorithm scores higher on which lens*.

3. **Multiple lenses, each bias stated.** Silhouette (convex-biased, *against*
   density methods) is the lens that exists today; **DBCV** (density-biased, the
   opposite way) is the genuine second lens and **must precede any verdict**.
   Davies-Bouldin / Calinski-Harabasz are **not** second opinions (same convex bias).
   **Structural descriptors** (#groups, #outliers, size distribution) are reported
   alongside as a non-metric signal — and carry the design-fit story even if HDBSCAN
   loses on a metric (kmeans cannot produce an `Outros` bucket at all).

4. **Hyperparameter variation is in scope as sensitivity + provenance** — explicitly
   **ADR 0018's property #3** ("does behavior change with configuration in
   theory-consistent ways?"), *not* a search for optimal values. One key at a time,
   "report + discuss", with the small-n caveat. Focus is the clustering algorithm's
   hyperparameters (e.g. `min_cluster_size`). Honest caveat: read through a single
   metric lens, a silhouette that responds to a knob shows *responsiveness*, not that
   the higher-scoring setting is "better" (same convex bias).

5. **Single corpus (n=1), owned.** 0018's "3–4 corpora" (Decision item 4) is amended
   to **one corpus** (Downloads). A comparison on n=1 is declared **illustrative on
   this corpus, not conclusive** (n=1 weakens a comparison far more than a
   description). This is stated as a limitation, not hidden.

6. **Reproducibility convention.** Tables label groups **"Grupo N"** (scores are
   deterministic; LLM naming is not). Numbering is **per-run** — not comparable across
   algorithms — so cross-algorithm comparison rests on aggregate/structural numbers,
   not name-matching.

7. **Artifact.** Each pass produces a **self-contained PT-BR HTML report** in the
   **V1 Sereno** design system (ADR 0032), **generated from a real run** (provenance,
   offline, no network), complete enough for a reader without the project's context
   (e.g. the advisor). The report **inherits the honesty above**: exploratory, biases
   named, n=1, no crowned winner.

## Rationale

- **Honest framing over false rigor** is 0018's own principle. Characterizing
  geometry and discussing biases as *provenance for a design choice* is a different
  epistemic claim than certifying correctness — a banca accepts the former only as
  long as it never slides into the latter, which items 2–3 enforce.
- **Sensitivity is already blessed by 0018** (property #3), so committing to
  hyperparameter variation *strengthens* the prior decision rather than contradicting
  it.
- **Design-fit as the primary justification** keeps the default's defense independent
  of any contested metric — the load-bearing move that makes the expansion safe.

## Consequences

### Positive
- The chapter's central strategic choice gains **provenance**; the chapter gains a
  methodological contribution (honest multi-lens trade-off discussion) without
  claiming optimality.
- A reproducible, self-contained artifact communicates progress to the advisor.

### Negative / owned limitations
- **n=1**: illustrative, not conclusive.
- **Different file subsets across algorithms**: silhouette excludes the `Outros`
  bucket and kmeans produces no outliers, so algorithms would be scored on different
  files unless a common set is used or coverage is reported beside each score — to be
  handled in the comparison harness.
- **Single metric lens** until DBCV lands: reliance on silhouette is mitigated only
  by the structural descriptors in the meantime.

### Scope / process
- No code or product contract changes in this ADR; it records the scope decision. The
  comparison harness + the new evaluation report (template, builder, CLI) are a
  separate step and will update `docs/SPEC.md` when implemented.

## References

- [ADR 0018](0018-empirical-characterization-no-ground-truth.md) — the
  characterization decision this amends (axes: comparative scope; corpora count).
- [ADR 0006](0006-clustering-validation-and-hdbscan.md) — why HDBSCAN was added
  (the choice now getting provenance).
- [ADR 0032](0032-html-report-v1-sereno.md) — the V1 Sereno report the artifact reuses.
- `docs/learning/02-experimental-scope.md` — the chapter roadmap (this ADR's prose home).
- `docs/learning/05-silhouette-metric.md` — the silhouette lens and its biases.
