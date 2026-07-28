from departments.discovery.tools.linters.discovery_linter.validators.shared.validation_utils import (
    validate_yaml_file,
)
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path


class Coverage(BaseModel):
    mode: str
    by: Optional[str] = None
    justification: str


class OperationalActor(BaseModel):
    id: str
    name: str
    responsibilities: List[str]
    jtbd_motivations: List[str]
    coverage: Coverage


class DomainItem(BaseModel):
    id: str
    name: str
    description: str
    data_residency: Optional[str] = None
    key_entities: List[str]
    operational_actors: List[OperationalActor] = []


class DomainsManifestSchema(BaseModel):
    strategic_insight: Optional[str] = None
    domains: List[DomainItem]


def run_validation(file_path: Path) -> DomainsManifestSchema:
    return validate_yaml_file(file_path, DomainsManifestSchema)
