from __future__ import annotations


def test_validate_config_rejects_unknown_provider() -> None:
    from dynamic_folding.core.validate_config import ConfigError, validate_config

    cfg = {
        "scanner": {"provider": "nope", "extractor": "basic", "max_depth": 2, "max_files": 200},
        "preprocess": {"provider": "basic"},
        "embedding": {"provider": "fake", "cache_db": "__default__", "fake_dim": 8},
        "proposal": {"provider": "two_level"},
    }
    try:
        validate_config(cfg)
        assert False, "expected ConfigError"
    except ConfigError as e:
        assert "scanner.provider" in str(e)


def test_validate_config_rejects_invalid_limits() -> None:
    from dynamic_folding.core.validate_config import ConfigError, validate_config

    cfg = {
        "scanner": {"provider": "fs", "extractor": "basic", "max_depth": -1, "max_files": 0},
        "preprocess": {"provider": "basic"},
        "embedding": {"provider": "fake", "cache_db": "__default__", "fake_dim": 8},
        "proposal": {"provider": "two_level"},
    }
    try:
        validate_config(cfg)
        assert False, "expected ConfigError"
    except ConfigError as e:
        assert "max_depth" in str(e) or "max_files" in str(e)
