from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from pathlib import Path

from departments.discovery.tools.linters.discovery_linter.validators.shared.validation_utils import (
    validate_yaml_file,
)
from departments.discovery.tools.linters.discovery_linter.validators.shared.io import (
    load_yaml,
)

MAX_STORIES = 30

EpicType = Literal["core", "growth", "monitoring", "promo"]
PainLevel = Literal["Critical", "High", "Medium", "Low"]


class EpicRequirements(BaseModel):
    platforms: List[str]
    is_headless: bool
    offline_first: bool
    events_to_handle: List[str]
    business_constraints: List[str]


class Story(BaseModel):
    id: str
    title: str
    situation: str
    motivation: str
    outcome: str
    actor_id: str
    pain_level: PainLevel
    metrics: List[str]
    is_standard_crud: Optional[bool] = False


class JobStoriesSchema(BaseModel):
    author_agent: str
    domain: str
    epic: str
    epic_type: EpicType
    description: str = ""
    epic_requirements: EpicRequirements
    stories: List[Story] = Field(..., max_length=30)


def _known_actor_ids(domain_dir: Path) -> Optional[set]:
    """Returns the set of valid `actor_id`s for this domain (Actor Source of
    Truth: personas_in_scope[].id ∪ operational_actors[].id from manifest.yaml),
    or None if manifest.yaml is missing/unreadable — the check is skipped, not
    failed, in that case (e.g. isolated unit-test fixtures)."""
    manifest = load_yaml(domain_dir / "manifest.yaml")
    if not manifest:
        return None
    ids = {
        p.get("id")
        for p in manifest.get("personas_in_scope", []) or []
        if isinstance(p, dict) and p.get("id")
    }
    ids |= {
        a.get("id")
        for a in manifest.get("operational_actors", []) or []
        if isinstance(a, dict) and a.get("id")
    }
    return ids


def run_validation(file_path: Path, fix: bool = False) -> JobStoriesSchema:
    model = validate_yaml_file(file_path, JobStoriesSchema)

    if len(model.stories) > MAX_STORIES:
        import sys

        print(
            f"Error: Maximum of {MAX_STORIES} Job Stories allowed, found {len(model.stories)}.",
            file=sys.stderr,
        )
        sys.exit(1)

    # file_path: workspace/discovery/domains/{domain}/epics/{epic}/stories.yaml
    known_actor_ids = _known_actor_ids(file_path.parent.parent)
    if known_actor_ids:
        unknown = sorted({s.actor_id for s in model.stories} - known_actor_ids)
        if unknown:
            raise ValueError(
                f"stories.actor_id не резолвится в personas_in_scope/operational_actors "
                f"этого домена manifest.yaml: {unknown}"
            )

    return model
