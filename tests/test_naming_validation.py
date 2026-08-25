from __future__ import annotations
import pytest
from dynamic_folding.contracts.file_ref import FileRef
from dynamic_folding.contracts.preprocessed import PreprocessedDoc
from dynamic_folding.contracts.embedding import EmbeddingRecord
from dynamic_folding.proposal.proposer import propose_structure

def test_propose_structure_calculates_name_scores():
    # Mock data
    files = [
        FileRef(path="a.txt", rel_path="a.txt", is_dir=False, depth=0, name="a", ext="txt", size=1, ctime=None, mtime=None),
        FileRef(path="b.txt", rel_path="b.txt", is_dir=False, depth=0, name="b", ext="txt", size=1, ctime=None, mtime=None),
    ]
    pre = [
        PreprocessedDoc(file=files[0], text_for_embedding="apple fruit", features={}),
        PreprocessedDoc(file=files[1], text_for_embedding="banana fruit", features={}),
    ]
    # Simple 2D vectors
    emb = [
        EmbeddingRecord(file=files[0], vector=[1.0, 0.0], model_id="m1", content_hash="h1"),
        EmbeddingRecord(file=files[1], vector=[1.0, 0.1], model_id="m1", content_hash="h2"),
    ]

    def mock_namer(texts, cfg):
        return "Fruit"

    # Mock embedder that returns a vector for "Fruit"
    def mock_embed_text(text):
        if text == "Fruit":
            return [1.0, 0.05]
        return [0.0, 0.0]

    proposal = propose_structure(
        root="C:/test",
        preprocessed=pre,
        embeddings=emb,
        top_k=1,
        sub_k=1,
        random_state=0,
        namer=mock_namer,
        naming_cfg={},
        min_cluster_size=2, # Force them into one cluster
        embed_text=mock_embed_text
    )

    def get_name_match(nodes, name):
        for n in nodes:
            if n.name == name:
                return n.name_match
            res = get_name_match(n.subfolders, name)
            if res is not None:
                return res
        return None

    assert get_name_match(proposal.folders, "Fruit") is not None
