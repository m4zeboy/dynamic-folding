# ADR 0021: PDF Smart Structural Extraction

## Status
Accepted

> **Numbering note:** this ADR was originally drafted as ADR 0018 on a parallel branch (`sprint-20`) that was forked before ADR 0018 (empirical characterization) was reserved on `main`. To preserve a unique ADR namespace, this ADR was renumbered to 0021 at cherry-pick time. ADRs 0019–0020 are gaps from sprint-20's deferred work; see `docs/learning/04-bisectable-changes-and-visible-failures.md` for the reconciliation context.

## Context
Sprint 17 introduced "Smart Structural Extraction" for `.docx` and `.pptx` files: prioritize headings/titles, then backfill with body text, all under a 4 KB cap. The existing PDF parser in `type_aware.py` predates this pattern — it dumps raw text from the first three pages into the snippet. For most PDFs (papers, manuals, reports), the first three pages are dominated by title pages, abstracts, copyright notices, and ToC pages, which carry weak topical signal compared to the bookmark outline a well-formed PDF already exposes.

`pypdf` (already a required dependency) exposes:
- `reader.metadata` — `/Title`, `/Author`, `/Subject`, `/Keywords`.
- `reader.outline` — bookmark tree as a (potentially nested) list of `Destination` objects, each with `.title`.

We currently use only `/Title` and `/Author`; `/Subject` and `/Keywords` and the outline are ignored.

## Decision
Upgrade `PdfParser.extract` to mirror the priority-then-backfill pattern from Sprint 17:

1. **Priority block (in order):**
   - PDF metadata `/Subject` and `/Keywords` (Title and Author remain in their dedicated metadata fields, not in the snippet — same as today).
   - Outline / bookmark titles, traversed depth-first, each title on its own line.
2. **Backfill:** if the priority block is shorter than `snippet_size`, append body text from the first 3 pages until the cap is reached. This preserves the current behavior for PDFs without an outline.
3. **Hard cap:** total snippet length ≤ `snippet_size`.
4. **No new dependency:** continue using `pypdf`.
5. **Graceful fallback:** unchanged. Missing `pypdf`, corrupted PDFs, or outline-traversal errors fall back to metadata-only or to body-text-only without raising.

Two additive metadata keys are introduced: `subject` and `keywords`. These are additive to `ExtractedDoc.metadata: dict[str, object]` and do not require a `contracts_version` bump.

## Consequences

### Positive
- **Higher-quality grouping for PDF-heavy corpora** (academic papers, manuals): outline titles are dense topical signal compared to first-page boilerplate.
- **Pattern parity** with `.docx`/`.pptx`: the type_aware extractor now applies the same prioritization shape across the three Office-style formats.
- **Backwards compatible** for PDFs without an outline — they still get body text, exactly as today.

### Negative
- **Outline parsing is brittle:** PDFs with malformed outlines or unusual encodings exist. Mitigation: each title is read inside a try/except; a title that fails to decode is skipped, not fatal.
- **Outline can be huge:** a 200-page manual can have hundreds of bookmarks. Mitigation: the priority block is also bounded by `snippet_size`, so a runaway outline simply means no body backfill — still safe.
- **Heuristic risk:** outline-driven snippets may differ from what a user would extract manually. Mitigation: behavior is deterministic and documented; users who prefer raw body text can keep the old config knob (none currently exposed; default is the new behavior).

## Out of scope
- OCR for scanned PDFs (no text layer) — remains metadata-only.
- Font-size-based heading inference for PDFs without an outline — deferred.
- Surfacing outline structure into clustering as a separate signal — deferred.
