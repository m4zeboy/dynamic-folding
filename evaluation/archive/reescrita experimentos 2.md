## Legenda da figura
o que ela mostra? (os dois paineis)

[de onde veio esse 24,5% e o que ele significa?]
a figura mostra em dois painéis a distribuição dos pontos no espaço e os grupos formados.

qual é a pegadinha honesta? por que ela é ilustrativa e não prova nada
esse grafico foi produzido com PCA 2D, o PCA nao é a mesma estrategia que a ferramenta usa para reduzir a dimensionalidade. ele foi usado pois ele é deterministico, diferente do UMAP que nao é. no entanto ela nao prova nada, ate podemos ver grupos sobrepostos, o intuito é ilustrar o antes e o depois.

---
O PCA acha as 2 direções onde os dados mais se espalham (variância) e projeta os pontos nelas.
Essas 2 direções carregam 24,5% de espalhamento total das 384 dim
os outros 75,5% estão nas 382 dimensões que ficam de fora.
Ou seja: a figura mostra só um quarto da estrutura real;
três quartos foram achatados na projeção.
É o número que quantifica o quão "sombra" lossy ela é?

[e como funciona, quanto menor melhor?]

por que eles se sobrepoem?

o PCA projeta qual espaço?

E o agrupamento acontecem em qual espaço?

os grupos se sobrepoem por que foram achatados as 384 dimensoes em duas, 
em duas dimensoes pode parecer que os pontos estao sobrepostos,
mas em alta dimensao eles podem estar distantes.
O pca projeta no espaço original, no entanto o agrupamento acontece no espaço reduzido de 10 dimensoes.

---
o olho nao resolve agrupamento em alta dimensão, o que motiva a análise por meio das métricas Silhouette e DBCV.

---
o que mostra
a ressalva
e dai

A figura mostra em dois painéis a distribuição dos pontos no espaço e os grupos formados.
Para produzir a ilustração foi aplicado o PCA-2D devido a propriedade deterministica, cabe ressalvar que essa estratégia difere do padrão utilizado pela ferramenta, o UMAP-10D.
Essa figura tem o intuito de apenas ilustrar, pois perde-se muita informação ao reduzir de 384 dimensoes para 2, o que pode resultar em pontos sobrepostos e o PCA mostra o espaço real, enquanto o os grupos foram encontrados no espaço reduzido de UMAP-10 D.
Essa figura capturou 24,5% de variância nos dois eixos.
A olho nu não se avalia agrupamento em alta dimensao, o que motiva a análise por meio das métricas silhouette e DBCV.

---

A figura mostra em dois painéis a distribuição dos pontos no espaço e os grupos formados.

Para produzir a ilustração foi aplicado o PCA-2D devido à propriedade determinística. Cabe ressalvar que essa estratégia difere do padrão utilizado pela ferramenta, o UMAP-10D.

Os eixos PC1+PC2 capturam 24,5% de variância, logo 3/4 da variação não aparecem na figura, resultando em pontos sobrepostos. 

O PCA mostra o espaço original, enquanto os grupos foram encontrados no espaço reduzido de UMAP-10D.

A olho nu não se avalia agrupamento em alta dimensão, o que motiva a análise por meio das métricas silhueta e DBCV.

## Intro das matrizes
o que o leitor precisa entender primeiro para nao ler errado?
desses 4 blocos, qual é um aviso de leitura (como/ler o que nao fazer) e qual é a explicação) e qual é a explicação do mecanismo (por que os numeros se movem)? avisos vem antes ou depois da mecanica?

1 descritor
2 raciocinio do knob
5 piso
6 ler as colunas juntas

o leitor precisa entender primeiro que cada matriz é separada por algoritmo. cada algoritmo varia um hiperparametro particular. hdbscan min_cluster_size, k-means k, agglomerative min_cluster_size. cada hiperparametro significa algo particular para o proprio algoritmo.

o 6 é um aviso de leitura, o 2 é a explicacao do raciocinio
avisos vem antes.

a estrutura esta confusa para mim, esse conteudo nao esta tao fresco, vamos aos poucos.

---
INTRO DAS MATRIZES
[1] abertura: cada matriz = 1 algoritmo, varrendo 1 hiperparametro seu
[2] ? descritor nao ranking - nao compare essas tabelas entre si
[3] ? ler colunas juntas - dentro de uma tabela
[4] ? raciocinio do knob
[5] ?
[6] ?

comecando do nivel macro para o micro, o que faz mais sentido de ser o proximo ponto é o descritor nao ranking- nao compare essas tabelas entre si, pois o primeiro ponto fala da matriz, esse ponto fala das tabelas, e o proximo fala de dentro de cada tabela. 

---
[1] a matriz
[2] as tabelas
[3] dentro da tabela
[4] mecanismo
[...] piso


### ponto 3

#### pensar
aviso contra o leitor tentar comparar o `min_cluster_size` do hdbscan e aglomerativo.
- dentro do hdbscan,  o que aquele numero manda o algoritmo fazer? Dentro do HDBSCAN o `min_cluster_size` serve de referencia para que o algoritmo forme grupos com base nesse valor mínimo, ou seja, é preciso que exista min_cluster_size pontos em uma regiao densa para ser caracterizada um grupo.
- dentro do aglomerativo, o que o mesmo numero manda fazer? eu nao tenho muita expertise com o aglomerativo, o que eu sei é algo por cima, o algoritmo pega esse numero para fazer o corte na arvore hierarquica, entao, intuitivamente, sem conhecimento formal, eu entendo que quanto maior esse numero, maior é o nivel da arvore que é exigido para fazer o corte, por exemplo, vai se criando um dendograma, quanto mais alto o nivel, mais abrangente o grupo é.  
- é a mesma operação nos dois, ou o mesmo numero esta fazendo coisas diferentes? a resposta é nao é a mesma operação, em cada algoritmo o numero é usado com propostas diferentes.
---
por que o leitor nao deve casar linha com linha entre a tabela do HDBSCAN e a do aglomerativo?

mesmo nome de knob, mas operações de naturezas diferentes.
densidade x arvore

O leitor não deve comparar as linhas entre as tabelas principalmente do HDBSCAN e Aglomerativo, pois mesmo que tenham o mesmo nome, os parametros mandam os algoritmos fazerem coisas totalmente diferentes. 

---
nao defendo o **totalmente**. sinceramente eu nao sei a fundo o funcionamento do aglomerativo. honestamente eu so me preocupei com o k-means e o hdbscan pois ele marca o ruido.

### ponto 4
- enquanto aquela coluna varia de  2 a 8, o que está parado no fundo? (pensa nos outros knobs do algrotimo, no redutor, no embeder - quanto deles estáo se mexendo nessa tabela?)
o embedder e o redutor nao mexem.
- se voce imaginar todas as combinações possiveis de todos os knobs ao mesmo tempo, quanto de tudo isso uma varredura uma coluna so esta mostrando?
essa varredura está variando apenas UM hiperparametro de um espaço vasto. parcela ínfima, de um espaço de combinações.

---
1. o que a tabela de fato mostra (uma coluna variando, o resto fixo no padrao);
   essa tabela mostra como o algoritmo reage com a variaçao  desse unico hiperparametro.
2. o que o leitor nao deve concluir por causa disso (que viu o algoritmo inteiro / espaço todo)
o leitor nao deve concluir com base na leitura dessa tabela que foi encontrado a combinação otima para a operacao da ferramenta, pois um unico parametro foi variado, dentro de um vasto espaço de combinaçoes (redutor, embedding, outros que nao lembro de cabeca agr).

Esta tabela mostra como o algoritmo reage à variação desse único hiperparâmetro.
O leitor não deve concluir com base na leitura que foi encontrada a combinação ótima para a operação da ferramenta, pois a variação ocorreu em uma parcela ínfica de um vasto espaço de combinações de hiperparâmetros.

---
o que é cada matriz e o que cada algoritmo varia?

cada matriz é a descrição de como o algoritmo reage com a variação de um único hiperparâmetro particular ao algoritmo. o k-means varia o k [nao sei por que está descrito top_k, pra mim faz mais sentido apenas k], o hdbscan e o aglomerativo variam o min_cluster_size, embora com nomes iguais, servem propositos diferentes.
## As duas lentes
### Ponto 1
A silhueta premia esferas porque mede distância a um centro. 
Me explica, com suas palavras: o DBCV premia o quê
e por causa de quê na mecânica que você dominou (a cadeia, a distância ajustada)?
E por que isso é o oposto da silhueta, não só diferente?

O DBCV premia grupos como regiões densas que formam uma cadeia, varios pontos proximos entre si, e não proximos a um centro. por causa da distancia ajustada que leva em consideração o entorno, a vizinhança e não somente a distancia crua entre dois pontos.
Isso é o oposto da silhueta por que aqui não existe um centro para comparar os pontos, cada ponto contribui para o calculo dos outros pontos.

---

O que o DBCV faz com exatamente essas formas irregulares que a silhueta penaliza?

O DBCV é o oposto da silhueta pois não penaliza os algoritmos que produzem grupos com formas irregulares, cada ponto é avaliado como um elo em uma cadeia.

---

Premia regiões densas em cadeia, não proximidade a um centro;
Por causa da distância ajustada (enxerga a vizinhança, não só a distância crua);
Não penaliza formas irregulares (ao contrário da silhueta) - julga por densidade;
Por isso é lente de viés oposto.

Em que ordem essas peças entram para fluir? Qual é a frase de abertura do parágrafo do DBCV - e o que vem depois? Só a ordem.

ao contrario da silhueta o DBCV Não penaliza formas irregulares (julga por densidade)
por causa da distancia ajustada (enxerga a vizinhança)
premia regioes densas em cadeia
por isso é a lente de vies oposto

---
Redige o parágrafo do DBCV (só o ponto 1, o viés oposto) seguindo suas 4 peças na ordem que voce pos. Joga no papel errado e tudo, a gente lapida depois.

Ao contrário da silhueta o dbcv não penaliza algoritmos que produzem grupos com formas irregulares.

Por causa da distância ajustada é possível ter informação de quão densa é a região dos pontos.

A distância ajustada é o elo entre os pontos na cadeia.

O DBCV premia regiões densas.

Por isso é a lente de viés oposto.

---
Por que julgar por densidade faz a forma deixar de importar?

Ao contrário da silhueta o DBCV não penaliza algoritmos que produzem grupos com formas irregulares, pois julga por densidade, não por forma.

Os pontos são julgados como uma cadeia, a distância ajustada é o elo entre os pontos, por causa dela é possível ter informação de quão densa é a região dos pontos.

Por isso é a lente de viés oposto.
### Ponto 2
Por que o DBCV é calculado no espaço reduzido 10 dim e não no espaço 384 dim onde a silhueta mora?

O que acontece com a densidade lá em 384?

O DBCV é calculado no espaço reduzido de 10 dimensões porque é onde é caracterizado a densidade, em 384 dimensões as distâncias entre os pontos ficam parecidas, dificultando a diferenciação entre densidade.

---
qual é a condição (pontos x dimensões)? E onde caem os nossos números - 54 arquivos contra 384 (e contra 10) dimensões?

Existe uma condição do agrupamento por densidade que diz que o número de pontos deve ser bem maior, do que o número de dimensões para operar num regime confortável, ou seja, de forma que seja possível discriminar as distâncias entre os pontos.

Nosso corpus tem 54 arquivos, 54 << 384, mas 54 > 10.

n > d não é o ideal, mas é o mínimo para conseguir discriminar as distâncias.

---
silhueta mora em 384 dim significado
dbcv mora em 10 dim agrupamento
os dois ja tem viéses opostos

> com as duas métricas medindo em espaços diferentes e com viéses opostos - dá pra botar as notas lado a lado e dizer "O DBCV deu 0,29 e a silhueta 0,11, logo... Por quê sim ou não? E o que isso faz das duas: Uma comparação controlada, ou outra coisa?"

Não é possível comparar as duas métricas lado a lado e concluir alguma coisa com base na diferença entre elas. Essas duas métricas medem coisas diferentes, em espaços diferentes.
Não caracteriza uma comparação controlada, não tem como comparar.

---
> se elas não são um cara-a-cara, o que elas são? e essa independencia (espaço diferente + viés oposto) é um defeito da sua avaliação, ou é exatamente um ponto de ter um 2a lente? (volta lá: por que você construiu o DBCV)

Elas são independentes, essa independência é intencional, pois o algoritmo escolhido como padrao por decisão de design estava sendo penalizado com a silhueta, pois ela mede bons grupos de maneira globular, enquanto o HDBSCAN pode formar grupos com formas irregulares, um "U" por exemplo.

---

> entao voce adicionou uma metrica porque seu algoritmo favorito ia mal na primeira? isso nao e vies de confirmacao - criar uma lente que salva seu padrao?

1. este relatorio nao tem a pretensao de concluir qual e o melhor algoritmo. se o dbcv existe para des-penalizar o hdbscan, voce esta defendendo um favorito - o oposto da p2
2. sua leitura assimetrica (ponto 3, que voce vi escrever a seguiri): o hdbscan indo bem no dbcv nao prova nada, se o dbcv existisse pra vindicar o hdbscan, por que voce descartaria as boas notas dele? nao bate
centra na metrica: uma unica lente enviesada nao descreve com justica algoritmo nenhum.
a 2s lente, de vies oposto, evitque um unico vies mande na descricao.

> rearticula o porque da independencia - montem o independente/intencional/globular vs U, mas troca o padrao estava penalizado por um motivo que nao coroe ninguem.

As métricas são independentes intencionalmente, a silhueta mede bons grupos de maneira globular, o dbcv mede por densidade, ou seja, o viés oposto para avaliar grupos com formas irregulares como um "U".

---
estruturar
- o dbcv é calculado no espaço reduzido 10 dim e não em 384 dim
- por que densidade precisa de n > d: 54 << 384 degenera, 54 > 10 opera (n > d é o mínimo, não o ideal)
- a silhueta vivem em 384, o dbcv em 10 -> espaços diferentes
- logo são lentes independentes (intencional), nao comparação controlada - nao da pra ler a diferença entre as notas.

3 - 1 - 2- 4

A silhueta vive em 384 dim, o DBCV em 10 -> espaços diferentes.
O dbcv é calculado no espaço reduzido 10 dim e não em 384 dim
por que densidade precisa de n > d: 54 << 384 degenera, 54 > 10 opera (n > d é o mínimo não o ideal)
logo são lentes independentes (intencional, não comparação controlada) não da pra ler a diferença entre as notas.

---
Espaços diferentes
Justifica dbcv em 10 d
logo, lentes independentes

---
A silhueta é calculada no espaço orignal de significado de 384 dimensões, enquanto o DBCV é calculado no espaço reduzido de 10 dimensões, por que existe uma condição do agrupamento por densidade que diz que o número de pontos deve ser bem maior, do que o número de dimensões para operar num regime confortável, ou seja, de forma que seja possível discriminar as distâncias entre os pontos. o corpus analisado tem 54 pontos, 54 << 384, mas 54 > 10, não é o ideal, mas é o mínimo para operar.
Portanto as métricas são independentes intencionalmente, o que não caracteriza uma comparação controlada, pois não da pra ler as duas lentes lado a lado.

---
A silhueta é calculada no espaço original de significado de 384 dimensões; o DBCV no espaço reduzido de 10 dimensões, devido uma condição do agrupamento por densidade a qual diz que o número de pontos deve ser bem maior do que o número de dimensões para operar num regime  que seja possível discriminar as distâncias entre os pontos.
Portando as métricas são independentes intencionalmente, o que não caracteriza uma comparação controlada, pois não é possível compará-las lado a lado.
O corpus analisado tem 54 pontos, o que é muito menor que as 384 dimensões do espaço original, mas ainda é maior que as 10 dimensões reduzidas. Não é o ideal, mas é o mínimo para operar.

---
A silhueta é calculada no espaço original de 384 dimensões;

o DBCV no espaço reduzido de 10 dimensões, devido uma condição do agrupamento por densidade a qual diz que número de pontos deve ser muito maior do que o número de dimensões para que seja possível discriminar as distâncias entre os pontos de forma confortável.

O corpus analisado tem 54 pontos, número muito **menor** que as 384 do espaço original, mas ainda **maior** que as 10 dimensões reduzida. Não é o ideal, mas é o mínimo para operar.

Logo, por estarem em espaços diferentes e com viéses opostos, as métricas são independentes intencionalmente, o que não carateriza uma comparação controlada, pois não é possível compará-las lado a lado.

###  Ponto 3
Leitura assimétrica - último parágrafo
espaço reduzido é a casa do HDBSCAN
hdbscan indo mal é sinal forte
regra de leitura

### pensar
Se um time ganha em casa, ele provou que é melhor?
E se ele perde em casa?
Agora mapeia pro HDBSCAN: quando a nota do dbcv dele te diz alguma coisa, e quando não diz nada?

O DBCV é a métrica que se encaixa no HDBSCAN, logo ele ir bem não é uma surpresa, não diz nada, Grande sinal é se ele for mal.

---
a)
O DBCV se encaixa no HDBSCAN por que ele mede por densidade, ao contrário da silhueta que tende a favorecer grupos globulares..

b)
Os outros algoritmos que não são baseados em densidade são penalizados. exemplo do k-means, não se encontra os grupos naturais, os grupos são forçados pelo k definido.
mas isso não conta contra o k-means, por que ele não é um algoritmo de densidade.

---
2a razao - espaço de 10 dimensoes.

O DBCV se encaixa no HDBSCAN pois ele mede por densidade no espaço reduzido, ao contrário contrário da silhueta que tende a favorecer grupos globulares e é medida no espaço original.
O espaço reduzido é otimizado para algoritmos de densidade, pois em alta dimensão não é possível discriminar as distâncias entre os pontos e determinar densidade.

---
O que o UMAP faz quando constrói os 10 eixos - que estrutura ele preserva?

### estruturar

casa + leitura assimetrica
- casa
- assimetria
- outro lado

### Rascunho feio
O DBCV é onde habita algoritmos como HDBSCAN pois mede a densidade no espaço reduzido. Os demais algoritmos não são otimizados para essa métrica, no entanto nota baixa do k-means/aglomerativo não conta contra eles.
Pois, mesmo que o HBDSCAN pontue alto, isso não quer dizer, pois é o esperado; ele ir mal aqui é um grande achado. 

### Revisar

O DBCV é onde habita algoritmos como HDBSCAN pois mede a densidade no espaço reduzido com a vizinhança preservada pelo UMAP. 

Os demais algoritmos não são otimizados para essa métrica, no entanto nota baixa do k-means/aglomerativo não conta contra eles.

O HDBSCAN pontuando alto nessa métrica não diz nada, pois é o esperado; por outro lado, ele ir mal aqui é um grande achado.

## Sensibilidade do redutor
a) procedencia
b) responde ao knob != otimo
c) sem coluna dbcv (espaço muda por linha)

### pensar
por que o redutor entra no relatório? O que essa tabela de n_components está provando - e o que ela explicitamente não está provando? puxa o que você já defende sobre o 10 ser arbitrário.

A sensibilidade do redutor entra no relatório para por a prova o número 10 escolhido como padrão arbitrário. [nao sei dizer o que ela esta provando ou nao]

---
nao da pra cravar que o 10 é otimo != nao da pra defender

> essa varredura 5/10/15/20 tenta provar que 10 é o melhor valor?
> se nao é isso - o que ela mostra de mais honesto?
> (a tabela diz o que sobre a ferramenta, se não te diz qual valor é ótimo?)

A varredura não tenta provar que o 10 é o melhor valor (nem nenhum outro valor), pelo contrário a tabela tem a finalidade de dizer se a ferramenta responde com a variação do knob [nao sei se esse termo é o correto para um relatório, podemos manter, mas seria bom colocarmos sinonimos, ou uma breve explicacao]

---
essa tabela do redutor nao tem coluna dbcv (so silhueta). as matrizes por algoritmo la em cima tem. por que aqui nao da? callback do ponto 2 - dbcv e espaço.

formalmente essa é uma area que na minha mente ainda nao esta clara o por que aqui nao tem essa metrica. O que meu INSTINTO diz é que tem algo relacionado com o espaço reduzido que calculamos o dbcv nas outras metricas. 
A silhueta orignal é calculada sobre o espaço original, logo temos uma base para comparar a variação. aqui me complica, nao sei explicar o dbcv propriamente, eu sei que ele é calculado no espaço reduzido mas me falta o entendimento;  

---
o que é o n_components?
ele controla a dimensão do espaço reduzido.
entao, nessa tabela, cada linha tem um espaço reduzido de tamanho diferente.
a linha do 5 vive num espaço de 5 dimensoes, a do 10 em 10, a do 15 em 15 a do 20 em 20.
E o DBCV vive no espaço reduzido.

> entao dá pra comparar o DBCV da linha de 5 dimensões com o da linha de 20 dimensões? Nao, mas eu nao sei explicar o por que
> é o mesmo espaço, ou espaços diferentes? sao espaços diferentes
> e por isso, faz sentido ter uma coluna DBCV para ler de cima a baixo aqui  Nao, mas eu nao sei explicar o por que, nao tenho visualizado ainda em minha mente a razao

---
quanto maior a dimensao mais dificil discriminar densidade
54 p em 5 dim, folgadíssimo
em 20 dim começa a apertar
em 384 degenera para ~0

agora imagina concretamente o DBCV da linha 20dim sai menor que o da linha de 5min.
duas explicacoes possiveis

a) o agrupamento em 20 dim é de fato pior ou
b) 20 dim é so um espaço mais hostil para densidade (aquela contraçao do ponto 2 puxa para 0), então ate um agrupamento igualzinho pontuaria menor.

> olhando so a coluna dbcv, voce consegue saber qual das duas causou a queda?
> Nao sei.
> se nao da pra separar - por que colocar uma coluna que mistura as duas coisas?
> nao faz sentido mesmo.

e fecho, contrastando: a silhueta está sempre em 384 - o espaço nunca muda entre as linhas, então só o agrupamento varia -> da pra ler de cima a baixo. de boca: 

> Por que o dbcv nao tem esse luxo aqui? por que o dbcv nao é calculado sobre o espaço original, é calculado no espaço reduzido, em alta dimensão é impossivel discriminar as distancias entre os pontos.

---
o que o n_components faz aqui que nao faz nas matrizes? 
ele varia
e é por isso que cada linha cai num espaco diferente
### estruturar
procedencia
	padrao arbitrario
	 tabela o poe a prova
descritivo
	n_c varia -> dimensao diferente por linha -> dbcv espaco diferente por linha -> incomparavel -> silhueta sempre 384 
sem coluna dbcv
	nao prova valor otimo
	 responde ao hp

---
### Rascunho feio

O `n_components=10` foi o padrão arbitrário escolhido, esta tabela é o teste que o poe a prova; mas variar muda o espaço a cada linha, o que torna incomparável para a métrica DBCV, o qual é calculado no espaço reduzido, por isso ela fica de fora dessa comparação. Comparamos somente a silhueta pois ela é calculada no espaço original de 384. 
A tabela tem função descritiva, não tem a finalidade de provar algum valor como ótimo, somente descrever se/como a ferramenta responde a variação do hiperparametro.

### Revisar

alvo a peça c embolou e o por isso montou na causa errada

O `n_components=10` foi o padrão arbitrário escolhido, esta tabela é o teste que o põe a prova; 

mas variar o n_components muda o espaço a cada linha, por isso o DBCV, que é calculado no espaço reduzido,  fica de fora dessa comparação.

Comparamos somente a silhueta pois ela é calculada no espaço original de 384. 

A tabela tem função descritiva, não tem a finalidade de provar algum valor como ótimo, somente descrever se/como a ferramenta responde a variação do hiperparâmetro.
## Reconciliar limitações

1. dos próximos passos antigos, o que ja foi feito e não é mais proximo passo?
Ja foi feito a avaliação da segunda metrica de vies oposto, o dbcv.
2. sobre o passo 5 adiado - por que voce decidiu nao escrever um roteiro especifico de proximos passos, agora, o que voce falaria no lugar disso?
nao escrevi pois os proximos passos sao o feedback da orientadora apos a revisao deste relatorio.
---
1. eu quero tirar sem comentario, a orientadora nunca esteve ciente dessa comparacao controlada.
2. a minha ideia é nao colocar proximos passos por que isso nao depende de mim, mas tambem nao quero colocar que depende da orientadora, acho que isso nao cabe nesse relatorio, o relatorio é auto contido, nao é algo que vai para tese de forma crua. o proposito dele é apenas relatar o que eu estou fazendo durante as semanas.
---
nessa segunda passada foi finalizada o estudo da segunda metrica, de vies oposto, por densidade o dbcv.

Não existe métrica neutra, por isso, nesta segunda passada foi finalizado o estudo da segunda métrica de viés oposto, o DBCV.