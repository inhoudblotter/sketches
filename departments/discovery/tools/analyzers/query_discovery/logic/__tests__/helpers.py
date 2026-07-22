"""Shared fixtures for query_discovery logic tests.

Builds a minimal but structurally valid `workspace/discovery/domains/...`
tree on disk (query_discovery reads real files, not an in-memory model), so
tests exercise the same file-walking code paths as the CLI.
"""

from __future__ import annotations

from pathlib import Path

import yaml


def write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)


def make_domain(
    workspace: Path,
    domain: str,
    *,
    entity: str = "Widget",
    epic_id: str = "core_epic",
    story_id: str = "story-01",
    epic_type: str = "core",
) -> Path:
    """Create one domain with a dictionary, summary, and a single epic/story."""
    domain_dir = workspace / "discovery" / "domains" / domain

    write_yaml(
        domain_dir / "dictionary.yaml",
        {
            "domain": domain,
            "entities": [
                {
                    "name": entity,
                    "description": f"{entity} entity",
                    "type": "AggregateRoot",
                    "attributes": [],
                    "relationships": [],
                }
            ],
        },
    )

    write_yaml(
        domain_dir / "summary.yaml",
        {
            "domain": domain,
            "executive_summary": f"{domain} summary",
            "strategic_trajectory": f"{domain} trajectory",
            "exports": [{"entity": entity, "description": "exported"}],
            "imports": [],
            "domain_metrics": {"kpi": [], "critical_events": []},
            "epics": [
                {
                    "epic_id": epic_id,
                    "focus": f"{epic_id} focus",
                    "is_standard_crud": False,
                }
            ],
        },
    )

    write_yaml(
        domain_dir / "epics" / epic_id / "stories.yaml",
        {
            "epic_type": epic_type,
            "epic_requirements": {"platforms": ["curator_web"]},
            "stories": [
                {
                    "id": story_id,
                    "title": "A story",
                    "pain_level": "High",
                    "is_standard_crud": False,
                    "metrics": [],
                }
            ],
        },
    )

    write_yaml(
        domain_dir / "epics" / epic_id / "features.yaml",
        {
            "features": {
                "mvp_mandatory": [
                    {
                        "id": f"{domain}_feature",
                        "name": "A feature",
                        "linked_job_stories": [story_id],
                    }
                ]
            }
        },
    )

    return domain_dir
