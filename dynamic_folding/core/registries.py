from __future__ import annotations

from pathlib import Path
from typing import Protocol

from dynamic_folding.clustering.agglomerative_tree import cluster_agglomerative_tree
from dynamic_folding.clustering.hdbscan import cluster_hdbscan
from dynamic_folding.clustering.kmeans import cluster_kmeans
from dynamic_folding.clustering.random_baseline import cluster_random
from dynamic_folding.clustering.result import ClusterPartition
from dynamic_folding.contracts.embedding import EmbeddingRecord
from dynamic_folding.contracts.extracted import ExtractedDoc
from dynamic_folding.contracts.file_ref import FileRef
from dynamic_folding.contracts.preprocessed import PreprocessedDoc
from dynamic_folding.contracts.proposal import StructureProposal
from dynamic_folding.core.registry import Registry
from dynamic_folding.embedding.engine import embed_with_cache
from dynamic_folding.embedding.fake import FakeEmbedder
from dynamic_folding.embedding.sbert import embed_sbert_with_cache
from dynamic_folding.extractor.basic import extract as extract_basic
from dynamic_folding.extractor.type_aware import extract as extract_type_aware
from dynamic_folding.naming.ollama import name_cluster_ollama
from dynamic_folding.naming.tfidf import aggregate_name, name_cluster
from dynamic_folding.preprocess.basic import preprocess as preprocess_basic
from dynamic_folding.proposal.proposer import propose_structure
from dynamic_folding.scanner.fs_scanner import scan as scan_fs


from dynamic_folding.reducer.identity import reduce_identity
from dynamic_folding.reducer.pca import reduce_pca
from dynamic_folding.reducer.umap import reduce_umap


# Explicit Type Protocols for Pipeline Stages
class Scanner(Protocol):
    def __call__(self, root: Path, cfg: dict) -> list[FileRef]: ...


class Extractor(Protocol):
    def __call__(self, fr: FileRef, cfg: dict) -> ExtractedDoc: ...


class Preprocessor(Protocol):
    def __call__(self, doc: ExtractedDoc, cfg: dict) -> PreprocessedDoc: ...


class Embedder(Protocol):
    def __call__(self, docs: list[PreprocessedDoc], cfg: dict) -> list[EmbeddingRecord]: ...


class Reducer(Protocol):
    def __call__(self, vectors: list[list[float]], cfg: dict) -> list[list[float]]: ...


class Clusterer(Protocol):
    def __call__(self, vectors: list[list[float]], cfg: dict) -> ClusterPartition: ...


class Namer(Protocol):
    def __call__(self, texts: list[str], cfg: dict) -> str: ...


class Proposer(Protocol):
    def __call__(
        self,
        root: str,
        preprocessed: list[PreprocessedDoc],
        embeddings: list[EmbeddingRecord],
        cfg: dict,
    ) -> StructureProposal: ...


SCANNERS: Registry[Scanner] = Registry("scanner")
EXTRACTORS: Registry[Extractor] = Registry("extractor")
PREPROCESSORS: Registry[Preprocessor] = Registry("preprocess")
EMBEDDERS: Registry[Embedder] = Registry("embedding")
REDUCERS: Registry[Reducer] = Registry("reducer")
CLUSTERERS: Registry[Clusterer] = Registry("clustering")
NAMERS: Registry[Namer] = Registry("naming")
PROPOSERS: Registry[Proposer] = Registry("proposal")


def _register_defaults() -> None:
    if SCANNERS.keys():
        return  # already registered

    SCANNERS.register(
        "fs",
        lambda _cfg: (lambda root, cfg: scan_fs(
            root,
            max_depth=int(cfg.get("max_depth", 2)),
            max_files=int(cfg.get("max_files", 200)),
            ignore_hidden=bool(cfg.get("ignore_hidden", True)),
            ignore_globs=list(cfg.get("ignore_globs", [])),
        )),
    )

    EXTRACTORS.register("basic", lambda _cfg: (lambda fr, cfg: extract_basic(fr)))
    EXTRACTORS.register("type_aware", lambda _cfg: (lambda fr, cfg: extract_type_aware(fr, cfg)))

    PREPROCESSORS.register(
        "basic",
        lambda _cfg: (
            lambda doc, cfg: preprocess_basic(doc, template=str(cfg.get("template", "{stem} ext:{ext} path:{rel_path}")))
        ),
    )

    EMBEDDERS.register(
        "fake",
        lambda _cfg: (
            lambda docs, cfg: embed_with_cache(
                docs,
                cache_db=Path(cfg["cache_db"]),
                embedder=FakeEmbedder(dim=int(cfg.get("fake_dim", 16))),
                progress=cfg.get("progress"),
            )
        ),
    )

    EMBEDDERS.register(
        "sbert",
        lambda _cfg: (
            lambda docs, cfg: embed_sbert_with_cache(
                docs,
                cache_db=Path(cfg["cache_db"]),
                model_path=Path(str(cfg["model_path"])),
                device=str(cfg.get("device", "cpu")),
                batch_size=int(cfg.get("batch_size", 32)),
                normalize=bool(cfg.get("normalize", True)),
                progress=cfg.get("progress"),
            )
        ),
    )

    REDUCERS.register("identity", lambda _cfg: (lambda vectors, cfg: reduce_identity(vectors, cfg)))
    REDUCERS.register("pca", lambda _cfg: (lambda vectors, cfg: reduce_pca(vectors, cfg)))
    REDUCERS.register("umap", lambda _cfg: (lambda vectors, cfg: reduce_umap(vectors, cfg)))

    CLUSTERERS.register(
        "kmeans",
        lambda _cfg: (
            lambda vectors, cfg: cluster_kmeans(
                vectors,
                k=int(cfg.get("k", 3)),
                random_state=int(cfg.get("random_state", 0)),
            )
        ),
    )

    CLUSTERERS.register(
        "agglomerative_tree",
        lambda _cfg: (
            lambda vectors, cfg: cluster_agglomerative_tree(
                vectors,
                min_cluster_size=int(cfg.get("min_cluster_size", 4)),
                linkage=str(cfg.get("linkage", "ward")),
            )
        ),
    )

    CLUSTERERS.register(
        "random",
        lambda _cfg: (
            lambda vectors, cfg: cluster_random(
                vectors,
                k=int(cfg.get("k", 3)),
                random_state=int(cfg.get("random_state", 42)),
            )
        ),
    )

    CLUSTERERS.register(
        "hdbscan",
        lambda _cfg: (
            lambda vectors, cfg: cluster_hdbscan(
                vectors,
                # Mirror the system default (config.py) and the agglomerative
                # fallback so the same knob can't disagree across stages. The
                # proposer/config always inject this in practice; 4 is the
                # consistent safety net. See ADR 0036 (config audit).
                min_cluster_size=int(cfg.get("min_cluster_size", 4)),
                min_samples=cfg.get("min_samples"),
                cluster_selection_epsilon=float(cfg.get("cluster_selection_epsilon", 0.0)),
            )
        ),
    )

    NAMERS.register(
        "tfidf",
        lambda _cfg: (
            lambda texts, cfg: (
                aggregate_name(
                    texts, cfg.get("loose_texts", []) or [], top_terms=int(cfg.get("top_terms", 2))
                )
                if cfg.get("aggregate")
                else name_cluster(texts, top_terms=int(cfg.get("top_terms", 2)))
            )
        ),
    )
    NAMERS.register("ollama", lambda _cfg: (lambda texts, cfg: name_cluster_ollama(texts, cfg)))

    PROPOSERS.register(
        "two_level",
        lambda _cfg: (
            lambda root, pre, emb, cfg: propose_structure(
                root=root,
                preprocessed=pre,
                embeddings=emb,
                top_k=int(cfg.get("top_k", 3)),
                sub_k=int(cfg.get("sub_k", 2)),
                random_state=int(cfg.get("random_state", 0)),
                namer=cfg["namer"],
                naming_cfg=dict(cfg.get("naming_cfg", {})),
                algorithm=str(cfg.get("algorithm", "kmeans")),
                clusterer=cfg.get("clusterer"),
                clustering_cfg=dict(cfg.get("clustering_cfg", {})),
                min_cluster_size=int(cfg.get("min_cluster_size", 4)),
                max_levels=int(cfg.get("max_levels", 2)),
                outliers_folder=str(cfg.get("outliers_folder", "Outros")),
                reduced_vectors=cfg.get("reduced_vectors"),
                embed_text=cfg.get("embed_text"),
                fetch_texts=cfg.get("fetch_texts"),
                naming_direction=str(cfg.get("naming_direction", "per_node")),
            )
        ),
    )


_register_defaults()
