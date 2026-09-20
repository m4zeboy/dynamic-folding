"""Tests for the post-Sprint-19 render polish layer.

Covers:
- `display_name` override on `FolderNode`
- Outlier bucket ("Outros") merged with orphans and rendered last
- Folder ordering: direct-file-count DESC, then name ASC (ADR 0035 — the former
  confidence-based ordering was removed with the user-facing confidence signal)
- Unicode glyphs by default, ASCII fallback with use_emojis=False
- File-count pluralisation
- Contract: display_name field serialises only when set; version is 4; the
  removed confidence fields (cohesion / cohesion_score) are gone
- Config: default outliers_folder is "Outros"; custom override flows through
"""
from __future__ import annotations

from dynamic_folding.contracts.proposal import FolderNode, StructureProposal
from dynamic_folding.render.tree import render_tree


def _proposal(folders, orphans=None, root="C:/test"):
    return StructureProposal(
        root=root,
        folders=folders,
        orphans=orphans or [],
        notes=[],
    )


# ---------------------------------------------------------------------------
# display_name override
# ---------------------------------------------------------------------------

def test_display_name_overrides_canonical_name_in_render():
    p = _proposal([
        FolderNode(name="canonical_xyz", display_name="Documentos", files=["a.txt"]),
    ])
    out = render_tree(p)
    assert "Documentos/" in out
    assert "canonical_xyz" not in out


def test_render_falls_back_to_name_when_display_name_is_none():
    p = _proposal([
        FolderNode(name="ExactName", files=["a.txt"]),
    ])
    out = render_tree(p)
    assert "ExactName/" in out


# ---------------------------------------------------------------------------
# Outlier bucket merge
# ---------------------------------------------------------------------------

def test_outlier_folder_and_orphans_merge_into_one_outros_bucket():
    p = _proposal(
        folders=[
            FolderNode(name="Documentos", files=["doc1.pdf"]),
            FolderNode(name="canonical_outlier", display_name="Outros", files=["odd1.txt"]),
        ],
        orphans=["orphan_a.bin", "orphan_b.tmp"],
    )
    out = render_tree(p)
    # Only one "Outros/" entry — the merge.
    assert out.count("Outros/") == 1
    # All three files (1 outlier + 2 orphans) appear under it.
    assert "odd1.txt" in out
    assert "orphan_a.bin" in out
    assert "orphan_b.tmp" in out
    # Old "(orphans)/" presentation is gone.
    assert "(orphans)" not in out


def test_outros_bucket_renders_last_even_if_alphabetically_first():
    p = _proposal([
        FolderNode(name="_Aoutlier", display_name="Outros", files=["x.txt"]),
        FolderNode(name="Zeta", files=["z.txt"]),
    ])
    out = render_tree(p)
    # Find positions of the two folder labels in the rendered tree.
    pos_outros = out.find("Outros/")
    pos_zeta = out.find("Zeta/")
    assert pos_zeta < pos_outros, "Outros bucket must render after non-outlier folders"


def test_orphans_only_still_render_outros_bucket():
    p = _proposal(folders=[], orphans=["lonely.txt"])
    out = render_tree(p)
    assert "Outros/" in out
    assert "lonely.txt" in out


# ---------------------------------------------------------------------------
# Folder ordering (file-count DESC, then name ASC)
# ---------------------------------------------------------------------------

def test_folders_ordered_by_file_count_desc():
    p = _proposal([
        FolderNode(name="Small", files=["a.txt"]),
        FolderNode(name="Big", files=["b.txt", "c.txt", "d.txt"]),
        FolderNode(name="Mid", files=["e.txt", "f.txt"]),
    ])
    out = render_tree(p)
    assert out.find("Big/") < out.find("Mid/") < out.find("Small/")


def test_folders_tie_break_by_name_when_size_matches():
    p = _proposal([
        FolderNode(name="Beta", files=["a.txt"]),
        FolderNode(name="Alpha", files=["b.txt"]),
    ])
    out = render_tree(p)
    assert out.find("Alpha/") < out.find("Beta/")


# ---------------------------------------------------------------------------
# Glyph rendering
# ---------------------------------------------------------------------------

def test_unicode_glyphs_by_default():
    p = _proposal([
        FolderNode(name="Docs", files=["a.txt"]),
    ])
    out = render_tree(p, use_emojis=True)
    assert "├── " in out or "└── " in out


def test_ascii_glyphs_when_emojis_disabled():
    p = _proposal([
        FolderNode(name="Docs", files=["a.txt"]),
    ])
    out = render_tree(p, use_emojis=False)
    # ASCII fallback uses the legacy "|-" pattern, never the Unicode box drawing.
    assert "├" not in out
    assert "└" not in out
    assert "|-" in out


def test_emoji_disabled_drops_folder_emoji():
    p = _proposal([
        FolderNode(name="Docs", files=["a.txt"]),
    ])
    out = render_tree(p, use_emojis=False)
    assert "📁" not in out
    assert "Docs/" in out


# ---------------------------------------------------------------------------
# File-count pluralisation
# ---------------------------------------------------------------------------

def test_single_file_uses_singular_arquivo():
    p = _proposal([
        FolderNode(name="One", files=["x.txt"]),
    ])
    out = render_tree(p)
    assert "(1 arquivo)" in out
    assert "1 arquivos" not in out


def test_multiple_files_use_plural_arquivos():
    p = _proposal([
        FolderNode(name="Many", files=["a.txt", "b.txt", "c.txt"]),
    ])
    out = render_tree(p)
    assert "(3 arquivos)" in out


def test_zero_direct_files_omits_count():
    """A folder with only subfolders shows no '(N arquivos)' annotation."""
    p = _proposal([
        FolderNode(
            name="Parent",
            files=[],
            subfolders=[FolderNode(name="Child", files=["x.txt"])],
        ),
    ])
    out = render_tree(p)
    # Parent line should have no parenthetical count.
    parent_line = next(ln for ln in out.splitlines() if "Parent/" in ln)
    assert "arquivo" not in parent_line


# ---------------------------------------------------------------------------
# No confidence signal in the render
# ---------------------------------------------------------------------------

def test_render_has_no_confidence_artefacts():
    """No colour bands, no 'verificar' label, no numeric score (ADR 0035)."""
    p = _proposal([
        FolderNode(name="A", files=["a.txt"]),
        FolderNode(name="B", files=["b.txt", "c.txt"]),
    ])
    out = render_tree(p)
    assert "[green]" not in out and "[yellow]" not in out and "[red]" not in out
    assert "verificar" not in out
    assert "score:" not in out


# ---------------------------------------------------------------------------
# Summary preamble
# ---------------------------------------------------------------------------

def test_summary_preamble_counts_folders_files_and_outliers():
    p = _proposal(
        folders=[
            FolderNode(name="A", files=["a.txt", "b.txt"]),
            FolderNode(name="B", files=["c.txt"]),
            FolderNode(name="canonical_outlier", display_name="Outros", files=["x.txt"]),
        ],
        orphans=["o.txt"],
    )
    out = render_tree(p)
    # 2 non-outlier folders, 3 non-outlier files, 2 in Outros (1 outlier + 1 orphan)
    assert "Proposta: 2 pastas, 3 arquivos · 2 em \"Outros\"" in out


def test_summary_preamble_omits_outlier_suffix_when_no_outliers():
    p = _proposal([
        FolderNode(name="A", files=["a.txt"]),
    ])
    out = render_tree(p)
    assert "Proposta: 1 pasta, 1 arquivo" in out
    assert "em \"Outros\"" not in out


# ---------------------------------------------------------------------------
# Contract: display_name serialisation + version + removed confidence fields
# ---------------------------------------------------------------------------

def test_display_name_omitted_from_json_when_none():
    folder = FolderNode(name="X", files=["a.txt"])
    d = folder.to_dict()
    assert "display_name" not in d


def test_display_name_present_in_json_when_set():
    folder = FolderNode(name="canonical", display_name="Outros", files=["a.txt"])
    d = folder.to_dict()
    assert d["display_name"] == "Outros"


def test_structure_proposal_contracts_version_is_4():
    p = StructureProposal(root=".")
    assert p.contracts_version == 4
    assert p.to_dict()["contracts_version"] == 4


def test_confidence_fields_removed_from_contract():
    """The user-facing confidence signal is gone from the contract (ADR 0035)."""
    folder = FolderNode(name="X", files=["a.txt"])
    assert not hasattr(folder, "cohesion")
    assert "cohesion" not in folder.to_dict()

    p = StructureProposal(root=".")
    assert not hasattr(p, "cohesion_score")
    assert "cohesion_score" not in p.to_dict()


# ---------------------------------------------------------------------------
# Config: outliers_folder default and override
# ---------------------------------------------------------------------------

def test_default_config_outliers_folder_is_outros():
    from dynamic_folding.core.config import get_system_defaults
    defaults = get_system_defaults()
    assert defaults["proposal"]["outliers_folder"] == "Outros"


def test_custom_outliers_folder_override_is_accepted_by_validation():
    """Power-user override of `proposal.outliers_folder` passes validation."""
    from dynamic_folding.core.config import get_system_defaults
    from dynamic_folding.core.validate_config import validate_config

    cfg = get_system_defaults()
    cfg["proposal"]["outliers_folder"] = "Para Revisar"
    # Should not raise — "Para Revisar" is a portable, safe folder name.
    validate_config(cfg)
