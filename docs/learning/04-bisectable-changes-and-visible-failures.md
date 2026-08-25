# 04 — Bisectable changes and visible failures

**Context.** A session after Sprint 19 shipped to main, the user ran the
tool on real datasets and hit four visible regressions: dot-folders in
the TUI directory picker, missing UI panel polish, cluster names like
`pdf_path` instead of LLM-generated Portuguese, and "too many
subgroups." The user said *"It was already fixed one time, I don't
know why is happening again."*

That sentence is the through-line of this note. The fixes *had*
existed. They were on a parallel branch (`sprint-20`) that was branched
*before* Sprint 19 merged, so when Sprint 19 landed on main, the
sprint-20 work was effectively isolated. Worse, sprint-20's TUI fix
was bundled in a single commit with an architectural change ("Hard ML
mandate" — removing FakeEmbedder and TF-IDF fallback) that would have
broken Sprint 19's offline test suite if cherry-picked naïvely.

This note distills the engineering principles that turned a mess into
four small, reviewable PRs, and the patterns that caused the mess in
the first place.

---

## Principle 1 — One commit, one concern

The original sprint-20 commit `061c49e` did six things at once:

- Filter dot-folders from the TUI directory picker.
- Add panels and rounded borders to the TUI.
- Add an ErrorScreen for failure reporting.
- Make the `tui` CLI subcommand load `config/default.toml`.
- Set Ollama temperature to 0.0 with stricter prompts ("naming grounding").
- Remove FakeEmbedder and TF-IDF fallback registrations ("Hard ML mandate").

The first four are user-visible UX fixes. The fifth changes naming
output. The sixth is an architectural philosophy change that breaks
every test relying on offline determinism.

**These belong in six different commits, ideally six different PRs.**
When they're bundled, you cannot adopt the fixes without also adopting
the philosophy. You cannot revert the philosophy without losing the
fixes. The bundle becomes harder to handle than the sum of its parts.

The session's fix was to split that one commit into four targeted
PRs (#17–#20), each with one concern, each independently reviewable
and revertible.

> **Rule of thumb:** if you can describe a commit's purpose with the
> word "and" — "fix dot-folders **and** change config defaults
> **and** remove fallbacks" — you have a bundle. Split it.

## Principle 2 — Silent fallbacks are debugging poison

The user's complaint about `pdf_certificado` cluster names had two
possible causes:

1. Ollama is being called and producing those names (the LLM is bad).
2. Ollama is *not* being called and TF-IDF is producing those names.

The original code couldn't distinguish them. When Ollama failed for
*any* reason — connection refused, timeout, bad response, missing
model — the code returned `fallback` (TF-IDF) silently. From the
caller's perspective, the two scenarios looked identical: cluster
names just appeared, they happened to be TF-IDF-ish.

**A silent fallback is a hidden state machine.** The user sees the
output, not the path that produced it. Debugging becomes guessing.

PR #17 added one `print(..., file=sys.stderr)` line at every fallback
path with the reason. Diff size: +23 / −1. Time to write: minutes.
The first run after merge produced this on stderr:

```
[ollama->tfidf] ollama call failed (URLError: <urlopen error
[WinError 10061] No connection could be made because the target
machine actively refused it>). Is `ollama serve` running and
`llama3.1` pulled?
```

Mystery solved in one line. Ollama wasn't running. Without that line,
we'd have spent a session chasing the wrong thing (e.g., assuming the
prompts were wrong, or that the embedder was misconfigured).

> **Rule of thumb:** if your code has a `try / except: return fallback`
> pattern, the `except` branch should *always* leave a trail —
> stderr, log, telemetry, *something*. The fallback is the
> exceptional path; treat it as exceptional.

## Principle 3 — Configuration parity across entry points

The TUI was loading the bare system defaults (fake embedder + tfidf +
minimal preprocess template) while the `run` and `characterize`
subcommands loaded `config/default.toml` (sbert + ollama + hdbscan +
proper template). Same pipeline, three entry points, three different
default behaviors.

The fix was *literally nine lines* in `cli.py` (PR #18) — extract
`_resolve_cli_config_path(args.config)` once, pass it to every
subcommand's pipeline call. The TUI app already accepted a
`config_path` parameter; only the CLI side was missing the wiring.

The lesson is broader than this one bug: **when a tool has multiple
entry points (CLI subcommands, library function, TUI), the default
configuration resolution must go through a single helper.** When each
entry point reimplements the lookup, drift is inevitable, and the
drift hides as different visible symptoms (here, "the names are bad,
but only in the TUI").

> **Rule of thumb:** `_resolve_cli_config_path` is a *contract*, not
> a convenience. Any new subcommand that takes a `--config` argument
> must call it; any subcommand that wires user input to the pipeline
> must call it.

## Principle 4 — Make divergent branches loud

`sprint-20` quietly diverged from main for ~5 days. During those
5 days:

- Sprint 19 landed on main (PR #14).
- Sprint-20 accumulated 4 commits on its old base.
- The user's main worktree was checked out to `sprint-20`, masking
  the divergence visually.

When the user opened a fresh worktree off main and ran the tool,
the regressions surfaced instantly. The divergence was real for
days; it just didn't surface until someone ran from the "wrong"
worktree.

There's no purely-technical fix for this — branches diverge, that's
their job — but there are two practical guards:

1. **Rebase divergent branches early and often.** A `sprint-20`
   that's rebased nightly onto `main` reveals integration costs
   immediately. A `sprint-20` that drifts for a week presents the
   full bill at merge time.
2. **Use `git worktree list` deliberately.** When debugging a
   "regression," the first thing to check is *which branch each
   worktree is on*. The user's main worktree being on `sprint-20`
   was the smoking gun, but it's easy to miss.

> **Rule of thumb:** if you have more than one worktree on the same
> repo, write down which branch each one tracks. Worktrees are a
> superpower for parallelism but a liability for "where am I,
> exactly?" debugging.

## Principle 5 — Reconciliation is a phased plan, not a merge

When two valuable lines of work diverge, you don't merge them — you
*reconcile* them. The reconciliation in this session had four phases:

- **Phase 1 (small PRs, one concern each):** the visible
  regressions. PR #17 (logging), PR #18 (config parity), PR #19
  (TUI polish), PR #20 (PDF extractor cherry-pick).
- **Phase 2 (deferred decision):** the Hard ML mandate.
  Architectural; needs its own ADR-level discussion and a learning
  note before any code change.
- **Phase 3 (deferred sprint):** sprint-20's metrics + LLM-judge
  overlap with Sprint 19's `analyze.py` / `characterize.py`.
  Requires sprint-sized reconciliation, not a side-quest in a
  bug-fix session.
- **Phase 4 (cleanup):** delete `sprint-20` branch only after
  Phase 3 absorbs its content; preserve as historical reference
  until then.

Writing this plan down before opening any PR was the move that
prevented the session from sprawling. Each PR could point to
"this is Phase 1 step N of the plan; here's why it's small; here's
why these other concerns are out of scope."

> **Rule of thumb:** before reconciling divergent branches, write a
> phased plan with explicit "out of scope" items. The plan does
> three things: (1) prevents scope creep mid-PR, (2) gives reviewers
> context for why a PR is *small*, (3) preserves the deferred work
> as a queue, not a forgotten pile.

## What this means for the TCC

The empirical chapter benefits directly from these principles in two
ways:

1. **Reproducibility narrative.** The chapter can claim, truthfully,
   that the tool's experiments are reproducible offline because each
   stage is independently testable and the only network operation
   (model download) is in a separate, explicit setup command.
   Principles 1, 2, and 3 are what make that claim defensible.
2. **Engineering process is part of the artifact.** Even if the
   defesa committee asks "how did you handle a critical regression
   between sprints?", you have an honest answer: the diagnostic
   visibility (Principle 2) revealed it within minutes, the
   reconciliation plan (Principle 5) absorbed the parallel work
   without losing either side, and the bisectable PRs (Principle 1)
   meant any individual change could be reverted in seconds. That
   kind of process maturity is uncommon in undergraduate work.

## References

- PR #17 — `fix(naming): log to stderr whenever ollama falls back`
- PR #18 — `fix(cli): tui subcommand loads config/default.toml`
- PRs #19, #20 — pending Phase 1 work
- `docs/learning/03-sbert-setup.md` — earlier example of separating
  setup-time and runtime concerns
- `docs/ADR/0018-empirical-characterization-no-ground-truth.md` —
  Sprint 19's framing
