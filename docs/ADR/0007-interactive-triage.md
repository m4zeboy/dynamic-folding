# ADR 0007: Interactive Triage and Human-in-the-Loop Validation

Date: 2026-04-30

## Status

Accepted.

## Context

Semantic clustering is probabilistic and may not always align with user intent. For a TCC prototype, demonstrating "Human-in-the-Loop" (HITL) capability is a high-value feature. Additionally, providing visual feedback on the mathematical "confidence" (cohesion score) helps the user make informed decisions.

## Decision

1.  **Introduce `--interactive` flag:** Add a CLI option to trigger a manual review phase.
2.  **Color-coded Tree Rendering:** Use the `rich` library to apply semantic colors to proposed folders based on their `cohesion_score`.
    - Green (>0.7): High confidence.
    - Yellow (0.4-0.7): Moderate confidence.
    - Red (<0.4): Low confidence, likely requires manual review.
3.  **Triage Phase:** Implement a blocking prompt after the tree is rendered.
    - If confirmed (Yes), the process completes successfully.
    - If rejected (No), the process terminates with a cancellation message and a non-zero exit code.
4.  **Decoupled Triage Logic:** The triage logic will live in `dynamic_folding/core/triage.py`, keeping the `pipeline.py` clean and focused on data processing.

## Rationale

-   **User Trust:** Allowing users to see and approve the structure before any action is taken is critical for a file organization tool.
-   **TCC Presentation:** Interactive demos are more engaging and demonstrate full-stack consideration (CLI, UX, ML validation).
-   **Extensibility:** This phase serves as the "checkpoint" where we can later add functionality to move files or manually re-assign clusters.

## Consequences

-   The CLI will require a user-facing prompt mechanism.
-   Render logic must now handle optional metadata (cohesion scores) per folder.
-   Automated tests for the CLI must be able to handle interactive inputs.
