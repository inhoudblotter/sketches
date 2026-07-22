from pathlib import Path
from typing import Dict, Any

from departments.discovery.tools.shared.file_utils import (
    load_yaml as _shared_load_yaml,
    domains_dir_or_warn,
)
from departments.discovery.tools.shared.epic_utils import iter_epic_feature_files

# T-shirt-size пороги по сумме story_points эпика/домена — качественный,
# человеко-понятный сигнал объёма работ для инвесторов (см. плейбук
# departments/discovery/playbooks/skill-tech-estimation.md). Намеренно не
# переводится в токены/деньги: на этапе discovery для этого нет данных
# (реальные прогоны появятся позже, в архитектуре/девопсе/разработке).
SIZE_BUCKET_THRESHOLDS = [
    (3, "XS"),
    (8, "S"),
    (20, "M"),
    (40, "L"),
    (80, "XL"),
]
SIZE_BUCKET_OVERFLOW = "XXL"

MVP_SIZE_BUCKET_THRESHOLDS = [
    (150, "S", "LEAN MVP"),
    (300, "M", "STANDARD MVP"),
    (600, "L", "HEAVY MVP"),
    (1000, "XL", "ENTERPRISE"),
]
MVP_SIZE_BUCKET_OVERFLOW = ("XXL", "MONOLITH")


def size_bucket_for_points(total_story_points: int) -> str:
    for threshold, label in SIZE_BUCKET_THRESHOLDS:
        if total_story_points <= threshold:
            return label
    return SIZE_BUCKET_OVERFLOW


def mvp_size_bucket_for_points(total_story_points: int) -> tuple[str, str]:
    for threshold, size, desc in MVP_SIZE_BUCKET_THRESHOLDS:
        if total_story_points <= threshold:
            return size, desc
    return MVP_SIZE_BUCKET_OVERFLOW


def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    return _shared_load_yaml(path)


def _load_epic_data(domain_dir: Path, epic: dict):
    epic_id = epic.get("epic_id")
    if not epic_id:
        return

    stories_path = domain_dir / "epics" / epic_id / "stories.yaml"
    if stories_path.exists():
        stories = load_yaml(stories_path)
        if stories:
            epic["stories"] = stories.get("stories", [])
            epic["requirements"] = stories.get("epic_requirements", {})
            epic["epic_type"] = stories.get("epic_type", "core")
    else:
        epic["stories"] = []

    flows_dir = domain_dir / "epics" / epic_id / "flows"
    epic["flows"] = []
    if flows_dir.is_dir():
        for flow_file in sorted(flows_dir.glob("*.yaml")):
            flow = load_yaml(flow_file)
            if flow:
                epic["flows"].append(flow)

    estimation_path = domain_dir / "epics" / epic_id / "estimation.yaml"
    epic["estimation"] = []
    if estimation_path.exists():
        estimation = load_yaml(estimation_path)
        if estimation:
            epic["estimation"] = estimation.get("estimations", [])


def _load_domain_data(domain_dir: Path) -> dict:
    domain_data: Dict[str, Any] = {}
    summary = load_yaml(domain_dir / "summary.yaml")
    domain_data["_summary_present"] = bool(summary)
    if summary:
        domain_data["executive_summary"] = summary.get("executive_summary", "")
        domain_data["strategic_trajectory"] = summary.get("strategic_trajectory", "")
        domain_data["exports"] = summary.get("exports", [])
        domain_data["imports"] = summary.get("imports", [])
        domain_data["domain_metrics"] = summary.get("domain_metrics", {})
        epics = summary.get("epics", [])
        for epic in epics:
            _load_epic_data(domain_dir, epic)
        domain_data["epics"] = epics

    merged_features: Dict[str, Any] = {}
    for _feat_file, features in iter_epic_feature_files(domain_dir):
        if not features:
            continue
        for bucket, items in features.get("features", {}).items():
            if isinstance(items, list):
                merged_features.setdefault(bucket, []).extend(items)
    if merged_features:
        domain_data["features"] = merged_features
    return domain_data


def load_domain_snapshot(workspace_dir: Path) -> dict:
    idx: Dict[str, Any] = {"domains": {}}
    domains_dir = domains_dir_or_warn(workspace_dir)
    if domains_dir is None:
        return idx

    for domain_dir in domains_dir.iterdir():
        if not domain_dir.is_dir():
            continue
        domain_data = _load_domain_data(domain_dir)
        if domain_data:
            idx["domains"][domain_dir.name] = domain_data

    return idx
