from pydantic import RootModel
from departments.discovery.tools.linters.discovery_linter.validators.shared.validation_utils import (
    validate_yaml_file,
)
import yaml
from pathlib import Path
from .filters.ui_noise import filter_ui_noise

from pydantic import BaseModel, Field
from typing import List, Optional


class ErrataEntry(BaseModel):
    id: str
    description: str
    severity: str
    domain: Optional[str] = None
    status: Optional[str] = "open"
    resolution: Optional[str] = None
    patch_ref: Optional[str] = None


class ErratumCollection(RootModel[List[ErrataEntry]]):
    pass


class ValidationResult(BaseModel):
    is_valid: bool
    fixed: bool = False
    errors: List[str] = Field(default_factory=list)


def format_errata(data: list) -> list:
    if not isinstance(data, list):
        data = data["errata"] if isinstance(data, dict) and "errata" in data else []

    return filter_ui_noise(data)


def run_validation(file_path: Path, fix: bool = True):

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if fix:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        new_data = format_errata(data)
        if new_data != data:
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.dump(new_data, f, allow_unicode=True, sort_keys=False)

    return validate_yaml_file(file_path, ErratumCollection)
