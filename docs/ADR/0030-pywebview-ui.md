# ADR 0030: Replace Textual TUI with pywebview (V1 Sereno)

## Status
Accepted

> Note (ADR 0031): the in-browser Babel transpile described below was later replaced — `app.jsx` is precompiled to `app.js` and `babel.min.js` is no longer loaded at runtime.

## Context

ADR 0029 introduced a Textual-based redesign of the TUI following the V1 Sereno design handoff. During implementation it became clear that Textual cannot reproduce the design at high fidelity: custom proportional fonts (DM Sans), border radius on cards and buttons, box shadows, smooth CSS transitions, and pixel-level spacing are all impossible in a character-grid terminal. The design was built as a React/HTML prototype and belongs in a real browser engine.

pywebview opens a native OS window backed by the system's browser engine (EdgeWebView2 on Windows 10/11, WebKit on macOS/Linux) and exposes a bidirectional Python↔JS bridge. This lets the existing React prototype run essentially unchanged, with mock data replaced by real API calls.

## Decision

Replace the `DynamicFoldingApp` (Textual) flow with a `launch_webview()` function that:

1. Creates a pywebview window loading `dynamic_folding/tui/web/index.html`
2. Exposes a `DFWebApi` Python class as `window.pywebview.api` in JS
3. Blocks via `webview.start()` until the window is closed
4. Returns `(accepted: bool, RunResult | None)`

### JS→Python API (`window.pywebview.api`)

| Method | Description |
|--------|-------------|
| `get_home_path()` | Returns `str(Path.home())` — tree root on launch |
| `get_initial_root()` | Returns `initial_root` if pre-seeded via `run --interactive`, else `None` |
| `list_directory(path)` | Immediate children sorted dirs-first, dotfiles excluded: `[{name, path, type, hasChildren}]` |
| `start_pipeline(path)` | Starts the pipeline in a daemon thread; progress streamed back via JS callbacks |
| `accept()` | Sets result `(True, run_result)` and calls `window.destroy()` |
| `cancel()` | Keeps result `(False, None)` and calls `window.destroy()` |

### Python→JS callbacks (`window._df.*`)

Called from the worker thread via `window.evaluate_js(...)`. The JS bridge object is registered before any pipeline starts.

| Callback | Payload |
|----------|---------|
| `onStageStart(name)` | Stage name string (e.g. `"scan"`) |
| `onStageEnd(name)` | Stage name string |
| `onPipelineDone(proposalObj)` | `StructureProposal.to_dict()` deserialized JS object |
| `onPipelineError(msg)` | Error summary string |

### Frontend

`dynamic_folding/tui/web/` — self-contained, no build step required:

- `index.html` — HTML shell loading vendored scripts
- `app.jsx` — Full V1 Sereno React app (Babel-compiled in-browser)
- `vendor/react.development.js` — React 18.3.1 (vendored; no CDN at runtime)
- `vendor/react-dom.development.js` — ReactDOM 18.3.1 (vendored)
- `vendor/babel.min.js` — Babel standalone 7.29.0 (vendored)

The UI uses only local/system fonts (`DM Sans` / `DM Mono` when already installed, otherwise Segoe UI / Consolas) so the webview remains offline-safe and performs no font CDN requests.

### "Recomeçar" behavior

Clicking "Recomeçar" resets React state (`screen → 'select'`, clears stages/proposal/selected path) **without closing the window**. The user can select a new folder and run again in the same session.

### Backward compatibility

- `_launch_tui()` in `cli.py` now calls `launch_webview()` instead of `DynamicFoldingApp`. The function signature, return value (`bool`), and report-emission logic are unchanged.
- `DynamicFoldingApp` (Textual) remains in `tui/app.py` but is no longer called by the CLI.
- `TriageApp` and `TriageScreen` remain intact; tests depending on them continue to pass.
- `pyproject.toml` adds `pywebview>=5.0` to the `[tui]` optional extra.

## Consequences

### Positive

- High-fidelity reproduction of the V1 Sereno design (custom fonts, border radius, smooth animations, precise spacing).
- The React prototype from the design handoff is reused almost directly — minimal translation work.
- Lazy-loading file tree scales to large directories without loading the full tree upfront.
- The pipeline stays entirely in Python; the frontend is a thin display layer.

### Negative

- pywebview requires a display environment (not headless). CI runs that invoke `dynamic-folding` interactively will fail without a display. Mitigated: CI uses `run` (non-interactive); only human-facing flows use the webview.
- Babel standalone compiles JSX in the browser (~80ms warm-up). Acceptable for an interactive tool.
- The vendored JS files (~4.3 MB) are committed to the repo. Acceptable for a single-user TCC artifact.
- `DynamicFoldingApp` (Textual) is dead code in `tui/app.py`. It can be removed in a future cleanup once the test surface is updated.

## Files changed

- `dynamic_folding/tui/webview_app.py` — new (`DFWebApi` + `launch_webview`)
- `dynamic_folding/tui/web/index.html` — new
- `dynamic_folding/tui/web/app.jsx` — new
- `dynamic_folding/tui/web/vendor/` — new (React 18.3.1, Babel 7.29.0)
- `dynamic_folding/cli.py` — `_launch_tui()` updated
- `pyproject.toml` — `tui` extra updated
- `docs/ADR/0030-pywebview-ui.md` — this document
- `docs/SPEC.md` — updated
