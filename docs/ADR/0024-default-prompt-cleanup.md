# ADR 0024: Default prompt cleanup — concrete domain examples removed

## Status
Accepted

## Context

After ADR 0023 (β.2.b hardening, system role + ambiguity normalization),
the recommended variant became `grounded` and `llama3.1:8b` was kept as
the default model. The user then switched her local config to
`model = "gemma3:1b"` (speed) and `prompt_variant = "default"` (wanting
to understand the default's behavior before relying on grounded as a
de-facto fix). Under that configuration two corpora produced
top-level clusters with duplicate names disambiguated by the proposer
(`Certificação de Janelas_2`, `Licitações_2`).

A focused diagnostic was added in Phase D (PR #26): an opt-in JSONL
logger inside `name_cluster_ollama` triggered by the env var
`DYNAMIC_FOLDING_NAMING_DEBUG_PATH`. The user ran on the Certificados
corpus and produced six records capturing the exact `files_block`
sent to the LLM and the verbatim `raw_response` for each cluster.

### Findings from the diagnostic

| # | Files (filenames; `[CONTENT]:` empty in all six) | LLM output | Match? |
|---|---|---|---|
| 1 | "certificado semana de desenvolvimento profissional", "comprovante avaliação institucional" | `Certificação Janelas` | ❌ |
| 2 | "certificado janelas da arquitetura 1..8" | `Certificação de Janelas` | ✅ |
| 3 | "NBR12284", "NBR13532", "NBR6492" | `Licitações` | ❌ |
| 4 | "HISTÓRICO ESCOLAR" (5x) | `Histórico-Escolar` | ✅ |
| 5 | "Certificado EIGEDIN, IC, Integra, arqfest" | `Certificado-arqfest` | ⚠️ |
| 6 | "CERTIDÃO NASCIMENTO", "CNI", "CPF", "Declaração Matrícula" | `Certificação de Janelas` | ❌ |

The `_DEFAULT_PROMPT_TEMPLATE` carried two literal example phrases in
its rules:

- Rule 1: `(ex: "Licitações", "Projetos Hidráulicos")`
- Rule 5: `Use "Certificação de Janelas", não "Certificar Janelas"`

Records 1, 3, and 6 contain **no overlap** between the `files_block`
and the produced name — the LLM returned the prompt's own example
phrases as the answer. Records 2 and 4 worked because each filename
in the cluster contained the same dominant noun repeated at least
five times, giving the model strong signal that overrode the
example-regurgitation pattern.

This is well-known small-model behavior: when content signal is
weak, recently-seen tokens from the prompt dominate output.
`gemma3:1b` at one billion parameters is squarely in the range where
this happens.

### Implication for β.3 (adaptive hierarchy)

The original plan placed β.3 (meta-clustering of semantically close
top-level clusters) as the next phase to address modo 3 of the
Likert pilot. The Phase D data refutes β.3's premise for the
observed duplicates: records 1 and 6 have **completely different
file sets** (institutional certificates vs. civil documents) but
were assigned near-identical names. The duplication is a naming
failure, not a clustering failure. Merging the wrongly-named
clusters via β.3 would produce wrongly-named meta-clusters. β.3 is
deferred until (a) the naming bug is corrected and (b) fresh data
shows clusters that are actually semantically close.

## Decision

### (A) Remove all concrete domain examples from `_DEFAULT_PROMPT_TEMPLATE`

The Phase D evidence is direct: small models default to recent
prompt tokens when signal is weak. The discriminating fix is to
remove the example tokens entirely (substituting them would only
shift which strings get regurgitated).

Rules 1, 2, and 5 of the default template now state principles
without naming any folder-label or banned-token example. The
template carries a header comment warning future contributors not
to reintroduce concrete examples without re-testing under a small
model first.

### (B) Reaffirm `grounded` as the recommended default variant

`prompt_variant = "grounded"` was already the value in
`config/default.toml` (set by ADR 0022, β.2 merge). The
`_GROUNDED_SYSTEM_MESSAGE` from ADR 0023 contains no concrete
domain examples by design — only abstract principles plus the
`_Ambíguo` escape token. It does not have the surface where the
prompt-poisoning failure mode lives.

This ADR makes the recommendation explicit: the comment in
`config/default.toml` now documents that `grounded` is the
recommended variant for small models (1–4 B params), with a
cross-reference to this ADR for the underlying evidence.

## What this ADR does NOT do

- **No model swap.** The user's explicit constraint is to stay on
  `gemma3:1b` for speed. ADR 0023 already rejected `qwen3.5:4b`
  for latency. A larger-model sensitivity sweep remains out of
  scope.
- **No OCR.** All six records had empty `[CONTENT]:` blocks. The
  type-aware extractor is not pulling text from these scanned
  PDFs. This is a real secondary issue but does not block the
  naming fix — filenames carry usable signal when the prompt
  isn't poisoning the output. A separate investigation is queued
  to decide whether to integrate optional OCR.
- **No β.3.** Adaptive hierarchy is deferred indefinitely, pending
  fresh evidence of clusters that are actually semantically close.
- **No retroactive change to ADR 0023.** The hardening it
  documented (system role split, ambiguity normalization) remains
  correct. The new finding is orthogonal: a bug in the *default*
  variant, not in the grounded one.

## Post-fix evidence (rerun on the same Certificados corpus)

The same six clusters re-run on the same corpus after the template
cleanup produced these names:

| # | Files | Pre-fix | Post-fix | Δ |
|---|---|---|---|---|
| 1 | "avaliação institucional", "comprovante participação" | `Certificação Janelas` | `Certificados_Desenvolvimento` | ✅ cured |
| 2 | "certificado janelas da arquitetura 1..8" | `Certificação de Janelas` | `certos_janelas` | ⚠️ exposes pre-existing word-invention |
| 3 | "NBR12284", "NBR13532", "NBR6492" | `Licitações` | `NBR_Arquivos` | ✅ cured |
| 4 | "HISTÓRICO ESCOLAR" (5x) | `Histórico-Escolar` | `Histórico-Escolar` | unchanged |
| 5 | "Certificado EIGEDIN, IC, Integra, arqfest" | `Certificado-arqfest` | `Certificados` | ✅ better |
| 6 | "CERTIDÃO NASCIMENTO", "CPF", "CNI" | `Certificação de Janelas` | `Certidão` | ✅ cured |

Four clusters improved, one unchanged, one exposes a pre-existing
weakness. **All six produced distinct names**, eliminating the
duplicate-name problem that motivated Phase D.

### Note on record 2

Record 2 deserves explicit honesty. Pre-fix, the LLM returned
`Certificação de Janelas` for this cluster. That looks like a
correct answer for files that contain "certificado janelas",
but the Phase D data shows that exact phrase was sitting in
rule 5 of the prompt template as an example — the model was
copy-pasting the example, and the copy happened to match the
cluster's actual theme. The model got the right answer for the
wrong reason.

Post-fix, with the example removed, the model produces
`certos_janelas` — "janelas" is real (8 filename occurrences);
`certos` is **invented** (not present in any file). This is
exactly the word-invention failure mode that the grounded
variant was originally designed to forbid ("PRINCÍPIO DE
ANCORAGEM: Use APENAS palavras presentes no conteúdo dos
arquivos").

The cleaned default solves prompt-poisoning but does **not**
solve word-invention. The grounded variant solves both. This
sharpens, not muddies, the recommendation that grounded is the
correct default for small models.

## Consequences

### Positive

- **Honest fix.** The diagnostic produced concrete evidence; the
  change is narrow, surgical, and tied to the evidence.
- **Prompt poisoning eliminated.** Four of six previously
  poisoned clusters now produce content-derived names; no
  duplicate names in the rerun.
- **Future-proof against the same mistake.** The template carries
  a "do not add concrete examples" header comment that makes the
  invariant explicit for future contributors.
- **Backwards compatible.** The default variant still exists for
  users who explicitly opt into it; it now produces less-poisoned
  output. The grounded variant is unchanged.
- **β.3 escape velocity preserved.** The plan no longer commits
  resources to a hierarchy fix that the data does not justify.

### Negative

- **Cleaned default exposes pre-existing word-invention** (record
  2 — `certos_janelas`). The previous "good" answer for that
  cluster was coincidental copy-paste from the prompt; the
  cleaned default reveals the model's actual generation behavior.
  Users who explicitly opt into `prompt_variant = "default"` on
  small models should expect occasional invented words.
- **Default template loses structural hints.** Without concrete
  examples, very weak-signal clusters may default to even more
  generic outputs (`Documento`, `Arquivo`). The opt-in JSONL
  logger from PR #26 remains available to investigate any future
  regressions.
- **Two variables in one PR.** This change touches both the
  template content and the documentation surrounding the variant
  choice. A confounded variable in any direct re-run — but the
  variant-default was already grounded in main, so the operative
  change is only the template cleanup.

## Follow-up: grounded variant anchor-term pollution

A grounded-variant rerun on the same six clusters confirmed that
the cleaned default's record-2 word-invention (`certos_janelas`)
is eliminated under grounded (`Arquitetura` — a real token from
the files), but exposed a separate weakness: the TF-IDF anchor
extraction is polluted by tokens from the preprocess template
(`pdf`, `file`, `ext`, `content` — emitted from the literal
`[FILE]:`, `[EXT]:`, `[CONTENT]:` markers that prefix every
file's text in `config/default.toml::preprocess.template`).

Concrete failures from the grounded rerun:

| # | Anchor terms emitted | Output | Issue |
|---|---|---|---|
| 3 | `pdf, para, fls, impressão, content` | `_Ambíguo` | No real distinguishing token (e.g., "NBR") survived TF-IDF; model defaults to escape hatch |
| 5 | `pdf, ext, file, content, certificado` | `Certificado-pdf` | "pdf" leaked into the folder name |
| 6 | `de, pdf, file, ext, content` | multi-line garbage | No distinguishing signal at all |

Grounded is therefore **not strictly better** than cleaned default
on this corpus under `gemma3:1b`. A separate fix is needed in
`dynamic_folding/naming/tfidf.py::extract_anchor_terms`: introduce
a stopword set blocking template-emitted tokens (`pdf`, `file`,
`ext`, `content`, and any future markers), or feed TF-IDF the
pre-template filename string instead of the formatted snippet.

### Phase E resolution

The stopword-set approach was implemented in PR for branch
`fix/anchor-terms-pollution`. `_TEMPLATE_STOPWORDS` in
`dynamic_folding/naming/tfidf.py` blocks the literal template
markers (`file`, `ext`, `content`) plus common file extensions
(`pdf`, `docx`, `pptx`, `xlsx`, `txt`, `csv`, `json`, image
formats, archive formats) before TF-IDF ranking. The change is
~30 lines including the stopword set and the
`TfidfVectorizer(stop_words=...)` integration; a regression test
asserts that template tokens do not leak and real content
(`certificado`) survives. Future contributors who add markers to
the preprocess template should also append them to
`_TEMPLATE_STOPWORDS` to preserve the invariant.

## Out of scope

- OCR integration for scanned PDFs (separate investigation queued).
- Model swap or sensitivity sweep across other Ollama models.
- β.3 adaptive hierarchy (deferred indefinitely pending fresh
  data).
- Re-validation with raters (postponed until the system is
  aligned across the three Likert failure modes and the advisor
  meeting has happened).
