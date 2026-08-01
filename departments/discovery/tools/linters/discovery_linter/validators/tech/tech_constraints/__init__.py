from departments.discovery.tools.linters.discovery_linter.validators.shared.validation_utils import (
    validate_yaml_file,
)
from pydantic import BaseModel, Field
from typing import List, Optional, Union
import yaml
from pathlib import Path

StackField = Union[str, List[str]]


class TechnologyStack(BaseModel):
    frontend: Optional[StackField] = None
    backend: Optional[StackField] = None
    database: Optional[StackField] = None
    infrastructure: Optional[StackField] = None
    p2p_network_layer: Optional[StackField] = None
    data_replication_model: Optional[StackField] = None
    cryptographic_identity: Optional[StackField] = None


class ExternalApiCall(BaseModel):
    provider: str
    metric: str
    amount: Union[int, str]


class ResourceQuotas(BaseModel):
    storage_gb: Union[float, str]
    database_reads_per_month: Union[int, str]
    database_writes_per_month: Union[int, str]
    egress_bandwidth_gb: Union[float, str]
    external_api_calls: List[ExternalApiCall]


class GrowthPathEntry(BaseModel):
    component: str
    trigger: str
    action: str
    rewrite_cost: str


class TechConstraintsConfig(BaseModel):
    technology_stack: TechnologyStack
    resource_quotas_per_user: ResourceQuotas
    compliance_flags: List[str]
    growth_path: List[GrowthPathEntry]
    maintainability_notes: str
    strategic_insight: str


class ValidationResult(BaseModel):
    is_valid: bool
    fixed: bool = False
    errors: List[str] = Field(default_factory=list)


def format_tech_data(data: dict) -> dict:
    try:
        # Cast resources
        rq = data.get("resource_quotas_per_user", {})
        for k in ["storage_gb", "egress_bandwidth_gb"]:
            if k in rq:
                rq[k] = float(rq[k])
        for k in ["database_reads_per_month", "database_writes_per_month"]:
            if k in rq:
                rq[k] = int(rq[k])

        calls = rq.get("external_api_calls", [])
        for c in calls:
            if "amount" in c:
                c["amount"] = int(c["amount"])

        # Clean empty nodes
        if not data.get("strategic_insight"):
            data["strategic_insight"] = "N/A"
    except Exception:
        pass
    return data


def run_validation(file_path: Path, fix: bool = True):

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if fix:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if isinstance(data, dict):
            data = format_tech_data(data)
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    return validate_yaml_file(file_path, TechConstraintsConfig)
