# 06 — Entendendo a métrica DBCV (a segunda lente, e por que no espaço reduzido)

**Contexto.** O Capítulo 4 adiciona **uma métrica de cada vez, totalmente
compreendida**, cada uma medindo *aquilo que a ferramenta realmente entrega*. A
primeira foi a **Silhueta** (nota 05), uma lente de **viés convexo** — ela premia
grupos compactos e mais ou menos redondos. Como discutido lá, uma métrica sozinha
não é neutra, e a silhueta é enviesada *contra* um algoritmo baseado em densidade
como o HDBSCAN. A correção honesta não é trocar de métrica, e sim **acrescentar uma
segunda lente de viés genuinamente oposto** antes de qualquer conclusão. Essa lente
é o **DBCV** (*Density-Based Clustering Validation*) — implementado conforme o
ADR 0038/0039. Esta nota é o entendimento dele, escrita para ser relida e para que
cada escolha se sustente na defesa.

---

## 1. O que o DBCV mede (em termos simples)

A intuição mais fácil é imaginar cada grupo como uma **cadeia que interliga todos
os seus pontos** — cada arquivo ligado ao vizinho mais próximo, até que o grupo
inteiro forme uma única teia conectada, sem sobras e sem ciclos. (Formalmente, essa
teia é a *árvore geradora mínima* — a MST — do grupo.) A partir dessa cadeia, o
DBCV pergunta duas coisas sobre cada grupo:

- **Esparsidade** (o quão *frouxo* o grupo é por dentro): é o **elo mais frouxo** da
  cadeia — a **maior distância** entre dois pontos que ainda precisam estar ligados
  para o grupo não se partir. Um grupo denso tem todos os elos curtos; um grupo
  esparso tem pelo menos um elo longo esticando a teia. *Menor é melhor.*
- **Separação** (o quão *isolado* o grupo é por fora): é a **folga até o grupo
  vizinho mais próximo** — o menor salto que seria preciso dar para sair deste grupo
  e cair no de perto. *Maior é melhor.*

A nota de **cada grupo** compara as duas:

> nota = (separação − esparsidade) / máximo(separação, esparsidade)

Isso cai sempre entre **−1 e +1**, e o **sinal** conta a história de imediato:

- separação **maior** que a esparsidade → o grupo é mais coeso por dentro do que a
  folga que o cerca → nota **positiva** (grupo bem formado e isolado).
- esparsidade **maior** que a separação → o grupo é mais frouxo por dentro do que a
  distância até o vizinho → nota **negativa** (o grupo praticamente encosta no
  vizinho, ou está esgarçado demais para ser um grupo só).

O **DBCV final** é a **média das notas por grupo, ponderada pelo tamanho** de cada
grupo (o peso é proporcional ao *número de pontos*, não à densidade — a densidade já
entrou dentro da nota, como a próxima seção mostra). Grupos maiores pesam mais no
resultado; grupos minúsculos não dominam a média.

**E o ruído?** Os arquivos que a ferramenta marcou como ruído (a pasta `Outros`)
não formam um grupo e **não recebem nota**. Mas eles continuam contando no
**denominador** da média — ou seja, entram na conta como "peso morto". O efeito é
**diluir** o DBCV em direção a 0: quanto mais ruído, mais a nota é puxada para
baixo. (Há uma identidade exata útil: `DBCV_sem_ruído = DBCV ÷ cobertura`, onde
cobertura é a fração de arquivos que caiu em algum grupo. Por isso nunca reportamos
um número "sem ruído" à parte — ele não diz nada além da cobertura, que já é
mostrada ao lado.)

## 2. Onde a densidade entra: as distâncias *ajustadas*

Até aqui falamos em "distância" como se fosse a distância crua entre dois pontos.
**Não é** — e é exatamente aqui que o DBCV vira uma lente de *densidade*, e não de
forma.

Antes de montar a cadeia, cada distância é **ajustada pela densidade local** de
duas peças:

1. **Distância de núcleo** (*core distance*) de um ponto: o quão **isolado** ele é —
   a distância até o seu k-ésimo vizinho mais próximo. Um ponto no meio de uma
   região densa tem núcleo pequeno; um ponto perdido numa região rala tem núcleo
   grande.
2. **Alcançabilidade mútua** entre dois pontos a e b: em vez da distância crua, usa
   o **máximo** entre três valores — `máximo(núcleo de a, núcleo de b, distância
   crua a–b)`. Ou seja: se *qualquer um* dos dois pontos vive numa região rala, o elo
   entre eles **incha**; só quando os dois estão em regiões densas o elo fica igual à
   distância crua.

A cadeia (a MST) é montada sobre essas distâncias **ajustadas** — e, portanto, tanto
a esparsidade quanto a separação são medidas nelas. **É aí que a "densidade" entra
na conta.** Um grupo denso e conectado tem elos ajustados curtos (esparsidade
baixa), mesmo que sua *forma* seja esticada ou torta; um grupo ralo é penalizado
pelos núcleos grandes de seus pontos.

**Por que isso é o viés *oposto* ao da silhueta.** A silhueta mede a distância
**crua** de cada arquivo até o "centro" do seu grupo → ela premia, implicitamente, a
bola compacta e redonda, e subestima formas irregulares (nota 05, seção 3). O DBCV
mede **conexão ao longo de uma cadeia** com distâncias **ajustadas por densidade** —
ele **julga por densidade, não por forma**, e por isso não penaliza um grupo válido
só por ele ser alongado. Duas definições legítimas e diferentes de "boa pasta";
nenhuma universalmente correta.

## 3. Em qual espaço se calcula — e por que aqui é o *reduzido* (10 dim)

Na nota 05, a decisão importante foi calcular a silhueta no espaço **bruto de 384
dimensões** (o espaço de *significado*), e não no reduzido. **Com o DBCV é o
contrário — e não por gosto, mas por necessidade.**

O DBCV **não pode** ser calculado em 384 dimensões. A estimativa de densidade exige
**muito mais pontos do que dimensões** (n ≫ d); nosso corpus tem **n = 54 arquivos e
d = 384** (n ≪ d). Nesse regime, o termo de distância de núcleo da biblioteca
transborda numericamente (*overflow*) e a nota **colapsa para ≈ 0** — a densidade
fica, na prática, "desligada". Isso **não** é um parâmetro que dá para ajustar
(verificado: passar d ∈ {384, 10, 5, 2} dá resultados idênticos e o mesmo
transbordamento) — é um **limite conceitual, não um bug**. A densidade simplesmente
não faz sentido quando há mais dimensões do que pontos.

Felizmente, o agrupamento **já acontece** no espaço **reduzido pelo UMAP (~10
dimensões)** — é ali que a densidade é significativa e onde os grupos foram de fato
desenhados. Então é ali que o DBCV é calculado: n = 54 **> ** d = 10, o regime opera.
Vale a ressalva honesta: **n > d é o mínimo, não o confortável** (o ideal é n ≫ d);
com 54 pontos estamos acima do piso, mas não folgados — mais uma razão para tratar o
número como ilustrativo.

Um detalhe de engenharia que sustenta a honestidade: o DBCV pontua os **vetores
reduzidos reais** que a ferramenta usou para agrupar (agora guardados em
`RunResult.reduced_vectors`, contrato v2), e **não** uma reprojeção recalculada na
hora da avaliação. Recalcular arriscaria pontuar uma projeção *diferente* daquela que
produziu os grupos — o mesmo antipadrão de "re-derivar na avaliação" que o recomeço
do Capítulo 4 abandonou. Medimos o que a ferramenta entrega.

## 4. Duas lentes, dois espaços, dois vieses — por isso *independentes*

Juntando as notas 05 e 06:

|                | Silhueta          | DBCV               |
|----------------|-------------------|--------------------|
| **espaço**     | 384 dim (significado) | ~10 dim (agrupamento) |
| **distância**  | crua, até o centro    | ajustada por densidade, ao longo da cadeia |
| **viés**       | forma convexa/redonda | densidade/conexão, forma livre |

As duas lentes diferem **tanto no viés quanto no espaço**. Por isso elas são
**independentes de propósito** — nunca comparamos uma com a outra linha a linha, nem
subtraímos uma da outra. O ponto não é "qual das duas dá o número maior" (elas
sequer vivem no mesmo espaço); é que **uma métrica única e enviesada não descreve
ninguém com justiça**, então usamos duas de vieses opostos e discutimos honestamente
o viés de cada uma.

Isso **não** é uma comparação controlada entre os algoritmos. (Uma alternativa
considerada e rejeitada: recalcular a silhueta também em 10 dimensões, para tê-las
no mesmo espaço. Mas a "silhueta-10" não é a silhueta do espaço de *significado* que
o projeto defende — ela responde a outra pergunta, num espaço que o próprio projeto
chama de semanticamente vazio — e a limpeza de estar no mesmo espaço só serviria
para emitir um **veredito**, que com n = 1 nós deliberadamente não emitimos.)

## 5. A leitura assimétrica (o frame que sustenta tudo)

Aqui está a parte mais importante de interpretar o DBCV **sem** trair a
independência de resultado (o princípio de que nenhuma evidência interna coroa um
vencedor).

O espaço reduzido de 10 dimensões é a **casa do HDBSCAN**, por duas razões que se
somam: o DBCV mede densidade (o próprio critério do HDBSCAN), **e** o espaço foi
construído pelo UMAP para *preservar a vizinhança* — quem-está-perto-de-quem —, o
que favorece justamente métodos de densidade. Ou seja, o DBCV é o cenário **mais
favorável possível** ao HDBSCAN. Disso decorre uma leitura **assimétrica**:

- HDBSCAN indo **mal** aqui seria um **sinal forte** — falhar até na própria casa.
- HDBSCAN indo **bem** é o **esperado**, e **não prova nada** — é o mando de campo
  dele.
- k-means ou aglomerativo com nota **baixa** **não** conta contra eles — estão
  jogando fora de casa, com o viés errado.

É essa assimetria que **legitima** incluir uma métrica duplamente enviesada a favor
do padrão: sem ela, o DBCV seria uma validação *post-hoc* do HDBSCAN (proibida pela
independência de resultado do ADR 0038). Com ela, a justificativa do HDBSCAN como
padrão continua sendo **a priori, de projeto** (tratamento de ruído, inferência
automática do número de grupos, hierarquia nativa) — **intocada** por estes números.
Duas lentes é condição **necessária, não suficiente**, para um veredito que ainda
assim não damos.

## 6. O que os números significam agora — e o que não significam

No corpus congelado (`datasets/downloads_2026-06-15`, 54 arquivos):

| algoritmo      | silhueta (384, convexo) | DBCV (10 dim, densidade) |
|----------------|-------------------------|--------------------------|
| hdbscan        | +0,078                  | **+0,292**               |
| k-means        | +0,074                  | +0,009                   |
| aglomerativo   | **+0,110**              | +0,089                   |

- **Viés oposto, de manual.** A silhueta (viés convexo) favorece o **aglomerativo**;
  o DBCV (viés de densidade) favorece o **HDBSCAN**. Cada lente premia o que o seu
  viés valoriza — exatamente o que se espera de duas lentes opostas, e a melhor
  ilustração de por que nenhuma delas sozinha decide.
- **O único sinal forte não ocorreu.** Pela leitura assimétrica, o achado que
  importaria seria o HDBSCAN indo *mal* no DBCV — e ele foi bem (+0,292). Isso é o
  *esperado* (casa dele) e **não coroa ninguém**.
- **Descritor, nunca ranking.** Os números descrevem trade-offs; não elegem um
  vencedor. E são **dependentes do instantâneo do corpus** — valem para esta
  fotografia congelada, não como veredito geral.

**Necessário, não suficiente:** agora existem duas lentes de vieses opostos (a
pré-condição do ADR 0038 está cumprida); mas com **n = 1** o resultado é
**ilustrativo, não conclusivo**.

## 7. Trecho pronto para a tese

> "O DBCV avalia cada grupo por duas medidas calculadas sobre distâncias **ajustadas
> pela densidade local**: a *esparsidade* (o elo mais frouxo da cadeia que interliga
> os pontos do grupo) e a *separação* (a folga até o grupo vizinho mais próximo); a
> nota por grupo é (separação − esparsidade) / máximo(separação, esparsidade), no
> intervalo [−1, +1], e o escore final é a média dessas notas ponderada pelo tamanho
> dos grupos. Por depender de estimativa de densidade, que exige mais pontos do que
> dimensões, o DBCV é **inaplicável no espaço bruto de 384 dimensões** (com n = 54
> arquivos a densidade degenera) e é calculado no **espaço reduzido de 10 dimensões**
> em que o agrupamento de fato ocorre. Ele constitui uma **segunda lente de viés
> oposto** ao da silhueta — premia densidade e conexão, tolerando formas
> irregulares, enquanto a silhueta premia compacidade —, e por isso é lido como
> descritor complementar, jamais como comparação direta com a silhueta (vivem em
> espaços e vieses distintos). Como o espaço reduzido é o cenário mais favorável ao
> algoritmo baseado em densidade, sua leitura é **assimétrica**: apenas um desempenho
> *fraco* do HDBSCAN seria informativo; um desempenho forte é esperado e não
> constitui evidência a favor do padrão."

## 8. Reprodutibilidade

- **Comando:** `dynamic-folding compare datasets/downloads_2026-06-15 --config config/default.toml --html comparacao-report.html`
- **Corpus:** `datasets/downloads_2026-06-15` (54 arquivos, instantâneo congelado —
  ver nota sobre *corpus drift* em 05; o congelamento é o que torna os números do
  DBCV estáveis entre execuções).
- **Implementação:** `dynamic_folding/evaluation/dbcv.py` (`dbcv_of_run`), via
  `hdbscan.validity.validity_index` sobre `RunResult.reduced_vectors` (contrato v2).
  Partições degeneradas (< 2 grupos, validade não-finita, falha da biblioteca)
  retornam `None` + motivo — a avaliação nunca quebra.
- **Config:** `config/default.toml` — SBERT + UMAP (10 dim) + HDBSCAN. Cite o
  `--config` explicitamente (os padrões embutidos no código diferem).

## 9. Referências para leitura adicional

- Moulavi, Jaskowiak, Campello, Zimek & Sander (2014), *Density-Based Clustering
  Validation* — a definição original do DBCV (esparsidade, separação, alcançabilidade
  mútua, densidade "toda-a-vizinhança").
- Biblioteca `hdbscan` (McInnes & Healy), `hdbscan.validity.validity_index` — a
  função exata que chamamos, e a distância de núcleo / alcançabilidade mútua que ela
  reusa do HDBSCAN.
- Campello, Moulavi & Sander (2013) — o HDBSCAN em si; por que grupos baseados em
  densidade podem ter formas arbitrárias (o que o DBCV foi feito para avaliar de
  forma justa).
- McInnes, Healy & Melville (2018), *UMAP* — o redutor cujo espaço de ~10 dimensões o
  DBCV lê; preserva vizinhanças locais, o que favorece métricas de densidade.
- Beyer et al. (1999) e Aggarwal et al. (2001) — a concentração de distâncias em alta
  dimensão (n ≪ d), a mesma razão pela qual o DBCV é inaplicável em 384 dimensões.

Você não precisa ler estas referências para defender o TCC — a explicação acima é
autocontida — mas elas estão aqui caso queira ver cada ideia usada em outros
lugares.
