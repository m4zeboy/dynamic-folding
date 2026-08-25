from __future__ import annotations
import pytest
from dynamic_folding.core.windows import apply_windows_safe_suffix

def test_apply_windows_safe_suffix_basic():
    # No truncation needed
    assert apply_windows_safe_suffix("Group", 2, max_len=10) == "Group_2"

def test_apply_windows_safe_suffix_truncation():
    # Base is too long, must truncate to fit _2
    # "A" * 10 = AAAAAAAAAA
    # suffix "_2" is 2 chars
    # max_len is 10
    # Expected: "AAAAAAAA_2" (8 chars + 2 suffix = 10)
    base = "A" * 10
    result = apply_windows_safe_suffix(base, 2, max_len=10)
    assert result == "AAAAAAAA_2"
    assert len(result) == 10

def test_apply_windows_safe_suffix_large_number():
    # Suffix _10 is 3 chars
    base = "A" * 10
    result = apply_windows_safe_suffix(base, 10, max_len=10)
    assert result == "AAAAAAA_10"
    assert len(result) == 10

def test_apply_windows_safe_suffix_reserved_name():
    # Suffixing a reserved name should still work and be safe
    assert apply_windows_safe_suffix("CON", 2, max_len=80) == "CON_2"
