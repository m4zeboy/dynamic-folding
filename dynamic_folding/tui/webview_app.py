from __future__ import annotations

import json
import os
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from dynamic_folding.contracts.run_result import RunResult
from dynamic_folding.core.pipeline import run_pipeline


def _quiet_ml_libraries() -> None:
    """Silence HuggingFace/transformers progress bars and chatter in GUI mode.

    The webview is the sole progress surface; library output to the host
    terminal is noise. Set via env so it applies even before those libs import,
    and stays offline-safe (no network, no behavior change)."""
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
    os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


class _WebProgress:
    """Progress adapter that pushes stage events to the JS bridge via evaluate_js."""

    def __init__(self, window: Any) -> None:
        self._window = window

    def _js(self, code: str) -> None:
        try:
            self._window.evaluate_js(code)
        except Exception:
            pass  # window may have been destroyed

    @contextmanager
    def stage(self, name: str, *, total: int | None = None) -> Iterator[Any]:
        self._js(f"window._df && window._df.onStageStart({json.dumps(name)})")

        class _Stage:
            def advance(self, n: int = 1) -> None:
                pass

        try:
            yield _Stage()
        finally:
            self._js(f"window._df && window._df.onStageEnd({json.dumps(name)})")


class DFWebApi:
    """Python API class exposed to the webview JS context as window.pywebview.api."""

    def __init__(
        self,
        config_path: Path | None,
        use_emojis: bool,
        initial_root: Path | None,
    ) -> None:
        self._config_path = config_path
        self._use_emojis = use_emojis
        self._initial_root = initial_root
        self._result: tuple[bool, RunResult | None] = (False, None)
        self._run_result: RunResult | None = None
        self._window: Any = None
        self._running = False

    def set_window(self, window: Any) -> None:
        self._window = window

    # ── Called by JS (window.pywebview.api.*) ─────────────────────────────────

    def get_home_path(self) -> str:
        return str(Path.home())

    def get_initial_root(self) -> str | None:
        return str(self._initial_root) if self._initial_root else None

    def list_directory(self, path: str) -> list[dict]:
        """Return immediate children of *path*, dirs first, dotfiles excluded."""
        p = Path(path)
        items: list[dict] = []
        try:
            entries = sorted(
                p.iterdir(),
                key=lambda x: (not x.is_dir(), x.name.lower()),
            )
            for entry in entries:
                if entry.name.startswith("."):
                    continue
                is_dir = entry.is_dir()
                has_children = False
                if is_dir:
                    try:
                        has_children = any(
                            not c.name.startswith(".")
                            for c in entry.iterdir()
                            if c.is_dir()
                        )
                    except (PermissionError, OSError):
                        pass
                items.append({
                    "name": entry.name,
                    "path": str(entry),
                    "type": "folder" if is_dir else "file",
                    "hasChildren": has_children,
                })
        except (PermissionError, OSError):
            pass
        return items

    def start_pipeline(self, path: str) -> None:
        """Kick off the pipeline in a daemon thread; results stream back via _df callbacks."""
        if self._running:
            return
        self._running = True
        t = threading.Thread(
            target=self._run_pipeline,
            args=(Path(path),),
            daemon=True,
        )
        t.start()

    def accept(self) -> None:
        """User accepted the proposal — record result and close the window."""
        self._result = (True, self._run_result)
        if self._window:
            self._window.destroy()

    def cancel(self) -> None:
        """User cancelled — keep result (False, None) and close the window."""
        self._result = (False, None)
        if self._window:
            self._window.destroy()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _run_pipeline(self, root: Path) -> None:
        win = self._window

        def js(code: str) -> None:
            try:
                win.evaluate_js(code)
            except Exception:
                pass

        try:
            progress = _WebProgress(win)
            result = run_pipeline(
                root,
                config_path=self._config_path,
                overrides=None,
                progress=progress,
            )
            self._run_result = result
            proposal_json = json.dumps(result.proposal.to_dict())
            js(f"window._df && window._df.onPipelineDone({proposal_json})")
        except Exception as exc:
            msg = f"{type(exc).__name__}: {exc}"
            js(f"window._df && window._df.onPipelineError({json.dumps(msg)})")
        finally:
            self._running = False


def launch_webview(
    cfg_path: Path | None,
    *,
    initial_root: Path | None = None,
    use_emojis: bool = True,
) -> tuple[bool, RunResult | None]:
    """Open the V1 Sereno pywebview window and block until it closes.

    Returns ``(accepted, run_result)``. ``accepted`` is True only when the
    user explicitly clicks "Aplicar proposta".
    """
    _quiet_ml_libraries()
    try:
        import webview  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "pywebview is required for the GUI. "
            "Install it with: uv pip install -e .[tui]"
        ) from exc

    html_path = Path(__file__).parent / "web" / "index.html"
    if not html_path.exists():
        raise FileNotFoundError(
            f"Web UI files not found at {html_path}. "
            "Ensure dynamic_folding/tui/web/ is present in the installation."
        )

    api = DFWebApi(cfg_path, use_emojis, initial_root)
    window = webview.create_window(
        title="dynamic folding",
        url=html_path.as_uri(),
        js_api=api,
        width=900,
        height=640,
        resizable=True,
        min_size=(640, 480),
    )
    api.set_window(window)

    # Brand the window/taskbar icon (otherwise Windows shows the python.exe icon).
    # The WinForms backend uses this .ico for the window + taskbar; if the asset is
    # missing it safely falls back to the host-executable icon.
    start_kwargs: dict[str, Any] = {}
    icon_path = Path(__file__).parent / "assets" / "dynamic-folding.ico"
    if icon_path.is_file():
        start_kwargs["icon"] = str(icon_path)

    webview.start(**start_kwargs)
    return api._result
