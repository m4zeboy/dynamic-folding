## etapa 1
1. o que a etapa de varredura faz quando o usuário aponta para um diretório?
é como se o sistema andasse pela pasta, arquivo por arquivo, pasta por pasta, para obter um mapa de como a pasta é.

2. como ela decide o que entra e o que fica de fora do corpus?
O sistema usa uma estrategia para registrar os tipos de arquivos suportados, se o arquivo analisado faz parte do registro ele entra, se nao é ignorado [meu medo é colocar informacao tecnica demais aqui.]

3. O que ele entrega para próxima etapa?
Ele entrega um mapa da pasta com alguns metadados basicos [estou com a ideia fria na mente, vou precisar de mais rodadas de revisao]

4. Por que a ordem em que ela le os aquivos importa tanto para o resto do sistema?
eu sei que ele performa a varredura usando uma travessia em arvore, nao sei qual ao certo, mas o porque é para manter a caracteristica de determinismo [vou precisar de mais revisao tambem]

---
A varredura não filtra por tipo de arquivo suportado ainda.
Ela pega tudo o que está na pasta,
exceto o que o usuário manda ignorar e arquivos que passam do limite de profundidade máxima.
O filtro de extratores suportados acontece na etapa seguinte (Leitura/Extração)

Ela entrega uma lista plana de referencias de arquivos,
cada uma contendo metadados básicos.

---
1. objetivo: O percurso inicial na pasta do usuário para mapear os arquivos.
2. controle de escopo: como a busca é controlada (profundidade máxima) e o que é deixado de fora.
3.  o produto gerado: que tipo de metadados básicos são coletados para cada arquivo.
4. garantia de reprodutibilidade: por que a ordenação alfabética é feita logo aqui.

Esta etapa realiza o percurso inicial na pasta do usuário para mapear os arquivos. O escopo da varredura é delimitado por uma profundidade máxima e padrões de exclusão [nao sei se padroes de exclusao vai ficar claro para o leitor] configuráveis.
Como resultado, a etapa produz uma lista plana de referência de arquivos, cada um contendo metadados básicos externos. [sei que aqui sao metadados compartilhados por todos os arquivos, e na leitura/extracao sao os metadados internos que variam de acordo com o tipo de arquivo, me ajuda a colocar essa informação.]
Para garantir a reprodutibilidade, os arquivos são lidos por uma busca em largura que devolve a lista ordenada alfabeticamente. [acho que aqui nao esta tao fluido]

---

O escopo da varredura é delimitado por uma profundidade máxima e por padrões de exclusão configuráveis, os quais permitem ignorar dependências e/ou cache por exemplo.

Como resultado, a etapa produz uma lista de referências de arquivos acompanhadas de seus metadados básicos comuns -- tais como data de criação e tamanho. Os metadados internos específicos de cada formato e o conteúdo serão tratados na próxima etapa.

Para garantir a reprodutibilidade, o percurso adota uma busca em largura com ordenação alfabética, uma vez que sistemas operacionais podem retornar a listagem de arquivos em ordem variável.

---
1. o que + fronteira: a etapa anterior (síntese da proposta) te entrega a estrutura pronta -- a arvore de grupos noemados, com a pasta outros definida. o que a renderizacao faz com isso?
   A etapa de renderização mostra em tela o resultado do processamento que o sistema fez.
2. qual e a entrada, qual e a saida? 
   Essa etapa recebe o artefato de dados da proposta e apresenta uma arvore de diretorios na UI e um relatorio HTML com essa proposta para o usuario revisar [realmente nao tem necessidade de duas saidas, nao sei por que fiz o html, parece que estou enchendo linguica, isso me preocupa]
3. e por que ela existe como etapa propria -- o que ela resolve que a sintese nao resolveria sozinha?
   ela tem a unica responsabilidade de mostrar. pegar o que foi construido e apresentar. a sintese monta a estrutura. essa etapa obtem a estrutura e apresenta.
4. a fronteira ao contrario. a renderizacao decide alguma coisa sobre a estrutura (o que agrupa, como corta, o que vira outros)?
   Essa etapa nao toma nenhuma decisao, 100% trabalho mecanico de apresentacao.
5. ou ela recebe tudo isso ja decidido?
   Ja recebe tudo decidido.
6. onde termina montar a proposta e comeca mostrar a proposta.
   O fim da etapa anterior termina o montar a proposta, essa etpa comeca mostrar proposta.
7. a forma de saida. voce disse que o que importa e a arvore de diretorios. mas o sistema tambem gera um relatorio html. sao duas saidas diferentes da mesma etapa, ou a arvore é o relatorio?
   a saida CONCEITUAL que importa é a arvore com as pastas, nomes e os arquivos, o que gira entorno disso é perfumaria.
8. e ponto importante pro seu projeto -- essa etapa move ou cria alguma pasta no disco? (pensa na regra de nao destrutividade do sistema)
   essa etapa somente apresenta (nao vou usar recomenda pois entraria no merito de algoritmos de recomendacao/ outro universo em IA), nenhuma pasta é criada, nenhum arquivo é movido.
---
