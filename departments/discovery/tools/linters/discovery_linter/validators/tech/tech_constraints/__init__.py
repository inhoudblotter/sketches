from departments.discovery.tools.linters.discovery_linter.validators.shared.validation_utils import (
    validate_yaml_file,
)
from departments.discovery.tools.shared.epic_utils import iter_epic_feature_files
from pydantic import BaseModel, Field
from typing import List, Optional, Set, Union
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


class DataSourcingEntry(BaseModel):
    domain: str
    feature_id: str
    feature_name: str
    automation_verdict: str
    moderation_signal: str
    legal_flags: List[str] = Field(default_factory=list)


class TechConstraintsConfig(BaseModel):
    technology_stack: TechnologyStack
    resource_quotas_per_user: ResourceQuotas
    compliance_flags: List[str]
    growth_path: List[GrowthPathEntry]
    maintainability_notes: str
    strategic_insight: str
    data_sourcing: List[DataSourcingEntry] = Field(default_factory=list)


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


def _collect_domain_feature_ids(domains_dir: Path, domain: str) -> Set[str]:
    """All feature ids across every epic's features.yaml for one domain — ids are
    merged domain-wide (not namespaced by epic), matching the same aggregation
    query-discovery's `features` command already does (see core.py::get_filtered_features),
    so a duplicate id across two epics of the same domain is a pre-existing ambiguity
    of that convention, not something this check can or needs to resolve."""
    ids: Set[str] = set()
    for _features_file, data in iter_epic_feature_files(domains_dir / domain):
        for bucket_items in data.get("features", {}).values():
            if not isinstance(bucket_items, list):
                continue
            for item in bucket_items:
                if isinstance(item, dict) and item.get("id"):
                    ids.add(item["id"])
    return ids


def _validate_data_sourcing_links(
    config: TechConstraintsConfig, domains_dir: Path
) -> List[str]:
    """Anti-Hallucination gate for data-miner's cross-domain feature references
    (Tracer Pattern target of tech-synthesizer Step 7): each `domain`/`feature_id`
    pair must resolve to a real entry the domain actually wrote, not a name
    data-miner or tech-synthesizer invented while summarizing."""
    errors: List[str] = []
    domain_ids_cache: dict[str, Set[str]] = {}
    for entry in config.data_sourcing:
        if not (domains_dir / entry.domain).is_dir():
            errors.append(
                f"data_sourcing: domain '{entry.domain}' (feature_id='{entry.feature_id}') "
                f"does not exist under {domains_dir}"
            )
            continue
        if entry.domain not in domain_ids_cache:
            domain_ids_cache[entry.domain] = _collect_domain_feature_ids(
                domains_dir, entry.domain
            )
        if entry.feature_id not in domain_ids_cache[entry.domain]:
            errors.append(
                f"data_sourcing: feature_id '{entry.feature_id}' not found in any "
                f"features.yaml under domains/{entry.domain}/epics/*/ "
                f"(hallucinated or renamed feature reference)"
            )
    return errors


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

    config = validate_yaml_file(file_path, TechConstraintsConfig)

    if config.data_sourcing:
        # tech_constraints.yaml lives at workspace/discovery/strategy/tech_constraints.yaml;
        # domains live at the sibling workspace/discovery/domains/.
        domains_dir = file_path.parent.parent / "domains"
        link_errors = _validate_data_sourcing_links(config, domains_dir)
        if link_errors:
            raise ValueError("; ".join(link_errors))

    return config
