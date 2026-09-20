from __future__ import annotations

import hashlib
import os
from pathlib import Path

import numpy as np
from dynamic_folding.cache.sqlite_cache import EmbeddingCache
from dynamic_folding.contracts.embedding import EmbeddingRecord
from dynamic_folding.contracts.preprocessed import PreprocessedDoc
from dynamic_folding.core.progress import ProgressStage


_SBERT_PROVIDER_VERSION = "v2"  # Increment to invalidate cache due to chunking

# Process-level cache of loaded SentenceTransformer models. Loading a model from
# disk costs seconds; the proposer embeds each cluster name with a fresh call, so
# without this cache the model is reloaded 15-30x during the proposal stage (the
# repeated "Loading weights" spam). Keyed by (resolved model_path, device).
_MODEL_CACHE: dict[tuple[str, str], object] = {}


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _stable_model_id(*, model_path: Path, normalize: bool, st_version: str, chunk_cfg: str) -> str:
    # Keep the cache key stable and short but sensitive to config changes.
    payload = "|".join(
        [
            "sbert",
            _SBERT_PROVIDER_VERSION,
            str(model_path),
            f"normalize={int(bool(normalize))}",
            f"sentence_transformers={st_version}",
            f"chunks={chunk_cfg}",
        ]
    ).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()[:16]
    return f"sbert:{_SBERT_PROVIDER_VERSION}:{digest}"


def _get_chunks(text: str, chunk_size_words: int, overlap_words: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + chunk_size_words])
        chunks.append(chunk)
        if i + chunk_size_words >= len(words):
            break
        i += chunk_size_words - overlap_words
        
    return chunks


def _load_model(SentenceTransformer, *, model_path: Path, device: str):
    """Return a SentenceTransformer for (model_path, device), loading at most once
    per process. Offline env guards wrap only the first, real load."""
    key = (str(model_path), str(device))
    model = _MODEL_CACHE.get(key)
    if model is not None:
        return model

    # Enforce offline behavior even if upstream libs would try to reach the hub.
    old_hf_offline = os.environ.get("HF_HUB_OFFLINE")
    old_tf_offline = os.environ.get("TRANSFORMERS_OFFLINE")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    try:
        model = SentenceTransformer(str(model_path), device=device)
    finally:
        if old_hf_offline is None:
            os.environ.pop("HF_HUB_OFFLINE", None)
        else:
            os.environ["HF_HUB_OFFLINE"] = old_hf_offline
        if old_tf_offline is None:
            os.environ.pop("TRANSFORMERS_OFFLINE", None)
        else:
            os.environ["TRANSFORMERS_OFFLINE"] = old_tf_offline

    _MODEL_CACHE[key] = model
    return model


def embed_sbert_with_cache(
    docs: list[PreprocessedDoc],
    *,
    cache_db: Path,
    model_path: Path,
    device: str = "cpu",
    batch_size: int = 32,
    normalize: bool = True,
    progress: ProgressStage | None = None,
    chunk_size_words: int = 300,
    overlap_words: int = 50,
) -> list[EmbeddingRecord]:
    model_path = Path(model_path).expanduser().resolve()
    if not model_path.exists() or not model_path.is_dir():
        raise ValueError(
            "SBERT embedding requires embedding.model_path to be an existing local directory "
            f"(got: {model_path})."
        )

    try:
        import sentence_transformers  # type: ignore
        from sentence_transformers import SentenceTransformer  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "embedding.provider='sbert' requires 'sentence-transformers' to be installed."
        ) from e

    st_version = str(getattr(sentence_transformers, "__version__", "unknown"))
    chunk_cfg = f"{chunk_size_words}:{overlap_words}"
    model_id = _stable_model_id(model_path=model_path, normalize=normalize, st_version=st_version, chunk_cfg=chunk_cfg)

    model = _load_model(SentenceTransformer, model_path=model_path, device=device)

    cache = EmbeddingCache(Path(cache_db))

    # Cache-aware batching: only embed cache misses.
    out: list[EmbeddingRecord] = []
    misses_info: list[dict] = []  # To track which chunks belong to which miss

    for i, d in enumerate(docs):
        text = d.text_for_embedding
        ch = _content_hash(text)
        key = d.file.rel_path
        cached = cache.get(key, model_id=model_id, content_hash=ch)
        if cached is None:
            chunks = _get_chunks(text, chunk_size_words, overlap_words)
            misses_info.append({
                "idx": i,
                "key": key,
                "content_hash": ch,
                "chunks": chunks,
                "full_text": text
            })
            out.append(
                EmbeddingRecord(file=d.file, vector=[], model_id=model_id, content_hash=ch)  # placeholder
            )
        else:
            vec, _ = cached
            out.append(EmbeddingRecord(file=d.file, vector=vec, model_id=model_id, content_hash=ch))
            if progress is not None:
                progress.advance(1)

    if misses_info:
        # Flatten chunks for batch processing
        all_chunks = []
        chunk_map = [] # To map flattened chunks back to docs
        for info in misses_info:
            for c in info["chunks"]:
                chunk_map.append(info["idx"])
                all_chunks.append(c)

        # Batch encode all chunks
        all_vecs = []
        for start in range(0, len(all_chunks), max(1, int(batch_size))):
            batch = all_chunks[start : start + max(1, int(batch_size))]
            vecs = model.encode(
                batch,
                batch_size=max(1, int(batch_size)),
                normalize_embeddings=bool(normalize),
                show_progress_bar=False,
            )
            all_vecs.append(vecs)
        
        if all_vecs:
            stacked_vecs = np.vstack(all_vecs)
            
            # Re-group by document and mean pool
            for info in misses_info:
                doc_idx = info["idx"]
                # Find vectors belonging to this doc
                doc_chunk_vecs = [v for i, v in enumerate(stacked_vecs) if chunk_map[i] == doc_idx]
                
                # Mean pooling
                pooled_vec = np.mean(doc_chunk_vecs, axis=0)
                
                # Normalize if requested (mean of normalized vectors is not necessarily normalized)
                if normalize:
                    norm = np.linalg.norm(pooled_vec)
                    if norm > 0:
                        pooled_vec = pooled_vec / norm
                
                vec_list = [float(x) for x in pooled_vec.tolist()]
                cache.put(info["key"], model_id=model_id, content_hash=info["content_hash"], vector=vec_list, text=info["full_text"])
                out[doc_idx] = EmbeddingRecord(
                    file=docs[doc_idx].file,
                    vector=vec_list,
                    model_id=model_id,
                    content_hash=info["content_hash"],
                )
                
                if progress is not None:
                    progress.advance(1)

    return out
