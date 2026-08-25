from __future__ import annotations
import pytest
from pathlib import Path
from dynamic_folding.core.pipeline import run_pipeline
from dynamic_folding.contracts.proposal import StructureProposal

def _touch(p: Path, content: str = "x") -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)

def test_streaming_pipeline_boundaries(tmp_path: Path):
    # Create 5 files
    for i in range(5):
        _touch(tmp_path / f"file_{i}.txt", f"content of file {i}")
    
    # Run with batch_size=2 to test boundary logic (5 files / 2 = 3 batches)
    overrides = {
        "pipeline": {"batch_size": 2},
        "embedding": {"provider": "fake", "cache_db": str(tmp_path / "cache.db")},
    }
    
    result = run_pipeline(tmp_path, overrides=overrides)
    
    # 1. Check notes mention batch size
    assert any("batches of 2" in note for note in result.proposal.notes)
    
    # 2. Check all files are present in the proposal
    placed = []
    def collect_files(nodes):
        for n in nodes:
            placed.extend(n.files)
            collect_files(n.subfolders)
    
    collect_files(result.proposal.folders)
    placed.extend(result.proposal.orphans)
    
    assert len(placed) == 5
    
    # 3. Check memory optimization (intermediate lists cleared)
    assert result.extracted == []
    assert result.preprocessed == []
    assert len(result.embeddings) == 5

def test_lazy_text_loading_in_proposer(tmp_path: Path):
    # Verify that the proposer can retrieve texts from cache
    _touch(tmp_path / "apple.txt", "this is about apples")
    _touch(tmp_path / "apple2.txt", "this is also about apples")
    _touch(tmp_path / "banana.txt", "this is about bananas")
    _touch(tmp_path / "banana2.txt", "this is also about bananas")
    
    cache_path = tmp_path / "cache.db"
    overrides = {
        "embedding": {"provider": "fake", "cache_db": str(cache_path)},
        "clustering": {"min_cluster_size": 2}, # Force folders for groups
    }
    
    result = run_pipeline(tmp_path, overrides=overrides)
    
    # Check if naming worked (requires texts)
    # The fake namer (tfidf) needs the texts to generate names
    assert len(result.proposal.folders) >= 1
    # If naming happened, it means get_texts() worked in proposer
