e se eu gerar essa figura de novo daqui a um mês, pra versão final? qual dos dois motivos cobre isso?

se eu gerar daqui a um mes a figura precisa ser a mesma (deterministica) 

essa figura mostra os dados como eles são, ou já embelezados?
a figura tem que mostrar os dados como eles sao [talvez essa figura nao faca tanto sentido, talvez podemos ilustrar os grupos produzidos de outra forma, que nao seja no espaço vetorial, já que é reproduzir esse espaço não é uma tarefa trivial muito menos precisa]

se a métrica de densidade (dbcv) quebra em 384 dim, o que acontece com o algoritmo de densidade (HDBSCAN) tentando achar grupos nesse mesmo espaço?

o algoritmo também quebra, todos os pontos ficam isolados? [na minha cabeça antes dessa sua explicação a redução era necessária por que em alta dimensao os pontos ficariam muito proximos uns dos outros, mas isso era só um achismo, nunca parei para pensar sobre]

*o problema não é os pontos ficarem próximos. É TODAS AS DISTÂNCIAS FICAREM PARECIDAS ENTRE SI - todo ponto a mais ou menos a mesma distância de todo outro. "Perto" e "longe" deixam de se distinguir*

*Isso mata o HDBSCAN: ele acha grupo procurando onde os pontos se aglomeram mais que o resto - denso vs esparso, um contraste. Se toda distância é parecida, não existe "mais denso aqui que ali" -> não há contraste -> não há grupo para achar. Ele fica sem medir.*

REFORMULAÇÃO

O algoritmo não encontra os grupos, pois todos os pontos ficam com as mesmas distâncias entre si, logo não forma-se regiões densas. 

COMO ESPREMER DE 384 PARA 10 PRESERVANDO QUEM ESTÁ PERTO DE QUEM?
sim, e por que reduzimos para 10? e se a compação ê n << d por que esse número é o 10 fixo? por que ele não varia conforme o tamanho do dataset?

Se a banca perguntar "por que 10"?
Não tenho justificativa, foi uma decisão arbitrária da IA no desenvolvimento dessa funcionalidade, não posso responder isso pra banca.

*Não sei justificar 10 como ótimo*.

O sistema foi pensado para ser executado em uma pasta de 100~200 arquivos, escolhi reduzir para 10 dimensoes como padrao pois é um numero consideravelmente menor que o numero maximo de pontos que o sistema foi pensado para lidar, para que tenhamos mais pontos do que dimensoes (o espaco de embeddingso original tem 384 dimensoes). colocamos o n_componentes a prova numa analise de sensibilidade para ver se a ferramenta responde ao ajuste do hiperparametro (5~20)

valor 10 = padrão herdado da literatura [é correto eu dizer isso?]
propriedade = n (numero de arquivos/pontos) > dimensoes
10 exato = sensibilidade
ressalva = n pequeno (54)

O valor 10 para o número de dimensões reduzidas foi escolhido arbitrariamente por um padrão herdado da literatura [é correto eu dizer isso?]. Existe uma propriedade que diz que o número de pontos a serem analisados precisa ser maior do que o número de dimensões para evitar a maldição da dimensionalidade. [ficou feio essa parte]. O número 10 é posto a prova em uma análise de sensibilidade para ver como a ferramenta responde com pequenas variações nesse hiper parametro. uma pequena ressalva que o dataset analisado apresenta um n analisado menor do que o máximo previsto 54 < 200, no entanto se encaixa na propriedade n > d.

---
1. Padrão arbitrário sem justificativa formal.
2. É um aspecto da maldição da dimensionalidade. Para distância e densidade voltarem a discriminar, o número de pontos precisa superar o número de dimensões; o regime confortável é n >> d, e o mínimo para escapar do pior é n > d.
3. Uma pequena ressalva que o dataset analisado apresenta um n modesto em relação ao regime confortável.

O valor 10 para o número de dimensões reduzidas foi escolhido arbitrariamente sem justificativa formal. Para a distância e densidade voltarem a discriminar, o número de pontos precisa superar o número de dimensões; o regime confortável é n >> d, e o mínimo é n > d. O número 10 é posto a prova em uma análise de sensibilidade para ver como a ferramenta responde com pequenas variações nesse hiperparâmetro. Cabe ressalvar que o dataset analisado apresenta um n modesto em relação ao regime confortável.

arbitrario
mas satisfaz propriedade
e eu não afirmei que 10 é otimo
posto a prova (sens 5-20)
ressalva.


O valor 10 para o número de dimensões foi escolhido arbitrariamente sem justificativa formal, mas satisfaz a propriedade de que para a distância e densidade voltarem a discriminar, o número de pontos precisa superar o número de dimensões; o regime confortável é `n >> d`, e o mínimo é `n > d`. 
O número 10 é posto à prova na análise de sensibilidade com o objetivo de descrever como a ferramenta responde à variação desse hiperparâmetro.
Cabe ressalvar que o dataset analisado apresenta um n modesto em relação ao regime confortável.