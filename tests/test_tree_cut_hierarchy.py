"""Tests for linkage-tree hierarchy extraction (ADR 0027).

Covers:
  - ClusterPartition returned by all four clusterers
  - AgglomerativeLinkage populated by agglomerative_tree
  - CondensedTreeData populated by hdbscan
  - _cut_agglomerative_subtree correctness and edge cases
  - _hdbscan_eom_subtree correctness and edge cases
  - propose_structure uses tree-cut path (no second clusterer call) for
    agglomerative_tree and hdbscan
"""
from __future__ import annotations

import math
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from dynamic_folding.clustering.result import (
    AgglomerativeLinkage,
    ClusterPartition,
    CondensedTreeData,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _touch(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"x")


def _two_cluster_vectors() -> list[list[float]]:
    """6 points: 3 near (0,0) and 3 near (10,10)."""
    return [
        [0.0, 0.0], [0.1, 0.0], [0.0, 0.1],
        [10.0, 10.0], [10.1, 10.0], [10.0, 10.1],
    ]


def _three_cluster_vectors() -> list[list[float]]:
    """9 points: 3 tight groups well-separated."""
    return [
        [0.0, 0.0], [0.1, 0.0], [0.0, 0.1],        # cluster A
        [10.0, 10.0], [10.1, 10.0], [10.0, 10.1],   # cluster B
        [100.0, 0.0], [100.1, 0.0], [100.0, 0.1],   # cluster C
    ]


# ---------------------------------------------------------------------------
# 1. All clusterers return ClusterPartition
# ---------------------------------------------------------------------------

class TestClusterPartitionReturnType:
    def test_kmeans_returns_cluster_partition(self):
        from dynamic_folding.clustering.kmeans import cluster_kmeans
        result = cluster_kmeans(_two_cluster_vectors(), k=2, random_state=0)
        assert isinstance(result, ClusterPartition)
        assert len(result.labels) == 6
        assert result.linkage is None

    def test_random_returns_cluster_partition(self):
        from dynamic_folding.clustering.random_baseline import cluster_random
        result = cluster_random(_two_cluster_vectors(), k=2, random_state=0)
        assert isinstance(result, ClusterPartition)
        assert len(result.labels) == 6
        assert result.linkage is None

    def test_agglomerative_returns_cluster_partition_with_linkage(self):
        from dynamic_folding.clustering.agglomerative_tree import cluster_agglomerative_tree
        result = cluster_agglomerative_tree(_two_cluster_vectors(), min_cluster_size=1)
        assert isinstance(result, ClusterPartition)
        assert len(result.labels) == 6
        assert isinstance(result.linkage, AgglomerativeLinkage)

    def test_hdbscan_returns_cluster_partition_with_condensed_tree(self):
        from dynamic_folding.clustering.hdbscan import cluster_hdbscan
        result = cluster_hdbscan(_two_cluster_vectors(), min_cluster_size=2)
        assert isinstance(result, ClusterPartition)
        assert len(result.labels) == 6
        assert isinstance(result.linkage, CondensedTreeData)

    def test_all_clusterers_via_registry(self):
        from dynamic_folding.core.registries import CLUSTERERS
        vecs = _two_cluster_vectors()
        for name in ("kmeans", "agglomerative_tree", "random", "hdbscan"):
            cl = CLUSTERERS.create(name, {})
            result = cl(vecs, {"k": 2, "min_cluster_size": 2})
            assert isinstance(result, ClusterPartition), f"{name} did not return ClusterPartition"
            assert len(result.labels) == len(vecs)


# ---------------------------------------------------------------------------
# 2. AgglomerativeLinkage structure
# ---------------------------------------------------------------------------

class TestAgglomerativeLinkage:
    def test_linkage_children_count(self):
        """n leaves → n-1 merges."""
        from dynamic_folding.clustering.agglomerative_tree import cluster_agglomerative_tree
        vecs = _two_cluster_vectors()
        result = cluster_agglomerative_tree(vecs, min_cluster_size=1)
        ag = result.linkage
        assert isinstance(ag, AgglomerativeLinkage)
        assert len(ag.children) == len(vecs) - 1
        assert len(ag.distances) == len(vecs) - 1
        assert ag.n_leaves == len(vecs)

    def test_distances_non_negative(self):
        from dynamic_folding.clustering.agglomerative_tree import cluster_agglomerative_tree
        result = cluster_agglomerative_tree(_two_cluster_vectors(), min_cluster_size=1)
        assert all(d >= 0.0 for d in result.linkage.distances)

    def test_distances_non_decreasing(self):
        """Agglomerative merges happen at non-decreasing distances."""
        from dynamic_folding.clustering.agglomerative_tree import cluster_agglomerative_tree
        result = cluster_agglomerative_tree(_three_cluster_vectors(), min_cluster_size=1)
        d = result.linkage.distances
        assert all(d[i] <= d[i + 1] + 1e-9 for i in range(len(d) - 1))


# ---------------------------------------------------------------------------
# 3. CondensedTreeData structure
# ---------------------------------------------------------------------------

class TestCondensedTreeData:
    def test_condensed_tree_fields(self):
        from dynamic_folding.clustering.hdbscan import cluster_hdbscan
        result = cluster_hdbscan(_two_cluster_vectors(), min_cluster_size=2)
        ct = result.linkage
        assert isinstance(ct, CondensedTreeData)
        assert ct.n_leaves == 6
        assert len(ct.parents) == len(ct.children) == len(ct.lambda_vals) == len(ct.child_sizes)
        assert len(ct.parents) > 0

    def test_selected_nodes_maps_cluster_labels(self):
        from dynamic_folding.clustering.hdbscan import cluster_hdbscan
        result = cluster_hdbscan(_two_cluster_vectors(), min_cluster_size=2)
        ct = result.linkage
        non_noise_labels = {lab for lab in result.labels if lab >= 0}
        # Every non-noise cluster label must have an entry in selected_nodes.
        for lab in non_noise_labels:
            assert lab in ct.selected_nodes, f"label {lab} missing from selected_nodes"
        # Selected node ids must be internal nodes (>= n_leaves).
        for node_id in ct.selected_nodes.values():
            assert node_id >= ct.n_leaves


# ---------------------------------------------------------------------------
# 4. _cut_agglomerative_subtree
# ---------------------------------------------------------------------------

class TestCutAgglomerativeSubtree:
    """Direct unit tests for the sub-tree cut function."""

    def _build_linkage_for(self, vecs: list[list[float]]) -> AgglomerativeLinkage:
        from dynamic_folding.clustering.agglomerative_tree import cluster_agglomerative_tree
        result = cluster_agglomerative_tree(vecs, min_cluster_size=1)
        return result.linkage

    def test_two_obvious_clusters(self):
        from dynamic_folding.proposal.proposer import _cut_agglomerative_subtree
        vecs = _two_cluster_vectors()
        ag = self._build_linkage_for(vecs)
        all_idxs = list(range(len(vecs)))
        labels = _cut_agglomerative_subtree(all_idxs, ag, min_cluster_size=2)
        assert len(labels) == len(vecs)
        # Verify the two groups are separated.
        group_a = {labels[i] for i in range(3)}
        group_b = {labels[i] for i in range(3, 6)}
        assert len(group_a) == 1 and len(group_b) == 1
        assert group_a != group_b
        # No outliers.
        assert -1 not in labels

    def test_single_point_with_min_1_returns_cluster(self):
        from dynamic_folding.proposal.proposer import _cut_agglomerative_subtree
        # Need a linkage built from multiple points; we just query a single leaf.
        vecs = _two_cluster_vectors()
        ag = self._build_linkage_for(vecs)
        labels = _cut_agglomerative_subtree([0], ag, min_cluster_size=1)
        assert labels == [0]

    def test_single_point_with_min_2_returns_outlier(self):
        from dynamic_folding.proposal.proposer import _cut_agglomerative_subtree
        vecs = _two_cluster_vectors()
        ag = self._build_linkage_for(vecs)
        labels = _cut_agglomerative_subtree([0], ag, min_cluster_size=2)
        assert labels == [-1]

    def test_min_cluster_size_marks_small_groups_as_outliers(self):
        from dynamic_folding.proposal.proposer import _cut_agglomerative_subtree
        # 3 points near origin → sub-tree, but min_cluster_size=4 means they can't form a cluster
        vecs = [[0.0, 0.0], [0.1, 0.0], [0.0, 0.1], [10.0, 10.0], [10.1, 10.0], [10.0, 10.1]]
        ag = self._build_linkage_for(vecs)
        # Query only the 3-point group with min_cluster_size=4.
        labels = _cut_agglomerative_subtree([0, 1, 2], ag, min_cluster_size=4)
        assert all(lab == -1 for lab in labels)

    def test_deterministic_repeated_calls(self):
        from dynamic_folding.proposal.proposer import _cut_agglomerative_subtree
        vecs = _three_cluster_vectors()
        ag = self._build_linkage_for(vecs)
        all_idxs = list(range(9))
        labels_1 = _cut_agglomerative_subtree(all_idxs, ag, min_cluster_size=2)
        labels_2 = _cut_agglomerative_subtree(all_idxs, ag, min_cluster_size=2)
        assert labels_1 == labels_2

    def test_subset_of_global_indices(self):
        """Cut should work on any subset of the original leaf indices."""
        from dynamic_folding.proposal.proposer import _cut_agglomerative_subtree
        vecs = _three_cluster_vectors()  # 9 points, 3 groups
        ag = self._build_linkage_for(vecs)
        # Query only group A (0,1,2) and group B (3,4,5)
        subset = [0, 1, 2, 3, 4, 5]
        labels = _cut_agglomerative_subtree(subset, ag, min_cluster_size=2)
        assert len(labels) == 6
        # A and B must be in different clusters.
        la = {labels[i] for i in range(3)} - {-1}
        lb = {labels[i] for i in range(3, 6)} - {-1}
        if la and lb:
            assert la.isdisjoint(lb)


# ---------------------------------------------------------------------------
# 5. _hdbscan_eom_subtree
# ---------------------------------------------------------------------------

class TestHDBSCANEOMSubtree:
    def _run_hdbscan(self, vecs, min_cluster_size=2):
        from dynamic_folding.clustering.hdbscan import cluster_hdbscan
        return cluster_hdbscan(vecs, min_cluster_size=min_cluster_size)

    def test_eom_subtree_returns_list(self):
        from dynamic_folding.proposal.proposer import _hdbscan_eom_subtree
        result = self._run_hdbscan(_two_cluster_vectors())
        ct = result.linkage
        non_noise = {lab for lab in result.labels if lab >= 0}
        if not non_noise:
            pytest.skip("no non-noise clusters found")
        first_label = min(non_noise)
        node_id = ct.selected_nodes[first_label]
        sub = _hdbscan_eom_subtree(node_id, ct, min_cluster_size=2)
        # Must be a list of (int, int, list[int]) tuples or empty.
        assert isinstance(sub, list)
        for item in sub:
            local_lab, nid, leaves = item
            assert isinstance(local_lab, int)
            assert isinstance(nid, int)
            assert isinstance(leaves, list)

    def test_eom_subtree_leaves_are_subsets(self):
        """All leaves returned by EOM subtree must be leaves of the given cluster."""
        from dynamic_folding.clustering.hdbscan import _get_leaves, _build_children_of
        from dynamic_folding.proposal.proposer import _hdbscan_eom_subtree
        vecs = _three_cluster_vectors()
        result = self._run_hdbscan(vecs, min_cluster_size=2)
        ct = result.linkage
        children_of = _build_children_of(ct.parents, ct.children)
        non_noise = {lab for lab in result.labels if lab >= 0}
        for lab in non_noise:
            node_id = ct.selected_nodes[lab]
            cluster_leaves = set(_get_leaves(node_id, children_of, ct.n_leaves))
            sub = _hdbscan_eom_subtree(node_id, ct, min_cluster_size=2)
            for _, _, leaves in sub:
                for lf in leaves:
                    assert lf in cluster_leaves, f"leaf {lf} outside cluster {lab} leaves {cluster_leaves}"

    def test_eom_subtree_root_not_selected(self):
        """Root node must never appear as a selected sub-cluster."""
        from dynamic_folding.proposal.proposer import _hdbscan_eom_subtree
        vecs = _three_cluster_vectors()
        result = self._run_hdbscan(vecs, min_cluster_size=2)
        ct = result.linkage
        non_noise = {lab for lab in result.labels if lab >= 0}
        for lab in non_noise:
            node_id = ct.selected_nodes[lab]
            sub = _hdbscan_eom_subtree(node_id, ct, min_cluster_size=2)
            selected_node_ids = [nid for _, nid, _ in sub]
            assert node_id not in selected_node_ids, "root node must not be in sub-cluster results"

    def test_eom_subtree_min_cluster_size_respected(self):
        """Sub-clusters smaller than min_cluster_size must not be returned."""
        from dynamic_folding.proposal.proposer import _hdbscan_eom_subtree
        vecs = _three_cluster_vectors()
        result = self._run_hdbscan(vecs, min_cluster_size=2)
        ct = result.linkage
        non_noise = {lab for lab in result.labels if lab >= 0}
        for lab in non_noise:
            node_id = ct.selected_nodes[lab]
            sub = _hdbscan_eom_subtree(node_id, ct, min_cluster_size=5)
            for _, _, leaves in sub:
                assert len(leaves) >= 5, "sub-cluster smaller than min_cluster_size returned"


# ---------------------------------------------------------------------------
# 6. propose_structure uses tree-cut path (no second clusterer call)
# ---------------------------------------------------------------------------

class TestProposeStructureTreeCutDispatch:
    """Verify the proposer never calls the clusterer a second time when
    agglomerative_tree or hdbscan is the algorithm (tree-cut path).
    """

    def _build_items(self, n: int = 12):
        """12 items in 2 tight groups."""
        rels = [f"f_{i}.txt" for i in range(n)]
        vecs = [[0.0, float(i)] if i < n // 2 else [10.0, float(i)] for i in range(n)]
        return rels, vecs

    def test_agglomerative_tree_no_second_call(self):
        from dynamic_folding.clustering.agglomerative_tree import cluster_agglomerative_tree
        from dynamic_folding.proposal.proposer import propose_structure
        from dynamic_folding.contracts.embedding import EmbeddingRecord
        from dynamic_folding.contracts.file_ref import FileRef

        rels, vecs = self._build_items()
        call_count = [0]

        def counting_clusterer(vectors, cfg):
            call_count[0] += 1
            return cluster_agglomerative_tree(vectors, min_cluster_size=2)

        embeddings = [
            EmbeddingRecord(
                file=FileRef(path=r, rel_path=r, is_dir=False, depth=0,
                             name=r, ext="txt", size=1, ctime=None, mtime=None),
                vector=v, model_id="t", content_hash="x",
            )
            for r, v in zip(rels, vecs)
        ]

        propose_structure(
            root="/tmp",
            preprocessed=[],
            embeddings=embeddings,
            top_k=2, sub_k=2, random_state=0,
            namer=lambda texts, _: "folder",
            naming_cfg={},
            algorithm="agglomerative_tree",
            clusterer=counting_clusterer,
            clustering_cfg={"min_cluster_size": 2},
            min_cluster_size=2,
            max_levels=2,
        )
        # Only ONE call at the top level; no second call during sub-level extraction.
        assert call_count[0] == 1, (
            f"clusterer called {call_count[0]} times; expected exactly 1 (tree-cut path)"
        )

    def test_agglomerative_tree_produces_subfolders(self, tmp_path: Path):
        """Agglomerative tree reaches depth 2 without re-clustering."""
        from dynamic_folding.contracts.embedding import EmbeddingRecord
        from dynamic_folding.contracts.file_ref import FileRef
        from dynamic_folding.core import registries
        from dynamic_folding.core.pipeline import run_pipeline

        # 12 files in 2 distinct groups; group A has 2 sub-groups inside.
        rels_a1 = [f"a1_{i}.txt" for i in range(4)]  # [0, 0.x]
        rels_a2 = [f"a2_{i}.txt" for i in range(4)]  # [1, 0.x]
        rels_b = [f"b_{i}.txt" for i in range(4)]    # [100, 0.x]

        for r in rels_a1 + rels_a2 + rels_b:
            _touch(tmp_path / r)

        vectors = {}
        for i, r in enumerate(rels_a1):
            vectors[r] = [0.0, float(i) * 0.01]
        for i, r in enumerate(rels_a2):
            vectors[r] = [5.0, float(i) * 0.01]
        for i, r in enumerate(rels_b):
            vectors[r] = [100.0, float(i)]

        def _embed(docs, _cfg):
            return [
                EmbeddingRecord(
                    file=d.file,
                    vector=vectors.get(d.file.rel_path, [0.0, 0.0]),
                    model_id="h", content_hash="x",
                )
                for d in docs
            ]

        monkeypatch_factories = dict(registries.EMBEDDERS._factories)
        monkeypatch_factories["handcrafted"] = lambda _: _embed
        original = registries.EMBEDDERS._factories
        registries.EMBEDDERS._factories = monkeypatch_factories

        try:
            result = run_pipeline(
                tmp_path,
                overrides={
                    "embedding": {"provider": "handcrafted"},
                    "clustering": {"algorithm": "agglomerative_tree", "min_cluster_size": 2},
                    "proposal": {"max_levels": 2},
                },
            )
        finally:
            registries.EMBEDDERS._factories = original

        p = result.proposal
        assert p.folders, "expected at least one folder"
        max_depth = 0

        def _depth(nodes, d):
            nonlocal max_depth
            max_depth = max(max_depth, d)
            for n in nodes:
                _depth(n.subfolders, d + 1)

        _depth(p.folders, 1)
        assert max_depth >= 2, f"expected depth >= 2, got {max_depth}"


# ---------------------------------------------------------------------------
# 7. HDBSCAN tree-cut path (integration)
# ---------------------------------------------------------------------------

class TestHDBSCANTreeCutIntegration:
    def test_hdbscan_no_second_call(self):
        from dynamic_folding.clustering.hdbscan import cluster_hdbscan
        from dynamic_folding.proposal.proposer import propose_structure
        from dynamic_folding.contracts.embedding import EmbeddingRecord
        from dynamic_folding.contracts.file_ref import FileRef

        n = 18  # 9 per group
        rels = [f"f_{i}.txt" for i in range(n)]
        vecs = [[0.0, float(i)] if i < 9 else [100.0, float(i)] for i in range(n)]
        call_count = [0]

        def counting_clusterer(vectors, cfg):
            call_count[0] += 1
            return cluster_hdbscan(vectors, min_cluster_size=cfg.get("min_cluster_size", 3))

        embeddings = [
            EmbeddingRecord(
                file=FileRef(path=r, rel_path=r, is_dir=False, depth=0,
                             name=r, ext="txt", size=1, ctime=None, mtime=None),
                vector=v, model_id="t", content_hash="x",
            )
            for r, v in zip(rels, vecs)
        ]

        propose_structure(
            root="/tmp",
            preprocessed=[],
            embeddings=embeddings,
            top_k=2, sub_k=2, random_state=0,
            namer=lambda texts, _: "folder",
            naming_cfg={},
            algorithm="hdbscan",
            clusterer=counting_clusterer,
            clustering_cfg={"min_cluster_size": 3},
            min_cluster_size=3,
            max_levels=2,
        )
        assert call_count[0] == 1, (
            f"hdbscan clusterer called {call_count[0]} times; expected 1"
        )


# ---------------------------------------------------------------------------
# 8. Regression tests for Bug 1 and Bug 2 (ADR 0027)
# ---------------------------------------------------------------------------

class TestRegressionBugs:
    """Regression suite for two correctness bugs fixed during Sprint 27 implementation.

    Bug 1 (sibling deselection): when node C1 beats its children in the EOM pass,
    the old code deselected ALL other subtree nodes, including sibling subtrees.
    The fix: only deselect desc_of[C1] (actual internal descendants).

    Bug 2 (noise leaf double-placement): _get_leaves(sub_node) returns every leaf
    under sub_node in the condensed tree, including noise leaves (labels_==-1)
    already routed to the outliers folder.  The fix: filter leaves to set(idxs)
    in _build_level_from_tree before adding to sub_info.
    """

    def test_bug1_sibling_subtrees_both_selected(self):
        """Bug 1 regression: selecting C1 must NOT deselect its sibling C2.

        Tree (n_leaves=8; internal ids 8..12):

            R(12)
            ├─ C1(10): stability=4.0, children_sum=4.0 → wins (tie goes to node)
            │   ├─ D1(8):  leaves [0,1], stability=2.0
            │   └─ D2(9):  leaves [2,3], stability=2.0
            └─ C2(11): leaf cluster, leaves [4,5,6,7], stability=8.0 → selected

        Old code: selecting C1 iterated all subtree_nodes and deselected C2.
        Fixed code: only deselects desc_of[C1] = {D1, D2}, leaving C2 intact.
        """
        from dynamic_folding.proposal.proposer import _hdbscan_eom_subtree

        n_leaves = 8  # leaf ids 0–7; internal ids 8–12

        # Row layout: R→C1, R→C2, C1→D1, C1→D2,
        #             D1→leaf0, D1→leaf1, D2→leaf2, D2→leaf3,
        #             C2→leaf4, C2→leaf5, C2→leaf6, C2→leaf7
        parents     = [12, 12, 10, 10, 8,   8,   9,   9,   11,  11,  11,  11 ]
        children    = [10, 11, 8,  9,  0,   1,   2,   3,   4,   5,   6,   7  ]
        lambda_vals = [1.0,1.0,2.0,2.0,3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0]
        child_sizes = [4,  4,  2,  2,  1,   1,   1,   1,   1,   1,   1,   1  ]

        ct = CondensedTreeData(
            parents=parents,
            children=children,
            lambda_vals=lambda_vals,
            child_sizes=child_sizes,
            n_leaves=n_leaves,
            selected_nodes={},
        )

        result = _hdbscan_eom_subtree(root_node_id=12, ct=ct, min_cluster_size=2)
        node_ids = {nid for _, nid, _ in result}

        # Both C1 (id=10) and C2 (id=11) must be selected.
        assert 10 in node_ids, (
            f"C1 (id=10) missing — sibling deselection bug: got node_ids={node_ids}"
        )
        assert 11 in node_ids, (
            f"C2 (id=11) missing — sibling was wrongly deselected: got node_ids={node_ids}"
        )
        # C1's descendants D1 and D2 must be deselected (C1 beat them).
        assert 8 not in node_ids, "D1 (id=8) should be deselected when C1 wins"
        assert 9 not in node_ids, "D2 (id=9) should be deselected when C1 wins"
        # Root must never be selected.
        assert 12 not in node_ids, "root (id=12) must never be in sub-cluster results"

        # Leaf coverage: C1 covers [0,1,2,3], C2 covers [4,5,6,7].
        all_leaves = set()
        for _, _, leaves in result:
            for lf in leaves:
                assert lf not in all_leaves, f"leaf {lf} appears in two sub-clusters"
                all_leaves.add(lf)
        assert all_leaves == set(range(8)), (
            f"unexpected leaf coverage: {all_leaves}"
        )

    def test_bug2_noise_leaves_not_double_placed(self):
        """Bug 2 regression: _build_level_from_tree must not include leaves outside idxs.

        Condensed tree (n_leaves=8; internal ids 8,9,10):

            C(8)  [cluster_node_id passed to _build_level_from_tree]
            ├─ C1(9):  leaves [0, 1, 2]        ← all in idxs
            └─ C2(10): leaves [3, 4, 5, 6]     ← leaves 5,6 are NOT in idxs
                                                   (they were noise at top level)

        idxs = [0, 1, 2, 3, 4]  (leaves 5 and 6 are noise, routed to outliers)

        Before fix: C2's global_idxs included 5 and 6 → their rel_paths appeared
        in a sub-folder even though they were already in the outliers folder.
        After fix:  C2's leaves are filtered to set(idxs) → only [3, 4].
        """
        from dynamic_folding.proposal.proposer import _build_level_from_tree

        n_leaves = 8  # leaf ids 0–7; internal ids 8, 9, 10

        # C(8) → C1(9) and C2(10);  C1 → leaves 0,1,2;  C2 → leaves 3,4,5,6
        parents     = [8,   8,   9,   9,   9,   10,  10,  10,  10 ]
        children    = [9,   10,  0,   1,   2,   3,   4,   5,   6  ]
        lambda_vals = [1.0, 1.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0]
        child_sizes = [3,   4,   1,   1,   1,   1,   1,   1,   1  ]

        ct = CondensedTreeData(
            parents=parents,
            children=children,
            lambda_vals=lambda_vals,
            child_sizes=child_sizes,
            n_leaves=n_leaves,
            selected_nodes={},
        )

        # 7 files total; leaves 5 and 6 correspond to indices 5 and 6 in rels.
        n_total = 7
        rels = [f"f{i}.txt" for i in range(n_total)]
        vecs = [[float(i), 0.0] for i in range(n_total)]
        idxs = [0, 1, 2, 3, 4]  # leaves 5 and 6 are NOT cluster members

        nodes = _build_level_from_tree(
            idxs=idxs,
            current_level=2,
            max_levels=2,   # no recursion
            linkage=ct,
            cluster_node_id=8,
            rels=rels,
            vecs=vecs,
            clustering_vecs=vecs,
            get_texts=lambda indices: [rels[i] for i in indices],
            namer=lambda texts, _: "folder",
            naming_cfg={},
            min_cluster_size=2,
            embed_text=None,
        )

        # Collect every file reference produced by _build_level_from_tree.
        all_files: list[str] = []

        def _collect(node_list):
            for node in node_list:
                all_files.extend(node.files)
                _collect(node.subfolders)

        _collect(nodes)

        # All files must belong to idxs.
        allowed = {rels[i] for i in idxs}
        outside = [f for f in all_files if f not in allowed]
        assert not outside, (
            f"files outside cluster members (noise double-placement bug): {outside}"
        )

        # No file may appear more than once.
        seen: set[str] = set()
        duplicates: list[str] = []
        for f in all_files:
            if f in seen:
                duplicates.append(f)
            seen.add(f)
        assert not duplicates, f"duplicate files in sub-folders: {duplicates}"
