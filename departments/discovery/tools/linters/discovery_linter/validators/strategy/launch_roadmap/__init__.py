from departments.discovery.tools.linters.discovery_linter.validators.shared.validation_utils import (
    validate_yaml_file,
)
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
from .validators.rules import validate_roadmap_data


class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []


class RoadmapMetadata(BaseModel):
    generated_by: str
    last_updated: str


class RoadmapPhase(BaseModel):
    source_ref: str
    description: str
    unit_economics_validation: str
    primary_growth_loop: Optional[List[str]] = None
    cold_start_tactics: Optional[List[str]] = None
    friction_management: Optional[List[str]] = None
    ecosystem_symbiosis: Optional[List[str]] = None
    defensibility_moats: Optional[List[str]] = None


class RoadmapPhases(BaseModel):
    demo_prototype: RoadmapPhase
    seed_mvp: RoadmapPhase
    v1_scale: RoadmapPhase


class LaunchRoadmapSchema(BaseModel):
    metadata: RoadmapMetadata
    phases: RoadmapPhases


def run_validation(file_path: Path, fix: bool = False):

    model = validate_yaml_file(file_path, LaunchRoadmapSchema)
    # custom logic
    is_valid, errors, warnings = validate_roadmap_data(model.model_dump())
    if not is_valid:
        raise ValueError(f"Roadmap validation failed: {errors}")
    return model
