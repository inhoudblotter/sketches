from pydantic import BaseModel, ConfigDict, Field
from typing import List
import yaml
from pathlib import Path

from departments.discovery.tools.linters.discovery_linter.validators.shared.validation_utils import (
    validate_yaml_file,
)
from departments.discovery.tools.linters.discovery_linter.validators.shared.job_story_refs import (
    resolve_workspace_dir,
    all_job_story_ids,
    unknown_refs,
)


class OverrideEntry(BaseModel):
    job_story_refs: List[str] = Field(default_factory=list)
    conflict: str
    resolution: str
    source: str
    model_config = ConfigDict(extra="allow")


class UxConstraintsSchema(BaseModel):
    author_agent: str
    overrides: List[OverrideEntry] = Field(default_factory=list)
    architect_note: str = ""
    model_config = ConfigDict(extra="allow")


class ValidateUxConstraintsInput(BaseModel):
    file_path: str


class ValidateUxConstraintsOutput(BaseModel):
    is_valid: bool
    errors: List[str] = Field(default_factory=list)


def run_validation(file_path: Path, fix: bool = True):

    if not file_path.exists() and fix:
        default_content = {
            "author_agent": "tech-synthesizer",
            "overrides": [],
            "architect_note": "",
        }
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(default_content, f, allow_unicode=True, sort_keys=False)
        pass

    try:
        model = validate_yaml_file(file_path, UxConstraintsSchema)
    except Exception as e:
        return ValidateUxConstraintsOutput(is_valid=False, errors=[str(e)])

    # Referential integrity: job_story_refs в overrides должны указывать на
    # реально существующие Job Stories. known_ids пуст => воркспейса нет
    # рядом (изолированный фикстур) — проверка пропускается, а не падает.
    workspace_dir = resolve_workspace_dir(file_path, levels_up=3)
    known_ids = all_job_story_ids(workspace_dir)
    errors: List[str] = []
    for entry in model.overrides:
        bad = unknown_refs(entry.job_story_refs, known_ids)
        if bad:
            errors.append(
                f"overrides[conflict={entry.conflict!r}]: неизвестные job_story_refs {bad}"
            )
    if errors:
        return ValidateUxConstraintsOutput(is_valid=False, errors=errors)
    return ValidateUxConstraintsOutput(is_valid=True)
