from pydantic import BaseModel, ConfigDict, Field
from typing import Dict, List, Optional
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


class PerceptualThreshold(BaseModel):
    interaction_class: str
    tolerance_ms: int
    source: str
    model_config = ConfigDict(extra="allow")


class PlatformResearch(BaseModel):
    environmental_context: str = ""
    device_constraints: str = ""
    perceptual_thresholds: List[PerceptualThreshold] = Field(default_factory=list)
    accessibility_level: str = ""
    model_config = ConfigDict(extra="allow")


class InteractionPattern(BaseModel):
    job_story_refs: List[str] = Field(default_factory=list)
    pattern: str
    source: str
    model_config = ConfigDict(extra="allow")


class KnownPitfall(BaseModel):
    job_story_refs: List[str] = Field(default_factory=list)
    pitfall: str
    consequence: str
    source: str
    model_config = ConfigDict(extra="allow")


class UxResearchSchema(BaseModel):
    author_agent: str
    by_platform: Dict[str, PlatformResearch] = Field(default_factory=dict)
    interaction_patterns: List[InteractionPattern] = Field(default_factory=list)
    known_pitfalls: List[KnownPitfall] = Field(default_factory=list)
    qualitative_analysis: Optional[str] = None
    model_config = ConfigDict(extra="allow")


class ValidateUxResearchInput(BaseModel):
    file_path: str


class ValidateUxResearchOutput(BaseModel):
    is_valid: bool
    errors: List[str] = Field(default_factory=list)


def run_validation(file_path: Path, fix: bool = True):

    if not file_path.exists() and fix:
        default_content = {
            "author_agent": "ux-scout",
            "by_platform": {},
            "interaction_patterns": [],
            "known_pitfalls": [],
            "qualitative_analysis": "",
        }
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(default_content, f, allow_unicode=True, sort_keys=False)
        pass

    try:
        model = validate_yaml_file(file_path, UxResearchSchema)
    except Exception as e:
        return ValidateUxResearchOutput(is_valid=False, errors=[str(e)])

    # Referential integrity: job_story_refs должны указывать на реально
    # существующие Job Stories (в любом домене — этот файл проектный, не
    # доменный). known_ids пуст => воркспейса нет рядом (изолированный
    # фикстур) — проверка пропускается, а не падает.
    workspace_dir = resolve_workspace_dir(file_path, levels_up=4)
    known_ids = all_job_story_ids(workspace_dir)
    errors: List[str] = []
    for entry in model.interaction_patterns:
        bad = unknown_refs(entry.job_story_refs, known_ids)
        if bad:
            errors.append(
                f"interaction_patterns[pattern={entry.pattern!r}]: неизвестные job_story_refs {bad}"
            )
    for pitfall_entry in model.known_pitfalls:
        bad = unknown_refs(pitfall_entry.job_story_refs, known_ids)
        if bad:
            errors.append(
                f"known_pitfalls[pitfall={pitfall_entry.pitfall!r}]: неизвестные job_story_refs {bad}"
            )
    if errors:
        return ValidateUxResearchOutput(is_valid=False, errors=errors)
    return ValidateUxResearchOutput(is_valid=True)
