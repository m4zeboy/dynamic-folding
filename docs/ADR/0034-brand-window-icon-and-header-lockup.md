# ADR 0034: Brand window icon + header lockup

## Status
Accepted

## Context

The pywebview window showed the **python.exe icon** on the Windows taskbar and title bar, and the
in-app header used a generic star + "dynamic folding" text. The finalized brand package provides
the "Geometric Fold" mark and a primary lockup. We apply that identity to the OS window icon and
the app's title-bar header.

Root cause of the Python icon (verified in pywebview `platforms/winforms.py`): the window icon is
set from `webview.start(icon=<path>)` when that points to a real `.ico`; otherwise the backend
extracts the icon from `sys.executable`.

## Decision

- **Mark color:** the app accent `#3B82F6` (V1_B), not the brand sheet's cyan `#3A9ED9`, so the
  logo matches the rest of the UI (steppers, buttons, folder accents). Scope: the **title-bar
  header only** — the proposal-subheader star is unchanged.
- **Window/taskbar icon:** ship `dynamic_folding/tui/assets/dynamic-folding.ico` (multi-size
  16–256, transparent, `#3B82F6`) and pass `icon=<path>` to `webview.start()`. A committed,
  deterministic, offline generator (`generate_icon.py`, Pillow) draws the five mark polygons and
  re-creates the `.ico`/`.png`. If the asset is missing, the run safely falls back to the host-exe
  icon (both our guard and the WinForms backend check `isfile`).
- **Header:** a new `DFLogo` React component renders the multi-fill mark (the existing `DFIcon` is
  stroke/single-color), replacing the star; the text becomes the lockup — `dynamic` (700) +
  `folding` (400), lowercase, no space. `app.jsx` is recompiled offline to `app.js` via the
  vendored Babel.
- **HTML report:** the report's top brand label (`report_template.html`) gets the same mark +
  lockup via an inline `mark()` SVG builder (no `xmlns`, to keep the report self-contained). As in
  the app, the hero/proposal star is left unchanged.

## Consequences

- The Windows taskbar/title bar and the in-app header now carry the brand identity.
- No favicon was added: a pywebview desktop window has no tab, so a document favicon is never
  visible; the `.ico` covers the OS surfaces.
- The `.ico`/`.png` ship in the wheel automatically (package data); no `pyproject` change.
- The GUI appearance can only be confirmed on a real desktop launch (not headless).

## Files changed
- `dynamic_folding/tui/assets/generate_icon.py` — new (icon generator)
- `dynamic_folding/tui/assets/dynamic-folding.ico` / `.png` — new (generated assets)
- `dynamic_folding/tui/webview_app.py` — pass `icon=` to `webview.start()`
- `dynamic_folding/tui/web/app.jsx` — `DFLogo` + header lockup
- `dynamic_folding/tui/web/app.js` — recompiled
- `dynamic_folding/render/report_template.html` — brand mark + lockup in the report header
- `docs/ADR/0034-brand-window-icon-and-header-lockup.md` — this document
