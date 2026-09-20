import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from dynamic_folding.contracts.file_ref import FileRef
from dynamic_folding.extractor.type_aware import extract as extract_type_aware
from dynamic_folding.preprocess.basic import preprocess
from dynamic_folding.embedding.sbert import embed_sbert_with_cache

def test_extract_pdf_multi_page_mocked(tmp_path):
    p = tmp_path / "test.pdf"
    p.write_bytes(b"%PDF-1.4 test")
    fr = FileRef(
        path=str(p),
        rel_path="test.pdf",
        is_dir=False,
        depth=0,
        name="test.pdf",
        ext="pdf",
        size=10,
        ctime=0,
        mtime=0,
    )
    
    mock_pypdf = MagicMock()
    mock_reader = mock_pypdf.PdfReader.return_value
    mock_reader.metadata = {"/Title": "Very Long Document", "/Author": "Tester"}
    
    # Simulate 5 pages
    pages = []
    for i in range(5):
        m = MagicMock()
        m.extract_text.return_value = f"Content of page {i+1}. "
        pages.append(m)
    mock_reader.pages = pages
    
    with patch.dict(sys.modules, {"pypdf": mock_pypdf}):
        # We expect it to read at least 3 pages now
        doc = extract_type_aware(fr, {"snippet_size": 1000})
        
        # Current implementation only reads page 0. 
        # New implementation should concatenate first 3 pages.
        assert "page 1" in doc.metadata["snippet"]
        assert "page 2" in doc.metadata["snippet"]
        assert "page 3" in doc.metadata["snippet"]
        assert "page 4" not in doc.metadata["snippet"]

def test_preprocess_emits_both_filename_and_title():
    """ADR 0025: template emits {stem} and {title} in distinct slots so the
    embedder sees both signals, instead of selecting one via priorização.
    """
    from dynamic_folding.contracts.extracted import ExtractedDoc

    fr = FileRef(path="DOC_123.pdf", rel_path="DOC_123.pdf", is_dir=False, depth=0, name="DOC_123.pdf", ext="pdf", size=10, ctime=0, mtime=0)
    template = "[NOME]: {stem} [TÍTULO]: {title} [EXT]: {ext} [CONTEÚDO]: {snippet}"

    # Case 1: Both filename and internal title present — both appear.
    doc1 = ExtractedDoc(
        file=fr,
        metadata={"name": "DOC_123.pdf", "ext": ".pdf", "title": "Academic Transcript 2024", "snippet": "some content"},
    )
    p1 = preprocess(doc1, template=template)
    assert "[NOME]: DOC_123" in p1.text_for_embedding
    assert "[TÍTULO]: Academic Transcript 2024" in p1.text_for_embedding

    # Case 2: Title missing or empty — the slot collapses but the filename
    # is still present (SafeDict returns "" for missing keys, no error).
    doc2 = ExtractedDoc(
        file=fr,
        metadata={"name": "DOC_123.pdf", "ext": ".pdf", "snippet": "some content"},
    )
    p2 = preprocess(doc2, template=template)
    assert "[NOME]: DOC_123" in p2.text_for_embedding
    # Title slot is present but empty; the stem is NOT silently substituted into it.
    assert "[TÍTULO]: DOC_123" not in p2.text_for_embedding

def test_sbert_pooling_mocked(tmp_path):
    from dynamic_folding.contracts.preprocessed import PreprocessedDoc
    
    fr = FileRef(path="long.txt", rel_path="long.txt", is_dir=False, depth=0, name="long.txt", ext="txt", size=1000, ctime=0, mtime=0)
    # Create a long text that should be chunked. 
    # If chunk size is ~300 words, let's make it 1000 words.
    long_text = "word " * 1000
    doc = PreprocessedDoc(file=fr, text_for_embedding=long_text)
    
    cache_db = tmp_path / "cache.db"
    model_path = tmp_path / "fake_model"
    model_path.mkdir()
    
    mock_st = MagicMock()
    mock_model = mock_st.SentenceTransformer.return_value
    
    # Mock encode to return different vectors for different chunks
    # Let's say it returns 4 chunks.
    import numpy as np
    mock_vecs = [np.array([1.0, 0.0]), np.array([0.0, 1.0]), np.array([-1.0, 0.0]), np.array([0.0, -1.0])]
    mock_model.encode.side_effect = lambda texts, **kwargs: np.array([mock_vecs[i % 4] for i in range(len(texts))])
    
    with patch.dict(sys.modules, {"sentence_transformers": mock_st}):
        # Mocking version for stable_model_id
        mock_st.__version__ = "3.0.0"
        
        recs = embed_sbert_with_cache([doc], cache_db=cache_db, model_path=model_path)
        
        # If it used mean pooling across 4 orthogonal vectors, the result should be [0, 0]
        # Actually it depends on how many chunks it made.
        # The key is that mock_model.encode should be called with a list of strings (chunks) 
        # instead of a single string.
        assert len(recs) == 1
        vec = recs[0].vector
        assert len(vec) == 2
        # If it pooled correctly: (1+0-1+0)/4 = 0, (0+1+0-1)/4 = 0
        assert vec == [0.0, 0.0]
