"""Render a self-contained PT-BR HTML report comparing several corpora
side by side (ADR 0045: aggregate-first structure).

Reuses the single-corpus machinery in ``comparison_report.py`` verbatim for
every corpus-agnostic and per-corpus section; this module only adds the
pieces the ADR calls out as new: the multi-corpus hero, the aggregate
("coração") section, and the multi-corpus limitations section. Anonymization
already happened upstream in ``multicorpus.py::run_multicorpus_comparison``
(each ``ComparisonResult.root`` is already a "Corpus N" label, never a real
path) — this module never sees or touches real directory names.
"""
from __future__ import annotations

from pathlib import Path

from dynamic_folding.evaluation.comparison import COMPARISON_ALGORITHMS
from dynamic_folding.evaluation.comparison_report import (
    MATRICES_PROSE,
    REDUCER_PROSE,
    _SENTINEL,
    _base_config,
    _brand,
    _coverage,
    _esc,
    _load_template,
    _score_text,
    _section,
    _section_figure,
    _section_intro,
    _section_matrices,
    _section_reducer,
    _section_silhouette,
    _section_structural,
    _table,
)
from dynamic_folding.evaluation.multicorpus import MultiCorpusComparison


def _multi_hero(multi: MultiCorpusComparison) -> str:
    labels = " / ".join(label for label, _ in multi.items)
    total_files = sum(res.n_files for _, res in multi.items)
    tags = [
        f"{len(multi.items)} corpus",
        "2 lentes (silhueta + DBCV)",
        "sem veredito",
        "n=3 (ilustrativo)",
        "determinístico · offline",
    ]
    tag_html = "".join(f"<span class='tag'>{_esc(t)}</span>" for t in tags)
    return (
        "<section class='hero'>"
        "<div class='hero-title'>Comparação de algoritmos — 3 corpus</div>"
        f"<div class='hero-sum'>{_esc(labels)} · {total_files} arquivos no total</div>"
        f"<div class='hero-tags'>{tag_html}</div></section>"
    )


def _section_aggregate(multi: MultiCorpusComparison) -> str:
    """The heart of the report: three corpus x algorithm tables, one per lens,
    plus a placeholder for the author's cross-corpus reading (guard-rail #3 —
    no authored prose from the agent)."""
    by_corpus = [
        (label, {a.algorithm: a for a in res.algorithms}) for label, res in multi.items
    ]

    sil_header = [("corpus", "")] + [(algo, "num") for algo in COMPARISON_ALGORITHMS]
    sil_rows = [
        [(label, "name")]
        + [
            (
                _score_text(by_algo[algo].score, by_algo[algo].reason)
                if algo in by_algo
                else "n/a",
                "num",
            )
            for algo in COMPARISON_ALGORITHMS
        ]
        for label, by_algo in by_corpus
    ]
    sil_table = _table(sil_header, sil_rows)
    sil_caption = (
        "<div class='lead'>silhueta — espaço 384-dim, viés convexo; descritor por "
        "algoritmo (compare por coluna, mesmo algoritmo entre corpora)</div>"
    )

    dbcv_header = [("corpus", "")] + [(algo, "num") for algo in COMPARISON_ALGORITHMS]
    dbcv_rows = [
        [(label, "name")]
        + [
            (
                _score_text(by_algo[algo].dbcv_score, by_algo[algo].dbcv_reason)
                if algo in by_algo
                else "n/a",
                "num",
            )
            for algo in COMPARISON_ALGORITHMS
        ]
        for label, by_algo in by_corpus
    ]
    dbcv_table = _table(dbcv_header, dbcv_rows)
    dbcv_caption = (
        "<div class='lead'>DBCV — espaço reduzido ~10-dim, viés de densidade; "
        "leitura assimétrica</div>"
    )

    struct_header = [
        ("corpus", ""),
        ("algoritmo", ""),
        ("grupos", "num"),
        ("outliers", "num"),
        ("cobertura", "num"),
    ]
    struct_rows = []
    for label, by_algo in by_corpus:
        for algo in COMPARISON_ALGORITHMS:
            if algo not in by_algo:
                continue
            a = by_algo[algo]
            struct_rows.append(
                [
                    (label, "name"),
                    (algo, ""),
                    (str(a.n_groups), "num"),
                    (str(a.n_outliers), "num"),
                    (_coverage(a.n_files_scored, a.n_total), "num"),
                ]
            )
    struct_table = _table(struct_header, struct_rows)

    # Leitura transversal — prosa autoral do usuário (pacto linha-dura; ver a
    # memória writing-coach-methodology). Mantida nas palavras dele.
    reading = (
        "<p class='prose'>As duas lentes discordam sobre qual algoritmo fica à "
        "frente, e cada ordenação se mostrou consistente nos três corpus: a "
        "silhueta coloca o aglomerativo à frente; o DBCV, o HDBSCAN. Era esperado "
        "o HDBSCAN liderar no DBCV, pois essa métrica mede a densidade e ainda "
        "mede no espaço reduzido, onde ocorreu o agrupamento — dupla vantagem "
        "desse algoritmo. Esse número específico não constitui evidência a favor "
        "do HDBSCAN.</p>"
        "<p class='prose'>A própria ordem na silhueta reflete estrutura, não "
        "qualidade. Prova disso: o k-means, com o viés convexo a favor, fica em "
        "último — não porque os grupos são ruins, mas porque a estrutura forçou "
        "apenas 3 grandes grupos, o que diminui a compacidade e puxa a nota para "
        "baixo.</p>"
        "<p class='prose'>Estes números caracterizam a coerência da proposta de "
        "organização; não elegem um vencedor, pois isso seria material para outro "
        "estudo, deliberadamente fora do escopo.</p>"
    )

    body = (
        "<h3>Silhueta</h3>" + sil_caption + sil_table
        + "<h3>DBCV</h3>" + dbcv_caption + dbcv_table
        + "<h3>Estrutural</h3>" + struct_table
        + reading
    )
    return _section(
        "Comparação entre os corpus",
        "os três corpus, lado a lado — sem eleger um vencedor",
        body,
    )


def _section_how_to_read() -> str:
    """Explicação metodológica das matrizes + do redutor, emitida uma única vez.

    A prosa é a mesma do relatório de corpus único (constantes em `comparison_report`),
    nas palavras do autor — aqui apenas hoistada para fora do laço por corpus.
    """
    return _section(
        "Como ler as matrizes",
        "vale para os três corpus",
        MATRICES_PROSE + REDUCER_PROSE,
    )


def _section_limitations_multi() -> str:
    # Prosa autoral do usuário (limitações — pacto linha-dura). Nas palavras dele.
    body = (
        "<p class='prose'>Esse estudo assume dois limites, declarados abertamente. "
        "O primeiro é o número de corpus: apenas três — pequeno o bastante para "
        "ilustrar, não para generalizar. O segundo: os três corpus são reais, "
        "diferentes em sua forma e conteúdo, o que não configura um experimento "
        "controlado.</p>"
        "<p class='prose'>Assumimos intencionalmente esses limites: a pergunta "
        "desta pesquisa é sobre como a ferramenta se comporta com pastas reais e "
        "bagunçadas, então um estudo pequeno, que reflita a realidade dos "
        "usuários, importa mais que um cenário controlado. Dentro deles, o estudo "
        "ainda estabelece quão coerente é a organização proposta e como a "
        "ferramenta se comporta em pastas diferentes.</p>"
    )
    return _section(
        "Limitações e próximos passos", "o que isto é — e o que não é", body
    )


def _section_provenance_shared(multi: MultiCorpusComparison) -> str:
    """Provenance is (almost) identical across corpora — same config, embedding
    model and reducer; only the corpus and its size differ (ADR 0045 amended:
    dedupe the identical). Show the shared config once + a per-corpus file count.
    """
    from datetime import datetime

    first = multi.items[0][1]
    base = _base_config(first)
    emb = base.get("embedding", {})
    red = base.get("reducer", {})
    model = emb.get("model_path") or "—"
    counts = " · ".join(f"{label}: {res.n_files}" for label, res in multi.items)
    badges = [
        ("corpora (arquivos)", counts),
        ("config base", first.base_config_source),
        ("embedding", str(emb.get("provider", "—"))),
        (
            "redutor",
            f"{red.get('provider', '—')} (n_components={red.get('n_components', '?')}, "
            f"n_neighbors={red.get('n_neighbors', '?')}, seed={red.get('random_state', '?')})",
        ),
        ("nomeação", "tfidf — naming-agnostic (não afeta a geometria)"),
        ("versão", first.version),
        ("gerado em", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    ]
    badge_html = "".join(
        f"<div class='badge'>{_esc(k)}: <b>{_esc(v)}</b></div>" for k, v in badges
    )
    cl_lines = "\n".join(
        f"{a.algorithm}: {a.effective_config.get('clustering', {})}" for a in first.algorithms
    )
    body = (
        f"<div class='kv'>{badge_html}</div>"
        "<h3>Configuração de agrupamento efetiva (por algoritmo, idêntica entre corpora)</h3>"
        f"<div class='mono'>{_esc(cl_lines)}</div>"
        "<h3>Modelo de embedding</h3>"
        f"<div class='mono'>{_esc(model)}</div>"
    )
    return (
        "<details class='tech card'><summary>Procedência e configuração efetiva</summary>"
        f"<div class='tech-body'>{body}</div></details>"
    )


def render_multicorpus_html(multi: MultiCorpusComparison, output_path: Path) -> None:
    """Write a self-contained multi-corpus HTML report to *output_path*.

    Order (ADR 0045, amended "médio"): brand -> multi hero -> conceptual
    sections (verbatim, once) -> aggregate section (the heart) -> ONE
    illustrative figure (Corpus 1) -> per-corpus sensitivity blocks (matrices +
    reducer, x N) -> ONE shared provenance -> multi limitations. The figure and
    provenance are deduplicated (near-identical across corpora); matrices/reducer
    stay per-corpus (genuinely different data). Per-corpus sections receive the
    already-anonymized ``ComparisonResult`` (``root`` is the "Corpus N" label),
    so they never see real paths.
    """
    illustrative = multi.items[0][1]  # Corpus 1 — the single illustrative figure
    parts = [
        _brand(),
        _multi_hero(multi),
        _section_intro(),
        _section_silhouette(),
        _section_structural(),
        _section_aggregate(multi),
        _section_figure(illustrative),
    ]
    # A explicação metodológica das matrizes e do redutor não varia entre corpora: emitida
    # UMA vez aqui, antes do primeiro corpus, em vez de repetida em cada bloco. Repetir fazia
    # o leitor reler blocos idênticos para conferir se havia algo diferente neles.
    parts.append(_section_how_to_read())
    for label, res in multi.items:
        parts.append(f"<h2 class='corpus-block-title'>{_esc(label)}</h2>")
        parts.append(_section_matrices(res, include_prose=False))
        parts.append(_section_reducer(res, include_prose=False))
    parts.append(_section_provenance_shared(multi))
    parts.append(_section_limitations_multi())

    content = "\n".join(parts)
    html = _load_template().replace(_SENTINEL, content)
    Path(output_path).write_text(html, encoding="utf-8")
