from departments.discovery.tools.linters.discovery_linter.validators.shared.validation_utils import (
    validate_yaml_file,
)
from pydantic import BaseModel
from typing import List
from pathlib import Path


class FeatureItem(BaseModel):
    id: str
    name: str
    linked_job_stories: List[str] = []


class Features(BaseModel):
    mvp_mandatory: List[FeatureItem] = []
    mvp_nice_to_have: List[FeatureItem] = []
    future_features: List[FeatureItem] = []


class FeaturesSchema(BaseModel):
    author_agent: str
    features: Features


def run_validation(file_path: Path) -> FeaturesSchema:
    return validate_yaml_file(file_path, FeaturesSchema)
