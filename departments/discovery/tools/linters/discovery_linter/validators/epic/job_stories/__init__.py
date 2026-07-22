from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from pathlib import Path

from departments.discovery.tools.linters.discovery_linter.validators.shared.validation_utils import (
    validate_yaml_file,
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


def run_validation(file_path: Path, fix: bool = False) -> JobStoriesSchema:
    model = validate_yaml_file(file_path, JobStoriesSchema)

    if len(model.stories) > MAX_STORIES:
        import sys

        print(
            f"Error: Maximum of {MAX_STORIES} Job Stories allowed, found {len(model.stories)}.",
            file=sys.stderr,
        )
        sys.exit(1)

    return model
