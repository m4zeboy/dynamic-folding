# Dynamic Folding

Ferramenta offline para propor uma organização semântica de arquivos em pastas. A interface permite selecionar uma pasta, revisar a proposta e gerar um relatório HTML.

## Requisitos

- Python 3.11 ou superior;
- [uv](https://docs.astral.sh/uv/);
- Windows (a interface gráfica foi projetada para este ambiente).

## Instalação

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
