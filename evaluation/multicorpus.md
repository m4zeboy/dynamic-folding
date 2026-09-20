SILHUETA (viés convexo)     hdbscan    kmeans    aglomerativo
Corpus 1                     +0.078    +0.074       +0.110
Corpus 2                     +0.230    +0.114       +0.241
Corpus 3                     +0.203    +0.128       +0.212

DBCV (viés densidade)       hdbscan    kmeans    aglomerativo
Corpus 1                     +0.292    +0.009       +0.089
Corpus 2                     +0.380    -0.055       +0.264
Corpus 3                     +0.405    -0.289       +0.287

1. **Quem lidera cada lente, e isso é consistente nos 3 corpus?** (olha coluna por coluna).
   O aglomerativo lidera a silhueta e o HDBSCAN lidera o DBCV.
2. O **hdbscan lidera o DBCV nos 3** corpus. Pela **leitura assimétrica** que você domina (nota 06) — o DBCV é a casa de quem? — isso é um **sinal forte** ou o **esperado**?
   O DBCV é a casa do HDBSCAN, isso é um sinal esperado.
3. Onde o padrão é **forte** e onde ele é **frágil**? (olha os _números_, não só quem está na frente — tem lente onde a liderança é por um fio?)**
   O KMEANS teve a pior performance, ficando negativo em alguns casos, a liderança ficou apertada para os corpus 2 e 3 na silhueta. 

## Por que o k-means afunda na silhueta (apesar do viés convexo)
A silhueta não premia só "ser redondo" 
Premia compacidade:
Cada ponto perto dos colegas do próprio grupo.
E o viés convexo é necessário, não suficiente.
O k-means te dá a forma redonda, mas falha na compacidade por duas razões estruturais:
1. É forçado a poucos grupos grandes (k=3)
   Com dados reais bagunçados, 3 grupos = 3 sacolas grandes, 
   Cada uma misturando vários temas.
   Num saco grande e espalhado, 
   O ponto fica longo do próprio centro -> silhueta baixa.
   Redondo, mas frouxo.
2. Não solta outlier. 
   O k-means é obrigado a enfiar todo arquivo num dos 3 grupos
   Inclusive os arquivos **lixo**,
   Que puxam a compacidade para baixo.
   O hdbscan joga esses outros no `Outros` e é pontuado só no seu núcleo limpo (46/54)

## O aglomerativo (a linha que faltava)
Ele constrói uma árvore,
Juntando de baixo para cima os pontos mais próximos,
E depois corta essa árvore pra formar os grupos (ADR 0027).
Como o corte gera mais grupos menores (9,7,14 vs 3 do k-means),
Cada grupo é mais aperado -> e a silhueta adora compacidade.
Ele não ganha por ser mais convexo.
Ganha por ser mais **granular**

## O Fecho honesto que isso te dá
A ordenação da silhueta (Aglo -> hbdscan -> k-means) reflete **estrutura**.
Granularidade e tratamento de outlier.
E não "Qualidade".
Por isso ela não coroa ninguém: 
O favorito teórico do viés (k-means) até perde.
Isso, do lado do DBCV, casa com a casa limpa do hdbscan.

Antes de rascunhar - o teste (defend-it after): Me explica de volta, com tuas palavras, por que o k-means afunda na silhueta mesmo com o viés a favor. Se sair limpo é teu, e a gente parte para o rascunho feio.

O k-means afunda na silhueta mesmo com o viés a favor por que ao forçar a criação de poucos grupos, esses grupos ficam mais frouxos, o que desfavorece a compacidade, critério importante para o calculo da silhueta.  

## Rascunho feio

SILHUETA (viés convexo)     hdbscan    kmeans    aglomerativo
Corpus 1                     +0.078    +0.074       +0.110
Corpus 2                     +0.230    +0.114       +0.241
Corpus 3                     +0.203    +0.128       +0.212

DBCV (viés densidade)       hdbscan    kmeans    aglomerativo
Corpus 1                     +0.292    +0.009       +0.089
Corpus 2                     +0.380    -0.055       +0.264
Corpus 3                     +0.405    -0.289       +0.287


O padrão - 
as duas lentes dão ordenações diferentes e consistentes nos 3 corpus
silhueta: aglo > hdbscan > k-means; 
DBCV: hdbscan > aglo > k-means

Foi identificado um padrão que se repete nos três corpus. Para silhueta o padrão é 1. Aglomerativo, 2. HDBSCAN e 3. K-Means. Para o DBCV o padrão é 1. HDBSCAN 2. Aglomerativo e 3. K-means. Com o k-means em último lugar em todos os cenários.



DBCV = a casa do hdbscan 
-> liderer ali é esperado, não mérito; 
o sinal que importaria (hdbscan *mal* no dbcv) não apareceu em nenhum corpus.

[Mais uma vez] o dbcv é o HDBSCAN jogando em casa [nao posso escrever essa linguagem de "casa" no artigo], era esperado ele liderar nessa métrica, logo sem novidades, nenhum achado.

Silhueta != qualidade 
-> o viés convexo favoreceria  o k-means, mas ele fica em último (teu argumento da compacidade) 
-> a ordenação reflete estrutura, não qualidade.

No entanto ir bem na silhueta (ou no hdbscan) não significa que a qualidade do agrupamento é boa, pois o k-means foi mal, ele que joga com o viés convexo a favor. se por um lado ele cria grupos redondos, quando k é baixo, como no caso do k =3, os grupos ficam poucos compactos, ficam frouxos na verdade, grandes grupos frouxos, o que puxa para baixo a equação.    

Ninguém é coroado 
-> n = 3, ilustrativo, sem veredito.
[aqui é um ponto que toca o tom da escrita que mencionei, isso que me preocupa, realmente não da pra coroar ninguem, meu problema é como falar isso da maneira correta em tcc, pois se nao da pra coroar ninguem qual é o sentido da minha pesquisa? ela me recomendou o livro Metodologia de Pesquisa para Ciência da Computação Raul Sidnei Wazlawick para basear minha escrita da tese]

---
PRINCÍPIO: VOCÊ GENUINAMENTE NÃO PODE ALEGAR QUE O ALGORITMO X É ÓTIMO - VIESES OPOSTOS, SEM GABARITO, N = 3.

MAS ISSO É UMA FRASE DE ESCOPO, DITA UMA VEZ, DE QUEIXO ERGUIDO - NÃO UM PEDIDO DE DESCULPAS REPETIDO. 

VIRA CADA HEDFE NUMA AFIRMAÇÃO DO QUE O TRABALHO ESTABELECE:

- A ferramenta existe e funciona (contribuição)
- A razão de projeto do padrão (agrupamento por densidade: trata ruido, infere K, aceita formas arbitrárias) é defensável - e a caracterização confirma que os trade-offs se comportam como o projeto previa.
- uma metodologia de avaliar honestamente uma ferramenta assim, onde não há gabarito.

> "Não elegemos vencedor" vira "Eleger um ótimo global é outro estudo, deliberadamente fora do escopo; este trabalho caracteriza e justifica."

## Qual é a pergunta da pesquisa?
Eu realmente não sei qual é a pergunta da pesquisa, eu não escolhi esse tema, o que eu sei é que eu peguei a ideia da orientadora e desenvolvi (a IA fez a parte bruta), eu não manjo de python, muito menos de machine learning, eu so liguei os pontos para construir uma ferramenta.

Uma pessoa tem uma pasta Downloads uma bagunça, 200 arquivos jogados. O que a *tua* ferramenta faz por ela que não existia antes?

A minha ferramenta analisa a pasta da pessoa e apresenta uma organização para esses arquivos bagunçados.

---

**É possível uma ferramenta  analisar e apresentar uma organização para uma pasta real e bagunçada?**

**Quão coerente é a organização que ela propõe?**

**Como uma ferramenta assim se comporta quando submetida a pastas diferentes?**

---

Beat 1
A abertura (o que o leitor vê antes de você interpretar).
O trabalho dela:
Dizer que as duas lentes discordam na ordem, e que isso é consistente nos 3 corpus. Frame pra preencher do teu jeito:

>As duas lentes discordam na ordem do resultado para os algoritmos, e cada ordenação se mostrou consistente nos três corpus: a silhueta coloca o Aglomerativo à frente; O DBCV, o HDBSCAN.

Beat 4
A frase de escopo
Aqui mora o queixo erguido
Essa é a importante.
Lembra: a tua pergunta nunca foi "qual é o melhor"
Então essa frase não pede desculpas.
Ela delimita.
Uma frase, dita uma vez, de coluna reta.
Escolhe um começo e preenche

> Estes números caracterizam a coerência da proposta de organização; não elegem um vencedor porque seria outro tipo de estudo, deliberadamente fora do escopo. 

---

As duas lentes discordam na ordem dos algoritmos,
e cada ordenação se mostrou consistente nos três corpus:
a silhueta coloca o Aglomerativo à frente; o DBCV, o HDBSCAN. 
[beat 2 →] o DBCV é o HDBSCAN _jogando em casa_, era esperado ele liderar, logo _nenhum achado_.
No entanto, ir bem na silhueta não significa que a qualidade do agrupamento é boa, pois o k-means foi mal — ele que joga com o viés convexo a favor: 
cria grupos redondos, mas com K baixo (K=3) ficam poucos e frouxos, o que puxa a equação pra baixo. 
Estes números caracterizam a coerência da proposta de organização; 
não elegem um vencedor porque seria outro tipo de estudo, deliberadamente fora do escopo.

As duas lentes discordam na ordem dos algoritmos [fico pensando se aqui está bem entendivel o "ordem dos algoritmos"], e cada ordenação se mostrou consistente nos três corpus: A silhueta coloca o Aglomerativo à frente; o DBCV, o HDBSCAN.
Era esperado o  HDBSCAN liderar no DBCV, pois essa métrica mede a densidade e ainda mede no espaço reduzido, onde ocorreu o agrupamento; dupla vantagem desse algoritmo [dificuldade em colocar isso no texto]. Esse número específico não constitui evidencia a favor do hdbscan.

No entanto, ir bem em uma métrica não significa que a qualidade do agrupamento é boa [sinto que aqui nao esta fluido]. O K-means com a vantagem do viés convexo ficou em último lugar na silhueta, devido a caracterização de poucos grandes grupos (k=3), o que diminui a compacidade e puxa a nota para baixo.

Estes números caracterizam a coerência da proposta de organização; não elegem um vencedor pois isso seria material para outro estudo, deliberadamente fora do escopo.

---
As duas lentes discordam sobre qual algoritmo fica à frente, e cada ordenação se mostrou consistente nos três corpus: A silhueta coloca o Aglomerativo à frente; o DBCV, o HDBSCAN.
Era esperado o  HDBSCAN liderar no DBCV, pois essa métrica mede a densidade e ainda mede no espaço reduzido, onde ocorreu o agrupamento — dupla vantagem desse algoritmo. Esse número específico não constitui evidencia a favor do hdbscan.

A própria ordem na silhueta reflete estrutura, não qualidade. Prova disso: o k-means, com o viés convexo a favor, fica em último — não porque os grupos são ruins, mas porque a estrutura forçou a caracterização de apenas 3 grandes grupos, o que diminui a compacidade e puxa a nota para baixo.

Estes números caracterizam a coerência da proposta de organização; não elegem um vencedor pois isso seria material para outro estudo, deliberadamente fora do escopo.

---

n = 3 é pequeno -> a comparação é ilustrativa, não conclusiva (3 corpus não fecham uma lei geral)
Os corpus são heterogêneos entre si (tipos de arquivos diferentes) -> é a ferramenta sobre entradas reais diferentes, não um experimento controlado.

### Rascunho feio
Diz cada limite uma vez, com firmeza
nada de repetir, mas é só ilustrativo 3 vezes -- isso é o  hedge que a orientadora cortou
fecha declarando por que assumir esses limites não derruba o trabalho (o que ele ainda estabelece, apesar deles)

As limitacoes desse estudo sao [ajuda a melhorar a fluidez aqui] que avaliamos 3 corpus, número pequeno o nao possibilita uma generalização, mas uma ilustração.
Os tres corpus sao corpus REAIS, diferentes em sua forma e conteúdo, não se caracteriza um experimento controlado [a orientadora me cortou uma vez quando coloquei a palavra heterogeneo, disse que é uma palavra muito forte na area de ML, e que a chace é grande de eu usar o termo de forma errada, por isso nao o coloquei aqui].
essas limitacoes foram assumidas com a intenção de descrever como a ferramenta se comporta com dados REAIS, [sinto que repeti e que falta alguma coisa]

---

Beat 1
Esse estudo assume dois limites, declarados abertamente. O primeiro é o número de corpus: apenas três -- pequeno o bastante ilustrar, não para generalizar.

Beat 2
Os três corpus são corpus REAIS, diferentes em sua forma e conteúdo, não configura um experimento controlado.

Assumimos intencionalmente esses limites: a pergunta dessa pesquisa é sobre como a ferramenta se comporta em [nao sei se em é a melhor palavra aqui] pastas reais e bagunçadas, então um cenário pequeno, mas real, de forma que reflita a realidade dos usuários, importa mais que um cenário controlado. Dentro deles, o estudo ainda estabelece quão coerente é o resultado e como a ferramenta se comporta em pastas diferentes [sinto que repeti muita coisa aqui]

**É possível uma ferramenta  analisar e apresentar uma organização para uma pasta real e bagunçada?**

**Quão coerente é a organização que ela propõe?**

**Como uma ferramenta assim se comporta quando submetida a pastas diferentes?**

---
Esse estudo assume dois limites, declarados abertamente.

O primeiro é o número de corpus: apenas três — pequeno o bastante para ilustrar, não para generalizar. 

O segundo: os três corpus são corpus reais, diferentes em sua forma e conteúdo, não configura um experimento controlado.

Assumimos intencionalmente esses limites:

a pergunta dessa pesquisa é sobre como a ferramenta se comporta com pastas reais e bagunçadas, então um  estudo pequeno de forma que reflita a realidade dos usuários, importa mais que um cenário controlado. 

Dentro deles, o estudo ainda estabelece quão coerente é o resultado e como a ferramenta se comporta em pastas diferentes.