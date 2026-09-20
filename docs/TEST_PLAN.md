# Test Plan (MVP)

Goal: validate robustness and determinism without requiring ML models.

## Test Types

1. Contract tests
- Validate `StructureProposal` invariants.
- Validate deterministic render output.

2. Golden tests
- Run CLI against a fixture directory.
- Compare JSON (internal representation) to golden file.

3. Unit tests
- Registry behavior.
- Sanitization for Windows folder names.
- Scan depth constraints.

4. Optional integration tests (gated)
- SBERT embedding smoke: only runs if a local model path is provided via env/config.
- Ollama naming smoke: only runs if Ollama is reachable on loopback and a model is configured.

## Fixtures

- `tests/fixtures/basic/`
  - A small set of files and subfolders within depth 2.

## Determinism Rules

- Sort inputs consistently.
- Fix any randomness via config seeds.
- In tests, use a fake deterministic embedding provider.

## Sprint 5 Coverage Additions

### Unit (model-free)

- Config validation:
  - Accepts `embedding.provider = "sbert"` only when `embedding.model_path` exists and is local.
  - Accepts `naming.provider = "ollama"` only when `naming.model` is set.
  - Rejects `naming.base_url` that is not loopback (e.g. not 127.0.0.1/localhost).
- Offline behavior guards:
  - SBERT provider must not attempt downloads (test via monkeypatching network/transformers download entry points if applicable).
  - Ollama provider falls back to TF-IDF on connection errors/timeouts and returns a valid Windows-safe name.

### Integration (skipped by default)

- SBERT embeddings:
  - Requires env `DYNAMIC_FOLDING_SBERT_MODEL_PATH` pointing to a local model directory.
  - Runs a minimal pipeline over a tiny fixture and asserts embeddings are non-empty and stable across two runs (cache hit).
- Ollama naming:
  - Requires env `DYNAMIC_FOLDING_OLLAMA_MODEL` and optional `DYNAMIC_FOLDING_OLLAMA_BASE_URL`.
  - Runs naming on a small cluster and asserts output is non-empty and Windows-safe.

### Contracts

- `docs/CONTRACTS.md` remains unchanged for Sprint 5.
