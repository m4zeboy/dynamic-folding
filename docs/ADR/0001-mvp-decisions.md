# ADR 0001: MVP Baseline Decisions

Date: 2026-04-29

## Decision

1. Python 3.11+ on Windows.
2. Offline-only: no network calls, no remote APIs.
3. Output displayed as an ASCII tree; internal representation is JSON-friendly.
4. Proposed structure supports 2 levels (folders + subfolders) from MVP.
5. Tests must not depend on real embeddings/LLMs; use deterministic fakes.

## Status

Accepted.

## Consequences

- We will implement plugin registries for embedding/clustering/naming.
- Real ML providers can be added later without changing pipeline contracts.
