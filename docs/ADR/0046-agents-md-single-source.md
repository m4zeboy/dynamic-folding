# ADR 0046: `AGENTS.md` as the single source of agent instructions

## Status
Accepted (2026-08-05). Process/tooling decision, taken while migrating the
project's day-to-day agent from Claude Code to Codex. No runtime behaviour
changes; no thesis number is touched.

## Context

The repo carried **three** agent-instruction files at the root, and they had
silently diverged:

| File | Lines | State on 2026-08-05 |
|---|---|---|
| `CLAUDE.md` | 111 | Current. The only one maintained. |
| `AGENTS.md` | 67 | A byte-copy of an older `CLAUDE.md`, frozen at commit `4de9135`. |
| `GEMINI.md` | 61 | A third, independently-written structure. |

The divergence was not cosmetic. `AGENTS.md` — **the file Codex reads** — was
missing every section that cannot be re-derived from the source code:

- **§ Como trabalhar com o autor** — go slow; never use subagents for
  engineering; **coach, never ghostwriter** for the author's own prose; the
  Windows UTF-8 `Add-Content` corruption trap; the PowerShell here-string
  quoting trap; the abandoned Sprint-19 characterization stack.
- **§ Fluxo de trabalho** — the `TODO.md` → `DONE.md` discipline and the 🔒
  guard rule protecting the frozen-corpus numbers.
- **§ Learning notes** — the master-the-concept-first gate on `docs/learning/`.

It also still carried a **revoked** rule ("No content extraction beyond metadata
in the MVP"), retired by ADR 0044. `GEMINI.md` listed a `render` pipeline stage
that does not exist and omitted `reducer`.

An agent opening this repo through `AGENTS.md` would therefore read a competent
technical briefing with zero process guardrails, plus one rule the project had
explicitly reversed. The concrete risk: ghostwriting thesis prose (which voids
the work's authorship), spawning subagents (which has burned the author's
session token limit twice), and corrupting the accented UTF-8 training diary.

The root cause is structural, not clerical: **three files that must say the same
thing will drift**, because only the one in daily use gets edited.

## Decision

1. **`AGENTS.md` is the single source.** It carries the full content, and is the
   file to edit when a rule changes. Chosen over `CLAUDE.md` because it is the
   emerging cross-tool convention and is read natively by Codex, the agent now
   in daily use.
2. **`CLAUDE.md` and `GEMINI.md` become pointers** — a few lines directing the
   reader to `AGENTS.md`, plus an explicit "do not write content here". They
   exist only because those tools look for them by name.
3. **Plain files, not symlinks.** Git symlinks on Windows require
   `core.symlinks` support and a developer-mode or elevated checkout; the
   failure mode (a pointer file silently containing the literal target path) is
   worse than the duplication it saves.
4. **Two pieces were salvaged before collapsing:** the "Triple Check"
   (contract → registry → fallback, before touching a stage), which existed
   **only** in `GEMINI.md`, moved to `AGENTS.md` § Triple check; and the local
   dev-server commands, which lived only in the untracked, Claude-specific
   `.claude/launch.json`, moved to `AGENTS.md` § Commands.
5. **The coach-never-ghostwriter rule is stated inline as prose**, not only by
   reference to the `coach-escrita` skill. Skill auto-discovery differs per tool
   and `.claude/skills/` is a Claude-shaped path; the hard rule must survive an
   agent that never loads the skill file. The skill remains the detailed method.

## Consequences

### Positive
- One file to edit; drift becomes structurally impossible rather than merely
  discouraged.
- Codex reads the current guardrails, including the two Windows traps that have
  each already cost a reversion.
- The revoked MVP metadata-only rule and the wrong pipeline diagram are gone.

### Negative / trade-offs
- Anyone used to editing `CLAUDE.md` must retrain; the pointer file says so
  loudly, which is the whole mitigation.
- `AGENTS.md` is now long and mixes English technical rules with PT-BR process
  rules. This mirrors the project as it actually is (code in English, thesis and
  author-facing work in PT-BR) and was preferred over splitting it into two
  files, which would reintroduce the drift this ADR exists to kill.

## Out of scope
- Whether Codex discovers project-level skills in `.claude/skills/` — to be
  tested empirically; the inlined rule (decision 5) makes the answer non-blocking.
- Renaming `.claude/skills/` to a tool-neutral path. Deferred: the directory is
  the only path under `.claude/` that git tracks, and renaming it touches
  `.gitignore`, `thesis/STATUS.md` and the skills' own cross-references.
- Uninstalling Claude Code, or removing the `ai-memory` hook chain from the
  user's global settings. Unrelated to this repo.
