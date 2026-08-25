from __future__ import annotations

import json
import sqlite3
from pathlib import Path


class EmbeddingCache:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(str(self.db_path))
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=NORMAL")
        return con

    def _init(self) -> None:
        with self._connect() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS embeddings (
                  key TEXT NOT NULL,
                  model_id TEXT NOT NULL,
                  content_hash TEXT NOT NULL,
                  vector_json TEXT NOT NULL,
                  text_content TEXT,
                  PRIMARY KEY (key, model_id, content_hash)
                )
                """
            )
            # Migration for existing DBs
            try:
                con.execute("ALTER TABLE embeddings ADD COLUMN text_content TEXT")
            except sqlite3.OperationalError:
                # Column already exists
                pass

    def get(self, key: str, *, model_id: str, content_hash: str) -> tuple[list[float], str | None] | None:
        with self._connect() as con:
            row = con.execute(
                "SELECT vector_json, text_content FROM embeddings WHERE key=? AND model_id=? AND content_hash=?",
                (key, model_id, content_hash),
            ).fetchone()
        if not row:
            return None
        return list(json.loads(row[0])), row[1]

    def put(self, key: str, *, model_id: str, content_hash: str, vector: list[float], text: str | None = None) -> None:
        vj = json.dumps(vector, ensure_ascii=True)
        with self._connect() as con:
            con.execute(
                "INSERT OR REPLACE INTO embeddings(key, model_id, content_hash, vector_json, text_content) VALUES(?,?,?,?,?)",
                (key, model_id, content_hash, vj, text),
            )

    def get_many_texts(
        self,
        keys: list[str],
        *,
        model_id: str,
        content_hash_by_key: dict[str, str] | None = None,
    ) -> dict[str, str]:
        """Fetch texts for a list of keys (e.g. for a cluster).

        The primary key is ``(key, model_id, content_hash)``, so multiple rows
        can exist for one ``(key, model_id)`` when a file's preprocessed text
        changed between runs. When ``content_hash_by_key`` is provided, a row is
        accepted only if its ``content_hash`` matches the requested hash for that
        key — pinning the result to the text that produced the current run's
        vectors, and keeping it deterministic in the presence of stale rows.
        When omitted, falls back to the legacy "any row for (key, model_id)"
        behavior. See ADR 0036 (F3).
        """
        if not keys:
            return {}

        # SQLite has a limit on the number of parameters (usually 999).
        out: dict[str, str] = {}
        with self._connect() as con:
            for i in range(0, len(keys), 900):
                batch = keys[i : i + 900]
                placeholders = ",".join(["?"] * len(batch))
                query = (
                    "SELECT key, content_hash, text_content FROM embeddings "
                    f"WHERE key IN ({placeholders}) AND model_id=?"
                )
                rows = con.execute(query, (*batch, model_id)).fetchall()
                for k, ch, t in rows:
                    if content_hash_by_key is not None:
                        want = content_hash_by_key.get(k)
                        if want is None or ch != want:
                            continue
                    if t:
                        out[k] = t
        return out
