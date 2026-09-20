from __future__ import annotations

import json
from unittest.mock import MagicMock, patch


def _mock_ollama_response(response_text: str) -> MagicMock:
    """Build a MagicMock that mimics urllib's response context manager."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(
        {"response": response_text}, ensure_ascii=False
    ).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    mock_resp.__exit__.return_value = False
    return mock_resp


def _ollama_cfg(**overrides) -> dict:
    base = {
        "model": "llama3.1",
        "base_url": "http://127.0.0.1:11434",
        "prompt_variant": "grounded",
        "timeout_s": 5,
        "top_k_files": 25,
        "top_terms": 2,
        "top_anchor_terms": 5,
    }
    base.update(overrides)
    return base


# -- extract_anchor_terms --------------------------------------------------


def test_extract_anchor_terms_returns_up_to_top_n() -> None:
    from dynamic_folding.naming.tfidf import extract_anchor_terms

    texts = [
        "certificacao abnt janelas",
        "certificacao abnt portas",
        "certificacao abnt esquadrias",
    ]
    terms = extract_anchor_terms(texts, top_n=3)

    # Terms shared across all texts should rank high.
    assert 0 < len(terms) <= 3
    assert "certificacao" in terms
    assert "abnt" in terms


def test_extract_anchor_terms_empty_input() -> None:
    from dynamic_folding.naming.tfidf import extract_anchor_terms

    assert extract_anchor_terms([], top_n=5) == []
    assert extract_anchor_terms(["", " ", "  "], top_n=5) == []


def test_extract_anchor_terms_filters_template_stopwords() -> None:
    """Preprocess-template markers and common extensions don't pollute anchors (Phase E)."""
    from dynamic_folding.naming.tfidf import extract_anchor_terms

    # Mirrors the default preprocess template output: every doc has the literal
    # [FILE]:, [EXT]:, [CONTENT]: markers plus an extension value (`pdf`).
    texts = [
        "[FILE]: certificado janelas [EXT]: pdf [CONTENT]:",
        "[FILE]: certificado portas [EXT]: pdf [CONTENT]:",
        "[FILE]: certificado esquadrias [EXT]: pdf [CONTENT]:",
    ]
    terms = extract_anchor_terms(texts, top_n=5)

    for stop in ("file", "ext", "content", "pdf"):
        assert stop not in terms, f"{stop!r} leaked into anchor terms: {terms}"

    # Real distinguishing content survives.
    assert "certificado" in terms


def test_extract_anchor_terms_ranks_by_tfidf_not_frequency() -> None:
    """A term shared by every doc has low TF-IDF; distinctive terms rank above it."""
    from dynamic_folding.naming.tfidf import extract_anchor_terms

    texts = [
        "shared shared shared exclusive_a",
        "shared shared shared exclusive_b",
        "shared shared shared exclusive_c",
    ]
    terms = extract_anchor_terms(texts, top_n=4)

    # All four tokens may appear; the distinctive ones should rank above 'shared'.
    # (TfidfVectorizer's idf for terms present in every doc is the lowest.)
    assert "exclusive_a" in terms
    assert "exclusive_b" in terms
    assert "exclusive_c" in terms


# -- grounded prompt construction ------------------------------------------


def test_grounded_request_uses_system_role_and_prompt() -> None:
    """Grounded variant must split rules (system) from data (prompt)."""
    from dynamic_folding.naming.ollama import name_cluster_ollama

    captured: dict = {}

    def fake_urlopen(req, timeout):  # noqa: ARG001
        body = json.loads(req.data.decode("utf-8"))
        captured["body"] = body
        return _mock_ollama_response("Certificacao ABNT")

    cfg = _ollama_cfg()
    texts = ["certificacao abnt janelas", "certificacao abnt portas"]

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        name = name_cluster_ollama(texts, cfg)

    body = captured["body"]
    assert "system" in body, "grounded variant must set the system field"
    assert "PRINCÍPIO DE ANCORAGEM" in body["system"]
    assert "REGRAS RÍGIDAS" in body["system"]
    # User prompt holds data + cue, not rules.
    assert "PALAVRAS RECORRENTES NO GRUPO" in body["prompt"]
    assert "ARQUIVOS:" in body["prompt"]
    assert "PRINCÍPIO DE ANCORAGEM" not in body["prompt"]
    # At least one anchor term must appear in the user message.
    assert "certificacao" in body["prompt"].lower() or "abnt" in body["prompt"].lower()
    assert name == "Certificacao ABNT"


def test_grounded_handles_no_anchor_terms_without_keyerror() -> None:
    """When TF-IDF returns no terms, the user prompt still formats cleanly."""
    from dynamic_folding.naming.ollama import name_cluster_ollama

    captured: dict = {}

    def fake_urlopen(req, timeout):  # noqa: ARG001
        body = json.loads(req.data.decode("utf-8"))
        captured["body"] = body
        return _mock_ollama_response("Tema")

    # Punctuation-only texts produce no TfidfVectorizer vocabulary, so the
    # anchor list is empty and the fallback marker should be injected.
    cfg = _ollama_cfg()
    texts = ["...", "!!!"]

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        name_cluster_ollama(texts, cfg)

    # System message is still present; user prompt has the fallback marker.
    assert "system" in captured["body"]
    assert "PRINCÍPIO DE ANCORAGEM" in captured["body"]["system"]
    assert "(nenhum termo recorrente identificado)" in captured["body"]["prompt"]


def test_default_variant_omits_system_field_and_anchor_block() -> None:
    """Default variant preserves the pre-β.2 single-prompt body shape."""
    from dynamic_folding.naming.ollama import name_cluster_ollama

    captured: dict = {}

    def fake_urlopen(req, timeout):  # noqa: ARG001
        body = json.loads(req.data.decode("utf-8"))
        captured["body"] = body
        return _mock_ollama_response("Tema")

    cfg = _ollama_cfg(prompt_variant="default")
    texts = ["arquivo um"]

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        name_cluster_ollama(texts, cfg)

    body = captured["body"]
    assert "system" not in body, "default variant must NOT use system field"
    assert "PRINCÍPIO DE ANCORAGEM" not in body["prompt"]
    assert "PALAVRAS RECORRENTES NO GRUPO" not in body["prompt"]


# -- ambiguity synonym normalization ---------------------------------------


def test_normalize_ambiguity_synonyms_rewrites_known_synonyms() -> None:
    """Small models paraphrase '_Ambíguo' as 'Nenhum', 'Vazio', etc."""
    from dynamic_folding.naming.ollama import _normalize_ambiguity_synonyms

    assert _normalize_ambiguity_synonyms("Nenhum") == "_Ambíguo"
    assert _normalize_ambiguity_synonyms("nenhum") == "_Ambíguo"
    assert _normalize_ambiguity_synonyms("NENHUM") == "_Ambíguo"
    assert _normalize_ambiguity_synonyms("Vazio") == "_Ambíguo"
    assert _normalize_ambiguity_synonyms("Ambíguo") == "_Ambíguo"  # missing underscore
    assert _normalize_ambiguity_synonyms("Ambiguo") == "_Ambíguo"  # no diacritic
    assert _normalize_ambiguity_synonyms("Indefinido") == "_Ambíguo"


def test_normalize_ambiguity_synonyms_passes_through_real_labels() -> None:
    """Real folder labels are returned unchanged."""
    from dynamic_folding.naming.ollama import _normalize_ambiguity_synonyms

    assert _normalize_ambiguity_synonyms("Certificação ABNT") == "Certificação ABNT"
    assert _normalize_ambiguity_synonyms("Projetos") == "Projetos"
    assert _normalize_ambiguity_synonyms("  Tema único  ") == "Tema único"
    # Multi-word labels with ambiguity-adjacent words but not exact match
    # are preserved.
    assert _normalize_ambiguity_synonyms("Pasta Vazia") == "Pasta Vazia"


# -- end-to-end with mocked Ollama -----------------------------------------


def test_grounded_normalizes_nenhum_to_ambiguo_end_to_end() -> None:
    """LLM responds 'Nenhum' → normalization rewrites to '_Ambíguo'."""
    from dynamic_folding.naming.ollama import name_cluster_ollama

    def fake_urlopen(req, timeout):  # noqa: ARG001
        return _mock_ollama_response("Nenhum")

    cfg = _ollama_cfg()
    texts = ["arquivo opaco um", "arquivo opaco dois"]

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        name = name_cluster_ollama(texts, cfg)

    assert name == "_Ambíguo"


# -- "_Ambíguo" escape hatch -----------------------------------------------


def test_grounded_preserves_ambiguous_response() -> None:
    """LLM response '_Ambíguo' must survive sanitization as folder name."""
    from dynamic_folding.naming.ollama import name_cluster_ollama

    def fake_urlopen(req, timeout):  # noqa: ARG001
        return _mock_ollama_response("_Ambíguo")

    cfg = _ollama_cfg()
    texts = ["arquivo opaco um", "arquivo opaco dois"]

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        name = name_cluster_ollama(texts, cfg)

    assert name == "_Ambíguo"


# -- β.1 sanitization composes with grounded output ------------------------


def test_grounded_output_strips_trailing_connectives() -> None:
    """β.1 sanitization (strip 'de'/'e' at end) applies to grounded output too."""
    from dynamic_folding.naming.ollama import name_cluster_ollama

    def fake_urlopen(req, timeout):  # noqa: ARG001
        return _mock_ollama_response("Tema de")

    cfg = _ollama_cfg()
    texts = ["arquivo um", "arquivo dois"]

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        name = name_cluster_ollama(texts, cfg)

    assert name == "Tema"


# -- Phase D: diagnostic JSONL logger --------------------------------------


def test_debug_logger_no_op_when_env_var_unset(tmp_path, monkeypatch) -> None:
    """Env var absent → no file created, pipeline behaves as before."""
    from dynamic_folding.naming.ollama import name_cluster_ollama

    monkeypatch.delenv("DYNAMIC_FOLDING_NAMING_DEBUG_PATH", raising=False)
    debug_file = tmp_path / "naming_debug.jsonl"

    def fake_urlopen(req, timeout):  # noqa: ARG001
        return _mock_ollama_response("Tema")

    cfg = _ollama_cfg()
    texts = ["arquivo um", "arquivo dois"]

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        name = name_cluster_ollama(texts, cfg)

    assert name == "Tema"
    assert not debug_file.exists(), "no file should be created when env var is unset"


def test_debug_logger_writes_full_record_on_success(tmp_path, monkeypatch) -> None:
    """Env var set → JSONL line with all schema fields and correct values."""
    from dynamic_folding.naming.ollama import name_cluster_ollama

    debug_file = tmp_path / "naming_debug.jsonl"
    monkeypatch.setenv("DYNAMIC_FOLDING_NAMING_DEBUG_PATH", str(debug_file))

    def fake_urlopen(req, timeout):  # noqa: ARG001
        return _mock_ollama_response("Certificacao ABNT")

    cfg = _ollama_cfg()
    texts = ["certificacao abnt janelas", "certificacao abnt portas"]

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        name = name_cluster_ollama(texts, cfg)

    assert name == "Certificacao ABNT"
    assert debug_file.exists()

    lines = debug_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])

    expected_fields = {
        "timestamp_utc",
        "model",
        "variant",
        "n_files",
        "files_block",
        "anchor_terms",
        "system",
        "prompt",
        "raw_response",
        "normalized_response",
        "final_name",
        "used_fallback",
    }
    assert expected_fields <= set(record.keys())

    # Specific values for this grounded-variant call.
    assert record["model"] == "llama3.1"
    assert record["variant"] == "grounded"
    assert record["n_files"] == 2
    assert "certificacao abnt janelas" in record["files_block"]
    assert "certificacao abnt portas" in record["files_block"]
    assert record["raw_response"] == "Certificacao ABNT"
    assert record["normalized_response"] == "Certificacao ABNT"
    assert record["final_name"] == "Certificacao ABNT"
    assert record["used_fallback"] is False
    assert isinstance(record["anchor_terms"], list)
    assert len(record["anchor_terms"]) > 0
    assert record["system"] is not None and "PRINCÍPIO DE ANCORAGEM" in record["system"]


def test_debug_logger_records_fallback_on_non_loopback(tmp_path, monkeypatch) -> None:
    """Fallback path → used_fallback=True, raw_response empty (LLM never called)."""
    from dynamic_folding.naming.ollama import name_cluster_ollama

    debug_file = tmp_path / "naming_debug.jsonl"
    monkeypatch.setenv("DYNAMIC_FOLDING_NAMING_DEBUG_PATH", str(debug_file))

    cfg = _ollama_cfg(base_url="https://example.com:11434")
    texts = ["certificacao abnt janelas"]

    # Should not raise; should return TF-IDF fallback.
    name = name_cluster_ollama(texts, cfg)
    assert name, "fallback must return a non-empty name"

    lines = debug_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["used_fallback"] is True
    assert record["raw_response"] == ""
    # Final name is the TF-IDF fallback value.
    assert record["final_name"] == name


def test_debug_logger_swallows_write_error(tmp_path, monkeypatch, capsys) -> None:
    """Invalid debug path → pipeline still works, warning goes to stderr."""
    from dynamic_folding.naming.ollama import name_cluster_ollama

    # A directory path cannot be opened as a file for append.
    bad_path = tmp_path / "subdir"
    bad_path.mkdir()
    monkeypatch.setenv("DYNAMIC_FOLDING_NAMING_DEBUG_PATH", str(bad_path))

    def fake_urlopen(req, timeout):  # noqa: ARG001
        return _mock_ollama_response("Tema")

    cfg = _ollama_cfg()
    texts = ["arquivo um"]

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        name = name_cluster_ollama(texts, cfg)

    # Pipeline succeeds despite logger failure.
    assert name == "Tema"
    captured = capsys.readouterr()
    assert "[naming-debug]" in captured.err


def test_debug_logger_appends_one_line_per_call(tmp_path, monkeypatch) -> None:
    """Multiple calls in the same run append distinct JSONL lines."""
    from dynamic_folding.naming.ollama import name_cluster_ollama

    debug_file = tmp_path / "naming_debug.jsonl"
    monkeypatch.setenv("DYNAMIC_FOLDING_NAMING_DEBUG_PATH", str(debug_file))

    responses = iter(["Tema A", "Tema B", "Tema C"])

    def fake_urlopen(req, timeout):  # noqa: ARG001
        return _mock_ollama_response(next(responses))

    cfg = _ollama_cfg()

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        name_cluster_ollama(["arquivo um"], cfg)
        name_cluster_ollama(["arquivo dois"], cfg)
        name_cluster_ollama(["arquivo tres"], cfg)

    lines = debug_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3
    records = [json.loads(line) for line in lines]
    assert [r["raw_response"] for r in records] == ["Tema A", "Tema B", "Tema C"]


def test_debug_logger_default_variant_omits_grounded_fields(tmp_path, monkeypatch) -> None:
    """Default variant record has anchor_terms=None and system=None."""
    from dynamic_folding.naming.ollama import name_cluster_ollama

    debug_file = tmp_path / "naming_debug.jsonl"
    monkeypatch.setenv("DYNAMIC_FOLDING_NAMING_DEBUG_PATH", str(debug_file))

    def fake_urlopen(req, timeout):  # noqa: ARG001
        return _mock_ollama_response("Tema")

    cfg = _ollama_cfg(prompt_variant="default")
    texts = ["arquivo um", "arquivo dois"]

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        name_cluster_ollama(texts, cfg)

    lines = debug_file.read_text(encoding="utf-8").strip().splitlines()
    record = json.loads(lines[0])
    assert record["variant"] == "default"
    assert record["anchor_terms"] is None
    assert record["system"] is None
    assert record["prompt"]  # default-variant prompt is still recorded
