# Silhouette vs baseline

## Config

```toml
[scanner]
provider = "fs"
extractor = "type_aware"
max_depth = 3
max_files = 200
snippet_size = 4096
ignore_hidden = true
ignore_globs = [".git/**", "node_modules/**", ".dynamic-folding/**", "Thumbs.db"]

[preprocess]
provider = "basic"
template = "[NOME]: {stem} [TÍTULO]: {title} [EXT]: {ext} [CONTEÚDO]: {snippet}"

[embedding]
provider = "sbert"
device = "cpu"
batch_size = 32
normalize = true
cache_db = "__default__"

[reducer]
provider = "umap"
n_components = 10
n_neighbors = 15
random_state = 0

[clustering]
algorithm = "hdbscan"
top_k = 3
sub_k = 2
random_state = 0
min_cluster_size = 2

[naming]
provider = "ollama"
base_url = "http://127.0.0.1:11434"
model = "llama3.1:8b"
timeout_s = 10
top_k_files = 25
prompt_variant = "default"
top_anchor_terms = 5
top_terms = 2

[proposal]
provider = "two_level"
naming_direction = "bottom_up"

[ui]
use_emojis = true

[report]
enabled = true
output_path = "__default__"
auto_open = true
```
## Corpus
C:\Users\moise\iCloudDrive\Downloads

## Results
Silhouette: 0.110  (7 groups, 45 files; 8 in Outros skipped)
Random baseline: -0.074 +/- 0.012 over 1000 shuffles  (real 0.110 is +0.184 above it)
