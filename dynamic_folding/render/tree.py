from __future__ import annotations

from pathlib import Path
from dynamic_folding.contracts.proposal import FolderNode, StructureProposal

# Map extensions to specific emojis for a better visual experience.
EXTENSION_EMOJIS = {
    ".pdf": "📑",
    ".jpg": "🖼️",
    ".jpeg": "🖼️",
    ".png": "🖼️",
    ".py": "🐍",
    ".txt": "📄",
    ".md": "📝",
    ".json": "⚙️",
    ".toml": "⚙️",
    ".csv": "📊",
    ".zip": "📦",
    ".rar": "📦",
    ".exe": "🚀",
}

# Tree glyphs. Unicode (default) matches the GNU `tree` command and modern file
# managers; ASCII is the legacy fallback for terminals that don't render Unicode
# box-drawing characters (kept under use_emojis=False, which doubles as a
# "plain ASCII" mode for piping or LaTeX screenshots).
_GLYPHS_UNICODE = {
    "branch": "├── ",
    "last": "└── ",
    "vert": "│   ",
    "blank": "    ",
}
_GLYPHS_ASCII = {
    "branch": "|- ",
    "last": "|- ",
    "vert": "|  ",
    "blank": "|  ",
}

# Public marker used by both the CLI tree renderer and the TUI to identify the
# outlier bucket. The proposer sets `FolderNode.display_name = OUTLIER_DISPLAY_NAME`
# on the outlier folder so the marker is stable across `proposal.outliers_folder`
# config overrides. See ADR 0026.
OUTLIER_DISPLAY_NAME = "Outros"
_PATH_DISPLAY_MAX = 60


def get_file_emoji(filename: str, use_emojis: bool) -> str:
    if not use_emojis:
        return ""
    ext = Path(filename).suffix.lower()
    return EXTENSION_EMOJIS.get(ext, "📄") + " "


def is_outlier(folder: FolderNode) -> bool:
    return folder.display_name == OUTLIER_DISPLAY_NAME


def label_for(folder: FolderNode) -> str:
    return folder.display_name if folder.display_name is not None else folder.name


def folder_sort_key(f: FolderNode) -> tuple[int, str]:
    # Direct-file-count DESC, then name ASC (tie-breaker). Deterministic and
    # independent of any quality signal (silhouette is evaluation-only — ADR 0035).
    return (-len(f.files), f.name.casefold())


def files_word(n: int) -> str:
    return "1 arquivo" if n == 1 else f"{n} arquivos"


def count_files_recursive(folder: FolderNode) -> int:
    total = len(folder.files)
    for s in folder.subfolders:
        total += count_files_recursive(s)
    return total


def _truncate_path(s: str, max_len: int = _PATH_DISPLAY_MAX) -> str:
    if len(s) <= max_len:
        return s
    return "…" + s[-(max_len - 1):]


def render_summary_line(p: StructureProposal) -> str:
    """Build the PT-BR summary line shown above the tree.

    Format: `Proposta: N pastas, M arquivos · K em "Outros"` (the trailing
    `· K em "Outros"` suffix is added only when there are outlier or orphan
    files). Both the CLI tree renderer and the TUI use this so counts stay in
    lockstep across surfaces.
    """
    normal_folders = [f for f in p.folders if not is_outlier(f)]
    outlier_folder = next((f for f in p.folders if is_outlier(f)), None)

    n_folders = len(normal_folders)
    n_files = sum(count_files_recursive(f) for f in normal_folders)
    n_outlier = len(p.orphans)
    if outlier_folder is not None:
        n_outlier += count_files_recursive(outlier_folder)

    folder_word = "1 pasta" if n_folders == 1 else f"{n_folders} pastas"
    summary = f"Proposta: {folder_word}, {files_word(n_files)}"
    if n_outlier > 0:
        summary += f" · {n_outlier} em \"{OUTLIER_DISPLAY_NAME}\""
    return summary


def _format_folder_line(
    folder: FolderNode,
    *,
    prefix: str,
    connector: str,
    use_emojis: bool,
) -> str:
    folder_icon = "📁 " if use_emojis else ""
    label = label_for(folder)

    n_files = len(folder.files)
    paren = f" ({files_word(n_files)})" if n_files > 0 else ""
    body = f"{folder_icon}{label}/{paren}"

    return f"{prefix}{connector}{body}"


def _render_folder(
    folder: FolderNode,
    *,
    prefix: str,
    is_last: bool,
    glyphs: dict,
    lines: list[str],
    use_emojis: bool,
    summary_only: bool,
    hidden: list[int],
) -> None:
    connector = glyphs["last"] if is_last else glyphs["branch"]
    lines.append(
        _format_folder_line(
            folder,
            prefix=prefix,
            connector=connector,
            use_emojis=use_emojis,
        )
    )

    child_prefix = prefix + (glyphs["blank"] if is_last else glyphs["vert"])

    files_sorted = sorted(folder.files, key=str.casefold)
    subs_sorted = sorted(folder.subfolders, key=folder_sort_key)

    if summary_only:
        hidden[0] += len(files_sorted)
        rendered_files: list[str] = []
    else:
        rendered_files = files_sorted

    total_children = len(rendered_files) + len(subs_sorted)
    for i, f in enumerate(rendered_files):
        is_last_child = (i == total_children - 1) and not subs_sorted
        f_connector = glyphs["last"] if is_last_child else glyphs["branch"]
        lines.append(f"{child_prefix}{f_connector}{get_file_emoji(f, use_emojis)}{f}")

    for j, sub in enumerate(subs_sorted):
        is_last_sub = (j == len(subs_sorted) - 1)
        _render_folder(
            sub,
            prefix=child_prefix,
            is_last=is_last_sub,
            glyphs=glyphs,
            lines=lines,
            use_emojis=use_emojis,
            summary_only=summary_only,
            hidden=hidden,
        )


def _render_outlier_bucket(
    outlier_folder: FolderNode | None,
    orphans: list[str],
    *,
    glyphs: dict,
    lines: list[str],
    use_emojis: bool,
    summary_only: bool,
    hidden: list[int],
) -> None:
    """Render the consolidated 'Outros' bucket as the final entry of the tree.

    Merges the proposer's outlier folder (canonical name from `proposal.outliers_folder`
    config, marked with display_name='Outros') and the top-level orphans into a
    single user-visible folder.
    """
    merged_files: list[str] = []
    if outlier_folder is not None:
        merged_files.extend(outlier_folder.files)
    merged_files.extend(orphans)
    merged_files = sorted(merged_files, key=str.casefold)
    n = len(merged_files)

    folder_icon = "📁 " if use_emojis else ""
    paren = f" ({files_word(n)})" if n > 0 else ""
    lines.append(f"{glyphs['last']}{folder_icon}{OUTLIER_DISPLAY_NAME}/{paren}")

    if summary_only:
        hidden[0] += n
        return

    child_prefix = glyphs["blank"]
    for i, f in enumerate(merged_files):
        is_last = (i == n - 1)
        f_connector = glyphs["last"] if is_last else glyphs["branch"]
        lines.append(f"{child_prefix}{f_connector}{get_file_emoji(f, use_emojis)}{f}")


def render_tree(
    p: StructureProposal,
    use_emojis: bool = True,
    summary_only: bool = False,
) -> str:
    """Render proposal as a tree using Rich formatting.

    Layout:
      - Summary preamble: "Proposta: N pastas, M arquivos · K em 'Outros'"
      - Root path (truncated when long)
      - Tree, with normal folders sorted by direct-file-count DESC then name ASC,
        outlier bucket ("Outros") always rendered last and merged with orphans.

    Args:
      use_emojis: when False, falls back to ASCII glyphs (and drops emoji);
        useful for piping output or LaTeX screenshots.
      summary_only: omit files from the tree (only the folder skeleton is shown).
    """
    glyphs = _GLYPHS_UNICODE if use_emojis else _GLYPHS_ASCII

    lines: list[str] = []

    if not p.folders and not p.orphans:
        lines.append(f"Raiz: {_truncate_path(p.root)}")
        lines.append("(no proposal)")
        return "\n".join(lines)

    lines.append(render_summary_line(p))
    lines.append(f"Raiz: {_truncate_path(p.root)}")

    normal_folders = [f for f in p.folders if not is_outlier(f)]
    outlier_folder = next((f for f in p.folders if is_outlier(f)), None)
    has_outlier_bucket = (outlier_folder is not None) or bool(p.orphans)

    sorted_normals = sorted(normal_folders, key=folder_sort_key)

    hidden = [0]
    total_top = len(sorted_normals) + (1 if has_outlier_bucket else 0)
    for i, folder in enumerate(sorted_normals):
        is_last_top = (i == total_top - 1)  # only true if no outlier bucket follows
        _render_folder(
            folder,
            prefix="",
            is_last=is_last_top,
            glyphs=glyphs,
            lines=lines,
            use_emojis=use_emojis,
            summary_only=summary_only,
            hidden=hidden,
        )

    if has_outlier_bucket:
        _render_outlier_bucket(
            outlier_folder,
            p.orphans,
            glyphs=glyphs,
            lines=lines,
            use_emojis=use_emojis,
            summary_only=summary_only,
            hidden=hidden,
        )

    if summary_only and hidden[0] > 0:
        lines.append(f"\n[italic grey37](... {hidden[0]} files hidden in summary view)[/italic grey37]")

    if p.notes:
        lines.append("\nNotas:")
        for n in p.notes:
            lines.append(f"- {n}")

    return "\n".join(lines)
