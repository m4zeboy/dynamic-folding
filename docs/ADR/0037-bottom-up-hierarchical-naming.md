# ADR 0037: Bottom-up Hierarchical Naming (selectable)

Date: 2026-06-12

## Status

Accepted. Adds a selectable naming strategy to the proposer. Builds on
[ADR 0031](0031-tui-performance-and-staging-hardening.md) (naming runs inside the
proposer) and [ADR 0024](0024-grounded-prompt-and-anchor-pollution.md) /
[ADR 0023](0023-ollama-naming-minimal-normalization.md) (Ollama namer design). No
contract/DTO change — `FolderNode.name` is still a string, so no version bump.

## Context

After the snippet-flow fix ([ADR 0036](0036-snippet-flow-and-config-default-consolidation.md))
a real 57-file run produced 7 clean groups, but one top-level folder was named the
meaningless **"Group"**, while its two children named cleanly ("Histórico Escolar
Arquitetura", "Declarações e Certificados Profissionais").

**Diagnosis (traced, not guessed — debug instrument + cache, per the snippet-fix
discipline):** `"Group"` is the tfidf empty-text sentinel, but the proposer
substitutes filenames on empty text, so it should be unreachable. Inspecting the
actual cache showed the node's files had **non-empty** content (4/5 real text), and
the deterministic tfidf path over those texts yields a real name (`de_escolar`),
never `"Group"`. Conclusion: **Ollama (llama3.1:8b) literally returned the generic
"Group"** when asked to thematize a genuinely heterogeneous parent bag (residence
proof + declarations + school history + course portaria). This is a weak-LLM failure
mode on heterogeneous input, *not* an empty-text bug.

The structural cause is **independent per-node naming**: every folder, at every
level, is named only from its own documents, with no information flowing between
levels (the `namer()` call sites in `proposer.py`). A parent cannot borrow the
meaning its well-named children already captured.

## Decision

Add a **selectable** naming strategy — `proposal.naming_direction` ∈
`{"per_node", "bottom_up"}` — rather than replacing the current behavior. This lets
Chapter 4 A/B-compare the two, removes regression risk (revert = flip the flag), and
fits the config-driven architecture.

1. **`bottom_up` inverts naming at internal nodes.** Leaf clusters are still named
   from their documents; each parent is then synthesized from **its children's names
   + its own loose-file terms** (the files not placed in any subfolder). Asking the
   LLM to summarize a handful of coherent child labels is a far easier task than
   thematizing a heterogeneous bag.
2. **Engine: Ollama summarization + deterministic TF-IDF fallback** (mirrors the
   existing namer architecture). A new `_AGGREGATE` Ollama prompt frames "subpastas"
   vs "arquivos soltos"; `tfidf.aggregate_name` is the offline/deterministic fallback
   and the test path. The "subpastas/arquivos" framing words live **only** in the
   prompt, never in the strings TF-IDF tokenizes (and are stopword-guarded anyway),
   so they cannot leak as anchor terms.
3. **Structure-invariant by construction.** A shared `proposer._finalize_node` helper
   builds every `FolderNode`; it computes `node_files` and `subfolders` identically
   for both directions — only the *source* of `name` differs. All three naming sites
   (`_build_level_from_tree`, `_build_level`, top level) now *recurse, then name*.
4. **Defaults mirror the two-stack pattern.** `config.py` system default stays
   `per_node` (the zero-deps/test stack is unchanged — all prior tests pass byte-for-
   byte); `config/default.toml` opts into `bottom_up` for real runs.
5. **Fallback-name hygiene.** A parent never inherits a child's sentinel label
   (`Group`/`unnamed_group`/`_Ambíguo`); those are filtered before aggregation, and
   if *all* children are sentinels the parent degrades to per-node document naming.

## Boundaries (verified)

- **B1 — structure-invariance (primary):** `per_node` vs `bottom_up` on a fixture
  yield identical folder/file membership and nesting; only names differ. Also
  evidenced by all 221 pre-existing tests passing unchanged.
- **B2 — no garbage parents:** internal nodes are never sentinel-named when children
  carry real names; `aggregate_name` is child-derived. (Real-case check: the actual
  "Group" node's deterministic bottom-up name is `escolar_de_historico`, not "Group".)
- **B3 — determinism:** `bottom_up` + tfidf is identical across runs.
- **B4 — offline + fallback:** a non-loopback / failed Ollama call falls back to the
  deterministic aggregator; the pipeline never crashes.
- **B5 — reversible:** `per_node` remains; flip `proposal.naming_direction` to revert.

`name_match` is **not** an acceptance metric: a good parent name synthesized from
diverse children can score low cosine against the muddy full-descendant centroid.

## Consequences

- Real runs (`config/default.toml`, Ollama) get parent folders that summarize their
  children instead of generic placeholders. The two strategies are now comparable
  evidence for Chapter 4.
- **The deterministic TF-IDF aggregation is blunt** (e.g. `escolar_de_historico` —
  the Portuguese stopword "de" leaks and it can lean toward one child). It is a
  *fallback*, not the primary path; acceptable for offline/test use. Filtering
  Portuguese stopwords from anchor terms is a separate follow-up that would improve
  both this and per-node tfidf naming.
- Out of scope: leaf-level sibling-collision dedup (`… / _2`); a formal Likert
  evaluation of naming quality (a Chapter-4 instrument).

## Verification

- `uv run pytest` — full suite green incl. `tests/test_bottom_up_naming.py` (B1–B4).
- Manual (SBERT+Ollama): clear the cache, run the default config on the corpus;
  confirm the former "Group" parent now has a synthesized name and the group
  *structure* is identical to a `per_node` run. Keep both reports as Ch.4 A/B evidence.
