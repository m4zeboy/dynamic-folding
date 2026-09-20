from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer

from dynamic_folding.core.windows import sanitize_windows_folder_name


# Tokens emitted by the preprocess template (see
# `config/default.toml::preprocess.template`). These tokens appear in every
# document and dominate TF-IDF rankings unless filtered, polluting the anchor
# terms list. See ADR 0024 (Phase D + Phase E) for the empirical evidence
# under the legacy English markers, and ADR 0025 for the dual-source
# template that introduced the Portuguese markers `[NOME]`, `[TÍTULO]`,
# `[EXT]`, `[CONTEÚDO]`.
#
# The set blocks the literal template markers from both the current and
# legacy templates, plus common file extensions emitted via the {ext}
# placeholder. Diacritic-stripped variants are included as safety.
_TEMPLATE_STOPWORDS: frozenset[str] = frozenset({
    # Current default template markers (ADR 0025).
    "nome",
    "título",
    "titulo",
    "conteúdo",
    "conteudo",
    # Legacy markers — kept so a user-supplied config hardcoding the older
    # template still yields clean anchors.
    "file",
    "ext",
    "content",
    # File extension values commonly emitted by {ext}.
    "pdf",
    "doc",
    "docx",
    "ppt",
    "pptx",
    "xls",
    "xlsx",
    "txt",
    "csv",
    "json",
    "xml",
    "html",
    "htm",
    "md",
    "jpg",
    "jpeg",
    "png",
    "gif",
    "bmp",
    "zip",
    "rar",
    "tar",
    "gz",
    # Bottom-up aggregation framing words (ADR 0037). These label "subpastas"
    # vs "arquivos soltos" inside the Ollama prompt only and are never fed to
    # TF-IDF in the current design — kept here as defensive insurance so they
    # can never surface as anchor terms.
    "subpasta",
    "subpastas",
    "arquivo",
    "arquivos",
})


def extract_anchor_terms(texts: list[str], *, top_n: int) -> list[str]:
    """Extract top-N terms ranked by mean TF-IDF score across `texts`.

    Returns an empty list when:
    - `texts` is empty or contains only whitespace; or
    - the corpus produces no usable tokens (TfidfVectorizer raises).

    Tokens listed in `_TEMPLATE_STOPWORDS` (preprocess-template markers
    and common file extensions) are filtered before TF-IDF ranking so
    they cannot dominate the output. See ADR 0024 (Phase E).

    Used by both the TF-IDF naming fallback and the grounded-prompt
    variant of the Ollama namer (which injects these terms into the
    prompt to anchor lexical generation).
    """
    if not texts or not any(t.strip() for t in texts):
        return []

    try:
        vec = TfidfVectorizer(
            lowercase=True,
            token_pattern=r"(?u)\b\w+\b",
            stop_words=list(_TEMPLATE_STOPWORDS),
        )
        X = vec.fit_transform(texts)
    except ValueError:
        return []

    scores = X.mean(axis=0).A1
    vocab = vec.get_feature_names_out()
    idx = scores.argsort()[::-1]

    terms: list[str] = []
    for i in idx:
        t = str(vocab[i])
        if not t:
            continue
        terms.append(t)
        if len(terms) >= max(1, top_n):
            break
    return terms


def name_cluster(texts: list[str], *, top_terms: int) -> str:
    if not texts or not any(t.strip() for t in texts):
        return "Group"

    terms = extract_anchor_terms(texts, top_n=top_terms)
    if not terms:
        return "unnamed_group"

    return sanitize_windows_folder_name("_".join(terms))


def aggregate_name(child_names: list[str], loose_texts: list[str], *, top_terms: int) -> str:
    """Deterministically name a parent folder from its children + loose files.

    Bottom-up parent namer (ADR 0037): combine the children's already-curated
    names with anchor terms mined from the parent's loose files, then reuse the
    standard TF-IDF naming over that small corpus. Used directly by the `tfidf`
    namer in aggregate mode, and as the deterministic fallback for the Ollama
    aggregator. Deterministic: same inputs → same name.
    """
    clean_children = [c for c in child_names if c and c.strip()]
    loose_terms = (
        extract_anchor_terms([t for t in loose_texts if t and t.strip()], top_n=top_terms)
        if loose_texts
        else []
    )
    corpus = clean_children + loose_terms
    if not corpus:
        return "unnamed_group"
    return name_cluster(corpus, top_terms=top_terms)
