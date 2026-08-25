from __future__ import annotations

import hashlib
from pathlib import Path

from dynamic_folding.cache.sqlite_cache import EmbeddingCache
from dynamic_folding.contracts.embedding import EmbeddingRecord
from dynamic_folding.contracts.preprocessed import PreprocessedDoc
from dynamic_folding.embedding.fake import FakeEmbedder
from dynamic_folding.core.progress import ProgressStage


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def embed_with_cache(
    docs: list[PreprocessedDoc],
    *,
    cache_db: Path,
    embedder: FakeEmbedder,
    progress: ProgressStage | None = None,
) -> list[EmbeddingRecord]:
    cache = EmbeddingCache(cache_db)
    out: list[EmbeddingRecord] = []

    for d in docs:
        ch = _content_hash(d.text_for_embedding)
        key = d.file.rel_path

        cached = cache.get(key, model_id=embedder.model_id, content_hash=ch)
        if cached is None:
            vec = embedder.embed_text(d.text_for_embedding)
            cache.put(key, model_id=embedder.model_id, content_hash=ch, vector=vec, text=d.text_for_embedding)
        else:
            vec, _ = cached

        out.append(
            EmbeddingRecord(
                file=d.file,
                vector=vec,
                model_id=embedder.model_id,
                content_hash=ch,
            )
        )

        if progress is not None:
            progress.advance(1)

    return out
