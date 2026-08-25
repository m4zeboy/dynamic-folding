Meu objetivo é desenvolver uma ferramenta que ajude as pessoas a organizarem seus arquivos digitais.
A ideia é a pessoa abrir a pasta, clicar com o botão direito e aparecer um menu de contexto "Dynamic Folding", quando ela clica o sistema começa a processar a pasta atual e no final propõe uma estrutura de organização baseada no relacionamento semântico dos arquivos.

O sistema deve ser simples, tanto no codigo, quanto na usabilidade. Não deve inserir complexidade desnecessária.

O sistema deve ser modular, cada módulo não deve interferir no funcionamento de outro módulo. Eles devem ser independentes, a comunicação entre eles deve ser feita por contratos, pre-definidos.

O sistema deve ser extensível, adicionar novas funcionalidades deve ser um processo simples e coeso, utilizando estrategias como strategy e registry.

O sistema deve ser configurável, preciso mudar o comportamento de alguma coisa? mudo a configuração especifica dessa funcionalidade.


Eu pensei no seguinte pipeline em alto nível:

1. File Scanner
2. Extractor Layer
3. Pre Processor
4. Embedding Engine
5. Clustering Engine
7. Folder Namer
8. Structure Proposer


A execução dos movimentos de uma pasta para outra não entra nessa etapa inicial, esse é o pipeline da intêligencia.

1. File Scanner.
Essa camada é responsavel por iniciar a execução do programa. O programa deve ser agnostico a UI, inicialmente vamos ter somente o terminal como interface, futuramente vamos implementar uma UI nativa do sistema operacional.

Ele deve ter a seguinte interface: dynamic-folding run <caminho do diretório>

O que essa etapa tem que fazer: Percorrer todos os arquivos e subpastas, limitado até 2 subníveis. <Pasta raiz / sub nível 1/ sub nível 2>

Cada arquivo será transformado em uma representação para que o sistema consiga processá-lo.

2. Extractor Layer
Essa camada tem a responsabilidade de extrair informações relevantes dos arquivs/subpastas. Esse sistema tem a ambição de analisar tanto metadados como o conteúdo. Vamos focar somente nos metadados, mas futuramente o sistema vai ser capaz de analizar o conteúdo. Por isso que entra a capacidade de ser extensível, cada tipo de arquivo tem sua particularidade, sua forma de ser processado. Arquivos de textos são simples, imagens exigem outra abordagem, arquivos de código outra, audio também e assim por diante. A ideia é que o sistema tenha uma classe abstratra com metodos definis e cada variante implemente sua particularidade, em seguida registramos essa nova estrategia em um catalogo que a disponibiliza para o sistema usar.

3. Preprocessor
Essa camada é responsável por tratar os os dados recebidos, inicialmente os metadados mas futuramente o conteúdo também. Arquivos grandes terão que ter tratamento diferente. Pensei em quebrar o conteudo em pequenos pedacos que se sobrepoem (chunks) e aplicar o mean pooling, ou o TF-IDF como segunda opção, mas isso deve ser pensado melhor depois.

Os metadados que nos interessam são: nome do arquivo, data de criação, data de modificação, caminho, tamanho, autor, tags. Tudo isso vai ser insumo para a proxima etapa.

4. Embedding Engine
essa etapa é responsavel por criar as representações vetoriais dos arquivos, um embedding. Minha ideia é usar um modelo o SBERT, que lide bem com documentos. Não sei se podemos usar outro para somente os metadados, isso é algo a se pensar. mas, denovo, se reforça o principio de modularidade, trocar o modelo deve ser uma operção simples e configurável. Essa etapa tambem deve guardar um cache do embedding de cada arquivo, pode ser um SQLite simples, para que na proxima execução, o tempo de processamento seja muito menor, dado que o embedding ja foi processado, é só usar o cache.

5. Clustering Engine
Essa camada tem a função de submeter o conjunto de dados vetorizados em algum algoritmo de agrupamento. Aqui se faz necessario, novamente a modularidade, deve ser uma experiencia sem atrito mudar o algoritmo de agrupamento. Idealmente, mudar um parametro apenas. A objetivo é comparar varios tipos de algoritmos para avaliar qual se sai melhor nessa atividade. K-means, aglomerativo, dbscan, hdscan etc... Essa camanda produz como saida os grupos.

6. Folder Namer
Essa camada tem função de dar nomes semanticos, aderentes ao contexto e significativos aos grupos gerados na camada anterior com base nos arquivos.
O objetivo é usar um modelo de LLM local para fazer essa nomeação. Passar um bom prompt, descrevendo a função, como os nomes devem ser, como os nomes não devem ser, e os arquivos mais significativos de cada grupo (3-5 arquivos, isso pode ser configurável para que possamos testar).
Caso aconteca algum problema com o LLM, o sistema deve ter o TF-IDF como fallback para essa atividade tambem.

7. Structure Proposer & Renderer
Essa camada tem a responsabilidade de mostrar o resultado obtido para o usuário. Futuramente vamos implementar a execução da proposta, para agora o sistema deve mostrar o antes e o depois.


Para o desenvolvimento, o objetivo é utilizar tres agentes de IA no opencode.

Um arquiteto, especialista em ML.

Um desenvolvedor Senior, especialista em Python.

E um testador.

O arquiteto tem a função de desenhar a estrutura, fazer o plano, segmentar em milestones/sprints e tarefas e detalhamento. O arquiteto faz a SPEC.
Em deve ser feito o contrato do que vai ser testado.
Depois realiza-se o teste, o teste falha ai o desenvolvedor implemente e o testador testa novamente. (TDD)


Quando abrir uma nova sessão/conversa, comece colando:
   - “Leia docs/SPEC.md, docs/CONTRACTS.md, docs/ADR/* e docs/TEST_PLAN.md e continue do último milestone”
