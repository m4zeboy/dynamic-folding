# Dynamic Folding

`dynamic-folding` é uma plataforma de pesquisa **offline, com foco em Windows**, criada para automatizar a organização semântica de pastas. Usa Machine Learning (SBERT, Clustering) para propor estruturas de diretórios lógicas para arquivos bagunçados (ex.: certificados, artigos, fotos).

## Principais funcionalidades

- **Descoberta semântica:** vai além do nome do arquivo, "lendo" texto de PDF, cabeçalhos estruturais de documentos Office (.docx, .pptx) e metadados EXIF de imagens.
- **Validação intrínseca:** toda proposta inclui um **Cohesion Score (Silhouette)** para quantificar a qualidade da organização.
- **Revisão interativa:** navegue, analise e aceite as estruturas propostas numa UI desktop nativa (pywebview).
- **100% offline:** usa modelos locais (SBERT) e LLMs locais (Ollama via loopback). Nenhum dado sai da sua máquina.

## Instalação (uv)

1. Clone o repositório. `git clone https://github.com/m4zeboy/TCC-Dynamic-Folding-v2.git`
2. Instale as dependências: `uv sync --all-extras`
3. Verifique a instalação: `uv run pytest`

A config default (`config/default.toml`) usa **embeddings SBERT locais** e
**naming via Ollama local**. Os dois são opcionais no sentido de que o
pipeline tem fallbacks graciosos (veja abaixo), mas os dois passos a seguir
são o que faz a config *default* funcionar de fábrica numa máquina limpa:

### Download do modelo SBERT 
A etapa de embedding precisa de um diretório de modelo local — ela nunca faz
download em tempo de execução do pipeline.
Baixe o modelo uma única vez:
```bash
uv run dynamic-folding setup-sbert
```
Este é o **único** comando do projeto que acessa a rede. Ele salva o modelo
em `%LOCALAPPDATA%/DynamicFolding/models/`, que o pipeline descobre
automaticamente — sem editar config nem variáveis de ambiente. Só pule esse
passo se for trocar `embedding.provider` para outro valor além de `sbert`
(ex.: o provider determinístico `fake`) na sua própria config.

### Ollama (opcional, para nomeação de pastas via LLM)
`naming.provider = "ollama"` é o valor default. Isso exige:
1. [Ollama](https://ollama.com) instalado e rodando (`ollama serve`).
2. O modelo default baixado: `ollama pull llama3.1:8b`.

Se o Ollama não estiver instalado, não estiver rodando, ou o modelo não
tiver sido baixado, a nomeação **cai automaticamente para TF-IDF** naquela
execução — o pipeline continua funcionando, só com nomes de pasta mais
simples (sem LLM). Ou seja, este passo pode ser pulado inteiramente se você só
quer experimentar a ferramenta; para pular deliberadamente (em vez de
depender do fallback), defina `naming.provider = "tfidf"` na sua config.

## Uso

### Experiência unificada 
Abre a aplicação interativa completa para navegar pastas, acompanhar o
pipeline de ML em tempo real e triar os resultados. 
```bash
uv run dynamic-folding       
```
- **Navegação:** clique nas pastas no explorador à esquerda para navegar pelo sistema de arquivos.
- **Seleção:** selecione uma pasta e clique em **Iniciar análise** para iniciar o pipeline de organização.
- **Triagem:** revise a estrutura proposta, depois clique em **Aplicar proposta** para aceitar ou **Recomeçar** para começar de novo.
- **Relatório:** ao aceitar, um relatório HTML autocontido é gerado (e aberto, quando `report.auto_open` está ativo). Veja a seção `[report]` em `config/default.toml`.

### Proposta rápida via CLI
Escaneia um diretório específico direto pela linha de comando:
```bash
uv run dynamic-folding run <dir> --interactive
```

### Métricas de qualidade (Silhouette + DBCV)
Compara os algoritmos de clustering no seu dataset e exporta as métricas:
```bash
uv run dynamic-folding compare <dir> --json metricas.json --csv metricas.csv
```
Gera um JSON (resultado completo) e/ou um CSV (uma linha por algoritmo) com os
scores de Silhouette e DBCV, sem precisar abrir o relatório HTML. `--html <path>`
continua disponível se preferir o relatório visual.

### Opções da CLI
- `--json`: retorna a proposta como um objeto JSON.
- `--print-config`: mostra a configuração efetiva (defaults e overrides mesclados).
- `--no-progress`: desativa a UI de progresso do Rich.

## Configuração

Edite `config/default.toml` para ajustar o pipeline:
- **Scanner:** `max_depth`, `ignore_globs`.
- **Extração:** `extractor.provider` (basic/type_aware), `snippet_size`.
- **Clustering:** `algorithm`, `min_cluster_size`.
- **Naming:** `provider` (tfidf/ollama), `model`.

---
*Desenvolvido como projeto de pesquisa para um TCC.*
