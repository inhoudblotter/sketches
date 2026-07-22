from pydantic import BaseModel, Field
from typing import List
import yaml
from pathlib import Path

from departments.discovery.tools.linters.discovery_linter.validators.shared.validation_utils import (
    validate_yaml_file,
)


class UxFlags(BaseModel):
    offline_first: bool
    is_self_hosted: bool


class FrictionManagement(BaseModel):
    intentional_friction: str
    cognitive_load: str


class DeviceSpecifics(BaseModel):
    primary_input: str
    accessibility_level: str


class UxConstraintsSchema(BaseModel):
    flags: UxFlags
    architect_note: str
    friction_management: FrictionManagement
    device_specifics: DeviceSpecifics


class ValidateUxConstraintsInput(BaseModel):
    file_path: str


class ValidateUxConstraintsOutput(BaseModel):
    is_valid: bool
    errors: List[str] = Field(default_factory=list)


def run_validation(file_path: Path, fix: bool = True):

    if not file_path.exists() and fix:
        default_content = {
            "flags": {"offline_first": False, "is_self_hosted": False},
            "architect_note": "Автоматически сгенерировано. Требует ревью.",
            "friction_management": {
                "intentional_friction": "N/A",
                "cognitive_load": "N/A",
            },
            "device_specifics": {
                "primary_input": "Touchscreen",
                "accessibility_level": "WCAG 2.1 AA",
            },
        }
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(default_content, f, allow_unicode=True, sort_keys=False)
        pass

    try:
        validate_yaml_file(file_path, UxConstraintsSchema)
    except Exception as e:
        return ValidateUxConstraintsOutput(is_valid=False, errors=[str(e)])
    return ValidateUxConstraintsOutput(is_valid=True)
