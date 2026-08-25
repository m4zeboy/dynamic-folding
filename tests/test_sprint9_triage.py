"""Live CLI render + interactive-launch tests.

(The former `confirm_proposal`/`TriageApp` tests were removed in T3 along with the
dead Textual stack — see ADR 0033. The interactive flow is now the pywebview UI.)
"""
from unittest.mock import patch

from dynamic_folding.contracts.proposal import StructureProposal
from dynamic_folding.cli import main


def test_tree_render_is_plain_without_confidence_signal():
    """
    Render carries no quality signal: no colour bands, no "verificar" label, no
    numeric score. Folder lines show only the name and file count (ADR 0035).
    """
    from dynamic_folding.render.tree import render_tree
    from dynamic_folding.contracts.proposal import FolderNode
    p = StructureProposal(
        root="C:/test",
        folders=[
            FolderNode(name="Good", files=["a.txt"]),
            FolderNode(name="Bad", files=["b.txt"]),
        ],
        orphans=[],
        notes=[],
    )
    output = render_tree(p, use_emojis=True)
    assert "📁 Good/ (1 arquivo)" in output
    assert "📁 Bad/ (1 arquivo)" in output
    # No quality-signal artefacts remain.
    assert "[green]" not in output and "[red]" not in output and "[yellow]" not in output
    assert "verificar" not in output
    assert "score:" not in output


def test_cli_interactive_flag():
    """
    Test the CLI entry point to ensure that if --interactive is passed,
    it attempts to launch the pywebview UI.
    """
    with patch("dynamic_folding.cli.resolve_effective_config") as mock_cfg:
        mock_cfg.return_value = {"ui": {"use_emojis": True}}

        with patch("dynamic_folding.tui.webview_app.launch_webview", return_value=(True, None)) as mock_launch:
            with patch("rich.print"):
                exit_code = main(["run", ".", "--interactive"])
                assert exit_code == 0
                mock_launch.assert_called_once()
