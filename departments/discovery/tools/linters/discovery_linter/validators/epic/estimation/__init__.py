from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Dict, Optional
import yaml
from pathlib import Path
from pydantic import ValidationError


class ArchitecturalRisk(BaseModel):
    risk: str
    impact: str
    description: str
    action_required: str
    model_config = ConfigDict(extra="allow")


class Rationale(BaseModel):
    technical_scope: str
    promptability: str
    verifiability: str
    blindspots: str
    model_config = ConfigDict(extra="allow")


class EstimationItem(BaseModel):
    story_id: str
    story_points: int
    dependencies: List[str] = Field(default_factory=list)
    rationale: Rationale
    flags: Optional[Dict[str, str]] = None
    model_config = ConfigDict(extra="allow")

    @field_validator("story_points")
    @classmethod
    def check_fibonacci(cls, v: int) -> int:
        allowed = {1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144}
        if v not in allowed:
            raise ValueError(
                f"story_points must be a valid Fibonacci number up to 144. Got: {v}"
            )
        return v

    @field_validator("flags")
    @classmethod
    def check_allowed_flags(
        cls, v: Optional[Dict[str, str]]
    ) -> Optional[Dict[str, str]]:
        if v is None:
            return v
        # Контракт разрешает добавлять свои теги, но они должны быть в формате [TAG NAME]
        invalid_format = [f for f in v if not (f.startswith("[") and f.endswith("]"))]
        if invalid_format:
            raise ValueError(
                f"Custom flags must be enclosed in square brackets like [FLAG NAME]. Invalid: {invalid_format}"
            )
        return v


class EstimationSchema(BaseModel):
    epic_id: str
    architectural_risks: List[ArchitecturalRisk] = Field(default_factory=list)
    estimations: List[EstimationItem]
    model_config = ConfigDict(extra="allow")


class ValidateEstimationOutput(BaseModel):
    is_valid: bool
    errors: List[str] = Field(default_factory=list)


def _create_default_estimation(file_path: Path) -> None:
    epic_id = file_path.parent.name
    default_content = {"epic_id": epic_id, "estimations": []}
    with open(file_path, "w", encoding="utf-8") as f:
        yaml.dump(default_content, f, allow_unicode=True, sort_keys=False)


def _load_valid_stories(stories_path: Path) -> set:
    if not stories_path.exists():
        return set()
    with open(stories_path, "r", encoding="utf-8") as f:
        stories_data = yaml.safe_load(f) or {}
    return {s["id"] for s in stories_data.get("stories", []) if "id" in s}


def _validate_story_coverage(
    parsed_data: EstimationSchema, valid_stories: set
) -> List[str]:
    errors = []
    estimated_stories = {item.story_id for item in parsed_data.estimations}

    missing_stories = [s for s in estimated_stories if s not in valid_stories]
    if missing_stories and valid_stories:
        errors.append(
            f"Invalid story_id in estimations: {missing_stories} (Not found in stories.yaml)"
        )

    if valid_stories:
        uncovered = valid_stories - estimated_stories
        if uncovered:
            errors.append(
                f"Incomplete coverage: the following job stories are not estimated: {sorted(uncovered)}"
            )

    return errors


def run_validation(file_path: Path, fix: bool = True) -> ValidateEstimationOutput:
    if not file_path.exists():
        if fix:
            _create_default_estimation(file_path)
            return ValidateEstimationOutput(is_valid=True)
        return ValidateEstimationOutput(
            is_valid=False, errors=[f"File not found: {file_path}"]
        )

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if data is None:
                raise ValueError("File is empty")
    except Exception as e:
        return ValidateEstimationOutput(
            is_valid=False, errors=[f"YAML parsing error: {e}"]
        )

    try:
        parsed_data = EstimationSchema(**data)
    except ValidationError as e:
        errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
        return ValidateEstimationOutput(is_valid=False, errors=errors)

    valid_stories = _load_valid_stories(file_path.parent / "stories.yaml")
    errors = _validate_story_coverage(parsed_data, valid_stories)

    if errors:
        return ValidateEstimationOutput(is_valid=False, errors=errors)

    return ValidateEstimationOutput(is_valid=True)
