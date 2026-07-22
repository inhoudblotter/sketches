from pathlib import Path
from typing import Optional, Dict, Any

from ...core import load_domain_snapshot
from .registry import build_flow_registry, find_duplicate_flow_ids
from .transitions import find_dangling_transitions, find_dangling_flow_refs
from .entity_coupling import get_entity_coupling


def _check_epic_flows(
    e: Dict[str, Any], d_name: str, lists: dict, registry: Dict[str, Any]
):
    epic_id = e.get("epic_id")
    flows = e.get("flows", [])
    stories = e.get("stories", [])
    story_ids = {s.get("id") for s in stories if s.get("id")}

    complex_story_ids = {
        s.get("id")
        for s in stories
        if s.get("id") and not s.get("is_standard_crud", False)
    }

    if complex_story_ids and not flows:
        lists["epics_without_flows"].append({"domain": d_name, "epic": epic_id})
        if not flows:
            return

    referenced_story_ids = set()
    for flow in flows:
        flow_id = flow.get("flow_id")
        for finding in find_dangling_transitions(flow):
            lists["dangling_transitions"].append(
                {"domain": d_name, "epic": epic_id, "flow": flow_id, **finding}
            )
        for finding in find_dangling_flow_refs(flow, registry):
            lists["dangling_flow_refs"].append(
                {"domain": d_name, "epic": epic_id, "flow": flow_id, **finding}
            )
        linked = flow.get("linked_job_stories", [])
        for s_id in linked:
            if s_id in story_ids:
                referenced_story_ids.add(s_id)
            else:
                lists["orphan_story_refs"].append(
                    {
                        "domain": d_name,
                        "epic": epic_id,
                        "flow": flow_id,
                        "story_id": s_id,
                    }
                )
        has_error = bool(flow.get("shared_states")) or bool(
            flow.get("telemetry_events")
        )
        has_success = bool(flow.get("success_criteria"))
        if not has_error and not has_success:
            lists["low_signal_flows"].append(
                {
                    "domain": d_name,
                    "epic": epic_id,
                    "flow": flow_id,
                    "reason": "no shared_states/telemetry_events and no success_criteria",
                }
            )

    uncovered = complex_story_ids - referenced_story_ids
    if uncovered:
        lists["stories_without_flow_coverage"].append(
            {"domain": d_name, "epic": epic_id, "story_ids": sorted(uncovered)}
        )


def get_flows_self_check(workspace_dir: Path, domain: Optional[str] = None) -> dict:
    idx = load_domain_snapshot(workspace_dir)
    registry = build_flow_registry(idx)
    lists: Any = {
        "epics_without_flows": [],
        "orphan_story_refs": [],
        "stories_without_flow_coverage": [],
        "low_signal_flows": [],
        "dangling_transitions": [],
        "dangling_flow_refs": [],
    }
    for d_name, d_data in idx.get("domains", {}).items():
        if domain and d_name != domain:
            continue
        for e in d_data.get("epics", []):
            _check_epic_flows(e, d_name, lists, registry)
    # Global regardless of --domain, like entity_coupling: collisions and
    # cross-file flow: resolution both need whole-tree visibility.
    lists["duplicate_flow_ids"] = find_duplicate_flow_ids(registry)
    lists["entity_coupling"] = get_entity_coupling(workspace_dir)
    return lists


def get_flows_self_check_summary(
    workspace_dir: Path, domain: Optional[str] = None
) -> dict:
    """Counts only, no per-finding detail — for callers that just need to
    know *whether* something needs attention without risking a large payload
    landing in their context (e.g. tech-lead, which is explicitly barred
    from reading raw flow files for exactly this reason). Callers that need
    to act on specific findings should use get_flows_self_check instead."""
    full = get_flows_self_check(workspace_dir, domain)
    entity_coupling = full.pop("entity_coupling")
    summary: Dict[str, Any] = {key: len(value) for key, value in full.items()}
    summary["entity_coupling_is_valid"] = (
        entity_coupling["is_valid"] if entity_coupling else None
    )
    return summary
