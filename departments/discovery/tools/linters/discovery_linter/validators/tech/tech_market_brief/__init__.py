from pydantic import BaseModel, Field
from typing import List
from departments.discovery.tools.linters.discovery_linter.validators.shared.validation_utils import (
    validate_yaml_file,
)
import yaml
from pathlib import Path


class ExpectedLoad(BaseModel):
    target_mau: str
    peak_events: str


class GeopoliticalRisks(BaseModel):
    censorship_probability: str
    splinternet_barriers: str
    data_residency_requirements: str


class CompetitorsTechSignals(BaseModel):
    known_bottlenecks: str
    architecture_hints: str


class PlatformFocus(BaseModel):
    primary_devices: str
    connectivity_quality: str


class TechMarketBriefSchema(BaseModel):
    audience_technical_literacy: str
    expected_load: ExpectedLoad
    geopolitical_risks: GeopoliticalRisks
    compliance_flags: List[str]
    competitors_tech_signals: CompetitorsTechSignals
    platform_focus: PlatformFocus


class ValidateTechMarketBriefInput(BaseModel):
    file_path: str


class ValidateTechMarketBriefOutput(BaseModel):
    is_valid: bool
    errors: List[str] = Field(default_factory=list)


def run_validation(file_path: Path, fix: bool = True):

    if not file_path.exists() and fix:
        default_content = {
            "audience_technical_literacy": "Unknown",
            "expected_load": {"target_mau": "Unknown", "peak_events": "Unknown"},
            "geopolitical_risks": {
                "censorship_probability": "Unknown",
                "splinternet_barriers": "Unknown",
                "data_residency_requirements": "Unknown",
            },
            "compliance_flags": [],
            "competitors_tech_signals": {
                "known_bottlenecks": "Unknown",
                "architecture_hints": "Unknown",
            },
            "platform_focus": {
                "primary_devices": "Unknown",
                "connectivity_quality": "Unknown",
            },
        }
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(default_content, f, allow_unicode=True, sort_keys=False)
        pass

    return validate_yaml_file(file_path, TechMarketBriefSchema)
