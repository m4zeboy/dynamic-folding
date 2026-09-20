from __future__ import annotations

import json
from pathlib import Path


def _normalize_run_result(d: dict) -> dict:
    # Make golden stable across OS/path ordering.
    files = sorted([f["rel_path"] for f in d.get("files", []) if not f.get("is_dir")], key=str.casefold)

    prop = d["proposal"]
    
    def normalize_nodes(nodes: list[dict]):
        res = []
        for n in nodes:
            res.append({
                "files": sorted(n.get("files", []), key=str.casefold),
                "subfolders": normalize_nodes(n.get("subfolders", []))
            })
        # Sort groups by their file content for stability
        return sorted(res, key=lambda x: "|".join(x["files"]).casefold())

    groups = normalize_nodes(prop.get("folders", []))

    out = {
        "contracts_version": d["contracts_version"],
        "files": files,
        "proposal": {
            "groups": groups,
            "orphans": sorted(prop.get("orphans", []), key=str.casefold),
        },
    }
    return out


def test_cli_json_golden(tmp_path: Path) -> None:
    # Build a deterministic fixture at runtime (avoids committing binary files).
    root = tmp_path / "golden1"
    root.mkdir(parents=True, exist_ok=True)

    (root / "invoice_2023_jan.pdf").write_bytes(b"x")
    (root / "invoice_2023_feb.pdf").write_bytes(b"x")
    (root / "photo_trip_paris_01.jpg").write_bytes(b"x")
    (root / "code_project_alpha.py").write_bytes(b"x")

    from dynamic_folding.core.pipeline import run_pipeline

    d = run_pipeline(root).to_dict()
    got = _normalize_run_result(d)

    golden_path = Path(__file__).resolve().parent / "golden" / "cli_golden1.json"
    expected = json.loads(golden_path.read_text(encoding="utf-8"))
    assert got == expected
