# ADR 0031: TUI performance & staging hardening

## Status
Accepted

## Context

Field review of the pywebview V1 Sereno UI (ADR 0030) surfaced four issues, all
root-caused to concrete bugs rather than to the GUI layer:

1. **Repeated SBERT model reloads.** `embed_sbert_with_cache`
   (`dynamic_folding/embedding/sbert.py`) constructed `SentenceTransformer(...)`
   on *every* call, before the cache lookup. The proposer embeds each cluster /
   folder name individually through `embed_text_callback`
   (`dynamic_folding/core/pipeline.py`), so a multi-level proposal reloaded the
   model 15–30× from disk during the proposal stage — the repeated
   `Loading weights: 100%` terminal spam and the dominant cost of "Gerar
   proposta". The main embedding stage also reloaded once per batch.

2. **Misleading stage order.** `run_pipeline` opened the `proposal` stage first,
   then emitted `clustering` and `naming` as instant no-op sub-stages *inside*
   it, then ran the real `proposer()`. Because the UI lists stages in emission
   order and the no-ops complete immediately, "Gerar proposta" appeared mid-list
   and sat spinning while "Agrupar arquivos" / "Nomear categorias" already read
   *Concluído*.

3. **Noisy terminal in GUI mode.** HuggingFace / transformers progress bars and
   logging printed to the host terminal while the webview was the intended
   progress surface.

4. **In-browser JSX transpile on every launch.** `index.html` loaded
   `babel.min.js` (~3 MB) and transpiled `app.jsx` in the webview on every
   launch, adding startup latency.

## Decision

### 1. Process-level SBERT model cache
Introduce `_MODEL_CACHE` and `_load_model(...)` in `sbert.py`, keyed by
`(resolved model_path, device)`. The model loads at most once per process and is
reused thereafter. The offline env guards (`HF_HUB_OFFLINE`,
`TRANSFORMERS_OFFLINE`) wrap only the first, real load.

Determinism is preserved: `model_id` is still derived from
`model_path`/`normalize`/`st_version`/`chunk_cfg` via `_stable_model_id`,
unchanged. The embedding SQLite cache key is unaffected — **no cache bust
needed**.

### 2. Proposal stage emitted last
`run_pipeline` now emits the lightweight `clustering` and `naming` markers as
siblings *before* a single final `proposal` stage that wraps the real
`proposer()` call. Emission order becomes
`scan → extractor → preprocess → embedding → reducer → clustering → naming →
proposal`. The `timings` dict keys are unchanged (the Sprint 19 performance
contract still sees `clustering`/`naming`/`proposal`).

### 3. Quiet ML libraries in GUI mode
`launch_webview()` calls `_quiet_ml_libraries()`, which sets (via
`os.environ.setdefault`, offline-safe) `HF_HUB_DISABLE_PROGRESS_BARS=1`,
`TRANSFORMERS_VERBOSITY=error`, `TRANSFORMERS_NO_ADVISORY_WARNINGS=1`,
`TOKENIZERS_PARALLELISM=false`. Combined with fix 1 (one load, not many) the
host terminal stays quiet.

### 4. Pre-compiled frontend
`app.jsx` is transpiled once, offline, to `app.js` using the already-vendored
`vendor/babel.min.js` under Node. `index.html` loads `app.js` as a plain script
and no longer loads `babel.min.js` or uses `type="text/babel"`. `app.jsx`
remains the editable source; the regeneration command is documented inline in
`index.html`. React dev builds are kept (production UMD builds were not vendored
to respect the offline / no-CDN boundary).

## Consequences

### Positive
- "Gerar proposta" is fast: the SBERT model loads once, not per cluster name.
- Stage list reads in dependency order with "Gerar proposta" last.
- Quiet host terminal; the webview is the sole progress surface.
- Faster window open — no in-browser Babel transpile per launch.

### Negative / notes
- The vendored `babel.min.js` is retained (referenced only by the documented
  regeneration command); it is dead weight at runtime but enables offline
  regeneration of `app.js`.
- Switching to production React UMD builds remains a small future win but
  requires vendoring two files, which the offline policy blocks from CDN.
- Clean process exit after the webview closes is a known
  pywebview + WebView2/Windows teardown concern; verified by a real run rather
  than added pre-emptively.

## Files changed
- `dynamic_folding/embedding/sbert.py` — `_MODEL_CACHE` + `_load_model`
- `dynamic_folding/core/pipeline.py` — proposal staging reorder
- `dynamic_folding/tui/webview_app.py` — `_quiet_ml_libraries()` on launch
- `dynamic_folding/tui/web/index.html` — load pre-compiled `app.js`, drop Babel
- `dynamic_folding/tui/web/app.js` — new, pre-compiled from `app.jsx`
- `docs/ADR/0031-tui-performance-and-staging-hardening.md` — this document
- `docs/SPEC.md` — stage-order note
