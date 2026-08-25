from __future__ import annotations

import json
from pathlib import Path

import pytest


def _touch(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"x")


def _write_config(
    path: Path,
    *,
    max_levels: int = 2,
    outliers_folder: str = "Outros",
    min_cluster_size: int = 4,
) -> None:
    # Intentionally specifies the Sprint 6 knobs.
    # Implementation is expected to:
    # - auto-discover K via agglomerative_tree
    # - route clusters smaller than min_cluster_size to proposal.outliers_folder
    path.write_text(
        f"""
[scanner]
provider = "fs"
extractor = "basic"
max_depth = 2
max_files = 200
ignore_hidden = false
ignore_globs = ["cfg.toml"]

[preprocess]
provider = "basic"
template = "{{stem}}"

[embedding]
provider = "handcrafted"
cache_db = "__default__"

[clustering]
algorithm = "agglomerative_tree"
min_cluster_size = {int(min_cluster_size)}

# Legacy keys should be ignored by agglomerative_tree.
top_k = 3
sub_k = 2
random_state = 0

[naming]
provider = "tfidf"
top_terms = 2

[proposal]
provider = "two_level"
max_levels = {int(max_levels)}
outliers_folder = "{outliers_folder}"
""".lstrip(),
        encoding="utf-8",
    )


def _install_handcrafted_embedder(monkeypatch, vectors_by_rel: dict[str, list[float]]) -> None:
    from dynamic_folding.contracts.embedding import EmbeddingRecord
    from dynamic_folding.core import registries

    def _embed(docs, _cfg):
        out = []
        for d in docs:
            # Ignore extra scanned files (e.g. local test config file).
            if d.file.rel_path not in vectors_by_rel:
                continue
            v = vectors_by_rel[d.file.rel_path]
            out.append(EmbeddingRecord(file=d.file, vector=v, model_id="handcrafted:v1", content_hash="x"))
        return out

    factories = dict(registries.EMBEDDERS._factories)
    factories["handcrafted"] = lambda _cfg: _embed
    monkeypatch.setattr(registries.EMBEDDERS, "_factories", factories)


def _proposal_top_memberships(proposal) -> dict[str, set[str]]:
    # Normalize the proposal so tests don't care whether items are directly under
    # a top folder or inside its subfolders.
    out: dict[str, set[str]] = {}
    
    def collect(node, top_name):
        out.setdefault(top_name, set()).update(node.files)
        for sub in node.subfolders:
            collect(sub, top_name)

    for node in proposal.folders:
        collect(node, node.name)

    return {k: v for k, v in out.items() if v}


def test_agglomerative_tree_auto_k_routes_small_clusters_to_review(tmp_path: Path, monkeypatch) -> None:
    # Two obvious clusters (>=4 each) + one small cluster (<min_cluster_size)
    group_a = [f"alpha_{i}.txt" for i in range(1, 5)]
    group_b = [f"beta_{i}.txt" for i in range(1, 5)]
    group_small = [f"misc_{i}.txt" for i in range(1, 4)]
    for rel in [*group_a, *group_b, *group_small]:
        _touch(tmp_path / rel)

    # Handcrafted 2D vectors; clusters are well-separated.
    vectors_by_rel = {
        # Group A near (0,0)
        group_a[0]: [0.0, 0.0],
        group_a[1]: [0.1, 0.0],
        group_a[2]: [0.0, 0.1],
        group_a[3]: [0.1, 0.1],
        # Group B near (10,10)
        group_b[0]: [10.0, 10.0],
        group_b[1]: [10.1, 10.0],
        group_b[2]: [10.0, 10.1],
        group_b[3]: [10.1, 10.1],
        # Small cluster near (50,50)
        group_small[0]: [50.0, 50.0],
        group_small[1]: [50.1, 50.0],
        group_small[2]: [50.0, 50.1],
    }
    _install_handcrafted_embedder(monkeypatch, vectors_by_rel)

    cfg_path = tmp_path / "cfg.toml"
    _write_config(cfg_path, max_levels=2, outliers_folder="Outros", min_cluster_size=4)

    from dynamic_folding.core.pipeline import run_pipeline

    r = run_pipeline(tmp_path, config_path=cfg_path)
    p = r.proposal

    memberships = _proposal_top_memberships(p)
    review = memberships.get("Outros", set())

    expected_review = set(group_small)
    expected_non_review = {frozenset(group_a), frozenset(group_b)}

    non_review_groups = [frozenset(v) for k, v in memberships.items() if k != "Outros"]
    assert set(non_review_groups) == expected_non_review
    assert review == expected_review

    # The proposer marks the outlier folder with display_name="Outros" so the
    # render layer can detect it even when proposal.outliers_folder is overridden.
    # See ADR 0026.
    outlier_folder = next(f for f in p.folders if f.name == "Outros")
    assert outlier_folder.display_name == "Outros"


def test_proposal_max_levels_1_disables_subfolders(tmp_path: Path, monkeypatch) -> None:
    # Max levels should control proposal depth independently of scan depth.
    files = [f"x_{i}.txt" for i in range(8)]
    for rel in files:
        _touch(tmp_path / rel)

    # Two clusters of 4.
    vectors_by_rel = {rel: ([0.0, float(i)] if i < 4 else [10.0, float(i)]) for i, rel in enumerate(files)}
    _install_handcrafted_embedder(monkeypatch, vectors_by_rel)

    cfg_path = tmp_path / "cfg.toml"
    _write_config(cfg_path, max_levels=1, outliers_folder="Outros", min_cluster_size=4)

    from dynamic_folding.core.pipeline import run_pipeline

    p = run_pipeline(tmp_path, config_path=cfg_path).proposal
    assert all(not f.subfolders for f in p.folders), "expected no subfolders when proposal.max_levels=1"


def test_agglomerative_tree_is_deterministic_for_memberships(tmp_path: Path, monkeypatch) -> None:
    files = [f"d_{i}.txt" for i in range(11)]
    for rel in files:
        _touch(tmp_path / rel)

    # Two clusters of 4 and one small cluster of 3.
    vectors_by_rel: dict[str, list[float]] = {}
    for i, rel in enumerate(files):
        if i < 4:
            vectors_by_rel[rel] = [0.0, float(i) / 10.0]
        elif i < 8:
            vectors_by_rel[rel] = [10.0, float(i) / 10.0]
        else:
            vectors_by_rel[rel] = [50.0, float(i) / 10.0]
    _install_handcrafted_embedder(monkeypatch, vectors_by_rel)

    cfg_path = tmp_path / "cfg.toml"
    _write_config(cfg_path, max_levels=2, outliers_folder="Outros", min_cluster_size=4)

    from dynamic_folding.core.pipeline import run_pipeline

    r1 = run_pipeline(tmp_path, config_path=cfg_path).proposal
    r2 = run_pipeline(tmp_path, config_path=cfg_path).proposal

    m1 = _proposal_top_memberships(r1)
    m2 = _proposal_top_memberships(r2)
    assert m1 == m2

    # JSON-level determinism as a backstop (folder names may still be deterministic).
    assert json.dumps(r1.to_dict(), sort_keys=True) == json.dumps(r2.to_dict(), sort_keys=True)


def test_outliers_folder_is_configurable(tmp_path: Path, monkeypatch) -> None:
    group_a = [f"alpha_{i}.txt" for i in range(1, 5)]
    group_b = [f"beta_{i}.txt" for i in range(1, 5)]
    group_small = [f"misc_{i}.txt" for i in range(1, 4)]
    for rel in [*group_a, *group_b, *group_small]:
        _touch(tmp_path / rel)

    vectors_by_rel = {rel: [0.0, float(i)] for i, rel in enumerate(group_a)}
    vectors_by_rel.update({rel: [10.0, float(i)] for i, rel in enumerate(group_b)})
    vectors_by_rel.update({rel: [50.0, float(i)] for i, rel in enumerate(group_small)})
    _install_handcrafted_embedder(monkeypatch, vectors_by_rel)

    cfg_path = tmp_path / "cfg.toml"
    _write_config(cfg_path, max_levels=2, outliers_folder="_NeedsReview", min_cluster_size=4)

    from dynamic_folding.core.pipeline import run_pipeline

    p = run_pipeline(tmp_path, config_path=cfg_path).proposal
    memberships = _proposal_top_memberships(p)
    assert memberships.get("_NeedsReview", set()) == set(group_small)

    # ADR 0026: even when the user overrides the canonical name, the proposer
    # marks the outlier folder with display_name="Outros" so the render layer
    # keys off a stable marker. The canonical user-chosen name is preserved
    # for cache keys and JSON, the display_name carries the standardised UX
    # label.
    outlier_folder = next(f for f in p.folders if f.name == "_NeedsReview")
    assert outlier_folder.display_name == "Outros"


@pytest.mark.parametrize(
    "bad_cfg, expected_substring",
    [
        ({"clustering": {"algorithm": "nope"}}, "clustering"),
        ({"clustering": {"algorithm": "agglomerative_tree", "min_cluster_size": 0}}, "min_cluster_size"),
        ({"proposal": {"max_levels": 0}}, "max_levels"),
        ({"proposal": {"outliers_folder": "bad/name"}}, "windows-safe"),
        ({"proposal": {"outliers_folder": ""}}, "outliers"),
    ],
)
def test_validate_config_rejects_invalid_sprint6_keys(bad_cfg: dict, expected_substring: str) -> None:
    from dynamic_folding.core.validate_config import ConfigError, validate_config

    # Minimal valid base config.
    cfg = {
        "scanner": {"provider": "fs", "extractor": "basic", "max_depth": 2, "max_files": 200},
        "preprocess": {"provider": "basic"},
        "embedding": {"provider": "fake", "cache_db": "__default__", "fake_dim": 8},
        "naming": {"provider": "tfidf", "top_terms": 2},
        "proposal": {"provider": "two_level", "max_levels": 2, "outliers_folder": "Outros"},
        "clustering": {"algorithm": "kmeans", "top_k": 3, "sub_k": 2, "random_state": 0},
    }

    # Overlay the bad keys.
    for section, values in bad_cfg.items():
        cfg.setdefault(section, {})
        cfg[section].update(values)

    with pytest.raises(ConfigError) as e:
        validate_config(cfg)
    assert expected_substring.lower() in str(e.value).lower()
