from __future__ import annotations
import re
from pathlib import Path

PATH_RE = re.compile(r'[`\'"]?((?:workspace|departments)/[\w./*{}-]+)[`\'"]?')
DIR_RE = re.compile(r'[`\'"]?(workspace/[\w/-]+/)[`\'"]?')


def is_template_path(path: str) -> bool:
    return "{" in path


def is_glob_path(path: str) -> bool:
    return "*" in path


def extract_list_paths(block_text: str) -> tuple[list[str], list[str]]:
    paths: list[str] = []
    optional_paths: list[str] = []
    for line in block_text.splitlines():
        stripped = line.strip().lstrip("- ").strip()
        if stripped and not stripped.startswith("#"):
            match = PATH_RE.search(stripped)
            if match:
                p = match.group(1)
                paths.append(p)
                if (
                    "[OPTIONAL]" in stripped.upper()
                    or "[ОПЦИОНАЛЬНО]" in stripped.upper()
                ):
                    optional_paths.append(p)
    return list(dict.fromkeys(paths)), list(dict.fromkeys(optional_paths))


def resolve_path(path: str, root: Path) -> list[Path]:
    if "{" in path:
        return []
    if "*" in path:
        return list(root.glob(path))
    full = root / path if not Path(path).is_absolute() else Path(path)
    return [full] if full.exists() else []
