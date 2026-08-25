# tests/test_sprint10_benchmark.py

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

class TestBenchmark:
    def test_benchmark_logic(self, tmp_path: Path) -> None:
        """
        Test that run_benchmark iterates through multiple configurations and returns a list of results.
        """
        root = tmp_path / "benchmark_subject"
        root.mkdir()
        (root / "file1.txt").write_text("content1")
        (root / "file2.txt").write_text("content2")

        with patch("dynamic_folding.core.benchmark.run_pipeline") as mock_run_pipeline:
            from dynamic_folding.contracts.run_result import RunResult
            from dynamic_folding.contracts.proposal import StructureProposal
            
            mock_proposal = MagicMock(spec=StructureProposal)
            mock_proposal.folders = ["Folder1"]
            mock_proposal.orphans = []
            mock_result = MagicMock(spec=RunResult)
            mock_result.proposal = mock_proposal
            mock_run_pipeline.return_value = mock_result

            try:
                from dynamic_folding.core.benchmark import run_benchmark
            except ImportError:
                pytest.fail("Module dynamic_folding.core.benchmark not found")

            results = run_benchmark(root)

            assert mock_run_pipeline.call_count > 1
            assert isinstance(results, list)
            assert len(results) > 0

            # Benchmark records structural facts only — quality grading (silhouette)
            # is no longer part of the grid (ADR 0035).
            for res in results:
                assert "cohesion_score" not in res
                assert "clusters" in res
                assert "outliers" in res
                assert "algorithm" in res
                assert "embedding" in res

    def test_benchmark_cli_command(self, tmp_path: Path) -> None:
        """
        Test that the CLI 'benchmark' command exists and calls run_benchmark.
        """
        root = tmp_path / "cli_test"
        root.mkdir()

        with patch("dynamic_folding.cli.run_benchmark") as mock_run_benchmark:
            from dynamic_folding.cli import main
            
            # Use main directly; SystemExit is raised by argparse if command not found
            try:
                main(["benchmark", str(root)])
            except SystemExit as e:
                if e.code != 0:
                    raise e
            
            mock_run_benchmark.assert_called_once_with(Path(str(root)))

    def test_benchmark_results_persistence(self, tmp_path: Path) -> None:
        """
        Test that benchmark results are persisted to a JSON file in a benchmark_results directory.
        """
        root = tmp_path / "persistence_test"
        root.mkdir()

        with patch("dynamic_folding.core.benchmark.run_pipeline") as mock_run_pipeline, \
             patch("pathlib.Path.mkdir") as mock_mkdir, \
             patch("builtins.open", mock_open()) as mock_file:
            
            from dynamic_folding.contracts.run_result import RunResult
            from dynamic_folding.contracts.proposal import StructureProposal
            
            mock_proposal = MagicMock(spec=StructureProposal)
            mock_proposal.folders = ["Folder1"]
            mock_proposal.orphans = []
            mock_result = MagicMock(spec=RunResult)
            mock_result.proposal = mock_proposal
            mock_run_pipeline.return_value = mock_result

            try:
                from dynamic_folding.core.benchmark import run_benchmark
            except ImportError:
                pytest.fail("Module dynamic_folding.core.benchmark not found")
            
            run_benchmark(root)

            mock_mkdir.assert_called()
            mock_file.assert_called()
            args, _ = mock_file.call_args
            assert "benchmark_results" in str(args[0])
            assert str(args[0]).endswith(".json")
