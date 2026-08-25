# ADR 0033: Remove the dead Textual TUI stack

## Status
Accepted

## Context

ADR 0030 replaced the Textual TUI with pywebview and explicitly noted the Textual
classes were left in place as dead code "to be removed in a future cleanup once the
test surface is updated." The audit (`docs/AUDIT.md`, findings C1/C2) confirmed the
state:

- `confirm_proposal` was imported in `cli.py` but **never called** — the interactive
  confirmation flow is now the pywebview "Aplicar proposta" button.
- `dynamic_folding/tui/app.py` (`DynamicFoldingApp`, `ProposalPanel`, `TriageScreen`,
  `TriageApp`, and the `_build_folder_label` / `_populate_proposal_tree` helpers) was
  reachable only from `core/triage.py` and two tests — not from any live CLI path.
- `textual` was imported by `tui/app.py` **only**.

## Decision

Remove the dead stack:

- Delete `dynamic_folding/tui/app.py` and `dynamic_folding/core/triage.py`.
- Drop the unused `from ...core.triage import confirm_proposal` import in `cli.py`.
- Remove `textual` from the `[tui]` optional extra and the dev dependency group.
- Delete `tests/test_tui_polish.py` (tested `TriageScreen` rendering only).
- Trim `tests/test_sprint9_triage.py` to its two **live** tests
  (`test_tree_render_with_colors`, `test_cli_interactive_flag`); the two
  `confirm_proposal`/`TriageApp` tests were removed.

## Why this loses no coverage

Every invariant `test_tui_polish.py` checked against the Textual `TriageScreen`
renderer is independently covered for the **live** `render.tree.render_tree` renderer
in `tests/test_render_polish.py`: Outros bucket merged with orphans and rendered last,
ordering by confidence/size/name, `verificar` on low confidence, singular/plural
`arquivo`, zero-files omits count, and `display_name` over the canonical name.
`test_cli_interactive_flag` already exercises the pywebview launch path.

## Consequences

### Positive
- ~883 LOC of unreachable Textual code removed; one fewer dependency (`textual`).
- The interactive surface is unambiguously the pywebview UI.

### Notes
- Historical ADRs (0026, 0028, 0029, 0030) and the SPEC sprint logs still reference the
  Textual classes as a record of what existed at the time; they are left intact.
- `dynamic_folding/tui/` now contains only `webview_app.py` and `web/`.

## Files changed
- `dynamic_folding/tui/app.py` — deleted
- `dynamic_folding/core/triage.py` — deleted
- `dynamic_folding/cli.py` — drop dead import
- `pyproject.toml` — drop `textual` from `[tui]` + dev
- `tests/test_tui_polish.py` — deleted
- `tests/test_sprint9_triage.py` — trimmed to live tests
- `docs/ADR/0033-remove-dead-textual-stack.md` — this document
