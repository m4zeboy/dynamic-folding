from __future__ import annotations

from dataclasses import dataclass, field

from dynamic_folding.contracts.stability import StabilityReport


@dataclass(frozen=True)
class CharacterizationResult:
    """Aggregate of all characterization properties for a single corpus run."""

    root: str
    corpus_metadata: dict
    config: dict
    structure: dict
    stability: StabilityReport
    performance: dict
    notes: list[str] = field(default_factory=list)
    contracts_version: int = 2

    def to_dict(self) -> dict:
        return {
            "contracts_version": self.contracts_version,
            "root": self.root,
            "corpus_metadata": dict(self.corpus_metadata),
            "config": dict(self.config),
            "structure": dict(self.structure),
            "stability": self.stability.to_dict(),
            "performance": dict(self.performance),
            "notes": list(self.notes),
        }
