from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AgglomerativeLinkage:
    """Linkage tree from sklearn AgglomerativeClustering (children_ / distances_ format).

    children[k] = (left, right): the k-th merge fused nodes 'left' and 'right'.
    Node ids 0 .. n_leaves-1 are original data points (leaves).
    Node ids n_leaves .. 2*n_leaves-2 are internal merge nodes.
    distances[k]: Euclidean (or ward / etc.) distance at which merge k occurred.
    """

    children: list[tuple[int, int]]
    distances: list[float]
    n_leaves: int


@dataclass(frozen=True)
class CondensedTreeData:
    """Condensed tree produced by the McInnes hdbscan package for sub-level extraction.

    Each row i of the tree is encoded by the four parallel lists:
        parents[i]     — parent cluster node id
        children[i]    — child node id
                         < n_leaves  → original data-point (left as noise)
                         >= n_leaves → sub-cluster node that split off
        lambda_vals[i] — λ = 1/distance at which the split / noise-departure occurred
        child_sizes[i] — number of original data points under children[i]

    selected_nodes maps each top-level cluster label (as stored in
    ClusterPartition.labels) to the condensed-tree node id that EOM selected for
    that cluster.  This is the starting node for sub-level extraction.
    """

    parents: list[int]
    children: list[int]
    lambda_vals: list[float]
    child_sizes: list[int]
    n_leaves: int
    # cluster label (0, 1, 2 ...) → condensed-tree node id
    selected_nodes: dict[int, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ClusterPartition:
    """Unified return type for every clustering algorithm.

    labels:             cluster assignments aligned with input vectors; -1 = outlier / noise.
    linkage:            tree structure enabling multi-level hierarchy extraction without
                        re-running the algorithm.  None for flat clusterers (kmeans, random).
    distance_threshold: agglomerative cut threshold used (telemetry only; None for others).
    """

    labels: list[int]
    linkage: AgglomerativeLinkage | CondensedTreeData | None = None
    distance_threshold: float | None = None
