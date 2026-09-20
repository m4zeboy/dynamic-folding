# 02 — O escopo do capítulo empírico (roteiro)

**Contexto.** O Capítulo 4 (a caracterização empírica do TCC) foi recomeçado do
zero, adicionando **uma métrica de cada vez, totalmente compreendida**, cada uma
medindo *aquilo que a ferramenta realmente entrega* — as pastas da proposta real e
os embeddings brutos de 384 dimensões, sem reagrupar. A primeira métrica, a
**silhueta** (com linha de base aleatória e versão por-grupo), já está pronta e
documentada na nota [`05-silhouette-metric.md`](05-silhouette-metric.md).

Esta nota não descreve um experimento; ela **fixa o escopo** do capítulo *antes* de
qualquer comparação, para que o trabalho que vier não contradiga o que está escrito.
Ela substitui uma versão anterior, que pertencia a uma abordagem hoje abandonada
(a antiga pilha `characterize`/`analyze`, com múltiplos corpora e uma "spine
experiment").

**A mudança de escopo.** A versão anterior prometia um capítulo *descritivo, não
comparativo*: uma configuração fixa, sem comparar algoritmos nem varrer
hiperparâmetros. Isso muda — de forma **limitada e deliberada**. O capítulo passa a
também **justificar empiricamente as escolhas estratégicas do padrão que até
então repousavam em intuição: o algoritmo de agrupamento e os seus
hiperparâmetros** (o HDBSCAN foi adotado sem nunca ter sido confrontado com kmeans
ou agglomerative, e os seus hiperparâmetros nunca foram variados). O resto da
configuração — em especial o redutor — permanece como pano de fundo descritivo.

**Uma ressalva sobre o formato.** O capítulo ainda *não* está sendo escrito — não há
formato fechado, e a estrutura vai surgir do material à medida que ele aparece. O
princípio de trabalho é **o mínimo possível agora** (um corpus, uma métrica que já
existe, comparar o que está ao alcance) e **expandir conforme os dados pedirem e o
entendimento permitir**. Por isso esta nota descreve uma *direção e princípios*, não
um programa rígido com resultados pré-comprometidos.

---

## 1. Três capítulos que se parecem de longe

Quando alguém diz "evidência empírica numa tese", três coisas bem diferentes cabem
na frase. Elas têm escopos muito distintos, e nomear o nosso evita confusão na
defesa.

**Validação.** *"Eu provo que a ferramenta produz a saída correta."* Exige um
*ground truth* — um gabarito. **Rejeitada** para este TCC pelo
[ADR 0018](../ADR/0018-empirical-characterization-no-ground-truth.md): o
agrupamento de arquivos pessoais não tem gabarito objetivo, e qualquer conjunto
rotulado por nós embutiria a opinião de um único humano. Métricas externas (ARI,
NMI) contra esse gabarito vestiriam um juízo subjetivo com números de aparência
objetiva.

**Otimização.** *"Eu varro o espaço de configurações e recomendo os melhores
hiperparâmetros."* Exige busca em grade sobre embedders, clusterizadores,
redutores, métricas de distância — um projeto de meses que alegaria um **ótimo
global**. **Fora do escopo.**

**Caracterização (+ justificativa limitada).** *"Eu descrevo como uma ferramenta
fixa se comporta numa entrada real — e dou procedência às suas escolhas
estratégicas centrais."* É isto que o capítulo é. A parte descritiva é a da nota 05. A parte nova
**não** vira otimização: não buscamos um "melhor" global no espaço de
configurações; pegamos as decisões que eram pura intuição (o **algoritmo** e os seus
**hiperparâmetros**), lançamos sobre as alternativas **algumas lentes honestas**, e
ou confirmamos que a razão de projeto se sustenta, ou expomos os trade-offs.
Procedência de uma decisão **não é** prova de otimalidade.

Sobre os hiperparâmetros, a distinção fina importa: variar um hiperparâmetro e
observar o efeito é **análise de sensibilidade**, não otimização — é, aliás, a
**propriedade #3 do próprio ADR 0018** (*"o comportamento muda com a configuração de
modo teoricamente coerente?"*). Perguntamos se a saída **responde** ao knob na
direção esperada, não qual valor seria "ótimo".

A fronteira entre os três não é "rodar a ferramenta e anotar números" — os três
fazem isso. A fronteira é **que pergunta se responde**: *está correto?* (validação),
*qual é o melhor?* (otimização), *como se comporta, e de onde veio esta escolha?*
(o nosso).

## 2. A configuração padrão caracterizada

O capítulo caracteriza a pilha padrão de fato instalável e executável pelo usuário
([`config/default.toml`](../../config/default.toml)):

- **Embedding:** `sbert` com um modelo *sentence-transformers* local (384 dim).
- **Redutor:** `umap` (comprime para 10 dim — apenas espaço de trabalho interno).
- **Agrupamento:** `hdbscan`.
- **Nomeação:** `ollama` com `llama3.1` em loopback (com *fallback* `tfidf`).
- **Proposta:** dois níveis.

Caracterizar o *fallback* de zero-dependências (embedder falso + nomeação `tfidf`)
não diria nada sobre a ferramenta que a tese propõe — descreveria um arnês de teste.

## 3. Princípios da comparação (a parte inegociável)

Estes princípios valem para qualquer comparação que o capítulo venha a conter. São
o que torna a expansão de escopo **defensável**, e não uma reabertura disfarçada da
"otimização" que rejeitamos.

**(a) Independência do resultado.** A contribuição é a **metodologia e a discussão
honesta dos trade-offs**, *qualquer que seja* o algoritmo que pontue mais alto em
qualquer lente. Teste ácido, a ser aplicado a cada frase escrita: *se os dados
voltarem com o kmeans à frente em todas as lentes, ainda consigo reportar isso como
um achado limpo e honesto?* Se a resposta for "não", a frase pré-compromete um
resultado e precisa ser reescrita.

**(b) A justificativa primária do padrão é por adequação de projeto, não por
pontuação.** O HDBSCAN é o padrão por razões de *design* independentes de qualquer
métrica: ele **modela o ruído** (arquivos que não pertencem a nenhum grupo viram o
balde `Outros` — o kmeans, por construção, *não* produz esse balde); aceita grupos
de **formas arbitrárias**; **não exige um K** pré-definido; e isso casa com a
entrada bagunçada do mundo real para a qual a ferramenta foi feita. A parte empírica
**ilustra trade-offs** ao redor dessa decisão — ela não *decide* o padrão.

**(c) Várias lentes, com o viés de cada uma declarado.** Nenhuma métrica interna é
universalmente correta — cada uma define "bom grupo" à sua maneira (ver nota 05,
§3):

- A **silhueta** premia grupos compactos/convexos → é **enviesada contra** métodos
  de densidade como o HDBSCAN (tende a favorecer o kmeans).
- O **DBCV** premia grupos densos e conectados → é enviesado **no sentido oposto**.

Por isso uma comparação só vale acompanhada da **discussão de qual viés está em jogo
em cada número**.

**(d) Nunca um número único coroando um vencedor.** O honesto é a procedência + a
discussão dos vieses, não um ranking. Um veredito só pode aparecer — se aparecer —
depois de mais de uma lente, e mesmo assim como leitura cuidadosa, não como troféu.

## 4. O programa — incremental e guiado pelos dados

O mínimo agora: **um corpus** (Downloads), **uma métrica que já existe**
(silhueta), comparar o que está ao alcance. Os incrementos abaixo entram **conforme
a necessidade aparecer nos dados** e o entendimento estiver confortável — não numa
ordem rígida pré-fixada.

**A primeira passada (exploratória, sem veredito).** Com a única lente que já existe
— a **silhueta** — e sobre o único corpus, a primeira passada cobre duas frentes,
ambas lidas *através do viés da silhueta* (favorável a formas convexas):

1. **Comparação de algoritmos** — rodar hdbscan × kmeans × agglomerative e ler a
   silhueta de cada um. A leitura é independente do resultado e já informa nos dois
   sentidos:
   - Se o HDBSCAN for **bem** numa lente que o **desfavorece**, é sinal forte
     *apesar* do viés.
   - Se for **mal**, é o viés esperado da silhueta — não uma derrota, e sim a
     **motivação** para a próxima lente.
2. **Primeiro corte de sensibilidade dos hiperparâmetros do agrupamento** — variar
   1–2 chaves do clusterizador (ex.: `min_cluster_size`), uma de cada vez, e observar
   como a silhueta responde.

Em nenhum dos casos a passada coroa um vencedor; ela diz se há diferença que mereça
investigação e prepara a próxima lente.

**Hiperparâmetros são um pilar, não um extra.** Variar os hiperparâmetros — em
especial os do agrupamento — é parte **comprometida** do capítulo, não um "se sobrar
tempo". Mas o enquadramento é **sensibilidade + procedência**, nunca otimização (ver
§1): perguntamos se a saída **responde** ao knob de modo teoricamente coerente (a
propriedade #3 do ADR 0018) e de onde veio cada valor padrão — não qual valor é
"ótimo". A ressalva do regime de poucos arquivos vale para todos eles. Continua
**uma chave de cada vez, "reportar e discutir"** — não uma varredura.

**Cuidado honesto: sensibilidade com uma só lente.** Se a silhueta sobe quando um
knob muda, isso mostra **responsividade** (a propriedade 3), não que o ajuste de
maior silhueta seja "melhor": a silhueta carrega o mesmo viés convexo aqui também
(subir `min_cluster_size`, por exemplo, tende a gerar grupos maiores e mais
redondos, que ela premia pela *forma*). Por isso, enquanto houver só uma lente, os
**descritores estruturais** abaixo pesam mais na leitura.

**Próxima lente, antes de qualquer conclusão: DBCV.** Concluir a partir de uma só
lente enviesada é o "número único" disfarçado. O contraponto real é o **DBCV**
(sensível a densidade). *Davies-Bouldin e Calinski-Harabasz não servem* aqui — têm o
mesmo viés convexo da silhueta, não são uma segunda opinião de verdade. O veredito,
se houver, fica **suspenso até existirem ≥ 2 lentes**.

> **Status (ADR 0039) — DBCV implementado.** Decisões: calculado no **espaço reduzido**
> (em 384-dim a densidade degenera, n≪d); lente **independente** da silhueta (espaço +
> viés diferentes, não comparação controlada); **leitura assimétrica** (é a casa do
> HDBSCAN — só HDBSCAN indo *mal* é sinal forte). O conceito da métrica vai na nota 06
> (a escrever).

**Robustez barata: descritores estruturais.** Além das métricas, reportar nº de
grupos, **nº de outliers** e distribuição de tamanhos. Esses números carregam a
história de adequação de projeto mesmo que o HDBSCAN perca na silhueta — e lembram
que o kmeans sequer produz um `Outros`. Com uma só lente métrica, eles são o
principal sinal *não-silhueta*.

**Fora do escopo: o redutor.** O UMAP e seus parâmetros não entram nesta expansão.

> **Atualização (ADR 0040) — revisado após feedback da orientadora.** O redutor entra
> *levemente* na sensibilidade: só `n_components` (5/10/15/20), com o clusterizador fixo
> no padrão (hdbscan), como **procedência** (responde ao knob ≠ valor "ótimo").
> `n_neighbors`/`min_dist` seguem **só discutidos**, não varridos.

**O artefato de cada passada: um relatório HTML.** Cada passada termina num
relatório **HTML autocontido**, em PT-BR, no design system **V1 Sereno** da própria
ferramenta (mesma paleta, tipografia e ícones; **offline**, sem rede). Ele é
**gerado a partir de uma execução real** — cada número rastreia até a run que o
produziu (procedência), nunca é digitado à mão — e é **completo o bastante para ser
lido por quem não acompanhou o processo** (explica o que é a ferramenta, o que a
silhueta mede, o que a passada comparou e o que fica para depois). O relatório
**herda a honestidade** desta nota: exploratório, vieses nomeados, n=1, **sem coroar
um vencedor**.

> **Status (ADR 0042) — figura ilustrativa implementada.** O relatório inclui uma projeção
> **PCA-2D** do run padrão (dados antes/depois do agrupamento), a partir do espaço de
> **384-dim** (sombra linear determinística; o agrupamento roda no espaço reduzido, então o
> scatter 2D é **ilustrativo**, não o espaço do cálculo). Só o **default** (HDBSCAN), para
> não convidar veredito visual. `matplotlib` é extra opcional (`[viz]`); ausente, o relatório
> mostra um aviso visível no lugar. A legenda é prosa do autor (a escrever).

## 5. Convenção de reprodutibilidade nas tabelas

Os **scores são determinísticos** (mesma entrada + mesma config → mesmo número), mas
os **nomes das pastas variam** quando o Ollama está ligado (a nomeação por LLM é
não-determinística). Para tabelas reproduzíveis, os grupos são rotulados por
**número** ("Grupo 1", "Grupo 2", …), e não pelo nome gerado.

Ressalva importante: a numeração é **local a cada execução** — "Grupo 2" do HDBSCAN
não é o "mesmo" que o "Grupo 2" do kmeans. Portanto os rótulos por número servem
para reportar *dentro* de uma execução; a comparação **entre** algoritmos se apoia
em números agregados/estruturais (médias, nº de outliers, distribuições), não no
casamento de grupos por nome.

## 6. Limitações declaradas abertamente

Declarar os limites é o que mantém o resto defensável.

- **Um único corpus (n = 1).** O n=1 fragiliza uma *comparação* muito mais do que
  uma *descrição*: para "descrever a ferramenta numa entrada real", um corpus basta;
  para "comparar três algoritmos", um corpus é uma anedota. A comparação será
  declarada como **ilustrativa neste corpus, não conclusiva**. (Isto também
  **emenda** o ADR 0018, que prometia 3–4 corpora — ver §8.)
- **A silhueta exclui o `Outros`, e o kmeans não produz outliers.** Logo, os
  algoritmos seriam pontuados em **subconjuntos diferentes de arquivos** — não é uma
  comparação maçã-com-maçã. Tratar isso no momento da comparação (pontuar sobre um
  conjunto comum de arquivos, ou reportar a cobertura ao lado de cada score).
- **Hiperparâmetros no regime de poucos arquivos não foram afinados.** O que se deve
  é procedência + a ressalva, não prova de otimalidade.

## 7. Trecho-âncora para a defesa

Esta é a frase (ou sua versão final em prosa) que abre a parte comparativa e
pré-empta a maioria dos "por que você não testou Y também?":

> *"Este capítulo caracteriza o comportamento da ferramenta proposta sobre uma
> entrada real e heterogênea, usando a configuração padrão do projeto. Além de
> descrever o que a ferramenta faz, ele oferece uma justificativa empírica
> **limitada** para as escolhas estratégicas do padrão que repousavam em
> intuição — o algoritmo de agrupamento e os seus hiperparâmetros. Essa
> justificativa é feita por
> **procedência** e por **caracterização honesta dos trade-offs**, sob múltiplas
> lentes internas cujos vieses são explicitados — e não por uma busca em grade que
> alegasse um ótimo global, nem por validação contra um gabarito (rejeitada em
> bases epistemológicas; ver ADR 0018). A contribuição é a metodologia e a
> discussão, independentemente de qual algoritmo pontue mais alto em qual lente."*

As três afirmações que sustentam o parágrafo:

1. **Caracterização + justificativa limitada** — não é validação, nem otimização.
2. **Procedência e trade-offs honestos, independentes do resultado** — sem coroar
   vencedor.
3. **Limites assumidos** (n=1; vieses das métricas) — o resto é trabalho futuro.

## 8. Relação com o ADR 0018

Esta nota **emenda** o
[ADR 0018](../ADR/0018-empirical-characterization-no-ground-truth.md) em dois eixos:

- **De "descritivo, não comparativo" → "descritivo + comparação e sensibilidade
  limitadas"** das escolhas do algoritmo e dos seus hiperparâmetros, sob os
  princípios da §3 (que preservam o espírito do 0018: franqueza acima de falso rigor
  — métricas internas *caracterizam* trade-offs, não *certificam* correção).
- **De "3–4 corpora" → "um corpus, com o limite assumido"** (§6).

O 0018 continua válido no essencial (sem ground truth, sem ARI/NMI, sem alegação de
correção). Para manter `docs/` como fonte autoritativa, o
[ADR 0038](../ADR/0038-bounded-empirical-justification-default-clusterer.md) registra
formalmente esta emenda.
