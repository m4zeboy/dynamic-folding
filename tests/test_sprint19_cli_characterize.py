"""Sprint 19: characterize CLI subcommand and orchestrator.

See ADR 0018 and SPEC Sprint 19. CONTRACTS.md defines CharacterizationResult.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest


def test_characterize_subcommand_exists(tmp_path: Path) -> None:
    """`dynamic-folding characterize <dir>` must be a registered subcommand."""
    root = tmp_path / "char_cli"
    root.mkdir()
    (root / "a.txt").write_text("a")

    with patch("dynamic_folding.cli.run_characterize") as mock_run:
        from dynamic_folding.cli import main

        try:
            main(["characterize", str(root)])
        except SystemExit as e:
            if e.code != 0:
                raise

        mock_run.assert_called_once()
        args, _ = mock_run.call_args
        assert args[0] == Path(str(root))


def test_characterization_result_dto_exists() -> None:
    try:
        from dynamic_folding.contracts.characterization import CharacterizationResult
    except ImportError:
        pytest.fail(
            "dynamic_folding.contracts.characterization.CharacterizationResult must exist"
        )

    assert hasattr(CharacterizationResult, "to_dict"), "CharacterizationResult must serialize"


def test_run_characterize_returns_result(tmp_path: Path) -> None:
    try:
        from dynamic_folding.core.characterize import run_characterize
    except ImportError:
        pytest.fail("dynamic_folding.core.characterize.run_characterize must exist")

    root = tmp_path / "char_run"
    root.mkdir()
    for i in range(8):
        (root / f"doc_{i}.txt").write_text(f"content {i}")

    result = run_characterize(root)
    d = result.to_dict()
    assert d["contracts_version"] == 2
    assert "structure" in d
    assert "stability" in d
    assert "performance" in d
    assert "corpus_metadata" in d
    assert "config" in d


def test_run_characterize_writes_json(tmp_path: Path) -> None:
    from dynamic_folding.core.characterize import run_characterize

    root = tmp_path / "char_persist"
    root.mkdir()
    (root / "a.txt").write_text("aa")
    (root / "b.txt").write_text("bb")
    (root / "c.txt").write_text("cc")

    out_dir = tmp_path / "out"
    run_characterize(root, output_dir=out_dir)
    files = list(out_dir.glob("characterize_*.json"))
    assert len(files) == 1, f"Expected one JSON output, got {len(files)}: {files}"

    payload = json.loads(files[0].read_text(encoding="utf-8"))
    assert payload["contracts_version"] == 2
    assert "structure" in payload
    assert "stability" in payload
    assert "performance" in payload


def test_run_characterize_deterministic(tmp_path: Path) -> None:
    from dynamic_folding.core.characterize import run_characterize

    root = tmp_path / "char_det"
    root.mkdir()
    for i in range(10):
        (root / f"x{i}.txt").write_text(f"x {i}")

    r1 = run_characterize(root, seed=11)
    r2 = run_characterize(root, seed=11)
    assert r1.stability.pair_co_occurrence == r2.stability.pair_co_occurrence
    assert r1.structure == r2.structure


def test_run_characterize_offline(tmp_path: Path) -> None:
    """Default characterize run must not call the network (uses fake embedder)."""
    from dynamic_folding.core.characterize import run_characterize

    root = tmp_path / "char_offline"
    root.mkdir()
    (root / "a.txt").write_text("a")
    (root / "b.txt").write_text("b")

    with patch("urllib.request.urlopen", side_effect=AssertionError("Network call!")):
        result = run_characterize(root)
        assert result is not None
        assert result.stability is not None
