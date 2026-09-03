from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dynamic_folding import __version__
from dynamic_folding.core.pipeline import run_pipeline
from dynamic_folding.render.tree import render_tree
from dynamic_folding.core.pipeline import resolve_effective_config
from dynamic_folding.core.config import project_default_config_path
from dynamic_folding.core.analyze import run_analyze
from dynamic_folding.core.benchmark import run_benchmark
from dynamic_folding.core.characterize import run_characterize
from dynamic_folding.core.experiment import run_experiment
from dynamic_folding.core.setup_sbert import DEFAULT_MODEL_NAME, setup_sbert_model


def _resolve_cli_config_path(user_path: str | None) -> Path | None:
    """
    Pick the config file the CLI should pass to the pipeline.

    - If --config was given, use it verbatim.
    - Otherwise fall back to the project's config/default.toml (the user-facing
      preset describing the intended ML stack), if it exists.
    - If neither is available, return None — the pipeline will use the
      hardcoded zero-deps system defaults from get_system_defaults().
    """
    if user_path:
        return Path(user_path)
    project_default = project_default_config_path()
    return project_default if project_default.exists() else None


def _resolve_naming_debug_path(flag_on: bool) -> str | None:
    """Resolve the naming-debug log path for this run.

    Sugar around the env var `DYNAMIC_FOLDING_NAMING_DEBUG_PATH` (Phase D).
    When `--debug-naming` is passed and the env var is not already set, a
    timestamped path under CWD is generated and the env var is set so the
    Ollama namer picks it up. Pre-existing env var wins (explicit beats
    flag).

    Returns the resolved path string if this call set the env var, else
    None (either the flag was off, or the env var was already set).
    """
    if not flag_on:
        return None
    if os.environ.get("DYNAMIC_FOLDING_NAMING_DEBUG_PATH"):
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = str(Path.cwd() / f"naming_debug_{ts}.jsonl")
    os.environ["DYNAMIC_FOLDING_NAMING_DEBUG_PATH"] = path
    return path


def _summarize_config(cfg: dict) -> str:
    sc = cfg.get("scanner", {})
    emb = cfg.get("embedding", {})
    cl = cfg.get("clustering", {})
    nm = cfg.get("naming", {})

    emb_provider = str(emb.get("provider", ""))
    model_path = str(emb.get("model_path", ""))
    if model_path:
        # Keep paths readable in console output.
        if len(model_path) > 70:
            model_path = "..." + model_path[-67:]

    parts = [
        f"scanner={sc.get('provider','fs')} depth={sc.get('max_depth',2)} max_files={sc.get('max_files',200)}",
        f"embedding={emb_provider} device={emb.get('device','cpu')} normalize={emb.get('normalize', True)}",
        (f"model_path={model_path}" if model_path else None),
        f"clustering={cl.get('algorithm','kmeans')} top_k={cl.get('top_k',3)} sub_k={cl.get('sub_k',2)} seed={cl.get('random_state',0)}",
        f"naming={nm.get('provider','tfidf')} model={nm.get('model','')} base_url={nm.get('base_url','http://127.0.0.1:11434')}",
    ]
    return " | ".join([p for p in parts if p])


def _resolve_report_path(report_cfg: dict, root: Path) -> Path:
    from datetime import datetime

    raw = str(report_cfg.get("output_path", "__default__"))
    if raw == "__default__":
        from dynamic_folding.core.paths import default_reports_dir
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        reports_dir = default_reports_dir()
        reports_dir.mkdir(parents=True, exist_ok=True)
        return reports_dir / f"{ts}-report.html"
    p = Path(raw)
    return p if p.is_absolute() else (root / p).resolve()


def _emit_report(result, cfg: dict, root: Path) -> None:
    """Render the HTML report for *result* and optionally open it.

    Shared by the non-interactive `run` command and the TUI-launching paths
    (`tui`, no-args default, `run --interactive`). The caller decides *whether*
    to call this (e.g. only on acceptance in the TUI); this helper only honours
    the `report` config section. A report failure never propagates — per the
    Robust Fallbacks rule, it warns and the run still succeeds.
    """
    report_cfg = cfg.get("report", {})
    if not report_cfg.get("enabled", False):
        return
    from dynamic_folding.render.html import render_html

    report_path = _resolve_report_path(report_cfg, root)
    try:
        render_html(result, report_path, config=cfg)
        if sys.stderr.isatty():
            print(f"report: {report_path}", file=sys.stderr)
        if report_cfg.get("auto_open", False):
            import webbrowser

            webbrowser.open(report_path.as_uri())
    except Exception as exc:
        print(f"warning: HTML report failed — {exc}", file=sys.stderr)


def _launch_tui(
    cfg_path: Path | None,
    *,
    initial_root: Path | None = None,
    use_emojis: bool = True,
) -> bool:
    """Launch the unified TUI and, on acceptance, emit the HTML report.

    Returns whether the user accepted the proposal. Shared by the `tui`
    command, the no-args default, and `run --interactive` so all three produce
    the report consistently (the proposal is only worth a report once accepted).
    """
    from dynamic_folding.tui.webview_app import launch_webview

    result_tuple = launch_webview(
        cfg_path,
        initial_root=initial_root,
        use_emojis=use_emojis,
    )
    accepted = bool(result_tuple and result_tuple[0])
    result = result_tuple[1] if result_tuple else None
    if accepted and result is not None:
        cfg = resolve_effective_config(Path(result.root), config_path=cfg_path)
        _emit_report(result, cfg, Path(result.root))
    return accepted


def _require_directory(path_str: str, label: str = "path") -> Path:
    p = Path(path_str)
    if not p.exists():
        print(f"error: {label} does not exist: {p}", file=sys.stderr)
        raise SystemExit(1)
    if not p.is_dir():
        print(f"error: {label} is not a directory: {p}", file=sys.stderr)
        raise SystemExit(1)
    return p


class _RichProgress:
    def __init__(self) -> None:
        from rich.console import Console
        from rich.progress import (
            BarColumn,
            Progress,
            SpinnerColumn,
            TaskProgressColumn,
            TextColumn,
            TimeElapsedColumn,
            TimeRemainingColumn,
        )

        self._console = Console(stderr=True)
        self._progress = Progress(
            SpinnerColumn(style="cyan"),
            TextColumn("[bold]{task.fields[stage]}"),
            BarColumn(bar_width=None, style="grey37", complete_style="green"),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=self._console,
            transient=True,
        )
        self._task_id: int | None = None

    def __enter__(self) -> "_RichProgress":
        self._progress.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._progress.__exit__(exc_type, exc, tb)

    from contextlib import contextmanager
    from collections.abc import Iterator

    @contextmanager
    def stage(self, name: str, *, total: int | None = None):
        if total is None:
            total = 1
        self._task_id = self._progress.add_task("", total=total, stage=name)

        class _Stage:
            def __init__(self, outer: _RichProgress) -> None:
                self._outer = outer

            def advance(self, n: int = 1) -> None:
                if self._outer._task_id is not None:
                    self._outer._progress.advance(self._outer._task_id, n)

        st = _Stage(self)
        try:
            yield st
        finally:
            # Ensure completion for spinner stages.
            if self._task_id is not None:
                task = self._progress.tasks[self._task_id]
                if task.completed < task.total:
                    self._progress.update(self._task_id, completed=task.total)



def _check_sbert(emb_cfg: dict) -> tuple[bool, str]:
    """Verify the sentence-transformers lib is importable and model_path exists."""
    try:
        import sentence_transformers  # noqa: F401
    except Exception as e:
        return False, f"sentence-transformers not installed ({e}). `uv pip install -e .[sbert]`"

    model_path = str(emb_cfg.get("model_path", "")).strip()
    if not model_path:
        from dynamic_folding.core.pipeline import SBERT_MODEL_PATH_ENV
        return False, (
            f"model_path is empty. Run `dynamic-folding setup-sbert` to install one "
            f"automatically, or set ${SBERT_MODEL_PATH_ENV} / embedding.model_path manually."
        )

    p = Path(model_path).expanduser()
    if not p.exists() or not p.is_dir():
        return False, f"model_path does not exist or is not a directory: {p}"
    return True, f"model_path={p}"


def _check_ollama(naming_cfg: dict) -> tuple[bool, str]:
    """Verify the Ollama loopback endpoint is reachable and the model is pulled."""
    base_url = str(naming_cfg.get("base_url", "http://127.0.0.1:11434")).rstrip("/")
    model = str(naming_cfg.get("model", "")).strip()
    if not model:
        return False, "naming.model is empty"

    import json as _json
    import urllib.error
    import urllib.request

    try:
        with urllib.request.urlopen(f"{base_url}/api/tags", timeout=3) as resp:
            payload = _json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        return False, f"cannot reach {base_url} ({e.reason}). Start `ollama serve`?"
    except Exception as e:
        return False, f"unexpected error talking to {base_url}: {e}"

    available = {m.get("name", "").split(":")[0] for m in payload.get("models", [])}
    available |= {m.get("name", "") for m in payload.get("models", [])}
    if model not in available and model.split(":")[0] not in available:
        return False, f"model '{model}' not pulled on {base_url}. Try `ollama pull {model}`."
    return True, f"{base_url} reachable, model '{model}' present"


def _run_doctor(config_arg: str | None) -> int:
    """Resolve the effective config and report whether each provider can run."""
    from rich import print as rich_print
    from rich.table import Table
    from rich.console import Console

    cfg_path = _resolve_cli_config_path(config_arg)
    cfg = resolve_effective_config(Path(".").resolve(), config_path=cfg_path)

    rows: list[tuple[str, str, bool, str]] = []

    emb = cfg.get("embedding", {})
    emb_provider = str(emb.get("provider", "")).lower()
    if emb_provider == "sbert":
        ok, detail = _check_sbert(emb)
    else:
        ok, detail = True, f"provider={emb_provider} (no external check needed)"
    rows.append(("embedding", emb_provider, ok, detail))

    naming = cfg.get("naming", {})
    naming_provider = str(naming.get("provider", "")).lower()
    if naming_provider == "ollama":
        ok, detail = _check_ollama(naming)
    else:
        ok, detail = True, f"provider={naming_provider} (no external check needed)"
    rows.append(("naming", naming_provider, ok, detail))

    table = Table(title="dynamic-folding doctor", show_lines=False)
    table.add_column("Stage", style="bold")
    table.add_column("Provider")
    table.add_column("Status")
    table.add_column("Detail", overflow="fold")
    for stage, provider, ok, detail in rows:
        status = "[green]OK[/green]" if ok else "[red]FAIL[/red]"
        table.add_row(stage, provider, status, detail)

    Console().print(table)
    rich_print(f"\nConfig source: [cyan]{cfg_path or '(system defaults)'}[/cyan]")

    all_ok = all(ok for _, _, ok, _ in rows)
    if not all_ok:
        rich_print("[bold red]One or more providers are not ready. Fix the issues above before running experiments.[/bold red]")
        return 1
    rich_print("[bold green]All configured providers ready.[/bold green]")
    return 0


def main(argv: list[str] | None = None) -> int:
    # Windows-first: emit UTF-8 on stdout/stderr so accented folder names (PT-BR)
    # survive being redirected/piped to UTF-8 files (thesis evidence, logs). The
    # hasattr guard keeps this safe under pytest's captured streams.
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(prog="dynamic-folding")
    parser.add_argument(
        "--version",
        action="version",
        version=f"dynamic-folding {__version__}",
    )
    sub = parser.add_subparsers(dest="cmd", required=False)

    run_p = sub.add_parser("run", help="Scan directory and propose structure")
    run_p.add_argument("path", type=str, help="Directory path")
    run_p.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to a TOML config file (optional)",
    )
    run_p.add_argument(
        "--json",
        action="store_true",
        help="Also print proposal JSON (useful for future UIs)",
    )
    run_p.add_argument(
        "--print-config",
        action="store_true",
        help="Print effective config and exit",
    )
    run_p.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress UI",
    )
    run_p.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Enable interactive triage/confirmation",
    )
    run_p.add_argument(
        "--summary",
        action="store_true",
        help="Only show folder structure, hide individual files",
    )
    run_p.add_argument(
        "--debug-naming",
        action="store_true",
        help=(
            "Log each Ollama namer call (prompt, raw response, final name) "
            "to ./naming_debug_<timestamp>.jsonl in the current directory. "
            "Use to diagnose duplicate/odd cluster names. The env var "
            "DYNAMIC_FOLDING_NAMING_DEBUG_PATH overrides the default path."
        ),
    )

    tui_p = sub.add_parser("tui", help="Launch the unified TUI experience")
    tui_p.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to a TOML config file (optional). Defaults to config/default.toml.",
    )

    bench_p = sub.add_parser("benchmark", help="Run benchmark across all algorithm combinations")
    bench_p.add_argument("path", type=str, help="Directory path")

    char_p = sub.add_parser(
        "characterize",
        help="Empirical characterization (structure-finding, stability, performance)",
    )
    char_p.add_argument("path", type=str, help="Directory path")
    char_p.add_argument("--config", type=str, default=None, help="Path to a TOML config file")
    char_p.add_argument("--runs", type=int, default=5, help="Number of perturbed runs for stability")
    char_p.add_argument(
        "--perturbation",
        type=float,
        default=0.10,
        help="Fraction of files to drop per stability run (0.0-0.5)",
    )
    char_p.add_argument("--seed", type=int, default=0, help="Random seed")
    char_p.add_argument(
        "--output-dir",
        type=str,
        default="characterization_results",
        help="Directory to write timestamped JSON results",
    )

    sil_p = sub.add_parser(
        "silhouette",
        help="Measure the Silhouette score of the proposed top-level grouping",
    )
    sil_p.add_argument("path", type=str, help="Directory path")
    sil_p.add_argument("--config", type=str, default=None, help="Path to a TOML config file")
    sil_p.add_argument(
        "--json",
        type=str,
        default=None,
        help="Also write the score (with per-group breakdown) as JSON to this path",
    )
    sil_p.add_argument(
        "--csv",
        type=str,
        default=None,
        help="Also write the per-group breakdown as CSV to this path",
    )

    ext_p = sub.add_parser(
        "external-eval",
        help="Compare the proposed top-level grouping with human reference labels",
    )
    ext_p.add_argument("path", type=str, help="Directory path")
    ext_p.add_argument(
        "--labels",
        type=str,
        required=True,
        help="UTF-8, semicolon-separated two-column human-label CSV",
    )
    ext_p.add_argument("--config", type=str, default=None, help="Path to a TOML config file")
    ext_p.add_argument(
        "--json",
        type=str,
        default=None,
        help="Also write the external-evaluation result as JSON to this path",
    )
    ext_p.add_argument(
        "--csv",
        type=str,
        default=None,
        help="Also write the external-evaluation summary as CSV to this path",
    )

    cmp_p = sub.add_parser(
        "compare",
        help="Compare clustering algorithms (structural + per-algorithm silhouette) "
        "and a hyperparameter sensitivity cut",
    )
    cmp_p.add_argument("path", type=str, help="Directory path")
    cmp_p.add_argument("--config", type=str, default=None, help="Path to a TOML config file")
    cmp_p.add_argument(
        "--html",
        type=str,
        default=None,
        help="Also write a self-contained HTML report to this path",
    )
    cmp_p.add_argument(
        "--json",
        type=str,
        default=None,
        help="Also write the full comparison result as JSON to this path",
    )
    cmp_p.add_argument(
        "--csv",
        type=str,
        default=None,
        help="Also write one row per algorithm as CSV to this path",
    )

    cmpm_p = sub.add_parser(
        "compare-multi",
        help="Compare clustering algorithms across several corpora in one "
        "side-by-side report (aggregate-first; ADR 0045)",
    )
    cmpm_p.add_argument(
        "paths", type=str, nargs="*",
        help="Directory paths, in order (Corpus 1..N). Omit when using --from-json.",
    )
    cmpm_p.add_argument("--config", type=str, default=None, help="Path to a TOML config file")
    cmpm_p.add_argument(
        "--from-json",
        type=str,
        default=None,
        dest="from_json",
        help="Re-render from a saved multi-corpus JSON (skips the pipeline — seconds "
        "instead of a full SBERT run). Mutually exclusive with the positional paths.",
    )
    cmpm_p.add_argument(
        "--html",
        type=str,
        default=None,
        help="Also write a self-contained HTML report to this path",
    )
    cmpm_p.add_argument(
        "--json",
        type=str,
        default=None,
        help="Also write the full multi-corpus comparison result as JSON to this path",
    )
    cmpm_p.add_argument(
        "--csv",
        type=str,
        default=None,
        help="Also write one row per (corpus, algorithm) as CSV to this path",
    )

    exp_p = sub.add_parser(
        "experiment",
        help="Run full Sprint 19 experimental matrix (spine + sensitivity + analysis) in one shot",
    )
    exp_p.add_argument(
        "datasets_dir",
        type=str,
        help="Parent directory; each immediate subdirectory is treated as one corpus",
    )
    exp_p.add_argument("--config", type=str, default=None, help="Path to a TOML config file")
    exp_p.add_argument(
        "--sensitivity-corpus",
        type=str,
        default=None,
        help="Basename of the corpus to use for sensitivity sub-study (default: smallest)",
    )
    exp_p.add_argument(
        "--perturbations",
        type=str,
        default="0.05,0.10,0.20",
        help="Comma-separated perturbation values for the experimental matrix",
    )
    exp_p.add_argument(
        "--spine-perturbation",
        type=float,
        default=0.10,
        help="Perturbation level for the spine pass (one run per corpus)",
    )
    exp_p.add_argument("--seed", type=int, default=0, help="Random seed")
    exp_p.add_argument(
        "--output-dir",
        type=str,
        default="characterization_results",
        help="Directory for characterize_*.json outputs",
    )
    exp_p.add_argument(
        "--analysis-output-dir",
        type=str,
        default="analysis_output",
        help="Directory for the Markdown report and figures",
    )
    exp_p.add_argument(
        "--no-analyze",
        action="store_true",
        help="Skip the analyze stage (just produce JSONs)",
    )

    ana_p = sub.add_parser(
        "analyze",
        help="Aggregate characterize_*.json results into a thesis-ready Markdown report",
    )
    ana_p.add_argument(
        "results_dir",
        nargs="?",
        default="characterization_results",
        help="Directory containing characterize_*.json files",
    )
    ana_p.add_argument(
        "--output-dir",
        type=str,
        default="analysis_output",
        help="Where to write report.md and PNG figures",
    )
    ana_p.add_argument(
        "--no-figures",
        action="store_true",
        help="Skip PNG figure generation (markdown only)",
    )

    doctor_p = sub.add_parser(
        "doctor",
        help="Check that the configured providers can actually load (env, models, services)",
    )
    doctor_p.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to a TOML config file (optional). Defaults to config/default.toml.",
    )

    setup_p = sub.add_parser(
        "setup-sbert",
        help="One-time download of an SBERT model into the local cache (offline thereafter)",
    )
    setup_p.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL_NAME,
        help=f"HuggingFace sentence-transformers model name (default: {DEFAULT_MODEL_NAME})",
    )
    setup_p.add_argument(
        "--target",
        type=str,
        default=None,
        help="Override the target directory (default: ~/.dynamic-folding/models/<model>/)",
    )
    setup_p.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip the confirmation prompt",
    )
    setup_p.add_argument(
        "--force",
        action="store_true",
        help="Redownload even if a model is already present at the target",
    )

    args = parser.parse_args(argv)

    if args.cmd is None:
        # No subcommand: launch the unified TUI as the default experience
        # (pick a folder → run the pipeline → open the HTML report on accept).
        cfg_path = _resolve_cli_config_path(None)
        accepted = _launch_tui(cfg_path)
        if accepted:
            from rich import print as rich_print
            rich_print("\n[bold green]Organization proposal accepted in TUI.[/bold green]")
        return 0

    if args.cmd == "tui":
        cfg_path = _resolve_cli_config_path(args.config)
        accepted = _launch_tui(cfg_path)
        if accepted:
            from rich import print as rich_print
            rich_print("\n[bold green]Organization proposal accepted in TUI.[/bold green]")
        return 0

    if args.cmd == "run":
        root = _require_directory(args.path, "path")
        cfg_path = _resolve_cli_config_path(args.config)

        resolved_debug = _resolve_naming_debug_path(getattr(args, "debug_naming", False))
        if resolved_debug:
            print(f"[naming-debug] logging to {resolved_debug}", file=sys.stderr)

        if args.print_config:
            cfg = resolve_effective_config(root, config_path=cfg_path)
            print(json.dumps(cfg, ensure_ascii=True, indent=2))
            return 0

        cfg = resolve_effective_config(root, config_path=cfg_path)
        use_emojis = cfg.get("ui", {}).get("use_emojis", True)

        if args.interactive:
            # Launch the Unified TUI starting at the Pipeline screen for this
            # specific path; the report is emitted on accept inside _launch_tui.
            accepted = _launch_tui(
                cfg_path,
                initial_root=root,
                use_emojis=use_emojis,
            )
            from rich import print as rich_print
            if accepted:
                rich_print("[bold green]Proposal confirmed in TUI.[/bold green]")
                return 0
            else:
                rich_print("[bold red]Proposal rejected or TUI closed.[/bold red]")
                return 1

        if cfg.get("embedding", {}).get("provider") == "sbert":
            ok, detail = _check_sbert(cfg["embedding"])
            if not ok:
                print(f"error: sbert not ready — {detail}", file=sys.stderr)
                raise SystemExit(1)

        if sys.stderr.isatty():
            print(f"dynamic-folding {__version__}", file=sys.stderr)
            print(_summarize_config(cfg), file=sys.stderr)
            print(f"config source: {cfg_path or '(system defaults)'}", file=sys.stderr)

        use_progress = (not args.no_progress) and sys.stderr.isatty()
        try:
            if use_progress:
                with _RichProgress() as prog:
                    result = run_pipeline(root, config_path=cfg_path, progress=prog)
            else:
                result = run_pipeline(root, config_path=cfg_path)
        except Exception as exc:
            print(f"error: pipeline failed — {exc}", file=sys.stderr)
            raise SystemExit(1)

        if args.json:
            print(json.dumps(result.to_dict(), ensure_ascii=True, indent=2))
        else:
            from rich import print as rich_print
            rich_print(render_tree(
                result.proposal,
                use_emojis=use_emojis,
                summary_only=args.summary,
            ))

        _emit_report(result, cfg, root)

        return 0

    if args.cmd == "benchmark":
        root = _require_directory(args.path, "path")
        run_benchmark(root)
        return 0

    if args.cmd == "characterize":
        char_root = _require_directory(args.path, "path")
        cfg_path = _resolve_cli_config_path(args.config)
        if sys.stderr.isatty():
            cfg = resolve_effective_config(char_root, config_path=cfg_path)
            print(f"dynamic-folding {__version__}", file=sys.stderr)
            print(_summarize_config(cfg), file=sys.stderr)
            print(f"config source: {cfg_path or '(system defaults)'}", file=sys.stderr)
        run_characterize(
            char_root,
            output_dir=Path(args.output_dir),
            config_path=cfg_path,
            runs=int(args.runs),
            perturbation=float(args.perturbation),
            seed=int(args.seed),
        )
        return 0

    if args.cmd == "silhouette":
        from dynamic_folding.evaluation.silhouette import silhouette_baseline_of_run

        sil_root = _require_directory(args.path, "path")
        cfg_path = _resolve_cli_config_path(args.config)
        if sys.stderr.isatty():
            print(f"dynamic-folding {__version__}", file=sys.stderr)
            print(f"config source: {cfg_path or '(system defaults)'}", file=sys.stderr)
        result = run_pipeline(sil_root, config_path=cfg_path)
        base = silhouette_baseline_of_run(result)
        sil = base.real
        if sil.score is None:
            print(
                f"Silhouette: n/a ({sil.reason}) — "
                f"{sil.n_groups} groups, {sil.n_outliers} in Outros"
            )
            print("(no baseline: need a defined silhouette first)")
        else:
            print(
                f"Silhouette: {sil.score:.3f}  "
                f"({sil.n_groups} groups, {sil.n_files_scored} files; "
                f"{sil.n_outliers} in Outros skipped)"
            )
            print(
                f"Random baseline: {base.baseline_mean:.3f} +/- {base.baseline_std:.3f} "
                f"over {base.n_permutations} shuffles  "
                f"(real {sil.score:.3f} is {base.gap:+.3f} above it)"
            )
            if sil.per_group:
                print("Per group (most to least coherent):")
                for g in sorted(sil.per_group, key=lambda x: x.score, reverse=True):
                    print(f"  {g.name:<28} {g.score:+.3f}  ({g.n_files} files)")
        if args.json:
            out = Path(args.json)
            out.write_text(json.dumps(base.to_dict(), ensure_ascii=True, indent=2))
            print(f"\nJSON: {out.resolve()}")
        if args.csv:
            from dynamic_folding.evaluation.csv_export import write_silhouette_csv

            out = Path(args.csv)
            write_silhouette_csv(base, out)
            print(f"\nCSV: {out.resolve()}")
        return 0

    if args.cmd == "external-eval":
        from dynamic_folding.evaluation.external import (
            ExternalEvaluationError,
            evaluate_external,
            format_external_evaluation,
            read_reference_labels,
        )

        ext_root = _require_directory(args.path, "path")
        cfg_path = _resolve_cli_config_path(args.config)
        cfg = resolve_effective_config(ext_root, config_path=cfg_path)
        if cfg.get("embedding", {}).get("provider") == "sbert":
            ok, detail = _check_sbert(cfg["embedding"])
            if not ok:
                print(f"error: sbert not ready — {detail}", file=sys.stderr)
                return 1
        try:
            labels = read_reference_labels(args.labels)
            run = run_pipeline(ext_root, config_path=cfg_path)
            evaluation = evaluate_external(run, labels)
        except ExternalEvaluationError as exc:
            print(f"error: external evaluation failed — {exc}", file=sys.stderr)
            return 2

        print(format_external_evaluation(evaluation))
        export = {
            "external_evaluation": evaluation.to_dict(),
            "effective_config": cfg,
            "config_source": str(cfg_path) if cfg_path else "system defaults",
            "version": __version__,
        }
        if args.json:
            out = Path(args.json)
            out.write_text(json.dumps(export, ensure_ascii=True, indent=2), encoding="utf-8")
            print(f"\nJSON: {out.resolve()}")
        if args.csv:
            from dynamic_folding.evaluation.csv_export import write_external_evaluation_csv

            out = Path(args.csv)
            write_external_evaluation_csv(evaluation, out)
            print(f"\nCSV: {out.resolve()}")
        return 0

    if args.cmd == "compare":
        from dynamic_folding.evaluation.comparison import (
            format_comparison_text,
            run_comparison,
        )

        cmp_root = _require_directory(args.path, "path")
        cfg_path = _resolve_cli_config_path(args.config)
        if sys.stderr.isatty():
            print(f"dynamic-folding {__version__}", file=sys.stderr)
            print(f"config source: {cfg_path or '(system defaults)'}", file=sys.stderr)
        res = run_comparison(cmp_root, config_path=cfg_path)
        print(format_comparison_text(res))
        if args.html:
            from dynamic_folding.evaluation.comparison_report import render_comparison_html

            out = Path(args.html)
            render_comparison_html(res, out)
            print(f"\nRelatório HTML: {out.resolve()}")
        if args.json:
            out = Path(args.json)
            out.write_text(json.dumps(res.to_dict(), ensure_ascii=True, indent=2))
            print(f"\nJSON: {out.resolve()}")
        if args.csv:
            from dynamic_folding.evaluation.csv_export import write_comparison_csv

            out = Path(args.csv)
            write_comparison_csv(res, out)
            print(f"\nCSV: {out.resolve()}")
        return 0

    if args.cmd == "compare-multi":
        from dynamic_folding.evaluation.multicorpus import (
            MultiCorpusComparison,
            run_multicorpus_comparison,
        )

        if args.from_json:
            if args.paths:
                print("erro: use OU diretórios OU --from-json, não ambos.", file=sys.stderr)
                return 2
            data = json.loads(Path(args.from_json).read_text(encoding="utf-8"))
            multi = MultiCorpusComparison.from_dict(data)
            print(f"re-render a partir de {args.from_json} (sem re-rodar o pipeline)")
        else:
            if not args.paths:
                print(
                    "erro: forneça os diretórios (Corpus 1..N) ou --from-json <json>.",
                    file=sys.stderr,
                )
                return 2
            from dynamic_folding.evaluation.comparison import format_comparison_text

            real_paths = [_require_directory(p, "paths") for p in args.paths]
            cfg_path = _resolve_cli_config_path(args.config)
            if sys.stderr.isatty():
                print(f"dynamic-folding {__version__}", file=sys.stderr)
                print(f"config source: {cfg_path or '(system defaults)'}", file=sys.stderr)
            multi = run_multicorpus_comparison(real_paths, config_path=cfg_path)
            # The real path is only ever printed to stdout, zipped by argument order —
            # never passed into the HTML/JSON, which only see the anonymized label.
            for (label, res), real_path in zip(multi.items, real_paths):
                print(f"=== {label} ({real_path}) ===")
                print(format_comparison_text(res))
                print()
        if args.html:
            from dynamic_folding.evaluation.multicorpus_report import render_multicorpus_html

            out = Path(args.html)
            render_multicorpus_html(multi, out)
            print(f"\nRelatório HTML: {out.resolve()}")
        if args.json:
            out = Path(args.json)
            out.write_text(json.dumps(multi.to_dict(), ensure_ascii=True, indent=2))
            print(f"\nJSON: {out.resolve()}")
        if args.csv:
            print(
                "aviso: exportação CSV multi-corpus ainda não suportada; use --json",
                file=sys.stderr,
            )
        return 0

    if args.cmd == "experiment":
        exp_root = _require_directory(args.datasets_dir, "datasets_dir")
        perts = [float(x) for x in args.perturbations.split(",") if x.strip()]
        cfg_path = _resolve_cli_config_path(args.config)
        if sys.stderr.isatty():
            print(f"dynamic-folding {__version__}", file=sys.stderr)
            print(f"config source: {cfg_path or '(system defaults)'}", file=sys.stderr)
        summary = run_experiment(
            exp_root,
            config_path=cfg_path,
            sensitivity_corpus=args.sensitivity_corpus,
            perturbations=perts,
            spine_perturbation=float(args.spine_perturbation),
            seed=int(args.seed),
            output_dir=Path(args.output_dir),
            analysis_output_dir=Path(args.analysis_output_dir),
            run_analysis=not args.no_analyze,
        )
        from rich import print as rich_print
        rich_print("\n[bold]Experiment summary[/bold]")
        rich_print(f"  corpora discovered: {summary['corpora_discovered']}")
        rich_print(f"  sensitivity corpus: [cyan]{summary['sensitivity_corpus']}[/cyan]")
        rich_print(f"  spine runs: {len(summary['spine_runs'])}")
        rich_print(f"  sensitivity runs: {len(summary['sensitivity_runs'])}")
        rich_print(f"  failures: {len(summary['failures'])}")
        if summary["report_path"]:
            rich_print(f"  report: [cyan]{summary['report_path']}[/cyan]")
        return 1 if summary["failures"] else 0

    if args.cmd == "analyze":
        report = run_analyze(
            Path(args.results_dir),
            output_dir=Path(args.output_dir),
            skip_figures=bool(args.no_figures),
        )
        print(f"wrote {report}")
        return 0

    if args.cmd == "setup-sbert":
        target = Path(args.target) if args.target else None
        setup_sbert_model(
            args.model,
            target=target,
            assume_yes=bool(args.yes),
            force=bool(args.force),
        )
        return 0

    if args.cmd == "doctor":
        return _run_doctor(args.config)

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
