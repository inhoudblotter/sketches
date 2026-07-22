from departments.discovery.tools.linters.discovery_linter.validators.shared.validation_utils import (
    validate_yaml_file,
)
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path


class Epic(BaseModel):
    epic_id: str
    focus: str


class ExportedEntity(BaseModel):
    entity: str
    description: str


class ImportedEntity(BaseModel):
    from_domain: str
    entity: str
    reason: str


class KPI(BaseModel):
    name: str
    description: str


class CriticalEvent(BaseModel):
    event_name: str
    business_impact: str


class DomainMetrics(BaseModel):
    kpi: List[KPI]
    critical_events: List[CriticalEvent]


class DomainSummarySchema(BaseModel):
    author_agent: str
    domain: str
    executive_summary: str
    strategic_trajectory: str
    exports: Optional[List[ExportedEntity]] = None
    imports: Optional[List[ImportedEntity]] = None
    epics: List[Epic]
    domain_metrics: DomainMetrics


def run_validation(file_path: Path) -> DomainSummarySchema:
    return validate_yaml_file(file_path, DomainSummarySchema)
