from departments.discovery.tools.linters.discovery_linter.validators.shared.validation_utils import (
    validate_yaml_file,
)
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional

from .rules.structure_validator import validate_structure
from .rules.fluff_linter import validate_fluff


class PitchDeckInput(BaseModel):
    file_path: str = Field(description="Path to the pitch deck YAML file")


class ValidationErrorDetail(BaseModel):
    rule: str
    message: str


class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[ValidationErrorDetail] = []


class TitleSlide(BaseModel):
    title: str
    subtitle: Optional[str] = None


class SlideContent(BaseModel):
    content: str


class MandatorySlides(BaseModel):
    problem: SlideContent
    solution: SlideContent
    market_and_competition: SlideContent
    go_to_market: SlideContent
    risks: SlideContent
    final_verdict: SlideContent


class OptionalSlides(BaseModel):
    network_effects_and_decentralization: Optional[SlideContent] = None


class PitchDeckSchema(BaseModel):
    title_slide: TitleSlide
    mandatory_slides: MandatorySlides
    optional_slides: Optional[OptionalSlides] = None


def run_validation(file_path: Path, fix: bool = False):
    """
    Core business logic for validating a pitch deck.
    """
    model = validate_yaml_file(file_path, PitchDeckSchema)
    data = model.model_dump()
    validate_structure(data)

    fluff_errors = validate_fluff(data)
    errors = []
    for err in fluff_errors:
        errors.append(ValidationErrorDetail(rule="no_marketing_fluff", message=err))

    is_valid = len(errors) == 0
    return ValidationResult(is_valid=is_valid, errors=errors)
