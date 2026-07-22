from pathlib import Path
from typing import Optional, Dict, Any, List

from ...core import load_domain_snapshot, size_bucket_for_points


def _process_epic_estimation(e: Dict[str, Any]) -> dict:
    estimations = e.get("estimation", [])
    story_ids = {s.get("id") for s in e.get("stories", [])}
    estimated_ids = {est.get("story_id") for est in estimations}
    story_points_list = [
        est.get("story_points") for est in estimations if est.get("story_points")
    ]
    total_points = sum(story_points_list)
    missing = sorted(story_ids - estimated_ids)
    return {
        "total_story_points": total_points,
        "size_bucket": size_bucket_for_points(total_points),
        "story_count": len(story_ids),
        "estimated_count": len(estimated_ids),
        "missing_estimation": missing,
        "fully_uncovered": bool(story_ids) and not estimated_ids,
        "flagged": [
            {
                "story_id": est.get("story_id"),
                "flags": list(est.get("flags", {}).keys()),
            }
            for est in estimations
            if est.get("flags")
        ],
    }


def get_estimation_summary(
    workspace_dir: Path,
    domain: Optional[str] = None,
    epic: Optional[str] = None,
    is_global: bool = False,
) -> dict:
    idx = load_domain_snapshot(workspace_dir)
    res: Dict[str, Any] = {}
    for d_name, d_data in idx.get("domains", {}).items():
        if domain and d_name != domain:
            continue
        for e in d_data.get("epics", []):
            epic_id = e.get("epic_id")
            if epic and epic_id != epic:
                continue
            res.setdefault(d_name, {})[epic_id] = _process_epic_estimation(e)

    if not is_global:
        return res

    total_story_points = 0
    total_missing: List[str] = []
    uncovered_epics: List[str] = []
    total_flagged: List[Dict[str, Any]] = []
    for d_name, epics in res.items():
        for epic_id, summary in epics.items():
            total_story_points += summary["total_story_points"]
            total_missing.extend(
                f"{d_name}/{epic_id}/{s_id}" for s_id in summary["missing_estimation"]
            )
            if summary["fully_uncovered"]:
                uncovered_epics.append(f"{d_name}/{epic_id}")
            total_flagged.extend(
                {"domain": d_name, "epic": epic_id, **flag}
                for flag in summary["flagged"]
            )

    return {
        "total_story_points": total_story_points,
        "size_bucket": size_bucket_for_points(total_story_points),
        "missing_estimation": total_missing,
        "uncovered_epics": uncovered_epics,
        "flagged": total_flagged,
        "by_domain": res,
    }
