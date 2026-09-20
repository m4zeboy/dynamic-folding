## Se um bom grupo é um fio denso de qualquer formato, o que uma métrica justa teria que medir - no lugar de compacidade?

compacidade = quao proximos os pontos estão uns dos outros. presume um centro esferico.

uma metrica justa não presume um centro esferico. teria que medir com base no numero minimo de pontos a ser considerado um grupo (regiao densa) e se o algoritmo foi capaz de caracterizar esses pontos ou mapeou muitos como ruído. ter muitos como ruído na minha cabeça indica que o agrupamento não foi bom. [mas ai teria que levar em conta a distancia entre dois pontos. exemplo o pontos a-b tem distancia 2 mas os pontos b-c tem distancia 8, isso nao devia ser levado em conta também?] 
## Como você mediria se dois grupos estão de fato separados, e não colados um no outro?

Eu mediria pelo espaço entre eles. se tiver pouco espaço dificulta saber se são dois grupos separados. [uma duvida, aqui teriamos que ter um limiar para decidir se separa ou não? ]
## Em que tipo de dados as duas métricas concordariam? nota alta nas duas
grupos compactos com a distancia media de dentro é baixa junto com esparsidade baixa e alta separação

## pro DBCV, você **excluiria** o `Outros` (igual à silhueta), ou **alimentaria como ruído `-1`**? E — chute — o que você acha que muda **no número** em cada caso?
Não excluiria, a métrica foi feita para isso. meu chute é que excluir o ruído criaria um resultado bom mas falso, pois desconsiderou exatamente a fraqueza do agrupamento

DBCV = qualidade da geometria dos grupos que se formaram
cobertura (n pontuados / n total n outliers) = descritor estrutural separado
reportar os dois lado a lado, sempre = isso que impede "bom mas falso" de se esconder

## DBCV 
Density based clustering validation (dbcv) é uma métrica de machine learning usada para avaliar a qualidade de agrupamentos em algoritmos de clusterização baseados em densidade (como DBSCAN, OPTICS e HDBSCAN).
O DBCV é especialmente útil em comparação a métricas tradicionais, como o Silhouette score, porque consegue lidar com clusters de formatos arbitrários, côncavos ou aninhados.
### Como funciona
o algoritmo calcula o DBCV avaliando dois componentes principais baseados na distância de alcance de alcançabilidade mútua (mutual reachability distance) e árvores geradoras mínimas.
- densidade interna do cluster: mede o quão compacto e densos são os pontos dentro de um mesmo cluster.
- densidade entre clusters: mede o quão separados e isolados estão os clusters uns dos outros.
### Pontuação e valores
O índice varia entre -1 e 1.
- próximo de 1: indica que os clusters são muito densos e bem separados.
- próximo de -1: indica que os clusters se sobrepõem ou não são bem definidos pela densidade.