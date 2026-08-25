# ADR 0039: DBCV — the Second Lens, Scored in the Reduced Space (implements ADR 0038's metric roadmap)

Date: 2026-06-20

## Status

Accepted. **Implements [ADR 0038](0038-bounded-empirical-justification-default-clusterer.md)
Decision item 3** (DBCV as the genuine second lens, which must precede any verdict).
Refines two of 0038's open points — the comparison's evaluation *space* and the
"different file subsets" limitation — and makes one **additive product-contract change**
(`RunResult` v1 → v2). ADR 0018 and 0038 remain in force in everything else.

## Context

ADR 0038 named **DBCV** (density-biased) as the genuine second lens — the opposite bias
to silhouette (convex-biased) — and made it a precondition for any verdict. Implementing
it, a throwaway spike on the frozen corpus (`datasets/downloads_2026-06-15`, n=54,
d=384) surfaced two facts that shape the design:

1. **DBCV is conceptually inapplicable in the 384-dim embedding space.** Density
   estimation needs n ≫ d; at n=54 / d=384 the library's `(1/dist)^d` core-distance term
   **overflows** and the score collapses to ≈ 0 (density effectively "switched off"). The
   `hdbscan.validity.validity_index` `d` argument does **not** reach that computation
   (verified: d ∈ {384, 10, 5, 2} give identical results *and* the same overflow), so it
   is not patchable from our side — and patching it would still yield garbage in the
   n ≪ d regime. This is a **conceptual limit, not a tunable bug**.
2. The clustering already runs in the **reduced (UMAP ~10-dim) space**; that is where
   density is meaningful and where the groups were actually drawn. DBCV is numerically
   clean and informative there.

A third empirical fact settles noise handling: **`DBCV_without_noise == DBCV_with_noise ÷
coverage`** exactly (the per-cluster geometry is independent of the noise points; only the
size-normalization changes). A "without-noise" number therefore carries no information
beyond coverage.

## Decision

1. **DBCV is scored in the reduced space** — the ~10-dim vectors the clusterer actually
   used — via `hdbscan.validity.validity_index`. **Never** the 384-dim embeddings
   (overflow; n ≪ d).

2. **Two independent lenses, not a controlled head-to-head.** Silhouette stays in the
   **384-dim meaning space** (its established, defended home — `docs/learning/05`); DBCV
   lives in the **10-dim clustering space**. They differ in **both bias and space**, so we
   never rank or subtract one against the other. *Rejected alternative:* recomputing
   silhouette in 10-dim for a same-space comparison — silhouette-10 is **not** the
   meaning-space silhouette the project defends (it answers a different question in a space
   the project itself calls semantically empty), and same-space cleanliness only buys a
   fair *verdict*, which we explicitly do not issue (n=1).

3. **Asymmetric reading (the load-bearing frame).** The reduced space is HDBSCAN's home
   turf — density bias *and* a space UMAP optimized to make density clusterable. DBCV is
   therefore the **most charitable possible** setting for HDBSCAN. Hence the only
   informative outcome is HDBSCAN **underperforming** (a strong signal); HDBSCAN topping
   DBCV is **expected and proves nothing**; kmeans/agglomerative scoring low does **not**
   count against them (wrong turf, wrong bias). This keeps **outcome-independence** intact:
   the default's justification stays a-priori **design-fit** (ADR 0038 item 2), untouched
   by these numbers; "≥ 2 lenses" remains *necessary, not sufficient*, for a verdict we
   still do not make.

4. **Noise fed as produced + coverage beside it.** The `Outros` bucket is passed to DBCV
   as noise (label `-1`), exactly as the algorithm produced it; coverage (scored/total) is
   reported next to every score. Excluding noise would **inflate** the score ("good but
   false"). Because `DBCV_without_noise == DBCV ÷ coverage`, we never report a separate
   without-noise number — it duplicates coverage. The "what if there were no noise"
   condition is already embodied by **k-means** (which produces none).

5. **Robustness (CLAUDE.md).** Degenerate partitions (< 2 groups, non-finite validity, or
   a library failure) return `None` + a reason; the harness never crashes.

6. **Additive product-contract change: `RunResult.reduced_vectors`, `contracts_version`
   1 → 2.** The reducer's output (the vectors the clusterer used) was discarded after the
   proposal was built. DBCV must score the **real** projection the groups were drawn in,
   so the pipeline now stores it on `RunResult` (empty for the identity reducer or pre-v2
   runs). *Rejected alternative:* re-deriving the projection in the evaluation layer — it
   risks scoring a *different* projection than the one that produced the groups, and
   repeats the "re-derive in evaluation" anti-pattern the restarted Chapter 4 abandoned
   (it must measure what the tool actually ships).

## Rationale

- **Density needs n ≫ d.** The meaning space cannot host DBCV, so the reduced space is not
  a preference but the **only viable home** — and the inapplicability in 384-dim is itself
  an honest, citable finding.
- **Same-space cleanliness was only a means to a fair head-to-head** — moot under n=1 /
  no-verdict — so each-lens-in-its-natural-space is both more honest and avoids a
  confusing, weaker silhouette-10.
- **The asymmetric reading is what makes it legitimate** to include a doubly-confounded
  metric at all; without it, DBCV would be post-hoc validation of the default (forbidden by
  0038's outcome-independence).
- **Scoring the shipped artifact** (not a re-derivation) is the core principle of the
  restarted chapter.

## Consequences

### Positive
- A genuine opposite-bias **second lens** now exists; the verdict-precondition of 0038 is met.
- **Outcome-independence preserved** via the asymmetric reading; no number crowns a winner.
- DBCV scores the **real clustering artifact** (the stored reduced vectors).

### Negative / owned limitations
- Silhouette and DBCV are **not directly comparable** (different space *and* bias) — by design.
- DBCV sits on **HDBSCAN's home turf** — read asymmetrically, never as a HDBSCAN win.
- Still **n=1**: illustrative on this corpus, not conclusive.

### Scope / process
- `RunResult` → **v2** (CONTRACTS.md updated; three version-pinned tests bumped 1 → 2).
- `dynamic-folding compare` text + HTML gain a **DBCV per-algorithm descriptor**
  (`dynamic_folding/evaluation/dbcv.py`, `tests/test_eval_dbcv.py`); `docs/SPEC.md` updated.
- The DBCV explainer (`docs/learning/06-dbcv-metric.md`) and the report's interpretive
  prose are authored in the **writing phase** (coached, not ghostwritten).

## References

- [ADR 0038](0038-bounded-empirical-justification-default-clusterer.md) — the metric
  roadmap this implements (DBCV as the second lens; outcome-independence).
- [ADR 0018](0018-empirical-characterization-no-ground-truth.md) — characterization
  without ground truth (in force).
- [ADR 0009](0009-dimensionality-reduction-stage.md) — the UMAP reducer whose output DBCV
  now reads.
- [ADR 0006](0006-clustering-validation-and-hdbscan.md) / [ADR 0027](0027-linkage-tree-hierarchy.md)
  — HDBSCAN and the `hdbscan` dependency that provides `validity_index`.
- `docs/learning/05-silhouette-metric.md` — the first lens and the two-space reasoning.
- `docs/learning/06-dbcv-metric.md` — the DBCV explainer (to be authored).
