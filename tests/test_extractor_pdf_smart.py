"""Sprint 19: PDF smart structural extraction.

Mirrors the Sprint 17 pattern (priority-then-backfill) for .pdf files,
using PDF outline titles + /Subject + /Keywords as the priority block,
backfilled with body text from the first 3 pages.
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from dynamic_folding.contracts.file_ref import FileRef
from dynamic_folding.extractor.type_aware import extract as extract_type_aware


def _pdf_file_ref(tmp_path):
    p = tmp_path / "doc.pdf"
    p.write_bytes(b"%PDF-1.4 test")
    return FileRef(
        path=str(p),
        rel_path="doc.pdf",
        is_dir=False,
        depth=0,
        name="doc.pdf",
        ext="pdf",
        size=p.stat().st_size,
        ctime=0,
        mtime=0,
    )


def _outline_entry(title):
    e = MagicMock()
    e.title = title
    return e


def test_pdf_outline_titles_prioritized_over_body(tmp_path):
    fr = _pdf_file_ref(tmp_path)

    mock_pypdf = MagicMock()
    reader = mock_pypdf.PdfReader.return_value
    reader.metadata = {"/Title": "Manual", "/Author": "Acme"}
    reader.outline = [
        _outline_entry("Introduction to Widgets"),
        _outline_entry("Advanced Widget Calibration"),
    ]
    page = MagicMock()
    page.extract_text.return_value = "boilerplate body text that should be deprioritized"
    reader.pages = [page, page, page]

    with patch.dict(sys.modules, {"pypdf": mock_pypdf}):
        doc = extract_type_aware(fr, {"snippet_size": 4096})

    assert doc.errors == []
    snippet = doc.metadata["snippet"]
    # Outline titles must appear and must precede the body text.
    intro_idx = snippet.find("Introduction to Widgets")
    adv_idx = snippet.find("Advanced Widget Calibration")
    body_idx = snippet.find("boilerplate body text")
    assert intro_idx != -1
    assert adv_idx != -1
    assert intro_idx < adv_idx, "outline traversal must be stable DFS order"
    if body_idx != -1:
        assert intro_idx < body_idx and adv_idx < body_idx


def test_pdf_subject_and_keywords_extracted(tmp_path):
    fr = _pdf_file_ref(tmp_path)

    mock_pypdf = MagicMock()
    reader = mock_pypdf.PdfReader.return_value
    reader.metadata = {
        "/Title": "Manual",
        "/Author": "Acme",
        "/Subject": "widget calibration procedures",
        "/Keywords": "widget, calibration, manual",
    }
    reader.outline = []
    page = MagicMock()
    page.extract_text.return_value = "body"
    reader.pages = [page]

    with patch.dict(sys.modules, {"pypdf": mock_pypdf}):
        doc = extract_type_aware(fr, {"snippet_size": 4096})

    assert doc.metadata["subject"] == "widget calibration procedures"
    assert doc.metadata["keywords"] == "widget, calibration, manual"
    # Subject + Keywords should also feed the priority block (signal density).
    assert "widget calibration procedures" in doc.metadata["snippet"]
    assert "widget, calibration, manual" in doc.metadata["snippet"]


def test_pdf_priority_block_at_cap_skips_body(tmp_path):
    fr = _pdf_file_ref(tmp_path)

    mock_pypdf = MagicMock()
    reader = mock_pypdf.PdfReader.return_value
    long_title = "A" * 50
    reader.metadata = {}
    reader.outline = [_outline_entry(long_title)]
    page = MagicMock()
    page.extract_text.return_value = "BODYBODYBODYBODY"
    reader.pages = [page]

    with patch.dict(sys.modules, {"pypdf": mock_pypdf}):
        doc = extract_type_aware(fr, {"snippet_size": 30})

    snippet = doc.metadata["snippet"]
    assert len(snippet) <= 30
    assert "A" * 30 in snippet
    assert "BODY" not in snippet


def test_pdf_no_outline_falls_back_to_body(tmp_path):
    """Regression guard: PDFs without an outline behave as before Sprint 19."""
    fr = _pdf_file_ref(tmp_path)

    mock_pypdf = MagicMock()
    reader = mock_pypdf.PdfReader.return_value
    reader.metadata = {"/Title": "T", "/Author": "A"}
    reader.outline = []
    page = MagicMock()
    page.extract_text.return_value = "PDF body content snippet"
    reader.pages = [page]

    with patch.dict(sys.modules, {"pypdf": mock_pypdf}):
        doc = extract_type_aware(fr, {"snippet_size": 24})

    assert doc.metadata["title"] == "T"
    assert doc.metadata["author"] == "A"
    assert "PDF body content snippet"[:24] == doc.metadata["snippet"]


def test_pdf_nested_outline_flattened_dfs(tmp_path):
    fr = _pdf_file_ref(tmp_path)

    mock_pypdf = MagicMock()
    reader = mock_pypdf.PdfReader.return_value
    reader.metadata = {}
    reader.outline = [
        _outline_entry("Chapter 1"),
        [
            _outline_entry("Section 1.1"),
            _outline_entry("Section 1.2"),
        ],
        _outline_entry("Chapter 2"),
    ]
    page = MagicMock()
    page.extract_text.return_value = ""
    reader.pages = [page]

    with patch.dict(sys.modules, {"pypdf": mock_pypdf}):
        doc = extract_type_aware(fr, {"snippet_size": 4096})

    snippet = doc.metadata["snippet"]
    positions = [
        snippet.find("Chapter 1"),
        snippet.find("Section 1.1"),
        snippet.find("Section 1.2"),
        snippet.find("Chapter 2"),
    ]
    assert all(p != -1 for p in positions)
    assert positions == sorted(positions), "DFS order: parent before children, siblings in order"


def test_pdf_corrupted_outline_does_not_crash(tmp_path):
    fr = _pdf_file_ref(tmp_path)

    mock_pypdf = MagicMock()
    reader = mock_pypdf.PdfReader.return_value
    reader.metadata = {}

    bad = MagicMock()
    type(bad).title = property(lambda self: (_ for _ in ()).throw(ValueError("bad encoding")))
    good = _outline_entry("Good Title")
    reader.outline = [bad, good]

    page = MagicMock()
    page.extract_text.return_value = ""
    reader.pages = [page]

    with patch.dict(sys.modules, {"pypdf": mock_pypdf}):
        doc = extract_type_aware(fr, {"snippet_size": 4096})

    # The bad entry is skipped, the good one survives, and we don't error out.
    assert doc.errors == []
    assert "Good Title" in doc.metadata["snippet"]


def test_pdf_missing_pypdf_graceful_fallback(tmp_path):
    fr = _pdf_file_ref(tmp_path)
    with patch.dict(sys.modules, {"pypdf": None}):
        doc = extract_type_aware(fr, {"snippet_size": 4096})
    assert doc.metadata["snippet"] == ""
    assert "title" not in doc.metadata
    assert "subject" not in doc.metadata


def test_pdf_deterministic_output(tmp_path):
    fr = _pdf_file_ref(tmp_path)

    def build_reader():
        mock_pypdf = MagicMock()
        reader = mock_pypdf.PdfReader.return_value
        reader.metadata = {"/Subject": "topic", "/Keywords": "k1, k2"}
        reader.outline = [_outline_entry("Alpha"), _outline_entry("Beta")]
        page = MagicMock()
        page.extract_text.return_value = "body text"
        reader.pages = [page]
        return mock_pypdf

    with patch.dict(sys.modules, {"pypdf": build_reader()}):
        doc1 = extract_type_aware(fr, {"snippet_size": 4096})
    with patch.dict(sys.modules, {"pypdf": build_reader()}):
        doc2 = extract_type_aware(fr, {"snippet_size": 4096})

    assert doc1.metadata["snippet"] == doc2.metadata["snippet"]
