from pathlib import Path
from typing import Any, Dict, Set

from departments.discovery.tools.shared.file_utils import (
    domains_dir_or_warn,
    load_yaml_safe,
)


def _known_target_audience_ids(workspace_dir: Path) -> Set[str]:
    target_audience = load_yaml_safe(
        workspace_dir / "discovery" / "strategy" / "target_audience.yaml", default={}
    )
    known_ids: Set[str] = set()
    for p in target_audience.get("personas", []) or []:
        if isinstance(p, dict) and p.get("id"):
            known_ids.add(p["id"])
    for m in target_audience.get("machine_personas", []) or []:
        if isinstance(m, dict) and m.get("id"):
            known_ids.add(m["id"])
    return known_ids


def _used_persona_ids(workspace_dir: Path) -> Set[str]:
    used_ids: Set[str] = set()
    domains_dir = domains_dir_or_warn(workspace_dir)
    if domains_dir is None:
        return used_ids
    for domain_dir in sorted(domains_dir.iterdir()):
        if not domain_dir.is_dir():
            continue
        manifest = load_yaml_safe(domain_dir / "manifest.yaml", default=None)
        if manifest is None:
            continue
        for entry in manifest.get("personas_in_scope", []) or []:
            if isinstance(entry, dict) and entry.get("id"):
                used_ids.add(entry["id"])
    return used_ids


def check_persona_consistency(workspace_dir: Path) -> dict:
    """Advisory check: personas/machine_personas from target_audience.yaml that
    are never referenced by any domain's personas_in_scope.

    Referential integrity (unknown persona ids, dangling owning_actor,
    operational_actors drift against domains_manifest.yaml) is enforced as a
    hard gate by the `domain-manifest` linter itself at write time — there's
    no legitimate reason for those to slip through, so they're not
    re-litigated here. Orphaned coverage is different: it can be a deliberate
    scope decision (a persona genuinely doesn't touch any domain), so it's
    left as an advisory read for the agent to judge, not a lint failure.
    """
    orphaned_personas = sorted(
        _known_target_audience_ids(workspace_dir) - _used_persona_ids(workspace_dir)
    )

    result: Dict[str, Any] = {}
    if orphaned_personas:
        result["orphaned_personas"] = orphaned_personas
    return result
