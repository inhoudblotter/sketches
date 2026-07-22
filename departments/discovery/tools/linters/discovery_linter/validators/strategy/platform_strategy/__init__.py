from departments.discovery.tools.linters.discovery_linter.validators.shared.validation_utils import (
    validate_yaml_file,
)
from pydantic import BaseModel
from typing import List, Optional, Union
from pathlib import Path
from departments.discovery.tools.shared.file_utils import load_yaml
from .rules.validators import validate_banned_words, validate_no_shared_context


class Platform(BaseModel):
    id: str
    name: str
    is_headless: Optional[Union[bool, str]] = None
    description: str
    target_users: List[str]
    supported_domains: List[str]


class PlatformStrategySchema(BaseModel):
    architecture_topology: Optional[str] = None
    strategic_insight: Optional[str] = None
    platforms: List[Platform]


def run_validation(file_path: Path) -> PlatformStrategySchema:
    data = load_yaml(file_path)

    validate_no_shared_context(file_path, data)
    validate_banned_words(data)

    return validate_yaml_file(file_path, PlatformStrategySchema)
