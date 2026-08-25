from __future__ import annotations

from pathlib import Path


def _touch(p: Path, data: bytes = b"x") -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)


def test_extractor_produces_metadata(tmp_path: Path) -> None:
    from dynamic_folding.contracts.file_ref import FileRef
    from dynamic_folding.extractor.basic import extract

    f = tmp_path / "Some File.TXT"
    _touch(f, b"hello")

    fr = FileRef(
        path=str(f),
        rel_path="Some File.TXT",
        is_dir=False,
        depth=0,
        name=f.name,
        ext="txt",
        size=5,
        ctime=None,
        mtime=None,
    )
    doc = extract(fr)
    assert doc.file.rel_path == "Some File.TXT"
    assert doc.errors == []
    assert doc.metadata["name"] == "Some File.TXT"
    assert doc.metadata["ext"] == "txt"


def test_preprocess_template_is_deterministic(tmp_path: Path) -> None:
    from dynamic_folding.contracts.file_ref import FileRef
    from dynamic_folding.contracts.extracted import ExtractedDoc
    from dynamic_folding.preprocess.basic import preprocess

    f = tmp_path / "a.Bin"
    _touch(f, b"123")

    fr = FileRef(
        path=str(f),
        rel_path="a.Bin",
        is_dir=False,
        depth=0,
        name=f.name,
        ext="bin",
        size=3,
        ctime=1.0,
        mtime=2.0,
    )
    doc = ExtractedDoc(file=fr, metadata={"name": "a.Bin", "ext": "bin"}, errors=[])

    tpl = "{stem} ext:{ext} path:{rel_path} size:{size} depth:{depth}"
    p1 = preprocess(doc, template=tpl)
    p2 = preprocess(doc, template=tpl)
    assert p1.text_for_embedding == p2.text_for_embedding
    assert p1.text_for_embedding == "a ext:bin path:a.Bin size:3 depth:0"


def test_preprocess_omits_empty_title_slot() -> None:
    """When title is absent, [TÍTULO]: must not appear in output."""
    from dynamic_folding.contracts.file_ref import FileRef
    from dynamic_folding.contracts.extracted import ExtractedDoc
    from dynamic_folding.preprocess.basic import preprocess

    fr = FileRef(path="x", rel_path="report.pdf", is_dir=False, depth=0,
                 name="report.pdf", ext="pdf", size=10, ctime=None, mtime=None)
    doc = ExtractedDoc(file=fr, metadata={"name": "report.pdf", "ext": "pdf"}, errors=[])
    tpl = "[NOME]: {stem} [TÍTULO]: {title} [EXT]: {ext}"
    result = preprocess(doc, template=tpl)
    assert "[TÍTULO]:" not in result.text_for_embedding
    assert "[NOME]: report" in result.text_for_embedding


def test_preprocess_keeps_title_slot_when_present() -> None:
    """When title is non-empty, [TÍTULO]: value must appear in output."""
    from dynamic_folding.contracts.file_ref import FileRef
    from dynamic_folding.contracts.extracted import ExtractedDoc
    from dynamic_folding.preprocess.basic import preprocess

    fr = FileRef(path="x", rel_path="report.pdf", is_dir=False, depth=0,
                 name="report.pdf", ext="pdf", size=10, ctime=None, mtime=None)
    doc = ExtractedDoc(file=fr, metadata={"name": "report.pdf", "ext": "pdf",
                                           "title": "Annual Report"}, errors=[])
    tpl = "[NOME]: {stem} [TÍTULO]: {title} [EXT]: {ext}"
    result = preprocess(doc, template=tpl)
    assert "[TÍTULO]: Annual Report" in result.text_for_embedding


def test_pipeline_json_contains_intermediate_data(tmp_path: Path) -> None:
    from dynamic_folding.core.pipeline import run_pipeline

    _touch(tmp_path / "x.txt")
    r = run_pipeline(tmp_path)
    d = r.to_dict()
    assert d["contracts_version"] == 2
    assert d["root"]
    assert isinstance(d["files"], list)
    assert isinstance(d["extracted"], list)
    assert isinstance(d["preprocessed"], list)
    assert isinstance(d["embeddings"], list)
    assert d["proposal"]["contracts_version"] == 4

