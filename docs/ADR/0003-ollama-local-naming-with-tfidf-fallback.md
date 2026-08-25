# ADR 0003: Ollama Naming Provider (Local HTTP) with TF-IDF Fallback

Date: 2026-04-29

## Decision

Add an optional naming provider: `naming.provider = "ollama"`.

- The provider connects to Ollama via local HTTP, default `http://127.0.0.1:11434`.
- Non-loopback base URLs are rejected to preserve the offline-only constraint.
- The provider is best-effort: on connection errors/timeouts/bad outputs, it falls back to the existing `tfidf` provider for that cluster.

## Status

Accepted.

## Rationale

- Users may want higher-quality, human-friendly cluster names.
- Ollama provides local model serving without remote API calls.
- A TF-IDF fallback preserves robustness and avoids making naming a single point of failure.

## Consequences

- Config must include `naming.model` and validate `base_url` as loopback.
- Implementation must sanitize/validate names to remain Windows-safe.
- Unit tests should validate fallback behavior without requiring Ollama.
- Optional integration tests can exercise Ollama when present.
