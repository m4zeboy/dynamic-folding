from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from dynamic_folding.core.registries import CLUSTERERS, EMBEDDERS, EXTRACTORS, NAMERS, PREPROCESSORS, PROPOSERS, REDUCERS, SCANNERS
from dynamic_folding.core.windows import sanitize_windows_folder_name


@dataclass
class ConfigError(Exception):
    message: str

    def __str__(self) -> str:  # pragma: no cover
        return self.message


def _require_int(cfg: dict, key: str, *, min_value: int | None = None) -> int:
    try:
        v = int(cfg.get(key))
    except Exception as e:
        raise ConfigError(f"Config '{key}' must be an integer") from e
    if min_value is not None and v < min_value:
        raise ConfigError(f"Config '{key}' must be >= {min_value}")
    return v


def validate_config(cfg: dict) -> None:
    sc = cfg.get("scanner", {})
    pp = cfg.get("preprocess", {})
    emb = cfg.get("embedding", {})
    nm = cfg.get("naming", {})
    prop = cfg.get("proposal", {})
    cl = cfg.get("clustering", {})

    scanner_id = str(sc.get("provider", "fs")).strip().lower()
    if scanner_id not in SCANNERS.keys():
        raise ConfigError(f"Unknown scanner.provider '{scanner_id}'")

    extractor_id = str(sc.get("extractor", "basic")).strip().lower()
    if extractor_id not in EXTRACTORS.keys():
        raise ConfigError(f"Unknown scanner.extractor '{extractor_id}'")

    pre_id = str(pp.get("provider", "basic")).strip().lower()
    if pre_id not in PREPROCESSORS.keys():
        raise ConfigError(f"Unknown preprocess.provider '{pre_id}'")

    # Coherence guard (ADR 0036): the type-aware extractor produces a content
    # snippet, but that snippet only reaches the embedder if the preprocess
    # template emits it. Pairing `type_aware` with a snippet-less template
    # silently discards all extracted content, degrading embeddings/naming to
    # filename-only — the exact class of bug that produced "57 files -> 2 groups".
    # Fail loudly instead of failing silently.
    if extractor_id == "type_aware":
        template = str(pp.get("template", ""))
        if "{snippet}" not in template:
            raise ConfigError(
                "scanner.extractor='type_aware' requires preprocess.template to "
                "include '{snippet}', otherwise extracted document content is "
                "silently dropped before embedding. Add '{snippet}' to the "
                "template, or use scanner.extractor='basic'."
            )
        if "snippet_size" in sc:
            _require_int(sc, "snippet_size", min_value=1)

    emb_id = str(emb.get("provider", "fake")).strip().lower()
    if emb_id not in EMBEDDERS.keys():
        raise ConfigError(f"Unknown embedding.provider '{emb_id}'")

    if emb_id == "sbert":
        try:
            import sentence_transformers  # noqa: F401
        except Exception as e:
            raise ConfigError(
                "embedding.provider='sbert' requires 'sentence-transformers'. "
                "Install the extra: `uv pip install -e \".[sbert]\"`"
            ) from e

        model_path_raw = emb.get("model_path")
        if not model_path_raw:
            raise ConfigError("embedding.provider='sbert' requires embedding.model_path")
        mp = Path(str(model_path_raw)).expanduser()
        if not mp.exists() or not mp.is_dir():
            raise ConfigError(f"embedding.model_path must be an existing local directory (got: {mp})")

    naming_id = str(nm.get("provider", "tfidf")).strip().lower()
    if naming_id not in NAMERS.keys():
        raise ConfigError(f"Unknown naming.provider '{naming_id}'")

    if naming_id == "ollama":
        model = str(nm.get("model", "")).strip()
        if not model:
            raise ConfigError("naming.provider='ollama' requires naming.model")

        base_url = str(nm.get("base_url", "http://127.0.0.1:11434"))
        p = urlparse(base_url)
        host = p.hostname
        if p.scheme not in {"http", "https"} or not host:
            raise ConfigError("naming.base_url must be a loopback http(s) URL")

        if host.lower() != "localhost":
            try:
                import ipaddress

                if not ipaddress.ip_address(host).is_loopback:
                    raise ConfigError("naming.base_url must be loopback-only (localhost/127.0.0.1/::1)")
            except ValueError as e:
                raise ConfigError("naming.base_url must be loopback-only (localhost/127.0.0.1/::1)") from e

        prompt_variant = str(nm.get("prompt_variant", "grounded")).strip().lower()
        if prompt_variant not in {"default", "grounded"}:
            raise ConfigError(
                f"naming.prompt_variant must be 'default' or 'grounded' "
                f"(got: {prompt_variant})"
            )

    prop_id = str(prop.get("provider", "two_level")).strip().lower()
    if prop_id not in PROPOSERS.keys():
        raise ConfigError(f"Unknown proposal.provider '{prop_id}'")

    naming_direction = str(prop.get("naming_direction", "per_node")).strip().lower()
    if naming_direction not in {"per_node", "bottom_up"}:
        raise ConfigError(
            f"proposal.naming_direction must be 'per_node' or 'bottom_up' "
            f"(got: {naming_direction})"
        )

    # Sprint 6 knobs (validated even if not yet used by proposer).
    # Defaults must be accepted by validate_config, since older configs/tests
    # don't specify these keys.
    try:
        max_levels = int(prop.get("max_levels", 2))
    except Exception as e:
        raise ConfigError("Config 'max_levels' must be an integer") from e
    if max_levels < 1:
        raise ConfigError("Config 'max_levels' must be >= 1")

    outliers_folder = str(prop.get("outliers_folder", "Outros")).strip()
    if not outliers_folder:
        raise ConfigError("proposal.outliers_folder must be a non-empty string")
    if sanitize_windows_folder_name(outliers_folder, fallback="Outros") != outliers_folder:
        raise ConfigError("proposal.outliers_folder must be a Windows-safe folder name")

    # Dynamic validation against CLUSTERERS registry
    algo = str(cl.get("algorithm", "kmeans")).strip().lower()
    if algo not in CLUSTERERS.keys():
        raise ConfigError(f"Unknown clustering.algorithm '{algo}' (supported: {list(CLUSTERERS.keys())})")

    try:
        min_cluster_size = int(cl.get("min_cluster_size", 4))
    except Exception as e:
        raise ConfigError("Config 'min_cluster_size' must be an integer") from e
    if min_cluster_size < 1:
        raise ConfigError("Config 'min_cluster_size' must be >= 1")

    _require_int(sc, "max_depth", min_value=0)
    _require_int(sc, "max_files", min_value=1)

    red = cfg.get("reducer", {})
    reducer_id = str(red.get("provider", "identity")).strip().lower()
    if reducer_id not in REDUCERS.keys():
        raise ConfigError(f"Unknown reducer.provider '{reducer_id}'")

    _require_int(red, "n_components", min_value=1)
    _require_int(red, "random_state", min_value=0)

    rep = cfg.get("report", {})
    if not isinstance(rep.get("enabled", False), bool):
        raise ConfigError("report.enabled must be true or false")
    if not isinstance(rep.get("auto_open", False), bool):
        raise ConfigError("report.auto_open must be true or false")
    if not isinstance(rep.get("output_path", "__default__"), str):
        raise ConfigError("report.output_path must be a string")
