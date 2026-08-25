# ADR 0045: Multi-corpus comparative report — aggregate-first structure

## Status
Accepted (2026-07-05). Decision layer for the Chapter 4 evaluation expansion
(3 corpus). **No implementation here** — this ADR only fixes the report structure
so the 🔒 implementation can follow cleanly. Amends the single-corpus assumption
of the comparison report (ADRs 0041/0042/0043).

**Decision criterion:** simplicity / minimal new code. Aggregate-first reuses every
existing per-corpus section untouched and adds only three small pieces (orchestrator,
aggregate section, top template); the alternatives were rejected for the churn or
weaker payoff they'd bring (see Consequences). This is a tooling/structure decision,
not a thesis claim — no external defense is required of it.

## Context

The advisor asked to expand the "Avaliação experimental" (cap.4) from one corpus
to **three, presented as a single report comparing them side by side** — not three
separate reports. Locked decisions (see `evaluation-expansion-plan` memory and the
planning file):

- **Corpora (anonymized, fixed order):** Corpus 1 = `datasets/downloads_2026-06-15`
  (the frozen snapshot the thesis already reports — **additive**, its numbers are
  preserved), Corpus 2 = `Dataset Astolfo`, Corpus 3 = `Dataset Gabriel`. Real
  names never appear in the report.
- The external/annotated comparison is **deferred** (separate, more delicate item).

The current report code is already factored for reuse. In
`dynamic_folding/evaluation/comparison_report.py`, sections split cleanly:

- **Corpus-agnostic (no argument):** `_section_intro`, `_section_silhouette`,
  `_section_structural`, `_section_limitations`.
- **Corpus-specific (take a `ComparisonResult`):** `_section_figure`,
  `_section_matrices`, `_section_reducer`, `_section_provenance`, `_hero`.

And `comparison.py::run_comparison(...)` already yields **one `ComparisonResult`
per corpus**. So a multi-corpus report is assembly, not a rewrite.

## Decision

Adopt an **aggregate-first** structure, built by reusing the per-corpus machinery
plus a thin new layer:

### Structure (section order)
1. **Conceptual, once:** intro · the two lenses (silhouette/DBCV) · structural
   framing (reuse `_section_intro/_section_silhouette/_section_structural`).
2. **★ New aggregate section — the heart:** the cross-corpus comparison.
3. **Per-corpus sensitivity blocks, ×3 (evidence appendix):** for each corpus,
   `_section_matrices` + `_section_reducer` under a "Corpus N" heading.
4. **One shared provenance + one illustrative figure.**
5. **Limitations, once** (reuse `_section_limitations`, extended with the n=3 and
   heterogeneous-corpora caveats).

> **Amendment (2026-07-06) — "médio: dedup só do idêntico".** On seeing the first
> rendered report the author found the per-corpus detail blocks too repetitive.
> Revised: the aggregate section (the 3 tables) IS the cross-corpus comparison, so
> only what genuinely differs per corpus stays per-corpus — the **matrices** and
> **reducer sensitivity** (different numbers). The **figure** (illustrative,
> ADR 0042 default-only spirit) and the **provenance** (config/model/reducer are
> identical across corpora) are **deduplicated to a single shared instance**: one
> figure of Corpus 1 + one `_section_provenance_shared(multi)` (shared config + a
> per-corpus file-count line). Side effect: the figure now renders once on Corpus 1,
> where its "24,5% de variância" / "54 pontos" text is correct — dissolving the ×3
> stale-caption issue flagged during review. `_hero` is not reused per corpus (its
> n=1 prose); `_multi_hero` is used once. This is a tooling/layout revision — no
> measurement changes.

> **Amendment (2026-07-27) — dedup completes: the prose too.** Reviewing the report
> before sending it to the advisor, the author flagged the same instinct again —
> still "muita prosa repetida". Measured: **7 authorial paragraphs (5 + 2 callouts
> for the matrices, 2 for the reducer) rendered 3× each**, because the per-corpus
> loop called `_section_matrices` / `_section_reducer`, which carried the prose
> inline with their tables. The 2026-07-06 amendment deduplicated the *figure* and
> *provenance* but left this, since the prose travelled inside functions that do
> differ per corpus.
>
> The explanation is **methodological, not per-corpus** — it says the same thing
> regardless of which corpus follows. Worse than volume: an identical block invites
> the reader to re-read it looking for a difference that isn't there. Prose extracted
> to module constants `MATRICES_PROSE` / `REDUCER_PROSE`; both sections take
> `include_prose: bool = True`. The **single-corpus report is unchanged** (default
> `True`) — that prose is the author's writing pilot and the Ch4 seed, so preserving
> it verbatim was the binding constraint. The multi-corpus report passes `False` in
> the loop and emits one new `_section_how_to_read()` before Corpus 1.
>
> Not a change of decision: aggregate-first stands, and per-corpus blocks still hold
> what genuinely differs (the tables). Layout only — no measurement changes; the
> preview was re-rendered from the frozen JSON, not recomputed. Note the placement
> trade-off left open for the author: the two scope caveats ("não é a combinação
> ótima", "função descritiva") now sit at the top rather than beside each table —
> consistent with the recorded posture that a scope limit is stated **once**, with
> spine, never as repeated apology.

### The aggregate section content
- **Metric tables, one lens per table** (more legible than one mega-grid):
  - *Silhueta* — corpus × algorithm (384-dim, convex bias labeled in header).
  - *DBCV* — corpus × algorithm (10-dim, density bias labeled).
  - *Estrutural* — corpus × algorithm: nº grupos, outliers, cobertura.
- **Transversal reading (author prose, written later under the linha-dura pact):**
  poses the honest question *"does the opposite-bias pattern hold across the three
  corpora?"* (on the frozen snapshot: silhouette favored agglomerative, DBCV favored
  hdbscan). It **shows the numbers and asks**, and does **not** pre-commit the
  answer — consistent → the "each lens has its bias" story generalizes; inconsistent
  → an honest corpus-dependence finding. Either outcome reports cleanly.

### Engineering
- New orchestrator: call `run_comparison` per corpus → collect
  `[ComparisonResult]` with labels Corpus 1/2/3.
- New assembler `render_multicorpus_html` (mirrors `render_comparison_html`):
  conceptual once → aggregate section → per-corpus blocks ×3 → limitations.
- New top-level HTML template (or extend the existing one). The V1 Sereno design
  system, offline, deterministic rendering are preserved.
- Per-corpus section functions are **not modified** (avoids the heavy
  fully-interleaved rewrite that would widen every table to 3 corpora).

### Honesty constraints (inherited, non-negotiable)
- **No crowning.** The aggregate reports trade-offs and the bias each number
  carries; it never elects a winner.
- **Biases labeled** on every metric column (silhouette convex, DBCV density).
- **n=3 and heterogeneity caveats.** Three corpora is a small comparison, and the
  corpora differ in file-type mix (downloads has PDFs/images; Astolfo/Gabriel are
  `.txt`) → framed as "the tool across different real inputs," **not** a controlled
  experiment.
- **Provenance.** Every number traces to the run that produced it; Corpus 1 must
  reproduce the frozen numbers already in the thesis.

## Consequences

### Positive
- Genuinely "one report comparing the three," which is what the advisor asked.
- Minimal new code: only the orchestrator, the aggregate section, and the top
  template. Per-corpus blocks and all metric computation are reused verbatim.
- The frozen Corpus 1 numbers are preserved (additive expansion; nothing re-derived
  conceptually).

### Negative / trade-offs
- The report gets long (conceptual + aggregate + 3 detail blocks). Mitigated by the
  aggregate-first order: a reader gets the comparison up front and can treat the
  per-corpus blocks as an appendix.
- Rejected **fully-interleaved** (each section shows all 3 corpora): most integrated
  but requires rewriting every `_section_*` and produces wide, dense tables.
- Rejected **per-corpus-first + summary**: easier, but reads as "three reports
  stapled together," under-delivering the side-by-side comparison.

## Out of scope
- Implementation (the 🔒 step: running the 3 corpora, regenerating the report).
- The new graphs (separate backlog item; they decorate this structure afterward).
- The external/annotated comparison (deferred).
- Any change to Corpus 1's frozen numbers.
