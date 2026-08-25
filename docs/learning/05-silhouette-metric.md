# 05 — Entendendo a métrica Silhueta (e em qual espaço ela é calculada)

**Contexto.** O Capítulo 4 (a caracterização empírica do TCC) foi recomeçado do
zero, adicionando **uma métrica de cada vez, totalmente compreendida**, cada uma
medindo *aquilo que a ferramenta realmente entrega* — as pastas da proposta real e
os embeddings reais. A primeira métrica é a **Silhueta**
(`dynamic-folding silhouette <dir>`). Seu primeiro resultado, no corpus
deliberadamente bagunçado do mundo real (a pasta Downloads), foi:

> `Silhouette: 0.110  (7 groups, 45 files; 8 in Outros skipped)` — idêntico em 5
> execuções (a ferramenta é determinística).

Antes de decidir o *próximo* passo — uma linha de base aleatória, para tornar
`0.110` interpretável — paramos para entender plenamente o que a silhueta mede e
para conseguir defender as escolhas por trás dela. Esta nota é esse entendimento,
escrita para ser relida e para que cada escolha se sustente na defesa.

---

## 1. O que a silhueta mede (em termos simples)

Para **cada arquivo**, a silhueta faz uma única pergunta:

> *"Estou mais perto dos arquivos do meu próprio grupo do que dos arquivos do
> grupo vizinho mais próximo?"*

- Claramente mais perto do meu próprio grupo → esse arquivo pontua perto de **+1**.
- Em cima do muro (mais ou menos à mesma distância dos dois) → perto de **0**.
- Na verdade mais perto de um grupo *diferente* do que do meu → **negativo** (até
  −1).

A silhueta reportada (`0.110`) é simplesmente a **média** dessa pontuação por
arquivo sobre todos os arquivos que caíram em um grupo de verdade.

Como nossos embeddings são *normalizados*, a distância euclidiana entre eles anda
lado a lado com a similaridade de cosseno. Então, no nosso caso, a silhueta está
de fato perguntando: **"os arquivos agrupados juntos são realmente similares em
significado?"** — que é exatamente o que queremos saber sobre uma pasta proposta.

A escala *não* é uma porcentagem. Uma leitura aproximada:

- por volta de **0** → os grupos se sobrepõem; a pertinência é pouco melhor que
  arbitrária.
- **positivo** → os arquivos de fato ficam mais perto do próprio grupo do que dos
  vizinhos — há estrutura real (ainda que modesta).
- em direção a **+1** → grupos compactos e bem separados.

## 2. Dois espaços: onde a ferramenta *agrupa* vs. onde nós *pontuamos*

Esta é a coisa mais importante — e mais contestável — de entender.

O pipeline, em termos simples:

1. Cada arquivo vira uma **"impressão digital de significado" de 384 números** (o
   embedding bruto do SBERT).
2. O **UMAP comprime esses 384 números para 10**, para dar ao algoritmo de
   agrupamento um espaço mais fácil de trabalhar.
3. O **HDBSCAN desenha os grupos nesse espaço de 10 números** — é isso que produziu
   os 7 grupos.
4. A **silhueta pontua esses grupos de volta no espaço original de 384 números.**
   Os vetores reduzidos de 10 números são então *descartados* — eles nem sequer
   são guardados depois que a proposta é construída.

Ou seja: **agrupados em 10 dimensões, avaliados em 384 dimensões.** Por que avaliar
em um lugar diferente de onde o agrupamento aconteceu?

**Porque os dois espaços respondem a duas perguntas diferentes:**

- O **espaço bruto de 384 dimensões é o "espaço de significado"** — a compreensão
  real do modelo sobre o que cada arquivo *é*. Pontuar ali pergunta: *"Os arquivos
  que coloquei na mesma pasta são de fato sobre coisas similares?"* — o que importa
  para uma pessoa organizando documentos.
- O **espaço de 10 dimensões do UMAP é o espaço de rascunho interno da
  ferramenta** — uma área de trabalho que o UMAP inventa só para facilitar o
  agrupamento. Seus números não significam nada por si só. Pontuar ali pergunta:
  *"O UMAP e o algoritmo conseguiram separar as coisas dentro da própria área de
  trabalho deles?"* — uma pergunta sobre o maquinário, não sobre o resultado.

**Nós avaliamos o produto (as pastas fazem sentido?), não o rascunho do
maquinário.**

### Importante: pontuamos os grupos entregues, não refazemos o agrupamento

Vale deixar isso explícito, porque é uma confusão fácil de ter. A silhueta usa **os
grupos que a ferramenta realmente entrega** — os rótulos produzidos pelo HDBSCAN no
espaço reduzido — e apenas os *pontua* usando os vetores brutos. Em dois eixos:

- **Os grupos (os rótulos):** vêm do agrupamento feito no espaço **reduzido**. São
  fixos — são as pastas propostas.
- **A geometria (as distâncias):** medida no espaço **original** de 384 dimensões.

Em particular, **não rodamos um segundo agrupamento no espaço bruto.** Refazer a
clusterização sobre os 384 números seria uma coisa *diferente* — poderia produzir
grupos diferentes dos que a ferramenta entrega — e responderia *"esses vetores de
384 dimensões são agrupáveis?"* em vez de *"as pastas que a ferramenta propõe são
coerentes?"*. Esse re-agrupamento no espaço bruto era, aliás, justamente **a falha
da abordagem antiga** (a pilha de caracterização abandonada): ela reclusterizava os
vetores em vez de avaliar a proposta real. O recomeço do Capítulo 4 corrige
exatamente isso — medimos o que a ferramenta entrega.

### Por que pontuar no espaço reduzido *inflaria* o número — e enganaria

Dois efeitos separados empurrariam a pontuação do espaço reduzido para cima, **e
nenhum dos dois significa que as pastas são de fato melhores:**

1. **O UMAP fabrica separação.** A função dele é puxar pontos similares para perto
   e empurrar o resto para bolhas arrumadas e bem separadas. Medir "separação" na
   saída do UMAP é, em parte, apenas medir *o UMAP fazendo o trabalho dele*. (Os
   próprios autores do UMAP alertam que as distâncias *entre* bolhas na saída dele
   não são confiáveis.)
2. **Menos dimensões = lacunas que parecem maiores.** Em 384 dimensões, quase tudo
   fica a uma distância parecida de tudo — a *maldição da dimensionalidade* — o que
   comprime a silhueta em direção a 0. Caia para 10 dimensões e as lacunas reabrem
   e o número sobe *só por ter menos dimensões*, não por um agrupamento melhor.

Então o número do espaço bruto é **mais baixo e conservador** — a versão honesta e
difícil de inflar. Um número alto no espaço reduzido poderia ser UMAP +
dimensionalidade em vez de pastas genuinamente coerentes.

Este é o mesmo princípio por trás de todo o recomeço do Capítulo 4: **medir o que a
ferramenta entrega** — as pastas, julgadas pelo significado real — e não seus
passos intermediários internos.

## 3. Uma sutileza: silhueta e HDBSCAN discordam sobre a *forma* do grupo

A silhueta e o algoritmo que *fez* os grupos nem sequer definem "um bom grupo" da
mesma maneira.

- **A silhueta quer uma bola compacta.** Sua lógica ("todo mundo perto do próprio
  grupo, longe dos outros") assume implicitamente que um grupo é uma bolha compacta
  e mais ou menos *redonda*.
- **O HDBSCAN quer um filamento denso.** Ele procura regiões onde os pontos estão
  densamente compactados e *conectados*, independentemente da forma — uma curva
  longa, uma meia-lua, um galho, tudo conta, desde que o fio denso seja contínuo.

Então um se importa com **compacidade/redondeza**, o outro com
**densidade/conectividade**.

**Onde eles discordam:** imagine um "macarrão" longo, curvo e denso de pontos.

- HDBSCAN: *"Um grupo só — é um filamento denso e contínuo."*
- Silhueta: *"Mediano — as duas pontas do macarrão estão longe uma da outra, talvez
  tão longe quanto um grupo vizinho."*

O mesmo agrupamento: polegar para cima de um e um dar de ombros do outro. Eles
estão medindo coisas diferentes, não se contradizendo.

**Consequência para `0.110`:** se o HDBSCAN encontrou alguns grupos alongados, mas
reais, a silhueta os subestima *pela forma, não pela qualidade*. Essa é **mais uma
razão para `0.110` ser uma leitura conservadora**, e não um veredito de que as
pastas são ruins.

### Então por que usar a silhueta, se ela não combina com o HDBSCAN?

Mas o descompasso corta para **os dois lados**, e é mais honesto dizer isso. A
silhueta e uma métrica de densidade são simplesmente duas definições diferentes de
"uma boa pasta", e nenhuma é universalmente correta:

- **A silhueta** premia pastas *compactas e específicas* (cada arquivo perto de
  todos os outros).
- **Uma métrica de densidade (DBCV)** premia pastas *densas e conectadas*,
  tolerando pastas amplas, de múltiplos temas relacionados, de qualquer forma.

A preferência da silhueta por compacidade até pega uma falha real — um "filamento
denso" cujas duas pontas são sobre coisas diferentes é uma pasta ruim, e a silhueta
a penaliza. Mas essa *mesma* preferência **também penaliza pastas boas, porém
amplas**: uma pasta sensata de "Aprendizado de Máquina", contendo tanto arquivos de
redes neurais quanto de árvores de decisão, são duas sub-bolhas no espaço de
embeddings, e a silhueta não gosta dessa forma esticada, mesmo a pasta sendo
perfeitamente razoável. Então a silhueta é uma lente *útil, porém parcial* — melhor
lida como **conservadora** (uma pontuação modesta como `0.110` pode refletir pastas
amplas, mas coerentes, e não pastas ruins). A correção não é descartá-la, e sim
**acrescentar uma lente sensível à densidade (DBCV) como uma segunda visão** num
passo futuro.

Além disso, três razões práticas e simples para ela ser uma boa avaliadora de
*saída*:

- **Um número só**, fácil de reportar e de raciocinar.
- **Só precisa dos rótulos** — basta (os vetores + em qual pasta cada arquivo
  caiu), então funciona com *qualquer* método de agrupamento; troque o
  clusterizador e a métrica continua valendo igual.
- **Amplamente compreendida**, o que importa para defendê-la.

A limitação honesta a declarar abertamente: como a silhueta favorece formas
compactas, ela é uma **avaliadora conservadora para uma ferramenta baseada em
densidade** — nunca dará nota máxima a um grupo válido, porém alongado. Dizer isso
reforça o mesmo tema de todo o resto: **`0.110` é uma leitura de piso, não o teto
da ferramenta.**

## 4. O que `0.110` significa agora — e o que não significa

- É **positivo**, em um corpus do mundo real deliberadamente bagunçado. Isso é
  evidência *necessária* de estrutura real: os grupos juntam arquivos similares
  melhor do que nada.
- **Não** é comparável a âncoras de livro-texto como "0,5 = bom". Dois efeitos
  separados (a concentração de distâncias em alta dimensão e a penalização pela
  silhueta de grupos HDBSCAN não-redondos) empurram nosso número para baixo, então
  um valor absoluto *baixo* aqui **não** significa *pastas ruins*.
- Uma silhueta sozinha ainda é **quase ininterpretável por si só.** Positivo é
  melhor que negativo, mas *"`0.110` está claramente acima do que se obteria por
  sorte?"* fica sem resposta. Fechar essa lacuna é o que a linha de base aleatória
  (próxima seção) faz.

**Necessário, não suficiente:** `0.110` ser positivo coloca *em jogo* a
possibilidade de estrutura real; não prova por si só que as pastas são boas.

## 5. A linha de base aleatória (construída)

Para tornar `0.110` interpretável, o comando `silhouette` agora também reporta uma
**linha de base aleatória**.

**A ideia em uma frase:** *que silhueta obteríamos se os mesmos 45 arquivos fossem
jogados nos mesmos 7 grupos de forma aleatória?* Se um agrupamento aleatório pontua
por volta de **zero** e a ferramenta pontuou **`0.110`**, essa diferença é sinal
real. Se o aleatório *também* pontua ~`0.110`, o agrupamento da ferramenta não é
melhor que o acaso.

**Por que o aleatório fica perto de 0 (ou abaixo):** quando um arquivo é colocado
em um grupo aleatório, seus "colegas de grupo" são apenas arquivos aleatórios — em
média, não mais perto do que arquivos de qualquer outro grupo — então sua pontuação
de silhueta ≈ 0, e a média fica em torno de 0 (levemente negativa neste corpus). A
aleatoriedade destrói justamente aquilo que a silhueta premia.

**Como é construída:** mantemos exatamente os mesmos arquivos pontuados, os
**mesmos 7 tamanhos de grupo** e o **mesmo espaço bruto de 384 dimensões**, e
embaralhamos apenas *qual arquivo cai em qual grupo*. Fazemos isso **1000 vezes** e
reportamos a média como o "piso aleatório" (mais uma margem de variação). Usamos
muitos embaralhamentos em vez de um só porque um único embaralhamento é, ele mesmo,
um sorteio com sorte ou azar; a média estabiliza o piso. Uma semente fixa torna
tudo determinístico, como o resto da ferramenta.

**O resultado no corpus Downloads:**

```
Silhouette: 0.110  (7 groups, 45 files; 8 in Outros skipped)
Random baseline: -0.074 +/- 0.012 over 1000 shuffles  (real 0.110 is +0.184 above it)
```

O piso aleatório é, na verdade, levemente **negativo** (`-0.074`), então `0.110`
fica claramente `+0.184` acima do acaso — muito maior que a variação de `0.012` do
piso. Em termos simples: o agrupamento da ferramenta **não** é ruído.

**O limite honesto da linha de base:** superar o piso aleatório apenas descarta
*"`0.110` é só ruído"*. Isso **não** prova que as pastas são *boas* — essa é uma
barra mais alta que uma comparação com o acaso não consegue vencer. A linha de base
**calibra** `0.110`; ela não **certifica** qualidade. (Também mantém o trabalho
seguramente *descritivo, não comparativo* — uma métrica, um corpus — coerente com a
decisão de escopo em `02-experimental-scope.md`.)

## 6. Trecho pronto para a tese

> "A silhueta avalia, para cada arquivo, se ele está mais próximo dos arquivos do
> seu próprio grupo do que dos arquivos do grupo vizinho mais próximo; o escore
> final é a média desses valores por arquivo e varia de −1 a +1. Optamos por
> calculá-la sobre os **embeddings brutos de 384 dimensões** — o espaço em que o
> modelo de linguagem representa o *significado* de cada arquivo — e não sobre o
> espaço de 10 dimensões reduzido pelo UMAP, que é apenas um espaço de trabalho
> interno usado pelo algoritmo de agrupamento. Medir no espaço reduzido
> superestimaria a qualidade, porque o UMAP é projetado para separar os pontos em
> grupos visivelmente distintos e porque, com menos dimensões, as distâncias se
> distinguem mais facilmente. A medição no espaço bruto é, portanto, uma leitura
> **conservadora**: pergunta se os arquivos reunidos numa mesma pasta são de fato
> semanticamente semelhantes — o critério que realmente importa para o usuário. O
> valor obtido (0,110), sobre uma entrada real e heterogênea, é positivo,
> indicando estrutura acima do acaso, mas não é diretamente comparável a
> referências de livro-texto como '0,5 = bom'."

## 7. Reprodutibilidade — a execução exata que produziu `0.110`

Procedência confirmada (cite isto ao lado do número na tese):

- **Comando:** `dynamic-folding silhouette "C:\Users\moise\iCloudDrive\Downloads" --config config/default.toml`
- **Versão:** `dynamic-folding 1.3.0`
- **Configuração:** `config/default.toml` — embeddings SBERT + UMAP (10 dim) +
  HDBSCAN.

Os padrões *embutidos no código* (redutor `identity` + `kmeans`) diferem de
`config/default.toml`, então sempre cite o `--config` explicitamente em vez de
confiar em "sem config".

## 8. Referências para leitura adicional

- Rousseeuw, P. (1987). *Silhouettes: a graphical aid to the interpretation and
  validation of cluster analysis.* — a definição original da silhueta.
- Documentação do scikit-learn, `sklearn.metrics.silhouette_score` — a função exata
  que chamamos (distância euclidiana por padrão).
- McInnes, Healy & Melville (2018), *UMAP*, e as notas/FAQ da documentação do UMAP
  — incluindo a ressalva de que as distâncias entre grupos na saída do UMAP não são
  significativas.
- Campello, Moulavi & Sander (2013) e a biblioteca `hdbscan` (McInnes & Healy) —
  agrupamento baseado em densidade e por que seus grupos podem ter formas
  arbitrárias.
- Beyer et al. (1999), *"When Is 'Nearest Neighbor' Meaningful?"*, e Aggarwal et
  al. (2001), *"On the Surprising Behavior of Distance Metrics in High-Dimensional
  Space"* — o efeito de concentração de distâncias (a "maldição da
  dimensionalidade") que comprime a silhueta no espaço bruto.

Você não precisa ler estas referências para defender o TCC — a explicação acima é
autocontida — mas elas estão aqui caso queira ver cada ideia usada em outros
lugares.
