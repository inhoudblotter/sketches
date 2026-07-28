from pathlib import Path
from typing import Any, Dict, List

from departments.discovery.tools.shared.file_utils import load_yaml_safe

from .queries.core import get_filtered_stories


def get_team_functions(workspace_dir: Path) -> dict:
    """Compact aggregated read for ops-scout: for every FTE operational_actor
    declared in domains_manifest.yaml (the canonical registry), collect the
    Job Stories written for them across their domain in one call — replacing
    what would otherwise be one `stories --actor` lookup per role.

    Non-fte actors (coverage.mode in ai_agent/dao_delegate/workflow/algorithm)
    are omitted: their function is already covered by automation, so they
    carry no headcount and are out of scope for ops-scout's Functional
    Coverage Matrix.
    """
    domains_manifest = load_yaml_safe(
        workspace_dir / "discovery" / "meta" / "domains_manifest.yaml", default={}
    )

    result: Dict[str, Any] = {}
    for d in domains_manifest.get("domains", []) or []:
        if not isinstance(d, dict):
            continue
        domain_id = d.get("id")
        fte_actors = [
            a
            for a in d.get("operational_actors", []) or []
            if isinstance(a, dict) and (a.get("coverage") or {}).get("mode") == "fte"
        ]
        if not domain_id or not fte_actors:
            continue

        domain_entry: Dict[str, Any] = {}
        for actor in fte_actors:
            actor_id = actor.get("id")
            if not actor_id:
                continue
            stories: List[dict] = get_filtered_stories(
                workspace_dir, domain=domain_id, actor=actor_id
            )
            domain_entry[actor_id] = {
                "name": actor.get("name"),
                "responsibilities": actor.get("responsibilities", []),
                "jtbd_motivations": actor.get("jtbd_motivations", []),
                "stories": [
                    {
                        "id": s.get("id"),
                        "title": s.get("title"),
                        "epic": s.get("_epic"),
                        "pain_level": s.get("pain_level"),
                    }
                    for s in stories
                ],
            }
        if domain_entry:
            result[domain_id] = domain_entry

    return result
