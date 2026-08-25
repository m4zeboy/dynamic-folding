# Contracts

Contracts are the only allowed communication mechanism between modules.

## Versioning

- Each contract carries its own `contracts_version` (e.g. `StructureProposal` is `4`; `StabilityReport` and the characterization contracts are `2`; `RunResult` is `2`).
- Breaking changes require a new version and an ADR.

## `StructureProposal`

Purpose: UI-agnostic result of the intelligence pipeline.

Fields:

- `contracts_version: int` (must be `4`)
- `root: str` absolute path
- `folders: list[FolderNode]` (Recursive list of folder objects)
- `orphans: list[str]` file `rel_path` that could not be placed
- `notes: list[str]` human-readable notes

> **v4 (ADR 0035):** the user-facing confidence signal was removed —
> `StructureProposal.cohesion_score` and `FolderNode.cohesion` no longer exist.
> Silhouette is now an evaluation-only instrument computed by the standalone
> characterization tooling, not carried on the product contract.

### `FolderNode`

Fields:
- `name: str` (canonical, Windows-safe folder name — used for cache keys, JSON, and on-disk creation if the user adopts the proposal)
- `files: list[str]` (Relative paths of files directly in this level)
- `subfolders: list[FolderNode]` (Nested sub-clusters)
- `name_match: float | None` (Semantic validation score for name)
- `display_name: str | None` (Added in v3. Optional render-layer override. When set, the renderer shows this instead of `name`. Omitted from `to_dict()` when `None`. Currently set by the proposer on the outlier bucket so the render layer can detect it via a stable marker independent of the user-configurable `proposal.outliers_folder`.)

Invariants:

- All file paths are relative to `root`.
- Each file should appear at most once across the recursive `folders` tree and `orphans`.
- Folder names must be valid on Windows and must not be empty.
- Hierarchy depth is typically 2-3 levels for clarity.
- `display_name`, when set, MUST also be a Windows-safe folder name (it is shown to users as a folder name they might create).

## `RunResult`

Purpose: the serializable top-level output of a pipeline run (`run_pipeline`). Carries the proposal plus intermediates kept for debugging and offline evaluation.

Fields (the ones consumers rely on):

- `contracts_version: int` (must be `2`)
- `root: str`, `embeddings: list[EmbeddingRecord]`, `proposal: StructureProposal`
- `reduced_vectors: list[list[float]]` — **added in v2.** The reducer's output (e.g. UMAP ~10-dim), in the **same order** as `embeddings`. Stored so density-based evaluation (DBCV) scores the *real* projection the clusters were drawn in, not a re-derived one. **Empty** for the identity reducer or runs that predate v2.
- `timings: dict[str, float]`, `peak_memory_mb: float | None`

> **v2 (ADR 0039):** additive — `reduced_vectors` added so `dynamic-folding compare`'s DBCV lens can read the clustering's actual reduced space. No existing field changed; old constructions keep working (the field defaults to empty).

## Sprint 1 intermediate contracts

In Sprint 1 we introduce intermediate DTOs to decouple scanning/extraction from later ML stages.
These are internal contracts (still versioned) and are expected to be stable.

### `FileRef`

Purpose: represent an on-disk file or directory discovered by the scanner.

Fields (minimum):

- `path: str` absolute path
- `rel_path: str` relative to `root`
- `is_dir: bool`
- `depth: int` where `root=0`
- `name: str`
- `ext: str` lowercase extension or empty
- `size: int | None` bytes (None for dirs)
- `ctime: float | None` seconds since epoch if available
- `mtime: float | None` seconds since epoch if available

### `ExtractedDoc`

Purpose: represent the signals extracted from a `FileRef` — filesystem metadata **and** a bounded content snippet.

Fields (minimum):

- `file: FileRef`
- `metadata: dict[str, object]` — carries both filesystem metadata and, for the default `type_aware` extractor, a bounded content **`snippet`** (first `scanner.snippet_size` chars, default 4096) plus rich fields where available (`title`, `subject`, `keywords`, image EXIF). Populated additively; no contracts version bump (see Sprint 7/17/22 and ADRs 0017/0021/0025/0036/0044).
- `errors: list[str]`

## Sprint 19: characterization contracts

These contracts support the `characterize` CLI and the empirical-characterization workflow described in ADR 0018. They are auxiliary outputs and do not change the pipeline's primary contract (`StructureProposal`).

### `StabilityReport`

Purpose: summary of pair-co-occurrence stability over `N` perturbed runs of the pipeline on a single corpus.

Fields:

- `contracts_version: int` (must be `2`. Previously the `StabilityReport` family was kept in lockstep with `StructureProposal`, but ADR 0026 advanced `StructureProposal` to v3 for a purely additive field — `StabilityReport` was unaffected and stays at v2. Future shared-shape changes will resume the lockstep convention; ADR 0026 documents this one-time decoupling.)
- `root: str` absolute path to the corpus root that was characterized
- `runs: int` number of perturbed pipeline runs that contributed to the report (`runs >= 1`)
- `perturbation: float` fraction of files removed per run, in `[0.0, 0.5]`
- `seed: int` base seed; run `i` uses `seed + i`
- `pair_co_occurrence: float` mean rate in `[0.0, 1.0]` that two evaluable files end up in the same top-level cluster across runs
- `evaluable_pairs: int` number of file pairs that were present in every run (the denominator for the mean)
- `notes: list[str]` human-readable notes (e.g., `"runs<2: stability disabled"`, `"psutil missing"`)

Invariants:

- `0.0 <= pair_co_occurrence <= 1.0`
- `0.0 <= perturbation <= 0.5`
- If `runs < 2`, `pair_co_occurrence` is reported as `1.0` and a note explaining that stability requires multiple runs is added.
- If `evaluable_pairs == 0` (e.g., perturbation removed too many files in common), `pair_co_occurrence` is `1.0` (vacuous truth) and a note is added.

### `CharacterizationResult`

Purpose: top-level container persisted by the `characterize` CLI as one JSON file per run.

Fields:

- `contracts_version: int` (must be `2`)
- `root: str` absolute path to the corpus root
- `corpus_metadata: dict[str, object]` file count, total bytes, type-mix histogram, depth (used for thesis tables; informational only)
- `config: dict[str, object]` effective configuration (post-resolution), so results are reproducible from the JSON alone
- `structure: dict[str, float | None]` `{"silhouette_real": float | None, "silhouette_random": float | None}` — both nullable when a single run produces ≤ 1 cluster
- `stability: StabilityReport`
- `performance: dict[str, object]` `{"timings": dict[str, float], "peak_memory_mb": float | None}` (matches the new `RunResult` fields)
- `notes: list[str]` aggregated notes from the underlying runs

Invariants:

- `config` MUST be the effective config (paths resolved, defaults filled in) — not the raw user-supplied TOML — so a thesis reader can reproduce the run from the JSON alone.
- All numeric fields are JSON-serializable (no NaN; use `null` instead).
