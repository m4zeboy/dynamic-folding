"""Regression guards for the snippet-flow defect class (ADR 0036).

These cover the three independent places content snippets were lost, plus the
config-coherence guard that prevents the class from recurring:

- F1  the type-aware extractor must extract a snippet from a FileRef produced by
      the REAL scanner (bare, dot-less ext) — the production path that the old
      dotted-ext unit fixtures never exercised.
- F2  the pipeline must pass the configured ``snippet_size`` to the extractor.
- F3  ``get_many_texts`` must return the text for the requested ``content_hash``,
      not an arbitrary stale row for the same ``(key, model_id)``.
- guard  ``validate_config`` must reject ``type_aware`` + snippet-less template.
"""
from __future__ import annotations

import pytest

from dynamic_folding.cache.sqlite_cache import EmbeddingCache
from dynamic_folding.core.paths import default_cache_db_path
from dynamic_folding.core.pipeline import run_pipeline
from dynamic_folding.core.validate_config import ConfigError, validate_config
from dynamic_folding.extractor.type_aware import extract as extract_type_aware
from dynamic_folding.scanner.fs_scanner import scan


# --------------------------------------------------------------------------- #
# F1 — real scanner output must yield a non-empty snippet
# --------------------------------------------------------------------------- #
def test_real_scanner_output_yields_nonempty_snippet(tmp_path):
    """The scanner emits a BARE ext ("txt"); the extractor must still dispatch.

    This is the exact production path the dotted-ext (".txt") unit fixtures
    failed to cover, letting the Sprint-7 dispatch bug live undetected.
    """
    (tmp_path / "report.txt").write_text(
        "Quarterly revenue analysis and 2026 forecast", encoding="utf-8"
    )

    refs = scan(
        tmp_path, max_depth=2, max_files=200, ignore_hidden=True, ignore_globs=[]
    )
    files = [r for r in refs if not r.is_dir]
    assert files, "scanner should discover the file"

    fr = files[0]
    assert fr.ext == "txt", "scanner must emit a bare, dot-less extension"

    doc = extract_type_aware(fr, {"snippet_size": 4096})
    assert "Quarterly revenue analysis" in doc.metadata["snippet"]


def test_real_scanner_pdf_dispatches_with_bare_ext(tmp_path, monkeypatch):
    """A bare 'pdf' ext (as the scanner emits) must reach the PDF parser."""
    import sys
    from unittest.mock import MagicMock

    (tmp_path / "manual.pdf").write_bytes(b"%PDF-1.4 test")
    refs = scan(
        tmp_path, max_depth=2, max_files=200, ignore_hidden=True, ignore_globs=[]
    )
    fr = [r for r in refs if not r.is_dir][0]
    assert fr.ext == "pdf"

    mock_pypdf = MagicMock()
    reader = mock_pypdf.PdfReader.return_value
    reader.metadata = {"/Subject": "widget calibration procedures"}
    reader.outline = []
    page = MagicMock()
    page.extract_text.return_value = "body"
    reader.pages = [page]

    monkeypatch.setitem(sys.modules, "pypdf", mock_pypdf)
    doc = extract_type_aware(fr, {"snippet_size": 4096})
    assert "widget calibration procedures" in doc.metadata["snippet"]


# --------------------------------------------------------------------------- #
# F2 — the pipeline must honor the configured snippet_size
# --------------------------------------------------------------------------- #
def test_pipeline_honors_configured_snippet_size(tmp_path):
    """With snippet_size=12, the embedded/cached text must reflect the cap.

    Before the fix the pipeline called ``extractor(fr, {})`` and the extractor
    fell back to its own default, ignoring ``scanner.snippet_size`` entirely.
    """
    (tmp_path / "doc.txt").write_text("X" * 200, encoding="utf-8")

    overrides = {
        "scanner": {"extractor": "type_aware", "snippet_size": 12},
        "preprocess": {"template": "[C]: {snippet}"},
        "embedding": {"provider": "fake"},
    }
    result = run_pipeline(tmp_path, overrides=overrides)

    rec = next(e for e in result.embeddings if e.file.rel_path == "doc.txt")
    cache = EmbeddingCache(default_cache_db_path())
    texts = cache.get_many_texts(
        ["doc.txt"],
        model_id=rec.model_id,
        content_hash_by_key={"doc.txt": rec.content_hash},
    )
    # template "[C]: {snippet}" with a 12-char snippet cap
    assert texts["doc.txt"] == "[C]: " + "X" * 12


# --------------------------------------------------------------------------- #
# F3 — get_many_texts pins to the requested content_hash
# --------------------------------------------------------------------------- #
def test_get_many_texts_respects_content_hash(tmp_path):
    """Two rows for one (key, model_id) must be disambiguated by content_hash.

    This is what protects naming from reading a prior run's stale (e.g.
    empty-snippet) text after the preprocessed text changes.
    """
    cache = EmbeddingCache(tmp_path / "c.sqlite")
    cache.put("a.txt", model_id="m", content_hash="old", vector=[0.0], text="OLD filename-only")
    cache.put("a.txt", model_id="m", content_hash="new", vector=[1.0], text="NEW text with snippet")

    got_new = cache.get_many_texts(
        ["a.txt"], model_id="m", content_hash_by_key={"a.txt": "new"}
    )
    assert got_new["a.txt"] == "NEW text with snippet"

    got_old = cache.get_many_texts(
        ["a.txt"], model_id="m", content_hash_by_key={"a.txt": "old"}
    )
    assert got_old["a.txt"] == "OLD filename-only"

    # A hash with no matching row yields no entry (not a wrong row).
    got_missing = cache.get_many_texts(
        ["a.txt"], model_id="m", content_hash_by_key={"a.txt": "absent"}
    )
    assert "a.txt" not in got_missing


# --------------------------------------------------------------------------- #
# guard — type_aware extractor requires a snippet-bearing template
# --------------------------------------------------------------------------- #
def _base_cfg(template: str) -> dict:
    return {
        "scanner": {"provider": "fs", "extractor": "type_aware", "max_depth": 2, "max_files": 200, "snippet_size": 4096},
        "preprocess": {"provider": "basic", "template": template},
        "embedding": {"provider": "fake", "cache_db": "__default__"},
        "naming": {"provider": "tfidf"},
        "proposal": {"provider": "two_level"},
        "clustering": {"algorithm": "kmeans"},
        "reducer": {"provider": "identity", "n_components": 10, "random_state": 0},
    }


def test_validate_config_rejects_type_aware_without_snippet_template():
    with pytest.raises(ConfigError) as exc:
        validate_config(_base_cfg("[NOME]: {stem} [EXT]: {ext}"))
    assert "snippet" in str(exc.value).lower()


def test_validate_config_accepts_type_aware_with_snippet_template():
    # Should not raise.
    validate_config(_base_cfg("[NOME]: {stem} [CONTEÚDO]: {snippet}"))
