from departments.discovery.tools.linters.discovery_linter.validators.shared.validation_utils import (
    validate_yaml_file,
)
from pydantic import BaseModel, Field
from typing import List, Optional, Union
import yaml
from pathlib import Path
from .validators.rules import validate_revenue_data, format_revenue_data


class RevenueStream(BaseModel):
    id: Optional[str] = None
    type: Optional[str] = None
    evidence_tier: Optional[str] = None
    commitment_status: Optional[str] = None
    target_audience: Optional[str] = None
    arpu_monthly_usd: Optional[Union[float, str]] = None
    expected_share_percent: Optional[Union[float, str]] = None
    source_hypothesis: Optional[str] = None
    wtp_validation_status: Optional[str] = None
    confidence: Optional[str] = None
    rationale: Optional[str] = None


class NonArpuFunding(BaseModel):
    id: Optional[str] = None
    type: Optional[str] = None
    source: Optional[str] = None
    total_amount_usd: Optional[Union[float, str]] = None
    runway_months: Optional[Union[int, str]] = None
    application_status: Optional[str] = None
    confidence: Optional[str] = None
    rationale: Optional[str] = None
    monthly_runway_offset_usd: Optional[Union[float, str]] = None


class SpeculativeScenario(BaseModel):
    included_stream_ids: Optional[Union[str, List[str]]] = None
    combined_confidence: Optional[str] = None
    projected_uplift_arpu_usd: Optional[Union[float, str]] = None
    blended_arpu_with_speculative_usd: Optional[Union[float, str]] = None


class ScenarioBand(BaseModel):
    driver_ref: str
    target_mau: Union[int, str]
    blended_arpu_usd: Union[float, str]


class ScenarioBands(BaseModel):
    worst: ScenarioBand
    base: ScenarioBand
    best: ScenarioBand


class RevenueModelConfig(BaseModel):
    author_agent: str
    target_mau: Union[int, str]
    revenue_streams: List[RevenueStream]
    non_arpu_funding: Optional[List[NonArpuFunding]] = None
    blended_arpu_usd: Union[float, str]
    budget_constraint_usd: Union[float, str]
    strategic_insight: str
    speculative_scenario: Optional[SpeculativeScenario] = None
    scenario_bands: Optional[ScenarioBands] = None


class ValidationResult(BaseModel):
    is_valid: bool
    fixed: bool = False
    errors: List[str] = Field(default_factory=list)


def run_validation(file_path: Path, fix: bool = True):

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if fix:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if isinstance(data, dict):
            data = format_revenue_data(data)
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    model = validate_yaml_file(file_path, RevenueModelConfig)
    is_valid, errors = validate_revenue_data(model.model_dump())
    if not is_valid:
        raise ValueError(f"Revenue validation failed: {errors}")
    return model
