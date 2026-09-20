# 01 — Why the stability metric is `1 − 4·p·(1−p)`

**Context.** Sprint 19 builds a characterization chapter for the TCC. One of the
properties we measure is *stability*: if I add or remove a few files from the
corpus, does the proposed grouping stay roughly the same, or does it shuffle?

The first version of the SPEC defined stability as "the average rate at which
each pair of files ends up in the same cluster across runs." When implemented,
it gave odd results — even a perfectly reproducible clusterer scored ~0.32 on
a small fixture. So we revisited the formula.

This note explains, step by step, why we replaced that formula with
`1 − 4·p·(1 − p)` and what each piece means.

---

## What `p` is

Pick any pair of files in your corpus, say `report.docx` and `invoice.pdf`. Run
the tool 5 times under perturbation (each run keeps a random 90% of files).
Count how many of those 5 runs ended up putting the pair in the same group.

`p` is just that count divided by the number of runs.

- 5 / 5 = 1.0 → the pair was *always* together. The tool is sure they belong
  in the same group.
- 0 / 5 = 0.0 → the pair was *always* apart. The tool is sure they belong in
  different groups.
- 3 / 5 = 0.6 → the tool is wobbling. Sometimes together, sometimes apart.

So `p` lives between 0 and 1, and is computed *per pair*.

## What "stable" means for a pair

A pair is **stable** when the tool gives the *same answer* every run. The
answer can be "yes, same group" or "no, different groups" — it does not matter
which. What matters is that it does not change when the input changes slightly.

Three example pairs:

| Pair | `p`   | Interpretation        | Stable? |
|------|-------|-----------------------|---------|
| X    | 1.0   | Always together       | yes     |
| Y    | 0.0   | Always apart          | yes     |
| Z    | 0.5   | Coin-flip every run   | no      |

So stability is *not* the same as "co-occurrence rate". A pair with `p = 0`
can be perfectly stable; the SPEC's first formula did not capture that.

## The formula `1 − 4·p·(1 − p)`

We need a function that takes any `p` in `[0, 1]` and returns a stability
score in `[0, 1]`:

- 1 when `p` is exactly 0 or exactly 1 (perfect consistency)
- 0 when `p` is exactly 0.5 (pure noise)
- somewhere in between for intermediate values

The simplest function with that shape is `1 − 4·p·(1 − p)`. Let's check:

| `p`  | `4·p·(1 − p)` | `1 − 4·p·(1 − p)` |
|------|----------------|---------------------|
| 0.0  | 0              | **1.0**             |
| 0.1  | 0.36           | 0.64                |
| 0.25 | 0.75           | 0.25                |
| 0.5  | 1.0            | **0.0**             |
| 0.75 | 0.75           | 0.25                |
| 0.9  | 0.36           | 0.64                |
| 1.0  | 0              | **1.0**             |

Plotted, this is an upside-down parabola: bottom at `p = 0.5`, peaks of 1 at
`p = 0` and `p = 1`. It is symmetric around 0.5 because we don't care which
direction stability points (always-together is just as stable as always-apart).

Why this exact formula? `p·(1 − p)` is variance of a Bernoulli draw — it
measures how "uncertain" a yes/no decision is. Multiplying by 4 rescales it so
the maximum (at 0.5) is 1 instead of 0.25. Subtracting from 1 flips it so high
values mean *more* stability, not less. Three small steps, no magic.

Equivalent forms (all give the same numbers):

- `(2·p − 1)²` — squared distance of `p` from 0.5, rescaled
- `1 − 2·p·(1 − p) − 2·p·(1 − p)` — same thing
- We use the first form because it reads most naturally.

## Aggregating across pairs

Each pair gives one stability score in `[0, 1]`. We average those scores over
*evaluable pairs* — pairs of files that survived in every run, so we have full
data for them.

That average is what the tool reports as `pair_co_occurrence`.

## What the reported number means

- **1.0** → every pair is consistently grouped (always-same or always-apart).
  The tool is perfectly reproducible under this perturbation level.
- **0.0** → every pair flips around 50/50. The tool is essentially random
  given this perturbation.
- **0.7** (for example) → most pairs are consistent, with a minority of
  borderline pairs that the tool sometimes groups, sometimes splits.

For the TCC chapter, this number answers a single, concrete question:
*"How much can I trust this proposal to remain the same if my corpus changes
slightly?"*

## Edge cases

- **`runs < 2`** — we need at least two runs to compare. With one run, every
  pair has `p` ∈ {0, 1} by definition, but that does not measure stability,
  it just measures the single clustering's structure. We short-circuit and
  return 1.0 with an explanatory note.
- **`perturbation = 0.0`** — every run sees the exact same input. Since our
  clusterer is deterministic, every pair has `p` ∈ {0, 1} and the formula
  naturally yields 1.0. No short-circuit needed.
- **No surviving pairs** — perturbation so high that no two files survived
  every run. The metric is undefined; we return 1.0 with a note rather than
  a divide-by-zero.

## In thesis prose (Portuguese sketch)

> "Para cada par de arquivos que sobreviveu a todas as N rodadas perturbadas,
> calculamos `p`, a fração de rodadas em que o par foi agrupado junto.
> Derivamos um *escore de estabilidade* `1 − 4·p·(1 − p)`, que vale 1 quando
> o par é consistentemente agrupado (sempre junto OU sempre separado) e 0
> quando a decisão se aproxima de uma moeda viciada. O *pair-co-occurrence
> stability* reportado é a média desses escores entre todos os pares
> avaliáveis."

## Why we changed the SPEC

The first SPEC formula — "mean of `p` across pairs" — measured cluster shape,
not stability. A clusterer that *always* puts everything in one big cluster
would score nearly 1.0 on it. A perfectly reproducible clusterer that splits
into 3 groups scored 0.32. The metric did not distinguish stable from random.

The new formula does. It is the same data (`p` values per pair), filtered
through a function that rewards consistency rather than togetherness.

## References for further reading

- Bertrand Michel, "Stability of clustering" (lecture notes, 2014) — the
  intuition behind pairwise-stability metrics.
- Lange et al., "Stability-Based Validation of Clustering Solutions" (Neural
  Computation, 2004) — broader survey, includes pair-confusion variants.
- The `1 − 4·p·(1 − p)` form is a Gini-style dispersion measure; it appears
  in decision-tree literature (Gini impurity) and in clustering stability
  papers under various names.

You don't need to read these to defend the TCC — the explanation above is
self-contained — but they exist if you want to see the metric used elsewhere.
