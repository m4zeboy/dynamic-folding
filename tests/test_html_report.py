from __future__ import annotations

from pathlib import Path

from dynamic_folding.core.pipeline import run_pipeline
from dynamic_folding.render.html import render_html


def test_html_report_created(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("alpha beta gamma")
    (tmp_path / "report.pdf").write_bytes(b"")
    (tmp_path / "photo.jpg").write_bytes(b"")

    result = run_pipeline(tmp_path)
    report_path = tmp_path / "report.html"
    render_html(result, report_path)

    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "dynamic-folding" in content
    assert "df-data" in content
    assert "Proposta de organização" in content
    assert "Detalhes técnicos" in content


def test_html_report_empty_dir(tmp_path: Path) -> None:
    result = run_pipeline(tmp_path)
    report_path = tmp_path / "report.html"
    render_html(result, report_path)

    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "Nenhuma pasta proposta" in content


def test_html_report_is_self_contained(tmp_path: Path) -> None:
    result = run_pipeline(tmp_path)
    report_path = tmp_path / "report.html"
    render_html(result, report_path)

    content = report_path.read_text(encoding="utf-8")
    # No external resource references
    assert "http://" not in content
    assert "https://" not in content
    assert 'src="' not in content
    assert 'href="' not in content
