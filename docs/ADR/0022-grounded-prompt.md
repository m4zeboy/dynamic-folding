# ADR 0022: Grounded prompt variant for LLM-based cluster labeling

## Status
Accepted

## Context

The Likert pilot reported in Ch4 §4.7 (`thesis/ch4/4_caracterizacao_empirica.md`) surfaced **lexical invention** as the second of three failure modes of the naming stage (§4.7.2, item 2): the LLM (Ollama, `llama3.1`) produced non-Portuguese words when given small clusters with little contextual text. Concrete examples from the pilot:

- *"PÁTULAS VISUAIS"* (corpus Astolfo) — evaluator wrote *"O que significa PÁTULAS?"*.
- *"Simulações Arquivos Quadros Pipelinhas"* (corpus Moisés) — evaluator wrote *"criou palavras"*.

The hypothesis is that the existing prompt (`_DEFAULT_PROMPT_TEMPLATE` in `dynamic_folding/naming/ollama.py`) leaves the model free to confabulate when the cluster's text is sparse, because the prompt asks for a "thematic name" without anchoring the model's vocabulary to the input.

A second related issue from §4.7.2, item 1 — trailing connectives ("Certificação **de**", "Fotos **e**") — has already been addressed by post-hoc sanitization (`_strip_trailing_connectives` in `dynamic_folding/core/windows.py`, ADR-less change merged as `fix/naming-trailing-connectives`). The grounded prompt described in this ADR additionally instructs the model to avoid trailing connectives at generation time, layered on top of the sanitization.

## Decision

Introduce a second prompt template, `_GROUNDED_PROMPT_TEMPLATE`, selected via a new configuration key `naming.prompt_variant ∈ {"default", "grounded"}`. The grounded variant is now the **default of the tool**.

The grounded template differs from the default along three axes:

1. **Lexical anchoring principle.** Explicit instruction that the folder name must be composed exclusively of words present in the cluster's files. Synonyms or invented words are forbidden.
2. **Anchor terms injection.** The top-N TF-IDF terms of the cluster (default N = 5, configurable via `naming.top_anchor_terms`) are computed by `extract_anchor_terms` in `dynamic_folding/naming/tfidf.py` and inlined into the prompt as a comma-separated list, prefixed by an instruction to prioritize them.
3. **Escape hatch.** If no clear theme emerges from the cluster's lexicon, the model is instructed to reply literally `"_Ambíguo"`. This avoids forcing a fabricated name when the cluster genuinely lacks coherent vocabulary. `"_Ambíguo"` passes through `sanitize_windows_folder_name` unchanged and becomes a valid folder name visible to the user.

The TF-IDF anchor extraction reuses the same vectorizer used by the `tfidf` namer fallback, refactored from `name_cluster` into a public `extract_anchor_terms(texts, top_n)` function.

`naming.prompt_variant` is validated by `validate_config.py` to be one of the two allowed values; an invalid setting raises `ConfigError` at startup.

## Consequences

### Positive

- **Reduces lexical invention** in small/sparse clusters by constraining the model's vocabulary to observed words.
- **Allows the model to abstain** ("_Ambíguo") instead of fabricating, making low-signal clusters visible to the user rather than silently mislabeled.
- **Reinforces ADR 0003** (Ollama local naming with TF-IDF fallback): the grounded prompt strengthens the LLM path; failure still gracefully falls back to TF-IDF.
- **Backwards compatible**: setting `naming.prompt_variant = "default"` restores the original behavior verbatim.

### Negative

- **Loss of generative flexibility**: the grounded prompt may produce less creative names in clusters where lexical invention would have been an asset (e.g., abstracting a list of bird species into "Ornitologia" — the anchoring forbids the abstraction). Mitigation: this trade-off is the explicit goal; the Likert pilot showed users prefer correct-but-mundane to creative-but-invented.
- **Extra TF-IDF computation** per LLM call. Mitigation: the same TF-IDF vectorizer is run anyway as part of the fallback path; the added cost is negligible.
- **Validation only at the LLM**: the grounded prompt asks the model to use anchor words, but the model can ignore the instruction. The post-hoc sanitization (`_strip_trailing_connectives`) protects against the connectives-at-end case, but no validation enforces that the generated name's words are actually present in the cluster — that's left to the model's compliance.

## Out of scope

- **Empirical re-validation with raters.** A 2nd Likert round or blind A/B preference test is deferred until all three failure modes of the pilot are addressed (modo 3 covered by ADR 0023). See `docs/learning/...` (forthcoming) for the rationale on aligning the system before re-validating.
- **Validation that generated words come from the cluster text.** Could be added as a post-hoc check that falls back to TF-IDF if violated; deferred until empirical evidence shows the grounded prompt itself doesn't fully eliminate invention.
- **Alternative anchor extraction methods** (e.g., named-entity recognition, frequency-only, embedding-cluster centroids in word-vector space). TF-IDF is a simple and well-understood baseline; alternatives are future work.
- **Prompt translation to other languages.** The grounded template is in PT-BR; an English variant is straightforward but unrelated to the current corpus base.
