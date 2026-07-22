import pytest
import yaml
from pathlib import Path

from departments.discovery.tools.linters.discovery_linter.validators.domain.domain_orphans import (
    run_check_domain_orphans,
)


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


def _build_domain(domain_dir: Path, epic_id="growth", story_id="story-01") -> None:
    _write_yaml(domain_dir / "summary.yaml", {"epics": [{"epic_id": epic_id}]})
    _write_yaml(
        domain_dir / "epics" / epic_id / "stories.yaml",
        {"stories": [{"id": story_id}]},
    )
    _write_yaml(
        domain_dir / "epics" / epic_id / "features.yaml",
        {
            "features": {
                "mvp_mandatory": [
                    {"id": "f1", "name": "Feature 1", "linked_job_stories": [story_id]}
                ]
            }
        },
    )


def test_valid_domain_has_no_orphans(tmp_path: Path):
    domain_dir = tmp_path / "billing"
    _build_domain(domain_dir)

    # Should not raise for a fully consistent domain.
    run_check_domain_orphans(domain_dir)


def test_dangling_linked_job_story_reference_is_detected(tmp_path: Path):
    # Regression test: features.yaml lives per-epic at
    # epics/{epic}/features.yaml, not at domain_dir/features.yaml, and the
    # actual feature list is nested under a top-level "features" key. The
    # orphan checker previously looked at the wrong path/shape and silently
    # never found any linked_job_stories references, so dangling references
    # went undetected.
    domain_dir = tmp_path / "billing"
    _build_domain(domain_dir)

    features_file = domain_dir / "epics" / "growth" / "features.yaml"
    data = yaml.safe_load(features_file.read_text(encoding="utf-8"))
    data["features"]["mvp_mandatory"][0]["linked_job_stories"] = ["does-not-exist"]
    _write_yaml(features_file, data)

    with pytest.raises(ValueError, match="Dangling linked_job_stories"):
        run_check_domain_orphans(domain_dir)


def test_orphaned_epic_directory_is_detected(tmp_path: Path):
    domain_dir = tmp_path / "billing"
    _build_domain(domain_dir)

    # An epic dir that exists on disk but is referenced by neither
    # summary.yaml nor any feature's linked_job_stories.
    _write_yaml(
        domain_dir / "epics" / "orphan_epic" / "stories.yaml",
        {"stories": []},
    )

    with pytest.raises(ValueError, match="Orphaned job stories"):
        run_check_domain_orphans(domain_dir)
