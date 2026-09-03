# SPEC (MVP)

## Objective

Build an **offline**, **Windows-first** tool that scans a directory and **proposes** a semantic organization structure, without moving files.

CLI:

```bash
dynamic-folding run <dir>
```

Output is rendered as a tree to the terminal — Unicode box-drawing glyphs (`├── `, `└── `, `│   `) by default, ASCII fallback (`|- `, `|  `) when `use_emojis=False`. The tree is preceded by a one-line summary preamble (`Proposta: N pastas, M arquivos · K em "Outros"`) and the root path. Each folder line shows the file count inline (`(N arquivos)`); low-confidence folders additionally receive a `· verificar` cue. Folders are ordered by confidence DESC, then file-count DESC, then name ASC; the outlier bucket ("Outros") is always rendered last and consolidates `proposal.outliers_folder` files together with top-level orphans. The raw silhouette score is hidden by default and can be restored via `--scores`. The internal representation is JSON-friendly to enable future native UIs.

An optional self-contained HTML report (`report.enabled`) is emitted on TUI accept / `run`. It is styled to match the V1 Sereno GUI design system (PT-BR, proposal tree with amber folder icons and pill counts, technical detail in a collapsed "Detalhes técnicos" footer) and stays fully offline — inline SVG icons, system fonts, no CDN. See ADR 0032.

The interactive UI is a **pywebview desktop window** (V1 Sereno), launched by `dynamic-folding` with no args or `tui` and driven by mouse/buttons (*Iniciar análise* → pipeline → *Aplicar proposta* / *Recomeçar*). This supersedes the Textual-based descriptions in the Sprint 9/12/14 sections below; JSX is precompiled to `app.js` (ADR 0031), so `babel.min.js` is not loaded at runtime. See ADR 0030–0032.

## Non-goals (MVP)

- No file moves/copies/deletes
- No OS-native context menu integration
- ~~No content extraction (metadata-only)~~ **— superseded.** Content extraction was added from Sprint 7 onward (see "Type-Aware Extraction" below) and is now the default: the `type_aware` extractor reads a bounded content snippet (`scanner.snippet_size`, default 4096) plus rich metadata. See ADRs 0017/0021/0025/0036 and the retirement record in ADR 0044.
- No remote / cloud LLM naming (offline-only)

## Constraints

- Offline only (no network calls)
- Python 3.11+
- Max ~200 files initially
- Scan depth limited to 2 sublevels: `root/level1/level2`
- Must support subgroups (two levels of proposed folders) from the start

## High-level Pipeline

1. File Scanner
2. Extractor Layer
3. Preprocessor
4. Embedding Engine
5. Clustering Engine
6. Folder Namer
7. Structure Proposer & Renderer

Progress is surfaced to the UI in this dependency order; the proposal stage
(`proposal`) is emitted **last**, after the `clustering` and `naming` markers,
so "Gerar proposta" reads as the final long-running step (see ADR 0031).

## Architectural Rules

- Each stage is a **Strategy plugin** registered in a `Registry`.
- Stages communicate only via **contracts** (DTOs) defined in `docs/CONTRACTS.md`.
- Behavior changes via config; swapping algorithms should not require refactors.
- Pipeline is UI-agnostic.

## Acceptance Criteria (MVP)

- `dynamic-folding run <dir>` runs on Windows and prints a tree.
- Scans up to depth 2; ignores deeper paths.
- Produces a `StructureProposal` (contracts v1) with up to 2 levels of folders.
- Deterministic output given same input + config.
- Tests run offline and do not require ML models.

## Configuration (MVP)

We use TOML for configuration.

- Default config file: `config/default.toml`
- CLI uses defaults unless overridden later (not in Sprint 1).

Initial keys:

- `scanner.max_depth = 2`
- `scanner.max_files = 200`
- `scanner.ignore_hidden = true`
- `scanner.ignore_globs = ["**/.git/**", "**/node_modules/**"]`

Sprint 1 implements scanner + basic metadata extraction wired to the pipeline.

## Milestones

1. Sprint 0: scaffolding (CLI, contracts, docs, test harness)
2. Sprint 1: config (TOML) + scanner + metadata extractor + proposal skeleton
3. Sprint 2: embedding interface + SQLite cache + fake embedding for tests
4. Sprint 3: clustering + TF-IDF naming + 2-level hierarchy proposal
5. Sprint 4: robustness (ignore rules, errors, perf for ~200 files)
6. Sprint 5: optional local LLM naming plugin (fallback remains TF-IDF)
7. Sprint 6: hierarchical clustering (auto-K) + outliers to review folder
8. Sprint 7: Type-Aware extraction (Rich Metadata + Snippets)

## Sprint 5: Local SBERT Embeddings + Ollama Naming (Optional)

### Goals

- Add `embedding.provider = "sbert"` using `sentence-transformers` with a user-supplied *local* model directory.
- Add `naming.provider = "ollama"` using a local Ollama server for naming, with automatic fallback to `tfidf` on failure.
- Keep the system offline-only: no downloads, no remote endpoints.

### Configuration Keys (Sprint 5)

Embedding:

- `embedding.provider = "sbert"`
- `embedding.model_path: str` (required)
  - Must be an existing local directory (or a local model snapshot directory).
  - The provider must refuse to download model files.
- `embedding.batch_size: int` (default: 32)
- `embedding.device: str` (default: "cpu")
  - Examples: "cpu", "cuda" (if available).
- `embedding.normalize: bool` (default: true)
  - If true, vectors are L2-normalized.
- Cache semantics (uses existing `embedding.cache_db`):
  - Cache key MUST incorporate the effective model identity and the preprocessed text hash.
  - Changing any of: `model_path`, `normalize`, or the embedding implementation version MUST change the cache `model_id` so old vectors are not reused.

Naming:

- `naming.provider = "ollama"`
- `naming.base_url: str` (default: "http://127.0.0.1:11434")
  - Must be loopback/local only.
- `naming.model: str` (required)
- `naming.timeout_s: float` (default: 30)
- `naming.top_k_files: int` (default: 25)
  - Maximum number of file snippets (stems/paths/exts) included in the prompt for a cluster.
- `naming.prompt_template: str` (default provided by implementation)
  - Supports placeholders like `{terms}`, `{files}`, `{rules}`.
- Failure behavior:
  - If Ollama is missing/unreachable/times out/returns invalid output, naming MUST fall back to `tfidf` for that cluster.
- `proposal.naming_direction: str` ∈ `{"per_node", "bottom_up"}` — see
  [ADR 0037](ADR/0037-bottom-up-hierarchical-naming.md). `per_node` (system default,
  legacy): every folder named independently from its own documents. `bottom_up`
  (`config/default.toml` default): leaf clusters named from documents, each parent
  then synthesized from its children's names + loose-file terms (Ollama summarization
  with deterministic `tfidf.aggregate_name` fallback). Naming-only — folder/file
  membership and nesting are identical across both directions.

### Acceptance Criteria (Sprint 5)

- Config validation:
  - `embedding.provider = "sbert"` requires `embedding.model_path` and it must be a local directory.
  - `naming.provider = "ollama"` requires `naming.model`; `naming.base_url` defaults to loopback and non-loopback URLs are rejected.
- Offline constraints:
  - SBERT provider MUST NOT download models under any circumstance; it must fail fast with a clear error if `model_path` is not usable.
  - Ollama naming uses local HTTP only; if it cannot connect to the local server it falls back to TF-IDF without failing the entire run.
- Determinism and tests:
  - Default unit tests remain model-free and do not require SBERT/Ollama.
  - Optional integration tests are gated by environment/model presence and are skipped by default.

## Sprint 6: Hierarchical Clustering (Auto-K) + Outliers

### Goals

- Replace the current 2-level hierarchy hack (running a flat clusterer twice) with a true hierarchical clustering output.
- Discover the number of clusters automatically (no fixed `k`).
- Detect outliers and route them to a dedicated folder (default: `Outros`).
- Prefer stable, non-trivial clusters; default `min_cluster_size = 4`.
- Keep proposal depth separate from scanner depth:
  - `scanner.max_depth` controls how far we *scan*.
  - `proposal.max_levels` controls how deep we *suggest* folders.

### New Clustering Option(s)

Add a clustering algorithm option that produces a hierarchy:

- `clustering.algorithm = "agglomerative_tree"`
  - Implementation uses scikit-learn agglomerative clustering to produce a linkage tree (dendrogram).
  - The hierarchy is cut into a flat partition to propose folders, but the underlying tree is used to derive multiple folder levels.

### Proposal Controls (Sprint 6)

- `proposal.max_levels: int` (default: 2)
  - Maximum suggested folder depth (levels of grouping) in the output proposal.
  - This does not affect scanning.
- `proposal.outliers_folder: str` (default: "Outros")
  - Folder name used to collect outliers/small clusters.
  - Must be Windows-safe per existing naming rules.

### Clustering Controls (Sprint 6)

- `clustering.min_cluster_size: int` (default: 4)
  - Clusters smaller than this are not emitted as folders; their members are routed to `proposal.outliers_folder`.
- Tree cut control (choose one):
  - `clustering.distance_threshold: float` (optional)
    - If provided, the tree is cut at this distance to form the first-level partition.
  - `clustering.cut_strategy: str` (default: "auto")
    - If `distance_threshold` is not set, derive a cut automatically from the tree distances and `min_cluster_size`.

### How K Is Derived (Cutting The Tree)

Definitions:

- The agglomerative algorithm builds a binary merge tree with merge distances.
- A cut is defined by a distance threshold `t` which yields a flat partition (a set of clusters).

Cut strategy:

- If `clustering.distance_threshold` is set:
  - Use it directly (deterministic; user-controlled).
- Otherwise (`clustering.cut_strategy = "auto"`):
  - Enumerate candidate thresholds: one midpoint between each pair of consecutive distinct merge distances.
  - For each candidate threshold, compute the flat partition.
  - Select the threshold that maximizes:
    - primary: number of files in clusters whose size is ≥ `min_cluster_size` (non-outlier coverage)
    - secondary: lower threshold (prefer tighter, more granular clusters when coverage is equal)
  - See ADR 0005 for why the "fewer non-outlier clusters" secondary from the original description was not implemented.

The derived `K` is the number of clusters ≥ `min_cluster_size` at the selected threshold.

### How Outliers Are Decided

- After selecting the cut threshold, any cluster whose size is `< clustering.min_cluster_size` is treated as an outlier cluster.
- All files in outlier clusters are placed under `proposal.outliers_folder`.
- `Outros` may be empty; it is only emitted if it has members.

### Hierarchy / Folder Depth (`proposal.max_levels`)

- Level 1 folders come from the selected first cut.
- If `proposal.max_levels > 1`, each non-outlier cluster may be subdivided by applying the same cut logic to the cluster's subtree to form subfolders, up to `proposal.max_levels` total levels.
- A proposed folder at any level must represent a cluster of size `>= min_cluster_size` (otherwise its members go to `proposal.outliers_folder`).

### Acceptance Criteria (Sprint 6)

- Config:
  - `clustering.algorithm = "agglomerative_tree"` is supported and uses scikit-learn only.
  - `proposal.max_levels` defaults to 2 and is enforced (no deeper folder proposal than requested).
  - `proposal.outliers_folder` defaults to `Outros` and is used for outliers.
  - `clustering.min_cluster_size` defaults to 4.
- Behavior:
  - The proposer produces hierarchy from clustering output (tree + cuts), not by running a flat clusterer twice.
  - `K` is derived automatically when `clustering.distance_threshold` is not provided.
  - No proposed non-outlier folder contains fewer than `min_cluster_size` files.
  - Outliers are grouped under `proposal.outliers_folder`.
- Determinism:
  - Given identical inputs, config, and environment, output is identical across runs.
  - No stochastic steps are used unless explicitly seeded; any ordering-sensitive steps MUST sort inputs with a stable key before clustering and before rendering.

## Sprint 7: Type-Aware Extraction (Rich Metadata + Snippets)

### Goals

- Implement a "Type-Aware" extractor that can inspect file contents to extract semantic signals.
- Extract **Content Snippets**: the first ~1KB of text for relevant file types.
- Extract **Rich Metadata**: internal properties like PDF Title/Author or Image EXIF data.
- Maintain **Graceful Degradation**: if optional dependencies are missing or files are unreadable, fall back to basic metadata without failing the run.
- Update **Preprocessing**: allow the embedding template to include new metadata fields like `{snippet}`.

### New Extractor: `extractor.provider = "type_aware"`

- **Text Extraction (Standard Lib):**
  - Targets: `.txt`, `.md`, `.py`, `.json`, `.csv`, etc.
  - Action: Read first 1024 bytes; handle UTF-8 and fallback to `latin-1`.
- **PDF Extraction (Optional `pypdf`):**
  - Targets: `.pdf`.
  - Action: Extract `Author`, `Title` from metadata; extract first 1024 chars of text from page 1.
- **Image Extraction (Optional `Pillow`):**
  - Targets: `.jpg`, `.jpeg`, `.png`.
  - Action: Extract EXIF `DateTimeOriginal`, `Make`, `Model`, `Software`.

### Configuration Keys (Sprint 7)

- `extractor.provider = "type_aware"`
- `extractor.snippet_size: int` (default: 1024)
  - **Corrected by [ADR 0036](ADR/0036-snippet-flow-and-config-default-consolidation.md):**
    the live key is `scanner.snippet_size` (default **4096** since Sprint 13). The
    extractor's stale `1024` fallback was raised to 4096 and is now actually passed
    through the pipeline (it was previously ignored). The same ADR fixes the
    extension-dispatch bug that left this snippet empty for all file types since
    Sprint 7.
- `preprocess.template: str` (default updated to: `"{stem} {ext} {snippet}"`)

### Acceptance Criteria (Sprint 7)

- **Graceful Fallback:** The system must not crash if `pypdf` or `Pillow` are not installed. It should log a warning (if verbose) and continue with basic metadata.
- **Robustness:** Corruption or permission errors on individual files must not stop the pipeline; the extractor should record an error in `ExtractedDoc.errors` and move on.
- **Contract Adherence:** New fields are added to the existing `metadata` dict; no changes to `CONTRACTS.md` version 1 are required.
- **Performance:** For ~200 files, extraction should complete in seconds on a typical machine.

## Sprint 8: Clustering Research & Validation (TCC Focus)

### Goals

- Implement **HDBSCAN** (Density-Based Spatial Clustering of Applications with Noise).
- Implement **Clustering Validation Metrics** (Silhouette Score) to quantify proposal quality.
- Expose the **Cohesion Score** in the final `StructureProposal`.
- Enable comparison between Hierarchical and Density-based approaches.

### New Clustering Option: `clustering.algorithm = "hdbscan"`

- **Implementation:** Use `sklearn.cluster.HDBSCAN`.
- **Parameters:**
  - `clustering.min_cluster_size: int` (reuse existing default 4).
  - `clustering.min_samples: int` (default: same as `min_cluster_size`).
  - `clustering.cluster_selection_epsilon: float` (default: 0.0).

### Validation Metrics

- **Silhouette Score:** Calculated using `sklearn.metrics.silhouette_score`.
- **Integration:** The `StructureProposal` will include a `cohesion_score` field (value between -1.0 and 1.0).
- **Fallback:** If a run results in only 1 cluster (or all noise), the score defaults to `0.0`.

### Acceptance Criteria (Sprint 8)

- **HDBSCAN Availability:** `hdbscan` is a valid algorithm in the registry.
- **Metric Accuracy:** The `cohesion_score` is present in the JSON output and CLI notes.
- **Provider Agnostic:** Metrics calculation works with any clustering algorithm (KMeans, Agglomerative, HDBSCAN).
- **Academic Rigor:** Output provides enough data to justify the "best" organization in a TCC context.

## Sprint 9: Interactive Review & Triage

### Goals

- Implement a "Human-in-the-Loop" review phase.
- Provide a rich, color-coded visualization of the semantic proposal and its cohesion scores.
- Allow the user to confirm or reject the proposal before finality.
- Prepare the architecture for the future "Apply" (move files) command.

### New CLI Flag: `--interactive` / `-i`

- If present, launches the Textual TUI Triage screen and waits for the user to
  accept or reject the proposal.
- Displays the same summary preamble as the CLI tree
  (`Proposta: N pastas, M arquivos · K em "Outros"`) plus a friendly overall
  cohesion label (`alta` / `média` / `verificar`); the numeric value is
  hidden by default and restored with `--scores`.
- Color-codes folder names based on `cohesion_score` (same thresholds as the
  CLI):
  - **Green:** High cohesion (> 0.7)
  - **Yellow:** Moderate cohesion (0.4 - 0.7)
  - **Red:** Low cohesion (< 0.4) — additionally annotated with
    `· verificar` so the cue survives a colour-blind reading.
- Folder ordering, file counts, the merged "Outros" bucket (outlier folder +
  top-level orphans), and the `--scores` opt-in for raw metrics all match the
  non-interactive CLI render. Both surfaces import the same helpers from
  `dynamic_folding.render.tree` so there is a single source of truth for the
  presentation conventions. See ADR 0026.

### Interactive Options

- `[Y]es`: Confirm the proposal (prints success and exits with code 0).
- `[N]o`: Reject the proposal (prints cancellation and exits with code 1).

### Acceptance Criteria (Sprint 9)

- **UI Fidelity:** Folder colors in the terminal accurately reflect their cohesion scores using `rich`.
- **Flow Control:** The tool correctly blocks execution when `--interactive` is used and respects the user's decision.
- **Backward Compatibility:** Standard runs (without `-i`) continue to work non-interactively.
- **Testability:** Triage logic can be tested with mocked stdin/stdout.

## Sprint 10: Automated Benchmarking

### Goals

- Implement an automated system to compare all available clustering and embedding combinations.
- Generate persistent, timestamped reports (JSON/CSV) for TCC results.
- Provide a "Best Configuration" recommendation based on cohesion scores.

### New CLI Command: `dynamic-folding benchmark <dir>`

- Iterates through a grid of configurations:
  - **Algorithms:** `kmeans`, `agglomerative_tree`, `hdbscan`.
  - **Embedders:** `fake`, `sbert` (if configured).
- For each run, captures:
  - `cohesion_score` (Silhouette).
  - Number of clusters.
  - Number of outliers.
  - Runtime duration.
- Saves results to `benchmark_results/run_<timestamp>.json`.

## Sprint 11: Dimensionality Reduction (Reducer Stage)

### Goals

- Implement a "Reducer" stage in the pipeline to handle high-dimensional embeddings.
- Improve clustering quality, especially for HDBSCAN.
- Provide a safe baseline (PCA) and support for UMAP.

### Configuration Keys (Sprint 11)

- `reducer.provider: str` (default: "identity")
  - `identity`: No reduction.
  - `pca`: Principal Component Analysis.
  - `umap`: Uniform Manifold Approximation and Projection (requires optional dependency).
- `reducer.n_components: int` (default: 10)
  - Target dimensionality.
- `reducer.random_state: int` (default: 0)
  - Ensure deterministic results.

### Acceptance Criteria (Sprint 11)

- **Backward Compatibility:** Default behavior (identity) produces identical results to previous versions.
- **PCA Availability:** PCA works out of the box using scikit-learn.
- **Dimensionality Safety:** Reducer should not attempt to reduce to more dimensions than available points or original dimensions.
- **Validation Consistency:** Cohesion scores are still calculated on original embeddings.

## Sprint 12: Hierarchical Proposer Refinement

### Goals

- Enable multi-level folder structures (`max_levels > 1`) for all clustering algorithms.
- Implement recursive re-clustering in the proposer logic.
- Ensure sub-level outliers remain in their parent folders.

### Acceptance Criteria (Sprint 12)

- **Algorithm Agnostic:** `hdbscan` and `agglomerative_tree` now produce subfolders when `max_levels >= 2`.
- **Recursive Logic:** Proposer correctly slices vectors for sub-clustering.
- **Clean Hierarchy:** Outliers at sub-levels do not create extra review folders.
- **Regression Tested:** Golden tests and silhouette scores are updated and verified.

## Sprint 13: Adaptive Chunk Pooling & Deep Semantic Signals

### Goals

- Implement sliding-window chunking (300 words with 50-word overlap) for long documents.
- Use **Mean Pooling + L2 Normalization** to represent documents exceeding model token limits (e.g., MiniLM 512 tokens).
- Prioritize internal metadata (PDF Title) over filenames when available and significant (>5 chars).
- Increase content snippet extraction from 1KB to 4KB for richer semantic signals.

### Acceptance Criteria (Sprint 13)

- **Semantic Gravity:** Long documents (multi-page PDFs) are correctly represented via pooling instead of being truncated.
- **Title Prioritization:** The preprocessor uses internal PDF Titles as the primary signal when available.
- **Robustness:** Handles documents with zero extractable text (falls back to metadata) without crashing.

## Sprint 14: The Unified TUI Experience

### Goals

- Consolidate standalone screens into a single, cohesive Textual application.
- Implement a **Home Screen** with a visual `DirectoryTree` for folder selection.
- Implement a **Pipeline Screen** with real-time progress bars for each stage.
- Implement a **Triage Screen** for interactive review and color-coded validation.
- Provide a seamless transition from "Select" to "Processing" to "Review."

### Acceptance Criteria (Sprint 14)

- **Unified Flow:** User can browse, scan, and triage in a single session without returning to the CLI.
- **Visual Selection:** Explicit 'S' key binding for directory selection ensures no accidental processing during navigation.
- **State Integrity:** Back-navigation and graceful error handling within the TUI.
- **Backward Compatibility:** `dynamic-folding run --interactive` still works by launching the TUI directly at the Pipeline stage.

### Acceptance Criteria (Sprint 10)

- **Comprehensive:** Successfully tests all 6 default combinations (3 algos x 2 embedders).
- **Persistent:** Results are written to disk and can be retrieved for the thesis.
- **Informative:** The CLI prints a summary table of the results.
- **Robust:** Individual run failures (e.g. missing SBERT model) do not stop the entire benchmark; they are recorded as errors.

## Sprint 15: Naming Robustness & Validation

### Goals

- Implement safe suffixing for folder name collisions to prevent Windows path length violations.
- Implement semantic name validation using vector similarity (Name Match score).
- Visualize naming confidence in the TUI.

### Acceptance Criteria (Sprint 15)

- **Safe Suffixing:** Folder names with suffixes (e.g., `_2`) never exceed `max_len` (default 80).
- **Name Match Score:** Every proposed folder has a `name_score` (cosine similarity) in the `StructureProposal`.
- **UI Feedback:** TUI display includes `Name Match` alongside `Cohesion` with appropriate color-coding.

## Sprint 16: Batch Execution & Registry Rigor

### Goals

- Implement **Batch Pipeline Execution** (generator-based) to handle thousands of files with constant memory pressure.
- Refactor `registries.py` using **Type Protocols** to ensure type-safe dependency injection and prevent wiring bugs.
- Implement **Lazy Text Loading** from SQLite to support semantic name validation without RAM bloat.

### Acceptance Criteria (Sprint 16)

- **Scalability:** The pipeline can process a directory with 1,000+ files while maintaining memory usage under 500MB.
- **Type Safety:** `registries.py` uses explicit `Protocol` classes; no generic `Callable` aliases are used for pipeline stages.
- **Robust Naming:** TF-IDF naming handles empty clusters or vocabulary errors gracefully (falls back to "Group" or "unnamed_group").
- **Contract Integrity:** `StructureProposal` correctly carries `name_scores` calculated via lazy-loaded embeddings.

## Sprint 17: Office Documents Smart Extraction

### Goals

- Enhance the `type_aware` extractor to support Microsoft Office documents (`.docx` and `.pptx`).
- Implement "Smart Structural Extraction" to prioritize high-value text (Headings and Titles) over standard body text.
- Maintain the 4KB `snippet_size` limit to protect performance and avoid dilution of the semantic signal.
- Make `python-docx` and `python-pptx` optional dependencies with graceful fallback to basic metadata.

### Acceptance Criteria (Sprint 17)

- **Optional Dependencies:** `python-docx` and `python-pptx` are optional. The pipeline must not crash if they are missing.
- **Smart Prioritization (.docx):** The extractor specifically targets paragraphs where `style.name` starts with "Heading" or "Title".
- **Smart Prioritization (.pptx):** The extractor specifically targets text shapes on slides marked as Titles or Headers.
- **Graceful Fallback:** If a document is corrupted or libraries are missing, it falls back to basic file metadata without halting the pipeline.

## Sprint 18: Naming Quality & TUI Progress

### Goals

- Fix "Empty Prompt" errors in Ollama namer during recursive sub-clustering.
- Implement naming robustness (avoid tautology, sentence-fragments, and mid-word truncation).
- Improve TUI transparency by splitting the "Process_files" and "Proposal" stages into granular progress bars.

### Acceptance Criteria (Sprint 18)

- **Naming Fallback:** The namer falls back to filenames if content extraction is missing/empty, preventing LLM error responses.
- **Concise Naming:** The Ollama prompt is tuned for 30-character тематические nouns, avoiding legal/administrative preambles.
- **Smart Truncation:** Folder names are truncated at the last space to prevent broken words.
- **Progress Granularity:** TUI shows distinct bars for `Extractor`, `Preprocess`, `Embedding`, `Clustering`, and `Naming`.

> SPEC numbering note: sprint entries between 18 and 19 were not retroactively documented. The sprint number was resumed at 19 to match the in-flight branch and ADR 0018. Git log is the authoritative timeline.

## Sprint 19: Empirical Characterization (TCC Evaluation)

### Goals

- Produce TCC-defensible empirical evidence under the framing established by ADR 0018: characterize measurable properties of the tool's output, not "validate correctness."
- Add a **floor baseline** clusterer (`random`) so that internal cohesion claims are anchored against a meaningful zero point.
- Add a **stability analyzer** that measures how consistent groupings are under input perturbation (a property that does not require ground truth).
- Add **performance instrumentation** (per-stage wall-clock + peak memory) for scaling evidence.
- Add a `characterize` CLI command that orchestrates the three quantitative properties (structure-finding, stability, scaling) and persists results to disk.
- Add an analysis script that turns persisted results into thesis-ready Markdown tables and PNG figures.
- Document the manual Likert protocol (perceived utility) as `docs/EVALUATION_PROTOCOL.md` — out-of-scope as code, in-scope as documentation.

### Non-goals (Sprint 19)

- No labeled corpora, no ARI/NMI/V-measure (rejected at the time — see ADR
  0018). This is later amended for the three human-labeled frozen corpora by
  ADR 0047; it remains outside the Sprint 19 characterization harness.
- No automation of the human Likert study; the protocol is intentionally manual.
- No new clustering algorithms beyond `random`. The other clusterers are unchanged.

### New Clustering Provider: `clustering.algorithm = "random"`

- **Implementation:** Assigns each file uniformly at random to one of `K` clusters, where `K` is chosen to match the number of non-outlier clusters produced by the configured "real" clusterer on the same input (so the comparison is fair). If the real clusterer is not available, `K = max(2, ceil(sqrt(N)))`.
- **Determinism:** Seeded by `clustering.random_state` (existing config key, default `42`). Same seed + same input → identical assignment.
- **Purpose:** Floor baseline for the structure-finding property. A real method should consistently outperform random on Silhouette.

### Stability Analyzer

Module: `dynamic_folding/core/stability.py`. Not a pipeline stage — invoked by the `characterize` CLI.

- Runs the pipeline `characterize.runs` times. Each run perturbs the input by removing a fraction of files (`characterize.perturbation`) at random, with a different seed.
- For every unordered pair of files that survived in *every* run, computes `p` = fraction of runs in which the pair was placed in the same top-level cluster.
- Derives a **pair-stability score** `1 − 4·p·(1 − p)` for each pair. The score is 1 when the pair was consistently grouped (always-same OR always-apart) and 0 when the decision was a 50/50 coin flip. See `docs/learning/01-stability-metric.md` for the rationale and worked examples.
- Reports the mean of these stability scores across all evaluable pairs as `pair_co_occurrence` on `StabilityReport`. The field name is preserved for backward compatibility with the contract; the value is the stability score, not the raw co-occurrence rate.

Edge cases: `runs < 2` and "no surviving pairs" both return 1.0 with an explanatory note rather than crashing or dividing by zero.

### Performance Instrumentation

- Per-stage wall-clock recorded in `RunResult.notes` or a new `RunResult.timings` mapping (decision: `timings: dict[str, float]` keyed by stage name; non-breaking — defaults to empty dict).
- Peak resident memory captured via `psutil` if installed; if `psutil` is missing, a note is added and the field is `None`. The pipeline must not fail if `psutil` is absent.

### New CLI: `dynamic-folding characterize <dir>`

- Runs three sub-procedures on the same corpus, in order: structure-finding (real config + random baseline), stability (N perturbed runs), performance (single instrumented run).
- Writes a single JSON result to `characterize.output_dir` (default `characterization_results/`), named `characterize_<timestamp>.json`.
- All sub-procedures respect the existing config; the user picks which "real" config they want to characterize via `--config <path.toml>` like the existing `run` command.
- Offline-only, deterministic given seed.

### Analysis Script: `scripts/analyze_results.py`

- Accepts one or more characterization result JSONs (glob or repeated `--input`).
- Aggregates across corpora and prints a Markdown table to stdout: method × Silhouette, with random-baseline row and per-corpus rows.
- Writes PNG figures to `--out-dir` (default `characterization_figures/`): stability bar chart and scaling curve.
- Pure Python + pandas + matplotlib. No new runtime dependencies on the package; the script lives under `scripts/` and is invoked directly.

### New Config Keys (Sprint 19)

Section `[characterize]`:

- `characterize.runs: int` (default `5`) — number of perturbed runs for the stability analyzer. `runs < 2` is allowed but disables stability (a note is recorded).
- `characterize.perturbation: float` (default `0.10`) — fraction of files removed per perturbed run. Must be in `[0.0, 0.5]`.
- `characterize.seed: int` (default `0`) — base seed for perturbation. Each run uses `seed + run_index`.
- `characterize.output_dir: str` (default `"characterization_results"`) — directory to write per-run JSON results.

### Acceptance Criteria (Sprint 19)

- **Random clusterer:** Registered in `dynamic_folding/core/registries.py` under id `random`. Deterministic given `clustering.random_state`. Produces a silhouette score not significantly different from zero on a fixture corpus (`abs(score) < 0.15`).
- **Stability:** `pair_co_occurrence == 1.0` when `characterize.perturbation == 0.0` (sanity floor). Strictly between 0 and 1 with default perturbation on the fixture corpus. Deterministic given the same seed.
- **Performance:** `RunResult.timings` populated for all stages on every run. `peak_memory_mb` is non-`None` when `psutil` is installed, `None` (with note) otherwise. The pipeline does not fail if `psutil` is missing.
- **CLI:** `dynamic-folding characterize <dir>` exits 0 on the fixture corpus, writes a single JSON to `characterize.output_dir`, and is offline-only (no network calls).
- **Analysis:** `scripts/analyze_results.py` runs on a directory of result JSONs and produces a Markdown table containing at minimum `method`, `corpus`, `silhouette`, `stability`, `runtime_s`. PNG figures are written if matplotlib is installed; otherwise a message is printed and exit code is still 0.
- **Determinism & offline:** All Sprint 19 tests run offline without SBERT or Ollama and produce identical output across runs.
- **Framing:** Documentation language follows ADR 0018 — "characterization", not "validation"; "properties", not "correctness". This is enforced by reviewer judgement, not by tests.

## External evaluation against human references (ADR 0047)

`dynamic-folding external-eval <dir> --labels <labels.csv> [--config <path.toml>]
--json <result.json> --csv <result.csv>` runs the ordinary pipeline once and
compares its proposed **top-level** partition with a human reference partition.
The labels CSV is UTF-8, semicolon-separated, with the relative file path and
human class in its first two columns. Existing exports may name the first column
either `Arquivo` or `Nome do arquivo`.

- **Complete, aligned inputs:** every scanned file must have one non-empty human
  label; duplicate, missing and extra paths are errors. This prevents a score
  over different populations of files.
- **Hierarchy and coverage:** descendants inherit their top-level folder label.
  Files in `Outros`, proposal orphans and any otherwise unassigned scanned file
  are evaluated as the predicted `Outros` class, never discarded.
- **Metrics:** output ARI, NMI and AMI (the advisor's ANMI terminology). NMI and
  AMI use `average_method="arithmetic"`; ARI and AMI correct their chance
  baseline. JSON additionally records class distributions, effective config,
  config source and software version. CSV has one flat corpus-summary row.
- **Interpretation:** the results quantify agreement with this contextual human
  reference, not universal correctness or universal usefulness. Each frozen
  corpus is reported separately; results must not choose a configuration or be
  pooled into an all-corpus score.

## Sprint 22: PDF Smart Structural Extraction

> SPEC numbering note: this section was originally proposed as "Sprint 19" on a parallel branch (`sprint-20`) that was forked before Sprint 19's empirical characterization work landed on `main`. To preserve a monotonic numbering after reconciliation, this section is documented as Sprint 22. (Sprint 20: deferred metrics work; Sprint 21: TUI polish absorbed across PRs #18 and #20.) See ADR 0021 for the design decision.

### Goals

- Upgrade the PDF branch of the `type_aware` extractor from "first three pages of raw text" to the priority-then-backfill pattern introduced in Sprint 17 for `.docx`/`.pptx`.
- Prioritize PDF outline (bookmark) titles plus `/Subject` and `/Keywords` metadata over body text.
- Backfill with body text from the first three pages when the priority block is shorter than `snippet_size`.
- Maintain the 4 KB `snippet_size` cap and graceful fallback (no new dependency; `pypdf` already required).

### Acceptance Criteria (Sprint 22)

- **Outline Prioritization:** when a PDF has a bookmark outline, outline titles appear in the snippet before any body text, in stable depth-first order.
- **Metadata Expansion:** `metadata["subject"]` and `metadata["keywords"]` are populated from `/Subject` and `/Keywords` when present (additive; no contracts version bump).
- **Backfill:** if the priority block is shorter than `snippet_size`, body text from the first 3 pages is appended; total snippet ≤ `snippet_size`.
- **No-Outline Compatibility:** PDFs without an outline behave as in Sprint 17 (body-text-only snippet) — regression-guarded.
- **Robustness:** corrupted PDFs, malformed outlines, and missing `pypdf` fall back without crashing the pipeline.
- **Determinism:** identical input + identical config → identical snippet bytes.

## Sprint 27: Linkage-Tree Hierarchy (ADR 0027)

> Supersedes Sprint 12 for `agglomerative_tree` and `hdbscan`.  Sprint 12's
> recursive re-clustering logic is retained **only** as a fallback for `kmeans`
> and `random`.  See ADR 0027 for the full rationale.

### Goals

- Eliminate the three problems identified in Campello et al. (2013/2015) that
  affect stacked re-clustering: error propagation, structural inconsistency, and
  O(K × depth) pipeline cost.
- Replace the recursive call to the clusterer inside `_build_level()` with a
  single tree-cut step that operates on the linkage structure produced at the
  top level.
- Make `hdbscan>=0.8.38` (McInnes et al. package) a required dependency and use
  its `condensed_tree_` to perform sub-level extraction via the EOM criterion.

### New Shared Return Type: `ClusterPartition`

`dynamic_folding/clustering/result.py` defines:

- `AgglomerativeLinkage(children, distances, n_leaves)` — stores the full
  binary merge tree from sklearn's `AgglomerativeClustering` (computed with
  `compute_distances=True`).
- `CondensedTreeData(parents, children, lambda_vals, child_sizes, n_leaves,
  selected_nodes)` — stores the condensed tree from the McInnes `hdbscan`
  package plus the EOM-selected node id for each top-level cluster label.
- `ClusterPartition(labels, linkage, distance_threshold)` — unified return type
  for all four registered clusterers, replacing the per-file `ClusterResult`
  dataclasses.

### Sub-level Extraction in `proposer.py`

**`_cut_agglomerative_subtree(leaf_indices, ag, min_cluster_size)`** (O(n)):
- Filters the linkage tree to merges whose full descendant set lies within the
  target cluster.
- Applies the same coverage-maximising / lower-threshold-tiebreaker heuristic
  as the top-level cut.
- Uses a union-find (no new sklearn fit).

**`_hdbscan_eom_subtree(root_node_id, ct, min_cluster_size)`**:
- Operates on the subtree of the condensed tree rooted at the cluster's
  EOM-selected node.
- Applies the EOM (Excess of Mass) criterion within that subtree (Campello et
  al. 2015, §3.3): `stability(C) = Σ child_sizes × (λ_split − λ_birth(C))`.
- The subtree root is **never** selected (forces at least one sub-division level).
- Bottom-up stability propagation selects sub-clusters; only descendants of a
  winning node are deselected (siblings are preserved).
- Leaves returned by EOM are intersected with `idxs` to prevent noise leaves
  (already in the outliers folder) from appearing in a sub-folder.

### Fallback

`kmeans` and `random` return `ClusterPartition(linkage=None)`.  The proposer
detects this and calls the original `_build_level()` re-clustering path,
which is unchanged.

### New Dependency

`hdbscan>=0.8.38` (McInnes et al. package, **not** sklearn's `HDBSCAN`) is a
required entry in `[project.dependencies]`.  The `cluster_hdbscan` function
will fail at import if the package is absent.

### Acceptance Criteria (Sprint 27)

- **Return type:** All four registered clusterers (`kmeans`, `agglomerative_tree`,
  `hdbscan`, `random`) return `ClusterPartition`.
- **Linkage populated:** `agglomerative_tree` returns `linkage: AgglomerativeLinkage`
  with `len(children) == n_leaves - 1`; `hdbscan` returns `linkage: CondensedTreeData`
  with `selected_nodes` mapping every non-noise label to a condensed-tree node id.
- **No second clusterer call:** for `agglomerative_tree` and `hdbscan`, the
  clusterer is called exactly once per `propose_structure` invocation.
- **Tree-cut depth:** on a corpus with two top-level clusters each containing
  two tight sub-groups, `agglomerative_tree` with `max_levels=2` reaches depth 2
  without re-running the algorithm.
- **Sibling correctness (Bug 1):** when node C1 wins the EOM pass, its sibling
  subtree C2 is not deselected.
- **No double-placement (Bug 2):** noise leaves (already in the outliers folder)
  are not included in any sub-folder.
- **Fallback intact:** `kmeans` and `random` still produce sub-folders via the
  original re-clustering path.
- **Determinism:** identical input + identical config → identical proposal tree.

## TUI Default Command & HTML Report on Accept (ADR 0028)

### Goals

- Make `dynamic-folding` with **no subcommand** the friendly default entry
  point: launch the unified TUI, pick a folder, run the pipeline, and open the
  HTML report on acceptance. Equivalent to typing `dynamic-folding tui`.
- Close the asymmetry where only the non-interactive `run` command produced the
  HTML report. All three TUI entry points (`tui`, no-args, `run --interactive`)
  now emit the report on accept.

### Behaviour

- The `run`/`tui` subparsers are no longer `required`. When `args.cmd is None`,
  the CLI resolves the project default config and launches the TUI (returns 0
  regardless of accept/reject — the default experience is not a gate).
- A shared `_launch_tui(...)` helper runs the Textual app and, **only on
  acceptance**, calls `_emit_report(result, cfg, root)`. Rejection produces no
  report and opens no browser (least-surprising behaviour).
- `_emit_report(...)` is the single render-and-open helper, honouring the
  `[report]` config (`enabled`, `output_path`, `auto_open`). It reuses the
  existing warn-and-continue fallback so a report failure never fails the run.

### Acceptance Criteria

- **No-args dispatch:** `dynamic-folding` (no args) launches the TUI; it does
  not exit with the argparse "required argument" error.
- **Report on accept:** accepting in any TUI path writes the HTML report and
  opens it when `report.auto_open` is true.
- **No report on reject:** rejecting writes no report and opens no browser.
- **Single source of truth:** `run`, `tui`, no-args, and `run --interactive`
  all route report emission through `_emit_report`.

## TUI Redesign — V1 Sereno (ADR 0029)

### Goals

- Replace the push/pop screen stack with a single-screen layout that has a
  persistent file-explorer sidebar visible across all three pipeline phases.
- Add a step indicator in the title bar so users always know which phase they
  are in (Selecionar → Processar → Proposta).
- Decouple folder selection from pipeline trigger: clicking a folder in the
  sidebar updates a path-chip confirmation panel; a separate "Iniciar análise"
  button (disabled until a folder is chosen) triggers the run.
- Add clickable footer buttons on the proposal screen: "Recomeçar" (restart
  the flow) and "Aplicar proposta" (accept and exit).

### Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ ● ● ●  ★ dynamic folding          ✓ Selecionar ─ ● Processar ─ ○ Proposta │
├────────────────┬────────────────────────────────────────────────┤
│  ⌂ EXPLORADOR  │                                                │
│                │   (SelectPanel / ProcessPanel / ProposalPanel) │
│  ▶ 📁 home/   │                                                │
│    ▼ 📁 user/ │                ContentSwitcher                 │
│      📁 docs  │                                                │
│      📁 proj  │                                                │
│               │                                                │
└───────────────┴────────────────────────────────────────────────┘
```

The `ContentSwitcher` swaps between three panels without dismounting the sidebar:

| Step | Panel | Contents |
|---|---|---|
| 0 | SelectPanel | Folder placeholder / path chip + "Iniciar análise" button |
| 1 | ProcessPanel | Stage list with ⠋/✓ icons and completion details |
| 2 | ProposalPanel | Proposal tree + "Recomeçar" / "Aplicar proposta" footer |

### Key interactions

- Pressing Enter on a directory in the sidebar populates the path chip (does not start the run).
- Pressing `S` selects the currently highlighted sidebar node as the target folder.
- Clicking "Iniciar análise" (active only when a folder is selected) starts the pipeline.
- Clicking "Recomeçar" resets to step 0 and clears the selected folder.
- Clicking "Aplicar proposta" (or was previously `Enter`) accepts the proposal, triggers the HTML report, and exits.
- Pressing `Q` at any step quits without accepting.

### Acceptance criteria

- **Step indicator:** title bar always shows which of the three phases is active.
- **Sidebar persistence:** the directory tree is visible and scrollable during all three phases.
- **Button states:** "Iniciar análise" is visually disabled (grey) until a folder is chosen, active (blue) once one is selected.
- **Restart flow:** "Recomeçar" returns to step 0 with the sidebar ready for a new selection.
- **Backward compatibility:** `DynamicFoldingApp.__init__` signature unchanged; `_launch_tui()` in `cli.py` unchanged; all existing tests pass (`TriageScreen` and `TriageApp` preserved).

## pywebview UI — V1 Sereno high-fidelity (ADR 0030)

### Motivation

The Textual TUI (ADR 0029) cannot reproduce the design handoff at high fidelity: custom fonts, border radius, smooth animations, and pixel-level spacing are impossible in a character-grid terminal. pywebview opens a native OS window backed by EdgeWebView2 (Windows 10/11), allowing the existing React prototype to run with full CSS rendering.

### Architecture

```
CLI  _launch_tui()
  └─ launch_webview()                  # dynamic_folding/tui/webview_app.py
       ├─ webview.create_window(url=web/index.html, js_api=DFWebApi)
       ├─ DFWebApi — Python methods exposed as window.pywebview.api
       └─ webview.start()  ← blocks; window.destroy() unblocks it
```

**JS→Python** (called from React): `get_home_path()`, `get_initial_root()`, `list_directory(path)`, `start_pipeline(path)`, `accept()`, `cancel()`.

**Python→JS** (pushed from pipeline thread via `evaluate_js`): `window._df.onStageStart(name)`, `onStageEnd(name)`, `onPipelineDone(proposalObj)`, `onPipelineError(msg)`.

### Frontend (`dynamic_folding/tui/web/`)

| File | Purpose |
|------|---------|
| `index.html` | HTML shell; loads vendored scripts |
| `app.jsx` | Full V1 React app (Babel in-browser, no build step) |
| `vendor/react.development.js` | React 18.3.1 (vendored, offline-safe) |
| `vendor/react-dom.development.js` | ReactDOM 18.3.1 (vendored) |
| `vendor/babel.min.js` | Babel standalone 7.29.0 (vendored) |

### Acceptance criteria

- **Visual fidelity:** window renders the local/system UI font stack, blue `#3B82F6` primary, amber folder icons, smooth pulse animation on active stage.
- **Lazy tree loading:** only immediate children are fetched on folder expand; no full-tree preload.
- **Pipeline streaming:** stages appear and complete in real time as the Python pipeline progresses.
- **Recomeçar:** resets React state without closing the window; user can pick a new folder and run again.
- **Aplicar proposta:** closes window, triggers HTML report, returns `accepted=True` to CLI.
- **Tests unchanged:** 227 tests pass; `TriageApp`/`TriageScreen` unaffected.

## Chapter 4 — Evaluation commands (offline, deterministic, read-only)

The empirical chapter (ADR 0018, amended by ADR 0038; roadmap in
`docs/learning/02-experimental-scope.md`) ships read-only evaluation commands that
measure what the tool *delivers* — the real proposal's groups + the raw 384-dim
embeddings. They never move files and add nothing to the product contract.

- `dynamic-folding silhouette <dir> [--config <toml>] [--json <path>] [--csv <path>]` —
  silhouette of the proposed top-level grouping, scored on the raw embeddings (the
  `Outros` bucket is excluded and counted), plus a size-preserving random baseline
  (1000 seeded shuffles) and a per-group breakdown. See
  `docs/learning/05-silhouette-metric.md`. `--json`/`--csv` are additive (write a
  file; the stdout text is unaffected), same convention as `compare --html`
  (ADR 0043).
- `dynamic-folding compare <dir> [--config <toml>] [--html <path>] [--json <path>] [--csv <path>]` — runs the
  pipeline once per clustering algorithm (`hdbscan`, `kmeans`, `agglomerative_tree`)
  via in-memory config overrides, plus hyperparameter sensitivity sweeps — hdbscan
  `min_cluster_size`, kmeans `top_k` (widened), and the reducer's `n_components` as one
  light cut (ADR 0040; `n_neighbors`/`min_dist` discussed, not swept). The **cross-algorithm
  comparison is the structural descriptors** (n_groups, n_outliers, coverage); the
  **silhouette is reported as a per-algorithm descriptor only, never a ranking** —
  the algorithms score over different file subsets (ADR 0038). A **second lens, DBCV**
  (density-biased, the opposite of silhouette) is also reported per algorithm, scored in
  the **reduced clustering space** (the ~10-dim UMAP vectors now carried on `RunResult`;
  DBCV degenerates in 384-dim, where n≪d) with the `Outros` bucket fed as noise and
  coverage beside it. Silhouette (384-dim meaning space) and DBCV (10-dim clustering
  space) differ in **both bias and space**, so they are independent lenses, never compared
  row-to-row; DBCV is read **asymmetrically** — the reduced space favours HDBSCAN, so only
  HDBSCAN *underperforming* is a strong signal (ADR 0039). The HTML report presents, per
  clustering algorithm, a **matrix** of the knob sweep × all metrics (structural + silhouette
  + DBCV), with the default config marked — it never elects a single execution (ADR 0041).
  The report also embeds an **illustrative PCA-2D figure** of the default run — the corpus
  before and after grouping, projected from the 384-dim embeddings (deterministic linear
  projection; the grouping ran in the reduced space, so the 2D scatter is illustrative, not
  the computation space). It is drawn only when the optional `matplotlib` (`[viz]`) extra is
  installed; otherwise the report shows a visible note in its place (ADR 0042).
  Naming is forced to the deterministic offline `tfidf` namer (naming never affects cluster
  membership), so results are reproducible. `--html` writes a self-contained PT-BR report in the
  V1 Sereno design system (`dynamic_folding/evaluation/comparison_report.py` +
  `comparison_report_template.html`), recording the exact effective config per run.
  `--json` writes `ComparisonResult.to_dict()` (all algorithms + sensitivity studies;
  the projection's raw 2D coordinates are left out — figure-only data); `--csv` writes
  one row per algorithm (structural + silhouette + DBCV descriptors; `group_sizes` and
  `effective_config` stay JSON-only, they don't flatten cleanly) via
  `dynamic_folding/evaluation/csv_export.py` (ADR 0043).

Both are deterministic (seeded; same input + config + env → identical numbers).
Thesis runs use a **frozen corpus snapshot** (a copy under gitignored `datasets/`),
because the live source folder drifts over time.

- `dynamic-folding compare-multi <dir1> <dir2> ... [--config <toml>] [--html <path>] [--json <path>] [--csv <path>]`
  (or `dynamic-folding compare-multi --from-json <json> [--html <path>]` to
  **re-render the report from a saved JSON without re-running the pipeline** —
  seconds instead of a full SBERT run; the JSON stores the figure coords, so the
  re-render is lossless. `--from-json` and the positional paths are mutually exclusive.)
  — runs `compare`'s single-corpus measurement (`run_comparison`) once per given
  directory, in argument order, and assembles **one side-by-side report comparing
  all of them** rather than N separate reports (ADR 0045, aggregate-first). Corpora
  are **anonymized**: displayed only as "Corpus 1", "Corpus 2", ... in argument
  order; real directory paths never appear in the HTML/JSON (they are printed only
  to stdout, `=== Corpus N (<real path>) ===`, for the operator's own reference).
  Report structure: conceptual sections once (intro, the two lenses, structural
  framing — reused verbatim from `compare`'s report) → a new **aggregate section**
  (the heart) with one table per lens (silhouette, DBCV, structural) with corpora as
  rows and algorithms as columns, plus a placeholder for the author's cross-corpus
  reading → per-corpus detail blocks (figure, matrices, reducer sensitivity,
  provenance), once per corpus, reusing the existing per-corpus section functions
  unmodified → a multi-corpus limitations section (n=3, heterogeneous corpora,
  non-controlled comparison — placeholder prose). Implemented in
  `dynamic_folding/evaluation/multicorpus.py` (`run_multicorpus_comparison`,
  `MultiCorpusComparison`) and `dynamic_folding/evaluation/multicorpus_report.py`
  (`render_multicorpus_html`); reuses the same `comparison_report_template.html`.
  `--json` writes `MultiCorpusComparison.to_dict()` (label + full `ComparisonResult`
  per corpus). `--csv` is not yet implemented for the multi-corpus case (prints a
  warning; use `--json`).
