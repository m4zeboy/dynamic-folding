"""Bottom-up hierarchical naming — boundary guards B1–B4 (ADR 0037).

Bottom-up names leaf clusters from their documents, then synthesizes each parent
from its children's names (+ loose-file terms). It is a *naming* change only:
clustering, file membership, and nesting must be byte-identical to per-node.

All tests are deterministic (FakeEmbedder-style hand-built vectors + the tfidf
aggregator); the Ollama path is validated manually with SBERT+Ollama.
"""
from __future__ import annotations

from dynamic_folding.contracts.embedding import EmbeddingRecord
from dynamic_folding.contracts.file_ref import FileRef
from dynamic_folding.contracts.preprocessed import PreprocessedDoc
from dynamic_folding.naming.tfidf import aggregate_name, name_cluster
from dynamic_folding.proposal.proposer import propose_structure

_FALLBACK = {"Group", "unnamed_group", "_Ambíguo", "_Ambiguo"}


def _tfidf_namer(texts, cfg):
    """Inline tfidf namer mirroring the registry wiring (per-node + aggregate)."""
    top_terms = int(cfg.get("top_terms", 2))
    if cfg.get("aggregate"):
        return aggregate_name(texts, cfg.get("loose_texts", []) or [], top_terms=top_terms)
    return name_cluster(texts, top_terms=top_terms)


def _fr(rel: str) -> FileRef:
    return FileRef(path=rel, rel_path=rel, is_dir=False, depth=0, name=rel,
                   ext="txt", size=1, ctime=None, mtime=None)


def _two_level_scenario():
    """8 docs → 2 top clusters (x vs y axis), each split into 2 leaf subfolders
    (z axis). Deterministic vectors so kmeans yields a stable 2-level tree."""
    specs = [
        ("a1_0", [10.0, 0.0, 5.0], "relatorio financeiro anual receita"),
        ("a1_1", [10.0, 0.0, 5.1], "relatorio financeiro trimestral receita"),
        ("a2_0", [10.0, 0.0, -5.0], "contrato prestacao servico clausula"),
        ("a2_1", [10.0, 0.0, -5.1], "contrato prestacao servico assinatura"),
        ("b1_0", [0.0, 10.0, 5.0], "fotografia paisagem natureza montanha"),
        ("b1_1", [0.0, 10.0, 5.1], "fotografia paisagem natureza floresta"),
        ("b2_0", [0.0, 10.0, -5.0], "musica audio gravacao estudio"),
        ("b2_1", [0.0, 10.0, -5.1], "musica audio gravacao mixagem"),
    ]
    pre, emb = [], []
    for rel, vec, text in specs:
        fr = _fr(rel + ".txt")
        pre.append(PreprocessedDoc(file=fr, text_for_embedding=text, features={}))
        emb.append(EmbeddingRecord(file=fr, vector=vec, model_id="t", content_hash=rel))
    return pre, emb


def _propose(direction: str):
    pre, emb = _two_level_scenario()
    return propose_structure(
        root="r", preprocessed=pre, embeddings=emb,
        top_k=2, sub_k=2, random_state=0,
        namer=_tfidf_namer, naming_cfg={"top_terms": 2},
        algorithm="kmeans", clusterer=None, clustering_cfg={},
        min_cluster_size=2, max_levels=2,
        reduced_vectors=None, embed_text=None, fetch_texts=None,
        naming_direction=direction,
    )


def _shape(folders):
    """Structure (files + nesting) with names stripped — the B1 comparison key."""
    return [(tuple(f.files), _shape(f.subfolders)) for f in folders]


def _names(folders):
    return [(f.name, _names(f.subfolders)) for f in folders]


# --------------------------------------------------------------------------- #
# B1 — structure-invariance (the primary regression guard)
# --------------------------------------------------------------------------- #
def test_b1_structure_identical_per_node_vs_bottom_up():
    per_node = _propose("per_node")
    bottom_up = _propose("bottom_up")
    # Same folder/file membership and nesting — naming must not perturb clustering.
    assert _shape(per_node.folders) == _shape(bottom_up.folders)
    # And the scenario actually produced a 2-level tree (else the guard is vacuous).
    assert any(f.subfolders for f in bottom_up.folders), "expected subfolders to exist"


def test_b1_only_names_differ():
    per_node = _propose("per_node")
    bottom_up = _propose("bottom_up")
    # At least one internal-node name should change (proves bottom-up did something).
    assert _names(per_node.folders) != _names(bottom_up.folders)


def _tree_cut_scenario():
    """12 docs that subdivide via the LINKAGE-TREE-CUT path (_build_level_from_tree)
    — the path production uses with hdbscan/agglomerative, distinct from the kmeans
    path above. Group A ({x≈0} ∪ {x≈5}) splits into 2 leaf subfolders; group B
    ({x≈100}) is a leaf. Mirrors tests/test_tree_cut_hierarchy.py's scenario."""
    specs = []
    for i in range(4):
        specs.append((f"a1_{i}.txt", [0.0, i * 0.01], "alpha relatorio financeiro receita"))
    for i in range(4):
        specs.append((f"a2_{i}.txt", [5.0, i * 0.01], "beta contrato servico clausula"))
    for i in range(4):
        specs.append((f"b_{i}.txt", [100.0, float(i)], "gamma fotografia paisagem natureza"))
    pre, emb = [], []
    for rel, vec, text in specs:
        fr = _fr(rel)
        pre.append(PreprocessedDoc(file=fr, text_for_embedding=text, features={}))
        emb.append(EmbeddingRecord(file=fr, vector=vec, model_id="t", content_hash=rel))
    return pre, emb


def _propose_tree_cut(direction: str):
    from dynamic_folding.clustering.agglomerative_tree import cluster_agglomerative_tree

    pre, emb = _tree_cut_scenario()
    return propose_structure(
        root="r", preprocessed=pre, embeddings=emb,
        top_k=2, sub_k=2, random_state=0,
        namer=_tfidf_namer, naming_cfg={"top_terms": 2},
        algorithm="agglomerative_tree",
        clusterer=lambda vectors, cfg: cluster_agglomerative_tree(
            vectors, min_cluster_size=2, linkage="ward"
        ),
        clustering_cfg={"min_cluster_size": 2},
        min_cluster_size=2, max_levels=2,
        reduced_vectors=None, embed_text=None, fetch_texts=None,
        naming_direction=direction,
    )


def test_b1_structure_identical_tree_cut_path():
    """B1 on the PRODUCTION naming path. The default stack is hdbscan, which (like
    agglomerative_tree) routes through _build_level_from_tree — a different function
    than the kmeans path covered above. Without this, the primary guardrail would
    stand in for production the way dotted-ext fixtures stood in for the scanner."""
    per_node = _propose_tree_cut("per_node")
    bottom_up = _propose_tree_cut("bottom_up")
    assert _shape(per_node.folders) == _shape(bottom_up.folders)
    assert any(f.subfolders for f in bottom_up.folders), "expected tree-cut subfolders"
    # And bottom-up actually relabeled an internal node on this path too.
    assert _names(per_node.folders) != _names(bottom_up.folders)


# --------------------------------------------------------------------------- #
# B2 — no garbage parents; parent names derive from children
# --------------------------------------------------------------------------- #
def test_b2_parents_never_fallback_named():
    bottom_up = _propose("bottom_up")
    parents = [f for f in bottom_up.folders if f.subfolders]
    assert parents, "expected at least one parent node"
    for p in parents:
        assert p.name not in _FALLBACK, f"parent got a fallback label: {p.name!r}"


def test_b2_aggregate_name_is_child_derived_and_non_fallback():
    name = aggregate_name(
        ["Historico Escolar Arquitetura", "Declaracoes Certificados"], [], top_terms=3
    )
    assert name not in _FALLBACK
    low = name.lower()
    assert any(
        tok in low
        for tok in ["historico", "escolar", "arquitetura", "declaracoes", "certificados"]
    )


def test_b2_all_fallback_children_degrade_to_document_naming():
    # When every child is a fallback label, the parent must not inherit garbage:
    # aggregate_name over an empty child set falls back to loose terms / unnamed.
    assert aggregate_name([], ["relatorio financeiro anual"], top_terms=2) not in {"Group"}
    assert aggregate_name([], [], top_terms=2) == "unnamed_group"


# --------------------------------------------------------------------------- #
# B3 — determinism (tfidf mode)
# --------------------------------------------------------------------------- #
def test_b3_bottom_up_is_deterministic():
    first = _names(_propose("bottom_up").folders)
    second = _names(_propose("bottom_up").folders)
    assert first == second


# --------------------------------------------------------------------------- #
# B4 — offline + fallback: Ollama aggregation failure → deterministic tfidf
# --------------------------------------------------------------------------- #
def test_b4_ollama_aggregate_falls_back_offline():
    from dynamic_folding.naming.ollama import name_cluster_ollama

    children = ["Relatorios Financeiros", "Contratos Servicos"]
    # Non-loopback base_url → the namer refuses to call out and returns the
    # deterministic aggregate fallback. No network is touched.
    cfg = {
        "aggregate": True,
        "loose_texts": [],
        "model": "llama3.1",
        "base_url": "http://10.0.0.1:11434",
        "top_terms": 2,
    }
    result = name_cluster_ollama(children, cfg)
    assert result == aggregate_name(children, [], top_terms=2)
    assert result not in _FALLBACK
