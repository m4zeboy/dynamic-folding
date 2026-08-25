"""Sprint 19 — Step 6c: one-time SBERT model setup.

Downloads a sentence-transformers model from HuggingFace and saves it to
a well-known local directory so the pipeline can auto-discover it without
env vars or config edits.

This module is the ONLY part of the project that touches the network. The
pipeline itself remains offline-only at runtime per CLAUDE.md.

See `docs/learning/03-sbert-setup.md` for the rationale.
"""
from __future__ import annotations

import sys
from pathlib import Path

from dynamic_folding.core.paths import default_sbert_models_dir


DEFAULT_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


def _model_dir_is_populated(p: Path) -> bool:
    return p.exists() and p.is_dir() and any(p.iterdir())


def setup_sbert_model(
    model_name: str = DEFAULT_MODEL_NAME,
    *,
    target: Path | None = None,
    assume_yes: bool = False,
    force: bool = False,
) -> Path:
    """Download a sentence-transformers model and save it locally.

    Returns the absolute path to the saved model directory. Raises
    SystemExit if the user declines the prompt or sentence-transformers
    is not installed.
    """
    if target is None:
        target = default_sbert_models_dir() / model_name
    target = Path(target).resolve()

    if _model_dir_is_populated(target) and not force:
        print(
            f"model already present at {target}; skipping download "
            "(--force to redownload)",
            file=sys.stderr,
        )
        return target

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        raise SystemExit(
            "sentence-transformers not installed. "
            "Run `uv pip install -e .[sbert]` first.\n"
            f"(import error: {e})"
        )

    print(f"about to download `{model_name}` to {target}")
    print(
        "this is the ONLY network operation in the project; "
        "the pipeline itself stays offline at runtime",
        file=sys.stderr,
    )
    if not assume_yes:
        try:
            ans = input("continue? [Y/n] ").strip().lower()
        except EOFError:
            ans = ""
        if ans not in ("", "y", "yes"):
            print("aborted by user", file=sys.stderr)
            raise SystemExit(1)

    target.parent.mkdir(parents=True, exist_ok=True)
    model = SentenceTransformer(model_name)
    model.save(str(target))
    print(f"saved to {target}")
    return target
