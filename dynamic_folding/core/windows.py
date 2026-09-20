from __future__ import annotations

import re


_INVALID_CHARS = re.compile(r"[<>:\"/\\|?*]+")
_CONTROL_CHARS = re.compile(r"[\x00-\x1f]")

_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

# PT-BR preposições e conjunções comuns. Quando aparecem como palavra
# terminal de um rótulo gerado pela LLM, o nome lê como truncado mesmo
# sem corte mecânico (ex.: "Certificação de", "Fotos e"). A remoção é
# recursiva até estabilizar: "Para a" -> "Para" -> "" (e cai para
# fallback).
_TRAILING_CONNECTIVES = frozenset({
    "de", "da", "do", "das", "dos",
    "e", "ou",
    "em", "no", "na", "nos", "nas",
    "para", "com",
    "a", "o", "as", "os",
    "pelo", "pela", "pelos", "pelas",
})


def _strip_trailing_connectives(s: str) -> str:
    """Remove conectivos-terminais (preposições/conjunções) de um rótulo.

    Aplicado recursivamente até nenhum conectivo restar como palavra
    final. Quando todas as palavras são conectivos, retorna string
    vazia (chamador aplica fallback).
    """
    while s:
        s = s.rstrip(" .")
        head, sep, tail = s.rpartition(" ")
        if tail.lower() not in _TRAILING_CONNECTIVES:
            return s
        # Tail é conectivo: descarta. Se não houver mais palavras à
        # esquerda, retorna vazio (todo o rótulo era conectivo).
        s = head
    return s


def sanitize_windows_folder_name(name: str, *, fallback: str = "Group", max_len: int = 80) -> str:
    """Make a Windows-safe folder name.

    Notes:
    - Removes invalid/control characters
    - Trims trailing dots/spaces
    - Strips trailing connectives (de, da, e, ...) recursively
    - Avoids reserved device names
    """

    s = str(name)
    s = _CONTROL_CHARS.sub(" ", s)
    s = _INVALID_CHARS.sub(" ", s)
    s = " ".join(s.split()).strip()
    s = s.rstrip(" .")

    # Remove conectivos terminais antes da verificação de comprimento
    # para que a lógica de truncamento não interaja com eles.
    s = _strip_trailing_connectives(s)

    if not s:
        s = fallback

    if s.upper() in _RESERVED:
        s = f"{s}_folder"

    if len(s) > max_len:
        # Avoid cutting in the middle of a word if possible
        truncated = s[:max_len]
        last_space = truncated.rfind(" ")
        if last_space > (max_len // 2):  # Only cut at space if it doesn't lose too much info
            s = truncated[:last_space].rstrip(" .")
        else:
            s = truncated.rstrip(" .")

        # Após o corte, conectivos novos podem ter sido expostos no
        # final do rótulo — aplica o stripping novamente.
        s = _strip_trailing_connectives(s)

        if not s:
            s = fallback

    return s


def apply_windows_safe_suffix(name: str, suffix_num: int, max_len: int = 80) -> str:
    """Apply a numeric suffix to a name while staying under max_len.

    If name + suffix > max_len, truncate the name to make room.
    """
    suffix = f"_{suffix_num}"
    if len(name) + len(suffix) <= max_len:
        return f"{name}{suffix}"

    # Truncate base name
    base_len = max_len - len(suffix)
    if base_len <= 0:
        # Fallback if max_len is too small for even the suffix
        return suffix[:max_len]

    return f"{name[:base_len]}{suffix}"
