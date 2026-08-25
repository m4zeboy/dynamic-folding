"""Tests for two wiring features:

1. `_emit_report` — the shared CLI helper that renders the HTML report and
   optionally opens it, reused by `run`, `tui`, and the no-args default.
2. No-args dispatch — `dynamic-folding` with no subcommand launches the webview
   and, on acceptance, emits the HTML report.

The webview is never actually opened here; `launch_webview` is monkeypatched
to return a canned `(accepted, run_result)` tuple so we test the CLI wiring
without starting a GUI window.
"""
from __future__ import annotations

from pathlib import Path

from dynamic_folding import cli
from dynamic_folding.core.pipeline import run_pipeline


def test_emit_report_writes_html(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("alpha beta gamma")
    result = run_pipeline(tmp_path)
    out = tmp_path / "report.html"
    cfg = {"report": {"enabled": True, "output_path": str(out), "auto_open": False}}

    cli._emit_report(result, cfg, tmp_path)

    assert out.exists()
    assert "dynamic-folding" in out.read_text(encoding="utf-8")


def test_emit_report_disabled_is_noop(tmp_path: Path) -> None:
    result = run_pipeline(tmp_path)
    out = tmp_path / "report.html"
    cfg = {"report": {"enabled": False, "output_path": str(out), "auto_open": False}}

    cli._emit_report(result, cfg, tmp_path)

    assert not out.exists()


def test_emit_report_auto_open(tmp_path: Path, monkeypatch) -> None:
    result = run_pipeline(tmp_path)
    out = tmp_path / "report.html"
    cfg = {"report": {"enabled": True, "output_path": str(out), "auto_open": True}}

    opened: list[str] = []
    monkeypatch.setattr("webbrowser.open", lambda uri: opened.append(uri))

    cli._emit_report(result, cfg, tmp_path)

    assert out.exists()
    assert len(opened) == 1


def test_no_args_launches_tui_and_emits_report(tmp_path: Path, monkeypatch) -> None:
    # Keep generated reports inside the temp dir, not the real LOCALAPPDATA.
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    fake_result = run_pipeline(tmp_path)

    def fake_launch(*args, **kwargs):
        return (True, fake_result)

    monkeypatch.setattr("dynamic_folding.tui.webview_app.launch_webview", fake_launch)

    opened: list[str] = []
    monkeypatch.setattr("webbrowser.open", lambda uri: opened.append(uri))

    rc = cli.main([])

    assert rc == 0
    # Default config has report.enabled=true and auto_open=true, so the
    # accepted no-args flow should have produced and opened a report.
    reports_dir = tmp_path / "DynamicFolding" / "reports"
    assert reports_dir.exists()
    assert any(reports_dir.glob("*-report.html"))
    assert len(opened) == 1


def test_no_args_rejected_emits_no_report(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    fake_result = run_pipeline(tmp_path)

    def fake_launch(*args, **kwargs):
        return (False, fake_result)

    monkeypatch.setattr("dynamic_folding.tui.webview_app.launch_webview", fake_launch)

    opened: list[str] = []
    monkeypatch.setattr("webbrowser.open", lambda uri: opened.append(uri))

    rc = cli.main([])

    # The no-args TUI is the default experience, not a gate: it returns 0 even
    # when the user rejects. Rejection just means no report is emitted.
    assert rc == 0
    reports_dir = tmp_path / "DynamicFolding" / "reports"
    assert not reports_dir.exists()
    assert opened == []
