# ADR 0016: Recursive Structure Proposal (Contract v2)

Date: 2026-05-01

## Status

Accepted.

## Context

The current `StructureProposal` (Contract v1) uses flat `folders` and `subfolders` dictionaries. While simple for the MVP (2 levels), it does not scale well to the 3-level depth required for advanced hierarchical research. Representing N-levels in v1 would lead to increasingly complex and non-intuitive dictionary structures.

## Decision

1.  **Contract Version:** Bump to `contracts_version: 2`.
2.  **Recursive Nodes:** Replace dictionaries with a recursive list of `FolderNode` objects.
3.  **Data Structure:**
    ```python
    @dataclass
    class FolderNode:
        name: str
        files: list[str]  # Files directly in this folder level
        subfolders: list['FolderNode']
        cohesion: float | None = None
        name_match: float | None = None
    ```
4.  **Guided Subdivision:** The `propose_structure` function will recursively re-cluster nodes up to `max_levels`.

## Rationale

-   **Scalability:** Allows for arbitrary depth (N-levels) without changing the data schema.
-   **Clean Logic:** The UI can render the proposal by simply traversing a tree, removing the need for special "Top" vs "Sub" handling.
-   **TCC Accuracy:** Better reflects the hierarchical nature of clustering linkage trees and recursive algorithms.

## Consequences

-   **Breaking Change:** All UI rendering and CLI output logic must be refactored to handle the recursive tree.
-   **Contract Invalidation:** Existing "Golden" tests and cached proposals from v1 will be incompatible with v2.
-   **Outlier Routing:** Sub-level outliers (noise) are kept in the `files` list of their immediate parent node, ensuring they remain semantically localized.
