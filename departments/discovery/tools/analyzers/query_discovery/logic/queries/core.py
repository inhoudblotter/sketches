from pathlib import Path
from ..core import load_domain_snapshot
from typing import Optional, Dict, Any, Set


def _get_story_priorities(
    idx: Dict[str, Any], domain: Optional[str]
) -> Dict[str, Set[str]]:
    story_priorities: Dict[str, Set[str]] = {}
    for d_name, d_data in idx.get("domains", {}).items():
        if domain and d_name != domain:
            continue
        features_dict = d_data.get("features", {})
        for p_name, p_features in features_dict.items():
            if isinstance(p_features, list):
                for f in p_features:
                    for l_id in f.get("linked_job_stories", []):
                        story_priorities.setdefault(l_id, set()).add(p_name.lower())
    return story_priorities


def _filter_stories_in_epic(
    e: Dict[str, Any],
    d_name: str,
    pain_level: Optional[str],
    priority: Optional[str],
    only_metrics: bool,
    story_priorities: Dict[str, Set[str]],
) -> list:
    res = []
    est_by_id = {
        est.get("story_id"): est
        for est in e.get("estimation", [])
        if est.get("story_id")
    }
    for s in e.get("stories", []):
        pl = s.get("pain_level", "unknown")
        if pain_level and pl.lower() != pain_level.lower():
            continue
        if priority:
            s_id = s.get("id")
            if not s_id or priority.lower() not in story_priorities.get(s_id, set()):
                continue
        if only_metrics:
            res.append(
                {
                    "story_id": s.get("id"),
                    "metrics": s.get("metrics", []),
                    "_domain": d_name,
                    "_epic": e.get("epic_id"),
                }
            )
        else:
            story_copy = dict(s)
            story_copy["_domain"] = d_name
            story_copy["_epic"] = e.get("epic_id")
            story_id = s.get("id")
            if story_id in est_by_id:
                est = est_by_id[story_id]
                story_copy["story_points"] = est.get("story_points", 0)
                story_copy["flags"] = list(est.get("flags", {}).keys())
            res.append(story_copy)
    return res


def get_filtered_stories(
    workspace_dir: Path,
    domain: Optional[str] = None,
    pain_level: Optional[str] = None,
    priority: Optional[str] = None,
    epic_type: Optional[str] = None,
    only_metrics: bool = False,
) -> list:
    idx = load_domain_snapshot(workspace_dir)
    res = []
    story_priorities = _get_story_priorities(idx, domain) if priority else {}

    for d_name, d_data in idx.get("domains", {}).items():
        if domain and d_name != domain:
            continue
        for e in d_data.get("epics", []):
            if epic_type and e.get("epic_type", "core").lower() != epic_type.lower():
                continue
            res.extend(
                _filter_stories_in_epic(
                    e, d_name, pain_level, priority, only_metrics, story_priorities
                )
            )
    return res


def get_slice(workspace_dir: Path, domain: str, section: str) -> dict:
    idx = load_domain_snapshot(workspace_dir)
    if domain not in idx.get("domains", {}):
        return {"error": f"Domain {domain} not found"}
    domain_data = idx["domains"][domain]
    if section not in domain_data:
        return {"error": f"Section {section} not found in domain {domain}"}
    return {section: domain_data[section]}


def _get_story_attrs(idx: Dict[str, Any], domain: Optional[str]) -> tuple:
    story_pain_levels = {}
    story_epic_types = {}
    for d_name, d_data in idx.get("domains", {}).items():
        if domain and d_name != domain:
            continue
        for e in d_data.get("epics", []):
            for s in e.get("stories", []):
                s_id = s.get("id")
                if s_id:
                    story_pain_levels[s_id] = s.get("pain_level", "unknown")
                    story_epic_types[s_id] = e.get("epic_type", "core")
    return story_pain_levels, story_epic_types


def _feature_matches(
    feature: dict,
    pain_level: Optional[str],
    epic_type: Optional[str],
    story_pain_levels: Dict[str, str],
    story_epic_types: Dict[str, str],
) -> bool:
    linked = feature.get("linked_job_stories", [])
    if pain_level and not any(
        story_pain_levels.get(l_id, "").lower() == pain_level.lower() for l_id in linked
    ):
        return False
    return not (
        epic_type
        and not any(
            story_epic_types.get(l_id, "core").lower() == epic_type.lower()
            for l_id in linked
        )
    )


def get_filtered_features(
    workspace_dir: Path,
    domain: Optional[str] = None,
    priority: Optional[str] = None,
    pain_level: Optional[str] = None,
    epic_type: Optional[str] = None,
) -> list:
    idx = load_domain_snapshot(workspace_dir)
    res = []
    story_pain_levels, story_epic_types = (
        _get_story_attrs(idx, domain) if (pain_level or epic_type) else ({}, {})
    )

    for d_name, d_data in idx.get("domains", {}).items():
        if domain and d_name != domain:
            continue
        features_dict = d_data.get("features", {})
        for p_name, p_features in features_dict.items():
            if priority and p_name.lower() != priority.lower():
                continue
            if not isinstance(p_features, list):
                continue
            for f in p_features:
                if not _feature_matches(
                    f, pain_level, epic_type, story_pain_levels, story_epic_types
                ):
                    continue
                feature_copy = dict(f)
                feature_copy["_domain"] = d_name
                feature_copy["_priority"] = p_name
                res.append(feature_copy)
    return res


def _epic_is_crud(epic: dict) -> bool:
    stories = epic.get("stories", [])
    if not stories:
        return epic.get("is_standard_crud", False)
    return all(s.get("is_standard_crud", False) for s in stories)


def _epic_matches_filters(
    epic: dict,
    is_crud: bool,
    crud_only: bool,
    complex_only: bool,
    epic_type: Optional[str],
) -> bool:
    if crud_only and not is_crud:
        return False
    if complex_only and is_crud:
        return False
    return not epic_type or epic.get("epic_type", "core").lower() == epic_type.lower()


def _strip_epic_details(epic: dict, domain_name: str) -> dict:
    epic_copy = dict(epic)
    epic_copy["_domain"] = domain_name
    for key in ("stories", "estimation", "flows"):
        epic_copy.pop(key, None)
    return epic_copy


def get_filtered_epics(
    workspace_dir: Path,
    domain: Optional[str] = None,
    crud_only: bool = False,
    complex_only: bool = False,
    epic_type: Optional[str] = None,
) -> list:
    idx = load_domain_snapshot(workspace_dir)
    res = []
    for d_name, d_data in idx.get("domains", {}).items():
        if domain and d_name != domain:
            continue
        for e in d_data.get("epics", []):
            is_crud = _epic_is_crud(e)
            if not _epic_matches_filters(
                e, is_crud, crud_only, complex_only, epic_type
            ):
                continue
            res.append(_strip_epic_details(e, d_name))
    return res
