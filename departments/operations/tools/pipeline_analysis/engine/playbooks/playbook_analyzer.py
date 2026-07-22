"""Resolve cross-references between playbooks (`skill-*.md` files linking each
other via backtick mentions, e.g. "Опираясь на `skill-blue-ocean-strategy.md`")
so that context-load and Playbook Analytics account for transitively-loaded
playbooks, not just the ones an agent's frontmatter explicitly lists."""

from __future__ import annotations
import re
from pathlib import Path

_REF_RE = re.compile(r"skill-[\w-]+\.md")


def parse_references(playbook_path: str, project_root: Path) -> list[str]:
    """Return sibling playbook paths referenced by this playbook's body."""
    p = Path(playbook_path)
    if not p.is_absolute():
        p = project_root / playbook_path
    if not p.exists():
        return []
    try:
        text = p.read_text(encoding="utf-8")
    except Exception:
        return []

    refs = []
    for match in _REF_RE.findall(text):
        if match == p.name:
            continue
        candidate = p.parent / match
        ref_path = str(Path(playbook_path).parent / match)
        if candidate.exists() and ref_path not in refs:
            refs.append(ref_path)
    return refs


def resolve_all_references(
    playbook_paths: list[str], project_root: Path
) -> dict[str, list[str]]:
    """Return {playbook_path: [direct references]} for every known playbook."""
    return {p: parse_references(p, project_root) for p in playbook_paths}


def transitive_closure(start: list[str], project_root: Path) -> set[str]:
    """All playbooks reachable from `start` via reference chains, resolved lazily
    (each hop parses the newly-discovered playbook's own body for further
    references), excluding the `start` set itself."""
    seen: set[str] = set()
    queue = list(start)
    while queue:
        curr = queue.pop()
        for ref in parse_references(curr, project_root):
            if ref not in seen and ref not in start:
                seen.add(ref)
                queue.append(ref)
    return seen
