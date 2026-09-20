# ADR 0014: Batch Pipeline Execution & SQLite Lazy Loading

Date: 2026-05-01

## Status

Accepted.

## Context

The system currently processes all files in sequential global loops: scan all -> extract all -> preprocess all -> embed all. This creates a high memory peak, especially when holding thousands of text snippets in memory before clustering. As the tool scales toward the "Full Scale" milestone (10,000+ files), a streaming/batch approach is required to remain performant on consumer hardware.

## Decision

1.  **Batch Execution:** Refactor `run_pipeline` to process files in chunks (default 100).
2.  **SQLite Persistence:** Update the `embeddings` table to include a `text_content` column.
3.  **Lazy Loading:** 
    -   The `Embedder` will store the `text_for_embedding` snippet in the SQLite database alongside the vector.
    -   The `Proposer` will fetch these snippets from the database only when needed (during the Naming stage for specific clusters), instead of keeping all snippets in memory.
4.  **Generator-based Flow:** Use Python generators to flow data through Extraction/Preprocessing/Embedding batch-by-batch.

## Rationale

-   **Scalability:** Drastically reduces peak RAM usage.
-   **Performance:** SQLite WAL mode handles concurrent reads/writes well, and batching embeddings preserves GPU/CPU utilization efficiency.
-   **Robustness:** If a long run is interrupted, all work up to the last successful batch is safely persisted in the database.

## Consequences

-   Increased complexity in `pipeline.py`.
-   Slightly larger database file size (due to text content).
-   Requires ensuring the `model_id` and `content_hash` remain strictly aligned to prevent stale text retrieval.
