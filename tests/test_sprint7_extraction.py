import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from dynamic_folding.contracts.file_ref import FileRef
from dynamic_folding.extractor.type_aware import extract as extract_type_aware

@pytest.fixture
def txt_file(tmp_path):
    p = tmp_path / "test.txt"
    p.write_text("This is a test snippet content " * 50, encoding="utf-8")
    return FileRef(
        path=str(p),
        rel_path="test.txt",
        is_dir=False,
        depth=0,
        name="test.txt",
        ext="txt",
        size=p.stat().st_size,
        ctime=p.stat().st_ctime,
        mtime=p.stat().st_mtime,
    )

def test_extract_text_snippet(txt_file):
    doc = extract_type_aware(txt_file, {"snippet_size": 10})
    assert "snippet" in doc.metadata
    assert doc.metadata["snippet"] == "This is a "
    assert len(doc.errors) == 0

def test_extract_pdf_mocked(tmp_path):
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
    
    # Simulate pypdf being present
    mock_pypdf = MagicMock()
    mock_reader = mock_pypdf.PdfReader.return_value
    mock_reader.metadata = {"/Title": "Test PDF", "/Author": "Tester"}
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "PDF page content snippet"
    mock_reader.pages = [mock_page]
    
    with patch.dict(sys.modules, {"pypdf": mock_pypdf}):
        doc = extract_type_aware(fr, {"snippet_size": 20})
        
        assert doc.metadata["title"] == "Test PDF"
        assert doc.metadata["author"] == "Tester"
        assert doc.metadata["snippet"] == "PDF page content sni"

def test_extract_image_mocked(tmp_path):
    p = tmp_path / "test.jpg"
    p.write_bytes(b"fake jpeg")
    fr = FileRef(
        path=str(p),
        rel_path="test.jpg",
        is_dir=False,
        depth=0,
        name="test.jpg",
        ext="jpg",
        size=10,
        ctime=0,
        mtime=0,
    )
    
    # Simulate PIL being present
    mock_pil = MagicMock()
    mock_img = mock_pil.Image.open.return_value.__enter__.return_value
    mock_img.getexif.return_value = {
        0x0110: "Camera Model",  # Model
        0x0132: "2026:04:30 12:00:00",  # DateTime
    }
    
    with patch.dict(sys.modules, {"PIL": mock_pil, "PIL.Image": mock_pil.Image}):
        doc = extract_type_aware(fr, {})
        
        assert doc.metadata["model"] == "Camera Model"
        assert "2026:04:30" in str(doc.metadata["datetime"])

def test_extract_fallback_on_missing_dependency():
    # If pypdf is "missing", it should still return basic metadata for a .pdf file
    fr_pdf = FileRef(
        path="test.pdf",
        rel_path="test.pdf",
        is_dir=False,
        depth=0,
        name="test.pdf",
        ext="pdf",
        size=10,
        ctime=0,
        mtime=0,
    )
    
    # Ensure pypdf is NOT in sys.modules for this test
    with patch.dict(sys.modules, {"pypdf": None}):
        doc = extract_type_aware(fr_pdf, {})
        assert doc.file.name == "test.pdf"
        assert doc.metadata["snippet"] == ""
        assert "title" not in doc.metadata

    fr_docx = FileRef(
        path="test.docx", rel_path="test.docx", is_dir=False, depth=0,
        name="test.docx", ext="docx", size=10, ctime=0, mtime=0
    )
    with patch.dict(sys.modules, {"docx": None}):
        doc = extract_type_aware(fr_docx, {})
        assert doc.file.name == "test.docx"
        assert doc.metadata["snippet"] == ""

    fr_pptx = FileRef(
        path="test.pptx", rel_path="test.pptx", is_dir=False, depth=0,
        name="test.pptx", ext="pptx", size=10, ctime=0, mtime=0
    )
    with patch.dict(sys.modules, {"pptx": None}):
        doc = extract_type_aware(fr_pptx, {})
        assert doc.file.name == "test.pptx"
        assert doc.metadata["snippet"] == ""

def test_extract_docx_mocked(tmp_path):
    p = tmp_path / "test.docx"
    p.write_bytes(b"fake docx")
    fr = FileRef(
        path=str(p), rel_path="test.docx", is_dir=False, depth=0,
        name="test.docx", ext="docx", size=10, ctime=0, mtime=0
    )
    
    mock_docx = MagicMock()
    mock_doc = mock_docx.Document.return_value
    mock_doc.core_properties.title = "Test Docx"
    mock_doc.core_properties.author = "Docx Tester"
    
    p1 = MagicMock()
    p1.style.name = "Normal"
    p1.text = "This is normal body text that should be lower priority."
    
    p2 = MagicMock()
    p2.style.name = "Heading 1"
    p2.text = "Important Heading"
    
    p3 = MagicMock()
    p3.style.name = "Title"
    p3.text = "Main Title"
    
    mock_doc.paragraphs = [p1, p2, p3]
    
    with patch.dict(sys.modules, {"docx": mock_docx}):
        # Limit snippet size so we only capture the priority ones if logic is right
        doc = extract_type_aware(fr, {"snippet_size": 30})
        
        print("DEBUG DOC ERRORS:", doc.errors)
        print("DEBUG DOC MD:", doc.metadata)
        assert doc.errors == []
        assert doc.metadata.get("title") == "Test Docx"
        assert doc.metadata["author"] == "Docx Tester"
        assert "Important Heading" in doc.metadata["snippet"]
        assert "Main Title" in doc.metadata["snippet"]
        assert "normal body text" not in doc.metadata["snippet"]

def test_extract_pptx_mocked(tmp_path):
    p = tmp_path / "test.pptx"
    p.write_bytes(b"fake pptx")
    fr = FileRef(
        path=str(p), rel_path="test.pptx", is_dir=False, depth=0,
        name="test.pptx", ext="pptx", size=10, ctime=0, mtime=0
    )
    
    mock_pptx = MagicMock()
    mock_prs = mock_pptx.Presentation.return_value
    mock_prs.core_properties.title = "Test Pptx"
    
    slide = MagicMock()
    
    shape1 = MagicMock()
    shape1.has_text_frame = True
    shape1.is_placeholder = False
    shape1.text = "Body text"
    
    shape2 = MagicMock()
    shape2.has_text_frame = True
    shape2.is_placeholder = True
    shape2.placeholder_format.type = 1 # Title
    shape2.text = "Slide Title"
    
    slide.shapes = [shape1, shape2]
    mock_prs.slides = [slide]
    
    # Mock pptx.enum.shapes for PP_PLACEHOLDER checking
    mock_enum = MagicMock()
    mock_enum.shapes.PP_PLACEHOLDER.TITLE = 1
    mock_enum.shapes.PP_PLACEHOLDER.CENTER_TITLE = 3
    
    with patch.dict(sys.modules, {"pptx": mock_pptx, "pptx.enum": mock_enum}):
        doc = extract_type_aware(fr, {"snippet_size": 20})
        
        assert doc.errors == []
        assert doc.metadata.get("title") == "Test Pptx"
        assert "Slide Title" in doc.metadata["snippet"]
        assert "Body text" not in doc.metadata["snippet"]
