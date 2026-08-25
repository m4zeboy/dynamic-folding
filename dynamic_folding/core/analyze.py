"""Sprint 19 — Step 6: turn characterize JSONs into thesis-ready artifacts.

Reads `characterization_results/*.json` and writes:
- `report.md` — spine table (one row per corpus) and (when applicable)
   a sensitivity table (multiple perturbation levels for one corpus).
- PNG figures (if matplotlib is installed; skipped silently otherwise).

See ADR 0018, SPEC Sprint 19, and `docs/learning/02-experimental-scope.md`
for the experimental design this script reads.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def load_results(results_dir: Path) -> list[dict[str, Any]]:
    """Load all `characterize_*.json` files in the directory, sorted by name."""
    results: list[dict[str, Any]] = []
    for path in sorted(results_dir.glob("characterize_*.json")):
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        data["_source_file"] = path.name
        results.append(data)
    return results


def group_by_corpus(results: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group runs by their corpus root path."""
    by_corpus: dict[str, list[dict[str, Any]]] = {}
    for r in results:
        by_corpus.setdefault(r["root"], []).append(r)
    return by_corpus


def _total_time(timings: dict[str, float]) -> float:
    return sum(timings.values()) if timings else 0.0


def _fmt(v: Any, fmt: str = ".3f") -> str:
    if v is None:
        return "n/a"
    try:
        return format(float(v), fmt)
    except (TypeError, ValueError):
        return str(v)


def _canonical_run(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Pick one run per corpus for the spine table.

    Prefers perturbation == 0.10 (the SPEC default); falls back to the first
    run if that level is not present.
    """
    for r in runs:
        if r["stability"]["perturbation"] == 0.10:
            return r
    return runs[0]


def render_spine_table(by_corpus: dict[str, list[dict[str, Any]]]) -> str:
    header = (
        "| Corpus | n files | silhouette real | silhouette random | "
        "stability | total time (s) | peak mem (MB) |"
    )
    sep = (
        "|--------|---------|-----------------|"
        "-------------------|-----------|----------------|---------------|"
    )
    lines = ["# Spine experiment", "", header, sep]
    for root, runs in sorted(by_corpus.items()):
        canonical = _canonical_run(runs)
        name = Path(root).name
        n = canonical["corpus_metadata"].get("n_embedded")
        sr = canonical["structure"].get("silhouette_real")
        sx = canonical["structure"].get("silhouette_random")
        st = canonical["stability"].get("pair_co_occurrence")
        t = _total_time(canonical["performance"].get("timings", {}))
        mem = canonical["performance"].get("peak_memory_mb")
        lines.append(
            f"| {name} | {n} | {_fmt(sr)} | {_fmt(sx)} | {_fmt(st)} | "
            f"{_fmt(t, '.2f')} | {_fmt(mem, '.1f')} |"
        )
    return "\n".join(lines)


def render_sensitivity_tables(by_corpus: dict[str, list[dict[str, Any]]]) -> str | None:
    """Render one sensitivity table per corpus that has multiple perturbation levels."""
    sections: list[str] = []
    for root, runs in sorted(by_corpus.items()):
        perts = sorted({r["stability"]["perturbation"] for r in runs})
        if len(perts) < 2:
            continue
        name = Path(root).name
        sections.append(f"## Sensitivity: {name}")
        sections.append("")
        sections.append("| Perturbation | Stability score | Evaluable pairs |")
        sections.append("|--------------|-----------------|-----------------|")
        for p in perts:
            run = next(r for r in runs if r["stability"]["perturbation"] == p)
            stab = run["stability"]["pair_co_occurrence"]
            ep = run["stability"].get("evaluable_pairs")
            sections.append(f"| {_fmt(p, '.2f')} | {_fmt(stab)} | {ep} |")
        sections.append("")
    if not sections:
        return None
    return "# Sensitivity sub-study\n\n" + "\n".join(sections)


def render_figures(
    by_corpus: dict[str, list[dict[str, Any]]], out_dir: Path
) -> list[Path]:
    """Generate PNG figures. Returns paths created. Empty list if matplotlib missing."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return []

    paths: list[Path] = []

    spine = []
    for root, runs in sorted(by_corpus.items()):
        c = _canonical_run(runs)
        spine.append(
            (
                Path(root).name,
                c["structure"].get("silhouette_real") or 0.0,
                c["structure"].get("silhouette_random") or 0.0,
            )
        )

    if spine:
        names = [s[0] for s in spine]
        reals = [s[1] for s in spine]
        rands = [s[2] for s in spine]
        x = list(range(len(names)))
        width = 0.35
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.bar([i - width / 2 for i in x], reals, width, label="real")
        ax.bar([i + width / 2 for i in x], rands, width, label="random")
        ax.set_xticks(x)
        ax.set_xticklabels(names, rotation=15, ha="right")
        ax.set_ylabel("silhouette score")
        ax.set_title("Structure-finding: real vs random clusterer")
        ax.axhline(0, linewidth=0.5, color="gray")
        ax.legend()
        plt.tight_layout()
        p = out_dir / "spine_silhouette.png"
        plt.savefig(p, dpi=150)
        plt.close(fig)
        paths.append(p)

    for root, runs in sorted(by_corpus.items()):
        perts = sorted({r["stability"]["perturbation"] for r in runs})
        if len(perts) < 2:
            continue
        name = Path(root).name
        xs, ys = [], []
        for pert in perts:
            run = next(r for r in runs if r["stability"]["perturbation"] == pert)
            xs.append(pert)
            ys.append(run["stability"]["pair_co_occurrence"])
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot(xs, ys, marker="o")
        ax.set_xlabel("perturbation")
        ax.set_ylabel("stability score")
        ax.set_ylim(0, 1.05)
        ax.set_title(f"Sensitivity: {name}")
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        p = out_dir / f"sensitivity_{name}.png"
        plt.savefig(p, dpi=150)
        plt.close(fig)
        paths.append(p)

    return paths


def run_analyze(
    results_dir: Path,
    *,
    output_dir: Path = Path("analysis_output"),
    skip_figures: bool = False,
) -> Path:
    """End-to-end: load results, write report.md (and PNGs), return report path."""
    results_dir = Path(results_dir)
    if not results_dir.exists():
        raise FileNotFoundError(f"results directory does not exist: {results_dir}")
    results = load_results(results_dir)
    if not results:
        raise ValueError(f"no characterize_*.json found in {results_dir}")

    by_corpus = group_by_corpus(results)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    spine_md = render_spine_table(by_corpus)
    sensitivity_md = render_sensitivity_tables(by_corpus)

    md_chunks = [spine_md, ""]
    if sensitivity_md:
        md_chunks.extend([sensitivity_md, ""])

    report_path = output_dir / "report.md"
    report_path.write_text("\n".join(md_chunks), encoding="utf-8")

    if not skip_figures:
        figs = render_figures(by_corpus, output_dir)
        if not figs:
            print(
                "matplotlib not installed; figures skipped. "
                "Install with `uv pip install matplotlib` to enable.",
                file=sys.stderr,
            )

    return report_path
