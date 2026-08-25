"""Sprint 19 — Step 6c: SBERT setup + auto-discovery tests.

Verifies:
- The default models dir helper picks the right platform path.
- The pipeline's `resolve_effective_config` follows the documented
  resolution order: explicit config > env var > auto-discovery.
- The `setup_sbert_model` function handles idempotency, user abort,
  and confirmation correctly without actually hitting the network.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest


def test_default_sbert_models_dir_uses_localappdata(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    from dynamic_folding.core.paths import default_sbert_models_dir

    assert default_sbert_models_dir() == (tmp_path / "DynamicFolding" / "models").resolve()


def test_default_sbert_models_dir_falls_back_to_home(monkeypatch) -> None:
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    from dynamic_folding.core.paths import default_sbert_models_dir

    assert default_sbert_models_dir() == (Path.home() / ".dynamic-folding" / "models").resolve()


def test_pipeline_auto_discovers_single_sbert_model(monkeypatch, tmp_path: Path) -> None:
    from dynamic_folding.core import paths, pipeline

    fake_models_dir = tmp_path / "models"
    fake_models_dir.mkdir()
    model_dir = fake_models_dir / "my-only-model"
    model_dir.mkdir()
    (model_dir / "config.json").write_text("{}")

    monkeypatch.setattr(paths, "default_sbert_models_dir", lambda: fake_models_dir)
    monkeypatch.delenv("DYNAMIC_FOLDING_SBERT_MODEL_PATH", raising=False)

    cfg_path = tmp_path / "sbert.toml"
    cfg_path.write_text('[embedding]\nprovider = "sbert"\n', encoding="utf-8")

    cfg = pipeline.resolve_effective_config(tmp_path, config_path=cfg_path)
    assert cfg["embedding"]["model_path"] == str(model_dir)


def test_pipeline_does_not_auto_discover_when_multiple_models(
    monkeypatch, tmp_path: Path
) -> None:
    from dynamic_folding.core import paths, pipeline

    fake_models_dir = tmp_path / "models"
    fake_models_dir.mkdir()
    (fake_models_dir / "model-a").mkdir()
    (fake_models_dir / "model-b").mkdir()

    monkeypatch.setattr(paths, "default_sbert_models_dir", lambda: fake_models_dir)
    monkeypatch.delenv("DYNAMIC_FOLDING_SBERT_MODEL_PATH", raising=False)

    cfg_path = tmp_path / "sbert.toml"
    cfg_path.write_text('[embedding]\nprovider = "sbert"\n', encoding="utf-8")

    cfg = pipeline.resolve_effective_config(tmp_path, config_path=cfg_path)
    assert not cfg["embedding"].get("model_path"), (
        "auto-discovery should not pick a model when multiple are present"
    )


def test_pipeline_env_var_overrides_auto_discover(monkeypatch, tmp_path: Path) -> None:
    from dynamic_folding.core import paths, pipeline

    fake_models_dir = tmp_path / "models"
    fake_models_dir.mkdir()
    (fake_models_dir / "auto-model").mkdir()
    explicit = tmp_path / "explicit-model"
    explicit.mkdir()

    monkeypatch.setattr(paths, "default_sbert_models_dir", lambda: fake_models_dir)
    monkeypatch.setenv("DYNAMIC_FOLDING_SBERT_MODEL_PATH", str(explicit))

    cfg_path = tmp_path / "sbert.toml"
    cfg_path.write_text('[embedding]\nprovider = "sbert"\n', encoding="utf-8")

    cfg = pipeline.resolve_effective_config(tmp_path, config_path=cfg_path)
    assert cfg["embedding"]["model_path"] == str(explicit)


def test_pipeline_explicit_config_path_overrides_everything(
    monkeypatch, tmp_path: Path
) -> None:
    from dynamic_folding.core import paths, pipeline

    fake_models_dir = tmp_path / "models"
    fake_models_dir.mkdir()
    (fake_models_dir / "auto-model").mkdir()
    env_model = tmp_path / "env-model"
    env_model.mkdir()
    explicit = tmp_path / "explicit-model"
    explicit.mkdir()

    monkeypatch.setattr(paths, "default_sbert_models_dir", lambda: fake_models_dir)
    monkeypatch.setenv("DYNAMIC_FOLDING_SBERT_MODEL_PATH", str(env_model))

    cfg_path = tmp_path / "sbert.toml"
    cfg_path.write_text(
        f'[embedding]\nprovider = "sbert"\nmodel_path = "{explicit.as_posix()}"\n',
        encoding="utf-8",
    )

    cfg = pipeline.resolve_effective_config(tmp_path, config_path=cfg_path)
    assert cfg["embedding"]["model_path"] == str(explicit) or cfg["embedding"][
        "model_path"
    ] == explicit.as_posix()


def test_setup_sbert_skips_when_model_already_present(tmp_path: Path, capsys) -> None:
    target = tmp_path / "my-model"
    target.mkdir()
    (target / "config.json").write_text("{}")

    from dynamic_folding.core.setup_sbert import setup_sbert_model

    result = setup_sbert_model("anything", target=target, assume_yes=True)
    assert result == target.resolve()
    captured = capsys.readouterr()
    assert "already present" in captured.err.lower()


def test_setup_sbert_aborts_when_user_says_no(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "new-model"
    fake_st = MagicMock()
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_st)
    monkeypatch.setattr("builtins.input", lambda *a, **kw: "n")

    from dynamic_folding.core.setup_sbert import setup_sbert_model

    with pytest.raises(SystemExit):
        setup_sbert_model("anything", target=target, assume_yes=False)


def test_setup_sbert_calls_save_when_user_confirms(
    monkeypatch, tmp_path: Path
) -> None:
    target = tmp_path / "new-model"
    fake_model = MagicMock()
    fake_st = MagicMock()
    fake_st.SentenceTransformer.return_value = fake_model
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_st)

    from dynamic_folding.core.setup_sbert import setup_sbert_model

    result = setup_sbert_model("any-model", target=target, assume_yes=True)
    assert fake_st.SentenceTransformer.called
    assert fake_model.save.called
    assert result == target.resolve()


def test_setup_sbert_force_redownloads_when_present(
    monkeypatch, tmp_path: Path
) -> None:
    target = tmp_path / "existing-model"
    target.mkdir()
    (target / "old.bin").write_text("stale")

    fake_model = MagicMock()
    fake_st = MagicMock()
    fake_st.SentenceTransformer.return_value = fake_model
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_st)

    from dynamic_folding.core.setup_sbert import setup_sbert_model

    setup_sbert_model("any-model", target=target, assume_yes=True, force=True)
    assert fake_model.save.called


def test_setup_sbert_raises_friendly_error_when_package_missing(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setitem(sys.modules, "sentence_transformers", None)

    from dynamic_folding.core.setup_sbert import setup_sbert_model

    with pytest.raises(SystemExit, match="sentence-transformers not installed"):
        setup_sbert_model("any-model", target=tmp_path / "x", assume_yes=True)
