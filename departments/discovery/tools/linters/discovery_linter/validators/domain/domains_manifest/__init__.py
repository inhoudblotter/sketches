from departments.discovery.tools.linters.discovery_linter.validators.shared.validation_utils import (
    validate_yaml_file,
)
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path


class DomainItem(BaseModel):
    id: str
    name: str
    description: str
    data_residency: Optional[str] = None
    target_roles: List[str]
    key_entities: List[str]


class DomainsManifestSchema(BaseModel):
    strategic_insight: Optional[str] = None
    domains: List[DomainItem]


def run_validation(file_path: Path) -> DomainsManifestSchema:
    return validate_yaml_file(file_path, DomainsManifestSchema)
