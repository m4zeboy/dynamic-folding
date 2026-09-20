"""Render a self-contained PT-BR HTML report for a clustering-algorithm
comparison (V1 Sereno design system; ADR 0032/0038).

Static server-side rendering: the report is tables + prose (no interactivity),
so the page is built here and injected into the template's ``__DF_CONTENT__``
sentinel. Self-contained and offline — inline CSS, inline SVG, system fonts, no
network references. The honest framing of ``comparison.py`` is carried through:
silhouette is shown as a per-algorithm descriptor, never a cross-algorithm
ranking; the structural descriptors do the comparing.
"""
from __future__ import annotations

from datetime import datetime
from importlib.resources import files
from pathlib import Path

from dynamic_folding.evaluation.comparison import ComparisonResult
from dynamic_folding.evaluation.projection import render_png

_SENTINEL = "__DF_CONTENT__"

# Brand mark — the same inline glyph the proposal report uses (offline-safe).
_MARK = (
    '<svg width="18" height="18" viewBox="0 0 100 100" fill="none">'
    '<path d="M20 20H60V40H80V80H40V60H20V20Z" fill="#3B82F6" fill-opacity=".12"/>'
    '<path d="M20 20L40 40V60H20V20Z" fill="#3B82F6" fill-opacity=".8"/>'
    '<path d="M40 40H60V60H40V40Z" fill="#3B82F6" fill-opacity=".6"/>'
    '<path d="M60 40H80V80H60V40Z" fill="#3B82F6"/>'
    '<path d="M40 60H60V80H40V60Z" fill="#3B82F6" fill-opacity=".4"/></svg>'
)


def _esc(s: object) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _load_template() -> str:
    return (
        files("dynamic_folding.evaluation")
        .joinpath("comparison_report_template.html")
        .read_text(encoding="utf-8")
    )


def _coverage(scored: int, total: int) -> str:
    if total <= 0:
        return "0/0"
    return f"{scored}/{total} ({round(100 * scored / total)}%)"


def _score_text(score: float | None, reason: str | None) -> str:
    if score is None:
        return f"n/a ({reason or 'indefinida'})"
    return f"{score:+.3f}"


def _knob_label(parameter: str) -> str:
    """Reader-facing label for a swept knob. The k-means K is stored under the config key
    ``top_k`` (a two-level-proposer inheritance), but the literature and the reader expect
    ``k`` — relabel for display only; the config key is unchanged (see BACKLOG: renaming the
    key itself is a separate, behaviour-adjacent task). Provenance still shows the real key."""
    return "k" if parameter == "top_k" else parameter


# --- small HTML builders ---------------------------------------------------

def _th(text: str, cls: str = "") -> str:
    c = f" class='{cls}'" if cls else ""
    return f"<th{c}>{_esc(text)}</th>"


def _td(text: str, cls: str = "") -> str:
    c = f" class='{cls}'" if cls else ""
    return f"<td{c}>{_esc(text)}</td>"


def _table(header: list[tuple[str, str]], rows: list[list[tuple[str, str]]]) -> str:
    head = "".join(_th(t, c) for t, c in header)
    body = "".join(
        "<tr>" + "".join(_td(t, c) for t, c in row) + "</tr>" for row in rows
    )
    return (
        f"<table class='tbl'><thead><tr>{head}</tr></thead>"
        f"<tbody>{body}</tbody></table>"
    )


def _section(title: str, lead: str | None, body_html: str) -> str:
    lead_html = f"<div class='lead'>{_esc(lead)}</div>" if lead else ""
    return (
        f"<section class='section card'><h2>{_esc(title)}</h2>"
        f"{lead_html}{body_html}</section>"
    )


def _base_config(res: ComparisonResult) -> dict:
    """The shared (non-clustering) effective config, from the first run that has it."""
    for a in res.algorithms:
        if a.effective_config:
            return a.effective_config
    return {}


# --- sections --------------------------------------------------------------

def _brand() -> str:
    return f"<div class='brand'>{_MARK}<span class='lockup'><b>dynamic</b>folding</span></div>"


def _hero(res: ComparisonResult) -> str:
    import os

    name = os.path.basename(res.root.rstrip("\\/")) or res.root
    tags = [
        "1ª passada · exploratória",
        "2 lentes (silhueta + DBCV)",
        "sem veredito",
        "n=1 (corpus congelado)",
        "determinístico · offline",
    ]
    tag_html = "".join(f"<span class='tag'>{_esc(t)}</span>" for t in tags)
    return (
        "<section class='hero'>"
        "<div class='hero-title'>Comparação de algoritmos de agrupamento</div>"
        f"<div class='hero-sum'>Corpus: {_esc(name)} · {res.n_files} arquivos</div>"
        f"<div class='hero-tags'>{tag_html}</div></section>"
    )


def _section_intro() -> str:
    # Texto autoral do usuário (piloto da metodologia de escrita — ver memória
    # writing-coach-methodology). Mantido nas palavras dele.
    p = (
        "<p class='prose'>A ferramenta propõe uma estrutura de organização de arquivos e "
        "pastas olhando para a <b>semântica</b> dos arquivos analisados. Esse relatório "
        "mostra como a ferramenta se comporta de forma <b>exploratória</b>, sem a pretensão "
        "de concluir qual é a melhor combinação de algoritmos e hiperparâmetros.</p>"
    )
    return _section("O que é este relatório", None, p)


def _section_silhouette() -> str:
    # Conceito da silhueta — texto autoral do usuário (ver writing-coach-methodology).
    p1 = (
        "<p class='prose'>A silhueta define um grupo como “bom” através de duas medidas, "
        "<i>Compacidade</i> e <i>Separação</i>. A Compacidade mede a distância entre dois "
        "pontos dentro do grupo, quanto mais próximos melhor. E a Separação mede a distância "
        "entre dois pontos de grupos diferentes. Quanto mais separados melhor.</p>"
    )
    p2 = (
        "<p class='prose'>Entretanto, ela possui uma limitação, para ela o conceito de “bons "
        "grupos” é uma esfera, com um centro onde os dados orbitam, essa caracterização é uma "
        "idealização impraticável com dados reais. Esse viés esférico é importante pois "
        "subestima algoritmos que produzem grupos com formas irregulares e favorece os que "
        "criam grupos esféricos, por isso esse relatório não tem a pretensão de concluir qual "
        "é o “melhor” algoritmo com base na pontuação dessa métrica.</p>"
    )
    # DBCV — ponto 1 (viés oposto): texto autoral do usuário (linha-dura; ver writing-coach-methodology).
    dbcv_p1 = (
        "<p class='prose'>Ao contrário da silhueta, o DBCV não penaliza algoritmos que "
        "produzem grupos com formas irregulares, pois julga por densidade, não por forma. "
        "Os pontos são julgados como uma cadeia, a distância ajustada é o elo entre os pontos, "
        "por causa dela é possível ter informação de quão densa é a região dos pontos. Por "
        "isso é a lente de viés oposto.</p>"
    )
    # DBCV — ponto 2 (espaço reduzido / lente independente): texto autoral do usuário (linha-dura).
    dbcv_p2 = (
        "<p class='prose'>A silhueta é calculada no espaço original de 384 dimensões; o DBCV "
        "no espaço reduzido de 10 dimensões, devido a uma condição do agrupamento por "
        "densidade segundo a qual o número de pontos deve ser muito maior do que o número de "
        "dimensões para que seja possível discriminar as distâncias entre os pontos de forma "
        "confortável. O número de pontos, na casa das dezenas, é muito menor que as 384 "
        "dimensões do espaço original, mas ainda maior que as 10 do reduzido. Não é o ideal, mas é "
        "o mínimo para operar. Logo, por estarem em espaços diferentes e com vieses opostos, "
        "as métricas são independentes intencionalmente, o que não caracteriza uma comparação "
        "controlada, pois não é possível compará-las lado a lado.</p>"
    )
    # DBCV — ponto 3 (leitura assimétrica): texto autoral do usuário (linha-dura).
    dbcv_p3 = (
        "<p class='prose'>O DBCV é onde habitam algoritmos como o HDBSCAN, pois mede a "
        "densidade no espaço reduzido com a vizinhança preservada pelo UMAP. Os demais "
        "algoritmos não são otimizados para essa métrica, logo nota baixa do "
        "k-means/aglomerativo não conta contra eles. O HDBSCAN pontuando alto nessa métrica "
        "não diz nada, pois é o esperado; por outro lado, ele ir mal aqui é um grande achado.</p>"
    )
    return _section("As duas lentes", "silhueta (convexa) e DBCV (densidade)", p1 + p2 + dbcv_p1 + dbcv_p2 + dbcv_p3)


def _section_structural() -> str:
    # Texto autoral do usuário (ver writing-coach-methodology). Os números por configuração
    # migraram para as matrizes por algoritmo; aqui fica o contraste que INDEPENDE da execução.
    prose = (
        "<p class='prose'>A comparação acontece na estrutura resultante dos agrupamentos, "
        "quantos grupos foram gerados, caracterização de ruído e a cobertura da medição. O "
        "k-means não mapeia ruído, logo 100% de cobertura (todos os arquivos são agrupados e "
        "medidos). O HDBSCAN caracteriza ruído e os move para a pasta Outros, estes não são "
        "cobertos pela medição, logo o HDBSCAN tem uma cobertura menor. O k-means precisa de "
        "um número fixo enquanto o HDBSCAN/Aglomerativo infere automaticamente esse número a "
        "partir dos dados.</p>"
    )
    return _section("Comparação estrutural", "o contraste que independe da execução", prose)


def _section_figure(res: ComparisonResult) -> str:
    """Illustrative PCA-2D figure: the data before / after grouping (default run).

    Honest by construction — the projection (data) is always computed; only the
    drawing needs matplotlib. When matplotlib is absent we say so *visibly* (loud, not
    silent), so a figureless report is never mistaken for a complete one.
    """
    proj = res.projection
    lead = "projeção PCA-2D ilustrativa do espaço original — antes e depois do agrupamento"

    # Caption: the user's authored interpretive prose (linha-dura — his words, my typing).
    caption = (
        "<p class='prose'>A figura mostra em dois painéis a distribuição dos pontos no "
        "espaço e os grupos formados. Para produzir a ilustração foi aplicado o PCA-2D "
        "devido à propriedade determinística. Cabe ressalvar que essa estratégia difere "
        "do padrão utilizado pela ferramenta, o UMAP-10D. Os eixos PC1+PC2 capturam "
        "24,5% de variância, logo 3/4 da variação não aparecem na figura, resultando em "
        "pontos sobrepostos. O PCA mostra o espaço original, enquanto os grupos foram "
        "encontrados no espaço reduzido de UMAP-10D. A olho nu não se avalia agrupamento "
        "em alta dimensão, o que motiva a análise por meio das métricas silhueta e DBCV.</p>"
    )

    if proj is None or not proj.coords:
        reason = (proj.reason if proj else None) or "projeção indisponível"
        body = f"<div class='callout'>Figura indisponível: {_esc(reason)}.</div>"
        return _section("Figura ilustrativa", lead, body + caption)

    png = render_png(proj)
    if png is None:
        body = (
            "<div class='callout'>Figura não gerada: o desenho requer "
            "<code>matplotlib</code> (dependência opcional). Instale com "
            "<code>uv pip install -e .[viz]</code> e regenere — a projeção já foi "
            "calculada, só o desenho ficou pendente.</div>"
        )
        return _section("Figura ilustrativa", lead, body + caption)

    img = (
        "<img alt='Projeção PCA-2D: dados antes e depois do agrupamento' "
        "style='max-width:100%;height:auto;display:block;margin:0 auto;border-radius:8px' "
        f"src='data:image/png;base64,{png}'>"
    )
    return _section("Figura ilustrativa", lead, img + caption)


def _matrix_for(study, algo_result) -> str:
    """One per-algorithm matrix: the knob sweep x all metrics, default row marked.

    The default execution is the AlgorithmResult (run at config defaults); we mark the
    sweep row that reproduces its structural signature, so we don't depend on knowing the
    default knob value. DBCV is shown (comparable down the column — fixed 10-dim space).
    """
    knob = study.parameter
    label = _knob_label(knob)
    default_sig = None
    if algo_result is not None:
        default_sig = (algo_result.n_groups, algo_result.n_outliers, algo_result.n_files_scored)
    header = [
        (label, ""),
        ("grupos", "num"),
        ("outliers", "num"),
        ("cobertura", "num"),
        ("silhueta", "num"),
        ("DBCV", "num"),
    ]
    rows = []
    default_value = None
    for r in study.rows:
        sig = (r.n_groups, r.n_outliers, r.n_files_scored)
        is_default = default_value is None and default_sig is not None and sig == default_sig
        if is_default:
            default_value = r.value
        rows.append([
            (f"{r.value} (padrão)" if is_default else str(r.value), "name" if is_default else ""),
            (str(r.n_groups), "num"),
            (str(r.n_outliers), "num"),
            (_coverage(r.n_files_scored, r.n_total), "num"),
            (_score_text(r.score, r.reason), "num" if r.score is not None else "na"),
            (_score_text(r.dbcv_score, r.dbcv_reason), "num" if r.dbcv_score is not None else "na"),
        ])
    piso = ""
    if algo_result is not None and algo_result.baseline_mean is not None:
        anchor = f" ({label}={default_value})" if default_value is not None else ""
        piso = (
            f"<div class='lead'>Piso aleatório da silhueta na linha padrão{anchor}: "
            f"{algo_result.baseline_mean:+.3f} ± {algo_result.baseline_std:.3f} "
            f"(acima do acaso {algo_result.gap:+.3f}).</div>"
        )
    return f"<h3>{_esc(study.algorithm)} · {_esc(label)}</h3>" + _table(header, rows) + piso


# Texto autoral do usuário (fase de escrita coachada — ver writing-coach-methodology /
# dbcv-state). Prosa relocada das seções dissolvidas na reestruturação (ADR 0041) mais
# os pontos novos das matrizes (hdbscan×aglomerativo, varredura 1D), todos nas palavras
# dele; ordenada macro→micro (a matriz → entre tabelas → dentro de uma tabela).
#
# Constante de módulo (não inline) porque o relatório multi-corpus emite esta prosa UMA vez,
# antes do primeiro corpus, em vez de repeti-la por corpus — a explicação é metodológica e
# não varia entre corpora. Ver `_section_matrices(include_prose=...)`.
MATRICES_PROSE = (
    "<p class='prose'>Cada matriz descreve como o algoritmo reage à variação de um único "
        "hiperparâmetro particular a ele. O k-means varia o <code>k</code> (o número de "
        "grupos), enquanto o HDBSCAN e o aglomerativo variam o <code>min_cluster_size</code>.</p>"
        "<div class='callout'>Esses números não são comparáveis entre os algoritmos pois cada "
        "um representa uma cobertura diferente dos arquivos analisados, logo devem ser tratados "
        "como uma descrição e não como um ranking.</div>"
        "<p class='prose'>O leitor não deve comparar as linhas entre as tabelas principalmente "
        "do HDBSCAN e Aglomerativo, pois mesmo que tenham o mesmo nome, os parâmetros mandam os "
        "algoritmos fazerem coisas diferentes.</p>"
        "<div class='callout'>O leitor deve ler todas as colunas em conjunto, não apenas a "
        "silhueta de forma cega.</div>"
        "<p class='prose'>A silhueta reagir à variação, no caso do HDBSCAN, mostra que o "
        "algoritmo está mais exigente para caracterizar um grupo, em outras palavras, mais "
        "pontos densos são necessários, o que naturalmente reduz o número de grupos produzidos "
        "e aumenta a quantidade de pontos mal encaixados marcados como ruído. Esses que "
        "puxariam a métrica para baixo ficam de fora da avaliação, como a silhueta só pontua "
        "sobre os pontos que não são ruídos, logo o resultado aumenta.</p>"
        "<p class='prose'>O leitor não deve concluir com base na leitura que foi encontrada a "
        "combinação ótima para a operação da ferramenta, pois a variação ocorreu em uma parcela "
        "ínfima de um vasto espaço de combinações de hiperparâmetros.</p>"
        "<p class='prose'>O piso tem característica pseudoaleatória com semente determinística. "
        "Obtém o resultado de um agrupamento real (seus grupos e tamanhos), embaralha os "
        "arquivos nesses mesmos grupos ao acaso, e mede a silhueta; repete-se mil vezes e por "
        "fim obtém-se a média. Ficar acima do piso significa que o algoritmo supera um "
    "agrupamento feito ao acaso, no entanto não significa que os grupos são bons ou úteis "
    "para o usuário final.</p>"
)


def _section_matrices(res: ComparisonResult, *, include_prose: bool = True) -> str:
    """Matrizes por algoritmo.

    `include_prose=False` omite a explicação metodológica (mantendo as tabelas), para o
    relatório multi-corpus, que a emite uma única vez antes do primeiro corpus.
    """
    by_algo = {a.algorithm: a for a in res.algorithms}
    clustering = [s for s in res.sensitivities if s.stage == "clustering"]
    intro = MATRICES_PROSE if include_prose else ""
    matrices = "".join(_matrix_for(s, by_algo.get(s.algorithm)) for s in clustering)
    return _section(
        "Matrizes por algoritmo",
        "as execuções, lado a lado — sem eleger uma",
        intro + matrices,
    )


# Caveat do redutor — texto autoral do usuário (linha-dura; ver writing-coach-methodology).
# Constante de módulo pelo mesmo motivo de MATRICES_PROSE.
REDUCER_PROSE = (
    "<p class='prose'>O n_components=10 foi o padrão arbitrário escolhido. Esta tabela é o "
    "teste que o põe à prova. Mas variar o n_components muda o espaço a cada linha, por "
    "isso o DBCV, que é calculado no espaço reduzido, fica de fora dessa comparação. "
    "Comparamos somente a silhueta, pois ela é calculada no espaço original de 384.</p>"
    "<p class='prose'>A tabela tem função descritiva, não tem a finalidade de provar algum "
    "valor como ótimo, somente descrever se/como a ferramenta responde à variação do "
    "hiperparâmetro.</p>"
)


def _section_reducer(res: ComparisonResult, *, include_prose: bool = True) -> str:
    """Sensibilidade do redutor.

    `include_prose=False`: ver `_section_matrices`.
    """
    studies = [s for s in res.sensitivities if s.stage == "reducer"]
    if not studies:
        return ""
    blocks = []
    for study in studies:
        # NO DBCV column here: each row uses a different reduced dimension, so DBCV would
        # compare different metric spaces — invalid to read down (ADR 0039/0040).
        header = [
            (study.parameter, ""),
            ("grupos", "num"),
            ("outliers", "num"),
            ("cobertura", "num"),
            ("silhueta", "num"),
        ]
        rows = [
            [
                (str(r.value), ""),
                (str(r.n_groups), "num"),
                (str(r.n_outliers), "num"),
                (_coverage(r.n_files_scored, r.n_total), "num"),
                (_score_text(r.score, r.reason), "num" if r.score is not None else "na"),
            ]
            for r in study.rows
        ]
        blocks.append(
            f"<h3>redutor · {_esc(study.parameter)} (clusterer: {_esc(study.algorithm)})</h3>"
            + _table(header, rows)
        )
    prose = REDUCER_PROSE if include_prose else ""
    return _section(
        "Sensibilidade do redutor (n_components)",
        "pipeline no padrão, variando só o redutor",
        prose + "".join(blocks),
    )


# As seções "Silhueta por algoritmo", "DBCV por algoritmo" e "Sensibilidade a
# hiperparâmetros" foram unificadas em _section_matrices (+ _section_reducer): cada algoritmo
# vira uma matriz (varredura do knob x todas as métricas), sem eleger uma execução. A prosa
# autoral dessas seções (callout, piso, raciocínio do knob) está preservada no histórico do
# git (HEAD pré-reestruturação) para o usuário reaproveitar ao preencher os placeholders.


def _section_limitations() -> str:
    # Texto autoral do usuário (metodologia de escrita — ver memória
    # writing-coach-methodology). Mantido nas palavras dele.
    p = (
        "<p class='prose'>Este estudo não permite dizer qual combinação performa "
        "melhor por três razões: o estudo cobre uma fração ínfima em um espaço "
        "contínuo de combinações; utiliza um único corpus pequeno como material de "
        "avaliação que não cobre todos os tipos de arquivos nem todos os casos de "
        "uso, e calcula apenas uma métrica que não é imparcial entre os algoritmos, "
        "pois a noção de bons grupos não é compartilhada. No entanto, isso não "
        "fragiliza o HDBSCAN como padrão da ferramenta, pois sua escolha não se "
        "apoia nessa comparação, mas em decisões de projeto, como o tratamento de "
        "ruído, inferência automática do número de grupos, e geração nativa de "
        "estrutura hierárquica.</p>"
    )
    items = [
        # Limitação "conjuntos diferentes" — texto autoral do usuário (ver writing-coach-methodology).
        "Não é possível comparar os números da silhueta entre os algoritmos pois ela ignora os "
        "arquivos marcados como ruído, e o k-means não marca ruído, logo cada algoritmo cobre "
        "dados diferentes.",
        # Ponte + fechamento (2ª métrica concluída) — texto autoral do usuário (ver writing-coach-methodology).
        "Comparar algoritmos de propostas diferentes não é trivial, pois não existe métrica "
        "neutra, por isso, nesta segunda passada, foi finalizado o estudo da segunda métrica "
        "de viés oposto, o DBCV.",
    ]
    lis = "".join(f"<li>{x}</li>" for x in items)
    return _section(
        "Limitações e próximos passos", "o que isto é — e o que não é", p + f"<ul class='tight'>{lis}</ul>"
    )


def _section_provenance(res: ComparisonResult) -> str:
    base = _base_config(res)
    emb = base.get("embedding", {})
    red = base.get("reducer", {})
    model = emb.get("model_path") or "—"
    badges = [
        ("corpus", res.root),
        ("arquivos", str(res.n_files)),
        ("config base", res.base_config_source),
        ("embedding", str(emb.get("provider", "—"))),
        (
            "redutor",
            f"{red.get('provider', '—')} (n_components={red.get('n_components', '?')}, "
            f"n_neighbors={red.get('n_neighbors', '?')}, seed={red.get('random_state', '?')})",
        ),
        ("nomeação", "tfidf — naming-agnostic (não afeta a geometria)"),
        ("versão", res.version),
        ("gerado em", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    ]
    badge_html = "".join(
        f"<div class='badge'>{_esc(k)}: <b>{_esc(v)}</b></div>" for k, v in badges
    )
    cl_lines = "\n".join(
        f"{a.algorithm}: {a.effective_config.get('clustering', {})}" for a in res.algorithms
    )
    body = (
        f"<div class='kv'>{badge_html}</div>"
        "<h3>Configuração de agrupamento efetiva (por algoritmo)</h3>"
        f"<div class='mono'>{_esc(cl_lines)}</div>"
        "<h3>Modelo de embedding</h3>"
        f"<div class='mono'>{_esc(model)}</div>"
    )
    return (
        "<details class='tech card'><summary>Procedência e configuração efetiva</summary>"
        f"<div class='tech-body'>{body}</div></details>"
    )


def render_comparison_html(res: ComparisonResult, output_path: Path) -> None:
    """Write a self-contained HTML comparison report to *output_path*."""
    content = "\n".join(
        [
            _brand(),
            _hero(res),
            _section_intro(),
            _section_silhouette(),
            _section_structural(),
            _section_figure(res),
            _section_matrices(res),
            _section_reducer(res),
            _section_limitations(),
            _section_provenance(res),
        ]
    )
    html = _load_template().replace(_SENTINEL, content)
    Path(output_path).write_text(html, encoding="utf-8")
