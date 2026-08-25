# Project Audit — dynamic-folding

_Snapshot after the pywebview migration (ADR 0030), perf/staging fixes (ADR 0031), and the
report restyle (ADR 0032). Every load-bearing claim below was verified against code._

This document tracks refinement work. Findings are grouped by category with severity and
file references; the work is organized into independent tranches (T1–T5) at the bottom.

## Status legend
done · doing · planned (⬜) · deferred/backlog (⏸)

---

## Findings

### A. Documentation drift — actively misleading
| # | Finding | Where | Sev |
|---|---------|-------|-----|
| A1 | Docs still call the TUI "Textual" (interactive section, `_launch_tui` text, Sprint-14, README keyboard shortcuts) — it's pywebview (`cli.py` → `launch_webview`) | `docs/SPEC.md`, `README.md` | High |
| A2 | "Babel compiles JSX in-browser / no build step" is stale after the PR #44 precompile (`index.html` loads `app.js`, not `babel.min.js`) | ADR 0030, `docs/SPEC.md` | High |
| A3 | Contract version mislabeled v1; `StructureProposal` is v3 (others v2) | `docs/CONTRACTS.md`, `CLAUDE.md` | High |
| A4 | Stage list omits `reducer` and predates the "proposal emitted last" reorder | `CLAUDE.md` | Med |
| A5 | ADR statuses stale: 0012 "Proposed"→Superseded; 0014 "Proposed"→Accepted | `docs/ADR/0012`, `0014` | Med |

### B. Version metadata
| # | Finding | Where | Sev |
|---|---------|-------|-----|
| B1 | `__version__ = "1.1.0"` vs `pyproject.toml` `version = "1.2.0"` (runtime/report show 1.1.0) | `dynamic_folding/__init__.py:3` | Med |

### C. Dead / vestigial code
| # | Finding | Where | Sev |
|---|---------|-------|-----|
| C1 | `confirm_proposal` imported but **never called** → dead import; function only hit by tests | `cli.py:15`, `core/triage.py` | High |
| C2 | Entire Textual interactive stack vestigial (`TriageApp`/`TriageScreen`/`DynamicFoldingApp` ~883 LOC + `textual` dep). ADR 0030 already flags it as planned cleanup | `tui/app.py`, `core/triage.py` | High |
| C3 | Unused imports (`dataclass`, `EmbeddingCache`, `ProgressStage`); unused `dummy_ext` local | `core/registries.py`, `core/pipeline.py` | Low |

### D. Pipeline timings / progress honesty
| # | Finding | Where | Sev |
|---|---------|-------|-----|
| D1 | `timings` `clustering`/`naming` always 0.0 (cosmetic markers); `reducer` not timed — report "Etapas" & Sprint-19 surface show misleading 0.000s | `core/pipeline.py` | Med |
| D2 | `_WebProgress.advance` is a no-op → GUI shows no per-file progress | `tui/webview_app.py` | Low |

### E. Packaging
| # | Finding | Where | Sev |
|---|---------|-------|-----|
| E1 | `tui/web/vendor/babel.min.js` (~3.1 MB) ships in the wheel but is never loaded at runtime (only regenerates `app.js` offline) → exclude from wheel | `pyproject.toml`, `tui/web/vendor/` | High |
| E2 | Redundant `[extract]` extra duplicates already-required `pypdf`/`Pillow` at lower bounds | `pyproject.toml:49-52` | Low |
| E3 | `[office]` (docx/pptx) is the real optional path for the default `type_aware` extractor but undocumented | `pyproject.toml:57-60` | Low |

> **Rejected recommendation:** an audit pass suggested moving `scikit-learn`/`hdbscan` to optional
> extras. **Do NOT** — `naming/tfidf.py:3` imports `TfidfVectorizer` unconditionally and TF-IDF is
> the *default* namer (kmeans the default clusterer); making sklearn optional breaks the default run.

### F. Repo hygiene
| # | Finding | Where | Sev |
|---|---------|-------|-----|
| F1 | `idea.txt` (PT-BR design notes) at repo root → move to `docs/` | `idea.txt` | Low |
| F2 | Ensure transient preview/report artifacts are git-ignored (`_preview_*.html`) | `.gitignore` | Low |

### G. Refactor opportunities (higher risk — touch core logic)
| # | Finding | Where | Sev |
|---|---------|-------|-----|
| G1 | `_build_level_from_tree` & `_build_level` duplicate name-gen/embedding/routing; name-match cosine repeats ~4× | `proposal/proposer.py` | Med |
| G2 | `embed_text_callback` builds dummy DTOs + re-imports per call | `core/pipeline.py` | Low |

### H. Test coverage gaps (additive)
| # | Finding | Where | Sev |
|---|---------|-------|-----|
| H1 | `tui/webview_app.py` only mocked, never unit-tested (`_quiet_ml_libraries`, `_WebProgress`) | `tests/` | Low |
| H2 | Brittle exact-string assertions in render/TUI polish tests | `tests/test_render_polish.py`, `test_tui_polish.py` | Low |

---

## Tranche backlog

| Tranche | Scope | Findings | Risk | Status |
|---------|-------|----------|------|--------|
| **T1** | Docs sync + `__version__` bump + this audit doc | A1–A5, B1 | none (docs) | done |
| **T2** | Code/packaging hygiene: dead imports, `dummy_ext`, exclude `babel.min.js` from wheel, drop `[extract]` extra, move `idea.txt`, gitignore previews | C3, E1, E2, F1, F2 | low | done |
| **T3** | Remove dead Textual stack (`tui/app.py`, `core/triage.py`, `confirm_proposal`, `textual` dep) + update tests + ADR | C1, C2 | medium | done |
| **T4** | Pipeline timings honesty (reconcile `timings` dict) | D1 | medium | ⏸ |
| **T5** | Proposer dedup refactor (extract shared helpers) | G1 | higher | ⏸ |

Each tranche = its own branch/PR, full suite green (baseline: 228 passed / 3 skipped).
T4/T5 are deferred backlog (tracked as issues), not executed in this pass.
