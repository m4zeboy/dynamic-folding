"""2D PCA projection of a run's points, for the illustrative comparison figure.

The PURE, deterministic data step behind the "before / after grouping" figure
(ADR 0042). It casts the run's points to 2D with PCA so the report can draw them;
the drawing itself (matplotlib) is a separate, optional step — kept out of here so
this module never imports matplotlib and the projection stays testable everywhere.

Honesty / scope (see the figure ADR):
- By default we project the **384-dim embeddings** (``space="embeddings"``) — the raw
  semantic space the figure is meant to show, the same space silhouette is read in.
  The grouping, though, was cut in the ~10-dim reduced space, so the colours may not
  visually separate here: that is the point (you cannot eyeball high-dim clustering,
  hence the metrics). ``space="reduced"`` projects the ~10-dim clustering space
  instead — a flagged deviation, kept available as a safeguard.
- Outliers (the "Outros" bucket) are projected too, labelled -1, so the figure shows
  every file — what was grouped and what was left out.
- ``explained_variance`` is how much of the variance the 2 axes capture: it quantifies
  how lossy the 2D shadow is (typically small in 384-dim) — honest fuel for the caption.
- Degenerate input (fewer than 2 points or 2 dimensions, or a failed fit) returns
  empty coords + a reason; it never raises (CLAUDE.md robustness rule).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.decomposition import PCA

from dynamic_folding.contracts.run_result import RunResult
from dynamic_folding.evaluation.silhouette import _top_level_labels

# Label given to files in the "Outros" bucket (projected and shown, not grouped).
_NOISE = -1


@dataclass(frozen=True)
class Projection2D:
    coords: list[list[float]]          # N x 2 PCA coords; empty when undefined
    labels: list[int]                  # N; top-level group idx, -1 = Outros
    group_names: list[str]             # ordered by group idx
    space: str                         # "embeddings" (384-dim) or "reduced" (~10-dim)
    explained_variance: float | None   # fraction of variance the 2 axes capture
    n_outliers: int                    # files labelled -1 (Outros)
    reason: str | None = None          # why coords are empty, when they are

    @classmethod
    def from_dict(cls, d: dict) -> "Projection2D":
        """Rebuild from a serialized projection dict (ComparisonResult.to_dict).

        Tolerates an old JSON without coords (coords default to empty → the figure
        degrades to a visible note instead of crashing)."""
        return cls(
            coords=[list(c) for c in d.get("coords", [])],
            labels=list(d.get("labels", [])),
            group_names=list(d.get("group_names", [])),
            space=d.get("space", "embeddings"),
            explained_variance=d.get("explained_variance"),
            n_outliers=int(d.get("n_outliers", 0)),
            reason=d.get("reason"),
        )


def _undefined(space: str, n_outliers: int, reason: str) -> Projection2D:
    return Projection2D(
        coords=[], labels=[], group_names=[], space=space,
        explained_variance=None, n_outliers=n_outliers, reason=reason,
    )


def _source_vectors(result: RunResult, space: str) -> list[list[float]] | None:
    """The vectors to project, aligned by index with ``result.embeddings``; None
    when the requested space is unavailable."""
    if space == "reduced":
        rv = result.reduced_vectors
        if not rv or len(rv) != len(result.embeddings):
            return None
        return [list(v) for v in rv]
    return [list(e.vector) for e in result.embeddings]


def project_2d(result: RunResult, *, space: str = "embeddings") -> Projection2D:
    """PCA-project the run's points to 2D, coloured by top-level group.

    Deterministic (full SVD, fixed seed; sklearn's sign convention is stable). See
    the module docstring for the space and outlier conventions.
    """
    label_of, group_names = _top_level_labels(result.proposal)
    labels = [label_of.get(e.file.rel_path, _NOISE) for e in result.embeddings]
    n_outliers = labels.count(_NOISE)

    vectors = _source_vectors(result, space)
    if vectors is None:
        return _undefined(space, n_outliers,
                          "reduced vectors unavailable (identity reducer or pre-v2 run)")
    if len(vectors) < 2:
        return _undefined(space, n_outliers, "need at least 2 points to project")
    if len(vectors[0]) < 2:
        return _undefined(space, n_outliers, "need at least 2 dimensions to project")

    try:
        pca = PCA(n_components=2, svd_solver="full", random_state=0)
        # Identical points give zero variance -> the ratio is 0/0; we handle the
        # resulting non-finite value below rather than let the warning leak.
        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
            coords = pca.fit_transform(np.asarray(vectors, dtype=np.float64))
            ev = float(np.sum(pca.explained_variance_ratio_))
    except Exception as exc:  # a bad projection must not abort the report
        return _undefined(space, n_outliers, f"projection undefined: {exc}")

    return Projection2D(
        coords=coords.tolist(),
        labels=labels,
        group_names=group_names,
        space=space,
        explained_variance=ev if np.isfinite(ev) else None,
        n_outliers=n_outliers,
    )


def _load_pyplot():
    """matplotlib's Agg pyplot, or None when matplotlib isn't installed.

    The single, mockable seam for the optional dependency: the figure degrades to a
    visible note when this returns None, so the report never silently drops it.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")  # headless, deterministic backend
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    return plt


def render_png(projection: Projection2D) -> str | None:
    """The before/after figure as a base64-encoded PNG, or None when it cannot be
    drawn (matplotlib absent, or an empty/degenerate projection).

    Two panels share the same axes (``sharex/sharey``): identical coordinates, so the
    points never appear to move — only the colour reveals the grouping. The caller
    turns a None result into a *visible* note rather than dropping the figure.
    """
    if not projection.coords:
        return None
    plt = _load_pyplot()
    if plt is None:
        return None

    import base64
    import io

    xs = [c[0] for c in projection.coords]
    ys = [c[1] for c in projection.coords]
    labels = projection.labels
    fig, (ax_before, ax_after) = plt.subplots(
        1, 2, figsize=(10, 4.5), sharex=True, sharey=True
    )
    try:
        # Before: the same cloud, ungrouped (one neutral colour).
        ax_before.scatter(xs, ys, c="#b0b0b0", s=18, edgecolors="none")
        ax_before.set_title("Antes (dados)")

        # After: same coordinates, coloured by group; "Outros" stays neutral.
        cmap = plt.get_cmap("tab10")
        for gi in sorted({lab for lab in labels if lab != _NOISE}):
            idx = [i for i, lab in enumerate(labels) if lab == gi]
            # Deterministic per-run group labels ("Grupo N"); the numbering is local to
            # this run and not comparable across algorithms (see docs/learning/02 §5).
            ax_after.scatter([xs[i] for i in idx], [ys[i] for i in idx],
                             c=[cmap(gi % 10)], s=18, edgecolors="none", label=f"Grupo {gi + 1}")
        out = [i for i, lab in enumerate(labels) if lab == _NOISE]
        if out:
            ax_after.scatter([xs[i] for i in out], [ys[i] for i in out],
                             c="#d0d0d0", s=14, marker="x", label="Outros")
        ax_after.set_title("Depois (grupos)")
        if ax_after.get_legend_handles_labels()[0]:
            ax_after.legend(fontsize=7, loc="best", framealpha=0.6)

        for ax in (ax_before, ax_after):
            ax.set_xlabel("PC1")
            ax.set_ylabel("PC2")
        fig.tight_layout()

        buf = io.BytesIO()
        # Fixed metadata (no embedded timestamp/version) for reproducible bytes.
        fig.savefig(buf, format="png", dpi=110, metadata={"Software": "dynamic-folding"})
        return base64.b64encode(buf.getvalue()).decode("ascii")
    finally:
        plt.close(fig)
