# ADR 0026: Post-Characterization Output-Naturalness Polish

Date: 2026-05-25

## Status

Accepted. **Partially superseded by [ADR 0035](0035-remove-user-facing-confidence-signal.md)**:
items 5, 6, and 8 below (inline-score → confidence-cue rendering, confidence-based
folder ordering, and the TUI confidence label) were removed when the user-facing
confidence signal was dropped from the product (contract v3 → v4). The remaining
items (the `_Review` → `Outros` rename, `display_name`, the merged-"Outros"
bucket, Unicode glyphs, and the summary preamble) still stand.

## Context

The Sprint 19 empirical characterization (thesis Ch4 §4.7) measured user
perception of the tool's proposed folder names via a Likert scale with three
raters across three corpora (N = 19 top-level folder names). The mean was
3.79 ± 1.58, but the distribution is **bimodal**: 53 % of names received the
maximum rating (5) while 16 % received the minimum (1), with very little mass in
the middle. The thesis frames this as *"a ferramenta opera em dois regimes —
claramente úteis ou claramente quebradas"*.

Qualitative analysis of the five low-rated names (Ch4 §4.7.2) taxonomises three
failure modes:

| Mode                                            | Share | Root cause            |
| ----------------------------------------------- | ----- | --------------------- |
| Truncation / repetition mid-word                | 3/5   | Post-processing       |
| Lexical invention ("PÁTULAS", "Pipelinhas")     | 2/5   | Naming-model prompt   |
| Hierarchy underuse ("Certificação de Janelas") | 1/5   | Clustering heuristic  |

The first mode (truncation + the surrounding "programmer aesthetic" of `_Review`,
`(orphans)/`, inline silhouette scores) is tractable through purely cosmetic /
render-layer changes that touch neither the namer nor the clusterer. The
remaining 40 % of the low-rated tail requires structural work in the namer
prompt (ADRs 0022–0024 already address part of this) and the clusterer
hierarchy heuristic. Those are scoped to Phase β experiments and are explicitly
**deferred** by this ADR.

The thesis (v1.2.0-TCC) is empirically frozen at the pre-polish behaviour. This
polish ships in the next minor release and is acknowledged in the thesis as
post-characterisation forward work, without re-running the Likert study.

## Decision

Apply the following changes, all within the render layer + a thin contract /
proposer touch-up. The clustering and naming algorithms are unchanged.

1. **Rename the outlier bucket canonical name `_Review` → `Outros`.** Update
   `proposal.outliers_folder` default in `config.py`, `pipeline.py`,
   `registries.py`, `validate_config.py`, and `proposer.py`. The
   leading-underscore programmer convention is replaced with a neutral PT-BR
   noun that any user would recognise as a folder name.

2. **Add `FolderNode.display_name: str | None = None`.** Render prefers
   `display_name` over `name` when set. The proposer sets
   `display_name="Outros"` on the outlier folder so the render layer can detect
   it via a stable marker even when a user overrides
   `proposal.outliers_folder` to a custom value. The field is also
   infrastructure for future polish work (e.g., name-normalisation) without
   another contract change.

3. **Bump `StructureProposal.contracts_version` 2 → 3.** Adding an optional
   field with a default is *not* technically a breaking change for consumers
   (old JSON still deserialises; new JSON gains an optional key), but the bump
   is done for thesis hygiene: visible contract evolution alongside the
   characterisation-driven polish phase makes the change auditable. The
   serialisation of `to_dict()` omits `display_name` when `None`, so JSON for
   non-outlier folders is identical to v2 except for the version field.

   The auxiliary `StabilityReport` and `CharacterizationResult` contracts
   (currently v2) are **not** advanced. Previously they were kept in lockstep
   with `StructureProposal`, but the v3 change here is purely additive on
   `FolderNode` and does not affect those auxiliary outputs. The lockstep
   convention resumes for the next change that genuinely touches the shared
   shape.

4. **Merge the outlier folder + top-level orphans into a single "Outros"
   bucket at render time.** The `(orphans)/` line is removed. Internally the
   pipeline still distinguishes "tiny cluster routed to outliers_folder" from
   "orphan never clustered"; from the user's perspective they are the same
   thing ("we couldn't confidently classify these").

5. **Replace inline numeric silhouette scores with named confidence cues.** The
   default tree shows count + colour only. Low-confidence (red) folders
   additionally get a `· verificar` label. High and medium-confidence folders
   stay clean — 53 % of folders are 5/5 per Sprint 19, so the common case
   becomes visually quiet. A new CLI flag `--scores` restores the raw numeric
   for research / debug use.

6. **Reorder top-level folders by confidence DESC, then file-count DESC, then
   name ASC (tie-breaker).** The strongest groups lead so the user encounters
   them first. The outlier bucket is always rendered last regardless of sort
   key.

7. **Render polish ergonomics:**
   - Unicode tree glyphs (`├── `, `└── `, `│   `) by default; ASCII fallback
     (`|- `, `|  `) retained under `use_emojis=False` for legacy terminals,
     piping, and LaTeX screenshots.
   - Summary preamble before the tree:
     `Proposta: N pastas, M arquivos · K em "Outros"`.
   - Per-folder inline file count (`(N arquivos)`), direct files only —
     subfolders show their own count, no double-counting.
   - Root path truncated to ~60 characters with a leading `…` when longer.

8. **TUI parity.** The interactive `TriageScreen` (Textual app, launched via
   `dynamic-folding run <path> -i`) consumes the same helpers from
   `dynamic_folding.render.tree` as the CLI tree renderer:
   `label_for`, `confidence_band`, `color_for_band`, `is_outlier`,
   `folder_sort_key`, `files_word`, `get_file_emoji`, `render_summary_line`,
   `OUTLIER_DISPLAY_NAME`. Result: the TUI shows the same summary preamble,
   the same confidence-only-on-red rule, the same file counts and folder
   ordering, and the same merged-"Outros"-last bucket. The overall cohesion
   label in the TUI header is also a friendly word
   (`alta` / `média` / `verificar`) by default and switches to the numeric
   `0.XXX` under `--scores`. The `--scores` flag is plumbed from the CLI
   through `DynamicFoldingApp` into `TriageScreen.show_scores`.

## Rationale

- **Anchored on measured failure modes.** Each change maps directly to a class
  of low-rated name from Sprint 19 §4.7.2, not on generic UX heuristics. The
  trade-off — polish addresses ~60 % of the low-rated tail, the rest waits for
  Phase β — is explicit.
- **Bimodal distribution → polish the tail, not the average.** Universal-layer
  changes (Unicode glyphs, less emoji noise, hidden scores) marginally help the
  working majority. The big wins come from changes that pull 1/5-rated names
  out of the failure regime (friendly outlier label, merged bucket, no inline
  programmer terminology).
- **Canonical rename + display_name marker.** Two complementary moves: the
  rename addresses the common case (default config), the marker addresses
  power-user config overrides without coupling render to a brittle literal
  string.
- **Thesis hygiene over technical optimisation.** The v3 bump is a non-breaking
  change that could legally stay at v2, but visible contract evolution maps
  cleanly to the Sprint-19 → polish narrative in the thesis.

## Consequences

- **Golden tests need regeneration.** The render output format changed
  substantially (Unicode glyphs, new preamble, confidence labels, new sort
  order, merged outlier bucket).
- **Sprint 6 outlier tests updated.** `_Review` literals replaced with
  `"Outros"` (the test still exercises both the default-name and explicit-
  config-override paths).
- **Backwards compatibility for power users.** Users who override
  `proposal.outliers_folder` (e.g., to `"Para Revisar"`) still see their
  canonical name on disk and in JSON, but the rendered tree shows "Outros"
  (the standardised display marker). This is an intentional UX choice.
- **Thesis text is unchanged.** Ch4 keeps `_Review` references as a historical
  description of v1.2.0-TCC behaviour. ADRs 0004 and 0010 (which mention the
  original outlier-routing design) get a forward-pointing note.
- **Phase β remains scoped.** Lexical invention (namer prompt) and hierarchy
  underuse (clustering) are *not* addressed here — they require structural
  work outside the polish boundary and remain the next experimental campaign.

## Alternatives considered

- **Render-only presentation, canonical unchanged.** Would create a "visual
  lie" if a user later tries to create the displayed folder on disk under the
  shown name; rejected.
- **Drop the `display_name` field entirely; render reads `proposal.outliers_folder`
  from config.** Cleaner in one sense, but couples render to config plumbing
  and gives no infrastructure for future name-polish work; rejected for the
  thesis-hygiene reason above.
- **Re-run the Likert study on the polished output.** Most rigorous but biggest
  time cost; deferred until Phase β results give a single re-validation round
  rather than a per-change one.

## References

- [Sprint 19 characterisation chapter](../../thesis/ch4/4_caracterizacao_empirica.md) §4.7.2 — failure-mode taxonomy
- [ADR 0016](0016-recursive-structure-proposal-v2.md) — previous contract bump (v1 → v2)
- [ADR 0004](0004-hierarchical-agglomerative-tree-clustering-and-outliers.md) — outlier routing design
- [ADR 0010](0010-hierarchical-subdivision-recursive.md) — recursive hierarchy
- [ADRs 0022–0024](0022-grounded-prompt.md) — namer prompt-hardening work that addresses the lexical-invention failure mode
