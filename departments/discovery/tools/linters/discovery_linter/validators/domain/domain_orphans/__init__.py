import yaml
from pathlib import Path

from departments.discovery.tools.shared.epic_utils import (
    iter_epic_dirs,
    iter_epic_feature_files,
)

FEATURE_SECTIONS = ["mvp_mandatory", "mvp_nice_to_have", "future_features"]


def _load_summary_epics(domain_dir: Path) -> set:
    summary_file = domain_dir / "summary.yaml"
    if not summary_file.exists():
        return set()
    with summary_file.open("r", encoding="utf-8") as f:
        try:
            summary = yaml.safe_load(f) or {}
        except Exception:
            return set()
    return {epic["epic_id"] for epic in summary.get("epics", []) if "epic_id" in epic}


def _load_story_to_epic(domain_dir: Path) -> dict:
    story_to_epic = {}
    for epic_dir in iter_epic_dirs(domain_dir):
        stories_file = epic_dir / "stories.yaml"
        if not stories_file.exists():
            continue
        with stories_file.open("r", encoding="utf-8") as f:
            try:
                data = yaml.safe_load(f) or {}
            except Exception:
                continue
            stories = data.get("stories", []) if isinstance(data, dict) else data
            for s in stories:
                if isinstance(s, dict) and "id" in s:
                    story_to_epic[s["id"]] = epic_dir.name
    return story_to_epic


def _load_feature_epic_refs(domain_dir: Path, story_to_epic: dict) -> tuple[set, set]:
    feature_epics = set()
    dangling_story_refs = set()

    # features.yaml lives per-epic (epics/{epic}/features.yaml), not once per
    # domain, so every epic's file must be walked to find all references.
    for _features_file, data in iter_epic_feature_files(domain_dir):
        features = data.get("features", {})
        for section in FEATURE_SECTIONS:
            for feature in features.get(section, []):
                for s_id in feature.get("linked_job_stories", []):
                    if s_id in story_to_epic:
                        feature_epics.add(story_to_epic[s_id])
                    else:
                        dangling_story_refs.add(s_id)

    return feature_epics, dangling_story_refs


def _build_orphan_errors(
    orphans: set, dangling: set, dangling_story_refs: set
) -> list[str]:
    errors = []
    if orphans:
        errors.append(
            f"Orphaned job stories found (files exist but not referenced in summary/features): {', '.join(orphans)}"
        )
    if dangling:
        errors.append(
            f"Dangling epics found (declared in summary.yaml but file is missing): {', '.join(dangling)}"
        )
    if dangling_story_refs:
        # A feature's linked_job_stories pointing at a non-existent story id is
        # silently dropped by downstream SP aggregation (build_project_analytics
        # treats it as 0 SP) instead of erroring, which quietly deflates the
        # MVP budget the pitcher later stress-tests — so it must fail loud here.
        errors.append(
            f"Dangling linked_job_stories references (feature points at a story id that does not exist): {', '.join(sorted(dangling_story_refs))}"
        )
    return errors


def run_check_domain_orphans(domain_dir: Path):
    epics_dir = domain_dir / "epics"
    if not epics_dir.exists() or not epics_dir.is_dir():
        return

    summary_file = domain_dir / "summary.yaml"
    if not summary_file.exists():
        raise ValueError("summary.yaml missing/not found")

    physical_epics = {f.name for f in iter_epic_dirs(domain_dir)}
    summary_epics = _load_summary_epics(domain_dir)
    story_to_epic = _load_story_to_epic(domain_dir)
    feature_epics, dangling_story_refs = _load_feature_epic_refs(
        domain_dir, story_to_epic
    )

    orphans = physical_epics - summary_epics - feature_epics
    dangling = summary_epics - physical_epics

    errors = _build_orphan_errors(orphans, dangling, dangling_story_refs)
    if errors:
        raise ValueError("\n".join(errors))
