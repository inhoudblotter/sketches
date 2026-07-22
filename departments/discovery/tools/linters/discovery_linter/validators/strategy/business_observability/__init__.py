from departments.discovery.tools.linters.discovery_linter.validators.shared.validation_utils import (
    validate_yaml_file,
)
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path


class KPI(BaseModel):
    id: str
    name: str
    description: str


class Event(BaseModel):
    event_name: str
    business_impact: str


class Transparency(BaseModel):
    need: str


class Scaling(BaseModel):
    trigger: str
    action: str


class BusinessObservabilitySchema(BaseModel):
    north_star_metric: str
    kpi: List[KPI]
    network_health_metrics: Optional[List[KPI]] = None
    critical_business_events: List[Event]
    transparency_needs: List[Transparency]
    business_scaling_triggers: List[Scaling]


def run_validation(file_path: Path) -> BusinessObservabilitySchema:
    return validate_yaml_file(file_path, BusinessObservabilitySchema)
