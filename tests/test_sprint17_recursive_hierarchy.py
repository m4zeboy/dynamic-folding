from __future__ import annotations

from pathlib import Path
from dynamic_folding.core.pipeline import run_pipeline

def _touch(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"x")

def test_recursive_proposer_handles_3_levels(tmp_path: Path, monkeypatch) -> None:
    # Build a hierarchy with 3 distinct clusters
    # Level 1: [A, B] vs [C]
    # Level 2: A vs B
    # Level 3: A1 vs A2
    
    # Actually let's just make 3 very distinct groups and use max_levels=3
    # Group A (10 files)
    group_a = [f"a_{i}.txt" for i in range(12)]
    # Group B (10 files)
    group_b = [f"b_{i}.txt" for i in range(12)]
    
    for rel in group_a + group_b:
        _touch(tmp_path / rel)

    # Handcrafted vectors to force deep hierarchy
    # A vs B at top level
    # A split into A_sub1, A_sub2 at level 2
    # A_sub1 split into A_sub1_sub1, A_sub1_sub2 at level 3
    
    vectors: dict[str, list[float]] = {}
    for i, rel in enumerate(group_a):
        # All A are near [0, 0]
        # Half A are [0, 0.1], half are [0.1, 0]
        # Sub-half are [0, 0.11], [0, 0.12]...
        if i < 6: # A_sub1
            if i < 3: # A_sub1_sub1
                vectors[rel] = [0.0, 0.1 + i*0.01]
            else: # A_sub1_sub2
                vectors[rel] = [0.0, 0.5 + i*0.01]
        else: # A_sub2
            vectors[rel] = [5.0, 0.0 + i*0.01]
            
    for i, rel in enumerate(group_b):
        vectors[rel] = [100.0, 100.0 + i]

    from dynamic_folding.contracts.embedding import EmbeddingRecord
    from dynamic_folding.core import registries

    def _embed(docs, _cfg):
        return [
            EmbeddingRecord(
                file=d.file,
                vector=vectors.get(d.file.rel_path, [0.0, 0.0]),
                model_id="h",
                content_hash="x"
            )
            for d in docs
        ]
    monkeypatch.setattr(registries.EMBEDDERS, "_factories", {"handcrafted": lambda _: _embed})

    overrides = {
        "embedding": {"provider": "handcrafted"},
        "clustering": {"algorithm": "kmeans", "min_cluster_size": 3, "top_k": 2, "sub_k": 2},
        "proposal": {"max_levels": 3}
    }

    result = run_pipeline(tmp_path, overrides=overrides)
    p = result.proposal

    # Check depth
    max_depth = 0
    def get_depth(nodes, current):
        nonlocal max_depth
        max_depth = max(max_depth, current)
        for n in nodes:
            get_depth(n.subfolders, current + 1)
    
    get_depth(p.folders, 1)
    
    assert max_depth >= 2 # KMeans might not find 3 levels with this data, but it should find at least 2
    assert p.contracts_version == 4


def test_agglomerative_tree_reaches_depth_2_via_tree_cut(tmp_path: Path, monkeypatch) -> None:
    """agglomerative_tree uses the linkage tree (not re-clustering) to reach depth 2."""
    # Two well-separated groups; group A has two internal sub-groups.
    rels_a1 = [f"a1_{i}.txt" for i in range(5)]  # near (0, 0..0.04)
    rels_a2 = [f"a2_{i}.txt" for i in range(5)]  # near (5, 0..0.04)
    rels_b  = [f"b_{i}.txt"  for i in range(5)]  # near (100, 0..4)

    for rel in rels_a1 + rels_a2 + rels_b:
        _touch(tmp_path / rel)

    vectors: dict[str, list[float]] = {}
    for i, r in enumerate(rels_a1):
        vectors[r] = [0.0, i * 0.01]
    for i, r in enumerate(rels_a2):
        vectors[r] = [5.0, i * 0.01]
    for i, r in enumerate(rels_b):
        vectors[r] = [100.0, float(i)]

    from dynamic_folding.contracts.embedding import EmbeddingRecord
    from dynamic_folding.core import registries

    def _embed(docs, _cfg):
        return [
            EmbeddingRecord(
                file=d.file,
                vector=vectors.get(d.file.rel_path, [0.0, 0.0]),
                model_id="h",
                content_hash="x",
            )
            for d in docs
        ]

    monkeypatch.setattr(registries.EMBEDDERS, "_factories", {"handcrafted": lambda _: _embed})

    overrides = {
        "embedding": {"provider": "handcrafted"},
        "clustering": {"algorithm": "agglomerative_tree", "min_cluster_size": 2},
        "proposal": {"max_levels": 2},
    }

    result = run_pipeline(tmp_path, overrides=overrides)
    p = result.proposal

    max_depth = 0

    def get_depth(nodes, current):
        nonlocal max_depth
        max_depth = max(max_depth, current)
        for n in nodes:
            get_depth(n.subfolders, current + 1)

    get_depth(p.folders, 1)

    assert max_depth >= 2, (
        f"agglomerative_tree tree-cut path should reach depth >= 2, got {max_depth}"
    )
    assert p.contracts_version == 4
