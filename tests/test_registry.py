from __future__ import annotations


def test_registry_unknown_key_is_clear() -> None:
    from dynamic_folding.core.registry import Registry

    r: Registry[int] = Registry("demo")
    try:
        r.create("missing", {})
        assert False, "expected KeyError"
    except KeyError as e:
        assert "demo" in str(e)
        assert "missing" in str(e)


def test_default_registries_have_expected_plugins() -> None:
    from dynamic_folding.core.registries import (
        CLUSTERERS,
        EMBEDDERS,
        EXTRACTORS,
        NAMERS,
        PREPROCESSORS,
        PROPOSERS,
        SCANNERS,
    )

    assert "fs" in SCANNERS.keys()
    assert "basic" in EXTRACTORS.keys()
    assert "basic" in PREPROCESSORS.keys()
    assert "fake" in EMBEDDERS.keys()
    assert "kmeans" in CLUSTERERS.keys()
    assert "tfidf" in NAMERS.keys()
    assert "two_level" in PROPOSERS.keys()
