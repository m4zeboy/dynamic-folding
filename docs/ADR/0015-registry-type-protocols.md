# ADR 0015: Registry Type Protocols

## Status
Accepted

## Context
The project uses a Registry/Strategy pattern in `dynamic_folding/core/registries.py` to decouple the pipeline from specific implementations. Previously, these strategies were defined using generic `Callable` aliases (e.g., `Scanner = Callable[[Path, dict], list[FileRef]]`). 

As the pipeline grew more complex (specifically with the introduction of callbacks like `fetch_texts` and `embed_text` in Sprint 16), these generic aliases became fragile. It was easy to forget to update a registry lambda when a strategy's signature changed, leading to runtime errors that were not caught by static analysis.

## Decision
We will replace all `Callable` aliases in `registries.py` with explicit `typing.Protocol` classes.

### Example:
```python
class Proposer(Protocol):
    def __call__(
        self,
        root: str,
        preprocessed: list[PreprocessedDoc],
        embeddings: list[EmbeddingRecord],
        cfg: dict,
    ) -> StructureProposal: ...
```

## Consequences
1.  **Improved Type Safety:** IDEs and static type checkers (like mypy) can now verify that the lambdas in `registries.py` exactly match the required signature.
2.  **Explicit Documentation:** The `__call__` method parameters serve as explicit documentation for what data each stage expects and returns.
3.  **Prevented "Wiring" Bugs:** Future changes to contracts or callbacks will force an update to the Protocol, which in turn will flag the registry construction logic if it is not updated.
4.  **No Runtime Overhead:** `typing.Protocol` is a static-only construct and does not affect the execution performance of the pipeline.
