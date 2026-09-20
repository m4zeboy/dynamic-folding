o que + fronteira + porque [um pequeno comentario, eu nao entendo o que esse fronteira significa]

a etapa anterior te entrega
a) a atribuicao arquivo -> grupo com identificadores numericos e 
b) a arvore de ligacao ainda nao cortada;
a nomeacao entrega c) os nomes dos grupos

o que a construcao da proposta faz com isso?
a construcao da proposta monta a estrutura (arvore) hierarquica de pastas. 
qual a entrada?
no meu entendimento atual a entrada é uma lista plana com as atribuicoes dos arquivos->grupos.
qual a saida?
a saida é a estrutura de arvore hierarquica cortada (se for o caso) e ja montada com todos os subniveis nos seus devidos lugares.
e por que ela existe como etapa propria?
ela existe pois as outras etapas so entrega a atribuicao dos arquivos -> grupos e o nome dos grupos, mas entregam isso de forma linear.
o que ela entrega que o agrupamento e a nomeacao, sozinhos, nao entregam?
ela entrega a arvore de diretorios.
[repeti muitas coisas muitas vezes, nao sei se faltou alguma coisa]

---
Fronteira é a linha que separa esta etapa das vizinhas: O que entra (aquilo que a etapa anterior ja resolveu e passou pronto), o que sai, e o que é responsabilidade desta etapa e nao da anterior nem da seguinte.
A banca ataca justamente as fronteiras: "Por que isso é feito aqui e nao no agrupamento?"

Saber a fronteira é saber dizer, com precisão, "até aqui é agrupamento; a partir daqui é construção."


das tres coisas que a etapa recebe (a,b,c), voce usou so uma na entrada.
qual delas carrega a informacao dos niveis?
e o que a construcao faz com ela para virar pasta e subpasta?

*a arvore de ligacao carrega a informacao dos niveis.
a construcao usa essa informacao para montar as pastas/subpastas
*

---
que palavra é essa - a operacao que a construcao faz sobre a arvore de ligacao?
e com suas palavras: o que muda no resultado, nas pastas, quando essa operacao é feita mais alto ou mais baixo na arvore?

a palavra é o corte na arvore.
vou responder na intuicao do que eu tenho de memoria. eu intuo que a hierarquia muda de acordo com o corte na arvore. pra ser honesto eu nao tenho esse mecanismo em detalhes no meu entendimento, eu nao consigo descrever o que muda, ou como funciona, so sei que a hierarquia muda com o corte na arvore.

---

## arvore de ligacao
a arvore de ligacao é um dendograma
embaixo, cada folha é um arquivo.
subindo, a arvore une primeiro os arquivos mais proximos, 
depois grupos de grupos,
ate no topo tudo estar junto.
a altura de cada juncao = o quao distantes estavam as coisas que se uniram ali
(juncao baixao = bem parecidos; juncao alta = so se juntaram no desespero)

cortar = passar uma linha horizontal numa altura.
tudo o que ja esta unido abaixo da linha vira um grupo.

- corte alto (perto da raiz) = a linha cruza poucos ramos
  poucos grupos -> grandes
- corte baixo (perto das folhas) -> cruza muitos ramos,
  mais subpastas

o que a construcao recebe (nao esquece o item que voce tinha deixado de fora antes);
a etapa da construcao recebe uma lista com as atribuicoes dos arquivos e dos grupos, a arvore de ligacao e os nomes dos grupos.

o que ela faz com a arvore de ligacao;
esta etapa corta a arvore de ligacao [como ela sabe onde cortar a arvore?]

o que muda quando o corte é mais alto ou mais baixo;
se o corte é mais alto (perto da raiz) menos grupos sao caracterizados (grupos grandes), se o corte é mais proximo as forlhas, mais grupos/subgrupos sao caracterizados.

---

como ela sabe onde cortar?
*a altura do corte não é um número cravado no código.
O sistema olha as distâncias entre as junções da árvore,
considera os cortes possíveis e escolhe automaticamente o 
que separa melhor os grupos 
e o critério muda com o algoritmo 
(no HDBSCAN, as regiões mais densas/estáveis;
no agglomerative, a altura que deixa mais arquivos
em grupos de tamanho válido).
O detalhe fino desse critério é assunto de apêndice;
no corpo do capítulo, basta você afirmar que a altura é decidida automaticamente,
a partir da própria estrutura da árvore.*

*até onde descer
a profundidade, quantos níveis de pasta
aí sim há um teto definido pelo projeto.
é a peça que você já tinha tocado na linha 84: 
"não sabemos quantos níveis... é responsabilidade da proposta.
Agora ela encaixa: a altura de cada corte é automática; 
o número máximo de níveis é uma escolha de projeto.*

os arquivos que o agrupamento marcou como ruído 
(não entraram em nenhum grupo) 
o que a construção faz com eles na proposta.

A etapa de construção move para a pasta `Outros` todos arquivos marcados como ruído pelo agrupamento.

---

1. proposito - o que a etapa monta (a arvore de diretórios da proposta)
   O propósito dessa etapa é montar [ou construir, nao sei qual fica mais correto] a árvore de pastas [nao sei qual termo usei como padrao se diretorios ou pastas, mas vamos usar um só em toda tese].
2. entrada - os três itens (atribuições arquivo -> grupo, arvore de ligação não cortada, nomes)
   Essa etapa recebe da etapa anterior as atribuições de arquivos e grupos, a árvore de ligação não cortada e os nomes dos grupos.
3. mecanismo - corta a árvore de ligação para derivar os níveis, em vez de re-agrupar;
   A estrutura de subníveis é obtida pelo corte da árvore de ligação, e nao pelo re-agrupamento [nao sei se precisamos falar do re agrupamento aqui, parece que estamos querendo dar enfase que nao estamos usando essa estrategia, mas o leito nao tem conhecimento de todas as estrategias existente.]
4. o corte - a altura é decidida automaticamente pela estrutura da árvore; a profundidade tem um teto do projeto;
   Onde a árvore é cortada é decidida automaticamente pela estrutura da árvore, e o mecanismo de decisao desse limite varia com o algoritmo. O limite que a ferramenta define é em questão até onde descer em uma hierarquia na hora da leitura (o que vira conteudo analisado).
5. ruído - os arquivos sem grupos são *atribuídos* à pasta `Outros`
   Para cada arquivo que foi marcado como ruido, a etapa atribui para a pasta Outros.
6. saída - a árvore pronta para a renderização.
   Como resultado, a etapa devolve a árvore pronta para renderizacao
---
Onde a árvore é cortada é decidida automaticamente pela estrutura da árvore; o mecanismo de decisão varia com o algoritmo. 
O limite de profundidade da **proposta**, que define quantos níveis de pasta a árvore proposta terá é  um parâmetro configurável. 

propostito  + o que a etapa recebe;

corta a árvore para derivar os níveis + como/ate onde (altura automática, profundidade configurável)

ruído -> outros + a saída pronta para a renderização.

O propósito dessa etapa é juntar os resultados isolados das etapas anteriores em uma arvore de diretórios. Como entrada, essa etapa recebe as atribuições de arquivos e grupos, a árvore de ligação e os nomes dos grupos.
Para derivar a estrutura hierárquica, essa etapa realiza o corte na árvore de ligação. Onde a árvore é cortada é decidida automaticamente pela estrutura da árvore; o mecanismo de decisão varia com o algoritmo. 
Por outro lado a ferramenta tem um parâmetro configurável para o limite de profundidade da **proposta**, que define quantos níveis de pasta a árvore proposta terá.
Os arquivos que foram marcados como ruído pelo algoritmo de agrupamento são atribuídos para a pasta `Outros`que é posicionada no primeiro nível da hierarquia. Como resultado, a etapa devolve a árvore pronta para a renderização.

---
1. meta linguagem
   O proposito dessa etapa é juntar
   -> essa etapa tem a finalidade de reunir.
   escrita academica corta a camada "o proposito é"
   e vai ao verbo.
   bonus: alinha com a abertura do agrupamento (essa etapa tem a finalidade de caracterizar)
   capitulo inteiro abre igual.
2. regencia de atribuir
   atribuidos para a pasta -> atribuidos à pasta
   atribui-se algo a algo.
   guard essa - vai aparecer denovo.
3. consistencia de termo. 
   voce escreveu arvore proposta aqui 
   e arvore de diretorios na abertura
   um conceito, um nome: fixei a arvore (elipse de arvore de diretorios).
   o leitor nao pode ficar se perguntando se sao coisas diferentes
4. redundancia. parametro configuravel para o limite de profundidade
   que define quantos niveis.
   dizia profundidade tres vezes. 
   vriou aposto enxuto
   o limite de profundidade - quantos niveis de pasta a arvore tera - e configuravel


