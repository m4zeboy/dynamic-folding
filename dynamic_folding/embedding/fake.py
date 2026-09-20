from __future__ import annotations

import hashlib
import re


class FakeEmbedder:
    """Deterministic embedder for tests/offline scaffolding.

    Produces a vector of floats in [0, 1) derived from sha256(text).
    """

    def __init__(self, *, dim: int = 16, model_id: str | None = None):
        if dim <= 0:
            raise ValueError("dim must be > 0")
        self.dim = dim
        # Include dim in the model_id so the embedding cache never returns
        # vectors of a different dimensionality for the same text.
        self.model_id = model_id if model_id is not None else f"fake:v2:dim={dim}"

    def embed_text(self, text: str) -> list[float]:
        # Token-based deterministic embedding: similar texts that share tokens
        # will have more similar vectors than a pure whole-string hash.
        tokens = [t for t in re.split(r"[^a-zA-Z0-9]+", text.lower()) if t]
        if not tokens:
            tokens = [""]

        acc = [0] * self.dim
        for tok in tokens:
            digest = hashlib.sha256(tok.encode("utf-8")).digest()
            # Expand digest if needed.
            buf = bytearray(digest)
            cur = digest
            while len(buf) < self.dim:
                cur = hashlib.sha256(cur).digest()
                buf.extend(cur)

            for i in range(self.dim):
                acc[i] = (acc[i] + buf[i]) % 256

        # Add a small whole-text signature to keep punctuation differences.
        raw = hashlib.sha256(text.encode("utf-8")).digest()
        raw_buf = bytearray(raw)
        cur2 = raw
        while len(raw_buf) < self.dim:
            cur2 = hashlib.sha256(cur2).digest()
            raw_buf.extend(cur2)
        for i in range(self.dim):
            acc[i] = (acc[i] + (raw_buf[i] // 8)) % 256

        # Normalize to [0, 1)
        return [x / 256.0 for x in acc]
