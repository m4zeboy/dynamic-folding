# ADR 0011: Adaptive Chunk Pooling & Structured Tagging

Date: 2026-05-01

## Status

Point 2 ("Title Prioritization") **superseded by ADR 0025**
(dual-source text representation, 2026-09-19). Points 1, 3, 4, 5 remain
in force.

## Context

Current embeddings are limited by the 512-token context window of SBERT models and the shallow extraction (1KB/1 page) of the extractor. This leads to semantic loss in long documents and poor clustering for files with misleading filenames.

## Decision

1.  **Semantic Sampling:** The `type_aware` extractor will extract text from the first 3 pages of PDFs and both "Head" and "Tail" of text files.
2.  **Title Prioritization:** The preprocessor will calculate a `best_title` feature. If a valid internal PDF Title (length > 5) exists, it is prioritized over the filename stem.
3.  **Structured Tagging:** Use `[FILE]`, `[EXT]`, and `[CONTENT]` tags in the `text_for_embedding` to provide semantic boundaries for the embedder.
4.  **Embedder-Side Chunking:** Implement a sliding window in the `sbert` embedder. Long strings are split into overlapping chunks (default 300 words, 50 words overlap).
5.  **Mean Pooling:** The final document vector is the mean average of all its chunk vectors.

## Rationale

-   **Deep Context:** Mean pooling allows the model to "see" the entire document regardless of its length.
-   **Signal Clarity:** Structured tagging helps the model distinguish between metadata and body text.
-   **Robustness:** Prioritizing internal titles mitigates the impact of poor filenames on semantic quality.

## Consequences

-   Embedding time will increase linearly with document length (more chunks to encode).
-   Cache efficiency is maintained by hashing the full `text_for_embedding`.
-   Requires updates to `type_aware.py`, `basic.py` (preprocess), and `sbert.py`.
