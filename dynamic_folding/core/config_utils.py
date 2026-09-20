from __future__ import annotations

from typing import Any


def deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """
    Recursively merge two dictionaries.
    Values from 'overrides' take precedence.
    """
    merged = base.copy()
    for key, value in overrides.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged
