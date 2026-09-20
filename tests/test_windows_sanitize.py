from __future__ import annotations


def test_sanitize_windows_folder_name_basic() -> None:
    from dynamic_folding.core.windows import sanitize_windows_folder_name

    assert sanitize_windows_folder_name("  abc  def ") == "abc def"
    assert sanitize_windows_folder_name("Tema.") == "Tema"
    assert sanitize_windows_folder_name("Tema ") == "Tema"


def test_sanitize_windows_folder_name_invalid_chars() -> None:
    from dynamic_folding.core.windows import sanitize_windows_folder_name

    assert sanitize_windows_folder_name("a<b>c") == "a b c"
    assert sanitize_windows_folder_name("a|b") == "a b"
    assert sanitize_windows_folder_name("a/b") == "a b"


def test_sanitize_windows_folder_name_reserved() -> None:
    from dynamic_folding.core.windows import sanitize_windows_folder_name

    assert sanitize_windows_folder_name("CON").lower().startswith("con")
    assert sanitize_windows_folder_name("CON") != "CON"


def test_sanitize_strips_trailing_connectives_single() -> None:
    """Rótulos da LLM terminando em 'de'/'e' (Likert pilot) viram limpos."""
    from dynamic_folding.core.windows import sanitize_windows_folder_name

    assert (
        sanitize_windows_folder_name("Licitações Abnt Normas Certificação de")
        == "Licitações Abnt Normas Certificação"
    )
    assert (
        sanitize_windows_folder_name("Normas Hidráulicas Certificação de")
        == "Normas Hidráulicas Certificação"
    )
    assert (
        sanitize_windows_folder_name("Fotos de Projetos Fotos do Site Fotos e")
        == "Fotos de Projetos Fotos do Site Fotos"
    )


def test_sanitize_strips_trailing_connectives_recursive() -> None:
    """Recursão remove múltiplos conectivos terminais até estabilizar."""
    from dynamic_folding.core.windows import sanitize_windows_folder_name

    # "Tema único" não tem conectivos: preserva integralmente.
    assert sanitize_windows_folder_name("Tema único") == "Tema único"
    # "Projetos para" — "para" é conectivo, removido; "Projetos" fica.
    assert sanitize_windows_folder_name("Projetos para") == "Projetos"


def test_sanitize_falls_back_when_only_connectives() -> None:
    """Quando todas as palavras são conectivos, retorna o fallback."""
    from dynamic_folding.core.windows import sanitize_windows_folder_name

    assert sanitize_windows_folder_name("de e da") == "Group"
    assert sanitize_windows_folder_name("Para a") == "Group"
    assert sanitize_windows_folder_name("de") == "Group"


def test_sanitize_strips_connectives_case_insensitive() -> None:
    """Conectivos com qualquer caixa são reconhecidos."""
    from dynamic_folding.core.windows import sanitize_windows_folder_name

    assert sanitize_windows_folder_name("Materiais DE") == "Materiais"
    assert sanitize_windows_folder_name("Projetos E") == "Projetos"
