import re
import yaml
from pathlib import Path
from typing import List, Dict, Any, Set

from departments.discovery.tools.shared.file_utils import load_yaml, domains_dir_or_warn
from departments.discovery.tools.shared.epic_utils import iter_epic_feature_files


def trace_source(workspace_dir: Path, source_ref: str) -> dict:
    """Find all files in workspace/discovery/ that reference the source (e.g. market_context.md#L54)"""
    discovery_dir = workspace_dir / "discovery"
    res: Dict[str, Any] = {}

    if not discovery_dir.exists():
        return res

    # Search in strategy and domains
    for f in discovery_dir.rglob("*.yaml"):
        with open(f, "r", encoding="utf-8") as file:
            lines = file.readlines()
            for i, line in enumerate(lines):
                if source_ref in line:
                    rel_path = str(f.relative_to(workspace_dir))
                    if rel_path not in res:
                        res[rel_path] = []
                    res[rel_path].append(
                        {"line_number": i + 1, "content": line.strip()}
                    )
    return res


def _extract_markdown_links(text: str) -> List[str]:
    # Matches [filename.ext#L123] or [filename.ext#L123-L125]
    pattern = r"\[([a-zA-Z0-9_\-]+\.(?:md|yaml|py)#[a-zA-Z0-9_\-]+)\]"
    return re.findall(pattern, text)


def _find_feature(domains_dir: Path, feature_id: str):
    for domain_dir in domains_dir.iterdir():
        if not domain_dir.is_dir():
            continue

        for _feat_file, data in iter_epic_feature_files(domain_dir):
            for _bucket, features in data.get("features", {}).items():
                if isinstance(features, list):
                    for feat in features:
                        if feat.get("id") == feature_id:
                            return feat, domain_dir
    return None, None


def _find_linked_stories(
    target_domain: Path, linked_stories: list, extracted_rationale_links: set
) -> list:
    res_linked = []
    stories_file = target_domain / "epics"
    if stories_file.exists():
        for epic_dir in stories_file.iterdir():
            if not epic_dir.is_dir():
                continue
            sf = epic_dir / "stories.yaml"
            if not sf.exists():
                continue

            s_data = load_yaml(sf)

            for story in s_data.get("stories", []):
                if story.get("id") in linked_stories:
                    res_linked.append(story.get("id"))
                    story_str = yaml.dump(story, allow_unicode=True)
                    for link in _extract_markdown_links(story_str):
                        extracted_rationale_links.add(link)
    return res_linked


def trace_feature(workspace_dir: Path, feature_id: str) -> dict:
    """Trace a feature back to its job stories and extract markdown links (rationale)."""
    domains_dir = domains_dir_or_warn(workspace_dir)
    extracted_rationale_links: Set[str] = set()

    if domains_dir is None:
        return {"error": f"Feature {feature_id} not found."}

    target_feature, target_domain = _find_feature(domains_dir, feature_id)

    if not target_feature:
        return {"error": f"Feature {feature_id} not found."}

    res: Dict[str, Any] = {
        "feature_id": feature_id,
        "found_in_domain": target_domain.name,
        "linked_stories": [],
    }
    res["feature_name"] = target_feature.get("name")

    # Extract links from feature itself
    feat_str = yaml.dump(target_feature, allow_unicode=True)
    for link in _extract_markdown_links(feat_str):
        extracted_rationale_links.add(link)

    # 2. Find linked job stories
    linked_stories = target_feature.get("linked_job_stories", [])

    if not linked_stories:
        res["extracted_rationale_links"] = sorted(extracted_rationale_links)
        return res

    res["linked_stories"] = _find_linked_stories(
        target_domain, linked_stories, extracted_rationale_links
    )
    res["extracted_rationale_links"] = sorted(extracted_rationale_links)
    return res
