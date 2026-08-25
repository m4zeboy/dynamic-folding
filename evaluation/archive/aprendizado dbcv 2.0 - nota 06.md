O que o DBCV mede, e como ele dá uma nota para um agrupamento?

O DBCV mede duas coisas, distancia entre pontos dentro do grupo, como uma cadeia interligada, exemplo tenho um grupo com três pontos A - B - C, e a distancia entre A-B é 2 e a distância de B-C é 5, quanto menor é esse numero entre os pontos de um grupo, mais forte é o elo da cadeia que os interliga. A segunda é o quanto de espaço vazio existe entre os grupos, se eles estão bem separados, ou se sobrepõem. [Os algoritmos de densidade caracterizam ruído, aqui eu não sei como esse ruído é tratado nessa métrica]  

--- 
A cadeia tem dois elos, um curto e um longo.

Quando o DBCV vai resumir "quão frouxa/esparsa é essa cadeia" num só número, ele olha pra média dos elos, ou para um elo específico? Se for um específico - qual é por quê?

Pensa no ditado sobre corrente e elo. Responde de boca.

O elo mais fraco é o responsável quando a corrente se quebra, entendo que ele olha para esse elo mais fraco, ou o elo mais frouxo [essa é a palavra certa para dizer que os pontos estão muito separados nesse elo?]

--- 
**==A corrente é tão forte quanto o seu elo mais fraco==**

esparso = quando os pontos estão muito separados / pouca densidade.

density sparseness = esparsidade de densidade do grupo

pensa em frouxo -> escreve esparso

esparsidade interna = o elo mais frouxo *dentro* do grupo;
separação = o espaço vazio até o grupo vizinho mais próximo.

- Um grupo está bem definido quando qual dos dois é maior do que o outro?
- E o que acontece com a nota desse grupo se a folga até o vizinho for menor que o elo mais frouxo dentro dele?

Um grupo está bem definido quando quando a esparsidade interna é menor do que a separação, o que diz que o elo que liga os pontos dentro do grupo está bem forte.
Quando a folga até o vizinho é menor que o elo mais frouxo quer dizer que os grupos estão se sobrepondo, dificultando a caracterização de grupos diferentes.

---
agora cada grupo tem a sua nota. Mas o agrupamento inteiro precisa de **uma** nota só.

Como o DBCV junta N notas (uma por grupo) numa nota só do agrupamento? 
E o gancho: um grupo com 30 pontos e um grupo com 3 pontos devem pesar igual nessa média?

[não sei o mecanismo formal] minha intuição diz que o DBCV Junta as N notas em uma só por meio de uma média ponderada, onde cada grupo tem um peso diferente.

--- 
CRITÉRIO DO PESO

No seu exemplo 30 pontos vs 3 pontos: 

qual grupo puxa a nota final com mais força?
O grupo com 30 pontos.

E o peso é proporcional a que?
O peso é proporcional a densidade do grupo, um grupo com 30 pontos é 10x mais denso que um grupo com 3.

--- 
quantidade de pontos != de densidade.

Grupo A: 3 pontos colados, praticamente um em cima do outro
Grupo B: 30 pontos espalhados por um galpão inteiro

Qual é mais denso? grupo A

Se mesmo o grupo de 30 espalhado (menos denso) ainda pesa mais na nota final - então o peso é proporcional a quê, na real?

O peso é proporcional a quantidade de pontos.

---
O Peso faz um trabalho diferente da densidade

Ele responde "Quanto do conjunto (dataset) esse grupo representa?"

Dois trabalhos distintos.
Por isso peso é **tamanho**, não densidade.
Porque o peso não é por densidade? Porque densidade já entrou na nota; o peso mede a **fatia dos dados**

dbcv mede das coisas -> esparsidade e separação

RUÍDO

O ponto de ruído não está em grupo nenhum
Não tem nota de grupo
Mas ele existe no dataset
No peso de cada grupo = pontos do grupo / total de pontos.

Esse total conta os pontos de ruído ou não?
Sim ele entra na conta.

E se contar: O que acontece com a nota final quando o ruído é grande?
Quando muitos pontos são ruído, menos pontos sobram para serem caracterizados em grupos, logo a parte pontos do grupo da equação diminui, em relação ao total de pontos.

FALTA A CONSEQUÊNCIA NA NOTA FINAL <A MÉDIA>

*Se o peso de cada grupo encolhe, e o ruído não entra com nota nenhuma (ele não tem nota de grupo - só ocupa espaço no total)... a nota final do agrupamento é puxada para perto de quê?*

A nota é puxada para perto de 0. [só não consegui visualizar o porque esse número ímã arrasta quando o ruído domina.]

---

Imagina 100 pontos, e grupos com qualidade interna idêntica nos dois casos (digamos, nota de grupo +0,6):
- Pouco ruído: 90 pontos em grupos bons, 10 de ruído -> nota = 0.90 * 0.6 = 0.54  (perto de 0,6 que os grupos mereceram)
- Ruído domina: 10 pontos em grupos bons, 90 de ruído -> nota = 0.10 * 0.6 = 0.06 (perto de 0).
*Os grupos eram igualmente bons (+0.6) nos dois. O que mudou foi de quantos dados eles falam.*
O porquê do ímã: O ruído ocupa peso no **total**, mas entra com nota **zero** (não tem grupo -> nem boa nem ruim -> conta como 0). É um bloco que "vota 0". Quando o ruído domina, é um monte de votos-zero afogando as poucas notas boas -> a média agunda para 0.

A sacada que vale ouro na banca = nota ≈ 0 com ruído alto NÃO diz os grupos são ruins - diz os grupos por melhores que sejam, falam por quase ninguém. São coisas diferentes.

Por que a nota é baixa se os grupos eram bons?

A nota é baixa por que eles falavam de apenas 10% do toal de 100, 90 não entraram na conta.

Se os 90 de ruído realmente não entrassem na conta, sobrariam só os 10 entre si -> a nota seria 0.6 não 0.06. O que derrua para 0.06 é justamente os 90 estarem lá embaixo.

> os 90 de ruído entraram na conta ou não? E se entraram - entraram onde (em que parte da fração) e contribuindo com que nota?

A nota é baixa por que o grupo fala de apenas 1/10 do total. os outros 9/10 de ruído ficaram no denominador, puxando a nota para perto de 0.

---

**Explica o DBCV do começo ao fim, com suas palavras, como se a banca tivesse perguntando "o que é essa métrica e como ela funciona?"**

Duas partes
Cadeia/Elo frouxo
Nota por grupo
Média ponderada por tamanho
Ruído diluindo

O que mede
Como pontua um grupo
Como N grupos viram uma nota só
O que o ruído faz

O DBCV é uma métrica para avaliar agrupamentos gerados por algoritmos baseados em densidade.
Ele mede a esparsidade e a separação de cada grupo.
A esparsidade é mede o elo entre os pontos dentro de um mesmo grupo e considera o elo mais fraco como o de referência. Exemplo, tenho um grupo com tres pontos A-B-C. O elo entre A-B é 2 e o elo entre B-C é 5. O elo mais fraco é o 5, pois significa que os pontos estão mais distantes.
A separação mede o quanto os grupos estão separados, quanto de espaço vazio existe entre eles, quanto mais espaço entre os grupos existir, mais separados eles são, quanto menos, mais sobrepostos, mais difícil de caracterizar um grupo do outro.
Essas duas medidas são combinadas em uma formula para calcular uma medida única por grupo, que varia entre -1 e 1.
Agora que cada grupo tem sua nota, precisamos dar uma nota pro agrupamento inteiro. Vamos pegar essas notas e aplicar a média ponderada, onde o peso é a quantidade de pontos que o grupo tem. Esse valor vai nos dizer o quanto esse grupo representa do total do corpus.
Se o agrupamento caracterizou muitos pontos como ruído, os grupos terão uma quantidade menor de pontos, eles representarão uma parcela menor do total do corpus, resultando em um valor próximo a 0, pois mesmo que os pontos de ruido nao tenham grupos, eles contabilizam para o TOTAL. [rascunho muito feio, nao liguei varias partes, repeti muitas palavras, joguei o que veio na mente]

---



O DBCV é uma métrica para avaliar agrupamentos gerados por algoritmos baseados em densidade.
Ele mede a esparsidade e a separação de cada grupo.

A esparsidade é mede o elo entre os pontos dentro de um mesmo grupo e considera o elo mais fraco como o de referência. 

Exemplo, tenho um grupo com tres pontos A-B-C. O elo entre A-B é 2 e o elo entre B-C é 5. O elo mais fraco é o 5, pois significa que os pontos estão mais distantes.

A separação mede o quanto os grupos estão separados, quanto de espaço vazio existe entre eles, quanto mais espaço entre os grupos existir, mais separados eles são, quanto menos, mais sobrepostos, mais difícil de caracterizar um grupo do outro.

Essas duas medidas são combinadas em uma formula para calcular uma medida única por grupo, que varia entre -1 e 1.

Combinadas como?
separaçao  - esparsidade / max(separação, esparsidade)
2 - 1 / 2 = 1/2 = 0,5
1 - 2 / 2 = -1/2 = -0,5

Qual o sinal da nota do grupo quando a separação ganha da esparsidade?
Positivo ex: 2 - 1 / 2 = 1/2 = 0,5

E quando a esparsidade ganha?
Negativo: 1 - 2 / 2 = -1/2 = -0,5


Agora que cada grupo tem sua nota, precisamos dar uma nota pro agrupamento inteiro. Vamos pegar essas notas e aplicar a média ponderada, onde o peso é a quantidade de pontos que o grupo tem. Esse valor vai nos dizer o quanto esse grupo representa do total do corpus.
Se o agrupamento caracterizou muitos pontos como ruído, os grupos terão uma quantidade menor de pontos, eles representarão uma parcela menor do total do corpus, resultando em um valor próximo a 0, pois mesmo que os pontos de ruido nao tenham grupos, eles contabilizam para o TOTAL.

---
Para X: Dois pontos a distância 2 um do outro, no meio de um aglomerado bem cheio
Para Y: Dois pontos a distância 2 um do outro, mas flutuando sozinhos no vazio, longe de tudo.

A distância crua diz que os dois pares estão igualmente pertinho (2 e 2)

> Para uma métrica de densidade, esses dois pares deveriam contar igual? Se não - qual dos dois é densamente conectado de verdade, e o que a distância crua está deixando passar?

Para uma métrica de densidade, esses dois pares deveriam contar de forma diferente, pois o X está em um ambiente mais "cheio". A distância crua está deixando passar essa relatividade do ambiente.

RELATIVIDADE DO AMBIENTE = DENSIDADE LOCAL
A VIZINHANÇA DO PONTO
A distância crua é cega para a vizinhança;
ela só olha os dois pontos, nunca o entorno.

Peça 1 - Distância de núcleo (o número de isolamento): Quão isolado o ponto é = quão longe estão os próprios vizinhos dele.
Ponto num ambiente cheio -> vizinho colados -> isolamento pequeno.

Ponto sozinho no vazio -> até o vizinho mais próximo é longe -> isolamento grande.

Peça 2 - Distância ajustada (alcançabilidade mútua).

No Par X e no Par Y ambos com distância crua 2 - qual fica com a distância ajustada ≈ 2, e qual incha bem acima de 2? roda o `max` de cabeça para os dois.

ajustada(x,y) = max(isolamento de x, isolamento de y, 2)
ajustada(x,y) = max(baixo isolamento, alto isolamento, 2)

---
Aquela cadeia agora é montada usando qual distância - a crua ou a ajustada? E, com isso: Por que dá pra afirmar que o DBCV é uma métrica de densidade, e não só "mais uma métrica de distância?"

A cadeia é montada usando a distância **ajustada**, com isso pode-se afirmar que o DBCV é uma métrica de densidade pois considera a relatividade do AMBIENTE (densidade local, vizinhança do ponto), a distância crua não enxerga o entorno.