from pathlib import Path
from typing import Any, Dict, Set

from ..core import load_yaml, load_domain_snapshot


def _domain_platforms(workspace_dir: Path, domain: str) -> Set[str]:
    manifest = load_yaml(
        workspace_dir / "discovery" / "domains" / domain / "manifest.yaml"
    )
    return set(manifest.get("platforms", []))


def _domain_story_ids(idx: Dict[str, Any], domain: str) -> Set[str]:
    story_ids: Set[str] = set()
    d_data = idx.get("domains", {}).get(domain, {})
    for epic in d_data.get("epics", []):
        for story in epic.get("stories", []):
            story_id = story.get("id")
            if story_id:
                story_ids.add(story_id)
    return story_ids


def _refs_intersect(entry: Dict[str, Any], story_ids: Set[str]) -> bool:
    refs = entry.get("job_story_refs", [])
    if not refs:
        # Записи без job_story_refs — глобальные, не привязаны к конкретному домену.
        return True
    return any(r in story_ids for r in refs)


def get_ux_constraints_for_domain(workspace_dir: Path, domain: str) -> dict:
    """Механический фильтр ux_research.yaml + ux_constraints.yaml под конкретный домен
    (PIT-17, Zero-Value Synthesis Pass) — платформы домена берутся из manifest.yaml,
    job_story_refs — из stories.yaml всех эпиков домена. Никакого LLM-пересказа, только
    отбор уже готовых структурных записей."""
    platforms = _domain_platforms(workspace_dir, domain)
    idx = load_domain_snapshot(workspace_dir)
    story_ids = _domain_story_ids(idx, domain)

    research = load_yaml(
        workspace_dir
        / "discovery"
        / "research"
        / "technical-context"
        / "ux_research.yaml"
    )
    constraints = load_yaml(
        workspace_dir / "discovery" / "strategy" / "ux_constraints.yaml"
    )

    by_platform = {
        platform_id: data
        for platform_id, data in research.get("by_platform", {}).items()
        if platform_id in platforms
    }
    interaction_patterns = [
        entry
        for entry in research.get("interaction_patterns", [])
        if _refs_intersect(entry, story_ids)
    ]
    known_pitfalls = [
        entry
        for entry in research.get("known_pitfalls", [])
        if _refs_intersect(entry, story_ids)
    ]
    overrides = [
        entry
        for entry in constraints.get("overrides", [])
        if _refs_intersect(entry, story_ids)
    ]

    return {
        "domain": domain,
        "by_platform": by_platform,
        "interaction_patterns": interaction_patterns,
        "known_pitfalls": known_pitfalls,
        "overrides": overrides,
    }
