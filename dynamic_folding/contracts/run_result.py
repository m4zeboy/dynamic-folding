from __future__ import annotations

from dataclasses import dataclass, field

from dynamic_folding.contracts.extracted import ExtractedDoc
from dynamic_folding.contracts.file_ref import FileRef
from dynamic_folding.contracts.preprocessed import PreprocessedDoc
from dynamic_folding.contracts.proposal import StructureProposal
from dynamic_folding.contracts.embedding import EmbeddingRecord


@dataclass(frozen=True)
class RunResult:
    """Serializable output of the pipeline run.

    In MVP we keep intermediate products to support debugging and future UIs.
    """

    root: str
    files: list[FileRef]
    extracted: list[ExtractedDoc]
    preprocessed: list[PreprocessedDoc]
    embeddings: list[EmbeddingRecord]
    proposal: StructureProposal
    # The reduced (e.g. UMAP 10-dim) vectors the clusterer actually used, in the
    # same order as `embeddings`. Kept so density-based evaluation (DBCV) scores the
    # *real* projection the groups were drawn in, not a re-derived one. Empty when
    # the run used the identity reducer or predates this field. See ADR 0039.
    reduced_vectors: list[list[float]] = field(default_factory=list)
    timings: dict[str, float] = field(default_factory=dict)
    peak_memory_mb: float | None = None
    contracts_version: int = 2

    def to_dict(self) -> dict:
        def file_to_dict(fr: FileRef) -> dict:
            return {
                "path": fr.path,
                "rel_path": fr.rel_path,
                "is_dir": fr.is_dir,
                "depth": fr.depth,
                "name": fr.name,
                "ext": fr.ext,
                "size": fr.size,
                "ctime": fr.ctime,
                "mtime": fr.mtime,
            }

        def extracted_to_dict(d: ExtractedDoc) -> dict:
            return {
                "file": file_to_dict(d.file),
                "metadata": d.metadata,
                "errors": d.errors,
            }

        def pre_to_dict(d: PreprocessedDoc) -> dict:
            return {
                "file": file_to_dict(d.file),
                "text_for_embedding": d.text_for_embedding,
                "features": d.features,
            }

        def emb_to_dict(e: EmbeddingRecord) -> dict:
            return {
                "file": file_to_dict(e.file),
                "model_id": e.model_id,
                "content_hash": e.content_hash,
                "vector": e.vector,
            }

        return {
            "contracts_version": self.contracts_version,
            "root": self.root,
            "files": [file_to_dict(f) for f in self.files],
            "extracted": [extracted_to_dict(x) for x in self.extracted],
            "preprocessed": [pre_to_dict(p) for p in self.preprocessed],
            "embeddings": [emb_to_dict(e) for e in self.embeddings],
            "reduced_vectors": [list(v) for v in self.reduced_vectors],
            "proposal": self.proposal.to_dict(),
            "timings": dict(self.timings),
            "peak_memory_mb": self.peak_memory_mb,
        }
