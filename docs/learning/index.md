# Learning notes — index

Content-oriented catalog of the `docs/learning/` wiki. Each note is one
fully-understood concept, written to be **re-read** and to make each choice
**defensible** (the "defend-it-after" bar — same as the banca).

These notes are an **LLM-wiki** in the Karpathy sense (a compounding, maintained
knowledge base), with one deliberate local rule: a note is a *graduated draft*,
not a raw source. The graduation ritual is a skill — see
[`.claude/skills/nota-learning/SKILL.md`](../../.claude/skills/nota-learning/SKILL.md).

**Language convention** (per project rule: thesis → PT-BR, internal → English):
thesis-concept notes that carry a "trecho pronto para a tese" are in **PT-BR**;
process/engineering notes are in **English**. Don't retranslate existing notes.

**How to add a note:** invoke the `nota-learning` skill. In short — master the
concept cold first, draft the note into the `NN-slug.md` mold, add a row here,
log it in `DONE.md` with the date.

---

## Métricas de avaliação (conceito)

Como cada lente interna mede a qualidade dos grupos — e em qual espaço, com qual
viés declarado.

- **[01 — Stability metric `1 − 4·p·(1−p)`](01-stability-metric.md)** *(EN)* —
  por que estabilidade é *consistência* (sempre-junto OU sempre-separado), não
  taxa de co-ocorrência; a forma de parábola invertida e o porquê da troca de
  fórmula no SPEC.
- **[05 — Métrica Silhueta](05-silhouette-metric.md)** *(PT-BR)* — 1ª lente (viés
  convexo); calculada nos embeddings **brutos de 384-dim** (espaço de
  significado), não no reduzido; linha de base aleatória; leitura conservadora de
  `0.110`. Liga-se a [02](02-experimental-scope.md) e [06](06-dbcv-metric.md).
- **[06 — Métrica DBCV](06-dbcv-metric.md)** *(PT-BR)* — 2ª lente (viés de
  densidade); calculada no espaço **reduzido de 10-dim** (n≪d degenera em 384);
  modelo mental da cadeia/MST; **leitura assimétrica** (casa do HDBSCAN).
  Contraparte de [05](05-silhouette-metric.md).

## Escopo & metodologia do capítulo empírico

- **[02 — Escopo do capítulo empírico](02-experimental-scope.md)** *(PT-BR)* — o
  roteiro: caracterização + justificativa limitada (não validação, não
  otimização); os 4 princípios inegociáveis (independência do resultado,
  procedência, múltiplas lentes com viés declarado, nunca coroar um vencedor).
  Emenda o ADR 0018. Fixa o escopo que [05](05-silhouette-metric.md)/[06](06-dbcv-metric.md) obedecem.

## Engenharia & processo

- **[03 — `setup-sbert` command](03-sbert-setup.md)** *(EN)* — separar
  *offline em runtime* (a regra dura, mantida) de *offline no setup* (o atrito
  real); a ordem de resolução do model path em 4 camadas.
- **[04 — Bisectable changes and visible failures](04-bisectable-changes-and-visible-failures.md)**
  *(EN)* — um-commit-uma-preocupação; fallbacks silenciosos são veneno de debug;
  paridade de config entre entry points; reconciliação de branches como plano
  faseado. Cita [03](03-sbert-setup.md).
