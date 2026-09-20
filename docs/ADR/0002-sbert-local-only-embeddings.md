#+#+#+#+
# ADR 0002: SBERT Embeddings via sentence-transformers (Local Model Only)

Date: 2026-04-29

## Decision

Add an optional real embedding provider: `embedding.provider = "sbert"` implemented with `sentence-transformers`.

Offline constraints are enforced as follows:

- `embedding.model_path` is required and MUST point to an existing local directory.
- The provider MUST NOT download model weights or configs.
- If the model cannot be loaded from `model_path`, the run fails fast with a clear error.

## Status

Accepted.

## Rationale

- SBERT provides strong general-purpose semantic embeddings suitable for clustering.
- `sentence-transformers` is a standard, well-supported local inference library.
- Requiring an explicit local `model_path` keeps the tool offline and predictable on Windows.

## Consequences

- Packaging/docs must clarify that users are responsible for placing the model directory on disk.
- Config validation must enforce `model_path` existence and local-only semantics.
- Tests remain model-free by default; integration tests are optional and gated by env.
