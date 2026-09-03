# Dynamic Folding

Ferramenta offline para propor uma organização semântica de arquivos em pastas. A interface permite selecionar uma pasta, revisar a proposta e gerar um relatório HTML.

## Requisitos

- Python 3.11 ou superior;
- [uv](https://docs.astral.sh/uv/);

## Instalação

No macOS, instale o [uv](https://docs.astral.sh/uv/getting-started/installation/) antes de continuar. Ter o Python instalado não instala o uv automaticamente.

```bash
git clone https://github.com/m4zeboy/dynamic-folding.git
cd dynamic-folding
uv sync --all-extras
```

Baixe uma única vez o modelo local usado para analisar os arquivos:

```bash
uv run dynamic-folding setup-sbert
```

O modelo é salvo em `%LOCALAPPDATA%/DynamicFolding/models/`. Esse é o único passo que acessa a rede; as análises são executadas localmente.

## Executar

Abra a interface gráfica:

```bash
uv run dynamic-folding
```

Ou abra a interface já com uma pasta selecionada:

```bash
uv run dynamic-folding run "C:\caminho\da\pasta" --interactive
```

Na interface, selecione a pasta, inicie a análise e revise a proposta. Ao aceitá-la, o programa gera um relatório HTML.

## Nomeação de pastas com Ollama (opcional)

Por padrão, o programa tenta usar o Ollama local para sugerir nomes de pastas. Para habilitá-lo, instale o [Ollama](https://ollama.com) e execute:

```bash
ollama pull llama3.1:8b
```

Se o Ollama não estiver disponível, o programa continua funcionando com nomes gerados por TF-IDF. Para usar somente esse modo, altere `naming.provider` para `"tfidf"` em `config/default.toml`.

## Avaliação

Além da interface interativa, a ferramenta tem dois comandos para avaliar a qualidade de uma proposta sobre um corpus qualquer, sem precisar abrir o relatório HTML.

### Avaliação interna (Silhouette + DBCV)

Não exige nada além do próprio corpus: compara os algoritmos de clustering disponíveis e exporta as métricas.

```bash
uv run dynamic-folding compare "C:\caminho\da\pasta" --json metricas.json --csv metricas.csv
```

Gera um JSON (resultado completo) e/ou um CSV (uma linha por algoritmo) com os scores de Silhouette e DBCV. `--html <caminho>` continua disponível se preferir o relatório visual. Para comparar vários corpus lado a lado num único relatório, use `compare-multi <pasta1> <pasta2> ...`.

### Avaliação externa (aderência a uma referência humana — ARI, NMI, AMI)

Compara a pasta de primeiro nível proposta com uma organização de referência feita por uma pessoa (por exemplo, a sua própria organização atual do corpus). Exige um CSV UTF-8 separado por `;`, com o caminho relativo do arquivo e o rótulo de referência nas duas primeiras colunas — um arquivo por linha, todos os arquivos do corpus precisam aparecer, sem duplicatas:

```csv
Arquivo;Rótulo
Contratos/2025/contrato_a.pdf;Contratos
Fotos/viagem/praia.jpg;Fotos
```

Para montar esse CSV a partir do zero, gere primeiro a lista de caminhos relativos (na mesma forma que a ferramenta usa: relativos à pasta escaneada, com `/`) e depois preencha a coluna de rótulo à mão ou em uma planilha:

```bash
uv run python -c "
from pathlib import Path
root = Path('C:/caminho/da/pasta')
for p in sorted(root.rglob('*')):
    if p.is_file():
        print(p.relative_to(root).as_posix() + ';')
"
```

Com o CSV pronto, rode:

```bash
uv run dynamic-folding external-eval "C:\caminho\da\pasta" --labels rotulos.csv --json externa.json --csv externa.csv
```

Arquivos que a proposta deixou em `Outros` também entram na conta. Os escores medem aderência àquela referência específica, não uma correção universal da organização — ver `docs/ADR/0047-external-evaluation-human-reference-partitions.md`.

## Configuração

Edite `config/default.toml` para ajustar o pipeline ao seu corpus:
- **Scanner:** `max_depth`, `ignore_globs`.
- **Extração:** `extractor.provider` (basic/type_aware), `snippet_size`.
- **Clustering:** `algorithm`, `min_cluster_size`.
- **Naming:** `provider` (tfidf/ollama), `model`.
