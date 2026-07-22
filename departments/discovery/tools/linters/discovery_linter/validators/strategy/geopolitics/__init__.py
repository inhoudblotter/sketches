from departments.discovery.tools.linters.discovery_linter.validators.shared.validation_utils import (
    validate_yaml_file,
)
from pydantic import BaseModel, Field
from typing import List
import yaml
from pathlib import Path


class RiskItem(BaseModel):
    category: str
    description: str
    severity: str
    mitigation_strategy: str


class GeopoliticalDraft(BaseModel):
    splinternet_paranoia: str
    access_resilience: str
    ideological_neutrality: str
    risks: List[RiskItem] = Field(default_factory=list)
    strategic_recommendation: str


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
            fixed = False
            required_str_keys = [
                "splinternet_paranoia",
                "access_resilience",
                "ideological_neutrality",
                "strategic_recommendation",
            ]
            for key in required_str_keys:
                if key not in data or data[key] is None:
                    data[key] = "TBD"
                    fixed = True
                elif not isinstance(data[key], str):
                    data[key] = str(data[key])
                    fixed = True

            if "risks" not in data:
                data["risks"] = []
                fixed = True
            elif not isinstance(data["risks"], list):
                data["risks"] = [data["risks"]]
                fixed = True

            if fixed:
                with open(file_path, "w", encoding="utf-8") as f:
                    yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    return validate_yaml_file(file_path, GeopoliticalDraft)
