# ADR 0029: TUI redesign — V1 Sereno (single-screen, two-panel layout)

## Status
Accepted

## Context

The original TUI used a push/pop screen stack (HomeScreen → PipelineScreen → TriageScreen → ErrorScreen). This model had several friction points:

- No visible step indicator — users had no sense of where they were in the three-phase flow.
- Full-width `DirectoryTree` with no confirmation panel — selecting a folder and kicking off the pipeline were conflated in a single keypress (`S`), with no visual confirmation of what was selected.
- Keyboard-only interaction on the proposal screen — no clickable buttons; the accept/reject actions were hidden behind `Enter`/`Esc` footer hints.
- No "restart" path — rejecting the proposal popped back to the pipeline screen rather than to the folder-selection step.
- Each screen was isolated; there was no persistent UI element across phases.

A design handoff (`design_handoff_dynamic_folding/`) provided three high-fidelity browser prototypes (V1 Sereno, V2 Studio, V3 Técnico). **V1 Sereno** was selected: a VS-Code-inspired two-panel layout with a persistent left sidebar and a context-sensitive right panel.

## Decision

### Architecture: single screen with ContentSwitcher

Replace the four-screen stack with a **single `MainScreen`** that contains:

```
MainScreen
  ├─ TitleBar   (traffic-light dots · app name · StepIndicator)
  └─ Horizontal
       ├─ Sidebar (width 32, always visible)
       │    └─ FilteredDirectoryTree
       └─ ContentSwitcher
            ├─ SelectPanel   (step 0)
            ├─ ProcessPanel  (step 1)
            └─ ProposalPanel (step 2)
```

State is managed via Textual reactives on `MainScreen`:
- `step: int` (0/1/2) — drives the `StepIndicator` and gates key bindings.
- `selected_path: Path | None` — drives the path chip in `SelectPanel`.

Custom messages coordinate across widget boundaries:
- `FolderChosen(path)` — Sidebar → MainScreen when a directory is activated.
- `StartAnalysis()` — SelectPanel button → MainScreen to kick off the pipeline.
- `Restart()` — ProposalPanel "Recomeçar" button → MainScreen to reset state.
- `Accept()` — ProposalPanel "Aplicar proposta" button → app exit with `(True, result)`.

### Visual design tokens (mapped to Textual CSS)

| Design token | Value | Used on |
|---|---|---|
| Blue primary | `#3B82F6` | active step, path chip, btn-start, stage-active |
| Blue light bg | `#EFF6FF` | path chip background |
| Blue light border | `#BFDBFE` | path chip border |
| Amber folder icon | `#F59E0B` | (in DirectoryTree, rendered by Textual default) |
| Success green | `#10B981` | completed stage checkmark |

### Button interactions on the proposal screen

| Button | Mapping |
|---|---|
| Recomeçar | Posts `Restart()` → reset to step 0, clear selected path, switch to SelectPanel |
| Aplicar proposta | Posts `Accept()` → `app.exit((True, run_result))` |

Both buttons are also accessible via `Q` (quit, equivalent to reject) from the keyboard.

### Pipeline stage details

Generic static labels per stage (no changes to the progress protocol or `RunResult`):

| Stage | Active label | Done detail |
|---|---|---|
| scan | Varrer estrutura | Estrutura varrida |
| extractor | Indexar metadados | Metadados indexados |
| preprocess | Pré-processar texto | Texto normalizado |
| embedding | Gerar vetores | Vetores calculados |
| reducer | Reduzir dimensões | Dimensões reduzidas |
| proposal | Gerar proposta | Proposta gerada |
| clustering | Agrupar arquivos | Agrupamentos computados |
| naming | Nomear categorias | Nomes atribuídos |

### Backward compatibility

`TriageScreen` and `TriageApp` are kept in `app.py` because:
- `tests/test_tui_polish.py` imports `TriageScreen` and tests `_folder_label` / `_populate_tree` directly.
- `dynamic_folding/core/triage.py` imports `TriageApp` for the `confirm_proposal` fallback.
- `tests/test_sprint9_triage.py` patches `TriageApp.run`.

The shared tree-rendering logic is extracted into module-level helpers (`_build_folder_label`, `_populate_proposal_tree`) consumed by both `ProposalPanel` and `TriageScreen`.

`DynamicFoldingApp.__init__` signature is unchanged; `cli.py` requires no edits.

## Consequences

### Positive

- Persistent sidebar gives spatial continuity across all three phases.
- Step indicator makes progress immediately visible.
- Decoupled folder selection (activate in tree) from pipeline trigger (click button) reduces accidental starts.
- "Recomeçar" button provides a natural restart path without restarting the app.
- `_build_folder_label` / `_populate_proposal_tree` are now module-level helpers, removing duplication between the new `ProposalPanel` and the legacy `TriageScreen`.

### Negative

- `TriageScreen` and `TriageApp` remain as legacy code. They are not reachable from the primary CLI flow but must be maintained for the test surface.
- The `Enter` key no longer accepts the proposal from the keyboard (removed to avoid conflicting with `Tree` node navigation). Users accept via button or the primary keyboard path `Q`→quit.

## Files changed

- `dynamic_folding/tui/app.py` — full rewrite of `DynamicFoldingApp` internals; legacy classes preserved.
- `docs/ADR/0029-tui-v1-sereno-redesign.md` — this document.
- `docs/SPEC.md` — TUI section updated.
