from __future__ import annotations

import numpy as np
from collections import defaultdict
from typing import Any

from dynamic_folding.clustering.result import AgglomerativeLinkage, ClusterPartition, CondensedTreeData
from dynamic_folding.contracts.embedding import EmbeddingRecord
from dynamic_folding.contracts.preprocessed import PreprocessedDoc
from dynamic_folding.contracts.proposal import StructureProposal, FolderNode
from dynamic_folding.core.windows import apply_windows_safe_suffix
from collections.abc import Callable


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _cosine_sim(v1: list[float], v2: list[float]) -> float:
    a1 = np.array(v1)
    a2 = np.array(v2)
    n1 = np.linalg.norm(a1)
    n2 = np.linalg.norm(a2)
    if n1 > 0 and n2 > 0:
        return float(np.dot(a1, a2) / (n1 * n2))
    return 0.0


def _collect_all_rels(node: FolderNode) -> set[str]:
    """Recursively collect every file path in a FolderNode tree."""
    result: set[str] = set(node.files)
    for sub in node.subfolders:
        result.update(_collect_all_rels(sub))
    return result


# ---------------------------------------------------------------------------
# Union-Find for agglomerative sub-tree cutting
# ---------------------------------------------------------------------------

class _UnionFind:
    def __init__(self, members: list[int]) -> None:
        self._parent: dict[int, int] = {x: x for x in members}

    def find(self, x: int) -> int:
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]  # path halving
            x = self._parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._parent[ra] = rb

    def components(self) -> dict[int, list[int]]:
        groups: dict[int, list[int]] = {}
        for x in self._parent:
            root = self.find(x)
            groups.setdefault(root, []).append(x)
        return groups


# ---------------------------------------------------------------------------
# Agglomerative sub-tree cut
# ---------------------------------------------------------------------------

def _cut_agglomerative_subtree(
    leaf_indices: list[int],
    ag: AgglomerativeLinkage,
    min_cluster_size: int,
) -> list[int]:
    """Partition *leaf_indices* by cutting the agglomerative linkage tree.

    Returns labels aligned with leaf_indices.  -1 = outlier (cluster smaller
    than min_cluster_size).  Applies the same coverage-maximising / lower-
    threshold-tiebreaker heuristic used by _select_threshold in
    agglomerative_tree.py — but operates directly on the stored tree without
    re-fitting AgglomerativeClustering.

    Algorithm
    ---------
    1. Build descendant frozensets for every internal node.
    2. Collect "sub-merges": merges where ALL descendants are in leaf_indices.
    3. Build candidate thresholds from midpoints between consecutive distances.
    4. For each candidate threshold, simulate with union-find and score.
    5. Select threshold that maximises non-outlier coverage (lower wins ties).
    6. Mark small clusters as -1; remap remainder to 0..K-1.
    """
    if not leaf_indices:
        return []
    if len(leaf_indices) == 1:
        return [0] if min_cluster_size <= 1 else [-1]

    n = ag.n_leaves
    S = frozenset(leaf_indices)
    idx_map: dict[int, int] = {gi: li for li, gi in enumerate(leaf_indices)}

    # Step 1: descendant sets for all nodes.
    desc: list[frozenset[int]] = [frozenset({i}) for i in range(n)]
    for left, right in ag.children:
        desc.append(desc[left] | desc[right])

    # Step 2: sub-merges entirely within S, sorted by distance.
    sub_merges: list[tuple[float, int, int]] = []  # (dist, left, right)
    for k, (left, right) in enumerate(ag.children):
        if desc[n + k] <= S:
            sub_merges.append((ag.distances[k], left, right))
    sub_merges.sort(key=lambda x: x[0])

    if not sub_merges:
        # No internal structure available.
        if len(leaf_indices) >= min_cluster_size:
            return [0] * len(leaf_indices)
        return [-1] * len(leaf_indices)

    # Precompute a representative leaf for each node.
    # rep[v] = a leaf in desc[v] ∩ S (guaranteed for sub-merge nodes since desc⊆S).
    rep: list[int] = list(range(n))
    for left, right in ag.children:
        rep.append(rep[left])

    # Step 3: candidate thresholds.
    unique_d = sorted({d for d, _, _ in sub_merges})
    if len(unique_d) == 1:
        candidates: list[float] = [unique_d[0] * 0.5, unique_d[0] * 2.0]
    else:
        candidates = [(unique_d[i] + unique_d[i + 1]) / 2.0 for i in range(len(unique_d) - 1)]

    best_labels: list[int] = [0] * len(leaf_indices)
    best_score: int = 0
    best_t: float = float("inf")

    # Step 4: evaluate each threshold.
    for t in candidates:
        uf = _UnionFind(leaf_indices)
        for d, left, right in sub_merges:
            if d > t:
                break
            uf.union(rep[left], rep[right])

        comps = uf.components()
        labels_t: list[int] = [-1] * len(leaf_indices)
        score = 0
        cid = 0
        for members in comps.values():
            if len(members) >= min_cluster_size:
                for gi in members:
                    labels_t[idx_map[gi]] = cid
                score += len(members)
                cid += 1

        if score > best_score or (score == best_score and t < best_t):
            best_score = score
            best_t = t
            best_labels = labels_t

    return best_labels


# ---------------------------------------------------------------------------
# HDBSCAN condensed-tree sub-level extraction (EOM within subtree)
# ---------------------------------------------------------------------------

def _hdbscan_eom_subtree(
    root_node_id: int,
    ct: CondensedTreeData,
    min_cluster_size: int,
) -> list[tuple[int, int, list[int]]]:
    """Extract sub-clusters from the condensed tree rooted at *root_node_id*.

    Applies the EOM (Excess of Mass) criterion within the subtree, with the
    constraint that root_node_id itself is NEVER selected — this forces at
    least one level of sub-division (appropriate for folder hierarchy proposals).

    Returns a list of (local_label, node_id, leaf_global_indices) tuples.
    local_label is 0-indexed.  Returns empty list if no stable sub-clusters
    are found.

    EOM recap (Campello et al. 2013/2015)
    -------------------------------------
    stability(C) = Σ_{i: row parent=C} child_sizes[i] * (lambda_vals[i] − λ_birth(C))

    Bottom-up propagation:
      • Leaf cluster (no internal children): selected; score = stability.
      • Internal cluster (has internal children):
          if stability(C) ≥ Σ children scores → select C, deselect its descendants
          else → don't select C; propagate children scores.
      • root_node_id is never selected (we always want sub-clusters).
    """
    n_leaves = ct.n_leaves

    # Build parent → [child, ...] adjacency (all children, leaf and internal).
    children_of: dict[int, list[tuple[int, float, int]]] = {}
    for p, c, lv, cs in zip(ct.parents, ct.children, ct.lambda_vals, ct.child_sizes):
        children_of.setdefault(p, []).append((c, lv, cs))

    # Collect all internal nodes in the subtree (DFS pre-order).
    subtree_nodes: list[int] = []

    def _collect(node_id: int) -> None:
        subtree_nodes.append(node_id)
        for child, _, _ in children_of.get(node_id, []):
            if child >= n_leaves:
                _collect(child)

    _collect(root_node_id)

    if len(subtree_nodes) <= 1:
        return []  # root has no internal descendants → no sub-structure

    # λ_birth for root_node_id: the lambda_val at which it split from its parent
    # (we need this to compute root's stability, though root is never selected).
    child_to_parent_lambda: dict[int, float] = {}
    for p, c, lv, cs in zip(ct.parents, ct.children, ct.lambda_vals, ct.child_sizes):
        child_to_parent_lambda[c] = lv

    lambda_birth: dict[int, float] = {root_node_id: child_to_parent_lambda.get(root_node_id, 0.0)}
    for node_id in subtree_nodes:
        for child, lv, _ in children_of.get(node_id, []):
            if child >= n_leaves:
                lambda_birth[child] = lv

    # Stability: Σ over all direct entries (leaf or sub-cluster children).
    def _stability(node_id: int) -> float:
        lb = lambda_birth[node_id]
        return sum(cs * (lv - lb) for _, lv, cs in children_of.get(node_id, []))

    stability: dict[int, float] = {nid: _stability(nid) for nid in subtree_nodes}

    # Pre-compute the set of all internal descendants for each subtree node so
    # that when a node is selected we can deselect only ITS descendants, not
    # unrelated sibling subtrees.
    def _internal_descendants(nid: int) -> set[int]:
        out: set[int] = set()
        stack = [nid]
        while stack:
            x = stack.pop()
            for child, _, _ in children_of.get(x, []):
                if child >= n_leaves:
                    out.add(child)
                    stack.append(child)
        return out

    desc_of: dict[int, set[int]] = {nid: _internal_descendants(nid) for nid in subtree_nodes}

    # EOM bottom-up pass (subtree_nodes is pre-order; reverse = bottom-up).
    selected_score: dict[int, float] = {}
    is_selected: dict[int, bool] = {}

    # Index of internal (cluster) children for each node in the subtree.
    internal_children_of: dict[int, list[int]] = {
        nid: [c for c, _, _ in children_of.get(nid, []) if c >= n_leaves]
        for nid in subtree_nodes
    }

    for node_id in reversed(subtree_nodes):
        int_children = internal_children_of[node_id]

        if not int_children:
            # Leaf cluster in subtree.
            node_size = sum(cs for _, _, cs in children_of.get(node_id, []))
            if node_id != root_node_id and node_size >= min_cluster_size:
                selected_score[node_id] = stability[node_id]
                is_selected[node_id] = True
            else:
                selected_score[node_id] = 0.0
                is_selected[node_id] = False
        else:
            children_sum = sum(selected_score.get(c, 0.0) for c in int_children)
            node_size = sum(cs for _, _, cs in children_of.get(node_id, []))

            if node_id == root_node_id:
                # Root is never selected; propagate children scores upward.
                selected_score[node_id] = children_sum
                is_selected[node_id] = False
            elif node_size >= min_cluster_size and stability[node_id] >= children_sum:
                # This node beats its children: select it and deselect only its
                # internal descendants (not sibling subtrees).
                selected_score[node_id] = stability[node_id]
                is_selected[node_id] = True
                for desc_id in desc_of[node_id]:
                    is_selected[desc_id] = False
            else:
                selected_score[node_id] = children_sum
                is_selected[node_id] = False

    # Collect the final selected nodes (no ancestor also selected).
    raw_selected = [nid for nid in subtree_nodes if is_selected.get(nid, False)]
    if not raw_selected:
        return []

    # Build leaf lists for each selected node.
    def _get_leaves(node_id: int) -> list[int]:
        if node_id < n_leaves:
            return [node_id]
        result: list[int] = []
        for child, _, _ in children_of.get(node_id, []):
            result.extend(_get_leaves(child))
        return result

    return [(i, nid, _get_leaves(nid)) for i, nid in enumerate(raw_selected)]


# ---------------------------------------------------------------------------
# Naming: shared node finalizer (per-node vs bottom-up) — ADR 0037
# ---------------------------------------------------------------------------

# Fallback / sentinel labels a namer may emit. A parent must not inherit these
# from a child (they carry no theme), and they are filtered before aggregation.
_FALLBACK_NAMES = frozenset({"Group", "unnamed_group", "_Ambíguo", "_Ambiguo", "Outros"})


def _name_parent_bottom_up(
    *,
    subfolders: list[FolderNode],
    node_files: list[str],
    global_idxs: list[int],
    rels: list[str],
    get_texts: Callable[[list[int]], list[str]],
    namer: Callable[[list[str], dict], str],
    naming_cfg: dict,
) -> str:
    """Name an internal node from its children's names + its loose-file signal.

    The parent borrows meaning from already-named, coherent children instead of
    being asked to thematize its full heterogeneous doc-bag (the failure mode
    that produced the meaningless "Group" label; see ADR 0037).

    Passes CLEAN strings to the namer — child names as ``texts`` and the loose
    files' raw texts via ``cfg["loose_texts"]``. No structural marker tokens are
    tokenized (the "subpastas/arquivos" framing lives only in the Ollama prompt),
    so the TF-IDF fallback cannot surface them as anchor terms.
    """
    child_names = [sf.name for sf in subfolders if sf.name not in _FALLBACK_NAMES]

    if not child_names:
        # Every child is a fallback label — nothing to propagate. Degrade to
        # per-node naming from the node's own documents.
        group_texts = get_texts(global_idxs)
        if not any(t.strip() for t in group_texts):
            group_texts = [rels[i] for i in global_idxs]
        return namer(group_texts, naming_cfg)

    loose_set = set(node_files)
    loose_idxs = [i for i in global_idxs if rels[i] in loose_set]
    loose_texts = [t for t in get_texts(loose_idxs) if t and t.strip()]

    agg_cfg = {**naming_cfg, "aggregate": True, "loose_texts": loose_texts}
    return namer(child_names, agg_cfg)


def _finalize_node(
    global_idxs: list[int],
    subfolders: list[FolderNode],
    *,
    rels: list[str],
    vecs: list[list[float]],
    get_texts: Callable[[list[int]], list[str]],
    namer: Callable[[list[str], dict], str],
    naming_cfg: dict,
    naming_direction: str,
    embed_text: Callable[[str], list[float]] | None,
    used_names: set[str],
) -> FolderNode:
    """Build one FolderNode from its already-constructed subfolders.

    Structure-invariant: ``node_files`` (loose files = node rels minus those
    placed in a subfolder) and ``subfolders`` are computed identically for both
    naming directions — only the *source* of ``name`` differs. In ``per_node``
    mode this reproduces the legacy behavior exactly (the name does not depend
    on the recursion, so computing it after the recursion changes nothing).
    """
    placed: set[str] = set()
    for sf in subfolders:
        placed.update(_collect_all_rels(sf))
    node_files = sorted(
        [rels[i] for i in global_idxs if rels[i] not in placed], key=str.casefold
    )

    if naming_direction == "bottom_up" and subfolders:
        name = _name_parent_bottom_up(
            subfolders=subfolders,
            node_files=node_files,
            global_idxs=global_idxs,
            rels=rels,
            get_texts=get_texts,
            namer=namer,
            naming_cfg=naming_cfg,
        )
    else:
        group_texts = get_texts(global_idxs)
        if not any(t.strip() for t in group_texts):
            group_texts = [rels[i] for i in global_idxs]
        name = namer(group_texts, naming_cfg)

    base = name
    n = 2
    while name in used_names:
        name = apply_windows_safe_suffix(base, n)
        n += 1
    used_names.add(name)

    name_match = None
    if embed_text:
        name_vec = embed_text(name)
        if name_vec:
            centroid = np.mean([vecs[i] for i in global_idxs], axis=0).tolist()
            name_match = _cosine_sim(name_vec, centroid)

    return FolderNode(
        name=name, files=node_files, subfolders=subfolders, name_match=name_match
    )


# ---------------------------------------------------------------------------
# _build_level_from_tree  (tree-cut path for agglomerative and HDBSCAN)
# ---------------------------------------------------------------------------

def _build_level_from_tree(
    idxs: list[int],
    current_level: int,
    max_levels: int,
    *,
    linkage: AgglomerativeLinkage | CondensedTreeData,
    cluster_node_id: int | None,  # condensed-tree node id; None for agglomerative
    rels: list[str],
    vecs: list[list[float]],
    clustering_vecs: list[list[float]],
    get_texts: Callable[[list[int]], list[str]],
    namer: Callable[[list[str], dict], str],
    naming_cfg: dict,
    min_cluster_size: int,
    embed_text: Callable[[str], list[float]] | None,
    naming_direction: str = "per_node",
) -> list[FolderNode]:
    """Build sub-folder nodes by cutting the linkage tree instead of re-clustering.

    For AgglomerativeLinkage: calls _cut_agglomerative_subtree on idxs.
    For CondensedTreeData: calls _hdbscan_eom_subtree on cluster_node_id.
    Recurses until current_level >= max_levels or clusters are too small.
    """
    if not idxs:
        return []

    # --- Cut the appropriate tree structure ---
    # Each entry: (local_label, sub_node_id_or_None, global_leaf_indices)
    sub_info: list[tuple[int, int | None, list[int]]] = []

    if isinstance(linkage, AgglomerativeLinkage):
        sub_labels = _cut_agglomerative_subtree(idxs, linkage, min_cluster_size)
        groups: dict[int, list[int]] = defaultdict(list)
        for li, lab in enumerate(sub_labels):
            if lab >= 0:
                groups[lab].append(idxs[li])
        for lab in sorted(groups.keys()):
            sub_info.append((lab, None, groups[lab]))

    elif isinstance(linkage, CondensedTreeData):
        if cluster_node_id is None:
            return []
        eom_results = _hdbscan_eom_subtree(cluster_node_id, linkage, min_cluster_size)
        # Filter leaves to only those in idxs: _get_leaves walks the full
        # condensed tree and returns every leaf under a node, including noise
        # leaves (labels_ == -1) that were already routed to the outliers folder.
        # Without this filter the same rel_path would appear both in the
        # outliers folder and in a sub-folder.
        target = set(idxs)
        for local_lab, node_id, leaves in eom_results:
            filtered = [l for l in leaves if l in target]
            if len(filtered) >= min_cluster_size:
                sub_info.append((local_lab, node_id, filtered))

    if not sub_info:
        return []

    # --- Build FolderNodes (recurse, then name — supports bottom-up; ADR 0037) ---
    nodes: list[FolderNode] = []
    used_names: set[str] = set()

    for lab, sub_node_id, global_idxs in sub_info:
        subfolders: list[FolderNode] = []
        if current_level < max_levels and len(global_idxs) >= max(2, min_cluster_size * 2):
            subfolders = _build_level_from_tree(
                global_idxs,
                current_level + 1,
                max_levels,
                linkage=linkage,
                cluster_node_id=sub_node_id,
                rels=rels,
                vecs=vecs,
                clustering_vecs=clustering_vecs,
                get_texts=get_texts,
                namer=namer,
                naming_cfg=naming_cfg,
                min_cluster_size=min_cluster_size,
                embed_text=embed_text,
                naming_direction=naming_direction,
            )

        nodes.append(_finalize_node(
            global_idxs,
            subfolders,
            rels=rels,
            vecs=vecs,
            get_texts=get_texts,
            namer=namer,
            naming_cfg=naming_cfg,
            naming_direction=naming_direction,
            embed_text=embed_text,
            used_names=used_names,
        ))

    return nodes


# ---------------------------------------------------------------------------
# _build_level  (kept as-is for the kmeans / random_baseline fallback path)
# ---------------------------------------------------------------------------

def _build_level(
    idxs: list[int],
    current_level: int,
    max_levels: int,
    *,
    rels: list[str],
    vecs: list[list[float]],
    clustering_vecs: list[list[float]],
    get_texts: Callable[[list[int]], list[str]],
    namer: Callable[[list[str], dict], str],
    naming_cfg: dict,
    algorithm: str,
    clusterer: Callable[[list[list[float]], dict], ClusterPartition] | None,
    clustering_cfg: dict,
    min_cluster_size: int,
    sub_k: int,
    random_state: int,
    embed_text: Callable[[str], list[float]] | None,
    naming_direction: str = "per_node",
) -> list[FolderNode]:
    """Recursively build folder nodes (fallback path: kmeans / random_baseline)."""
    if not idxs:
        return []

    # Prepare data for this subset
    subset_vecs_original = [vecs[i] for i in idxs]
    subset_vecs_clustering = [clustering_vecs[i] for i in idxs]

    # Cluster this level
    algo_clean = str(algorithm).strip().lower()
    if algo_clean in ("agglomerative_tree", "hdbscan") and clusterer is not None:
        ccfg = dict(clustering_cfg)
        ccfg.setdefault("min_cluster_size", int(min_cluster_size))
        partition_sub = clusterer(subset_vecs_clustering, ccfg)
        labels = list(partition_sub.labels)
    else:
        # Fallback to KMeans
        from dynamic_folding.clustering.kmeans import cluster_kmeans
        k = min(len(idxs), sub_k)
        result = cluster_kmeans(subset_vecs_original, k=k, random_state=random_state)
        labels = list(result.labels)

    # Group by label
    groups: dict[int, list[int]] = defaultdict(list)
    for i, lab in enumerate(labels):
        groups[int(lab)].append(i)

    nodes: list[FolderNode] = []
    used_names: set[str] = set()

    for lab in sorted(groups.keys()):
        if lab == -1:
            continue  # Handled as 'files' in the parent node

        local_idxs = groups[lab]
        global_idxs = [idxs[li] for li in local_idxs]

        # Recurse first, then name (supports bottom-up; ADR 0037).
        subfolders: list[FolderNode] = []
        if current_level < max_levels and len(global_idxs) >= max(2, min_cluster_size * 2):
            subfolders = _build_level(
                global_idxs,
                current_level + 1,
                max_levels,
                rels=rels,
                vecs=vecs,
                clustering_vecs=clustering_vecs,
                get_texts=get_texts,
                namer=namer,
                naming_cfg=naming_cfg,
                algorithm=algorithm,
                clusterer=clusterer,
                clustering_cfg=clustering_cfg,
                min_cluster_size=min_cluster_size,
                sub_k=sub_k,
                random_state=random_state,
                embed_text=embed_text,
                naming_direction=naming_direction,
            )

        nodes.append(_finalize_node(
            global_idxs,
            subfolders,
            rels=rels,
            vecs=vecs,
            get_texts=get_texts,
            namer=namer,
            naming_cfg=naming_cfg,
            naming_direction=naming_direction,
            embed_text=embed_text,
            used_names=used_names,
        ))

    return nodes


# ---------------------------------------------------------------------------
# propose_structure  (main entry point)
# ---------------------------------------------------------------------------

def propose_structure(
    *,
    root: str,
    preprocessed: list[PreprocessedDoc],
    embeddings: list[EmbeddingRecord],
    top_k: int,
    sub_k: int,
    random_state: int,
    namer: Callable[[list[str], dict], str],
    naming_cfg: dict,
    algorithm: str = "kmeans",
    clusterer: Callable[[list[list[float]], dict], ClusterPartition] | None = None,
    clustering_cfg: dict | None = None,
    min_cluster_size: int = 4,
    max_levels: int = 2,
    outliers_folder: str = "Outros",
    reduced_vectors: list[list[float]] | None = None,
    embed_text: Callable[[str], list[float]] | None = None,
    fetch_texts: Callable[[list[str]], list[str]] | None = None,
    naming_direction: str = "per_node",
) -> StructureProposal:
    # Align by rel_path
    by_rel = {d.file.rel_path: d for d in preprocessed}
    items: list[tuple[str, list[float], str, list[float] | None]] = []

    reduced_vecs_map: dict[str, list[float]] = {}
    if reduced_vectors:
        for i, rv in enumerate(reduced_vectors):
            if i < len(embeddings):
                reduced_vecs_map[embeddings[i].file.rel_path] = rv

    for e in embeddings:
        rel = e.file.rel_path
        d = by_rel.get(rel)
        txt = d.text_for_embedding if d else ""
        items.append((rel, e.vector, txt, reduced_vecs_map.get(rel)))

    if not items:
        return StructureProposal(
            root=root,
            folders=[],
            orphans=[],
            notes=["No files to propose."],
        )

    rels = [x[0] for x in items]
    vecs = [x[1] for x in items]
    clustering_vecs = [x[3] if x[3] is not None else x[1] for x in items]

    def get_texts(indices: list[int]) -> list[str]:
        batch_rels = [rels[i] for i in indices]
        if fetch_texts:
            return fetch_texts(batch_rels)
        return [items[i][2] for i in indices]

    # -----------------------------------------------------------------------
    # Top-level partition
    # -----------------------------------------------------------------------
    algo_clean = str(algorithm).strip().lower()
    if algo_clean in ("agglomerative_tree", "hdbscan") and clusterer is not None:
        ccfg = dict(clustering_cfg or {})
        ccfg.setdefault("min_cluster_size", int(min_cluster_size))
        top_partition: ClusterPartition = clusterer(clustering_vecs, ccfg)
    else:
        from dynamic_folding.clustering.kmeans import cluster_kmeans
        top = cluster_kmeans(vecs, k=top_k, random_state=random_state)
        top_partition = top

    top_labels = list(top_partition.labels)

    top_groups: dict[int, list[int]] = defaultdict(list)
    for i, lab in enumerate(top_labels):
        top_groups[int(lab)].append(i)

    # -----------------------------------------------------------------------
    # Build the recursive tree
    # 1. Outliers first
    # -----------------------------------------------------------------------
    out_idxs = top_groups.pop(-1, [])
    root_folders: list[FolderNode] = []

    if out_idxs:
        root_folders.append(FolderNode(
            name=outliers_folder,
            display_name="Outros",
            files=sorted([rels[i] for i in out_idxs], key=str.casefold),
            subfolders=[],
        ))

    used_top_names: set[str] = {outliers_folder} if out_idxs else set()

    # -----------------------------------------------------------------------
    # 2. Non-outlier clusters
    # -----------------------------------------------------------------------
    for lab in sorted(top_groups.keys()):
        idxs = top_groups[lab]

        # Build subfolders first (recurse), then name the node via the shared
        # finalizer (supports bottom-up; ADR 0037). Subfolder construction —
        # the tree-cut vs kmeans branching — is unchanged, so the structure is
        # identical to per-node; only the name source/order differs.
        subfolders: list[FolderNode] = []
        if int(max_levels) >= 2 and len(idxs) >= max(2, min_cluster_size * 2):
            if top_partition.linkage is not None:
                # ---- Tree-cut path: agglomerative or HDBSCAN ----
                if isinstance(top_partition.linkage, CondensedTreeData):
                    cluster_node = top_partition.linkage.selected_nodes.get(lab)
                    # If the label has no selected node (e.g. noise not captured),
                    # leave subfolders empty (skip tree-cut for this cluster).
                    if cluster_node is not None:
                        subfolders = _build_level_from_tree(
                            idxs, 2, int(max_levels),
                            linkage=top_partition.linkage,
                            cluster_node_id=cluster_node,
                            rels=rels, vecs=vecs, clustering_vecs=clustering_vecs,
                            get_texts=get_texts, namer=namer, naming_cfg=naming_cfg,
                            min_cluster_size=min_cluster_size, embed_text=embed_text,
                            naming_direction=naming_direction,
                        )
                else:
                    # AgglomerativeLinkage: no per-cluster node id needed
                    subfolders = _build_level_from_tree(
                        idxs, 2, int(max_levels),
                        linkage=top_partition.linkage,
                        cluster_node_id=None,
                        rels=rels, vecs=vecs, clustering_vecs=clustering_vecs,
                        get_texts=get_texts, namer=namer, naming_cfg=naming_cfg,
                        min_cluster_size=min_cluster_size, embed_text=embed_text,
                        naming_direction=naming_direction,
                    )
            else:
                # ---- Fallback: kmeans / random re-clustering ----
                subfolders = _build_level(
                    idxs, 2, int(max_levels),
                    rels=rels, vecs=vecs, clustering_vecs=clustering_vecs,
                    get_texts=get_texts, namer=namer, naming_cfg=naming_cfg,
                    algorithm=algorithm, clusterer=clusterer,
                    clustering_cfg=dict(clustering_cfg or {}),
                    min_cluster_size=min_cluster_size, sub_k=sub_k,
                    random_state=random_state, embed_text=embed_text,
                    naming_direction=naming_direction,
                )

        root_folders.append(_finalize_node(
            idxs,
            subfolders,
            rels=rels,
            vecs=vecs,
            get_texts=get_texts,
            namer=namer,
            naming_cfg=naming_cfg,
            naming_direction=naming_direction,
            embed_text=embed_text,
            used_names=used_top_names,
        ))

    return StructureProposal(
        root=root,
        folders=root_folders,
        orphans=[],
        notes=[],
    )
