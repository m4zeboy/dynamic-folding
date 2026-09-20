# Manual Evaluation Protocol — Perceived Utility

This document describes the **manual** human-evaluation workflow that complements the automated empirical characterization (`dynamic-folding characterize`). It is referenced in ADR 0018 as Property #5 ("Perceived Utility") and is intentionally NOT implemented as code.

## Why this exists

The automated characterization measures three properties without requiring ground truth:

1. Structure-finding (vs. random baseline)
2. Stability under input perturbation
3. Computational scaling

These tell us the tool produces *non-random, stable, fast* groupings. They do NOT tell us whether a human looking at the proposal finds it useful. That question is inherently subjective — it cannot be automated honestly. Hence: a small, transparent, manually-run study.

## Why this is not in code

The Likert protocol is by design a **manual research instrument**. Building a TUI/web form for it would (a) imply a level of automation that the underlying claim cannot support, and (b) bias toward whoever sits in front of the terminal. Pen-and-paper or a shared spreadsheet keeps the data collection honest.

## Recommended setup

### Sample size and panel

- **3 to 5 raters.** More is welcome but not required.
- Mix raters with different familiarity with the corpus when possible (e.g., one who organized the files, one who didn't). Asymmetry in familiarity is a finding worth reporting, not a flaw to eliminate.
- Avoid having raters who have seen the algorithmic explanation; the claim is about *the proposal as presented*, not about the method.

### Materials per session

- A printed or shared rendering of the **top-level folders only** of one proposal. Do not show subfolders on the first pass — they bias the rating.
- A short instruction sheet:

  > You will see a proposed folder organization for a set of files. For each top-level folder, you will rate how *useful* the grouping seems to you on a 1–5 scale (1 = "I would not use this", 5 = "I would adopt this immediately"). At the end you give one overall rating. There is no right answer; we want your honest reaction.

- A response sheet (CSV-friendly):

  ```
  rater_id,corpus_id,folder_name,usefulness_1to5,comment_optional
  R1,corpus_a,Academic_Documents,4,"clear category"
  R1,corpus_a,Bills_And_Receipts,3,"name is awkward"
  ...
  R1,corpus_a,_OVERALL_,4,
  ```

### Procedure

1. Pick **one** corpus and **one** configuration (the one being defended in the thesis).
2. Run `dynamic-folding run <corpus> --config <thesis-config.toml>` once and capture the proposal.
3. Render the top-level folders to a sheet. For each folder, list the folder name and the count of files inside (not the file names — those bias the rating toward "I recognize this file").
4. Hand the sheet to each rater independently. Do not discuss the proposal with raters until they have submitted their response.
5. Aggregate the responses into a single CSV stored next to the corpus (e.g., `datasets/<corpus_id>/likert_responses.csv`). The `datasets/` folder is gitignored — keep this with your thesis materials, not the repository.

### Reporting in the thesis

Report at minimum:

- **Sample size** (`N` raters).
- **Mean and standard deviation** of overall usefulness.
- **Folder-level distribution** (which folders had high agreement, which had high disagreement).
- **One representative qualitative comment** per folder that received a low rating, when available.
- An honest caveat:

  > These results reflect the *perceived utility* of the proposal to a small panel of raters; they do not constitute a validation of correctness. See ADR 0018 for the methodological framing.

## What this protocol deliberately does NOT do

- It does not compute inter-rater reliability scores (Krippendorff's alpha, Fleiss' kappa) — sample sizes of 3–5 are too small for those statistics to be meaningful, and reporting them would be statistical theater.
- It does not aggregate across configurations or corpora. Run the protocol once, on the configuration you are defending, on one corpus. Replication across corpora is welcome but should be reported as separate studies, not pooled.
- It does not produce an automated "score" that goes into the JSON outputs. The Likert results are stand-alone qualitative evidence reported in the thesis prose.

## Relationship to the `characterize` command

The Likert protocol is a **complement** to `dynamic-folding characterize`, not a replacement. The TCC's empirical chapter uses both:

- Automated quantitative properties (silhouette vs. random, stability, scaling) — from `characterize`.
- Manual qualitative property (perceived utility) — from this protocol.

The two are presented as independent lines of evidence. Either one alone would be insufficient; together they triangulate.
