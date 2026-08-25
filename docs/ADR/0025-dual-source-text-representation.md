# ADR 0025: Dual-source text representation — filename and internal title

## Status
Accepted (supersedes point 2 of ADR 0011).

## Context

ADR 0011 (proposed 2026-05-01) introduced "Title Prioritization" in the
preprocess stage: when an internal document title with length greater
than five was available, it replaced the filename stem in the
`text_for_embedding` field. The rationale registered there was that
"prioritizing internal titles mitigates the impact of poor filenames on
semantic quality." This decision was reflected in
`dynamic_folding/preprocess/basic.py` and materialized in the default
template
`"[FILE]: {best_title} [EXT]: {ext} [CONTENT]: {snippet}"`.

The thesis advisor reviewed Chapter 3 (sections 3.1–3.3.3) on
2026-09-18 and rejected the underlying premise. Two of her observations
are recorded verbatim by the user:

- "A premissa de que os nomes [de arquivo] não são válidos não é
  defensável."
- "O programa deve usar OS DOIS — tanto nome quanto título interno —
  para fazer o processamento."

The advisor's critique is methodological: the prior design discarded a
signal (the filename) on the basis of an unverified premise (that
filenames are "poor"). The thesis text in 3.1 stated this premise
explicitly; 3.3.3 documented the resulting priorização in the code. Both
are no longer defensible under the advisor's standard.

## Decision

The preprocess stage emits **both** the filename stem and the internal
document title in distinct slots of the text representation. The slots
are emitted by the configurable template, not by a derived `best_title`
field computed in code.

Concretely:

1. `dynamic_folding/preprocess/basic.py` removes the title-prioritization
   block. The `best_title` derived field is no longer produced.
2. `config/default.toml::preprocess.template` becomes
   `"[NOME]: {stem} [TÍTULO]: {title} [EXT]: {ext} [CONTEÚDO]: {snippet}"`.
3. When a document has no internal title (e.g., images, plain-text
   files without a structured title), the entire `[TÍTULO]: {title}`
   slot is omitted from the output. A post-render regex step in
   `dynamic_folding/preprocess/basic.py` removes any `[TAG]:` segment
   whose value rendered to empty before whitespace normalization.
   Downstream stages are unaffected.

The thesis sections that documented the prior design (3.1 and 3.3.3 of
`thesis/3_proposta_v2.md`) are revised in the same change to reflect
the new behaviour and to remove the "filenames are unreliable" framing.

## Consequences

### Positive

- The embedder receives both lexical sources (filename and internal
  title) for every document, eliminating the silent dropping of one
  signal in favour of the other.
- The thesis text aligns with the code: section 3.3.3 now states what
  the code does (concatenates both in distinct slots), not what the
  prior premise dictated.
- The decision is configurable. Users who prefer the prior behaviour
  can restore a single-slot template in their own config file; the
  preprocess function imposes no policy.

### Negative

- **Cache invalidation, one-time.** The text fed to the embedder changes
  for every file with an internal title (the order and structure of
  the emitted slots are different). The SQLite cache key incorporates
  the content hash, so the next run recomputes embeddings. This is a
  one-time cost.
- ~~**Empty `[TÍTULO]:` slots for image and plain-text corpora.**~~
  Resolved: the post-render strip step removes the entire slot when the
  title is absent, so no empty `[TÍTULO]:` token reaches the embedder.
- **Empirical re-validation under the new representation is deferred.**
  Chapter 4 reports characterization runs under the prior
  representation. Re-running the full experimental matrix is out of
  scope here; the change is committed because the new design is
  defensible by the advisor's standard regardless of whether the
  resulting clusters shift.

## Out of scope

- Re-running the Chapter 4 characterization experiments under the new
  representation.
- Changing the markers from Portuguese to English (or vice-versa). The
  Portuguese markers `[NOME]`, `[TÍTULO]`, `[EXT]`, `[CONTEÚDO]` are
  consistent with the rest of the project's user-facing locale.
- Adding new slots (e.g., `[AUTOR]`, `[CRIADO_EM]`). The current four
  slots match the metadata that the existing extractors reliably
  provide.
