# Architecture

## Modules

- `scanner` => enumerates files (depth-limited)
- `extractor` => extracts metadata (content later)
- `preprocess` => creates text/features for embedding
- `embedding` => produces vectors + cache
- `clustering` => produces groups and subgroups
- `naming` => generates Windows-safe folder names (TF-IDF first)
- `proposal` => maps clustering output to a folder structure (depth-limited)
- `render` => prints tree (and optionally JSON)

## Configuration

- TOML config file, default: `config/default.toml`
- Use Python stdlib `tomllib` for parsing (Python 3.11+)

## Registry / Strategy

Each module type is selected by config using a string id.

Example:

- `embedding.provider = "fake" | "sbert"`
- `clustering.algorithm = "agglomerative_tree" | "kmeans" | ...`
- `naming.provider = "tfidf" | "ollama"`

The proposer MUST request its clusterer by id from the registry (similar to naming/embedding) rather than importing a concrete clustering implementation. The selected clusterer id is controlled by `clustering.algorithm`.

The pipeline never imports concrete implementations directly; it requests them from the registry.

## Hierarchy Source

Hierarchy is produced by the clustering output itself:

- Hierarchical clusterers (e.g. `agglomerative_tree`) provide a linkage tree.
- The proposer cuts the tree to derive groups/subgroups up to `proposal.max_levels`.
- We do not build hierarchy by running a flat clusterer twice.

## Offline

- No network calls.
- Any local model files must be provided by the user.

### Sprint 5 Providers

#### Embedding: `sbert`

- Implementation uses `sentence-transformers`.
- Model loading MUST be from a user-supplied local `embedding.model_path`.
- The provider must refuse to download (no implicit fetch from Hugging Face).
- Cache model identity should be stable and include:
  - Provider id ("sbert")
  - A model identifier derived from `model_path` (and optionally its directory fingerprint)
  - Relevant params (`normalize`, and an internal provider version string)

Expected failure mode:

- If `model_path` does not exist or is not a valid local model directory, fail fast with a clear, actionable error and do not attempt any network access.

#### Naming: `ollama`

- Implementation calls a local Ollama server via HTTP.
- Must default to `http://127.0.0.1:11434` and reject non-loopback hosts to preserve offline-only constraints.
- Provider should be best-effort:
  - If Ollama is not installed, not running, times out, or returns an invalid/unsafe name, fall back to `tfidf` for that cluster.

Expected failure mode:

- On connection errors/timeouts: emit a note and fall back to TF-IDF (pipeline run should still succeed).
