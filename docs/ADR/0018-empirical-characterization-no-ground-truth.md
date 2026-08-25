# ADR 0018: Empirical Characterization Without Ground Truth

Date: 2026-05-07

## Status

Accepted. **Amended by [ADR 0038](0038-bounded-empirical-justification-default-clusterer.md)** —
bounded comparison + hyperparameter sensitivity of the default clusterer, and a single
corpus (n=1). The core of this ADR (no ground truth; internal metrics characterize,
not certify) stands.

## Context

For the TCC defense, the project needs empirical evidence that the tool *works*. Earlier ADRs (0006, 0008) framed this as "validation" and "measuring intelligence" using internal metrics (Silhouette) over a grid search. Two issues with that framing:

1. **Silhouette only measures internal cohesion.** A grouping can score high on Silhouette and still be useless to a human (e.g., grouping every `.pdf` together regardless of topic). Internal metrics tell us the clusters are tight; they do not tell us the clusters are *correct*.

2. **Unsupervised clustering on real-world files has no ground truth.** Two reasonable humans organizing the same files would produce different folder structures. Any labeled corpus we built ourselves would encode our own subjective opinion. External metrics (ARI, NMI, V-measure) computed against such labels would dress subjective judgment in objective-looking numbers — a banca that knows the field would dismantle the framing.

The honest path is to stop claiming "correctness" and instead *characterize* measurable properties of the tool's output that do not require a ground truth.

## Decision

1.  **Reject ground-truth approaches.** No ARI, NMI, V-measure, or self-labeled corpus. The TCC will explicitly state that these were rejected on epistemological grounds and explain why.

2.  **Characterize the tool along five properties:**

    | # | Property | Question it answers | Status in this sprint |
    |---|---|---|---|
    | 1 | **Structure-finding** | Does the tool produce groupings tighter than random? | In code (random clusterer baseline) |
    | 2 | **Stability** | Is the grouping consistent under small input perturbations? | In code (stability analyzer) |
    | 3 | **Sensitivity** | Does behavior change with config in theory-consistent ways? | Doc only (narrative reframing of existing grid search) |
    | 4 | **Computational scaling** | How does it scale (time, memory) with corpus size? | In code (performance instrumentation) |
    | 5 | **Perceived utility** | Do humans find the proposal useful? | Doc only (manual Likert protocol) |

3.  **TCC chapter title is "Empirical Characterization," not "Validation."** Language matters: characterization claims modest, defensible properties; validation implies a correctness criterion we cannot honestly meet.

4.  **Multiple corpora.** All quantitative properties are computed across 3–4 independent corpora to avoid overfitting the conclusion to a single dataset. Corpora live in a local `datasets/` folder (gitignored) and are referenced only by metadata (file count, size distribution, type mix) in the thesis.

5.  **ADR 0008 is not superseded.** The benchmark *implementation* (grid search, JSON persistence, leaderboard) remains valid — its outputs are reframed as evidence of *sensitivity to configuration*, not *correctness*. ADR 0008 receives a status note pointing to this ADR.

## Rationale

-   **Honest framing is more defensible than false rigor.** A banca can challenge "ARI = 0.7 against my labels" by asking "why are your labels the truth?". A banca cannot challenge "across three corpora, our method's Silhouette is consistently above the random-clustering baseline by margin X" — the claim is bounded and the evidence is reproducible.

-   **Five properties give five independent angles.** Even if one property is weak on a given corpus, the others provide redundancy. The argument is cumulative.

-   **Stability is the most distinctive claim.** Pair-co-occurrence under perturbation is rarely reported in clustering papers and gives the TCC a methodologically interesting contribution beyond "we ran sklearn."

-   **Performance scaling is unimpeachable.** Wall-clock and memory curves are objective measurements. They cannot be argued with.

-   **Subjectivity is acknowledged, not hidden.** The Likert protocol is documented honestly as "perceived utility, by a small panel" — not promoted to a correctness claim.

## Consequences

### Positive
-   **Defensible empirical chapter.** The thesis can present three quantitative subsections (structure, stability, performance) plus a sensitivity reframing and a manual-protocol future-work note — all under honest framing.
-   **No labeling work.** Avoids the time-sink of building and defending a labeled corpus.
-   **Adds one clusterer (`random`) and one analyzer (`stability`) to the registry** — both are small, isolated, deterministic, and useful as research instruments beyond this sprint.

### Negative
-   **Cannot answer the question "is the output correct?"** The thesis must explicitly own this limitation in a methodology section. This is a feature, not a bug — owning the limit is what makes the rest defensible — but it requires careful writing.
-   **The Likert protocol is manual and out-of-code-scope** for this sprint. Running it and aggregating results is the user's responsibility.
-   **`StructureProposal` and `RunResult` contracts are unchanged**, but a new `StabilityReport` DTO is added (see ADR-companion update to `docs/CONTRACTS.md`).
