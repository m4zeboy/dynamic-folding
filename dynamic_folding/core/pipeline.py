from __future__ import annotations

import time
from pathlib import Path

from dynamic_folding.contracts.proposal import StructureProposal
from dynamic_folding.contracts.run_result import RunResult
from dynamic_folding.cache.sqlite_cache import EmbeddingCache
from dynamic_folding.core.config import load_config
from dynamic_folding.core.paths import default_cache_db_path
from dynamic_folding.core.registries import (
    CLUSTERERS,
    EMBEDDERS,
    EXTRACTORS,
    NAMERS,
    PREPROCESSORS,
    PROPOSERS,
    REDUCERS,
    SCANNERS,
)
from dynamic_folding.core.validate import validate_proposal
from dynamic_folding.core.validate_config import validate_config
from dynamic_folding.core.progress import NullProgress, Progress


import os

from dynamic_folding.core.config_utils import deep_merge

SBERT_MODEL_PATH_ENV = "DYNAMIC_FOLDING_SBERT_MODEL_PATH"


def _get_peak_memory_mb() -> float | None:
    """Return current process resident memory in MB, or None if unavailable.

    Module-level callable so tests can monkey-patch it.
    """
    try:
        import psutil
    except ImportError:
        return None
    try:
        return psutil.Process().memory_info().rss / (1024 * 1024)
    except Exception:
        return None


def resolve_effective_config(root: Path, *, config_path: Path | None = None, overrides: dict | None = None) -> dict:
    root = root.resolve()
    cfg = load_config(config_path)

    if overrides:
        cfg = deep_merge(cfg, overrides)

    # Resolve cache_db default and relative paths.
    emb_cfg = cfg.get("embedding", {})
    cache_db_raw = str(emb_cfg.get("cache_db", "__default__"))
    if cache_db_raw == "__default__":
        cache_db = default_cache_db_path()
    else:
        cache_db = Path(cache_db_raw)
        if not cache_db.is_absolute():
            cache_db = (Path(str(root)) / cache_db).resolve()

    emb_cfg_effective = dict(emb_cfg)
    emb_cfg_effective["cache_db"] = str(cache_db)

    # SBERT model_path resolution order (see docs/learning/03-sbert-setup.md):
    #   1. explicit `embedding.model_path` in config (already populated above)
    #   2. env var DYNAMIC_FOLDING_SBERT_MODEL_PATH
    #   3. auto-discovery from default_sbert_models_dir() if exactly one model
    if emb_cfg_effective.get("provider") == "sbert" and not emb_cfg_effective.get("model_path"):
        env_model_path = os.environ.get(SBERT_MODEL_PATH_ENV)
        if env_model_path:
            emb_cfg_effective["model_path"] = env_model_path
        else:
            from dynamic_folding.core.paths import default_sbert_models_dir

            models_dir = default_sbert_models_dir()
            if models_dir.exists() and models_dir.is_dir():
                subdirs = [p for p in models_dir.iterdir() if p.is_dir()]
                if len(subdirs) == 1:
                    emb_cfg_effective["model_path"] = str(subdirs[0])

    out = dict(cfg)
    out["embedding"] = emb_cfg_effective
    return out


def run_pipeline(
    root: Path, 
    *, 
    config_path: Path | None = None, 
    overrides: dict | None = None,
    progress: Progress | None = None
) -> RunResult:
    """Run the full pipeline and return a RunResult."""

    root = root.resolve()
    cfg = resolve_effective_config(root, config_path=config_path, overrides=overrides)
    validate_config(cfg)

    timings: dict[str, float] = {
        "scanner": 0.0,
        "extractor": 0.0,
        "preprocess": 0.0,
        "embedding": 0.0,
        "clustering": 0.0,
        "naming": 0.0,
        "proposal": 0.0,
    }

    prog: Progress = progress or NullProgress()
    sc = cfg.get("scanner", {})
    pp = cfg.get("preprocess", {})
    emb_cfg = cfg.get("embedding", {})
    cl_cfg = cfg.get("clustering", {})
    nm_cfg = cfg.get("naming", {})
    prop_cfg = cfg.get("proposal", {})

    scanner_id = str(sc.get("provider", "fs")).strip().lower()
    scanner = SCANNERS.create(scanner_id, {})
    with prog.stage("scan") as st:
        _t0 = time.perf_counter()
        file_refs = scanner(root, sc)
        timings["scanner"] += time.perf_counter() - _t0
        st.advance(1)

    extractor_id = str(sc.get("extractor", "basic")).strip().lower()
    extractor = EXTRACTORS.create(extractor_id, {})

    preprocessor_id = str(pp.get("provider", "basic")).strip().lower()
    preprocessor = PREPROCESSORS.create(preprocessor_id, {})

    emb_provider = str(emb_cfg.get("provider", "fake")).strip().lower()
    emb_cfg_effective = dict(emb_cfg)
    # cache_db is already resolved to an absolute string path by resolve_effective_config
    emb_cfg_effective["cache_db"] = Path(str(emb_cfg_effective["cache_db"]))
    embedder = EMBEDDERS.create(emb_provider, {})

    # Batch processing for Extraction, Preprocessing, and Embedding
    chunk_size = int(cfg.get("pipeline", {}).get("batch_size", 100))
    all_preprocessed = []
    all_embeddings = []
    model_id = None
    
    to_extract = [fr for fr in file_refs if not fr.is_dir]
    
    with prog.stage("extractor", total=len(to_extract)) as st_ext, \
         prog.stage("preprocess", total=len(to_extract)) as st_pre, \
         prog.stage("embedding", total=len(to_extract)) as st_emb:
        
        for i in range(0, len(to_extract), chunk_size):
            batch = to_extract[i : i + chunk_size]

            # 1. Extract
            # Pass the extractor its config. snippet_size lives under [scanner]
            # (alongside the `extractor` id); without this the type-aware
            # extractor silently fell back to its own default and ignored the
            # configured value. See ADR 0036 (F2).
            _t0 = time.perf_counter()
            extract_cfg = {"snippet_size": int(sc.get("snippet_size", 4096))}
            batch_extracted = []
            for fr in batch:
                batch_extracted.append(extractor(fr, extract_cfg))
            timings["extractor"] += time.perf_counter() - _t0
            st_ext.advance(len(batch))

            # 2. Preprocess
            _t0 = time.perf_counter()
            batch_pre = []
            for d in batch_extracted:
                batch_pre.append(preprocessor(d, pp))
            timings["preprocess"] += time.perf_counter() - _t0
            all_preprocessed.extend(batch_pre)
            st_pre.advance(len(batch))

            # 3. Embed
            _t0 = time.perf_counter()
            batch_emb = embedder(batch_pre, emb_cfg_effective)
            timings["embedding"] += time.perf_counter() - _t0
            all_embeddings.extend(batch_emb)
            if batch_emb and model_id is None:
                model_id = batch_emb[0].model_id
            st_emb.advance(len(batch))

    reducer_cfg = cfg.get("reducer", {})
    reducer_id = str(reducer_cfg.get("provider", "identity")).strip().lower()
    reducer = REDUCERS.create(reducer_id, {})
    with prog.stage("reducer") as st:
        raw_vecs = [e.vector for e in all_embeddings]
        reduced_vecs = reducer(raw_vecs, reducer_cfg)
        st.advance(1)

    proposer_id = str(cfg.get("proposal", {}).get("provider", "two_level")).strip().lower()
    proposer = PROPOSERS.create(proposer_id, {})

    namer_id = str(nm_cfg.get("provider", "tfidf")).strip().lower()
    namer = NAMERS.create(namer_id, {})

    algo = str(cl_cfg.get("algorithm", "kmeans")).strip().lower()
    clusterer = CLUSTERERS.create(algo, {})

    # Lazy-loading texts from cache
    cache = EmbeddingCache(Path(str(emb_cfg_effective["cache_db"])))

    # Map each file to the exact content_hash embedded in THIS run, so naming
    # reads the text that produced the current vectors. Without this, a prior
    # run's row for the same (key, model_id) — e.g. an old empty-snippet text —
    # could be served to the namer nondeterministically. See ADR 0036 (F3).
    hash_by_rel = {e.file.rel_path: e.content_hash for e in all_embeddings}

    def fetch_texts_callback(keys: list[str]) -> list[str]:
        if not model_id:
            return []
        text_map = cache.get_many_texts(keys, model_id=model_id, content_hash_by_key=hash_by_rel)
        # Return in same order as keys
        return [text_map.get(k, "") for k in keys]

    def embed_text_callback(text: str) -> list[float]:
        # Helper to embed a single piece of text (like a folder name)
        # using the same logic as the main embedding stage.
        # We create a dummy FileRef/ExtractedDoc/PreprocessedDoc for it.
        from dynamic_folding.contracts.file_ref import FileRef
        from dynamic_folding.contracts.preprocessed import PreprocessedDoc

        dummy_fr = FileRef(path=text, rel_path=text, is_dir=False, depth=0, name=text, ext="", size=0, ctime=None, mtime=None)
        dummy_pre = PreprocessedDoc(file=dummy_fr, text_for_embedding=text, features={})
        
        # Use the same embedder created earlier
        res = embedder([dummy_pre], emb_cfg_effective)
        if res:
            return res[0].vector
        return []

    propose_cfg = {
        "algorithm": algo,
        "clusterer": clusterer,
        "clustering_cfg": dict(cl_cfg),
        "top_k": int(cl_cfg.get("top_k", 3)),
        "sub_k": int(cl_cfg.get("sub_k", 2)),
        "random_state": int(cl_cfg.get("random_state", 0)),
        "min_cluster_size": int(cl_cfg.get("min_cluster_size", 4)),
        "max_levels": int(prop_cfg.get("max_levels", 2)),
        "outliers_folder": str(prop_cfg.get("outliers_folder", "Outros")),
        "namer": namer,
        "naming_cfg": dict(nm_cfg),
        "reduced_vectors": reduced_vecs,
        "embed_text": embed_text_callback,
        "fetch_texts": fetch_texts_callback,
        "naming_direction": str(prop_cfg.get("naming_direction", "per_node")),
    }
    # The proposer performs clustering and naming internally; we surface them as
    # lightweight markers *before* the proposal stage so the UI shows them in
    # dependency order and "Gerar proposta" remains the final, long-running step.
    with prog.stage("clustering") as st_cl:
        st_cl.advance(1)
    with prog.stage("naming") as st_nm:
        st_nm.advance(1)

    with prog.stage("proposal") as st:
        _t0 = time.perf_counter()
        proposal = proposer(str(root), all_preprocessed, all_embeddings, propose_cfg)
        timings["proposal"] += time.perf_counter() - _t0
        st.advance(1)

    file_count = sum(1 for fr in file_refs if not fr.is_dir)

    # Keep basic run notes and metrics.
    proposal = StructureProposal(
        root=proposal.root,
        folders=proposal.folders,
        orphans=proposal.orphans,
        notes=[
            f"Scanned {file_count} files (max_depth={sc.get('max_depth', 2)}).",
            f"Processed in batches of {chunk_size}."
        ]
        + list(proposal.notes),
    )
    proposal.notes.extend(validate_proposal(proposal, file_refs))

    return RunResult(
        root=str(root),
        files=file_refs,
        extracted=[], # Optimization: Clear content-heavy intermediate lists
        preprocessed=[],
        embeddings=all_embeddings,
        reduced_vectors=reduced_vecs,
        proposal=proposal,
        timings=timings,
        peak_memory_mb=_get_peak_memory_mb(),
    )
