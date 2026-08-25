# Limitações
### Estágio 1 - Pensar
1. O que é essa limitação?

> A ferramenta permite que o usuário escolha entre 3 algoritmos de agrupamento (todas as outras etapas são intercambiáveis, mas somente o agrupamento e talvez a redução UMAP principalmente merecem atenção para o estudo de machine learning, as outras etapas usam a melhor estratégia implementada até o momento como o padrão da ferramenta que é o que o usuário final vai usar).
> Cada algoritmo de agrupamento tem suas particularidades, o K-means tem o hiperparâmetro k, que diz quantos grupos o agrupamento deve produzir.
> O HDBSCAN tem o min_cluster_size, que é a quantidade minima de pontos que a densidade precisa ter para ser considerada um grupo.
> O material de teste é ínfimo, um corpus apenas com ~50 arquivos.
> Apenas uma métrica e ainda não se adequa a todos os algoritmos analisados, pois mede coisas diferentes.

2. E daí, por que importa?

>Essa limitação me impede de afirmar qual é a combinação de estratégia que performa melhor. 

3. Tem número por trás?

>As possibilidades são infinitas, rodei 30 vezes no máximo, isso é um chute tirando o aleatório, que êalgo que podemos falar mais sobre no ele no relatorio, a orientadora não tem ideia dele e por que ele está aqui.

4. Se o estudo **não** consegue dizer qual combinação performa melhor, isso **enfraquece a escolha do HDBSCAN como padrão da ferramenta**? Por quê — ou por que não?
Não enfraquece. O padrão da ferramenta é o HDBSCAN porque ele apresenta algumas caraterísticas interessantes que os outros algoritmos não apresentam.
- Tratamento de ruído: arquivos que o agrupamento não foi capaz de alocar em algum grupo são roteados para a pasta Outros, uma funcionalidade que passa a mensagem de honestidade para o usuário final. "esses arquivos não se adequam a nenhum desses grupos que gerei, acho que é melhor você revisar"
- O algoritmo inferir o melhor numero de grupos de forma emergente, com base na estrutura dos dados e não um k prefixado.
- Habilidade de inferir uma estrutura hierárquica de forma nativa sem a necessidade de processar um reagrupamento e consumir mais recursos desnecessários.
- A forma como ele representa os grupos como regiões densas [para mim faz mais sentido representar documentos assim ao invés de grupos esféricos, mas isso é um achismo, não tenho como provar isso com o conhecimento que eu tenho hoje]
### Estágio 3 - Rascunho feio
Este estudo não permite dizer qual combinação performa melhor por três razões: o estudo cobre uma fração ínfima em um espaço contínuo de combinações; utiliza um único corpus pequeno como material de avaliação que não cobre todos os tipos de arquivos nem todos os casos de uso, e calcula apenas uma métrica que não é imparcial entre os algoritmos, pois a noção de bons grupos não é compartilhada. No entanto, isso não fragiliza o HDBSCAN como padrão da ferramenta, pois sua escolha não se apoia nessa comparação, mas em decisões de projeto, como o tratamento de ruído, inferência automática do numero de grupos, e geração nativa de estrutura hierárquica.
# Próximos passos
os algoritmos sao medidos sobre arquivos diferentes
### Pensar
por quê os algoritmos acabam medidos sobre conjuntos de arquivos diferentes, e por que isso impere comparar os números da silhueta entre eles?
os algoritmos medem sobre arquivos diferentes por que criam estruturas diferentes, o hdbscan tem a estratégia de mapear arquivos como ruído, que são ignorados pela métrica, enquanto o k-means não possui essa funcionalidade, todos os arquivos são considerados. O crítério para formar grupos é diferente também, logo tanto o número de pastas pode variar como o conteúdo delas.
Isso impede de comparar a silhueta porque as estruturas geradas não são comparáveis, foram geradas seguindo critérios diferentes e sobre dados diferentes praticamente. [alguns pontos estão repetidos mas mantive por clareza mental de onde veio cada coisa]
### Rascunho feio
cobertura: ruído ignorado
arquivos diferentes
Não é possível comparar os números da silhueta entre os algoritmos pois ela ignora os arquivos marcados como ruído, e o k-means não marca ruído, logo cada algoritmo cobre dados diferentes.
## O que a silhueta mede
### Pensar
1. o que ela mede?
A silhueta mede o quão "bom" os grupos são, e como "bons grupos" ele usa duas medidas, *compactness* e *separation*. *Compactness* mede o quanto os dados dentro do grupo estão próximos uns dos outros, quanto mais compacto melhor. E *Separation* mede o quanto um ponto dentro de um grupo está separado de um ponto em outro grupo. Quanto mais separado melhor. 
2. o limite dela?
O limite dela é que pra ela o conceito de um bom grupo é uma esfera, com um centro onde os dados orbitam, o que na vida real é difícil de acontecer grupos tão perfeitos assim.
3. por que esse viés importa aqui?
O viés esférico importa por que esse relatório apenas descreve essa métrica e não cria um ranking de qual foi o algoritmo que mais pontuou e com base nisso conclui que ele é o melhor. Não. Essa métrica subestima algoritmos que produzem grupos irregulares, dando a eles notas menores e favorece aqueles que criam grupos esféricos.  
### Rascunho feio
A silhuete define um grupo como "bom" através de duas medidas, *Compacidade* e *Separação*.
A Compacidade mede a distância entre dois pontos dentro do grupo, quanto mais próximos  melhor. E a Separação mede a distância entre dois pontos de grupos diferentes. Quanto mais separados melhor. 
Entretanto, ela possui uma limitação, para ela o conceito de "bons grupos" é uma esfera, com um centro onde os dados orbitam, essa caracterização é uma idealização impraticável com dados reais. Esse viés esférico é importante pois subestima algoritmos que produzem grupos com formas irregulares e favorece os que criam grupos esféricos, por isso esse relatório não tem a pretensão de concluir qual é o "melhor" algoritmo com base na pontuação dessa métrica.
## Comparação estrutural
### Pensar
onde a comparação acontece?
A comparação acontece na estrutura resultante dos agrupamentos, quantos grupos foram gerados, caracterização de ruído e a cobertura da medição. O k-means não mapeia ruído, logo 100% de cobertura (todos os arquivos são agrupados e medidos). O HDBSCAN caracteriza ruído e move os move para a pasta Outros, estes não são cobertos pela medição, logo o HBDSCAN tem uma cobertura menor. O k-means precisa de um número fixo enquanto o HDBSCAN/Aglomerativo infere automaticamente esse número a partir dos dados. 
## Silhoueta por algoritmo
esses números não são comparáveis entre os algoritmos pois cada um representa uma cobertura diferente dos arquivos analisados, logo esses números devem ser tratados como uma descrição e não como um ranking.

o que é o piso aleatório?

o piso não roda algoritmo nenhum
ele pega o agrupamento real (os 9 do hdbscan, com os tamanhos que tem), embaralha quais arquivos caem em qual grupo, mantendo os tamanhos e mede a silhueta. repete 1000x e tira a média.
e se eu jogasse estes arquivos nestes mesmo grupos, mas no chute? (por isso o piso muda por algoritmo, cada um tem tamanhos diferentes)


O piso é pseudo aleatório com semente determinística. O piso pega o resultado de um agrupamento real (seus grupos e tamanho) e embaralha os arquivos nestes mesmo grupo, mas ao acaso, e mede a silhueta. faz isso mil vezes e por fim obtém a média.

o que ficar acima dele significa?

ficar acima do aleatório significa que o algoritmo performa melhor do que um agrupamento ao feito pelo acaso. 


o que não significa?

ficar acima não significa que os grupos são bons, ou que fazem sentido, ou que são úteis para o usuário final.


O piso têm característica pseudo aleatória com semente determinística. Obtém o resultado de um agrupamento real (seus grupos e tamanhos), embaralha os arquivos nestes mesmos grupos ao acaso, e mede a silhueta; repete-se mil vezes e por fim obtém-se a média. 
Ficar acima do piso significa que o algoritmo performa melhor do que um agrupamento feito ao acaso, no entanto não significa que os grupos são bons, ou úteis para o usuário final.

---
Esses números não são comparáveis entre os algoritmos pois cada um representa uma cobertura diferente dos arquivos analisados, logo devem ser tratados como uma descrição e não como um ranking. O piso tem característica pseudo aleatória com semente determinística. Obtém o resultado de um agrupamento real (seus grupos e tamanhos), embaralha os arquivos nesses mesmos grupos ao acaso, e mede a silhueta; repete-se mil vezes e por fim obtém-se a média. Ficar acima do piso significa que o algoritmo supera um agrupamento feito ao acaso, no entanto não significa que os grupos são bons ou úteis para o usuário final.

## Sensibilidade
Esse estudo submete os algoritmos à várias execuções variando seus hiperparâmetros. Para o HDBSCAN, varia o hiperparâmetro min_cluster_size, enquanto para o K-Means varia o K. O resultado desse estudo não permite concluir qual é a melhor variação pois, a silhueta reagir a variação, no caso do HDBSCAN, mostra que o algoritmo está mais exigente para caracterizar um grupo, em outras palavras, mais pontos densos são necessários, o que naturalmente reduz o número de grupos produzidos e aumenta a quantidade de pontos mal encaixados marcados como ruido, esses que puxariam a métrica para baixo ficam de fora da avaliação, como a silhueta só pontua sobre os pontos que não são ruídos, logo o resultado aumenta. O leitor deve ler as quatro colunas em conjunto, não apenas a silhueta de forma cega.