# ADR 0044: Retire the MVP "metadata-only" non-goal

## Status
Accepted (2026-07-04). Amends the MVP scope (`docs/SPEC.md` Non-goals; `CLAUDE.md`).
Records a docs↔code reconciliation; introduces **no behavior change**.

## Context

The MVP scope declared, as an explicit non-goal, that the tool would do "no
content extraction (metadata-only)":

- `docs/SPEC.md` → `## Non-goals (MVP)`: *"No content extraction (metadata-only)"*.
- `CLAUDE.md` → `## What NOT to add`: *"No content extraction beyond metadata in
  the MVP."*

That constraint stopped being true long ago. Content extraction was introduced
from **Sprint 7** and progressively deepened, each step already recorded as a
deliberate decision:

- **Sprint 7 / 13** — the `type_aware` extractor reads a bounded content snippet
  (`scanner.snippet_size`, raised to and fixed at **4096** chars) for text-like
  files, plus rich metadata (internal title, image EXIF). Snippet flow and the
  config-default consolidation are documented in **ADR 0036**.
- **ADR 0017** — smart structural extraction for `.docx`/`.pptx` (headings/titles
  prioritized over body text, within the 4 KB cap).
- **ADR 0021** — smart structural extraction for PDF (outline titles + `/Subject`
  + `/Keywords`, backfilled with first-pages body text).
- **ADR 0025** — the dual-source text representation, whose default template
  `"[NOME]: {stem} [TÍTULO]: {title} [EXT]: {ext} [CONTEÚDO]: {snippet}"` feeds the
  content snippet to the embedder as a first-class signal.

So the code has, by design, embedded file **content** (not just filesystem
metadata) for many sprints. The stale non-goal directly contradicted the later
"Type-Aware Extraction" sections of the very same `SPEC.md`, and violated the
project's "docs are authoritative" rule. It also understated the tool in the
thesis: the system groups files by the **meaning of their content**, not merely by
filename — a stronger and more accurate claim.

The contradiction was surfaced while scoping the Chapter 4 evaluation expansion
(a labeled external comparison on a document benchmark only makes sense *because*
the tool reads content). The user flagged the reconciliation as the first thing
to fix, ahead of any evaluation work.

## Decision

**Retire** the MVP "metadata-only / no content extraction" non-goal. Content
extraction bounded to a snippet is the established, deliberate design, already
justified by ADRs 0017/0021/0025/0036 — this ADR does not re-justify it; it
formally records that the old constraint is superseded and reconciles the
authoritative docs with the code:

1. `docs/SPEC.md` — the Non-goals line is struck through and annotated as
   superseded, pointing here and to the Sprint 7+ sections.
2. `CLAUDE.md` `## What NOT to add` — the bullet is rewritten to state the *real*
   current boundary: content extraction is limited to a bounded snippet
   (`scanner.snippet_size`, default 4096) plus rich metadata; what remains out of
   scope is **full-text indexing, OCR, or unbounded content ingestion**.
3. `docs/CONTRACTS.md` — `ExtractedDoc` is clarified to state that its `metadata`
   dict carries both filesystem metadata and the content `snippet` (additive; no
   contracts version bump — consistent with the Sprint 7/17/22 notes).

The current boundary that *does* still hold (and is the useful guardrail going
forward): extraction is **bounded** — first `snippet_size` chars + reliable
metadata — and stays **offline** (no network, no OCR service, no unbounded read).

## Consequences

### Positive
- `docs/` is internally consistent again and matches the code (docs-authoritative
  rule honored).
- The thesis can accurately state the stronger property: grouping is driven by
  content meaning, not just filenames — which is also what legitimizes an external
  labeled-document comparison (the tool actually reads the articles).
- A single anchor exists for "why does the tool read content when an old rule said
  it wouldn't?" — useful for the defesa.

### Negative / non-effects
- **No behavior change and no number change.** The code already extracts content;
  every existing metric/frozen-corpus number was already produced under
  content-snippet extraction. Nothing is re-run.
- The retired non-goal remains visible (struck through, not deleted) so the
  historical MVP scope is still legible.

## Out of scope
- Any change to *how much* content is extracted (the 4096-char cap stays).
- Reverting to metadata-only — explicitly **not** the path; it would invalidate all
  reported numbers and discard a load-bearing signal.
- Adding new extraction sources (OCR, full-text indexing).
