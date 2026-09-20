# ADR 0042: Illustrative PCA-2D figure (data before / after grouping)

Date: 2026-06-25

## Status

Accepted.

## Context

The orientadora's feedback on the first comparison report asked for a data
visualization: show the corpus **before** and **after** grouping (a 2D projection
coloured by cluster). This is genuinely illustrative, and an honest version has a trap:
the grouping runs in the ~10-dim reduced (UMAP) space and the metrics are read in
384-dim (silhouette) / 10-dim (DBCV), so **no 2D scatter is the space where the math
happens**. The figure must show the data without implying it is evidence, and without
flattering the result.

## Decision

1. **PCA-2D, not UMAP-2D.** PCA is a deterministic linear projection (CLAUDE.md's
   determinism is a hard rule; a UMAP-2D would add a second stochastic step) and a
   *faithful* shadow — it does not manufacture separation. UMAP's separation-creating
   property is a feature for the *reducer* (it is what makes density clustering work in
   10-dim) but a **bug** for an honest illustration, where it would make any cloud look
   well grouped.

2. **Project the 384-dim embeddings** (`space="embeddings"`, the default) — the raw
   semantic space the figure is meant to show, the same space silhouette reads. Because
   the groups were cut in the 10-dim space, the colours may **not** visually separate
   here; that is the point — you cannot eyeball high-dim clustering, which is *why* the
   chapter builds silhouette and DBCV. `space="reduced"` (10-dim) is kept available as a
   **flagged-deviation safeguard**, to be used only if the 384 panel is illegible.

3. **The default algorithm only** (HDBSCAN). Three colourings side by side would invite a
   visual verdict ("which looks best"), against outcome-independence — and doubly
   meaningless here, since apparent cleanliness is partly a 384→2D projection artifact.
   The cross-algorithm contrast already lives, quantitatively, in the matrices.

4. **Both panels share identical coordinates** (before = neutral grey, after = coloured
   by group; matplotlib `sharex`/`sharey`). The points must never appear to *move*; only
   the colour reveals the grouping.

5. **matplotlib is an optional `[viz]` extra; the figure degrades loudly.** The
   projection (data) is always computed — pure `sklearn` PCA, deterministic, and needing
   **no contract change** (the 384-dim embeddings are already on `RunResult`, unlike DBCV
   which required `reduced_vectors`). Only the *drawing* needs matplotlib; when it is
   absent the report shows a **visible note** (install `.[viz]`), never a silently dropped
   figure — so a figureless report is never mistaken for a complete one.

6. **`explained_variance` is exposed** (the fraction of variance the 2 axes capture). It
   quantifies how lossy the 2D shadow is — honest fuel for the author-written caption.

## Rationale

- The figure is **illustrative, not evidence**: it issues no verdict and crowns no
  algorithm, consistent with the exploratory, two-lens, n=1 framing (ADR 0038/0039/0041).
- Reframing the honesty caveat as the figure's *point* (if you cannot see the groups by
  eye, that is why the metrics exist) turns a limitation into motivation, fully honestly.
- The pure-data / optional-draw split keeps determinism testable everywhere and the new
  dependency clean: no module imports matplotlib at top level (the import is lazy inside
  `render_png`), so the suite stays green without the extra.

## Consequences

- New `dynamic_folding/evaluation/projection.py`: `project_2d` (pure, deterministic, full
  SVD, fixed seed) + `render_png` (lazy matplotlib, base64 PNG or `None`). Tested with and
  without matplotlib (`tests/test_projection.py`).
- `ComparisonResult` gains a local `projection` field (a comparison-layer DTO, so
  `docs/CONTRACTS.md` is unchanged); the report renders it, or the visible note.
- `pyproject.toml` gains a `viz = ["matplotlib"]` optional extra.
- The interpretive **caption is left as a marked placeholder** for the author — the report
  prose is authored, not generated.
