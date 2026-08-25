from __future__ import annotations

import json as _json
from importlib.resources import files
from pathlib import Path

from dynamic_folding.contracts.run_result import RunResult


_SENTINEL = "__DF_DATA__"


def _load_template() -> str:
    return files("dynamic_folding.render").joinpath("report_template.html").read_text(encoding="utf-8")


def _count_files(result: RunResult) -> int:
    return sum(1 for fr in result.files if not fr.is_dir)


def _count_folders(folders: list) -> int:
    total = 0
    for f in folders:
        total += 1
        total += _count_folders(f.subfolders)
    return total


def _noise_file_count(folders: list, outliers_folder: str) -> int:
    """Count files inside the designated noise/outliers folder."""
    for f in folders:
        if f.name == outliers_folder:
            return len(f.files)
    return 0


def _build_data(result: RunResult, version: str, config: dict) -> dict:
    from datetime import datetime

    proposal = result.proposal
    outliers_folder = config.get("proposal", {}).get("outliers_folder", "Outros")

    # Exclude the noise folder from the "real" folder count.
    real_folders = [f for f in proposal.folders if f.name != outliers_folder]
    noise_count = _noise_file_count(proposal.folders, outliers_folder)

    nm = config.get("naming", {})
    naming_provider = str(nm.get("provider", "tfidf"))
    naming_model = str(nm.get("model", "")) if naming_provider == "ollama" else ""

    emb = config.get("embedding", {})
    cl = config.get("clustering", {})

    return {
        "version": version,
        "root": result.root,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "file_count": _count_files(result),
        "folder_count": _count_folders(real_folders),
        "noise_count": noise_count,
        "peak_memory_mb": round(result.peak_memory_mb, 1) if result.peak_memory_mb else None,
        "providers": {
            "embedding": str(emb.get("provider", "fake")),
            "naming": naming_provider,
            "naming_model": naming_model,
            "clustering": str(cl.get("algorithm", "kmeans")),
        },
        "timings": {k: round(v, 3) for k, v in result.timings.items()},
        "folders": [f.to_dict() for f in proposal.folders],
        "orphans": list(proposal.orphans),
        "notes": list(proposal.notes),
    }


def render_html(result: RunResult, output_path: Path, *, config: dict | None = None, version: str = "") -> None:
    """Write a self-contained HTML report for *result* to *output_path*."""
    from dynamic_folding import __version__ as _ver

    ver = version or _ver
    cfg = config or {}
    data = _build_data(result, ver, cfg)
    data_json = _json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    # Prevent </script> from closing the embedded data block prematurely.
    data_json = data_json.replace("</", "<\\/")
    html = _load_template().replace(_SENTINEL, data_json)
    output_path.write_text(html, encoding="utf-8")
