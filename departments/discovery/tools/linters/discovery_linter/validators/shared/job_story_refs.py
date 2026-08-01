from pathlib import Path
from typing import Set

from departments.discovery.tools.linters.discovery_linter.validators.shared.io import (
    load_yaml,
)


def resolve_workspace_dir(strategy_or_research_file: Path, levels_up: int) -> Path:
    """Walks up from a file under workspace/discovery/... to the workspace/ root.
    levels_up=3 for workspace/discovery/strategy/<file>,
    levels_up=4 for workspace/discovery/research/technical-context/<file>."""
    d = strategy_or_research_file
    for _ in range(levels_up):
        d = d.parent
    return d


def all_job_story_ids(workspace_dir: Path) -> Set[str]:
    """Scans every domains/*/epics/*/stories.yaml under workspace_dir and returns
    the set of all Job Story IDs across the whole project. Returns an empty set
    (skip the check, don't fail) if no domains dir is present — e.g. isolated
    unit-test fixtures without a full workspace."""
    domains_dir = workspace_dir / "discovery" / "domains"
    if not domains_dir.is_dir():
        return set()

    ids: Set[str] = set()
    for stories_file in domains_dir.glob("*/epics/*/stories.yaml"):
        data = load_yaml(stories_file)
        if not data:
            continue
        for story in data.get("stories", []) or []:
            if isinstance(story, dict) and story.get("id"):
                ids.add(story["id"])
    return ids


def unknown_refs(job_story_refs: list, known_ids: Set[str]) -> list:
    """known_ids empty means the check was skipped (no workspace found) —
    treat every ref as fine rather than reporting false positives."""
    if not known_ids:
        return []
    return [r for r in job_story_refs if r not in known_ids]
