# ADR 0028: TUI as the default command, HTML report emitted on accept

## Status
Accepted

## Context

Two gaps remained after the HTML report landed (PR #41, no ADR at the time):

1. **No-args was a dead end.** `dynamic-folding` with no subcommand exited with
   argparse's `error: the following arguments are required: cmd`. The intended
   first-run experience — open the TUI, pick a folder, see a proposal — required
   the user to already know the `tui` subcommand existed.

2. **The report was asymmetric.** Only the non-interactive `run` command
   rendered the HTML report. The three paths that launch the unified TUI
   (`tui`, the new no-args default, and `run --interactive`) ran the pipeline
   but never produced a report, so the most user-facing flow was the one
   missing the deliverable.

## Decision

### (A) No subcommand launches the TUI

`add_subparsers(dest="cmd", required=False)`. When `args.cmd is None`, the CLI
resolves the project default config (`_resolve_cli_config_path(None)`) and
launches the unified TUI — behaviourally identical to `dynamic-folding tui`.
It returns exit code 0 regardless of accept/reject: the default experience is
an exploration surface, not a CI gate, so rejection is a normal outcome, not a
failure. (The `run --interactive` gate keeps its accept=0 / reject=1 contract
from ADR 0007 / Sprint 9, unchanged.)

### (B) One report helper, accept-gated at the call site

`_emit_report(result, cfg, root)` is the single place that renders the HTML
report and optionally opens it, honouring the `[report]` config section
(`enabled`, `output_path`, `auto_open`). The non-interactive `run` calls it
unconditionally; the TUI paths call it via `_launch_tui(...)` **only when the
user accepts**. Keeping the accept-gate at the call site (not inside the
helper) is what lets all four entry points reuse the same helper cleanly.

The discriminating question for the gate: would a user who *rejects* the
proposal want a browser to auto-pop? No — so reject emits no report.

## Constraints honoured

- **Robust Fallbacks (CLAUDE.md).** `_emit_report` preserves the existing
  warn-and-continue `try/except`: a report failure prints a warning and the run
  still succeeds. Never fail the pipeline flow over a report.
- **No app.py changes.** The TUI already returns `(accepted, run_result)` and
  sets `self.app.run_result`. All report logic stays in `cli.py` after
  `app.run()`, keeping the TUI decoupled from rendering — zero regression risk
  on the Textual app itself.
- **Offline / determinism.** Unchanged. The report is a pure function of the
  `RunResult` and config.

## What this ADR does NOT do

- **No file moves.** The tool still only proposes; the report is read-only output.
- **No new config keys.** The `[report]` section from PR #41 is reused as-is.
- **No TUI redesign.** Screens, navigation, and triage behaviour are untouched.

## Consequences

### Positive

- First-run `dynamic-folding` is self-explanatory: it opens the TUI instead of
  printing an error.
- The HTML report is produced consistently across every entry point that runs
  the pipeline interactively.
- Single source of truth (`_emit_report`) — future report changes touch one place.

### Negative

- `dynamic-folding` with no args is now interactive; a script that relied on the
  old "required subcommand" error to detect misuse would now open a TUI instead.
  Mitigated: all real commands are explicit subcommands, and `--version` / `-h`
  still short-circuit before dispatch.

## Tests

`tests/test_cli_tui_report.py`:
- `_emit_report` writes HTML when enabled; is a no-op when disabled; calls
  `webbrowser.open` once when `auto_open` is true.
- No-args dispatch launches the TUI (monkeypatched `DynamicFoldingApp.run`) and,
  on accept, emits and opens the report; on reject, emits nothing and returns 0.

## CLI smoke run

Command (no subcommand; `DynamicFoldingApp.run` patched to accept, so no real
TUI is needed for the smoke):

```
$ dynamic-folding
```

Expected output (on accept, with default `report.enabled=true`,
`report.auto_open=true`):

```
report: %LOCALAPPDATA%\DynamicFolding\reports\<timestamp>-report.html
<browser opens that file>
Organization proposal accepted in TUI.
```

Exit code `0`. On reject: no `report:` line, no browser, exit code `0`.
`dynamic-folding --version` and `-h` still short-circuit before dispatch.
