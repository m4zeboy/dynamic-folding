# 03 — Why a `setup-sbert` command (and why we kept "offline at runtime")

**Context.** During the first attempt to run the Sprint 19 experiments on
real datasets, the user hit a five-step manual setup ritual to enable the
SBERT embedding provider: install the package, pick a model, download it,
save it somewhere, set an environment variable. None of those steps was
hard in isolation — but together they were a wall, and the friction came
from a design tension worth writing down.

This note captures the analysis and the chosen fix so future students (or
defesa committee members reading the repo) understand *why* this part of
the project looks the way it does.

---

## The constraint that created the friction

The project has a hard rule, declared in `CLAUDE.md`:

> **Offline only.** No network calls anywhere in the pipeline or tests.
> SBERT embedding (`embedding.provider = "sbert"`) loads strictly from
> a user-supplied local `embedding.model_path` and must refuse to download.

This rule is **correct** and load-bearing for the TCC. If the pipeline
phoned home during characterization, every metric in the chapter would
become contingent on network latency, model registry availability, and
HuggingFace's rate limits on the day of the experiment. The chapter
would also be unreproducible: someone reading it in 2027 might find
the model checkpoint was renamed or removed.

So: keep the rule.

The mistake was conflating two different concerns under that one rule:

1. **Runtime offline-ness.** When the user runs `characterize`, the tool
   must not touch the network. ← This is what the rule actually requires.
2. **Setup-time offline-ness.** The user must somehow obtain the model
   in the first place. ← This is *not* what the rule requires, but the
   project enforced it anyway by making setup the user's manual problem.

If conflated, the only way to get a model onto disk is to do it
yourself, by hand, with a Python snippet — and that's the wall we hit.

## Three options we considered

**Option A — Documentation only.** Write a `docs/SETUP.md` with the
exact commands. Cheap. Doesn't fix anything structurally; still five
steps, just with a better reference to copy from. Rejected.

**Option B — A setup CLI command, env var still required.** Add
`dynamic-folding setup-sbert` that downloads + saves the model. User
still sets `DYNAMIC_FOLDING_SBERT_MODEL_PATH` afterward. Reduces five
steps to two. Better, but env vars on Windows + Git Bash are a known
footgun (forgetting `source ~/.bashrc`, opening a fresh terminal that
loses the variable, persisting incorrectly across reboots). Rejected.

**Option C — Setup command + auto-discovery, no env var needed.** Two
changes that compose:
- A `setup-sbert` command that saves the model to a well-known path:
  `%LOCALAPPDATA%/DynamicFolding/models/<model>/` on Windows, or
  `~/.dynamic-folding/models/<model>/` elsewhere (mirrors the existing
  cache_db convention from `dynamic_folding/core/paths.py`).
- The pipeline's `resolve_effective_config` learns to look in that
  well-known directory when there's no env var and no explicit
  `embedding.model_path`. If exactly one subdirectory is present, it
  uses it. If zero or more than one, behavior is unchanged.

The env var still works as an explicit override for power users with
multiple models. Backward-compatible.

**Chosen: Option C.**

## The resolution order, written down

When deciding which SBERT model directory to load, the pipeline now
checks four sources in order:

1. **Explicit `embedding.model_path` in the TOML config.** Highest
   priority — a config file is a deliberate, version-controllable
   declaration.
2. **Env var `DYNAMIC_FOLDING_SBERT_MODEL_PATH`.** Useful for CI and
   for users who want to switch between multiple checkpoints.
3. **Auto-discovery from the default models dir.** If exactly one
   subdirectory exists, use it. Removes the need for an env var in
   the common single-model case.
4. **Unset.** Falls through to the existing failure path; `doctor`
   reports the issue with a friendly hint that points at
   `setup-sbert`.

Each layer is a strictly more permissive default than the layer above.
A user can always opt up the chain (set an env var, write a config) and
get back the previous behavior.

## What this looks like for a fresh user

After Option C, the full setup ritual is:

```bash
uv pip install -e .[sbert]
uv run dynamic-folding setup-sbert      # one prompt: confirm download
uv run dynamic-folding doctor           # both rows say OK
uv run dynamic-folding experiment "datasets/..."
```

Three commands instead of five. No env vars to remember. No Python
snippets to copy. The setup-sbert command is the *only* part of the
project that ever touches the network, and it announces this loudly
before doing so.

## TCC narrative implication

The chapter (or its appendix) can now describe the offline-at-runtime
property cleanly:

> "The proposed tool runs all characterization experiments in an
> offline configuration: at runtime no network call is made by any
> stage of the pipeline. A separate one-time setup command,
> `dynamic-folding setup-sbert`, performs the only network activity
> required by the system: downloading the embedding model checkpoint
> into a local cache. After this setup step, the entire characterization
> can be reproduced offline by re-executing
> `dynamic-folding experiment <datasets_dir>`."

That sentence is much stronger than describing five manual steps. It
also pre-empts the obvious defesa question: *"how do you guarantee
reproducibility if your tool depends on a remote model?"* — answer:
*"the model lives on disk, and there is exactly one moment, separated
from experiments, when the network is touched."*

## What we did not do (and why)

- We did **not** make `sentence-transformers` a hard dependency. It
  remains an optional extra (`.[sbert]`) so users who only want to test
  the deterministic FakeEmbedder don't need to download torch.
- We did **not** add a `--model` flag that downloads at runtime. That
  would violate the offline rule.
- We did **not** auto-pick a model when multiple are present. Ambiguity
  is better surfaced (let the user pick via env var) than guessed.

## References

- `CLAUDE.md` — the offline-only hard rule.
- `dynamic_folding/core/paths.py` — platform-aware default location
  helpers.
- `dynamic_folding/core/setup_sbert.py` — the new setup command's
  implementation.
- `dynamic_folding/core/pipeline.py::resolve_effective_config` — where
  the resolution order lives.
