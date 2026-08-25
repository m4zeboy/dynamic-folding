from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class StabilityReport:
    """Stability characterization (pair-co-occurrence under perturbation)."""

    root: str
    runs: int
    perturbation: float
    seed: int
    pair_co_occurrence: float
    evaluable_pairs: int
    notes: list[str] = field(default_factory=list)
    contracts_version: int = 2

    def to_dict(self) -> dict:
        return {
            "contracts_version": self.contracts_version,
            "root": self.root,
            "runs": self.runs,
            "perturbation": self.perturbation,
            "seed": self.seed,
            "pair_co_occurrence": self.pair_co_occurrence,
            "evaluable_pairs": self.evaluable_pairs,
            "notes": list(self.notes),
        }
