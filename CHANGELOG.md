# Changelog

## Unreleased - External Evaluation

### Features
- **External Evaluation (ARI + NMI + AMI):** New `external-eval` subcommand compares the proposed top-level grouping against a human-made reference partition (a semicolon-separated `caminho_relativo;rótulo` CSV covering every scanned file) and reports Adjusted Rand Index, Normalized Mutual Information, and Adjusted Mutual Information. Complements the existing unsupervised `compare` metrics (Silhouette + DBCV) with a supervised comparison against a labeling you provide yourself. (ADR 0047)

## 1.3.0-TCC (2026-06-07) - Native UI & Branding Release

### Features
- **Native Desktop UI (pywebview):** Replaced the Textual terminal UI with a native OS window (EdgeWebView2 on Windows) that renders the V1 "Sereno" React design at full fidelity — file explorer, live pipeline progress, and a click-to-accept proposal view. Launched by `dynamic-folding` with no args or `tui`. (ADR 0029, 0030)
- **Brand Identity:** New "Geometric Fold" mark + lockup applied to the window/taskbar icon (a shipped multi-size `.ico`, replacing the default Python icon), the in-app header, and the HTML report header. (ADR 0034)
- **Redesigned HTML Report:** The on-accept report now matches the V1 Sereno design system (PT-BR, proposal tree with amber folder icons and pill counts, technical detail in a collapsed "Detalhes técnicos" footer) and stays fully self-contained / offline. (ADR 0032)

### Technical Improvements
- **Faster proposals:** The SBERT model is cached per process instead of being reloaded on every cluster-name embedding — eliminating the repeated multi-second "Loading weights" reloads that dominated the proposal stage. (ADR 0031)
- **Honest staging & quiet GUI:** The `proposal` stage is emitted last (after the `clustering`/`naming` markers); ML-library progress bars and logging are silenced while the GUI is the progress surface; JSX is precompiled to `app.js` (no in-browser Babel at launch). (ADR 0031)
- **Lighter install:** The ~3 MB vendored `babel.min.js` is excluded from the wheel (kept in-repo for offline regeneration of `app.js`); removed the redundant `[extract]` optional extra.
- **Dead-code removal:** Removed the unreachable Textual TUI stack (`tui/app.py`, `core/triage.py`, the never-called `confirm_proposal`) and the `textual` dependency. (ADR 0033)

### Documentation
- **Project Audit (`docs/AUDIT.md`):** Catalogued inconsistencies, dead code, packaging bloat, and stale docs with a prioritized backlog; tranches T1–T3 executed in this release.
- **Docs sync:** Corrected stale Textual references, contract-version labels, the pipeline stage list, and ADR statuses across SPEC/CONTRACTS/CLAUDE/README; aligned `__version__` with `pyproject`.
- **New ADRs 0031–0034** (perf/staging, report restyle, Textual removal, branding).

## 1.2.0-TCC (2026-05-10) - Empirical Characterization Release

### Features
- **Empirical Characterization Tooling:** New `characterize` subcommand orchestrates structure-finding, stability, and performance measurement on a corpus and writes a timestamped JSON to `characterization_results/`. New `analyze` subcommand aggregates those JSONs into a Markdown spine table and per-corpus sensitivity figures. New `experiment` subcommand chains a spine run + sensitivity sub-study + analyze in one call.
- **PDF Smart Structural Extraction:** PDF extractor now mirrors the priority-then-backfill pattern from Office documents — `/Subject` and `/Keywords` metadata plus the bookmark outline are prioritized; first-3-pages body text backfills only if the priority block is short of `snippet_size`.
- **Streamlined SBERT Setup:** New `setup-sbert` command performs a one-shot, idempotent local model download (default `paraphrase-multilingual-MiniLM-L12-v2`, Portuguese-suitable). Pipeline auto-discovers a single model under `%LOCALAPPDATA%/DynamicFolding/models/` when `embedding.model_path` is unset, removing manual config editing for the default flow.
- **TUI Polish:** Directory picker filters dot-folders (`.git`, `.cache`, …) via a new `FilteredDirectoryTree`. Panel-based welcome screen with rounded borders. New `ErrorScreen` surfaces pipeline failures interactively instead of crashing to a traceback. Stage progress now uses status icons (spinner → check) for visible per-stage feedback.
- **TUI Configuration Parity:** `tui` subcommand now accepts `--config` and shares the resolution path used by `run`, `characterize`, and `experiment` — eliminating the silent default-divergence that produced low-quality cluster names in the TUI.

### Technical Improvements
- **Pair-Stability Metric:** Replaced the prior cluster-shape proxy with `1 − 4·p·(1−p)` over pair co-occurrence under input perturbation. Peaks at perfectly stable (p∈{0,1}) groupings, bottoms at random (p=0.5). Documented in `docs/learning/01-stability-metric.md`.
- **Random Clusterer Baseline:** New `random` clusterer (`dynamic_folding/clustering/random_baseline.py`) provides the floor against which `silhouette_real` is reported, so the structure-finding claim is bounded against noise.
- **Per-Stage Pipeline Instrumentation:** `RunResult` now carries `timings: dict[str, float]` and `peak_memory_mb: float | None`, populated via `time.perf_counter` deltas around scanner, extractor, preprocess, embedding, and proposer stages. Memory is read via `psutil.Process().memory_info().rss` when available.
- **Visible Ollama Fallback Logging:** Every `ollama → tfidf` fallback path now prints a one-line reason to stderr (`[ollama->tfidf] <reason>`). Silent failures previously masked "is `ollama serve` running?" diagnostics behind TF-IDF cluster names.

### Documentation
- **ADR 0018 — Empirical Characterization Without Ground Truth:** Reframes the chapter from validation to characterization across five properties (structure, stability, sensitivity, scaling, perceived utility). Rejects ARI/NMI/V-measure on epistemological grounds for unsupervised clustering of personal corpora.
- **ADR 0021 — PDF Smart Structural Extraction:** Extends the Sprint 17 priority-then-backfill pattern to PDFs.
- **Learning Notes 01–04:** Stability metric math, experimental scope (spine + sub-study), SBERT setup rationale, and bisectable-changes-and-visible-failures (engineering-process journal of Phase 1 reconciliation).
- **SPEC Additions:** Sprint 19 (empirical characterization) and Sprint 22 (PDF smart extraction) sections.

## 1.1.0-TCC (2026-05-01) - Advanced Research Release

### Features
- **Smart Office Extraction:** Support for `.docx` and `.pptx` documents, intelligently prioritizing headings and slide titles for high-density semantic signals.
- **Hierarchical Subdivision:** Support for recursive re-clustering, allowing deeper folder structures (up to `max_levels`) for all clustering algorithms.
- **Unified TUI Experience:** A consolidated Textual application with a visual directory browser, real-time pipeline progress, and interactive color-coded triage.
- **Adaptive Chunk Pooling:** Improved semantic signals for long documents (e.g., multi-page PDFs) using sliding-window chunking and mean pooling.
- **Name Validation:** Integrated vector similarity scoring (`name_score`) between cluster centroids and proposed folder names.
- **Batch Pipeline Execution:** Generator-based execution for constant memory pressure, enabling processing of 1,000+ files.

### Technical Improvements
- **Registry Type Protocols:** Formalized provider interfaces using Python Protocols for better type safety and modularity.
- **Naming Quality & Robustness:** Improved Ollama prompts, smart space-aware truncation, and graceful fallbacks for empty clusters.
- **Lazy Text Loading:** Reduced memory footprint by lazy-loading content from SQLite for naming and validation stages.
- **Granular Progress:** TUI now provides distinct progress bars for Extractor, Preprocess, Embedding, Clustering, and Naming stages.

## 1.0.0-TCC (2026-04-30) - Thesis Release

### Features
- **The Matrix (Grid Search):** Automated command `benchmark` to test dozens of configuration combinations (Algorithms x Embedders x Hyperparameters).
- **Type-Aware Extraction:** Rich support for PDF (pypdf) and Images (Pillow) to extract snippets and internal metadata.
- **Intrinsic Validation:** Integrated Silhouette Score (`cohesion_score`) for empirical result evaluation.
- **Interactive Triage:** New `--interactive` flag with color-coded confidence visualization (Green/Yellow/Red).
- **HDBSCAN Support:** Added density-based clustering for identifying natural groups and noise.
- **Hierarchical Clustering:** Stable `agglomerative_tree` provider for multi-level folder proposals.
- **Tiered Configuration:** Robust system with hardcoded defaults, TOML project config, and runtime dictionary overrides.

### Technical Improvements
- **Deep-Merge Engine:** Recursive configuration merging for easier hyperparameter tuning.
- **Safe Preprocessing:** Robust template formatting that handles missing metadata gracefully.
- **Deterministic Pipeline:** Seeded randomness and stable sorting for research reproducibility.

## 0.1.0 (2026-04-29) - Initial Research Baseline

- Add SBERT embedding provider (`embedding.provider = "sbert"`) using a user-supplied local model directory.
- Add Ollama naming provider (`naming.provider = "ollama"`) restricted to loopback URLs.
- Wire naming providers through the registry into the proposer.
- Extend config validation for SBERT/Ollama required keys and offline constraints.
