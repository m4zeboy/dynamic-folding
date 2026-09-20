# ADR 0012: Unified TUI Workflow & State Management

Date: 2026-05-01

## Status

Superseded by ADR 0029 (Textual V1 Sereno redesign) and ADR 0030 (pywebview migration).

## Context

The current TUI is split into disconnected screens, often launched as standalone apps from the CLI. This breaks the user flow and prevents a cohesive "Windows-first" experience where the user can browse, scan, and review in one session.

## Decision

1.  **Unified App:** Consolidate all TUI logic into a single `DynamicFoldingApp` (class `DynamicFoldingApp`).
2.  **Screen-Based Flow:** Use Textual's `Screen` system to manage states:
    -   `HomeScreen`: Visual file browser (`DirectoryTree`).
    -   `PipelineScreen`: Progress bars and worker thread execution.
    -   `TriageScreen`: Result review and confirmation.
3.  **Home Entry Point:** The app starts at `HomeScreen` unless a path is provided via CLI.
4.  **Worker Isolation:** Run the pipeline in a background thread (`@work(thread=True)`) to keep the TUI responsive during CPU-intensive embedding.

## Rationale

-   **User Experience:** Eliminates the need to switch back and forth between terminal input and TUI review.
-   **Visual Discovery:** The `DirectoryTree` makes it easier to target folders without manual path entry.
-   **State Continuity:** Allows for "back" navigation and retries without restarting the process.

## Consequences

-   Increased complexity in `app.py`.
-   Requires careful handling of terminal resizing and thread-safety for progress updates.
-   CLI `run` command will need to detect when to launch the unified app vs. the legacy terminal output.
