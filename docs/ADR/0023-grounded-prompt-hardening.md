# ADR 0023: Grounded prompt hardening — system role + light normalization

## Status
Accepted

## Context

ADR 0022 introduced the grounded prompt variant (anchor terms + escape hatch + sanitization). Unit tests proved the design mechanically. The user then ran the new default on her own corpus under `llama3.1:8b` and shared a screenshot whose outputs contradicted the prompt's intent: meta-text bleeding (`_Pastas de PDF_ Justificativa O nome`, `Pipeline O nome da pasta foi escolhido`), escape-token paraphrasing (`Nenhum` instead of literal `_Ambíguo`), and residual lexical invention (`TCC SI Moades`, `Julia Curricula`).

A first draft of this ADR proposed three combined interventions: (A) swap the model to `qwen3.5:4b`, (B) split the prompt into `system` + `prompt` Ollama fields, (C) reject outputs containing instruction-bleed meta-tokens or longer than five words.

Auto-inspection then narrowed the scope:

1. **`qwen3.5:4b` is unusably slow** on the user's local hardware — ~60 seconds to respond to a one-word greeting; ~3 minutes per cluster during a `characterize` run. Model swap is rejected for now. Reverted to `llama3.1:8b`.
2. **The system role split alone produces acceptable outputs** under llama3.1:8b. A follow-up screenshot showed clean labels (`CertificadosPdf`, `HISTÓRICO ESCOLAR`, `Comprovantes`, `Janelas Arquitetura Certificados`) — no meta-text bleed, no invented words. The earlier failures appear sample-rare; the role split mitigates them empirically.
3. **The meta-token / sentence rejection rules carry false-positive risk** without proving they catch frequent failures. Multi-word labels and labels containing tokens like "pasta", "documento", "tema" are legitimate; rejecting them in defense of rare bleed cases is a poor cost-benefit trade.

The remaining defensible interventions are: the system role split (cheap, helps small models, no false-positive surface) and a narrow ambiguity-synonym normalization (catches `Nenhum`/`Vazio`/etc. with no risk to legitimate labels, because the synonym set is unambiguous).

## Decision

### (B) System role + simplified prompt

Ollama's `/api/generate` accepts a `system` field separate from `prompt`. The grounded variant now splits:

- `_GROUNDED_SYSTEM_MESSAGE` (stable per request): role declaration + PRINCÍPIO DE ANCORAGEM + REGRAS RÍGIDAS + escape-token instruction. Sent in the `system` field on every grounded call.
- `_GROUNDED_USER_TEMPLATE` (per-call data): anchor terms list + files block + final "Nome:" cue. Sent in the `prompt` field.

The `system` field gives the model a stable role identity ("you are a classifier") outside the per-call data stream. Smaller models hold the role more consistently than they hold instructions interleaved with data, reducing meta-text bleed.

The default variant (`prompt_variant = "default"`) is unchanged: single `prompt` field, no `system` — preserving backward compatibility.

### (C1) Light ambiguity normalization

A new pure function `_normalize_ambiguity_synonyms(out: str) -> str` runs between the raw LLM response and the existing `sanitize_windows_folder_name` call. Behavior:

- If the stripped, lowercased output is in `_AMBIGUITY_SYNONYMS` (`nenhum`, `vazio`, `indefinido`, `incerto`, `ambíguo`, `ambiguo`), return `"_Ambíguo"`.
- Otherwise, return the stripped output unchanged.

The synonym set is intentionally narrow: each entry is unambiguous as a folder label (no one names a folder "Nenhum" intentionally), so false-positives are practically nil. This catches the model's tendency to paraphrase the literal escape token, which the grounded prompt design depends on.

## What this ADR does NOT do

- **No model swap.** The first draft proposed `qwen3.5:4b`. Local profiling rejected it for unacceptable latency. The model remains `llama3.1:8b`. Future sensitivity analysis on other models is deferred.
- **No meta-token rejection.** The first draft proposed rejecting outputs containing tokens like `nome`, `pasta`, `documento`, `tema`. False-positive risk on legitimate labels was higher than the rare-bleed catch rate. Removed in favor of trusting the system role split.
- **No sentence-length rejection.** Same reasoning: the 5-token boundary was speculative and risked rejecting legitimate multi-word labels.
- **No word-by-word anchoring enforcement** (the ADR 0022 deferred item): remains deferred. Generative flexibility is preserved.

## Consequences

### Positive

- **Cheap and conservative.** Two changes only: prompt structure (no runtime cost) and one normalization function (~5 lines). Zero false-positive surface.
- **Empirically acceptable.** Auto-inspection screenshot post-system-role-split shows clean labels under llama3.1:8b.
- **Backwards compatible.** Default variant unchanged. Grounded variant's system field is transparent to user-facing config (no new required keys).

### Negative

- **No safety net against future regressions.** If the LLM behavior degrades and meta-text bleed returns, it will surface as ugly labels in the proposal tree with no automatic fallback. The user will notice and we will reopen this ADR.
- **`_Ambíguo` is the only normalized escape.** If the model finds another way to communicate ambiguity (e.g., "Sem categoria", "Diversos"), the normalization won't catch it. Iteration is possible if patterns emerge.

## Out of scope

- Model sensitivity sweep (qwen2.5:7b, gemma2:9b, mistral-nemo:12b): deferred to post-defense.
- Portuguese-specific finetuned models (cabrita, sabiá, bode): Ollama registry support inconsistent; deferred.
- Empirical re-validation with raters: deferred to a phase after all three β failure modes are aligned (β.3 covers modo 3).
- Few-shot prompting in the system message: not needed under current observations.
