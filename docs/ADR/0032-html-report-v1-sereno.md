# ADR 0032: HTML report restyled to V1 Sereno (PT-BR)

## Status
Accepted

## Context

The pywebview GUI adopted the **V1 Sereno** design system (ADR 0029/0030): palette `#FAFAF8`/
`#E5E7EB`/`#3B82F6`, amber folder icons `#F59E0B`, DM Sans/DM Mono, pill count badges, PT-BR copy.
The HTML report — emitted on TUI accept and used as the thesis artifact — still used the old
Bootstrap-ish look (`#0d6efd` blue, `#f8f9fa` grey, Segoe-only, English copy), so the accepted
proposal looked nothing like the app that produced it.

## Decision

Restyle `dynamic_folding/render/report_template.html` to match V1 Sereno. Confirmed choices:

- **Language:** PT-BR, matching the GUI ("Proposta de organização", "categorias/arquivos",
  "Outros", stage labels reuse the GUI's `STAGE_LABELS`).
- **Framing:** a clean standalone document — no window chrome or stepper.
- **Proposal-focused:** the proposal tree (styled like the GUI's `V1PropNode` — amber folder
  icons, name in `#374151`, right-aligned pill count badge, 16px/level indent, click-to-collapse,
  "Outros" muted and last) leads. The technical sections (stat grid, provider badges, stage
  timings, run notes) are demoted into a native `<details>` "Detalhes técnicos", collapsed by
  default.

The data layer is unchanged: `render_html` / `_build_data` in `dynamic_folding/render/html.py`
still produce the same `#df-data` JSON (keys `version, root, timestamp, file_count, folder_count,
noise_count, peak_memory_mb, providers, timings, folders, orphans, notes`) and the template keeps
the `__DF_DATA__` sentinel, the `esc()` helper, and the `FolderNode` shape. **`html.py` is not
touched.**

### Offline-safety preserved
Icons are inline Feather SVGs (the same glyphs as the GUI's `DFIcon`); fonts are system-only
(`DM Sans`/`DM Mono` if installed, else Segoe UI/Consolas), no `@font-face`, no CDN, no
`src=`/`href=`/`http(s)`. The report opens with zero network requests.

### Clarity note
The summary line counts top-level groups as "categorias"; the technical stat grid labels the
recursive `folder_count` as "Pastas" (total folders) so the two counts never collide on the same
word.

## Consequences

- The report visually matches the GUI proposal screen; the TCC artifact is consistent end to end.
- Report tests assert PT-BR markers ("Proposta de organização", "Detalhes técnicos", empty →
  "Nenhuma pasta proposta."); the self-contained and `#df-data` assertions are unchanged.
- Pure template change → determinism and the rest of the suite are unaffected.

## Files changed
- `dynamic_folding/render/report_template.html` — full restyle (only substantive change)
- `tests/test_html_report.py` — PT-BR assertions
- `docs/ADR/0032-html-report-v1-sereno.md` — this document
- `docs/SPEC.md` — report note
