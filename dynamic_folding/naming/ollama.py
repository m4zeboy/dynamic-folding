from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

from dynamic_folding.core.windows import sanitize_windows_folder_name
from dynamic_folding.naming.tfidf import (
    aggregate_name,
    extract_anchor_terms,
)
from dynamic_folding.naming.tfidf import (
    name_cluster as name_cluster_tfidf,
)


def _is_loopback_base_url(base_url: str) -> bool:
    p = urlparse(str(base_url))
    if p.scheme not in {"http", "https"}:
        return False
    host = p.hostname
    if not host:
        return False
    if host.lower() == "localhost":
        return True

    try:
        import ipaddress

        return ipaddress.ip_address(host).is_loopback
    except Exception:
        return False


def _log_ollama_fallback(reason: str) -> None:
    """Print a short stderr line whenever ollama->tfidf fallback fires.

    Without this, an unreachable Ollama looks identical to a successful
    Ollama call from the user's perspective: cluster names just appear,
    they happen to be TF-IDF style. This visibility is the difference
    between "the LLM is broken" and "the LLM was never reached."
    """
    print(f"[ollama->tfidf] {reason}", file=sys.stderr)


# Diagnostic instrumentation (Phase D / ADR 0024).
#
# When the env var DYNAMIC_FOLDING_NAMING_DEBUG_PATH is set, every call
# to `name_cluster_ollama` appends one JSONL line capturing what was
# sent to the LLM and what came back. Used to answer questions like
# "why did two clusters get the same name?" without guessing. The
# instrumentation was what surfaced the prompt-poisoning failure mode
# documented in ADR 0024.
#
# Opt-in: env var absent → zero overhead, no file created. Errors
# writing to the file (path invalid, disk full, etc.) never propagate
# — they degrade to a stderr warning so the pipeline keeps working.
_DEBUG_ENV_VAR = "DYNAMIC_FOLDING_NAMING_DEBUG_PATH"


def _dump_debug_record(record: dict) -> None:
    """Append one JSONL line to the diagnostic log if opt-in env var is set.

    Silent no-op when the env var is absent. Failure to write logs a
    short stderr warning and swallows the exception so the pipeline is
    not affected by instrumentation.
    """
    path = os.environ.get(_DEBUG_ENV_VAR)
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        print(
            f"[naming-debug] failed to write to {path}: {type(e).__name__}: {e}",
            file=sys.stderr,
        )


# Default prompt template. Free of concrete domain examples by design
# (see ADR 0024). Phase D diagnostic evidence under `gemma3:1b` showed
# small models regurgitate literal example phrases ("Licitações",
# "Certificação de Janelas") as the answer when the file-block signal
# is weak — producing duplicate names across unrelated clusters. The
# rules below state principles only; no example strings of folder
# names or banned tokens are embedded in the template.
#
# Do NOT reintroduce concrete domain examples here without re-testing
# under a 1–4 B parameter model first.
_DEFAULT_PROMPT_TEMPLATE = """\
Você é um especialista em taxonomia e organização de pastas.
Tarefa: Analisar a lista de arquivos e criar um NOME DE PASTA curto e temático.

Regras:
1. TEMA: Use substantivos que descrevam o ASSUNTO do conjunto de arquivos.
2. PROIBIDO PREÂMBULOS: Ignore termos administrativos e conectivos.
3. ELEGÂNCIA: O nome deve parecer uma pasta de arquivo profissional, não uma frase ou título de documento.
4. TAMANHO: 1 a 3 palavras (máximo 30 caracteres).
5. NUNCA use verbos no início; prefira substantivos como núcleo do nome.

Saída: Responda APENAS o nome e nada mais.
Arquivos do grupo:\n{files}\n
"""


# Grounded variant — split into a stable system message (role + rules) and
# a per-call user message (data + final "Nome:" cue). Smaller LLMs hold the
# system role more consistently than they hold instructions embedded mid-
# prompt; this split reduces meta-text bleed observed under the single-
# message β.2 design.

_GROUNDED_SYSTEM_MESSAGE = """\
Você é um classificador de pastas. Gera um nome curto (1–3 palavras,
máximo 30 caracteres) para um conjunto de arquivos.

PRINCÍPIO DE ANCORAGEM:
- Use APENAS palavras presentes no conteúdo dos arquivos.
- Não invente palavras novas, não use sinônimos de palavras ausentes.

REGRAS RÍGIDAS:
- Sem preâmbulos, sem explicações, sem pontuação adicional.
- Sem verbos no início.
- Não termine com preposições (de, da, do, em, para) ou conjunções (e, ou).
- Se os arquivos não compartilharem um tema claro, responda EXATAMENTE: _Ambíguo

Você responde APENAS o nome — mais nada."""


_GROUNDED_USER_TEMPLATE = """\
PALAVRAS RECORRENTES NO GRUPO: {anchor_terms}

ARQUIVOS:
{files}

Nome:"""


# Bottom-up aggregation variant (ADR 0037). Used when the proposer names a
# PARENT folder from its already-named children (+ loose-file terms) instead of
# from its raw document bag. The model summarizes coherent child labels — a far
# easier task than thematizing a heterogeneous grab-bag, which is what made an
# 8B model emit the generic "Group". Same anti-invention / anti-preamble rules.
_AGGREGATE_SYSTEM_MESSAGE = """\
Você é um classificador de pastas. Dada a lista de SUBPASTAS de uma pasta (e,
opcionalmente, termos de arquivos soltos), gere um NOME curto (1–3 palavras,
máximo 30 caracteres) para a pasta-mãe que ABRANJA os temas das subpastas.

REGRAS RÍGIDAS:
- Use apenas palavras presentes nos nomes das subpastas / termos fornecidos;
  não invente temas ausentes nem use sinônimos de palavras ausentes.
- Substantivos como núcleo; nunca comece com verbo.
- Sem preâmbulos, sem explicações, sem pontuação adicional.
- Não termine com preposições (de, da, do, em, para) ou conjunções (e, ou).
- Se as subpastas não compartilharem um tema comum, responda EXATAMENTE: _Ambíguo

Você responde APENAS o nome — mais nada."""


_AGGREGATE_USER_TEMPLATE = """\
SUBPASTAS:
{children}

TERMOS DE ARQUIVOS SOLTOS: {loose}

Nome da pasta-mãe:"""


# Light post-generation normalization: small models occasionally paraphrase
# the literal "_Ambíguo" escape token as Portuguese synonyms ("Nenhum",
# "Vazio", etc.). Rewriting them to the canonical token keeps the
# downstream contract stable (`_Ambíguo` is a meaningful folder name in
# the proposal; "Nenhum" would look like an arbitrary label).
#
# Note (β.2.b simplification): an earlier draft of this module also
# rejected outputs containing meta-tokens or longer than 5 words, on the
# hypothesis that LLM instruction-bleed would be common under llama3.1.
# Real auto-inspection showed (a) the system role split alone produces
# acceptable labels and (b) the rejection rules carried false-positive
# risk on legitimate multi-word labels. Removed in favor of this minimal
# normalization step. See ADR 0023.

_AMBIGUITY_SYNONYMS = frozenset(
    {
        "nenhum",
        "vazio",
        "indefinido",
        "incerto",
        "ambíguo",  # without leading underscore; normalize to "_Ambíguo"
        "ambiguo",  # no-diacritic variant
    }
)


def _normalize_ambiguity_synonyms(out: str) -> str:
    """Rewrite Portuguese synonyms of '_Ambíguo' to the canonical escape token.

    Returns the original (stripped) output unchanged when it is not a
    recognized synonym, including the empty string. The caller's existing
    post-sanitization empty check handles empty input as a fallback signal.
    """
    s = out.strip()
    if s.lower() in _AMBIGUITY_SYNONYMS:
        return "_Ambíguo"
    return s


def name_cluster_ollama(texts: list[str], cfg: dict) -> str:
    # Best-effort: any failure falls back to deterministic TF-IDF. In aggregate
    # mode (bottom-up parent naming, ADR 0037) the deterministic fallback is the
    # child-name/loose-term aggregator, not the document namer.
    top_terms = int(cfg.get("top_terms", 2))
    is_aggregate = bool(cfg.get("aggregate"))
    if is_aggregate:
        fallback = aggregate_name(texts, cfg.get("loose_texts", []) or [], top_terms=top_terms)
    else:
        fallback = name_cluster_tfidf(texts, top_terms=top_terms)

    base_url = str(cfg.get("base_url", "http://127.0.0.1:11434"))
    model = str(cfg.get("model", "")).strip()
    timeout_s = float(cfg.get("timeout_s", 30.0))
    top_k_files = int(cfg.get("top_k_files", 25))
    prompt_variant = str(cfg.get("prompt_variant", "grounded"))
    top_anchor_terms = int(cfg.get("top_anchor_terms", 5))

    # Diagnostic record. Populated as we proceed; dumped at every exit
    # point via `_dump_debug_record` (opt-in via env var; see helper).
    record: dict = {
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model": model,
        "variant": prompt_variant,
        "n_files": 0,
        "files_block": "",
        "anchor_terms": None,
        "system": None,
        "prompt": "",
        "raw_response": "",
        "normalized_response": "",
        "final_name": "",
        "used_fallback": False,
    }

    def _emit_fallback(name: str) -> str:
        record["used_fallback"] = True
        record["final_name"] = name
        _dump_debug_record(record)
        return name

    def _emit_success(name: str) -> str:
        record["final_name"] = name
        _dump_debug_record(record)
        return name

    if not model:
        _log_ollama_fallback("naming.model is empty in config")
        return _emit_fallback(fallback)
    if not _is_loopback_base_url(base_url):
        _log_ollama_fallback(f"naming.base_url is not a loopback address: {base_url}")
        return _emit_fallback(fallback)

    # HARD CHECK: If we have no real text, don't even call the LLM.
    # LLMs love to explain themselves in Portuguese when given nothing.
    valid_texts = [t.strip() for t in texts if t and t.strip()]
    if not valid_texts:
        _log_ollama_fallback("cluster has no usable text content")
        return _emit_fallback(fallback)

    files_sent = valid_texts[: max(0, top_k_files)]
    files = "\n".join(str(t) for t in files_sent)
    record["n_files"] = len(files_sent)
    record["files_block"] = files

    # Build the request body. Grounded variant separates `system` (role +
    # rules; stable across the call) from `prompt` (data + cue). Default
    # variant keeps the single-prompt shape from before β.2 for backwards
    # compatibility with any config that hard-codes `prompt_template`.
    body_dict: dict = {
        "model": model,
        "stream": False,
    }

    if is_aggregate:
        # Parent naming: `valid_texts`/`files` are the child folder names; the
        # loose-file terms come via cfg. Framing words ("SUBPASTAS"/"ARQUIVOS")
        # live only here, never in the tokenized fallback corpus.
        loose_raw = cfg.get("loose_texts", []) or []
        loose_terms = (
            extract_anchor_terms(
                [t for t in loose_raw if t and t.strip()], top_n=top_anchor_terms
            )
            if loose_raw
            else []
        )
        loose_str = ", ".join(loose_terms) if loose_terms else "(nenhum)"
        system_msg = str(cfg.get("aggregate_system_message", _AGGREGATE_SYSTEM_MESSAGE))
        user_tmpl = str(cfg.get("aggregate_prompt_template", _AGGREGATE_USER_TEMPLATE))
        body_dict["system"] = system_msg
        body_dict["prompt"] = user_tmpl.format(children=files, loose=loose_str)
        record["anchor_terms"] = list(loose_terms)
        record["system"] = system_msg
    elif prompt_variant == "grounded":
        anchor_terms_list = extract_anchor_terms(valid_texts, top_n=top_anchor_terms)
        anchor_terms_str = (
            ", ".join(anchor_terms_list)
            if anchor_terms_list
            else "(nenhum termo recorrente identificado)"
        )
        system_msg = str(cfg.get("system_message", _GROUNDED_SYSTEM_MESSAGE))
        user_tmpl = str(cfg.get("prompt_template", _GROUNDED_USER_TEMPLATE))
        body_dict["system"] = system_msg
        body_dict["prompt"] = user_tmpl.format(
            files=files, anchor_terms=anchor_terms_str
        )
        record["anchor_terms"] = list(anchor_terms_list)
        record["system"] = system_msg
    else:
        prompt_template = str(cfg.get("prompt_template", _DEFAULT_PROMPT_TEMPLATE))
        body_dict["prompt"] = prompt_template.format(files=files)

    record["prompt"] = body_dict["prompt"]

    body = json.dumps(body_dict, ensure_ascii=True).encode("utf-8")

    try:
        url = urljoin(base_url.rstrip("/") + "/", "api/generate")
        req = urllib.request.Request(url, method="POST", data=body)
        req.add_header("Content-Type", "application/json")

        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read()
        payload = json.loads(raw.decode("utf-8"))
        out = str(payload.get("response", ""))
    except Exception as e:
        _log_ollama_fallback(
            f"ollama call failed ({type(e).__name__}: {e}). "
            f"Is `ollama serve` running and `{model}` pulled?"
        )
        return _emit_fallback(fallback)

    record["raw_response"] = out

    # Normalize Portuguese synonyms of "_Ambíguo" so the canonical escape
    # token survives even when the model paraphrases.
    normalized = _normalize_ambiguity_synonyms(out)
    record["normalized_response"] = normalized

    name = sanitize_windows_folder_name(normalized, max_len=40)
    if not name:
        _log_ollama_fallback(
            "ollama returned an empty or unusable name after sanitization"
        )
        return _emit_fallback(fallback)
    return _emit_success(name)
